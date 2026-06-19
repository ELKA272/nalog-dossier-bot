import asyncio
import re
import time
from utils.logger import logger
from agents._playwright_helper import find_chrome


def _sync_fetch(inn: str, ogrn: str = "") -> dict:
    chrome = find_chrome()
    if not chrome:
        return {"source": "Rusprofile/rusprofile.ru", "error": "Chromium не найден"}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=chrome,
                                         args=["--no-sandbox"])
            page = browser.new_page()

            # Go to search
            page.goto(f"https://www.rusprofile.ru/search?query={inn}", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # Click first result link
            link = page.query_selector("a[href*='/company/'], a[href*='/ip/']")
            if link:
                link.click()
                page.wait_for_timeout(5000)
            else:
                # Try if already on company page (direct match)
                pass

            html = page.content()
            browser.close()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            revenue = {}
            profit = {}
            net_assets = {}

            # Find financial table
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        label = cells[0].get_text(strip=True).lower()
                        vals = [c.get_text(strip=True) for c in cells[1:]]
                        if "выручка" in label:
                            for y, v in zip(("2022", "2023", "2024"), vals):
                                revenue[y] = v
                        if "чистая прибыль" in label:
                            for y, v in zip(("2022", "2023", "2024"), vals):
                                profit[y] = v
                        if "чистые активы" in label:
                            for y, v in zip(("2022", "2023", "2024"), vals):
                                net_assets[y] = v

            # Also look for financial data in dl/dt/dd structure
            dt_items = soup.find_all("dt")
            for dt in dt_items:
                label = dt.get_text(strip=True).lower()
                dd = dt.find_next_sibling("dd")
                if dd:
                    val = dd.get_text(strip=True)
                    if "выручка" in label:
                        revenue["2024"] = val
                    elif "прибыль" in label:
                        profit["2024"] = val

            # Also try extracting from div-based layout
            for div in soup.find_all("div", class_=re.compile("finance|fin|revenue|profit|stats", re.I)):
                text = div.get_text(strip=True)
                m = re.search(r"(выручка|revenue)[:\s]*([\d\s]+)", text, re.I)
                if m:
                    revenue["2024"] = m.group(2).strip()
                m = re.search(r"(прибыль|profit)[:\s]*([\d\s]+)", text, re.I)
                if m:
                    profit["2024"] = m.group(2).strip()

            # Phone and website
            phone = ""
            website = ""
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "tel:" in href:
                    phone = href.replace("tel:", "")
                elif not website and href.startswith("http") and "rusprofile" not in href:
                    website = href

            # Related companies
            related = []
            for div in soup.find_all("div", class_=re.compile("related|link|company")):
                text = div.get_text(strip=True)
                if text and len(text) > 5 and ("ООО" in text or "АО" in text or "ИП" in text):
                    related.append(text[:100])

            return {
                "source": "Rusprofile/rusprofile.ru",
                "revenue": revenue,
                "net_profit": profit,
                "net_assets": net_assets,
                "liabilities": {"short": 0, "long": 0},
                "related_companies": related[:10],
                "phones": [phone] if phone else [],
                "website": website,
                "error": None,
            }

    except Exception as e:
        logger.error(f"Rusprofile Playwright error: {e}")
        return {"source": "Rusprofile/rusprofile.ru", "error": str(e)}


async def fetch(inn: str, ogrn: str = "") -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fetch, inn, ogrn)
