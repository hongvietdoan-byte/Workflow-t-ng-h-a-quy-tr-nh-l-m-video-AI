"""Thử Cách 1 (người dùng duyệt 17/10): tách shot 15 cảnh 4 #31 (Kelly chạy hạ 3 địch) thành 3 shot, mỗi shot MỘT lần gặp + hạ MỘT địch,
để dàn sân khấu giữ địch ở đúng ngả (luật 'mọi nhân vật vào khung' thỏa mà địch không dịch chuyển). Chạy trên DỰ ÁN THỬ (nhân bản #31, chỉ
giữ cảnh 4), KHÔNG đụng #31. So với Cách 2 (previs Blender làm ref V2V — phiên khác) ở khâu video nháp.

    py tools/experiments/split_shot15_trial.py setup     dự án thử (0 USD) — in mã dự án
    py tools/experiments/split_shot15_trial.py show N    in các shot của dự án thử

Chạy từ D:\\AI-Video-Pipeline.

BỎ DỞ 17/10 (người dùng bật chế độ siêu nhanh tập 2 — TODO mục BÀN GIAO): CHƯA chạy lần nào, chưa có dự án thử. Lưu để tham khảo nếu làm
lại. `setup` GHI CSDL (nhân bản dự án) → chỉ chạy khi PIPELINE_DB trỏ tới BẢN SAO (chặn ở dưới; lần thử 17/10 bị hệ thống chặn ghi CSDL thật)."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

NAME = "Thử tách shot 15 cảnh 4 thành 3 shot (17/10)"
SOURCE, STORY_SCENE, SPLIT_IDX = 31, 4, 15
# (tên địch, chỗ đứng Kho, mô tả trong ảnh, thời lượng giây) — tổng 7,0 s như shot gốc
PARTS = [
    ("Lính địch áo choàng", "me_cung_nga_re_bac", "a figure in a long black leather cloak with a dark red hood", 2.4),
    ("Yêu nữ tà linh dạng 1", "me_cung_loi_vao_dong", "a ragged-dressed figure", 2.3),
    ("Sứ giả bóng đêm", "me_cung_nga_re_nam", "a masked figure", 2.3),
]


def _p():
    from tools.experiments.group_test import load_env
    load_env(os.getcwd())
    from core.db import connect
    from core.pipeline import Pipeline
    return Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))


def split_row(base: dict, k: int) -> dict:
    """Bản shot gốc → phần k (0..2): Kelly + một địch."""
    name, spot, look, dur = PARTS[k]
    d = copy.deepcopy(base)
    d["characters"] = ["Kelly", name]
    d["plate_spot"] = spot
    d["duration_s"] = dur
    d["action"] = f"Kelly chạy lướt tới và áp sát, hạ gục {name} bằng khẩu SKORP tỏa hào quang đỏ"
    d["image_prompt"] = ("Free Fire in-game 3D render, stylized proportions, moderate texture detail, clear gameplay lighting, everything in "
                         "focus. Third-person gameplay camera behind and above Kelly's right shoulder, following her through narrow trimmed "
                         "hedge corridors at night, cold purple-red moonlight, thin ground fog. Kelly, in her translucent purple-blue ghost "
                         "form with a red outline, is captured mid-stride, crouched low, her glowing SKORP raised in both hands with a faint "
                         f"red aura pulsing along the barrel. Ahead at the corridor fork, {look} is caught mid-fall, only partly visible in "
                         "the hedge shadow. Hedge walls fill both sides of the frame, trimmed green dusted with fog at the base.")
    d["end_state"] = f"Kelly runs on past {name}, who collapses out of frame behind her"
    d["dialogue"] = base.get("dialogue") if k == 0 else []
    d["text"] = d["action"] + ("\n" + "\n".join(f"{x['speaker']}: {x['text']}" for x in d["dialogue"]) if d["dialogue"] else "")
    d["continuous_with_next"] = True
    d["why"] = (f"[thử 17/10] shot 15 gốc tách 3 phần để địch đứng đúng ngả; phần {k + 1}/3 — {name}. " + str(base.get("why") or ""))
    for key in ("stage_camera", "stage_segment"):
        d.pop(key, None)
    return d


def setup(p):
    from core import compare
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return row["id"]
    pid = compare.clone_project(p, SOURCE, NAME)
    rows = [(r["id"], r["idx"], json.loads(r["data"] or "{}")) for r in
            p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]
    keep = [r for r in rows if r[2].get("story_scene") == STORY_SCENE]
    for sid, _idx, _d in rows:
        if sid not in {k[0] for k in keep}:
            p.conn.execute("DELETE FROM scenes WHERE id=?", (sid,))
    p.conn.execute("DELETE FROM story_scenes WHERE project_id=? AND idx<>?", (pid, STORY_SCENE))
    # dựng lại danh sách: shot gốc 15 → 3 phần; idx liên tiếp từ idx đầu của cảnh 4
    out = []
    for sid, idx, d in keep:
        if idx == SPLIT_IDX:
            out += [("split", sid, idx, split_row(d, k), k) for k in range(len(PARTS))]
        else:
            out.append(("keep", sid, idx, d, 0))
    start = keep[0][1]
    p.conn.execute("UPDATE scenes SET idx=idx+1000 WHERE project_id=?", (pid,))    # nhường chỗ để đánh số lại không đụng UNIQUE
    title = next(r for r in p.conn.execute("SELECT title FROM scenes WHERE id=?", (keep[0][0],)))
    shot_no = 0
    for n, (kind, sid, idx, d, k) in enumerate(out):
        shot_no += 1
        d["shot_no"] = shot_no
        d["sequence"] = shot_no
        for key in ("stage_camera", "stage_segment"):
            d.pop(key, None)
        data = json.dumps(d, ensure_ascii=False)
        if kind == "keep" or k == 0:
            p.conn.execute("UPDATE scenes SET idx=?, data=?, title=? WHERE id=?", (start + n, data, p.conn.execute(
                "SELECT title FROM scenes WHERE id=?", (sid,)).fetchone()["title"].rsplit("· shot", 1)[0] + f"· shot {shot_no}", sid))
        else:
            p.conn.execute("INSERT INTO scenes (project_id, idx, title, state, data) VALUES (?,?,?,?,?)",
                           (pid, start + n, title["title"].rsplit("· shot", 1)[0] + f"· shot {shot_no}", "ready", data))
    p.conn.commit()
    print("dự án thử:", pid, "·", len(out), "shot")
    return pid


def show(p, pid):
    for r in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)):
        d = json.loads(r["data"] or "{}")
        print(r["idx"], d.get("shot_no"), d.get("duration_s"), d.get("characters"), d.get("plate_spot"), "|", str(d.get("action"))[:70])


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    pp = _p()
    if cmd == "setup":
        db = os.path.abspath(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite"))
        if db.lower() == os.path.abspath(os.path.join("data", "manifest.sqlite")).lower():
            sys.exit("Từ chối: setup ghi CSDL — đặt PIPELINE_DB=<bản sao manifest.sqlite> (không chạy trên CSDL thật)")
        show(pp, setup(pp))
    elif cmd == "show":
        show(pp, int(sys.argv[2]))
    else:
        print(__doc__)
