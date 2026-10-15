"""C3 (người dùng duyệt 15/10, docs/handoff/RA_QUYET_DINH_LOI_LAP_2026-10-15.md): sổ quyết định người dùng MỘT nguồn — data/decisions.json
(trong git). Quyết định kiểm được bằng cờ / code ghi ở sổ + `enforced_by`; memory / TODO chỉ trỏ id. Quyết định sau thay quyết định
trước bằng `replaces` (mục cũ 'replaced'), không sửa chữ mục cũ.

  py -m core.decisions list    — in sổ
  py -m core.decisions check   — đối chiếu: cờ ở mặc định code + trên máy này (tệp 🧪 / dashboard.env đang nạp), chạy các check code
                                  (hàm check_* trong tests/test_decisions.py). Mã thoát 1 khi mặc định code / check code lệch quyết định
                                  đang hiệu lực (máy lệch chỉ in cảnh báo: cài đặt máy là lựa chọn của người dùng trên máy đó).

Khác devsys/decisions.json (bản đồ 'AI quyết ở khâu nào'). 0 USD, không gọi mạng."""
import json
import os
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "decisions.json")
FIELDS = ("id", "date", "by", "text", "keeps", "changes", "replaces", "enforced_by", "status")
STATUSES = ("active", "replaced")
CHECK_MODULE = os.path.join(ROOT, "tests", "test_decisions.py")


def load(path: Optional[str] = None) -> Dict:
    with open(path or PATH, encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict) or not isinstance(doc.get("items"), list):
        raise ValueError(f"{path or PATH}: cần {{'items': [...]}}")
    return doc


def problems(doc: Dict, checks: Optional[set] = None) -> List[str]:
    """Lỗi cấu trúc của sổ: thiếu trường, id trùng, `replaces` trỏ id không có, mục 'replaced' không có mục mới thay, enforced_by sai
    (cờ không có trong core/features.FEATURES; check không có trong `checks` khi được truyền)."""
    from . import features
    out = []
    items = doc.get("items") or []
    ids = [i.get("id") for i in items]
    seen = set()
    for i in ids:
        if i in seen:
            out.append(f"id trùng: {i!r}")
        seen.add(i)
    replaced_by = {i.get("replaces"): i.get("id") for i in items if i.get("replaces")}
    for it in items:
        iid = it.get("id")
        miss = [f for f in FIELDS if f not in it]
        if miss:
            out.append(f"{iid!r}: thiếu trường {', '.join(miss)}")
        if it.get("status") not in STATUSES:
            out.append(f"{iid!r}: status {it.get('status')!r} (cần active / replaced)")
        rep = it.get("replaces")
        if rep and rep not in seen:
            out.append(f"{iid!r}: replaces {rep!r} không có trong sổ")
        if rep == iid:
            out.append(f"{iid!r}: tự thay chính nó")
        if it.get("status") == "replaced" and iid not in replaced_by:
            out.append(f"{iid!r}: status replaced nhưng không mục nào replaces nó")
        if rep and rep in seen and next((x for x in items if x.get("id") == rep), {}).get("status") != "replaced":
            out.append(f"{iid!r}: thay {rep!r} mà {rep!r} chưa đánh dấu replaced")
        for e in it.get("enforced_by") or []:
            kind = e.get("kind") if isinstance(e, dict) else None
            if kind == "flag":
                if e.get("name") not in features.FEATURES:
                    out.append(f"{iid!r}: cờ {e.get('name')!r} không có trong core/features.FEATURES")
                if not isinstance(e.get("on"), bool):
                    out.append(f"{iid!r}: cờ {e.get('name')!r} thiếu 'on' true/false")
            elif kind == "code":
                if not e.get("check"):
                    out.append(f"{iid!r}: check code thiếu tên hàm")
                elif checks is not None and e["check"] not in checks:
                    out.append(f"{iid!r}: check {e['check']!r} không có trong tests/test_decisions.py")
            else:
                out.append(f"{iid!r}: enforced_by kind {kind!r} (cần flag / code)")
    return out


def flag_rows(doc: Dict) -> List[Dict]:
    """Mỗi cờ của mục active: mặc định code (features.default_state) + trạng thái trên máy này (features.state)."""
    from . import features
    out = []
    for it in doc["items"]:
        if it["status"] != "active":
            continue
        for e in it["enforced_by"]:
            if e.get("kind") != "flag" or e.get("name") not in features.FEATURES:
                continue
            default, here = features.default_state(e["name"]), features.state(e["name"])
            out.append({"id": it["id"], "name": e["name"], "want_on": e["on"], "default": default, "machine": here,
                        "machine_source": features.source(e["name"]),
                        "ok_default": (default == "on") is e["on"], "ok_machine": (here == "on") is e["on"]})
    return out


def _check_module():
    import importlib.util
    import sys
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    spec = importlib.util.spec_from_file_location("_decision_checks", CHECK_MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def code_rows(doc: Dict) -> List[Dict]:
    """Chạy từng check code của mục active. pending + đỏ = đúng như đang chờ; pending + XANH = nhánh đã gộp → bỏ 'pending' khỏi sổ."""
    try:
        mod = _check_module()
    except Exception as e:  # noqa: BLE001 - say it, never pretend the checks passed
        return [{"id": "-", "check": "-", "ok": False, "pending": None, "error": f"không nạp được {CHECK_MODULE}: {type(e).__name__}: {e}"}]
    out = []
    for it in doc["items"]:
        if it["status"] != "active":
            continue
        for e in it["enforced_by"]:
            if e.get("kind") != "code":
                continue
            fn = getattr(mod, e["check"], None)
            err = None
            if fn is None:
                err = "không có hàm check"
            else:
                try:
                    fn()
                except BaseException as ex:  # noqa: BLE001 - AssertionError / pytest.raises Failed / anything: a failed check
                    if isinstance(ex, (KeyboardInterrupt, SystemExit)):
                        raise
                    err = f"{type(ex).__name__}: {str(ex)[:200]}"
            out.append({"id": it["id"], "check": e["check"], "ok": err is None, "pending": e.get("pending"), "error": err})
    return out


def _print(s: str = "") -> None:
    print(s)


def cmd_list(doc: Dict) -> int:
    for it in doc["items"]:
        mark = "●" if it["status"] == "active" else "○ (đã thay)"
        _print(f"{mark} {it['id']} — {it['date']} — {it['by']}" + (f" — thay {it['replaces']}" if it.get("replaces") else ""))
        _print(f"    {it['text']}")
        if it.get("keeps"):
            _print(f"    giữ: {it['keeps']}")
        if it.get("changes"):
            _print(f"    đổi: {it['changes']}")
        for e in it["enforced_by"]:
            if e["kind"] == "flag":
                _print(f"    ⚑ cờ {e['name']} {'BẬT' if e['on'] else 'không bật'}")
            else:
                _print(f"    ✓ code {e['check']}" + (f" (chờ: {e['pending']})" if e.get("pending") else ""))
    return 0


def cmd_check(doc: Dict) -> int:
    bad = 0
    probs = problems(doc)
    for p in probs:
        _print(f"🔴 sổ: {p}")
    bad += len(probs)
    for r in flag_rows(doc):
        want = "BẬT" if r["want_on"] else "không bật"
        if not r["ok_default"]:
            bad += 1
            _print(f"🔴 {r['id']}: cờ {r['name']} mặc định code '{r['default']}' — quyết định {want}")
        if not r["ok_machine"]:
            _print(f"🟡 {r['id']}: cờ {r['name']} trên máy này '{r['machine']}' (nguồn {r['machine_source']}) — quyết định {want}")
        if r["ok_default"] and r["ok_machine"]:
            _print(f"✅ {r['id']}: cờ {r['name']} {r['machine']}")
    for r in code_rows(doc):
        if r["ok"] and r["pending"]:
            bad += 1
            _print(f"🔴 {r['id']}: {r['check']} đã XANH mà sổ còn ghi chờ ({r['pending']}) — bỏ 'pending' khỏi data/decisions.json")
        elif r["ok"]:
            _print(f"✅ {r['id']}: {r['check']}")
        elif r["pending"]:
            _print(f"⏳ {r['id']}: {r['check']} chưa đạt — chờ: {r['pending']} ({r['error']})")
        else:
            bad += 1
            _print(f"🔴 {r['id']}: {r['check']} — {r['error']}")
    _print(f"\n{'Khớp' if not bad else f'{bad} chỗ lệch'} — sổ {PATH}")
    return 1 if bad else 0


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog="py -m core.decisions", description="Sổ quyết định người dùng (data/decisions.json)")
    ap.add_argument("cmd", choices=("list", "check"))
    a = ap.parse_args(argv)
    doc = load()
    return cmd_list(doc) if a.cmd == "list" else cmd_check(doc)


if __name__ == "__main__":
    raise SystemExit(main())
