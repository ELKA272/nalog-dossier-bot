import asyncio
import aiohttp
from utils.logger import logger

API_KEY = "d117c8b0e4d8bd9cb9f80dcfc612cd3d"
BASE = "https://parser-api.com/parser"


async def _get(session, endpoint: str, params: dict) -> dict:
    params["key"] = API_KEY
    url = f"{BASE}/{endpoint}"
    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.error(f"ParserAPI {endpoint}: HTTP {resp.status}")
                return {}
            return await resp.json()
    except Exception as e:
        logger.error(f"ParserAPI {endpoint}: {e}")
        return {}


# ── 1. ФНС Прозрачный Бизнес (pb.nalog.ru) ──
async def fetch_nalog_pb(inn: str, director_fio: str = "") -> dict:
    logger.info(f"ParserAPI: Налог ПБ по ИНН {inn}")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
        org = await _get(s, "nalog_pb_api/search_org", {"inn": inn})
        dis = {}
        if director_fio:
            dis = await _get(s, "nalog_pb_api/search_dis", {"fio": director_fio})
        limit_org = await _get(s, "nalog_pb_api/search_limit_org", {"inn": inn})

    result = {"source": "parser-api.com/nalog-pb", "api": True}

    if org.get("success") and org.get("org"):
        o = org["org"][0]
        result.update({
            "full_name": o.get("name", ""),
            "short_name": o.get("name_short", ""),
            "address": o.get("address", ""),
            "status": o.get("status", ""),
            "okved": o.get("okved", ""),
            "okved_name": o.get("okved_name", ""),
            "inn": inn,
        })

    if dis.get("success") and dis.get("dis"):
        result["disqualified"] = []
        for d in dis["dis"]:
            result["disqualified"].append({
                "name": d.get("name", ""),
                "period": d.get("period", ""),
                "start_date": d.get("start_date", ""),
                "end_date": d.get("end_date", ""),
                "court": d.get("court", ""),
                "article": d.get("article", ""),
            })

    if limit_org.get("success") and limit_org.get("limit_org"):
        result["restrictions"] = []
        for r in limit_org["limit_org"]:
            result["restrictions"].append({
                "name": r.get("name", ""),
                "reason": r.get("reason", ""),
                "start_date": r.get("start_date", ""),
                "end_date": r.get("end_date", ""),
                "org_name": r.get("org_name", ""),
            })

    return result


# ── 2. ФССП (fssp.gov.ru) ──
async def fetch_fssp(inn: str) -> dict:
    logger.info(f"ParserAPI: ФССП по ИНН {inn}")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
        data = await _get(s, "fssp_api/search_ur_by_inn", {"inn": inn})

    result = {"source": "parser-api.com/fssp", "api": True}

    if data.get("done"):
        proceedings = data.get("result", [])
        total_debt = 0
        proc_list = []
        for p in proceedings:
            subjects = p.get("subjects", [])
            debt = 0
            for sub in subjects:
                try:
                    debt += float(sub.get("sum", "0").replace(" ", "").replace(",", "."))
                except (ValueError, AttributeError):
                    pass
            total_debt += debt
            proc_list.append({
                "number": p.get("process_title", ""),
                "debt": debt,
                "date": p.get("process_date", ""),
                "bailiff": p.get("officer_name", ""),
                "department": p.get("department_title", ""),
                "status": "закрыто" if p.get("stop_date") else "активно",
                "stop_date": p.get("stop_date", ""),
                "stop_reason": p.get("stop_reason", ""),
            })

        result["total_proceedings"] = len(proc_list)
        result["total_debt"] = total_debt
        result["proceedings"] = proc_list
    else:
        result["note"] = "Исполнительные производства не найдены"

    return result


# ── 3. Федресурс (bankrot.fedresurs.ru) ──
async def fetch_fedresurs(inn: str) -> dict:
    logger.info(f"ParserAPI: Федресурс по ИНН {inn}")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
        data = await _get(s, "fedresurs_api/search_ur", {"orgCode": inn})

    result = {"source": "parser-api.com/fedresurs", "api": True}

    if data.get("success") and data.get("records"):
        records = data["records"]
        result["total_bankrupt"] = int(data.get("total_count", 0))
        result["records"] = []
        for r in records:
            rec = {
                "name": r.get("debtor", ""),
                "inn": r.get("inn", ""),
                "ogrn": r.get("ogrn", ""),
                "region": r.get("region", ""),
                "id": r.get("id", ""),
            }
            # get details
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s2:
                detail = await _get(s2, "fedresurs_api/get_org", {"id": r.get("id", "")})
            if detail.get("success") and detail.get("record"):
                rec["address"] = detail["record"].get("address", "")
                rec["category"] = detail["record"].get("category", "")
                rec["okpo"] = detail["record"].get("okpo", "")
                rec["full_name"] = detail["record"].get("full_name", "")
            result["records"].append(rec)
    else:
        result["total_bankrupt"] = 0
        result["records"] = []

    return result


# ── 4. Арбитраж (kad.arbitr.ru) ──
async def fetch_arbitr(inn: str) -> dict:
    logger.info(f"ParserAPI: Арбитраж по ИНН {inn}")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
        data = await _get(s, "arbitr_api/search", {"Inn": inn})
    if not data.get("Success"):
        return {"source": "parser-api.com/arbitr", "api": True, "error": data.get("error", "Нет данных")}

    cases = data.get("Cases", [])
    case_list = []
    for c in cases:
        case_list.append({
            "number": c.get("CaseNumber", ""),
            "type": c.get("CaseType", ""),
            "court": c.get("Court", ""),
            "date": c.get("StartDate", ""),
        })

    return {
        "source": "parser-api.com/arbitr",
        "api": True,
        "total_cases": len(case_list),
        "cases": case_list,
    }


# ── Main entry ──
async def fetch(inn: str, director_fio: str = "") -> dict:
    logger.info(f"ParserAPI: сбор данных из 4 источников по ИНН {inn}")

    # Get company name from egrul first (passed from orchestrator)
    director_fio = ""

    tasks = {
        "nalog_pb": asyncio.create_task(fetch_nalog_pb(inn, director_fio)),
        "fssp": asyncio.create_task(fetch_fssp(inn)),
        "fedresurs": asyncio.create_task(fetch_fedresurs(inn)),
        "arbitr": asyncio.create_task(fetch_arbitr(inn)),
    }

    results = {}
    for name, task in tasks.items():
        try:
            results[name] = await task
        except Exception as e:
            results[name] = {"error": str(e)}

    return {
        "source": "parser-api.com",
        "api": True,
        "nalog_pb": results.get("nalog_pb", {}),
        "fssp": results.get("fssp", {}),
        "fedresurs": results.get("fedresurs", {}),
        "arbitr": results.get("arbitr", {}),
    }
