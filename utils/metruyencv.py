import os
import json
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import json
from .common import slugify, upload_to_r2, read_from_r2

R2_PREFIX = "Ebook/metruyencv"
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_PATH = os.path.join(CUR_DIR, "cookies.json")

# === Crawl danh sách truyện ===
def crawl_books(limit=20, max_page=769):
    # Đọc index.json đã có trên R2 (nếu có)
    r2_index_key = f"{R2_PREFIX}/index.json"
    old_books = {str(book['id']): book for book in read_from_r2(r2_index_key)}
    all_books = []
    for page in tqdm(range(1, max_page + 1), desc='Crawling books'):
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
            # Merge chapterCount nếu đã crawl trước đó
            if str(book['id']) in old_books and 'chapterCount' in old_books[str(book['id'])]:
                book['chapterCount'] = old_books[str(book['id'])]['chapterCount']
            all_books.append(book)
    # Ghi lại index mới lên R2
    upload_to_r2(r2_index_key, all_books)
    return all_books

# === Crawl danh sách chương (trả về mảng, auto upload lên R2) ===
def crawl_chapters(book_id):
    r2_chapter_key = f"{R2_PREFIX}/{book_id}/chapters.json"
    # Nếu đã có trên R2 thì bỏ qua
    existed = read_from_r2(r2_chapter_key)
    if existed:
        # print(f"[SKIP] Chapters {book_id} đã có trên R2.")
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

def get_chapter_content_with_cookies(chapter_url):
    # Khởi tạo Chrome headless
    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.get("https://metruyencv.com/")
    time.sleep(2)

    # Load cookies
    with open(COOKIES_PATH, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    for cookie in cookies:
        c = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie.get("domain", ".metruyencv.com"),
            "path": cookie.get("path", "/")
        }
        driver.add_cookie(c)
    driver.refresh()
    time.sleep(2)

    driver.get(chapter_url)
    time.sleep(2)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("#chapter-content")
    if not content:
        print("Không tìm thấy nội dung chương, cookie hết hạn hoặc chương bị khóa.")
        driver.quit()
        return None, None
    # Xóa tag rác
    for tag in content.find_all(["canvas", "div"]):
        if tag.name == "canvas":
            tag.decompose()
        elif tag.get("id", "").startswith("middle-content"):
            tag.decompose()
    content_html = content.decode_contents()
    content_text = content.get_text("\n", strip=True)
    driver.quit()
    return content_html, content_text

def crawl_chapter_content(book_link, chapter_index, book_id):
    r2_chap_key = f"Ebook/metruyencv/{book_id}/chuong-{chapter_index}.json"
    # Nếu đã có trên R2 thì bỏ qua
    if read_from_r2(r2_chap_key):
        # print(f"[SKIP] Chapter {book_id} - {chapter_index} đã có trên R2.")
        return None
    url = f"{book_link}/chuong-{chapter_index}"
    content_html, content_text = get_chapter_content_with_cookies(url)
    if not content_html:
        print(f"[ERROR] Không lấy được nội dung chương {chapter_index} của {book_id}")
        return None
    # Optional: lấy title từ html nếu muốn
    chapter_data = {
        "title": f"Chương {chapter_index}",
        "content_html": content_html,
        "content_text": content_text
    }
    upload_to_r2(r2_chap_key, chapter_data)
    return chapter_data

# === Hàm chính: crawl full/update truyện ===
def sync_all_books(max_page=769, limit=20, chapters_per_book=1, crawl_full_chapters=True):
    books = crawl_books(limit=limit, max_page=max_page)
    # print(f"[INFO] Found {len(books)} books.")
    # Update index sau khi biết số chương thực tế
    r2_index_key = f"{R2_PREFIX}/index.json"
    for i, book in enumerate(tqdm(books, desc="Crawl chapters")):
        chapters = crawl_chapters(book["id"])
        # print(f"[INFO] Found {len(chapters)} chapters for {book['name']}")
        books[i]['chapterCount'] = len(chapters)
        # Crawl từng chương
        chaps = chapters if crawl_full_chapters else chapters[:chapters_per_book]
        for ch in tqdm(chaps, desc=f"{book['id']} chapters", leave=False):
            crawl_chapter_content(book["link"], ch["index"], book["id"])
    # Update lại index.json với chapterCount mới nhất
    upload_to_r2(r2_index_key, books)

def sync_books():
    # Crawl 2 page đầu, mỗi truyện 1 chương đầu tiên cho test nhẹ (thay đổi tùy ý)
    sync_all_books(crawl_full_chapters=True)
