import asyncio
from utils.logger import logger
from agents._playwright_helper import find_chrome


def _sync_fetch(inn: str, ogrn: str = "") -> dict:
    chrome = find_chrome()
    if not chrome:
        return {"source": "B2B House/b2b.house", "error": "Chromium не найден"}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=chrome,
                                         args=["--no-sandbox"])
            page = browser.new_page()
            if ogrn:
                page.goto(f"https://b2b.house/company/{ogrn}", wait_until="domcontentloaded", timeout=30000)
            else:
                page.goto(f"https://b2b.house/company/{inn}", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)

            body = page.inner_text("body")
            html = page.content()
            browser.close()

            lines = [l.strip() for l in body.split("\n") if l.strip()]
            result = {
                "source": "B2B House/b2b.house",
                "inn": inn,
                "company_name": "",
                "ogrn": "",
                "director": "",
                "revenue": "",
                "profit": "",
                "category": "",
                "error": None,
            }

            for i, l in enumerate(lines):
                lower = l.lower()
                if "огрн" in lower:
                    result["ogrn"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "директор" in lower or "руководител" in lower:
                    result["director"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "выручк" in lower:
                    result["revenue"] = l
                if "прибыль" in lower:
                    result["profit"] = l
                if "категория" in lower or "отрасль" in lower:
                    result["category"] = lines[i + 1] if i + 1 < len(lines) else ""

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            h1 = soup.find("h1")
            if h1:
                result["company_name"] = h1.get_text(strip=True)

            logger.info(f"b2b.house: данные получены для ИНН {inn}")
            return result

    except Exception as e:
        logger.error(f"B2B House Playwright error: {e}")
        return {"source": "B2B House/b2b.house", "error": str(e)}


async def fetch(inn: str, ogrn: str = "") -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch, inn, ogrn)
