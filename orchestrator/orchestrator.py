import asyncio
from datetime import datetime
from utils.logger import logger
from agents import agent_irbis
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


async def run(inn: str, company_name: str = "") -> dict:
    logger.info(f"Запуск сбора данных (irbis) по ИНН {inn}")

    # ── Single call to ir-bis API replaces 12 old agents ──
    agent_data = await agent_irbis.fetch(inn)
    egrul_data = agent_data.get("agent_egrul", {})
    transparent_data = agent_data.get("agent_transparent", {})
    fssp_data = agent_data.get("agent_fssp", {})
    bankrupt_data = agent_data.get("agent_bankrupt", {})
    arbitr_data = agent_data.get("agent_arbitr", {})
    rusprofile_data = agent_data.get("agent_rusprofile", {})
    media_data = agent_data.get("agent_media", {})
    ndp_data = agent_data.get("agent_ndp", {})
    inspections_data = agent_data.get("agent_inspections", {})
    licenses_data = agent_data.get("agent_licenses", {})
    crosscheck_data = agent_data.get("agent_crosscheck", {"connections": []})

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
        debt_val = transparent_data.get("tax_debt", 0)
        recommendations.append(f"🔴 СРОЧНО: Погасить налоговую задолженность в размере {debt_val} руб.")
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
        "agent_data": agent_data,
        "scoring": scoring,
        "splitting": splitting_risk,
        "technical": technical_risk,
        "tax_risk": tax_risk,
        "financial_risk": financial_risk,
        "corporate_risk": corporate_risk,
        "reputation_risk": reputation_risk,
        "licenses_data": licenses_data,
        "disqual_data": {
            "disqualified_persons": [
                {
                    "fio": d.get("fio", d.get("name", "")),
                    "article": d.get("article", d.get("reason", "")),
                    "start_date": d.get("start_date", d.get("date_start", "")),
                    "end_date": d.get("end_date", d.get("date_end", "")),
                }
                for d in (agent_data.get("_irbis_disqualified", []) or [])
                if isinstance(d, dict)
            ],
        },
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
