import asyncio
import random
from typing import Optional

import httpx
from fake_useragent import UserAgent
from cachetools import TTLCache

from config import (
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
    REQUEST_TIMEOUT,
    CACHE_TTL,
)

ua = UserAgent()
_cache = TTLCache(maxsize=500, ttl=CACHE_TTL)


class HttpClient:
    def __init__(self):
        self.proxy_pool = []
        self.retries = 3

    def _random_headers(self) -> dict:
        return {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": random.choice(["ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7", "en-US,en;q=0.9,ru;q=0.8"]),
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": random.choice([
                "https://yandex.ru/",
                "https://google.com/",
                "https://mail.ru/",
            ]),
            "DNT": "1",
            "Connection": "keep-alive",
        }

    async def _sleep(self):
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        await asyncio.sleep(delay)

    async def get(
        self,
        url: str,
        params: Optional[dict] = None,
        use_playwright: bool = False,
        use_curl: bool = True,
    ) -> Optional[dict]:
        cache_key = (url, str(params))
        if cache_key in _cache:
            return _cache[cache_key]

        await self._sleep()

        for attempt in range(self.retries):
            try:
                headers = self._random_headers()
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=False) as client:
                    resp = await client.get(url, params=params, headers=headers)
                    if resp.status_code in (403, 429):
                        if use_playwright:
                            return await self._fetch_with_playwright(url)
                        raise Exception(f"HTTP {resp.status_code}: blocked")
                    resp.raise_for_status()
                    result = resp.json() if "application/json" in resp.headers.get("Content-Type", "") else resp.text
                    _cache[cache_key] = result
                    return result
            except Exception as e:
                if attempt == self.retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        return None

    async def post(self, url: str, data: dict, headers: Optional[dict] = None) -> Optional[dict]:
        await self._sleep()
        for attempt in range(self.retries):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=False) as client:
                    resp = await client.post(url, json=data, headers=headers or self._random_headers())
                    resp.raise_for_status()
                    return resp.json() if "application/json" in resp.headers.get("Content-Type", "") else resp.text
            except Exception as e:
                if attempt == self.retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        return None

    async def _fetch_with_playwright(self, url: str) -> str:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle")
                html = await page.content()
                await browser.close()
                return html
        except Exception:
            return ""
