"""Schema benchmark: tường minh provenance/nhãn, không tự nâng gợi ý."""
import copy
from unittest.mock import patch

import pytest
from tools import qc_benchmark as bench
from tests.test_qc_benchmark import make_case


@pytest.mark.parametrize('field,value', [
    ('label', 'unknown'), ('split', 'test'), ('label_by', ''), ('label_at', '2026-10-21'),
    ('synthetic', 'true'), ('label_confirmed', 1), ('qc_path', 'Q0'), ('artifact_kind', 'audio'),
    ('artifact_sha', 'x'), ('project_id', True), ('scene_idx', -1), ('job_id', '1'),
    ('qc_code', 'QC-UNKNOWN'), ('case_id', '\n'), ('source_ref', ''), ('label_note', 12)])
def test_schema_rejects_invalid_fields(tmp_path, field, value):
    c = make_case(tmp_path)
    c[field] = value
    with pytest.raises(bench.BenchError):
        bench.validate_cases([c])


@pytest.mark.parametrize('field,value', [('commit_sha', ''), ('flags_snapshot', {'on': 'yes'}),
    ('schema_version', 0), ('provider', 'fake'), ('prompt_sha', 'x')])
def test_capture_provenance_required(tmp_path, field, value):
    c = make_case(tmp_path)
    c['capture'][field] = value
    with pytest.raises(bench.BenchError):
        bench.validate_cases([c])


def test_missing_fields_suggestion_confirmation_and_uppercase_sha(tmp_path):
    c = make_case(tmp_path)
    c.pop('capture')
    with pytest.raises(bench.BenchError):
        bench.validate_cases([c])
    c = make_case(tmp_path, label_by='goi_y')
    with pytest.raises(bench.BenchError):
        bench.validate_cases([c])
    c['label_confirmed'] = False
    c['artifact_sha'] = c['artifact_sha'].upper()
    assert bench.validate_cases([c]) == [c]


def test_case_count_limit_and_duplicate_ids(tmp_path):
    c = make_case(tmp_path)
    with patch.object(bench, 'MAX_CASES', 0):
        with pytest.raises(bench.BenchError):
            bench.validate_cases([c])
    with pytest.raises(bench.BenchError, match='case_id'):
        bench.validate_cases([c, copy.deepcopy(c)])



def test_unhashable_qc_path_is_schema_error(tmp_path):
    c = make_case(tmp_path, qc_path=[])
    with pytest.raises(bench.BenchError):
        bench.validate_cases([c])


def test_source_ref_must_be_traceable(tmp_path):
    c = make_case(tmp_path, source_ref='untraceable')
    with pytest.raises(bench.BenchError):
        bench.validate_cases([c])
