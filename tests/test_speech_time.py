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


def test_breath_is_the_edit_lead_and_tail():
    """Rà gop-1510 r2: phần đệm mỗi lượt lời khi ước giây = đúng LEAD + TAIL khâu dựng đặt (trước: 0,5 < 0,7 → ước hụt)."""
    assert dialogue.BREATH == pytest.approx(voice.LEAD + voice.TAIL) == pytest.approx(0.7)
    assert voice.LEAD is dialogue.LEAD and voice.TAIL is dialogue.TAIL


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


def test_a_measured_voice_uses_its_median_speed_with_a_floor(table):
    """Rà vòng gop-1510 mục 1: tốc độ giọng = p50 đo trên GIÂY NÓI (đã cắt lặng), sàn 0,8 × RATE; giọng nhanh được ước ngắn hơn RATE
    (trước: p10 + chỉ được dài ra → giọng 72 luôn dư ~1 s, giọng 70 câu 23 âm tiết ước 14,4 s)."""
    table({"min_n": 8, "voices": {"70": {"n": 10, "p10": 1.6, "p50": 3.0}, "72": {"n": 16, "p10": 3.6, "p50": 4.2},
                                  "69": {"n": 3, "p50": 1.0}, "71": {"n": 9, "p10": 1.0, "p50": 1.5}}})
    assert dialogue.voice_rate(70) == 3.0                        # p50, not p10
    assert dialogue.voice_rate(72) == 4.2                        # faster than RATE: measured, the estimate gets shorter
    assert dialogue.voice_rate(69) == dialogue.RATE              # too few samples
    assert dialogue.voice_rate(71) == pytest.approx(0.8 * dialogue.RATE)   # floor: one odd slow table never balloons the seconds
    assert dialogue.voice_rate(None) == dialogue.RATE
    ctx = {"voices": {"KELLY": {"voice_id": 70, "model": "eleven_v3"}}, "gap": dialogue.LINE_GAP}
    assert dialogue.needed_seconds([("KELLY", N1)], ctx) == round(8 / 3.0 + dialogue.BREATH, 1)


def _samples():
    with open(os.path.join(os.path.dirname(__file__), "fixtures", "speech_samples_1510.json"), encoding="utf-8") as f:
        return json.load(f)


def test_real_table_is_measured_on_speech_seconds_and_fits_each_voice():
    """Mục 1 (CAO — tiền): bảng thật data/speech_rates.json (tools/measure_speech_rate.py --write, audio TTS thật của máy chính, 0 USD)
    đo trên giây nói; với từng giọng đủ mẫu, trung vị (ước − độ dài file thật) ≤ +0,5 s; giọng 70 câu 23 âm tiết ≤ ~8 s."""
    dialogue._RATES_CACHE.clear()
    try:
        real = dialogue._rates()
        assert real.get("basis") == "speech_s"
        by_voice = {}
        for r in _samples():
            by_voice.setdefault(r["voice_id"], []).append(r)
        import statistics
        checked = []
        for v, rows in by_voice.items():
            entry = (real.get("voices") or {}).get(str(v)) if v is not None else None
            if not entry or int(entry.get("n") or 0) < int(real.get("min_n") or 8):
                continue
            # rà gop-1510 r2: so với cái khâu dựng thật đặt — LEAD + giây nói + TAIL (voice.layout), không phải độ dài file
            err = statistics.median(r["syllables"] / dialogue.voice_rate(v) + dialogue.BREATH - (voice.LEAD + r["speech_s"] + voice.TAIL)
                                    for r in rows)
            assert err <= 0.5 + 1e-6, (v, round(err, 3))
            checked.append(v)
        assert {"70", "72", "30007", "30020"} <= set(checked)
        assert 23 / dialogue.voice_rate("70") + dialogue.BREATH <= 8.0 + dialogue.BREATH    # giây nói ~8 s + đệm dựng (LEAD + TAIL)
        # số câu ước THIẾU > 0,5 s so với LEAD + giây nói + TAIL: BREATH 0,5 cũ → 34/86 câu; BREATH = LEAD + TAIL (0,7) → 22/86
        def under(breath):
            return sum(1 for r in _samples() if r["syllables"] / dialogue.voice_rate(r["voice_id"]) + breath
                       < voice.LEAD + r["speech_s"] + voice.TAIL - 0.5)
        assert under(dialogue.BREATH) <= 22 < under(0.5) == 34
    finally:
        dialogue._RATES_CACHE.clear()


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
    assert f"thoại 3 câu cần ~{want:g} giây nói (≈ số âm tiết ÷ 3.5; + {dialogue.BREATH:g} s mỗi lượt lời" in prompts.intent_frame_block(p, pid)


def test_normalize_and_report_use_the_project_voice(table):
    table({"min_n": 8, "voices": {"70": {"n": 10, "p50": 2.8}}})
    ctx = {"voices": {"KELLY": {"voice_id": 70, "model": "eleven_v3"}}, "gap": dialogue.LINE_GAP}
    obj = {"scenes": [{"idx": 1, "shots": [{"size": "MCU", "duration_s": 3.0, "dialogue": [{"speaker": "KELLY", "text": N1}]}]}]}
    out, _ = shot_normalize.normalize(obj, "", None, ctx=ctx)
    assert out["scenes"][0]["shots"][0]["duration_s"] == round(8 / 2.8 + dialogue.BREATH, 1)   # 8 / 2,8 + 0,7 = 3,6 (3,5 âm/s → kept 3)
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


def _multishot(secs, voiced=None):
    """A Kling multi-shot project: one continuity group of shots with these Director seconds; voiced = {shot index: motion seconds
    already stretched to the real voice (voice.fit_durations)}."""
    p, pid = _project()
    p.conn.execute("UPDATE projects SET shot_mode='multishot' WHERE id=?", (pid,))
    ids = []
    for i, sec in enumerate(secs, 1):
        sid = p.create_scene(pid, i, f"S{i}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"shot_no": i, "story_scene": 1, "sequence": 1,
                                                                          "duration_s": sec}), sid))
        if voiced and i in voiced:
            p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, duration_sec) VALUES (?,?,?)", (sid, "m", voiced[i]))
        ids.append(sid)
    p.conn.commit()
    return p, pid, ids


def test_multishot_shot_gets_its_voice_stretched_seconds():
    from core import shots
    from core.runner import VideoRunner
    p, pid, ids = _multishot([3.2, 3.2], voiced={1: 6.3, 2: 2.0})
    rows = {r["id"]: r for r in shots._rows(p.conn, pid)}
    fake = SimpleNamespace(p=p)
    assert shots.billed_seconds(p.conn, rows[ids[0]]) == VideoRunner._billed_seconds(fake, rows[ids[0]]) == 7   # Đạo diễn: 4
    assert shots.billed_seconds(p.conn, rows[ids[1]]) == VideoRunner._billed_seconds(fake, rows[ids[1]]) == 4


def test_multishot_groups_use_the_voice_stretched_seconds_never_over_15():
    """Lỗi CAO (rà 15/10): nhóm chia theo giây Đạo diễn 5+5+5 = 15, runner gửi giây đã kéo theo giọng 5+7+5 = 17 > 15 (Kling từ chối /
    tốn thêm). Một hàm giây chung: nhóm tách."""
    from core import shots
    p, pid, ids = _multishot([5, 5, 5], voiced={2: 7})
    groups = shots.multishot_groups(p.conn, pid)
    assert [[r["id"] for r in g] for g in groups] == [ids[:2], ids[2:]]
    assert all(sum(shots.billed_seconds(p.conn, r) for r in g) <= shots.MULTISHOT_MAX for g in groups)
    p2, pid2, ids2 = _multishot([5, 5, 5])                               # không ai kéo: nhóm như cũ
    assert [[r["id"] for r in g] for g in shots.multishot_groups(p2.conn, pid2)] == [ids2]


def test_group_parts_cut_at_the_seconds_the_runner_sends():
    """Mục 2: clip nhóm Kling multishot cắt theo billed_seconds (giây runner gửi, đã kéo theo giọng) — nhóm [4 kéo 7, 4] → (0,7),(7,4)."""
    from core import shots
    p, pid, ids = _multishot([4, 4], voiced={1: 7})
    group = shots.multishot_groups(p.conn, pid)[0]
    assert [r["id"] for r in group] == ids
    assert shots.group_parts(group, p.conn) == [(0.0, 7), (7.0, 4)]
    assert shots.group_parts(group) == [(0.0, 4), (4.0, 4)]               # không conn: giây Đạo diễn như cũ (clip dựng máy H5)
    d = tempfile.mkdtemp()
    src = os.path.join(d, "g.mp4")
    with open(src, "wb") as f:
        f.write(b"x")
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        return SimpleNamespace(returncode=1)
    with mock.patch("core.ffmpeg_studio.find_ffmpeg", return_value="ffmpeg"), mock.patch("core.ffmpeg_studio.has_audio", return_value=False), \
            mock.patch("subprocess.run", side_effect=run):
        shots.split_group_clip(src, group, [os.path.join(d, "a.mp4"), os.path.join(d, "b.mp4")], conn=p.conn)
    assert [(c[c.index("-ss") + 1], c[c.index("-t") + 1]) for c in calls] == [("0.00", "7.00"), ("7.00", "4.00")]


def test_group_parts_of_a_sent_group_keep_the_seconds_sent():
    """Rà gop-1510 r2: nhóm đọc lại từ sent_group (data.sent) đã mang đúng giây đã gửi — motion/giọng đổi SAU khi gửi không làm cắt
    lệch clip đã gen (cắt theo giây đã gửi, không theo billed_seconds mới)."""
    from core import shots
    p, pid, ids = _multishot([4, 4], voiced={1: 7})
    group = [dict(r, data=dict(r["data"], sent=True)) for r in shots.multishot_groups(p.conn, pid)[0]]
    assert shots.group_parts(group, p.conn) == [(0.0, 4), (4.0, 4)]          # giây đã gửi (4 + 4), không 7 của motion mới
    group[0]["data"]["duration_s"] = 7
    assert shots.group_parts(group, p.conn) == [(0.0, 7), (7.0, 4)]


def test_pacing_warnings_use_the_project_voice(table):
    """Mục 7: cảnh báo nhịp ở Bước 1 ước giây theo giọng dự án (ctx) như mọi chỗ khác."""
    from core import shots
    table({"min_n": 8, "voices": {"70": {"n": 10, "p50": 2.8}}})
    ctx = {"voices": {"KELLY": {"voice_id": 70, "model": "eleven_v3"}}, "gap": dialogue.LINE_GAP}
    shot = [{"size": "MCU", "role": "dialogue", "duration_s": 3.0, "dialogue": [{"speaker": "KELLY", "text": N1}]}]
    assert shots.pacing_warnings(shot) == []                                  # 8 / 3,5 + 0,7 = 3,0 ≤ 3,0 + 0,3
    need = round(8 / 2.8 + dialogue.BREATH, 1)                                # 8 / 2,8 + 0,7 = 3,6 > 3,3
    assert any(f"thoại cần ~{need:g}s" in w for w in shots.pacing_warnings(shot, ctx))


def test_over_model_max_checks_the_multishot_group_limit():
    """Một shot Kling multishot không dài hơn 15 s (cả nhóm ≤ 15) dù model đơn làm được dài hơn."""
    p, pid, ids = _multishot([5, 5])
    d = tempfile.mkdtemp()
    _voiced(p, pid, d, ids[1], 16000)
    with mock.patch("core.dialogue.max_clip_seconds", return_value=20):
        got = voice.over_model_max(p.conn, pid, d)
    assert [(c["scene_id"], c["max"]) for c in got] == [(ids[1], 15)]
    _voiced(p, pid, d, ids[1], 8000)                                      # nhóm 5 + 9 ≤ 15: không chặn oan
    with mock.patch("core.dialogue.max_clip_seconds", return_value=20):
        assert voice.over_model_max(p.conn, pid, d) == []


def test_voice_over_max_waits_again_when_the_cut_lines_change():
    from core import autopilot
    p, pid = _project()
    ctx = autopilot.Context(tempfile.mkdtemp(), None, None, None, audio=object())
    over = [{"scene_id": 1, "idx": 1, "need": 17.2, "max": 15}]

    def run():
        with mock.patch("core.voice.status", return_value={"total": 1, "missing": 0}),              mock.patch("core.voice.fit_durations", return_value=[]),              mock.patch("core.voice.over_model_max", return_value=list(over)),              mock.patch("core.voice.pending_fits", return_value=[]),              mock.patch.object(autopilot, "_check_voices"):
            return autopilot._voice_phase(p, pid, ctx)

    with pytest.raises(autopilot._Wait):
        run()
    autopilot.set_gates(p, pid, {"waiting_for": "voice_over_max"})
    autopilot.resume(p, pid)
    assert run() is None                                                   # người dùng cho qua đúng danh sách này
    over.append({"scene_id": 2, "idx": 2, "need": 16.0, "max": 15})
    with pytest.raises(autopilot._Wait):                                   # giọng đổi → danh sách khác → chờ lại
        run()


# ---- 5. bảng tốc độ thiếu / hỏng; tốc độ lời dẫn không đè hồ sơ ---------------------------------------------------------------------
def test_missing_speech_rates_file_is_said_and_gives_the_defaults():
    p, pid = _project()
    dialogue._RATES_CACHE.clear()
    try:
        with mock.patch.object(dialogue, "_RATES_FILE", os.path.join(tempfile.mkdtemp(), "none.json")):
            assert dialogue._rates() == dialogue.RATES_DEFAULT
            dialogue.speech_ctx(p.conn, pid)
        rows = p.conn.execute("SELECT severity FROM diag_events WHERE code='speech_rates_missing'").fetchall()
        assert [r["severity"] for r in rows] == ["warn"]
    finally:
        dialogue._RATES_CACHE.clear()
    assert os.path.isabs(dialogue._RATES_FILE) and os.path.exists(dialogue._RATES_FILE)   # theo gốc dự án, không theo cwd


def test_narration_speed_never_overrides_a_saved_voice_profile():
    p, pid = _project()
    p.set_project_field(pid, "narration_speed", 1.2)
    p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (pid, "LỜI DẪN", "x"))
    voice.set_profile(p.conn, pid, "LỜI DẪN", {"voice_id": 72, "voice_name": "boy", "model": "eleven_v3", "speed": None})
    voice.set_profile(p.conn, pid, "LỜI DẪN", {"voice_id": 72, "voice_name": "boy", "model": "eleven_v3"})   # lưu lại (không key speed)
    assert "speed" not in voice.profiles(p.conn, pid)["LỜI DẪN"]          # hồ sơ đã có (1,0 người chọn) giữ nguyên
    voice.set_profile(p.conn, pid, "LỜI DẪN", {"voice_id": 72, "voice_name": "boy", "model": "eleven_v3", "speed": 0.9})
    voice.set_profile(p.conn, pid, "LỜI DẪN", {"voice_id": 72, "voice_name": "boy", "model": "eleven_v3"})
    assert voice.profiles(p.conn, pid)["LỜI DẪN"]["speed"] == 0.9
