"""Fixture UI M82 riêng: snapshot giả, mọi đường gửi/ghi bị mock; không phải app production.

Chạy bằng Streamlit trên cổng thử riêng, không dùng thư mục live hay DB thật.
"""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, ROOT)
FAKE_HOME = tempfile.mkdtemp(prefix="m82_ui_fake_")
with patch.object(os, "environ", {"HOME": FAKE_HOME, "USERPROFILE": FAKE_HOME,
                                 "TEMP": FAKE_HOME, "TMP": FAKE_HOME, "PYTHONUTF8": "1"}):
    import streamlit as st
    from dashboard.basic import model, views

    st.set_page_config(page_title="M82 — dữ liệu giả", layout="wide")
    key = st.query_params.get("screen", "idea")
    names = {"idea": model.SCREENS[0], "script": model.SCREENS[1], "images": model.SCREENS[2],
             "video": model.SCREENS[3], "download": model.SCREENS[4]}
    st.session_state["basic_screen_1"] = names.get(key, model.SCREENS[0])
    state = {"project": {"id": 1, "name": "Phim giả · Kelly vào kho", "paused": int(key == "pause"),
                         "script_text": "CẢNH 1 - NGÀY, KHO HÀNG\nKelly bước vào kho và tìm thấy một chiếc hộp đỏ."},
             "scenes": [{"id": 1, "idx": 1, "title": "Kelly vào kho", "image_used": 2, "video_used": 1},
                        {"id": 2, "idx": 2, "title": "Mở chiếc hộp đỏ", "image_used": 3, "video_used": 2}],
             "jobs": [{"id": 12, "scene_id": 2, "type": "video_gen", "state": "failed", "result_path": None}],
             "budget": {"approved": {"limit_usd": 10}, "recorded": 7, "held": 1, "limit": 10,
                        "ratio": .8, "warning": True, "stages": {"Ảnh": 3, "Video": 4}},
             "idea": {}, "can_edit": False, "identity": {"email": "viewer@example.test", "role": "member"},
             "data_dir": FAKE_HOME}
    p = SimpleNamespace(conn=SimpleNamespace(execute=lambda *a, **kw: SimpleNamespace(fetchall=lambda: [])))
    with patch.object(model, "load", return_value=state), \
            patch.object(views.simple_budget, "proposal", return_value={"total": None, "incomplete": True}), \
            patch.object(views.actions, "quote", side_effect=ValueError("fixture: chưa có giá")), \
            patch.object(views.actions, "send", side_effect=AssertionError("fixture không gửi")), \
            patch.object(views.paid_confirm, "enabled", return_value=False):
        views.render_workspace(p, 1, FAKE_HOME)
