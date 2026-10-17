"""Kiểm TRƯỚC KHI GEN ẢNH — 0 USD, CHỈ ĐỌC dữ liệu thật (17/10, sau #31: phiên Claude báo giá tính tay 1,87 USD trong khi Dashboard
ghi ≈ 2,13 / 5,0 USD, 7 nền 3D cũ và 13 mục đỏ của Tổ rà soát đang giữ gen — mấy thứ chỉ thấy khi mở Dashboard).

    PYTHONUTF8=1 py tools/pregen_check.py --project 31 [--main D:/AI-Video-Pipeline] [--payload] [--shot 5] [--json out.json]

Gọi ĐÚNG các hàm nút "▶ Gen ảnh" (Bước 2) và job gen ảnh chạy, không tính lại song song:
  - batch.image_gates(…, data_dir)        cổng chặn / lưu ý (Bible, Character Lock, nền 3D cũ = location_pack.stale_plates)
  - change_review.blocking(…) từng shot   mục đỏ Tổ rà soát tác động còn mở / thay đổi chờ rà (chạy lại luật code, như runner)
  - place_refs.missing / broken / needs    nền 3D chưa có / hỏng / chờ hướng (runner giữ ảnh)
  - cost.estimate_images(…)                MỘT con số giá = nút Gen = ô 💰 (ảnh + khung cuối + ảnh toàn cảnh + D6 + QC Claude), có dòng tách
  - --payload: tools/replay_payload.replay  gói gửi model từng shot (prompt + ảnh tham chiếu)
Chạy trong thư mục thử như replay_payload (bản sao CSDL + cài đặt cờ + thư mục dự án; junction assets/_plates3d chỉ đọc; mọi ghi dưới
<main>/data bị chặn). Giá và cổng tính với cờ THẬT của máy (kể cả D6 chat_prompts); phần --payload tắt D6 (không gọi Claude).
Mã thoát: 0 = gen được; 1 = còn chặn (cổng / mục đỏ / nền) — báo người dùng, không xin duyệt gen khi còn chặn.
Phiên Claude dùng lệnh này để báo giá và tình trạng trước khi xin duyệt gen ảnh (CLAUDE.md, skill vong-lam-viec-theo-plan).
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import replay_payload as rp  # noqa: E402


def check(conn, pid: int, data_dir: str) -> dict:
    """{gates, plates_stale, holds: [{idx, why}], plates: [{idx, state, why}], estimate, estimate_text} — the Gen button's own calls."""
    from core import batch, change_review, cost, image_models, place_refs, shots
    from core.pipeline import Pipeline
    pipe = Pipeline(conn)
    proj = pipe.project(pid)
    gates = batch.image_gates(pipe, pid, data_dir, scene_ids=batch.image_targets(pipe, pid, include_queued=True))   # = the button
    holds, plates = [], []
    on = place_refs.enabled()
    for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        data = json.loads(r["data"] or "{}")
        if not shots.needs_own_image(conn, r["id"]):
            continue
        why = change_review.blocking(conn, r["id"], data_dir)
        if why:
            holds.append({"idx": r["idx"], "scene_id": r["id"], "why": why})
        if on and place_refs.wants_render(conn, pid, data):
            state = None
            if place_refs.missing(conn, data_dir, pid, r["id"], data):
                state = ("chưa có", "chưa có render nền 3D — job sẽ chờ render (Blender, 0 USD)")
            else:
                need = place_refs.needs(data_dir, pid, r["id"])
                bad = place_refs.broken(conn, data_dir, pid, r["id"], data)
                if need:
                    state = ("chờ hướng", need)
                elif bad:
                    state = ("hỏng", bad)
            if r["id"] in gates.get("plates_stale", {}):
                state = ("cũ", gates["plates_stale"][r["id"]]["why"])
            if state:
                plates.append({"idx": r["idx"], "scene_id": r["id"], "state": state[0], "why": state[1]})
    est = cost.estimate_images(pipe, pid, cost.load_pricing(), image_models.of_project(proj), data_dir=data_dir)
    return {"gates": {"block": gates["block"], "warn": gates["warn"]}, "holds": holds, "plates": plates, "estimate": est,
            "estimate_text": cost.format_estimate(est) if est["items"] else "không có ảnh nào phải gen",
            "blocked": bool(gates["block"] or holds or any(p["state"] in ("cũ", "hỏng", "chờ hướng") for p in plates))}


def _print(res: dict) -> None:
    est = res["estimate"]
    print("=== GIÁ (cùng số với nút Gen ảnh + ô 💰 ở Bước 2) ===")
    print("  " + res["estimate_text"])
    for part in est.get("parts") or []:
        usd = "chưa có giá" if part.get("usd") is None else f"{part['usd']:.3f} {est['currency']}"
        print(f"    - {part['label']}: {part.get('count') or '-'} → {usd}")
    print("=== CỔNG NÚT GEN (batch.image_gates) ===")
    for b in res["gates"]["block"]:
        print("  CHẶN:", b)
    for w in res["gates"]["warn"]:
        print("  lưu ý:", w)
    if not res["gates"]["block"] and not res["gates"]["warn"]:
        print("  không có")
    print(f"=== TỔ RÀ SOÁT TÁC ĐỘNG (change_review.blocking, như job gửi) — {len(res['holds'])} shot bị giữ ===")
    for h in res["holds"]:
        print(f"  shot {h['idx']}: {h['why']}")
    print(f"=== NỀN 3D (place_refs / location_pack.stale_plates) — {len(res['plates'])} shot chưa sẵn ===")
    for p in res["plates"]:
        print(f"  shot {p['idx']} [{p['state']}]: {p['why']}")
    print("=== KẾT LUẬN ===")
    print("  " + ("CÒN CHẶN — sửa / render xong rồi mới xin duyệt gen" if res["blocked"] else
                  f"GEN ĐƯỢC — xin duyệt với giá ≈ {est.get('total') or 0:.2f} {est['currency']}"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kiểm trước khi gen ảnh: giá + cổng + Tổ rà soát + nền 3D (0 USD, chỉ đọc)")
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--main", default=r"D:\AI-Video-Pipeline", help="thư mục cài đặt chứa data/ thật")
    ap.add_argument("--payload", action="store_true", help="in thêm gói gửi model từng shot (tools/replay_payload)")
    ap.add_argument("--shot", type=int, help="--payload: chỉ shot này (scenes.idx)")
    ap.add_argument("--width", type=int, default=400, help="--payload: cắt prompt in ra (0 = đủ)")
    ap.add_argument("--json", help="ghi kết quả ra file JSON (ngoài data/ thật)")
    ap.add_argument("--keep", action="store_true", help="giữ thư mục thử (junction vẫn được gỡ)")
    a = ap.parse_args(argv)
    main_dir = os.path.abspath(a.main)
    work = tempfile.mkdtemp(prefix=f"pregen_p{a.project}_")
    envf = rp.env_flags(os.path.join(main_dir, "dashboard.env"))      # cờ FEATURE_ máy chính, như Dashboard chạy
    old_cwd = os.getcwd()
    old_env = {k: os.environ.get(k) for k in ("PIPELINE_DB", "FEATURE_SETTINGS_FILE", *envf)}
    box = None
    try:
        box = rp.build_sandbox(main_dir, a.project, work, {})
        real_settings = os.path.join(work, "data", "feature_settings_real.json")   # cờ THẬT (D6 bật thì giá có D6)
        src = os.path.join(main_dir, "data", "feature_settings.json")
        if os.path.exists(src):
            shutil.copyfile(src, real_settings)
        else:
            with open(real_settings, "w", encoding="utf-8") as f:
                json.dump({}, f)
        os.environ["PIPELINE_DB"] = box["db"]
        os.environ["FEATURE_SETTINGS_FILE"] = real_settings
        os.environ.update(envf)
        os.chdir(work)
        conn = sqlite3.connect(box["db"])
        conn.row_factory = sqlite3.Row
        with rp.WriteGuard(os.path.join(main_dir, "data")):
            res = check(conn, a.project, box["data_dir"])
            payload = None
            if a.payload:
                os.environ["FEATURE_SETTINGS_FILE"] = box["settings"]     # D6 tắt: gói code ghép, không gọi Claude
                payload = rp.replay(conn, a.project, box["data_dir"], a.shot)
        conn.close()
        _print(res)
        if payload is not None:
            print("=== GÓI GỬI MODEL (tools/replay_payload) ===")
            rp._print(payload, a.width)
        if a.json:
            out = dict(res, payload=payload)
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=1, default=str)
            print("đã ghi", a.json)
        return 1 if res["blocked"] else 0
    finally:
        os.chdir(old_cwd)
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for link in (box or {}).get("links", []):
            rp._unlink_dir(link)
        for name in ("assets", "_plates3d"):
            rp._unlink_dir(os.path.join(work, "data", name))
        if not a.keep:
            if any(os.path.exists(os.path.join(work, "data", n)) for n in ("assets", "_plates3d")):
                print("CẢNH BÁO: junction chưa gỡ được — KHÔNG xóa thư mục thử", work, file=sys.stderr)
            else:
                shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
