import requests
from .common import slugify, read_from_r2, upload_to_r2

BASE_URL = "https://mimihentai.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 15
INDEX_KEY = "comics/mimihentai/index.json"
COMIC_DIR = "comics/mimihentai/"

def get_manga_list():
    manga_list = []
    page = 0
    while True:
        try:
            res = requests.get(f"{BASE_URL}/api/v1/manga/tatcatruyen?page={page}", headers=HEADERS, timeout=TIMEOUT)
            data = res.json().get("data", [])
            if not data:
                print(f"[INFO] No more manga found at page {page}")
                break
            for item in data:
                print(f"[INFO] Found manga: {item.get('title')}")
                manga_list.append({
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "slug": slugify(item.get("title", "")),
                    "coverUrl": item.get("coverUrl"),
                    "updatedAt": item.get("updatedAt")
                })
            page += 1
        except Exception as e:
            print(f"[ERROR] manga list page {page}: {e}")
            break
    return manga_list

def get_chapters(manga_id):
    try:
        url = f"{BASE_URL}/api/v1/manga/gallery/{manga_id}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        return res.json()
    except:
        return []

def get_images(chapter_id):
    try:
        url = f"{BASE_URL}/api/v1/manga/chapter?id={chapter_id}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        return res.json().get("pages", [])
    except:
        return []

def sync_one_manga(manga, existing_slugs):
    slug = manga["slug"]
    detail_key = f"{COMIC_DIR}{slug}.json"
    detail_data = read_from_r2(detail_key) if slug in existing_slugs else {
        "name": manga["title"], "slug": slug, "image": manga["coverUrl"], "chapters": []
    }
    known_ids = {c["id"] for c in detail_data.get("chapters", [])}
    chapters = get_chapters(manga["id"])
    print(f"[INFO] Found {len(chapters)} chapters for {manga['title']}")
    for chap in chapters:
        if chap["id"] in known_ids:
            continue
        images = get_images(chap["id"])
        print(f"[INFO] Found {len(images)} images for chapter {chap['id']}")
        detail_data["chapters"].append({
            "name": chap.get("title", f"Chap {chap['id']}"),
            "id": chap["id"],
            "images": images
        })
    upload_to_r2(detail_key, detail_data)
    return {
        "name": manga["title"],
        "slug": slug,
        "image": manga["coverUrl"],
        "chapterCount": len(detail_data["chapters"])
    }

def sync_all_manga():
    manga_list = get_manga_list()
    current_index = read_from_r2(INDEX_KEY)
    existing_slugs = {c["slug"] for c in current_index}
    new_index = [sync_one_manga(m, existing_slugs) for m in manga_list]
    upload_to_r2(INDEX_KEY, new_index)

def sync_latest_manga(slug):
    manga_list = get_manga_list()
    current_index = read_from_r2(INDEX_KEY)
    existing_slugs = {c["slug"] for c in current_index}
    for m in manga_list:
        if m["slug"] == slug:
            info = sync_one_manga(m, existing_slugs)
            upload_to_r2(INDEX_KEY, [info if i["slug"] == slug else i for i in current_index])
            break