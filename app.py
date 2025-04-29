from flask import Flask, jsonify, request
from tranh18_crawler import Tranh18Crawler

app = Flask(__name__)
crawler = Tranh18Crawler()

@app.route('/api/comics', methods=['GET'])
def get_comics():
    page = int(request.args.get('page', 1))
    return jsonify(crawler.get_comics(page))

@app.route('/api/comics/<comic_id>', methods=['GET'])
def get_chapters(comic_id):
    return jsonify(crawler.get_chapters(comic_id))

@app.route('/api/comics/<comic_id>/chapters/<chapter_id>', methods=['GET'])
def get_chapter(comic_id, chapter_id):
    return jsonify(crawler.get_chapter_images(comic_id, chapter_id))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)