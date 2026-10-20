"""DP7: benchmark QC chỉ đọc, offline mặc định, không quyết định production.

Python API nhận registry callable tin cậy cho client giả; đây không phải sandbox
cho Python không tin cậy. CLI chỉ dùng adapter local có sẵn, không có live mode.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager, ExitStack
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import socket
import subprocess
import sys
from unittest.mock import patch
import urllib.request

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.qc_bench_metrics import score_cases

MAX_CASES = 10000
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
SHA = re.compile(r'[0-9a-fA-F]{64}')
IDENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}')
QC_PATHS = {f'Q{i}' for i in range(1, 11)}
REGRESSIONS = {'QC-L6-SIZE_MISMATCH': ('P33-A5',), 'QC-L9-HORIZON_MISMATCH': ('P31-G20',),
               'QC-V3-LIP_SYNC': ('P31-G10', 'P31-G16', 'P31-G53'),
               'QC-CR-INPUT_MISSING': ('P33-A6',), 'QC-SYS-QC_CRASH': ('V21-R3',)}


class BenchError(ValueError):
    """Lỗi hợp đồng; thông báo không chứa giá trị đầu vào/payload."""


def known_codes():
    # Chỉ đọc hằng schema; không gọi registry_ids/error_types/CSDL của ứng dụng.
    from core.qc_evidence import CODES
    return set(CODES) | {'QC-CR-INPUT_MISSING', 'QC-SYS-QC_CRASH'}


def _text(value, *, empty=False, limit=2048):
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()):
        raise BenchError('Chuỗi thiếu hoặc quá giới hạn')
    if any(ord(c) < 32 for c in value):
        raise BenchError('Chuỗi chứa ký tự điều khiển')


def _sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise BenchError('SHA256 không hợp lệ')


def _timestamp(value):
    _text(value, limit=64)
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise BenchError('Thời điểm nhãn không hợp lệ') from None
    if parsed.tzinfo is None:
        raise BenchError('Thời điểm nhãn thiếu múi giờ')


def _relative(value):
    _text(value, limit=512)
    # Không URL, ổ đĩa Windows, UNC, ADS, traversal, backslash hay file cấu hình.
    if ':' in value or '\\' in value or value.startswith('/') or PureWindowsPath(value).drive:
        raise BenchError('Artifact phải là đường dẫn tương đối trong root')
    parts = value.split('/')
    if any(p in ('', '.', '..') or p != p.strip(' .') for p in parts):
        raise BenchError('Artifact chứa đoạn đường dẫn không hợp lệ')
    if any(p.lower().endswith(('.env', '.sqlite', '.db')) or p.lower() in ('.git',) for p in parts):
        raise BenchError('Artifact không thuộc loại đầu vào benchmark')


def validate_cases(cases, *, allow_unknown=False):
    """Schema §2 + artifact/qc_path/label_confirmed tường minh; không đoán xác minh.

    Cho phép unknown ở runner chỉ để xuất UNSUPPORTED; API validator mặc định từ chối.
    Cùng SHA khác mã được phép trong cùng split, cùng mã không lặp để tăng số mẫu.
    """
    if not isinstance(cases, list) or len(cases) > MAX_CASES:
        raise BenchError('Bộ ca phải là list trong giới hạn')
    ids, sha_splits, pairs = set(), {}, set()
    codes = known_codes()
    for c in cases:
        if not isinstance(c, dict):
            raise BenchError('Ca phải là object')
        required = {'case_id', 'qc_code', 'artifact_kind', 'artifact', 'artifact_sha', 'project_id',
                    'scene_idx', 'job_id', 'source_ref', 'label', 'label_by', 'label_at', 'label_note',
                    'split', 'synthetic', 'capture', 'qc_path', 'label_confirmed'}
        if not required <= c.keys():
            raise BenchError('Ca thiếu trường schema')
        for key in ('case_id', 'qc_code'):
            if not isinstance(c[key], str) or not IDENT.fullmatch(c[key]):
                raise BenchError('Mã định danh không hợp lệ')
        if c['case_id'] in ids:
            raise BenchError('case_id trùng')
        ids.add(c['case_id'])
        if not allow_unknown and c['qc_code'] not in codes:
            raise BenchError('qc_code chưa có trong schema')
        if c['artifact_kind'] not in ('image', 'clip', 'package', 'render') or not isinstance(c['qc_path'], str) or c['qc_path'] not in QC_PATHS:
            raise BenchError('Loại artifact hoặc đường QC không hợp lệ')
        _relative(c['artifact'])
        _sha(c['artifact_sha'])
        if c['label'] not in ('LOI', 'DAT', 'KHONG_XET') or c['split'] not in ('dev', 'independent'):
            raise BenchError('Nhãn hoặc split không hợp lệ')
        for key in ('synthetic', 'label_confirmed'):
            if type(c[key]) is not bool:
                raise BenchError('Cờ phải là boolean')
        if type(c['project_id']) is not int or c['project_id'] <= 0:
            raise BenchError('project_id phải là số nguyên dương')
        for key in ('scene_idx', 'job_id'):
            if c[key] is not None and (type(c[key]) is not int or c[key] < 0):
                raise BenchError('Định danh scene/job không hợp lệ')
        for key in ('source_ref', 'label_by', 'label_note'):
            _text(c[key], empty=key == 'label_note')
        if not c['source_ref'].startswith(('docs/', 'errors.json:')) and not (c['synthetic'] and c['source_ref'].startswith('synthetic:')):
            raise BenchError('source_ref thiếu nguồn tài liệu hoặc fixture tổng hợp')
        _timestamp(c['label_at'])
        if c['label_by'].strip().casefold() in ('goi_y', 'suggested', 'unknown') and c['label_confirmed']:
            raise BenchError('Nhãn gợi ý không thể tự xác nhận')
        capture = c['capture']
        if not isinstance(capture, dict) or not {'commit_sha', 'flags_snapshot', 'schema_version', 'provider', 'model', 'prompt_sha'} <= capture.keys():
            raise BenchError('Thiếu provenance capture')
        if not isinstance(capture['commit_sha'], str) or not re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', capture['commit_sha']):
            raise BenchError('Commit capture không hợp lệ')
        flags = capture['flags_snapshot']
        if not isinstance(flags, dict) or len(flags) > 1000 or any(not isinstance(k, str) or not IDENT.fullmatch(k) or type(v) is not bool for k, v in flags.items()):
            raise BenchError('Snapshot cờ không hợp lệ')
        if type(capture['schema_version']) is not int or capture['schema_version'] < 1:
            raise BenchError('Phiên bản schema không hợp lệ')
        for key in ('provider', 'model'):
            if capture[key] is not None:
                _text(capture[key], limit=128)
        if (capture['provider'] is None) != (capture['model'] is None):
            raise BenchError('Provider/model phải có cùng nhau')
        if capture['prompt_sha'] is not None:
            _sha(capture['prompt_sha'])
        sha = c['artifact_sha'].lower()
        if sha in sha_splits and sha_splits[sha] != c['split']:
            raise BenchError('artifact_sha lọt giữa hai split')
        sha_splits[sha] = c['split']
        pair = (c['qc_code'], sha)
        if pair in pairs:
            raise BenchError('Artifact trùng trong cùng mã QC')
        pairs.add(pair)
    return cases


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise BenchError('JSON chứa khóa trùng')
        result[key] = value
    return result


def _loads(raw):
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(BenchError('JSON không hữu hạn')))
    except (ValueError, UnicodeError, RecursionError):
        raise BenchError('JSON không hợp lệ') from None


def load_cases(path):
    """Đọc JSON list hoặc JSONL đã xuất; không trích CSDL hay thư mục production."""
    path = Path(path)
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise BenchError('Bộ ca quá lớn')
    with path.open('rb') as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise BenchError('Bộ ca quá lớn')
    # PowerShell/Windows thường xuất UTF-8 BOM; bỏ đúng tiền tố trước khi
    # phân biệt JSON list nhiều dòng với JSONL (json.loads(bytes) vốn nhận BOM).
    raw = raw.removeprefix(b'\xef\xbb\xbf')
    if raw.lstrip().startswith(b'['):
        cases = _loads(raw)
    else:
        cases = [_loads(line) for line in raw.splitlines() if line.strip()]
    return validate_cases(cases, allow_unknown=True)


@contextmanager
def offline_guard():
    """Fail closed cho network/process và môi trường; callable tiêm phải tin cậy.

    Không đọc môi trường User/registry. Không có subprocess được phép ở tranche
    này; FFmpeg adapter đang OPEN, tuyệt đối không tự dò PATH hay from_env.
    """
    def denied(*args, **kwargs):
        raise PermissionError('Benchmark chỉ chạy offline, không network/process')
    fake_home = 'C:/Windows/Temp/qc-bench-isolated-home' if os.name == 'nt' else '/tmp/qc-bench-isolated-home'
    safe = {'HOME': fake_home, 'USERPROFILE': fake_home, 'PYTHONUTF8': '1', 'SYSTEMROOT': 'C:/Windows'}
    with ExitStack() as stack:
        stack.enter_context(patch.object(os, 'environ', safe))
        for obj, name in ((socket, 'create_connection'), (socket, 'getaddrinfo'),
                          (socket.socket, 'connect'), (socket.socket, 'connect_ex'),
                          (socket.socket, 'sendto'), (urllib.request, 'urlopen'), (subprocess, 'Popen')):
            stack.enter_context(patch.object(obj, name, denied))
        if os.name == 'nt':
            import winreg
            for name in ('OpenKey', 'OpenKeyEx', 'ConnectRegistry', 'QueryValue', 'QueryValueEx', 'EnumKey', 'EnumValue'):
                stack.enter_context(patch.object(winreg, name, denied))
        yield


def _artifact_bytes(root, relative, expected):
    _relative(relative)
    candidate = root / relative
    # Cấm symlink/junction cả bên trong root để không dựa vào nguồn ngoài snapshot.
    part = root
    for segment in Path(relative).parts:
        part = part / segment
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise BenchError('Artifact là liên kết, chưa đủ đầu vào')
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise BenchError('Artifact thiếu hoặc ngoài root')
    if resolved.stat().st_size > MAX_ARTIFACT_BYTES:
        raise BenchError('Artifact quá lớn')
    with resolved.open('rb') as stream:
        raw = stream.read(MAX_ARTIFACT_BYTES + 1)
    if len(raw) > MAX_ARTIFACT_BYTES or hashlib.sha256(raw).hexdigest() != expected.lower():
        raise BenchError('Artifact không khớp SHA hoặc quá lớn')
    return raw


def _result(value):
    if not isinstance(value, dict) or value.get('prediction') not in ('error', 'pass', 'doubt'):
        raise BenchError('Checker không trả quyết định hợp lệ')
    confidence = value.get('confidence')
    if confidence is not None and (type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1):
        raise BenchError('Checker trả confidence không hợp lệ')
    return {'prediction': value['prediction'], 'confidence': confidence}


def _summaries(cases, results):
    splits = {}
    by_id = {r['case_id']: r for r in results}
    diagnostics = {'QC-CR-INPUT_MISSING', 'QC-SYS-QC_CRASH'}
    def metric_row(c, *, excluded=False, code=None):
        r = by_id[c['case_id']]
        return dict(case_id=c['case_id'], qc_code=code or c['qc_code'], artifact_sha=c['artifact_sha'],
                    split=c['split'], label='KHONG_XET' if excluded else c['label'],
                    prediction='doubt' if excluded else r['prediction'],
                    confidence=None if excluded else r['confidence'])
    for split in ('dev', 'independent'):
        rows = [c for c in cases if c['split'] == split]
        eligible = [c for c in rows if c['label_confirmed'] and c['label'] != 'KHONG_XET']
        measured = [c for c in eligible if by_id[c['case_id']]['status'] == 'MEASURED' and c['qc_code'] not in diagnostics]
        per_code = score_cases([metric_row(c) for c in measured])
        for code in sorted({c['qc_code'] for c in rows}):
            code_rows = [c for c in rows if c['qc_code'] == code]
            if code not in per_code:
                per_code[code] = score_cases([metric_row(c, excluded=True) for c in code_rows])[code]
            m = per_code[code]
            selected = [c for c in eligible if c['qc_code'] == code]
            n_measured = m['n_pos'] + m['n_neg']
            missing = len(selected) - n_measured
            known = REGRESSIONS.get(code, ())
            missing_regressions = [ref for ref in known if not any(
                c['label'] == 'DAT' and re.search(r'(?<![A-Za-z0-9_-])' + re.escape(ref) + r'(?![A-Za-z0-9_-])', c['source_ref'])
                for c in selected)]
            shares = {p: sum(c['project_id'] == p for c in selected) for p in {c['project_id'] for c in selected}}
            m.update(label_verification='EXPLICIT_ASSERTION_ONLY', eligible=len(selected), measured=n_measured,
                     unmeasured=missing, coverage=n_measured / len(selected) if selected else None,
                     excluded=sum(c['label_confirmed'] and c['label'] == 'KHONG_XET' for c in code_rows),
                     excluded_unconfirmed=sum(not c['label_confirmed'] for c in code_rows),
                     synthetic=sum(c['synthetic'] for c in selected),
                     synthetic_fraction=sum(c['synthetic'] for c in selected) / len(selected) if selected else None,
                     projects=sorted(shares), max_project_share=max(shares.values()) / len(selected) if selected else None,
                     missing_regressions=missing_regressions,
                     sample_status='DEV_ONLY' if split == 'dev' else ('CHUA_DU_MAU' if min(m['n_pos'], m['n_neg']) < 20 else 'DU_MAU_SANG_LOC'),
                     status='DIAGNOSTIC_ONLY' if code in diagnostics else ('INCOMPLETE' if missing else 'REVIEW_ONLY'))
            m['false_alarm_per_100'] = 100*m['fpr'] if m['fpr'] is not None else None
            m['miss_per_100'] = 100*m['fnr'] if m['fnr'] is not None else None
        paths = score_cases([metric_row(c, code=c['qc_path']) for c in measured])
        for path in sorted({c['qc_path'] for c in rows}):
            path_rows = [c for c in rows if c['qc_path'] == path]
            if path not in paths:
                paths[path] = score_cases([metric_row(c, excluded=True, code=path) for c in path_rows])[path]
            m = paths[path]
            selected = [c for c in eligible if c['qc_path'] == path and c['qc_code'] not in diagnostics]
            n = m['n_pos'] + m['n_neg']
            m.update(eligible=len(selected), measured=n, unmeasured=len(selected)-n,
                     coverage=n / len(selected) if selected else None,
                     status='INCOMPLETE' if n < len(selected) else 'REVIEW_ONLY',
                     label_verification='EXPLICIT_ASSERTION_ONLY')
        splits[split] = {'per_code': per_code, 'per_qc_path': paths, 'total': len(rows),
                         'unique_artifacts': len({c['artifact_sha'].lower() for c in rows}),
                         'excluded_unconfirmed': sum(not c['label_confirmed'] for c in rows),
                         'excluded_khong_xet': sum(c['label_confirmed'] and c['label'] == 'KHONG_XET' for c in rows)}
    return splits

def run_benchmark(cases, artifact_root, *, registry=None, benchmark_id='offline'):
    """Không ghi artifact/calibration/CSDL. Registry chỉ cho callable test tin cậy."""
    with offline_guard():
        validate_cases(cases, allow_unknown=True)  # toàn bộ set trước khi tách split
        if not isinstance(benchmark_id, str) or not IDENT.fullmatch(benchmark_id):
            raise BenchError('benchmark_id không hợp lệ')
        root = Path(artifact_root).resolve()
        if not root.is_dir():
            raise BenchError('Artifact root không tồn tại')
        if registry is None:
            from tools.qc_bench_adapters import local_registry
            registry = local_registry()
        codes, results = known_codes(), []
        for c in cases:
            r = {k: c[k] for k in ('case_id', 'qc_code', 'qc_path', 'split')}
            r['provenance'] = {k: c['capture'][k] for k in ('commit_sha', 'schema_version', 'provider', 'model', 'prompt_sha')}
            if not c['label_confirmed'] or c['label'] == 'KHONG_XET':
                r['status'] = 'EXCLUDED_UNCONFIRMED' if not c['label_confirmed'] else 'EXCLUDED_KHONG_XET'
            elif c['qc_code'] not in codes or (c['qc_code'], c['qc_path']) not in registry:
                r['status'] = 'UNSUPPORTED'
            else:
                try:
                    if c['qc_path'] in ('Q1', 'Q2', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q10') and any(c['capture'][k] is None for k in ('provider', 'model', 'prompt_sha')):
                        raise BenchError('Thiếu provenance của checker model')
                    raw = _artifact_bytes(root, c['artifact'], c['artifact_sha'])
                    value = registry[(c['qc_code'], c['qc_path'])](copy.deepcopy(c), raw)
                    r.update(_result(value), status='MEASURED')
                except (OSError, ValueError, TypeError, KeyError):
                    r['status'] = 'INSUFFICIENT_INPUT'
                except Exception:
                    # Không xuất exception/payload; lỗi checker là trạng thái thật, không giả pass.
                    r['status'] = 'CHECKER_FAILED'
            results.append(r)
        return {'schema_version': 1, 'benchmark_id': benchmark_id, 'mode': 'OFFLINE_SHADOW',
                'decision': 'REVIEW_ONLY', 'calibration_persisted': False,
                'unit': 'artifact-qc_code pair; per_qc_path micro aggregation',
                'label_trust': 'Explicit assertion in supplied manifest, not identity authentication',
                'splits': _summaries(cases, results), 'results': results}


def markdown_report(report):
    lines = ['# Benchmark QC offline', '', 'Chỉ REVIEW; 20+20 chỉ là sàng lọc. Không tự cấp quyền chặn.', '',
             '| Split | Mã | Lỗi/đạt đo được | P | R | FP/100 | FN/100 | ECE | Độ phủ | Trạng thái |',
             '|---|---|---|---|---|---|---|---|---|---|']
    def fmt(value):
        return '—' if value is None else f'{value:.4f}'
    for split, group in report['splits'].items():
        for code, m in group['per_code'].items():
            lines.append(f"| {split} | {code} | {m['n_pos']}/{m['n_neg']} | {fmt(m['precision'])} | {fmt(m['recall'])} | "
                         f"{fmt(m['false_alarm_per_100'])} | {fmt(m['miss_per_100'])} | {fmt(m['ece'])} | {fmt(m['coverage'])} | {m['status']}/{m['sample_status']} |")
    lines += ['', 'Wilson 95%, 5 ngăn ECE, loại nhãn và từng ca thiếu hỗ trợ có trong JSON.',
              'Nhãn xác nhận là khai báo tường minh của manifest; chưa xác thực danh tính người gán nhãn.',
              'Chưa hỗ trợ FFmpeg/audio/video thật và live VLM; chỉ dùng adapter offline đã đăng ký.']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description='QC benchmark offline, chỉ đọc; không live/API')
    parser.add_argument('cases')
    parser.add_argument('--artifact-root', required=True)
    parser.add_argument('--format', choices=('json', 'markdown'), default='json')
    args = parser.parse_args(argv)
    try:
        with offline_guard():
            report = run_benchmark(load_cases(args.cases), args.artifact_root)
        print(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) if args.format == 'json' else markdown_report(report))
        return 1 if any(r['status'] in ('UNSUPPORTED', 'INSUFFICIENT_INPUT', 'CHECKER_FAILED') for r in report['results']) else 0
    except (OSError, ValueError):
        print('INVALID_INPUT: không đọc được bộ ca hợp lệ trong phạm vi.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
