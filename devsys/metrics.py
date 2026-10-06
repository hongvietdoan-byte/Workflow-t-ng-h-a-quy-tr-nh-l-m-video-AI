"""Số đo do CODE tính cho thang chấm bản 2 (devsys/rubric.md) — không AI, không tiền, đọc thẳng từ repo bằng ast / grep có cấu trúc.

Mỗi số đo thành một "khoản trừ tự động" (`auto`) có bằng chứng `file:dòng` kiểm được; người chấm KHÔNG trừ lại những điều này.
Bảng luật (hằng số bên dưới) được liệt kê nguyên văn trong devsys/rubric.md — đổi hằng số = đổi thang (tăng bản rubric).

    area_metrics(root, cfg, area, snap)   số đo thô của một khu vực
    auto_deductions(m)                    số đo → các khoản trừ tự động [{criterion, points, rule, reason, evidence, heuristic}]
    ui_metrics(root)                      kết quả đo giao diện thật đã lưu (devsys/data/ui_metrics.json) hoặc None
    ui_from_text(...)                     đọc đầu ra của tools/ui_v2_acceptance.py + tools/ui_contrast_audit.js thành ui_metrics.json
    facts_extra(...)                      gói số đo + khoản trừ tự động để nhét vào `facts` của file điểm
"""
import ast
import json
import os
import re
from typing import Dict, List, Optional, Sequence

# ---- bảng luật tự động (rubric.md mục "Khoản trừ do code tính") -----------------------------------------------------------
BIG_FILE_LINES = 900            # file code dài hơn → trừ bao_tri
LONG_FUNC_LINES = 150           # hàm dài hơn → trừ bao_tri
COMPLEX_FUNC = 30               # độ phức tạp (số nhánh + 1) hơn → trừ bao_tri
CROWDED_SCREEN_CONTROLS = 60    # một file màn hình có hơn ngần này điều khiển → trừ trai_nghiem
UI_NO_MEASURE_CAP = 6.0         # khu vực giao diện chưa có số đo UI thật: trai_nghiem tối đa
RULES = {   # rule: (criterion, điểm mỗi lần, tổng tối đa của rule)
    "file_dai": ("bao_tri", 1.0, 3.0),
    "ham_dai": ("bao_tri", 0.4, 2.0),
    "ham_phuc_tap": ("bao_tri", 0.4, 2.0),
    "todo_mo": ("chuc_nang", 0.3, 3.0),
    "co_bat_chua_thu": ("bang_chung", 0.5, 4.0),
    "nuot_loi": ("tin_cay", 0.4, 4.0),
    "tien_khong_qua_so": ("tuan_thu", 0.5, 2.0),
    "module_khong_test": ("test", 0.6, 3.0),
    "ham_khong_test": ("test", 0.0, 2.0),          # theo tỉ lệ: xem _untested_func_points
    "man_nhieu_nut": ("trai_nghiem", 0.5, 3.0),
    "tuong_phan": ("trai_nghiem", 0.1, 2.0),
    "chu_nho": ("trai_nghiem", 0.05, 1.0),
    "ui_nhieu_click": ("trai_nghiem", 1.0, 1.0),
    "ui_cham": ("trai_nghiem", 1.0, 1.0),
    "hieu_qua_tut": ("bang_chung", 1.0, 2.0),      # thang 2.1 (Đợt 6b): qua-lần-đầu tụt > 10 điểm % giữa 2 mốc mà cờ + kiến thức không đổi
    "gop_y_lap": ("trai_nghiem", 1.0, 2.0),        # thang 2.1 (Đợt 6b): ≥ 3 góp ý ≤ 2/5 cùng khâu trong 30 ngày chưa xử lý
}
BAO_TRI_AUTO_CAP = 4.0          # thang 2.1 (S10): tổng khoản trừ tự động của bao_tri (file_dai + ham_dai + ham_phuc_tap) tối đa
OPS_DROP_PCT = 10.0             # hieu_qua_tut: tụt hơn ngần này điểm phần trăm
OPS_REPEAT_MIN = 3              # gop_y_lap: từ ngần này góp ý không hài lòng cùng khâu
PAID_CALLS = {"submit", "submit_video_edit", "submit_storyboard_frame", "generate_music", "generate_seed_audio",
              "generate_sfx", "generate_tts"}
PAID_IMPLEMENTATIONS = ("core/adapters/", "core/providers.py", "mcp_servers/", "tools/", "tests/")
GUARD_WORDS = ("budget.", "check_video", "check_audio", "check_image", "check_llm", "record_usage", "SPEND_LOCK", "estimate", "cost.", "ledger",
               "_spend", "usage_events")
CONTROL_CALLS = {"button", "checkbox", "selectbox", "multiselect", "text_input", "text_area", "number_input", "radio", "toggle", "slider",
                 "select_slider", "file_uploader", "expander", "popover", "download_button", "form_submit_button", "data_editor", "tabs",
                 "color_picker", "date_input", "time_input", "pills", "segmented_control", "link_button"}
UI_FILE = os.path.join("devsys", "data", "ui_metrics.json")


# ---- ast ----------------------------------------------------------------------------------------------------------------
def _parse(root: str, rel: str):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            src = f.read()
        return ast.parse(src), src
    except (OSError, SyntaxError, ValueError):
        return None, ""


def _silent_stmt(n: ast.stmt) -> bool:
    if isinstance(n, (ast.Pass, ast.Continue, ast.Break)):
        return True
    if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
        return True
    if isinstance(n, ast.Return):
        v = n.value
        return v is None or isinstance(v, (ast.Constant, ast.Name)) or (isinstance(v, (ast.List, ast.Dict, ast.Tuple, ast.Set))
                                                                         and not getattr(v, "elts", getattr(v, "keys", [])))
    if isinstance(n, ast.Assign):
        return isinstance(n.value, (ast.Constant, ast.Name)) and all(isinstance(t, ast.Name) for t in n.targets)
    return False


def _broad(h: ast.ExceptHandler) -> bool:
    t = h.type
    if t is None:
        return True
    names = [e for e in (t.elts if isinstance(t, ast.Tuple) else [t])]
    return any(isinstance(e, ast.Name) and e.id in ("Exception", "BaseException") for e in names)


_NOQA = re.compile(r"^\s*(?:noqa(?::\s*[A-Z]+\d+(?:\s*,\s*[A-Z]+\d+)*)?|pragma:[^-–—]*|type:\s*ignore\S*)\s*[-–—:]?\s*", re.I)


def _comments(src: str) -> Dict[int, str]:
    """{line: comment text} of a source (tokenize: a '#' inside a string is not a comment)."""
    import io
    import tokenize
    out: Dict[int, str] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                out[tok.start[0]] = tok.string.lstrip("#").strip()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def _explained(h: ast.ExceptHandler, comments: Dict[int, str]) -> bool:
    """S10 (thang 2.1): the handler says WHY the error is let go — a comment of ≥ 8 characters on the `except` line or in its body,
    once the bare 'noqa: BLE001' / 'pragma' tag is taken off."""
    end = getattr(h, "end_lineno", h.lineno) or h.lineno
    return any(len(_NOQA.sub("", comments.get(ln, ""), count=1).strip()) >= 8 for ln in range(h.lineno, end + 1))


def swallowed_excepts(tree: ast.AST, src: Optional[str] = None) -> List[int]:
    """Lines of `except:` / `except Exception:` handlers that do nothing with the error: no raise, no call (so no log / record / print),
    only pass / continue / return-a-constant / assign-a-constant — the 'nuốt lỗi im lặng' of docs/CHUAN_XAY_DUNG.md. With the source,
    a handler whose comment gives the reason (thang 2.1, S10) is a decision, not silence."""
    comments = _comments(src) if src else {}
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ExceptHandler) and _broad(n) and all(_silent_stmt(s) for s in n.body) and not _explained(n, comments):
            out.append(n.lineno)
    return sorted(out)


def _functions(tree: ast.AST):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield n


def _complexity(fn: ast.AST) -> int:
    c = 1
    for n in ast.walk(fn):
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.Assert)):
            c += 1
        elif isinstance(n, ast.BoolOp):
            c += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            c += 1 + len(n.ifs)
    return c


def long_and_complex(tree: ast.AST):
    long_, cx = [], []
    for fn in _functions(tree):
        n = (getattr(fn, "end_lineno", fn.lineno) or fn.lineno) - fn.lineno + 1
        if n > LONG_FUNC_LINES:
            long_.append((fn.lineno, fn.name, n))
        k = _complexity(fn)
        if k > COMPLEX_FUNC:
            cx.append((fn.lineno, fn.name, k))
    return long_, cx


def public_functions(tree: ast.Module) -> List[str]:
    """Top-level functions and methods of top-level classes whose name has no leading underscore."""
    names = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_"):
            names.append(n.name)
        elif isinstance(n, ast.ClassDef) and not n.name.startswith("_"):
            names += [m.name for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not m.name.startswith("_")]
    return names


def paid_call_sites(tree: ast.AST, src: str) -> List[Dict]:
    """Calls to a paid adapter method (submit / generate_*) inside a function whose own source has no budget / cost / estimate word.
    A heuristic: the guard can sit in the caller — so these are marked `heuristic` and weigh little."""
    found = []
    lines = src.splitlines()
    for fn in _functions(tree):
        body = "\n".join(lines[fn.lineno - 1:getattr(fn, "end_lineno", fn.lineno)])
        guarded = any(w in body for w in GUARD_WORDS)
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in PAID_CALLS and not guarded:
                recv = n.func.value
                if isinstance(recv, ast.Name) and recv.id in ("pool", "executor", "ex", "tp"):     # thread pool .submit, not a provider
                    continue
                found.append({"line": n.lineno, "call": n.func.attr, "function": fn.name})
    seen, out = set(), []
    for f in found:                                  # nested functions are visited twice
        if (f["line"], f["call"]) not in seen:
            seen.add((f["line"], f["call"]))
            out.append(f)
    return sorted(out, key=lambda f: f["line"])


def controls_in(tree: ast.AST) -> int:
    return sum(1 for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in CONTROL_CALLS)


PEOPLE_WORK = re.compile(r"👤|người dùng\s+(?:tự\s+)?(?:làm|chạy|xem|nghe|chấm|nạp|thử|bấm|kiểm|mở|chọn|quay|ghi)", re.I)
CONVENTION = re.compile(r"quy ước|nguyên tắc", re.I)


def todo_work_kind(item: Dict) -> str:
    """S14.10 S11: 'code' (Claude Code can do it) · 'nguoi_dung' (a person must do it) · 'quy_uoc' (a standing rule of how to work)."""
    text = f"{item.get('section', '')} {item.get('text', '')}"
    if CONVENTION.search(text):
        return "quy_uoc"
    if PEOPLE_WORK.search(item.get("text", "")):
        return "nguoi_dung"
    return "code"


# ---- số đo một khu vực --------------------------------------------------------------------------------------------------
def area_metrics(root: str, cfg: Dict, area: Dict, snap: Dict) -> Dict:
    from . import collect
    files = snap["files"]
    code = [f for f in collect.area_files(area, files, ("code",)) if f.endswith(".py")]
    mods = [f for f in code if not f.endswith("__init__.py")]
    tmap = snap["test_map"]
    t = snap["tests_by_area"].get(area["id"], {})
    covered = {m for tf in t.get("test_files", []) for m in tmap.get(tf, {}).get("modules", [])}
    texts: Dict[str, str] = {}

    def test_text(tf: str) -> str:
        if tf not in texts:
            try:
                with open(os.path.join(root, tf), encoding="utf-8", errors="replace") as fh:
                    texts[tf] = fh.read()
            except OSError:
                texts[tf] = ""
        return texts[tf]

    m: Dict = {"code_files": len(mods), "swallowed": [], "long_funcs": [], "complex_funcs": [], "big_files": [], "paid_unguarded": [],
               "funcs_public": 0, "funcs_untested": 0, "untested_names": [], "controls": {}, "modules_untested": []}
    for rel in mods:
        tree, src = _parse(root, rel)
        if tree is None:
            continue
        for ln in swallowed_excepts(tree, src):
            m["swallowed"].append(f"{rel}:{ln}")
        lg, cx = long_and_complex(tree)
        m["long_funcs"] += [f"{rel}:{ln} {name} ({n} dòng)" for ln, name, n in lg]
        m["complex_funcs"] += [f"{rel}:{ln} {name} ({k})" for ln, name, k in cx]
        n_lines = snap["line_counts"].get(rel) or collect.line_count(os.path.join(root, rel))
        if n_lines > BIG_FILE_LINES:
            m["big_files"].append(f"{rel}:{n_lines}")
        if not rel.startswith(PAID_IMPLEMENTATIONS):
            for s in paid_call_sites(tree, src):
                m["paid_unguarded"].append(f"{rel}:{s['line']} {s['call']} trong {s['function']}()")
        if rel.startswith("dashboard/"):
            c = controls_in(tree)
            if c:
                m["controls"][rel] = c
        elif rel in covered:                         # function-level only for modules a test imports, and not for screens (AppTest)
            importing = [tf for tf in t.get("test_files", []) if rel in tmap.get(tf, {}).get("modules", [])]
            blob = "\n".join(test_text(tf) for tf in importing)
            for name in public_functions(tree):
                m["funcs_public"] += 1
                if not re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", blob):
                    m["funcs_untested"] += 1
                    m["untested_names"].append(f"{rel}:{name}")
        if rel not in covered:
            m["modules_untested"].append(rel)
    m["funcs_untested_ratio"] = round(m["funcs_untested"] / m["funcs_public"], 3) if m["funcs_public"] else 0.0
    # S14.10 S11: a TODO line tied to N areas costs each 1/N (one job, counted once for the system); only CODE work counts — a person's
    # job (👤, "người dùng nghe / chấm / chạy…") and a working convention ("quy ước") are listed apart, never as missing code.
    shared: Dict[int, int] = {}
    for aid, items in snap["todo_by_area"].items():
        if aid != "_chung":
            for i in items:
                shared[i["line"]] = shared.get(i["line"], 0) + 1
    open_items = [i for i in snap["todo_by_area"].get(area["id"], []) if i["kind"] == "open" and not i["waiting_user"]]
    kinds = {i["line"]: todo_work_kind(i) for i in open_items}
    m["todo_open"] = [i["line"] for i in open_items if kinds[i["line"]] == "code"]
    m["todo_people"] = [i["line"] for i in open_items if kinds[i["line"]] == "nguoi_dung"]
    m["todo_rules"] = [i["line"] for i in open_items if kinds[i["line"]] == "quy_uoc"]
    m["todo_share"] = round(sum(1.0 / max(1, shared.get(n, 1)) for n in m["todo_open"]), 3)
    m["todo_shared_lines"] = [n for n in m["todo_open"] if shared.get(n, 1) > 1]
    m["flags_on_unverified"] = [f["name"] for f in snap["flags"] if area["id"] in f["areas"] and f["on"] and not f["verified"]]
    m["has_ui"] = any(f.startswith("dashboard/") for f in mods)
    m["ui_measured"] = bool(area.get("ui_metrics"))
    m.update(ops_measures(snap.get("ops") or {}, area))
    return m


def ops_measures(ops: Dict, area: Dict) -> Dict:
    """Thang 2.1 (Đợt 6b): from the read-only ops summary — `ops_drop`: the area's first-pass figure fell > OPS_DROP_PCT points between
    the two latest system snapshots while the flags ON and the knowledge fingerprint stayed the same (nothing we changed explains it);
    `ops_repeat`: {stage: feedback ids} with ≥ OPS_REPEAT_MIN unhandled complaints (≤ 2/5) in 30 days."""
    from . import collect
    mine = collect.ops_for_area(ops, area)
    out: Dict = {"ops_drop": [], "ops_repeat": {}}
    rows = ops.get("trend") or []
    if len(rows) >= 2:
        a, b = rows[-2], rows[-1]
        if sorted(a.get("flags_on") or []) == sorted(b.get("flags_on") or []) and (a.get("knowledge_fp") or "") == (b.get("knowledge_fp") or ""):
            for fig in mine["figures"]:
                x, y = a.get(fig), b.get(fig)
                if x is not None and y is not None and (float(x) - float(y)) * 100 > OPS_DROP_PCT:
                    out["ops_drop"].append({"figure": fig, "from_id": a["id"], "to_id": b["id"], "before": x, "after": y})
    for st, v in mine["feedback"].items():
        if len(v.get("low_open_30d") or []) >= OPS_REPEAT_MIN:
            out["ops_repeat"][st] = list(v["low_open_30d"])
    return out


def _untested_func_points(ratio: float, n_public: int) -> float:
    if n_public < 5:
        return 0.0
    return 3.0 if ratio > 0.9 else 2.0 if ratio > 0.75 else 1.0 if ratio > 0.5 else 0.0


def _auto(out: List[Dict], rule: str, items: Sequence[str], reason: str, heuristic: bool = False, per: Optional[float] = None,
          points: Optional[float] = None) -> None:
    crit, each, cap = RULES[rule]
    if not items and points is None:
        return
    pts = points if points is not None else min(cap, round(len(items) * (per if per is not None else each), 1))
    if pts <= 0:
        return
    out.append({"criterion": crit, "points": round(pts, 1), "rule": rule, "reason": reason, "heuristic": heuristic,
                "evidence": [str(i) for i in items[:6]], "count": len(items)})


def _ev(path_lines: Sequence[str]) -> List[str]:
    """`file:line detail` → `file:line` (the part code can verify)."""
    return [p.split(" ")[0] for p in path_lines]


def auto_deductions(m: Dict, ui: Optional[Dict] = None) -> List[Dict]:
    out: List[Dict] = []
    # S10 (thang 2.1): a file costs bao_tri ONCE — a long file is not charged again for its long / complex functions, a file with long
    # functions not again for complex ones; each rule counts files (first offending line as evidence); the three share BAO_TRI_AUTO_CAP.
    seen: set = set()

    def per_file(items: Sequence[str]) -> List[str]:
        firsts: Dict[str, str] = {}
        for it in _ev(items):
            f = it.split(":")[0]
            if f not in seen:
                firsts.setdefault(f, it)
        seen.update(firsts)
        return list(firsts.values())

    big, long_, cx = per_file(m["big_files"]), per_file(m["long_funcs"]), per_file(m["complex_funcs"])
    before = len(out)
    _auto(out, "file_dai", big, f"{len(big)} file code dài hơn {BIG_FILE_LINES} dòng (khó đọc, khó sửa)")
    _auto(out, "ham_dai", long_, f"{len(long_)} file (không tính file đã bị trừ vì dài) có hàm dài hơn {LONG_FUNC_LINES} dòng "
          f"({len(m['long_funcs'])} hàm)")
    _auto(out, "ham_phuc_tap", cx, f"{len(cx)} file (chưa bị trừ ở trên) có hàm độ phức tạp > {COMPLEX_FUNC} ({len(m['complex_funcs'])} hàm)")
    room = BAO_TRI_AUTO_CAP
    for a in out[before:]:
        a["points"] = round(min(a["points"], room), 1)
        room = max(0.0, room - a["points"])
    out[before:] = [a for a in out[before:] if a["points"] > 0]
    if m["todo_open"]:
        crit, each, cap = RULES["todo_mo"]
        n_shared = len(m.get("todo_shared_lines") or [])
        _auto(out, "todo_mo", [f"TODO.md:{n}" for n in m["todo_open"]],
              f"{len(m['todo_open'])} dòng TODO.md còn mở là việc code của khu vực (không tính dòng chờ / việc người dùng / quy ước)"
              + (f"; {n_shared} dòng chung nhiều khu vực → chia điểm theo số khu vực" if n_shared else ""),
              points=min(cap, round(each * float(m.get("todo_share", len(m["todo_open"]))), 1)))
    _auto(out, "co_bat_chua_thu", [f"flag:{n}" for n in m["flags_on_unverified"]],
          f"{len(m['flags_on_unverified'])} cờ đang BẬT mà verified=False (chưa thử thật)")
    _auto(out, "nuot_loi", m["swallowed"], f"{len(m['swallowed'])} chỗ `except Exception` không báo / không ghi / không ném lại lỗi")
    _auto(out, "tien_khong_qua_so", _ev(m["paid_unguarded"]),
          f"{len(m['paid_unguarded'])} lời gọi nhà cung cấp tốn tiền trong hàm không thấy kiểm trần / sổ chi / ước tính (dấu hiệu — người chấm xác minh)", heuristic=True)
    _auto(out, "module_khong_test", m["modules_untested"], f"{len(m['modules_untested'])} module không có test nào import tới")
    p = _untested_func_points(m["funcs_untested_ratio"], m["funcs_public"])
    if p:
        _auto(out, "ham_khong_test", sorted({x.split(":")[0] + ":1" for x in m["untested_names"]}),
              f"{m['funcs_untested']}/{m['funcs_public']} hàm công khai không được test nhắc tới tên (dấu hiệu)", heuristic=True, points=p)
    crowded = [f"{f}:1" for f, n in sorted(m["controls"].items()) if n > CROWDED_SCREEN_CONTROLS]
    _auto(out, "man_nhieu_nut", crowded, f"{len(crowded)} file màn hình có hơn {CROWDED_SCREEN_CONTROLS} điều khiển (nút / ô / khối gập)")
    for d in m.get("ops_drop") or []:                 # thang 2.1 (Đợt 6b): evidence = the two rows of the real database (db:)
        _auto(out, "hieu_qua_tut", [f"db:effectiveness_snapshots:{d['from_id']}", f"db:effectiveness_snapshots:{d['to_id']}"],
              f"{d['figure']} tụt {100 * (float(d['before']) - float(d['after'])):.0f} điểm % ({100 * float(d['before']):.0f} → "
              f"{100 * float(d['after']):.0f} %) giữa hai mốc mà cờ bật + kiến thức không đổi", points=RULES["hieu_qua_tut"][1])
    if m.get("ops_repeat"):
        ids = [i for st in sorted(m["ops_repeat"]) for i in m["ops_repeat"][st]]
        _auto(out, "gop_y_lap", [f"db:user_feedback:{i}" for i in ids],
              "; ".join(f"{len(v)} góp ý không hài lòng (≤ 2/5) chưa xử lý trong 30 ngày ở khâu {st}" for st, v in sorted(m["ops_repeat"].items())),
              points=min(RULES["gop_y_lap"][2], RULES["gop_y_lap"][1] * len(m["ops_repeat"])))
    if m.get("ui_measured") and ui:
        if ui.get("contrast_fail"):
            _auto(out, "tuong_phan", [UI_FILE.replace("\\", "/")] * int(ui["contrast_fail"]), f"{ui['contrast_fail']} phần tử chữ có tương phản < 4,5:1 (đo thật)")
        if ui.get("small_text"):
            _auto(out, "chu_nho", [UI_FILE.replace("\\", "/")] * int(ui["small_text"]), f"{ui['small_text']} phần tử chữ nhỏ hơn 12,5 px (đo thật)")
        if ui.get("clicks_v2") is not None and ui.get("clicks_old") is not None and ui["clicks_v2"] > ui["clicks_old"]:
            _auto(out, "ui_nhieu_click", [UI_FILE.replace("\\", "/")], f"Số click 'Dự án mới → video đầu' tăng: {ui['clicks_old']} → {ui['clicks_v2']}", points=1.0)
        if ui.get("perf_worst_pct") is not None and ui["perf_worst_pct"] > 20:
            _auto(out, "ui_cham", [UI_FILE.replace("\\", "/")], f"Rerun chậm hơn bản cũ {ui['perf_worst_pct']:.0f} % (ngưỡng 20 %)", points=1.0)
    return out


# ---- đo giao diện thật --------------------------------------------------------------------------------------------------
def ui_metrics(root: str) -> Optional[Dict]:
    """The saved real UI measurement (tools/devsys_ui_metrics.py), or None."""
    try:
        with open(os.path.join(root, UI_FILE), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


_CONTRAST = re.compile(r"chữ\s*<\s*4[.,]5\s*:\s*(\d+)\s*\|\s*chữ\s*<\s*12[.,]5\s*px\s*:\s*(\d+)", re.I)
_CLICK = re.compile(r"CLICK[^:]*:\s*cũ\s*(\d+)\s*·\s*v2\s*(\d+)")
_KEYS_LOST = re.compile(r"mất(?: trong v2)?\s*(\[[^\]]*\])")


def _renamed_check():
    """S14.8 U8: the RENAMED table of tools/ui_v2_acceptance.py (keys renamed on purpose, with a reason) as a predicate. The file is
    loaded by path (tools/ is not a package); if it cannot be read, every key counts as lost (the stricter answer)."""
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "ui_v2_acceptance.py")
    try:
        spec = importlib.util.spec_from_file_location("_ui_v2_acceptance_renamed", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return lambda key: not mod.unexplained([key])
    except (OSError, ImportError, AttributeError, SyntaxError):
        return lambda key: False


def ui_from_text(acceptance: str = "", contrast: str = "", source: str = "") -> Dict:
    """Parse the printed output of `py tools/ui_v2_acceptance.py all` and of tools/ui_contrast_audit.js (one line per zone:
    '<vùng> | chữ<4.5: N | chữ<12.5px: M') into the numbers the scorer uses. Missing parts stay None."""
    out: Dict = {"clicks_old": None, "clicks_v2": None, "perf_worst_pct": None, "keys_lost": None, "contrast_fail": None,
                 "small_text": None, "zones": 0, "source": source}
    m = _CLICK.search(acceptance)
    if m:
        out["clicks_old"], out["clicks_v2"] = int(m.group(1)), int(m.group(2))
    perf = [float(x) for x in re.findall(r"PERF\s+\S+[^\n]*?([+-]\d+(?:\.\d+)?)\s*%\s*\|", acceptance)]   # the first '+x.x % |' of each line = wall time
    if perf:
        out["perf_worst_pct"] = max(perf)
    lost = 0
    explained = _renamed_check()
    for k in _KEYS_LOST.finditer(acceptance):
        try:
            lost += sum(1 for key in json.loads(k.group(1).replace("'", '"')) if not explained(key))   # S14.8 U8: renamed on purpose ≠ lost
        except ValueError:
            pass
    if acceptance:
        out["keys_lost"] = lost
    rows = _CONTRAST.findall(contrast)
    if rows:
        out["contrast_fail"] = sum(int(a) for a, _ in rows)
        out["small_text"] = sum(int(b) for _, b in rows)
        out["zones"] = len(rows)
    return out


def facts_extra(root: str, cfg: Dict, area: Dict, snap: Dict) -> Dict:
    """What goes into `facts` of a v2 score: the raw measures, the automatic deductions and the UI measurement state."""
    m = area_metrics(root, cfg, area, snap)
    ui = ui_metrics(root) if area.get("ui_metrics") else None
    return {"metrics": m, "auto": auto_deductions(m, ui), "ui_measured": bool(area.get("ui_metrics")), "ui_present": ui is not None,
            "ui": ui or {}, "doc_only": not area.get("code") and bool(area.get("docs"))}   # S6: an area of documents only
