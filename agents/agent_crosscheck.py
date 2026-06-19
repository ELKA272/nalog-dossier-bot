from utils.logger import logger


async def fetch(all_agents_data: dict) -> dict:
    connections = []
    splitting_count = 0

    try:
        egrul = all_agents_data.get("agent_egrul", {})
        is_ip = egrul.get("is_ip", False)
        company_name = egrul.get("full_name", "") or egrul.get("short_name", "")
        director = egrul.get("director", {}).get("fio", "")
        address = egrul.get("address", "")
        founders = egrul.get("founders", [])
        okved = egrul.get("okved_main", "")

        # Shared address check
        if address:
            connections.append({
                "type": "Юридический адрес",
                "entity_a": company_name,
                "entity_b": address,
                "detail": "Проверить массовость адреса через сервис ФНС",
                "strength": "medium",
            })

        # Director links
        if director:
            connections.append({
                "type": "Руководитель",
                "entity_a": company_name,
                "entity_b": director,
                "detail": "Проверить участие руководителя в других ЮЛ через сервис ФНС",
                "strength": "medium",
            })

        # Founder links
        for f in founders:
            fio = f.get("fio", "")
            if fio and fio != director:
                connections.append({
                    "type": "Учредитель",
                    "entity_a": company_name,
                    "entity_b": fio,
                    "detail": "Учредитель может быть связан с другими компаниями",
                    "strength": "medium",
                })
                splitting_count += 1

        # Same-person indicators (director = founder)
        for f in founders:
            if f.get("fio", "") == director and director:
                connections.append({
                    "type": "Совпадение руководителя и учредителя",
                    "entity_a": company_name,
                    "entity_b": director,
                    "detail": "Руководитель является учредителем — типично для микробизнеса",
                    "strength": "weak",
                })
                break

        # Business splitting indicators
        if is_ip:
            connections.append({
                "type": "ИП — единоличная форма",
                "entity_a": company_name,
                "entity_b": director,
                "detail": "ИП не имеет учредителей, контроль 100% у физлица",
                "strength": "weak",
            })
        else:
            if len(founders) > 1:
                connections.append({
                    "type": "Несколько учредителей",
                    "entity_a": company_name,
                    "entity_b": ", ".join(f.get("fio", "") for f in founders),
                    "detail": f"Количество учредителей: {len(founders)}",
                    "strength": "weak",
                })

    except Exception as e:
        logger.error(f"Кросс-анализ error: {e}")

    return {
        "source": "Кросс-анализ (ЕГРЮЛ)",
        "connections": connections,
        "link_map": {},
        "splitting_indicators_count": splitting_count,
        "error": None,
    }
