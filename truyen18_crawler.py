import requests
from bs4 import BeautifulSoup

class Truyen18Crawler:
    BASE_URL = "https://truyen18.com"

    def get_comics(self, page=1):
        url = f"{self.BASE_URL}/?page={page}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")

        comics = []
        for item in soup.select("div.story-item"):
            a = item.select_one("a")
            title = a["title"]
            link = a["href"]
            thumbnail = item.select_one("img")["src"]
            comic_id = link.rstrip("/").split("/")[-1]
            comics.append({
                "id": comic_id,
                "title": title,
                "thumbnail": thumbnail,
                "url": link
            })
        return {"page": page, "comics": comics}

    def get_chapters(self, comic_id):
        url = f"{self.BASE_URL}/truyen/{comic_id}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")

        title = soup.select_one("h1").text.strip() if soup.select_one("h1") else comic_id
        chapters = []
        for li in soup.select(".list-chapter li"):
            a = li.select_one("a")
            chapter_title = a.text.strip()
            chapter_url = a["href"]
            chapter_id = chapter_url.rstrip("/").split("/")[-1]
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

        title = soup.select_one("h1").text.strip() if soup.select_one("h1") else chapter_id
        images = [img["src"] for img in soup.select(".chapter-content img")]
        return {"comic_id": comic_id, "chapter_id": chapter_id, "title": title, "images": images}