import asyncio
from utils.logger import logger
from agents._playwright_helper import find_chrome


def _sync_fetch(inn: str, ogrn: str = "") -> dict:
    chrome = find_chrome()
    if not chrome:
        return {"source": "Точка/check.tochka.com", "error": "Chromium не найден"}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=chrome,
                                         args=["--no-sandbox"])
            page = browser.new_page()
            if ogrn:
                page.goto(f"https://check.tochka.com/company/{ogrn}/", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(5000)
            else:
                page.goto("https://check.tochka.com/", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)

                search_input = page.query_selector('input[type="text"], input[placeholder*="ИНН"], input[placeholder*="ОГРН"], input[placeholder*="назван"]')
                if search_input:
                    search_input.fill(inn)
                    search_input.press("Enter")
                    page.wait_for_timeout(5000)
                else:
                    page.goto(f"https://check.tochka.com/search?query={inn}", wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(5000)

            current_url = page.url
            body = page.inner_text("body")
            html = page.content()
            browser.close()

            lines = [l.strip() for l in body.split("\n") if l.strip()]
            text = " ".join(lines)

            result = {
                "source": "Точка/check.tochka.com",
                "inn": inn,
                "company_name": "",
                "ogrn": "",
                "status": "",
                "address": "",
                "director": "",
                "revenue": "",
                "profit": "",
                "tax_debt": "",
                "court_cases_count": 0,
                "enforcement_count": 0,
                "error": None,
            }

            if "такой страницы здесь нет" in text.lower() or "404" in text:
                result["error"] = "Компания не найдена на check.tochka.com"
                logger.info(f"check.tochka.com: компания с ИНН {inn} не найдена")
                return result

            for i, l in enumerate(lines):
                lower = l.lower()
                if "огрн" in lower:
                    result["ogrn"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "статус" in lower:
                    result["status"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "адрес" in lower:
                    result["address"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "директор" in lower or "руководител" in lower:
                    result["director"] = lines[i + 1] if i + 1 < len(lines) else ""
                if "выручк" in lower:
                    result["revenue"] = l
                if "прибыл" in lower:
                    result["profit"] = l
                if "долг" in lower or "задолженност" in lower:
                    result["tax_debt"] = l

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            h1 = soup.find("h1")
            if h1:
                result["company_name"] = h1.get_text(strip=True)

            logger.info(f"check.tochka.com: данные получены для ИНН {inn}")
            return result

    except Exception as e:
        logger.error(f"Точка Playwright error: {e}")
        return {"source": "Точка/check.tochka.com", "error": str(e)}


async def fetch(inn: str, ogrn: str = "") -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch, inn, ogrn)
