from datetime import datetime


def _s(v):
    return str(v) if v is not None else "—"


def _fmt(val):
    if val is None or val == "" or val == 0:
        return "—"
    if isinstance(val, str):
        val = val.replace(" ", "")
        try:
            v = float(val)
        except ValueError:
            return val
    else:
        v = float(val)
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.2f} млн ₽"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.1f} тыс ₽"
    return _s(v)


def _level_emoji(level):
    lvl = _s(level).upper()
    if "ВЫСОК" in lvl:
        return "🔴"
    if "СРЕДН" in lvl:
        return "🟡"
    return "🟢"


def build_all_messages(company_name: str, inn: str, data: dict) -> list:
    agent = data.get("agent_data", {})
    eg = agent.get("agent_egrul", {})
    tp = agent.get("agent_transparent", {})
    ar = agent.get("agent_arbitr", {})
    fssp = agent.get("agent_fssp", {})
    rp = agent.get("agent_rusprofile", {})
    media = agent.get("agent_media", {})
    cross = agent.get("agent_crosscheck", {})
    sc = data.get("scoring", {})
    splitting = data.get("splitting", {})
    technical = data.get("technical", {})
    lic = data.get("licenses_data", {})
    disqual = data.get("disqual_data", {})
    recs = data.get("recommendations", [])
    director = eg.get("director", {})
    founders = eg.get("founders", [])
    rev = rp.get("revenue", {})
    profit = rp.get("net_profit", {})
    connections = cross.get("connections", [])
    cases = ar.get("cases", [])
    proceedings = fssp.get("proceedings", [])

    msgs = []

    # ─── Message 1: Header + Resume + General ───
    m1 = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>НАЛОГОВОЕ ДОСЬЕ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{company_name}</b>\n"
        f"📋 ИНН: <code>{inn}</code>\n"
        f"📋 ОГРН: <code>{eg.get('ogrn', '—')}</code>\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>1. РЕЗЮМЕ ДЛЯ СОБСТВЕННИКА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Проведён анализ организации <b>{company_name}</b> (ИНН {inn}).\n\n"
        f"<b>Результаты оценки рисков:</b>\n"
        f"{_level_emoji(sc.get('tax_level'))} Налоговый:      {sc.get('tax_score', 0)}/100 ({sc.get('tax_level', '—')})\n"
        f"{_level_emoji(sc.get('financial_level'))} Финансовый:     {sc.get('financial_score', 0)}/100 ({sc.get('financial_level', '—')})\n"
        f"{_level_emoji(sc.get('corporate_level'))} Корпоративный:  {sc.get('corporate_score', 0)}/100 ({sc.get('corporate_level', '—')})\n"
        f"{_level_emoji(sc.get('reputation_level'))} Репутационный:  {sc.get('reputation_score', 0)}/100 ({sc.get('reputation_level', '—')})\n\n"
        f"⚠️ <b>Общий уровень риска:</b> {sc.get('total_level', '—')}\n\n"
        f"🏢 Дробление бизнеса: <b>{splitting.get('conclusion', '—')}</b>\n"
        f"💻 Техническая компания: <b>{technical.get('conclusion', '—')}</b>\n"
    )
    top3 = data.get("top3_risks", [])
    if top3 and top3 != ["Значимых рисков не выявлено"]:
        m1 += f"\n🔴 <b>Главные риски:</b>\n"
        for r in top3[:3]:
            m1 += f"• {r}\n"

    m1 += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>2. ОБЩАЯ ИНФОРМАЦИЯ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 Наименование:     <b>{eg.get('full_name', '—') or eg.get('short_name', '—')}</b>\n"
        f"🔢 ИНН:              <code>{inn}</code>\n"
        f"🔢 ОГРН:             <code>{eg.get('ogrn', '—')}</code>\n"
        f"📅 Регистрация:      {eg.get('reg_date', '—')}\n"
        f"💰 Налоговый режим:  {eg.get('tax_regime', '—')}\n"
        f"📍 Адрес:            {eg.get('address', '—')}\n"
        f"📋 ОКВЭД:            {eg.get('okved_main', '—')}\n"
        f"📊 Статус:           {eg.get('status', '—')}\n"
        f"💰 Уставной капитал: {eg.get('authorized_capital', '—')} ₽\n"
        f"👥 Сотрудников:      {eg.get('employees', '—')}\n"
    )
    msgs.append(m1)

    # ─── Message 2: Management + Related ───
    m2 = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>3. РУКОВОДИТЕЛИ И УЧРЕДИТЕЛИ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Директор:</b> {director.get('fio', '—')}\n"
        f"🔢 ИНН директора: {director.get('inn', '—')}\n"
        f"⛔ Дисквалификация: <b>{'ДА' if disqual.get('has_disqualified') else 'нет'}</b>\n\n"
        f"<b>Учредители:</b>\n"
    )
    if not founders:
        m2 += "— данные отсутствуют\n"
    else:
        for f in founders:
            m2 += f"• {f.get('fio', '—')} (ИНН: {f.get('inn', '—')}) — доля: {f.get('share', '—')}\n"

    # Disqualified persons
    disq_list = disqual.get("disqualified", [])
    if disq_list:
        m2 += f"\n<b>⛔ Дисквалифицированные лица:</b>\n"
        for d in disq_list:
            m2 += f"• {d.get('fio')} — {d.get('reason')}\n"

    m2 += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>4. СВЯЗАННЫЕ КОМПАНИИ И КАРТА СВЯЗЕЙ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    if connections:
        m2 += f"Всего связей: {len(connections)}\n"
        for c in connections:
            weight = c.get("strength", "weak")
            icon = "🔴" if weight == "strong" else ("🟡" if weight == "medium" else "⚪")
            m2 += f"{icon} {c.get('type')}: {c.get('detail')} [{weight}]\n"
        m2 += f"\n📊 Показателей дробления: {cross.get('splitting_indicators_count', 0)}\n"
    else:
        m2 += "Связанные компании не выявлены.\n"
    msgs.append(m2)

    # ─── Message 3: Finance + Court ───
    m3 = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>5. ФИНАНСОВЫЙ АНАЛИЗ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Финансовые показатели:</b>\n"
        f"┌────────────────────┬────────────┐\n"
        f"│ Показатель         │ Значение   │\n"
        f"├────────────────────┼────────────┤\n"
    )
    # Use egrul data as fallback when rusprofile is empty
    has_rp_data = any(rev.get(y) for y in ("2022", "2023", "2024"))
    if has_rp_data:
        m3 += (
            f"│ Выручка 2022       │ {_fmt(rev.get('2022', 0)):>10} │\n"
            f"│ Выручка 2023       │ {_fmt(rev.get('2023', 0)):>10} │\n"
            f"│ Выручка 2024       │ {_fmt(rev.get('2024', 0)):>10} │\n"
            f"│ Прибыль 2022       │ {_fmt(profit.get('2022', 0)):>10} │\n"
            f"│ Прибыль 2023       │ {_fmt(profit.get('2023', 0)):>10} │\n"
            f"│ Прибыль 2024       │ {_fmt(profit.get('2024', 0)):>10} │\n"
        )
    else:
        eg_rev = eg.get("revenue_2025", "")
        eg_profit = eg.get("profit_2025", "")
        m3 += (
            f"│ Выручка 2025       │ {eg_rev if eg_rev else '—':>10} │\n"
            f"│ Прибыль 2025       │ {eg_profit if eg_profit else '—':>10} │\n"
        )
    m3 += (
        f"│ Сотрудников        │ {_s(tp.get('employees_count') or eg.get('employees')):>10} │\n"
        f"│ Налоговая нагрузка │ {tp.get('tax_burden_percent') or eg.get('tax_burden_percent', '—'):>10}% │\n"
        f"└────────────────────┴────────────┘\n\n"
        f"💰 Налоги уплачено: {_fmt(tp.get('taxes_paid') or eg.get('tax_paid', 0))}\n"
        f"💰 Доходы: {_fmt(tp.get('income') or eg.get('revenue_2025', 0))}\n"
        f"💰 Расходы: {_fmt(tp.get('expenses') or eg.get('expenses_2025', 0))}\n"
        f"⚠️ Налоговая задолженность: {_fmt(tp.get('tax_debt') or eg.get('tax_debt', 0))}\n"
    )

    m3 += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>6. СУДЕБНЫЕ ДЕЛА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Всего дел: {ar.get('total_cases', 0)}\n"
        f"⚖️ Как истец: {ar.get('as_plaintiff', 0)}\n"
        f"🔴 Как ответчик: {ar.get('as_defendant', 0)} ⬅️ <b>особое внимание</b>\n"
        f"⚖️ Налоговые споры: {ar.get('tax_disputes', 0)}\n"
        f"💰 Общая сумма исков: {_fmt(ar.get('total_claims_amount', 0))}\n\n"
    )
    if cases:
        for c in cases[:10]:
            role = c.get("role", "")
            role_mark = "🔴 ОТВЕТЧИК" if role == "defendant" else ("⚪ истец" if role == "plaintiff" else "⚪ 3-е лицо")
            m3 += f"• №{c.get('number', '—')} от {c.get('date', '—')}\n  {role_mark} | сумма: {_fmt(c.get('amount', 0))} | {c.get('subject', '')[:50]}\n"
    else:
        m3 += "Судебные дела не найдены.\n"
    msgs.append(m3)

    # ─── Message 4: Enforcement + Licenses + Risks ───
    m4 = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>7. ИСПОЛНИТЕЛЬНЫЕ ПРОИЗВОДСТВА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Наличие: <b>{'ДА' if fssp.get('has_proceedings') else 'нет'}</b>\n"
    )
    if proceedings:
        m4 += f"Общая задолженность: {_fmt(fssp.get('total_debt', 0))}\n"
        for p in proceedings[:10]:
            m4 += f"• №{p.get('number', '—')} — {_fmt(p.get('amount', 0))} — {p.get('subject', '—')} — {p.get('status', '—')}\n"
    else:
        m4 += "Исполнительные производства не найдены.\n"

    m4 += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>8. ЛИЦЕНЗИИ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Требуется лицензия: <b>{'да' if lic.get('license_required') else 'нет'}</b>\n"
    )
    if lic.get("license_required"):
        m4 += f"Вид деятельности: {lic.get('license_activity', '—')}\n"
        m4 += f"Наличие лицензии: <b>{'да' if lic.get('has_license') else 'нет'}</b>\n"
        if lic.get("risk_no_license") and not lic.get("has_license"):
            m4 += f"\n<b>⚠️ РИСК: лицензируемая деятельность без лицензии!</b>\n"
    else:
        m4 += "Данные о лицензиях отсутствуют.\n"

    # Media / Reputation
    m4 += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>10. САЙТ И СОЦИАЛЬНЫЕ СЕТИ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Сайт: {rp.get('website', 'не обнаружен')}\n"
        f"Соцсети: не обнаружены\n"
        f"Тональность: {media.get('overall_sentiment', 'не определена')}\n"
    )
    articles = media.get("media_articles", [])
    if articles:
        m4 += f"\nПубликаций в СМИ: {len(articles)}\n"
        for a in articles[:5]:
            emoji = "🔴" if a.get("sentiment") == "negative" else "⚪"
            m4 += f"{emoji} {a.get('title', '')[:80]}\n"

    # Parser-API sources
    pa = agent.get("agent_parserapi", {})
    if pa.get("api"):
        m4 += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n<b>📡 ДАННЫЕ PARSER-API</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        pa_arbitr = pa.get("arbitr", {})
        if pa_arbitr.get("total_cases"):
            m4 += f"⚖️ Арбитраж: {pa_arbitr.get('total_cases', 0)} дел\n"
        pa_fssp = pa.get("fssp", {})
        if pa_fssp.get("total_proceedings"):
            m4 += f"🔨 ФССП: {pa_fssp.get('total_proceedings', 0)} производств"
            if pa_fssp.get("total_debt"):
                m4 += f", долг {_fmt(pa_fssp['total_debt'])}"
            m4 += "\n"
        pa_fedr = pa.get("fedresurs", {})
        if pa_fedr.get("total_bankrupt"):
            m4 += f"📋 Федресурс: {pa_fedr.get('total_bankrupt', 0)} записей о банкротстве\n"
        pa_nalog = pa.get("nalog_pb", {})
        if pa_nalog.get("restrictions"):
            m4 += f"⛔ ФНС: {len(pa_nalog['restrictions'])} ограничений на руководителя\n"
        if pa_nalog.get("disqualified"):
            m4 += f"⛔ ФНС: {len(pa_nalog['disqualified'])} дисквалификаций\n"

    # Additional sources
    tc = agent.get("agent_tochka", {})
    kt = agent.get("agent_kontur", {})
    lo = agent.get("agent_listorg", {})
    bh = agent.get("agent_b2bhouse", {})

    m4 += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n<b>ДОПОЛНИТЕЛЬНЫЕ ИСТОЧНИКИ</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    if not tc.get("error"):
        m4 += f"\n✅ <b>Точка (check.tochka.com):</b>\n"
        m4 += f"• Название: {tc.get('company_name', '—')}\n"
        m4 += f"• ОГРН: {tc.get('ogrn', '—')}\n"
        m4 += f"• Статус: {tc.get('status', '—')}\n"
        m4 += f"• Адрес: {tc.get('address', '—')}\n"
        m4 += f"• Директор: {tc.get('director', '—')}\n"
        if tc.get("revenue"): m4 += f"• Выручка: {tc['revenue'][:60]}\n"
        if tc.get("profit"): m4 += f"• Прибыль: {tc['profit'][:60]}\n"
    else:
        m4 += f"\n❌ Точка: недоступен\n"

    if not kt.get("error"):
        m4 += f"\n✅ <b>Контур Фокус (focus.kontur.ru):</b>\n"
        m4 += f"• ОГРН: {kt.get('ogrn', '—')}\n"
        m4 += f"• Статус: {kt.get('status', '—')}\n"
        m4 += f"• Директор: {kt.get('director', '—')}\n"
        if kt.get("revenue"): m4 += f"• Выручка: {kt['revenue'][:60]}\n"
        if kt.get("court_cases"): m4 += f"• Судебных дел: {kt['court_cases']}\n"
        if kt.get("enforcement"): m4 += f"• Исп. производств: {kt['enforcement']}\n"
    else:
        m4 += f"\n❌ Контур Фокус: недоступен\n"

    if not lo.get("error"):
        m4 += f"\n✅ <b>List-Org (list-org.com):</b>\n"
        m4 += f"• Название: {lo.get('company_name', '—')}\n"
        m4 += f"• ОГРН: {lo.get('ogrn', '—')}\n"
        m4 += f"• Адрес: {lo.get('address', '—')}\n"
        m4 += f"• Директор: {lo.get('director', '—')}\n"
        m4 += f"• ОКВЭД: {lo.get('okved', '—')}\n"
        m4 += f"• Статус: {lo.get('status', '—')}\n"
    else:
        m4 += f"\n❌ List-Org: недоступен\n"

    if not bh.get("error"):
        m4 += f"\n✅ <b>B2B House (b2b.house):</b>\n"
        m4 += f"• Название: {bh.get('company_name', '—')}\n"
        m4 += f"• ОГРН: {bh.get('ogrn', '—')}\n"
        m4 += f"• Директор: {bh.get('director', '—')}\n"
        if bh.get("revenue"): m4 += f"• Выручка: {bh['revenue'][:60]}\n"
        if bh.get("profit"): m4 += f"• Прибыль: {bh['profit'][:60]}\n"
        if bh.get("category"): m4 += f"• Отрасль: {bh['category']}\n"
    else:
        m4 += f"\n❌ B2B House: недоступен\n"

    msgs.append(m4)

    # ─── Message 5: Risks Table + FNS Claims + Recommendations + Sources ───
    m5 = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>9. ОЦЕНКА РИСКОВ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"┌────────────────────┬────────┬──────────┐\n"
        f"│ Вид риска          │ Оценка │ Уровень  │\n"
        f"├────────────────────┼────────┼──────────┤\n"
        f"│ {_level_emoji(sc.get('tax_level'))} Налоговый      │ {sc.get('tax_score', 0):>4}/100 │ {sc.get('tax_level', '—'):>8} │\n"
        f"│ {_level_emoji(sc.get('financial_level'))} Финансовый     │ {sc.get('financial_score', 0):>4}/100 │ {sc.get('financial_level', '—'):>8} │\n"
        f"│ {_level_emoji(sc.get('corporate_level'))} Корпоративный  │ {sc.get('corporate_score', 0):>4}/100 │ {sc.get('corporate_level', '—'):>8} │\n"
        f"│ {_level_emoji(sc.get('reputation_level'))} Репутационный  │ {sc.get('reputation_score', 0):>4}/100 │ {sc.get('reputation_level', '—'):>8} │\n"
        f"└────────────────────┴────────┴──────────┘\n\n"
        f"<b>Дробление бизнеса:</b> {splitting.get('conclusion', '—')}\n"
        f"<b>Техническая компания:</b> {technical.get('conclusion', '—')}\n\n"
    )

    # Splitting indicators
    if splitting.get("indicators"):
        m5 += f"<b>Признаки дробления:</b>\n"
        for ind in splitting["indicators"][:10]:
            m5 += f"• {ind}\n"

    # Technical indicators
    if technical.get("indicators"):
        m5 += f"\n<b>Признаки технической компании:</b>\n"
        for ind in technical["indicators"][:10]:
            m5 += f"• {ind}\n"

    m5 += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>11. ВЕРОЯТНЫЕ ПРЕТЕНЗИИ ФНС</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"На основании выявленных факторов:\n"
    )
    tax_s = sc.get("tax_score", 0)
    corp_s = sc.get("corporate_score", 0)
    spl_conc = splitting.get("conclusion", "")
    tech_conc = technical.get("conclusion", "")
    has_claim = False
    if tax_s >= 50:
        m5 += f"• Высокий налоговый риск — возможны претензии по необоснованной налоговой выгоде (ст. 54.1 НК РФ)\n"
        has_claim = True
    if corp_s >= 50:
        m5 += f"• Высокий корпоративный риск — возможна инициация налоговой проверки\n"
        has_claim = True
    if spl_conc == "ВЫСОКАЯ":
        m5 += f"• Высокая вероятность дробления бизнеса — возможны претензии по ст. 54.1 НК РФ\n"
        has_claim = True
    if tech_conc == "ВЫСОКАЯ":
        m5 += f"• Компания имеет признаки технической — возможно доначисление налогов\n"
        has_claim = True
    if not has_claim:
        m5 += f"• Существенных предпосылок для претензий ФНС не выявлено.\n"

    m5 += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>12. РЕКОМЕНДАЦИИ ПО СНИЖЕНИЮ РИСКОВ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    if recs:
        for r in recs:
            m5 += f"{r}\n"
    else:
        m5 += "• Существенных рисков не выявлено. Рекомендуется регулярный мониторинг.\n"

    m5 += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>13. ИСПОЛЬЗОВАННЫЕ ИСТОЧНИКИ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    for name, src_data in agent.items():
        err = src_data.get("error")
        status = "✅" if not err else "❌"
        m5 += f"{status} {src_data.get('source', name)}\n"
    m5 += f"\n📅 Дата проверки: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"

    msgs.append(m5)

    return msgs
