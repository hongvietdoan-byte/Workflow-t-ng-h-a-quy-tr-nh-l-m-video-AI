"""Khung chat Kịch bản nhận mọi tệp (người dùng 07/10, Khủng Long Đỏ mục 10 — Đợt 1; cờ `chat_first`).

Ảnh / video / nhạc thả vào chat → code xếp loại 0 USD, KHÔNG gọi model: đuôi tệp + chữ gõ kèm + tên tệp + tên nhân vật/nơi của dự án.
Chắc (`sure`) → gắn ngay vào đúng chỗ cũ (Kho dự án, video ref của cảnh, thư mục nhạc); không chắc → hỏi lại trong chat (luật 3: không
đoán). Tệp chờ nằm trên đĩa (`<data>/<pid>/chat_inbox/`), không trong session: tải lại trang không mất. Mọi chỗ ghi dùng lại hàm cũ
(assets.add_reference_images / add_outfit_images, Pipeline.set_motion_ref_video, thư mục nhạc của music/delivery)."""
import json
import os
import re
import shutil
import subprocess
import time
from typing import Dict, List, Optional

from . import access, assets, chat_refs, delivery, music, script_reader

IMAGE_EXT = ("png", "jpg", "jpeg", "webp")
VIDEO_EXT = ("mp4", "mov", "webm")
AUDIO_EXT = ("mp3", "wav", "m4a")
ACCEPT = tuple(script_reader.SUPPORTED) + IMAGE_EXT + VIDEO_EXT + AUDIO_EXT

ROLES = {"character": "Nhân vật", "outfit": "Trang phục", "location": "Bối cảnh", "prop": "Đạo cụ", "style": "Phong cách hình ảnh",
         "motion_ref": "Tham chiếu động tác cho một cảnh", "video_music": "Lấy tiếng làm nhạc nền",
         "video_music2": "Lấy tiếng làm nhạc đoạn 2", "music": "Nhạc nền", "music2": "Nhạc đoạn 2",
         "script_page": "Ảnh trang kịch bản (đọc chữ, có giá)", "video_ref": "Video tham khảo cho kịch bản"}
# 09/10: script_page = đọc chữ bằng Claude (core.chat_refs.read_page, nút có giá — KHÔNG qua apply); video_ref = tư liệu cho kịch bản.
ROLES_BY_TYPE = {"image": ("character", "outfit", "location", "prop", "style", "script_page"),
                 "video": ("motion_ref", "video_music", "video_music2", "video_ref"),
                 "audio": ("music", "music2")}
NEEDS_NAME = ("character", "location", "prop")
FEATURE = "chat_first"

_W = r"(?<!\w)(?:{})(?!\w)"
_WORDS = {
    "outfit": _W.format("bộ đồ|trang phục|quần áo|outfit|costume|đồ bơi|đồ ngủ"),
    "style": _W.format("phong cách|style|tông màu|mood|màu sắc"),
    "location": _W.format("bối cảnh|địa điểm|cảnh nền|nơi|phòng|location|background|map"),
    "prop": _W.format("đạo cụ|prop|vũ khí|đồ vật"),
    "motion": _W.format("động tác|nhảy|múa|chuyển động|tham chiếu|dance|vũ đạo"),
    "music": _W.format("nhạc|bài hát|music|song|bgm"),
    "part2": _W.format("đoạn 2|đoạn hai|nhạc 2|phần 2|part 2"),
}
_SCENE = re.compile(r"(?<!\w)(?:cảnh|shot|scene)\s*(\d+)", re.I)


def enabled() -> bool:
    from . import features
    return features.on(FEATURE)


def file_type(name: str) -> Optional[str]:
    ext = os.path.splitext(name or "")[1].lower().lstrip(".")
    if ext in script_reader.SUPPORTED:
        return "script"
    for kind, exts in (("image", IMAGE_EXT), ("video", VIDEO_EXT), ("audio", AUDIO_EXT)):
        if ext in exts:
            return kind
    return None


def _has(key: str, text: str) -> bool:
    return re.search(_WORDS[key], text, re.I) is not None


def _name_in(text: str, names: List[str]) -> Optional[str]:
    low = text.lower()
    for n in sorted(names, key=len, reverse=True):              # longest first: "Kelly KL" before "Kelly"
        if n and re.search(_W.format(re.escape(n.lower())), low):
            return n
    return None


def guess(ftype: str, filename: str, text: str, names: List[str], n_scenes: int) -> Dict:
    """What a file probably is — {"role", "name", "who", "scene", "sure", "why"}. `sure` only when nothing is left to choose."""
    words = f"{text or ''} {os.path.splitext(filename or '')[0].replace('_', ' ')}"
    g = {"role": None, "name": None, "who": None, "scene": None, "sure": False, "why": ""}
    if ftype == "image":
        who = _name_in(words, names)
        if _has("outfit", words):
            g.update(role="outfit", who=who, sure=who is not None, why="có chữ trang phục" + (f" + tên {who}" if who else ""))
        elif _has("style", words):
            g.update(role="style", sure=True, why="có chữ phong cách")
        elif _has("prop", words):
            g.update(role="prop", name=who, sure=False, why="có chữ đạo cụ — cần tên")
        elif _has("location", words):
            g.update(role="location", name=who, sure=who is not None, why="có chữ bối cảnh" + (f" + tên {who}" if who else ""))
        elif who:
            g.update(role="character", name=who, sure=True, why=f"có tên {who}")
        else:
            g["why"] = "không có chữ gợi ý"
    elif ftype == "video":
        m = _SCENE.search(words)
        scene = int(m.group(1)) if m and 1 <= int(m.group(1)) <= n_scenes else None
        if _has("music", words) and not _has("motion", words):
            g.update(role="video_music2" if _has("part2", words) else "video_music", sure=True, why="có chữ nhạc")
        elif _has("motion", words) or scene:
            g.update(role="motion_ref", scene=scene, sure=scene is not None,
                     why=f"động tác cho cảnh {scene}" if scene else "động tác — chưa rõ cảnh nào")
        else:
            g["why"] = "không có chữ gợi ý"
    elif ftype == "audio":
        if _has("part2", words):
            g.update(role="music2", sure=True, why="có chữ đoạn 2")
        elif _has("music", words):
            g.update(role="music", sure=True, why="có chữ nhạc")
        else:
            g.update(role="music", why="tệp âm thanh — nhạc nền hay nhạc đoạn 2?")
    return g


def known_names(conn, pid: int) -> List[str]:
    rows = conn.execute("SELECT name FROM characters WHERE project_id=? UNION SELECT a.name FROM assets a JOIN project_assets pa "
                        "ON pa.asset_id=a.id WHERE pa.project_id=? AND a.kind IN ('character','location','prop')", (pid, pid)).fetchall()
    names = [r[0] for r in rows if r[0]]
    for (data,) in conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,)):    # tên trong cảnh đã tách: biết trước khi Director chạy
        try:
            names += [n for n in (json.loads(data or "{}").get("characters") or []) if isinstance(n, str)]
        except ValueError:
            continue
    seen = set()
    return [n for n in names if n and not (n.lower() in seen or seen.add(n.lower()))]


def _dir(data_dir: str, pid: int) -> str:
    d = os.path.join(data_dir, str(pid), "chat_inbox")
    os.makedirs(d, exist_ok=True)
    return d


def _manifest(data_dir: str, pid: int) -> str:
    return os.path.join(_dir(data_dir, pid), "pending.json")


def pending(data_dir: str, pid: int) -> List[Dict]:
    path = _manifest(data_dir, pid)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [it for it in json.load(f) if os.path.exists(it["path"])]


def _save(data_dir: str, pid: int, items: List[Dict]) -> None:
    path = _manifest(data_dir, pid)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    os.replace(path + ".tmp", path)


def receive(p, data_dir: str, pid: int, files: List[tuple], text: str) -> List[Dict]:
    """(name, bytes) of media files → into the inbox, each with its guess. A file type the chat cannot route → ValueError, nothing kept."""
    access.need_edit(p, pid, "thả tệp vào chat Kịch bản")
    bad = [n for n, _ in files if file_type(n) in (None, "script")]
    if bad:
        raise ValueError("Chưa nhận loại tệp này trong chat: " + ", ".join(bad) + " — dùng ảnh (" + ", ".join(IMAGE_EXT) + "), video ("
                         + ", ".join(VIDEO_EXT) + "), nhạc (" + ", ".join(AUDIO_EXT) + ") hoặc tệp kịch bản.")
    names = known_names(p.conn, pid)
    n_scenes = p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (pid,)).fetchone()[0]
    items, now = pending(data_dir, pid), int(time.time() * 1000)
    out = []
    for i, (name, data) in enumerate(files):
        iid = f"{now}_{i}"
        safe = re.sub(r"[^\w.\-]+", "_", os.path.basename(name))[-80:]
        path = os.path.join(_dir(data_dir, pid), f"{iid}_{safe}")
        with open(path, "wb") as f:
            f.write(data)
        ftype = file_type(name)
        g = guess(ftype, name, text, names, n_scenes)
        if len(files) > 1 and g["sure"]:                        # one caption, several files: sure only when the FILE NAME agrees too
            own = guess(ftype, name, "", names, n_scenes)
            if (own["role"], own["name"], own["who"]) != (g["role"], g["name"], g["who"]):
                g.update(sure=False, why=g["why"] + " — nhưng câu ghi chung cho nhiều tệp, tên tệp không khớp")
        it = {**g, "id": iid, "file": name, "path": path, "type": ftype, "text": text or ""}
        items.append(it)
        out.append(it)
    _save(data_dir, pid, items)
    return out


def drop(data_dir: str, pid: int, iid: str) -> None:
    items = pending(data_dir, pid)
    for it in items:
        if it["id"] == iid and os.path.exists(it["path"]):
            os.remove(it["path"])
    _save(data_dir, pid, [it for it in items if it["id"] != iid])


def _extract_audio(src: str, dest_dir: str, stem: str) -> str:
    ff = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg")
    if not ff:
        raise ValueError("Không tìm thấy ffmpeg để tách tiếng từ video — cài ffmpeg (hoặc đặt FFMPEG_PATH) rồi thử lại")
    tmp = os.path.join(os.path.dirname(src), stem + ".m4a")
    r = subprocess.run([ff, "-y", "-v", "error", "-i", src, "-vn", "-c:a", "aac", "-b:a", "192k", tmp], capture_output=True, text=True)
    if r.returncode or not os.path.exists(tmp):
        raise ValueError("Không tách được tiếng từ video: " + ((r.stderr or "").strip()[-200:] or "video không có tiếng?"))
    music.clear_selected(dest_dir)
    dest = os.path.join(dest_dir, stem + ".m4a")
    os.replace(tmp, dest)
    return dest


def apply(p, data_dir: str, pid: int, iid: str, role: str, name: Optional[str] = None, who: Optional[str] = None,
          scene: Optional[int] = None) -> str:
    """Put one waiting file where `role` says (the old functions). Missing answers → ValueError and the file keeps waiting. → a line to say."""
    access.need_edit(p, pid, "gắn tệp từ chat Kịch bản")
    it = next((x for x in pending(data_dir, pid) if x["id"] == iid), None)
    if it is None:
        raise ValueError("Tệp này không còn trong hộp chờ (đã gắn hoặc đã bỏ)")
    if role not in ROLES_BY_TYPE.get(it["type"], ()):
        raise ValueError(f"“{it['file']}” không dùng được làm {ROLES.get(role, role)}")
    if role == "script_page":                                   # tốn tiền: chỉ qua nút có giá (chat_refs.read_page), không gắn chui
        raise ValueError(f"“{it['file']}”: đọc chữ trang kịch bản là nút có giá riêng (📄 Ảnh trang kịch bản) — chưa gọi gì")
    name = " ".join((name or "").split())
    if role in NEEDS_NAME and not name:
        raise ValueError(f"Cho “{it['file']}” một cái tên ({ROLES[role].lower()} nào?)")
    with open(it["path"], "rb") as f:
        data = f.read()
    game = p.project(pid)["game"] or "FF"
    if role in NEEDS_NAME:
        rep = assets.add_reference_images(p.conn, pid, game, role, name, [(it["file"], data)], False, created_by=p.actor)
        msg = f"Đã gắn ảnh “{it['file']}” làm {ROLES[role].lower()} **{name}** (Kho của dự án)"
        if rep["skipped"]:
            msg += " · bỏ qua: " + "; ".join(w for _, w in rep["skipped"])
        else:                                                   # 09/10: cũng là tư liệu cho Biên kịch / Đạo diễn (dạng chữ)
            chat_refs.add(p.conn, pid, role, name, it.get("text") or "", it["file"], None)
    elif role == "outfit":
        label = name or (f"{who} — trang phục" if who else "")
        if not label:
            raise ValueError(f"Trang phục “{it['file']}” của ai? Chọn nhân vật hoặc gõ tên bộ đồ")
        rep = assets.add_outfit_images(p.conn, pid, game, label, [(it["file"], data)], False, character=who, created_by=p.actor)
        msg = f"Đã lưu trang phục **{label}** — {rep['note']}"
    elif role == "style":
        folder = os.path.join(data_dir, str(pid), "style_refs")
        os.makedirs(folder, exist_ok=True)
        n = len(os.listdir(folder)) + 1
        shutil.copyfile(it["path"], os.path.join(folder, f"ref_{n}{os.path.splitext(it['file'])[1].lower() or '.png'}"))
        msg = f"Đã lưu “{it['file']}” làm ảnh phong cách ({n} ảnh) — phân tích bằng Claude là nút có giá riêng"
    elif role == "motion_ref":
        if not scene:
            raise ValueError(f"Video “{it['file']}” là động tác cho cảnh nào?")
        row = p.conn.execute("SELECT s.id, m.id mid FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id "
                             "WHERE s.project_id=? AND s.idx=?", (pid, int(scene))).fetchone()
        if row is None:
            raise ValueError(f"Dự án không có cảnh {scene}")
        if row["mid"] is None:
            raise ValueError(f"Cảnh {scene} chưa có motion prompt (làm ở Storyboard) — video vẫn ở hộp chờ, gắn lại sau")
        folder = os.path.join(data_dir, str(pid), "motion_ref")
        os.makedirs(folder, exist_ok=True)
        dest = os.path.join(folder, f"scene_{int(scene)}_{os.path.basename(it['path'])}")
        shutil.copyfile(it["path"], dest)
        p.set_motion_ref_video(row["id"], dest, "feature")
        msg = f"Đã gắn video “{it['file']}” làm tham chiếu động tác cho **cảnh {scene}** (chỉ lấy chuyển động, không lấy diện mạo)"
    elif role == "video_ref":
        label = name or os.path.splitext(it["file"])[0]
        dest = os.path.join(chat_refs.video_dir(data_dir, pid), os.path.basename(it["path"]))
        shutil.copyfile(it["path"], dest)
        chat_refs.add(p.conn, pid, "video_ref", label, it.get("text") or "", it["file"], dest)
        msg = f"Đã lưu video “{it['file']}” làm **video tham khảo** “{label}” — Biên kịch / Đạo diễn đọc tên + ghi chú (dạng chữ)"
    elif role in ("music", "music2"):
        dest_dir = music.project_dirs(data_dir, pid)[1] if role == "music" else delivery.second_music_dir(data_dir, pid)
        music.clear_selected(dest_dir)
        shutil.copyfile(it["path"], os.path.join(dest_dir, ("selected" if role == "music" else "second") +
                                                  os.path.splitext(it["file"])[1].lower()))
        if role == "music":
            music.set_off(p, pid, False)
        msg = f"Đã dùng “{it['file']}” làm **{ROLES[role].lower()}**"
    else:                                                       # video_music / video_music2
        to_main = role == "video_music"
        dest_dir = music.project_dirs(data_dir, pid)[1] if to_main else delivery.second_music_dir(data_dir, pid)
        _extract_audio(it["path"], dest_dir, "selected" if to_main else "second")
        if to_main:
            music.set_off(p, pid, False)
        msg = f"Đã tách tiếng từ “{it['file']}” làm **{'nhạc nền' if to_main else 'nhạc đoạn 2'}**"
    drop(data_dir, pid, iid)
    return msg


def retry_waiting(p, data_dir: str, pid: int) -> List[str]:
    """Đợt 2: a motion video that waited because its scene had no motion prompt yet is attached as soon as the scene has one (the scene was
    named when it was dropped). Others keep waiting. → the lines to say in the chat."""
    said = []
    for it in pending(data_dir, pid):
        if it.get("role") != "motion_ref" or not it.get("scene"):
            continue
        ready = p.conn.execute("SELECT 1 FROM scenes s JOIN motion_prompts m ON m.scene_id=s.id WHERE s.project_id=? AND s.idx=?",
                               (pid, int(it["scene"]))).fetchone()
        if ready:
            said.append(apply(p, data_dir, pid, it["id"], "motion_ref", scene=it["scene"]))
    return said
