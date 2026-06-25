import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from config import TELEGRAM_BOT_TOKEN, BASE_DIR
from utils.logger import logger
from bot import main as run_bot


def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не задан! Запишите токен в .env")
        sys.exit(1)

    os.makedirs(os.path.join(BASE_DIR, "data", "cache"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "data", "reports"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

    logger.info("Агент Налоговое досье запущен")
    run_bot()


if __name__ == "__main__":
    main()
