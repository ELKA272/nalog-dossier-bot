def calculate(data: dict) -> dict:
    findings = []
    score = 0

    revenue = data.get("revenue", {})
    profit = data.get("net_profit", {})

    # Check losses for 2+ years
    loss_years = 0
    for year in ("2022", "2023", "2024"):
        p = profit.get(year, 0)
        try:
            if float(str(p).replace(" ", "").replace(",", ".")) < 0:
                loss_years += 1
        except (ValueError, TypeError):
            pass

    if loss_years >= 2:
        findings.append({"risk": "Убытки на протяжении 2+ лет", "confirmed": True, "source": "Rusprofile", "detail": f"Убыточные годы: {loss_years}"})
        score += 30

    # Check revenue drop > 50%
    rev_values = []
    for year in ("2022", "2023", "2024"):
        try:
            rev_values.append(float(str(revenue.get(year, 0)).replace(" ", "").replace(",", ".")))
        except (ValueError, TypeError):
            rev_values.append(0)

    if len(rev_values) >= 2 and rev_values[-1] > 0 and rev_values[-2] > 0:
        if rev_values[-1] < rev_values[-2] * 0.5:
            findings.append({"risk": "Резкий спад выручки более чем на 50%", "confirmed": True, "source": "Rusprofile", "detail": f"Спад с {rev_values[-2]} до {rev_values[-1]}"})
            score += 25

    level = "low"
    if score > 50:
        level = "high"
    elif score > 20:
        level = "medium"

    return {"category": "financial", "score": min(score, 100), "level": level, "findings": findings}
