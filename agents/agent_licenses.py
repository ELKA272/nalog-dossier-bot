from utils.logger import logger


# Simplified license check based on OKVED codes
LICENSED_OKVED_PREFIXES = {
    "86": "Медицинская деятельность",
    "85": "Образовательная деятельность",
    "46.71": "Алкоголь",
    "47.11": "Розничная торговля алкоголем",
    "47.25": "Алкоголь",
    "49": "Перевозки",
    "50": "Перевозки",
    "51": "Перевозки",
    "52.21": "Деятельность такси",
    "80": "Частная охрана",
    "84.25": "Противопожарная безопасность",
    "91": "Фармацевтика",
    "20": "Химическое производство",
}


async def fetch(inn: str, okved_main: str = "", okved_additional: list = None) -> dict:
    if okved_additional is None:
        okved_additional = []

    all_okved = [okved_main] + (okved_additional or [])
    license_required = False
    required_activity = ""

    for okved in all_okved:
        for prefix, activity in LICENSED_OKVED_PREFIXES.items():
            if okved.startswith(prefix):
                license_required = True
                required_activity = activity
                break

    return {
        "source": "Реестры лицензий",
        "license_required": license_required,
        "has_license": False,
        "licenses": [],
        "risk_no_license": license_required,
        "license_activity": required_activity if license_required else "",
        "error": None,
    }
