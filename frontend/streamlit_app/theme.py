"""SHB brand theme for the Streamlit UI (Track C).

One place for the palette + the CSS blob so `app.py` stays about behaviour.
The palette follows SHB's identity: orange primary on a deep navy, with a warm
neutral surface. Everything is exposed as constants so charts/badges can reuse
the exact same values instead of re-typing hex codes.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# palette
# --------------------------------------------------------------------------- #
SHB_ORANGE = "#F58220"        # primary — SHB signature orange
SHB_ORANGE_DARK = "#E35F13"   # hover / pressed
SHB_ORANGE_SOFT = "#FFF3E8"   # tinted surface (user bubble, chips)
SHB_NAVY = "#16283C"          # headings, sidebar
SHB_NAVY_SOFT = "#22384F"     # sidebar hover
SHB_RED = "#D32027"           # SHB secondary — alerts
SHB_GREEN = "#1E9E6A"         # valid / grounded
SHB_AMBER = "#C77700"         # needs review
SURFACE = "#FFFFFF"
CANVAS = "#F5F6F8"
BORDER = "#E3E6EB"
TEXT = "#1B2733"
TEXT_MUTED = "#6B7785"

# status → (colour, icon, Vietnamese label)
STATUS_THEME = {
    "SOURCE_GROUNDED": (SHB_GREEN, "✅", "Có nguồn dẫn"),
    "DETERMINISTIC_CHECKS_PASSED": (SHB_GREEN, "✅", "Qua kiểm tra xác định"),
    "HUMAN_REVIEWED": (SHB_GREEN, "✅", "Đã người duyệt"),
    "NEEDS_REVIEW": (SHB_AMBER, "⚠️", "Cần rà soát"),
    "INSUFFICIENT_EVIDENCE": (SHB_RED, "⛔", "Không đủ bằng chứng"),
}


def status_parts(status: str | None) -> tuple[str, str, str]:
    """(colour, icon, label) for an answer status — never raises on unknown values."""
    return STATUS_THEME.get(status or "", (TEXT_MUTED, "•", status or "Không rõ"))


# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #
def css() -> str:
    """The full stylesheet, injected once per run via st.markdown(unsafe_allow_html)."""
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}}
.stApp {{ background: {CANVAS}; color: {TEXT}; }}

/* hide Streamlit chrome so the app reads as a product, not a notebook */
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 1rem; max-width: 60rem; }}

/* ----------------------------- sidebar ---------------------------------- */
section[data-testid="stSidebar"] {{
    background: {SHB_NAVY};
    border-right: 1px solid rgba(255,255,255,.06);
}}
section[data-testid="stSidebar"] * {{ color: #E8EDF3; }}
section[data-testid="stSidebar"] .stButton > button {{
    width: 100%;
    text-align: left;
    justify-content: flex-start;
    background: transparent;
    border: 1px solid transparent;
    color: #D7DEE7;
    font-weight: 500;
    padding: .5rem .7rem;
    border-radius: 8px;
    transition: background .15s ease, border-color .15s ease;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    background: {SHB_NAVY_SOFT};
    border-color: rgba(255,255,255,.10);
    color: #FFFFFF;
}}
/* the "new chat" CTA — first button in the sidebar */
section[data-testid="stSidebar"] .shb-newchat + div .stButton > button,
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background: {SHB_ORANGE};
    border-color: {SHB_ORANGE};
    color: #FFFFFF;
    font-weight: 600;
    justify-content: center;
    text-align: center;
}}
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
    background: {SHB_ORANGE_DARK};
    border-color: {SHB_ORANGE_DARK};
}}

.shb-brand {{
    display: flex; align-items: center; gap: .6rem;
    padding: .2rem 0 .9rem 0;
}}
.shb-brand-mark {{
    width: 34px; height: 34px; border-radius: 9px;
    background: linear-gradient(135deg, {SHB_ORANGE} 0%, {SHB_RED} 100%);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 700; font-size: .82rem; letter-spacing: .02em;
}}
.shb-brand-text {{ line-height: 1.15; }}
.shb-brand-text b {{ font-size: .96rem; color: #FFFFFF; }}
.shb-brand-text span {{ font-size: .72rem; color: #9FB0C2; }}

/* account menu: expander must sit on the navy sidebar, not a white card */
section[data-testid="stSidebar"] div[data-testid="stExpander"] details {{
    background: {SHB_NAVY_SOFT};
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 10px;
}}
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {{
    color: #FFFFFF; font-weight: 600; font-size: .86rem;
}}
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary:hover {{
    color: {SHB_ORANGE};
}}
section[data-testid="stSidebar"] div[data-testid="stExpander"] .shb-user {{
    background: rgba(0,0,0,.18);
}}
section[data-testid="stSidebar"] input {{
    background: rgba(0,0,0,.22); color: #EAF0F6;
    border: 1px solid rgba(255,255,255,.14); border-radius: 8px;
}}
section[data-testid="stSidebar"] input:focus {{
    border-color: {SHB_ORANGE};
}}
/* logout reads as a destructive-ish action, not a nav item */
section[data-testid="stSidebar"] .stButton > button[kind="secondary"][data-testid*="logout"] {{
    justify-content: center;
}}

.shb-side-label {{
    font-size: .70rem; font-weight: 600; letter-spacing: .09em;
    text-transform: uppercase; color: #7E90A4;
    margin: 1.1rem 0 .35rem 0;
}}

/* user card pinned in the sidebar */
.shb-user {{
    display: flex; align-items: center; gap: .65rem;
    padding: .65rem .7rem; margin-top: .4rem;
    background: {SHB_NAVY_SOFT}; border: 1px solid rgba(255,255,255,.08);
    border-radius: 10px;
}}
.shb-avatar {{
    width: 34px; height: 34px; border-radius: 50%; flex: 0 0 34px;
    background: linear-gradient(135deg, {SHB_ORANGE} 0%, {SHB_ORANGE_DARK} 100%);
    color: #fff; font-weight: 700; font-size: .9rem;
    display: flex; align-items: center; justify-content: center;
}}
.shb-user-meta {{ line-height: 1.2; overflow: hidden; }}
.shb-user-meta b {{ font-size: .86rem; color: #FFFFFF; }}
.shb-user-meta span {{ font-size: .72rem; color: #9FB0C2; }}

/* --------------------------- chat surface -------------------------------- */
.shb-hero {{
    text-align: center; padding: 3.2rem 1rem 1.4rem 1rem;
}}
.shb-hero h1 {{
    font-size: 1.75rem; font-weight: 700; color: {SHB_NAVY}; margin: .6rem 0 .35rem 0;
}}
.shb-hero p {{ color: {TEXT_MUTED}; font-size: .95rem; margin: 0; }}
.shb-hero-mark {{
    width: 54px; height: 54px; border-radius: 15px; margin: 0 auto;
    background: linear-gradient(135deg, {SHB_ORANGE} 0%, {SHB_RED} 100%);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 700; font-size: 1.05rem;
}}

div[data-testid="stChatMessage"] {{
    background: transparent; padding: .35rem 0;
}}
/* assistant answer card */
.shb-card {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
    padding: 1rem 1.1rem; box-shadow: 0 1px 2px rgba(16,40,64,.04);
}}
.shb-card + .shb-card {{ margin-top: .6rem; }}

.shb-badge {{
    display: inline-flex; align-items: center; gap: .35rem;
    font-size: .76rem; font-weight: 600; padding: .18rem .6rem;
    border-radius: 999px; border: 1px solid currentColor;
}}
.shb-chip {{
    display: inline-block; font-size: .74rem; font-weight: 500;
    padding: .2rem .55rem; margin: .15rem .3rem .15rem 0;
    border-radius: 6px; background: {SHB_ORANGE_SOFT};
    color: {SHB_ORANGE_DARK}; border: 1px solid #F7D9BF;
}}
.shb-cite {{
    font-size: .84rem; color: {TEXT}; padding: .45rem .6rem;
    border-left: 3px solid {SHB_ORANGE}; background: #FAFBFC;
    border-radius: 0 6px 6px 0; margin-bottom: .35rem;
}}
.shb-cite small {{ color: {TEXT_MUTED}; }}
.shb-sec {{
    font-size: .74rem; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: {TEXT_MUTED}; margin: .9rem 0 .4rem 0;
}}

/* ---------------------- composer (mode buttons + input) ------------------ */
.shb-modes {{ margin: .5rem 0 .25rem 0; }}
.shb-modes .stButton > button {{
    width: 100%; border-radius: 999px; font-size: .85rem; font-weight: 600;
    padding: .38rem .8rem; border: 1px solid {BORDER};
    background: {SURFACE}; color: {TEXT_MUTED};
    transition: all .15s ease;
}}
.shb-modes .stButton > button:hover {{
    border-color: {SHB_ORANGE}; color: {SHB_ORANGE_DARK};
}}
.shb-modes .stButton > button[kind="primary"] {{
    background: {SHB_ORANGE_SOFT}; border-color: {SHB_ORANGE};
    color: {SHB_ORANGE_DARK};
}}

div[data-testid="stChatInput"] {{
    border: 1px solid {BORDER}; border-radius: 14px; background: {SURFACE};
    box-shadow: 0 2px 10px rgba(16,40,64,.06);
}}
div[data-testid="stChatInput"]:focus-within {{
    border-color: {SHB_ORANGE};
    box-shadow: 0 0 0 3px rgba(245,130,32,.14);
}}

/* main-area buttons default to the SHB accent */
.stApp .main .stButton > button[kind="primary"] {{
    background: {SHB_ORANGE}; border-color: {SHB_ORANGE}; color: #fff; font-weight: 600;
}}
.stApp .main .stButton > button[kind="primary"]:hover {{
    background: {SHB_ORANGE_DARK}; border-color: {SHB_ORANGE_DARK};
}}

/* expanders ("Vì sao câu trả lời này") */
div[data-testid="stExpander"] details {{
    border: 1px solid {BORDER}; border-radius: 10px; background: {SURFACE};
}}
div[data-testid="stExpander"] summary {{ font-weight: 600; color: {SHB_NAVY}; }}

.shb-disclaimer {{
    text-align: center; font-size: .74rem; color: {TEXT_MUTED}; margin-top: .45rem;
}}
</style>
"""
