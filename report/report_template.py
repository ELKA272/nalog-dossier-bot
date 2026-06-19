REPORT_SECTIONS = [
    {
        "number": 1,
        "title": "РЕЗЮМЕ ДЛЯ СОБСТВЕННИКА",
        "fields": ["summary", "total_risk_level", "top3_risks", "key_recommendations"],
    },
    {
        "number": 2,
        "title": "ОБЩАЯ ИНФОРМАЦИЯ",
        "fields": ["inn", "ogrn", "kpp", "full_name", "short_name", "reg_date",
                   "legal_address", "actual_address", "ifns", "tax_regime",
                   "okved_main", "okved_additional", "status", "authorized_capital"],
    },
    {
        "number": 3,
        "title": "РУКОВОДИТЕЛИ И УЧРЕДИТЕЛИ",
        "fields": ["director", "founders", "director_changes", "disqualification"],
    },
    {
        "number": 4,
        "title": "СВЯЗАННЫЕ КОМПАНИИ",
        "fields": ["related_companies"],
    },
    {
        "number": 5,
        "title": "КАРТА СВЯЗЕЙ",
        "fields": ["connections_description", "connection_weights", "splitting_indicators_count"],
    },
    {
        "number": 6,
        "title": "ФИНАНСОВЫЙ АНАЛИЗ",
        "fields": ["financial_table"],
    },
    {
        "number": 7,
        "title": "СУДЕБНЫЕ ДЕЛА",
        "fields": ["total_cases", "as_plaintiff", "as_defendant", "as_third_party",
                   "tax_disputes", "significant_cases"],
    },
    {
        "number": 8,
        "title": "ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА",
        "fields": ["has_proceedings", "total_debt", "proceedings_count", "proceedings_list"],
    },
    {
        "number": 9,
        "title": "ЛИЦЕНЗИИ",
        "fields": ["license_required", "has_license", "license_data", "risk_flag"],
    },
    {
        "number": 10,
        "title": "САЙТ И СОЦИАЛЬНЫЕ СЕТИ",
        "fields": ["website", "social_networks", "sentiment"],
    },
    {
        "number": 11,
        "title": "НАЛОГОВЫЕ РИСКИ",
        "fields": ["tax_score", "tax_level", "tax_findings"],
    },
    {
        "number": 12,
        "title": "ФИНАНСОВЫЕ РИСКИ",
        "fields": ["financial_score", "financial_level", "financial_findings"],
    },
    {
        "number": 13,
        "title": "КОРПОРАТИВНЫЕ РИСКИ",
        "fields": ["corporate_score", "corporate_level", "corporate_findings"],
    },
    {
        "number": 14,
        "title": "РЕПУТАЦИОННЫЕ РИСКИ",
        "fields": ["reputation_score", "reputation_level", "reputation_findings"],
    },
    {
        "number": 15,
        "title": "ВЕРОЯТНЫЕ ПРЕТЕНЗИИ ФНС",
        "fields": ["splitting_conclusion", "technical_conclusion", "nk_articles"],
    },
    {
        "number": 16,
        "title": "РЕКОМЕНДАЦИИ ПО СНИЖЕНИЮ РИСКОВ",
        "fields": ["recommendations"],
    },
    {
        "number": 17,
        "title": "ИСПОЛЬЗОВАННЫЕ ИСТОЧНИКИ",
        "fields": ["sources_list"],
    },
    {
        "number": 18,
        "title": "АНКЕТА ПРОВЕРКИ КОНТРАГЕНТА",
        "fields": [f"field_{i:02d}" for i in range(1, 40)],
    },
]
