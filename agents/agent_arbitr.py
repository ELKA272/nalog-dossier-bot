import asyncio
import re
from utils.logger import logger
from agents._playwright_helper import find_chrome


def _sync_fetch(inn: str) -> dict:
    chrome = find_chrome()
    if not chrome:
        return {"source": "Картотека арбитражных дел/kad.arbitr.ru", "error": "Chromium не найден"}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=chrome,
                                         args=["--no-sandbox"])
            page = browser.new_page()
            page.goto("https://kad.arbitr.ru/", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Type INN into search
            page.fill("input[placeholder*='ИНН'], input[placeholder*='Поиск'], input[type='text']", inn)
            page.wait_for_timeout(1000)
            page.press("input[placeholder*='ИНН'], input[placeholder*='Поиск'], input[type='text']", "Enter")
            page.wait_for_timeout(8000)

            body = page.inner_text("body")
            html = page.content()
            browser.close()

            lines = [l.strip() for l in body.split("\n") if l.strip()]
            text = " ".join(lines)

            cases = []
            case_blocks = re.split(r"\n\s*\n", body)
            for block in case_blocks[:20]:
                if re.search(r"\d{2,4}/\d{2,}", block) or "дело" in block.lower():
                    lines_b = [l.strip() for l in block.split("\n") if l.strip()]
                    case = {
                        "number": "",
                        "role": "",
                        "amount": 0,
                        "date": "",
                        "status": "",
                        "subject": "",
                    }
                    for l in lines_b:
                        lower = l.lower()
                        if re.match(r"^[а-яА-Яa-zA-Z0-9].*\d{4}", l):
                            case["number"] = l[:50]
                        if "истец" in lower:
                            case["role"] = "plaintiff"
                        elif "ответчик" in lower:
                            case["role"] = "defendant"
                        nums = re.findall(r"\d[\d\s]*", l)
                        for n in nums:
                            try:
                                v = int(n.replace(" ", ""))
                                if v > 1000:
                                    case["amount"] = v
                                    break
                            except ValueError:
                                pass
                    if case.get("number") or any(c.get("number") for c in cases):
                        cases.append(case)

            total = len(cases)
            as_plaintiff = sum(1 for c in cases if c["role"] == "plaintiff")
            as_defendant = sum(1 for c in cases if c["role"] == "defendant")
            total_amount = sum(c["amount"] for c in cases)
            tax_disputes = sum(1 for c in cases if "налог" in c.get("subject", "").lower() or "фнс" in c.get("subject", "").lower())

            return {
                "source": "Картотека арбитражных дел/kad.arbitr.ru",
                "total_cases": total,
                "as_plaintiff": as_plaintiff,
                "as_defendant": as_defendant,
                "as_third_party": total - as_plaintiff - as_defendant,
                "tax_disputes": tax_disputes,
                "total_claims_amount": total_amount,
                "cases": cases[:15],
                "error": None,
                "note": "Playwright сбор" if cases else "Дела не найдены",
            }

    except Exception as e:
        logger.error(f"КАД Арбитраж Playwright error: {e}")
        return {"source": "Картотека арбитражных дел/kad.arbitr.ru", "error": str(e)}


async def fetch(inn: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch, inn)
