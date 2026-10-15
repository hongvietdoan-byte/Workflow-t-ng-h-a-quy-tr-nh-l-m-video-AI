"""15/10 (#31): giây đọc theo (giọng, tốc độ) — MỘT hàm cho mọi chỗ ước giây; nghỉ đúng như khâu dựng (một BREATH mỗi lượt lời, khoảng
thật giữa hai câu); tốc độ chỉ rút ước tính khi model đã đo là đọc theo speed (eleven_v3: không); giọng đo chậm làm ước tính dài ra,
không bao giờ ngắn đi; tốc độ lời dẫn của dự án (Bước 1) vào hồ sơ LỜI DẪN khi lập Bible; lưới an toàn sau TTS (shot không ngắn hơn
giọng thật). Không gọi dịch vụ nào."""
import json
import os
import tempfile
from types import SimpleNamespace
from unittest import mock

import pytest

from core import audio_lib, dialogue, pacing, prompts, shot_normalize, voice
from core.db import connect
from core.pipeline import Pipeline

N1 = "Bốn đối thủ ập tới từ bốn phía."          # 8 âm tiết
N2 = "Không ai biết chuyện gì."                  # 5
N3 = "Cánh cửa đóng lại."                        # 4


def _old(rows):
    """The formula of before 15/10: each line its own breath (scene sums), n / RATE + BREATH."""
    return round(sum(round(dialogue.syllables(s) / dialogue.RATE + dialogue.BREATH, 1) for _, s in rows if dialogue.syllables(s)), 1)


def _project(pacing_value=None, text="LỜI DẪN: " + N1):
    p = Pipeline(connect())
    pid = p.create_project("speech")
    p.conn.execute("UPDATE projects SET shot_mode='per_shot', script_text=? WHERE id=?", (text, pid))
    p.conn.execute("INSERT INTO story_scenes (project_id, idx, heading, text, data) VALUES (?,1,'Cảnh 1',?,'{}')", (pid, text))
    if pacing_value:
        p.set_project_field(pid, "pacing", pacing_value)
    p.conn.commit()
    return p, pid


@pytest.fixture
def table():
    """A speech_rates table for one test (the real file is left alone)."""
    def use(data):
        dialogue._RATES_CACHE["v"] = data
    yield use
    dialogue._RATES_CACHE.clear()


# ---- 1. một hàm, công thức một câu giữ nguyên ------------------------------------------------------------------------------------
def test_one_line_is_exactly_the_old_formula():
    for s in (N1, N2, N3, "Ừ."):
        assert dialogue.needed_seconds([("KELLY", s)]) == round(dialogue.syllables(s) / dialogue.RATE + dialogue.BREATH, 1)
    assert dialogue.line_seconds(N1) == pytest.approx(8 / dialogue.RATE)


def test_gaps_are_the_edit_gaps():
    assert dialogue.LINE_GAP == voice.GAP                       # one clip: the next line comes GAP after the last (voice.layout)
    p, pid = _project("fast")
    assert dialogue.speech_ctx(p.conn, pid)["gap"] == pacing.FAST_LINE_GAP
    p2, pid2 = _project()
    assert dialogue.speech_ctx(p2.conn, pid2)["gap"] == dialogue.LINE_GAP


# ---- 3. BREATH: một lượt lời một hơi -----------------------------------------------------------------------------------------------
def test_split_narration_gets_one_breath_per_turn_not_per_sentence():
    rows = [("LỜI DẪN", N1), ("LỜI DẪN", N2), ("LỜI DẪN", N3)]
    want = round(17 / dialogue.RATE + dialogue.BREATH + 2 * dialogue.LINE_GAP, 1)
    assert dialogue.scene_seconds(rows) == want                          # 5.6 (before: 3 breaths = 6.3)
    assert dialogue.scene_seconds(rows) < _old(rows)
    fast = {"voices": {}, "narration_speed": None, "gap": pacing.FAST_LINE_GAP}
    assert dialogue.scene_seconds(rows, fast) == round(17 / dialogue.RATE + dialogue.BREATH + 2 * pacing.FAST_LINE_GAP, 1)


def test_alternating_speakers_keep_the_old_numbers():
    rows = [("KELLY", N1), ("MAXIM", N2), ("KELLY", N3)]
    assert dialogue.scene_seconds(rows) == _old(rows)


def test_a_shot_with_two_lines_counts_the_real_gap():
    rows = [("LỜI DẪN", N1), ("LỜI DẪN", N2)]
    assert dialogue.needed_seconds(rows) == round(13 / dialogue.RATE + dialogue.BREATH + dialogue.LINE_GAP, 1)


def test_numbers_are_counted_as_read():
    assert dialogue.needed_seconds([("X", "Năm 2025")]) == round(8 / dialogue.RATE + dialogue.BREATH, 1)   # hai nghìn không trăm hai mươi lăm


# ---- 2. tốc độ / giọng -------------------------------------------------------------------------------------------------------------
def test_eleven_v3_speed_does_not_shorten_the_estimate(table):
    table({"speed_follows": {"eleven_v3": False}})
    v3 = {"voice_id": 72, "model": "eleven_v3", "speed": 1.2}
    assert dialogue.line_seconds(N1, v3) == dialogue.line_seconds(N1)
    table({"speed_follows": {"eleven_v3": True}})               # only once measured as following the speed
    assert dialogue.line_seconds(N1, v3) == pytest.approx(8 / (dialogue.RATE * 1.2))


def test_the_real_table_says_v3_does_not_follow_speed():
    dialogue._RATES_CACHE.clear()
    assert dialogue._rates()["speed_follows"]["eleven_v3"] is False


def test_a_measured_slow_voice_lengthens_a_fast_one_never_shortens(table):
    table({"min_n": 8, "voices": {"70": {"n": 10, "p10": 2.0}, "72": {"n": 16, "p10": 4.2}, "69": {"n": 3, "p10": 1.0}}})
    assert dialogue.voice_rate(70) == 2.0
    assert dialogue.voice_rate(72) == dialogue.RATE              # faster than RATE: estimate unchanged (never shorter)
    assert dialogue.voice_rate(69) == dialogue.RATE              # too few samples
    assert dialogue.voice_rate(None) == dialogue.RATE
    ctx = {"voices": {"KELLY": {"voice_id": 70, "model": "eleven_v3"}}, "gap": dialogue.LINE_GAP}
    assert dialogue.needed_seconds([("KELLY", N1)], ctx) == round(8 / 2.0 + dialogue.BREATH, 1)


def test_narration_speed_setting_reaches_ctx_and_the_narrator_profile(table):
    p, pid = _project()
    assert dialogue.speech_ctx(p.conn, pid)["narration_speed"] is None
    p.set_project_field(pid, "narration_speed", 1.2)
    ctx = dialogue.speech_ctx(p.conn, pid)
    assert ctx["narration_speed"] == 1.2 and dialogue.voice_of(ctx, "LỜI DẪN") == {"speed": 1.2}
    assert dialogue.voice_of(ctx, "KELLY") is None
    table({"speed_follows": {"eleven_v3": False}})
    assert dialogue.needed_seconds([("LỜI DẪN", N1)], ctx) == dialogue.needed_seconds([("LỜI DẪN", N1)])
    for n in ("LỜI DẪN", "KELLY"):
        p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (pid, n, n))
    voice.set_profile(p.conn, pid, "LỜI DẪN", {"voice_id": 72, "voice_name": "boy", "model": "eleven_v3"})
    voice.set_profile(p.conn, pid, "KELLY", {"voice_id": 70, "voice_name": "girl", "model": "eleven_v3"})
    prof = voice.profiles(p.conn, pid)
    assert prof["LỜI DẪN"]["speed"] == 1.2 and "speed" not in prof["KELLY"]
    voice.set_profile(p.conn, pid, "LỜI DẪN", {"voice_id": 72, "voice_name": "boy", "model": "eleven_v3", "speed": None})
    assert "speed" not in voice.profiles(p.conn, pid)["LỜI DẪN"]          # the person removed it: not put back
    assert dialogue.speech_ctx(p.conn, pid)["voices"]["LỜI DẪN"] == {"voice_id": 72, "model": "eleven_v3", "speed": None}


# ---- 2. mọi chỗ ước giây dùng cùng hàm ----------------------------------------------------------------------------------------------
def test_director_prompt_uses_one_breath_per_turn():
    p, pid = _project(text=f"LỜI DẪN: {N1}\nLỜI DẪN: {N2}\nLỜI DẪN: {N3}")
    want = dialogue.scene_seconds([("LỜI DẪN", N1), ("LỜI DẪN", N2), ("LỜI DẪN", N3)])
    block = prompts.duration_block(p, pid)
    assert f"thoại 3 câu cần ~{want:g} giây nói" in block and f"+ {dialogue.LINE_GAP:g} giây giữa hai câu" in block
    assert f"thoại 3 câu cần ~{want:g} giây nói (≈ số âm tiết ÷ 3.5; + 0.5 s mỗi lượt lời" in prompts.intent_frame_block(p, pid)


def test_normalize_and_report_use_the_project_voice(table):
    table({"min_n": 8, "voices": {"70": {"n": 10, "p10": 2.0}}})
    ctx = {"voices": {"KELLY": {"voice_id": 70, "model": "eleven_v3"}}, "gap": dialogue.LINE_GAP}
    obj = {"scenes": [{"idx": 1, "shots": [{"size": "MCU", "duration_s": 3.0, "dialogue": [{"speaker": "KELLY", "text": N1}]}]}]}
    out, _ = shot_normalize.normalize(obj, "", None, ctx=ctx)
    assert out["scenes"][0]["shots"][0]["duration_s"] == 4.5                 # 8 / 2,0 + 0,5 (3,5 âm/s would give 2,8 → kept 3)
    plain, _ = shot_normalize.normalize(obj, "")
    assert plain["scenes"][0]["shots"][0]["duration_s"] == 3.0


def test_check_plan_reads_speed_only_when_the_model_follows_it(table):
    p, pid = _project("fast")
    sid = p.create_scene(pid, 1, "shot 1")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": 1, "story_scene": 1, "duration_s": 4.5, "dialogue": [
        {"speaker": "LỜI DẪN", "text": "Bốn đối thủ ập tới từ bốn phía"}]}, ensure_ascii=False), sid))
    p.conn.execute("INSERT INTO characters (project_id, name, description, voice_profile) VALUES (?,?,?,?)",
                   (pid, "LỜI DẪN", "", json.dumps({"voice_id": 72, "model": "eleven_v3", "speed": 1.2})))
    p.conn.commit()
    table({"speed_follows": {"eleven_v3": False}})
    assert pacing.check_plan(p, pid, record=False)[0]["speech_s"] == 2.3       # v3 measured: 1,2 does not read faster
    table({"speed_follows": {"eleven_v3": True}})
    assert pacing.check_plan(p, pid, record=False)[0]["speech_s"] == 1.9


# ---- 4. lưới an toàn sau TTS -------------------------------------------------------------------------------------------------------
def _voiced(p, pid, data_dir, sid, ms):
    d = audio_lib.assets_dir(data_dir, pid)
    with open(os.path.join(d, "assets.json"), "w", encoding="utf-8") as f:
        json.dump([{"kind": "tts", "state": "succeeded", "scene_id": sid, "line": 1, "duration_ms": ms, "file": "a.mp3",
                    "dialogue": True, "text": N1}], f)


def test_over_model_max_names_the_shot_whose_voice_no_clip_can_hold():
    p, pid = _project()
    sid = p.create_scene(pid, 1, "S1")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"dialogue": [{"speaker": "KELLY", "text": N1}]},
                                                                      ensure_ascii=False), sid))
    p.conn.commit()
    d = tempfile.mkdtemp()
    _voiced(p, pid, d, sid, 9000)
    with mock.patch("core.dialogue.max_clip_seconds", return_value=10):
        assert voice.over_model_max(p.conn, pid, d) == []
    with mock.patch("core.dialogue.max_clip_seconds", return_value=8):
        got = voice.over_model_max(p.conn, pid, d)
    assert got == [{"scene_id": sid, "idx": 1, "need": round(voice.LEAD + 9.0, 2), "max": 8}]


def test_multishot_shot_gets_its_voice_stretched_seconds():
    from core.runner import VideoRunner
    row = {"id": 1, "data": {"duration_s": 3.2}}
    fake = SimpleNamespace(_cut_seconds=lambda r: 6.3)
    assert VideoRunner._billed_seconds(fake, row) == 7                    # before: shots.billed_shot_seconds = 4
    fake = SimpleNamespace(_cut_seconds=lambda r: 2.0)
    assert VideoRunner._billed_seconds(fake, row) == 4
