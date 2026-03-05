import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────────────────
#  scheduler/jobs.py  –  APScheduler jobs
# ─────────────────────────────────────────────────────────────
from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import queries as q
from utils.announcements import announce_task_ended, send_group, dm_users

scheduler = AsyncIOScheduler()
_client = None


def init_scheduler(client):
    global _client
    _client = client
    scheduler.add_job(check_expired_tasks,   "interval", minutes=1,  id="expire_tasks")
    scheduler.add_job(send_daily_reminders,  "interval", minutes=1,  id="reminders")
    scheduler.add_job(reset_recurring_tasks, "cron",     hour=0, minute=5, id="recurring")
    scheduler.start()


async def check_expired_tasks():
    """End any task whose ends_at has passed."""
    now = datetime.utcnow()
    active = await q.get_active_tasks()
    for task in active:
        ends = task.get("ends_at")
        if ends and ends <= now:
            await q.end_task(task["_id"])
            await announce_task_ended(_client, task)


async def send_daily_reminders():
    """DM members whose reminder_time matches current UTC minute."""
    now = datetime.utcnow()
    hhmm = now.strftime("%H:%M")
    active_tasks = await q.get_active_tasks()
    if not active_tasks:
        return
    users = await q.get_users_with_notif("reminders")
    targets = [u["user_id"] for u in users if u.get("reminder_time") == hhmm]
    if targets:
        task_titles = ", ".join(t["title"] for t in active_tasks[:3])
        text = (
            f"⏰ *Your Daily Dhikr Reminder*\n\n"
            f"Active tasks: _{task_titles}_\n\n"
            f"Open the bot to contribute: /start 🌙"
        )
        await dm_users(_client, targets, text)


async def reset_recurring_tasks():
    """At midnight, close current cycle of recurring tasks and restart them."""
    from datetime import timedelta
    all_tasks = await q.get_tasks_by_status("active")
    for task in all_tasks:
        if task.get("type") == "recurring":
            interval = task.get("recurring_interval", "daily")
            if interval == "daily":
                await announce_task_ended(_client, task)
                # Reset count for new cycle, keep task active
                await q.update_task(task["_id"],
                    total_count=0,
                    milestone_announced=[],
                    starts_at=datetime.utcnow(),
                    ends_at=datetime.utcnow() + timedelta(hours=24),
                )
            # Weekly tasks handled by checking day of week
            elif interval == "weekly" and datetime.utcnow().weekday() == 4:  # Friday
                await announce_task_ended(_client, task)
                await q.update_task(task["_id"],
                    total_count=0,
                    milestone_announced=[],
                    starts_at=datetime.utcnow(),
                    ends_at=datetime.utcnow() + timedelta(days=7),
                )
