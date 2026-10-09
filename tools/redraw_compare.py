"""Vẽ lại THỬ mọi ảnh khung đầu của một dự án theo quy trình hiện tại để so với bản cũ (đợt C 09/10, người dùng duyệt chi phí cho #24).

    py tools/redraw_compare.py --pid 24          # chạy khô: in số job sẽ tạo + ước tính giá
    py tools/redraw_compare.py --pid 24 --go     # tạo job

Chỉ TẠO job `image_gen` (origin 'user'); bản cũ đã duyệt giữ nguyên (không bỏ duyệt) — thẻ ảnh có ‹ › / chip để so, chọn lại bằng
"↩ Dùng bản này". Vòng nền của Dashboard đang chạy tự gửi / tải / QC như khi bấm nút. KHÔNG tự gửi từ đây: gửi + hỏi từ hai tiến trình
cùng lúc có thể gửi trùng (trả tiền 2 lần). Chạy từ thư mục gốc repo."""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core import cost, image_models  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--go", action="store_true")
    a = ap.parse_args()
    p = Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))
    proj = p.project(a.pid)
    rows = p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx", (a.pid,)).fetchall()
    busy = {r[0] for r in p.conn.execute("SELECT scene_id FROM jobs WHERE project_id=? AND type='image_gen' "
                                          "AND state IN ('queued','running','retryable')", (a.pid,))}
    todo = [r for r in rows if r["id"] not in busy]
    model = image_models.of_project(proj)
    unit = (cost.load_pricing().get("per_image") or {}).get(model)
    print(f"#{a.pid}: {len(rows)} shot, đang có job ảnh chờ/chạy: {len(busy)} → tạo {len(todo)} job · {model} · ≈ {unit} USD/ảnh → "
          f"≈ {len(todo) * (unit or 0):.2f} USD (chưa tính QC Claude / tự vẽ lại)")
    if a.go:
        made = [(r["idx"], p._insert_job(a.pid, r["id"], "image_gen", origin="user")) for r in todo]
        p.conn.commit()
        print("đã tạo (shot, job):", made)


if __name__ == "__main__":
    main()
