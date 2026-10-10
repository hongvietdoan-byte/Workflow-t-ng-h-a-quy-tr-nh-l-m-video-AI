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

from devsys import answers, collect, decisions, metrics, plan_progress, scorer, scores, stages, workflow  # noqa: E402

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
    state = scorer.run_state(log)                 # rà soát A2: a refused / stopped / crashed run is shown as a failure
    job["failed"] = state == "failed"
    job["running"] = state == "running" and time.time() - job.get("started", 0) < 45 * 60
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
ov = scores.overall(latest, cfg, rubric=scores.rubric_hash(ROOT))     # S14: only the current scale is averaged


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
    page = st.radio("Trang", ["📋 Kế hoạch đang chạy", "Tổng quan", "Bản đồ hệ thống", "Dòng thời gian", "Sức khỏe (đo bằng code)", "Chấm điểm AI", "Hiệu quả vận hành",
                              "Hiệu quả quy trình", "Ai quyết", "Làm ↔ Kiểm", "Bộ kỹ năng 3 vai", "Đang chạy"], label_visibility="collapsed")
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
        tests_stale = snap.get("tests_stale")
        if tests_stale:
            st.warning(f"⚠ Kết quả test cũ hơn code: {len(tests_stale['files'])} file code đổi sau lần chạy"
                       + (f" ({tests_stale['commits']} commit)" if tests_stale.get("commits") else "") + " — bấm ▶ Chạy test")
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
            f"{len(ov['covered'])}/{ov['areas']} khu vực có điểm thật cùng thang"
            + (f" · {len(ov['other_scale'])} khu vực điểm thang cũ (chấm lại)" if ov.get("mixed") else ""), scores.band(o)),
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
@st.cache_data(show_spinner="Đang đo bằng code (ast)…", max_entries=2)
def load_metrics(key: str):
    return {a["id"]: metrics.facts_extra(ROOT, cfg, a, snap) for a in cfg["areas"]}


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
    with st.expander("Số đo thang bản 2 — do code tính (nuốt lỗi, hàm dài, độ phủ test, điều khiển giao diện…)"):
        show_m = st.toggle("Tính số đo (đọc ast toàn bộ code, ≈ 10 giây, miễn phí)", value=False, key="show_metrics")
        mrows = []
        for a in (cfg["areas"] if show_m else []):
            m = load_metrics(key)[a["id"]]
            mrows.append({"Khu vực": a["name"], "Khoản trừ tự động": round(sum(x["points"] for x in m["auto"]), 1),
                          "except nuốt lỗi": len(m["metrics"]["swallowed"]), "Module không test": len(m["metrics"]["modules_untested"]),
                          "Hàm công khai chưa được test nhắc": f"{m['metrics']['funcs_untested']}/{m['metrics']['funcs_public']}",
                          "Hàm > 150 dòng": len(m["metrics"]["long_funcs"]), "Hàm phức tạp > 30": len(m["metrics"]["complex_funcs"]),
                          "Điều khiển giao diện": sum(m["metrics"]["controls"].values()),
                          "Cờ BẬT chưa thử thật": len(m["metrics"]["flags_on_unverified"]),
                          "Cờ học việc": len(m["metrics"].get("flags_trainee") or []),
                          "Lời gọi tiền không thấy guard": len(m["metrics"]["paid_unguarded"])})
        if mrows:
            st.dataframe(pd.DataFrame(mrows), hide_index=True)
        ui = metrics.ui_metrics(ROOT)
        st.caption("Đo giao diện thật: " + (", ".join(f"{k} = {ui.get(k)}" for k in ("clicks_old", "clicks_v2", "perf_worst_pct", "keys_lost",
                                                                                      "contrast_fail", "small_text")) + f" · {ui.get('date', '')[:16]}"
                                              if ui else "chưa có — `py tools/devsys_ui_metrics.py --run-acceptance` rồi `--contrast <file>`."))
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
                    state = ("🎓 học việc (chạy bóng, so với người)" if f.get("mode") == "trainee" else
                             "✅ đã kiểm thật" if f["verified"] else
                             ("🟠 chưa kiểm thật · đang BẬT bằng biến môi trường" if f["on"] else "⚪ chưa kiểm thật · tắt"))
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
            if scores.is_v2(rec):
                sev = rec.get("severity") or {}
                st.caption(f"Thang {scores.scale_label(rec)} · lỗi chặn {sev.get('chan', 0)} · lớn {sev.get('lon', 0)} · nhỏ {sev.get('nho', 0)} · "
                           f"khoản trừ tự động do code đo −{rec.get('auto_points', 0):g}")
                for cap in rec.get("code_caps", []):
                    if cap.startswith("khu vực:"):
                        st.markdown(md(f"🔒 {cap}"))
                if rec.get("drift"):
                    dr = rec["drift"]
                    st.caption(f"Độ ổn định: {dr['prev_score']:g} → {dr['now']:g} (lệch {dr['delta']:+g}, ngưỡng {dr['limit']:g}) — "
                               + ("có giải thích: " + "; ".join(e["why"] for e in dr.get("explanations", []))[:300] if dr.get("explained") else "trong ngưỡng"))
            else:
                st.info("Điểm này chấm theo thang bản 1 (6 tiêu chí, người chấm tự ghi số điểm trừ) — không so thẳng với bản 2.")
            for k, label, mx in scores.criteria_of(rec):
                c = rec["criteria"][k]
                if c.get("khong_ap_dung"):                     # S6 (thang 2.1): an area of documents only has no `test`
                    st.markdown(f"**{label}** — không áp dụng (khu vực chỉ có tài liệu; điểm chia lại trên các tiêu chí còn lại)")
                    continue
                st.markdown(f"**{label}** — {c['score']:g}/{mx}")
                st.progress(min(1.0, c["score"] / mx))
                for d in c["deductions"]:
                    ev = ", ".join(f"`{e}`" + (" ⚠" if e in d.get("unverified", []) else "") for e in d["evidence"])
                    tag = "🤖 code đo" if d.get("auto") else scores.SEVERITY_LABEL.get(d.get("muc"), "")
                    tag = f"[{tag}{' · dấu hiệu' if d.get('heuristic') else ''}] " if tag else ""
                    st.markdown(md(f"- −{d['points']:g} {tag}{d['reason']} — {ev}"))
                    fb = d.get("feedback")
                    if fb:                     # S8.1: why it costs points and how to win them back
                        bits = [f"**Vì sao:** {fb['why']}" if fb.get("why") else "", f"**Sửa:** {fb['fix']}" if fb.get("fix") else "",
                                ("**File:** " + ", ".join(f"`{f}`" for f in fb["files"])) if fb.get("files") else "",
                                f"**Nghiệm thu:** {fb['verify']}" if fb.get("verify") else "",
                                " ".join(x for x in [fb.get("effort", ""), f"ưu tiên {fb['priority']}" if fb.get("priority") else ""] if x)]
                        st.caption(md("  \n".join(b for b in bits if b)))
                for cap in c.get("code_caps", []):
                    st.markdown(md(f"- 🔒 {cap}"))
                if c.get("evidence_for"):
                    st.caption("Bằng chứng được điểm: " + ", ".join(c["evidence_for"]))
            if rec.get("unverified_evidence"):
                st.warning("Bằng chứng không kiểm được trong repo (⚠): " +
                           "; ".join(f"{u['evidence']} ({u['why']})" for u in rec["unverified_evidence"][:12]))
            if rec.get("checklist"):
                with st.expander("Checklist các loại lỗi đã gặp (B1–B6, 26/09)"):
                    st.dataframe(pd.DataFrame([{"Loại": c["id"], "Trả lời": c["tra_loi"], "Khoản trừ": c["khoan_tru"], "Ghi chú": c["ghi_chu"]}
                                               for c in rec["checklist"]]), hide_index=True)
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
        with st.expander("Báo cáo hành động theo khu vực · độ ổn định · so thang cũ ↔ mới"):
            real = [s for s in all_scores if not str(s.get("scorer", "")).startswith("mock")]
            st.download_button("Tải báo cáo hành động (Markdown)", scores.action_report(scores.latest_by_area(real), cfg), file_name="bao_cao_hanh_dong.md",
                               mime="text/markdown")
            stab = scores.stability(real)
            if stab["n"]:
                st.markdown(md(f"**Độ ổn định:** {stab['n']} cặp lần chấm cùng thang, lệch trung bình {stab['mean_abs']} điểm, lớn nhất {stab['max_abs']}; "
                               f"{stab['over_limit']} cặp > {scores.DRIFT_LIMIT:g}; {len(stab['noise'])} cặp lệch dù dấu vân tay không đổi."))
            else:
                st.caption("Chưa có hai lần chấm liền nhau cùng thang bản 2 — chưa đo được độ ổn định.")
            old = scores.latest_by_area([s for s in real if s.get("format") == scores.FORMAT])
            new = scores.latest_by_area([s for s in real if scores.is_v2(s)])
            if new:
                st.dataframe(pd.DataFrame([{"Khu vực": r["name"], "Bản 1": r["old"], "Bản 2": r["new"], "Chênh": r["delta"]}
                                           for r in scores.compare_rounds(old, new, cfg) if r["new"] is not None]), hide_index=True)
            else:
                st.caption("Chưa có điểm bản 2 để so với bản 1.")

    st.subheader("Chấm lại")
    job = score_job()
    if job and job["running"]:
        st.info(f"⏳ Đang chấm ({job.get('provider')}, {len(job.get('areas', []))} khu vực) từ {datetime.fromtimestamp(job['started']).strftime('%H:%M')} — "
                "bấm 🔄 Làm mới để xem tiến độ.")
        st.code(job["log"][-2500:] or "…", language=None)
        return
    if job and job.get("failed"):
        st.error("Lần chấm gần nhất KHÔNG chạy xong (bị từ chối, chạm trần --max-usd hoặc lỗi) — xem dòng cuối nhật ký bên dưới, "
                 "sửa rồi bấm chấm lại.")
        st.code(job["log"][-2500:], language=None)
    elif job and job.get("log"):
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
        spawn(scorer.score_command(areas, provider, est if provider == "anthropic" else {}), "score_run.log")  # S14.2: + --max-usd
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


STATUS_BAND = {"✅": "ok", "🔄": "warn", "⏸": "bad", "⬜": "grey", "✖": "grey"}
ORDER = {"⏸": 0, "🔄": 1, "⬜": 2, "✅": 3, "✖": 4}        # waiting for the person first, then running, then not started, then done


def _short(text: str, n: int = 96) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def _wave_name(name: str) -> str:
    """Wave title without the trailing `(docs/…)` reference, shortened; the full text goes in the ⓘ."""
    import re
    return _short(re.sub(r"\s*\(`?docs/[^)]*\)\s*$", "", name or ""), 78)


def _task_row(t: dict, key: str, detail: bool = True) -> None:
    """One compact line: status chip · id · short title; everything long (full title, note, commit, weight) is behind a small ⓘ."""
    full = t["title"]
    extra = bool(t["note"] or t["commit"] or len(full) > 96 or True)
    c1, c2 = st.columns([14, 1], vertical_alignment="center")
    c1.markdown(f"<div class='row'><span class='chip {STATUS_BAND[t['status']]}'>{t['status']} {plan_progress.STATUS[t['status']]}</span> "
                f"<b>{escape(t['id'])}</b> {escape(_short(full))}</div>", unsafe_allow_html=True)
    if detail and extra:
        with c2.popover("ⓘ", help="Xem chi tiết việc này"):
            st.markdown(f"**{t['id']}** · nặng {t['weight']} · {t['status']} {plan_progress.STATUS[t['status']]}")
            st.markdown(full)
            if t["commit"]:
                st.markdown(f"Commit: `{t['commit']}`")
            if t["note"]:
                st.markdown(t["note"])


def _rel(path: str) -> str:
    """Path relative to the repo for display; a path on another drive (Windows) is shown whole."""
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return path


ANSWER_CHOICES = ["—", *answers.CHOICES]


def _save_answer(task_id: str, key: str) -> None:
    """Form callback (runs before the page redraws, so the new state shows at once). Errors are kept and shown, never dropped."""
    import getpass
    choice = st.session_state.get(f"ans-choice-{key}")
    text = st.session_state.get(f"ans-text-{key}") or ""
    try:
        answers.answer(task_id, text, source="devsys", who=getpass.getuser(), choice=None if choice in (None, "—") else choice)
        st.session_state[f"ans-msg-{key}"] = ("ok", f"Đã lưu câu trả lời cho {task_id}.")
    except (answers.AnswersError, OSError) as e:
        st.session_state[f"ans-msg-{key}"] = ("err", f"Chưa lưu được: {e}")


def _answer_state(rec) -> str:
    """'✅ đã trả lời — chờ Claude áp dụng' / '✔ đã áp dụng (…)' + the answer and its time."""
    when = escape((rec.get("at") or "")[:16].replace("T", " "))
    body = escape(" · ".join(x for x in (rec.get("choice"), rec.get("text")) if x))
    if rec.get("status") == "applied":
        note = escape(rec.get("applied_note") or "")
        return f"<div class='row'><span class='chip ok'>✔ đã áp dụng</span> ({note}) <span class='muted'>· {body} · trả lời {when}</span></div>"
    who = escape(rec.get("who") or rec.get("source") or "")
    return (f"<div class='row'><span class='chip warn'>✅ đã trả lời — chờ Claude áp dụng</span> {body} "
            f"<span class='muted'>· {who} · {when}</span></div>")


def _answer_form(t: dict, key: str, rec) -> None:
    """Quick choice + free text + 💾 Lưu, prefilled with the saved answer (editable)."""
    rec = rec or {}
    with st.form(f"ans-form-{key}", border=False):
        cur = rec.get("choice")
        st.radio("Chọn nhanh", ANSWER_CHOICES, index=ANSWER_CHOICES.index(cur) if cur in ANSWER_CHOICES else 0, horizontal=True,
                 key=f"ans-choice-{key}")
        st.text_area("Trả lời (ghi chữ tự do)", value=rec.get("text") or "", height=68, key=f"ans-text-{key}",
                     placeholder="Vd. duyệt trần 10 USD; hoặc lý do không duyệt…")
        st.form_submit_button("💾 Lưu", key=f"ans-save-{key}", on_click=_save_answer, args=(t["id"], key))
    msg = st.session_state.pop(f"ans-msg-{key}", None)
    if msg:
        (st.success if msg[0] == "ok" else st.error)(msg[1])


def _answer_box(t: dict, key: str, ans, inline: bool) -> None:
    """S14.27: under a ⏸ task — the saved answer's state and a box to answer/edit it. `ans` None = the answers file is unreadable
    (the error is shown once above; no box, so a broken file is never overwritten). An answer never changes the plan file itself:
    the Claude session applies it, updates docs/KE_HOACH_SUA_SAU_DU_AN_8.md and marks it applied (`py -m devsys.answers applied`)."""
    if t["status"] != "⏸" or ans is None:
        return
    rec = ans.get(t["id"])
    if rec:
        st.markdown(_answer_state(rec), unsafe_allow_html=True)
    if inline:
        _answer_form(t, key, rec)
    else:
        with st.popover("✏ Sửa trả lời" if rec else "✍ Trả lời", help="Trả lời việc này ngay tại đây (Claude đọc ở đầu phiên)"):
            _answer_form(t, key, rec)


def _wave_body(w: dict, r: dict, key: str, ans=None) -> None:
    """Not-done tasks first (waiting → running → not started), the done ones folded below; ⏸ tasks get an answer box."""
    todo = sorted([t for t in w["tasks"] if t["status"] not in ("✅", "✖")], key=lambda t: ORDER[t["status"]])
    done = [t for t in w["tasks"] if t["status"] in ("✅", "✖")]
    for t in todo:
        _task_row(t, f"{key}-{t['id']}")
        _answer_box(t, f"{key}-{t['id']}", ans, inline=False)
    if not todo:
        st.caption("Không còn việc nào chưa xong.")
    if done:
        with st.expander(f"Đã xong ({len(done)} việc)", expanded=False):
            st.markdown("".join(f"<div class='row'><span class='chip {STATUS_BAND[t['status']]}'>{t['status']}</span> <b>{escape(t['id'])}</b> "
                                f"{escape(_short(t['title'], 110))}</div>" for t in done), unsafe_allow_html=True)


def _pct_text(pct) -> str:
    return "—" if pct is None else f"{pct:g} %".replace(".", ",")


def page_plan():
    t1, t2 = st.columns([14, 1], vertical_alignment="center")
    t1.title("📋 Kế hoạch đang chạy")
    path = plan_progress.PLAN_FILE
    plan = plan_progress.load(path)
    if plan is None:
        st.info(f"Chưa có file kế hoạch `{_rel(path)}`.")
        return
    with t2.popover("ⓘ", help="Nguồn và cách tính"):
        st.markdown(f"Nguồn: `{_rel(path)}`. Câu trả lời cho việc ⏸: `{_rel(answers.default_path())}` (không vào git). % do code tính từ danh sách việc: ✅ tính đủ, 🔄 tính nửa, ✖ không tính; "
                    "trọng số nặng 1/2/3. Đặt tay đợt hiện tại bằng dòng `> Đợt ưu tiên: S13` ở đầu file.")
    if plan["bad"]:
        st.error("Dòng việc không đọc được (sửa trong file kế hoạch):\n\n" + "\n".join(f"- {b}" for b in plan["bad"]))
    s = plan_progress.summary(plan)
    total = s["total"] or 0.0
    n = sum(r["n"] for r in s["waves"])
    done = sum(r["done"] for r in s["waves"])
    money = None
    try:
        money = plan_progress.spend(plan["cap"], collect.default_db(ROOT))
    except Exception as e:  # noqa: BLE001 - the page still shows progress; the reason is shown
        st.warning(f"Không đọc được sổ chi: {e}")
    cur = next((r for r in s["waves"] if r["id"] == s["current"]), None)
    tiles = [kpi("Tiến độ tổng", _pct_text(total), f"{done}/{n} việc xong", "ok" if total >= 80 else "warn" if total >= 30 else "none"),
             kpi("Đợt hiện tại", s["current"] or "—", _wave_name(cur["name"]) if cur else ""),
             kpi("Việc kế", s["next"]["id"] if s["next"] else "—", _short(s["next"]["title"], 60) if s["next"] else ""),
             kpi("Chờ người dùng", str(len(s["waiting"])), ", ".join(t["id"] for t in s["waiting"]) or "không", "bad" if s["waiting"] else "none")]
    if money:
        tiles.append(kpi("Tiền đợt này", f"{money['usd']:.2f} / {money['cap_usd']:g} USD",
                         f"Claude {money['llm_usd']:.2f} / {money['cap_llm']:g} USD", "bad" if money["usd"] > money["cap_usd"] else "none"))
    st.markdown('<div class="kpis">' + "".join(tiles) + "</div>", unsafe_allow_html=True)
    st.progress(min(1.0, total / 100.0))

    waves = {w["id"]: (w, r) for w, r in zip(plan["waves"], s["waves"])}
    finished = [wid for wid, (w, r) in waves.items() if r["pct"] is not None and r["pct"] >= 100]
    others = [wid for wid in waves if wid not in finished and wid != s["current"]]

    ans, ans_err = None, None
    try:
        ans = answers.load()
    except answers.AnswersError as e:
        ans_err = str(e)
    if s["waiting"]:
        with st.container(border=True):
            st.markdown("**⏸ Đang chờ bạn** <span class='muted'>— trả lời ngay dưới mỗi việc; Claude đọc ở đầu phiên, áp dụng rồi "
                        "mới đổi trạng thái việc trong kế hoạch</span>", unsafe_allow_html=True)
            if ans_err:
                st.error(ans_err)
            for t in s["waiting"]:
                _task_row(t, "w-" + t["id"])
                _answer_box(t, "w-" + t["id"], ans, inline=True)
    if s["current"] in waves:
        w, r = waves[s["current"]]
        with st.container(border=True):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.markdown(f"**▶ {escape(w['id'])} — {escape(_wave_name(w['name']))}**  <span class='muted'>{r['done']}/{r['n']} xong"
                        f"{' · ' + str(r['doing']) + ' đang làm' if r['doing'] else ''}</span>", unsafe_allow_html=True)
            c2.markdown(f"<div style='text-align:right;font-weight:800'>{_pct_text(r['pct'])}</div>", unsafe_allow_html=True)
            st.progress(min(1.0, (r["pct"] or 0.0) / 100.0))
            _wave_body(w, r, "cur", ans)
    for wid in others:
        w, r = waves[wid]
        with st.expander(f"{wid} — {_wave_name(w['name'])} · {_pct_text(r['pct'])} · {r['done']}/{r['n']} xong"
                         + (f" · {r['waiting']} chờ bạn" if r["waiting"] else ""), expanded=False):
            st.progress(min(1.0, (r["pct"] or 0.0) / 100.0))
            _wave_body(w, r, wid, ans)
    if finished:
        with st.expander(f"✅ Đã xong ({len(finished)} đợt)", expanded=False):
            st.markdown("".join(f"<div class='row'><span class='chip ok'>✅ 100 %</span> <b>{escape(wid)}</b> "
                                f"{escape(_wave_name(waves[wid][0]['name']))} <span class='muted'>· {waves[wid][1]['n']} việc</span></div>"
                                for wid in finished), unsafe_allow_html=True)


# ---- trang: Hiệu quả (S14.10 Đợt 6b) -----------------------------------------------------------------------------------
def page_effect():
    st.title("Hiệu quả — điểm devsys ↔ chất lượng đầu ra thật")
    st.caption("Ba đường cùng một trục thời gian: điểm devsys có trọng số, tỉ lệ ảnh/video qua lần đầu, tỉ lệ góp ý hài lòng. Vạch dọc = "
               "lúc bật/tắt cờ, đổi kiến thức, duyệt bài học — chỉ khi có vạch dọc mới quy được đường nào đổi vì đâu. Đọc CSDL thật, chỉ đọc, miễn phí.")
    ops = snap.get("ops") or {}
    data = collect.effect_series(scores.trend(all_scores, cfg), ops)
    for n in data["notes"]:
        st.info(n)
    if data["points"]:
        import altair as alt
        df = pd.DataFrame(data["points"])
        df["thời điểm"] = pd.to_datetime(df["at"], errors="coerce")
        chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X("thời điểm:T", title=None), y=alt.Y("value:Q", title="%", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("series:N", title=None, legend=alt.Legend(orient="bottom")), tooltip=["series", "value", "at"])
        if data["markers"]:
            mk = pd.DataFrame(data["markers"])
            mk["thời điểm"] = pd.to_datetime(mk["at"], errors="coerce")
            chart = chart + alt.Chart(mk).mark_rule(strokeDash=[4, 3], color="#98A2B3").encode(x="thời điểm:T", tooltip=["kind", "text", "at"])
        st.altair_chart(chart, width="stretch")
    if data["markers"]:
        st.markdown("#### Mốc thay đổi")
        st.dataframe(pd.DataFrame(data["markers"]).rename(columns={"at": "Lúc", "kind": "Loại", "text": "Nội dung"}), hide_index=True)
    fb = (ops.get("feedback") or {}).get("by_stage") or {}
    if fb:
        st.markdown("#### Góp ý theo khâu")
        st.dataframe(pd.DataFrame([{"Khâu": k, "Góp ý": v["n"], "Có điểm": v["rated"], "Hài lòng (≥ 4)": v["positive"], "Không hài lòng (≤ 2)": v["low"],
                                    "Chưa xử lý 30 ngày": len(v["low_open_30d"])} for k, v in fb.items()]), hide_index=True)


# ---- trang: Hiệu quả quy trình (S14.45) --------------------------------------------------------------------------------
def _flow_table(groups: dict, label) -> "pd.DataFrame":
    return pd.DataFrame([{label[0]: label[1](k), "Nhánh": g["n"], "Tổng (nghìn)": g["total_k"], "Token/nhánh": g["per_branch_k"],
                          "% rà": g["pct_review"], "% sửa": g["pct_fix"], "Lỗi rà bắt": g["bugs"], "Token rà / lỗi": g["review_per_bug_k"],
                          "Vòng sửa / nhánh": g["fix_rounds_per_branch"]} for k, g in groups.items()])


def page_flow():
    st.title("Hiệu quả quy trình — token mỗi nhánh của vòng làm việc nhiều phiên")
    st.caption("Số đo mỗi nhánh đã gộp (phiên làm / rà / sửa, lỗi rà bắt) từ `devsys/workflow_runs.jsonl` trong git. Ghi sau mỗi nhánh gộp: "
               "`python -m devsys.workflow add S14.x --mode goi|usd|cloud --review ky|nhe --work … --review-k … --fix … --bugs …`. Miễn phí.")
    try:
        rows = workflow.load()
    except workflow.WorkflowError as e:
        st.error(f"File số đo hỏng: {e}")
        return
    try:
        with open(plan_progress.PLAN_FILE, encoding="utf-8") as f:
            got = workflow.parse_plan(f.read())
    except OSError:
        got = {"bad": [], "runs": []}
    if got["bad"]:
        st.warning("Dòng 'Số đo:' trong kế hoạch KHÔNG đọc được (sửa lại cho đúng dạng 'làm ≈ 200k + sửa ≈ 50k, rà ≈ 100k, rà bắt 3'):\n\n"
                   + "\n".join(f"- {b}" for b in got["bad"]))
    have = {(r.get("task"), r.get("part") or "") for r in rows}
    missing = [r for r in got["runs"] if (r["task"], r.get("part") or "") not in have]
    if missing:
        st.info(f"{len(missing)} nhánh có 'Số đo:' trong kế hoạch nhưng chưa có trong file: "
                + ", ".join(r["task"] + (" " + r["part"] if r.get("part") else "") for r in missing) + " — `python -m devsys.workflow import-plan --write`")
    if not rows:
        st.info("Chưa có số đo nào.")
        return
    s = workflow.summarize(rows)
    al, ky, nhe = s["all"], s["by_review"].get("ky") or {}, s["by_review"].get("nhe") or {}
    b = workflow.BASELINES

    def band(v, ref, lower_better=True):
        if v is None:
            return "none"
        return "ok" if (v <= ref if lower_better else v >= ref) else "warn"
    st.markdown("<div class='kpis'>" + "".join([
        kpi("Nhánh đã ghi", al["n"], f"tổng {al['total_k']:,}k token".replace(",", ".")),
        kpi("Token/nhánh rà kỹ", f"{ky.get('per_branch_k') or '—'}k", f"mốc B {b['B']['per_branch_ky_k']}k", band(ky.get("per_branch_k"), b["B"]["per_branch_ky_k"])),
        kpi("Token/nhánh rà nhẹ", f"{nhe.get('per_branch_k') or '—'}k", f"mốc B {b['B']['per_branch_nhe_k']}k", band(nhe.get("per_branch_k"), b["B"]["per_branch_nhe_k"])),
        kpi("% rà (rà kỹ)", f"{ky.get('pct_review') if ky.get('pct_review') is not None else '—'} %", f"mốc A {b['A']['pct_review']:.0f} % · B {b['B']['pct_review']:.0f} %"),
        kpi("% sửa (rà kỹ)", f"{ky.get('pct_fix') if ky.get('pct_fix') is not None else '—'} %", f"mốc B {b['B']['pct_fix']:.0f} %", band(ky.get("pct_fix"), b["B"]["pct_fix"])),
        kpi("Token rà / lỗi bắt", f"{ky.get('review_per_bug_k') or '—'}k", "rà kỹ, chỉ nhánh có ghi số lỗi"),
    ]) + "</div>", unsafe_allow_html=True)
    st.markdown("#### So với 2 mốc")
    st.dataframe(pd.DataFrame(workflow.compare(s)).astype(str), hide_index=True)
    st.markdown("#### Từng nhánh")
    st.dataframe(pd.DataFrame([{"Việc": r["task"] + (" " + r["part"] if r.get("part") else ""), "Ngày": r.get("date"),
                                "Chế độ": workflow.MODE_LABEL.get(r.get("mode"), "?"), "Mức rà": workflow.REVIEW_LABEL[r.get("review") or "?"],
                                "Làm": r.get("work_k"), "Rà": r.get("review_k"), "Sửa": r.get("fix_k"), "Tổng": workflow.total_k(r),
                                "Vòng sửa": r.get("fix_rounds"), "Lỗi rà bắt": r.get("bugs"), "Lỗi nặng": r.get("bugs_major"),
                                "Commit": r.get("commit"), "Ghi chú": r.get("note")} for r in rows]), hide_index=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### Theo mức rà")
        st.dataframe(_flow_table(s["by_review"], ("Mức rà", lambda k: workflow.REVIEW_LABEL.get(k, k))), hide_index=True)
    with c2:
        st.markdown("#### Theo ngày")
        st.dataframe(_flow_table(s["by_date"], ("Ngày", str)), hide_index=True)
    with c3:
        st.markdown("#### Theo chế độ tài khoản")
        st.dataframe(_flow_table(s["by_mode"], ("Chế độ", lambda k: workflow.MODE_LABEL.get(k, k))), hide_index=True)
    st.caption("Nhánh nhập từ kế hoạch: chế độ ghi 'gói' (giả định — kế hoạch không ghi), mức rà 'không rõ' khi dòng Số đo không nhắc tới rà; "
               "'thêm ≈ …k (đánh thức lại)' tính vào sửa. Mốc A/B lấy từ skill vong-lam-viec-theo-plan mục 2/2b.")


# ---- trang: Ai quyết (S14.50) ------------------------------------------------------------------------------------------
def page_decisions():
    st.title("Ai quyết — code, Claude hay người ở mỗi điểm của pipeline")
    st.caption("Từ `devsys/decisions.json` (liệt kê tay, test buộc khớp code). Đếm theo LOẠI quyết định, không theo số lượt chạy. "
               "Mục tiêu: điểm nào đang trả tiền Claude mà code làm được → chuyển sang code (0 USD, tất định). Miễn phí.")
    try:
        doc = decisions.load()
    except (OSError, ValueError) as e:
        st.error(f"Không đọc được devsys/decisions.json: {e}")
        return
    bad = decisions.problems(doc) + decisions.broken_wheres(doc) + [f"khâu Claude '{s}' có trong code nhưng chưa có trên bản đồ"
                                                                   for s in decisions.unmapped_stages(doc)]
    if bad:
        st.warning("Bản đồ lệch code:\n\n" + "\n".join(f"- {b}" for b in bad))
    s = decisions.summary(doc)
    al = s["all"]
    st.markdown("<div class='kpis'>" + "".join([
        kpi("Điểm quyết định", al["n"]),
        kpi("Code", f"{al['code']} · {al['pct']['code']} %", "0 USD, tất định", "ok"),
        kpi("Claude", f"{al['claude']} · {al['pct']['claude']} %", "tốn token", "warn"),
        kpi("Người duyệt", f"{al['human']} · {al['pct']['human']} %", "điểm chặn"),
        kpi("Gợi ý chuyển sang code", len(s["suggest"]), "xem bảng dưới"),
        kpi("Chưa nối luồng", al["chua_noi"], "code có, bat: false — không đếm"),
    ]) + "</div>", unsafe_allow_html=True)
    steps = doc.get("steps") or {}
    st.markdown("#### Theo bước")
    st.dataframe(pd.DataFrame([{"Bước": steps[k], "Điểm": v["n"], "Code": v["code"], "Claude": v["claude"], "Người": v["human"],
                                "% Claude": v["pct"]["claude"]} for k, v in s["by_step"].items() if v["n"]]), hide_index=True)
    st.markdown("#### Gợi ý: Claude → code / bỏ")
    st.dataframe(pd.DataFrame([{"Bước": steps.get(d["step"], d["step"]), "Việc": d["what"], "Khâu": d.get("stage"), "Ở đâu": d["where"],
                                "Gợi ý": d["suggest"]} for d in s["suggest"]]), hide_index=True)
    st.markdown("#### Toàn bộ")
    st.dataframe(pd.DataFrame([{"Bước": steps.get(d["step"], d["step"]), "Ai": decisions.WHO[d["who"]], "Việc": d["what"],
                                "Khâu": d.get("stage") or "", "Ở đâu": d["where"],
                                "Chưa nối": "chưa nối" if d.get("bat") is False else ""} for d in doc.get("items", [])]), hide_index=True)


# ---- trang: Làm ↔ Kiểm (K0a kế hoạch kiểm soát, mục 3.9 / 7) ----------------------------------------------------------------
_RED, _YELLOW = "background-color: #f8d0d0", "background-color: #fff1c2"


def page_stages():
    st.title("Làm ↔ Kiểm — khâu nào đang có kiểm trước tiền")
    st.caption("Từ `devsys/stages.json` (sổ khâu) + `devsys/error_types.json` (bảng loại lỗi); trạng thái dòng có `co` đọc từ cờ thật "
               "(`core.features.state`). Đỏ = khâu tốn tiền đang chạy mà không có kiểm trước đang chạy / học việc (N3). "
               "Vàng = lớp kiểm đọc chữ tự do để kết luận (N1). Cột 'Đợt' = đợt kế hoạch sẽ lấp.")
    try:
        raw, types, deci = stages.load_stages(), stages.load_error_types(), decisions.load()
    except (OSError, ValueError) as e:
        st.error(f"Không đọc được sổ khâu / bảng loại lỗi: {e}")
        return
    bad = stages.stage_problems(raw, deci) + stages.error_type_problems(types)
    if bad:
        st.warning("Sổ lệch hợp đồng:\n\n" + "\n".join(f"- {b}" for b in bad))
    doc = stages.effective(raw)
    rows = stages.summary_rows(doc)
    only = stages.only_building(types)
    st.markdown("<div class='kpis'>" + "".join([
        kpi("Khâu", len(rows)),
        kpi("Tốn tiền thiếu kiểm trước", sum(r["thieu"] for r in rows), "đỏ", "bad" if any(r["thieu"] for r in rows) else "ok"),
        kpi("Kiểm đọc chữ tự do", sum(r["tu_do"] for r in rows), "vàng", "warn"),
        kpi("Loại lỗi không có kiểm đang chạy",f"{len(only)} / {len(types.get('types', []))}", ", ".join(t["id"] for t in only)),
    ]) + "</div>", unsafe_allow_html=True)
    flags = [r for r in rows if r["ghi_co"]]
    if flags:
        st.info("Trạng thái đọc từ cờ khác ghi tay:\n\n" + "\n".join(f"- {r['id']}: {r['ghi_co']}" for r in flags))
    st.markdown("#### Khâu làm")
    df = pd.DataFrame([{"Khâu": r["id"], "Tên": r["ten"], "Tốn tiền": "có" if r["ton_tien"] else "—", "Khâu chạy": r["khau"],
                        "Kiểm trước": r["kiem_truoc"], "Kiểm sau": r["kiem_sau"], "Đọc từ": r["doc_tu"], "Cờ": r["co"], "Đợt": r["dot"]}
                       for r in rows])
    marks = {i: _RED if r["thieu"] else (_YELLOW if r["tu_do"] else "") for i, r in enumerate(rows)}
    st.dataframe(df.style.apply(lambda row: [marks[row.name]] * len(row), axis=1), hide_index=True)
    st.markdown("#### Loại lỗi (mục 4)")
    trows = stages.error_type_rows(types)
    tdf = pd.DataFrame([{"Loại": r["id"], "Tên": r["ten"], "Áp cho": r["ap_dung"], "Có (code / Claude)": r["co"] or "—",
                         "Xây (đợt)": r["xay"] or "—"} for r in trows])
    st.dataframe(tdf.style.apply(lambda row: [_RED if trows[row.name]["chi_xay"] else ""] * len(row), axis=1), hide_index=True)


def page_running():
    from devsys import activity
    st.title("Đang chạy — nhánh, worktree, việc giao")
    st.caption("Git local sau lần fetch gần nhất; trang chỉ đọc. Có dấu rà/kết quả không đồng nghĩa đã rà độc lập hay đã gộp.")
    data = activity.snapshot(ROOT)
    for error in data["errors"]:
        st.error(error)
    st.subheader("Nhánh chưa gộp origin/main")
    st.dataframe([{"Nhánh": b["branch"], "Của ai": b["owner"], "Commit cuối": b["commit"], "Ngày": b["date"],
                   "Commit chưa gộp": b["ahead"], "Đổi file": b["stat"], "Bằng chứng rà": b["review_evidence"] or "Chưa thấy",
                   "Đọc kết quả nhánh": b["report_error"] or "—"}
                  for b in data["branches"]], hide_index=True, width="stretch")
    st.subheader("Worktree")
    st.dataframe(data["worktrees"], hide_index=True, width="stretch")
    st.subheader("Việc giao Codex")
    st.dataframe([{"Đợt": t["wave"], "Việc": t["task"], "Tên": t["title"],
                   "Kết quả trong checkout": "Có" if t["has_result"] else "Chưa", "Nhánh": t["branch"], "Commit": t["commit"],
                   "Kết quả trên nhánh chưa gộp": "; ".join(f"{r['source']} · {r['commit']}" for r in t["unmerged_results"])}
                  for t in data["tasks"]], hide_index=True, width="stretch")


PAGES = {"Đang chạy": page_running, "📋 Kế hoạch đang chạy": page_plan, "Tổng quan": page_overview, "Bản đồ hệ thống": page_map, "Dòng thời gian": page_timeline, "Sức khỏe (đo bằng code)": page_health,
         "Chấm điểm AI": page_scores, "Hiệu quả vận hành": page_effect, "Hiệu quả quy trình": page_flow, "Ai quyết": page_decisions, "Làm ↔ Kiểm": page_stages,
         "Bộ kỹ năng 3 vai": page_skills}
PAGES[page]()
