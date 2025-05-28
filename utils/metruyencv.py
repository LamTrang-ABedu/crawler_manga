import os
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import random
import tempfile

from .common import slugify, upload_to_r2, read_from_r2

R2_PREFIX = "Ebook/metruyencv"
R2_INDEX_KEY = f"{R2_PREFIX}/index.json"
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_PATH = os.path.join(CUR_DIR, "cookies.json")

def load_cookies_to_driver(driver):
    with open(COOKIES_PATH, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    driver.get("https://metruyencv.com/")  # Load domain first
    time.sleep(1)
    for cookie in cookies:
        c = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie.get("domain", ".metruyencv.com"),
            "path": cookie.get("path", "/")
        }
        try:
            driver.add_cookie(c)
        except Exception as e:
            continue
    driver.refresh()
    time.sleep(1)

def crawl_books():
    old_books = read_from_r2(R2_INDEX_KEY) or []
    # Xoá duplicate theo id, giữ book đầu tiên
    unique_books = {}
    for book in old_books:
            if book["id"] not in unique_books:
                unique_books[book["id"]] = book
    final_books = list(unique_books.values())

    upload_to_r2(R2_INDEX_KEY, final_books)
    return final_books
    # existing_ids = {book["id"] for book in old_books}
    # new_books = []
    # page = 1
    # while page <= 769:  # Giả sử có 769 trang
    #     url = f"https://backend.metruyencv.com/api/books?limit=20&page={page}"
    #     try:
    #         resp = requests.get(url, timeout=20)
    #         resp.raise_for_status()
    #     except Exception as e:
    #         print(f"Error at page {page}: {e}")
    #         break
    #     js = resp.json()
    #     books = js.get('data', [])
    #     if not books:  # Giả sử có 769 trang
    #         break
    #     for item in books:
    #         book = {
    #             "id": item["id"],
    #             "name": item["name"],
    #             "link": item["link"],
    #             "poster": item["poster"].get("150", ""),
    #         }
    #         if book["id"] not in existing_ids:
    #             new_books.append(book)
    #             existing_ids.add(book["id"])
    #     print(f"[Crawl Books] Page {page} - {len(new_books)} new books found.")
    #     page += 1
    #     time.sleep(1.2 + random.uniform(0, 1.5))  # Thêm sleep tránh crash RAM/network

    # if new_books:
    #     old_books.extend(new_books)
    #     upload_to_r2(R2_INDEX_KEY, old_books)
    # return old_books

def crawl_chapters(book_id=None, all_books=[]):
    r2_chapter_key = f"{R2_PREFIX}/{book_id}/chapters.json"
    url = f"https://backend.metruyencv.com/api/chapters?filter%5Bbook_id%5D={book_id}"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error get chapters {book_id}: {e}")
        return []
    js = resp.json()
    chapters = []
    for ch in js.get('data', []):
        chapters.append({
            "index": ch["index"],
            "name": ch["name"]
        })
    upload_to_r2(r2_chapter_key, chapters)
    print(f"[Crawl Chapters] Book {book_id} - {len(chapters)} chapters found.")
    for item in all_books:
        if item["id"] == book_id:
            item["chapterCount"] = len(chapters)
            break
    upload_to_r2(R2_INDEX_KEY, all_books)
    time.sleep(1.2 + random.uniform(0, 1.5))  # Thêm sleep tránh crash RAM/network
    return chapters


def crawl_chapter_content_batch(book, chapters):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Thêm dòng này:
    user_data_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        load_cookies_to_driver(driver)
        for ch in chapters:
            index = ch["index"]
            r2_chap_key = f"{R2_PREFIX}/{book['id']}/chuong-{index}.json"
            if read_from_r2(r2_chap_key):
                print(f"[SKIP] Chapter {book['id']} - {index} đã có trên R2.")
                continue
            url = f"{book['link']}/chuong-{index}"
            print(f"Crawling {url} ...")
            try:
                driver.get(url)
                time.sleep(1.5 + random.uniform(0,1))  # Sleep nhẹ tránh bị block
                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")
                content = soup.select_one("#chapter-content")
                if not content:
                    print(f"Không tìm thấy nội dung chương {index}, có thể bị khóa/cookie hết hạn.")
                    continue
                for tag in content.find_all(["canvas", "div"]):
                    if tag.name == "canvas":
                        tag.decompose()
                    elif tag.get("id", "").startswith("middle-content"):
                        tag.decompose()
                content_html = content.decode_contents()
                content_text = content.get_text("\n", strip=True)
                chapter_data = {
                    "title": f"Chương {index}",
                    "content_html": content_html,
                    "content_text": content_text
                }
                upload_to_r2(r2_chap_key, chapter_data)
            except Exception as e:
                print(f"Error crawl chapter {index}: {e}")
            time.sleep(1.2 + random.uniform(0, 1.5))  # Thêm sleep tránh crash RAM/network
    finally:
        driver.quit()

def crawl_batch():
    batch_size=3
    max_page=769
    books = crawl_books()
    # Lấy đúng sách thuộc batch này
    # Chia từng batch nhỏ, chạy nối tiếp nhau
    for start_page in range(1, max_page + 1, batch_size):
        end_page = min(start_page + batch_size - 1, max_page)
        print(f"[Metruyencv] Crawling from page {start_page} to {end_page}")
        batch_books = books[(start_page-1)*20 : end_page*20]
        for book in batch_books:
            chapters = crawl_chapters(book_id=book["id"], all_books=books)
            # Crawl tất cả hoặc 1 số chương
            crawl_chapter_content_batch(book, chapters)
        time.sleep(90)  # nghỉ sau mỗi batch
