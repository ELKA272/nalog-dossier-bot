RISKS = [
    "Дробление бизнеса",
    "Необоснованная налоговая выгода",
    "Технические компании",
    "Фиктивный документооборот",
    "Схемы с ИП",
    "Схемы с самозанятыми",
    "Серые выплаты зарплаты",
    "Разрывы НДС",
    "Искусственное снижение налоговой нагрузки",
    "Вывод денежных средств",
]


def calculate(data: dict) -> dict:
    findings = []
    score = 0

    # Check tax burden
    tax_burden = data.get("tax_burden_percent", 100)
    if tax_burden < 1:
        findings.append({"risk": "Искусственное снижение налоговой нагрузки", "confirmed": True, "source": "Прозрачный бизнес", "detail": f"Нагрузка {tax_burden}% < 1%"})
        score += 30

    # Check violations flag
    if data.get("violations_flag"):
        findings.append({"risk": "Необоснованная налоговая выгода", "confirmed": True, "source": "Прозрачный бизнес", "detail": "Флаг нарушений налогового законодательства"})
        score += 25

    # Check tax debt
    tax_debt = data.get("tax_debt", 0)
    if tax_debt > 0:
        findings.append({"risk": "Серые выплаты зарплаты", "confirmed": True, "source": "Прозрачный бизнес", "detail": f"Налоговая задолженность: {tax_debt} руб."})
        score += 15

    # Check expenses vs income ratio
    income = data.get("income", 0)
    expenses = data.get("expenses", 0)
    if income > 0 and expenses > income * 0.95:
        findings.append({"risk": "Вывод денежных средств", "confirmed": True, "source": "Прозрачный бизнес", "detail": f"Расходы ({expenses}) составляют >95% от доходов ({income})"})
        score += 20

    level = "low"
    if score > 50:
        level = "high"
    elif score > 20:
        level = "medium"

    return {"category": "tax", "score": min(score, 100), "level": level, "findings": findings}
