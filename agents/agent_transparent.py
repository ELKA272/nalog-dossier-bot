import httpx
from utils.logger import logger


async def fetch(inn: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            resp = await client.get(
                "https://pb.nalog.ru/api/search",
                params={"query": inn, "page": 0, "pageSize": 10},
            )
            if resp.status_code == 404:
                return {"source": "Прозрачный бизнес/pb.nalog.ru", "error": "Не найдено (404)", "employees_count": 0, "taxes_paid": 0, "income": 0, "expenses": 0, "tax_debt": 0, "tax_regime_special": "", "violations_flag": False, "tax_burden_percent": 0}
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return {"source": "Прозрачный бизнес/pb.nalog.ru", "error": "Не найдено", "employees_count": 0, "taxes_paid": 0, "income": 0, "expenses": 0, "tax_debt": 0, "tax_regime_special": "", "violations_flag": False, "tax_burden_percent": 0}

            item = items[0]
            taxes_paid = item.get("налогУплачено", 0) or 0
            income = item.get("доходы", 0) or 0
            expenses = item.get("расходы", 0) or 0
            tax_burden = round(taxes_paid / income * 100, 2) if income else 0
            return {
                "source": "Прозрачный бизнес/pb.nalog.ru",
                "employees_count": item.get("среднесписочнаяЧисленность", 0),
                "taxes_paid": taxes_paid,
                "income": income,
                "expenses": expenses,
                "tax_debt": item.get("налогЗадолженность", 0),
                "tax_regime_special": item.get("спецРежим", ""),
                "violations_flag": item.get("нарушения", False),
                "tax_burden_percent": tax_burden,
                "error": None,
            }
    except Exception as e:
        logger.error(f"Прозрачный бизнес error: {e}")
        return {"source": "Прозрачный бизнес/pb.nalog.ru", "error": str(e), "employees_count": 0, "taxes_paid": 0, "income": 0, "expenses": 0, "tax_debt": 0, "tax_regime_special": "", "violations_flag": False, "tax_burden_percent": 0}
