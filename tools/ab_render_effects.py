"""Đợt 4 (rà soát 01/10): dựng HAI bản của một dự án — có / không 10 hiệu ứng dựng + âm thanh chưa được duyệt — để người dùng xem rồi quyết
từng cờ. 0 USD: chỉ ffmpeg trên máy. Chạy trên BẢN SAO của CSDL và thư mục dự án (bản giao thật và dòng `outputs` của dự án không bị đụng).

  py tools/ab_render_effects.py --project 8 --src D:\\AI-Video-Pipeline --out D:\\AI-Video-Output\\2026-10-01_ab-hieu-ung-8

Ra: <out>/1_KHONG_hieu_ung.mp4 · <out>/2_CO_hieu_ung.mp4 · <out>/BAO_CAO.md (cờ nào thật sự đổi bản dựng: lấy từ manifest của bản "có").
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FLAGS = ("shot_transitions", "impact_shake", "music_breath", "sound_intent", "flashback_fx", "end_hold", "music_fit", "ambience_bed",
         "motion_trim", "shot_color_match")
# which manifest key shows that a flag really changed the cut
EVIDENCE = {"shot_transitions": "shot_transitions", "impact_shake": "shakes", "music_breath": "music_breaths", "sound_intent": "sound_intent",
            "flashback_fx": "flashback_fx", "end_hold": "end_hold", "music_fit": "music_fit", "ambience_bed": "ambience",
            "color_match": "color_match", "shot_color_match": "color_match"}


def read_env_file(path: str) -> dict:
    out = {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.split("#", 1)[0].strip()
    except OSError:
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--src", default=os.path.join(os.path.dirname(__file__), ".."), help="repo root that holds data/manifest.sqlite and data/projects")
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=None, help="scratch folder for the copy (default: <out>/_work, deleted at the end)")
    a = ap.parse_args()
    src = os.path.abspath(a.src)
    out = os.path.abspath(a.out)
    work = os.path.abspath(a.work or os.path.join(out, "_work"))
    os.makedirs(out, exist_ok=True)
    os.makedirs(work, exist_ok=True)

    # 1) copies: the database (sqlite backup API — safe while the dashboard runs) and this project's folder
    db_copy = os.path.join(work, "manifest.sqlite")
    s = sqlite3.connect(f"file:{os.path.join(src, 'data', 'manifest.sqlite')}?mode=ro", uri=True)
    d = sqlite3.connect(db_copy)
    s.backup(d)
    s.close()
    d.close()
    data_copy = os.path.join(work, "projects")
    proj_src = os.path.join(src, "data", "projects", str(a.project))
    proj_dst = os.path.join(data_copy, str(a.project))
    if not os.path.isdir(proj_dst):
        shutil.copytree(proj_src, proj_dst)
    for sub in ("_colour", "_flashback", "_edges", "_music", "_ambience"):          # leftovers of the real render must not leak in
        shutil.rmtree(os.path.join(proj_dst, "output", sub), ignore_errors=True)

    # 2) the other flags as the dashboard has them; the ten vary per variant
    for k, v in read_env_file(os.path.join(src, "dashboard.env")).items():
        if k.startswith("FEATURE_") and k[8:].lower() not in FLAGS:
            os.environ.setdefault(k, v)
    os.environ["PIPELINE_DATA"] = data_copy
    from core import delivery
    from core.db import connect
    from core.pipeline import Pipeline

    report = {}
    for name, value in (("1_KHONG_hieu_ung", "0"), ("2_CO_hieu_ung", "1")):
        for f in FLAGS:
            os.environ["FEATURE_" + f.upper()] = value
        p = Pipeline(connect(db_copy))
        t0 = time.time()
        res = delivery.render(p, a.project, data_copy)
        dest = os.path.join(out, name + ".mp4")
        shutil.copyfile(res["path"], dest)
        man = json.loads(p.conn.execute("SELECT manifest FROM outputs WHERE id=?", (res["output_id"],)).fetchone()[0] or "{}")
        report[name] = {"seconds": res["seconds"], "took": round(time.time() - t0, 1), "manifest": man, "path": dest,
                        "loudness": man.get("loudness")}
        print(f"{name}: {res['seconds']:.1f} s video, {report[name]['took']} s render -> {dest}")

    # 3) report: which flags really changed the cut
    on = report["2_CO_hieu_ung"]["manifest"]
    lines = ["# Dựng 2 bản có / không 10 hiệu ứng", "",
             f"Dự án #{a.project} · 0 USD (ffmpeg trên máy) · dựng trên bản sao, bản giao thật không đổi.", "",
             "| Cờ | Có đổi bản dựng không? | Dấu vết trong manifest bản “có” |", "|---|---|---|"]
    for f in FLAGS:
        key = EVIDENCE.get(f)
        val = on.get(key) if key else None
        if f == "motion_trim":
            changed, note = "xem bằng mắt (cắt đầu/đuôi clip, không ghi manifest)", ""
        else:
            changed = "CÓ" if val else "không (không có chỗ để áp dụng hoặc bị bỏ)"
            note = json.dumps(val, ensure_ascii=False)[:160] if val else ""
        lines.append(f"| `{f}` | {changed} | {note} |")
    lines += ["", "Độ to (LUFS): không hiệu ứng "
              f"{(report['1_KHONG_hieu_ung']['loudness'] or {}).get('lufs')} · có hiệu ứng {(report['2_CO_hieu_ung']['loudness'] or {}).get('lufs')}",
              f"Thời lượng: {report['1_KHONG_hieu_ung']['seconds']:.1f} s · {report['2_CO_hieu_ung']['seconds']:.1f} s", "",
              "Xem 2 file cạnh nhau rồi quyết từng cờ (giữ BẬT / TẮT) ở ⚙ → Hệ thống → 🧪 Tính năng thử."]
    with open(os.path.join(out, "BAO_CAO.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(out, "manifests.json"), "w", encoding="utf-8") as f:
        json.dump({k: v["manifest"] for k, v in report.items()}, f, ensure_ascii=False, indent=1)
    if not a.work:
        shutil.rmtree(work, ignore_errors=True)
    print("Báo cáo:", os.path.join(out, "BAO_CAO.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
