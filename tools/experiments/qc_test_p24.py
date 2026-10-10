"""Thử QC lớp 1 (Claude) trên cảnh 1 #24 sau vẽ lại 10/10 — CHỈ CHẤM + GHI, không apply (không duyệt / vẽ lại / giữ job).

    py <worktree>/tools/experiments/qc_test_p24.py a      # QC nguyên như hệ thống (core.qc_scene.build_request)
    py <worktree>/tools/experiments/qc_test_p24.py b      # + render 3D từng shot + số máy (cao máy vs miệng giếng, khối thay thế)

Chạy từ D:/AI-Video-Pipeline (cần data/ + khóa Claude). Lời gọi qua llm_runner.tagged('qc', 24) → sổ chi. Người dùng duyệt 10/10
(≈ 0,04 + 0,06 USD). Kết quả: data/projects/24/stage_v2/qc_test_<a|b>.json"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core import cost, llm_runner, qc_scene  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402

PID, STORY, DATA = 24, 1, os.path.join("data", "projects")


def _env() -> None:
    if os.path.exists("dashboard.env"):
        for ln in open("dashboard.env", encoding="utf-8"):
            if "=" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.strip().split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def stage_facts(p, frames):
    """(chữ, ảnh) render 3D + số máy cho các shot có stage_camera."""
    imgs = []
    lines = ["# Render nền 3D đã gửi cho model ảnh + số máy (đối chiếu từng K)",
                   "Render 3D là CHUẨN hình học của nơi chốn và góc máy. Giếng trong render là KHỐI THAY THẾ tám cạnh màu đá tối (đúng chỗ + "
                   "cỡ): ảnh phải vẽ thành giếng đá thật, không được giữ nguyên khối phẳng. Với mỗi K: nền + vị trí giếng/tháp có theo render "
                   "không; phần nào của giếng được thấy có hợp với chiều cao máy không (máy thấp hơn miệng giếng thì chỉ thấy thành giếng, "
                   "không thấy lòng giếng)."]
    for k, r in enumerate(frames, 1):
        sc = r["data"].get("stage_camera") or {}
        loc, props = sc.get("location"), sc.get("props") or []
        if not loc:
            continue
        well = next((x for x in props if x.get("kind") == "well"), None)
        if well:
            ground = well["at"][2]
            cam_h = loc[2] - ground
            lines.append(f"- K{k} (shot {r['idx']}): máy cao {cam_h:.2f} m so với mặt đất, ống kính {sc.get('lens')} mm; miệng giếng cao "
                         f"{well['height']:.2f} m → máy {'THẤP hơn' if cam_h < well['height'] else 'cao hơn'} miệng giếng "
                         f"{abs(cam_h - well['height']):.2f} m")
        j = p.conn.execute("SELECT sent_refs FROM jobs WHERE id=?", (r["job_id"],)).fetchone()
        key = next((x.get("plate_key") for x in json.loads(j[0] or "[]") if x.get("role") == "place_render"), None)
        path = os.path.join("data", "_plates3d", "cache", str(key), "plate_lift.png")
        if key and os.path.exists(path):
            imgs.append((path, f"K{k} · render 3D shot {r['idx']}"))
    if imgs:                                       # một tấm ghép (tối đa 12 ảnh mỗi lời gọi), cùng bố cục tấm ghép khung
        from core import layout
        sheet = layout.storyboard(imgs, os.path.join(DATA, str(PID), "stage_v2", "qc_test_renders.png"), cols=3, cell=(384, 683))
        imgs = [("Tấm ghép render nền 3D (đã làm sáng) — cùng thứ tự K với tấm ghép khung:", sheet)]
    return "\n".join(lines), imgs


def main() -> None:
    import argparse
    from core import script_cap
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", default="a", choices=("a", "b"))
    ap.add_argument("--yes", action="store_true", help="gọi Claude thật (thiếu thì chỉ in ước tính)")
    script_cap.add_argument(ap)                           # trần CỨNG (test_script_cap; lần chạy 10/10 thiếu trần — ≈ 0,144 USD)
    a = ap.parse_args()
    mode = a.mode
    _env()
    p = Pipeline(connect(os.path.join("data", "manifest.sqlite")))
    frames = qc_scene.scene_frames(p, PID, STORY, DATA)
    if not frames:
        sys.exit("cảnh chưa đủ khung")
    prompt, images, labels = qc_scene.build_request(p, PID, frames, DATA)
    if mode == "b":
        text, extra = stage_facts(p, frames)
        prompt += "\n\n---\n\n" + text
        images = list(images) + extra
    est = cost.llm_estimate(p.conn, "qc", 1)
    print(f"mode {mode}: {len(frames)} khung (jobs {[r['job_id'] for r in frames]}), {len(images)} ảnh, ước ≈ "
          f"{(est or 0) * cost.LLM_MARGIN:.3f} USD (chưa tính ảnh thêm)")
    if not a.yes:
        print("(chưa gọi — thêm --yes --max-usd <USD>)")
        return
    cap = script_cap.from_args(a, f"qc_test_p24 {mode}").start()
    cap.guard((est or 0) * cost.LLM_MARGIN * 2, "QC cảnh 1")    # ×2: output QC thật ≈ 5k token, ước bảng thấp ≈ 40 % (10/10)
    client = llm_runner.client_from_env(ledger=llm_runner.db_file(p.conn))
    if client is None:
        sys.exit("chưa cấu hình Claude")
    with llm_runner.tagged("qc", PID):
        obj, tin, tout = llm_runner.ask_json(client, prompt, lambda o: qc_scene.validate(o, labels), images)
    out = os.path.join(DATA, str(PID), "stage_v2", f"qc_test_{mode}.json")
    json.dump({"jobs": {lab: r["job_id"] for (_, lab), r in zip(labels, frames)}, "tokens": [tin, tout], "answer": obj},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("tokens", tin, tout, "→", out)


if __name__ == "__main__":
    main()
