import asyncio
import re
from utils.logger import logger
from agents._playwright_helper import find_chrome


def _sync_fetch(inn: str) -> dict:
    chrome = find_chrome()
    if not chrome:
        return {"source": "Федресурс/fedresurs.ru", "error": "Chromium не найден"}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=chrome,
                                         args=["--no-sandbox"])
            page = browser.new_page()
            page.goto(f"https://fedresurs.ru/search?q={inn}", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)

            body = page.inner_text("body")
            browser.close()

            lines = [l.strip() for l in body.split("\n") if l.strip()]
            text = " ".join(lines)

            # Detect bankruptcy status
            bankruptcy_status = "none"
            if "банкрот" in text.lower():
                if "завершен" in text.lower():
                    bankruptcy_status = "completed"
                elif "процедур" in text.lower() or "введен" in text.lower():
                    bankruptcy_status = "in_progress"
                else:
                    bankruptcy_status = "mentioned"

            # Extract publications
            publications = []
            for l in lines:
                if "сообщение" in l.lower() or "публикация" in l.lower() or "№" in l:
                    publications.append(l[:100])

            return {
                "source": "Федресурс/fedresurs.ru",
                "bankruptcy_status": bankruptcy_status,
                "procedure_type": "",
                "procedure_date": "",
                "manager": "",
                "publications": publications[:10],
                "pledges": [],
                "error": None,
                "note": "Playwright сбор",
            }

    except Exception as e:
        logger.error(f"Федресурс Playwright error: {e}")
        return {"source": "Федресурс/fedresurs.ru", "error": str(e)}


async def fetch(inn: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch, inn)
