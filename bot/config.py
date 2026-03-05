import os
from dotenv import load_dotenv

# Try loading from current directory first, then parent directory
if not load_dotenv():
    # If not found, try one level up (common in project structures)
    parent_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(parent_env)

# Telegram API Credentials
API_ID = int(os.getenv("TELEGRAM_API_ID") or os.getenv("API_ID") or "0")
API_HASH = os.getenv("TELEGRAM_API_HASH") or os.getenv("API_HASH") or ""
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""

# Bot Configuration
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
GROUP_ID = int(os.getenv("GROUP_ID", "0"))  # Community group ID
HEALTH_PORT = int(os.getenv("HEALTH_PORT") or os.getenv("PORT") or "8080")

# Database Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "dhikr_bot")

# Logic Configuration
SUBMISSION_COOLDOWN_SECONDS = 3
ABSOLUTE_MILESTONES = [1000, 5000, 10000, 50000, 100000, 500000, 1000000]
MILESTONE_PERCENTAGES = [25, 50, 75, 100]
