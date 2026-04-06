import asyncio
import pprint
from agent import RutrackerScraper

async def test():
    r = RutrackerScraper()
    cover, desc = await r.get_cover_and_desc('5954917')
    print("COVER:", cover)
    print("DESC LEN:", len(desc))
    print("DESC:\n", desc[:200])
    await r.close()

asyncio.run(test())
