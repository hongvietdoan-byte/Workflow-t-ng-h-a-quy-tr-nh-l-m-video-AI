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
    ap.add_argument("--prompt-out", help="NGOẠI TUYẾN 0 USD: ghi đề bài + khuôn định dạng của cảnh (--scene, một cảnh) ra tệp này")
    ap.add_argument("--answer", help="NGOẠI TUYẾN 0 USD: đọc câu trả lời JSON (người / phiên Claude Code viết) thay lời gọi Claude; lỗi "
                                     "ghi <tệp>.loi.txt để sửa rồi chạy lại; đạt → Blender + ghi stage_camera")
    ap.add_argument("--source", default="claude_code", help="nguồn câu trả lời ngoại tuyến (ghi vào result.json / báo cáo)")
    ap.add_argument("--score", action="store_true", help="0 USD: chấm các lượt Đạo diễn đã lưu bằng bộ kiểm hiện tại (luật kịch bản + "
                                                         "K3 khung) + cổng 0 USD của đề bài hiện tại — chạy TRƯỚC khi trả tiền chạy lại")
    ap.add_argument("--rerender", action="store_true", help="đo + render lại (Blender, 0 USD) từ câu trả lời Đạo diễn đã trả tiền, "
                                                            "không gọi Claude; ghi stage_camera")
    ap.add_argument("--crew", action="store_true", help="NGOẠI TUYẾN 0 USD, CHIA VAI (Đạo diễn → Quay phim → Quay phim duyệt → duyệt "
                                                        "chốt): --prompt-out ghi đề bài của vai đang tới lượt, --answer đưa câu trả lời "
                                                        "của vai đó (đo K3 + K4 khi cần)")
    ap.add_argument("--crew-reset", action="store_true", help="cất lượt chia vai đang dở, bắt đầu lại từ Đạo diễn")
    ap.add_argument("--cam-tay", action="store_true", help="cờ stage_handheld_props: dàn lại đoạn ĐÃ dàn (không có đồ cầm tay) CÓ súng "
                                                         "(đầu vào đổi — kèm --crew-reset / --again)")
    ap.add_argument("--crew-approve", action="store_true", help="NGƯỜI DÙNG đã duyệt ảnh ghép (nói trong chat) → ghi stage_camera")
    ap.add_argument("--crew-tra-lai", metavar="JSON", help="NGƯỜI DÙNG trả lại: tệp [{\"shot\": 10, \"y_do\": \"…\"}] → Quay phim duyệt lại")
    ap.add_argument("--beats", metavar="THU_MUC", help="0 USD: lượt đã lưu của từng cảnh → mặt cắt bỏ mái (Blender, nếu chưa có) + "
                                                       "top_beats.png (đánh số / làm mờ theo nhịp) + ảnh ghép san_khau_canh<N>.png "
                                                       "vào THU_MUC; không ghi CSDL")
    ap.add_argument("--set-family",help="khai họ sân khấu (0 USD, ghi Kho) cho các --place, vd --set-family phong_2_cua --place 447 --place 448")
    ap.add_argument("--place", type=int, action="append", help="id bối cảnh Kho cho --set-family")
    from core import script_cap
    script_cap.add_argument(ap)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = ap.parse_args(argv)
    os.environ["FEATURE_STAGE_AUTO"] = "1"               # lệnh tay = người chọn chạy (cờ chỉ điều khiển autopilot)
    from core import features, stage_auto
    miss = [n for n in features.REQUIRES.get("stage_auto", ()) if not features.on(n)]
    if miss and not a.beats:                             # --beats chỉ vẽ ảnh từ lượt đã lưu (0 USD, không ghi CSDL)
        print(f"Cờ cần cho sân khấu tự động đang TẮT: {', '.join(miss)} — bật ở 🧪 rồi chạy lại (máy sân khấu sẽ không được nền 3D dùng)")
        return
    from core.camera_plan import drawn_shots
    from core.db import connect
    conn = connect(os.path.abspath(a.db))
    from core import ui_step                             # C-DEVSYS-MAPS (cờ ui_step_log): việc làm NGOÀI Dashboard → nút ảo trên sơ đồ
    ui_step.cli(conn, "stage_auto", a.project, "sân khấu 3D" + (f" cảnh {a.scene}" if a.scene else " cả dự án"))
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
    from core import features
    if a.cam_tay:
        os.environ[stage_auto.HANDHELD_REDO_ENV] = "1"
    elif features.on(stage_auto.HANDHELD_FLAG):         # 16/10: nói rõ đoạn nào giữ đầu vào cũ (không im lặng)
        for g in segs:
            if stage_auto.placed_without_handheld(os.path.join(stage_auto.base_dir(a.data_dir, a.project, g["stage"]), "k1"), g):
                print(f"ℹ {g['id']}: đã dàn trước cờ đồ cầm tay → giữ đầu vào cũ (không có súng); dàn lại có súng: --crew-reset --cam-tay")
    if a.crew or a.crew_approve or a.crew_tra_lai:     # 16/10 chia vai (kế hoạch docs/KE_HOACH_CHIA_VAI_SAN_KHAU_2026-10-16.md)
        if len(segs) != 1:
            print("Chế độ chia vai cần đúng MỘT cảnh (--scene)")
            return
        g = segs[0]
        if (a.answer or a.crew_approve or a.crew_tra_lai) and drawn_shots(conn, g) and not a.force:
            print(f"{g['id']}: có shot đã vẽ ảnh — thêm --force để đổi máy")
            return
        if a.crew_approve or a.crew_tra_lai:
            tra = []
            if a.crew_tra_lai:
                with open(a.crew_tra_lai, encoding="utf-8") as f:
                    tra = json.load(f)
            r = stage_auto.crew_user_verdict(conn, a.project, g, a.data_dir, bool(a.crew_approve), tra, log=print)
            print(json.dumps({k: v for k, v in r.items() if k != "result"}, ensure_ascii=False, indent=1, default=str))
            return
        if a.prompt_out:
            text, problems, st = stage_auto.crew_prompt(conn, a.project, g, a.data_dir, reset=a.crew_reset)
            if text:
                with open(a.prompt_out, "w", encoding="utf-8") as f:
                    f.write(text)
            print(f"{g['id']} — bước '{st['phase']}'" + (f": đề bài → {a.prompt_out} ({len(text)} ký tự)" if text else "")
                  + (f" — CHÚ Ý: {'; '.join(problems)}" if problems else ""))
        if a.answer:
            from core.llm_runner import extract_json
            try:
                with open(a.answer, encoding="utf-8") as f:
                    obj = extract_json(f.read())
                r = stage_auto.crew_answer(conn, a.project, g, a.data_dir, obj, source=a.source, log=print)
            except (OSError, ValueError, TypeError) as e:
                r = {"ok": False, "errors": [f"không đọc được câu trả lời: {type(e).__name__}: {e}"]}
            loi = a.answer + ".loi.txt"
            with open(loi, "w", encoding="utf-8") as f:
                f.write(chr(10).join(r["errors"]) if r.get("errors") else "ĐẠT")
            print(json.dumps({k: v for k, v in r.items() if k not in ("errors", "result")}, ensure_ascii=False, indent=1, default=str))
            print(("LỖI (" + str(len(r["errors"])) + ") → " + loi) if r.get("errors") else f"ĐẠT — bước kế: {r.get('phase')}")
        return
    if a.prompt_out or a.answer:
        if len(segs) != 1:
            print("Chế độ ngoại tuyến cần đúng MỘT cảnh (--scene)")
            return
        g = segs[0]
        if a.prompt_out:
            text, problems = stage_auto.offline_prompt(conn, a.project, g, a.data_dir)
            with open(a.prompt_out, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Đã ghi đề bài {g['id']} → {a.prompt_out} ({len(text)} ký tự)" + (f" — CHÚ Ý: {'; '.join(problems)}" if problems else ""))
        if a.answer:
            if drawn_shots(conn, g) and not a.force:
                print(f"{g['id']}: có shot đã vẽ ảnh — thêm --force để đổi máy")
                return
            from core.llm_runner import extract_json
            try:
                with open(a.answer, encoding="utf-8") as f:
                    obj = extract_json(f.read())
                r = stage_auto.offline_answer(conn, a.project, g, a.data_dir, obj, source=a.source, log=print)
            except (OSError, ValueError, TypeError) as e:
                r = {"ok": False, "errors": [f"không đọc được câu trả lời: {type(e).__name__}: {e}"]}
            loi = a.answer + ".loi.txt"
            with open(loi, "w", encoding="utf-8") as f:
                f.write(chr(10).join(r["errors"]) if r["errors"] else "ĐẠT")
            print(json.dumps({k: v for k, v in r.items() if k != "errors"}, ensure_ascii=False, indent=1))
            print(("LỖI (" + str(len(r["errors"])) + ") → " + loi) if r["errors"] else "ĐẠT — đã ghi stage_camera")
        return
    if a.beats:                                          # 16/10: ảnh nhìn từ trên theo nhịp cho người duyệt — 0 USD, không ghi CSDL
        os.makedirs(a.beats, exist_ok=True)
        t = stage_auto.tool()
        for g in segs:
            got = stage_auto.result_round(a.data_dir, a.project, g)
            if got is None:
                print(f"## {g['id']}: chưa có lượt đã lưu — bỏ qua")
                continue
            if not os.path.exists(os.path.join(got, "top_cut.png")):
                try:
                    t.top_cut(got, log=print)
                except Exception as e:  # noqa: BLE001 - vẫn vẽ trên ảnh chưa cắt
                    print(f"  {g['id']}: không cắt được mái ({type(e).__name__}: {e}) — vẽ trên ảnh từ trên thường")
            title = f"#{a.project} cảnh {g['scene']} — {g['id']} (shot {g['shots'][0]['idx']}–{g['shots'][-1]['idx']})"
            try:                                         # rà 16/10: một cảnh hỏng không dừng cả vòng
                t.draw_beats(got)
                print(t.stage_sheet(got, title, os.path.join(a.beats, f"san_khau_canh{g['scene']}.png")))
            except Exception as e:  # noqa: BLE001
                print(f"  {g['id']}: không vẽ được ({type(e).__name__}: {e})")
        return
    if a.score:
        for g in segs:
            print(f"## {g['id']}")
            print(json.dumps(stage_auto.score_saved(conn, a.project, g, a.data_dir), ensure_ascii=False, indent=1))
        return
    if a.rerender:                                       # 16/10: dựng lại ảnh clay / số đo từ câu trả lời đã trả tiền — 0 USD
        for g in segs:
            if drawn_shots(conn, g) and not a.force:      # rà 16/10: máy mới làm ảnh đã vẽ lệch nền — như luồng thường
                print(f"## {g['id']}: có shot đã vẽ ảnh — bỏ qua (thêm --force)")
                continue
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
                k1 = stage_auto.ensure_k1_seg(g, stage_auto.base_dir(a.data_dir, a.project, g["stage"]), log=print)
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
    if client is None:
        raise SystemExit("Chưa có Claude: " + llm_runner.missing_hint())
    with cap:
        res = stage_auto.run(conn, a.project, a.data_dir, client=client, force=a.force, again=a.again, log=print,
                             scenes=set(a.scene) if a.scene else None)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
