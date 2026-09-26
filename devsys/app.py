"""AI Development System — web theo dõi quá trình sửa/cập nhật dashboard và mức hoàn thiện thật sau mỗi thay đổi.

Chạy:  Start-DevSystem.bat   hoặc   py -m streamlit run devsys/app.py --server.port 8502
Mọi số liệu tính trực tiếp từ repo mỗi lần mở/làm mới (có bộ nhớ đệm theo commit + file đang sửa + giờ sửa), không tốn tiền. Chỉ nút
"Chấm điểm" bằng Claude API là tốn tiền: luôn hiện ước tính và phải xác nhận; lời gọi đi qua sổ chi của dự án (stage "devsys").
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from html import escape as _html_escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from devsys import collect, scorer, scores  # noqa: E402

st.set_page_config(page_title="AI Development System", page_icon="🧭", layout="wide")

CSS = """
<style>
:root{--bg:#F4F5F8;--surface:#fff;--border:#E2E5EB;--text:#1A1F2B;--muted:#667085;--primary:#4F46E5;--primary-soft:#EEF0FF;
--ok:#12B76A;--ok-soft:#E7F8EF;--warn:#DC6803;--warn-soft:#FFF4E0;--bad:#D92D20;--bad-soft:#FDECEA;--none:#98A2B3;--none-soft:#F2F4F7}
.stApp{background:var(--bg)}
.block-container{padding-top:1.4rem;padding-bottom:3rem;max-width:1500px}
div[data-testid="stVerticalBlockBorderWrapper"]{background:var(--surface);border-radius:12px;border-color:var(--border)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:4px 0 16px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 14px}
.kpi .l{font-size:12px;color:var(--muted);margin-bottom:4px}
.kpi .v{font-size:26px;font-weight:700;color:var(--text);line-height:1.15}
.kpi .s{font-size:11.5px;color:var(--muted);margin-top:2px}
.kpi.ok{border-left:4px solid var(--ok)}.kpi.warn{border-left:4px solid var(--warn)}.kpi.bad{border-left:4px solid var(--bad)}.kpi.none{border-left:4px solid var(--none)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;margin-bottom:12px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:6px}
.card .t{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.card .n{font-weight:600;font-size:13.5px;color:var(--text)}
.card .d{font-size:11.5px;color:var(--muted)}
.score{font-weight:700;font-size:15px;border-radius:8px;padding:2px 9px;white-space:nowrap}
.score.ok{background:var(--ok-soft);color:var(--ok)}.score.warn{background:var(--warn-soft);color:var(--warn)}
.score.bad{background:var(--bad-soft);color:var(--bad)}.score.none{background:var(--none-soft);color:var(--muted)}
.bar{height:6px;background:var(--none-soft);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%}
.bar i.ok{background:var(--ok)}.bar i.warn{background:var(--warn)}.bar i.bad{background:var(--bad)}.bar i.none{background:var(--none)}
.chip{display:inline-block;font-size:11px;border-radius:10px;padding:1px 8px;margin:1px 3px 1px 0;background:var(--primary-soft);color:var(--primary);white-space:nowrap}
.chip.ok{background:var(--ok-soft);color:var(--ok)}.chip.warn{background:var(--warn-soft);color:var(--warn)}.chip.bad{background:var(--bad-soft);color:var(--bad)}
.chip.grey{background:var(--none-soft);color:var(--muted)}
.row{font-size:12.5px;padding:6px 0;border-bottom:1px solid var(--border)}
.row:last-child{border-bottom:none}
.row code{font-size:11.5px}
.muted{color:var(--muted);font-size:12px}
.src{font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:var(--muted)}
h1{font-size:1.55rem!important}h2{font-size:1.2rem!important}h3{font-size:1.02rem!important}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

BAND_LABEL = {"ok": "tốt (≥ 80)", "warn": "khá (60–79)", "bad": "yếu (< 60)", "none": "chưa chấm"}


# ---- dữ liệu (bộ nhớ đệm theo trạng thái repo) -------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=6)
def load_snapshot(key: str):
    cfg = collect.load_areas()
    snap = collect.collect(ROOT, cfg)
    health = collect.area_health(snap, cfg)
    fps = {a["id"]: scorer.fingerprint(ROOT, a, snap, health[a["id"]]) for a in cfg["areas"]}
    return cfg, snap, health, fps


@st.cache_data(show_spinner=False, max_entries=6)
def load_scores(key: str, ids: tuple):
    return scores.load_all(ROOT, list(ids))


def fmt_date(iso) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(str(iso)).astimezone().strftime("%d/%m %H:%M")
    except ValueError:
        return str(iso)[:16]


def md(text: str) -> str:
    """Streamlit Markdown reads $…$ as a formula: escape the dollar signs of prices."""
    return str(text).replace("$", "\\$")


def escape(text) -> str:
    """HTML-escaped text for the cards (dollar signs as an entity, so '$5 … $2' never turns into a formula)."""
    return _html_escape(str(text)).replace("$", "&#36;")


def chips(area_ids, names, cls="") -> str:
    return "".join(f'<span class="chip {cls}">{escape(names.get(a, a))}</span>' for a in area_ids) or '<span class="chip grey">khác</span>'


def kpi(label, value, sub="", band="none") -> str:
    return f'<div class="kpi {band}"><div class="l">{escape(label)}</div><div class="v">{escape(str(value))}</div><div class="s">{escape(sub)}</div></div>'


def score_badge(s) -> str:
    b = scores.band(s)
    return f'<span class="score {b}">{"—" if s is None else f"{s:g}"}</span>'


def bar(s) -> str:
    b = scores.band(s)
    return f'<div class="bar"><i class="{b}" style="width:{0 if s is None else max(2, min(100, s))}%"></i></div>'


def spawn(args, log_name: str) -> int:
    """Start a helper script in the background (log in devsys/data/<log_name>); returns its pid."""
    os.makedirs(collect.data_dir(ROOT), exist_ok=True)
    log = open(os.path.join(collect.data_dir(ROOT), log_name), "w", encoding="utf-8")
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen([sys.executable, *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=flags, env=env)
    return proc.pid


def read_log(name: str, tail: int = 4000) -> str:
    try:
        with open(os.path.join(collect.data_dir(ROOT), name), encoding="utf-8", errors="replace") as f:
            return f.read()[-tail:]
    except OSError:
        return ""


def score_job():
    path = os.path.join(collect.data_dir(ROOT), "score_job.json")
    try:
        with open(path, encoding="utf-8") as f:
            job = json.load(f)
    except (OSError, ValueError):
        return None
    log = read_log("score_run.log")
    done = bool(re.search(r"^(Xong:|Không chấm|Lỗi:|Traceback)", log, re.M))
    job["running"] = not done and time.time() - job.get("started", 0) < 45 * 60
    job["log"] = log
    return job


# ---- tải dữ liệu -------------------------------------------------------------------------------------------------------
key = collect.status_key(ROOT)
with st.spinner("Đang đọc repo…"):
    cfg, snap, health, fps = load_snapshot(key)
names = {a["id"]: a["name"] for a in cfg["areas"]}
ids = tuple(names)
all_scores, score_problems = load_scores(key, ids)
latest = scores.latest_by_area(all_scores)
ov = scores.overall(latest, cfg)


def area_score(aid):
    s = latest.get(aid)
    if not s or str(s.get("scorer", "")).startswith("mock"):
        return None, s
    return s["score"], s


def stale(aid) -> bool:
    s = latest.get(aid)
    return bool(s) and s.get("fingerprint") != fps.get(aid)


# ---- thanh bên ---------------------------------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🧭 AI Development System")
    hd = snap.get("head") or {}
    st.caption(f"Nhánh **{hd.get('branch', '?')}** · commit `{hd.get('short', '?')}` · {fmt_date(hd.get('date'))}")
    st.caption(f"Đọc repo lúc {fmt_date(snap['generated_at'])} ({snap['collect_s']} s) · {len(snap['working'])} file đang sửa")
    if st.button("🔄 Làm mới", help="Đọc lại repo (bình thường tự làm mới khi có commit / file đổi)"):
        st.cache_data.clear()
        st.rerun()
    page = st.radio("Trang", ["Tổng quan", "Bản đồ hệ thống", "Dòng thời gian", "Sức khỏe (đo bằng code)", "Chấm điểm AI",
                              "Bộ kỹ năng 3 vai"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Test**")
    running = collect.tests_running(ROOT)
    run = snap.get("latest_run")
    if running:
        st.info(f"⏳ Đang chạy test từ {datetime.fromtimestamp(running['started']).strftime('%H:%M')} (~4 phút). Bấm Làm mới sau.")
    elif run and run.get("totals"):
        t = run["totals"]
        bad = t["failed"] + t["errors"]
        (st.success if not bad else st.error)(f"{t['passed']}/{t['tests']} qua · {bad} lỗi · {fmt_date(run['date'])} · `{run.get('short')}`")
    else:
        st.warning("Chưa có lần chạy test nào được lưu.")
    if st.button("▶ Chạy test (~4 phút, miễn phí)", disabled=bool(running)):
        spawn([os.path.join("tools", "devsys_collect.py"), "--tests", "--quiet"], "test_run.log")
        time.sleep(1.0)
        st.rerun()
    st.divider()
    try:
        from tools import devsys_hook
        hook_on = devsys_hook.installed(ROOT)
    except Exception:  # noqa: BLE001 - only a status line
        hook_on = False
    st.caption(("✅ Hook post-commit đã cài: mỗi commit tự ghi sự kiện + số đo." if hook_on else
                "Hook post-commit chưa cài — `py tools/devsys_hook.py install` để mỗi commit tự ghi sự kiện."))


# ---- trang: Tổng quan --------------------------------------------------------------------------------------------------
def page_overview():
    st.title("Tổng quan — mức hoàn thiện thật")
    run = snap.get("latest_run")
    t = (run or {}).get("totals") or {}
    flags = snap["flags"]
    todo_open = [i for i in snap["todo"] if i["kind"] == "open"]
    o = ov["score"]
    parts = [
        kpi("Hoàn thiện tổng (AI chấm, có trọng số)", "—" if o is None else f"{o:g}/100",
            f"{len(ov['covered'])}/{ov['areas']} khu vực có điểm thật", scores.band(o)),
        kpi("Test lần chạy mới nhất", f"{t.get('passed', 0)}/{t.get('tests', 0)}" if t else "—",
            f"{t.get('failed', 0) + t.get('errors', 0)} lỗi · {fmt_date((run or {}).get('date'))}" if t else "chưa chạy",
            "none" if not t else "ok" if not (t["failed"] + t["errors"]) else "bad"),
        kpi("Cờ tính năng đã kiểm thật", f"{sum(f['verified'] for f in flags)}/{len(flags)}", "luật 5: chưa kiểm thật = tắt",
            "ok" if flags and all(f["verified"] for f in flags) else "warn"),
        kpi("Việc còn mở trong TODO.md", len(todo_open), f"{sum(i['waiting_user'] for i in todo_open)} chờ người dùng quyết",
            "warn" if todo_open else "ok"),
        kpi("Đang sửa (chưa commit)", len(snap["working"]), f"{len({a for w in snap['working'] for a in w['areas']})} khu vực", "none"),
        kpi("File code chưa thuộc khu vực", len(snap["coverage"]["unmapped"]), "bản đồ devsys/areas.json",
            "ok" if not snap["coverage"]["unmapped"] else "bad"),
    ]
    st.markdown('<div class="kpis">' + "".join(parts) + "</div>", unsafe_allow_html=True)
    if o is None:
        st.info("Chưa có điểm AI thật nào. Vào **Chấm điểm AI** để xem ước tính và chấm (hoặc dùng người chấm ngoài miễn phí). "
                "Các số đo bằng code bên dưới luôn có sẵn.")

    st.subheader("Các khu vực")
    cards = []
    for a in cfg["areas"]:
        h = health[a["id"]]
        s, rec = area_score(a["id"])
        tags = []
        if stale(a["id"]):
            tags.append('<span class="chip warn">điểm cũ — đã đổi</span>')
        if rec and str(rec.get("scorer", "")).startswith("mock"):
            tags.append('<span class="chip grey">chỉ có điểm giả lập</span>')
        if h["working"]:
            tags.append(f'<span class="chip">đang sửa {len(h["working"])} file</span>')
        if h["failed"]:
            tags.append(f'<span class="chip bad">{h["failed"]} test lỗi</span>')
        test_txt = (f"{h['passed']}✓ {h['failed']}✗" if (h["passed"] or h["failed"]) else f"{h['test_files']} file test")
        cards.append(
            f'<div class="card"><div class="t"><div class="n">{escape(a["name"])}</div>{score_badge(s)}</div>{bar(s)}'
            f'<div class="d">Test {test_txt} · cờ {h["flags_verified"]}/{h["flags_total"]} kiểm thật · TODO mở {h["todo_open"]} · '
            f'{h["commits_7d"]} commit/7 ngày</div><div>{"".join(tags)}</div></div>')
    st.markdown('<div class="grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("#### 🛠 Đang sửa ở đâu")
            work = snap["working"]
            if work:
                by = {}
                for w in work:
                    for aid in w["areas"] or ["_khac"]:
                        by.setdefault(aid, []).append(w)
                for aid, ws in sorted(by.items(), key=lambda x: -len(x[1])):
                    files = ", ".join(f"<code>{escape(w['path'])}</code> ({escape(w['status'])}, +{w['added']}/−{w['deleted']})" for w in ws[:6])
                    more = f" … +{len(ws) - 6}" if len(ws) > 6 else ""
                    st.markdown(f'<div class="row"><b>{escape(names.get(aid, "Khác"))}</b>: {files}{more}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="muted">Không có thay đổi chưa commit.</div>', unsafe_allow_html=True)
            st.markdown("**Commit gần nhất**")
            for c in snap["timeline"][:6]:
                st.markdown(f'<div class="row"><span class="src">{escape(c["short"])} · {fmt_date(c["date"])}</span> '
                            f'{escape(c["subject"][:110])}<br>{chips(c["areas"], names)}</div>', unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            st.markdown("#### 🔎 Chưa hoàn thiện / cần kiểm lại")
            scored = sorted(((area_score(a["id"])[0], a["id"]) for a in cfg["areas"] if area_score(a["id"])[0] is not None))
            for s, aid in scored[:5]:
                rec = latest[aid]
                first = (rec.get("can_kiem_lai") or [{}])[0]
                old_tag = ' <span class="chip warn">điểm cũ</span>' if stale(aid) else ""
                st.markdown(f'<div class="row">{score_badge(s)} <b>{escape(names[aid])}</b>{old_tag}<br>'
                            f'<span class="muted">{escape(str(first.get("what", rec.get("summary", "")))[:220])}</span></div>',
                            unsafe_allow_html=True)
            fails = [(aid, n) for aid in names for n in health[aid]["failed_names"]]
            seen = set()
            for aid, n in fails:
                if n["name"] in seen:
                    continue
                seen.add(n["name"])
                st.markdown(f'<div class="row"><span class="chip bad">test lỗi</span><code>{escape(n["name"])}</code> '
                            f'<span class="muted">{escape(n.get("message", ""))[:160]}</span></div>', unsafe_allow_html=True)
                if len(seen) >= 6:
                    break
            unv = [f for f in flags if not f["verified"]]
            if unv:
                st.markdown(f'<div class="row"><span class="chip warn">{len(unv)} cờ chưa kiểm thật</span> '
                            + " ".join(f'<code>{escape(f["name"])}</code>' for f in unv) + "</div>", unsafe_allow_html=True)
            top = sorted(((health[a]["todo_open"], a) for a in names), reverse=True)[:5]
            st.markdown('<div class="row"><b>TODO còn mở nhiều nhất:</b> ' +
                        " · ".join(f"{escape(names[a])} ({n})" for n, a in top if n) + "</div>", unsafe_allow_html=True)
            if not scored:
                st.markdown('<div class="muted">Chưa có điểm AI thật để xếp khu vực yếu nhất.</div>', unsafe_allow_html=True)

    st.subheader("Xu hướng")
    t1, t2 = st.columns(2)
    with t1:
        points = scores.trend(all_scores, cfg)
        if points:
            df = pd.DataFrame(points)
            df["thời điểm"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
            st.caption("Hoàn thiện tổng sau mỗi lần chấm (trung bình có trọng số các khu vực đã có điểm)")
            st.line_chart(df.set_index("thời điểm")[["overall"]].rename(columns={"overall": "Hoàn thiện tổng"}))
        else:
            st.caption("Chưa có điểm AI thật để vẽ xu hướng.")
    with t2:
        runs = [r for r in snap["runs"] if r.get("totals")]
        if runs:
            df = pd.DataFrame([{"thời điểm": pd.to_datetime(r["date"], errors="coerce", utc=True), "Test qua": r["totals"]["passed"],
                                "Test lỗi": r["totals"]["failed"] + r["totals"]["errors"]} for r in runs])
            st.caption("Kết quả các lần chạy test")
            st.line_chart(df.set_index("thời điểm"))
        else:
            st.caption("Chưa có lần chạy test nào (nút ▶ Chạy test ở thanh bên).")

    with st.container(border=True):
        st.markdown("#### 🎬 Bộ kỹ năng 3 vai — bảng điểm chờ duyệt")
        cards = skill_cards()
        if cards:
            st.markdown('<div class="kpis">' + "".join(kpi(r["role"], f"{r['last']}/50", f"cũ {r['old']} → lần 1 {r['first']} → lần 2 {r['last']}",
                                                            "ok" if r["last"] >= 40 else "warn") for r in cards) + "</div>", unsafe_allow_html=True)
        st.caption("Mở trang **Bộ kỹ năng 3 vai** để đọc toàn bộ bảng điểm (docs/DANH_GIA_BO_NGUYEN_TAC_V4.md) và duyệt.")


# ---- trang: Bản đồ hệ thống --------------------------------------------------------------------------------------------
def page_map():
    st.title("Bản đồ hệ thống")
    st.caption("Nguồn: `devsys/areas.json` (bản {}). Mỗi file .py dưới {} phải thuộc ít nhất một khu vực. Test tự gán theo module chúng import."
               .format(cfg.get("version"), ", ".join(f"`{r}/`" for r in cfg["scan_roots"])))
    cov = snap["coverage"]
    if cov["unmapped"]:
        st.error("⚠ File code chưa thuộc khu vực nào — thêm vào `devsys/areas.json`:\n\n" + "\n".join(f"- `{f}`" for f in cov["unmapped"]))
    else:
        st.success(f"Tất cả {len(cov['files'])} file .py dưới core/ và dashboard/ đã thuộc ít nhất một khu vực.")
    no_area_tests = [t for t, v in snap["test_map"].items() if not v["areas"]]
    if no_area_tests:
        st.warning("Test chưa gán được khu vực (không import module nào của khu vực): " + ", ".join(f"`{t}`" for t in no_area_tests))
    rows = []
    for a in cfg["areas"]:
        h = health[a["id"]]
        rows.append({"Khu vực": a["name"], "id": a["id"], "Trọng số": a["weight"], "File code": h["code_files"], "Dòng code": h["lines"],
                     "File test": h["test_files"], "Cờ": h["flags_total"], "File > 900 dòng": len(h["big_files"])})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    for a in cfg["areas"]:
        with st.expander(f"{a['name']} — {a['description'][:110]}"):
            files = snap["files"]
            code = collect.area_files(a, files, ("code",))
            st.markdown("**Code**: " + (", ".join(f"`{f}` ({snap['line_counts'].get(f, 0)}{' ⚠' if snap['line_counts'].get(f, 0) > collect.BIG_FILE_LINES else ''})"
                                                 for f in code) or "—"))
            st.markdown("**Tài nguyên**: " + (", ".join(f"`{f}`" for f in collect.area_files(a, files, ("assets",))[:60]) or "—"))
            st.markdown("**Tài liệu**: " + (", ".join(f"`{f}`" for f in collect.area_files(a, files, ("docs",))[:60]) or "—"))
            st.markdown("**Test**: " + (", ".join(f"`{t}`" for t in snap["tests_by_area"][a["id"]]["test_files"]) or "— (không có test nào)"))
            st.markdown("**Cờ**: " + (", ".join(f"`{f}`" for f in a["flags"]) or "—") + " · **Stage diag**: " + (", ".join(a["diag_stages"]) or "—"))
    if cov["multi"]:
        with st.expander(f"File thuộc nhiều khu vực ({len(cov['multi'])})"):
            st.markdown("\n".join(f"- `{f}` → {', '.join(names[x] for x in cov['files'][f])}" for f in cov["multi"]))


# ---- trang: Dòng thời gian ---------------------------------------------------------------------------------------------
def page_timeline():
    st.title("Dòng thời gian thay đổi")
    st.subheader("Đang sửa ngay lúc này (chưa commit)")
    if snap["working"]:
        st.dataframe(pd.DataFrame([{"Trạng thái": w["status"], "File": w["path"], "+": w["added"], "−": w["deleted"],
                                    "Khu vực": ", ".join(names.get(a, a) for a in w["areas"]) or "khác",
                                    "Sửa lúc": datetime.fromtimestamp(w["mtime"]).strftime("%d/%m %H:%M") if w.get("mtime") else "—"}
                                   for w in snap["working"]]), hide_index=True)
    else:
        st.caption("Không có thay đổi chưa commit.")
    st.subheader("Commit")
    pick = st.multiselect("Lọc theo khu vực", list(names), format_func=lambda x: names[x])
    commits = [c for c in snap["timeline"] if not pick or set(pick) & set(c["areas"])]
    st.dataframe(pd.DataFrame([{"Giờ": fmt_date(c["date"]), "Commit": c["short"], "Nội dung (dòng đầu)": c["subject"],
                                "Tác giả": c["author"], "Khu vực": ", ".join(names.get(a, a) for a in c["areas"]) or "khác",
                                "Số file": len(c["files"])} for c in commits]), hide_index=True, height=520)
    st.caption("Commit message chỉ để xem; người chấm AI không bao giờ nhận commit message làm bằng chứng.")
    events = collect.read_events(ROOT)
    with st.expander(f"Sự kiện ghi tự động ({len(events)}) — hook post-commit, chạy test, chấm điểm"):
        if events:
            st.dataframe(pd.DataFrame([{"Lúc": fmt_date(e.get("at")), "Loại": e.get("kind"), "Commit": e.get("short") or e.get("commit") or "",
                                        "Chi tiết": e.get("subject") or json.dumps({k: v for k, v in e.items() if k not in ("at", "kind", "files")},
                                                                                   ensure_ascii=False)[:160]}
                                       for e in reversed(events)]), hide_index=True)
        else:
            st.caption("Chưa có sự kiện (cài hook: `py tools/devsys_hook.py install`).")


# ---- trang: Sức khỏe ---------------------------------------------------------------------------------------------------
def page_health():
    st.title("Sức khỏe — đo bằng code (miễn phí, khách quan)")
    run = snap.get("latest_run")
    st.caption(("Test: lần chạy " + fmt_date(run["date"]) + f" (commit `{run.get('short')}`, {run.get('duration_s')} s)") if run else
               "Test: chưa có lần chạy nào — bấm ▶ Chạy test ở thanh bên.")
    rows = []
    for a in cfg["areas"]:
        h = health[a["id"]]
        rows.append({"Khu vực": a["name"], "Test qua": h["passed"], "Test lỗi": h["failed"], "File test": h["test_files"],
                     "Cờ kiểm thật": f"{h['flags_verified']}/{h['flags_total']}", "TODO mở": h["todo_open"],
                     "Chờ người dùng": h["todo_waiting_user"], "Diag cảnh báo/lỗi": f"{h['diag_warn']}/{h['diag_error']}",
                     "File > 900 dòng": len(h["big_files"]), "Commit 7 ngày": h["commits_7d"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    if not snap["diag"]["available"]:
        st.caption("Diag: " + snap["diag"]["note"])
    if snap.get("todo_note"):
        st.warning(snap["todo_note"])
    show_paused = st.toggle("Hiện cả việc 'Tạm gác'", value=False)
    for a in cfg["areas"]:
        h = health[a["id"]]
        items = [i for i in snap["todo_by_area"].get(a["id"], []) if show_paused or i["kind"] == "open"]
        label = f"{a['name']} — {h['failed']} test lỗi · {len(h['flags_unverified'])} cờ chưa kiểm thật · {len(items)} dòng TODO"
        with st.expander(label):
            if h["failed_names"]:
                st.markdown("**Test lỗi**")
                for n in h["failed_names"][:30]:
                    st.markdown(md(f"- `{n['name']}` — {n.get('message', '')}"))
            t = snap["tests_by_area"][a["id"]]
            if t["not_run"] and run:
                st.caption("File test không có trong lần chạy mới nhất: " + ", ".join(t["not_run"]))
            fl = [f for f in snap["flags"] if a["id"] in f["areas"]]
            if fl:
                st.markdown("**Cờ tính năng**")
                for f in fl:
                    state = "✅ đã kiểm thật" if f["verified"] else ("🟠 chưa kiểm thật · đang BẬT bằng biến môi trường" if f["on"] else "⚪ chưa kiểm thật · tắt")
                    st.markdown(f"- `{f['name']}` — {state}: {escape(f['label'])}  \n  <span class='muted'>Vì sao: {escape(f['why'])} · dùng ở: "
                                f"{escape(', '.join(f['sites'][:5]) or 'không thấy features.on(...)')}</span>", unsafe_allow_html=True)
            if items:
                st.markdown("**Dòng TODO.md còn mở** (số dòng = dòng nguồn trong TODO.md)")
                for i in items[:60]:
                    marks = " ".join(f'<span class="chip warn">{escape(m)}</span>' for m in i["markers"])
                    extra = ('<span class="chip bad">chờ người dùng</span>' if i["waiting_user"] else "") + \
                            ('<span class="chip grey">tạm gác</span>' if i["kind"] == "paused" else "")
                    st.markdown(f'<div class="row"><span class="src">TODO.md:{i["line"]}</span> {marks}{extra} '
                                f'<span class="muted">({escape(i["section"][:70])} · gán theo {escape(i["matched_by"] or "—")})</span><br>'
                                f'{escape((i["focus"] or i["text"])[:420])}</div>', unsafe_allow_html=True)
                if len(items) > 60:
                    st.caption(f"… và {len(items) - 60} dòng nữa")
            if h["big_files"]:
                st.markdown("**File quá dài (> 900 dòng)**: " + ", ".join(f"`{f}` ({n})" for f, n in h["big_files"]))
            if snap["diag"]["available"]:
                rec = [r for r in snap["diag"]["recent"] if r["stage"] in a["diag_stages"]]
                if rec:
                    st.markdown("**Cảnh báo diag gần đây**")
                    for r in rec[:10]:
                        st.markdown(md(f"- [{r['severity']}] ×{r['count']} {fmt_date(r['last_at'])}: {r['message']}"))
    gen = snap["todo_by_area"].get("_chung", [])
    if gen:
        with st.expander(f"Dòng TODO chưa gán khu vực nào ({len(gen)})"):
            for i in gen:
                st.markdown(f'<div class="row"><span class="src">TODO.md:{i["line"]}</span> {escape(i["text"][:400])}</div>', unsafe_allow_html=True)
    runs = snap["runs"]
    if runs:
        with st.expander(f"Lịch sử chạy test ({len(runs)})"):
            st.dataframe(pd.DataFrame([{"Lúc": fmt_date(r["date"]), "Commit": r.get("short"), "Tổng": (r.get("totals") or {}).get("tests"),
                                        "Lỗi": ((r.get("totals") or {}).get("failed") or 0) + ((r.get("totals") or {}).get("errors") or 0),
                                        "Giây": r.get("duration_s"), "Mã thoát": r.get("returncode")} for r in reversed(runs)]), hide_index=True)


# ---- trang: Chấm điểm AI -----------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=6)
def cached_plan(key: str, mode: str, picked: tuple, provider: str):
    p = scorer.plan(ROOT, cfg, snap, health, list(picked) or None, mode == "all", provider)
    est = scorer.estimate(p["todo"]) if provider == "anthropic" else None
    slim = [{k: b[k] for k in ("area", "name", "why", "chars", "notes")} for b in p["todo"]]
    return slim, p["skipped"], est


def page_scores():
    st.title("Chấm điểm AI khách quan")
    st.caption("Thang cố định `devsys/rubric.md` · điểm = code cộng từ các khoản trừ có bằng chứng · người chấm không thấy commit message.")
    if score_problems:
        st.warning("File điểm không đọc được:\n\n" + "\n".join(f"- {p}" for p in score_problems))
    rows = []
    for a in cfg["areas"]:
        s = latest.get(a["id"])
        rows.append({"Khu vực": a["name"], "Điểm": s["score"] if s else None, "Mức": BAND_LABEL[scores.band(s["score"] if s else None)],
                     "Người chấm": (s or {}).get("scorer", "—"), "Model": (s or {}).get("model", "—"), "Lúc": fmt_date((s or {}).get("date")),
                     "Commit": str((s or {}).get("commit") or "")[:9], "Còn đúng?": ("—" if not s else "⚠ đã đổi, nên chấm lại" if stale(a["id"]) else "✅ khớp")})
    st.dataframe(pd.DataFrame(rows), hide_index=True, column_config={"Điểm": st.column_config.ProgressColumn("Điểm", min_value=0, max_value=100, format="%.0f")})

    scored_ids = [a["id"] for a in cfg["areas"] if a["id"] in latest]
    if scored_ids:
        aid = st.selectbox("Xem chi tiết khu vực", scored_ids, format_func=lambda x: names[x])
        rec = latest[aid]
        with st.container(border=True):
            st.markdown(f"#### {escape(names[aid])} — {score_badge(rec['score'])} "
                        f"<span class='muted'>{escape(str(rec.get('scorer')))} · {escape(str(rec.get('model')))} · {fmt_date(rec.get('date'))} · "
                        f"commit {escape(str(rec.get('commit') or '')[:9])}{' (có thay đổi chưa commit)' if rec.get('dirty') else ''}</span>",
                        unsafe_allow_html=True)
            if rec.get("summary"):
                st.markdown(md(rec["summary"]))
            if rec.get("rubric_hash") and rec["rubric_hash"] != scores.rubric_hash(ROOT):
                st.warning("Điểm này chấm theo thang cũ (devsys/rubric.md đã đổi).")
            for k, label, mx in scores.CRITERIA:
                c = rec["criteria"][k]
                st.markdown(f"**{label}** — {c['score']:g}/{mx}")
                st.progress(min(1.0, c["score"] / mx))
                for d in c["deductions"]:
                    ev = ", ".join(f"`{e}`" + (" ⚠" if e in d.get("unverified", []) else "") for e in d["evidence"])
                    st.markdown(md(f"- −{d['points']:g}: {d['reason']} — {ev}"))
                for cap in c.get("code_caps", []):
                    st.markdown(md(f"- 🔒 {cap}"))
                if c.get("evidence_for"):
                    st.caption("Bằng chứng được điểm: " + ", ".join(c["evidence_for"]))
            if rec.get("unverified_evidence"):
                st.warning("Bằng chứng không kiểm được trong repo (⚠): " +
                           "; ".join(f"{u['evidence']} ({u['why']})" for u in rec["unverified_evidence"][:12]))
            if rec.get("can_kiem_lai"):
                st.markdown("**Cần kiểm lại**")
                for c in rec["can_kiem_lai"]:
                    st.markdown(md(f"- {c.get('what', '')}" + (f" — {c['why']}" if c.get("why") else "") +
                                   (" · " + ", ".join(f"`{e}`" for e in c.get("evidence", [])) if c.get("evidence") else "")))
            usage = rec.get("usage") or {}
            if usage.get("usd") is not None:
                st.caption(f"Chi phí lần chấm: {usage.get('input_tokens')} token vào, {usage.get('output_tokens')} token ra ≈ \\${usage['usd']:.4f}")
            hist = [s for s in all_scores if s["area"] == aid]
            if len(hist) > 1:
                st.caption("Lịch sử: " + " → ".join(f"{s['score']:g} ({fmt_date(s['date'])}, {s.get('scorer')})" for s in hist[-8:]))
            with st.expander("JSON đầy đủ của lần chấm"):
                st.json(rec)

    st.subheader("Chấm lại")
    job = score_job()
    if job and job["running"]:
        st.info(f"⏳ Đang chấm ({job.get('provider')}, {len(job.get('areas', []))} khu vực) từ {datetime.fromtimestamp(job['started']).strftime('%H:%M')} — "
                "bấm 🔄 Làm mới để xem tiến độ.")
        st.code(job["log"][-2500:] or "…", language=None)
        return
    if job and job.get("log"):
        with st.expander("Kết quả lần chấm gần nhất"):
            st.code(job["log"][-3000:], language=None)
    c1, c2 = st.columns(2)
    mode = c1.radio("Khu vực", ["changed", "pick", "all"], format_func={"changed": "Tăng dần: chỉ khu vực đã đổi từ lần chấm trước",
                                                                       "pick": "Tự chọn khu vực", "all": "Tất cả (chấm lại hết)"}.get)
    provider = c2.radio("Người chấm", ["anthropic", "mock"], format_func={"anthropic": "Claude API (tốn tiền, ghi sổ chi, trần Claude)",
                                                                         "mock": "Giả lập (miễn phí — chỉ để thử luồng)"}.get)
    picked = ()
    if mode == "pick":
        picked = tuple(st.multiselect("Chọn khu vực", list(names), format_func=lambda x: names[x]))
        if not picked:
            st.caption("Chọn ít nhất một khu vực.")
            return
    try:
        todo, skipped, est = cached_plan(key, mode, picked, provider)
    except scorer.ScorerError as e:
        st.error(str(e))
        return
    if skipped:
        st.caption("Bỏ qua (không đổi): " + ", ".join(f"{names[s['area']]}" for s in skipped))
    if not todo:
        st.success("Không có khu vực nào cần chấm lại — mọi điểm còn khớp với repo.")
        return
    st.dataframe(pd.DataFrame([{"Khu vực": b["name"], "Lý do": b["why"], "Token vào (ước tính)": round(b["chars"] / scorer.CHARS_PER_TOKEN),
                                "Đã cắt vì dài": "; ".join(b["notes"])[:120] or "—"} for b in todo]), hide_index=True)
    if provider == "anthropic":
        st.info(md(scorer.estimate_text(est)))
        if not est["priced"]:
            return
        db = collect.default_db(ROOT)
        if not os.path.exists(db):
            st.error(f"Không thấy sổ chi `{os.path.relpath(db, ROOT)}` — mở Dashboard thật một lần rồi quay lại. Không gọi Claude ngoài sổ chi.")
            return
        ok = st.checkbox(md(f"Tôi đồng ý chi khoảng ${est['usd_expected']:.2f} (tối đa ${est['usd_max']:.2f}) cho lần chấm này"))
        label = md(f"Chấm {len(todo)} khu vực bằng Claude (≈ ${est['usd_expected']:.2f})")
    else:
        ok = True
        label = md(f"Chấm giả lập {len(todo)} khu vực ($0)")
    if st.button(label, type="primary", disabled=not ok):
        areas = [b["area"] for b in todo]
        spawn([os.path.join("tools", "devsys_score.py"), "--areas", ",".join(areas), "--provider", provider, "--yes"], "score_run.log")
        with open(os.path.join(collect.data_dir(ROOT), "score_job.json"), "w", encoding="utf-8") as f:
            json.dump({"started": time.time(), "areas": areas, "provider": provider}, f)
        time.sleep(1.0)
        st.rerun()

    st.subheader("Người chấm ngoài (miễn phí)")
    st.markdown("Một phiên Claude Code / subagent có thể chấm bằng gói của bạn: tải dữ liệu đầu vào của khu vực, chấm theo "
                "`devsys/rubric.md`, rồi nhập file JSON (định dạng ở cuối thang). Điểm vẫn do code tính lại và áp giới hạn như người chấm API.")
    e1, e2 = st.columns(2)
    with e1:
        ex = st.selectbox("Khu vực cần xuất dữ liệu", list(names), format_func=lambda x: names[x], key="export_area")
        if st.button("Tạo dữ liệu đầu vào"):
            area = collect.area_by_id(cfg)[ex]
            last = scores.latest_by_area([s for s in all_scores if not str(s.get("scorer", "")).startswith("mock")]).get(ex)
            b = scorer.build_bundle(ROOT, cfg, area, snap, health[ex], last)
            path = scorer.export_bundle(ROOT, b)
            st.session_state["export_path"] = path
        path = st.session_state.get("export_path")
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                st.download_button(f"Tải {os.path.basename(path)}", f.read(), file_name=os.path.basename(path), mime="text/markdown")
            st.caption(f"Đã ghi `{os.path.relpath(path, ROOT)}`")
    with e2:
        up = st.file_uploader("Nhập file điểm JSON", type=["json"])
        who = st.text_input("Người chấm (scorer)", value="claude-code-session")
        if up is not None and st.button("Nhập điểm"):
            try:
                raw = json.loads(up.getvalue().decode("utf-8"))
                saved = scorer.import_score(ROOT, cfg, snap, health, raw, who.strip() or None)
                st.success(f"Đã nhập → `{os.path.relpath(saved, ROOT)}`")
                st.cache_data.clear()
            except (ValueError, scores.ScoreError) as e:
                st.error(f"Không nhập được: {e}")
    with st.expander("Thang chấm (devsys/rubric.md)"):
        with open(os.path.join(ROOT, "devsys", "rubric.md"), encoding="utf-8") as f:
            st.markdown(md(f.read()))


# ---- trang: Bộ kỹ năng 3 vai -------------------------------------------------------------------------------------------
SKILL_DOC = os.path.join(ROOT, "docs", "DANH_GIA_BO_NGUYEN_TAC_V4.md")


def skill_cards():
    """[{role, old, first, last}] from the scorecard table (section 1) of docs/DANH_GIA_BO_NGUYEN_TAC_V4.md."""
    try:
        with open(SKILL_DOC, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    out, role = [], None
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        if cells[0] and cells[1].startswith("1 ·"):
            role = cells[0]
        elif role and cells[1].startswith("Tổng"):
            nums = [re.sub(r"\D", "", c) for c in cells[2:5]]
            if all(nums):
                out.append({"role": role, "old": int(nums[0]), "first": int(nums[1]), "last": int(nums[2])})
            role = None
    return out


def page_skills():
    st.title("Bộ kỹ năng 3 vai — bảng điểm")
    cards = skill_cards()
    if cards:
        st.markdown('<div class="kpis">' + "".join(kpi(r["role"], f"{r['last']}/50", f"cũ {r['old']} → lần 1 {r['first']} → lần 2 {r['last']} (+{r['last'] - r['old']})",
                                                        "ok" if r["last"] >= 40 else "warn") for r in cards) + "</div>", unsafe_allow_html=True)
    fc = next((f for f in snap["flags"] if f["name"] == "film_crew"), None)
    if fc:
        st.info(f"Cờ `film_crew` (Director đọc bộ kỹ năng mới): {'đã kiểm thật' if fc['verified'] else 'chưa kiểm thật'}, đang "
                f"{'BẬT' if fc['on'] else 'tắt'}. Duyệt bảng điểm này = cho phép phiên Claude bật `film_crew` cho lần chạy Director thật đầu tiên "
                "(FEATURE_FILM_CREW=1); `verified` chỉ đổi thành True khi lần chạy thật đó đạt (luật 5 của CHUAN_XAY_DUNG).")
    try:
        with open(SKILL_DOC, encoding="utf-8") as f:
            st.markdown(md(f.read()))
    except OSError:
        st.error("Không thấy docs/DANH_GIA_BO_NGUYEN_TAC_V4.md")


PAGES = {"Tổng quan": page_overview, "Bản đồ hệ thống": page_map, "Dòng thời gian": page_timeline, "Sức khỏe (đo bằng code)": page_health,
         "Chấm điểm AI": page_scores, "Bộ kỹ năng 3 vai": page_skills}
PAGES[page]()
