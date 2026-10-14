"""Nhật ký THAO TÁC trên Dashboard (14/10, tập 2 #27): ai bấm nút nào, nguồn người / Claude, kết quả, thời gian xử lý.

Người dùng thôi tự bấm Dashboard — Claude điều khiển bằng trình duyệt, đăng nhập CHUNG tài khoản. Bảng `ui_actions` (core/db.py)
ghi từng thao tác chính để đo khâu khó dùng (bấm hụt, bấm 2 lần, đổi ý, thời gian mỗi bước) và tách nguồn người / Claude
(`?op=claude` khi mở Dashboard). Không đổi quyền gì theo nguồn.

Luật: `record` KHÔNG BAO GIỜ làm hỏng thao tác — một INSERT, không gọi mạng; lỗi ghi → nuốt + ghi diag MỘT lần mỗi tiến trình.
`detail` được che khóa/mật khẩu (diag.redact) và cắt ≤ 300 ký tự.
"""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional

SOURCES = ("nguoi", "claude")
RESULTS = ("ok", "error", "noop")
DETAIL_MAX = 300
FLIP_WINDOW_S = 300          # duyệt → loại (hoặc ngược lại) cùng job trong ≤ 5 phút = đổi ý
CANCEL_WINDOW_S = 600        # gen → hủy job cùng dự án trong ≤ 10 phút = đổi ý
DOUBLE_WINDOW_S = 10         # bấm cùng nút 2 lần trong ≤ 10 s mà lần 1 'noop' = bấm hụt / bấm đôi

# cặp duyệt/loại theo loại nội dung: hành động → (nhóm, quyết định)
_DECISIONS = {"duyet_anh": ("anh", "duyet"), "loai_anh": ("anh", "loai"),
              "duyet_video": ("video", "duyet"), "loai_video": ("video", "loai")}
_GEN = ("gen_anh", "gen_video")
_CANCEL = "huy_job"

_warned: List[bool] = []     # diag đã ghi một lần trong tiến trình này


def norm_source(value) -> str:
    """'claude' (không phân biệt hoa/thường, bỏ khoảng trắng) → 'claude'; mọi thứ khác → 'nguoi'."""
    return "claude" if str(value or "").strip().lower() == "claude" else "nguoi"


def source_from(query_value, current: Optional[str]) -> str:
    """Nguồn của phiên trình duyệt: `?op=` có mặt thì quyết định; không có thì GIỮ nguồn cũ của phiên (dính sau đăng nhập /
    đổi trang); phiên mới không có gì → 'nguoi'."""
    if query_value not in (None, "", []):
        if isinstance(query_value, (list, tuple)):
            query_value = query_value[-1]
        return norm_source(query_value)
    return current if current in SOURCES else "nguoi"


def _clean_detail(detail) -> str:
    text = "" if detail is None else str(detail)
    try:
        from .diag import redact
        text = redact(text)
    except Exception:  # noqa: BLE001 - che khóa hỏng thì vẫn cắt ngắn, không làm hỏng thao tác
        pass
    return text[:DETAIL_MAX]


def _int_or_none(v):
    try:
        return None if v is None else int(v)
    except (TypeError, ValueError):
        return None


def record(conn, action: str, *, email: Optional[str] = None, source: str = "nguoi", page: Optional[str] = None,
           project_id=None, scene_id=None, job_id=None, result: str = "ok", detail=None, ms=None) -> bool:
    """Ghi một thao tác. Trả True nếu ghi được; mọi lỗi (bảng thiếu, CSDL khóa/hỏng, conn None…) → False, không ném lỗi."""
    try:
        res = result if result in RESULTS else "ok"
        conn.execute(
            "INSERT INTO ui_actions (at, email, source, page, action, project_id, scene_id, job_id, result, detail, ms)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), (email or None), norm_source(source), (str(page)[:60] if page else None), str(action)[:80],
             _int_or_none(project_id), _int_or_none(scene_id), _int_or_none(job_id), res, _clean_detail(detail) or None,
             _int_or_none(ms)))
        conn.commit()
        return True
    except Exception as e:  # noqa: BLE001 - nhật ký không bao giờ được chặn thao tác
        if not _warned:
            _warned.append(True)
            try:
                from . import diag
                diag.record(conn, "dashboard", "warning", f"ui_log: không ghi được nhật ký thao tác ({type(e).__name__}: {e})",
                            code="ui_log_write")
            except Exception:  # noqa: BLE001
                pass
        return False


def rows(conn, project_id=None, since: Optional[float] = None, source: Optional[str] = None) -> List[Dict]:
    sql, args = "SELECT * FROM ui_actions WHERE 1=1", []
    if project_id is not None:
        sql += " AND project_id=?"
        args.append(int(project_id))
    if since is not None:
        sql += " AND at>=?"
        args.append(float(since))
    if source:
        sql += " AND source=?"
        args.append(norm_source(source))
    try:
        cur = conn.execute(sql + " ORDER BY at, id", args)
        names = [d[0] for d in cur.description]
        return [dict(zip(names, tuple(r))) for r in cur.fetchall()]
    except Exception:  # noqa: BLE001 - CSDL cũ chưa có bảng → không có dữ liệu
        return []


def summary(conn, project_id=None, since: Optional[float] = None, source: Optional[str] = None) -> Dict:
    """Tóm tắt: số thao tác theo (action, result, source); thời gian xử lý TB theo action; danh sách đổi ý (duyệt↔loại ≤ 5 phút
    cùng job, gen → hủy ≤ 10 phút cùng dự án) và bấm đôi (cùng nút + cùng người + cùng đích ≤ 10 s, lần 1 'noop')."""
    data = rows(conn, project_id, since, source)
    counts = Counter((r["action"], r["result"], r["source"]) for r in data)
    by_source = Counter(r["source"] for r in data)
    ms_acc: Dict[str, List[int]] = defaultdict(list)
    for r in data:
        if r["ms"] is not None:
            ms_acc[r["action"]].append(int(r["ms"]))
    avg_ms = {a: round(sum(v) / len(v)) for a, v in ms_acc.items()}

    flips: List[Dict] = []
    last_decision: Dict = {}                              # (nhóm, job) → dòng quyết định gần nhất
    last_gen: Dict = {}                                   # dự án → dòng gen gần nhất
    last_click: Dict = {}                                 # (action, email, dự án, cảnh, job) → dòng gần nhất
    doubles: List[Dict] = []
    for r in data:
        a = r["action"]
        if a in _DECISIONS and r["result"] == "ok" and r["job_id"] is not None:
            kind, dec = _DECISIONS[a]
            prev = last_decision.get((kind, r["job_id"]))
            if prev is not None and prev["decision"] != dec and r["at"] - prev["row"]["at"] <= FLIP_WINDOW_S:
                flips.append({"kind": f"{prev['row']['action']}→{a}", "job_id": r["job_id"], "project_id": r["project_id"],
                              "source": r["source"], "seconds": round(r["at"] - prev["row"]["at"], 1)})
            last_decision[(kind, r["job_id"])] = {"decision": dec, "row": r}
        if a in _GEN and r["result"] == "ok":
            last_gen[r["project_id"]] = r
        elif a == _CANCEL and r["result"] == "ok":
            prev = last_gen.get(r["project_id"])
            if prev is not None and r["at"] - prev["at"] <= CANCEL_WINDOW_S:
                flips.append({"kind": f"{prev['action']}→{a}", "job_id": r["job_id"], "project_id": r["project_id"],
                              "source": r["source"], "seconds": round(r["at"] - prev["at"], 1)})
        key = (a, r["email"], r["project_id"], r["scene_id"], r["job_id"])
        prev = last_click.get(key)
        if prev is not None and prev["result"] == "noop" and r["at"] - prev["at"] <= DOUBLE_WINDOW_S:
            doubles.append({"action": a, "project_id": r["project_id"], "job_id": r["job_id"], "source": r["source"],
                            "seconds": round(r["at"] - prev["at"], 1)})
        last_click[key] = r
    return {"total": len(data), "by_source": dict(by_source),
            "counts": [{"action": a, "result": res, "source": s, "n": n} for (a, res, s), n in sorted(counts.items())],
            "errors": sum(1 for r in data if r["result"] == "error"), "noops": sum(1 for r in data if r["result"] == "noop"),
            "avg_ms": avg_ms, "flips": flips, "doubles": doubles}
