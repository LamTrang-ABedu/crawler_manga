import requests
from bs4 import BeautifulSoup

class Tranh18Crawler:
    BASE_URL = "https://tranh18.com"

    def get_comics(self, page=1):
        url = f"{self.BASE_URL}/page/{page}/"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")

        comics = []
        for item in soup.select(".c-image-hover"):
            a = item.select_one("a")
            img = item.select_one("img")
            if not a or not img:
                continue
            title = img.get("alt", "").strip()
            link = a["href"]
            comic_id = link.rstrip("/").split("/")[-1]
            thumbnail = img["src"]
            comics.append({
                "id": comic_id,
                "title": title,
                "url": link,
                "thumbnail": thumbnail
            })
        return {"page": page, "comics": comics}

    def get_chapters(self, comic_id):
        url = f"{self.BASE_URL}/truyen/{comic_id}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")

        title = soup.select_one("h1").text.strip()
        chapters = []
        for a in soup.select(".wp-manga-chapter > a"):
            chapter_url = a["href"]
            chapter_id = chapter_url.rstrip("/").split("/")[-1]
            chapter_title = a.text.strip()
            chapters.append({
                "id": chapter_id,
                "title": chapter_title,
                "url": chapter_url
            })
        return {"comic_id": comic_id, "title": title, "chapters": chapters}

    def get_chapter_images(self, comic_id, chapter_id):
        url = f"{self.BASE_URL}/truyen/{comic_id}/{chapter_id}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")

        images = [img["src"] for img in soup.select(".reading-content img")]
        return {
            "comic_id": comic_id,
            "chapter_id": chapter_id,
            "images": images
        }