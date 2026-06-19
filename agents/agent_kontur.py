import asyncio
from utils.logger import logger
from agents._playwright_helper import find_chrome


def _sync_fetch(inn: str, ogrn: str = "") -> dict:
    chrome = find_chrome()
    if not chrome:
        return {"source": "Контур Фокус/focus.kontur.ru", "error": "Chromium не найден"}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=chrome,
                                         args=["--no-sandbox"])
            page = browser.new_page()
            if ogrn:
                page.goto(f"https://focus.kontur.ru/search?ogrn={ogrn}", wait_until="domcontentloaded", timeout=30000)
            else:
                page.goto(f"https://focus.kontur.ru/search?inn={inn}", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)

            body = page.inner_text("body")
            browser.close()

            lines = [l.strip() for l in body.split("\n") if l.strip()]
            result = {
                "source": "Контур Фокус/focus.kontur.ru",
                "inn": inn,
                "company_name": "",
                "ogrn": "",
                "status": "",
                "director": "",
                "revenue": "",
                "profit": "",
                "court_cases": 0,
                "enforcement": 0,
                "licenses": "",
                "error": None,
            }

            for i, l in enumerate(lines):
                lower = l.lower()
                if "огрн" in lower:
                    result["ogrn"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "статус" in lower:
                    result["status"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "руководител" in lower or "директор" in lower:
                    result["director"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "выручк" in lower:
                    result["revenue"] = l
                if "чистая прибыль" in lower or "прибыль" in lower:
                    result["profit"] = l
                if "судебн" in lower or "арбитраж" in lower:
                    import re
                    nums = re.findall(r"\d+", l)
                    result["court_cases"] = int(nums[0]) if nums else 0
                if "исполнительн" in lower or "фссп" in lower:
                    import re
                    nums = re.findall(r"\d+", l)
                    result["enforcement"] = int(nums[0]) if nums else 0

            logger.info(f"focus.kontur.ru: данные получены для ИНН {inn}")
            return result

    except Exception as e:
        logger.error(f"Контур Фокус Playwright error: {e}")
        return {"source": "Контур Фокус/focus.kontur.ru", "error": str(e)}


async def fetch(inn: str, ogrn: str = "") -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch, inn, ogrn)
