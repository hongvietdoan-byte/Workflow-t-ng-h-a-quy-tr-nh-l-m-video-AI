"""Sân khấu 3D tự động — chạy tay (core/stage_auto, kế hoạch docs/KE_HOACH_NOI_SAN_KHAU_3D_TU_DONG_2026-10-15.md).

    py tools/stage_auto.py --project 31                       # ước tính Claude, không gọi gì (0 USD)
    py tools/stage_auto.py --project 31 --dry                 # + đo sàn K1 (Blender, 0 USD) + in đề bài từng cảnh, KHÔNG gọi Claude
    py tools/stage_auto.py --project 31 --scene 1 --force --yes --max-usd 1     # thử thật MỘT cảnh (tốn tiền Claude, trần cứng)

--scene: chỉ cảnh truyện này (story_scene) · --force: cả cảnh có shot đã vẽ ảnh (máy mới làm ảnh cũ lệch nền) · --again: bỏ kết quả
đã lưu, gọi Đạo diễn lại. Ghi `stage_camera` vào CSDL (--db) — chỉ khi --yes. Cờ stage_auto TẮT vẫn chạy được ở đây (lệnh tay = người
chọn); autopilot chỉ chạy khi cờ bật."""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATA = os.environ.get("PIPELINE_DATA", os.path.join("data", "projects"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="stage_auto.py")
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--data-dir", default=DATA)
    ap.add_argument("--scene", action="append", help="chỉ cảnh truyện này (story_scene), lặp được")
    ap.add_argument("--dry", action="store_true", help="đo K1 + in đề bài, không gọi Claude (0 USD)")
    ap.add_argument("--force", action="store_true", help="cả cảnh có shot đã vẽ ảnh")
    ap.add_argument("--again", action="store_true", help="bỏ kết quả đã lưu, gọi Đạo diễn lại (tốn tiền)")
    ap.add_argument("--yes", action="store_true", help="đồng ý chi tiền Claude + ghi stage_camera vào CSDL")
    ap.add_argument("--rerender", action="store_true", help="đo + render lại (Blender, 0 USD) từ câu trả lời Đạo diễn đã trả tiền, "
                                                            "không gọi Claude; ghi stage_camera")
    ap.add_argument("--set-family", help="khai họ sân khấu (0 USD, ghi Kho) cho các --place, vd --set-family phong_2_cua --place 447 --place 448")
    ap.add_argument("--place", type=int, action="append", help="id bối cảnh Kho cho --set-family")
    from core import script_cap
    script_cap.add_argument(ap)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = ap.parse_args(argv)
    os.environ["FEATURE_STAGE_AUTO"] = "1"               # lệnh tay = người chọn chạy (cờ chỉ điều khiển autopilot)
    from core import features, stage_auto
    miss = [n for n in features.REQUIRES.get("stage_auto", ()) if not features.on(n)]
    if miss:
        print(f"Cờ cần cho sân khấu tự động đang TẮT: {', '.join(miss)} — bật ở 🧪 rồi chạy lại (máy sân khấu sẽ không được nền 3D dùng)")
        return
    from core.camera_plan import drawn_shots
    from core.db import connect
    conn = connect(os.path.abspath(a.db))
    if a.set_family:
        stage_auto.set_family(conn, a.place or [], a.set_family)
        print(f"Đã khai họ sân khấu '{a.set_family}' cho Kho {a.place}")
    segs = stage_auto.segments(conn, a.project)
    if a.scene:
        segs = [g for g in segs if g["scene"] in a.scene]
    for g in segs:
        drawn = drawn_shots(conn, g)
        print(f"- {g['id']}: shot {', '.join(str(s['idx']) for s in g['shots'])} · chỗ đứng {g['spots']} · gốc O = {g['main_spot']}"
              + (f" · ĐÃ có ảnh shot {drawn}" + ("" if a.force else " → bỏ qua (thêm --force)") if drawn else ""))
    for h in stage_auto.family_hints(segs):
        print("⚠", h)
    if a.rerender:                                       # 16/10: dựng lại ảnh clay / số đo từ câu trả lời đã trả tiền — 0 USD
        for g in segs:
            print()
            print(f"## {g['id']} — render lại từ câu trả lời đã lưu")
            print(json.dumps(stage_auto.rerender(conn, a.project, g, a.data_dir, log=print), ensure_ascii=False, indent=1))
        return
    est = stage_auto.estimate(conn, a.project, a.data_dir, force=a.force)
    picked = [g["id"] for g in segs if a.force or not drawn_shots(conn, g)]
    n = len([x for x in est["segments"] if x in picked])
    one = (est["usd"] or 0) / max(len(est["segments"]), 1)
    if est["usd"] is None:
        print(f"Claude (ước tính): {n} cảnh × 1 lượt — chưa có giá Claude cho model đang dùng (bảng giá)")
    else:
        print(f"Claude (ước tính): {n} cảnh × 1 lượt ≈ {one * n:.3f} USD · xấu nhất ≈ {one * n * 4:.3f} USD (2 lượt sửa × hỏi lại sai mẫu)")
    if a.dry:
        for g in segs:
            if not (a.force or not drawn_shots(conn, g)):
                continue
            try:
                k1 = stage_auto.ensure_k1(g["entry"], g["main_spot"], stage_auto.base_dir(a.data_dir, a.project, g["stage"]), log=print)
            except Exception as e:  # noqa: BLE001
                print(f"  {g['id']}: K1 lỗi — {type(e).__name__}: {e}")
                continue
            inputs, missing = stage_auto.inputs_for(conn, a.project, g, k1)
            print(f"\n## {g['id']}" + (f" — THIẾU: {'; '.join(missing)}" if missing else ""))
            with open(os.path.join(k1, "stage.json"), encoding="utf-8") as f:
                gate = stage_auto.preflight(inputs, json.load(f).get("marks"))
            print("cổng 0 USD (bộ kiểm thật trên câu trả lời mẫu dựng từ đề bài): " + ("; ".join(gate) if gate else "QUA"))
            print(json.dumps(inputs, ensure_ascii=False, indent=1))
        return
    if not a.yes:
        print("Chưa chạy (thêm --yes --max-usd <USD> để đồng ý chi tiền; --dry để xem đề bài 0 USD)")
        return
    from core import llm_runner
    from core.adapters.check import load_dashboard_env
    load_dashboard_env(os.path.join(ROOT, "dashboard.env"))
    cap = script_cap.from_args(a, "stage_auto")
    client = llm_runner.client_from_env(ledger=llm_runner.db_file(conn))
    with cap:
        res = stage_auto.run(conn, a.project, a.data_dir, client=client, force=a.force, again=a.again, log=print,
                             scenes=set(a.scene) if a.scene else None)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
