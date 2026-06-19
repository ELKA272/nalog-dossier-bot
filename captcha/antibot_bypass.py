import asyncio
import random
from typing import Optional

from utils.logger import logger


class AntibotBypass:
    @staticmethod
    def get_random_headers() -> dict:
        return {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            ]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": random.choice(["ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7", "en-US,en;q=0.9,ru;q=0.8"]),
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": random.choice([
                "https://yandex.ru/", "https://google.com/", "https://mail.ru/",
                "https://www.google.com/search?q=",
            ]),
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

    @staticmethod
    def get_random_delay() -> float:
        return random.uniform(2.0, 5.0)

    async def fetch_with_curl_cffi(self, url: str, params: Optional[dict] = None) -> Optional[str]:
        try:
            from curl_cffi import requests as cf_requests
            resp = cf_requests.get(url, params=params, impersonate="chrome120", headers=self.get_random_headers())
            return resp.text if resp.status_code == 200 else None
        except Exception as e:
            logger.error(f"curl_cffi error for {url}: {e}")
            return None

    async def fetch_with_playwright(self, url: str) -> Optional[str]:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
                page = await browser.new_page()
                await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                await asyncio.sleep(random.uniform(1, 3))
                await page.goto(url, wait_until="networkidle")
                html = await page.content()
                await browser.close()
                return html
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return None
