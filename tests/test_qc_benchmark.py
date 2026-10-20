"""DP7: bộ ca tổng hợp, checker local thật và client VLM giả."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

import pytest
from tools import qc_benchmark as bench


@pytest.fixture(autouse=True)
def isolated(tmp_path):
    safe = {'HOME': str(tmp_path / 'fake-home'), 'USERPROFILE': str(tmp_path / 'fake-home'),
            'SYSTEMROOT': 'C:/Windows', 'PYTHONUTF8': '1'}
    with patch.object(os, 'environ', safe):
        yield


def make_case(root, i=1, *, content=None, code='QC-PKG-VI_TEXT', label='LOI', split='independent', **extra):
    content = content if content is not None else {'prompt': f'Có chữ Việt {i}'}
    content = {'text_stage': 'final_sent_text', **content}
    raw = json.dumps(content, ensure_ascii=False).encode()
    path = root / f'case-{i}.json'
    path.write_bytes(raw)
    c = dict(case_id=f'case-{i}', qc_code=code, qc_path='Q9', artifact_kind='package',
             artifact=path.name, artifact_sha=hashlib.sha256(raw).hexdigest(), project_id=24,
             scene_idx=i, job_id=None, source_ref='synthetic:test', label=label,
             label_by='human-fixture', label_at='2026-10-21T04:00:00+07:00', label_note='',
             label_confirmed=True, split=split, synthetic=True,
             capture=dict(commit_sha='a'*40, flags_snapshot={'shadow': False}, schema_version=1,
                          provider=None, model=None, prompt_sha=None))
    c.update(extra)
    return c


def test_actual_local_checks_separate_splits_and_readonly(tmp_path):
    cases = [make_case(tmp_path, 1), make_case(tmp_path, 2, content={'prompt': 'plain English'}, label='DAT'),
             make_case(tmp_path, 3, split='dev', content={'prompt': 'Another English'}, label='LOI')]
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    report = bench.run_benchmark(cases, tmp_path)
    held = report['splits']['independent']['per_code']['QC-PKG-VI_TEXT']
    dev = report['splits']['dev']['per_code']['QC-PKG-VI_TEXT']
    assert (held['tp'], held['tn'], held['fn'], held['n_pos']) == (1, 1, 0, 1)
    assert held['precision'] == held['recall'] == 1
    assert dev['fn'] == 1 and dev['sample_status'] == 'DEV_ONLY'
    assert report['decision'] == 'REVIEW_ONLY' and report['calibration_persisted'] is False
    assert report['splits']['independent']['per_qc_path']['Q9']['n_pos'] == 1
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize('code,content,expected', [
    ('QC-PKG-PROMPT_TOO_LONG', {'model': 'kling', 'prompt': 'x'*2501}, 'error'),
    ('QC-PKG-PROMPT_TOO_LONG', {'model': 'kling', 'prompt': 'x'*2500}, 'pass'),
    ('QC-A4-LENGTH_MISMATCH', {'planned_s': 10, 'final_s': 13}, 'error'),
    ('QC-A4-LENGTH_MISMATCH', {'planned_s': 10, 'final_s': 10}, 'pass'),
    ('QC-A2-PEAK_OVER', {'true_peak_dbfs': -.5}, 'error'),
    ('QC-A2-PEAK_OVER', {'true_peak_dbfs': -2}, 'pass')])
def test_existing_qc_adapters(tmp_path, code, content, expected):
    c = make_case(tmp_path, code=code, content=content,
                  artifact_kind='render' if code.startswith('QC-A') else 'package')
    r = bench.run_benchmark([c], tmp_path)['results'][0]
    assert r['status'] == 'MEASURED' and r['prediction'] == expected


def test_fake_vlm_doubt_and_calibration(tmp_path):
    cases = [make_case(tmp_path, i, code='QC-L1-IDENTITY_DRIFT', qc_path='Q5', label='DAT' if i == 2 else 'LOI') for i in range(1, 4)]
    for c in cases:
        c['capture'].update(provider='fake', model='fake-vlm', prompt_sha='b'*64)
    def fake_client(case, raw):
        assert isinstance(raw, bytes)
        return {'prediction': 'doubt' if case['case_id'] == 'case-3' else 'error', 'confidence': .9}
    report = bench.run_benchmark(cases, tmp_path, registry={('QC-L1-IDENTITY_DRIFT', 'Q5'): fake_client})
    m = report['splits']['independent']['per_code']['QC-L1-IDENTITY_DRIFT']
    assert (m['tp'], m['fp'], m['fn'], m['abstain']) == (1, 1, 1, 1)
    assert m['precision'] == m['recall'] == .5
    assert m['ece'] == pytest.approx(.4)
    assert m['missing_regressions'] == []
    assert report['splits']['independent']['per_qc_path']['Q5']['tp'] == 1


def test_unconfirmed_and_khong_xet_never_call_checker(tmp_path):
    cases = [make_case(tmp_path, 1, label_by='goi_y', label_confirmed=False),
             make_case(tmp_path, 2, label='KHONG_XET'), make_case(tmp_path, 3, label_confirmed=False)]
    def forbidden(*args):
        pytest.fail('Không được chạy checker cho nhãn bị loại')
    report = bench.run_benchmark(cases, tmp_path, registry={('QC-PKG-VI_TEXT', 'Q9'): forbidden})
    group = report['splits']['independent']
    assert group['excluded_unconfirmed'] == 2 and group['excluded_khong_xet'] == 1
    assert group['per_code']['QC-PKG-VI_TEXT']['precision'] is None
    assert group['per_code']['QC-PKG-VI_TEXT']['n_pos'] == 0


@pytest.mark.parametrize('change', [{'qc_code': 'QC-UNKNOWN'}, {'qc_code': 'QC-L1-IDENTITY_DRIFT'}, {'qc_path': 'Q1'}])
def test_unsupported_cannot_become_pass(tmp_path, change):
    c = make_case(tmp_path, **change)
    report = bench.run_benchmark([c], tmp_path)
    assert report['results'][0]['status'] == 'UNSUPPORTED'
    m = report['splits']['independent']['per_code'][c['qc_code']]
    assert m['recall'] is None and m['coverage'] == 0 and m['status'] == 'INCOMPLETE'


@pytest.mark.parametrize('content', [{}, {'prompt': ''}, {'prompt': 7}])
def test_missing_checker_input_not_pass(tmp_path, content):
    c = make_case(tmp_path, content=content)
    assert bench.run_benchmark([c], tmp_path)['results'][0]['status'] == 'INSUFFICIENT_INPUT'


def test_missing_tampered_and_size_bound_artifact(tmp_path):
    c = make_case(tmp_path)
    path = tmp_path / c['artifact']
    path.write_text('tampered')
    assert bench.run_benchmark([c], tmp_path)['results'][0]['status'] == 'INSUFFICIENT_INPUT'
    path.unlink()
    assert bench.run_benchmark([c], tmp_path)['results'][0]['status'] == 'INSUFFICIENT_INPUT'
    c = make_case(tmp_path)
    with patch.object(bench, 'MAX_ARTIFACT_BYTES', 2):
        assert bench.run_benchmark([c], tmp_path)['results'][0]['status'] == 'INSUFFICIENT_INPUT'


@pytest.mark.parametrize('artifact', ['../escape.json', '/root.json', 'C:/root.json', '//server/x', 'x\\y', 'x:stream', 'dashboard.env', 'data/manifest.sqlite'])
def test_path_escape_rejected_before_read(tmp_path, artifact):
    c = make_case(tmp_path, artifact=artifact)
    with pytest.raises(bench.BenchError):
        bench.run_benchmark([c], tmp_path)


def test_symlink_artifact_rejected(tmp_path):
    c = make_case(tmp_path)
    link = tmp_path / 'linked.json'
    try:
        link.symlink_to(tmp_path / c['artifact'])
    except OSError:
        pytest.skip('Windows không cấp quyền symlink; test resolver vẫn chạy riêng')
    c['artifact'] = link.name
    assert bench.run_benchmark([c], tmp_path)['results'][0]['status'] == 'INSUFFICIENT_INPUT'


def test_link_detection_without_native_symlink_privilege(tmp_path):
    c = make_case(tmp_path)
    with patch.object(Path, 'is_symlink', return_value=True):
        assert bench.run_benchmark([c], tmp_path)['results'][0]['status'] == 'INSUFFICIENT_INPUT'


@pytest.mark.parametrize('action', [lambda: socket.create_connection(('invalid.test', 443)),
                                      lambda: socket.getaddrinfo('invalid.test', 443),
                                      lambda: subprocess.run(['anything'])])
def test_offline_guard_blocks_network_and_processes(tmp_path, action):
    c = make_case(tmp_path)
    def checker(case, raw):
        action()
        return {'prediction': 'pass'}
    r = bench.run_benchmark([c], tmp_path, registry={('QC-PKG-VI_TEXT', 'Q9'): checker})
    assert r['results'][0]['status'] == 'INSUFFICIENT_INPUT'


def test_checker_crash_and_invalid_confidence_do_not_pass(tmp_path):
    c = make_case(tmp_path)
    def crash(case, raw):
        raise RuntimeError('Lỗi giả')
    r = bench.run_benchmark([c], tmp_path, registry={('QC-PKG-VI_TEXT', 'Q9'): crash})
    assert r['results'][0]['status'] == 'CHECKER_FAILED'
    def bad(case, raw):
        return {'prediction': 'pass', 'confidence': float('nan')}
    r = bench.run_benchmark([c], tmp_path, registry={('QC-PKG-VI_TEXT', 'Q9'): bad})
    assert r['results'][0]['status'] == 'INSUFFICIENT_INPUT'


def test_cross_split_sha_detected_even_for_excluded_unknown_code(tmp_path):
    c = make_case(tmp_path)
    other = dict(c, case_id='other', qc_code='QC-UNKNOWN', split='dev', label='KHONG_XET', label_confirmed=False)
    with pytest.raises(bench.BenchError, match='split'):
        bench.run_benchmark([c, other], tmp_path)


def test_duplicate_artifact_same_code_does_not_inflate_count(tmp_path):
    c = make_case(tmp_path)
    with pytest.raises(bench.BenchError, match='trùng'):
        bench.run_benchmark([c, dict(c, case_id='other')], tmp_path)


def test_cli_json_markdown_and_invalid_input(tmp_path, capsys):
    c = make_case(tmp_path)
    manifest = tmp_path / 'cases.json'
    manifest.write_text(json.dumps([c]))
    assert bench.main([str(manifest), '--artifact-root', str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['mode'] == 'OFFLINE_SHADOW'
    assert bench.main([str(manifest), '--artifact-root', str(tmp_path), '--format', 'markdown']) == 0
    assert '| independent | QC-PKG-VI_TEXT |' in capsys.readouterr().out
    c['qc_code'] = 'QC-UNKNOWN'
    manifest.write_text(json.dumps([c]))
    assert bench.main([str(manifest), '--artifact-root', str(tmp_path)]) == 1
    capsys.readouterr()
    manifest.write_text('[{"bad":1}]')
    assert bench.main([str(manifest), '--artifact-root', str(tmp_path)]) == 2
    assert 'INVALID_INPUT' in capsys.readouterr().err


def test_jsonl_and_manifest_bounds(tmp_path):
    c = make_case(tmp_path)
    manifest = tmp_path / 'cases.jsonl'
    manifest.write_text(json.dumps(c) + '\n')
    assert bench.load_cases(manifest) == [c]
    with patch.object(bench, 'MAX_MANIFEST_BYTES', 1):
        with pytest.raises(bench.BenchError):
            bench.load_cases(manifest)
    manifest.write_text('{"case_id":"a","case_id":"b"}')
    with pytest.raises(bench.BenchError):
        bench.load_cases(manifest)


def test_known_regression_and_diagnostic_codes_no_precision_recall(tmp_path):
    c = make_case(tmp_path, code='QC-L6-SIZE_MISMATCH')
    r = bench.run_benchmark([c], tmp_path)
    assert r['splits']['independent']['per_code'][c['qc_code']]['missing_regressions'] == ['P33-A5']
    c = make_case(tmp_path, code='QC-CR-INPUT_MISSING')
    r = bench.run_benchmark([c], tmp_path, registry={(c['qc_code'], 'Q9'): lambda *_: {'prediction': 'error'}})
    assert r['splits']['independent']['per_code'][c['qc_code']]['precision'] is None


def test_report_never_suggests_block_even_with_twenty_plus_twenty(tmp_path):
    cases = [make_case(tmp_path, i, content={'prompt': f'Có chữ Việt {i}' if i < 21 else f'English {i}'},
                       label='LOI' if i < 21 else 'DAT') for i in range(1, 41)]
    r = bench.run_benchmark(cases, tmp_path)
    m = r['splits']['independent']['per_code']['QC-PKG-VI_TEXT']
    assert m['sample_status'] == 'DU_MAU_SANG_LOC'
    assert r['decision'] == 'REVIEW_ONLY'
    assert 'DE_XUAT_BLOCK' not in json.dumps(r)


def test_qc_path_coverage_cannot_hide_unsupported_code(tmp_path):
    cases = [make_case(tmp_path, 1), make_case(tmp_path, 2, code='QC-L1-IDENTITY_DRIFT')]
    report = bench.run_benchmark(cases, tmp_path)
    m = report['splits']['independent']['per_qc_path']['Q9']
    assert m['coverage'] == .5 and m['unmeasured'] == 1 and m['status'] == 'INCOMPLETE'


def test_vietnamese_dialogue_uses_existing_exception(tmp_path):
    c = make_case(tmp_path, content={'prompt': 'Dialogue (Kelly): "Có chuyện gì?"'}, label='DAT')
    assert bench.run_benchmark([c], tmp_path)['results'][0]['prediction'] == 'pass'


def test_unfinalized_package_is_insufficient_input(tmp_path):
    c = make_case(tmp_path, content={'prompt': 'raw motion before context', 'text_stage': 'raw'})
    assert bench.run_benchmark([c], tmp_path)['results'][0]['status'] == 'INSUFFICIENT_INPUT'


def test_missing_vlm_provenance_never_calls_fake_client(tmp_path):
    c = make_case(tmp_path, code='QC-L1-IDENTITY_DRIFT', qc_path='Q5')
    def forbidden(*args):
        pytest.fail('Không gọi model thiếu provenance')
    r = bench.run_benchmark([c], tmp_path, registry={(c['qc_code'], 'Q5'): forbidden})
    assert r['results'][0]['status'] == 'INSUFFICIENT_INPUT'


def test_local_adapters_never_construct_real_provider(tmp_path):
    from core.adapters.clipai import ClipAIVideoProvider
    c = make_case(tmp_path, code='QC-PKG-PROMPT_TOO_LONG', content={'model': 'kling', 'prompt': 'safe text'})
    with patch.object(ClipAIVideoProvider, 'from_env', side_effect=AssertionError('Cấm provider thật')) as blocked:
        r = bench.run_benchmark([c], tmp_path)
    assert r['results'][0]['status'] == 'MEASURED'
    blocked.assert_not_called()


def test_checker_cannot_mutate_supplied_capture(tmp_path):
    c = make_case(tmp_path)
    def checker(case, raw):
        case['capture']['flags_snapshot']['shadow'] = True
        return {'prediction': 'error'}
    bench.run_benchmark([c], tmp_path, registry={(c['qc_code'], 'Q9'): checker})
    assert c['capture']['flags_snapshot']['shadow'] is False


@pytest.mark.parametrize('artifact', ['dashboard.env.', 'folder /x.json', 'x.json '])
def test_windows_normalized_path_rejected(tmp_path, artifact):
    c = make_case(tmp_path, artifact=artifact)
    with pytest.raises(bench.BenchError):
        bench.run_benchmark([c], tmp_path)


def test_registry_guard_without_registry_access():
    if os.name != 'nt':
        pytest.skip('Guard registry chỉ dùng trên Windows')
    import winreg
    # Không gọi registry thật: guard đã thay hàm trước lệnh bên dưới.
    with bench.offline_guard():
        with pytest.raises(PermissionError):
            winreg.OpenKey(None, 'synthetic')
