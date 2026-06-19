def calculate(
    egrul_data: dict,
    transparent_data: dict,
    rusprofile_data: dict,
    licenses_data: dict,
) -> dict:
    indicators = []
    score = 0

    employees = transparent_data.get("employees_count", 0)
    if employees == 0:
        indicators.append("Нет сотрудников при наличии деятельности")
        score += 2
    elif employees == 1:
        indicators.append("Всего 1 сотрудник")
        score += 1

    income = transparent_data.get("income", 0)
    if income > 5_000_000 and employees == 0:
        indicators.append("Большие обороты при нулевом количестве сотрудников")
        score += 3

    tax_burden = transparent_data.get("tax_burden_percent", 0)
    if tax_burden < 1 and income > 0:
        indicators.append(f"Налоговая нагрузка < 1% ({tax_burden}%)")
        score += 3

    if egrul_data.get("mass_address"):
        indicators.append("Массовый адрес регистрации")
        score += 2

    if egrul_data.get("mass_director"):
        indicators.append("Массовый директор")
        score += 2

    if licenses_data.get("risk_no_license") and not licenses_data.get("has_license"):
        indicators.append("Лицензируемая деятельность без лицензии")
        score += 3

    if score >= 7:
        conclusion = "ВЫСОКАЯ"
    elif score >= 4:
        conclusion = "СРЕДНЯЯ"
    else:
        conclusion = "НИЗКАЯ"

    return {
        "category": "technical",
        "score": score,
        "conclusion": conclusion,
        "indicators": indicators,
        "detail": f"На основании выявленных признаков вероятность признания организации технической компанией оценивается как {conclusion}",
    }
