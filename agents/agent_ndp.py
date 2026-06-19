from captcha.antibot_bypass import AntibotBypass
from utils.logger import logger


async def fetch(inn: str) -> dict:
    bypass = AntibotBypass()
    try:
        html = await bypass.fetch_with_curl_cffi("https://rnp.fas.gov.ru/", {"inn": inn})
        return {
            "source": "РНП/rnp.fas.gov.ru",
            "in_registry": False,
            "entries": [],
            "error": None,
            "note": "Требуется парсинг HTML",
            "raw_html_length": len(html) if html else 0,
        }
    except Exception as e:
        logger.error(f"РНП error: {e}")
        return {"source": "РНП/rnp.fas.gov.ru", "error": str(e)}
