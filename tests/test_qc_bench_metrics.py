import math
import pytest
from tools.qc_bench_metrics import score_cases


def row(i, label='LOI', prediction='error', **extra):
    return dict(case_id=str(i), qc_code='QC-X', artifact_sha=f'{i:064x}',
                label=label, split='independent', prediction=prediction, **extra)


def test_known_counts_and_doubt():
    rows = [row(1), row(2), row(3, prediction='pass'), row(4, prediction='doubt'),
            row(5, 'DAT', 'error'), row(6, 'DAT', 'pass'), row(7, 'DAT', 'doubt'),
            row(8, 'KHONG_XET', 'error')]
    m = score_cases(rows)['QC-X']
    assert (m['tp'], m['fp'], m['fn'], m['tn'], m['abstain']) == (2, 1, 2, 1, 2)
    assert (m['n_pos'], m['n_neg'], m['excluded']) == (4, 3, 1)
    assert m['precision'] == pytest.approx(2/3)
    assert m['recall'] == .5
    assert m['fpr'] == pytest.approx(1/3)
    assert m['fnr'] == .5
    assert m['doubt_rate'] == pytest.approx(2/7)


def test_empty_unknown_and_wilson():
    assert score_cases([]) == {}
    m = score_cases([row(1, 'KHONG_XET')])['QC-X']
    assert all(m[k] is None for k in ('precision', 'recall', 'fpr', 'fnr', 'ece', 'precision_wilson95'))
    m = score_cases([row(i) for i in range(20)])['QC-X']
    assert m['precision_wilson95'][0] == pytest.approx(.83887484)
    assert m['recall_wilson95'][1] == pytest.approx(1)


def test_calibration_five_bins_and_doubt_exclusion():
    m = score_cases([row(1, confidence=.9), row(2, 'DAT', 'error', confidence=.9),
                     row(3, prediction='doubt', confidence=1)])['QC-X']
    assert len(m['confidence_bins']) == 5
    assert m['ece'] == pytest.approx(.4)
    assert m['confidence_bins'][4]['n'] == 2
    assert m['confidence_excluded_doubt'] == 1


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -.1, 1.1, True, '0.5'])
def test_invalid_confidence(value):
    with pytest.raises(ValueError):
        score_cases([row(1, confidence=value)])


@pytest.mark.parametrize('extra', [dict(label='unknown'), dict(split='test'), dict(prediction='unknown'), dict(artifact_sha='x')])
def test_invalid_minimum_schema(extra):
    r = row(1)
    r.update(extra)
    with pytest.raises(ValueError):
        score_cases([r])


def test_duplicate_artifact_across_codes_and_splits():
    r = row(1)
    other = dict(r, split='dev', qc_code='QC-Y')
    with pytest.raises(ValueError):
        score_cases([r, other])


def test_does_not_infer_verified_labels_or_promote_block():
    m = score_cases([row(1, label_by='goi_y')])['QC-X']
    assert m['label_verification'] == 'NOT_ASSESSED'
    assert 'BLOCK' not in str(m)
