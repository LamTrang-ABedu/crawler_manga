import os
import json
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

from .common import slugify, upload_to_r2, read_from_r2

R2_PREFIX = "Ebook/metruyencv"

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
        print(f"[SKIP] Chapters {book_id} đã có trên R2.")
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

def clean_chapter_html(chapter_soup):
    """Loại bỏ tag canvas, các div rác trong content."""
    # Xóa tất cả <canvas>
    for canvas in chapter_soup.find_all('canvas'):
        canvas.decompose()
    # Xóa các <div> với id middle-content-*
    for div in chapter_soup.find_all('div'):
        if div.get('id', '').startswith('middle-content'):
            div.decompose()
    # Giữ lại text, <br>, <b>, <i>, <strong>, <em>
    allowed_tags = ['br', 'b', 'i', 'strong', 'em', 'p', 'u']
    for tag in chapter_soup.find_all(True):
        if tag.name not in allowed_tags:
            tag.unwrap()
    # Trả về HTML gọn
    return str(chapter_soup)

def crawl_chapter_content(book_link, chapter_index, book_id):
    r2_chap_key = f"Ebook/metruyencv/{book_id}/chuong-{chapter_index}.json"
    # Nếu đã có trên R2 thì bỏ qua
    if read_from_r2(r2_chap_key):
        print(f"[SKIP] Chapter {book_id} - {chapter_index} đã có trên R2.")
        return None
    url = f"{book_link}/chuong-{chapter_index}"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error loading chapter {chapter_index} of {book_id}: {e}")
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    content = soup.select_one("#chapter-content")
    title = soup.select_one("h1")
    content_html = ""
    content_text = ""
    if content:
        content_html = clean_chapter_html(content)
        # Lấy text, thay <br> thành \n cho dễ đọc
        content_text = content_html.replace('<br>', '\n').replace('<br/>', '\n')
        # Xóa tag còn lại nếu có
        content_text = BeautifulSoup(content_text, "html.parser").get_text('\n', strip=True)
    title_text = title.get_text(strip=True) if title else f"Chương {chapter_index}"
    chapter_data = {
        "title": title_text,
        "content_html": content_html,
        "content_text": content_text
    }
    upload_to_r2(r2_chap_key, chapter_data)
    return chapter_data

# === Hàm chính: crawl full/update truyện ===
def sync_all_books(max_page=769, limit=20, chapters_per_book=1, crawl_full_chapters=False):
    books = crawl_books(limit=limit, max_page=max_page)
    print(f"[INFO] Found {len(books)} books.")
    # Update index sau khi biết số chương thực tế
    r2_index_key = f"{R2_PREFIX}/index.json"
    for i, book in enumerate(tqdm(books, desc="Crawl chapters")):
        chapters = crawl_chapters(book["id"])
        print(f"[INFO] Found {len(chapters)} chapters for {book['name']}")
        books[i]['chapterCount'] = len(chapters)
        # Crawl từng chương
        chaps = chapters if crawl_full_chapters else chapters[:chapters_per_book]
        for ch in tqdm(chaps, desc=f"{book['id']} chapters", leave=False):
            crawl_chapter_content(book["link"], ch["index"], book["id"])
    # Update lại index.json với chapterCount mới nhất
    upload_to_r2(r2_index_key, books)

def sync_books():
    # Crawl 2 page đầu, mỗi truyện 1 chương đầu tiên cho test nhẹ (thay đổi tùy ý)
    sync_all_books(max_page=2, limit=20, chapters_per_book=1, crawl_full_chapters=False)
