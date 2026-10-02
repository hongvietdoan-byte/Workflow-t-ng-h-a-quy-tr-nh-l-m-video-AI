"""AI-planned sound effects: Claude reads the scenes and the person's sound library and proposes where an effect belongs.

One button in the render step. The proposal (what, when, how loud, and why) is shown for review; only what the person keeps is
copied into the project's mix (audio_lib), where it can still be adjusted or removed like any other effect.

Effects are for scene changes and accents (a hit, a whoosh, an impact), not a constant bed, so the prompt asks for few, well-placed ones.
"""
from . import access
import json
import os
from typing import Dict, List, Optional

from . import audio_lib, ffmpeg_studio, final_cut, llm_runner, sound_lib
from .pipeline import Pipeline

MARKER = "Chuyên viên sound design"
LABEL_PREFIX = "AI: "
MAX_CATALOG = 260
PER_KIND = 6            # the best few of every kind of sound, so a library of any size is represented


class SfxPlanError(Exception):
    """A message that can be shown to the person. `not_ready`: the library has not been listened to (yet), nothing was decided."""

    def __init__(self, message: str, not_ready: bool = False):
        super().__init__(message)
        self.not_ready = not_ready


def timeline(p: Pipeline, data_dir: str, pid: int, transition: str = "cut", fade: float = 1.0) -> List[Dict]:
    """The scenes on the final video's timeline: idx, title, start, length, text (script), mood."""
    overlap = fade if transition in ffmpeg_studio.OVERLAP_STYLES else 0.0
    info = {r["idx"]: json.loads(r["data"] or "{}") for r in p.conn.execute("SELECT idx, data FROM scenes WHERE project_id=?", (pid,))}
    out, t = [], 0.0
    for clip in final_cut.collect_clips(p, data_dir, pid):
        if not clip["path"]:
            continue
        length = final_cut.clip_seconds(clip["path"], clip["requested_sec"])
        d = info.get(clip["idx"], {}) if clip["idx"] is not None else {}
        out.append({"idx": clip["idx"], "title": clip["title"], "start": round(t, 2), "length": round(length, 2),
                    "text": (d.get("text") or "")[:400], "mood": d.get("mood") or "", "shot": d.get("shot") or "",
                    **({"sound": d["sound"]} if isinstance(d.get("sound"), dict) else {})})   # director.md Đ9
        t += length - overlap
    return out


def catalog(conn, limit: int = MAX_CATALOG, per_kind: int = PER_KIND) -> List[Dict]:
    """Only effects that were LISTENED to and recognised with confidence (never chosen by file name alone; human voices are left out):
    the best `per_kind` of each recognised kind of sound, so the whole library is represented without listing every file."""
    rows = [dict(r) for r in conn.execute(
        f"SELECT id, name, category, tags, duration, heard_label, heard_score FROM sounds WHERE {sound_lib.TRUSTED_SQL} ORDER BY heard_label, heard_score DESC, name")]
    picked: List[Dict] = []
    seen: Dict[str, int] = {}
    for r in rows:
        if seen.get(r["heard_label"], 0) < per_kind:
            seen[r["heard_label"]] = seen.get(r["heard_label"], 0) + 1
            picked.append(r)
    picked.sort(key=lambda r: -r["heard_score"])
    return picked[:limit]


def build_prompt(scenes: List[Dict], sounds: List[Dict], total: float, wish: str = "") -> str:
    lines = [{"scene": s["idx"], "start": s["start"], "length": s["length"], "mood": s["mood"], "shot": s["shot"], "script": s["text"],
              **({"director_sound": s["sound"]} if s.get("sound") else {})} for s in scenes]
    asked = sum(len((s.get("sound") or {}).get("sfx") or []) for s in scenes)
    library = [{"id": s["id"], "heard": s["heard_label"], "name": s["name"], "folder": s["category"], **({"tags": s["tags"]} if s.get("tags") else {}),
                **({"sec": round(s["duration"], 1)} if s.get("duration") else {})} for s in sounds]
    return (f"{MARKER} cho video game ngắn. Đọc các cảnh và chọn hiệu ứng âm thanh từ kho có sẵn để thêm vào video.\n\n"
            "Nguyên tắc: hiệu ứng chỉ dùng cho **điểm chuyển cảnh và điểm nhấn** (va chạm, ra đòn, xuất hiện, chuyển cảnh nhanh), "
            "KHÔNG phủ kín video và không chọi với nhạc nền. Ít mà đúng chỗ: tối đa 1 hiệu ứng mỗi ~4 giây, tổng tối đa "
            f"{max(2, len(scenes) * 2)}. Đặt điểm nhấn đúng giây hành động xảy ra (chuyển cảnh = đúng giây bắt đầu cảnh mới, có thể sớm 0.1–0.3s). "
            "Tránh đặt lên câu thoại nếu tiếng to. Chỉ dùng `id` có trong danh sách. Âm lượng 0.3–1.0 (nhấn mạnh 0.8–1.0, chi tiết nhỏ 0.3–0.5). "
            "Mỗi hiệu ứng trong kho có `heard` = loại âm thanh mà mô hình nhận dạng âm thanh ĐÃ NGHE ra (đáng tin); tên file có thể sai nên chọn theo `heard`. "
            "Chỉ chọn khi loại âm thanh khớp đúng nhu cầu của khoảnh khắc đó; không có cái nào khớp thì KHÔNG thêm. `heard` cho biết LOẠI âm thanh chứ không cho biết sắc thái: tên file gợi ý dễ thương/hài (cute, meme, fun...) thì đừng dùng cho cảnh nghiêm túc hay hành động. "
            "Mỗi hiệu ứng có `reason` ngắn bằng tiếng Việt nói rõ vì sao chọn.\n"
            # director.md Đ9: the Director decides sound together with the feeling; the sound designer carries it out
            + ("\n# Ý đồ âm thanh của Đạo diễn (ưu tiên hơn nguyên tắc chung ở trên)\n"
               "Cảnh có `director_sound` là chỗ Đạo diễn đã quyết âm thanh cùng cảm xúc: `sfx` = âm khoảnh khắc đó cần (tiếng thở, nuốt "
               "nước bọt, sột soạt vải, tiếng lên đạn, tiếng bíp…) — đặt trong cảnh đó dù không phải điểm chuyển cảnh, tính thêm ngoài "
               f"giới hạn trên ({asked} âm); kho không có âm khớp thì KHÔNG thay bằng âm khác loại, nói rõ âm nào thiếu trong summary. "
               "`music: cut` = nhạc tắt từ cảnh đó tới cảnh `in`: trong khoảng lặng một âm nhỏ nghe rất rõ, đừng lấp bằng hiệu ứng to; "
               "`breath` = lặng ngắn ngay trước cảnh, đừng đặt hiệu ứng vào khoảng lặng đó. `why` là lý do của Đạo diễn.\n"
               if any(s.get("sound") for s in scenes) else "")
            + (f"\n# Yêu cầu thêm của người dùng (ưu tiên làm theo)\n{wish.strip()}\n" if wish.strip() else "")
            + f"\n# Các cảnh (tổng {total:.1f} giây)\n```json\n" + json.dumps(lines, ensure_ascii=False) + "\n```\n"
            "\n# Hiệu ứng có sẵn\n```json\n" + json.dumps(library, ensure_ascii=False) + "\n```\n\n"
            "Trả về **một JSON duy nhất**: {\"summary\": \"nhận xét 1-2 câu về cách bạn đặt hiệu ứng\", "
            "\"cues\": [{\"at\": <giây trên video>, \"scene\": <số cảnh>, \"id\": <id hiệu ứng>, \"volume\": 0.8, \"reason\": \"...\"}]}. "
            "Không có chỗ nào hợp thì trả `cues` rỗng và nói lý do trong summary.")


def propose(client, p: Pipeline, data_dir: str, pid: int, transition: str = "cut", fade: float = 1.0, wish: str = "") -> Dict:
    """{'summary': str, 'cues': [{at, scene, id, name, folder, volume, reason}]} (nothing is added to the project yet)."""
    if client is None:
        raise SfxPlanError("Cần Claude API (ANTHROPIC_API_KEY) để AI đọc kịch bản và chọn hiệu ứng.")
    scenes = timeline(p, data_dir, pid, transition, fade)
    if not scenes:
        raise SfxPlanError("Chưa có clip nào (Bước 4) nên chưa biết đặt hiệu ứng ở đâu.")
    sounds = catalog(p.conn)
    if not sounds:
        heard = sound_lib.sound_ai.available()
        raise SfxPlanError("Chưa có hiệu ứng nào đã được nghe và nhận dạng chắc chắn" + ("" if heard else " (máy chưa có mô hình nhận dạng âm thanh)")
                           + ": AI không tự chọn hiệu ứng theo tên file để tránh nhầm. Thêm thư mục ở ⚙ Cài đặt → Kho âm thanh và chờ hệ thống nghe xong.",
                           not_ready=True)
    by_id = {s["id"]: s for s in sounds}
    total = scenes[-1]["start"] + scenes[-1]["length"]

    def validate(obj):
        if not isinstance(obj, dict) or not isinstance(obj.get("cues"), list):
            raise ValueError("cần khóa cues (danh sách)")
        for c in obj["cues"]:
            if not isinstance(c, dict) or int(c.get("id", -1)) not in by_id:
                raise ValueError("có hiệu ứng không nằm trong danh sách (id sai)")
            float(c.get("at"))

    with llm_runner.tagged("sfx"):
        obj, _, _ = llm_runner.ask_json(client, build_prompt(scenes, sounds, total, wish), validate)
    cues = []
    for c in obj["cues"]:
        s = by_id[int(c["id"])]
        at = min(max(float(c["at"]), 0.0), max(total - 0.3, 0.0))
        cues.append({"at": round(at, 2), "scene": c.get("scene"), "id": s["id"], "name": s["name"], "folder": s["category"],
                     "volume": round(min(max(float(c.get("volume", 0.8)), 0.1), 1.5), 2), "reason": str(c.get("reason", "")).strip()})
    cues.sort(key=lambda c: c["at"])
    from . import sound_intent
    # CHUAN luật 1: a sound the Director asked for and nobody placed is shown, never lost in silence
    return {"summary": str(obj.get("summary", "")).strip(), "cues": cues, "unmet": sound_intent.unmet(scenes, cues)}


def anchor(scenes: List[Dict], at: float) -> Optional[Dict]:
    """The shot a second of the timeline falls in: {"anchor_idx", "offset"} (offset = seconds after that shot starts)."""
    hit = None
    for s in scenes:
        if s.get("idx") is not None and float(s["start"]) <= at + 1e-6:
            hit = s
    if hit is None:
        return None
    return {"anchor_idx": hit["idx"], "offset": round(max(at - float(hit["start"]), 0.0), 2)}


def place_on_timeline(data_dir: str, pid: int, rows: List[Dict], durations: List[float], transition: str = "cut",
                      fade: float = 1.0) -> Dict:
    """Trial #8 (2026-09-28): an effect was saved at an absolute second, then 19 clips were remade longer and the gunshot of shot 26
    played 20 s early, over another line. An AI-placed effect keeps the shot it belongs to (anchor_idx + offset): its second is worked
    out again on the render's own timeline; an effect whose shot is not in this render is switched off (never played at an old time).
    Effects without an anchor (added by hand) keep the second the person set. Returns {"moved", "off"}."""
    directory = audio_lib.assets_dir(data_dir, pid)
    items = audio_lib.load(directory)
    overlap = fade if transition in ffmpeg_studio.OVERLAP_STYLES else 0.0
    starts, t = {}, 0.0
    for r, d in zip(rows, durations):
        if r.get("idx") is not None:
            starts[r["idx"]] = (t, float(d))
        t += float(d) - overlap
    moved = off = 0
    for e in items:
        if e.get("kind") != "sound_effect" or e.get("anchor_idx") is None:
            continue
        where = starts.get(e["anchor_idx"])
        if where is None:
            if e.get("use"):
                e["use"], e["anchor_off"], off = False, True, off + 1
            continue
        if e.pop("anchor_off", False):           # switched off only because its shot was left out: back in with the shot
            e["use"] = True
        start = round(where[0] + min(float(e.get("offset") or 0.0), max(where[1] - 0.05, 0.0)), 2)
        if abs(float(e.get("start") or 0.0) - start) > 1e-6:
            moved += 1
        e["start"] = start
    audio_lib._save(directory, items)
    return {"moved": moved, "off": off}


def apply(p: Pipeline, data_dir: str, pid: int, chosen: List[Dict], scenes: Optional[List[Dict]] = None) -> int:
    """Replace the effects an earlier AI proposal added with `chosen` (rows: id, at, volume, name). Other effects stay. Returns the count.
    Each effect is anchored to the shot its second falls in on `scenes` (the timeline the proposal was made on; read again when not
    given), so a later render with other clip lengths moves it with its shot (place_on_timeline)."""
    access.need_edit(p, pid, "áp dụng hiệu ứng âm thanh")
    directory = audio_lib.assets_dir(data_dir, pid)
    if scenes is None:
        scenes = timeline(p, data_dir, pid)
    for i in reversed([i for i, e in enumerate(audio_lib.load(directory)) if str(e.get("label", "")).startswith(LABEL_PREFIX)]):
        audio_lib.remove(directory, i)
    n = 0
    for c in chosen:
        row = sound_lib.get(p.conn, int(c["id"]))
        if row is None or not os.path.exists(row["path"]):
            continue
        seconds = sound_lib.ensure_duration(p.conn, row["id"])
        audio_lib.add_local(directory, row["path"], LABEL_PREFIX + row["name"], float(c["at"]), float(c["volume"]),
                            int(seconds * 1000) if seconds else None, anchor(scenes, float(c["at"])))
        n += 1
    return n
