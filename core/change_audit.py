"""Bộ kiểm TÁC ĐỘNG khi đổi đầu vào của một shot (người dùng 10/10 sau đợt vẽ lại #24: "mỗi lần đổi ảnh cần rà soát lại cả các khâu liên
quan, tránh trường hợp tương tự"). 0 USD, chỉ đọc. Chạy TRƯỚC khi gửi vẽ lại một shot đã đổi máy / nền / trang phục / câu tả.

Đợt #24 (job 623–631): đổi máy 3D (stage_camera) nhưng ảnh neo frame 1 CŨ + phiên storyboard chung vẫn gửi kèm → 9/9 ảnh vẽ lại nền cũ;
câu tả yêu nữ chép từ prompt cũ ("black-skinned") → mặt người thay vì mặt nạ đen trơn. Mỗi luật dưới đây là một khâu liên quan:
  nen     nền 3D gửi kèm = render của máy HIỆN TẠI; nền không quá tối so với ảnh khác
  neo     ảnh neo / phiên storyboard không mang khung của máy cũ
  cau     câu tả khung trong prompt khớp máy (cỡ, cúi/ngửa, góc nhìn nhân vật, chuyển động); câu Director trái sự thật hình học (core/stage_facts,
          vd "its dark mouth facing us" khi máy thấp hơn miệng giếng) → đỏ + `de_xuat` câu đúng (không tự sửa chữ Director)
  vai     nhân vật trong shot có hồ sơ Kho đủ "must_keep" (không thì câu tả tự chế → lệch trang phục)
  anh     ảnh đang có của shot vẽ trên nền cũ → phải vẽ lại
  video   clip / khung cuối phía sau làm từ ảnh cũ → lỗi thời theo
Mức: "do" = phải sửa trước khi vẽ (vẽ sẽ hỏng / tốn tiền vô ích); "vang" = nên xem. Thêm khâu mới → thêm luật ở đây.
  py -m core.change_audit --db data/manifest.sqlite --data data/projects --pid 24 [--shots 2,9]
"""
import json
import os
import re
import sqlite3
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


def _audit_columns(conn, table):
    # Tên bảng chỉ do caller nội bộ truyền, không từ dữ liệu người dùng.
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _audit_rows(conn, sql, params=()):
    cursor = conn.execute(sql, params)
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor]


def _unique_role_match(pool, name):
    """Giữ matching có dấu/alias của before_run, nhưng không chọn first khi trùng."""
    from . import before_run
    exact = [a for a in pool if before_run._key(name) in {before_run._key(n) for n in before_run._names(a)}]
    matches = exact or [a for a in pool if before_run._match([a], name) is not None]
    return (matches[0], None) if len(matches) == 1 else (None, "có nhiều hồ sơ Kho trùng tên/alias; chọn lại liên kết nhân vật" if matches else None)


def _role_asset(conn, pid, name):
    """Hồ sơ vai theo lựa chọn đã lưu, độc lập ảnh; chỉ đọc, không tự sửa link."""
    from . import before_run
    try:
        columns = _audit_columns(conn, "characters")
        saved = []
        if {"project_id", "name"} <= columns:
            saved = [r for r in _audit_rows(conn, "SELECT * FROM characters WHERE project_id=?", (pid,))
                     if before_run._key(r["name"]) == before_run._key(name)]
            if len(saved) > 1:
                return None, "có nhiều nhân vật cùng tên trong dự án; cần chọn lại liên kết Kho"
        elif columns:
            return None, "bảng nhân vật thiếu tên hoặc project_id; không xác minh được liên kết Kho"
        asset_columns = _audit_columns(conn, "assets")
        if not {"id", "kind", "name", "profile"} <= asset_columns:
            return None, "không đọc được hồ sơ Kho: bảng assets thiếu trường bắt buộc"
        selected = saved[0].get("ref_asset_id") if saved else None
        if selected is not None:
            if type(selected) is not int or selected <= 0:
                return None, "ref_asset_id đã lưu không hợp lệ hoặc đã chọn không dùng ảnh; cần chọn lại hồ sơ Kho"
            candidates = _audit_rows(conn, "SELECT * FROM assets WHERE id=?", (selected,))
            if len(candidates) != 1:
                return None, f"liên kết Kho #{selected} không tồn tại hoặc không duy nhất; cần chọn lại hồ sơ"
            asset = candidates[0]
            if asset["kind"] not in ("character", "pet") or asset.get("project_id") not in (None, pid):
                return None, f"liên kết Kho #{selected} sai loại vai hoặc thuộc dự án khác; cần chọn lại hồ sơ"
            return asset, None
        # Chỉ link NULL hoặc schema cũ thiếu link mới được dò tên. Không đòi ảnh.
        people = [r for r in _audit_rows(conn, "SELECT * FROM assets WHERE kind IN ('character','pet')")
                  if r.get("project_id") in (None, pid)]
        if {"project_id", "asset_id"} <= _audit_columns(conn, "project_assets"):
            chosen = {r[0] for r in conn.execute("SELECT asset_id FROM project_assets WHERE project_id=?", (pid,))}
            match, problem = _unique_role_match([r for r in people if r["id"] in chosen], name)
            if match is not None or problem:
                return match, problem
        return _unique_role_match(people, name)
    except (sqlite3.Error, TypeError, ValueError):
        return None, "không đọc được liên kết nhân vật/hồ sơ Kho; kiểm tra cấu trúc dữ liệu"


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
        # 17/10 (#31 shot 20–25, 33): ONE definition of "old background" with the render step and the runner's hold —
        # location_pack.stale_plates (plan key + render_moved); before, this compared stage_camera with the index on its own and
        # called 7 renders old that `location_pack render` (ensure_plates) reused
        from . import location_pack
        st = None
        if rec and not (rec.get("failed") or rec.get("needs")):   # only asked when a usable render exists (the one case it decides)
            try:
                prow = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
                st = location_pack.stale_plate(conn, pid, data_dir, scene_id, place_refs.resolution_of(prow)) if prow else None
            except Exception as e:  # noqa: BLE001 - said, never silently passed (an old/partial database has no projects table)
                say("vang", "nen", f"không so được nền 3D với kế hoạch ({type(e).__name__}: {e})")
        if not rec:
            say("do", "nen", "render nền 3D chưa theo máy hiện tại — chưa có render (tự render khi gửi / location_pack render, 0 USD)")
        elif rec.get("failed") or rec.get("needs"):
            say("do", "nen", f"nền 3D chưa dùng được: {str(rec.get('failed') or rec.get('needs'))[:200]}")
        elif st:
            say("do", "nen", f"render nền 3D chưa theo máy hiện tại: {st['why']}")
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
    if locked and text:                    # 10/10 (#24 shot 4): câu Director trái sự thật hình học (core/stage_facts) — không tự sửa chữ
        from . import stage_facts
        facts = stage_facts.for_shot(conn, pid, data)["facts"]
        for c in stage_facts.prompt_contradictions(data, facts):       # 11/10: cả blocking / action_peak (runner nối vào prompt ảnh)
            where = "" if c["field"] == "image_prompt" else f" (trường {c['field']})"
            out.append({"shot": idx, "muc": c["level"], "khau": "cau",
                        "msg": f"câu Director trái sự thật hình học {c['fact']}{where}: \"{c['phrase']}\" (máy Sân khấu 3D tính khác)",
                        "de_xuat": f"Bỏ cụm \"{c['phrase']}\"; câu đúng: {c['fix']}"})
    if sc and sc.get("move") and data.get("camera_move") in (None, "static"):
        say("do", "cau", f"máy chuyển động ({sc['move'].get('kieu')}) nhưng camera_move = {data.get('camera_move')}")
    if data.get("camera_move") == "pull_out" and not ((data.get("motion_en") or {}).get("end_state") or data.get("end_state")):
        say("do", "cau", "pull_out mà chưa tả khung cuối (end_state) — motion_prompt_lint sẽ chặn")
    from . import speaker_lint
    for name in data.get("characters") or []:
        if not isinstance(name, str) or not name.strip() or speaker_lint.is_narrator(name):   # giọng dẫn không phải người trong Kho
            continue
        r, problem = _role_asset(conn, pid, name)
        if problem:
            say("vang", "vai", f"'{name}': {problem}")
            continue
        if r is None:
            say("vang", "vai", f"'{name}' không có trong Kho")
            continue
        try:
            def invalid_constant(_):
                raise ValueError("profile JSON không hợp lệ")
            prof = json.loads(r["profile"] or "{}", parse_constant=invalid_constant)
            if not isinstance(prof, dict) or (prof.get("must_keep") is not None and not isinstance(prof["must_keep"], str)):
                raise ValueError("profile sai cấu trúc")
        except (TypeError, ValueError):
            say("vang", "vai", f"hồ sơ Kho #{r['id']} '{name}' lỗi JSON/cấu trúc; mở Kho sửa hồ sơ chuẩn")
            continue
        if not (prof.get("must_keep") or "").strip():
            say("vang", "vai", f"hồ sơ Kho #{r['id']} '{name}' thiếu must_keep → câu tả trang phục tự chế, dễ lệch")
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
        if r.get("de_xuat"):
            print(f"    → đề xuất: {r['de_xuat']}")
    print(f"{sum(1 for r in res if r['muc'] == 'do')} mục ĐỎ, {sum(1 for r in res if r['muc'] == 'vang')} mục vàng")
