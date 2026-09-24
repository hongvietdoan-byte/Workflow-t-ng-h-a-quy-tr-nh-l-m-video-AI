"""AI-planned sound effects: Claude reads the scenes and the person's sound library and proposes where an effect belongs.

One button in the render step. The proposal (what, when, how loud, and why) is shown for review; only what the person keeps is
copied into the project's mix (audio_lib), where it can still be adjusted or removed like any other effect.

Effects are for scene changes and accents (a hit, a whoosh, an impact), not a constant bed, so the prompt asks for few, well-placed ones.
"""
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
                    "text": (d.get("text") or "")[:400], "mood": d.get("mood") or "", "shot": d.get("shot") or ""})
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
    lines = [{"scene": s["idx"], "start": s["start"], "length": s["length"], "mood": s["mood"], "shot": s["shot"], "script": s["text"]}
             for s in scenes]
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
    return {"summary": str(obj.get("summary", "")).strip(), "cues": cues}


def apply(p: Pipeline, data_dir: str, pid: int, chosen: List[Dict]) -> int:
    """Replace the effects an earlier AI proposal added with `chosen` (rows: id, at, volume, name). Other effects stay. Returns the count."""
    directory = audio_lib.assets_dir(data_dir, pid)
    for i in reversed([i for i, e in enumerate(audio_lib.load(directory)) if str(e.get("label", "")).startswith(LABEL_PREFIX)]):
        audio_lib.remove(directory, i)
    n = 0
    for c in chosen:
        row = sound_lib.get(p.conn, int(c["id"]))
        if row is None or not os.path.exists(row["path"]):
            continue
        seconds = sound_lib.ensure_duration(p.conn, row["id"])
        audio_lib.add_local(directory, row["path"], LABEL_PREFIX + row["name"], float(c["at"]), float(c["volume"]),
                            int(seconds * 1000) if seconds else None)
        n += 1
    return n
