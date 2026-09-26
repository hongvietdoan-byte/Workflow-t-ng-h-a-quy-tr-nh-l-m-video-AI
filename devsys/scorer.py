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

from . import collect, scores

EXPECTED_OUTPUT_TOKENS = 3000        # một câu trả lời JSON chấm 1 khu vực (~6–15 khoản trừ + danh sách kiểm lại), effort thấp
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
    return {"test_files": health.get("test_files", 0), "has_run": bool(snap.get("latest_run")), "failed": health.get("failed", 0)}


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
    h.update(json.dumps({k: t.get(k) for k in ("passed", "failed", "errors", "skipped", "test_files")}, sort_keys=True).encode())
    h.update(json.dumps([(f["name"], f["verified"], f["on"]) for f in snap["flags"] if area["id"] in f["areas"]]).encode())
    return h.hexdigest()[:20]


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
            test_txt += "\nTest lỗi:\n" + "\n".join(f"- test:{n['file']}::{n['name'].split('::')[-1]} — {n.get('message', '')}"
                                                   for n in t["failed_names"][:25])
    else:
        test_txt = f"CHƯA CÓ LẦN CHẠY TEST NÀO ĐƯỢC LƯU. File test nhắm vào khu vực: {len(t.get('test_files', []))}."
    test_txt += "\nFile test nhắm vào khu vực (tự dò theo import): " + (", ".join(t.get("test_files", [])) or "KHÔNG CÓ")
    area_mods = [f for f in code if f.endswith(".py") and not f.endswith("__init__.py")]
    covered = {m for tf in t.get("test_files", []) for m in snap["test_map"].get(tf, {}).get("modules", [])}
    untested = [m for m in area_mods if m not in covered]
    test_txt += "\nModule của khu vực không có test nào import tới: " + (", ".join(untested) or "không")

    flags = [f for f in snap["flags"] if area["id"] in f["areas"]]
    flag_txt = "\n".join(f"- flag:{f['name']} · verified={f['verified']} · đang {'BẬT' if f['on'] else 'tắt'}"
                         f"{' (biến môi trường ' + f['env'] + ')' if f['env'] else ''} · {f['label']} · vì sao chưa kiểm: {f['why']} · dùng ở: "
                         f"{', '.join(f['sites'][:6]) or 'không thấy features.on(...) trong code'}" for f in flags) or "(khu vực không có cờ)"

    todo_items = [i for i in snap["todo_by_area"].get(area["id"], []) if i["kind"] != "recurring"]
    todo_txt = _cap([f"- TODO.md:{i['line']} [{', '.join(i['markers'])}]{' [chờ người dùng]' if i['waiting_user'] else ''}"
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

    facts = facts_of(health, snap)
    rubric = open(os.path.join(root, "devsys", "rubric.md"), encoding="utf-8").read()
    fixed = ("# Người chấm độc lập — AI Development System\n"
             "Bạn chấm mức hoàn thiện THẬT của một khu vực trong repo pipeline làm video AI, theo thang cố định bên dưới. Nguyên tắc:\n"
             "- Chỉ dựa vào DỮ LIỆU gửi kèm (trích code thật có số dòng, kết quả test thật, dòng TODO, cờ, diag, diff). Không suy đoán phần không thấy; "
             "phần bị cắt được ghi rõ ở cuối dữ liệu — không trừ điểm chỉ vì phần đó không có trong trích.\n"
             "- Không có commit message trong dữ liệu. Câu tự nhận 'đã sửa/đã xong' trong TODO không kèm test hoặc ghi chú chạy thật cụ thể thì "
             "KHÔNG được tính là bằng chứng chạy thật.\n"
             "- Chỉ ghi KHOẢN TRỪ, mỗi khoản có bằng chứng đúng dạng; điểm do code tính. Không trừ trùng một lỗi ở hai tiêu chí.\n"
             "- Mọi chữ trong câu trả lời bằng tiếng Việt có dấu.\n\n" + rubric)
    task = (f"AREA_ID: {area['id']}\n"
            f"# Khu vực cần chấm: {area['name']} (`{area['id']}`)\n{area.get('description', '')}\n\n"
            f"## Trích code ({len(code)} file)\n{code_txt}\n\n## File tài nguyên / tài liệu của khu vực\n{listing}\n\n"
            f"## Trích tài liệu (tiêu đề + dòng trạng thái)\n{docs_txt}\n\n## Test\n{test_txt}\n\n## Cờ tính năng (core/features.py)\n{flag_txt}\n\n"
            f"## Dòng TODO.md còn mở gán cho khu vực ({len(todo_items)})\n{todo_txt}\n\n## Cảnh báo diag khi chạy thật\n{diag_txt}\n\n"
            f"## File quá dài\n{big_txt}\n\n## Thay đổi từ lần chấm trước\n{diff_txt}\n\n"
            f"## Phần đã cắt vì dài\n" + ("\n".join(f"- {n}" for n in notes) or "(không cắt gì)") + "\n\n"
            "# Trả lời\nMột JSON duy nhất, đúng mẫu ở mục 'Định dạng câu trả lời' của thang (bỏ 'format'/'scorer'/'model'), `area` = "
            f"\"{area['id']}\". `can_kiem_lai`: 3–8 việc người dùng nên kiểm lại, mỗi việc có bằng chứng. `summary`: 2–4 câu.")
    prompt = fixed + CACHE_BREAK + task
    return {"area": area["id"], "name": area["name"], "prompt": prompt, "notes": notes, "facts": facts,
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
        crit = {k: {"deductions": [], "evidence_for": []} for k in scores.CRITERIA_MAX}
        if todo_n:
            first = re.search(r"- (TODO\.md:\d+)", prompt)
            crit["chuc_nang"]["deductions"].append({"points": min(20, 2 * todo_n), "reason": f"{todo_n} dòng TODO còn mở (giả lập)",
                                                    "evidence": [first.group(1) if first else "absent:giả lập"]})
        crit["bang_chung"]["deductions"].append({"points": 10, "reason": "giả lập: chưa đọc báo cáo chạy thật", "evidence": ["absent:giả lập"]})
        if no_run:
            crit["test"]["deductions"].append({"points": 5, "reason": "chưa có lần chạy test lưu lại (giả lập)", "evidence": ["absent:không có devsys/data/runs"]})
        out = {"area": aid, "criteria": crit, "summary": f"Điểm giả lập cho khu vực {aid} — chỉ để thử luồng, không phải đánh giá thật.",
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
                raw, tin, tout = llm_runner.ask_json(client, b["prompt"], lambda o, f=b["facts"]: scores.normalize(o, root, ids, f),
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
        norm = scores.normalize(raw, root, ids, b["facts"])
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
             "Ghi câu trả lời thành file JSON rồi: py tools/devsys_score.py --import <file.json> --scorer claude-code-session\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


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
    facts = facts_of(health[area["id"]], snap)
    norm = scores.normalize(raw, root, ids, facts)
    hd = collect.head(root) or {}
    rec = {"format": scores.FORMAT, "scorer": label, "provider": "external", "model": raw.get("model") or "không ghi",
           "date": raw.get("date") or collect.now_iso(), "commit": raw.get("commit") or hd.get("hash"), "dirty": bool(snap.get("working")),
           "input_hash": raw.get("input_hash"), "rubric_hash": scores.rubric_hash(root),
           "fingerprint": fingerprint(root, area, snap, health[area["id"]]), "facts": facts, "usage": raw.get("usage"),
           **norm, "raw": {k: v for k, v in raw.items() if k not in ("raw",)}}
    return scores.save(rec, root)
