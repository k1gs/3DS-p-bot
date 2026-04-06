import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
from config import settings
import re

logger = logging.getLogger(__name__)

class RutrackerScraper:
    def __init__(self):
        self.session = httpx.AsyncClient(
            base_url=settings.RUTRACKER_MIRROR,
            follow_redirects=True,
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        self.logged_in = False

    async def login(self) -> bool:
        if self.logged_in:
            return True
            
        data = {
            "login_username": settings.RUTRACKER_USERNAME,
            "login_password": settings.RUTRACKER_PASSWORD,
            "login": "Вход"
        }
        
        try:
            response = await self.session.post("/forum/login.php", data=data)
            if "login_username" not in response.text:
                self.logged_in = True
                logger.info("Successfully logged in to Rutracker")
                return True
            else:
                logger.error("Failed to login to Rutracker. Check credentials.")
                return False
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False

    async def search_3ds_games(self, query: str = "") -> List[Dict]:
        if not await self.login():
            return []

        if query:
            params = {
                "f": settings.FORUM_ID,
                "nm": query
            }
            url = "/forum/tracker.php"
        else:
            params = {
                "f": settings.FORUM_ID
            }
            url = "/forum/viewforum.php"
        
        try:
            response = await self.session.get(url, params=params)
            response.encoding = 'windows-1251'
            return self._parse_topics(response.text)
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []

    def _parse_topics(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "html.parser")
        topics = []
        
        rows = soup.select("tr.tCenter")
        
        for row in rows:
            title_tag = row.select_one("a.tLink") or row.select_one("a.tt-text")
            if not title_tag:
                continue
                
            title = title_tag.text.strip()
            href = title_tag.get("href", "")
            topic_id_match = re.search(r"t=(\d+)", href)
            if not topic_id_match:
                continue
            topic_id = int(topic_id_match.group(1))
            
            size_td = row.select_one("td.tor-size")
            if size_td:
                size = size_td.get_text(separator=" ").replace("\xa0", " ").strip()
            else:
                size = "Unknown"
            
            seeds_b = row.select_one("b.seedmed")
            seeds_td = row.select_one("td.seedmed")
            
            if seeds_b:
                seeds_text = seeds_b.text.strip()
            elif seeds_td:
                seeds_text = seeds_td.text.strip()
            else:
                seeds_text = "0"
            
            seeds = int(seeds_text) if seeds_text.isdigit() else 0
            
            topics.append({
                "source": "rutracker",
                "id": str(topic_id),
                "title": title,
                "size": size,
                "seeds": seeds,
                "url": f"{settings.RUTRACKER_MIRROR}/forum/viewtopic.php?t={topic_id}"
            })
            
        return topics

    async def download_torrent(self, topic_id: str) -> tuple[Optional[bytes], str]:
        if not await self.login():
            return None, ""
            
        try:
            resp = await self.session.get(f"/forum/dl.php?t={topic_id}")
            if resp.status_code == 200 and 'application/x-bittorrent' in resp.headers.get("content-type", ""):
                cd = resp.headers.get("content-disposition", "")
                filename = f"rutracker_{topic_id}.torrent"
                if "filename=" in cd:
                    filename = cd.split("filename=")[-1].strip('"')
                return resp.content, filename
        except Exception as e:
            logger.error(f"Error downloading torrent {topic_id}: {e}")
        return None, ""
        
    async def get_magnet(self, topic_id: str) -> Optional[str]:
        if not await self.login():
            return None
            
        try:
            resp = await self.session.get(f"/forum/viewtopic.php?t={topic_id}")
            resp.encoding = 'windows-1251'
            soup = BeautifulSoup(resp.text, "html.parser")
            magnet_a = soup.select_one("a.magnet-link-14") or soup.select_one("a.magnet-link") or soup.select_one("a[href^='magnet:']")
            if magnet_a:
                return magnet_a.get("href")
        except Exception as e:
            logger.error(f"Error getting magnet for {topic_id}: {e}")
        return None

    async def get_cover_and_desc(self, topic_id: str) -> tuple[Optional[str], str]:
        if not await self.login():
            return None, ""
        try:
            resp = await self.session.get(f"/forum/viewtopic.php?t={topic_id}")
            resp.encoding = 'windows-1251'
            soup = BeautifulSoup(resp.text, "html.parser")
            post_body = soup.select_one("div.post_body")
            
            cover_url = None
            desc = ""
            if post_body:
                img_var = post_body.select_one("var.postImg")
                if img_var and img_var.get("title"):
                    cover_url = img_var.get("title")
                else:
                    img_tag = post_body.select_one("img.postImg")
                    if img_tag and img_tag.get("src"):
                        cover_url = img_tag.get("src")
                        
                desc_span = None
                for span in post_body.find_all("span", class_="post-b"):
                    if "Описание" in span.text:
                        desc_span = span
                        break
                        
                if desc_span:
                    curr = desc_span.next_sibling
                    extracted = []
                    while curr:
                        if curr.name == "span" and "post-b" in curr.get("class", []):
                            break
                        if curr.name == "div" and "sp-wrap" in curr.get("class", []):
                            break
                        if hasattr(curr, "text"):
                            extracted.append(curr.text)
                        elif isinstance(curr, str):
                            extracted.append(str(curr))
                        curr = curr.next_sibling
                    desc = "".join(extracted).strip()

                if not desc:
                    text_parts = []
                    for el in post_body.children:
                        if el.name == "div" and "sp-wrap" in el.get("class", []): continue
                        if hasattr(el, "text"): text_parts.append(el.text.strip())
                        elif isinstance(el, str): text_parts.append(str(el).strip())
                    
                    full_text = "\n".join(t for t in text_parts if t)
                    lines = full_text.split('\n')
                    desc_lines = []
                    for line in lines:
                        if "Проверен" in line or "Релиз от" in line: continue
                        desc_lines.append(line)
                    desc = "\n".join(desc_lines)[:4000] + ("..." if len("\n".join(desc_lines)) > 4000 else "")
                    
            return cover_url, desc
        except Exception as e:
            logger.error(f"Error getting cover/desc for {topic_id}: {e}")
        return None, ""

    async def close(self):
        await self.session.aclose()

class RomsfunScraper:
    def __init__(self):
        self.session = httpx.AsyncClient(
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0"}
        )

    async def search_3ds_games(self, query: str) -> List[Dict]:
        try:
            resp = await self.session.get(f"https://romsfun.com/?s={query}")
            soup = BeautifulSoup(resp.text, "html.parser")
            
            topics = []
            for a_tag in soup.find_all("a", href=True):
                url = a_tag["href"]
                if "/roms/3ds/" in url:
                    title = a_tag.text.strip()
                    if title and title not in [t['title'] for t in topics]:
                        topics.append({
                            "source": "romsfun",
                            "id": url,
                            "title": title,
                            "size": "Неизвестно", 
                            "seeds": 0,
                            "url": url
                        })
            return topics
        except Exception as e:
            logger.error(f"Error in Romsfun search: {e}")
            return []
            
    async def close(self):
        await self.session.aclose()
