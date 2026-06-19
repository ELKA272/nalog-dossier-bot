def calculate(crosscheck_data: dict, egrul_data: dict) -> dict:
    indicators = []
    count = 0

    # From crosscheck
    connections = crosscheck_data.get("connections", [])
    count += crosscheck_data.get("splitting_indicators_count", 0)

    for conn in connections:
        if conn.get("strength") == "strong":
            count += 2
        else:
            count += 1
        indicators.append(f"{conn.get('type')}: {conn.get('detail')}")

    # Shared address
    if egrul_data.get("mass_address"):
        count += 2
        indicators.append("Массовый адрес (возможность дробления)")

    # Shared director
    if egrul_data.get("mass_director"):
        count += 2
        indicators.append("Массовый директор (признак дробления)")

    if count >= 5:
        conclusion = "ВЫСОКАЯ"
    elif count >= 3:
        conclusion = "СРЕДНЯЯ"
    else:
        conclusion = "НИЗКАЯ"

    return {
        "category": "splitting",
        "indicators_count": count,
        "conclusion": conclusion,
        "indicators": indicators,
        "detail": f"На основании совокупности выявленных признаков вероятность квалификации деятельности группы компаний как дробления бизнеса оценивается как {conclusion}",
    }
