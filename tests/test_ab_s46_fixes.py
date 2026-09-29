"""S4.6 A/B hành động (#10, 2026-09-29): the two defects it found — the reference picture's red plus drawn into a Seedance Fast clip,
and one-person storyboard frames drawn with the whole scene's cast."""
import os

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from core import clip_measure, scene_storyboard  # noqa: E402


def _clip(tmp_path, draw, n=24):
    path = str(tmp_path / "c.mp4")
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 24, (360, 640))
    for i in range(n):
        f = np.full((640, 360, 3), (200, 170, 120), np.uint8)
        draw(f, i)
        out.write(f)
    out.release()
    return path


def _plus(f, i):
    cv2.line(f, (140, 300 + i), (184, 300 + i), (0, 0, 220), 10)
    cv2.line(f, (162, 278 + i), (162, 322 + i), (0, 0, 220), 10)


def test_red_plus_in_clip_is_flagged(tmp_path):
    r = clip_measure.ref_mark(_clip(tmp_path, _plus))
    assert r["hits"] == r["frames"] and r.get("flag")


def test_red_clothes_are_not_a_mark(tmp_path):
    def hood(f, i):                               # a solid red block and a tall red V (a hood) — not a plus
        cv2.rectangle(f, (40, 400), (120, 470), (0, 0, 220), -1)
        cv2.fillPoly(f, [np.array([[200, 300], [250, 300], [225, 370]])], (0, 0, 220))
    r = clip_measure.ref_mark(_clip(tmp_path, hood))
    assert r["hits"] == 0 and not r.get("flag")


def test_a_few_stray_frames_do_not_flag(tmp_path):
    r = clip_measure.ref_mark(_clip(tmp_path, lambda f, i: _plus(f, 0) if i < 6 else None))
    assert 0 < r["hits"] < r["frames"] and not r.get("flag")


def _g():
    shots = [{"id": 1, "data": {"characters": ["KELLY"], "action": "Kelly runs"}},
             {"id": 2, "data": {"characters": ["KENTA"], "action": "Kenta swings"}},
             {"id": 3, "data": {"characters": ["MAXIM", "KELLY"], "action": "Maxim flinches"}}]
    return {"shots": shots}


def test_cast_note_names_who_is_not_in_the_frame():
    note = scene_storyboard.cast_note(_g(), 1)
    assert "Only KELLY is in this frame" in note and "KENTA, MAXIM are NOT in this frame" in note
    assert "MAXIM, KELLY are in this frame" in scene_storyboard.cast_note(_g(), 3)


def test_cast_note_empty_when_everyone_is_in():
    g = {"shots": [{"id": 1, "data": {"characters": ["A", "B"]}}, {"id": 2, "data": {"characters": ["B", "A"]}}]}
    assert scene_storyboard.cast_note(g, 1) == ""


def test_story_text_says_who_is_in_each_frame():
    assert scene_storyboard._in_frame({"characters": ["KELLY"]}) == " (in frame: KELLY)"
    assert scene_storyboard._in_frame({}) == " (no person in frame)"
