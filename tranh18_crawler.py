import httpx
from bs4 import BeautifulSoup

class Tranh18Crawler:
    BASE_URL = "https://tranh18.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://google.com"
    }

    def fetch_html(self, url):
        with httpx.Client(headers=self.HEADERS, timeout=30) as client:
            print(f"Fetching URL: {url}")
            res = client.get(url)
            print(f"Response status: {res.status_code}")
            if res.status_code != 200:
                print(f"Error fetching {url}: {res.status_code}")
                raise httpx.HTTPStatusError(f"Error fetching {url}: {res.status_code}", request=res.request, response=res)
            res.raise_for_status()
            return BeautifulSoup(res.text, "html.parser")

    def get_comics(self, page=1):
        soup = self.fetch_html(f"{self.BASE_URL}/comics?page={page}")
        comics = []
        for li in soup.select("ul.list > li"):
            a = li.select_one("a")
            img = li.select_one("img")
            if not a or not img:
                continue
            title = img.get("alt", "").strip()
            link = a["href"]
            cover = img["src"]
            comic_id = link.rstrip("/").split("/")[-1]
            comics.append({
                "id": comic_id,
                "title": title,
                "url": link,
                "cover": cover
            })
        return {"page": page, "comics": comics}

    def get_chapters(self, comic_id):
        soup = self.fetch_html(f"{self.BASE_URL}/comic/{comic_id}")
        title = soup.select_one("h1").text.strip() if soup.select_one("h1") else comic_id
        chapters = []
        for opt in soup.select("select#select-chapter option"):
            chapter_id = opt["value"]
            chapter_title = opt.text.strip()
            if chapter_id:
                chapters.append({
                    "id": chapter_id,
                    "title": chapter_title
                })
        return {"comic_id": comic_id, "title": title, "chapters": chapters}

    def get_chapter_images(self, comic_id, chapter_id):
        soup = self.fetch_html(f"{self.BASE_URL}/comic/{comic_id}/chapter/{chapter_id}")
        title = soup.select_one("h1").text.strip() if soup.select_one("h1") else f"Chapter {chapter_id}"
        images = []
        for img in soup.select("div.comicpage img"):
            src = img.get("data-original") or img.get("src")
            if src:
                images.append(src)
        return {
            "comic_id": comic_id,
            "chapter_id": chapter_id,
            "title": title,
            "images": images
        }