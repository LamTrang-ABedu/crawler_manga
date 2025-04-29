import requests
from bs4 import BeautifulSoup

class TruyenQQCrawler:
    BASE_URL = "https://nettruyen3q.net"

    def get_comics(self, page=1):
        url = f"{self.BASE_URL}/truyen-moi-cap-nhat/trang-{page}.html"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        comics = []
        for item in soup.select("div.item > a"):
            link = item["href"]
            comic_id = link.rstrip("/").split("/")[-1].replace(".html", "")
            thumbnail = item.select_one("img")["src"]
            title = item.select_one("img").get("alt", "").strip()
            comics.append({
                "id": comic_id,
                "title": title,
                "thumbnail": thumbnail,
                "url": link
            })
        return {"page": page, "comics": comics}

    def get_chapters(self, comic_id):
        url = f"{self.BASE_URL}/truyen-tranh/{comic_id}.html"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        title = soup.select_one(".title-detail").text.strip()
        chapters = []
        for a in soup.select(".works-chapter-list a"):
            chapter_title = a.text.strip()
            chapter_url = a["href"]
            chapter_id = chapter_url.rstrip("/").split("/")[-1].replace(".html", "")
            chapters.append({
                "id": chapter_id,
                "title": chapter_title,
                "url": chapter_url
            })
        return {"comic_id": comic_id, "title": title, "chapters": chapters}

    def get_chapter_images(self, comic_id, chapter_id):
        url = f"{self.BASE_URL}/truyen-tranh/{comic_id}/chap-{chapter_id}.html"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        images = [img["src"] for img in soup.select(".page-chapter img")]
        return {
            "comic_id": comic_id,
            "chapter_id": chapter_id,
            "images": images
        }