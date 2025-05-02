from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import html

app = Flask(__name__)

BASE_URL = "https://tranh18x.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_comic_list(max_page=359):
    all_comics = []
    for page in range(1, max_page + 1):
        url = f"{BASE_URL}/comics?page={page}"
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            break

        soup = BeautifulSoup(res.text, "html.parser")
        script_tag = soup.find("script", type="application/ld+json")
        if not script_tag:
            break

        try:
            json_data = eval(script_tag.string.strip())
            items = json_data.get("itemListElement", [])
            for item in items:
                all_comics.append({
                    "name": html.unescape(item.get("name", "")),
                    "image": item.get("image", ""),
                    "url": item.get("url", "")
                })
        except Exception as e:
            print(f"Error parsing page {page}: {e}")
            break
    return all_comics

def get_chapters(comic_url):
    res = requests.get(comic_url, headers=HEADERS)
    if res.status_code != 200:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    chapter_tags = soup.select("#chapterlistload ul#detail-list-select li a")

    chapters = []
    for tag in chapter_tags:
        href = tag.get("href", "")
        full_url = f"{BASE_URL}{href}"
        title = html.unescape(tag.get("title", "")).strip()
        chapters.append({
            "name": title,
            "url": full_url
        })
    return chapters

def get_images(chapter_url):
    res = requests.get(chapter_url, headers=HEADERS)
    if res.status_code != 200:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    img_tags = soup.select("div.comiclist div.comicpage img.lazy")
    image_urls = []
    for img in img_tags:
        raw_url = img.get("data-original", "")
        if "?u=" in raw_url:
            true_url = raw_url.split("?u=")[-1]
        else:
            true_url = raw_url
        image_urls.append(true_url)
    return image_urls

@app.route("/api/comics", methods=["GET"])
def api_comic_list():
    comics = get_comic_list()
    return jsonify({"total": len(comics), "comics": comics})

@app.route("/api/chapters", methods=["GET"])
def api_chapter_list():
    comic_url = request.args.get("url")
    if not comic_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    chapters = get_chapters(comic_url)
    return jsonify({"total": len(chapters), "chapters": chapters})

@app.route("/api/images", methods=["GET"])
def api_image_list():
    chapter_url = request.args.get("url")
    if not chapter_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    images = get_images(chapter_url)
    return jsonify({"total": len(images), "images": images})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
