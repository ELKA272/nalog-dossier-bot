def calculate_total(
    tax_score: int,
    financial_score: int,
    corporate_score: int,
    reputation_score: int,
) -> dict:
    total = (tax_score * 0.35) + (financial_score * 0.25) + (corporate_score * 0.25) + (reputation_score * 0.15)

    def level(s):
        if s > 50:
            return "ВЫСОКИЙ"
        if s > 20:
            return "СРЕДНИЙ"
        return "НИЗКИЙ"

    return {
        "tax_score": tax_score,
        "tax_level": level(tax_score),
        "financial_score": financial_score,
        "financial_level": level(financial_score),
        "corporate_score": corporate_score,
        "corporate_level": level(corporate_score),
        "reputation_score": reputation_score,
        "reputation_level": level(reputation_score),
        "total_score": round(total, 1),
        "total_level": level(total),
    }
