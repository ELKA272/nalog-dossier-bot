from captcha.antibot_bypass import AntibotBypass
from utils.logger import logger


async def fetch(inn: str) -> dict:
    bypass = AntibotBypass()
    try:
        html = await bypass.fetch_with_curl_cffi(
            "https://bankrot.fedresurs.ru/DebitorList.aspx", {"inn": inn}
        )
        return {
            "source": "Банкротства/bankrot.fedresurs.ru",
            "bankruptcy_status": "checked",
            "raw_html_length": len(html) if html else 0,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Банкротства error: {e}")
        return {"source": "Банкротства/bankrot.fedresurs.ru", "error": str(e)}
