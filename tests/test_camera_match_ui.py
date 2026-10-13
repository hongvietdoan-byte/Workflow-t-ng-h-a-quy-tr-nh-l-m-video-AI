"""Adapter giả, không phiên Dashboard/DB/model thật."""
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from dashboard import camera_match_ui as U


def test_off_does_not_read_database():
    with patch.object(U.features, "on", return_value=False):
        U.render(None, 1, 1, "missing")


def test_missing_subject_stale_plan_and_missing_price_are_yellow():
    p = MagicMock()
    p.conn.execute.return_value.fetchone.return_value = {"data": json.dumps({"characters": ["A"]})}
    rec = {"camera_plan": {"location": [0, -5, 1], "look_at": [0, 0, 1], "lens": 35,
                           "subject": {"location": [0, 0, 0], "height_m": 1.7}}}
    original = os.environ
    for stale in ({}, {1: {"why": "old"}}):
        with patch.object(os, "environ", {}), patch.dict(sys.modules, {"dashboard.common": SimpleNamespace(DATA="temporary")}), patch.object(U, "st") as st, patch.object(U.features, "on", return_value=True), patch.object(U.location_pack, "plate_of", return_value=rec), patch.object(U.location_pack, "stale_plates", return_value=stale), patch.object(U.camera_match_qc, "check_image", return_value=[{"muc": "vang", "loi": "không đo mắt"}]) as check, patch.object(U.cost, "image_button_tag", side_effect=ValueError), patch.object(U.image_models, "of_project", return_value="fake"):
            U.render(p, 1, 1, "fake.png")
            assert check.call_args.args[2] is None
            if stale:
                assert check.call_args.args[1] == {}
            st.warning.assert_called_with("không đo mắt")
            assert any("chưa có giá" in c.args[0] for c in st.caption.call_args_list)
        assert os.environ is original
