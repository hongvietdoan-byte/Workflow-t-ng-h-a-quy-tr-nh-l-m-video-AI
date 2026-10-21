"""V3.1 M7.4 (C-M74, cloud-C 21/10) — Gói B sửa cờ (docs/KE_HOACH_SUA_20_CO_2026-10-21.md mục 2, bằng chứng docs/BANG_CHUNG_CHOT_CO_2026-10-21.md
2.4.3). KHÔNG khóa cờ nào. Mỗi cờ một commit + test. B7 (release_gate × final_black_freeze) ở tests/test_v31_dp6_release_gate.py."""
import os
from unittest import mock

import pytest

from core import before_run, features
from core.db import connect
from core.pipeline import Pipeline


@pytest.fixture
def conn(tmp_path):
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    return p.conn


# ---- B2: dialogue_take 🔒 cần lip_sync (mặc định TẮT) → khóa giả ---------------------------------------------------------------------
def test_b2_locked_flag_without_its_parent_is_said_before_the_run(conn, monkeypatch):
    monkeypatch.setattr(features, "_TEST_BYPASS", False)                    # khóa thật: dialogue_take 🔒 BẬT
    with mock.patch.dict(os.environ, {"FEATURE_LIP_SYNC": "0"}):
        items = before_run._cost_items(conn)
    hit = [i for i in items if "dialogue_take" in i["text"]]
    assert hit and hit[0]["level"] == "vang" and hit[0]["text"].startswith("🔒") and "lip_sync" in hit[0]["text"]
    assert "lip-sync-lock-after-real-run" in hit[0]["text"]
    with mock.patch.dict(os.environ, {"FEATURE_LIP_SYNC": "1"}):
        assert not [i for i in before_run._cost_items(conn) if "dialogue_take" in i["text"]]


def test_b2_no_flag_is_locked_on_top_of_an_unlocked_parent_except_the_decided_one():
    """Cờ 🔒 không được có cha trong REQUIRES chưa 🔒 — ngoại lệ đã ghi sổ: dialogue_take → lip_sync (khóa lip_sync chờ chạy thật)."""
    bad = {k: [n for n in needs if not features.FEATURES[n]["verified"]] for k, needs in features.REQUIRES.items()
           if features.FEATURES.get(k, {}).get("verified")}
    assert {k: v for k, v in bad.items() if v} == {"dialogue_take": ["lip_sync"]}
