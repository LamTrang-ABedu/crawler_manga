import threading
from flask import Flask, jsonify, request
from utils import mimihentai, tranh18, metruyencv

app = Flask(__name__)

# --- TỰ ĐỘNG CRAWL KHI APP START ---
def crawl_metruyencv_full_batch(batch_size=3, max_page=769, delay=90):
    # Chia từng batch nhỏ, chạy nối tiếp nhau
    for start_page in range(1, max_page + 1, batch_size):
        end_page = min(start_page + batch_size - 1, max_page)
        print(f"[Metruyencv] Crawling from page {start_page} to {end_page}")
        metruyencv.crawl_batch(start_page, end_page)
        time.sleep(delay)  # nghỉ sau mỗi batch

def auto_crawl_on_start():
    threading.Thread(
        target=crawl_metruyencv_full_batch, args=(3, 769, 90), daemon=True
    ).start()
    # Có thể chạy thêm các nguồn khác song song như cũ nếu muốn

auto_crawl_on_start()

@app.route("/api/crawl", methods=["POST"])
def crawl_all():
    source = request.args.get("source")
    if source == "mimihentai":
        threading.Thread(target=mimihentai.sync_all_manga, daemon=True).start()
        return jsonify({"status": "mimihentai crawl started"})
    elif source == "tranh18":
        threading.Thread(target=tranh18.sync_all_comics, daemon=True).start()
        return jsonify({"status": "tranh18 crawl started"})
    else:
        return jsonify({"error": "Unknown source"}), 400

@app.route("/api/crawl-latest", methods=["POST"])
def crawl_latest():
    source = request.args.get("source")
    slug = request.args.get("slug")
    if source == "mimihentai":
        threading.Thread(target=mimihentai.sync_latest_manga, args=(slug,), daemon=True).start()
        return jsonify({"status": f"mimihentai crawl for {slug} started"})
    elif source == "tranh18":
        threading.Thread(target=tranh18.sync_latest_comic, args=(slug,), daemon=True).start()
        return jsonify({"status": f"tranh18 crawl for {slug} started"})
    else:
        return jsonify({"error": "Unknown source"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
