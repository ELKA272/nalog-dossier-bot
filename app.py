import sys, os, asyncio, json, sqlite3, hashlib, pandas as pd, streamlit as st
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.styles import get_css
from agents import agent_ai_summary, agent_ai_qa

try:
    import altair as alt
except ImportError:
    os.system("pip3 install altair -q")
    import altair as alt

# ── Cache ──
_CACHE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cache.db")
os.makedirs(os.path.dirname(_CACHE_DB), exist_ok=True)

def _init_cache():
    with sqlite3.connect(_CACHE_DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, data TEXT, expires REAL)")

def _cache_get(key: str) -> dict | None:
    _init_cache()
    with sqlite3.connect(_CACHE_DB) as c:
        row = c.execute("SELECT data, expires FROM cache WHERE key=?", (key,)).fetchone()
        if row and row[1] > datetime.now().timestamp():
            return json.loads(row[0])
    return None

def _cache_set(key: str, data: dict, ttl_hours=24):
    _init_cache()
    with sqlite3.connect(_CACHE_DB) as c:
        c.execute("INSERT OR REPLACE INTO cache (key, data, expires) VALUES (?, ?, ?)",
                  (key, json.dumps(data, default=str), (datetime.now() + timedelta(hours=ttl_hours)).timestamp()))

def _cache_clear():
    _init_cache()
    with sqlite3.connect(_CACHE_DB) as c:
        c.execute("DELETE FROM cache WHERE expires < ?", (datetime.now().timestamp(),))
        c.execute("VACUUM")

# ── Helpers ──
def _indicator(data, label_true="✅ Есть данные", label_false="⏳ Данные загружаются"):
    """Show a small colored indicator for data readiness."""
    if data:
        st.success(label_true, icon="✅")
    else:
        st.info(label_false, icon="⏳")

st.set_page_config(page_title="Налоговое досье", page_icon="🏢", layout="wide")

# ── Session state ──
if "section" not in st.session_state: st.session_state.section = "resume"
if "result" not in st.session_state:
    st.session_state.result = None
    st.session_state.analyzed_inn = ""
if "ai_summary" not in st.session_state: st.session_state.ai_summary = ""
if "ai_loading" not in st.session_state: st.session_state.ai_loading = False
if "ai_mode" not in st.session_state: st.session_state.ai_mode = "brief"
if "ai_qa_answer" not in st.session_state: st.session_state.ai_qa_answer = ""

# ── Dynamic CSS ──
st.markdown(get_css("light"), unsafe_allow_html=True)
st.markdown('<div class="animated-bg"></div>', unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown('<div class="sidebar-header">', unsafe_allow_html=True)
    st.title("🏢 Налоговое досье")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")

    inn = st.text_input("Введите ИНН:", max_chars=12, placeholder="6670409336",
                        help="10 цифр — ЮЛ, 12 цифр — ИП")
    run_btn = st.button("🔍 Анализировать", type="primary", use_container_width=True)

    menu_items = [
        # ═══ Основные ═══
        ("📊 Резюме", "resume"),
        ("📋 Общая информация", "general"),
        ("👤 Руководители / учредители", "management"),
        ("🔗 Связи / граф", "connections"),
        ("💰 Финансовый анализ", "finance"),
        # ═══ Суды и долги ═══
        ("⚖️ Арбитраж", "court"),
        ("⚖️ Суды ОЮ", "judge_common"),
        ("🔨 ФССП", "fssp"),
        ("📋 Банкротства", "bankrupt"),
        ("⚡ Намерения о банкротстве", "bankruptcy_intention"),
        # ═══ Налоги / ФНС ═══
        ("💸 Налоговые долги", "nalog_debt"),
        ("🛡️ Приостановления по счетам", "arrest"),
        ("🏢 Поддержка МСП", "msp"),
        # ═══ Контракты / Закупки ═══
        ("🏛️ Госконтракты", "goscon"),
        ("⚫ НДП / РНП", "ndp"),
        # ═══ Имущество / Активы ═══
        ("🔐 Залоги", "pledge"),
        ("🏷️ Товарные знаки", "trademarks"),
        ("📦 Лизинг", "leasing"),
        ("🏠 Недвижимость / Кадастр", "real_estate"),
        # ═══ Регуляторы / Надзор ═══
        ("🔍 Проверки КНМ", "inspections"),
        ("🪪 Лицензии", "licenses"),
        ("📄 Декларации Роструда", "rostud"),
        ("🏭 РАФП", "rafp"),
        ("📋 Документы гос.регистрации", "pb"),
        # ═══ Реестры ═══
        ("⚠️ Санкции", "sanctions"),
        ("👽 Иноагенты", "foreign_agent"),
        ("💣 Террористы / Экстремисты", "terrorist"),
        ("👤 Реестр дисквалифицированных", "disqualified"),
        ("👮 Реестр коррупционеров", "corruption"),
        ("🏦 ЦБ РФ чёрный список", "cbr_wl"),
        ("🛡️ Обеспечительные меры", "rom"),
        ("⚖️ Субсидиарная ответственность", "subsidiary"),
        ("📜 Наследственные дела", "inheritance"),
        ("👤 Самозанятые", "self_employed"),
        ("👥 Болельщики (запрет)", "banned_fans"),
        # ═══ Розыск / Проверки ФЛ ═══
        ("🚔 Розыск МВД", "mvd"),
        ("🔒 Розыск ФСИН", "fsin"),
        ("👤 Контролируемые лица", "controlled"),
        ("🚗 Водительское удостоверение", "driver_license"),
        ("🛂 Паспорт", "passport"),
        ("🧠 ML-индекс", "ml_index"),
        ("🗣️ Популярность ФИО", "popularity"),
        # ═══ Инфраструктура ═══
        ("📞 Контакты", "contact"),
        ("📋 Раскрытие информации", "disclosure"),
        ("📊 ФСГС (статистика)", "fsgs"),
        ("🏛️ Адрес (ОКАТО)", "address_okato"),
        ("📋 История изменений ЕГРЮЛ", "history"),
        # ═══ Прочее ═══
        ("📰 СМИ / Репутация", "media"),
        ("⚠️ Риски", "risks"),
        ("📄 Отчёт DOCX", "report"),
    ]
    menu_keys = [m[1] for m in menu_items]

    st.markdown("---")
    if st.session_state.analyzed_inn:
        st.caption(f"Текущий: {st.session_state.analyzed_inn}")

    if run_btn and inn:
        with st.spinner("Сбор данных из открытых источников... Это может занять до 2 минут"):
            cache_key = hashlib.md5(f"inn_{inn}".encode()).hexdigest()
            cached = _cache_get(cache_key)
            if cached:
                st.session_state.result = cached
                st.success(f"✅ Данные по ИНН {inn} загружены из кэша")
            else:
                from orchestrator.orchestrator import run
                st.session_state.result = asyncio.run(run(inn))
                _cache_set(cache_key, st.session_state.result)
                _cache_clear()
            st.session_state.analyzed_inn = inn
            st.session_state.ai_summary = ""
            st.session_state.ai_loading = False
            st.session_state.ai_qa_answer = ""
        st.session_state.section = "resume"
        st.rerun()
    elif run_btn and not inn:
        st.warning("Введите ИНН")

    st.markdown("---")
    for i, (label, key) in enumerate(menu_items):
        active = st.session_state.section == key
        if st.button(label, key=f"nav_{i}", use_container_width=True,
                     type="primary" if active else "secondary"):
            st.session_state.section = key
            st.rerun()

    st.markdown("---")

# ── Main area ──
result = st.session_state.result
if result is None:
    st.markdown("""
    <div class="hero-section animate-in">
        <div class="hero-icon">🏢</div>
        <div class="hero-title animate-in animate-in-1">Налоговое досье контрагента</div>
        <div class="hero-subtitle animate-in animate-in-2">
            Введите ИНН организации в боковой панели и нажмите «Анализировать»
        </div>
        <div class="hero-sources animate-in animate-in-3">
            Сбор данных из 15+ источников: ЕГРЮЛ, ФНС, ФССП, КАД Арбитраж, Федресурс, СМИ и др.
        </div>
        <div class="hero-disclaimer animate-in animate-in-4">
            ТОЛЬКО ДЛЯ ЛИЧНОГО ПОЛЬЗОВАНИЯ<br>
            <span class="hero-disclaimer-company">ООО "КЛЮЧ КОММЕРЦИИ"</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

rd = result.get("_report_data", {})
ad = rd.get("agent_data", {})
eg = ad.get("agent_egrul", {})
display_name = result.get("display_name", f"ИНН {st.session_state.analyzed_inn}")
analyzed_inn = st.session_state.analyzed_inn

def pb_url(inn_val: str = "") -> str:
    return f"https://pb.nalog.ru/search.html?queryAll={inn_val}"

def _s(v):
    return str(v) if v is not None and v != "" else "—"

def _fmt(val):
    if val is None or val == "" or val == 0: return "—"
    if isinstance(val, str):
        val = val.replace(" ", "")
        try: v = float(val)
        except ValueError: return val
    elif isinstance(val, (int, float)):
        v = float(val)
    else:
        return str(val)
    if abs(v) >= 1_000_000: return f"{v/1_000_000:.2f} млн"
    if abs(v) >= 1_000: return f"{v/1_000:.1f} тыс"
    return f"{v:.0f}"

def level_badge(level):
    lvl = _s(level).upper()
    if "ВЫСОК" in lvl: return '<span class="badge badge-red">ВЫСОКИЙ</span>'
    if "СРЕДН" in lvl: return '<span class="badge badge-yellow">СРЕДНИЙ</span>'
    return '<span class="badge badge-green">НИЗКИЙ</span>'

section = st.session_state.section
active_label = [m[0] for m in menu_items if m[1] == section][0]

# ══════════════════════════════════════════════════════════
# RESUME
# ══════════════════════════════════════════════════════════
if section == "resume":
    sc = result.get("scoring", {})
    sp = result.get("splitting", {})
    tc = result.get("technical", {})
    score = sc.get("total_score", 0)
    level = sc.get("total_level", "—")

    score_color = "#059669" if level == "НИЗКИЙ" else ("#d97706" if level == "СРЕДНИЙ" else "#dc2626")
    score_bg = "#ecfdf5" if level == "НИЗКИЙ" else ("#fffbeb" if level == "СРЕДНИЙ" else "#fef2f2")

    st.markdown(f"""
    <div class="card animate-in" style="border-left:6px solid {score_color};background:{score_bg};">
        <div class="score-wrap">
            <div class="score-circle pulse-glow" style="background:{score_color};">
                <span class="num">{score}</span>
                <span class="lbl">/ 100</span>
            </div>
            <div>
                <div style="font-size:1.5rem;font-weight:700;color:{score_color};">{level}</div>
                <div style="color:var(--text-secondary);font-size:0.85rem;">Общий уровень риска • {display_name}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="risk-grid">', unsafe_allow_html=True)
    risk_items = [
        ("Налоговый", sc.get("tax_score", 0), sc.get("tax_level", "—")),
        ("Финансовый", sc.get("financial_score", 0), sc.get("financial_level", "—")),
        ("Корпоративный", sc.get("corporate_score", 0), sc.get("corporate_level", "—")),
        ("Репутационный", sc.get("reputation_score", 0), sc.get("reputation_level", "—")),
    ]
    for name, s, lvl in risk_items:
        c = "#059669" if s <= 20 else ("#d97706" if s <= 50 else "#dc2626")
        st.markdown(f"""
        <div class="risk-box">
            <div class="val" style="color:{c};">{s}</div>
            <div class="lbl">{name}</div>
            <div>{level_badge(lvl)}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        conc = sp.get("conclusion", "—")
        c = "#059669" if conc == "НИЗКАЯ" else ("#d97706" if conc == "СРЕДНЯЯ" else "#dc2626")
        st.markdown(f"""
        <div class="card card-{'green' if conc=='НИЗКАЯ' else ('orange' if conc=='СРЕДНЯЯ' else 'red')}">
            <b>Дробление бизнеса</b><br>
            <span style="font-size:1.2rem;font-weight:600;color:{c};">{conc}</span>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        conc = tc.get("conclusion", "—")
        c = "#059669" if conc == "НИЗКАЯ" else ("#d97706" if conc == "СРЕДНЯЯ" else "#dc2626")
        st.markdown(f"""
        <div class="card card-{'green' if conc=='НИЗКАЯ' else ('orange' if conc=='СРЕДНЯЯ' else 'red')}">
            <b>Техническая компания</b><br>
            <span style="font-size:1.2rem;font-weight:600;color:{c};">{conc}</span>
        </div>
        """, unsafe_allow_html=True)

    if rd.get("recommendations"):
        st.markdown('<div class="section-title">📌 Рекомендации</div>', unsafe_allow_html=True)
        for r in rd.get("recommendations", []):
            st.markdown(f'<div class="card card-gray" style="padding:0.75rem 1rem;">{r}</div>', unsafe_allow_html=True)

    # Top risks
    top3 = rd.get("top3_risks", [])
    if top3 and top3 != ["Значимых рисков не выявлено"]:
        st.markdown('<div class="section-title">🔴 Главные риски</div>', unsafe_allow_html=True)
        for r in top3[:3]:
            st.markdown(f'<div class="card card-red" style="padding:0.75rem 1rem;">⚠️ {r}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="card" style="text-align:center;background:#eff6ff;"><a href="{pb_url(analyzed_inn)}" target="_blank">🔍 Открыть на pb.nalog.ru</a></div>', unsafe_allow_html=True)

    # ── AI Summary ──
    st.markdown("---")
    st.markdown('<div class="section-title">🧠 AI-анализ контрагента</div>', unsafe_allow_html=True)

    mode_map = {"Кратко": "brief", "Детально": "detailed", "Сравнение": "compare"}
    mode_labels = list(mode_map.keys())
    mode_default_idx = mode_labels.index("Кратко")
    chosen = st.selectbox("Режим анализа:", mode_labels, index=mode_default_idx, key="ai_mode_sel")
    ai_mode = mode_map[chosen]

    col_gen, col_status = st.columns([1, 3])
    with col_gen:
        if st.button("🤖 Сгенерировать", type="primary", use_container_width=True, disabled=st.session_state.ai_loading):
            st.session_state.ai_mode = ai_mode
            st.session_state.ai_summary = ""
            st.session_state.ai_qa_answer = ""
            st.session_state.ai_loading = True
            st.rerun()
    with col_status:
        if st.session_state.ai_loading:
            st.caption("⏳ Генерация...")

    if st.session_state.ai_loading and not st.session_state.ai_summary:
        with st.spinner("Генерируем AI-резюме..."):
            ai_result = asyncio.run(agent_ai_summary.fetch(rd, mode=st.session_state.ai_mode))
            st.session_state.ai_summary = ai_result.get("summary", "❌ Ошибка генерации")
            st.session_state.ai_loading = False
            st.rerun()

    if st.session_state.ai_summary:
        st.markdown(f'<div class="card" style="border-left:6px solid var(--accent);background:var(--accent-light);"><span style="font-size:0.95rem;line-height:1.6;">{st.session_state.ai_summary}</span></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### ❓ Задать вопрос о контрагенте")
        qa_q = st.text_input("Введите вопрос:", placeholder="Например: есть ли налоговые долги? сколько судов?")
        if st.button("Спросить", key="qa_btn", type="primary"):
            if qa_q.strip():
                with st.spinner("Думаю..."):
                    qa_result = asyncio.run(agent_ai_qa.fetch(rd, qa_q))
                    st.session_state.ai_qa_answer = qa_result.get("answer", "❌ Ошибка")
                st.rerun()

        if st.session_state.ai_qa_answer:
            st.markdown(f'<div class="card" style="border-left:6px solid #8b5cf6;background:#f5f3ff;"><span style="font-size:0.95rem;line-height:1.6;">{st.session_state.ai_qa_answer}</span></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# GENERAL
# ══════════════════════════════════════════════════════════
elif section == "general":
    st.markdown('<div class="section-title">🏢 Общая информация</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="card"><b>Полное наименование</b><br>{eg.get("full_name") or eg.get("short_name", "—")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><b>ИНН</b><br><code>{analyzed_inn}</code></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><b>ОГРН</b><br><code>{eg.get("ogrn", "—")}</code></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><b>КПП</b><br>{eg.get("kpp", "—")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><b>Статус</b><br>{eg.get("status", "—")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><b>Дата регистрации</b><br>{eg.get("reg_date", "—")}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="card"><b>Налоговый режим</b><br>{eg.get("tax_regime", "—")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><b>ОКВЭД</b><br>{eg.get("okved_main", "—")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><b>Юридический адрес</b><br>{eg.get("address", "—")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><b>Сотрудники</b><br>{eg.get("employees", "—")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><b>Уставной капитал</b><br>{_fmt(eg.get("authorized_capital", 0))} ₽</div>', unsafe_allow_html=True)
        ifns = eg.get("ifns", "")
        st.markdown(f'<div class="card"><b>ИФНС</b><br>{ifns if ifns else "—"}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card" style="text-align:center;background:#eff6ff;"><a href="{pb_url(analyzed_inn)}" target="_blank">🔍 Открыть на pb.nalog.ru</a></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# MANAGEMENT
# ══════════════════════════════════════════════════════════
elif section == "management":
    st.markdown('<div class="section-title">👤 Руководители и учредители</div>', unsafe_allow_html=True)

    director = eg.get("director", {})
    dir_fio = director.get('fio', '—')
    dir_inn = director.get('inn', '')

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="card"><b>Генеральный директор</b><br>{dir_fio}</div>', unsafe_allow_html=True)
        if dir_inn:
            st.markdown(f'<div class="card"><b>ИНН директора</b><br><code>{dir_inn}</code></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card" style="text-align:center;background:#eff6ff;"><a href="{pb_url(dir_inn)}" target="_blank">🔍 Проверить директора</a></div>', unsafe_allow_html=True)

    with col2:
        founders = eg.get("founders", [])
        if founders:
            for f in founders:
                fio = f.get('fio', '—')
                finn = f.get('inn', '')
                share = f.get('share', '')
                extra = f'<br><a href="{pb_url(finn)}" target="_blank">🔍 Проверить</a>' if finn else ''
                st.markdown(f'<div class="card"><b>Учредитель</b><br>{fio}{" ("+share+")" if share else ""}{extra}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card card-gray">Данные об учредителях не найдены</div>', unsafe_allow_html=True)

    disqual = rd.get("disqual_data", {})
    if disqual.get("disqualified_persons") or disqual.get("disqualified"):
        st.markdown('<div class="card card-red"><b>⛔ Дисквалифицированные лица</b></div>', unsafe_allow_html=True)
        for d in disqual.get("disqualified_persons", disqual.get("disqualified", [])):
            st.markdown(f'<div class="card card-red" style="padding:0.75rem 1rem;">{d.get("fio", "—")} — {d.get("article", d.get("reason", "—"))} ({d.get("start_date", "")} — {d.get("end_date", "")})</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# CONNECTIONS
# ══════════════════════════════════════════════════════════
elif section == "connections":
    st.markdown('<div class="section-title">🔗 Связанные компании и карта связей</div>', unsafe_allow_html=True)
    cc = ad.get("agent_crosscheck", {})
    conns = cc.get("connections", [])

    if conns:
        st.markdown("""
        <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1rem;font-size:13px;">
            <span><span style="color:#dc2626;">●</span> <b>высокая</b> — высокая вероятность дробления</span>
            <span><span style="color:#d97706;">●</span> <b>средняя</b> — стандартная ситуация</span>
            <span><span style="color:#9ca3af;">●</span> <b>низкая</b> — информационно</span>
        </div>
        """, unsafe_allow_html=True)

        for c in conns:
            strength = c.get("strength", "weak")
            cls = {"strong": "conn-strong", "medium": "conn-medium", "weak": "conn-weak"}.get(strength, "conn-weak")
            icon = {"strong": "🔴", "medium": "🟡", "weak": "⚪"}.get(strength, "⚪")
            person_inn = c.get("person_inn", "")
            detail = c.get("detail", "")
            if person_inn:
                detail += f' <a href="{pb_url(person_inn)}" target="_blank">🔍</a>'
            st.markdown(f'<div class="conn-card {cls}"><b>{icon} {c.get("type", "")}</b><br>{detail}</div>', unsafe_allow_html=True)

        st.markdown("---")
        def _wrap_label(text, maxlen=22):
            if len(text) <= maxlen:
                return text
            mid = len(text) // 2
            left = text.rfind(' ', 0, mid)
            right = text.find(' ', mid)
            if left > 0 and (right < 0 or mid - left <= right - mid):
                return text[:left] + '\n' + text[left+1:]
            elif right > 0:
                return text[:right] + '\n' + text[right+1:]
            return text[:mid] + '\n' + text[mid:]

        st.markdown('<div class="section-title">📊 Граф связей</div>', unsafe_allow_html=True)
        sl_map = {"strong": "высокая", "medium": "средняя", "weak": "низкая"}
        graph_lines = ["digraph G {", "  rankdir=LR;", "  node [shape=ellipse style=filled fillcolor=\"#f0f8ff\" fontsize=10];"]
        for c in conns:
            a = _wrap_label(c.get("entity_a", ""))
            b = _wrap_label(c.get("entity_b", ""))
            s = c.get("strength", "weak")
            sl = sl_map.get(s, s)
            style = "dashed" if s == "weak" else ("bold" if s == "strong" else "solid")
            color = "#cc0000" if s == "strong" else ("#cc8800" if s == "medium" else "#888888")
            person_inn = c.get("person_inn", "")
            url_a = pb_url(analyzed_inn)
            url_b = pb_url(person_inn) if person_inn else ""
            if a:
                a_safe = a.replace('"', "'")
                graph_lines.append(f'  "{a_safe}" [URL="{url_a}" fontcolor="#3366cc"];')
                if b:
                    b_safe = b.replace('"', "'")
                    if url_b: graph_lines.append(f'  "{b_safe}" [URL="{url_b}" fontcolor="#3366cc"];')
                    else: graph_lines.append(f'  "{b_safe}";')
                    graph_lines.append(f'  "{a_safe}" -> "{b_safe}" [label="{sl}" style="{style}" color="{color}"];')
        graph_lines.append("}")
        st.graphviz_chart("\n".join(graph_lines), use_container_width=True)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Связанные компании не выявлены</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# FINANCE
# ══════════════════════════════════════════════════════════
elif section == "finance":
    st.markdown('<div class="section-title">💰 Финансовый анализ</div>', unsafe_allow_html=True)

    rp = ad.get("agent_rusprofile", {})
    tp = ad.get("agent_transparent", {})

    rev = rp.get("revenue", {})
    profit = rp.get("net_profit", {})

    # Main financial metrics
    cols = st.columns(3)
    metrics = [
        (cols[0], "Выручка 2024", _fmt(rev.get("2024", 0))),
        (cols[1], "Прибыль 2024", _fmt(profit.get("2024", 0))),
        (cols[2], "Налоговая нагрузка", f'{tp.get("tax_burden_percent") or eg.get("tax_burden_percent", "—")}%'),
    ]
    for col, label, val in metrics:
        with col: st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{val}</div><div style="font-size:12px;color:#6b7280;">{label}</div></div>', unsafe_allow_html=True)

    cols = st.columns(3)
    metrics2 = [
        (cols[0], "Налоги уплачено", _fmt(tp.get("taxes_paid") or eg.get("tax_paid", 0))),
        (cols[1], "Налоговый долг", _fmt(tp.get("tax_debt") or eg.get("tax_debt", 0))),
        (cols[2], "Сотрудники", eg.get("employees", "—")),
    ]
    for col, label, val in metrics2:
        with col: st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{val}</div><div style="font-size:12px;color:#6b7280;">{label}</div></div>', unsafe_allow_html=True)

    # Revenue history
    has_rp = any(rev.get(y) for y in ("2020", "2021", "2022", "2023", "2024"))
    if has_rp:
        st.markdown('<div class="section-title">📈 Динамика выручки</div>', unsafe_allow_html=True)
        rev_data = {y: rev.get(y, 0) for y in ("2020", "2021", "2022", "2023", "2024") if rev.get(y)}
        if rev_data:
            df_rev = pd.DataFrame(list(rev_data.items()), columns=["Год", "Выручка"])
            df_rev["Выручка_млн"] = df_rev["Выручка"].apply(lambda x: round(x / 1e6, 1))
            chart = alt.Chart(df_rev).mark_bar(color="#3b82f6", cornerRadius=4).encode(
                x=alt.X("Год:N", title="", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Выручка_млн:Q", title="млн руб."),
                tooltip=[alt.Tooltip("Год:N"), alt.Tooltip("Выручка_млн:Q", title="Выручка (млн)")],
            ).properties(height=350).configure_axis(
                labelFontSize=12, titleFontSize=13
            )
            text = chart.mark_text(align="center", baseline="bottom", dy=-5, fontSize=12,
                                   color="#374151").encode(text=alt.Text("Выручка_млн:Q", format=".0f"))
            st.altair_chart(chart + text, use_container_width=True)
            st.caption("Выручка в млн руб.")

    # Net assets
    net_assets = rp.get("net_assets", {})
    if net_assets:
        st.markdown('<div class="section-title">📊 Чистые активы</div>', unsafe_allow_html=True)
        na_data = {y: net_assets.get(y, 0) for y in ("2020", "2021", "2022", "2023", "2024") if net_assets.get(y)}
        if na_data:
            df_na = pd.DataFrame(list(na_data.items()), columns=["Год", "Активы"])
            df_na["Активы_млн"] = df_na["Активы"].apply(lambda x: round(x / 1e6, 1))
            chart2 = alt.Chart(df_na).mark_bar(color="#059669", cornerRadius=4).encode(
                x=alt.X("Год:N", title="", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Активы_млн:Q", title="млн руб."),
                tooltip=[alt.Tooltip("Год:N"), alt.Tooltip("Активы_млн:Q", title="Активы (млн)")],
            ).properties(height=350).configure_axis(
                labelFontSize=12, titleFontSize=13
            )
            text2 = chart2.mark_text(align="center", baseline="bottom", dy=-5, fontSize=12,
                                     color="#374151").encode(text=alt.Text("Активы_млн:Q", format=".0f"))
            st.altair_chart(chart2 + text2, use_container_width=True)
            st.caption("Чистые активы в млн руб.")

    # Net profit history
    profit = rp.get("net_profit", {})
    has_profit = any(profit.get(y) for y in ("2020", "2021", "2022", "2023", "2024"))
    if has_profit:
        st.markdown('<div class="section-title">📉 Чистая прибыль</div>', unsafe_allow_html=True)
        profit_data = {y: profit.get(y, 0) for y in ("2020", "2021", "2022", "2023", "2024") if profit.get(y)}
        if profit_data:
            df_profit = pd.DataFrame(list(profit_data.items()), columns=["Год", "Прибыль"])
            df_profit["Прибыль_млн"] = df_profit["Прибыль"].apply(lambda x: round(x / 1e6, 1))
            color_col = alt.condition(
                alt.datum.Прибыль_млн > 0, alt.value("#10b981"), alt.value("#ef4444")
            )
            chart3 = alt.Chart(df_profit).mark_bar(cornerRadius=4).encode(
                x=alt.X("Год:N", title="", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Прибыль_млн:Q", title="млн руб."),
                color=color_col,
                tooltip=[alt.Tooltip("Год:N"), alt.Tooltip("Прибыль_млн:Q", title="Прибыль (млн)")],
            ).properties(height=350).configure_axis(
                labelFontSize=12, titleFontSize=13
            )
            text3 = chart3.mark_text(align="center", baseline="bottom", dy=-5, fontSize=12,
                                     color="#374151").encode(text=alt.Text("Прибыль_млн:Q", format=".0f"))
            st.altair_chart(chart3 + text3, use_container_width=True)
            st.caption("Чистая прибыль в млн руб.")

    # Combined dashboard
    rev = rp.get("revenue", {})
    if any(rev.get(y) for y in ("2020", "2021", "2022", "2023", "2024")):
        st.markdown('<div class="section-title">📊 Финансовый дашборд</div>', unsafe_allow_html=True)
        rows = []
        for y in ("2020", "2021", "2022", "2023", "2024"):
            rv = rev.get(y)
            pr = profit.get(y) if profit else None
            na = net_assets.get(y) if net_assets else None
            if any([rv, pr, na]):
                rows.append({"Год": y, "Выручка": _fmt(rv) if rv else "—",
                             "Прибыль": _fmt(pr) if pr else "—",
                             "Активы": _fmt(na) if na else "—"})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════
# COURT
# ══════════════════════════════════════════════════════════
elif section == "court":
    st.markdown('<div class="section-title">⚖️ Судебные дела</div>', unsafe_allow_html=True)
    ar = ad.get("agent_arbitr", {})

    cols = st.columns(4)
    court_metrics = [
        (cols[0], "Всего дел", ar.get("total_cases", 0)),
        (cols[1], "Как истец", ar.get("as_plaintiff", 0)),
        (cols[2], "Как ответчик", ar.get("as_defendant", 0)),
        (cols[3], "Налоговые споры", ar.get("tax_disputes", 0)),
    ]
    for col, label, val in court_metrics:
        with col:
            st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{val}</div><div style="font-size:12px;color:#6b7280;">{label}</div></div>', unsafe_allow_html=True)

    if ar.get("total_claims_amount"):
        st.markdown(f'<div class="card"><b>Общая сумма исков:</b> {_fmt(ar["total_claims_amount"])}</div>', unsafe_allow_html=True)

    # Court timeline chart from arbitr_preview
    arbitr_preview = ad.get("_irbis_arbitr_preview", [])
    if isinstance(arbitr_preview, list) and len(arbitr_preview) > 1:
        df_timeline = pd.DataFrame(arbitr_preview)
        if "year" in df_timeline.columns and "count" in df_timeline.columns:
            df_timeline["year"] = df_timeline["year"].astype(str)
            df_timeline = df_timeline.sort_values("year")
            st.markdown('<div class="section-title">📅 Динамика по годам</div>', unsafe_allow_html=True)
            chart = alt.Chart(df_timeline).mark_bar(color="#f59e0b", cornerRadius=4).encode(
                x=alt.X("year:N", title="", axis=alt.Axis(labelAngle=45, labelFontSize=10)),
                y=alt.Y("count:Q", title="Количество дел"),
                tooltip=[alt.Tooltip("year:N", title="Год"), alt.Tooltip("count:Q", title="Дел")],
            ).properties(height=250)
            text = chart.mark_text(align="center", baseline="bottom", dy=-4, fontSize=10,
                                   color="#374151").encode(text=alt.Text("count:Q"))
            st.altair_chart(chart + text, use_container_width=True)

    cases = ar.get("cases", [])
    if cases:
        df = pd.DataFrame(cases)
        if "date" in df.columns: df["date"] = df["date"].astype(str)
        if "amount" in df.columns: df["amount"] = df["amount"].apply(lambda x: _fmt(x))
        if "role" in df.columns:
            role_map = {"plaintiff": "Истец", "defendant": "Ответчик", "third": "Третье лицо"}
            df["role"] = df["role"].map(role_map).fillna(df["role"])
        if "opponents" in df.columns:
            df["opponents"] = df["opponents"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
        col_map = {"number": "Номер дела", "date": "Дата", "role": "Роль", "amount": "Сумма иска", "subject": "Суд", "opponents": "Оппоненты"}
        df = df.rename(columns=col_map)
        cols_show = [c for c in col_map.values() if c in df.columns]
        df = df[cols_show]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Показано {len(df)} из {ar.get('total_cases', 0)} дел")
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Судебные дела не найдены ✅</div>', unsafe_allow_html=True)
        _indicator(ar.get("total_cases", 0) > 0, "✅ Всего дел известно из ЕГРЮЛ", "⏳ Детали дел загружаются — попробуйте позже")

# ══════════════════════════════════════════════════════════
# FSSP
# ══════════════════════════════════════════════════════════
elif section == "fssp":
    st.markdown('<div class="section-title">🔨 Исполнительные производства (ФССП)</div>', unsafe_allow_html=True)
    fs = ad.get("agent_fssp", {})

    cols = st.columns(2)
    with cols[0]:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{fs.get("total_proceedings", 0)}</div><div style="font-size:12px;color:#6b7280;">Всего производств</div></div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{_fmt(fs.get("total_debt", 0))}</div><div style="font-size:12px;color:#6b7280;">Общий долг</div></div>', unsafe_allow_html=True)

    # FSSP breakdown chart
    fssp_chart_data = ad.get("_irbis_fssp_preview_chart", [])
    if isinstance(fssp_chart_data, list) and len(fssp_chart_data) > 1:
        df_fc = pd.DataFrame(fssp_chart_data)
        if "type" in df_fc.columns and "type_sum" in df_fc.columns:
            df_fc = df_fc.sort_values("type_sum", ascending=False)
            st.markdown('<div class="section-title">📊 Разбивка по типам долгов</div>', unsafe_allow_html=True)
            chart = alt.Chart(df_fc).mark_bar(color="#dc2626", cornerRadius=4).encode(
                x=alt.X("type:N", title="", axis=alt.Axis(labelAngle=35, labelFontSize=10), sort="-y"),
                y=alt.Y("type_sum:Q", title="Сумма долга (₽)"),
                tooltip=[alt.Tooltip("type:N", title="Тип"), alt.Tooltip("type_sum:Q", title="Сумма", format=",.0f")],
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)

    procs = fs.get("proceedings", [])
    if procs:
        df = pd.DataFrame(procs)
        if "amount" in df.columns: df["amount"] = df["amount"].apply(lambda x: _fmt(x))
        col_map = {"number": "Номер ИП", "amount": "Сумма долга", "status": "Статус", "date": "Дата"}
        df = df.rename(columns=col_map)
        cols_show = [c for c in col_map.values() if c in df.columns]
        df = df[cols_show]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Показано {len(procs)} из {fs.get('total_proceedings', 0)} производств")
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Исполнительные производства не найдены ✅</div>', unsafe_allow_html=True)
        _indicator(fs.get("total_proceedings", 0) > 0, "✅ Количество известно из ЕГРЮЛ", "⏳ Детали загружаются — попробуйте позже")

# ══════════════════════════════════════════════════════════
# BANKRUPT
# ══════════════════════════════════════════════════════════
elif section == "bankrupt":
    st.markdown('<div class="section-title">📋 Банкротства (Федресурс)</div>', unsafe_allow_html=True)
    br = ad.get("agent_bankrupt", {})

    st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{br.get("total_records", 0)}</div><div style="font-size:12px;color:#6b7280;">Записей на Федресурсе</div></div>', unsafe_allow_html=True)

    records = br.get("records", [])
    if br.get("has_bankruptcy") and isinstance(records, list) and len(records) > 0:
        st.error("⚠️ Обнаружены записи о банкротстве!")
        for rec in records:
            if isinstance(rec, dict):
                st.markdown(f'<div class="card card-red">{rec.get("debtor", rec.get("name", "—"))}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="card card-red">{str(rec)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Банкротства не обнаружены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# LICENSES
# ══════════════════════════════════════════════════════════
elif section == "licenses":
    st.markdown('<div class="section-title">🪪 Лицензии</div>', unsafe_allow_html=True)
    lic = rd.get("licenses_data", {})
    if lic.get("license_required"):
        st.warning(f"Деятельность требует лицензии: **{lic.get('license_activity', '—')}**")
        if lic.get("has_license"):
            st.success("✅ Лицензия имеется")
            for l in lic.get("licenses", []):
                st.markdown(f'<div class="card card-green">№ {l.get("number", "—")} ({l.get("date", "—")})</div>', unsafe_allow_html=True)
        else:
            st.error("❌ Лицензия не найдена — риск приостановки деятельности")
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">По ОКВЭД лицензия не требуется ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# GOSCON
# ══════════════════════════════════════════════════════════
elif section == "goscon":
    st.markdown('<div class="section-title">🏛️ Госконтракты (44-ФЗ / 223-ФЗ)</div>', unsafe_allow_html=True)
    gc = ad.get("_irbis_goscon", {})
    total = gc.get("Количество контрактов", gc.get("total_contracts", 0))
    total_sum = gc.get("Общая сумма", gc.get("total_sum", 0))
    cols = st.columns(2)
    with cols[0]:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{total}</div><div style="font-size:12px;color:#6b7280;">Контрактов</div></div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{_fmt(total_sum) if isinstance(total_sum, (int,float)) else total_sum}</div><div style="font-size:12px;color:#6b7280;">Общая сумма</div></div>', unsafe_allow_html=True)
    items = gc.get("Контракты", gc.get("contracts", []))
    if items:
        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Госконтракты не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# SANCTIONS
# ══════════════════════════════════════════════════════════
elif section == "sanctions":
    st.markdown('<div class="section-title">⚠️ Санкционные проверки</div>', unsafe_allow_html=True)
    sc = ad.get("_irbis_sanctions", {})
    if sc.get("Проверка", sc.get("found", False)):
        st.error("🚨 Организация найдена в санкционных списках")
        items = sc.get("Списки", sc.get("lists", [sc]))
        for s in items if isinstance(items, list) else [items]:
            st.markdown(f'<div class="card" style="border-left:4px solid #ef4444;">{str(s)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">В санкционных списках не найдена ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# PLEDGE
# ══════════════════════════════════════════════════════════
elif section == "pledge":
    st.markdown('<div class="section-title">🔐 Залоги (Федресурс / Нотариат)</div>', unsafe_allow_html=True)
    pl = ad.get("_irbis_pledge", {})
    items = pl.get("Залоги", pl.get("pledges", []))
    if items:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(items)}</div><div style="font-size:12px;color:#6b7280;">Записей о залогах</div></div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Записи о залогах не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# TRADEMARKS
# ══════════════════════════════════════════════════════════
elif section == "trademarks":
    st.markdown('<div class="section-title">🏷️ Торговые марки (Роспатент)</div>', unsafe_allow_html=True)
    tm = ad.get("_irbis_trademarks", {})
    items = tm.get("Торговые марки", tm.get("trademarks", []))
    if items and len(items) > 0:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(items)}</div><div style="font-size:12px;color:#6b7280;">Зарегистрированных ТМ</div></div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Торговые марки не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# LEASING
# ══════════════════════════════════════════════════════════
elif section == "leasing":
    st.markdown('<div class="section-title">📦 Лизинг</div>', unsafe_allow_html=True)
    ls = ad.get("_irbis_leasing", {})
    items = ls.get("Договоры лизинга", ls.get("leases", []))
    if items and len(items) > 0:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(items)}</div><div style="font-size:12px;color:#6b7280;">Договоров лизинга</div></div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Договоры лизинга не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# FOREIGN AGENT
# ══════════════════════════════════════════════════════════
elif section == "foreign_agent":
    st.markdown('<div class="section-title">👽 Иноагенты и нежелательные организации</div>', unsafe_allow_html=True)
    fa = ad.get("_irbis_foreign_agent", {})
    if fa.get("Проверка", fa.get("found", False)):
        st.error("🚨 Организация связана с иноагентами / нежелательными организациями")
        st.json(fa)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Связи с иноагентами не обнаружены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# ROM
# ══════════════════════════════════════════════════════════
elif section == "rom":
    st.markdown('<div class="section-title">🛡️ Розыск и обеспечительные меры (РОМ)</div>', unsafe_allow_html=True)
    rm = ad.get("_irbis_rom", {})
    items = rm.get("Обеспечительные меры", rm.get("securities", []))
    if items and len(items) > 0:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(items)}</div><div style="font-size:12px;color:#6b7280;">Обеспечительных мер</div></div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Обеспечительные меры не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# SUBSIDIARY
# ══════════════════════════════════════════════════════════
elif section == "subsidiary":
    st.markdown('<div class="section-title">⚖️ Субсидиарная ответственность</div>', unsafe_allow_html=True)
    sb = ad.get("_irbis_subsidiary", {})
    items = sb.get("Субсидиарные ответчики", sb.get("defendants", []))
    if items and len(items) > 0:
        st.warning("⚡ Организация привлекалась как субсидиарный ответчик")
        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Привлечения к субсидиарной ответственности не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# INSPECTIONS
# ══════════════════════════════════════════════════════════
elif section == "inspections":
    st.markdown('<div class="section-title">🔍 Проверки (КНД)</div>', unsafe_allow_html=True)
    insp = ad.get("agent_inspections", {})
    cols = st.columns(3)
    insp_metrics = [
        (cols[0], "Всего проверок", insp.get("total_inspections", 0)),
        (cols[1], "Налоговые", insp.get("tax_inspections", 0)),
        (cols[2], "Нарушения", insp.get("violations", 0)),
    ]
    for col, label, val in insp_metrics:
        with col:
            st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{val}</div><div style="font-size:12px;color:#6b7280;">{label}</div></div>', unsafe_allow_html=True)
    insp_items = insp.get("inspections", [])
    if isinstance(insp_items, dict):
        insp_items = [insp_items]
    if isinstance(insp_items, list) and len(insp_items) > 0:
        df_insp = pd.DataFrame(insp_items)
        if not df_insp.empty and all(df_insp.dtypes == object):
            pass
        st.dataframe(df_insp, use_container_width=True, hide_index=True)
    if insp.get("note"):
        st.caption(insp["note"])

# ══════════════════════════════════════════════════════════
# NDP
# ══════════════════════════════════════════════════════════
elif section == "ndp":
    st.markdown('<div class="section-title">⚫ НДП / РНП</div>', unsafe_allow_html=True)
    ndp = ad.get("agent_ndp", {})
    if ndp.get("in_registry"):
        st.error("⚠️ Компания найдена в реестре недобросовестных поставщиков!")
        for e in ndp.get("entries", []):
            st.markdown(f'<div class="card card-red">{e.get("customer", "—")}: {e.get("reason", "—")} ({e.get("date", "—")})</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">В реестре недобросовестных поставщиков не числится ✅</div>', unsafe_allow_html=True)
    if ndp.get("note"):
        st.caption(ndp["note"])

# ══════════════════════════════════════════════════════════
# JUDGE (общей юрисдикции)
# ══════════════════════════════════════════════════════════
elif section == "judge_common":
    st.markdown('<div class="section-title">⚖️ Суды общей юрисдикции</div>', unsafe_allow_html=True)
    jdg = ad.get("_irbis_judge", [])
    if jdg and isinstance(jdg, list) and len(jdg) > 0:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(jdg)}</div><div style="font-size:12px;color:#6b7280;">Судебных дел</div></div>', unsafe_allow_html=True)
        df = pd.DataFrame(jdg)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Дела в судах общей юрисдикции не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# ARREST
# ══════════════════════════════════════════════════════════
elif section == "arrest":
    st.markdown('<div class="section-title">🔒 Приостановления операций по счетам</div>', unsafe_allow_html=True)
    art = ad.get("_irbis_arrest", [])
    saldo = ad.get("_irbis_arrest_saldo", 0)
    if isinstance(saldo, dict):
        saldo = saldo.get("saldo") or saldo.get("sum") or 0
    try:
        saldo = float(saldo) if saldo else 0
    except (ValueError, TypeError):
        saldo = 0
    if saldo:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{_fmt(saldo)}</div><div style="font-size:12px;color:#6b7280;">Задолженность перед ФНС</div></div>', unsafe_allow_html=True)
    if art and isinstance(art, list) and len(art) > 0:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(art)}</div><div style="font-size:12px;color:#6b7280;">Приостановлений</div></div>', unsafe_allow_html=True)
        df = pd.DataFrame(art)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Приостановления операций по счетам не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# NALOG_DEBT
# ══════════════════════════════════════════════════════════
elif section == "nalog_debt":
    st.markdown('<div class="section-title">💸 Налоговые задолженности</div>', unsafe_allow_html=True)
    nd = ad.get("_irbis_arrest_saldo", 0)
    if not isinstance(nd, (int, float)):
        nd = 0
    st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{_fmt(nd)}</div><div style="font-size:12px;color:#6b7280;">Задолженность перед ФНС</div></div>', unsafe_allow_html=True)
    fns = ad.get("_irbis_fssp_preview_fns", {})
    if isinstance(fns, dict) and fns.get("sum"):
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.2rem;">Долги ФССП перед ФНС: {_fmt(fns.get("sum", 0))}</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# MSP
# ══════════════════════════════════════════════════════════
elif section == "msp":
    st.markdown('<div class="section-title">🏢 Поддержка малого и среднего предпринимательства</div>', unsafe_allow_html=True)
    msp = ad.get("_irbis_msp", {})
    if msp and isinstance(msp, dict):
        if msp.get("status") == -1:
            st.markdown('<div class="card card-gray" style="text-align:center;">⏳ Данные МСП загружаются, повторите попытку позже</div>', unsafe_allow_html=True)
        elif msp.get("response"):
            st.json(msp["response"])
        else:
            items = msp.get("itemList", msp.get("result", []))
            if items:
                st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(items)}</div><div style="font-size:12px;color:#6b7280;">Записей</div></div>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
            else:
                st.markdown('<div class="card card-green" style="text-align:center;">Данные о поддержке МСП не найдены ✅</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Данные о поддержке МСП не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# BANKRUPTCY_INTENTION
# ══════════════════════════════════════════════════════════
elif section == "bankruptcy_intention":
    st.markdown('<div class="section-title">⚡ Намерения о банкротстве</div>', unsafe_allow_html=True)
    bi = ad.get("_irbis_bankruptcy_intention", [])
    if bi and isinstance(bi, list) and bi:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(bi)}</div><div style="font-size:12px;color:#6b7280;">Намерений</div></div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(bi), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Намерения о банкротстве не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# REAL_ESTATE
# ══════════════════════════════════════════════════════════
elif section == "real_estate":
    st.markdown('<div class="section-title">🏠 Недвижимость / Кадастр</div>', unsafe_allow_html=True)
    okato = ad.get("_irbis_okato", {})
    if okato and isinstance(okato, dict):
        address = okato.get("address") or okato.get("full_address") or ""
        if address:
            st.markdown(f'<div class="card"><b>🏛️ Адрес:</b> {address}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card card-gray" style="text-align:center;">Данные о недвижимости доступны только при кадастровом запросе</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Данные о недвижимости доступны только при кадастровом запросе</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# ROSTRUD
# ══════════════════════════════════════════════════════════
elif section == "rostud":
    st.markdown('<div class="section-title">📄 Декларации Роструда</div>', unsafe_allow_html=True)
    rd = ad.get("_irbis_rd", [])
    if rd and isinstance(rd, list) and rd:
        st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(rd)}</div><div style="font-size:12px;color:#6b7280;">Деклараций</div></div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rd), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Декларации Роструда не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# RAFP
# ══════════════════════════════════════════════════════════
elif section == "rafp":
    st.markdown('<div class="section-title">🏭 РАФП (Реестр аккредитованных филиалов)</div>', unsafe_allow_html=True)
    st.markdown('<div class="card card-gray" style="text-align:center;">Данные РАФП доступны в PDF через ir-bis</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# PB (Documents for state registration)
# ══════════════════════════════════════════════════════════
elif section == "pb":
    st.markdown('<div class="section-title">📋 Документы, представленные для гос.регистрации</div>', unsafe_allow_html=True)
    pb = ad.get("_irbis_pb_urls", {})
    url = pb.get("url", "") if isinstance(pb, dict) else ""
    if url:
        st.markdown(f'<div class="card"><b>🔗 Ссылка на ФНС:</b><br><a href="{url}" target="_blank">{url[:80]}...</a></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Данные не найдены</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# TERRORIST
# ══════════════════════════════════════════════════════════
elif section == "terrorist":
    st.markdown('<div class="section-title">💣 Террористы / Экстремисты</div>', unsafe_allow_html=True)
    tr = ad.get("_irbis_terrorist", [])
    if tr and isinstance(tr, list) and tr:
        st.error("🚨 Организация/лицо найдено в списке террористов и экстремистов!")
        st.dataframe(pd.DataFrame(tr), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">В списках террористов и экстремистов не числится ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# DISQUALIFIED
# ══════════════════════════════════════════════════════════
elif section == "disqualified":
    st.markdown('<div class="section-title">👤 Реестр дисквалифицированных лиц</div>', unsafe_allow_html=True)
    dq = ad.get("_irbis_disqualified", [])
    if dq and isinstance(dq, list) and dq:
        st.warning("⚠️ Найдены дисквалифицированные лица")
        st.dataframe(pd.DataFrame(dq), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Дисквалифицированные лица не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# CORRUPTION
# ══════════════════════════════════════════════════════════
elif section == "corruption":
    st.markdown('<div class="section-title">👮 Реестр коррупционеров</div>', unsafe_allow_html=True)
    cr = ad.get("_irbis_remuneration", [])
    if cr and isinstance(cr, list) and cr:
        st.error("⚠️ Найдены записи в реестре коррупционеров!")
        st.dataframe(pd.DataFrame(cr), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">В реестре коррупционеров не числится ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# CBR_WL
# ══════════════════════════════════════════════════════════
elif section == "cbr_wl":
    st.markdown('<div class="section-title">🏦 ЦБ РФ — Реестр нелегальных поставщиков финансовых услуг</div>', unsafe_allow_html=True)
    cbr = ad.get("_irbis_cbr_wl", {})
    if cbr:
        st.json(cbr)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">В чёрном списке ЦБ РФ не числится ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# INHERITANCE
# ══════════════════════════════════════════════════════════
elif section == "inheritance":
    st.markdown('<div class="section-title">📜 Реестр наследственных дел</div>', unsafe_allow_html=True)
    inh = ad.get("_irbis_inheritance", [])
    if inh and isinstance(inh, list) and inh:
        st.dataframe(pd.DataFrame(inh), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Наследственные дела не найдены ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# SELF_EMPLOYED
# ══════════════════════════════════════════════════════════
elif section == "self_employed":
    st.markdown('<div class="section-title">👤 Реестр самозанятых</div>', unsafe_allow_html=True)
    se = ad.get("_irbis_self_employed", {})
    if se:
        st.json(se)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Данные о самозанятости доступны только для ФЛ</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# BANNED_FANS
# ══════════════════════════════════════════════════════════
elif section == "banned_fans":
    st.markdown('<div class="section-title">👥 Реестр лиц с запретом посещения спорт.мероприятий</div>', unsafe_allow_html=True)
    bf = ad.get("_irbis_mvd_bannedfans", [])
    if bf and isinstance(bf, list) and bf:
        st.dataframe(pd.DataFrame(bf), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">Не найдено ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# MVD
# ══════════════════════════════════════════════════════════
elif section == "mvd":
    st.markdown('<div class="section-title">🚔 Розыск МВД</div>', unsafe_allow_html=True)
    mvd = ad.get("_irbis_mvd", {})
    if mvd:
        st.json(mvd)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">В розыске МВД не числится ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# FSIN
# ══════════════════════════════════════════════════════════
elif section == "fsin":
    st.markdown('<div class="section-title">🔒 Розыск ФСИН</div>', unsafe_allow_html=True)
    fsin = ad.get("_irbis_fsin", {})
    if fsin:
        st.json(fsin)
    else:
        st.markdown('<div class="card card-green" style="text-align:center;">В розыске ФСИН не числится ✅</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# CONTROLLED
# ══════════════════════════════════════════════════════════
elif section == "controlled":
    st.markdown('<div class="section-title">👤 Контролируемые лица</div>', unsafe_allow_html=True)
    st.markdown('<div class="card card-gray" style="text-align:center;">Проверка контролируемых лиц доступна через проверку ФЛ</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# DRIVER LICENSE
# ══════════════════════════════════════════════════════════
elif section == "driver_license":
    st.markdown('<div class="section-title">🚗 Водительское удостоверение</div>', unsafe_allow_html=True)
    dl = ad.get("_irbis_driver_license", {})
    dtl = ad.get("_irbis_driver_tractor_license", {})
    if dl and isinstance(dl, dict) and dl.get("response"):
        st.markdown('<div class="card"><b>🚗 Водительское удостоверение</b></div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([dl.get("response", {})]), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Данные водительского удостоверения не найдены (только для ФЛ)</div>', unsafe_allow_html=True)
    if dtl and isinstance(dtl, dict) and dtl.get("response"):
        st.markdown('<div class="card"><b>🚜 Тракторное водительское удостоверение</b></div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([dtl.get("response", {})]), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════
# PASSPORT
# ══════════════════════════════════════════════════════════
elif section == "passport":
    st.markdown('<div class="section-title">🛂 Проверка паспорта</div>', unsafe_allow_html=True)
    pp = ad.get("_irbis_passport", {})
    if pp:
        st.json(pp)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Проверка паспорта доступна только для ФЛ</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# ML_INDEX
# ══════════════════════════════════════════════════════════
elif section == "ml_index":
    st.markdown('<div class="section-title">🧠 ML-индекс</div>', unsafe_allow_html=True)
    sc = ad.get("_irbis_scoring", {})
    if sc:
        st.json(sc)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">ML-индекс доступен только для ФЛ</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# POPULARITY
# ══════════════════════════════════════════════════════════
elif section == "popularity":
    st.markdown('<div class="section-title">🗣️ Популярность ФИО в госреестрах</div>', unsafe_allow_html=True)
    pop = ad.get("_irbis_popularity", {})
    if pop:
        st.json(pop)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Данные доступны только для ФЛ</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# CONTACT
# ══════════════════════════════════════════════════════════
elif section == "contact":
    st.markdown('<div class="section-title">📞 Контакты организации</div>', unsafe_allow_html=True)
    ct = ad.get("_irbis_contacts", {})
    if ct and isinstance(ct, dict):
        contacts = ct.get("contacts", {})
        if contacts:
            col1, col2, col3 = st.columns(3)
            with col1:
                email = contacts.get("email", "")
                st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.2rem;">📧</div><div style="font-size:12px;color:#6b7280;">Email</div><div style="font-weight:700;">{email if email else "—"}</div></div>', unsafe_allow_html=True)
            with col2:
                phone = contacts.get("phone", "")
                st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.2rem;">📞</div><div style="font-size:12px;color:#6b7280;">Телефон</div><div style="font-weight:700;">{phone if phone else "—"}</div></div>', unsafe_allow_html=True)
            with col3:
                site = contacts.get("site", "")
                if site:
                    st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.2rem;">🌐</div><div style="font-size:12px;color:#6b7280;">Сайт</div><div style="font-weight:700;"><a href="https://{site}" target="_blank">{site}</a></div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.2rem;">🌐</div><div style="font-size:12px;color:#6b7280;">Сайт</div><div style="font-weight:700;">—</div></div>', unsafe_allow_html=True)
            if ct.get("lastUpdate"):
                st.caption(f"Дата обновления: {ct['lastUpdate']}")
        else:
            st.markdown('<div class="card card-gray" style="text-align:center;">Контактные данные не найдены</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Контактные данные не найдены</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# DISCLOSURE
# ══════════════════════════════════════════════════════════
elif section == "disclosure":
    st.markdown('<div class="section-title">📋 Раскрытие корпоративной информации</div>', unsafe_allow_html=True)
    dc = ad.get("_irbis_disclosure", {})
    if dc and isinstance(dc, dict):
        url = dc.get("url", "")
        if url:
            st.markdown(f'<div class="card"><b>🔗 Ссылка раскрытия:</b><br><a href="{url}" target="_blank">{url}</a></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card card-gray" style="text-align:center;">Данные раскрытия корпоративной информации не найдены</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Данные раскрытия корпоративной информации не найдены</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# FSGS
# ══════════════════════════════════════════════════════════
elif section == "fsgs":
    st.markdown('<div class="section-title">📊 ФСГС (Федеральная служба гос.статистики)</div>', unsafe_allow_html=True)
    fsgs = ad.get("_irbis_fsgs", {})
    if fsgs and isinstance(fsgs, dict):
        if fsgs.get("status") == -1:
            st.markdown('<div class="card card-gray" style="text-align:center;">⏳ Данные ФСГС загружаются, повторите попытку позже</div>', unsafe_allow_html=True)
        elif fsgs.get("response"):
            st.json(fsgs["response"])
        else:
            items = fsgs.get("itemList", fsgs.get("result", []))
            if items:
                st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
            else:
                st.markdown('<div class="card card-gray" style="text-align:center;">Данные ФСГС не найдены</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Данные ФСГС не найдены</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# ADDRESS_OKATO
# ══════════════════════════════════════════════════════════
elif section == "address_okato":
    st.markdown('<div class="section-title">🏛️ Адрес (ОКАТО)</div>', unsafe_allow_html=True)
    addr = ad.get("_irbis_okato", {})
    if addr and isinstance(addr, dict):
        address = addr.get("address") or addr.get("full_address") or addr.get("result", {}).get("address", "")
        if address:
            st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.1rem;">🏛️ {address}</div></div>', unsafe_allow_html=True)
            if addr.get("okato"):
                st.markdown(f'<div class="card" style="text-align:center;">ОКАТО: {addr["okato"]}</div>', unsafe_allow_html=True)
            if addr.get("oktmo"):
                st.markdown(f'<div class="card" style="text-align:center;">ОКТМО: {addr["oktmo"]}</div>', unsafe_allow_html=True)
            if addr.get("kladr"):
                st.markdown(f'<div class="card" style="text-align:center;">КЛАДР: {addr["kladr"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card card-gray" style="text-align:center;">Данные адреса по ОКАТО не найдены</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Данные адреса по ОКАТО не найдены</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════
elif section == "history":
    st.markdown('<div class="section-title">📋 История изменений ЕГРЮЛ</div>', unsafe_allow_html=True)
    hist = ad.get("_irbis_history", {})
    if hist and isinstance(hist, dict):
        # Names history
        names = hist.get("names", [])
        if names:
            st.markdown('<div class="card"><b>📛 История наименований</b></div>', unsafe_allow_html=True)
            df_names = pd.DataFrame(names)
            if "period" in df_names.columns:
                df_names["period"] = df_names["period"].apply(lambda x: x.get("since", "") if isinstance(x, dict) else "")
            col_map = {"shortName": "Краткое", "fullName": "Полное", "period": "Дата"}
            df_names = df_names.rename(columns=col_map)
            st.dataframe(df_names[["Дата", "Краткое", "Полное"]], use_container_width=True, hide_index=True)

        # Founders history
        founders = hist.get("founders", [])
        if founders:
            st.markdown('<div class="card"><b>👤 История учредителей</b></div>', unsafe_allow_html=True)
            df_f = pd.DataFrame(founders)
            if "period" in df_f.columns:
                df_f["period"] = df_f["period"].apply(lambda x: x.get("since", "") if isinstance(x, dict) else "")
            col_map = {"lastName": "Фамилия", "firstName": "Имя", "secondName": "Отчество", "inn": "ИНН", "role": "Роль", "period": "С"}
            df_f = df_f.rename(columns=col_map)
            df_f["ФИО"] = df_f.apply(lambda r: f'{r.get("Фамилия","")} {r.get("Имя","")} {r.get("Отчество","")}'.strip(), axis=1)
            st.dataframe(df_f[["С", "ФИО", "ИНН", "Роль"]], use_container_width=True, hide_index=True)

        # Managers history
        managers = hist.get("managers", [])
        if managers:
            st.markdown('<div class="card"><b>👔 История руководителей</b></div>', unsafe_allow_html=True)
            df_m = pd.DataFrame(managers)
            if "period" in df_m.columns:
                df_m["period"] = df_m["period"].apply(lambda x: x.get("since", "") if isinstance(x, dict) else "")
            col_map = {"lastName": "Фамилия", "firstName": "Имя", "secondName": "Отчество", "inn": "ИНН", "role": "Должность", "period": "С"}
            df_m = df_m.rename(columns=col_map)
            df_m["ФИО"] = df_m.apply(lambda r: f'{r.get("Фамилия","")} {r.get("Имя","")} {r.get("Отчество","")}'.strip(), axis=1)
            st.dataframe(df_m[["С", "ФИО", "ИНН", "Должность"]], use_container_width=True, hide_index=True)

        # Addresses history
        addresses = hist.get("addresses", [])
        if addresses:
            st.markdown('<div class="card"><b>🏛️ История адресов</b></div>', unsafe_allow_html=True)
            for a in addresses:
                period = ""
                if a.get("period"):
                    p = a["period"]
                    since = p.get("since", "")
                    until = p.get("until", "")
                    period = f"{since} — {until}" if until else f"с {since}"
                st.markdown(f'<div class="card card-gray" style="padding:0.5rem 1rem;">{a.get("full_address", "")}<br><span style="font-size:11px;color:#6b7280;">{period}</span></div>', unsafe_allow_html=True)

        # Sizes (employees history)
        sizes = hist.get("sizes", [])
        if sizes:
            st.markdown('<div class="card"><b>👥 Численность сотрудников</b></div>', unsafe_allow_html=True)
            df_s = pd.DataFrame(sizes)
            if "period" in df_s.columns:
                df_s["period"] = df_s["period"].apply(lambda x: f'{x.get("since","")} — {x.get("until","")}' if isinstance(x, dict) and x.get("until") else f'с {x.get("since","")}' if isinstance(x, dict) else "")
            col_map = {"size": "Кол-во", "period": "Период"}
            df_s = df_s.rename(columns=col_map)
            st.dataframe(df_s[["Период", "Кол-во"]], use_container_width=True, hide_index=True)

        # Limitations
        limits = hist.get("limitations", {})
        if limits and isinstance(limits, dict):
            active_limits = {k: v for k, v in limits.items() if v}
            if active_limits:
                st.markdown('<div class="card card-red"><b>⚠️ Ограничения:</b></div>', unsafe_allow_html=True)
                limit_names = {
                    "ogr_uchr_ul": "Учредитель ЮЛ", "ogr_uchr_fl": "Учредитель ФЛ",
                    "ogr_manager_ul": "Руководитель ЮЛ", "ogr_manager_fl": "Руководитель ФЛ",
                    "ogr_license": "Лицензия", "ogr_reorg": "Реорганизация",
                }
                for k, v in active_limits.items():
                    name = limit_names.get(k, k)
                    st.markdown(f'<div class="card card-gray" style="padding:0.3rem 1rem;">⛔ {name}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">История изменений не найдена</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# MEDIA
# ══════════════════════════════════════════════════════════
elif section == "media":
    st.markdown('<div class="section-title">📰 СМИ и репутация</div>', unsafe_allow_html=True)
    md = ad.get("agent_media", {})
    sentiment = md.get("overall_sentiment", "не определена")
    emoji = {"negative": "🔴", "positive": "🟢", "neutral": "⚪"}
    st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.5rem;">{emoji.get(sentiment, "⚪")} {sentiment}</div><div style="font-size:12px;color:#6b7280;">Общая тональность</div></div>', unsafe_allow_html=True)
    articles = md.get("media_articles", [])
    if articles:
        st.markdown(f'<div class="card"><b>Всего публикаций:</b> {len(articles)}</div>', unsafe_allow_html=True)
        for a in articles[:10]:
            em = "🔴" if a.get("sentiment") == "negative" else "⚪"
            st.markdown(f'<div class="card card-gray">{em} <a href="{a.get("url", "#")}" target="_blank">{a.get("title", "")[:120]}</a></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card card-gray" style="text-align:center;">Публикации в СМИ не найдены</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# RISKS
# ══════════════════════════════════════════════════════════
elif section == "risks":
    st.markdown('<div class="section-title">⚠️ Оценка рисков</div>', unsafe_allow_html=True)

    sc = result.get("scoring", {})
    sp = result.get("splitting", {})
    tc = result.get("technical", {})

    # Risk table
    risk_data = [
        ("Налоговый", sc.get("tax_score", 0), sc.get("tax_level", "—")),
        ("Финансовый", sc.get("financial_score", 0), sc.get("financial_level", "—")),
        ("Корпоративный", sc.get("corporate_score", 0), sc.get("corporate_level", "—")),
        ("Репутационный", sc.get("reputation_score", 0), sc.get("reputation_level", "—")),
    ]
    df = pd.DataFrame(risk_data, columns=["Вид риска", "Оценка", "Уровень"])
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">🔍 Дробление бизнеса</div>', unsafe_allow_html=True)
    s_color = "green" if sp.get("conclusion") == "НИЗКАЯ" else ("orange" if sp.get("conclusion") == "СРЕДНЯЯ" else "red")
    st.markdown(f'<div class="card card-{s_color}"><b>Вывод:</b> {sp.get("conclusion", "—")}</div>', unsafe_allow_html=True)
    for i in sp.get("indicators", []):
        st.markdown(f'<div class="card card-gray" style="padding:0.5rem 1rem;">— {i}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">💻 Техническая компания</div>', unsafe_allow_html=True)
    t_color = "green" if tc.get("conclusion") == "НИЗКАЯ" else ("orange" if tc.get("conclusion") == "СРЕДНЯЯ" else "red")
    st.markdown(f'<div class="card card-{t_color}"><b>Вывод:</b> {tc.get("conclusion", "—")}</div>', unsafe_allow_html=True)
    for i in tc.get("indicators", []):
        st.markdown(f'<div class="card card-gray" style="padding:0.5rem 1rem;">— {i}</div>', unsafe_allow_html=True)

    # Tax risk findings
    tax_risk = rd.get("tax_risk", {})
    if tax_risk.get("findings"):
        st.markdown('<div class="section-title">📋 Детали налогового риска</div>', unsafe_allow_html=True)
        for f in tax_risk["findings"]:
            st.markdown(f'<div class="card card-gray" style="padding:0.5rem 1rem;">• {f.get("risk", "")}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════
elif section == "report":
    st.markdown('<div class="section-title">📄 Скачать отчёт</div>', unsafe_allow_html=True)
    rp = result.get("report_path", "")
    if rp and os.path.exists(rp):
        with open(rp, "rb") as f:
            st.markdown('<div class="card" style="text-align:center;">', unsafe_allow_html=True)
            st.download_button(
                label="📥 Скачать DOCX-отчёт",
                data=f,
                file_name=os.path.basename(rp),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary", use_container_width=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card card-blue"><b>Файл:</b> {os.path.basename(rp)}<br><b>Дата:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}</div>', unsafe_allow_html=True)
    else:
        st.warning("DOCX-отчёт ещё не сформирован")
        if st.button("🔄 Сформировать отчёт заново", type="primary", use_container_width=True):
            st.rerun()

# ── Footer ──
st.markdown(f"""
<div class="footer">
    ТОЛЬКО ДЛЯ ЛИЧНОГО ПОЛЬЗОВАНИЯ • ООО "КЛЮЧ КОММЕРЦИИ"<br>
    <span style="opacity:0.5;font-size:10px;">Налоговое досье.v9</span>
</div>
""", unsafe_allow_html=True)
