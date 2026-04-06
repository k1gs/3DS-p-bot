import asyncio
import httpx
from bs4 import BeautifulSoup
from config import settings

async def test_search():
    session = httpx.AsyncClient(base_url=settings.RUTRACKER_MIRROR)
    data = {"login_username": settings.RUTRACKER_USERNAME, "login_password": settings.RUTRACKER_PASSWORD, "login": "Вход"}
    auth_resp = await session.post("/forum/login.php", data=data)
    
    params = {"f": "774", "nm": "Animal crossing"}
    resp = await session.get("/forum/tracker.php", params=params)
    resp.encoding = 'windows-1251'
    
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("tr.tCenter")
    
    print(f"Found {len(rows)} matching rows in tracker.php")
    for row in rows:
        a_tag = row.select_one("a.tLink") or row.select_one("a.tt-text")
        if not a_tag: continue
        title = a_tag.text.strip()
        
        size_td = row.select_one("td.tor-size a") or row.select_one("td.tor-size")
        size = size_td.text.strip() if size_td else "Unknown"
        
        seeds_td = row.select_one("td.seedmed") or row.select("td")[7] if len(row.select("td")) > 7 else None
        
        seeds_b = row.select_one("b.seedmed")
        if seeds_b:
             seeds = seeds_b.text.strip()
        elif seeds_td:
             seeds = seeds_td.text.strip()
        else:
             seeds = "0"
             
        print(f"- {title} | Size: {size} | Seeds: {seeds}")

    await session.aclose()

asyncio.run(test_search())
