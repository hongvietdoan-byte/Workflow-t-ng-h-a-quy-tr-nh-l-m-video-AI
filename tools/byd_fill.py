"""K1a — điền bảng ý đồ shot (BYĐ) cho các shot ĐÃ CÓ của một dự án, KHÔNG chạy lại Đạo diễn.

    py tools/byd_fill.py --project 24                       # chạy khô (mặc định): 0 USD, không gọi Claude
    py tools/byd_fill.py --project 24 --yes --max-usd 0.5   # gọi thật

Cách làm: đọc các hàng `scenes` (shot) của dự án như core/shots.shots_of; shot đã có `data['byd']` hợp lệ (core.director_byd.problems
không còn lỗi ĐỎ) → giữ nguyên, KHÔNG gửi; shot chưa có BYĐ / BYĐ hỏng → đưa vào core.director_byd.settle (BYĐ thiếu = lỗi ĐỎ → lượt
Claude sửa ≤ MAX_ROUNDS vòng, khâu `director_byd`, sổ chi `llm_runner.tagged`; còn hỏng → VÀNG + lý do). Shot không dựng được đầu vào
(data hỏng / không phải hàng shot) → in VÀNG lý do, bỏ qua (không im lặng).

--dry-run (mặc định khi không có --yes): in số shot sẽ điền + ước tính USD (cost.llm_estimate("director_byd", MAX_ROUNDS) — cùng số
project_budget dùng cho lượt sửa — và ước tính theo số shot của director_byd.estimate như nút Đạo diễn; lấy số LỚN hơn, tính dư) + cảnh
báo mức dự tính dự án (project_budget.warning). Không gọi Claude.

--yes: bắt buộc --max-usd (core.script_cap, trần CỨNG). Client = llm_runner.client_from_env(ledger=--db) — cùng client/sổ chi như
run_director (AnthropicClient tự `_check_budget` trước mỗi lượt). CHỈ ghi `scenes.data['byd']` + `['byd_kiem']` của shot được gửi;
mọi trường khác của shot, ảnh, job giữ nguyên.

Cờ `shot_intent`: công cụ tự BẬT cờ trong phạm vi lời gọi settle (vá `director_byd.enabled` tạm thời bằng unittest.mock, KHÔNG ghi
feature_settings, không đổi cờ cho Dashboard / tiến trình khác). Cờ tắt thì các khâu đọc BYĐ (shots.shot_data, …) vẫn bỏ qua trường mới.
"""
import argparse
import json
import os
import sys
from typing import Dict, List, Optional
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import cost, director_byd  # noqa: E402


def plan(conn, pid: int) -> Dict:
    """Chia các hàng scenes của dự án: `fill` (gửi sửa), `keep` (đã có BYĐ hợp lệ), `bad_input` (không dựng được đầu vào, kèm lý do)."""
    fill, keep, bad_input = [], [], []
    for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)):
        rid, idx = r[0], r[1]
        try:
            data = json.loads(r[2] or "{}")
        except (TypeError, ValueError) as e:
            bad_input.append({"id": rid, "idx": idx, "why": f"data không đọc được JSON ({e})"})
            continue
        if not isinstance(data, dict):
            bad_input.append({"id": rid, "idx": idx, "why": "data không phải object"})
            continue
        missing = [k for k in ("shot_no", "size", "action") if data.get(k) in (None, "")]
        if missing:
            bad_input.append({"id": rid, "idx": idx, "why": "không phải hàng shot của Đạo diễn (thiếu " + ", ".join(missing) + ")"})
            continue
        row = {"id": rid, "idx": idx, "data": data}
        if data.get("byd") is not None and not director_byd.problems(data, conn)[0]:
            keep.append(row)
        else:
            fill.append(row)
    return {"fill": fill, "keep": keep, "bad_input": bad_input}


def estimate_usd(conn, n_shots: int) -> Dict:
    """Ước tính (tính dư) cho n shot: lượt sửa đo theo sổ chi / bảng LLM_STAGE_TOKENS và theo cỡ đề bài; dùng số lớn hơn."""
    if n_shots <= 0:
        return {"ledger": 0.0, "by_size": 0.0, "usd": 0.0}
    ledger = cost.llm_estimate(conn, director_byd.STAGE, director_byd.MAX_ROUNDS)
    from core.director_two_pass import _usd
    ext = director_byd.estimate(n_shots)
    by_size = _usd(cost.llm_model(), {"input": ext["repair_input"], "output": ext["repair_output"]})
    known = [u for u in (ledger, by_size) if u is not None]
    return {"ledger": ledger, "by_size": by_size, "usd": max(known) if known else None}


def _obj(rows: List[Dict]) -> Dict:
    """Đầu vào cho settle: cảnh = story_scene (không có → idx hàng), shot theo shot_no; trả kèm bản đồ (cảnh, k) → hàng."""
    groups: Dict[int, List[Dict]] = {}
    for row in rows:
        sc = row["data"].get("story_scene")
        sc = sc if isinstance(sc, int) else row["idx"]
        groups.setdefault(sc, []).append(row)
    scenes, where = [], {}
    for sc in sorted(groups):
        lst = sorted(groups[sc], key=lambda r: (r["data"].get("shot_no") if isinstance(r["data"].get("shot_no"), int) else 0, r["idx"]))
        shots = []
        for k, row in enumerate(lst, 1):
            s = dict(row["data"])                 # bản sao: settle chỉ đặt byd / byd_kiem lên đây
            shots.append(s)
            where[(sc, k)] = (row, s)
        scenes.append({"idx": sc, "shots": shots})
    return {"scenes": scenes}, where


def fill(conn, pid: int, rows: List[Dict], client) -> List[Dict]:
    """Gọi settle (cờ shot_intent bật trong phạm vi này), ghi CHỈ byd/byd_kiem của từng hàng; trả kết quả mỗi shot."""
    obj, where = _obj(rows)
    with mock.patch.object(director_byd, "enabled", lambda: True):
        director_byd.settle(conn, pid, obj, client)
    out = []
    for (sc, k), (row, s) in sorted(where.items()):
        cur = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (row["id"],)).fetchone()[0] or "{}")
        for key in ("byd", "byd_kiem"):
            if s.get(key) is not None:
                cur[key] = s[key]
        conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(cur, ensure_ascii=False), row["id"]))
        kiem = s.get("byd_kiem") or {}
        out.append({"id": row["id"], "idx": row["idx"], "canh": sc, "shot": k, "muc": kiem.get("muc") or "vang",
                    "ly_do": kiem.get("ly_do") or ("" if kiem else "settle không ghi byd_kiem")})
    conn.commit()
    return out


def main(argv=None, conn=None, client=None) -> int:
    ap = argparse.ArgumentParser(description="Điền BYĐ cho shot đã có (không chạy lại Đạo diễn)")
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--dry-run", action="store_true", help="mặc định khi không có --yes: 0 USD, không gọi Claude")
    ap.add_argument("--yes", action="store_true", help="gọi Claude thật (cần --max-usd)")
    from core import script_cap
    script_cap.add_argument(ap)
    a = ap.parse_args(argv)
    paid = a.yes and not a.dry_run
    a.yes = paid
    cap = script_cap.from_args(a, "byd_fill")
    if conn is None:
        from core.db import connect
        conn = connect(a.db)
    pid = a.project
    pl = plan(conn, pid)
    for b in pl["bad_input"]:
        print(f"  VÀNG hàng #{b['idx']} (id {b['id']}): không dựng được đầu vào — {b['why']}")
    n = len(pl["fill"])
    print(f"dự án #{pid}: {n} shot sẽ điền BYĐ · {len(pl['keep'])} shot đã có BYĐ hợp lệ (giữ nguyên, không gửi) · "
          f"{len(pl['bad_input'])} hàng bỏ qua (VÀNG)")
    if not n:
        print("không có shot nào cần điền — không gọi Claude")
        return 0
    est = estimate_usd(conn, n)
    usd = est["usd"]
    print("Ước tính ≈ " + (f"{usd:.2f} USD" if usd is not None else "chưa có giá") + f" (tối đa {director_byd.MAX_ROUNDS} lượt sửa; "
          f"sổ chi {est['ledger']} · theo cỡ {est['by_size']}; tính dư)")
    from core import project_budget
    warn = project_budget.warning(conn, pid, project_budget.claude_stage(director_byd.STAGE), usd)
    print(warn or "mức dự tính dự án: không vượt (hoặc dự án chưa đặt mức)")
    if not paid:
        print("(chạy khô — chưa gọi Claude; thêm --yes --max-usd <USD> để chạy)")
        return 0
    cap.guard(usd, "điền BYĐ")
    if client is None:
        from core import llm_runner
        from core.adapters.check import load_dashboard_env
        load_dashboard_env()
        client = llm_runner.client_from_env(ledger=a.db)
        if client is None:
            raise SystemExit("Chưa cấu hình Claude API (dashboard.env).")
    for r in fill(conn, pid, pl["fill"], client):
        print(f"  {r['muc'].upper():4} cảnh {r['canh']} shot {r['shot']} (hàng #{r['idx']})" + (f" — {r['ly_do']}" if r["ly_do"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
