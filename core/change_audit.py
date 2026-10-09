"""Bộ kiểm TÁC ĐỘNG khi đổi đầu vào của một shot (người dùng 10/10 sau đợt vẽ lại #24: "mỗi lần đổi ảnh cần rà soát lại cả các khâu liên
quan, tránh trường hợp tương tự"). 0 USD, chỉ đọc. Chạy TRƯỚC khi gửi vẽ lại một shot đã đổi máy / nền / trang phục / câu tả.

Đợt #24 (job 623–631): đổi máy 3D (stage_camera) nhưng ảnh neo frame 1 CŨ + phiên storyboard chung vẫn gửi kèm → 9/9 ảnh vẽ lại nền cũ;
câu tả yêu nữ chép từ prompt cũ ("black-skinned") → mặt người thay vì mặt nạ đen trơn. Mỗi luật dưới đây là một khâu liên quan:
  nen     nền 3D gửi kèm = render của máy HIỆN TẠI; nền không quá tối so với ảnh khác
  neo     ảnh neo / phiên storyboard không mang khung của máy cũ
  cau     câu tả khung trong prompt khớp máy (cỡ, cúi/ngửa, góc nhìn nhân vật, chuyển động)
  vai     nhân vật trong shot có hồ sơ Kho đủ "must_keep" (không thì câu tả tự chế → lệch trang phục)
  anh     ảnh đang có của shot vẽ trên nền cũ → phải vẽ lại
  video   clip / khung cuối phía sau làm từ ảnh cũ → lỗi thời theo
Mức: "do" = phải sửa trước khi vẽ (vẽ sẽ hỏng / tốn tiền vô ích); "vang" = nên xem. Thêm khâu mới → thêm luật ở đây.
  py -m core.change_audit --db data/manifest.sqlite --data data/projects --pid 24 [--shots 2,9]
"""
import json
import os
import re
from typing import Dict, List, Optional

SIZE_WORDS = {"EWS": ("extreme wide",), "WS": ("wide shot", "wide"), "GAME_TPS": ("third-person", "wide"), "MLS": ("medium long", "medium full",
              "full body", "medium shot"), "MS": ("medium shot", "medium"), "MCU": ("medium close", "close-up"), "CU": ("close-up", "close up"),
              "ECU": ("extreme close",)}
DOWN_WORDS = ("high", "looking down", "from above", "top-down", "overhead", "down at", "down into", "slightly down")
UP_WORDS = ("low", "looking up", "from below", "up at", "slightly up", "close to the ground")


def _plate_rec(data_dir: str, pid: int, scene_id: int) -> Optional[Dict]:
    try:
        ix = json.load(open(os.path.join(data_dir, str(pid), "plates", "index.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return ix.get(str(scene_id))


def _brightness(path: str) -> Optional[float]:
    try:
        from PIL import Image, ImageStat
        return ImageStat.Stat(Image.open(path).convert("L")).mean[0]
    except Exception:  # noqa: BLE001
        return None


def audit_shot(conn, data_dir: str, pid: int, scene_id: int) -> List[Dict]:
    from . import features, place_refs, plate_camera, scene_storyboard
    row = conn.execute("SELECT idx, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return [{"muc": "do", "khau": "shot", "msg": f"không có shot id {scene_id}"}]
    idx, data = row[0], json.loads(row[1] or "{}")
    out: List[Dict] = []

    def say(level, khau, msg):
        out.append({"shot": idx, "muc": level, "khau": khau, "msg": msg})
    sc = data.get(plate_camera.STAGE_FIELD)
    locked = bool(sc) and features.on("stage_camera")
    if sc and not features.on("stage_camera"):
        say("do", "nen", "shot có máy Sân khấu 3D (stage_camera) nhưng cờ stage_camera TẮT → nền dựng bằng máy cũ")
    rec = _plate_rec(data_dir, pid, scene_id)
    if locked:
        cp = (rec or {}).get("camera_plan") or {}
        if not rec or [round(v, 2) for v in cp.get("location", [])] != [round(v, 2) for v in sc["location"]]:
            say("do", "nen", "render nền 3D chưa theo máy hiện tại (render lại: location_pack render)")
        elif sc.get("props") and cp.get("props") != sc.get("props"):
            say("do", "nen", "khối đạo cụ thay thế trong nền khác dàn cảnh hiện tại → render lại")
        b = _brightness(rec["plate"]) if rec and rec.get("plate") else None
        if b is not None and b < place_refs.LIFT_BELOW:
            sent = place_refs.lifted(rec["plate"])
            b2 = _brightness(sent)
            say("vang" if sent != rec["plate"] and (b2 or 0) >= place_refs.LIFT_BELOW else "do", "nen",
                f"nền tối {b:.0f}/255 → gửi bản làm sáng {b2 and round(b2)}/255")
    g = scene_storyboard.group_of(conn, pid, scene_id) if scene_storyboard.enabled() else None
    if g:
        is_anchor = g["anchor"]["id"] == scene_id
        if locked and not is_anchor and not scene_storyboard.own_camera(g, scene_id):
            say("do", "neo", "shot có máy riêng nhưng vẫn nhận ảnh neo frame 1 + phiên storyboard chung → nền bị kéo về khung cũ")
        if not is_anchor and scene_storyboard.uses_anchor(g, scene_id):
            pic = scene_storyboard.anchor_picture(conn, data_dir, pid, g["anchor"]["id"])
            arec = _plate_rec(data_dir, pid, g["anchor"]["id"])
            if pic and arec and not _drawn_on(conn, pic, arec.get("key")):
                say("do", "neo", f"ảnh neo {os.path.basename(pic)} vẽ trên nền CŨ của shot neo → vẽ lại shot neo trước")
    text = str(data.get("image_prompt") or "").lower()
    if sc and text:
        if sc.get("pov") and not re.search(r"point[- ]of[- ]view|\bpov\b", text):
            say("do", "cau", f"máy là góc nhìn của {sc['pov']} nhưng prompt không nói 'point-of-view'")
        cp = (rec or {}).get("camera_plan") or {}
        loc, aim = sc["location"], sc["look_at"]
        import math
        pitch = math.degrees(math.atan2(aim[2] - loc[2], math.hypot(aim[0] - loc[0], aim[1] - loc[1])))
        if pitch <= -15 and not any(w in text for w in DOWN_WORDS):
            say("do", "cau", f"máy cúi {pitch:.0f}° nhưng prompt không tả nhìn xuống (high / looking down …)")
        if pitch >= 10 and not any(w in text for w in UP_WORDS):
            say("vang", "cau", f"máy ngửa {pitch:.0f}° nhưng prompt không tả nhìn lên")
        size = data.get("size")
        if size in SIZE_WORDS and not any(w in text for w in SIZE_WORDS[size]):
            say("vang", "cau", f"cỡ {size} nhưng câu đầu prompt không nói cỡ tương ứng")
    if sc and sc.get("move") and data.get("camera_move") in (None, "static"):
        say("do", "cau", f"máy chuyển động ({sc['move'].get('kieu')}) nhưng camera_move = {data.get('camera_move')}")
    if data.get("camera_move") == "pull_out" and not ((data.get("motion_en") or {}).get("end_state") or data.get("end_state")):
        say("do", "cau", "pull_out mà chưa tả khung cuối (end_state) — motion_prompt_lint sẽ chặn")
    for name in data.get("characters") or []:
        r = conn.execute("SELECT id, profile FROM assets WHERE kind='character' AND upper(name)=upper(?)", (name,)).fetchone()
        if r is None:
            say("vang", "vai", f"'{name}' không có trong Kho")
            continue
        prof = json.loads(r[1] or "{}")
        if not (prof.get("must_keep") or "").strip():
            say("vang", "vai", f"hồ sơ Kho #{r[0]} '{name}' thiếu must_keep → câu tả trang phục tự chế, dễ lệch")
    creature = re.search(r"creature|demoness|yêu nữ", text)
    if creature and text and "featureless" not in text and "mask" not in text and "faceless" in text and "skin" in text:
        say("vang", "vai", "tả yêu nữ 'faceless … skin' dễ ra mặt người da sẫm — Kho: mặt đen trơn như mặt nạ, chỉ hai mắt đỏ")
    img = conn.execute("SELECT j.id, j.sent_refs FROM jobs j WHERE j.scene_id=? AND j.type='image_gen' AND j.state='succeeded' "
                       "ORDER BY j.id DESC LIMIT 1", (scene_id,)).fetchone()
    if img and rec:
        keys = [r.get("plate_key") for r in json.loads(img[1] or "[]") if r.get("role") == "place_render"]
        if keys and rec.get("key") not in keys:
            say("do", "anh", f"ảnh mới nhất (job {img[0]}) vẽ trên nền cũ → cần vẽ lại")
    if img:
        vids = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='video_gen' AND state='succeeded' AND id < ?",
                            (scene_id, img[0])).fetchall()
        if vids:
            say("vang", "video", f"{len(vids)} clip làm từ ảnh trước job {img[0]} → lỗi thời khi duyệt ảnh mới")
    return out


def _drawn_on(conn, pic: str, key: Optional[str]) -> bool:
    m = re.search(r"job_(\d+)", os.path.basename(pic))
    if not m or not key:
        return True
    row = conn.execute("SELECT sent_refs FROM jobs WHERE id=?", (int(m.group(1)),)).fetchone()
    keys = [r.get("plate_key") for r in json.loads((row[0] if row else None) or "[]") if r.get("role") == "place_render"]
    return not keys or key in keys


def audit(conn, data_dir: str, pid: int, shots: Optional[List[int]] = None) -> List[Dict]:
    rows = conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    out = []
    for sid, idx in rows:
        if shots is None or idx in shots:
            out += audit_shot(conn, data_dir, pid, sid)
    return out


if __name__ == "__main__":
    import argparse
    import sqlite3
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--data", required=True, help="thư mục dự án (data/projects)")
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--shots", default=None)
    a = ap.parse_args()
    conn = sqlite3.connect(f"file:{os.path.abspath(a.db)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    res = audit(conn, a.data, a.pid, [int(x) for x in a.shots.split(",")] if a.shots else None)
    for r in res:
        print(f"shot {r['shot']} [{r['muc'].upper()}] {r['khau']}: {r['msg']}")
    print(f"{sum(1 for r in res if r['muc'] == 'do')} mục ĐỎ, {sum(1 for r in res if r['muc'] == 'vang')} mục vàng")
