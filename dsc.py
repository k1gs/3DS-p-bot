import asyncio
import httpx
from bs4 import BeautifulSoup
from config import settings

async def test_description():
    topic_id = "5679802"
    
    session = httpx.AsyncClient(base_url=settings.RUTRACKER_MIRROR, follow_redirects=True)
    data = {"login_username": settings.RUTRACKER_USERNAME, "login_password": settings.RUTRACKER_PASSWORD, "login": "Вход"}
    await session.post("/forum/login.php", data=data)
    
    resp = await session.get(f"/forum/viewtopic.php?t={topic_id}")
    resp.encoding = 'windows-1251'
    soup = BeautifulSoup(resp.text, "html.parser")
    post_body = soup.select_one("div.post_body")
    
    if post_body:
        desc_text = ""
        for tag in post_body.find_all("span", class_="post-b"):
            if "Описание" in tag.text:
                curr = tag.next_sibling
                while curr:
                    if curr.name == "span" and "post-b" in curr.get("class", []):
                        break # Stop at next bold tag
                    if curr.name == "br" or curr.name == "hr":
                         desc_text += "\n"
                    elif curr.name == "div" and "sp-wrap" in curr.get("class", []):
                         break # Stop at spoilres
                    elif curr.name:
                         desc_text += curr.text
                    elif isinstance(curr, str):
                         desc_text += str(curr)
                    curr = curr.next_sibling
                break
                
        if not desc_text.strip():
            text = post_body.get_text(separator="\n").strip()
            lines = [l.strip() for l in text.split("\n") if l.strip() and "Проверен" not in l]
            desc_text = "\n".join(lines[:10])

        print("Extracted Description:")
        print(desc_text.strip()[:500])

    await session.aclose()

asyncio.run(test_description())
