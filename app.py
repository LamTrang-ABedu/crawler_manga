import threading
from flask import Flask, jsonify, request
from utils import mimihentai, tranh18, metruyencv
import time

app = Flask(__name__)

def auto_crawl_on_start():
    threading.Thread(
        target=metruyencv.crawl_batch, daemon=True
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
