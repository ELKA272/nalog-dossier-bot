import asyncio
from utils.logger import logger
from agents._playwright_helper import find_chrome


def _sync_fetch(inn: str, ogrn: str = "") -> dict:
    chrome = find_chrome()
    if not chrome:
        return {"source": "List-Org/list-org.com", "error": "Chromium не найден"}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=chrome,
                                         args=["--no-sandbox"])
            page = browser.new_page()
            if ogrn:
                page.goto(f"https://www.list-org.com/search?q={ogrn}", wait_until="domcontentloaded", timeout=30000)
            else:
                page.goto(f"https://www.list-org.com/search?q={inn}", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            body = page.inner_text("body")
            html = page.content()
            browser.close()

            lines = [l.strip() for l in body.split("\n") if l.strip()]
            result = {
                "source": "List-Org/list-org.com",
                "inn": inn,
                "company_name": "",
                "ogrn": "",
                "address": "",
                "director": "",
                "okved": "",
                "status": "",
                "error": None,
            }

            for i, l in enumerate(lines):
                lower = l.lower()
                if "огрн" in lower:
                    result["ogrn"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "адрес" in lower and len(l) < 20:
                    result["address"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "руководител" in lower or "директор" in lower:
                    result["director"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "оквэд" in lower:
                    result["okved"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "статус" in lower and "действ" in l.lower():
                    result["status"] = l

            # Try to get company name from HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            h1 = soup.find("h1")
            if h1:
                result["company_name"] = h1.get_text(strip=True)
            title = soup.find("title")
            if title and not result.get("company_name"):
                t = title.get_text(strip=True)
                if "|" in t:
                    result["company_name"] = t.split("|")[0].strip()

            logger.info(f"list-org.com: данные получены для ИНН {inn}")
            return result

    except Exception as e:
        logger.error(f"List-Org Playwright error: {e}")
        return {"source": "List-Org/list-org.com", "error": str(e)}


async def fetch(inn: str, ogrn: str = "") -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch, inn, ogrn)
