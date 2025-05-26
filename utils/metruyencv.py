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

def crawl_books(limit=20, max_page=2):  # Chỉ crawl 2 page test thôi, tránh quá tải
    r2_index_key = f"{R2_PREFIX}/index.json"
    old_books = {str(book['id']): book for book in read_from_r2(r2_index_key)}
    all_books = []
    for page in range(1, max_page + 1):
        url = f"https://backend.metruyencv.com/api/books?limit={limit}&page={page}"
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"Error at page {page}: {e}")
            continue
        js = resp.json()
        for item in js.get('data', []):
            book = {
                "id": item["id"],
                "name": item["name"],
                "link": item["link"],
                "poster": item["poster"].get("150", ""),
            }
            if str(book['id']) in old_books and 'chapterCount' in old_books[str(book['id'])]:
                book['chapterCount'] = old_books[str(book['id'])]['chapterCount']
            all_books.append(book)
    upload_to_r2(r2_index_key, all_books)
    return all_books

def crawl_chapters(book_id):
    r2_chapter_key = f"{R2_PREFIX}/{book_id}/chapters.json"
    existed = read_from_r2(r2_chapter_key)
    if existed:
        return existed
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
    return chapters


def crawl_chapter_content_batch(book, chapters):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
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

def crawl_batch(start_page, end_page, limit=20, chapters_per_book=None):
    books = crawl_books(limit=limit, max_page=end_page)
    # Lấy đúng sách thuộc batch này
    batch_books = books[(start_page-1)*limit : end_page*limit]
    for book in batch_books:
        chapters = crawl_chapters(book["id"])
        # Crawl tất cả hoặc 1 số chương
        chaps = chapters if chapters_per_book is None else chapters[:chapters_per_book]
        crawl_chapter_content_batch(book, chaps)
