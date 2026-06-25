def get_css(theme="light"):
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
    --bg: #f0f2f6;
    --card-bg: #ffffff;
    --card-border: #e2e8f0;
    --text-primary: #1a202c;
    --text-secondary: #64748b;
    --sidebar-bg: #ffffff;
    --shadow: 0 1px 3px rgba(0,0,0,0.06);
    --shadow-hover: 0 8px 25px rgba(0,0,0,0.1);
    --accent: #3b82f6;
    --accent-light: #eff6ff;
    --divider: #e5e7eb;
    --green: #059669;
    --green-bg: #ecfdf5;
    --orange: #d97706;
    --orange-bg: #fffbeb;
    --red: #dc2626;
    --red-bg: #fef2f2;
    --gray: #9ca3af;
    --gray-bg: #f9fafb;
    --glass-bg: rgba(255,255,255,0.7);
    --glass-border: rgba(255,255,255,0.3);
    --graph-bg: #f0f8ff;
    --font: 'Inter', -apple-system, sans-serif;
}}

* {{ font-family: var(--font); }}
.stApp {{
    background: var(--bg);
    transition: background 0.4s ease;
}}
.main .block-container {{ padding: 2rem 1.5rem; max-width: 1400px; }}

/* ── Animated gradient background ── */
@keyframes gradientShift {{
    0% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}

.animated-bg {{
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: linear-gradient(-45deg, #667eea, #764ba2, #f093fb, #4facfe);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
    opacity: 0.03;
    z-index: -1;
    pointer-events: none;
}}

/* ── Fade-in animation ── */
@keyframes fadeSlideUp {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.animate-in {{
    animation: fadeSlideUp 0.5s ease forwards;
}}

.animate-in-1 {{ animation-delay: 0.05s; }}
.animate-in-2 {{ animation-delay: 0.1s; }}
.animate-in-3 {{ animation-delay: 0.15s; }}
.animate-in-4 {{ animation-delay: 0.2s; }}
.animate-in-5 {{ animation-delay: 0.25s; }}
.animate-in-6 {{ animation-delay: 0.3s; }}

/* ── Pulse for score ── */
@keyframes pulseGlow {{
    0%, 100% {{ box-shadow: 0 0 20px rgba(59,130,246,0.2); }}
    50% {{ box-shadow: 0 0 40px rgba(59,130,246,0.4); }}
}}

.pulse-glow {{
    animation: pulseGlow 2s ease-in-out infinite;
}}

/* ── Cards ── */
.card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    overflow-wrap: break-word;
    word-wrap: break-word;
    word-break: break-word;
    line-height: 1.6;
    color: var(--text-primary);
}}
.card:hover {{
    box-shadow: var(--shadow-hover);
    transform: translateY(-2px);
}}
.card-green {{ border-left: 5px solid var(--green); background: var(--green-bg); }}
.card-orange {{ border-left: 5px solid var(--orange); background: var(--orange-bg); }}
.card-red {{ border-left: 5px solid var(--red); background: var(--red-bg); }}
.card-gray {{ border-left: 5px solid var(--gray); background: var(--gray-bg); }}
.card-blue {{ border-left: 5px solid var(--accent); background: var(--accent-light); }}

/* ── Glass card ── */
.glass-card {{
    background: var(--glass-bg);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow);
    transition: all 0.3s ease;
    color: var(--text-primary);
}}
.glass-card:hover {{
    box-shadow: var(--shadow-hover);
    transform: translateY(-2px);
}}

/* ── Big score ── */
.score-wrap {{
    display: flex; align-items: center; gap: 1.5rem;
    flex-wrap: wrap;
}}
.score-circle {{
    width: 104px; height: 104px; border-radius: 50%;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    font-weight: 700; color: #fff; flex-shrink: 0;
    position: relative;
}}
.score-circle .num {{ font-size: 34px; line-height: 1; }}
.score-circle .lbl {{ font-size: 10px; opacity: 0.9; }}

/* ── Risk boxes ── */
.risk-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; margin: 1rem 0; }}
.risk-box {{
    border-radius: 12px; padding: 1.1rem; text-align: center;
    border: 1px solid var(--card-border); background: var(--card-bg);
    transition: all 0.3s ease;
}}
.risk-box:hover {{
    transform: scale(1.03);
    box-shadow: var(--shadow-hover);
}}
.risk-box .val {{ font-size: 28px; font-weight: 700; line-height: 1.2; }}
.risk-box .lbl {{ font-size: 12px; color: var(--text-secondary); margin-top: 2px; }}

/* ── Connections ── */
.conn-card {{
    padding: 0.875rem 1rem; border-radius: 10px; margin-bottom: 0.5rem;
    line-height: 1.5; transition: all 0.2s ease;
}}
.conn-card:hover {{ transform: translateX(4px); }}
.conn-strong {{ border-left: 4px solid var(--red); background: var(--red-bg); }}
.conn-medium {{ border-left: 4px solid var(--orange); background: var(--orange-bg); }}
.conn-weak {{ border-left: 4px solid var(--gray); background: var(--gray-bg); }}

/* ── Tables ── */
.data-compact td, .data-compact th {{
    padding: 0.4rem 0.6rem !important;
    font-size: 13px !important;
}}

/* ── Links ── */
a {{ color: var(--accent) !important; text-decoration: none !important; }}
a:hover {{ text-decoration: underline !important; }}

/* ── Sidebar ── */
.css-1d391kg, .css-1wrcr25 {{ background: var(--sidebar-bg) !important; }}
.sidebar-header {{ padding: 1rem 0; }}

/* ── Badges ── */
.badge {{
    display: inline-block; padding: 0.2rem 0.7rem; border-radius: 9999px;
    font-size: 11px; font-weight: 600;
}}
.badge-green {{ background: var(--green-bg); color: var(--green); }}
.badge-red {{ background: var(--red-bg); color: var(--red); }}
.badge-yellow {{ background: var(--orange-bg); color: var(--orange); }}
.badge-blue {{ background: var(--accent-light); color: var(--accent); }}

/* ── Section title ── */
.section-title {{
    font-size: 1.1rem; font-weight: 600; color: var(--text-primary);
    padding-bottom: 0.5rem; margin-bottom: 1rem;
    border-bottom: 2px solid var(--divider);
    animation: fadeSlideUp 0.4s ease forwards;
}}

/* ── Metrics ── */
.metric-row {{ display: flex; gap: 1rem; flex-wrap: wrap; }}
.metric-box {{
    flex: 1; min-width: 120px; background: var(--card-bg); border: 1px solid var(--card-border);
    border-radius: 12px; padding: 1rem; text-align: center;
    transition: all 0.3s ease;
}}
.metric-box:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-hover); }}
.metric-box .num {{ font-size: 24px; font-weight: 700; line-height: 1.2; color: var(--text-primary); }}
.metric-box .lbl {{ font-size: 12px; color: var(--text-secondary); }}

/* ── Hero / Landing ── */
.hero-section {{
    text-align: center; padding: 3rem 2rem;
}}
.hero-icon {{
    font-size: 72px; margin-bottom: 1rem;
    display: inline-block;
    animation: floatIcon 3s ease-in-out infinite;
}}
@keyframes floatIcon {{
    0%, 100% {{ transform: translateY(0); }}
    50% {{ transform: translateY(-10px); }}
}}
.hero-title {{
    font-size: 2rem; font-weight: 800; color: var(--text-primary);
    margin-bottom: 0.75rem;
}}
.hero-subtitle {{
    font-size: 1rem; color: var(--text-secondary);
    max-width: 540px; margin: 0 auto 0.5rem;
}}
.hero-sources {{
    font-size: 0.85rem; color: var(--text-secondary); opacity: 0.7;
    margin-top: 0.5rem;
}}
.hero-disclaimer {{
    margin-top: 2.5rem;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: var(--text-secondary);
    opacity: 0.8;
    border-top: 1px solid var(--divider);
    padding-top: 1.5rem;
}}
.hero-disclaimer-company {{
    font-size: 1.25rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

/* ── Buttons overrides ── */
.stButton > button {{
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}}
.stButton > button:hover {{
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
}}

/* ── Text inputs (always light bg for contrast) ── */
.stTextInput > div > div > input {{
    border-radius: 10px !important;
    border: 1px solid #d1d5db !important;
    background: #ffffff !important;
    color: #1a202c !important;
}}
.stTextInput > div > div > input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}}

/* ── Dataframes ── */
.stDataFrame {{
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid var(--card-border) !important;
}}
.stDataFrame [data-testid="StyledDataFrameDataCell"] {{
    color: var(--text-primary) !important;
}}

/* ── Footer ── */
.footer {{
    font-size: 12px; color: var(--text-secondary); margin-top: 2rem;
    text-align: center; padding: 1.2rem 0;
    border-top: 1px solid var(--divider);
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{
    background: var(--card-border);
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{ background: var(--text-secondary); }}

/* ── Loading shimmer ── */
@keyframes shimmer {{
    0% {{ background-position: -200% 0; }}
    100% {{ background-position: 200% 0; }}
}}
.shimmer {{
    background: linear-gradient(90deg, var(--card-bg) 25%, var(--card-border) 50%, var(--card-bg) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 8px;
    height: 20px;
    margin-bottom: 0.5rem;
}}
</style>
"""
