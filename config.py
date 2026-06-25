import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
IRBIS_LOGIN = os.getenv("IRBIS_LOGIN", "")
IRBIS_PASSWORD = os.getenv("IRBIS_PASSWORD", "")
IRBIS_API_TOKEN = os.getenv("IRBIS_API_TOKEN", "")

REQUEST_DELAY_MIN = 2.0
REQUEST_DELAY_MAX = 5.0
REQUEST_TIMEOUT = 30
CACHE_TTL = 86400
REPORTS_DIR = "data/reports"
CACHE_DIR = "data/cache"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
