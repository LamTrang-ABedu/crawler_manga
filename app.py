import threading
from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import html
import json
import os
import boto3
from datetime import datetime

app = Flask(__name__)

BASE_URL = "https://tranh18x.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 15

R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID')
R2_BUCKET = 'hopehub-storage'

s3 = boto3.client('s3',
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY
)

def upload_to_r2(key, data):
    s3 = boto3.client('s3',
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY
    )
    try:
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType='application/json'
        )
        print(f"[UPLOAD] {key} uploaded successfully")
    except Exception as e:
        print(f"[UPLOAD ERROR] {key}: {e}")

def read_from_r2(key):
    try:
        res = s3.get_object(Bucket=R2_BUCKET, Key=key)
        return json.loads(res['Body'].read().decode('utf-8'))
    except:
        return {"comics": []}

def get_comic_list(max_page=359):
    all_comics = []
    for page in range(1, max_page + 1):
        url = f"{BASE_URL}/comics?page={page}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        except Exception as e:
            print(f"[ERROR] Failed to fetch page {page}: {e}")
            break
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
    try:
        res = requests.get(comic_url, headers=HEADERS, timeout=TIMEOUT)
    except:
        return []
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
    try:
        res = requests.get(chapter_url, headers=HEADERS, timeout=TIMEOUT)
    except:
        return []
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
    key = "comics/tranh18.json"
    full_data = read_from_r2(key)
    comics_data = full_data.get("comics", [])
    existing_by_url = {c["url"]: c for c in comics_data}

    comics = get_comic_list()
    for i, comic in enumerate(comics):
        print(f"[SYNC] [{i+1}/{len(comics)}] Crawling: {comic['name']}")
        if comic["url"] in existing_by_url:
            existing_comic = existing_by_url[comic["url"]]
            existing_chapter_urls = {c['url'] for c in existing_comic.get("chapters", [])}
        else:
            existing_comic = {
                "name": comic["name"],
                "image": comic["image"],
                "url": comic["url"],
                "chapters": []
            }
            existing_chapter_urls = set()

        chapters = get_chapters(comic["url"])
        for j, chap in enumerate(chapters):
            if chap["url"] in existing_chapter_urls:
                print(f"[SKIP]    [{j+1}/{len(chapters)}] Chapter exists: {chap['name']}")
                continue
            print(f"[SYNC]    [{j+1}/{len(chapters)}] Crawling chapter: {chap['name']}")
            try:
                images = get_images(chap["url"])
                existing_comic["chapters"].append({
                    "name": chap["name"],
                    "url": chap["url"],
                    "images": images
                })
            except Exception as e:
                print(f"[ERROR] Failed to crawl chapter {chap['name']}: {e}")

        # update or append comic
        if comic["url"] in existing_by_url:
            existing_by_url[comic["url"]] = existing_comic
        else:
            comics_data.append(existing_comic)
            existing_by_url[comic["url"]] = existing_comic

        upload_to_r2(key, {"comics": comics_data})

@app.route("/api/tranh18x-sync", methods=["POST"])
def sync_all_route():
    threading.Thread(target=sync_all).start()
    return jsonify({"status": "started"})

if __name__ == "__main__":
    threading.Thread(target=sync_all).start()
    app.run(host="0.0.0.0", port=8000)
