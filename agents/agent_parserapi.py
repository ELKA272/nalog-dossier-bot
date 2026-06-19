import asyncio
import aiohttp
from utils.logger import logger

PARSER_API_KEY = "d117c8b0e4d8bd9cb9f80dcfc612cd3d"
PARSER_BASE = "https://parser-api.com/parser"


async def fetch_arbitr(inn: str) -> dict:
    """Get arbitration cases from parser-api.com by INN."""
    url = f"{PARSER_BASE}/arbitr_api/search"
    params = {"key": PARSER_API_KEY, "Inn": inn}
    logger.info(f"ParserAPI: запрос арбитражных дел по ИНН {inn}")

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"ParserAPI arbitr: HTTP {resp.status}")
                    return {"error": f"HTTP {resp.status}"}
                data = await resp.json()
    except Exception as e:
        logger.error(f"ParserAPI arbitr: {e}")
        return {"error": str(e)}

    if not data.get("Success"):
        return {"error": data.get("error", "Unknown error")}

    cases = data.get("Cases", [])
    total = len(cases)
    as_plaintiff = sum(1 for c in cases if any(p.get("Inn") == inn for p in (c.get("Plaintiffs") or [])))
    as_defendant = sum(1 for c in cases if any(r.get("Inn") == inn for r in (c.get("Respondents") or [])))
    tax_disputes = sum(1 for c in cases if c.get("CaseType") == "A" and any(
        "налог" in (p.get("Name", "") or "").lower() or "фнс" in (p.get("Name", "") or "").lower()
        for p in (c.get("Plaintiffs") or []) + (c.get("Respondents") or [])
    ))

    case_list = []
    for c in cases:
        case_list.append({
            "number": c.get("CaseNumber", ""),
            "type": c.get("CaseType", ""),
            "court": c.get("Court", ""),
            "date": c.get("StartDate", ""),
        })

    return {
        "source": "parser-api.com/kad.arbitr.ru",
        "total_cases": total,
        "as_plaintiff": as_plaintiff,
        "as_defendant": as_defendant,
        "tax_disputes": tax_disputes,
        "total_claims_amount": 0,
        "cases": case_list,
        "api": True,
    }


async def fetch_fssp(inn: str) -> dict:
    """Get FSSP (bailiff) data from parser-api by INN."""
    url = f"{PARSER_BASE}/fssp_api/search_ul"
    params = {"key": PARSER_API_KEY, "inn": inn}
    logger.info(f"ParserAPI: запрос ФССП по ИНН {inn}")

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.info(f"ParserAPI FSSP ul: HTTP {resp.status}, trying fiz endpoint")
                    return {"error": f"HTTP {resp.status}", "note": "ФССП по юрлицам через parser-api недоступен"}
                data = await resp.json()
    except Exception as e:
        logger.error(f"ParserAPI FSSP: {e}")
        return {"error": str(e)}

    if not data.get("done"):
        return {"error": data.get("error", "Unknown")}

    proceedings = data.get("result", [])
    total_debt = 0
    proc_list = []
    for p in proceedings:
        debt_str = p.get("debt", "0")
        try:
            debt = float(debt_str.replace(" ", "").replace(",", "."))
            total_debt += debt
        except (ValueError, AttributeError):
            debt = 0
        proc_list.append({
            "number": p.get("number", ""),
            "debt": debt,
            "date": p.get("date", ""),
            "bailiff": p.get("bailiff", ""),
        })

    return {
        "source": "parser-api.com/fssp",
        "total_proceedings": len(proc_list),
        "total_debt": total_debt,
        "proceedings": proc_list,
        "api": True,
    }


async def fetch(inn: str) -> dict:
    """Main entry point: fetch all parser-api data by INN."""
    logger.info(f"ParserAPI: сбор данных по ИНН {inn}")

    arbitr_task = asyncio.create_task(fetch_arbitr(inn))
    fssp_task = asyncio.create_task(fetch_fssp(inn))

    arbitr_data, fssp_data = await asyncio.gather(arbitr_task, fssp_task, return_exceptions=True)

    result = {
        "arbitr": arbitr_data if not isinstance(arbitr_data, Exception) else {"error": str(arbitr_data)},
        "fssp": fssp_data if not isinstance(fssp_data, Exception) else {"error": str(fssp_data)},
        "source": "parser-api.com",
        "api": True,
    }
    return result
