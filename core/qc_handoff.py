"""M610B — adapter QC/cổng thuần, checkpoint shadow chưa nối caller/writer.

Caller truyền snapshot M6.2 đã pin và findings đã có; hàm không đọc cờ,
registry, sổ lỗi, tệp hay CSDL. ``enabled=False`` thoát trước mọi đầu vào.
Một proposal cho mỗi vai trong snapshot; không phải phiếu đã lưu/được duyệt.
``seen_keys`` do caller cung cấp, module không giữ store/queue/cache riêng.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from . import crew, handoff

FLAG = 'qc_handoff_shadow'


class QCHandoffInputError(ValueError):
    """Snapshot hoặc bằng chứng explicit chưa đủ hợp đồng."""


def _json(value: Any) -> str:
    def check(item):
        if isinstance(item, dict):
            if not all(isinstance(k, str) for k in item):
                raise QCHandoffInputError('JSON cần tên trường dạng chuỗi')
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
        elif item is not None and not isinstance(item, (str, int, float, bool)):
            raise QCHandoffInputError('đầu vào phải là dữ liệu JSON')
    check(value)
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise QCHandoffInputError('đầu vào không phải JSON an toàn') from exc


def _copy(value: Any) -> Any:
    return json.loads(_json(value))


def _snapshot(value: Any) -> dict:
    keys = {'project_id', 'scene_id', 'shot_no', 'revision',
            'source_fingerprint', 'dependencies', 'products'}
    if not isinstance(value, dict) or set(value) != keys:
        raise QCHandoffInputError('snapshot cần đúng phạm vi, revision, fingerprint, dependencies, products M62')
    value = _copy(value)
    for key in ('project_id', 'scene_id', 'shot_no'):
        value[key] = handoff._positive_int(value[key], key)
    value['revision'] = handoff._revision(value['revision'])
    value['source_fingerprint'] = handoff._text(value['source_fingerprint'], 'source_fingerprint')
    value['dependencies'] = handoff._dependencies(value['dependencies'])
    products = handoff._simple_rows(value['products'], 'products', handoff._PRODUCT_KEYS, {'path', 'sha256'})
    if not products:
        raise QCHandoffInputError('snapshot.products thiếu sản phẩm đã pin')
    for row in products:
        row['path'] = handoff._canonical_path(row['path'], 'product.path')
        row['sha256'] = handoff._digest(row['sha256'], 'product.sha256')
        if 'kind' in row:
            row['kind'] = handoff._text(row['kind'], 'product.kind')
        for key in ('id', 'job_id'):
            if key in row:
                row[key] = handoff._positive_int(row[key], f'product.{key}')
        if 'revision' in row:
            row['revision'] = handoff._nonnegative_int(row['revision'], 'product.revision')
    value['products'] = products
    return value


def build(*, findings=None, snapshot=None, registry=None, errors=None,
          validator_version=None, enabled=False, seen_keys=()) -> list[dict]:
    """Đề xuất shadow M62, gộp theo vai; không ghi hoặc xác minh nguồn thật.

    Finding: ``qc_code``, ``registry_ids`` (list[str]), ``actionability``
    (object, layer tùy chọn), ``qc_evidence`` ({id,status?,path?,sha256?}).
    Metadata tùy chọn chỉ gồm severity/why/source dạng chuỗi; cấm payload lạ.
    ``errors`` bắt buộc list/object explicit (rỗng hợp lệ); registry cần
    roles không rỗng và Director fallback có thật. Dedup dùng toàn snapshot,
    vai, validator và nội dung finding/route/evidence canonical. scope_key giữ
    ổn định theo vai/snapshot/validator; content_fingerprint đổi khi finding
    mới dùng lại cùng evidence. seen_keys chỉ loại đúng nội dung đã thấy.
    Group nhiều finding: đọc routing.findings để biết via/fix_field từng lỗi;
    top-level chỉ có owner và tổng hợp owner_cannot_fix/note.
    """
    if enabled is False:
        return []
    if enabled is not True:
        raise QCHandoffInputError('enabled phải là bool explicit')
    if not isinstance(registry, dict) or not registry or not isinstance(registry.get('roles'), list) or not registry['roles']:
        raise QCHandoffInputError('registry explicit cần roles không rỗng')
    if not isinstance(errors, (list, dict)):
        raise QCHandoffInputError('errors snapshot bắt buộc explicit list/object')
    reg, error_snapshot = _copy(registry), _copy(errors)
    roles = reg['roles']
    if any(not isinstance(r, dict) or not isinstance(r.get('id'), str) or not r['id'].strip() for r in roles):
        raise QCHandoffInputError('registry.roles thiếu id hợp lệ')
    known = {r['id'] for r in roles}
    if len(known) != len(roles) or 'director' not in known or reg.get('fallback_owner', 'director') != 'director':
        raise QCHandoffInputError('registry cần id duy nhất và fallback Director')
    for r in roles:
        if not isinstance(r.get('writes', []), list) or any(not isinstance(v, str) for v in r.get('writes', [])):
            raise QCHandoffInputError('registry.roles.writes phải là list chuỗi')
        owns = r.get('owns_errors', {})
        if not isinstance(owns, dict) or any(not isinstance(owns.get(k, []), list) or any(not isinstance(v, str) for v in owns.get(k, [])) for k in ('codes', 'categories', 'stages')):
            raise QCHandoffInputError('registry.owns_errors không hợp lệ')
    fields, layers = reg.get('fields', {}), reg.get('layer_fields', {})
    if not isinstance(fields, dict) or any(not isinstance(v, dict) or v.get('owner') not in known for v in fields.values()):
        raise QCHandoffInputError('registry.fields cần vai chủ có thật')
    if not isinstance(layers, dict) or any(not isinstance(v, str) or v not in fields for v in layers.values()):
        raise QCHandoffInputError('registry.layer_fields cần trường có thật')
    error_rows = error_snapshot.values() if isinstance(error_snapshot, dict) else error_snapshot
    for error in error_rows:
        if not isinstance(error, dict) or not isinstance(error.get('id'), str) or not error['id'].strip():
            raise QCHandoffInputError('errors cần các mục có id')
        if not isinstance(error.get('alias', []), list) or any(not isinstance(a, str) for a in error.get('alias', [])):
            raise QCHandoffInputError('errors.alias cần list chuỗi')
    version = handoff._text(validator_version, 'validator_version')
    pinned = _snapshot(snapshot)
    if not isinstance(findings, list):
        raise QCHandoffInputError('findings phải là danh sách explicit')
    findings = _copy(findings)
    if not isinstance(seen_keys, (list, tuple, set, frozenset)) or any(not isinstance(k, str) for k in seen_keys):
        raise QCHandoffInputError('seen_keys phải là tập/danh sách khóa chuỗi')
    seen = set(seen_keys)
    indexed = crew.errors_index(error_snapshot)
    grouped = {}
    for f in findings:
        if not isinstance(f, dict):
            raise QCHandoffInputError('finding phải là object')
        allowed = {'qc_code', 'registry_ids', 'actionability', 'qc_evidence', 'severity', 'why', 'source'}
        if set(f) - allowed:
            raise QCHandoffInputError('finding có trường ngoài hợp đồng đã lọc')
        for meta in ('severity', 'why', 'source'):
            if meta in f and not isinstance(f[meta], str):
                raise QCHandoffInputError('finding metadata phải là chuỗi đã lọc')
        code = handoff._text(f.get('qc_code'), 'finding.qc_code')
        ids, act = f.get('registry_ids'), f.get('actionability')
        if not isinstance(ids, list) or any(not isinstance(i, str) or not i.strip() for i in ids):
            raise QCHandoffInputError('finding.registry_ids phải là list chuỗi không rỗng')
        if not isinstance(act, dict) or set(act) - {'layer'} or ('layer' in act and act['layer'] is not None and (not isinstance(act['layer'], str) or not act['layer'].strip())):
            raise QCHandoffInputError('finding.actionability/layer không hợp lệ')
        ev, = handoff._simple_rows([f.get('qc_evidence')], 'qc_evidence', handoff._QC_KEYS, {'id'})
        for key in ('id', 'status'):
            if key in ev:
                ev[key] = handoff._text(ev[key], f'qc_evidence.{key}')
        if 'path' in ev:
            ev['path'] = handoff._canonical_path(ev['path'], 'qc_evidence.path')
        if 'sha256' in ev:
            ev['sha256'] = handoff._digest(ev['sha256'], 'qc_evidence.sha256')
        routing = crew.owner_of_error(code, ids, reg, indexed, layer=act.get('layer'))
        owner = routing['owner']
        if owner not in known or owner == 'continuity_validator':
            raise QCHandoffInputError('vai chủ không hợp lệ trong registry snapshot')
        group = grouped.setdefault(owner, {'evidence': {}, 'findings': {}})
        f['qc_evidence'] = ev
        detail = {'finding': f, **routing}
        group['evidence'][_json(ev)] = ev
        group['findings'][_json(detail)] = detail
    out = []
    for owner, group in sorted(grouped.items()):
        evidence = [group['evidence'][k] for k in sorted(group['evidence'])]
        details = [group['findings'][k] for k in sorted(group['findings'])]
        scope = {'role': owner, 'snapshot': pinned, 'validator_version': version}
        scope_key = hashlib.sha256(_json(scope).encode('utf-8')).hexdigest()
        evidence_fingerprint = hashlib.sha256(_json(evidence).encode('utf-8')).hexdigest()
        content_fingerprint = hashlib.sha256(_json({'evidence': evidence, 'findings': details}).encode('utf-8')).hexdigest()
        key = hashlib.sha256(_json({'scope_key': scope_key, 'content_fingerprint': content_fingerprint}).encode('utf-8')).hexdigest()
        if key in seen:
            continue
        payload = {k: pinned[k] for k in ('project_id', 'scene_id', 'shot_no', 'revision', 'dependencies', 'products')}
        payload.update(from_role='continuity_validator', to_role=owner, qc_evidence=evidence, approval_state='returned')
        # Không trình bày route của lỗi đầu như route chung của nhiều lỗi.
        routing = ({k: v for k, v in details[0].items() if k != 'finding'}
                   if len(details) == 1 else {'owner': owner})
        routing['findings'] = details
        states = [d['owner_cannot_fix'] for d in details]
        routing['owner_cannot_fix'] = True if True in states else (False if False in states else None)
        routing['note'] = '; '.join(sorted({d['note'] for d in details if d['note']}))
        out.append({'status': 'SHADOW_ONLY', 'dedup_key': key,
                    'scope_key': scope_key, 'evidence_fingerprint': evidence_fingerprint,
                    'content_fingerprint': content_fingerprint,
                    'source_fingerprint': pinned['source_fingerprint'],
                    'validator_version': version, 'payload': payload, 'routing': routing})
    return _copy(out)
