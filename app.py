import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
import uvicorn
import logging
import time  # Để thêm độ trễ nhỏ

# Cấu hình logging cơ bản
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Tranh18 Comic Scraper API",
    description="Microservice để lấy danh sách truyện từ tranh18.com",
    version="1.0.0"
)

# URL mục tiêu
TARGET_URL = "https://m.tranh18.com/comics?page=0" # Hoặc một trang cụ thể chứa danh sách, ví dụ: trang mới cập nhật

# Headers để giả lập trình duyệt
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def scrape_comics_from_tranh18(url: str):
    """
    Hàm thực hiện việc cào dữ liệu danh sách truyện từ URL được cung cấp.
    """
    comics = []
    try:
        # Thêm độ trễ nhỏ để tránh làm quá tải server
        time.sleep(0.5) 
        
        logger.info(f"Bắt đầu lấy dữ liệu từ: {url}")
        response = requests.get(url, headers=HEADERS, timeout=15) # Thêm timeout
        response.raise_for_status()  # Ném lỗi nếu request không thành công (vd: 404, 500)
        
        # Sử dụng encoding utf-8 nếu trang web trả về đúng
        response.encoding = 'utf-8' 
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'lxml') # Sử dụng lxml parser cho tốc độ

        # --- PHẦN QUAN TRỌNG CẦN CẬP NHẬT ---
        # Tìm các phần tử chứa thông tin truyện. 
        # Bạn cần KIỂM TRA TRỰC TIẾP trang web bằng Inspect Element (F12) 
        # để xác định đúng các thẻ và class/id.
        # Ví dụ giả định: Mỗi truyện nằm trong thẻ 'div' với class 'item'
        
        # Ví dụ 1: Nếu trang có cấu trúc các item trong một list (phổ biến)
        # comic_items = soup.find_all('div', class_='item') # Thay 'div' và 'item' bằng selector đúng
        
        # Ví dụ 2: Nếu là các bài post (cập nhật mới)
        comic_items = soup.find_all('article', class_='post') # CẦN THAY THẾ SELECTOR NÀY

        if not comic_items:
            logger.warning(f"Không tìm thấy phần tử truyện nào với selector đã định nghĩa tại {url}.")
            return []

        logger.info(f"Tìm thấy {len(comic_items)} truyện.")

        for item in comic_items:
            # Tìm tiêu đề và link bên trong mỗi item
            # Ví dụ giả định: Tiêu đề nằm trong thẻ 'h3' > 'a'
            title_tag = item.find('h3', class_='entry-title').find('a') # CẦN THAY THẾ SELECTOR NÀY
            
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag.get('href')
                
                # Đảm bảo link là URL đầy đủ
                if link and not link.startswith('http'):
                     # Có thể cần thêm logic để nối đúng base URL nếu link là tương đối
                     # Ví dụ: from urllib.parse import urljoin; link = urljoin(TARGET_URL, link)
                     pass # Bỏ qua nếu link không hợp lệ hoặc cần xử lý thêm

                if title and link:
                    comics.append({"title": title, "link": link})
                else:
                     logger.warning(f"Bỏ qua item vì thiếu tiêu đề hoặc link: {item.prettify()}")
            else:
                 logger.warning(f"Không tìm thấy thẻ tiêu đề trong item: {item.prettify()}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi khi thực hiện request đến {url}: {e}")
        raise HTTPException(status_code=503, detail=f"Không thể kết nối đến trang nguồn: {e}")
    except Exception as e:
        logger.error(f"Lỗi không xác định khi xử lý dữ liệu: {e}")
        # Ghi lại chi tiết lỗi nếu cần để debug
        # logger.exception("Chi tiết lỗi:") 
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý dữ liệu: {e}")

    logger.info(f"Hoàn thành lấy dữ liệu, {len(comics)} truyện được thêm vào danh sách.")
    return comics

@app.get("/comics", summary="Lấy danh sách truyện mới cập nhật")
async def get_comics_list():
    """
    Endpoint để lấy danh sách truyện từ trang chủ hoặc trang mới cập nhật của tranh18.com.
    """
    try:
        # Bạn có thể thay TARGET_URL bằng trang cụ thể nếu muốn
        # Ví dụ: https://tranh18.com/page/1/
        comics_data = scrape_comics_from_tranh18(TARGET_URL) 
        if not comics_data:
             # Trả về 404 nếu không tìm thấy truyện (hoặc 200 với list rỗng tùy logic)
             raise HTTPException(status_code=404, detail="Không tìm thấy truyện nào trên trang mục tiêu.")
        return {"count": len(comics_data), "comics": comics_data}
    except HTTPException as http_err:
        # Ném lại lỗi HTTP đã được xử lý trong hàm scrape
        raise http_err
    except Exception as e:
         # Bắt các lỗi khác chưa được xử lý
        logger.error(f"Lỗi không mong muốn tại endpoint /comics: {e}")
        raise HTTPException(status_code=500, detail="Lỗi máy chủ nội bộ.")


# Chạy server (chỉ khi chạy file này trực tiếp)
if __name__ == "__main__":
    # Chạy uvicorn server trên localhost, port 8000
    # host="0.0.0.0" để có thể truy cập từ máy khác trong mạng
    uvicorn.run(app, host="0.0.0.0", port=8000) 

    # Để chạy: Mở terminal, di chuyển đến thư mục chứa file này và gõ:
    # python ten_file_cua_ban.py
    # Sau đó truy cập vào http://localhost:8000/docs để xem API và thử nghiệm
    # Hoặc truy cập trực tiếp http://localhost:8000/comics
