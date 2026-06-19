import asyncio
import random
from typing import Optional

from config import CAPTCHA_API_KEY
from utils.logger import logger


class CaptchaSolver:
    def __init__(self):
        self.api_key = CAPTCHA_API_KEY

    async def solve_recaptcha_v2(self, site_key: str, page_url: str) -> Optional[str]:
        if not self.api_key:
            logger.warning("CAPTCHA_API_KEY не задан, пропускаем решение капчи")
            return None
        try:
            from twocaptcha import TwoCaptcha
            solver = TwoCaptcha(self.api_key)
            result = solver.recaptcha(sitekey=site_key, url=page_url)
            return result.get("code")
        except Exception as e:
            logger.error(f"Ошибка решения капчи: {e}")
            return None

    async def solve_hcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        if not self.api_key:
            return None
        try:
            from twocaptcha import TwoCaptcha
            solver = TwoCaptcha(self.api_key)
            result = solver.hcaptcha(sitekey=site_key, url=page_url)
            return result.get("code")
        except Exception as e:
            logger.error(f"Ошибка решения hCaptcha: {e}")
            return None
