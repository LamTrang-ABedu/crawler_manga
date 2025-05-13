import html
import requests
from bs4 import BeautifulSoup
from .common import slugify, read_from_r2, upload_to_r2

BASE_URL = "https://tranh18x.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 15
INDEX_KEY = "comics/index.json"
COMIC_DIR = "comics/tranh18/"

def get_comic_list(max_page=100):
    comics = []
    for page in range(1, max_page + 1):
        url = f"{BASE_URL}/comics?page={page}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if res.status_code != 200:
                break
            soup = BeautifulSoup(res.text, "html.parser")
            script_tag = soup.find("script", type="application/ld+json")
            if not script_tag:
                break
            data = eval(script_tag.string.strip())
            for item in data.get("itemListElement", []):
                name = html.unescape(item.get("name", ""))
                comics.append({
                    "name": name,
                    "slug": slugify(name),
                    "image": item.get("image", ""),
                    "url": item.get("url", "")
                })
        except Exception as e:
            print(f"[ERROR] get_comic_list page {page}: {e}")
            break
    return comics

def get_chapters(comic_url):
    try:
        res = requests.get(comic_url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(res.text, "html.parser")
        tags = soup.select("#chapterlistload ul#detail-list-select li a")
        return [{
            "name": html.unescape(tag.get("title", "")).strip(),
            "url": f"{BASE_URL}{tag.get('href', '')}"
        } for tag in tags]
    except:
        return []

def get_images(chapter_url):
    try:
        res = requests.get(chapter_url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(res.text, "html.parser")
        return [
            img.get("data-original", "").split("?u=")[-1]
            for img in soup.select("div.comiclist div.comicpage img.lazy")
        ]
    except:
        return []

def sync_one_comic(comic, existing_slugs):
    slug = comic["slug"]
    detail_key = f"{COMIC_DIR}{slug}.json"
    detail_data = read_from_r2(detail_key) if slug in existing_slugs else {
        "name": comic["name"], "slug": slug, "image": comic["image"], "chapters": []
    }
    known_chapters = {c["url"] for c in detail_data.get("chapters", [])}
    chapters = get_chapters(comic["url"])
    for chap in chapters:
        if chap["url"] in known_chapters:
            continue
        images = get_images(chap["url"])
        detail_data["chapters"].append({
            "name": chap["name"], "url": chap["url"], "images": images
        })
    upload_to_r2(detail_key, detail_data)
    return {
        "name": comic["name"],
        "slug": slug,
        "image": comic["image"],
        "chapterCount": len(detail_data["chapters"])
    }

def sync_all_comics():
    comic_list = get_comic_list()
    current_index = read_from_r2(INDEX_KEY)
    existing_slugs = {c["slug"] for c in current_index}
    new_index = [sync_one_comic(c, existing_slugs) for c in comic_list]
    upload_to_r2(INDEX_KEY, new_index)

def sync_latest_comic(slug):
    comic_list = get_comic_list()
    current_index = read_from_r2(INDEX_KEY)
    existing_slugs = {c["slug"] for c in current_index}
    for c in comic_list:
        if c["slug"] == slug:
            info = sync_one_comic(c, existing_slugs)
            upload_to_r2(INDEX_KEY, [info if i["slug"] == slug else i for i in current_index])
            break
