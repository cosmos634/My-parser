"""Telegram public-lead monitor for Lead Finder.

Reads only public messages from discoverable sources. It does not join groups,
enumerate members, extract phone numbers, or contact authors automatically.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
from telethon import TelegramClient, errors
from telethon.tl.functions.contacts import SearchRequest

from lead_finder.database import add_lead, connect, get_stats, init_db
from lead_finder.scoring import score_lead

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("telegram-monitor")

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE = os.getenv("TELEGRAM_PHONE", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("LEAD_FINDER_DB", "data/leads.db")
SESSION = os.getenv("TELETHON_SESSION", "data/lead_finder")
KEYWORDS = [x.strip() for x in os.getenv(
    "SEARCH_KEYWORDS",
    "ищу разработчика;нужен сайт;нужен телеграм бот;заказать сайт;нужен парсер"
).split(";") if x.strip()]
SCAN_INTERVAL = max(15, int(os.getenv("SCAN_INTERVAL_MINUTES", "60")))
MESSAGES_PER_SOURCE = max(10, min(200, int(os.getenv("MAX_MESSAGES_PER_SOURCE", "80"))))

client = TelegramClient(SESSION, API_ID, API_HASH, flood_sleep_threshold=60)
router = Router()


def is_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id == ADMIN_ID)


def save_source(username: str, title: str, source_type: str) -> bool:
    with connect(DB_PATH) as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO sources(name, type, url, enabled) VALUES (?, ?, ?, 1)",
            (username, source_type, f"https://t.me/{username}"),
        )
        return cur.rowcount > 0


async def discover_sources() -> int:
    """Find public groups/channels by phrases; never auto-join them."""
    found = 0
    for keyword in KEYWORDS:
        try:
            result = await client(SearchRequest(q=keyword, limit=10))
            for entity in result.chats:
                username = getattr(entity, "username", None)
                if not username:
                    continue
                kind = "group" if getattr(entity, "megagroup", False) else "channel"
                if save_source(username, getattr(entity, "title", username), kind):
                    found += 1
        except errors.FloodWaitError as exc:
            log.warning("Telegram requested a wait of %s seconds", exc.seconds)
            await asyncio.sleep(exc.seconds)
        except Exception:
            log.exception("Public-source search failed for keyword: %s", keyword)
    return found


def message_link(source_username: str | None, message_id: int) -> str | None:
    return f"https://t.me/{source_username}/{message_id}" if source_username else None


async def scan_sources(bot: Bot | None = None) -> list[dict]:
    with connect(DB_PATH) as conn:
        sources = conn.execute(
            "SELECT name, type, url FROM sources WHERE enabled = 1 ORDER BY name"
        ).fetchall()

    new_leads = []
    for source in sources:
        username = source["name"].lstrip("@")
        try:
            entity = await client.get_entity(username)
            source_username = getattr(entity, "username", None)
            async for message in client.iter_messages(entity, limit=MESSAGES_PER_SOURCE, wait_time=1):
                body = (message.message or "").strip()
                if len(body) < 20:
                    continue
                sender = await message.get_sender()
                author_username = getattr(sender, "username", None) if sender else None
                public_contact = f"@{author_username}" if author_username else None
                published = message.date.astimezone(timezone.utc).isoformat() if message.date else None
                analysis = score_lead(body[:120], body, None, public_contact, published)

                # Keep only relevant buyer requests, not freelancer advertisements.
                if analysis["intent"] not in {"buyer_request", "developer_search"}:
                    continue
                if analysis["category"] == "other" or analysis["score"] < 40:
                    continue

                url = message_link(source_username, message.id)
                data = {
                    "title": body[:120],
                    "description": body,
                    "source": "telegram",
                    "source_name": getattr(entity, "title", username),
                    "url": url,
                    "contact": public_contact,
                    "published_at": published,
                    **analysis,
                }
                created, lead_id = add_lead(data, DB_PATH)
                if created:
                    new_leads.append({**data, "id": lead_id})

            with connect(DB_PATH) as conn:
                conn.execute(
                    "UPDATE sources SET last_checked = ? WHERE name = ?",
                    (datetime.now(timezone.utc).isoformat(), username),
                )
        except errors.FloodWaitError as exc:
            log.warning("Flood wait while scanning %s: %s seconds", username, exc.seconds)
            await asyncio.sleep(exc.seconds)
        except (ValueError, errors.UsernameNotOccupiedError):
            log.warning("Source is no longer available: %s", username)
        except Exception:
            log.exception("Failed to scan source: %s", username)

    if bot and new_leads:
        for lead in new_leads[:20]:
            await send_lead(bot, lead)
    return new_leads


async def send_lead(bot: Bot, lead: dict) -> None:
    contact = lead.get("contact") or "Ochiq username ko'rsatilmagan"
    link = lead.get("url") or "Havola mavjud emas"
    text = (
        f"🎯 Yangi potensial mijoz\n\n"
        f"📌 {lead['title']}\n\n"
        f"🧩 Xizmat: {lead['category']}\n"
        f"📊 Ball: {lead['score']}/100 ({lead['status']})\n"
        f"👤 Ochiq kontakt: {contact}\n"
        f"👥 Manba: {lead['source_name']}\n"
        f"🕒 Sana: {lead.get('published_at') or 'Noma’lum'}\n"
        f"🔗 Xabar: {link}"
    )
    await bot.send_message(ADMIN_ID, text, disable_web_page_preview=True)


@router.message(Command("start", "help"))
async def help_command(message: Message):
    if not is_admin(message):
        return
    await message.answer(
        "Lead Finder boshqaruvi\n"
        "/discover — kalit so'zlar bo'yicha ochiq manbalarni qidirish\n"
        "/sources — kuzatilayotgan manbalar\n"
        "/scan — hozir skanerlash\n"
        "/status — statistika\n"
        "/addsource username — ochiq manbani qo'shish"
    )


@router.message(Command("discover"))
async def discover_command(message: Message):
    if not is_admin(message):
        return
    await message.answer("🔎 Ochiq Telegram manbalari qidirilmoqda...")
    count = await discover_sources()
    await message.answer(f"Topilgan yangi manbalar: {count}. Ular avtomatik ravishda guruhlarga qo'shilmaydi.")


@router.message(Command("addsource"))
async def add_source_command(message: Message):
    if not is_admin(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Foydalanish: /addsource public_username")
        return
    username = parts[1].strip().lstrip("@")
    try:
        entity = await client.get_entity(username)
        if not getattr(entity, "username", None):
            await message.answer("Bu manba ochiq username'ga ega emas.")
            return
        kind = "group" if getattr(entity, "megagroup", False) else "channel"
        created = save_source(entity.username, getattr(entity, "title", username), kind)
        await message.answer("Manba qo'shildi." if created else "Bu manba allaqachon ro'yxatda.")
    except Exception as exc:
        await message.answer(f"Manbani tekshirib bo'lmadi: {type(exc).__name__}")


@router.message(Command("sources"))
async def sources_command(message: Message):
    if not is_admin(message):
        return
    with connect(DB_PATH) as conn:
        rows = conn.execute("SELECT name, type, enabled FROM sources ORDER BY name").fetchall()
    if not rows:
        await message.answer("Hozircha manba yo'q. /discover buyrug'ini yubor.")
        return
    await message.answer("\n".join(
        f"• @{row['name']} — {row['type']} — {'ON' if row['enabled'] else 'OFF'}"
        for row in rows[:100]
    ))


@router.message(Command("scan"))
async def scan_command(message: Message):
    if not is_admin(message):
        return
    await message.answer("⏳ Manbalar tekshirilmoqda...")
    leads = await scan_sources()
    await message.answer(f"Tekshiruv tugadi. Yangi mos e'lonlar: {len(leads)}")


@router.message(Command("status"))
async def status_command(message: Message):
    if not is_admin(message):
        return
    stats = get_stats(DB_PATH)
    with connect(DB_PATH) as conn:
        sources = conn.execute("SELECT COUNT(*) FROM sources WHERE enabled = 1").fetchone()[0]
    await message.answer(
        f"📊 Lead Finder\n"
        f"Jami leadlar: {stats.get('total', 0)}\n"
        f"HOT: {stats.get('hot', 0)} | WARM: {stats.get('warm', 0)}\n"
        f"Faol manbalar: {sources}"
    )


async def hourly_worker(bot: Bot):
    while True:
        try:
            added = await discover_sources()
            log.info("Discovered %s new sources", added)
            leads = await scan_sources(bot)
            log.info("Saved %s new leads", len(leads))
        except Exception:
            log.exception("Hourly monitoring cycle failed")
        await asyncio.sleep(SCAN_INTERVAL * 60)


async def run_bot():
    if not all([API_ID, API_HASH, BOT_TOKEN, ADMIN_ID]):
        raise RuntimeError("Set TELEGRAM_API_ID, TELEGRAM_API_HASH, BOT_TOKEN and ADMIN_ID in .env")
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Telethon session is not authorized. Run: python telegram_monitor.py login")
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    worker = asyncio.create_task(hourly_worker(bot))
    try:
        await dp.start_polling(bot)
    finally:
        worker.cancel()
        await bot.session.close()
        await client.disconnect()


async def login():
    if not API_ID or not API_HASH or not PHONE:
        raise RuntimeError("Set TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_PHONE in .env")
    await client.start(phone=PHONE)
    print("Telethon session authorized. Keep the .session file private and out of Git.")
    await client.disconnect()


if __name__ == "__main__":
    import sys
    init_db(DB_PATH)
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        asyncio.run(login())
    else:
        asyncio.run(run_bot())
