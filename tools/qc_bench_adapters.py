"""Adapter offline gọi lại luật QC hiện có; không dựng provider/config production.

Artifact JSON là đầu vào đã chụp và băm, không phải kết quả đo giả làm file media.
Audio/video thực phải có adapter riêng; thiếu adapter → UNSUPPORTED.
"""
import json
import math
from unittest.mock import patch


def _json(raw):
    try:
        value = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError):
        raise ValueError('Artifact không phải JSON hữu hạn') from None
    if not isinstance(value, dict):
        raise ValueError('Artifact phải là JSON object')
    return value


def _number(value, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (positive and value <= 0):
        raise ValueError('Thiếu số đo hữu hạn hợp lệ')
    return value


def _package(raw):
    data = _json(raw)
    if not isinstance(data.get('prompt'), str) or not data['prompt'].strip():
        raise ValueError('Thiếu prompt')
    if data.get('text_stage') != 'final_sent_text':
        raise ValueError('Cần prompt cuối đã gộp ngữ cảnh, tránh đo thiếu gói')
    return data


def _lint(text, limit):
    from core import seedance_refs
    # lint_group giữ quy tắc thoại Việt được phép. Khóa nguồn trần bằng bảng
    # adapter đã biết, không gọi prompt_limit đọc cấu hình/dữ liệu production.
    with patch.object(seedance_refs, 'prompt_limit', return_value=limit):
        return seedance_refs.lint_group(text, 0, 0, 0, [], False)


def package_vi(case, raw):
    if case['artifact_kind'] != 'package':
        raise ValueError('Bộ kiểm cần artifact package')
    data = _package(raw)
    issues = _lint(data['prompt'], len(data['prompt']))
    return {'prediction': 'error' if any(i.startswith('prompt còn chữ tiếng Việt') for i in issues) else 'pass', 'confidence': None}


def package_length(case, raw):
    if case['artifact_kind'] != 'package':
        raise ValueError('Bộ kiểm cần artifact package')
    data = _package(raw)
    from core.adapters.clipai import PROMPT_LIMITS
    if data.get('model') not in PROMPT_LIMITS:
        raise ValueError('Chưa có trần cho model này')
    issues = _lint(data['prompt'], PROMPT_LIMITS[data['model']])
    return {'prediction': 'error' if any(i.startswith('prompt dài ') for i in issues) else 'pass', 'confidence': None}

def metadata_length(case, raw):
    if case['artifact_kind'] != 'render':
        raise ValueError('Bộ kiểm cần metadata render JSON')
    data = _json(raw)
    planned = _number(data.get('planned_s'), positive=True)
    final = _number(data.get('final_s'), positive=True)
    from core.final_qc import check_length
    return {'prediction': 'error' if check_length(planned, final) else 'pass', 'confidence': None}


def metadata_peak(case, raw):
    if case['artifact_kind'] != 'render':
        raise ValueError('Bộ kiểm cần metadata render JSON')
    data = _json(raw)
    peak = _number(data.get('true_peak_dbfs'))
    from core.final_qc import check_peak
    return {'prediction': 'error' if check_peak({'true_peak_dbfs': peak}) else 'pass', 'confidence': None}


def local_registry():
    """(qc_code, đường QC) là khóa; không ngầm dùng Q9 để đo Q1/VLM."""
    return {('QC-PKG-VI_TEXT', 'Q9'): package_vi,
            ('QC-PKG-PROMPT_TOO_LONG', 'Q9'): package_length,
            ('QC-A4-LENGTH_MISMATCH', 'Q9'): metadata_length,
            ('QC-A2-PEAK_OVER', 'Q9'): metadata_peak}
