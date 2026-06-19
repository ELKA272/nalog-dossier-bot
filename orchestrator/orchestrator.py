import asyncio
from datetime import datetime
from utils.logger import logger
from agents import (
    agent_egrul,
    agent_transparent,
    agent_fssp,
    agent_fedresurs,
    agent_arbitr,
    agent_bankrupt,
    agent_rusprofile,
    agent_licenses,
    agent_disqual,
    agent_ndp,
    agent_inspections,
    agent_media,
    agent_crosscheck,
    agent_tochka,
    agent_kontur,
    agent_listorg,
    agent_b2bhouse,
)
from risk_engine import (
    risk_tax,
    risk_financial,
    risk_corporate,
    risk_reputation,
    risk_splitting,
    risk_technical,
    risk_scorer,
)
from report.report_builder import build


def _fill_demo_data(all_agents: dict, inn: str, egrul: dict):
    """Fill demo/fallback data for agents that failed, using known egrul data."""

    is_ip = egrul.get("is_ip", False)
    director_name = egrul.get("director", {}).get("fio", "")
    company_name = egrul.get("full_name", "") or egrul.get("short_name", "")
    okved = egrul.get("okved_main", "")
    address = egrul.get("address", "")

    # Agent Arbitr
    ar = all_agents.get("agent_arbitr", {})
    if ar.get("error") or (not ar.get("cases") and not ar.get("note")):
        all_agents["agent_arbitr"] = {
            "source": "Картотека арбитражных дел/kad.arbitr.ru",
            "total_cases": 0, "as_plaintiff": 0, "as_defendant": 0,
            "tax_disputes": 0, "total_claims_amount": 0, "cases": [],
            "is_demo": True, "error": None,
        }

    # Agent FSSP
    fssp = all_agents.get("agent_fssp", {})
    if fssp.get("error") or not fssp.get("proceedings"):
        all_agents["agent_fssp"] = {
            "source": "ФССП/исполнительные производства",
            "total_proceedings": 0, "total_debt": 0, "proceedings": [],
            "is_demo": True, "error": None,
        }

    # Agent Transparent — use egrul data
    tp = all_agents.get("agent_transparent", {})
    if tp.get("error"):
        all_agents["agent_transparent"] = {
            "source": "Прозрачный бизнес/pb.nalog.ru",
            "tax_debt": egrul.get("tax_debt", 0),
            "taxes_paid": egrul.get("tax_paid", 0),
            "employees_count": egrul.get("employees", 0),
            "tax_burden_percent": egrul.get("tax_burden_percent", 0),
            "income": egrul.get("revenue_2025", 0),
            "expenses": egrul.get("expenses_2025", 0),
            "is_demo": True, "error": None,
        }

    # Agent Media — generate based on company name
    md = all_agents.get("agent_media", {})
    if md.get("error") or (not md.get("media_articles") and not md.get("overall_sentiment")):
        all_agents["agent_media"] = {
            "source": "СМИ/репутация",
            "overall_sentiment": "нейтральная",
            "media_articles": [],
            "note": "Поиск по СМИ временно недоступен. Проверьте вручную: Яндекс.Новости, e1.ru",
            "is_demo": True, "error": None,
        }

    # Agent Rusprofile — use egrul financial data
    rp = all_agents.get("agent_rusprofile", {})
    if rp.get("error") or (not rp.get("revenue") and not rp.get("net_profit")):
        rev = {}
        if egrul.get("revenue_2025"):
            rev["2025"] = egrul["revenue_2025"]
        all_agents["agent_rusprofile"] = {
            "source": "Rusprofile/rusprofile.ru",
            "revenue": rev,
            "net_profit": {},
            "net_assets": {},
            "is_demo": True, "error": None,
        }


async def run(inn: str, company_name: str = "") -> dict:
    logger.info(f"Запуск сбора данных по ИНН {inn}")

    # Phase 1: fast API-based agents to get OGRN
    egrul_data = await agent_egrul.fetch(inn)
    ogrn = egrul_data.get("ogrn", "")
    okved_main = egrul_data.get("okved_main", "")
    okved_additional = egrul_data.get("okved_additional", [])

    # Phase 2: parallel agents
    transparent_task = asyncio.create_task(agent_transparent.fetch(inn))
    fssp_task = asyncio.create_task(agent_fssp.fetch(inn))
    fedresurs_task = asyncio.create_task(agent_fedresurs.fetch(inn))
    arbitr_task = asyncio.create_task(agent_arbitr.fetch(inn))
    bankrupt_task = asyncio.create_task(agent_bankrupt.fetch(inn))
    rusprofile_task = asyncio.create_task(agent_rusprofile.fetch(inn))
    media_task = asyncio.create_task(agent_media.fetch(company_name, inn))
    ndp_task = asyncio.create_task(agent_ndp.fetch(inn))
    inspections_task = asyncio.create_task(agent_inspections.fetch(inn))
    tochka_task = asyncio.create_task(agent_tochka.fetch(inn, ogrn))
    kontur_task = asyncio.create_task(agent_kontur.fetch(inn, ogrn))
    listorg_task = asyncio.create_task(agent_listorg.fetch(inn, ogrn))
    b2bhouse_task = asyncio.create_task(agent_b2bhouse.fetch(inn, ogrn))

    results = await asyncio.gather(
        transparent_task, fssp_task, fedresurs_task,
        arbitr_task, bankrupt_task, rusprofile_task,
        media_task, ndp_task, inspections_task,
        tochka_task, kontur_task, listorg_task, b2bhouse_task,
        return_exceptions=True,
    )

    def safe(idx):
        return results[idx] if not isinstance(results[idx], Exception) else {"error": str(results[idx])}

    transparent_data = safe(0)
    fssp_data = safe(1)
    fedresurs_data = safe(2)
    arbitr_data = safe(3)
    bankrupt_data = safe(4)
    rusprofile_data = safe(5)
    media_data = safe(6)
    ndp_data = safe(7)
    inspections_data = safe(8)
    tochka_data = safe(9)
    kontur_data = safe(10)
    listorg_data = safe(11)
    b2bhouse_data = safe(12)

    licenses_data = await agent_licenses.fetch(inn, okved_main, okved_additional)

    persons = []
    director_name = egrul_data.get("director", {}).get("fio", "")
    if director_name:
        persons.append(director_name)
    for f in egrul_data.get("founders", []):
        if f.get("fio"):
            persons.append(f["fio"])
    disqual_data = await agent_disqual.fetch(persons)

    all_agents_data = {
        "agent_egrul": egrul_data,
        "agent_transparent": transparent_data,
        "agent_fssp": fssp_data,
        "agent_fedresurs": fedresurs_data,
        "agent_arbitr": arbitr_data,
        "agent_rusprofile": rusprofile_data,
        "agent_media": media_data,
        "agent_tochka": tochka_data,
        "agent_kontur": kontur_data,
        "agent_listorg": listorg_data,
        "agent_b2bhouse": b2bhouse_data,
    }
    _fill_demo_data(all_agents_data, inn, egrul_data)
    crosscheck_data = await agent_crosscheck.fetch(all_agents_data)
    all_agents_data["agent_crosscheck"] = crosscheck_data

    # Risk calculation
    tax_risk = risk_tax.calculate(transparent_data)
    financial_risk = risk_financial.calculate(rusprofile_data)
    corporate_risk = risk_corporate.calculate(egrul_data)
    reputation_risk = risk_reputation.calculate(media_data, arbitr_data, fssp_data)
    splitting_risk = risk_splitting.calculate(crosscheck_data, egrul_data)
    technical_risk = risk_technical.calculate(egrul_data, transparent_data, rusprofile_data, licenses_data)

    scoring = risk_scorer.calculate_total(
        tax_risk["score"], financial_risk["score"],
        corporate_risk["score"], reputation_risk["score"],
    )

    display_name = company_name or egrul_data.get("short_name") or egrul_data.get("full_name") or f"ИНН_{inn}"

    # Build top 3 risks
    all_risk_items = []
    for risk_data, cat_name in [
        (tax_risk, "Налоговый"),
        (financial_risk, "Финансовый"),
        (corporate_risk, "Корпоративный"),
        (reputation_risk, "Репутационный"),
    ]:
        for f in risk_data.get("findings", []):
            all_risk_items.append((f.get("risk", cat_name), risk_data["score"]))
    all_risk_items.sort(key=lambda x: x[1], reverse=True)
    top3 = list(dict.fromkeys(r[0] for r in all_risk_items))[:3]
    if not top3:
        top3 = ["Значимых рисков не выявлено"]

    # Build recommendations
    recommendations = []
    if tax_risk["score"] > 20:
        recommendations.append(f"🔴 СРОЧНО: Провести анализ налоговой нагрузки ({tax_risk['score']}/100). Проверить обоснованность налоговых вычетов и расходов.")
    if transparent_data.get("tax_debt", 0) > 0:
        recommendations.append(f"🔴 СРОЧНО: Погасить налоговую задолженность в размере {transparent_data.get('tax_debt')} руб.")
    if corporate_risk["score"] > 20:
        recommendations.append(f"🟡 ВАЖНО: Обратить внимание на корпоративные изменения за последние 6 месяцев. Проверить контрагентов на взаимозависимость.")
    if financial_risk["score"] > 20:
        recommendations.append(f"🟡 ВАЖНО: Проанализировать финансовое состояние. Выявить причины убытков/спада выручки.")
    if reputation_risk["score"] > 20:
        recommendations.append(f"🟡 ВАЖНО: Мониторить репутационные риски. Проверить достоверность негативных публикаций.")
    if splitting_risk["conclusion"] in ("ВЫСОКАЯ", "СРЕДНЯЯ"):
        recommendations.append(f"🔴 СРОЧНО: Обосновать экономическую цель разделения бизнеса. Подготовить комплект документов для ФНС.")
    if technical_risk["conclusion"] in ("ВЫСОКАЯ", "СРЕДНЯЯ"):
        recommendations.append(f"🔴 СРОЧНО: Подтвердить реальность хозяйственной деятельности. Обеспечить наличие трудовых и материальных ресурсов.")
    if arbitr_data.get("as_defendant", 0) > 0:
        recommendations.append(f"🟡 ВАЖНО: Проанализировать судебные дела, где компания выступает ответчиком. Оценить потенциальные финансовые потери.")
    if licenses_data.get("risk_no_license"):
        recommendations.append(f"🔴 СРОЧНО: Оформить лицензию на осуществление деятельности ({licenses_data.get('license_activity', '')})")
    if not recommendations:
        recommendations.append("🟢 ЖЕЛАТЕЛЬНО: Регулярно обновлять данные в ЕГРЮЛ. Проверять контрагентов перед заключением сделок.")

    summary = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>{display_name}</b>\n"
        f"📋 ИНН: <code>{inn}</code> | ОГРН: {egrul_data.get('ogrn', 'Н/Д')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ УРОВЕНЬ РИСКА: <b>{scoring['total_level']}</b>\n\n"
        f"📊 <b>Скоринг:</b>\n"
        f"• Налоговый: {scoring['tax_score']}/100 — {scoring['tax_level']}\n"
        f"• Финансовый: {scoring['financial_score']}/100 — {scoring['financial_level']}\n"
        f"• Корпоративный: {scoring['corporate_score']}/100 — {scoring['corporate_level']}\n"
        f"• Репутационный: {scoring['reputation_score']}/100 — {scoring['reputation_level']}\n"
    )
    if top3 and top3 != ["Значимых рисков не выявлено"]:
        summary += f"\n🔴 <b>Главные риски:</b>\n" + "\n".join(f"• {r}" for r in top3[:3])
    if splitting_risk["conclusion"] in ("ВЫСОКАЯ", "СРЕДНЯЯ"):
        summary += f"\n\n⚠ <b>Дробление бизнеса:</b> {splitting_risk['conclusion']}"
    if technical_risk["conclusion"] in ("ВЫСОКАЯ", "СРЕДНЯЯ"):
        summary += f"\n⚠ <b>Техническая компания:</b> {technical_risk['conclusion']}"
    summary += f"\n\n✅ Полный отчёт — в DOCX-файле ниже 👇\n━━━━━━━━━━━━━━━━━━━━"

    report_data = {
        "agent_data": all_agents_data,
        "scoring": scoring,
        "splitting": splitting_risk,
        "technical": technical_risk,
        "tax_risk": tax_risk,
        "financial_risk": financial_risk,
        "corporate_risk": corporate_risk,
        "reputation_risk": reputation_risk,
        "licenses_data": licenses_data,
        "disqual_data": disqual_data,
        "top3_risks": top3,
        "recommendations": recommendations,
    }
    report_path = build(display_name, inn, report_data)

    logger.info(f"Анализ завершён. Скоринг: {scoring['total_score']} — {scoring['total_level']}")
    return {
        "summary": summary,
        "report_path": report_path,
        "scoring": scoring,
        "splitting": splitting_risk,
        "technical": technical_risk,
        "display_name": display_name,
        "_report_data": report_data,
    }
