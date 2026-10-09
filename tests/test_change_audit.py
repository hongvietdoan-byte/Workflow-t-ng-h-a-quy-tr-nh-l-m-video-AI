"""Bộ kiểm tác động (người dùng 10/10): đổi máy/nền/câu tả của shot → rà các khâu liên quan trước khi vẽ."""
import json
import sqlite3

from core import change_audit, features


def db(data):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("CREATE TABLE scenes(id INTEGER PRIMARY KEY, project_id INT, idx INT, data TEXT);"
                    "CREATE TABLE assets(id INTEGER PRIMARY KEY, kind TEXT, name TEXT, profile TEXT);"
                    "CREATE TABLE jobs(id INTEGER PRIMARY KEY, scene_id INT, type TEXT, state TEXT, sent_refs TEXT);")
    c.execute("INSERT INTO scenes VALUES (1, 24, 6, ?)", (json.dumps(data),))
    c.execute("INSERT INTO assets VALUES (418, 'character', 'YÊU NỮ', '{}')")
    return c


SC = {"location": [0, -3, 1.0], "look_at": [0, 0, -0.5], "lens": 24, "pov": "kelly", "move": {"kieu": "lui", "m": 1}}


def test_flags_prompt_and_move_and_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(features, "on", lambda n: n == "stage_camera")
    data = {"stage_camera": SC, "image_prompt": "Medium shot, a creature, faceless black skin", "size": "MS", "camera_move": "static",
            "characters": ["YÊU NỮ"]}
    res = change_audit.audit_shot(db(data), str(tmp_path), 24, 1)
    msgs = {(r["muc"], r["khau"]): r["msg"] for r in res}
    assert ("do", "nen") in msgs                                   # chưa render nền theo máy
    assert any(r["khau"] == "cau" and "point-of-view" in r["msg"] for r in res)
    assert any(r["khau"] == "cau" and "cúi" in r["msg"] for r in res)
    assert any(r["khau"] == "cau" and "camera_move" in r["msg"] for r in res)
    assert any(r["khau"] == "vai" and "must_keep" in r["msg"] for r in res)


def test_flag_off_with_stage_camera_is_red(monkeypatch, tmp_path):
    monkeypatch.setattr(features, "on", lambda n: False)
    res = change_audit.audit_shot(db({"stage_camera": SC, "image_prompt": "point-of-view, looking down"}), str(tmp_path), 24, 1)
    assert any(r["muc"] == "do" and "cờ stage_camera TẮT" in r["msg"] for r in res)
