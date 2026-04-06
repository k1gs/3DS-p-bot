import asyncio
import logging
import html
import hashlib
from aiogram import Bot, Dispatcher, types, F
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from agent import RutrackerScraper, RomsfunScraper
from config import settings
from db import init_db, add_user, is_topic_new, add_topic, get_all_users
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
rt_scraper = RutrackerScraper()
rf_scraper = RomsfunScraper()

@dp.message(Command("start"))
async def start_handler(message: Message):
    add_user(message.from_user.id)
    
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("dl_"):
        topic_id = args[1].split("_")[1]
        await message.answer("Файл запрошен через Inline. Начинаю загрузку...")
        content, filename = await rt_scraper.download_torrent(topic_id)
        if content:
            torrent_file = BufferedInputFile(content, filename=filename)
            await message.answer_document(torrent_file)
        else:
            await message.answer("Не удалось скачать торрент-файл.")
        return

    await message.answer("Это бот для поиска игр для консоли нинтендо 3дс . \n\n"
                         "Достаточно написать название игры(например, <b>Pokemon</b>) или используйте команду /search &lt;название&gt;.\n\n"
                         "Также есть возможность инлайн комманд. Пример команды: <code>@ndsgames_bot mario</code> в поле ввода текста.", 
                         parse_mode="HTML")

@dp.message(Command("search"))
async def search_handler(message: Message):
    query = message.text.split(maxsplit=1)
    if len(query) < 2:
        await message.answer("Использование: /search &lt;название&gt;\nИли просто напишите название игры.", parse_mode="HTML")
        return
    await perform_search(message, query[1])



async def perform_search(message: Message, query: str):
    wait_msg = await message.answer(f"Ищу <b>{html.escape(query)}</b>...", parse_mode="HTML")
    
    rt_res, rf_res = await asyncio.gather(
        rt_scraper.search_3ds_games(query), 
        rf_scraper.search_3ds_games(query)
    )
    
    results = (rt_res + rf_res)[:10]
    
    if not results:
        await wait_msg.edit_text("Ошибка, либо игра не найдена :(")
        return
        
    text = ""
    
    for idx, item in enumerate(results, start=1):
        if item['source'] == 'rutracker':
            text += (f"{idx}. {item['title']} (Rutracker)\n"
                     f"Скачать: /download{item['id']} /cover{item['id']}\n")
        else:
            text += (f"{idx}. {item['title']} (RomsFun)\n"
                     f"Ссылка: {item['url']}\n")
        
    await wait_msg.edit_text(text, parse_mode=None, disable_web_page_preview=True)

@dp.message(F.text.startswith('/download'))
async def dl_handler(message: Message):
    text = message.text.split('@')[0]
    topic_id = text.replace('/download', '').strip()
    if not topic_id.isdigit(): return
    
    wait_msg = await message.answer("Загрузка...")
    content, filename = await rt_scraper.download_torrent(topic_id)
    if content:
        torrent_file = BufferedInputFile(content, filename=filename)
        await message.answer_document(torrent_file)
        await wait_msg.delete()
    else:
        await wait_msg.edit_text("Не удалось скачать торрент-файл.")

@dp.message(F.text.startswith('/cover'))
async def cover_handler(message: Message):
    text = message.text.split('@')[0]
    topic_id = text.replace('/cover', '').strip()
    if not topic_id.isdigit(): return
    
    wait_msg = await message.answer("Загрузка...")
    cover_url, desc = await rt_scraper.get_cover_and_desc(topic_id)
    
    caption = desc if desc else ""
    is_long_desc = len(caption) > 1000

    if cover_url:
        try:
            from aiogram.types import BufferedInputFile
            import httpx
            async with httpx.AsyncClient() as client:
                img_resp = await client.get(cover_url, timeout=10.0)
                if img_resp.status_code == 200:
                    photo = BufferedInputFile(img_resp.content, filename="cover.png")
                    await wait_msg.delete()
                    if is_long_desc:
                        await message.answer_photo(photo)
                        await message.answer(caption)
                    else:
                        await message.answer_photo(photo, caption=caption)
                else:
                    raise Exception("Status not 200")
        except Exception as e:
            logger.error(f"Could not download photo locally: {e}")
            try:
                await wait_msg.delete()
                if is_long_desc:
                    await message.answer_photo(cover_url)
                    await message.answer(caption)
                else:
                    await message.answer_photo(cover_url, caption=caption)
            except Exception:
                await message.answer(f"[Обложка недоступна]\n{cover_url}\n\n{caption}")
    else:
        if caption:
            await wait_msg.edit_text(caption)
        else:
            await wait_msg.edit_text("Обложка не найдена.")

@dp.inline_query()
async def inline_search(inline_query: InlineQuery):
    query = inline_query.query or ""
    if len(query) < 2:
        return
        
    rt_res, rf_res = await asyncio.gather(
        rt_scraper.search_3ds_games(query), 
        rf_scraper.search_3ds_games(query)
    )
    
    results = rt_res[:5] + rf_res[:5]
    
    inline_results = []
    
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    for item in results:
        safe_title = html.escape(item['title'])
        builder = InlineKeyboardBuilder()
        
        if item['source'] == 'rutracker':
            text = (f"<a href='{item['url']}'>{safe_title}</a> (Rutracker)\n"
                    f"Размер: {item['size']}")
            builder.button(text="Скачать .torrent", url=f"https://t.me/{bot_username}?start=dl_{item['id']}")
        else:
            text = f"<a href='{item['url']}'>{safe_title}</a> (RomsFun)"
            builder.button(text="Сайт RomsFun", url=item['url'])
                
        text_content = InputTextMessageContent(message_text=text, parse_mode="HTML", disable_web_page_preview=True)
        
        result_id = hashlib.md5(f"{item['url']}".encode()).hexdigest()
        
        inline_results.append(
            InlineQueryResultArticle(
                id=result_id,
                title=item['title'],
                description=f"Источник: {item['source'].title()} | Размер: {item['size']}",
                input_message_content=text_content,
                reply_markup=builder.as_markup()
            )
        )
        
    await inline_query.answer(inline_results, cache_time=60)

@dp.message(F.text.startswith('/magnet'))
async def magnet_handler(message: Message):
    text = message.text.split('@')[0]
    topic_id = text.replace('/magnet', '').strip()
    if not topic_id.isdigit(): return
    
    wait_msg = await message.answer("Загрузка...")
    magnet_link = await rt_scraper.get_magnet(topic_id)
    if magnet_link:
        await wait_msg.edit_text(f"Magnet-ссылка:\n\n`{magnet_link}`", parse_mode="Markdown")
    else:
        await wait_msg.edit_text("Не удалось найти magnet-ссылку на странице раздачи.")

async def check_new_games():
    while True:
        try:
            logger.info("Checking for new 3DS games...")
            results = await rt_scraper.search_3ds_games()
            
            for item in results:
                if is_topic_new(item['id']):
                    add_topic(item['id'], item['title'], item['size'], item['seeds'])
                    
                    users = get_all_users()
                    notification = (f"Новая раздача! (Rutracker)\n"
                                   f"{html.escape(item['title'])}\n"
                                   f"Размер: {item['size']}\n"
                                   f"Скачать: /download{item['id']} /cover{item['id']}")
                                   
                    for user_id in users:
                        try:
                            await bot.send_message(user_id, notification, parse_mode=None)
                        except Exception as e:
                            logger.error(f"Failed to notify user {user_id}: {e}")
                            
        except Exception as e:
            logger.error(f"Error in background task: {e}")
            
        await asyncio.sleep(settings.CHECK_INTERVAL * 60)

@dp.message()
async def plain_text_handler(message: Message):
    if message.text and not message.text.startswith('/'):
        await perform_search(message, message.text)

async def main():
    init_db()
    asyncio.create_task(check_new_games())
    
    try:
        await dp.start_polling(bot)
    finally:
        await rt_scraper.close()
        await rf_scraper.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
        sys.exit(0)
