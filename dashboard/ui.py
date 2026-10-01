"""Look & feel of the dashboard (colors, stepper, badges, cards) following mockup/dashboard.html.

Pure presentation: CSS injected once per run plus small HTML helpers. No pipeline logic here.
"""
from contextlib import contextmanager
from html import escape

import streamlit as st

CSS = """
<style>
:root{--bg:#F4F5F8;--surface:#fff;--border:#E2E5EB;--text:#1A1F2B;--muted:#667085;--primary:#4F46E5;--primary-soft:#EEF0FF;
--ok:#12B76A;--ok-soft:#E7F8EF;--warn:#F79009;--warn-soft:#FFF4E0;--bad:#F04438;--bad-soft:#FDECEA;--info:#0BA5EC;--info-soft:#E5F5FD}
.stApp{background:var(--bg)}
header[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1.2rem;padding-bottom:3rem;max-width:1500px}
h1,h2,h3{letter-spacing:-.01em}
/* bordered containers = cards */
div[data-testid="stVerticalBlockBorderWrapper"]{background:var(--surface);border-radius:12px;border-color:var(--border)}
/* buttons */
.stButton>button,.stDownloadButton>button{border-radius:8px;border:1px solid var(--border);font-size:12px;font-weight:500;padding:.35rem .8rem;min-height:2.1rem}
.stButton>button:disabled{opacity:.45;cursor:not-allowed}
.stButton>button[kind="primary"]{background:var(--primary);border-color:var(--primary);color:#fff}
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
[class*="st-key-mode_"] label[data-testid="stRadioOption"] p,[class*="st-key-filter_"] label[data-testid="stRadioOption"] p{font-size:11.5px;color:var(--muted);margin:0}
[class*="st-key-mode_"] label[data-testid="stRadioOption"][data-selected="true"] p,[class*="st-key-filter_"] label[data-testid="stRadioOption"][data-selected="true"] p{color:#fff;font-weight:600}
.st-key-step label[data-testid="stRadioOption"]>div>div:first-child,[class*="st-key-mode_"] label[data-testid="stRadioOption"]>div>div:first-child,[class*="st-key-filter_"] label[data-testid="stRadioOption"]>div>div:first-child{display:none}
/* badges, bars, items */
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10.5px;font-weight:600;background:var(--bg);color:var(--muted);white-space:nowrap}
.b-ok{background:var(--ok-soft);color:var(--ok)}.b-warn{background:var(--warn-soft);color:var(--warn)}.b-bad{background:var(--bad-soft);color:var(--bad)}
.b-info{background:var(--info-soft);color:var(--info)}.b-pri{background:var(--primary-soft);color:var(--primary)}
.bar{height:5px;background:var(--border);border-radius:3px;flex:1}.bar i{display:block;height:100%;border-radius:3px}
.qcrow{display:flex;align-items:center;gap:8px;font-size:11px;margin:2px 0}.qcrow b{min-width:52px}
.crit{display:flex;justify-content:space-between;font-size:11.5px;margin:5px 0}
.prog{height:10px;background:var(--border);border-radius:5px;overflow:hidden;margin:6px 0}.prog i{display:block;height:100%;background:var(--primary)}
.item{display:flex;align-items:center;gap:12px;background:var(--bg);border-radius:8px;padding:10px 12px;margin-bottom:8px}
.item .av{width:36px;height:36px;border-radius:50%;background:var(--primary-soft);flex:none;display:grid;place-items:center;font-weight:700;color:var(--primary)}
.item .t{flex:1;min-width:0}.item .t b{display:block;font-size:12.5px}.item .t span{font-size:11.5px;color:var(--muted)}
.cardtitle{font-size:14px;font-weight:700;margin:0 0 8px}.cardtitle span{font-size:11px;color:var(--muted);font-weight:400;margin-left:6px}
.cardhead{display:flex;align-items:center;gap:8px;margin:4px 0 6px}.cardhead .grow{flex:1}
.muted{color:var(--muted);font-size:11.5px}
.note-warn{background:var(--warn-soft);border:1px solid var(--warn);border-radius:10px;padding:10px 14px;margin:8px 0}
.wave{height:46px;border-radius:8px;background:repeating-linear-gradient(90deg,var(--primary-soft) 0 3px,transparent 3px 6px);margin:8px 0}
.scenetext{white-space:pre-wrap;font-size:13.5px;line-height:1.5;background:var(--bg);border-left:4px solid var(--primary);border-radius:6px;padding:10px 12px;margin:2px 0 8px}
.scriptfull{white-space:pre-wrap;font-size:13.5px;line-height:1.6;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:14px 16px;max-height:640px;overflow:auto}
.thumb{width:64px;height:36px;border-radius:6px;object-fit:cover;background:var(--border)}
.stephead{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:10px 14px;margin:2px 0 10px;background:var(--surface);
border:1px solid var(--border);border-left:4px solid var(--primary);border-radius:10px;font-size:14px}
.stephead b{font-size:16px}
.nextband{margin:-4px 0 10px;padding:7px 14px;border-radius:8px;font-size:13px;font-weight:600;background:var(--primary-soft);color:var(--primary)}
.nextband.wait{background:var(--warn-soft);color:#93370D;border:1px solid var(--warn)}.nextband.done{background:var(--ok-soft);color:var(--ok)}
.sub-num{display:inline-block;min-width:26px;padding:1px 7px;margin-right:6px;border-radius:6px;background:var(--primary-soft);
color:var(--primary);font-weight:700;font-size:12px;text-align:center}
/* đợt 3 (01/10): dễ đọc hơn — chữ to hơn, màu chữ phụ đậm hơn (người dùng: "nhìn khá khó đọc chữ") */
:root{--muted:#475467;--ok:#067647;--warn:#B54708;--bad:#B42318;--info:#026AA2}
.stButton>button,.stDownloadButton>button{font-size:13.5px}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p,.stCaption{font-size:13.5px;color:var(--muted);line-height:1.5}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li{font-size:14.5px;line-height:1.55}
[data-testid="stPopover"] button p,[data-testid="stSelectbox"] div[data-baseweb="select"] div{font-size:13.5px}
label[data-testid="stWidgetLabel"] p{font-size:13.5px;color:var(--text)}
.badge{font-size:11.5px;padding:2px 9px}
.muted,.cardtitle span{font-size:12.5px}
.qcrow,.crit,.item .t span{font-size:12.5px}.item .t b{font-size:13.5px}
.st-key-step label[data-testid="stRadioOption"] p{font-size:14px}
.nextband{font-size:14px}.stephead{font-size:15px}.stephead b{font-size:17px}
/* radios of the 🎚 Mức tự động bar and the ⌂ filters look like the other chips */
[class*="st-key-level_"] [data-testid="stRadioGroup"],[class*="st-key-home_status"] [data-testid="stRadioGroup"]{gap:6px;flex-wrap:wrap}
[class*="st-key-level_"] label[data-testid="stRadioOption"],[class*="st-key-home_status"] label[data-testid="stRadioOption"]{border:1px solid var(--border);background:var(--surface);border-radius:16px;padding:4px 14px;margin:0;cursor:pointer}
[class*="st-key-level_"] label[data-testid="stRadioOption"][data-selected="true"],[class*="st-key-home_status"] label[data-testid="stRadioOption"][data-selected="true"]{background:var(--primary);border-color:var(--primary)}
[class*="st-key-level_"] label[data-testid="stRadioOption"] p,[class*="st-key-home_status"] label[data-testid="stRadioOption"] p{font-size:13.5px;color:var(--text);margin:0}
[class*="st-key-level_"] label[data-testid="stRadioOption"][data-selected="true"] p,[class*="st-key-home_status"] label[data-testid="stRadioOption"][data-selected="true"] p{color:#fff;font-weight:600}
[class*="st-key-level_"] label[data-testid="stRadioOption"]>div>div:first-child,[class*="st-key-home_status"] label[data-testid="stRadioOption"]>div>div:first-child{display:none}
/* khung giống bản demo đã duyệt: chữ Inter/hệ thống, thanh bước có số trong vòng tròn */
.stApp,.stApp button,.stApp input,.stApp textarea{font-family:Inter,"Segoe UI",system-ui,-apple-system,Roboto,sans-serif}
.st-key-step [data-testid="stRadioGroup"]{counter-reset:stp 0}
.st-key-step [data-testid="stRadioGroup"]>div:not(:first-child) label[data-testid="stRadioOption"]{counter-increment:stp}
.st-key-step label[data-testid="stRadioOption"]{display:flex;align-items:center;gap:9px}
.st-key-step label[data-testid="stRadioOption"]::before{content:counter(stp);width:26px;height:26px;border-radius:50%;background:var(--border);color:var(--muted);display:grid;place-items:center;font-size:12.5px;font-weight:700;flex:none}
.st-key-step [data-testid="stRadioGroup"]>div:first-child label[data-testid="stRadioOption"]::before{content:"⌂";font-size:15px}
.st-key-step [data-testid="stRadioGroup"]>div:nth-child(n+6) label[data-testid="stRadioOption"]::before{display:none}
.st-key-step label[data-testid="stRadioOption"][data-selected="true"]::before{background:var(--primary);color:#fff}
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


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


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
