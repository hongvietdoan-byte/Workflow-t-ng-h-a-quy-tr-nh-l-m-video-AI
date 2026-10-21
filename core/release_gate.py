"""V3.1 M5.2 (DP6, cloud-C 20/10) — CỔNG PHÁT HÀNH: checklist đo được trước khi xuất bản → ĐẠT / CHƯA ĐẠT kèm lý do.
Thiết kế docs/V3_1_M5_THIET_KE_REPAIR_RELEASE_2026-10-20.md mục 3. Cờ `release_gate` (mặc định TẮT: không đo, không hiện gì). Bật = chế độ
shadow: CHỈ CẢNH BÁO ở màn Bản giao, KHÔNG chặn nút xuất (chặn = `guarded`, Cấp 3, người dùng duyệt sau). 0 USD, chỉ đọc.

Mỗi mục: "dat" / "chua_dat" / "khong_ro" (đo không được — nói lý do; KHÔNG BAO GIỜ coi là đạt)."""
import json
import os
import time
from typing import Dict, List, Optional

FLAG = "release_gate"
DAT, CHUA, KHONG_RO = "dat", "chua_dat", "khong_ro"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPEN_SEVERE = ("cao",)
CLOSED = ("VERIFIED", "WONT_FIX")
CACHE_TTL_S = 120          # C-FIX-THAP-3: thiết lập đổi mà chưa dựng lại vẫn hiện "⚠ cũ" trong ≤ 2 phút (khóa cache chỉ theo bản dựng)


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _item(gid: str, label: str, state: str, why: str, **numbers) -> Dict:
    return {"id": gid, "label": label, "state": state, "why": why, **({"numbers": numbers} if numbers else {})}


def _g1_shots_approved(p, pid: int, data_dir: str) -> Dict:
    from . import final_cut
    clips = [c for c in final_cut.collect_clips(p, data_dir, pid) if not c.get("extra")]
    if not clips:
        return _item("G1", "Mọi shot trong bản dựng đã duyệt", KHONG_RO, "chưa có shot nào có clip")
    bad = [c for c in clips if c.get("state") != "approved"]
    if bad:
        return _item("G1", "Mọi shot trong bản dựng đã duyệt", CHUA,
                     f"{len(bad)}/{len(clips)} shot chưa duyệt: " + ", ".join(f"{c['idx']} ({c.get('state') or 'chưa có clip'})" for c in bad[:8])
                     + (" …" if len(bad) > 8 else ""), chua_duyet=len(bad), tong=len(clips))
    return _item("G1", "Mọi shot trong bản dựng đã duyệt", DAT, f"{len(clips)}/{len(clips)} shot đã duyệt", tong=len(clips))


def _render_mtime(p, pid: int) -> Optional[float]:
    from . import lineage
    fin = lineage.latest_output(p.conn, pid, "final")
    try:
        return os.path.getmtime(fin["path"]) if fin is not None else None
    except (OSError, TypeError, KeyError, IndexError):
        return None


def _cached(cache: Optional[Dict], name: str, p, pid: int, fn):
    """C-FIX-THAP-3: kết quả đo đắt (final_qc.run / delivery.status) nhớ theo BẢN DỰNG — (id bản final mới nhất, id output mới nhất của dự án
    = lớp phụ đề / card / kích thước, mtime tệp final) + hạn CACHE_TTL_S. cache None = đo mỗi lần như cũ."""
    if cache is None:
        return fn()
    conn = p.conn
    final = conn.execute("SELECT MAX(id) FROM outputs WHERE project_id=? AND kind='final'", (pid,)).fetchone()[0]
    last = conn.execute("SELECT MAX(id) FROM outputs WHERE project_id=?", (pid,)).fetchone()[0]
    key = (pid, name, final, last, _render_mtime(p, pid))
    now = time.monotonic()
    hit = cache.get(key)
    if hit is not None and now - hit[0] <= CACHE_TTL_S:
        return hit[1]
    for k in [k for k in cache if isinstance(k, tuple) and k[:2] == (pid, name)]:
        cache.pop(k, None)                             # bản cũ của chính phép đo này: không giữ mãi trong session
    val = fn()
    cache[key] = (now, val)
    return val


def _g2_final_qc(p, pid: int, data_dir: str, cache: Optional[Dict] = None) -> Dict:
    from . import final_qc
    res = _cached(cache, "final_qc", p, pid, lambda: final_qc.run(p, pid, data_dir, frames=False))          # chỉ đọc số liệu dựng (không đọc video) — cổng chạy nhanh mỗi lần mở màn
    codes = [i["code"] for i in res["issues"]]
    if "no_render" in codes:
        return _item("G2", "Kiểm bản dựng không có lỗi chặn", CHUA, "chưa có bản dựng")
    if res["blocks"]:
        return _item("G2", "Kiểm bản dựng không có lỗi chặn", CHUA, "; ".join(i["msg"] for i in res["issues"] if i["level"] == "block")[:400],
                     blocks=res["blocks"], warns=res["warns"])
    return _item("G2", "Kiểm bản dựng không có lỗi chặn", DAT,
                 f"0 lỗi chặn, {res['warns']} cần xem (mục đọc video — im lặng, phụ đề đè mặt, đen/đứng hình — chạy ở nút Kiểm bản dựng)",
                 warns=res["warns"])


def _g3_layers_current(p, pid: int, data_dir: str, cache: Optional[Dict] = None) -> Dict:
    from . import delivery
    st = _cached(cache, "delivery_status", p, pid, lambda: delivery.status(p, pid, data_dir))
    fin = st.get("final") or {}
    if fin.get("state") == "missing":
        return _item("G3", "Bản giao khớp nguồn (không lớp ⚠ cũ)", CHUA, "chưa có bản dựng")
    stale = []
    if fin.get("state") == "stale":
        stale.append("bản dựng: " + "; ".join(fin.get("reasons") or ["cũ"]))
    stale += [f"{x['kind']}: {x['stale']}" for x in st.get("layers") or [] if x.get("stale")]
    if stale:
        return _item("G3", "Bản giao khớp nguồn (không lớp ⚠ cũ)", CHUA, " · ".join(stale)[:400], cu=len(stale))
    return _item("G3", "Bản giao khớp nguồn (không lớp ⚠ cũ)", DAT, "bản dựng + các lớp khớp clip / âm / thiết lập hiện tại")


def _g4_cost(p, pid: int) -> Dict:
    """Đối soát sổ chi ↔ nhà cung cấp cần đọc ClipAI (tools/clipai_cost_reconcile.py, máy chính) — cổng không gọi mạng: báo KHÔNG RÕ kèm lệnh;
    sổ chi có lượt chưa có giá thì CHƯA ĐẠT ngay (đo được tại chỗ)."""
    from . import project_budget
    unpriced = sum(project_budget.unpriced_by_stage(p.conn, pid).values())     # dòng sổ chi bảng giá không biết (tiền chưa rõ, không phải 0)
    if unpriced:
        return _item("G4", "Đối soát chi phí", CHUA, f"{unpriced} lượt gen trong sổ chi chưa có giá — đối soát với nhà cung cấp", chua_gia=unpriced)
    return _item("G4", "Đối soát chi phí", KHONG_RO,
                 f"chưa đối soát với nhà cung cấp — chạy `py tools/clipai_cost_reconcile.py --project {pid}` ở máy chính (đọc ClipAI, 0 USD)")


def _g5_no_unknown_send(p, pid: int) -> Dict:
    from .pipeline import SUBMIT_UNKNOWN
    rows = p.conn.execute(
        "SELECT j.id, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id JOIN job_events e ON e.job_id=j.id AND e.to_state='failed' "
        "WHERE j.project_id=? AND j.state='failed' AND e.note LIKE ? AND NOT EXISTS (SELECT 1 FROM jobs k WHERE k.scene_id=j.scene_id "
        "AND k.type=j.type AND k.id>j.id AND k.state IN ('succeeded','pending_review','approved'))", (pid, SUBMIT_UNKNOWN + "%")).fetchall()
    if rows:
        return _item("G5", "Không còn lần gửi chưa rõ kết quả", CHUA,
                     "job gửi không rõ kết quả chưa đối soát (có thể đã tính tiền): " + ", ".join(f"#{r[0]} (shot {r[1]})" for r in rows[:8]),
                     so_job=len(rows))
    return _item("G5", "Không còn lần gửi chưa rõ kết quả", DAT, "0 job submit_unknown chưa đối soát")


def _g6_severe_errors(pid: int, path: Optional[str] = None) -> Dict:
    try:
        with open(path or os.path.join(ROOT, "devsys", "errors.json"), encoding="utf-8") as f:
            items = json.load(f)["items"]
    except (OSError, ValueError, KeyError) as e:
        return _item("G6", "Không còn lỗi nghiêm trọng mở", KHONG_RO, f"không đọc được sổ lỗi ({type(e).__name__})")
    open_ = [x["id"] for x in items if pid in (x.get("project_ids") or []) and x.get("severity") in OPEN_SEVERE
             and x.get("status") not in CLOSED]
    if open_:
        return _item("G6", "Không còn lỗi nghiêm trọng mở", CHUA, f"{len(open_)} lỗi mức CAO của dự án chưa VERIFIED: " + ", ".join(open_[:10]),
                     so_loi=len(open_))
    return _item("G6", "Không còn lỗi nghiêm trọng mở", DAT, "0 lỗi mức CAO mở gắn dự án này trong sổ lỗi")


def _g7_no_waiting_review(p, pid: int) -> Dict:
    n = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND escalated=1 AND state IN ('pending_review','failed','succeeded')",
                       (pid,)).fetchone()[0]
    if n:
        return _item("G7", "Không còn việc chờ người quyết", CHUA, f"{n} job đang chờ bạn quyết (📥)", cho=n)
    return _item("G7", "Không còn việc chờ người quyết", DAT, "0 job leo thang chờ người")


def _g8_lineage(p, pid: int) -> Dict:
    from . import lineage
    fin = lineage.latest_output(p.conn, pid, "final")
    if fin is None:
        return _item("G8", "Bản dựng có nguồn (lineage)", CHUA, "chưa có bản dựng")
    try:
        man = json.loads(fin["manifest"] or "{}")
    except ValueError:
        man = {}
    if not man.get("timeline"):
        return _item("G8", "Bản dựng có nguồn (lineage)", CHUA, "bản dựng không ghi danh sách clip (timeline) — không truy được nguồn")
    return _item("G8", "Bản dựng có nguồn (lineage)", DAT, f"bản dựng ghi {len(man['timeline'])} clip nguồn")


def check(p, project_id: int, data_dir: str, errors_path: Optional[str] = None, cache: Optional[Dict] = None) -> Dict:
    """{"ok", "items": [8 mục], "dat", "chua_dat", "khong_ro"} — chỉ đọc. Một mục đo lỗi → KHÔNG RÕ có lý do (không coi là đạt).
    `cache` (dict sống qua các lần Streamlit rerun, vd session_state): G2 / G3 không đo lại khi bản dựng chưa đổi (_cached)."""
    steps = [("G1", lambda: _g1_shots_approved(p, project_id, data_dir)), ("G2", lambda: _g2_final_qc(p, project_id, data_dir, cache)),
             ("G3", lambda: _g3_layers_current(p, project_id, data_dir, cache)), ("G4", lambda: _g4_cost(p, project_id)),
             ("G5", lambda: _g5_no_unknown_send(p, project_id)), ("G6", lambda: _g6_severe_errors(project_id, errors_path)),
             ("G7", lambda: _g7_no_waiting_review(p, project_id)), ("G8", lambda: _g8_lineage(p, project_id))]
    items: List[Dict] = []
    for gid, fn in steps:
        try:
            items.append(fn())
        except Exception as e:  # noqa: BLE001 - one unmeasurable item never hides the others
            items.append(_item(gid, gid, KHONG_RO, f"không đo được ({type(e).__name__}: {str(e)[:120]})"))
    count = {s: sum(i["state"] == s for i in items) for s in (DAT, CHUA, KHONG_RO)}
    return {"ok": count[DAT] == len(items), "items": items, **count}


def summary(res: Dict) -> str:
    """Câu cho màn Bản giao (shadow): ĐẠT / CHƯA ĐẠT + từng mục chưa đạt / không rõ. Chỉ cảnh báo — không chặn nút xuất."""
    mark = {DAT: "✅", CHUA: "❌", KHONG_RO: "❔"}
    counts = f"đạt {res[DAT]} · chưa đo {res[KHONG_RO]} · chưa đạt {res[CHUA]}"
    # C-FIX-THAP-3: chỉ THIẾU ĐO (G4 đối soát cần máy chính) không phải "CHƯA ĐẠT" — vẫn không phải ĐẠT (ok False)
    head = ("✅ Cổng phát hành: ĐẠT 8/8" if res["ok"] else
            f"⚠ Cổng phát hành: CHƯA ĐẠT — {counts} (chỉ cảnh báo, vẫn xuất được)" if res[CHUA] else
            f"❔ Cổng phát hành: CHƯA ĐO ĐỦ — {counts} (chỉ cảnh báo, vẫn xuất được)")
    lines = [f"- {mark[i['state']]} {i['id']} {i['label']}: {i['why']}" for i in res["items"] if i["state"] != DAT]
    return head + ("\n" + "\n".join(lines) if lines else "")
