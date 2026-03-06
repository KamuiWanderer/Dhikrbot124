import sys, os
# Ensure the directory of main.py is in the path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

# DNS Resolver fix for Termux/Android
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4']

import asyncio
import logging
from aiohttp import web
from telethon import TelegramClient, functions, types
from config import API_ID, API_HASH, BOT_TOKEN, HEALTH_PORT
from db.models import create_indexes
from scheduler.jobs import init_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("dhikr-bot")

client = TelegramClient("dhikr_bot_session", API_ID, API_HASH)

def setup_handlers():
    from handlers import registration, member, admin
    registration.register(client)
    member.register(client)
    admin.register(client)
    log.info("All handlers registered.")

async def set_bot_commands():
    """Register commands that appear in the Telegram menu."""
    await client(functions.bots.SetBotCommandsRequest(
        scope=types.BotCommandScopeDefault(),
        lang_code="",
        commands=[
            types.BotCommand(command="start",  description="Open the main menu"),
            types.BotCommand(command="stats",  description="View community & personal stats"),
            types.BotCommand(command="admin",  description="Open admin panel (admins only)"),
        ]
    ))
    log.info("Bot commands registered.")

async def health_handler(request):
    return web.Response(text="OK", status=200)

async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HEALTH_PORT)
    await site.start()
    log.info(f"Health server on port {HEALTH_PORT}")

async def main():
    log.info("Starting Dhikr Bot...")
    await client.start(bot_token=BOT_TOKEN)
    await create_indexes()
    setup_handlers()
    await set_bot_commands()
    await start_health_server()
    init_scheduler(client)
    me = await client.get_me()
    log.info(f"Bot running as @{me.username}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
