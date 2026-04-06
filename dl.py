import asyncio
import httpx
from bs4 import BeautifulSoup
from config import settings

async def test_download():
    session = httpx.AsyncClient(base_url=settings.RUTRACKER_MIRROR, follow_redirects=True)
    data = {"login_username": settings.RUTRACKER_USERNAME, "login_password": settings.RUTRACKER_PASSWORD, "login": "Вход"}
    await session.post("/forum/login.php", data=data)
    
    # known topic id for Animal Crossing Happy Home Designer from earlier run
    topic_id = "5091722" # Note: using a random recent one or let's use search again
    
    params = {"f": "774", "nm": "Animal crossing"}
    resp = await session.get("/forum/tracker.php", params=params)
    resp.encoding = 'windows-1251'
    soup = BeautifulSoup(resp.text, "html.parser")
    first_row = soup.select_one("tr.tCenter")
    
    topic_id = first_row.select_one("a.tLink")["href"].split("t=")[1]
    print("Found topic:", topic_id)
    
    dl_resp = await session.get(f"/forum/dl.php?t={topic_id}")
    print("DL status:", dl_resp.status_code)
    print("DL headers:", dict(dl_resp.headers))
    print("Content len:", len(dl_resp.content))
    if b'html' in dl_resp.content[:100].lower():
         print("It's an HTML page!")
         print(dl_resp.content[:500].decode('windows-1251', 'ignore'))
         
    # MAGNET
    t_resp = await session.get(f"/forum/viewtopic.php?t={topic_id}")
    t_soup = BeautifulSoup(t_resp.text, "html.parser")
    mag = t_soup.select_one("a.magnet-link-14") or t_soup.select_one("a.magnet-link") or t_soup.select_one("a[href^='magnet:']")
    print("Magnet:", mag["href"] if mag else "Not found")

    await session.aclose()

asyncio.run(test_download())
