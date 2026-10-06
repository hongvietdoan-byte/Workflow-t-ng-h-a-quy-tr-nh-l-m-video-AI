"""Người chấm AI khách quan của AI Development System.

- Dữ liệu gửi người chấm: thang cố định (devsys/rubric.md) + trích code thật của khu vực (chữ ký hàm, docstring, dòng đánh dấu có số
  dòng) + kết quả test thật + dòng TODO còn mở + trạng thái cờ + cảnh báo diag + git diff từ lần chấm trước. KHÔNG có commit message.
- Lời gọi Claude đi qua client có sổ chi của dự án (core.llm_runner.AnthropicClient, ledger = data/manifest.sqlite, stage "devsys"):
  ghi vào usage_events và bị chặn bởi trần Claude (core.budget.check_llm) như mọi bước khác. Trước khi gọi luôn có ước tính và phải
  xác nhận (`--yes` ở dòng lệnh, nút xác nhận ở web).
- Điểm do code tính từ các khoản trừ có bằng chứng (devsys/scores.normalize), có giới hạn do code áp.
- provider "mock": người chấm giả lập tất định cho test/demo — không gọi mạng, không ghi sổ chi.
"""
import ast
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime
from typing import Callable, Dict, List, Optional, Sequence

from . import collect, metrics, scores

EXPECTED_OUTPUT_TOKENS = 4500        # một câu trả lời JSON chấm 1 khu vực (~6–15 khoản trừ kèm feedback + checklist 12 loại lỗi), effort thấp
MAX_OUTPUT_TOKENS = 16000            # = STAGE_SETTINGS["devsys"]["max_tokens"] trong core/llm_runner.py
CHARS_PER_TOKEN = 3.0                # ước tính thận trọng cho chữ Việt + code (tiếng Anh ~4)
CODE_BUDGET = 42000                  # ký tự trích code tối đa mỗi khu vực
DOCS_BUDGET = 6000                   # ký tự trích tài liệu mỗi khu vực (khu vực "Tài liệu": 20000)
TODO_BUDGET = 12000
DIFF_BUDGET = 9000
PER_FILE_LINES = 140
LINE_CUT = 150
_MARK = re.compile(r"TODO|FIXME|XXX|NotImplementedError|features\.on|budget\.|check_llm|record_usage|ledger|ước tính|estimate|"
                   r"except\s+Exception|except\s*:|pass\s*$|raise \w*Error\(|diag\.record|st\.button\(|confirm|chưa", re.I)
_MD_MARK = re.compile(r"✅|⏳|chưa|đã sửa|còn:|\[ \]|cần người dùng", re.I)


class ScorerError(Exception):
    pass


def _root_on_path(root: str = collect.ROOT) -> None:
    """The project's own code (core.*) always comes from the repo devsys lives in — never from the repo being measured (tests
    measure small temporary repos)."""
    if collect.ROOT not in sys.path:
        sys.path.insert(0, collect.ROOT)


# ---- trích code / tài liệu ------------------------------------------------------------------------------------------
def excerpt_py(root: str, rel: str, max_lines: int = PER_FILE_LINES) -> str:
    """Outline of a Python file with real line numbers: module docstring, every def/class with its docstring's first line, and
    the lines that matter for the rubric (error handling, cost ledger, feature flags, buttons, TODO…)."""
    full = os.path.join(root, rel)
    try:
        with open(full, encoding="utf-8", errors="replace") as f:
            src = f.read()
    except OSError as e:
        return f"### {rel}\n(không đọc được: {e})\n"
    lines = src.splitlines()
    picked: Dict[int, str] = {}
    doc = ""
    try:
        tree = ast.parse(src)
        doc = (ast.get_docstring(tree) or "").strip()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                d = (ast.get_docstring(node) or "").strip().splitlines()
                head = lines[node.lineno - 1].strip() if node.lineno - 1 < len(lines) else node.name
                picked[node.lineno] = head + (f"   # {d[0]}" if d else "")
    except SyntaxError as e:
        picked[0] = f"(lỗi cú pháp khi đọc: {e})"
    marks = [(i, l.strip()) for i, l in enumerate(lines, 1) if _MARK.search(l) and i not in picked]
    room = max(0, max_lines - len(picked))
    for i, l in marks[:room]:
        picked[i] = l
    dropped = len(marks) - min(len(marks), room)
    body = "\n".join(f"L{i}: {t[:LINE_CUT]}" for i, t in sorted(picked.items()) if i)
    head = f"### {rel} ({len(lines)} dòng)\n"
    if doc:
        head += "Docstring: " + " ".join(doc.split())[:500] + "\n"
    if dropped:
        body += f"\n(… bỏ {dropped} dòng đánh dấu khác vì giới hạn {max_lines} dòng/file)"
    return head + body + "\n"


def excerpt_md(root: str, rel: str, max_lines: int = 60) -> str:
    full = os.path.join(root, rel)
    try:
        with open(full, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError as e:
        return f"### {rel}\n(không đọc được: {e})\n"
    picked = [(i, l.strip()) for i, l in enumerate(lines, 1) if l.startswith("#") or _MD_MARK.search(l)]
    body = "\n".join(f"L{i}: {t[:LINE_CUT]}" for i, t in picked[:max_lines])
    more = f"\n(… bỏ {len(picked) - max_lines} dòng)" if len(picked) > max_lines else ""
    return f"### {rel} ({len(lines)} dòng)\n{body}{more}\n"


# ---- dữ liệu mỗi khu vực ----------------------------------------------------------------------------------------------
def _file_hash(root: str, rel: str) -> str:
    try:
        with open(os.path.join(root, rel), "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return "-"


def facts_of(health: Dict, snap: Dict) -> Dict:
    root = snap.get("root") or collect.ROOT
    return {"test_files": health.get("test_files", 0), "has_run": bool(snap.get("latest_run")), "failed": health.get("failed", 0),
            "runs_dir": os.path.isdir(os.path.join(collect.data_dir(root), "runs"))}     # S4: no devsys/data/runs ≠ "never ran the tests"


def facts_for(root: str, cfg: Dict, area: Dict, snap: Dict, health: Dict) -> Dict:
    """Facts of a bản 2 score: the old caps' facts + the code-measured numbers and automatic deductions (devsys/metrics.py)."""
    return {**facts_of(health, snap), **metrics.facts_extra(root, cfg, area, snap)}


def prev_summary(last: Optional[Dict]) -> Optional[Dict]:
    """What the stability rule needs from the area's previous score (a bản 2 score of the same rubric is comparable)."""
    if not last:
        return None
    return {k: last.get(k) for k in ("score", "auto_points", "rubric_hash", "format", "date", "commit", "criteria", "checklist")}


def fingerprint(root: str, area: Dict, snap: Dict, health: Dict) -> str:
    """What the score of an area depends on: its files' content, its open TODO lines, its test results, its flags and the rubric.
    Unchanged fingerprint = nothing to re-score (incremental mode)."""
    h = hashlib.sha256()
    h.update(scores.rubric_hash(root).encode())
    h.update(json.dumps(area, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    for f in collect.area_files(area, snap["files"]):
        h.update(f.encode("utf-8"))
        h.update(_file_hash(root, f).encode())
    for it in snap["todo_by_area"].get(area["id"], []):
        h.update(it["text"].encode("utf-8"))
    t = snap["tests_by_area"].get(area["id"], {})
    # S17 (thang 2.1): whether tests fail / error / exist — not how many pass (adding a test is not a reason to score again)
    h.update(json.dumps({"failed": bool(t.get("failed")), "errors": bool(t.get("errors")), "has_tests": bool(t.get("test_files"))},
                        sort_keys=True).encode())
    h.update(json.dumps([(f["name"], f["verified"], f["on"]) for f in snap["flags"] if area["id"] in f["areas"]]).encode())
    if area.get("ui_metrics"):
        h.update(_file_hash(root, metrics.UI_FILE).encode())           # a new real UI measurement is a reason to score again
    if area.get("ops_stages"):                                         # S14.10 Đợt 6b: a new effectiveness snapshot / new unhandled feedback
        ops = snap.get("ops") or {}
        mine = collect.ops_for_area(ops, area)
        h.update(json.dumps([(ops.get("latest") or {}).get("id"), len(mine["low_open_30d"])]).encode())
    return h.hexdigest()[:20]


def test_ref(file: str, junit_name: str) -> str:
    """S14.10 S2: a failing test as the citation the rubric asks for — `test:tests/x.py::Lớp::tên` (the class comes from the JUnit
    classname `tests.test_x.Lop`), so the scorer can cite it and code can check it."""
    classname, _, name = str(junit_name).rpartition("::")
    cls = classname.rsplit(".", 1)[-1] if classname else ""
    stem = os.path.splitext(os.path.basename(file))[0]
    return f"test:{file}::{cls}::{name}" if cls and cls != stem else f"test:{file}::{name}"


def _pct(v) -> str:
    return "—" if v is None else f"{100 * float(v):.0f} %"


def ops_text(snap: Dict, area: Dict) -> Dict[str, str]:
    """S14.10 Đợt 6b: the two bundle sections on the OUTPUT of real runs — "Hiệu quả vận hành" (effectiveness snapshots: first-pass,
    minutes and cost per second, satisfaction, what changed between snapshots) and "Góp ý người dùng" (feedback of the area's stages).
    No database → says so (a missing input is never silent)."""
    ops = snap.get("ops") or {}
    if not ops.get("available"):
        note = f"(không có: {ops.get('note') or 'chưa thu số đo hiệu quả'})"
        return {"effect": note, "feedback": note}
    mine = collect.ops_for_area(ops, area)
    if not mine["stages"]:
        return {"effect": "(khu vực không gắn khâu vận hành — areas.json không có 'ops_stages')",
                "feedback": "(khu vực không gắn khâu vận hành)"}
    rows = ops.get("trend") or []
    if rows:
        lines = [f"- db:effectiveness_snapshots:{r['id']} · {r['at']} · ảnh qua lần đầu {_pct(r.get('image_first_pass'))} · video qua lần đầu "
                 f"{_pct(r.get('video_first_pass'))} · {r.get('wall_min_per_sec') or '—'} phút/giây · {r.get('cost_per_sec') or '—'} $/giây · "
                 f"hài lòng {_pct(r.get('satisfaction'))} ({r.get('feedback_n') or 0} góp ý) · {len(r.get('flags_on') or [])} cờ bật"
                 for r in rows[-8:]]
        marks = [f"- {m['at']} [{m['kind']}] {m['text']}" for m in (ops.get("markers") or [])[-10:]]
        effect = (f"Khâu của khu vực: {', '.join(mine['stages'])}; chỉ số gắn khu vực: {', '.join(mine['figures']) or '—'}.\n"
                  + "\n".join(lines) + ("\nThay đổi giữa các mốc:\n" + "\n".join(marks) if marks else ""))
    else:
        effect = f"(chưa có mốc hiệu quả toàn hệ thống trong {ops.get('days', 90)} ngày — {ops.get('note')})"
    fb = mine["feedback"]
    if fb:
        lines = [f"- {st}: {v['n']} góp ý, {v['rated']} có điểm, {v['positive']} hài lòng (≥ 4), {v['low']} không hài lòng (≤ 2), "
                 f"{len(v['low_open_30d'])} không hài lòng chưa xử lý trong 30 ngày" for st, v in fb.items()]
        rec = [f"- db:user_feedback:{f['id']} {f['at']} [{f['stage']}] {f['rating'] or '—'}/5{' (đã xử lý)' if f['handled'] else ''}: {f['text']}"
               for f in (ops.get("feedback") or {}).get("recent", []) if f.get("stage") in mine["stages"]][:12]
        feedback = "\n".join(lines) + ("\nGần đây:\n" + "\n".join(rec) if rec else "")
    else:
        feedback = f"(không có góp ý nào cho khâu {', '.join(mine['stages'])} trong {ops.get('days', 90)} ngày)"
    return {"effect": effect, "feedback": feedback}


def _cap(parts: List[str], budget: int, what: str, notes: List[str]) -> str:
    out, used, dropped = [], 0, []
    for p in parts:
        if used + len(p) > budget:
            dropped.append(p.split("\n", 1)[0])
            continue
        out.append(p)
        used += len(p)
    if dropped:
        notes.append(f"{what}: bỏ {len(dropped)} mục vì vượt {budget} ký tự — " + "; ".join(d[:80] for d in dropped[:12]))
    return "\n".join(out)


def build_bundle(root: str, cfg: Dict, area: Dict, snap: Dict, health: Dict, last: Optional[Dict] = None) -> Dict:
    """The full prompt for one area + its fingerprint, input hash and facts (for the code caps)."""
    _root_on_path(root)
    from core.prompts import CACHE_BREAK
    notes: List[str] = []
    files = snap["files"]
    code = collect.area_files(area, files, ("code",))
    assets = collect.area_files(area, files, ("assets",))
    docs = collect.area_files(area, files, ("docs",))

    code_txt = _cap([excerpt_py(root, f) for f in code if f.endswith(".py")], CODE_BUDGET, "Trích code", notes) or "(khu vực không có code)"
    listing = "\n".join(f"- {f} ({snap['line_counts'].get(f) or collect.line_count(os.path.join(root, f))} dòng)"
                        for f in assets + docs) or "(không có)"
    docs_budget = 20000 if area["id"] == "docs" else DOCS_BUDGET
    docs_txt = _cap([excerpt_md(root, f) for f in docs if f.endswith(".md")], docs_budget, "Trích tài liệu", notes) or "(không có)"

    t = snap["tests_by_area"].get(area["id"], {})
    run = snap.get("latest_run")
    if run:
        tt = run.get("totals") or {}
        test_txt = (f"Lần chạy mới nhất: {run.get('date')} · commit {run.get('short')} · toàn bộ: {tt.get('tests')} test, "
                    f"{tt.get('failed')} lỗi, {tt.get('errors')} lỗi chạy, {tt.get('skipped')} bỏ qua.\n"
                    f"Của khu vực ({len(t.get('test_files', []))} file test): {t.get('passed', 0)} qua, {t.get('failed', 0)} lỗi, "
                    f"{t.get('errors', 0)} lỗi chạy, {t.get('skipped', 0)} bỏ qua.")
        if t.get("failed_names"):
            test_txt += "\nTest lỗi:\n" + "\n".join(f"- {test_ref(n['file'], n['name'])} — {n.get('message', '')}"
                                                   for n in t["failed_names"][:25])
        stale = snap.get("tests_stale")
        if stale:
            test_txt += (f"\n⚠ LẦN CHẠY TEST NÀY CŨ HƠN CODE: {len(stale['files'])} file đổi sau đó — "
                         + ", ".join(stale["files"][:15]) + " (số test trên không nói gì về phần đổi).")
    else:
        test_txt = f"CHƯA CÓ LẦN CHẠY TEST NÀO ĐƯỢC LƯU. File test nhắm vào khu vực: {len(t.get('test_files', []))}."
    test_txt += "\nFile test nhắm vào khu vực (tự dò theo import): " + (", ".join(t.get("test_files", [])) or "KHÔNG CÓ")
    area_mods = [f for f in code if f.endswith(".py") and not f.endswith("__init__.py")]
    covered = {m for tf in t.get("test_files", []) for m in snap["test_map"].get(tf, {}).get("modules", [])}
    untested = [m for m in area_mods if m not in covered]
    test_txt += "\nModule của khu vực không có test nào import tới: " + (", ".join(untested) or "không")

    flags = [f for f in snap["flags"] if area["id"] in f["areas"]]
    flag_txt = "\n".join(f"- flag:{f['name']} · verified={f['verified']} · đang {'BẬT' if f['on'] else 'tắt'}"
                         f"{' (biến môi trường ' + f['env'] + ')' if f['env'] else ''}{' — ' + f['on_why'] if f.get('on_why') else ''} · {f['label']} · vì sao chưa kiểm: {f['why']} · dùng ở: "
                         f"{', '.join(f['sites'][:6]) or 'không thấy features.on(...) trong code'}" for f in flags) or "(khu vực không có cờ)"

    todo_items = [i for i in snap["todo_by_area"].get(area["id"], []) if i["kind"] != "recurring"]
    work = {"nguoi_dung": " [việc người dùng]", "quy_uoc": " [quy ước]"}
    todo_txt = _cap([f"- TODO.md:{i['line']} [{', '.join(i['markers'])}]{' [chờ người dùng]' if i['waiting_user'] else ''}"
                     f"{work.get(metrics.todo_work_kind(i), '')}"
                     f"{' [tạm gác]' if i['kind'] == 'paused' else ''} (mục: {i['section'][:60]}) "
                     f"{(i['focus'] or i['text'])[:400]}" for i in todo_items], TODO_BUDGET, "Dòng TODO", notes) or "(không có dòng TODO còn mở gán cho khu vực)"

    diag = snap.get("diag", {})
    if diag.get("available"):
        rec = [r for r in diag.get("recent", []) if r["stage"] in area.get("diag_stages", [])][:15]
        diag_txt = "\n".join(f"- [{r['severity']}] {r['stage']} ×{r['count']} ({r['last_at']}): {r['message'][:200]}" for r in rec) or "(không có cảnh báo)"
    else:
        diag_txt = f"(không có: {diag.get('note', 'không có CSDL')})"
    big_txt = "\n".join(f"- {f}: {n} dòng" for f, n in health.get("big_files", [])) or "(không có file > 900 dòng)"

    diff_txt = "(lần chấm đầu tiên của khu vực — không có diff)"
    if last and last.get("commit"):
        paths = collect.area_files(area, files)
        try:
            stat = collect.git(root, "diff", "--stat", last["commit"], "--", *paths)
            patch = collect.git(root, "diff", "-U1", last["commit"], "--", *[p for p in paths if p.endswith(".py")])
            if len(patch) > DIFF_BUDGET:
                notes.append(f"Diff: cắt còn {DIFF_BUDGET} / {len(patch)} ký tự")
                patch = patch[:DIFF_BUDGET] + "\n(… đã cắt)"
            diff_txt = (f"Từ lần chấm trước ({last.get('date')}, commit {str(last['commit'])[:9]}, điểm {last.get('score')}):\n"
                        f"{stat.strip() or '(không đổi file nào)'}\n\n{patch}")
        except collect.GitError as e:
            diff_txt = f"(không lấy được diff từ commit {str(last['commit'])[:9]}: {e})"

    facts = facts_for(root, cfg, area, snap, health)
    ops = ops_text(snap, area)
    auto_txt ="\n".join(f"- −{a['points']:g} ({a['criterion']}) {a['reason']}"
                         f"{' [dấu hiệu, cần xác minh]' if a.get('heuristic') else ''} — " + ", ".join(a["evidence"][:4]) for a in facts["auto"]) \
        or "(code không đo thấy khoản trừ nào)"
    m = facts["metrics"]
    auto_txt += (f"\nSố đo thô: {m['code_files']} module · {len(m['modules_untested'])} module không test · hàm công khai "
                 f"{m['funcs_public']} (test nhắc tới tên: {m['funcs_public'] - m['funcs_untested']}) · except nuốt lỗi {len(m['swallowed'])} · "
                 f"hàm > {metrics.LONG_FUNC_LINES} dòng {len(m['long_funcs'])} · điều khiển giao diện {sum(m['controls'].values())}")
    if m["swallowed"]:
        auto_txt += "\nExcept nuốt lỗi (file:dòng): " + ", ".join(m["swallowed"][:12]) + (" …" if len(m["swallowed"]) > 12 else "")
    if facts.get("ui_measured"):
        ui = facts.get("ui") or {}
        auto_txt += ("\nĐo giao diện thật: " + (
            f"tương phản <4,5:1 = {ui.get('contrast_fail')}, chữ <12,5px = {ui.get('small_text')}, click cũ→v2 = {ui.get('clicks_old')}→{ui.get('clicks_v2')}, "
            f"rerun chậm nhất {ui.get('perf_worst_pct')} %, khóa widget mất = {ui.get('keys_lost')} (nguồn {ui.get('source') or '?'})"
            if facts.get("ui_present") else "CHƯA CÓ (devsys/data/ui_metrics.json) — trai_nghiem bị code giới hạn tối đa "
                                            f"{scores.UI_NO_MEASURE_CAP:g}; chạy py tools/devsys_ui_metrics.py"))
    prev = prev_summary(last) if last and last.get("rubric_hash") == scores.rubric_hash(root) else None
    if prev and scores.is_v2(prev):
        rows = []
        for ck, c in (prev.get("criteria") or {}).items():
            for d in c.get("deductions", []):
                if not d.get("auto"):
                    rows.append(f"- {ck} [{d.get('muc')}] −{d['points']:g}: {d['reason'][:110]} — {', '.join(d['evidence'][:2])}")
        prev_txt = (f"Lần trước: {prev['score']:g}/100 (khoản trừ tự động {prev.get('auto_points', 0):g}), {str(prev.get('date'))[:16]}. "
                    f"Điểm chưa tính khoản trừ tự động lần này không được lệch quá {scores.DRIFT_LIMIT:g} so với "
                    f"{prev['score'] + (prev.get('auto_points') or 0):g} nếu không có `giai_thich_chenh`.\nKhoản trừ lần trước (còn đúng thì giữ; "
                    "đã sửa thì bỏ và nói vì sao):\n" + ("\n".join(rows[:30])[:4000] or "(không có)"))
    else:
        prev_txt = "(không có điểm cùng thang hiện tại để đối chiếu — không áp quy tắc ổn định lần này)"
    rubric = open(os.path.join(root, "devsys", "rubric.md"), encoding="utf-8").read()
    try:                                   # S8.1: the feedback format lives outside the rubric (its hash, old scores unchanged)
        rubric += "\n\n" + open(os.path.join(root, "devsys", "feedback_format.md"), encoding="utf-8").read()
    except OSError:
        pass
    fixed = ("# Người chấm độc lập — AI Development System\n"
             "Bạn chấm mức hoàn thiện THẬT của một khu vực trong repo pipeline làm video AI, theo thang cố định bên dưới. Nguyên tắc:\n"
             "- Chỉ dựa vào DỮ LIỆU gửi kèm (trích code thật có số dòng, kết quả test thật, dòng TODO, cờ, diag, diff). Không suy đoán phần không thấy; "
             "phần bị cắt được ghi rõ ở cuối dữ liệu — không trừ điểm chỉ vì phần đó không có trong trích.\n"
             "- Không có commit message trong dữ liệu. Câu tự nhận 'đã sửa/đã xong' trong TODO không kèm test hoặc ghi chú chạy thật cụ thể thì "
             "KHÔNG được tính là bằng chứng chạy thật.\n"
             "- Chỉ ghi KHOẢN TRỪ, mỗi khoản có bằng chứng đúng dạng; điểm do code tính. Không trừ trùng một lỗi ở hai tiêu chí.\n"
             "- Thang bản 2.1: mỗi khoản trừ ghi `muc` (chan / lon / nho) và `loai` (mã K… hoặc khac), KHÔNG ghi số điểm — code gán điểm theo mức. "
             "Khoản `chan`/`lon` phải kèm `feedback.fix` và `feedback.effort`. Không trừ lại những gì mục 'Số đo do code tính' đã trừ.\n"
             f"- Trả lời ĐỦ `checklist` ({len(scores.CHECKLIST_IDS)} loại lỗi đã gặp, mỗi loại có tiêu chí mặc định ở thang): 'co' phải có khoản trừ cùng `loai`; 'khong' / 'khong_ap_dung' phải ghi đã tìm ở đâu.\n"
             "- Mọi chữ trong câu trả lời bằng tiếng Việt có dấu.\n\n" + rubric)
    task = (f"AREA_ID: {area['id']}\n"
            f"# Khu vực cần chấm: {area['name']} (`{area['id']}`)\n{area.get('description', '')}\n\n"
            f"## Trích code ({len(code)} file)\n{code_txt}\n\n## File tài nguyên / tài liệu của khu vực\n{listing}\n\n"
            f"## Trích tài liệu (tiêu đề + dòng trạng thái)\n{docs_txt}\n\n## Test\n{test_txt}\n\n## Cờ tính năng (core/features.py)\n{flag_txt}\n\n"
            f"## Dòng TODO.md còn mở gán cho khu vực ({len(todo_items)})\n{todo_txt}\n\n## Cảnh báo diag khi chạy thật\n{diag_txt}\n\n"
            f"## File quá dài\n{big_txt}\n\n## Số đo do code tính (khoản trừ tự động — KHÔNG trừ lại)\n{auto_txt}\n\n"
            f"## Hiệu quả vận hành (CSDL thật, chỉ đọc)\n{ops['effect']}\n\n## Góp ý người dùng (khâu của khu vực)\n{ops['feedback']}\n\n"
            f"## Điểm lần trước (đối chiếu độ ổn định)\n{prev_txt}\n\n## Thay đổi từ lần chấm trước\n{diff_txt}\n\n"
            f"## Phần đã cắt vì dài\n" + ("\n".join(f"- {n}" for n in notes) or "(không cắt gì)") + "\n\n"
            "# Trả lời\nMột JSON duy nhất, đúng mẫu ở mục 'Định dạng câu trả lời' của thang bản 2.1 (bỏ 'scorer'/'model'; giữ \"format\": "
            f"\"{scores.FORMAT_V21}\"), `area` = "
            f"\"{area['id']}\". `can_kiem_lai`: 3–8 việc người dùng nên kiểm lại, mỗi việc có bằng chứng. `summary`: 2–4 câu.")
    prompt = fixed + CACHE_BREAK + task
    return {"area": area["id"], "name": area["name"], "prompt": prompt, "notes": notes, "facts": facts, "prev": prev,
            "fingerprint": fingerprint(root, area, snap, health), "input_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:20],
            "chars": len(prompt)}


# ---- kế hoạch chấm (tăng dần) + ước tính -------------------------------------------------------------------------------
def default_model() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "").strip() or "claude-sonnet-5"


def plan(root: str, cfg: Dict, snap: Dict, health: Dict, area_ids: Optional[Sequence[str]] = None, redo_all: bool = False,
         provider: str = "anthropic") -> Dict:
    """Which areas to (re)score. Default: those whose fingerprint changed since their last score (of the same kind: a mock score
    never counts as a real one). `redo_all` or an explicit `area_ids` list scores those anyway."""
    all_scores, _ = scores.load_all(root)
    same = [s for s in all_scores if str(s.get("scorer", "")).startswith("mock") == (provider == "mock")]
    last_by = {}
    for s in same:
        last_by[s["area"]] = s
    todo, skipped = [], []
    wanted = list(area_ids) if area_ids else [a["id"] for a in cfg["areas"]]
    by_id = collect.area_by_id(cfg)
    unknown = [a for a in wanted if a not in by_id]
    if unknown:
        raise ScorerError(f"không có khu vực: {', '.join(unknown)} (xem devsys/areas.json)")
    for aid in wanted:
        area = by_id[aid]
        last = last_by.get(aid)
        fp = fingerprint(root, area, snap, health[aid])
        if last and not redo_all and not area_ids and last.get("fingerprint") == fp:
            skipped.append({"area": aid, "why": f"không đổi từ lần chấm {str(last.get('date'))[:16]} (điểm {last['score']})"})
            continue
        why = ("chấm lại theo yêu cầu" if (redo_all or area_ids) and last else "chưa chấm lần nào" if not last
               else "thang chấm đổi" if last.get("rubric_hash") != scores.rubric_hash(root) else "file / TODO / test / cờ đã đổi")
        b = build_bundle(root, cfg, area, snap, health[aid], last)
        b["why"] = why
        todo.append(b)
    return {"todo": todo, "skipped": skipped}


def estimate(bundles: Sequence[Dict], model: Optional[str] = None) -> Dict:
    """Tokens and USD before any call (prices: data/pricing.json per_million_tokens). usd_max = every answer uses max_tokens AND is
    asked twice (the one retry after an invalid JSON)."""
    from core import budget, cost
    model = model or default_model()
    pricing = cost.load_pricing()
    pin = budget.token_price(pricing, model, "input", 1_000_000)
    pout = budget.token_price(pricing, model, "output", 1_000_000)
    rows = []
    for b in bundles:
        tin = math.ceil(b["chars"] / CHARS_PER_TOKEN)
        exp = None if pin is None else (tin * pin + EXPECTED_OUTPUT_TOKENS * pout) / 1_000_000
        mx = None if pin is None else 2 * (tin * pin + MAX_OUTPUT_TOKENS * pout) / 1_000_000
        rows.append({"area": b["area"], "input_tokens": tin, "usd_expected": exp, "usd_max": mx})
    known = pin is not None
    return {"model": model, "priced": known, "price_in": pin, "price_out": pout, "areas": len(rows), "rows": rows,
            "input_tokens": sum(r["input_tokens"] for r in rows), "output_tokens_expected": EXPECTED_OUTPUT_TOKENS * len(rows),
            "usd_expected": round(sum(r["usd_expected"] for r in rows), 4) if known else None,
            "usd_max": round(sum(r["usd_max"] for r in rows), 4) if known else None}


def score_command(areas: Sequence[str], provider: str, est: Dict) -> List[str]:
    """Arguments of `tools/devsys_score.py` for the page's "Chấm" button. Claude API: the hard lock `--max-usd` (core/script_cap.py,
    S14.2) = the worst case of the estimate rounded UP to the cent — without it the script refuses to run (rà soát A2)."""
    cmd = [os.path.join("tools", "devsys_score.py"), "--areas", ",".join(areas), "--provider", provider, "--yes"]
    if provider != "mock":
        cap = math.ceil(float(est.get("usd_max") or 0.0) * 100 - 1e-9) / 100
        cmd += ["--max-usd", f"{max(cap, 0.01):.2f}"]
    return cmd


_FAILED = re.compile(r"^(Từ chối chạy|DỪNG|Lỗi:|Không chấm|Traceback|SystemExit|\w*Error\b)", re.M)


def run_state(log: str) -> str:
    """'failed' | 'done' | 'running' from the log of a spawned scoring run (a refusal / stop / crash is a failure to SHOW on the page,
    not only in the log — rà soát A2)."""
    if _FAILED.search(log or ""):
        return "failed"
    return "done" if re.search(r"^Xong:", log or "", re.M) else "running"


def _n(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def estimate_text(est: Dict) -> str:
    if not est["areas"]:
        return "Không có khu vực nào cần chấm."
    if not est["priced"]:
        return f"Model {est['model']} chưa có giá trong data/pricing.json — không ước tính được, không chấm (thêm giá trước)."
    return (f"Ước tính chấm {est['areas']} khu vực bằng {est['model']}: ~{_n(est['input_tokens'])} token vào + "
            f"~{_n(est['output_tokens_expected'])} token ra ≈ ${est['usd_expected']:.2f} (tối đa ${est['usd_max']:.2f} nếu mọi câu trả lời "
            f"dùng hết {_n(MAX_OUTPUT_TOKENS)} token và phải hỏi lại một lần). Ghi vào sổ chi, stage \"devsys\", tính vào trần Claude.")


# ---- client ----------------------------------------------------------------------------------------------------------
class MockScorerClient:
    """Deterministic stand-in: a valid score answer from the facts in the prompt. No network, no cost ledger."""
    name = "mock-devsys"
    model = "mock"

    def complete(self, prompt: str, images=()):
        from core.llm_runner import LlmReply
        aid = (re.search(r"^AREA_ID: (\S+)", prompt, re.M) or [None, "?"])[1]
        no_run = "CHƯA CÓ LẦN CHẠY TEST" in prompt
        todo_n = int((re.search(r"## Dòng TODO\.md còn mở gán cho khu vực \((\d+)\)", prompt) or [None, "0"])[1])
        crit = {k: {"deductions": [], "evidence_for": []} for k in scores.CRITERIA_MAX_V2}
        if todo_n:
            first = re.search(r"- (TODO\.md:\d+)", prompt)
            crit["chuc_nang"]["deductions"].append({"muc": "nho", "loai": "khac", "reason": f"{todo_n} dòng TODO còn mở (giả lập)",
                                                    "evidence": [first.group(1) if first else "absent:giả lập"]})
        crit["bang_chung"]["deductions"].append({"muc": "lon", "loai": "khac", "reason": "giả lập: chưa đọc báo cáo chạy thật",
                                                 "evidence": ["absent:giả lập"],
                                                 "feedback": {"fix": "Chạy người chấm thật (Claude) hoặc người chấm ngoài rồi ghi lần chạy.",
                                                              "effort": "👤", "priority": 2}})
        if no_run:
            crit["test"]["deductions"].append({"muc": "nho", "loai": "khac", "reason": "chưa có lần chạy test lưu lại (giả lập)",
                                               "evidence": ["absent:không có devsys/data/runs"]})
        out = {"format": scores.FORMAT_V21, "area": aid, "criteria": crit,
               "checklist": {k: {"tra_loi": "khong_ap_dung", "ghi_chu": "giả lập — không đọc code"} for k in scores.CHECKLIST_IDS},
               "summary": f"Điểm giả lập cho khu vực {aid} — chỉ để thử luồng, không phải đánh giá thật.",
               "can_kiem_lai": [{"what": "Chạy người chấm thật (Claude) hoặc người chấm ngoài", "why": "đây là điểm giả lập",
                                 "evidence": ["absent:giả lập"]}]}
        return LlmReply("```json\n" + json.dumps(out, ensure_ascii=False) + "\n```", len(prompt) // 4, 300)


def make_client(provider: str, db_path: Optional[str], transport=None):
    """provider 'mock' → MockScorerClient; 'anthropic' → the project's AnthropicClient bound to the cost ledger (never without it)."""
    if provider == "mock":
        return MockScorerClient()
    if provider != "anthropic":
        raise ScorerError(f"provider '{provider}' không hỗ trợ (anthropic | mock). Chế độ Claude Code trên máy không ghi sổ chi → dùng "
                          "người chấm ngoài: py tools/devsys_score.py --export <khu_vực> rồi --import")
    if not db_path or not os.path.exists(db_path):
        raise ScorerError(f"không thấy sổ chi {db_path or 'data/manifest.sqlite'} — mở Dashboard thật một lần (tạo CSDL) rồi chấm; "
                          "không gọi Claude ngoài sổ chi")
    from core import llm_runner
    kwargs = {"ledger": db_path}
    if transport is not None:
        kwargs["transport"] = transport
    try:
        return llm_runner.AnthropicClient.from_env(**kwargs)
    except llm_runner.LlmError as e:
        raise ScorerError(str(e)) from None


def budget_room(db_path: str) -> Optional[float]:
    """USD left under the Claude cap (None when the cap is off)."""
    import sqlite3
    from core import budget
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        st = budget.status(conn)
    finally:
        conn.close()
    return None if st["llm_usd"] <= 0 else float(st["llm_left"])


def run(root: str, cfg: Dict, snap: Dict, bundles: Sequence[Dict], provider: str = "anthropic", yes: bool = False,
        db_path: Optional[str] = None, transport=None, note: Callable[[str], None] = print, scorer_label: Optional[str] = None) -> Dict:
    """Score the planned areas. Refuses without `yes` (the estimate must have been shown and accepted)."""
    _root_on_path(root)
    from core import budget, cost, llm_runner
    if not bundles:
        return {"saved": [], "failed": [], "usd": 0.0}
    if not yes:
        raise ScorerError("chưa xác nhận chi phí — xem ước tính rồi chạy lại với --yes (web: bấm nút xác nhận)")
    db_path = db_path or collect.default_db(root)
    client = make_client(provider, db_path, transport)
    model = getattr(client, "model", "mock")
    if provider == "anthropic":
        est = estimate(bundles, model)
        if not est["priced"]:
            raise ScorerError(f"model {model} chưa có giá trong data/pricing.json — không chấm")
        room = budget_room(db_path)
        if room is not None and est["usd_expected"] > room:
            raise ScorerError(f"ước tính ≈ ${est['usd_expected']:.2f} vượt phần còn lại của trần Claude (${room:.2f}) — nâng trần trong "
                              "Dashboard ⚙ → 💵 Ngân sách thử hoặc chấm ít khu vực hơn")
    pricing = cost.load_pricing()
    ids = [a["id"] for a in cfg["areas"]]
    hd = collect.head(root) or {}
    dirty = bool(snap.get("working"))
    saved, failed, usd = [], [], 0.0
    for b in bundles:
        note(f"Đang chấm {b['area']} ({b['name']})…")
        try:
            with llm_runner.tagged("devsys"):
                raw, tin, tout = llm_runner.ask_json(client, b["prompt"],
                                                     lambda o, f=b["facts"], pv=b.get("prev"): scores.normalize(o, root, ids, f, prev=pv, version=scores.CURRENT_VERSION),
                                                     note=lambda m: note(f"  {m}"))
        except llm_runner.LlmError as e:
            failed.append({"area": b["area"], "error": str(e)})
            note(f"  lỗi: {e}")
            if e.code in ("budget", "auth", "config"):
                note("  dừng: lỗi này sẽ lặp lại ở mọi khu vực")
                break
            continue
        if raw.get("area") != b["area"]:
            raw["area"] = b["area"]
        norm = scores.normalize(raw, root, ids, b["facts"], prev=b.get("prev"), version=scores.CURRENT_VERSION)
        price = None
        if provider == "anthropic":
            pi = budget.token_price(pricing, model, "input", tin)
            po = budget.token_price(pricing, model, "output", tout)
            price = round((pi or 0) + (po or 0), 4)
            usd += price
        rec = {"format": scores.FORMAT, "scorer": scorer_label or ("claude-api" if provider == "anthropic" else "mock"),
               "provider": provider, "model": model, "date": collect.now_iso(), "commit": hd.get("hash"), "dirty": dirty,
               "input_hash": b["input_hash"], "rubric_hash": scores.rubric_hash(root), "fingerprint": b["fingerprint"],
               "facts": b["facts"], "usage": {"input_tokens": tin, "output_tokens": tout, "usd": price}, "truncated": b["notes"],
               **norm, "raw": raw}
        path = scores.save(rec, root)
        saved.append(path)
        note(f"  {b['area']}: {norm['score']}/100 → {os.path.relpath(path, root)}")
    return {"saved": saved, "failed": failed, "usd": round(usd, 4)}


# ---- người chấm ngoài (Claude Code session / subagent) -----------------------------------------------------------------
def export_bundle(root: str, bundle: Dict) -> str:
    d = os.path.join(collect.data_dir(root), "exports")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{bundle['area']}.md")
    text = bundle["prompt"].replace("\n\n<<<cache>>>\n\n", "\n\n---\n\n")
    text += (f"\n\n---\nfingerprint: {bundle['fingerprint']} · input_hash: {bundle['input_hash']}\n"
             "Ghi câu trả lời thành file JSON — CHÉP NGUYÊN hai trường sau vào gốc JSON (S14.10 S3: thiếu hoặc lệch → không nhập được):\n"
             f"\"fingerprint\": \"{bundle['fingerprint']}\", \"input_hash\": \"{bundle['input_hash']}\"\n"
             "rồi: py tools/devsys_score.py --import <file.json> --scorer claude-code-session (chạy ở thư mục repo gốc, không ở worktree)\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def worktree_of(root: str) -> Optional[str]:
    """The main checkout when `root` is a git worktree (its own .git file), else None. A worktree has no devsys/data, data/ or
    dashboard.env of the real machine: scores measured / imported there are capped wrongly (test 6,4/12) and land in the wrong place."""
    try:
        own = os.path.abspath(os.path.join(root, collect.git(root, "rev-parse", "--git-dir").strip()))
        common = os.path.abspath(os.path.join(root, collect.git(root, "rev-parse", "--git-common-dir").strip()))
    except collect.GitError:
        return None
    return os.path.dirname(common) if os.path.normcase(own) != os.path.normcase(common) else None


def check_import_place(root: str) -> None:
    """S4: refuse an import from a git worktree — say where to run it instead (never import quietly into a copy)."""
    main = worktree_of(root)
    if main:
        raise scores.ScoreError(f"đang ở worktree {root}: nhập điểm phải chạy ở repo gốc {main} (có devsys/data, data/, dashboard.env thật) — "
                                f"chép file JSON sang rồi chạy py tools/devsys_score.py --import … ở đó")


def import_score(root: str, cfg: Dict, snap: Dict, health: Dict, raw: Dict, scorer: Optional[str] = None) -> str:
    """Store a score written by an external scorer (same format). The score is recomputed and capped by code like any other."""
    if not isinstance(raw, dict):
        raise scores.ScoreError("file điểm phải là object JSON")
    label = scorer or raw.get("scorer")
    if not label:
        raise scores.ScoreError("thiếu 'scorer' (vd. claude-code-session) — ghi trong file hoặc truyền --scorer")
    if str(label).startswith("mock"):
        raise scores.ScoreError("'scorer' bắt đầu bằng 'mock' dành cho người chấm giả lập")
    ids = [a["id"] for a in cfg["areas"]]
    area = collect.area_by_id(cfg).get(raw.get("area"))
    if area is None:
        raise scores.ScoreError(f"khu vực '{raw.get('area')}' không có trong devsys/areas.json")
    all_scores, _ = scores.load_all(root)
    last = scores.latest_by_area([s for s in all_scores if not str(s.get("scorer", "")).startswith("mock")]).get(area["id"])
    # S14.10 S3: the score must be of THIS export — the data the scorer read (fingerprint: files + TODO + tests + flags + rubric;
    # input_hash: the whole prompt incl. the previous score and the diff). Code / TODO changed since → score again on a new export.
    b = build_bundle(root, cfg, area, snap, health[area["id"]], last)
    for key in ("fingerprint", "input_hash"):
        got = str(raw.get(key) or "").strip()
        if not got:
            raise scores.ScoreError(f"thiếu '{key}' — chép nguyên \"fingerprint\" và \"input_hash\" ở cuối file xuất "
                                    f"(devsys/data/exports/{area['id']}.md) vào JSON; không nhập điểm không rõ chấm trên dữ liệu nào")
        if got != b[key]:
            raise scores.ScoreError(f"'{key}' {got} khác bản hiện tại {b[key]}: code / TODO / test / cờ / điểm trước đã đổi từ lúc xuất — "
                                    f"xuất lại (py tools/devsys_score.py --export {area['id']}) rồi chấm lại")
    facts = b["facts"]
    norm = scores.normalize(raw, root, ids, facts, prev=prev_summary(last), version=scores.CURRENT_VERSION)
    hd = collect.head(root) or {}
    claimed = {k: raw[k] for k in ("commit", "date") if raw.get(k)}
    rec = {"format": scores.FORMAT, "scorer": label, "provider": "external", "model": raw.get("model") or "không ghi",
           "date": collect.now_iso(), "commit": hd.get("hash"), "dirty": bool(snap.get("working")),   # S3: this machine's, never the file's
           "input_hash": b["input_hash"], "rubric_hash": scores.rubric_hash(root), "fingerprint": b["fingerprint"], "facts": facts,
           "usage": raw.get("usage"), **norm, "raw": {k: v for k, v in raw.items() if k not in ("raw",)}}
    if claimed:
        rec["claimed"] = claimed
    return scores.save(rec, root)
