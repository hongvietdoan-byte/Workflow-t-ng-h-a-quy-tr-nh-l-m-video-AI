"""Đ10.5: kiểm đề ngoại tuyến; không đánh đồng test chữ với chất lượng Claude."""
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from core import change_review as cr, features


def prompt(on, **overrides):
    conn = sqlite3.connect(':memory:')
    conn.executescript('CREATE TABLE scenes(id INTEGER, idx INTEGER, data TEXT); CREATE TABLE assets(id INTEGER, name TEXT, profile TEXT, description TEXT);')
    data = {'characters': ['Kelly'], 'blocking': 'đứng', 'image_prompt': 'Kelly standing',
            'action': 'đứng rồi ngã', 'motion_en': 'stand, stumble, fall, settle', 'end_state': 'nằm',
            'duration_s': 4, 'byd': {'hanh_dong': [{'ai': 'Kelly', 'bat_dau': 'đứng', 'dinh': 'ngã', 'ket_thuc': 'nằm'}]}}
    data.update(overrides)
    conn.execute('INSERT INTO scenes VALUES(1,1,?)', (json.dumps(data),))
    ev = {'id': 84, 'kind': 'scene', 'scene_id': 1, 'before': '{}', 'after': json.dumps(data)}
    try:
        with patch('core.features.on', return_value=on):
            return cr.build_prompt(conn, ev, ['blocking'], [1], [])
    finally:
        conn.close()


def test_off_exact_snapshot_bytes():
    assert prompt(False).encode('utf-8') == (Path(__file__).parent / 'fixtures/change_review_frames_off.txt').read_bytes()


@pytest.mark.parametrize('data,expected', [
    ({}, ('blocking (khung đầu)', 'end_state (khung cuối)', 'BÌNH THƯỜNG')),
    ({'motion_en': '0–1 đứng; 1–2 chao; 2–3 ngã; 3–4 nằm'}, ('4 nhịp / 4 s', 'không theo số câu', 'duration_s: 4')),
    ({'byd': {'hanh_dong': [{'ai': 'Kelly', 'bat_dau': 'đứng', 'dinh': 'biến hình', 'ket_thuc': 'dạng 2'}],
              'ngoai_le': [{'dieu_trai': 'chủ ý biến hình'}], 'thanh_phan': [{'vat': 'Kelly', 'dang': 'dạng 1'}]}},
     ('byd (đầu → đỉnh → cuối)', 'chủ ý biến hình', 'dạng 1', 'dạng 2')),
])
def test_golden_frame_context(data, expected):
    text = prompt(True, **data)
    for part in expected:
        assert part in text
    assert 'Chỉ so cùng loại khung' in text
    assert 'ảnh đã duyệt' in text
    assert 'byd.hanh_dong[].bat_dau' in text
    assert 'byd.hanh_dong[].ket_thuc' in text


def test_flag_default_off(monkeypatch, tmp_path):
    monkeypatch.setenv('FEATURE_SETTINGS_FILE', str(tmp_path / 'none.json'))
    monkeypatch.delenv('FEATURE_CHANGE_REVIEW_FRAMES', raising=False)
    assert features.on('change_review_frames') is False


def test_byd_context_not_cut_and_path_independent(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    byd = {'thanh_phan': [{'vat': 'Kelly', 'thay': 'x' * 700}],
           'hanh_dong': [{'ai': 'Kelly', 'bat_dau': 'đứng', 'dinh': 'chao', 'ket_thuc': 'nằm-cuối-BYĐ'}],
           'ngoai_le': [{'dieu_trai': 'ngoại-lệ-cuối-BYĐ'}]}
    text = prompt(True, byd=byd)
    assert 'nằm-cuối-BYĐ' in text
    assert 'ngoại-lệ-cuối-BYĐ' in text
