from __future__ import annotations

import html
import os
from typing import Any
from urllib.parse import urlparse

import httpx
import streamlit as st

st.set_page_config(
    page_title="JanScope AI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)


CSS = """
<style>
    :root {
        --paper:#f6f2e9; --paper-deep:#eee8da; --card:#fffdf8; --ink:#26332b;
        --muted:#6f766d; --line:#ded8ca; --terracotta:#c65f3c; --terracotta-dark:#9d4229;
        --olive:#66734e; --olive-soft:#e8ecd9; --sand:#ead5b5;
    }
    html, body, [class*="css"] { font-family: "Aptos", "Segoe UI", sans-serif; }
    .stApp {
        color:var(--ink);
        background:
            radial-gradient(circle at 88% 4%, rgba(198,95,60,.10), transparent 24rem),
            linear-gradient(115deg, rgba(255,255,255,.22) 1px, transparent 1px), var(--paper);
        background-size:auto, 28px 28px, auto;
    }
    .block-container { max-width:1280px; padding-top:2rem; padding-bottom:3rem; }
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stSidebar"] {
        background:rgba(255,253,248,.94); border-right:1px solid var(--line);
        box-shadow:12px 0 40px rgba(54,48,34,.045);
    }
    [data-testid="stSidebar"] * { color:var(--ink); }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        padding:.66rem .78rem; border-radius:.85rem; margin:.16rem 0; border:1px solid transparent;
        transition:all .18s ease;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background:var(--paper); border-color:var(--line); transform:translateX(3px);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background:var(--olive-soft); border-color:#cbd2b6; font-weight:700;
    }
    [data-testid="stSidebar"] hr { border-color:var(--line); }
    .brand { display:flex; gap:.75rem; align-items:center; margin:.4rem 0 1.45rem; }
    .brand-mark { width:48px; height:48px; border-radius:15px 15px 15px 4px; display:grid; place-items:center;
        background:var(--ink); color:#fff9ec; font-size:24px; box-shadow:5px 5px 0 var(--sand); }
    .brand-name { font-family:Georgia,serif; font-size:1.48rem; font-weight:700; line-height:1.05; letter-spacing:-.03em; }
    .brand-name span { color:var(--terracotta); }
    .brand-sub { color:var(--muted)!important; font-size:.72rem; margin-top:.25rem; letter-spacing:.12em; text-transform:uppercase; }
    .hero { position:relative; overflow:hidden; background:var(--ink); color:#fffdf8;
        border-radius:1.4rem 1.4rem 1.4rem .35rem; padding:2.15rem 2.2rem; margin-bottom:1.35rem;
        box-shadow:9px 10px 0 var(--sand); border:1px solid #36483d; }
    .hero:after { content:""; position:absolute; width:190px; height:190px; right:-38px; top:-70px;
        border:38px solid var(--terracotta); border-radius:50%; opacity:.9; }
    .hero:before { content:"JAN / SCOPE"; position:absolute; right:1.65rem; bottom:.85rem; color:#d8dec9;
        opacity:.38; font-size:.65rem; letter-spacing:.22em; }
    .hero .eyebrow { color:#e9c89d; text-transform:uppercase; letter-spacing:.16em; font-size:.7rem; font-weight:700; margin-bottom:.55rem; }
    .hero h1 { font-family:Georgia,serif; margin:0 0 .5rem; font-size:clamp(2rem,4vw,3.25rem); line-height:1; letter-spacing:-.035em; max-width:78%; }
    .hero p { margin:0; color:#dbe0d7; font-size:1rem; max-width:68%; line-height:1.55; }
    .surface { background:rgba(255,253,248,.88); border:1px solid var(--line); border-radius:1.05rem 1.05rem 1.05rem .3rem; padding:1.05rem 1.12rem;
        box-shadow:0 8px 24px rgba(54,48,34,.055); margin-bottom:.8rem; }
    .surface h3 { margin:.05rem 0 .5rem; font-size:1.05rem; }
    .scheme-card { position:relative; background:var(--card); border:1px solid var(--line); border-radius:1.1rem 1.1rem .35rem 1.1rem; padding:1.15rem;
        min-height:245px; box-shadow:0 8px 22px rgba(54,48,34,.055); transition:transform .18s ease, box-shadow .18s ease; }
    .scheme-card:hover { transform:translateY(-4px); box-shadow:0 15px 30px rgba(54,48,34,.09); }
    .scheme-card:before { content:""; display:block; width:34px; height:4px; border-radius:5px; background:var(--terracotta); margin-bottom:.85rem; }
    .scheme-title { font-family:Georgia,serif; font-weight:700; font-size:1.08rem; min-height:48px; }
    .badge { display:inline-block; border-radius:999px; padding:.2rem .52rem; font-size:.72rem;
        background:var(--olive-soft); color:#4c5a35; margin:.25rem .2rem .5rem 0; font-weight:700; }
    .badge.orange { background:#f5e2d5; color:var(--terracotta-dark); }
    .muted { color:var(--muted); font-size:.84rem; }
    .profile-row { display:flex; justify-content:space-between; border-bottom:1px solid #e8e2d6;
        padding:.42rem 0; gap:1rem; }
    .profile-row:last-child { border:0; }
    .profile-label { color:var(--muted); }
    .profile-value { font-weight:680; text-align:right; }
    .eligibility-good { border-left:5px solid var(--olive); }
    .eligibility-maybe { border-left:5px solid #d79a42; }
    .eligibility-no { border-left:5px solid var(--terracotta); }
    .source-card { border:1px solid var(--line); background:var(--card); border-radius:.9rem .9rem .9rem .25rem; padding:.8rem .9rem; margin:.5rem 0; }
    .source-number { display:inline-grid; place-items:center; width:24px; height:24px; border-radius:50%;
        background:var(--ink); color:#fffdf8; font-weight:750; margin-right:.45rem; }
    .notice { border:1px solid #dfc298; background:#fbefdc; color:#67492e; border-radius:.85rem .85rem .85rem .25rem; padding:.78rem .9rem; }
    .public-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.8rem; margin:.7rem 0 1.35rem; }
    .public-card { background:var(--card); border:1px solid var(--line); border-radius:1rem 1rem 1rem .28rem; padding:1rem; min-height:125px; }
    .public-card .step { color:var(--terracotta); font:700 .7rem/1 Georgia,serif; letter-spacing:.12em; text-transform:uppercase; }
    .public-card h3 { font-family:Georgia,serif; margin:.45rem 0 .35rem; font-size:1.05rem; }
    .public-card p { color:var(--muted); font-size:.84rem; line-height:1.5; margin:0; }
    .question-chip { display:inline-block; background:var(--olive-soft); border:1px solid #cfd5bd; color:#435035; border-radius:999px; padding:.45rem .7rem; margin:.2rem; font-size:.82rem; }
    .welcome-shell { max-width:1120px; margin:0 auto; padding:.15rem 0 1rem; }
    .welcome-brand { display:flex; align-items:center; gap:.8rem; margin-bottom:.85rem; }
    div[data-testid="stHorizontalBlock"]:has(.welcome-hero) {
        position:relative; overflow:hidden; min-height:100vh; min-height:100svh; padding:0; gap:0;
        border:0; border-radius:0;
        background:
            radial-gradient(circle at 57% -17%, rgba(198,95,60,.92) 0 88px, transparent 89px),
            linear-gradient(90deg, #26332b 0%, #26332b 42%, rgba(38,51,43,.88) 51%, rgba(38,51,43,.30) 65%, rgba(246,242,233,.68) 79%, rgba(246,242,233,.96) 100%);
        box-shadow:none;
    }
    div[data-testid="stHorizontalBlock"]:has(.welcome-hero):after {
        content:"JAN / SCOPE"; position:absolute; right:1.6rem; bottom:.8rem; z-index:0;
        color:var(--ink); opacity:.055; font:700 clamp(3rem,7vw,6.5rem)/1 Georgia,serif;
        letter-spacing:.08em; white-space:nowrap; pointer-events:none;
    }
    div[data-testid="stHorizontalBlock"]:has(.welcome-hero) > div[data-testid="stColumn"] { position:relative; z-index:1; }
    div[data-testid="stHorizontalBlock"]:has(.welcome-hero) > div[data-testid="stColumn"]:last-child { padding:clamp(3.8rem,8vh,6rem) 2.4rem 2rem 1rem; }
    .welcome-hero { position:relative; overflow:hidden; background:transparent; color:#fffdf8; border-radius:0; padding:6.5rem 3.6rem 3rem; box-shadow:none; min-height:100vh; min-height:100svh; display:flex; flex-direction:column; justify-content:center; }
    .welcome-hero:after { display:none; }
    .welcome-hero > * { position:relative; z-index:1; }
    .welcome-brand-on-hero { position:absolute!important; left:3.6rem; top:2rem; z-index:3!important; margin:0; }
    .welcome-brand-on-hero .brand-mark { background:#fffdf8; color:var(--ink); box-shadow:5px 5px 0 rgba(234,213,181,.55); }
    .welcome-brand-on-hero .brand-name { color:#fffdf8; }
    .welcome-brand-on-hero .brand-sub { color:#cbd3ca!important; }
    .welcome-kicker { color:#e9c89d; text-transform:uppercase; letter-spacing:.18em; font-size:.72rem; font-weight:800; animation:welcomeFade .55s ease-out .08s both; }
    .welcome-hero h1 { position:relative; font-family:Georgia,serif; color:#fffdf8; font-size:clamp(2.65rem,4.5vw,4.5rem); letter-spacing:-.045em; line-height:.98; max-width:650px; margin:.8rem 0 1rem; animation:headlineReveal .9s cubic-bezier(.2,.75,.25,1) .14s both; }
    .welcome-hero h1:after { content:""; display:block; width:96px; height:4px; margin-top:.72rem; border-radius:5px; background:linear-gradient(90deg,var(--terracotta),#e7b27c); transform-origin:left; animation:accentSweep .8s cubic-bezier(.2,.8,.2,1) .72s both; }
    .welcome-hero p { color:#dbe0d7; max-width:620px; font-size:1.05rem; line-height:1.65; margin:0; animation:welcomeFade .65s ease-out .48s both; }
    .welcome-points { display:flex; flex-wrap:wrap; gap:.55rem; margin-top:1.5rem; animation:welcomeFade .65s ease-out .64s both; }
    .welcome-point { border:1px solid #536157; color:#eef0e8; border-radius:999px; padding:.42rem .72rem; font-size:.78rem; }
    .access-heading { padding:.15rem .2rem .25rem; }
    .access-heading .access-kicker { color:var(--terracotta-dark); text-transform:uppercase; letter-spacing:.15em; font-size:.68rem; font-weight:800; }
    .access-heading h2 { margin:.28rem 0 .25rem; font-size:1.75rem; }
    .access-heading p { color:var(--muted); margin:0 0 .35rem; font-size:.86rem; }
    .access-card { background:var(--card); border:1px solid var(--line); border-radius:1.15rem 1.15rem 1.15rem .3rem; padding:.78rem .9rem; min-height:82px; margin-top:.35rem; box-shadow:0 7px 22px rgba(54,48,34,.045); }
    .access-card.primary-card { min-height:118px; }
    .access-card.demo-card { min-height:72px; }
    .access-card h3 { font-family:Georgia,serif; margin:0 0 .22rem; font-size:1.08rem; }
    .access-card p { color:var(--muted); font-size:.79rem; line-height:1.4; margin:0; }
    .access-trust { display:flex; gap:.45rem; flex-wrap:wrap; margin:.45rem 0 .15rem; }
    .access-trust span { background:var(--olive-soft); color:#4d593b; border-radius:999px; padding:.3rem .52rem; font-size:.7rem; font-weight:700; }
    @keyframes headlineReveal {
        from { opacity:0; transform:translateX(-46px) scale(.985); filter:blur(7px); }
        to { opacity:1; transform:translateX(0) scale(1); filter:blur(0); }
    }
    @keyframes welcomeFade {
        from { opacity:0; transform:translateY(10px); }
        to { opacity:1; transform:translateY(0); }
    }
    @keyframes accentSweep {
        from { opacity:0; transform:scaleX(0); }
        to { opacity:1; transform:scaleX(1); }
    }
    @media (prefers-reduced-motion: reduce) {
        .welcome-kicker, .welcome-hero h1, .welcome-hero h1:after, .welcome-hero p, .welcome-points { animation:none!important; }
    }
    .privacy-line { text-align:center; color:var(--muted); font-size:.78rem; margin-top:1.2rem; }
    .footer-note { color:var(--muted)!important; font-size:.73rem; line-height:1.45; padding:.8rem .2rem; }
    div[data-testid="stChatMessage"] { background:rgba(255,253,248,.9); border:1px solid var(--line); border-radius:1rem 1rem 1rem .28rem; padding:.5rem .7rem; }
    div[data-testid="stMetric"] { background:var(--card); border:1px solid var(--line); border-radius:1rem 1rem .3rem 1rem; padding:.9rem 1rem; box-shadow:0 6px 18px rgba(54,48,34,.04); }
    div[data-testid="stMetricValue"] { font-family:Georgia,serif; color:var(--terracotta-dark); font-size:clamp(1.45rem,2.2vw,2rem); white-space:nowrap; }
    div[data-testid="stAlert"] { background:var(--olive-soft); border:1px solid #cdd4b9; border-radius:1rem 1rem 1rem .28rem; color:var(--ink); }
    div[data-testid="stAlert"] a { color:var(--terracotta-dark); }
    [data-testid="stExpander"] { background:rgba(255,253,248,.72); border:1px solid var(--line)!important; border-radius:.9rem!important; }
    .stButton button, .stDownloadButton button, .stLinkButton a { border-radius:.75rem .75rem .75rem .22rem!important; font-weight:700!important; border-color:#cfc7b7!important; }
    .stButton button[kind="primary"], button[kind="primaryFormSubmit"] { background:var(--terracotta)!important; border-color:var(--terracotta)!important; color:white!important; }
    .stButton button:hover, .stDownloadButton button:hover, .stLinkButton a:hover { border-color:var(--terracotta)!important; color:var(--terracotta-dark)!important; }
    .stButton button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover { background:var(--terracotta-dark)!important; color:white!important; }
    input, textarea, [data-baseweb="select"] > div { background:var(--card)!important; border-color:#d6cfbf!important; border-radius:.72rem!important; }
    [data-testid="stForm"] { background:rgba(255,253,248,.52); border:1px solid var(--line); border-radius:1.2rem 1.2rem 1.2rem .35rem; padding:1.2rem; }
    h1, h2, h3 { color:var(--ink); }
    h2 { font-family:Georgia,serif; letter-spacing:-.02em; }
    a { color:var(--terracotta-dark); }
    @media (max-width: 700px) {
        .block-container { padding-top:1rem; }
        .hero { padding:1.6rem 1.4rem; }
        .hero h1 { max-width:90%; font-size:2rem; }
        .hero p { max-width:92%; font-size:.9rem; }
        .hero:after { width:120px; height:120px; right:-55px; top:-45px; border-width:25px; }
        .public-grid { grid-template-columns:1fr; }
        .scheme-card { min-height:auto; }
        div[data-testid="stHorizontalBlock"] { gap:.65rem; }
        div[data-testid="stHorizontalBlock"]:has(.welcome-hero) {
            background:
                radial-gradient(circle at 92% -3%, rgba(198,95,60,.9) 0 58px, transparent 59px),
                linear-gradient(180deg, #26332b 0%, #26332b 35%, rgba(38,51,43,.88) 43%, rgba(246,242,233,.92) 58%, rgba(246,242,233,.98) 100%);
        }
        div[data-testid="stHorizontalBlock"]:has(.welcome-hero) > div[data-testid="stColumn"]:last-child { padding:1rem 1rem 1.5rem; min-height:45svh; }
        div[data-testid="stHorizontalBlock"]:has(.welcome-hero):after { font-size:3rem; bottom:.5rem; right:.5rem; }
        .welcome-hero { padding:6rem 1.4rem 2.2rem; min-height:55svh; }
        .welcome-brand-on-hero { left:1.4rem; top:1.15rem; }
        .welcome-brand-on-hero .brand-mark { width:42px; height:42px; font-size:20px; }
        .welcome-brand-on-hero .brand-name { font-size:1.2rem; }
        .welcome-brand-on-hero .brand-sub { font-size:.62rem; }
        .welcome-hero h1 { font-size:2.15rem; max-width:92%; }
        .welcome-hero p { max-width:92%; font-size:.92rem; }
        .access-heading { margin-top:1rem; }
    }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


class APIError(RuntimeError):
    pass


def friendly_api_error(response: httpx.Response) -> str:
    """Turn API failures into short, actionable messages for every frontend page."""
    try:
        payload = response.json()
    except Exception:
        payload = {}
    field_errors = payload.get("field_errors") if isinstance(payload, dict) else None
    if response.status_code == 422:
        if field_errors:
            return "Please review the form:\n\n" + "\n".join(f"• {item}" for item in field_errors)
        return "Some information is missing or invalid. Please review the form and try again."
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if response.status_code == 400 and isinstance(detail, str) and len(detail) <= 180:
        return detail.rstrip(".") + "."
    messages = {
        400: "Some information could not be accepted. Please review it and try again.",
        401: "Administrator authorization is required for this action.",
        403: "This conversation is protected or the session has expired. Start a new conversation.",
        404: "The requested information is no longer available. Refresh the page and try again.",
        409: "This information was changed elsewhere. Refresh the page and try again.",
        413: "That request is too large. Please shorten it and try again.",
        429: "JanScope is receiving many requests. Please wait a moment and try again.",
        500: "JanScope encountered a temporary problem. Please try again shortly.",
        502: "An external information service is temporarily unavailable. Please try again later.",
        503: "JanScope is temporarily unavailable. Please try again in a few minutes.",
        504: "An external service took too long to respond. Please try again.",
    }
    if response.status_code in messages:
        return messages[response.status_code]
    return "JanScope could not complete that request. Please try again."


class JanScopeAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            headers = dict(kwargs.pop("headers", {}) or {})
            token = st.session_state.get("auth_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
            with httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
                response = client.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
            if response.status_code >= 400:
                raise APIError(friendly_api_error(response))
            if response.status_code == 204:
                return None
            return response.json()
        except httpx.ConnectError as exc:
            raise APIError("Cannot reach the backend. Start it with run_backend.bat first.") from exc
        except httpx.TimeoutException as exc:
            raise APIError("The backend took too long to respond. Please try again.") from exc
        except httpx.RequestError as exc:
            raise APIError("A network error interrupted the request. Check your connection and try again.") from exc

    def health(self):
        return self._request("GET", "/api/v1/health")

    def request_otp(self, email: str, purpose: str):
        return self._request("POST", "/api/v1/auth/request-otp", json={"email": email, "purpose": purpose})

    def verify_otp(self, challenge_id: str, code: str):
        return self._request("POST", "/api/v1/auth/verify-otp", json={"challenge_id": challenge_id, "code": code})

    def logout(self):
        return self._request("POST", "/api/v1/auth/logout")

    def schemes(self, state: str | None = None, category: str | None = None):
        params = {key: value for key, value in {"state": state, "category": category}.items() if value}
        return self._request("GET", "/api/v1/schemes", params=params)

    def scheme(self, slug: str):
        return self._request("GET", f"/api/v1/schemes/{slug}")

    def chat(self, payload: dict):
        return self._request("POST", "/api/v1/chat", json=payload)

    def eligibility(self, payload: dict):
        return self._request("POST", "/api/v1/eligibility/check", json=payload)

    def grievance(self, payload: dict):
        return self._request("POST", "/api/v1/grievances/draft", json=payload)

    def conversation(self, conversation_id: str, token: str):
        return self._request(
            "GET",
            f"/api/v1/conversations/{conversation_id}",
            headers={"X-Conversation-Token": token},
        )


def init_state() -> None:
    defaults = {
        "backend_url": os.getenv("JANSCOPE_BACKEND_URL", "http://127.0.0.1:8000"),
        "conversation_id": None,
        "conversation_token": None,
        "chat_messages": [],
        "citizen_profile": {},
        "last_chat_response": None,
        "selected_language": "auto",
        "access_mode": None,
        "auth_token": None,
        "auth_email": None,
        "welcome_view": "landing",
        "otp_challenge_id": None,
        "otp_purpose": None,
        "development_otp": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()
api = JanScopeAPI(st.session_state.backend_url)


def reset_welcome() -> None:
    st.session_state.welcome_view = "landing"
    st.session_state.otp_challenge_id = None
    st.session_state.otp_purpose = None
    st.session_state.development_otp = None


def page_welcome() -> None:
    st.markdown(
        '<style>[data-testid="stSidebar"]{display:none}'
        '.stApp,[data-testid="stHeader"]{background:linear-gradient(90deg,#26332b 0%,#26332b 42%,rgba(38,51,43,.88) 51%,rgba(38,51,43,.30) 65%,rgba(246,242,233,.68) 79%,rgba(246,242,233,.96) 100%)!important}'
        '[data-testid="stHeader"]{border:0!important;box-shadow:none!important}'
        '[data-testid="stToolbar"],[data-testid="stDecoration"]{background:transparent!important;border:0!important}'
        '.block-container{max-width:none!important;min-height:100svh!important;padding:0!important;margin:0!important}'
        '.welcome-shell{max-width:none}'
        '</style>',
        unsafe_allow_html=True,
    )
    view = st.session_state.welcome_view
    story_col, access_col = st.columns([1.45, 1], gap="large", vertical_alignment="top")
    with story_col:
        st.markdown(
            '<div class="welcome-hero"><div class="welcome-brand welcome-brand-on-hero"><div class="brand-mark">ज</div>'
            '<div><div class="brand-name">JanScope <span>AI</span></div><div class="brand-sub">Citizen companion</div></div></div>'
            '<div class="welcome-kicker">Government schemes · explained simply</div>'
            '<h1>Public support should feel easier to find.</h1>'
            '<p>Explore trusted scheme information, check provisional eligibility and prepare reviewable grievances—in English, हिन्दी or Hinglish.</p>'
            '<div class="welcome-points"><span class="welcome-point">Official-source citations</span>'
            '<span class="welcome-point">Private by design</span><span class="welcome-point">No government affiliation</span></div></div>',
            unsafe_allow_html=True,
        )
    with access_col:
        if view == "landing":
            st.markdown(
                '<div class="access-heading"><div class="access-kicker">Secure access</div>'
                '<h2>Start with JanScope</h2><p>Choose the option that works best for you.</p></div>',
                unsafe_allow_html=True,
            )
            login_col, create_col = st.columns(2, gap="small")
            with login_col:
                st.markdown('<div class="access-card primary-card"><h3>Welcome back</h3><p>Continue securely with a one-time email code.</p></div>', unsafe_allow_html=True)
                if st.button("Log in", type="primary", use_container_width=True):
                    st.session_state.welcome_view = "login"
                    st.rerun()
            with create_col:
                st.markdown('<div class="access-card primary-card"><h3>New here?</h3><p>Verify your email and create a free account.</p></div>', unsafe_allow_html=True)
                if st.button("Create account", type="primary", use_container_width=True):
                    st.session_state.welcome_view = "register"
                    st.rerun()
            st.markdown('<div class="access-card demo-card"><h3>Explore without signing up</h3><p>Open the complete Demo now. Account history will not be saved.</p></div>', unsafe_allow_html=True)
            if st.button("Continue in Demo", type="primary", use_container_width=True):
                st.session_state.access_mode = "demo"
                st.rerun()
            st.markdown('<div class="access-trust"><span>No password</span><span>10-minute OTP</span><span>Demo available</span></div>', unsafe_allow_html=True)
        elif view in {"login", "register"}:
            title = "Log in to JanScope" if view == "login" else "Create your JanScope account"
            st.markdown(f"### {title}")
            st.caption("We’ll email a 6-digit code. No password is required.")
            with st.form("email_otp_request"):
                email = st.text_input("Email address", placeholder="you@example.com", max_chars=320)
                sent = st.form_submit_button("Send verification code", type="primary", use_container_width=True)
            if sent:
                if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                    st.error("Enter a valid email address, such as name@example.com.")
                else:
                    try:
                        with st.spinner("Sending your secure code..."):
                            result = api.request_otp(email.strip(), view)
                        st.session_state.otp_challenge_id = result["challenge_id"]
                        st.session_state.otp_purpose = view
                        st.session_state.development_otp = result.get("development_code")
                        st.session_state.welcome_view = "verify"
                        st.rerun()
                    except APIError as exc:
                        st.error(str(exc))
            if st.button("← Back"):
                reset_welcome()
                st.rerun()
        elif view == "verify":
            st.markdown("### Enter your verification code")
            st.caption("The code expires in 10 minutes. Check your spam folder if it doesn’t arrive.")
            if st.session_state.development_otp:
                st.info(f"Local development code: {st.session_state.development_otp}")
            with st.form("otp_verify"):
                code = st.text_input("6-digit code", max_chars=6, placeholder="000000")
                verified = st.form_submit_button("Verify and continue", type="primary", use_container_width=True)
            if verified:
                if not (code.isdigit() and len(code) == 6):
                    st.error("Enter the complete 6-digit code from your email.")
                else:
                    try:
                        with st.spinner("Verifying securely..."):
                            result = api.verify_otp(st.session_state.otp_challenge_id, code)
                        st.session_state.auth_token = result["access_token"]
                        st.session_state.auth_email = result["email"]
                        st.session_state.access_mode = "account"
                        reset_welcome()
                        st.rerun()
                    except APIError as exc:
                        st.error(str(exc))
            if st.button("Request another code"):
                st.session_state.welcome_view = st.session_state.otp_purpose or "login"
                st.session_state.otp_challenge_id = None
                st.rerun()
        st.markdown('<div class="privacy-line">JanScope never asks for Aadhaar, bank credentials or government-portal passwords.</div>', unsafe_allow_html=True)


def backend_health(show_error: bool = False) -> dict | None:
    try:
        return api.health()
    except APIError as exc:
        if show_error:
            st.error(str(exc))
        return None


def sidebar() -> str:
    with st.sidebar:
        st.markdown(
            '<div class="brand"><div class="brand-mark">ज</div><div><div class="brand-name">JanScope <span>AI</span></div>'
            '<div class="brand-sub">Citizen companion</div></div></div>',
            unsafe_allow_html=True,
        )
        page = st.radio(
            "Navigation",
            [
                "🏠 Home",
                "💬 AI Assistant",
                "🔎 Discover Schemes",
                "🛡️ Eligibility Check",
                "📝 Grievance Draft",
                "🕘 Conversation History",
                "⚙️ Settings",
            ],
            label_visibility="collapsed",
        )
        st.markdown("---")
        health = backend_health()
        if health:
            mode = "Gemini AI" if health["ai_mode"] == "gemini" else "Demo mode"
            st.success(f"● Backend connected · {mode}")
        else:
            st.error("● Backend offline")
        if st.session_state.access_mode == "account":
            st.caption(f"Signed in as {st.session_state.auth_email}")
            if st.button("Log out", use_container_width=True):
                try:
                    api.logout()
                except APIError:
                    pass
                st.session_state.auth_token = None
                st.session_state.auth_email = None
                st.session_state.access_mode = None
                st.session_state.conversation_id = None
                st.session_state.conversation_token = None
                st.session_state.chat_messages = []
                reset_welcome()
                st.rerun()
        else:
            st.caption("Using JanScope in Demo mode")
            if st.button("Leave Demo", use_container_width=True):
                st.session_state.access_mode = None
                st.session_state.conversation_id = None
                st.session_state.conversation_token = None
                st.session_state.chat_messages = []
                reset_welcome()
                st.rerun()
        st.markdown(
            '<div class="footer-note">ℹ️ JanScope AI is an informational student project and is not affiliated with any government entity.<br><br>'
            "Always verify information on official government portals.</div>",
            unsafe_allow_html=True,
        )
    return page


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="hero"><div class="eyebrow">Public services · made clearer</div>'
        f'<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def scheme_cards(items: list[dict], limit: int = 3) -> None:
    if not items:
        st.info("No schemes matched the selected filters.")
        return
    columns = st.columns(min(3, len(items[:limit])))
    for column, scheme in zip(columns, items[:limit]):
        with column:
            name = html.escape(scheme.get("short_name") or scheme["name"])
            description = html.escape(scheme.get("description", ""))
            benefit = html.escape(scheme.get("benefits", ""))
            st.markdown(
                f'<div class="scheme-card"><div class="scheme-title">🌾 {name}</div>'
                f'<span class="badge">{html.escape(scheme.get("category", "Scheme"))}</span>'
                f'<span class="badge orange">{html.escape(scheme.get("level", ""))}</span>'
                f'<div class="muted">{description[:180]}</div><hr>'
                f'<div style="font-size:.82rem"><b>Benefit:</b> {benefit[:180]}</div></div>',
                unsafe_allow_html=True,
            )
            st.link_button("Open official source ↗", scheme["official_url"], use_container_width=True)


def profile_panel(profile: dict) -> None:
    labels = {
        "age": "Age",
        "state": "State",
        "occupation": "Occupation",
        "annual_income": "Annual income",
        "gender": "Gender",
        "category": "Category",
        "education": "Education",
    }
    rows = []
    for key, label in labels.items():
        value = profile.get(key)
        if value is None:
            continue
        if key == "annual_income":
            value = f"₹{value:,.0f}"
        rows.append(
            f'<div class="profile-row"><span class="profile-label">{label}</span>'
            f'<span class="profile-value">{html.escape(str(value))}</span></div>'
        )
    st.markdown(
        '<div class="surface"><h3>👤 Citizen Profile</h3>'
        + ("".join(rows) if rows else '<div class="muted">No profile details extracted yet.</div>')
        + "</div>",
        unsafe_allow_html=True,
    )


def eligibility_cards(results: list[dict], limit: int = 4) -> None:
    for result in results[:limit]:
        status = result["status"]
        class_name = {"eligible": "eligibility-good", "potentially_eligible": "eligibility-maybe"}.get(
            status, "eligibility-no"
        )
        label = status.replace("_", " ").title()
        with st.container():
            st.markdown(
                f'<div class="surface {class_name}"><h3>{html.escape(result["scheme_name"])}</h3>'
                f"<b>{label}</b> · Match score {result['score']}%</div>",
                unsafe_allow_html=True,
            )
            left, right = st.columns(2)
            with left:
                if result["matched_rules"]:
                    st.markdown("**Matched conditions**")
                    for item in result["matched_rules"]:
                        st.markdown(f"✅ {item}")
            with right:
                if result["failed_rules"]:
                    st.markdown("**Failed conditions**")
                    for item in result["failed_rules"]:
                        st.markdown(f"❌ {item}")
                if result["missing_information"]:
                    st.markdown("**Missing information**")
                    for item in result["missing_information"]:
                        st.markdown(f"⚠️ {item.replace('_', ' ').title()}")
            st.caption(result["disclaimer"])


def source_cards(sources: list[dict]) -> None:
    if not sources:
        return
    st.subheader("Official Sources")
    for source in sources:
        st.markdown(
            f'<div class="source-card"><span class="source-number">{source["number"]}</span>'
            f"<b>{html.escape(source['scheme_name'])}</b><br>"
            f'<span class="muted">{html.escape(source["excerpt"][:260])}</span><br>'
            f'<a href="{html.escape(source["url"])}" target="_blank">Open official source ↗</a>'
            f' <span class="muted">· Dataset checked {html.escape(source.get("last_verified", ""))}</span></div>',
            unsafe_allow_html=True,
        )


def page_home() -> None:
    hero(
        "Namaste! How can JanScope help you?", "Find government schemes, check eligibility, and get source-grounded guidance."
    )
    health = backend_health(show_error=True)
    schemes = []
    if not health:
        st.info("JanScope’s service is temporarily unavailable. You can still explore how the project works below.")
    else:
        try:
            with st.spinner("Preparing verified scheme information..."):
                schemes = api.schemes()
        except APIError as exc:
            st.error(str(exc))
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Available schemes", len(schemes))
        m2.metric("AI mode", health["ai_mode"].title())
        m3.metric("Source search", health["vector_backend"].title())
        m4.metric("Languages", "EN · HI · Hinglish")
    st.subheader("What would you like to do?")
    c1, c2, c3 = st.columns(3)
    c1.info(
        "💬 **Ask JanScope**\n\nDescribe your situation naturally and receive relevant schemes with sources."
    )
    c2.info("🛡️ **Check eligibility**\n\nGet an explainable provisional result from deterministic rules.")
    c3.info("📝 **Draft a grievance**\n\nCreate a neutral English or Hindi draft for human review.")
    st.subheader("Featured schemes")
    scheme_cards(schemes, 3)
    st.markdown(
        '<div class="notice">⚠️ JanScope never guarantees eligibility. Final decisions rest with the relevant authority or lender.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("## How JanScope works")
    st.markdown(
        '<div class="public-grid">'
        '<div class="public-card"><div class="step">Step 01</div><h3>Tell us your situation</h3><p>Ask naturally in English, Hindi, or Hinglish. Share only details needed for your question.</p></div>'
        '<div class="public-card"><div class="step">Step 02</div><h3>Check trusted material</h3><p>JanScope searches indexed official-source summaries and applies explainable eligibility rules.</p></div>'
        '<div class="public-card"><div class="step">Step 03</div><h3>Verify before acting</h3><p>Review citations and confirm current rules, deadlines, and documents on the official portal.</p></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("## Example questions")
    st.markdown(
        '<span class="question-chip">Which schemes are available for farmers in Bihar?</span>'
        '<span class="question-chip">Can a 22-year-old student get a scholarship?</span>'
        '<span class="question-chip">मेरी पेंशन में देरी हुई है—मैं क्या करूँ?</span>'
        '<span class="question-chip">Help me draft a grievance for a delayed benefit.</span>',
        unsafe_allow_html=True,
    )
    st.markdown("## About the project")
    about, stack = st.columns([1.35, 1])
    with about:
        st.markdown(
            '<div class="surface"><h3>Citizen-first assistance</h3><div class="muted">JanScope is an open educational project that makes public-scheme information easier to explore. It combines conversational guidance, provisional rule checks, official-source citations, and reviewable grievance drafts.</div></div>',
            unsafe_allow_html=True,
        )
    with stack:
        st.markdown(
            '<div class="surface"><h3>Technology stack</h3><div class="muted">FastAPI · Streamlit · Gemini · LangGraph · ChromaDB · SQLAlchemy · SQLite</div></div>',
            unsafe_allow_html=True,
        )
    github_url = os.getenv("PROJECT_GITHUB_URL", "").strip()
    if github_url:
        st.link_button("View project on GitHub ↗", github_url)
    st.markdown(
        '<div class="notice"><b>Independent project disclaimer:</b> JanScope AI is not a Government of India website, is not affiliated with or endorsed by any government department, and cannot approve applications or guarantee benefits. Always verify information and apply through the relevant official government portal.</div>',
        unsafe_allow_html=True,
    )


def page_chat() -> None:
    hero(
        "Citizen Assistance",
        "Ask in English, हिन्दी, or Hinglish. Your profile is extracted only from details you provide.",
    )
    main, side = st.columns([1.9, 1], gap="large")
    with main:
        if not st.session_state.chat_messages:
            st.markdown("Try: `Mere pita ji 65 saal ke farmer hain, Bihar se. Kaunsi yojana mil sakti hai?`")
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        prompt = st.chat_input("Describe the citizen's situation...", max_chars=4000)
        if prompt:
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            payload = {
                "message": prompt,
                "conversation_id": st.session_state.conversation_id,
                "conversation_token": st.session_state.conversation_token,
                "profile": st.session_state.citizen_profile or None,
                "language": st.session_state.selected_language,
            }
            try:
                with st.spinner("Searching official-source summaries and checking rules..."):
                    result = api.chat(payload)
                st.session_state.conversation_id = result["conversation_id"]
                st.session_state.conversation_token = result["conversation_token"]
                st.session_state.citizen_profile = result["profile"]
                st.session_state.last_chat_response = result
                st.session_state.chat_messages.append({"role": "assistant", "content": result["answer"]})
                st.rerun()
            except APIError as exc:
                st.error(str(exc))
        result = st.session_state.last_chat_response
        if result:
            source_cards(result.get("sources", []))
            with st.expander("View workflow trace"):
                st.write(" → ".join(result.get("workflow_steps", [])))
                st.caption(f"Intent: {result['intent']} · Mode: {result['ai_mode']}")
    with side:
        profile_panel(st.session_state.citizen_profile)
        result = st.session_state.last_chat_response
        if result and result.get("eligibility"):
            st.markdown("### Provisional Eligibility")
            eligibility_cards(result["eligibility"], 2)
        st.markdown(
            '<div class="notice">AI responses may be incomplete. Open every source and verify current eligibility, dates and documents.</div>',
            unsafe_allow_html=True,
        )


def page_discover() -> None:
    hero("Discover Schemes", "Filter the curated catalogue and open the official source before applying.")
    c1, c2 = st.columns(2)
    state = c1.selectbox("State", ["All", "Bihar", "Jharkhand", "Delhi", "Uttar Pradesh", "Maharashtra"])
    category = c2.selectbox(
        "Category",
        [
            "All",
            "Agriculture",
            "Pension",
            "Credit",
            "Education",
            "Skill and Enterprise",
            "Urban Livelihood",
            "Entrepreneurship",
        ],
    )
    try:
        schemes = api.schemes(None if state == "All" else state, None if category == "All" else category)
    except APIError as exc:
        st.error(str(exc))
        return
    st.caption(f"{len(schemes)} scheme(s) found")
    for scheme in schemes:
        with st.expander(f"{scheme['short_name'] or scheme['name']} · {scheme['category']}"):
            st.write(scheme["description"])
            st.markdown(f"**Benefit:** {scheme['benefits']}")
            st.markdown(f"**Coverage:** {', '.join(scheme['states'])}")
            st.caption(f"Dataset checked: {scheme['last_verified']}")
            st.link_button("Official source ↗", scheme["official_url"])


def page_eligibility() -> None:
    hero("Eligibility Check", "Enter known details. Missing information is reported instead of guessed.")
    with st.form("eligibility_form"):
        c1, c2, c3 = st.columns(3)
        age = c1.number_input("Age", min_value=0, max_value=125, value=22)
        income_known = c2.checkbox("Annual income is known", value=True)
        income = c2.number_input(
            "Annual income (₹)", min_value=0, value=150000, step=10000, disabled=not income_known
        )
        state = c3.selectbox(
            "State", ["Bihar", "Jharkhand", "Delhi", "Uttar Pradesh", "Maharashtra", "Other"]
        )
        c4, c5, c6 = st.columns(3)
        occupation = c4.selectbox(
            "Occupation",
            [
                "farmer",
                "student",
                "unorganised worker",
                "labourer",
                "street vendor",
                "artisan",
                "entrepreneur",
                "other",
            ],
        )
        gender = c5.selectbox("Gender (optional)", ["Not provided", "female", "male", "other"])
        category = c6.selectbox("Category (optional)", ["Not provided", "General", "OBC", "SC", "ST", "EWS"])
        education = st.selectbox(
            "Education (optional)",
            ["Not provided", "class 12", "diploma", "BTech", "undergraduate", "postgraduate"],
        )
        submitted = st.form_submit_button(
            "Check provisional eligibility", type="primary", use_container_width=True
        )
    if submitted:
        profile = {
            "age": age,
            "annual_income": income if income_known else None,
            "state": state,
            "occupation": occupation,
            "gender": None if gender == "Not provided" else gender,
            "category": None if category == "Not provided" else category,
            "education": None if education == "Not provided" else education,
        }
        try:
            result = api.eligibility({"profile": profile})
            st.session_state.citizen_profile = profile
            st.subheader("Results")
            eligibility_cards(result["results"], 8)
        except APIError as exc:
            st.error(str(exc))


def page_grievance() -> None:
    hero(
        "Grievance Draft",
        "Create a neutral draft from verified facts. JanScope never submits it automatically.",
    )
    with st.form("grievance_form"):
        c1, c2 = st.columns(2)
        subject = c1.text_input("Subject *", placeholder="Delay in PM-KISAN instalment", max_chars=250)
        department = c2.text_input("Department *", placeholder="Department of Agriculture and Farmers Welfare", max_chars=250)
        c3, c4 = st.columns(2)
        applicant = c3.text_input("Applicant name (optional)", max_chars=160)
        address = c4.text_input("Address (optional)", max_chars=500)
        problem = st.text_area("Problem summary *", height=130, max_chars=4000, placeholder="Describe only verified facts...")
        dates = st.text_input("Relevant dates (optional)", max_chars=1000)
        previous = st.text_area("Previous action taken (optional)", height=80, max_chars=2000)
        resolution = st.text_area("Requested resolution (optional)", height=80, max_chars=2000)
        attachments = st.text_input("Attachments, comma-separated (optional)", max_chars=1000)
        language = st.selectbox("Draft language", ["English", "Hindi"])
        submitted = st.form_submit_button(
            "Generate reviewable draft", type="primary", use_container_width=True
        )
    if submitted:
        attachment_items = [item.strip() for item in attachments.split(",") if item.strip()]
        form_errors = []
        if len(subject.strip()) < 3:
            form_errors.append("Add a subject of at least 3 characters.")
        if len(department.strip()) < 2:
            form_errors.append("Add the department responsible for the issue.")
        if len(problem.strip()) < 10:
            form_errors.append("Describe the problem in at least 10 characters.")
        if len(attachment_items) > 10:
            form_errors.append("Add no more than 10 attachment names.")
        if form_errors:
            st.error("Please complete the required information:\n\n" + "\n".join(f"• {item}" for item in form_errors))
            return
        payload = {
            "subject": subject.strip(),
            "department": department.strip(),
            "applicant_name": applicant or None,
            "address": address or None,
            "problem_summary": problem.strip(),
            "relevant_dates": dates or None,
            "previous_action": previous or None,
            "requested_resolution": resolution or None,
            "attachments": attachment_items,
            "language": "hi" if language == "Hindi" else "en",
        }
        try:
            result = api.grievance(payload)
            st.warning(result["warning"])
            st.text_area("Generated draft", result["draft"], height=440)
            st.download_button(
                "Download draft as text",
                result["draft"],
                file_name="janscope-grievance-draft.txt",
                mime="text/plain",
            )
            if result["missing_information"]:
                st.info("Complete before submission: " + ", ".join(result["missing_information"]))
        except APIError as exc:
            st.error(str(exc))


def page_history() -> None:
    hero("Conversation History", "Review the current local demo conversation and its cited responses.")
    conversation_id = st.session_state.conversation_id
    if not conversation_id:
        st.info("No conversation yet. Start from AI Assistant.")
        return
    try:
        item = api.conversation(conversation_id, st.session_state.conversation_token or "")
    except APIError as exc:
        st.error(str(exc))
        return
    st.caption(f"Conversation ID: {conversation_id}")
    profile_panel(item["profile"])
    for message in item["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("intent"):
                st.caption(f"Intent: {message['intent']} · {message['created_at']}")
    if st.button("Start a new conversation"):
        st.session_state.conversation_id = None
        st.session_state.conversation_token = None
        st.session_state.chat_messages = []
        st.session_state.last_chat_response = None
        st.rerun()


def page_settings() -> None:
    hero(
        "Settings and Status",
        "Configure only the local frontend connection. API keys remain in the backend .env file.",
    )
    new_url = st.text_input("Backend URL", st.session_state.backend_url)
    if st.button("Save backend URL"):
        parsed = urlparse(new_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            st.error("Enter a complete backend address beginning with http:// or https://.")
        else:
            st.session_state.backend_url = new_url.rstrip("/")
            st.success("Backend address saved for this browser session.")
    language = st.selectbox(
        "Preferred answer language",
        ["auto", "en", "hi", "hi-en"],
        index=["auto", "en", "hi", "hi-en"].index(st.session_state.selected_language),
    )
    st.session_state.selected_language = language
    health = backend_health(show_error=True)
    if health:
        st.json(health)
    st.markdown("### AI configuration")
    st.code("AI_ENABLED=true\nGEMINI_API_KEY=your_key_here\nGEMINI_MODEL=gemini-3.7-flash", language="text")
    st.info(
        "Never paste your API key into this page, source code, screenshots, or GitHub. Put it only in the local `.env` file."
    )
    st.markdown("### Privacy")
    st.write(
        "This development version stores conversations in the local SQLite database on the computer running the backend. Avoid entering unnecessary personal identifiers."
    )


if st.session_state.access_mode is None:
    page_welcome()
    st.stop()

page = sidebar()
routes = {
    "🏠 Home": page_home,
    "💬 AI Assistant": page_chat,
    "🔎 Discover Schemes": page_discover,
    "🛡️ Eligibility Check": page_eligibility,
    "📝 Grievance Draft": page_grievance,
    "🕘 Conversation History": page_history,
    "⚙️ Settings": page_settings,
}
routes[page]()
