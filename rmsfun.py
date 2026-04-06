import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_romsfun_search():
    query = "Pokemon"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
        resp = await client.get(f"https://romsfun.com/?s={query}")
        print("Status Code:", resp.status_code)
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        articles = soup.select("article") or soup.select(".post-item") or soup.select("div.item") 
        print(f"Found {len(articles)} potential articles/items")
        
        for idx, article in enumerate(articles[:5]):
            title_tag = article.select_one("h2") or article.select_one(".title") or article.select_one("h3")
            if title_tag and title_tag.text:
                title = title_tag.text.strip()
                link = article.select_one("a")
                url = link.get("href") if link else "No URL"
                print(f"{idx+1}. {title} - {url}")

asyncio.run(test_romsfun_search())
