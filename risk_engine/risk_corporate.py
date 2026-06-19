from datetime import datetime, timedelta


def _is_recent(date_str: str) -> bool:
    if not date_str:
        return False
    try:
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                d = datetime.strptime(date_str, fmt)
                return d > datetime.now() - timedelta(days=180)
            except ValueError:
                continue
    except Exception:
        pass
    return False


def calculate(egrul_data: dict) -> dict:
    findings = []
    score = 0

    # Check status
    status = egrul_data.get("status", "")
    if "ликвидац" in status.lower() or "банкрот" in status.lower():
        findings.append({"risk": "Процедура ликвидации или банкротства", "confirmed": True, "source": "ЕГРЮЛ", "detail": f"Статус: {status}"})
        score += 40

    # Mass address
    if egrul_data.get("mass_address"):
        findings.append({"risk": "Массовый адрес", "confirmed": True, "source": "ЕГРЮЛ", "detail": "Адрес массовой регистрации"})
        score += 20

    # Mass director
    if egrul_data.get("mass_director"):
        findings.append({"risk": "Массовый директор", "confirmed": True, "source": "ЕГРЮЛ", "detail": "Массовый руководитель"})
        score += 20

    # Recent changes x1.5 multiplier
    changes = egrul_data.get("changes_history", [])
    recent_changes = [c for c in changes if _is_recent(c.get("date", ""))]
    if recent_changes:
        score = int(score * 1.5)
        findings.append({"risk": "Изменения за последние 6 месяцев", "confirmed": True, "source": "ЕГРЮЛ", "detail": f"Изменений: {len(recent_changes)}"})

    level = "low"
    if score > 50:
        level = "high"
    elif score > 20:
        level = "medium"

    return {"category": "corporate", "score": min(score, 100), "level": level, "findings": findings}
