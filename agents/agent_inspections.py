from captcha.antibot_bypass import AntibotBypass
from utils.logger import logger


async def fetch(inn: str) -> dict:
    bypass = AntibotBypass()
    try:
        html = await bypass.fetch_with_curl_cffi("https://proverki.gov.ru/portal/public/inspection", {"inn": inn})
        return {
            "source": "Реестр проверок/proverki.gov.ru",
            "total_inspections": 0,
            "tax_inspections": 0,
            "violations": 0,
            "inspections": [],
            "error": None,
            "note": "Требуется парсинг HTML",
            "raw_html_length": len(html) if html else 0,
        }
    except Exception as e:
        logger.error(f"Реестр проверок error: {e}")
        return {"source": "Реестр проверок/proverki.gov.ru", "error": str(e)}
