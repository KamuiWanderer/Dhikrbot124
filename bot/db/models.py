import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────────────────
#  db/models.py  –  MongoDB collection accessors + schema docs
# ─────────────────────────────────────────────────────────────
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

_client: AsyncIOMotorClient = None

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client

def get_db():
    return get_client()[DB_NAME]

# ── Shorthand collection accessors ───────────────────────────
def users():          return get_db()["users"]
def tasks():          return get_db()["tasks"]
def contributions():  return get_db()["contributions"]
def notif_log():      return get_db()["notifications_log"]
def admins():         return get_db()["admins"]
def fsm_states():     return get_db()["fsm_states"]
def stats_cache():    return get_db()["stats_cache"]
def counters():       return get_db()["counters"]

# ─────────────────────────────────────────────────────────────
#  Index creation  (called once on startup)
# ─────────────────────────────────────────────────────────────
async def create_indexes():
    await users().create_index("user_id", unique=True)
    await tasks().create_index("status")
    await tasks().create_index("ends_at")
    await contributions().create_index([("task_id", 1), ("user_id", 1)])
    await contributions().create_index("submitted_at")
    await contributions().create_index("session_date")
    await admins().create_index("user_id", unique=True)
    await fsm_states().create_index("user_id", unique=True)
    await notif_log().create_index("sent_at")
    await counters().create_index("name", unique=True)
