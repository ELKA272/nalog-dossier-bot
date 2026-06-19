import re


def parse_input(text: str) -> dict:
    text = text.strip()
    original = text
    cleaned = re.sub(r"[\s\-–—]", "", text)

    if cleaned.isdigit():
        if len(cleaned) == 10:
            return {"type": "inn_ul", "value": cleaned, "original": original}
        if len(cleaned) == 12:
            return {"type": "inn_ip", "value": cleaned, "original": original}
        if len(cleaned) == 13:
            return {"type": "ogrn", "value": cleaned, "original": original}
        if len(cleaned) == 15:
            return {"type": "ogrnip", "value": cleaned, "original": original}

    words = text.split()
    if 2 <= len(words) <= 4 and all(w.isalpha() for w in words):
        return {"type": "fio", "value": text, "original": original}

    if re.search(r"(ООО|АО|ИП|ЗАО|ПАО)", text, re.IGNORECASE):
        return {"type": "name", "value": text, "original": original}

    return {"type": "unknown", "value": text, "original": original}
