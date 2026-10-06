"""Look & feel of the dashboard (colors, stepper, badges, cards) following mockup/dashboard.html.

Pure presentation: CSS injected once per run plus small HTML helpers. No pipeline logic here.
"""
from contextlib import contextmanager
from html import escape

import streamlit as st

CSS = """
<style>
:root{--bg:#F7F8FA;--surface:#FFFFFF;--raised:#FFFFFF;--border:#7C879A;--border-strong:#5F6B7E;--text:#111827;--muted:#4B5563;--disabled:#6B7280;
--primary:#2F5BEA;--on-primary:#FFFFFF;--primary-soft:#E4EDFF;--focus:#1D4ED8;
--ok:#13693A;--ok-soft:#E3F6EA;--warn:#8A4B00;--warn-soft:#FFF1D6;--bad:#B42318;--bad-soft:#FDE8E6;--info:#1D4ED8;--info-soft:#E4EDFF}
.stApp{background:var(--bg)}
header[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1.2rem;padding-bottom:3rem;max-width:1500px}
h1,h2,h3{letter-spacing:-.01em}
/* bordered containers = cards */
div[data-testid="stVerticalBlockBorderWrapper"]{background:var(--surface);border-radius:12px;border-color:var(--border)}
/* buttons */
.stButton>button,.stDownloadButton>button{border-radius:8px;border:1px solid var(--border);font-size:12.5px;font-weight:500;padding:.35rem .8rem;min-height:2.1rem}
.stButton>button:disabled{opacity:.45;cursor:not-allowed}
.stButton>button[kind="primary"]{background:var(--primary);border-color:var(--primary);color:var(--on-primary)}
.st-key-btn_resume button,.st-key-approve_all button,.st-key-btn_ok button{background:var(--ok-soft);border-color:var(--ok);color:var(--ok)}
.st-key-btn_cancel button,.st-key-reject_all button,.st-key-btn_bad button{background:var(--bad-soft);border-color:var(--bad);color:var(--bad)}
/* brand */
.brand{display:flex;align-items:center;gap:8px;font-weight:700;font-size:16px;white-space:nowrap}
.brand i{width:28px;height:28px;border-radius:8px;background:var(--primary);display:inline-block}
/* radios restyled: stepper (key "step"), segmented mode and filter chips */
.st-key-step [data-testid="stRadioGroup"]{display:flex;gap:6px;flex-wrap:wrap;padding:4px 2px}
.st-key-step [data-testid="stRadioGroup"]>div{flex:1 1 auto;min-width:max-content}
.st-key-step label[data-testid="stRadioOption"]{width:100%;background:var(--surface);border:1.5px solid var(--border);border-radius:10px;padding:9px 14px;margin:0;cursor:pointer}
.st-key-step label[data-testid="stRadioOption"][data-selected="true"]{background:var(--primary-soft);border-color:var(--primary)}
.st-key-step label[data-testid="stRadioOption"][data-selected="true"] p{color:var(--text);font-weight:600}
.st-key-step label[data-testid="stRadioOption"] p{font-size:12.5px;color:var(--muted);margin:0}
[class*="st-key-mode_"] [data-testid="stRadioGroup"],[class*="st-key-filter_"] [data-testid="stRadioGroup"]{gap:6px;flex-wrap:wrap}
[class*="st-key-mode_"] label[data-testid="stRadioOption"],[class*="st-key-filter_"] label[data-testid="stRadioOption"]{border:1px solid var(--border);background:var(--surface);border-radius:16px;padding:3px 12px;margin:0;cursor:pointer}
[class*="st-key-mode_"] label[data-testid="stRadioOption"][data-selected="true"],[class*="st-key-filter_"] label[data-testid="stRadioOption"][data-selected="true"]{background:var(--primary);border-color:var(--primary)}
[class*="st-key-mode_"] label[data-testid="stRadioOption"] p,[class*="st-key-filter_"] label[data-testid="stRadioOption"] p{font-size:13.5px;color:var(--text);margin:0}
[class*="st-key-mode_"] label[data-testid="stRadioOption"][data-selected="true"] p,[class*="st-key-filter_"] label[data-testid="stRadioOption"][data-selected="true"] p{color:var(--on-primary);font-weight:600}
.st-key-step label[data-testid="stRadioOption"]>div>div:first-child,[class*="st-key-mode_"] label[data-testid="stRadioOption"]>div>div:first-child,[class*="st-key-filter_"] label[data-testid="stRadioOption"]>div>div:first-child{display:none}
/* badges, bars, items */
.badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:12.5px;font-weight:600;background:var(--bg);color:var(--muted);white-space:nowrap}
.b-ok{background:var(--ok-soft);color:var(--ok)}.b-warn{background:var(--warn-soft);color:var(--warn)}.b-bad{background:var(--bad-soft);color:var(--bad)}
.b-info{background:var(--info-soft);color:var(--info)}.b-pri{background:var(--primary-soft);color:var(--primary)}
.bar{height:5px;background:var(--border);border-radius:3px;flex:1}.bar i{display:block;height:100%;border-radius:3px}
.qcrow{display:flex;align-items:center;gap:8px;font-size:12.5px;margin:2px 0}.qcrow b{min-width:52px}
.crit{display:flex;justify-content:space-between;font-size:12.5px;margin:5px 0}
.prog{height:10px;background:var(--border);border-radius:5px;overflow:hidden;margin:6px 0}.prog i{display:block;height:100%;background:var(--primary)}
.item{display:flex;align-items:center;gap:12px;background:var(--bg);border-radius:8px;padding:10px 12px;margin-bottom:8px}
.item .av{width:36px;height:36px;border-radius:50%;background:var(--primary-soft);flex:none;display:grid;place-items:center;font-weight:700;color:var(--primary)}
.item .t{flex:1;min-width:0}.item .t b{display:block;font-size:12.5px}.item .t span{font-size:12.5px;color:var(--muted)}
.cardtitle{font-size:14px;font-weight:700;margin:0 0 8px}.cardtitle span{font-size:12.5px;color:var(--muted);font-weight:400;margin-left:6px}
.cardhead{display:flex;align-items:center;gap:8px;margin:4px 0 6px}.cardhead .grow{flex:1}
.muted{color:var(--muted);font-size:12.5px}
.note-warn{background:var(--warn-soft);border:1px solid var(--warn);border-radius:10px;padding:10px 14px;margin:8px 0}
.wave{height:46px;border-radius:8px;background:repeating-linear-gradient(90deg,var(--primary-soft) 0 3px,transparent 3px 6px);margin:8px 0}
.scenetext{white-space:pre-wrap;font-size:13.5px;line-height:1.5;background:var(--bg);border-left:4px solid var(--primary);border-radius:6px;padding:10px 12px;margin:2px 0 8px}
.scriptfull{white-space:pre-wrap;font-size:13.5px;line-height:1.6;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:14px 16px;max-height:640px;overflow:auto}
.thumb{width:64px;height:36px;border-radius:6px;object-fit:cover;background:var(--border)}
.stephead{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:10px 14px;margin:2px 0 10px;background:var(--surface);
border:1px solid var(--border);border-left:4px solid var(--primary);border-radius:10px;font-size:14px}
.stephead b{font-size:16px}
.nextband{margin:-4px 0 10px;padding:7px 14px;border-radius:8px;font-size:13px;font-weight:600;background:var(--primary-soft);color:var(--primary)}
.nextband.wait,.nextband.warn{background:var(--warn-soft);color:#93370D;border:1px solid var(--warn)}.nextband.done{background:var(--ok-soft);color:var(--ok)}
.sub-num{display:inline-block;min-width:26px;padding:1px 7px;margin-right:6px;border-radius:6px;background:var(--primary-soft);
color:var(--primary);font-weight:700;font-size:12.5px;text-align:center}
/* đợt 3 (01/10): dễ đọc hơn — chữ to hơn, màu chữ phụ đậm hơn (người dùng: "nhìn khá khó đọc chữ") */
.stButton>button,.stDownloadButton>button{font-size:13.5px}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p,.stCaption{font-size:13.5px;color:var(--muted);line-height:1.5}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li{font-size:14.5px;line-height:1.55}
[data-testid="stPopover"] button p,[data-testid="stSelectbox"] input{font-size:13.5px}
label[data-testid="stWidgetLabel"] p{font-size:13.5px;color:var(--text)}
.muted,.cardtitle span{font-size:12.5px}
.qcrow,.crit,.item .t span{font-size:12.5px}.item .t b{font-size:13.5px}
.st-key-step label[data-testid="stRadioOption"] p{font-size:14px}
.nextband{font-size:14px}.stephead{font-size:15px}.stephead b{font-size:17px}
/* radios of the 🎚 Mức tự động bar and the ⌂ filters look like the other chips */
[class*="st-key-level_"] [data-testid="stRadioGroup"],[class*="st-key-home_status"] [data-testid="stRadioGroup"]{gap:6px;flex-wrap:wrap}
[class*="st-key-level_"] label[data-testid="stRadioOption"],[class*="st-key-home_status"] label[data-testid="stRadioOption"]{border:1px solid var(--border);background:var(--surface);border-radius:16px;padding:4px 14px;margin:0;cursor:pointer}
[class*="st-key-level_"] label[data-testid="stRadioOption"][data-selected="true"],[class*="st-key-home_status"] label[data-testid="stRadioOption"][data-selected="true"]{background:var(--primary);border-color:var(--primary)}
[class*="st-key-level_"] label[data-testid="stRadioOption"] p,[class*="st-key-home_status"] label[data-testid="stRadioOption"] p{font-size:13.5px;color:var(--text);margin:0}
[class*="st-key-level_"] label[data-testid="stRadioOption"][data-selected="true"] p,[class*="st-key-home_status"] label[data-testid="stRadioOption"][data-selected="true"] p{color:var(--on-primary);font-weight:600}
[class*="st-key-level_"] label[data-testid="stRadioOption"]>div>div:first-child,[class*="st-key-home_status"] label[data-testid="stRadioOption"]>div>div:first-child{display:none}
/* khung giống bản demo đã duyệt: chữ Inter/hệ thống, thanh bước có số trong vòng tròn */
.stApp,.stApp button,.stApp input,.stApp textarea{font-family:Inter,"Segoe UI",system-ui,-apple-system,Roboto,sans-serif}
.st-key-step [data-testid="stRadioGroup"]{counter-reset:stp 0}
.st-key-step [data-testid="stRadioGroup"]>div:not(:first-child) label[data-testid="stRadioOption"]{counter-increment:stp}
.st-key-step label[data-testid="stRadioOption"]{display:flex;align-items:center;gap:9px}
.st-key-step label[data-testid="stRadioOption"]::before{content:counter(stp);width:26px;height:26px;border-radius:50%;background:var(--border);color:var(--muted);display:grid;place-items:center;font-size:12.5px;font-weight:700;flex:none}
.st-key-step [data-testid="stRadioGroup"]>div:first-child label[data-testid="stRadioOption"]::before{content:"⌂";font-size:15px}
.st-key-step [data-testid="stRadioGroup"]>div:nth-child(n+6) label[data-testid="stRadioOption"]::before{display:none}
.st-key-step label[data-testid="stRadioOption"][data-selected="true"]::before{background:var(--primary);color:var(--on-primary)}
/* viền rõ nét hơn (người dùng 01/10): đậm màu + dày 1.5px cho thẻ, ô nhập, mục gập */
div[data-testid="stVerticalBlockBorderWrapper"]{border-width:1.5px}
[data-testid="stExpander"] details,[data-testid="stTextInputRootElement"],[data-testid="stNumberInputContainer"],[data-testid="stTextAreaRootElement"],div[role="group"]{border-width:1.5px}
.stButton>button,.stDownloadButton>button,[data-testid="stPopoverButton"]{border-width:1.5px}
.st-key-step label[data-testid="stRadioOption"]{border-width:2px}
/* thanh tiến độ đổi màu theo % hoàn thành + khung của container có viền (Streamlit 1.64: stVerticalBlock) */
.pbwrap{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:4px 0}.pbtext{flex:1 1 100%;font-size:13px;color:var(--muted)}
.pb{flex:1;height:10px;background:var(--border);border-radius:5px;overflow:hidden;min-width:80px}.pb i{display:block;height:100%;border-radius:5px}
.pbpct{font-size:12.5px;font-weight:700;min-width:36px;text-align:right}
[data-testid="stVerticalBlock"]{border-color:var(--border)!important;border-width:1.5px!important}
/* ===== hệ thống thiết kế (01/10): tab / bước hiện ĐỦ mục với trạng thái chọn nền đặc; focus rõ; chữ tối thiểu 12-14px ===== */
[role="tablist"]{gap:6px;border-bottom:1.5px solid var(--border)}
[role="tab"]{background:var(--surface);border:1.5px solid var(--border);border-bottom:none;border-radius:8px 8px 0 0;padding:6px 14px;color:var(--muted)}
[role="tab"] p{color:var(--muted)!important;font-size:14px;font-weight:600}
[role="tab"][aria-selected="true"]{background:var(--primary-soft);border-color:var(--primary)}
[role="tab"][aria-selected="true"] p{color:var(--primary)!important}
[data-testid="stTab"] .react-aria-SelectionIndicator{background:var(--primary)!important}
:focus-visible{outline:2px solid var(--focus)!important;outline-offset:2px}
a,a:visited{color:var(--info)}
body:has([data-testid="stDialog"]) [data-testid="stPopoverBody"]:has(.st-key-dark_toggle,.st-key-mc_pricing,.st-key-mc_budget){display:none!important}
.stMarkdownColoredText{font-weight:600}
</style>
"""

STATE_LABELS = {"queued": ("Chờ gen", ""), "running": ("Đang gen", "b-info"), "succeeded": ("Xong · chờ kiểm tra", "b-ok"),
                "failed": ("Lỗi", "b-bad"), "retryable": ("Chờ gửi lại", "b-warn"), "pending_review": ("Chờ duyệt", "b-pri"),
                "approved": ("Đã duyệt", "b-ok"), "rejected": ("Đã loại", "b-bad"), "cancelled": ("Đã hủy", ""),
                "stale": ("⚠ cũ", "b-warn"), "missing": ("Chưa có", ""), "draft": ("Nháp", ""), "ready": ("Sẵn sàng", "b-info"),
                "needs_attention": ("Cần xem", "b-warn"), "pending": ("Chờ duyệt", "b-pri"), "done": ("Xong", "b-ok")}
KIND_LABELS = {("video_gen", "succeeded"): ("Đã gen · chờ duyệt", "b-ok"), ("audio", "succeeded"): ("Xong", "b-ok"),
               ("audio", "running"): ("Đang tạo", "b-info")}
BADGES = STATE_LABELS
MODE_LABELS = {"auto": "Tự duyệt theo QC", "human_qc": "Người duyệt"}


DARK_CSS = """
<style>
/* 🌙 Nền tối (thử 01/10): đổi biến màu của khung + các thành phần gốc của Streamlit. Bảng dữ liệu (canvas) vẫn nền sáng. */
:root{--bg:#0F1115;--surface:#171A21;--raised:#1F232C;--border:#657086;--border-strong:#8791A3;--text:#F2F4F8;--muted:#AAB2C0;--disabled:#7C8596;
--primary:#7C9CFF;--on-primary:#0F1115;--primary-soft:#1E2A4F;--focus:#9DB6FF;
--ok:#6EE7A0;--ok-soft:#10281B;--warn:#FBBF55;--warn-soft:#2E2108;--bad:#FF8B80;--bad-soft:#34130F;--info:#8FB2FF;--info-soft:#122046}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--bg);color:var(--text)}
[data-testid="stHeader"]{background:transparent}
.stApp p,.stApp li,.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6,.stApp summary{color:var(--text)}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:var(--muted)}
.stButton>button,.stDownloadButton>button{background:var(--surface);color:var(--text);border-color:var(--border)}
.stButton>button p{color:inherit}
.stButton>button[kind="primary"]{background:var(--primary);color:var(--on-primary)}
.stButton>button[kind="primary"] p{color:#0F1420}
.stButton>button:hover{border-color:var(--primary);color:var(--primary)}
[data-testid="stTextInputRootElement"],[data-testid="stTextAreaRootElement"],[data-testid="stNumberInputContainer"]{background:var(--surface)!important;border-color:var(--border)!important}
input,textarea{color:var(--text)!important}
[data-testid="stChatInput"],[data-testid="stChatInput"]>div{background:var(--surface)!important;border-color:var(--border)!important}
[data-testid="stChatInput"] textarea{color:var(--text)!important;-webkit-text-fill-color:var(--text)!important;caret-color:var(--text)!important}
[data-testid="stChatInput"] textarea::placeholder{color:var(--muted)!important;-webkit-text-fill-color:var(--muted)!important;opacity:1}
:is([data-testid="stSelectbox"],[data-testid="stMultiSelect"]) svg:not([data-testid="stTooltipIcon"] svg){color:var(--text)!important}
[data-testid="stTooltipIcon"] svg,[data-testid="stTooltipIcon"] svg *{stroke:var(--muted)!important}
[data-testid="stTooltipContent"]{background:var(--surface)!important;border:1px solid var(--border)}
[data-testid="stTooltipContent"] *{color:var(--text)!important}
input::placeholder,textarea::placeholder{color:var(--muted)!important}
:is([data-testid="stSelectboxVirtualDropdown"],[data-testid="stMultiSelectDropdown"]){background:var(--surface)!important}
:is([data-testid="stSelectboxVirtualDropdown"],[data-testid="stMultiSelectDropdown"]) [role="option"],:is([data-testid="stSelectboxVirtualDropdown"],[data-testid="stMultiSelectDropdown"]) [role="option"] *{color:var(--text)!important}
:is([data-testid="stSelectboxVirtualDropdown"],[data-testid="stMultiSelectDropdown"]) [role="option"]:hover{background:var(--primary-soft)!important}
[data-testid="stPopoverBody"],[data-testid="stPopover"]>div[role="dialog"],div[role="dialog"]{background:var(--surface);color:var(--text)}
[data-testid="stExpander"] details{background:var(--surface);border-color:var(--border)}
[data-testid="stExpander"] summary:hover{color:var(--primary)}
[data-testid="stTab"] p{color:var(--muted)}
[data-testid="stTab"][aria-selected="true"] p{color:var(--primary)}
[data-testid="stFileUploaderDropzone"]{background:var(--surface);border-color:var(--border)}
[data-testid="stFileUploaderDropzone"] *{color:var(--muted)}
.stCheckbox label span,.stToggle label span{color:var(--text)}
[data-testid="stAlert"]{background:var(--surface)}
.scenetext,.scriptfull{background:var(--surface)}
.stephead,.item,.note{background:var(--surface)}
.stMarkdownColoredText{filter:brightness(1.9) saturate(1.1)}
[data-testid="stBaseButton-secondary"],[data-testid="stPopoverButton"],[data-testid="stBaseButton-secondaryFormSubmit"]{background:var(--surface)!important;color:var(--text)!important;border-color:var(--border)!important}
[data-testid="stBaseButton-primary"]{background:var(--primary)!important;color:var(--on-primary)!important}
[data-testid="stBaseButton-secondary"] p,[data-testid="stPopoverButton"] p{color:var(--text)!important}
div[role="group"],[data-testid="stTextInputRootElement"],[data-testid="stNumberInputContainer"],[data-testid="stTextAreaRootElement"]{background:var(--surface)!important;border-color:var(--border)!important}
ul[role="listbox"],[data-testid="stSelectboxVirtualDropdown"]{background:var(--surface)!important;color:var(--text)!important}
[data-testid="stExpander"] summary,[data-testid="stExpander"] details{background:var(--surface)!important;color:var(--text)!important}
[data-testid="stExpander"] summary p{color:var(--text)!important}
</style>
"""



def dark_on() -> bool:
    """🌙 Nền tối: the ⚙ toggle, remembered in the address (?theme=dark) so a reload keeps it."""
    try:
        if "dark_mode" not in st.session_state:
            qp = st.query_params.get("theme")
            st.session_state["dark_mode"] = qp != "light"                    # UI v2 (mặc định từ S14.14): opens dark unless ?theme=light
    except Exception:  # noqa: BLE001 - no request context (tests, tools): light
        return False
    return bool(st.session_state.get("dark_mode"))


def set_dark(on: bool) -> None:
    st.session_state["dark_mode"] = bool(on)
    try:
        st.query_params["theme"] = "dark" if on else "light"          # v2 opens dark, so light must be said in the address
    except Exception:  # noqa: BLE001
        pass


def v2_on() -> bool:
    """UI v2 (cờ ui_v2, mặc định BẬT từ S14.14 — người dùng duyệt 05/10). G-a (06/10) gỡ luồng cũ ở nhóm nhẹ (app, ui, admin, step1_*,
    step4): ở đó giao diện v2 luôn vẽ, không hỏi cờ. Chỉ các màn nhóm nặng chưa gỡ (team_screen*, header, step2, step3, step5 — G-b)
    còn đọc cờ này; FEATURE_UI_V2=0 chỉ đổi bố cục của các màn đó."""
    try:
        from core import features
        return features.on("ui_v2")
    except Exception:  # noqa: BLE001 - never break the page for a style flag
        return False


_V2_CACHE = {"stamp": None, "css": ""}


def _v2_css(dark: bool) -> str:
    import os
    from dashboard.design import tokens
    path = os.path.join(os.path.dirname(__file__), "design", "theme.css")
    stamp = os.path.getmtime(path)
    if _V2_CACHE["stamp"] != stamp:
        with open(path, encoding="utf-8") as f:
            _V2_CACHE.update(stamp=stamp, css=f.read())
    import glob
    screens = ""
    for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "design", "screens", "*.css"))):   # one file per lane/screen (S13)
        with open(f, encoding="utf-8") as fh:
            screens += "\n/* " + os.path.basename(f) + " */\n" + fh.read()
    return "<style>" + tokens.css_vars("dark" if dark else "light") + _V2_CACHE["css"] + screens + "</style>"


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    dark = dark_on()
    if dark:
        st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.markdown(_v2_css(dark), unsafe_allow_html=True)              # UI v2: always (S14.14 G-a) — the light screens have no old layout left


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def badge(text: str, kind: str = "") -> str:
    return f'<span class="badge {kind}">{escape(text)}</span>'


def state_label(state: str, kind: str = None) -> str:
    """The one Vietnamese wording of a job/scene/output state, used by every step."""
    return (KIND_LABELS.get((kind, state)) or STATE_LABELS.get(state, (state, "")))[0]


def state_badge(state: str, kind: str = None) -> str:
    text, css = KIND_LABELS.get((kind, state)) or STATE_LABELS.get(state, (state, ""))
    return badge(text, css)


def stale_badge(reason: str = "") -> str:
    """'⚠ cũ' marker for a result made from inputs that have changed since (reason in the tooltip)."""
    return f'<span class="badge b-warn" title="{escape(reason)}">⚠ cũ{(" · " + escape(reason)) if reason else ""}</span>'


def bar_color(frac: float, invert: bool = False) -> str:
    """Colour of a progress bar by how complete it is (0–33 % red, 34–66 % orange, 67–99 % blue, 100 % green).
    invert=True for money / budget bars where FULL is bad (≥ 90 % red, ≥ 70 % orange, else green)."""
    f = max(0.0, min(1.0, float(frac or 0)))
    if invert:
        return "var(--bad)" if f >= 0.9 else "var(--warn)" if f >= 0.7 else "var(--ok)"
    return "var(--ok)" if f >= 0.999 else "var(--info)" if f >= 0.67 else "var(--warn)" if f >= 0.34 else "var(--bad)"


def progress_bar(frac: float, text: str = "", invert: bool = False) -> None:
    """Drop-in for st.progress with the colour by percentage."""
    f = max(0.0, min(1.0, float(frac or 0)))
    html(pbar(f, text, invert))


def pbar(frac: float, text: str = "", invert: bool = False) -> str:
    f = max(0.0, min(1.0, float(frac or 0)))
    label = f'<div class="pbtext">{escape(text)}</div>' if text else ""
    return (f'<div class="pbwrap">{label}<div class="pb"><i style="width:{f * 100:.0f}%;background:{bar_color(f, invert)}"></i></div>'
            f'<span class="pbpct">{f * 100:.0f}%</span></div>')


def score_color(score: float, threshold: float) -> str:
    return "var(--ok)" if score >= threshold else "var(--warn)" if score >= 0.6 else "var(--bad)"


def qc_bar(score: float, threshold: float) -> str:
    color = score_color(score, threshold)
    return (f'<div class="qcrow"><b style="color:{color}">QC {score:.2f}</b>'
            f'<div class="bar"><i style="width:{max(0, min(score, 1)) * 100:.0f}%;background:{color}"></i></div></div>')


def progress(done: int, total: int, extra: str = "") -> str:
    pct = 0 if not total else done / total * 100
    return (f'<div class="cardhead"><b>{done} / {total} hoàn thành</b>{extra}</div>'
            f'<div class="prog"><i style="width:{pct:.0f}%"></i></div>')


def card_title(title: str, sub: str = "") -> str:
    return f'<div class="cardtitle">{escape(title)}' + (f"<span>{escape(sub)}</span>" if sub else "") + "</div>"


@contextmanager
def fold(title: str, summary: str, key: str, default_open: bool = True, sub: str = ""):
    """A card that can be folded to one line (kế hoạch sau #8, S9.2 — người dùng: "thêm nút thu gọn … những phần người dùng không phải
    tương tác thì sắp xếp gọn hoặc ẩn đi, kèm nút show ra"). Folded, the card shows its title + a one-line summary and a "▸ Mở" button;
    open, the body is drawn. The choice is kept per `key` for the session. Use:  with ui.fold(...) as is_open:  if is_open: …"""
    k = f"fold_{key}"
    if k not in st.session_state:
        st.session_state[k] = bool(default_open)

    def flip():
        st.session_state[k] = not st.session_state[k]

    with st.container(border=True):
        a, b = st.columns([6, 1], vertical_alignment="center")
        opened = bool(st.session_state[k])
        a.markdown(card_title(title, sub) + ("" if opened or not summary else f'<div class="muted">{escape(summary)}</div>'),
                   unsafe_allow_html=True)
        b.button("▾ Thu gọn" if opened else "▸ Mở", key=f"{k}_btn", on_click=flip, width="stretch",
                 help="Thu gọn phần này" if opened else "Hiện chi tiết")
        yield opened


def waveform_svg(peaks, height: int = 46) -> str:
    """Row of bars (0..1) as inline SVG; a striped placeholder when there is nothing to draw."""
    if not peaks:
        return '<div class="wave"></div>'
    n = len(peaks)
    bars = "".join(f'<rect x="{i * 6}" y="{(height - max(p * height, 2)) / 2:.1f}" width="3" '
                   f'height="{max(p * height, 2):.1f}" rx="1.5" fill="var(--primary)" opacity="0.75"/>'
                   for i, p in enumerate(peaks))
    return (f'<svg viewBox="0 0 {n * 6} {height}" preserveAspectRatio="none" width="100%" height="{height}" '
            f'style="margin:8px 0;display:block">{bars}</svg>')


def item(name: str, desc: str, right: str = "", avatar: str = "") -> str:
    return (f'<div class="item"><div class="av">{escape(avatar or name[:1])}</div><div class="t"><b>{escape(name)}</b>'
            f'<span>{escape(desc)}</span></div>{right}</div>')
