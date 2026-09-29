"""Build copy-paste prompt bundles for V0 (Claude Desktop chat). V1 sends the same text via API."""
import json
import os
import re
from typing import List, Optional

from . import assets, dialogue, knowledge, looks
from .evalset import few_shot_text
from .pipeline import Pipeline

_ROOT = os.path.join(os.path.dirname(__file__), "..")
_SEP = "\n\n---\n\n"
CACHE_BREAK = "\n\n<<<cache>>>\n\n"   # C2: parts before it repeat between calls (Claude API prompt cache); shown to people as _SEP


def _cached(*groups: List[str]) -> str:
    """Join prompt groups (each a list of parts, empty parts dropped) with a cache mark after every group but the last."""
    return CACHE_BREAK.join(_SEP.join(x for x in g if x) for g in groups if any(g))
_SCENE_KEYS = ("location", "time", "characters", "mood", "lighting", "shot", "blocking", "image_prompt", "emotional_intent", "beat",
               "camera_complexity", "shot_role", "dialogue", "duration_s", "sequence")
# v3 shot rows: what the shot contract adds (only present on shot rows, so v2 prompts do not change)
_SHOT_KEYS = ("story_scene", "shot_no", "size", "angle", "camera_move", "role", "action", "end_state", "action_peak", "continuous_with_next",
              "performance", "why", "speed", "freeze_end_s")   # GĐ4: acting over time, the DP reason; E10: slowed shots


def _read(*parts: str) -> str:
    with open(os.path.join(_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def qc_criteria() -> List[str]:
    return [c["key"] for c in json.loads(_read("data", "qc_checklist.json"))["criteria"]]


WORLD_BIBLE_FIELDS = (("render_style", "Phong cách dựng hình"), ("palette", "Bảng màu"), ("lighting_logic", "Logic ánh sáng"),
                      ("texture_finish", "Chất liệu/hoàn thiện hình ảnh"), ("era_lore", "Thời đại/thế giới"),
                      ("physics", "Vật lý/thời tiết"))


def world_bible_text(pipeline: Pipeline, project_id: int) -> str:
    """The project's style bible (set in step 1), as a block every step must inherit; empty when not set."""
    row = pipeline.project(project_id)
    raw = row["world_bible"] if "world_bible" in row.keys() else None   # old database not migrated yet
    try:
        data = json.loads(raw or "{}")
    except ValueError:
        return ""
    lines = [f"- **{label}:** {str(data[key]).strip()}" for key, label in WORLD_BIBLE_FIELDS if str(data.get(key) or "").strip()]
    if not lines:
        return ""
    return ("# World Bible của dự án (BẮT BUỘC kế thừa, không mâu thuẫn)\n" + "\n".join(lines) +
            "\nMọi prompt ảnh/video của dự án dùng lại cách diễn đạt này để các cảnh nhất quán (không cần chép nguyên văn ở mỗi cảnh).")


def _skill_block(names) -> str:
    """Feature skill_dossier: the characters' skill dossiers (data/skills) — they win over the few lines of the skills notes."""
    from . import skill_dossier
    return skill_dossier.director_block(names) if skill_dossier.enabled() else ""


def people_in_project(pipeline: Pipeline, project_id: int) -> List[str]:
    """Names the FF skill notes are filtered by: Character Bible, the project's character resources, capitalised speakers."""
    conn = pipeline.conn
    names = [r["name"] for r in conn.execute("SELECT name FROM characters WHERE project_id=?", (project_id,))]
    names += [a["name"] for a in assets.project_assets(conn, project_id) if a["kind"] in ("character", "pet")]
    for r in conn.execute("SELECT data FROM scenes WHERE project_id=?", (project_id,)):
        names += [who for who, _ in dialogue.scene_lines(json.loads(r["data"] or "{}")) if who]
    return sorted(set(names))


def bible_block(pipeline: Pipeline, project_id: int) -> str:
    """The Character Bible as it stands: the Director reuses these exact names (a re-run returning "KELLY" for "Kelly" used to add a
    duplicate) and does not rewrite a locked or hand-edited entry."""
    rows = pipeline.conn.execute("SELECT name, description, wardrobe, locked, user_edited FROM characters WHERE project_id=? ORDER BY id",
                                 (project_id,)).fetchall()
    if not rows:
        return ""
    lines = []
    for r in rows:
        keep = "đã khóa" if r["locked"] else ("người dùng đã sửa tay" if r["user_edited"] else "")
        lines.append(f"- {r['name']}" + (f" ({keep} — giữ nguyên mô tả)" if keep else "") + f": {r['description']}"
                     + (f" | trang phục: {r['wardrobe']}" if r["wardrobe"] else ""))
    return ("# Character Bible hiện có (dùng ĐÚNG các tên này, không tạo bản trùng khác hoa/thường hay khác cách viết)\n" + "\n".join(lines))


def locked_block(pipeline: Pipeline, project_id: int) -> str:
    from .llm_io import locked_fields
    rows = locked_fields(pipeline.conn, project_id)
    if not rows:
        return ""
    return ("# Giá trị người dùng đã khóa (GIỮ NGUYÊN, lên kế hoạch xung quanh)\n"
            + "\n".join(f"- {r.get('label') or 'Cảnh ' + str(r['idx'])}: " + json.dumps(r["fields"], ensure_ascii=False) for r in rows))


def project_frame_block(pipeline: Pipeline, project_id: int) -> str:
    from . import formats
    proj = pipeline.project(project_id)
    bits = [formats.director_line(formats.project_aspect(proj))]
    genre = proj["genre"] if "genre" in proj.keys() else None
    if genre:
        bits.append(f"Thể loại của dự án: {genre}" + (" (người dùng đã chọn — giữ nguyên)" if proj["genre_locked"] else ""))
    bits = [b for b in bits if b]
    return ("# Khung hình và thể loại\n" + "\n".join(f"- {b}" for b in bits)) if bits else ""


def shot_style_block(proj) -> str:
    """v3: how Free Fire videos are cut (knowledge/ff_directing.md) + the project's editing style (knowledge/ff_styles/<STYLE>.md)."""
    from . import shots
    parts = [_read("prompts", "17_director_shots.md"), _read("knowledge", "ff_directing.md")]
    picked = [s for s in shots.styles(proj) if os.path.exists(os.path.join(_ROOT, "knowledge", "ff_styles", f"{s}.md"))]
    if picked:
        # người dùng 2026-09-28: reference styles are suggestions to mix, not one frame every film must follow
        parts.append("# Phong cách tham khảo của dự án — GỢI Ý, KHÔNG BẮT BUỘC\n"
                     f"Người dùng chọn {len(picked)} phong cách tham khảo: {', '.join(picked)}. Đây là cách những video thật đã làm (số đo + "
                     "thói quen dựng), để bạn CHỌN LỌC: lấy điều hợp với kịch bản này, "
                     + ("trộn các phong cách với nhau (vd nhịp của phong cách này, cách dựng thoại của phong cách kia), " if len(picked) > 1 else "")
                     + "và làm khác khi kịch bản cần. Không có con số nào ở đây là ngưỡng phải đạt. Khi cố ý làm khác một gợi ý quan trọng, "
                     "ghi một dòng vào `tradeoffs` (chọn gì, bỏ gì, vì sao).")
        for st_name in picked:
            parts.append(f"## Phong cách tham khảo: {st_name}\n\n" + _read("knowledge", f"ff_styles/{st_name}.md"))
    return _SEP.join(p for p in parts if p)


_TARGET = re.compile(r"(thời lượng|thoi luong|duration|độ dài|do dai)\s*:?\s*(\d{1,3})\s*(?:[–—-]\s*(\d{1,3}))?\s*(giây|giay|s|sec|seconds)\b",
                     re.IGNORECASE)
_SECTION_TIME = re.compile(r"[–—-]\s*(\d{1,3})\s*[–—-]\s*(\d{1,3})\s*(giây|giay|s|sec|secs|seconds)\b", re.IGNORECASE)


DROPPED_LINES_FORMAT = ("Ghi mọi câu đã bỏ vào `dropped_lines` ở gốc JSON: "
                        "[{\"scene\": số cảnh, \"speaker\": \"TÊN\", \"text\": \"câu nguyên văn\", \"why\": \"lý do ngắn\"}].")


def target_seconds(script_text: str):
    """(low, high) seconds the script asks for ("THỜI LƯỢNG: 55–58 GIÂY" / "Duration: 60s"), or None."""
    m = _TARGET.search(script_text or "")
    if not m:
        return None
    lo = int(m.group(2))
    return lo, int(m.group(3) or lo)


def duration_block(pipeline: Pipeline, project_id: int, for_dp: bool = False) -> str:
    """A hard frame for the shot plan: the Director of "ANH CHỌN AI?" made 65 s of shots for a 55–58 s script.
    for_dp (GĐ5 two-pass, Tầng B): the camera rules only — the Director already split the total into a frame per scene and chose the
    lines (the DP never drops one), so the whole-film total, the per-section lines and the trim permission are left out."""
    from . import shots
    proj = pipeline.project(project_id)
    target = None if for_dp else target_seconds(proj["script_text"] if "script_text" in proj.keys() else "")
    parts, speech = [], 0.0
    for s in shots.story_scenes(pipeline, project_id) if shots.mode(proj) else []:
        if for_dp:
            speech += sum(dialogue.needed_seconds([r]) for r in dialogue.lines(s["text"]))
            continue
        rows = dialogue.lines(s["text"])
        need = round(sum(dialogue.needed_seconds([r]) for r in rows), 1)   # each line said in its own shot, with its own breath
        speech += need
        talk = f"; thoại {len(rows)} câu cần ~{need:g} giây nói" if rows else ""
        m = _SECTION_TIME.search(s["heading"] or "")
        if m:
            parts.append(f"- Cảnh {s['idx']} ({s['heading'].split('–')[0].strip()}): tổng các shot ≈ {int(m.group(2)) - int(m.group(1))} giây{talk}")
        elif talk:
            parts.append(f"- Cảnh {s['idx']}{talk}")
    from . import features
    if features.on("camera_setups"):   # H5 (trial 2A: one clip for two shots of one set-up = 33% fewer paid seconds)
        parts.append("- **Vị trí máy**: gán `camera_setup` (A, B, C… trong mỗi cảnh) cho mọi shot; các shot cùng góc máy, cùng người trong khung "
                     "dùng chung một chữ — chúng được gen thành MỘT clip rồi cắt. Đối thoại trong một chỗ: 1 vị trí thiết lập + 2–3 vị trí phủ. "
                     "Shot cần khung nhấn riêng một nhân vật thì cho vị trí riêng.")
    from . import lipsync
    if lipsync.enabled() and lipsync.post_available():   # V4 GĐ3: lip sync is on — the "no close-up on the speaker" rule (N3) is a choice
        parts.append("- **Khớp môi đang BẬT**: được đặt thoại ở shot thấy mặt người nói (kể cả cận) — miệng sẽ được khớp với giọng Việt. "
                     "Câu then chốt quay cận mặt (CU/ECU/MCU, ngang mắt, mặt không bị che, ≤ 5 s) ghi `\"lip_sync\": true` trong shot "
                     "(tạo video kèm giọng — đắt hơn, dùng cho ~20% câu quan trọng nhất); các shot thoại khác khớp môi sau khi có clip. "
                     "Shot người nói quay lưng / ngoài khung thì không cần.")
    elif lipsync.enabled():  # user decision 2026-09-26: no sync.so — the ONLY way a mouth is matched is Seedance generating with the voice
        parts.append("- **Khớp môi đang BẬT, chỉ bằng cách tạo video KÈM GIỌNG** (Seedance nhận file giọng của shot — không có khớp môi sau): "
                     "câu then chốt đặt ở shot cận thấy rõ mặt người nói (CU/ECU/MCU, ngang mắt, mặt không bị che, ≤ 5 s, chỉ người nói "
                     "mở miệng) và ghi `\"lip_sync\": true`. Các câu thoại khác đặt ở trung/toàn, qua vai, người nói quay nghiêng, hoặc lên "
                     "shot người nghe (như luật N3 khi tắt) — shot rộng giữ nguyên miệng của clip. Shot người nói quay lưng / ngoài khung thì "
                     "không cần.")
    if speech:     # the 3rd Director run of "ANH CHỌN AI?" gave 11 spoken shots less time than their line needs (6,8 s in all)
        parts.append(f"- Shot có thoại: `duration_s` ≥ (số âm tiết ÷ {dialogue.RATE:g}) + {dialogue.BREATH:g} giây cho câu của nó "
                     "— không nén câu vào shot ngắn hơn.")
    trim = ("\n**Được phép bỏ bớt câu thoại** (người dùng cho phép): bỏ những câu không cần cho cốt truyện để hầu hết shot dài 2–4 giây — sau khi đã gộp shot im lặng ngắn; không bỏ câu mà câu sau đáp lại. "
            "KHÔNG thêm câu mới, KHÔNG sửa chữ câu giữ lại (giữ nguyên văn). " + DROPPED_LINES_FORMAT
            if "dialogue_trim" in proj.keys() and proj["dialogue_trim"] and not for_dp else "")
    if for_dp:
        if not parts:
            return ""
        return ("# Luật máy quay theo thời lượng và thoại (Đạo diễn đã chốt khung giây + câu thoại của từng cảnh)\n" + "\n".join(parts)
                + "\nTổng các shot của cảnh nằm trong khung giây Đạo diễn ghi cho cảnh đó; thừa thì gộp shot phản ứng/chèn ngắn, "
                  "KHÔNG bỏ câu thoại (quyết định thoại là của Đạo diễn).")
    if not target and not parts and not trim:
        return ""
    head = f"Tổng `duration_s` của MỌI shot phải nằm trong {target[0]}–{target[1]} giây (kịch bản yêu cầu)." if target else ""
    return ("# Thời lượng bắt buộc\n" + head + ("\n" + "\n".join(parts) if parts else "")
            + "\nCộng lại trước khi trả lời; thừa thì gộp shot phản ứng/chèn ngắn" + (", hoặc bỏ bớt câu thoại như dưới đây." if trim
                                                                                   else ", không cắt câu thoại.") + trim)


def _budget_note(pipeline: Pipeline, project_id: int) -> str:
    """The person's budget target as an input of the Director (core.project_budget), or ''."""
    from . import project_budget
    try:
        return project_budget.director_note(pipeline.conn, project_id).strip()
    except Exception:  # noqa: BLE001 - the Director goes without it
        return ""


def build_director_bundle(pipeline: Pipeline, project_id: int, only_scene: Optional[int] = None, note: str = "") -> str:
    """The Director's prompt. only_scene (1.4 "↻ Chia shot lại cảnh này"): the whole bundle stays the same (it is cached — every
    re-planned scene reads it at 1/10 price) and a short task after the cache mark asks for that ONE scene's shots."""
    from . import shots
    proj = pipeline.project(project_id)
    if shots.mode(proj):         # v3: the Director reads the script's scenes (story_scenes) and splits each into shots
        scenes = "\n\n".join(f"### Cảnh {s['idx']} — {s['heading']}\n{s['text']}" for s in shots.story_scenes(pipeline, project_id))
    else:
        rows = pipeline.conn.execute(
            "SELECT idx, title, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
        scenes = "\n\n".join(
            f"### Cảnh {r['idx']} — {r['title']}\n{json.loads(r['data'] or '{}').get('text', '')}" for r in rows)
    folded = knowledge.folded_builtin("director")
    keep = lambda rel: "" if f"knowledge/{rel}" in folded else _read("knowledge", rel)  # noqa: E731
    from . import features
    if features.on("film_crew"):                   # H3/H7: one reasoned rule book per role instead of the scattered documents
        crew = [role_text("director.md")] + ([role_text("dp.md")] if shots.mode(proj) else [])
        keep = lambda rel: "" if rel in ("cinematography_basics.md", "film_director_method.md", "dialogue_craft.md") else (  # noqa: E731
            "" if f"knowledge/{rel}" in folded else _read("knowledge", rel))
    else:
        crew = []
    ff = "" if "knowledge/ff_character_skills_visual.md" in folded else knowledge.ff_skills_for(people_in_project(pipeline, project_id))
    ff = _SEP.join(x for x in [ff, _skill_block(people_in_project(pipeline, project_id))] if x)
    body = _SEP.join(x for x in [
        _read("prompts", "01_director_scene_analysis.md"),
        project_frame_block(pipeline, project_id),
        looks.director_note(proj),
        _budget_note(pipeline, project_id),
        _read("knowledge", "ff_gameplay_visual.md"),   # what Free Fire gameplay really looks like (reference, not footage to cut in)
        keep("cinematography_basics.md"),
        keep("genre_guides.md"),
        knowledge.genre_text(proj["genre"] if "genre" in proj.keys() else None),
        shot_style_block(proj) if shots.mode(proj) else "",
        duration_block(pipeline, project_id) if shots.mode(proj) else "",
        *crew,
        _location_block(pipeline, project_id) if shots.mode(proj) else "",
        keep("research_notes.md"),
        keep("film_director_method.md"),
        keep("character_lock.md"),
        keep("dialogue_craft.md"),
        ff,
        assets.context_text(pipeline.conn, project_id),
        standard_block(pipeline, project_id),
        bible_block(pipeline, project_id),
        world_bible_text(pipeline, project_id),
        knowledge.user_text("director"),
        few_shot_text(),
        locked_block(pipeline, project_id),
        script_preamble(proj),
        "# Kịch bản đã tách cảnh\n\n" + scenes,
    ] if x)
    if only_scene is None:
        return body
    current = [{k: s["data"].get(k) for k in ("shot_no", "size", "angle", "duration_s", "characters", "action", "dialogue")}
               for s in shots.shots_of(pipeline, project_id) if s["data"].get("story_scene") == only_scene]
    task = (f"# Việc lần này: CHỈ chia shot lại **Cảnh {only_scene}**\n"
            f"Các cảnh khác giữ nguyên (đã có kế hoạch). Trả về **một JSON duy nhất**: `{{\"characters\": [], \"scenes\": [{{...}}]}}` — "
            f"`characters` để RỖNG (Character Bible giữ nguyên), `scenes` có đúng MỘT phần tử là Cảnh {only_scene} (`idx`: {only_scene}) "
            "với đủ các trường của cảnh và danh sách `shots` mới theo mọi luật ở trên (thoại nguyên văn, thời lượng phần này, khớp môi…)."
            + (f"\nLý do chia lại: {note}" if note else "")
            + ("\nKế hoạch hiện tại của cảnh này (để biết đang có gì):\n" + json.dumps(current, ensure_ascii=False) if current else ""))
    return body + CACHE_BREAK + task


# ---- GĐ5: the Director in two passes (feature director_two_pass, core/director_two_pass.py) --------------------------------------
def _story_text(pipeline: Pipeline, project_id: int) -> str:
    from . import shots
    return "\n\n".join(f"### Cảnh {s['idx']} — {s['heading']}\n{s['text']}" for s in shots.story_scenes(pipeline, project_id))


def intent_frame_block(pipeline: Pipeline, project_id: int) -> str:
    """Tầng A: the length the Director splits between the scenes (`target_s`), what each scene's lines need to be said, and the
    dialogue decision (every line, or the ✂ permission with its rules) — the same numbers the single-call duration block gives."""
    from . import shots
    proj = pipeline.project(project_id)
    target = target_seconds(proj["script_text"] if "script_text" in proj.keys() else "")
    rows = []
    for s in shots.story_scenes(pipeline, project_id):
        said = dialogue.lines(s["text"])
        need = round(sum(dialogue.needed_seconds([r]) for r in said), 1)
        bits = []
        m = _SECTION_TIME.search(s["heading"] or "")
        if m:
            bits.append(f"kịch bản ghi ≈ {int(m.group(2)) - int(m.group(1))} giây")
        if said:
            bits.append(f"thoại {len(said)} câu cần ~{need:g} giây nói (mỗi câu một hơi, ≈ số âm tiết ÷ {dialogue.RATE:g} + {dialogue.BREATH:g} s)")
        rows.append(f"- Cảnh {s['idx']}: " + ("; ".join(bits) or "không ghi giây, không có thoại"))
    head = (f"Tổng `target_s` của mọi cảnh phải nằm trong {target[0]}–{target[1]} giây (kịch bản yêu cầu)." if target
            else "Kịch bản không ghi tổng thời lượng: đặt `target_s` theo nhịp thể loại và thời gian nói.")
    if "dialogue_trim" in proj.keys() and proj["dialogue_trim"]:
        talk = ("**Được phép bỏ bớt câu thoại** (người dùng bật ✂): chỉ câu hình ảnh đã nói thay và không ai đáp lại; không bỏ câu gieo "
                "cho twist/kết. KHÔNG thêm câu mới, KHÔNG sửa chữ câu giữ lại (giữ nguyên văn). " + DROPPED_LINES_FORMAT)
    else:
        talk = ("**Không được bỏ câu thoại**: `dialogue` của mỗi cảnh là MỌI câu của cảnh đó, nguyên văn, đúng người nói, đúng thứ tự "
                "(thời lượng không đủ thì thoại thắng — ghi `tradeoffs`).")
    return "# Khung thời lượng và quyết định thoại (Tầng A)\n" + head + "\n" + "\n".join(rows) + "\n" + talk


def build_intent_bundle(pipeline: Pipeline, project_id: int) -> str:
    """Tầng A — Đạo diễn: Character Bible + the intent of every scene (no shots). Reads the Director's knowledge only — story, emotion,
    genre, look, the Free Fire gameplay reference, the library — never the DP's camera knowledge (cinematography_basics, dp.md, prompt
    17): each role reads its own book (kế hoạch H7). Keeps every block of the single call that protects the Bible and the lines:
    standard profiles (T1), the stored Bible (exact names, locked / hand-edited entries), locked fields, World Bible, the preamble."""
    from . import features
    proj = pipeline.project(project_id)
    folded = knowledge.folded_builtin("director")
    keep = lambda rel: "" if f"knowledge/{rel}" in folded else _read("knowledge", rel)  # noqa: E731
    if features.on("film_crew"):                   # H3/H7: the Director's reasoned rule book instead of the scattered documents
        method = [role_text("director.md", intent_only=True), keep("research_notes.md")]
    else:
        method = [keep("research_notes.md"), keep("film_director_method.md"), keep("dialogue_craft.md")]
    return _SEP.join(x for x in [
        _read("prompts", "19_director_intent.md"),
        project_frame_block(pipeline, project_id),
        looks.director_note(proj),
        _budget_note(pipeline, project_id),
        _read("knowledge", "ff_gameplay_visual.md"),
        keep("genre_guides.md"),
        knowledge.genre_text(proj["genre"] if "genre" in proj.keys() else None),
        intent_frame_block(pipeline, project_id),
        *method,
        _location_block(pipeline, project_id),     # weather / time names of a location pack (the spots are the DP's)
        keep("character_lock.md"),
        assets.context_text(pipeline.conn, project_id),
        standard_block(pipeline, project_id),
        bible_block(pipeline, project_id),
        world_bible_text(pipeline, project_id),
        knowledge.user_text("director"),
        locked_block(pipeline, project_id),
        script_preamble(proj),
        "# Kịch bản đã tách cảnh\n\n" + _story_text(pipeline, project_id),
    ] if x)


def dp_common(pipeline: Pipeline, project_id: int, intent: dict) -> str:
    """Tầng B, the part every scene's call shares (before the cache mark — written once, then read at ~1/10 price): the shot rules
    (prompt 17 + FF editing grammar + the project's style), the DP's book (dp.md with film_crew, else cinematography_basics), the camera
    side of the duration block (lip sync, camera set-ups, speaking time), the location pack, FF skill visuals, the library, standard
    profiles, the Bible Tầng A wrote, World Bible, locked fields, the script and the Director's intent for every scene."""
    from . import features
    proj = pipeline.project(project_id)
    folded = knowledge.folded_builtin("director")
    keep = lambda rel: "" if f"knowledge/{rel}" in folded else _read("knowledge", rel)  # noqa: E731
    book = role_text("dp.md") if features.on("film_crew") else keep("cinematography_basics.md")
    chars = [c for c in intent.get("characters") or [] if isinstance(c, dict)]
    names = [str(c.get("name")) for c in chars]
    bible = "\n".join(f"- **{c.get('name')}**: {c.get('description') or ''}"
                      + (f" | trang phục: {c['wardrobe']}" if c.get("wardrobe") else "")
                      + (f" | Lock: {json.dumps(c['lock'], ensure_ascii=False)}" if c.get("lock") else "") for c in chars)
    plan = {"genre": intent.get("genre"), "scenes": intent.get("scenes") or []}
    ff = "" if "knowledge/ff_character_skills_visual.md" in folded else knowledge.ff_skills_for(names or people_in_project(pipeline, project_id))
    ff = _SEP.join(x for x in [ff, _skill_block(names or people_in_project(pipeline, project_id))] if x)
    return _SEP.join(x for x in [
        _read("prompts", "20_dp_scene_shots.md"),
        shot_style_block(proj),
        book,
        project_frame_block(pipeline, project_id),
        looks.director_note(proj),
        _budget_note(pipeline, project_id),
        _read("knowledge", "ff_gameplay_visual.md"),
        duration_block(pipeline, project_id, for_dp=True),
        _location_block(pipeline, project_id),
        ff,
        assets.context_text(pipeline.conn, project_id),
        standard_block(pipeline, project_id, names=names),
        ("# Character Bible (Đạo diễn vừa chốt ở Tầng A — dùng ĐÚNG các tên này trong `characters` và `speaker`)\n" + bible) if bible else "",
        world_bible_text(pipeline, project_id),
        knowledge.user_text("director"),
        locked_block(pipeline, project_id),
        script_preamble(proj),
        "# Kịch bản đã tách cảnh\n\n" + _story_text(pipeline, project_id),
        "# Ý đồ của Đạo diễn cho mọi cảnh (Tầng A)\n```json\n" + json.dumps(plan, ensure_ascii=False, indent=1) + "\n```",
    ] if x)


def dp_scene_task(pipeline: Pipeline, project_id: int, intent: dict, scene_idx: int, note: str = "", current=None) -> str:
    """Tầng B, the part of ONE scene (after the cache mark): which scene, its intent, the lines to place, the seconds frame."""
    from .director_two_pass import frame_of, kept_lines
    scenes = [s for s in intent.get("scenes") or [] if isinstance(s, dict)]
    sc = next(s for s in scenes if s.get("idx") == scene_idx)
    idxs = [s.get("idx") for s in scenes]
    where = " và ".join((["cảnh ĐẦU phim — mở bằng `hook`"] if scene_idx == idxs[0] else [])
                        + (["cảnh CUỐI phim — kết bằng `ending`"] if scene_idx == idxs[-1] else []))
    lo, hi = frame_of(sc)
    lines = kept_lines(sc)
    said = ("\n".join(f"{k}. {who}: {text}" for k, (who, text) in enumerate(lines, 1)) if lines
            else "(cảnh này không có câu thoại nào được giữ — không đặt thoại vào shot)")
    return (f"# Việc lần này: Quay phim chia shot Cảnh {scene_idx}" + (f" ({where})" if where else "") + "\n"
            f"Khung giây của cảnh: tổng `duration_s` các shot trong **{lo:g}–{hi:g} giây** (Đạo diễn đặt `target_s` = {sc.get('target_s')}).\n"
            f"Trọng tâm: {sc.get('focus') or '(không ghi)'} · độ mạnh khoảnh khắc: {sc.get('peak') or '(không ghi)'}.\n"
            "Câu thoại được giữ — mỗi câu đúng một lần, nguyên văn, đúng người nói, đúng thứ tự này (câu lệch là bị trả lại):\n" + said + "\n"
            + "# Ý đồ cảnh này\n```json\n" + json.dumps(sc, ensure_ascii=False, indent=1) + "\n```\n"
            + f"Trả về **một JSON duy nhất**: `{{\"idx\": {scene_idx}, \"shots\": [...], \"tradeoffs\": []}}` theo mọi luật ở trên."
            + (f"\nLý do chia lại: {note}" if note else "")
            + ("\nKế hoạch hiện tại của cảnh này (để biết đang có gì):\n" + json.dumps(current, ensure_ascii=False) if current else ""))


def build_dp_bundle(pipeline: Pipeline, project_id: int, intent: dict, scene_idx: int, note: str = "", current=None,
                    common: Optional[str] = None) -> str:
    """Tầng B prompt of one scene: the shared part (pass `common` to reuse the exact same text — the cache only hits on identical
    bytes) + cache mark + the scene's task."""
    return (common if common is not None else dp_common(pipeline, project_id, intent)) + CACHE_BREAK + dp_scene_task(
        pipeline, project_id, intent, scene_idx, note, current)


def _location_block(pipeline: Pipeline, project_id: int) -> str:
    from . import location_pack
    return location_pack.director_block(pipeline.conn, project_id)


MODEL_RULES_MARK = "<!-- model_rules -->"


_SHOT_ONLY = re.compile(r"<!-- shot -->.*?<!-- /shot -->\n?", re.S)
_INTENT_ONLY = re.compile(r"<!-- intent: (.*?) -->", re.S)


def role_text(name: str, intent_only: bool = False) -> str:
    """A role book of knowledge/roles/. The DP's model limits (dp.md Q4) are not copied by hand: the mark is replaced by the lines of
    data/provider_rules.json (core/video_rules.summary_lines) — the same table the adapters check before sending.
    intent_only (Tầng A of director_two_pass): the parts marked <!-- shot -->…<!-- /shot --> (fields the DP writes per shot) are cut
    and the <!-- intent: … --> notes shown instead, so the Director does not read ~a page of shot orders it may not follow (grader
    2026-09-26). Otherwise the intent notes are dropped and the marks removed."""
    text = _read("knowledge", "roles", name)
    if intent_only:
        text = _INTENT_ONLY.sub(lambda m: m.group(1), _SHOT_ONLY.sub("", text))
    else:
        text = _INTENT_ONLY.sub("", text).replace("<!-- shot -->", "").replace("<!-- /shot -->", "")
    if MODEL_RULES_MARK in text:
        from . import video_rules
        text = text.replace(MODEL_RULES_MARK, "\n".join(video_rules.summary_lines()))
    return text


def script_preamble(proj) -> str:
    """What the script says before its first scene (title, length, cast, setting such as "Map Đảo Quân Sự — Tháp Đồng Hồ"): it
    applies to every scene, so the Director gets it too."""
    from .script_parser import _SEPARATOR, is_heading
    text = (proj["script_text"] if "script_text" in proj.keys() else None) or ""
    head = []
    for row in text.splitlines():
        if is_heading(row):
            break
        if row.strip() and not _SEPARATOR.match(row):
            head.append(row.strip())
    return ("# Thông tin chung của kịch bản (trước cảnh đầu tiên — áp dụng cho mọi cảnh)\n" + "\n".join(head)) if head else ""


def standard_block(pipeline: Pipeline, project_id: int, names=None) -> str:
    """T1: characters whose look is fixed in the library. The Director writes the story around them, never a new appearance.
    names: these characters instead of the stored Bible (GĐ5 Tầng B: the Bible Tầng A just wrote is not stored yet)."""
    rows = []
    if names is None:
        names = [r["name"] for r in pipeline.conn.execute("SELECT name FROM characters WHERE project_id=?", (project_id,))]
    for name in names:
        prof = assets.standard_for(pipeline.conn, project_id, name)
        if prof:
            rows.append(f"- **{name}** ({prof['asset']}): {prof.get('identity') or ''} — giữ: {prof.get('must_keep') or ''}"
                        + (f"; cao ~{prof['height_m']:g} m" if prof.get("height_m") else ""))
    return ("# Hồ sơ chuẩn nhân vật (Kho — đã duyệt, KHÔNG viết lại ngoại hình; chỉ ghi biến thể của video này như trang phục/bị thương)\n"
            + "\n".join(rows)) if rows else ""


def lock_text(conn, project_id: int, names=None) -> str:
    """Character Lock of the characters (all, or the given names) as a readable block."""
    rows = []
    for r in conn.execute("SELECT name, lock_rules FROM characters WHERE project_id=?", (project_id,)):
        if names is not None and r["name"] not in names:
            continue
        lock, source = assets.standard_for(conn, project_id, r["name"]), " (hồ sơ chuẩn Kho)"   # T1: the library profile wins
        if lock is None:
            source = ""
            try:
                lock = json.loads(r["lock_rules"]) if r["lock_rules"] else None
            except ValueError:
                lock = None
        if not lock:
            continue
        size = f"; cao ~{lock['height_m']:g} m" if lock.get("height_m") else ""
        size += f", {lock['build']}" if lock.get("build") else ""
        rows.append(f"- **{r['name']}**{source} — giữ: {lock.get('must_keep', '')}; được đổi: {lock.get('may_change', '')}; "
                    f"cấm lệch: {lock.get('forbidden', '')}{size}")
    return ("# Character Lock\n" + "\n".join(rows)) if rows else ""


def short_lock_block(conn, project_id: int) -> str:
    """V4 4.4 (feature profile_digest): the ≤ 200-character form of each approved profile — the words the motion prompt carries for
    a character (a Kling multi-shot prompt holds 512 characters in all, the full Lock does not fit)."""
    from . import features, profile_digest
    if not features.on("profile_digest"):
        return ""
    rows = []
    for r in conn.execute("SELECT name FROM characters WHERE project_id=?", (project_id,)):
        text = profile_digest.for_character(conn, project_id, r["name"], "lock_short")
        if text:
            rows.append(f"- **{r['name']}**: {text}")
    return ("# Nhận diện ngắn (hồ sơ chuẩn rút gọn ≤ 200 ký tự — motion prompt chỉ nhắc nhân vật bằng các chữ này, không chép Lock dài)\n"
            + "\n".join(rows)) if rows else ""


_ROLE_LABEL = {"location": "địa điểm", "object": "đạo cụ", "character": "nhân vật",
               "layout": "LAYOUT — bố cục dựng sẵn: góc máy, vị trí, cỡ và hướng mặt mong muốn; người là hình nộm/ảnh cắt dán"}


def qc_references(pipeline: Pipeline, project_id: int, idx: int, scene_data: dict, data_dir: Optional[str] = None) -> List[dict]:
    """The reference pictures the QC agent compares against: the scene's layout first (when it was laid out), then the same
    character/place/object pictures the image model got."""
    from .layout import layout_reference
    lay = layout_reference(data_dir, project_id, idx, scene_data) if data_dir else None
    return ([lay] if lay else []) + assets.scene_references(pipeline.conn, project_id, scene_data)


def _reference_block(refs: List[dict]) -> str:
    if not refs:
        return ""
    return "# Ảnh tham chiếu (đính kèm sau ảnh cần chấm, theo thứ tự)\n" + "\n".join(
        f"{i}. {r['label']} ({_ROLE_LABEL.get(r['role'], 'nhân vật')})" for i, r in enumerate(refs, 1))


def build_qc_bundle(pipeline: Pipeline, scene_id: int, data_dir: Optional[str] = None) -> str:
    scene = pipeline.conn.execute("SELECT * FROM scenes WHERE id=?", (scene_id,)).fetchone()
    chars = pipeline.conn.execute(
        "SELECT name, description, wardrobe FROM characters WHERE project_id=?",
        (scene["project_id"],)).fetchall()
    bible = "\n".join(f"- {c['name']}: {c['description']} {c['wardrobe'] or ''}".strip() for c in chars)
    data = json.loads(scene["data"] or "{}")
    refs = qc_references(pipeline, scene["project_id"], scene["idx"], data, data_dir)
    spec = {k: data.get(k) for k in _SCENE_KEYS}
    spec.update({k: data[k] for k in _SHOT_KEYS if k in data})
    if spec.get("performance"):
        from . import performance
        spec["performance"] = performance.for_prompt(data)
    return _cached([                                     # same for every picture of every project
        _read("prompts", "02_qc_agent.md"),
        "" if "knowledge/ai_image_failure_modes.md" in knowledge.folded_builtin("qc")
        else _read("knowledge", "ai_image_failure_modes.md"),
        _read("knowledge", "character_lock.md"),
        knowledge.user_text("qc"),
    ], [                                                 # same for every picture of this project
        looks.qc_note(pipeline.project(scene["project_id"])),
        world_bible_text(pipeline, scene["project_id"]),
        "# Character Bible\n" + bible,
    ], [                                                 # this shot
        lock_text(pipeline.conn, scene["project_id"], data.get("characters")),
        "# Thông số cảnh\n" + json.dumps(spec, ensure_ascii=False, indent=2),
        _reference_block(refs),
        "(Đính kèm ảnh cần chấm điểm" + (", rồi các ảnh tham chiếu." if refs else ".") + ")",
    ])


def video_family(pipeline: Pipeline, project_id: int):
    """'omni' (Kling), 'seedance', or None when the project's video model is unset/unknown."""
    from .adapters.clipai import resolve_model
    from .providers import ProviderError
    try:
        return resolve_model(pipeline.project(project_id)["video_model"])[1]
    except ProviderError:
        return None


def motion_scene_rows(pipeline: Pipeline, project_id: int, only_missing: bool = False, only_idx=None):
    """Scenes with an approved image; only_missing: without a motion prompt yet; only_idx: exactly these scenes (e.g. the ones
    whose prompt is outdated)."""
    from .shots import image_scene
    conn = pipeline.conn
    rows = conn.execute(
        "SELECT s.id, s.idx, s.data FROM scenes s WHERE s.project_id=?"
        + (" AND NOT EXISTS (SELECT 1 FROM motion_prompts m WHERE m.scene_id=s.id)" if only_missing else "")
        + " ORDER BY s.idx", (project_id,)).fetchall()
    rows = [r for r in rows if conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'",
                                             (image_scene(conn, r["id"]),)).fetchone()]   # v3 multi-shot: the group's picture
    return [r for r in rows if only_idx is None or r["idx"] in only_idx]


def build_motion_bundle(pipeline: Pipeline, project_id: int, only_missing: bool = False, only_idx=None) -> str:
    """Step 3: scenes that have an approved image, with their spec, the model each will use and the character descriptions.
    only_missing: skip scenes that already have a motion prompt (used by the API runner); only_idx: just these scenes."""
    from . import model_router
    conn = pipeline.conn
    rows = motion_scene_rows(pipeline, project_id, only_missing, only_idx)
    chars = conn.execute("SELECT name, description, wardrobe FROM characters WHERE project_id=?", (project_id,)).fetchall()
    profiles = model_router.load_profiles()["models"]
    all_scenes = {r["idx"]: json.loads(r["data"] or "{}") for r in conn.execute(
        "SELECT idx, data FROM scenes WHERE project_id=?", (project_id,))}

    def extra(r) -> dict:
        data = json.loads(r["data"] or "{}")
        out = {}
        need = dialogue.needed_seconds(dialogue.scene_lines(data))
        if need:
            out["dialogue_min_sec"] = need
        choice = model_router.scene_choice(conn, r["id"])
        out["video_model"] = choice["model"]
        out["max_sec"] = (profiles.get(choice["model"]) or {}).get("max_sec", 15)
        from . import shots
        if shots.mode(pipeline.project(project_id)) == "multishot":
            group = shots.multishot_group_of(conn, r["id"]) or []
            if len(group) > 1:                 # M9: the real limits of a Kling multi-shot request, not the single-clip ones
                out.update(multishot_group=[g["idx"] for g in group], prompt_max_chars=512, group_max_sec=shots.MULTISHOT_MAX,
                           video_model="kling")
        from . import motion_physics
        body = motion_physics.sentence(str(data.get("action") or ""))
        if body:                               # S4.4: the physics of this kind of action, for the writer to keep (not a formula)
            out["physics_hint"] = body
        prev = all_scenes.get(r["idx"] - 1) or {}
        if data.get("sequence") and prev.get("sequence") == data.get("sequence") and prev.get("spatial_state"):
            out["previous_spatial_state"] = prev["spatial_state"]
        return out

    scenes = [{"idx": r["idx"], **{k: v for k, v in json.loads(r["data"] or "{}").items() if k in _SCENE_KEYS or k in _SHOT_KEYS},
               **extra(r)}
              for r in rows]
    from . import performance
    for s in scenes:
        if s.get("performance"):
            s["performance"] = performance.for_prompt(s)          # + shown_intensity: the strength to act (close-up one step less)
    payload = {"characters": [dict(c) for c in chars], "scenes": scenes}
    folded = knowledge.folded_builtin("motion")
    complexity_known = any(s.get("camera_complexity") for s in scenes)
    any_complex = any(s.get("camera_complexity") == "complex" for s in scenes)
    uses_seedance = any("seedance" in (s.get("video_model") or "") for s in scenes) or video_family(pipeline, project_id) == "seedance"
    parts = [_read("prompts", "03_video_motion.md"), looks.motion_note(pipeline.project(project_id))]
    for rel in ("video_motion_vocab.md", "research_notes.md", "t2v_prompt_structure.md"):
        if f"knowledge/{rel}" not in folded:
            parts.append(_read("knowledge", rel))
    if (any_complex or not complexity_known) and "knowledge/motion_complex_shots.md" not in folded:
        parts.append(_read("knowledge", "motion_complex_shots.md"))
    if any_complex:
        parts.append(_read("knowledge", "motion_prompt_lint.md"))
    if "knowledge/ff_character_skills_visual.md" not in folded:
        ff = knowledge.ff_skills_for(people_in_project(pipeline, project_id))
        if ff:
            parts.append(ff)
    skill = _skill_block(people_in_project(pipeline, project_id))
    if skill:
        parts.append(skill)
    lock = lock_text(conn, project_id)
    if lock:
        parts.append(lock)
    short = short_lock_block(conn, project_id)
    if short:
        parts.append(short)
    if uses_seedance:
        for rel in ("seedance_prompting.md", "seedance_director_workflow.md"):
            if f"knowledge/{rel}" not in folded:
                parts.append(_read("knowledge", rel))
    wb = world_bible_text(pipeline, project_id)
    if wb:
        parts.append(wb)
    extra = knowledge.user_text("motion")
    return _SEP.join([x for x in parts if x] + ([extra] if extra else [])) + CACHE_BREAK + (       # rules repeat between batches (C2)
        "# Cảnh đã có ảnh được duyệt\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```")
