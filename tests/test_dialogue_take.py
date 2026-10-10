"""S4.6 lip sync option (c): one clip for a whole dialogue, lines + seconds + speaker in the prompt (core/dialogue_take.py)."""
import pytest

from core import dialogue_take as dt, seedance_refs

LINES = [{"speaker": "MAXIM", "text": "Của anh, không ai lấy được!", "file": "a.mp3", "duration_ms": 1800},
         {"speaker": "KENTA", "text": "Chia đôi.", "file": "b.mp3", "duration_ms": 900},
         {"speaker": "KELLY", "text": "…Còn em?", "file": "c.mp3", "duration_ms": 1100}]
CAST = [{"name": "MAXIM", "where": "right, crouching behind the gloo wall", "pose": "hugging half a bun"},
        {"name": "KENTA", "where": "centre", "pose": "holding the other half"},
        {"name": "KELLY", "where": "left", "pose": "hands on knees, panting"}]


def test_segments_follow_each_other_with_a_breath():
    s = dt.segments(LINES)
    assert s[0]["start"] == pytest.approx(0.3) and s[0]["end"] == pytest.approx(2.1)
    assert s[1]["start"] == pytest.approx(2.45) and s[2]["end"] == pytest.approx(4.8)
    assert dt.billed_seconds(s) == 6


def test_unvoiced_line_and_too_long_take_are_errors():
    with pytest.raises(ValueError):
        dt.segments([{"speaker": "A", "text": "x"}])
    with pytest.raises(ValueError):
        dt.billed_seconds(dt.segments([dict(LINES[0], duration_ms=16000)]))


def test_prompt_has_the_seven_blocks_and_every_line_with_its_speaker():
    p = dt.prompt(CAST, dt.segments(LINES), "ingame", place="Clock Tower plaza")
    for block in ("REFERENCE ASSETS:", "CHARACTERS & BLOCKING:", "AUDIO & LIP-SYNC:", "TIMELINE:", "CONTINUITY & AVOID:"):
        assert block in p
    assert '[00:00 - 00:03] Dialogue (MAXIM / C1 lipsync @Audio1): "Của anh, không ai lấy được!"' in p
    assert '(KENTA / C2 lipsync @Audio1): "Chia đôi."' in p and "Image2 = identity of C1 MAXIM" in p
    assert "one continuous take of 6 seconds" in p and "burned-in subtitles" in p


def test_the_two_styles_differ_only_in_the_look():
    a, b = (dt.prompt(CAST, dt.segments(LINES), s) for s in ("ingame", "real3d"))
    assert "Free Fire in-game" in a and "Unreal Engine 5" in b and "anime face" in b and "anime face" not in a
    with pytest.raises(ValueError):
        dt.prompt(CAST, dt.segments(LINES), "cartoon")


def test_mark_styles(tmp_path):
    from PIL import Image
    src = tmp_path / "k.png"
    Image.new("RGB", (200, 300), (120, 120, 120)).save(src)
    outs = {s: seedance_refs.mark(str(src), str(tmp_path / "m"), s) for s in seedance_refs.MARK_STYLES}
    assert len(set(outs.values())) == 4
    def red(path):
        with Image.open(path) as im:
            pixels = im.convert("RGB").tobytes()
        return sum(1 for r, g in zip(pixels[0::3], pixels[1::3]) if r > 200 and g < 30)

    assert red(outs["eye_plus"]) > 0 and red(outs["corner_plus"]) > 0 and red(outs["banner"]) == 0 and red(outs["none"]) == 0
    assert Image.open(outs["banner"]).getpixel((5, 5)) == (255, 255, 255)
    assert Image.open(outs["none"]).getpixel((5, 5)) == (120, 120, 120)
    with pytest.raises(ValueError):
        seedance_refs.mark(str(src), str(tmp_path / "m"), "stars")
