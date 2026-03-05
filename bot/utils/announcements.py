import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────────────────
#  utils/announcements.py  –  Group + DM broadcast helpers
# ─────────────────────────────────────────────────────────────
import asyncio
import random
from telethon import functions, types
from config import GROUP_ID
from db import queries as q
from utils.messages import (
    msg_task_announcement, msg_task_ended, msg_milestone,
    msg_emergency_task
)


async def send_group(client, text: str, media=None, buttons=None):
    """Send a message to the community group."""
    try:
        if media:
            await client.send_file(GROUP_ID, media, caption=text, parse_mode="html", buttons=buttons)
        else:
            await client.send_message(GROUP_ID, text, parse_mode="html", buttons=buttons)
    except ValueError:
        # Try to resolve entity if not in cache
        try:
            entity = await client.get_entity(GROUP_ID)
            if media:
                await client.send_file(entity, media, caption=text, parse_mode="html", buttons=buttons)
            else:
                await client.send_message(entity, text, parse_mode="html", buttons=buttons)
        except Exception:
            pass
    except Exception:
        pass


async def dm_users(client, user_ids: list[int], text: str, protect_content: bool = False, buttons=None):
    """Send a protected DM to a list of user IDs. Returns (sent, blocked, failed)."""
    sent, blocked, failed = 0, 0, 0
    for uid in user_ids:
        try:
            await client.send_message(
                uid,
                text,
                parse_mode="html",
                noforwards=protect_content,
                buttons=buttons
            )
            sent += 1
            await asyncio.sleep(0.05)   # stay within Telegram rate limits
        except Exception as e:
            # Common errors: User blocked bot, user deactivated account, etc.
            if "UserIsBlocked" in str(e) or "PeerIdInvalid" in str(e):
                blocked += 1
            else:
                failed += 1
    return sent, blocked, failed


async def announce_task_published(client, task: dict):
    """Announce new task to group + DM opted-in members."""
    from keyboards.builder import btn, row, markup
    text = msg_task_announcement(task)
    first_media = None
    if task.get("media"):
        m = task["media"][0]
        if m.get("type") in ("image", "video", "audio"):
            first_media = m.get("file_id")
    
    me = await client.get_me()
    buttons = markup(row(btn("📿 Join Dhikr", f"https://t.me/{me.username}?start=task_{task['_id']}", "url")))
    await send_group(client, text, first_media, buttons=buttons)
    users = await q.get_users_with_notif("tasks")
    await dm_users(client, [u["user_id"] for u in users], text, buttons=buttons)
    await q.log_notification("task_start", task["_id"])


async def announce_task_ended(client, task: dict):
    text = msg_task_ended(task, task.get("total_count", 0))
    await send_group(client, text)
    users = await q.get_users_with_notif("endings")
    await dm_users(client, [u["user_id"] for u in users], text)
    await q.log_notification("task_end", task["_id"])


async def announce_milestone(client, task: dict, milestone):
    from keyboards.builder import btn, row, markup
    text = msg_milestone(task, milestone, task["total_count"])
    me = await client.get_me()
    buttons = markup(row(btn("📿 Join Dhikr", f"https://t.me/{me.username}?start=task_{task['_id']}", "url")))
    await send_group(client, text, buttons=buttons)
    await q.log_notification("milestone", task["_id"])


async def announce_emergency(client, task: dict):
    """Emergency bypasses all notification filters — DM everyone."""
    from keyboards.builder import btn, row, markup
    text = msg_emergency_task(task)
    me = await client.get_me()
    buttons = markup(row(btn("🚨 Join Now", f"https://t.me/{me.username}?start=task_{task['_id']}", "url")))
    await send_group(client, text, buttons=buttons)
    all_users = await q.get_all_users()
    await dm_users(client, [u["user_id"] for u in all_users], text, buttons=buttons)
    await q.log_notification("emergency", task["_id"])


async def announce_paused(client, task: dict, paused: bool):
    symbol = "⏸" if paused else "▶️"
    state = "paused" if paused else "resumed"
    text = f"{symbol} <b>Task {state}:</b> {h(task['title'])}"
    await send_group(client, text)


async def send_manual_reminder(client, task: dict, custom_text: str):
    from keyboards.builder import btn, row, markup
    me = await client.get_me()
    buttons = markup(row(btn("📿 Join Dhikr", f"https://t.me/{me.username}?start=task_{task['_id']}", "url")))
    await send_group(client, custom_text, buttons=buttons)
    users = await q.get_users_with_notif("tasks")
    await dm_users(client, [u["user_id"] for u in users], custom_text, buttons=buttons)
    await q.log_notification("manual_reminder", task["_id"])


async def send_stats_dm(client, user_id: int, text: str):
    """Send protected (non-forwardable) stats DM."""
    await dm_users(client, [user_id], text, protect_content=True)
