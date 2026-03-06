import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────────────────
#  db/queries.py  –  All database operations
# ─────────────────────────────────────────────────────────────
from datetime import datetime, date, timedelta
from bson import ObjectId
import random
from db.models import users, tasks, contributions, admins, fsm_states, notif_log, counters

# ─────────────────────────────────────────────────────────────
#  PERMISSIONS MASTER LIST
# ─────────────────────────────────────────────────────────────
ALL_PERMISSIONS = [
    # Admin management
    "appoint_admins",           # appoint / remove regular admins
    "edit_admin_permissions",   # edit regular admin permission sets
    "view_admins",              # view all admin profiles
    # Task management
    "create_tasks",
    "edit_tasks",
    "pause_resume_tasks",
    "end_tasks_early",
    "extend_tasks",
    "delete_tasks",
    "add_media",
    # Announcements
    "send_announcements",
    "edit_templates",
    "dm_blast",
    # User management
    "view_contributors",
    "remove_contributions",
    "ban_users",
    "view_users",
    # Stats
    "view_per_task_stats",
    "export_stats",
    # Settings
    "toggle_leaderboard",
    "manage_ramadan",
]

# Default permissions for each role
SUPER_ADMIN_DEFAULTS = {
    "appoint_admins": True,
    "edit_admin_permissions": False,   # owner grants manually
    "view_admins": True,
    "create_tasks": True,
    "edit_tasks": True,
    "pause_resume_tasks": True,
    "end_tasks_early": True,
    "extend_tasks": True,
    "delete_tasks": True,
    "add_media": True,
    "send_announcements": True,
    "edit_templates": False,
    "dm_blast": False,
    "view_contributors": True,
    "remove_contributions": False,
    "ban_users": True,
    "view_users": True,
    "view_per_task_stats": True,
    "export_stats": False,
    "toggle_leaderboard": True,
    "manage_ramadan": True,
}

ADMIN_DEFAULTS = {p: False for p in ALL_PERMISSIONS}
ADMIN_DEFAULTS.update({
    "create_tasks": True,
    "edit_tasks": True,
    "pause_resume_tasks": True,
    "view_users": True,
    "view_per_task_stats": True,
    "send_announcements": True,
    "add_media": True,
})

# ─────────────────────────────────────────────────────────────
#  USERS
# ─────────────────────────────────────────────────────────────
async def get_user(user_id: int):
    return await users().find_one({"user_id": user_id})

async def user_exists(user_id: int) -> bool:
    return await users().count_documents({"user_id": user_id}) > 0

async def create_user(user_id: int, username: str, display_name: str,
                      visibility: str, notifications: dict,
                      reminder_time: str | None):
    anon_name = f"Servant_{random.randint(1000, 9999)}"
    doc = {
        "user_id": user_id,
        "username": username or "",
        "display_name": display_name,
        "visibility": visibility,
        "anon_name": anon_name,
        "notify_tasks": notifications.get("tasks", True),
        "notify_endings": notifications.get("endings", True),
        "notify_leaderboard": notifications.get("leaderboard", False),
        "notify_reminders": notifications.get("reminders", False),
        "reminder_time": reminder_time,
        "streak": 0,
        "last_participated": None,
        "lifetime_count": 0,
        "registered_at": datetime.utcnow(),
        "is_banned": False,
    }
    await users().insert_one(doc)
    return doc

async def update_user(user_id: int, **fields):
    await users().update_one({"user_id": user_id}, {"$set": fields})

async def get_all_users(skip_banned=True):
    q = {"is_banned": False} if skip_banned else {}
    return await users().find(q).to_list(None)

async def get_users_with_notif(notif_type: str):
    """notif_type: 'tasks'|'endings'|'leaderboard'|'reminders'"""
    return await users().find({
        f"notify_{notif_type}": True,
        "is_banned": False
    }).to_list(None)

async def ban_user(user_id: int):
    await users().update_one({"user_id": user_id}, {"$set": {"is_banned": True}})

async def unban_user(user_id: int):
    await users().update_one({"user_id": user_id}, {"$set": {"is_banned": False}})

async def update_streak(user_id: int):
    user = await get_user(user_id)
    if not user:
        return
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last = user.get("last_participated")
    if last == today:
        return
    streak = user.get("streak", 0)
    new_streak = streak + 1 if last == yesterday else 1
    await users().update_one({"user_id": user_id}, {"$set": {
        "last_participated": today,
        "streak": new_streak,
    }})

async def get_user_count() -> int:
    return await users().count_documents({"is_banned": False})

# ─────────────────────────────────────────────────────────────
#  ADMINS
# ─────────────────────────────────────────────────────────────
async def get_admin(user_id: int):
    return await admins().find_one({"user_id": user_id})

async def is_admin(user_id: int) -> bool:
    return await admins().count_documents({"user_id": user_id}) > 0

async def create_admin(user_id: int, role: str, permissions: dict, appointed_by: int):
    doc = {
        "user_id": user_id,
        "role": role,
        "permissions": permissions,
        "appointed_by": appointed_by,
        "appointed_at": datetime.utcnow(),
    }
    await admins().replace_one({"user_id": user_id}, doc, upsert=True)

async def update_admin_permissions(user_id: int, permissions: dict):
    await admins().update_one({"user_id": user_id}, {"$set": {"permissions": permissions}})

async def update_admin_role(user_id: int, role: str):
    await admins().update_one({"user_id": user_id}, {"$set": {"role": role}})

async def remove_admin(user_id: int):
    await admins().delete_one({"user_id": user_id})

async def get_all_admins():
    return await admins().find({}).to_list(None)

async def has_permission(user_id: int, perm: str, owner_id: int) -> bool:
    if user_id == owner_id:
        return True
    adm = await get_admin(user_id)
    if not adm:
        return False
    return adm.get("permissions", {}).get(perm, False)

# ─────────────────────────────────────────────────────────────
#  TASKS
# ─────────────────────────────────────────────────────────────
async def get_next_sequence(name: str) -> int:
    res = await counters().find_one_and_update(
        {"name": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return res["seq"]

async def create_task(data: dict) -> int:
    data["created_at"] = datetime.utcnow()
    data.setdefault("total_count", 0)
    data.setdefault("participant_count", 0)
    data.setdefault("milestone_announced", [])
    data.setdefault("media", [])
    
    # Use sequential ID
    task_id = await get_next_sequence("task_id")
    data["_id"] = task_id
    
    await tasks().insert_one(data)
    return task_id

async def get_task(task_id) -> dict | None:
    if isinstance(task_id, str) and not task_id.isdigit():
        try:
            task_id = ObjectId(task_id)
        except:
            pass
    elif isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    return await tasks().find_one({"_id": task_id})

async def get_active_tasks():
    return await tasks().find({"status": "active"}).to_list(None)

async def get_tasks_by_status(status: str):
    return await tasks().find({"status": status}).sort("created_at", -1).to_list(None)

async def update_task(task_id, **fields):
    if isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    elif isinstance(task_id, str):
        task_id = ObjectId(task_id)
    await tasks().update_one({"_id": task_id}, {"$set": fields})

async def add_milestone_announced(task_id, milestone):
    if isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    elif isinstance(task_id, str):
        task_id = ObjectId(task_id)
    await tasks().update_one({"_id": task_id}, {"$push": {"milestone_announced": milestone}})

async def increment_task_count(task_id, amount: int):
    if isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    elif isinstance(task_id, str):
        task_id = ObjectId(task_id)
    await tasks().update_one({"_id": task_id}, {"$inc": {"total_count": amount}})

async def increment_participant_count(task_id):
    if isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    elif isinstance(task_id, str):
        task_id = ObjectId(task_id)
    await tasks().update_one({"_id": task_id}, {"$inc": {"participant_count": 1}})

async def end_task(task_id):
    await update_task(task_id, status="ended")

# ─────────────────────────────────────────────────────────────
#  CONTRIBUTIONS
# ─────────────────────────────────────────────────────────────
async def add_contribution(task_id, user_id: int, count: int):
    if isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    elif isinstance(task_id, str):
        task_id = ObjectId(task_id)
    
    task = await get_task(task_id)
    today = date.today()
    doc = {
        "task_id": task_id,
        "user_id": user_id,
        "count": count,
        "submitted_at": datetime.utcnow(),
        "session_date": today.isoformat(),
        "year": today.year,
        "month": today.month,
        "week": today.isocalendar()[1],
        "category": task.get("category"),
        "subcategory": task.get("subcategory"),
        "sub_subcategory": task.get("sub_subcategory"),
        "dhikr_text": task.get("dhikr_text")
    }
    await contributions().insert_one(doc)
    await increment_task_count(task_id, count)
    await users().update_one({"user_id": user_id}, {"$inc": {"lifetime_count": count}})
    await update_streak(user_id)

async def get_user_task_total(task_id, user_id: int) -> int:
    if isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    elif isinstance(task_id, str):
        task_id = ObjectId(task_id)
    pipeline = [
        {"$match": {"task_id": task_id, "user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}},
    ]
    result = await contributions().aggregate(pipeline).to_list(None)
    return result[0]["total"] if result else 0

async def get_user_daily_total(task_id, user_id: int) -> int:
    if isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    elif isinstance(task_id, str):
        task_id = ObjectId(task_id)
    today = date.today().isoformat()
    pipeline = [
        {"$match": {"task_id": task_id, "user_id": user_id, "session_date": today}},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}},
    ]
    result = await contributions().aggregate(pipeline).to_list(None)
    return result[0]["total"] if result else 0

async def get_task_leaderboard(task_id, limit=10):
    if isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    elif isinstance(task_id, str):
        task_id = ObjectId(task_id)
    pipeline = [
        {"$match": {"task_id": task_id}},
        {"$group": {"_id": "$user_id", "total": {"$sum": "$count"}}},
        {"$sort": {"total": -1}},
        {"$limit": limit},
    ]
    return await contributions().aggregate(pipeline).to_list(None)

async def get_user_rank(task_id, user_id: int) -> int:
    if isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    elif isinstance(task_id, str):
        task_id = ObjectId(task_id)
    user_total = await get_user_task_total(task_id, user_id)
    higher = await contributions().aggregate([
        {"$match": {"task_id": task_id}},
        {"$group": {"_id": "$user_id", "total": {"$sum": "$count"}}},
        {"$match": {"total": {"$gt": user_total}}},
        {"$count": "n"},
    ]).to_list(None)
    return (higher[0]["n"] if higher else 0) + 1

async def get_global_leaderboard(period: str = "all", limit: int = 10):
    match_q = {}
    today = date.today()
    if period == "today":
        match_q["session_date"] = today.isoformat()
    elif period == "week":
        match_q["year"] = today.year
        match_q["week"] = today.isocalendar()[1]
    elif period == "month":
        match_q["year"] = today.year
        match_q["month"] = today.month
    elif period == "year":
        match_q["year"] = today.year

    pipeline = [
        {"$match": match_q},
        {"$group": {"_id": "$user_id", "total": {"$sum": "$count"}}},
        {"$sort": {"total": -1}},
        {"$limit": limit}
    ]
    return await contributions().aggregate(pipeline).to_list(None)

async def get_hierarchical_stats(user_id: int | None = None, period: str = "all"):
    """
    Returns stats grouped by Year -> Month -> Dhikr Type.
    If user_id is None, returns global stats.
    """
    match_q = {}
    if user_id:
        match_q["user_id"] = user_id
    
    today = date.today()
    if period == "today":
        match_q["session_date"] = today.isoformat()
    elif period == "week":
        match_q["year"] = today.year
        match_q["week"] = today.isocalendar()[1]
    elif period == "month":
        match_q["year"] = today.year
        match_q["month"] = today.month
    elif period == "year":
        match_q["year"] = today.year

    pipeline = [
        {"$match": match_q},
        {
            "$group": {
                "_id": {
                    "year": {"$ifNull": ["$year", {"$year": "$submitted_at"}]},
                    "month": {"$ifNull": ["$month", {"$month": "$submitted_at"}]},
                    "dhikr_text": "$dhikr_text"
                },
                "total": {"$sum": "$count"}
            }
        },
        {"$sort": {"_id.year": -1, "_id.month": -1, "total": -1}}
    ]
    return await contributions().aggregate(pipeline).to_list(None)

async def get_owner_concise_stats():
    """Returns total users, total contributions, and active tasks count."""
    total_users = await users().count_documents({})
    total_active_tasks = await tasks().count_documents({"status": "active"})
    
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$count"}}}]
    res = await contributions().aggregate(pipeline).to_list(None)
    total_dhikr = res[0]["total"] if res else 0
    
    return {
        "total_users": total_users,
        "active_tasks": total_active_tasks,
        "total_dhikr": total_dhikr
    }

async def reset_database():
    """Wipes all data from the database. OWNER ONLY."""
    await users().delete_many({})
    await tasks().delete_many({})
    await contributions().delete_many({})
    await admins().delete_many({})
    await states().delete_many({})
    await notifications().delete_many({})

async def remove_user_contributions(task_id, user_id: int):
    if isinstance(task_id, str):
        task_id = ObjectId(task_id)
    result = await contributions().find({"task_id": task_id, "user_id": user_id}).to_list(None)
    total = sum(r["count"] for r in result)
    await contributions().delete_many({"task_id": task_id, "user_id": user_id})
    if total:
        await tasks().update_one({"_id": task_id}, {"$inc": {"total_count": -total}})
        await users().update_one({"user_id": user_id}, {"$inc": {"lifetime_count": -total}})

async def get_task_per_contributor(task_id):
    if isinstance(task_id, str):
        task_id = ObjectId(task_id)
    pipeline = [
        {"$match": {"task_id": task_id}},
        {"$group": {"_id": "$user_id", "total": {"$sum": "$count"}}},
        {"$sort": {"total": -1}},
    ]
    return await contributions().aggregate(pipeline).to_list(None)

async def get_daily_breakdown(task_id):
    """Returns per-day totals for a task."""
    if isinstance(task_id, str):
        task_id = ObjectId(task_id)
    pipeline = [
        {"$match": {"task_id": task_id}},
        {"$group": {"_id": "$session_date", "total": {"$sum": "$count"}}},
        {"$sort": {"_id": 1}},
    ]
    return await contributions().aggregate(pipeline).to_list(None)

# ─────────────────────────────────────────────────────────────
#  GRAND / PERIOD STATS
# ─────────────────────────────────────────────────────────────
async def get_grand_total() -> int:
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$count"}}}]
    r = await contributions().aggregate(pipeline).to_list(None)
    return r[0]["total"] if r else 0

async def get_period_total(start_date: str, end_date: str | None = None) -> int:
    q: dict = {"session_date": {"$gte": start_date}}
    if end_date:
        q["session_date"]["$lte"] = end_date
    pipeline = [
        {"$match": q},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}},
    ]
    r = await contributions().aggregate(pipeline).to_list(None)
    return r[0]["total"] if r else 0

async def get_monthly_total() -> int:
    start = date.today().replace(day=1).isoformat()
    return await get_period_total(start)

async def get_yearly_total() -> int:
    start = date.today().replace(month=1, day=1).isoformat()
    return await get_period_total(start)

async def get_daily_total() -> int:
    today = date.today().isoformat()
    return await get_period_total(today, today)

async def get_user_period_total(user_id: int, start_date: str, end_date: str | None = None) -> int:
    q: dict = {"user_id": user_id, "session_date": {"$gte": start_date}}
    if end_date:
        q["session_date"]["$lte"] = end_date
    pipeline = [
        {"$match": q},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}},
    ]
    r = await contributions().aggregate(pipeline).to_list(None)
    return r[0]["total"] if r else 0

async def get_user_category_stats(user_id: int, start_date=None, end_date=None):
    match = {"user_id": user_id}
    if start_date or end_date:
        match["session_date"] = {}
        if start_date: match["session_date"]["$gte"] = start_date
        if end_date:   match["session_date"]["$lte"] = end_date
    
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {
                "category": "$category",
                "subcategory": "$subcategory",
                "sub_subcategory": "$sub_subcategory",
                "dhikr_text": "$dhikr_text"
            },
            "total": {"$sum": "$count"}
        }},
        {"$sort": {"total": -1}}
    ]
    return await contributions().aggregate(pipeline).to_list(None)

async def get_global_category_stats(start_date=None, end_date=None):
    match = {}
    if start_date or end_date:
        match["session_date"] = {}
        if start_date: match["session_date"]["$gte"] = start_date
        if end_date:   match["session_date"]["$lte"] = end_date
    
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {
                "category": "$category",
                "subcategory": "$subcategory",
                "sub_subcategory": "$sub_subcategory",
                "dhikr_text": "$dhikr_text"
            },
            "total": {"$sum": "$count"}
        }},
        {"$sort": {"total": -1}}
    ]
    return await contributions().aggregate(pipeline).to_list(None)

# ─────────────────────────────────────────────────────────────
#  FSM STATE
# ─────────────────────────────────────────────────────────────
async def get_state(user_id: int) -> dict | None:
    return await fsm_states().find_one({"user_id": user_id})

async def set_state(user_id: int, state: str, data: dict = None):
    await fsm_states().replace_one(
        {"user_id": user_id},
        {"user_id": user_id, "state": state, "data": data or {}, "updated": datetime.utcnow()},
        upsert=True,
    )

async def clear_state(user_id: int):
    await fsm_states().delete_one({"user_id": user_id})

async def update_state_data(user_id: int, **kwargs):
    doc = await get_state(user_id)
    if doc:
        data = doc.get("data", {})
        data.update(kwargs)
        await fsm_states().update_one(
            {"user_id": user_id},
            {"$set": {"data": data, "updated": datetime.utcnow()}},
        )

# ─────────────────────────────────────────────────────────────
#  NOTIFICATION LOG
# ─────────────────────────────────────────────────────────────
async def log_notification(ntype: str, task_id=None, sent_to=None):
    await notif_log().insert_one({
        "type": ntype,
        "task_id": task_id,
        "sent_at": datetime.utcnow(),
        "sent_to": sent_to or "group",
    })
