"""The person's own sound library (music and sound effects) that the video steps can pick from.

Folders of audio files (for example a synced Google Drive folder) are registered as *sources*. A scan only lists the files
(names, folders, sizes: no file is opened, so a 2.5 GB folder is ready in a second); the length of a track is measured the first
time it is needed. Each track is labelled from its folder:

  kind  music (background tracks) or sfx (short effects), from folder / file words and, failing that, from the file size;
  mood  vui vẻ, sôi động, kịch tính, hài, buồn, thư giãn ... when the folder name says so ("nhạc nền kịch tính").

Uses: search and preview in Step 5, "use as the background music", "add as a sound effect at second N", and - when the project
asks for it - the automatic mode picks a background track that matches the scene moods, at no credit cost.
"""
import os
import re
import shutil
from typing import Dict, List, Optional

from . import ffmpeg_studio
from .assets import fold

AUDIO_EXT = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac")
KINDS = {"music": "Nhạc nền", "sfx": "Hiệu ứng âm thanh"}
DEFAULT_IGNORE = "trash, backup, old"
MUSIC_WORDS = ("nhac", "music", "macleod", "bgm", "theme", "song", "ost", "soundtrack")
SFX_WORDS = ("fx", "sfx", "swoosh", "whoosh", "dap dat", "roi do", "popup", "ngoai canh", "hieu ung", "impact", "hit", "click", "trailer")
MOODS = {"vui vẻ": ("vui ve", "nang luong", "happy", "fun", "tuoi sang"),
         "sôi động": ("soi dong", "energetic", "hype", "action", "nhanh"),
         "kịch tính": ("kich tinh", "dramatic", "epic", "tension", "hung trang", "trailer"),
         "hài": ("hai", "comedy", "funny", "hai huoc"),
         "buồn": ("buon", "sad", "cam dong"),
         "thư giãn": ("thu gian", "chill", "relax", "lofi", "binh yen")}
# words a scene's "mood" field may use -> the library mood they call for
SCENE_MOODS = {"kịch tính": ("cang thang", "hoi hop", "kich tinh", "tension", "dramatic", "epic", "hung trang", "u am", "dark", "nguy hiem",
                             "gay can", "bi an", "lanh"),
               "sôi động": ("hanh dong", "action", "soi dong", "nhanh", "energetic", "chien dau", "doi khang", "ruot duoi"),
               "vui vẻ": ("vui", "happy", "tuoi", "bright", "hao hung", "am ap", "hy vong"),
               "hài": ("hai", "funny", "comedy", "tinh nghich"),
               "buồn": ("buon", "sad", "xuc dong", "mat mat", "co don"),
               "thư giãn": ("binh yen", "thu gian", "calm", "peace", "nhe nhang", "yen tinh")}


class SoundError(Exception):
    """A message that can be shown to the person."""


def _words(text: str) -> List[str]:
    return [fold(w) for w in re.split(r"[,;\n]+", text or "") if fold(w)]


def _has(padded: str, keys) -> bool:
    return any(" " + k + " " in padded for k in keys)


def classify(category: str, name: str, size: int) -> tuple:
    """(kind, mood) of a track from its folder path and file name."""
    path = " " + fold(re.sub(r"[_\-\.]+", " ", category + " " + name)) + " "
    mood = next((m for m, keys in MOODS.items() if _has(path, keys)), "")
    if _has(path, SFX_WORDS):
        return "sfx", mood
    if _has(path, MUSIC_WORDS):
        return "music", mood
    return ("music" if size > 2_500_000 else "sfx"), mood


def moods_of_text(text: str) -> List[str]:
    """Library moods that a scene mood text ('căng thẳng, u ám') calls for, strongest first."""
    padded = " " + fold(re.sub(r"[_\-\.,;/]+", " ", text or "")) + " "
    scored = [(sum(padded.count(" " + k + " ") for k in keys), m) for m, keys in SCENE_MOODS.items()]
    return [m for n, m in sorted(scored, key=lambda x: -x[0]) if n]


# ---- sources and scanning ---------------------------------------------------------------------------------------------
def _audio_files(folder: str, ignore: List[str]):
    for dirpath, dirnames, names in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if not any(" " + w + " " in " " + fold(re.sub(r"[_\-\.]+", " ", d)) + " " for w in ignore))
        for n in sorted(names):
            if n.lower().endswith(AUDIO_EXT) and not n.startswith("."):
                yield dirpath, n


def folder_signature(folder: str) -> str:
    count = size = newest = 0
    for dirpath, n in _audio_files(folder, []):
        try:
            st = os.stat(os.path.join(dirpath, n))
        except OSError:
            continue
        count += 1
        size += st.st_size
        newest = max(newest, int(st.st_mtime))
    return f"{count}:{size}:{newest}"


def add_source(conn, path: str, ignore: str = DEFAULT_IGNORE, auto: bool = True) -> int:
    path = os.path.abspath((path or "").strip().strip('"'))
    if not os.path.isdir(path):
        raise SoundError("Không tìm thấy thư mục này trên máy chạy Dashboard")
    if conn.execute("SELECT 1 FROM sound_sources WHERE path=?", (path,)).fetchone():
        raise SoundError("Thư mục này đã có trong danh sách")
    cur = conn.execute("INSERT INTO sound_sources (path, ignore, auto) VALUES (?,?,?)", (path, ignore.strip(), 1 if auto else 0))
    conn.commit()
    return cur.lastrowid


def list_sources(conn) -> List[Dict]:
    out = []
    for r in conn.execute("SELECT * FROM sound_sources ORDER BY id").fetchall():
        d = dict(r)
        d["tracks"] = conn.execute("SELECT COUNT(*) FROM sounds WHERE source_id=?", (r["id"],)).fetchone()[0]
        out.append(d)
    return out


def set_source(conn, source_id: int, ignore: str, auto: bool) -> None:
    conn.execute("UPDATE sound_sources SET ignore=?, auto=? WHERE id=?", (ignore.strip(), 1 if auto else 0, source_id))
    conn.commit()


def remove_source(conn, source_id: int) -> None:
    conn.execute("DELETE FROM sounds WHERE source_id=?", (source_id,))
    conn.execute("DELETE FROM sound_sources WHERE id=?", (source_id,))
    conn.commit()


def scan(conn, source_id: int) -> Dict:
    """List a source's audio files into the library (names and file info only). Returns counts."""
    src = conn.execute("SELECT * FROM sound_sources WHERE id=?", (source_id,)).fetchone()
    if src is None:
        raise SoundError("Không có nguồn này")
    root = src["path"]
    if not os.path.isdir(root):
        raise SoundError("Không truy cập được thư mục (ổ đĩa/Drive chưa kết nối?)")
    rep = {"added": 0, "changed": 0, "unchanged": 0, "removed": 0}
    seen = set()
    for dirpath, n in _audio_files(root, _words(src["ignore"])):
        path = os.path.join(dirpath, n)
        try:
            st = os.stat(path)
        except OSError:
            continue
        seen.add(path)
        rel = os.path.relpath(dirpath, root)
        category = "" if rel == "." else rel.replace(os.sep, " / ")
        name = os.path.splitext(n)[0]
        kind, mood = classify(category, name, st.st_size)
        row = conn.execute("SELECT id, size, mtime FROM sounds WHERE path=?", (path,)).fetchone()
        search = fold(f"{name} {category} {mood}")
        if row is None:
            conn.execute("INSERT INTO sounds (source_id, path, name, category, kind, mood, search, ext, size, mtime) VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (source_id, path, name, category, kind, mood, search, os.path.splitext(n)[1].lower(), st.st_size, int(st.st_mtime)))
            rep["added"] += 1
        elif row["size"] != st.st_size or row["mtime"] != int(st.st_mtime):
            conn.execute("UPDATE sounds SET name=?, category=?, kind=?, mood=?, search=?, size=?, mtime=?, duration=NULL WHERE id=?",
                         (name, category, kind, mood, search, st.st_size, int(st.st_mtime), row["id"]))
            rep["changed"] += 1
        else:
            rep["unchanged"] += 1
    for r in conn.execute("SELECT id, path FROM sounds WHERE source_id=?", (source_id,)).fetchall():
        if r["path"] not in seen:
            conn.execute("DELETE FROM sounds WHERE id=?", (r["id"],))
            rep["removed"] += 1
    summary = ", ".join(f"{v} {label}" for k, label in (("added", "thêm"), ("changed", "đổi"), ("removed", "không còn")) if (v := rep[k])) \
        or "không có gì thay đổi"
    conn.execute("UPDATE sound_sources SET last_sync=datetime('now'), last_signature=?, last_summary=? WHERE id=?",
                 (folder_signature(root), f"{summary} · {len(seen)} bản", source_id))
    conn.commit()
    return rep


def auto_scan(conn) -> List[int]:
    """Re-scan every 'auto' source whose folder changed. Never raises (a Drive that is not connected is just noted)."""
    done = []
    for src in list_sources(conn):
        if not src["auto"]:
            continue
        try:
            if folder_signature(src["path"]) == src["last_signature"] and os.path.isdir(src["path"]):
                continue
            scan(conn, src["id"])
            done.append(src["id"])
        except (SoundError, OSError) as e:
            conn.execute("UPDATE sound_sources SET last_summary=? WHERE id=?", (f"Lỗi: {e}", src["id"]))
            conn.commit()
    return done


# ---- searching --------------------------------------------------------------------------------------------------------
def search(conn, query: str = "", kind: Optional[str] = None, category: Optional[str] = None, mood: Optional[str] = None,
           limit: int = 12, offset: int = 0) -> Dict:
    sql, args = " FROM sounds WHERE 1=1", []
    for word in fold(query).split():
        sql += " AND search LIKE ?"
        args.append(f"%{word}%")
    if kind:
        sql += " AND kind=?"
        args.append(kind)
    if category:
        sql += " AND category=?"
        args.append(category)
    if mood:
        sql += " AND mood=?"
        args.append(mood)
    total = conn.execute("SELECT COUNT(*)" + sql, args).fetchone()[0]
    rows = conn.execute("SELECT *" + sql + " ORDER BY category, lower(name) LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
    return {"total": total, "rows": [dict(r) for r in rows]}


def categories(conn, kind: Optional[str] = None) -> List[tuple]:
    sql = "SELECT category, COUNT(*) n FROM sounds" + (" WHERE kind=?" if kind else "") + " GROUP BY category ORDER BY category"
    return [(r["category"], r["n"]) for r in conn.execute(sql, (kind,) if kind else ()).fetchall()]


def counts(conn) -> Dict[str, int]:
    return {r["kind"]: r["n"] for r in conn.execute("SELECT kind, COUNT(*) n FROM sounds GROUP BY kind").fetchall()}


def get(conn, sound_id: int) -> Optional[Dict]:
    r = conn.execute("SELECT * FROM sounds WHERE id=?", (sound_id,)).fetchone()
    return dict(r) if r else None


def ensure_duration(conn, sound_id: int) -> Optional[float]:
    """Length in seconds, measured the first time (an unreadable file is remembered as 0 so it is not retried)."""
    row = get(conn, sound_id)
    if row is None:
        return None
    if row["duration"] is not None:
        return row["duration"] or None
    try:
        seconds = ffmpeg_studio.probe_duration(row["path"])
    except (ffmpeg_studio.FFmpegNotFound, OSError):
        return None                                    # no ffmpeg now: try again later
    conn.execute("UPDATE sounds SET duration=? WHERE id=?", (seconds or 0, sound_id))
    if seconds and seconds > 75 and row["kind"] == "sfx" and row["mood"]:
        conn.execute("UPDATE sounds SET kind='music' WHERE id=?", (sound_id,))
    conn.commit()
    return seconds


# ---- listening (measured, not guessed from the name) ------------------------------------------------------------------
_MEAN = re.compile(r"mean_volume:\s*(-?[\d.]+) dB")
_MAX = re.compile(r"max_volume:\s*(-?[\d.]+) dB")
_LENGTH = re.compile(r"Duration:\s*(\d+):(\d+):([\d.]+)")


def measure(path: str) -> Optional[Dict]:
    """Length and loudness of a file from one ffmpeg pass (`volumedetect`); None when it cannot be read."""
    import subprocess
    try:
        proc = subprocess.run([ffmpeg_studio.find_ffmpeg(), "-hide_banner", "-i", path, "-vn", "-af", "volumedetect", "-f", "null", "-"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    except (ffmpeg_studio.FFmpegNotFound, OSError, subprocess.TimeoutExpired):
        return None
    text = proc.stderr or ""
    d, mean, peak = _LENGTH.search(text), _MEAN.search(text), _MAX.search(text)
    if not (d and mean and peak):
        return None
    return {"seconds": int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)), "mean": float(mean.group(1)), "peak": float(peak.group(1))}


def tags_from(kind: str, seconds: float, mean: float, peak: float) -> str:
    """Words describing what the sound is good for, from its length and loudness (comma separated)."""
    tags = []
    if kind == "sfx":
        if seconds < 0.7:
            tags.append("điểm nhấn ngắn (click, hit)")
        elif seconds < 2.5:
            tags.append("hiệu ứng vừa (whoosh, va chạm)")
        elif seconds < 8:
            tags.append("hiệu ứng dài (nổ, dâng lên)")
        else:
            tags.append("âm nền / môi trường dài")
        if peak > -3 and seconds < 4:
            tags.append("mạnh")
        elif peak < -18:
            tags.append("nhẹ")
    else:
        if mean > -14:
            tags.append("năng lượng cao")
        elif mean < -22:
            tags.append("nhẹ nhàng")
    return ", ".join(tags)


def analyze(conn, limit: Optional[int] = None, workers: int = 4) -> Dict:
    """Listen (measure) to tracks that were not analysed yet, store length + tags and, for music without a mood, an energy mood.
    Safe to repeat: only unanalysed files are touched. Returns {'done', 'failed', 'left'}."""
    from concurrent.futures import ThreadPoolExecutor
    rows = conn.execute("SELECT id, path, kind, mood, category, name FROM sounds WHERE tags IS NULL ORDER BY id" + (f" LIMIT {int(limit)}" if limit else "")).fetchall()
    done = failed = 0
    with ThreadPoolExecutor(max_workers=max(workers, 1)) as pool:
        results = list(pool.map(lambda r: measure(r["path"]) if os.path.exists(r["path"]) else None, rows))
    for r, m in zip(rows, results):
        if m is None:
            failed += 1
            conn.execute("UPDATE sounds SET tags='' WHERE id=?", (r["id"],))          # unreadable: do not retry every time
            continue
        kind = r["kind"]
        if m["seconds"] > 75 and kind == "sfx":
            kind = "music"                                                           # a long file in an effects folder is a track
        tags = tags_from(kind, m["seconds"], m["mean"], m["peak"])
        mood = r["mood"]
        if kind == "music" and not mood:
            mood = "sôi động" if m["mean"] > -14 else ("thư giãn" if m["mean"] < -22 else "")
        conn.execute("UPDATE sounds SET duration=?, tags=?, kind=?, mood=?, search=? WHERE id=?",
                     (m["seconds"], tags, kind, mood, fold(f"{r['name']} {r['category']} {mood or ''} {tags}"), r["id"]))
        done += 1
    conn.commit()
    left = conn.execute("SELECT COUNT(*) FROM sounds WHERE tags IS NULL").fetchone()[0]
    return {"done": done, "failed": failed, "left": left}


# ---- choosing for a project -------------------------------------------------------------------------------------------
def suggest_music(conn, scene_mood_texts: List[str], limit: int = 5, seed: int = 0) -> List[Dict]:
    """Background tracks that fit the scene moods: tracks of a wanted mood first (the first scene mood weighs most)."""
    wanted: List[str] = []
    for text in scene_mood_texts:
        for m in moods_of_text(text):
            if m not in wanted:
                wanted.append(m)
    picks: List[Dict] = []
    for m in wanted:
        rows = conn.execute("SELECT * FROM sounds WHERE kind='music' AND mood=? ORDER BY path", (m,)).fetchall()
        if rows:
            start = seed % len(rows)
            picks.extend(dict(r) for r in rows[start:] + rows[:start])
        if len(picks) >= limit * 2:
            break
    if not picks:
        rows = conn.execute("SELECT * FROM sounds WHERE kind='music' ORDER BY path").fetchall()
        if rows:
            start = seed % len(rows)
            picks = [dict(r) for r in rows[start:] + rows[:start]]
    seen, out = set(), []
    for r in picks:
        if r["id"] not in seen:
            seen.add(r["id"])
            out.append(r)
    return out[:limit]


def pick_music(conn, scene_mood_texts: List[str], min_seconds: float = 0, seed: int = 0) -> Optional[Dict]:
    """One background track for the automatic mode: best mood match, and long enough when that can be checked."""
    options = suggest_music(conn, scene_mood_texts, limit=8, seed=seed)
    best = None
    for r in options:
        seconds = ensure_duration(conn, r["id"])
        if seconds and min_seconds and seconds >= min_seconds * 0.8:
            return dict(r, duration=seconds)
        if best is None or (seconds or 0) > (best.get("duration") or 0):
            best = dict(r, duration=seconds)
    return best


def copy_into(sound: Dict, dest_dir: str, name: str) -> str:
    """Copy a library file into a project folder (the original is never moved)."""
    if not os.path.exists(sound["path"]):
        raise SoundError("File không còn ở vị trí cũ (Drive chưa kết nối hoặc đã xóa)")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, name + sound["ext"])
    shutil.copyfile(sound["path"], dest)
    return dest
