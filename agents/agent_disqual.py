import httpx
from utils.logger import logger


async def fetch(persons: list) -> dict:
    if not persons:
        return {"source": "Реестр дисквалифицированных лиц/nalog.ru", "persons_checked": [], "disqualified": [], "has_disqualified": False, "error": None}

    disqualified = []
    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            for person in persons:
                resp = await client.post(
                    "https://service.nalog.ru/disfind.do",
                    data={"fio": person},
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("disqualified"):
                    disqualified.append({
                        "fio": person,
                        "date": data.get("date"),
                        "period": data.get("period"),
                        "reason": data.get("reason"),
                    })

        return {
            "source": "Реестр дисквалифицированных лиц/nalog.ru",
            "persons_checked": persons,
            "disqualified": disqualified,
            "has_disqualified": len(disqualified) > 0,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Дисквалификация error: {e}")
        return {"source": "Реестр дисквалифицированных лиц/nalog.ru", "error": str(e)}
