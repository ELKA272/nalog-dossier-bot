def calculate(media_data: dict, arbitr_data: dict, fssp_data: dict) -> dict:
    findings = []
    score = 0

    # Negative media
    if media_data.get("negative_media"):
        findings.append({"risk": "Негативные публикации в СМИ", "confirmed": True, "source": "Яндекс.Новости/Google News", "detail": f"Найдено негативных статей"})
        score += 25

    # Fraud mentions
    if media_data.get("fraud_mentions"):
        findings.append({"risk": "Упоминания мошенничества или обмана", "confirmed": True, "source": "СМИ", "detail": "Упоминания мошенничества в публикациях"})
        score += 30

    # Defendant in court
    as_defendant = arbitr_data.get("as_defendant", 0)
    if as_defendant > 0:
        findings.append({"risk": "Активные судебные споры в роли ответчика", "confirmed": True, "source": "КАД Арбитраж", "detail": f"Дела как ответчик: {as_defendant}"})
        score += min(as_defendant * 10, 30)

    # Enforcement proceedings
    if fssp_data.get("has_proceedings"):
        findings.append({"risk": "Неоплаченные исполнительные производства", "confirmed": True, "source": "ФССП", "detail": f"Общая задолженность: {fssp_data.get('total_debt', 0)} руб."})
        score += 20

    level = "low"
    if score > 50:
        level = "high"
    elif score > 20:
        level = "medium"

    return {"category": "reputation", "score": min(score, 100), "level": level, "findings": findings}
