from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import html
import json
import os
import boto3
from datetime import datetime
import threading

app = Flask(__name__)

BASE_URL = "https://tranh18x.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

R2_BUCKET = "hopehub-storage"
R2_ENDPOINT = "https://pub-a849c091b30844d5aee5e88b7f6fb5d1.r2.cloudflarestorage.com"  # Replace this with actual endpoint
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")

s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

def upload_to_r2(key, data):
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    return f"{R2_ENDPOINT}/{R2_BUCKET}/{key}"

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

def sync_all():
    result = []
    comics = get_comic_list()
    for comic in comics:
        comic_data = {
            "name": comic["name"],
            "image": comic["image"],
            "url": comic["url"],
            "chapters": []
        }
        chapters = get_chapters(comic["url"])
        for chap in chapters:
            images = get_images(chap["url"])
            comic_data["chapters"].append({
                "name": chap["name"],
                "url": chap["url"],
                "images": images
            })
        result.append(comic_data)

    key = "tranh18x/full_catalog.json"
    url = upload_to_r2(key, {"total": len(result), "comics": result})
    return jsonify({"stored_url": url, "total": len(result)})

# Tự chạy crawl sau khi server start
def run_background_crawler():
    print("[INFO] Starting background sync_all()")
    try:
        sync_all()
        print("[INFO] Sync finished")
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_background_crawler).start()
    app.run(host="0.0.0.0", port=8000)
