"""14/10 nhịp nhanh, ít khoảng lặng (projects.pacing, core/pacing.py) — normal giữ y cũ; fast: prompt Đạo diễn/Biên kịch, kiểm sau
Đạo diễn (diag vàng có số liệu), đặt lời trên trục thời gian (≤ 0,25 s giữa hai câu), cắt lặng cuối shot có lời."""
import json
import os
import tempfile
from unittest import mock

import pytest

from core import audio_lib, dialogue, pacing, project_defaults, prompts, voice
from core.db import connect
from core.pipeline import Pipeline


def _project(pacing_value=None, created_by="a@x"):
    p = Pipeline(connect())
    pid = p.create_project("nhip", created_by=created_by)
    p.conn.execute("UPDATE projects SET shot_mode='per_shot', script_text=? WHERE id=?",
                   ("CẢNH 1\nLỜI DẪN: Bốn đối thủ ập tới từ bốn phía.\n", pid))
    p.conn.execute("INSERT INTO story_scenes (project_id, idx, heading, text, data) VALUES (?,1,'Cảnh 1',?,'{}')",
                   (pid, "LỜI DẪN: Bốn đối thủ ập tới từ bốn phía."))
    if pacing_value is not None:
        p.set_project_field(pid, "pacing", pacing_value)
    p.conn.commit()
    return p, pid


def _shot(p, pid, idx, shot_no, dur, line=None, scene=1):
    sid = p.create_scene(pid, idx, f"shot {shot_no}")
    data = {"shot_no": shot_no, "story_scene": scene, "duration_s": dur,
            "dialogue": [{"speaker": "LỜI DẪN", "text": line}] if line else []}
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
    p.conn.commit()
    return sid


# ---- 1. thiết lập dự án ------------------------------------------------------------------------------------------------------------
def test_default_is_normal_and_value_is_stored():
    p, pid = _project()
    assert pacing.of(p.project(pid)) == "normal" and not pacing.is_fast(p.project(pid))
    p.set_project_field(pid, "pacing", "fast")
    assert pacing.of(p.project(pid)) == "fast"
    p.conn.execute("UPDATE projects SET pacing='weird' WHERE id=?", (pid,))
    assert pacing.of(p.project(pid)) == "normal"


def test_new_project_does_not_inherit_fast():
    p, src = _project("fast")
    new = p.create_project("tập 3", created_by="a@x")
    copied = project_defaults.inherit(p.conn, new, "a@x")
    assert "pacing" not in copied and "pacing" not in project_defaults.INHERIT
    assert pacing.of(p.project(new)) == "normal"


# ---- 2. prompt -----------------------------------------------------------------------------------------------------------------------
def _bundles(p, pid):
    intent = {"characters": [], "scenes": [{"idx": 1}]}
    return [prompts.build_director_bundle(p, pid), prompts.build_intent_bundle(p, pid), prompts.dp_common(p, pid, intent)]


def test_normal_prompt_identical_and_fast_only_adds_the_block():
    p, pid = _project()
    unset = _bundles(p, pid)
    p.set_project_field(pid, "pacing", "normal")
    assert _bundles(p, pid) == unset                         # 'normal' == NULL, byte for byte
    assert all("NHANH, ít khoảng lặng" not in b for b in unset)
    p.set_project_field(pid, "pacing", "fast")
    block = pacing.director_block(p.project(pid))
    assert "≤ 0,6 s" in block and "J-cut" in block and "0,5 s" in block and "giữa một câu" in block and "1,5–3 s" in block
    for before, after in zip(unset, _bundles(p, pid)):
        assert block in after
        # 15/10: the one other change of a fast project — sentences of one turn are FAST_LINE_GAP apart (0,2 s, not 0,15 s)
        before = before.replace(f"+ {dialogue.LINE_GAP:g} s giữa hai câu liền nhau", f"+ {pacing.FAST_LINE_GAP:g} s giữa hai câu liền nhau")
        assert after.replace(block + prompts._SEP, "", 1) == before or after.replace(prompts._SEP + block, "", 1) == before


def test_screenwriter_block_only_when_fast():
    from core import idea_to_script
    p, pid = _project()
    state = {"inputs": {"idea": "x", "duration_s": 30, "aspect": "9:16", "platform": "TikTok"}}
    normal = idea_to_script.build_prompt(p.conn, pid, state, 1)
    assert "NHANH, ít khoảng lặng" not in normal
    p.set_project_field(pid, "pacing", "fast")
    fast = idea_to_script.build_prompt(p.conn, pid, state, 1)
    sw = pacing.screenwriter_block(p.project(pid))
    assert sw in fast and fast.replace("\n\n" + sw, "", 1) == normal
    assert "## Đạo diễn" not in sw and "## Biên kịch" not in sw     # the heading of the file is never sent as content


# ---- 3. kiểm sau Đạo diễn ---------------------------------------------------------------------------------------------------------
def test_check_plan_warns_with_numbers_and_reads_voice_speed():
    p, pid = _project("fast")
    line = "Bốn đối thủ ập tới từ bốn phía"           # 8 âm tiết → 2,29 s ở 3,5 âm tiết/s
    _shot(p, pid, 1, 1, 4.5, line)
    _shot(p, pid, 2, 2, 1.0)
    found = pacing.check_plan(p, pid)
    assert len(found) == 1 and found[0]["speech_s"] == 2.3 and found[0]["shots_s"] == 5.5 and found[0]["gap_s"] == 3.2
    assert found[0]["long_shots"] == [{"shot_no": 1, "duration_s": 4.5, "speech_s": 2.3}]
    rows = p.conn.execute("SELECT severity, message, code FROM diag_events WHERE project_id=? AND code='pacing_gap'", (pid,)).fetchall()
    assert rows and rows[0]["severity"] == "warn" and "5.5 s" in rows[0]["message"] and "#1 4.5 s" in rows[0]["message"]
    # 15/10: the narrator's voice set to 1,2 on eleven_v3 — measured on #8/#24/#27: v3 does not read faster with speed, so the estimate
    # stays 8 / 3,5 = 2,29 s; the speed counts only for a model measured as following it
    # (tests/test_speech_time.py::test_check_plan_reads_speed_only_when_the_model_follows_it). A fixed table (no measured row for voice
    # 72): the real data/speech_rates.json is re-measured over time (vòng gop-1510: p50 on speech seconds) and must not move this check.
    dialogue._RATES_CACHE["v"] = {"min_n": 8, "voices": {}, "speed_follows": {"eleven_v3": False}}
    p.conn.execute("INSERT INTO characters (project_id, name, description, voice_profile) VALUES (?,?,?,?)",
                   (pid, "LỜI DẪN", "", json.dumps({"voice_id": 72, "speed": 1.2})))
    p.conn.commit()
    try:
        assert pacing.check_plan(p, pid, record=False)[0]["speech_s"] == 2.3
    finally:
        dialogue._RATES_CACHE.clear()


def test_check_plan_quiet_when_tight_and_off_when_normal():
    p, pid = _project("fast")
    _shot(p, pid, 1, 1, 2.3, "Bốn đối thủ ập tới từ bốn phía")
    assert pacing.check_plan(p, pid) == []
    p2, pid2 = _project()
    _shot(p2, pid2, 1, 1, 9.0, "Bốn đối thủ ập tới từ bốn phía")
    assert pacing.check_plan(p2, pid2) == []


def test_voice_speed_soft_read():
    assert pacing.voice_speed(None) == 1.0 and pacing.voice_speed({"speed": "x"}) == 1.0
    assert pacing.voice_speed({"variant": {"pitch": 2, "speed": 1.1}}) == 1.1 and pacing.voice_speed({"speed": 1.2}) == 1.2


# ---- 4. khâu dựng --------------------------------------------------------------------------------------------------------------------
def _voiced(p, pid, n=2, ms=1000):
    data = tempfile.mkdtemp()
    sids = [_shot(p, pid, i, i, 3.0, "câu") for i in range(1, n + 1)]
    directory = audio_lib.assets_dir(data, pid)
    os.makedirs(directory, exist_ok=True)
    audio_lib._save(directory, [{"kind": "tts", "scene_id": sid, "line": 1, "speaker": "LỜI DẪN", "state": "succeeded",
                                 "file": f"t{i}.mp3", "duration_ms": ms, "dialogue": True} for i, sid in enumerate(sids, 1)])
    rows = [{"idx": i, "scene_id": sid, "path": os.path.join(data, f"{i}.mp4"), "requested_sec": 3.0, "usable": True}
            for i, sid in enumerate(sids, 1)]
    return data, sids, rows


def _starts(data, pid):
    return [e["start"] for e in audio_lib.load(audio_lib.assets_dir(data, pid))]


@pytest.mark.parametrize("fast", [False, True])
def test_lines_on_timeline(fast, monkeypatch):
    monkeypatch.setenv("FEATURE_J_CUT", "0")
    p, pid = _project("fast" if fast else None)
    data, _, rows = _voiced(p, pid)
    with mock.patch("core.final_cut.collect_clips_for_render", return_value=rows):
        durations, _ = pacing.tighten(p.conn, pid, data, rows, [3.0, 3.0])
        voice.place_on_timeline(p.conn, pid, data, durations=durations)
    starts = _starts(data, pid)
    if not fast:
        assert durations == [3.0, 3.0] and starts == [voice.LEAD, 3.0 + voice.LEAD]      # y cũ
    else:
        assert durations[0] == round(voice.LEAD + 1.0 + pacing.FAST_TAIL_MAX, 2)
        # rà 14/10: shot 2's line came in before the cut → its tail is cut from where the line really ends (not LEAD + line)
        assert durations[1] == round(max(starts[1] + 1.0 - durations[0] + pacing.FAST_TAIL_MAX, pacing.FAST_MIN_SHOT), 2) == 1.2
        gap = starts[1] - (starts[0] + 1.0)
        assert 0 < gap <= 0.25 + 1e-9
        assert starts[1] >= durations[0] - pacing.FAST_J_MAX - 1e-9                        # gối tiếng tối đa 0,5 s trước cú cắt


def test_tighten_keeps_silent_lipsynced_and_person_edited_shots():
    p, pid = _project("fast")
    data, sids, rows = _voiced(p, pid, n=2)
    silent = _shot(p, pid, 3, 3, 4.0)
    rows = rows + [{"idx": 3, "scene_id": silent, "path": os.path.join(data, "3.mp4"), "requested_sec": 4.0, "usable": True}]
    out, changes = pacing.tighten(p.conn, pid, data, rows, [3.0, 3.0, 4.0], keep={sids[1]})
    assert out == [1.8, 3.0, 4.0] and [c["scene_id"] for c in changes] == [sids[0]]
    with mock.patch("core.lipsync.synced_scene_ids", return_value={sids[0]}):
        # shot 2 = same voice after a lip-synced shot: its line starts ON the cut (no J-in) → 1,0 s line + 0,5 s tail
        assert pacing.tighten(p.conn, pid, data, rows, [3.0, 3.0, 4.0])[0] == [3.0, 1.5, 4.0]
    p.set_project_field(pid, "pacing", None)
    assert pacing.tighten(p.conn, pid, data, rows, [3.0, 3.0, 4.0]) == ([3.0, 3.0, 4.0], [])


def test_missing_knowledge_section_is_an_error(monkeypatch, tmp_path):
    f = tmp_path / "k.md"
    f.write_text("# x\n## Đạo diễn\n\n", encoding="utf-8")
    monkeypatch.setattr(pacing, "_KNOWLEDGE", str(f))
    with pytest.raises(ValueError):
        pacing.director_block({"pacing": "fast"})
    assert pacing.director_block({"pacing": "normal"}) == ""


# ---- rà 14/10 (claude/pacing-fast-ra) ------------------------------------------------------------------------------------------------
def test_tighten_reapplied_on_already_short_durations_still_fits_the_clip():
    """editor_apply dựng lại với giây của bản trước (đã cắt đuôi) → shot vẫn phải vào `fit`, không thì cut ghép nguyên clip 3 s."""
    p, pid = _project("fast")
    data, sids, rows = _voiced(p, pid, n=1)
    out, changes = pacing.tighten(p.conn, pid, data, rows, [1.8])
    assert out == [1.8] and [c["scene_id"] for c in changes] == [sids[0]] and changes[0]["from_s"] == 3.0


def test_tighten_follows_where_the_line_really_starts():
    """câu shot trước tràn sang → câu shot này vào muộn hơn LEAD; cắt theo chỗ câu thật, không cắt dưới câu."""
    p, pid = _project("fast")
    data, sids, rows = _voiced(p, pid, n=2)
    directory = audio_lib.assets_dir(data, pid)
    items = audio_lib.load(directory)
    items[0]["duration_ms"] = 4000                  # 4 s line in a 3 s shot: spills 1,3 s into shot 2
    audio_lib._save(directory, items)
    out, _ = pacing.tighten(p.conn, pid, data, rows, [3.0, 3.0])
    assert out == [3.0, 3.0]                         # shot 2's line ends at 2,5 s of it (+0,5 s tail = 3,0) — nothing to cut


def test_tighten_never_below_the_crossfade():
    p, pid = _project("fast")
    data, sids, rows = _voiced(p, pid, n=3, ms=200)
    from core import final_cut
    out, _ = pacing.tighten(p.conn, pid, data, rows, [3.0, 3.0, 3.0], transition="crossfade", fade=1.0)
    assert final_cut.render_problems(out, "crossfade", 1.0) == [] and all(d < 3.0 for d in out)


def test_no_j_in_over_a_lipsynced_shot_of_the_same_speaker(monkeypatch):
    monkeypatch.setenv("FEATURE_J_CUT", "0")
    p, pid = _project("fast")
    data, sids, rows = _voiced(p, pid, n=2)
    with mock.patch("core.final_cut.collect_clips_for_render", return_value=rows), \
            mock.patch("core.lipsync.synced_scene_ids", return_value={sids[0]}):
        voice.place_on_timeline(p.conn, pid, data, durations=[3.0, 3.0])
    starts = _starts(data, pid)
    assert starts[1] >= 3.0                         # the same voice is never heard over the closed mouth of the lip-synced shot


def test_old_database_gets_the_column_and_clone_keeps_it():
    import sqlite3
    from core import compare, db
    p, pid = _project("fast")
    new = compare.clone_project(p, pid, "bản sao")
    assert pacing.of(p.project(new)) == "fast"
    conn = sqlite3.connect(":memory:")                      # a database from before the column: the migration adds it, NULL = normal
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO projects (name) VALUES ('cũ')")
    db._migrate_v2(conn)
    assert pacing.project_fast(conn, 1) is False and conn.execute("SELECT pacing FROM projects").fetchone()["pacing"] is None


def test_voice_speed_is_profile_times_variant_clamped():
    assert pacing.voice_speed({"speed": 0.8, "variant": {"pitch": 2, "speed": 1.1}}) == pytest.approx(0.88)
    assert pacing.voice_speed({"speed": 1.2, "variant": {"speed": 1.1}}) == 1.2
    assert pacing.voice_speed({"speed": 5}) == 1.2


def test_syllables_vietnamese_nfd_marks_and_numbers():
    import unicodedata
    line = "Bốn đối thủ ập tới — từ bốn phía…"
    assert pacing.syllables(line) == 8
    assert pacing.syllables(unicodedata.normalize("NFD", line)) == 8
    assert pacing.syllables("15 người") == 3 and pacing.syllables("có 100 bạn") == 4 and pacing.syllables("_ … —") == 0
    assert [pacing.syllables(n) for n in ("5", "10", "25", "105", "2025", "0")] == [1, 1, 3, 4, 7, 1]
