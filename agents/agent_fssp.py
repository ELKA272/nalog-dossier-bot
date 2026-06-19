import asyncio
import re
import aiohttp
from utils.logger import logger
from config import FSSP_API_KEY, PARSER_FSSP_BASE_URL
from agents._playwright_helper import find_chrome


def _extract_proceedings(api_result: list) -> list:
    proceedings = []
    for item in api_result:
        subjects = item.get("subjects", [])
        total = 0
        subject_text = ""
        for s in subjects:
            title = s.get("title", "")
            raw_sum = s.get("sum", "")
            if raw_sum and title not in ("Исполнительский сбор",):
                try:
                    total += int(float(raw_sum))
                except (ValueError, TypeError):
                    pass
            if not subject_text and title and title not in (
                "Общая сумма задолженности", "Задолженность", "Исполнительский сбор",
            ):
                subject_text = title

        stop_date = item.get("stop_date") or ""
        is_active = not bool(stop_date)

        proceedings.append({
            "number": item.get("process_title", ""),
            "amount": total,
            "subject": subject_text,
            "date_start": item.get("process_date", ""),
            "status": "активное" if is_active else f"окончено: {item.get('stop_reason', '')}",
        })
    return proceedings


async def _api_fetch(inn: str) -> dict:
    if not FSSP_API_KEY:
        return {"source": "ФССП/parser-api.com", "error": "FSSP_API_KEY не задан"}

    is_ul = len(inn) == 10
    endpoint = f"{PARSER_FSSP_BASE_URL}/search_ur_by_inn"

    params = {"key": FSSP_API_KEY, "inn": inn}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params, timeout=30) as resp:
                if resp.status != 200:
                    return {"source": "ФССП/parser-api.com", "error": f"HTTP {resp.status}"}
                data = await resp.json()

        if data.get("done") != 1:
            return {"source": "ФССП/parser-api.com", "error": f"API error: {data.get('error', 'unknown')}"}

        result = data.get("result", [])
        proceedings = _extract_proceedings(result)
        total_debt = sum(p["amount"] for p in proceedings)

        return {
            "source": "ФССП/parser-api.com",
            "has_proceedings": len(proceedings) > 0,
            "total_debt": total_debt,
            "proceedings": proceedings,
            "repeat_flag": len(proceedings) > 3,
            "error": None,
            "note": f"parser-api.com: {len(proceedings)} производств",
        }

    except asyncio.TimeoutError:
        return {"source": "ФССП/parser-api.com", "error": "Timeout"}
    except Exception as e:
        logger.error(f"ФССП parser-api error: {e}")
        return {"source": "ФССП/parser-api.com", "error": str(e)}


def _sync_fetch_fallback(inn: str) -> dict:
    chrome = find_chrome()
    if not chrome:
        return {"source": "ФССП/fssp.gov.ru", "error": "Chromium не найден"}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=chrome,
                                         args=["--no-sandbox"])
            page = browser.new_page()
            page.goto("https://fssp.gov.ru/iss/ip", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            try:
                page.fill("input[name='inn'], input[placeholder*='ИНН'], input[type='text']", inn)
                page.wait_for_timeout(1000)
                page.press("input[name='inn'], input[placeholder*='ИНН'], input[type='text']", "Enter")
                page.wait_for_timeout(5000)
            except Exception:
                pass

            body = page.inner_text("body")
            browser.close()

            lines = [l.strip() for l in body.split("\n") if l.strip()]
            proceedings = []

            amounts = re.findall(r"(\d[\d\s]*)\s*руб", body)
            numbers = re.findall(r"\d{4,8}/\d{2,4}/\d{2,4}", body)

            for i, num in enumerate(numbers[:10]):
                amount = 0
                if i < len(amounts):
                    try:
                        amount = int(amounts[i].replace(" ", ""))
                    except ValueError:
                        pass
                proceedings.append({
                    "number": num,
                    "amount": amount,
                    "subject": "",
                    "date_start": "",
                    "status": "активное" if amount > 0 else "окончено",
                })

            return {
                "source": "ФССП/fssp.gov.ru",
                "has_proceedings": len(proceedings) > 0,
                "total_debt": sum(p["amount"] for p in proceedings),
                "proceedings": proceedings,
                "repeat_flag": len(proceedings) > 3,
                "error": None,
                "note": "Playwright сбор" if proceedings else "Производства не найдены",
            }

    except Exception as e:
        logger.error(f"ФССП Playwright fallback error: {e}")
        return {"source": "ФССП/fssp.gov.ru", "error": str(e)}


async def fetch(inn: str) -> dict:
    result = await _api_fetch(inn)
    if result.get("error") and result["error"] not in ("FSSP_API_KEY не задан",):
        logger.warning(f"Parser API failed, fallback to Playwright: {result['error']}")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _sync_fetch_fallback, inn)
    return result
