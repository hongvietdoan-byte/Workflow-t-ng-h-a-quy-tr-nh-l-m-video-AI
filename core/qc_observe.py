"""QC quan sát Đ14: model khai bằng chứng; code quyết điểm. Chưa thử thật."""
from core import kho_profile
import hashlib
import json
import math
import os
import re

from . import qc_spec

ENUM = ('thay', 'khong_thay', 'khong_chac')


def compile_checks(conn, pid, job, data, criteria, profiles=None):
    spec = qc_spec.compile_frame(conn, pid, job, data, profiles=profiles)
    if spec['missing_profiles']:
        raise ValueError('Thiếu hồ sơ chuẩn: ' + ', '.join(spec['missing_profiles']))
    if spec['plan_conflicts']:
        raise ValueError('Bảng shot mâu thuẫn: ' + '; '.join(spec['plan_conflicts']))
    if spec.get('geometry_missing'):
        raise ValueError('Thiếu ngữ cảnh máy 3D: ' + str(spec['geometry_missing']))
    checks = []

    def add(criterion, detail, source, subject='-', expected='thay'):
        detail = str(detail or '').strip()
        if not detail:
            raise ValueError('Thiếu đặc điểm chuẩn: ' + source)
        tag = hashlib.sha256(json.dumps([job, criterion, detail, source, subject], ensure_ascii=False).encode()).hexdigest()[:16]
        checks.append({'id': f'{job}#{tag}', 'criterion': criterion, 'detail': detail,
                       'subject': subject, 'source': source, 'expected': expected})

    # Dùng bộ dịch chuẩn đã áp ngoại lệ shot; giữ từng mệnh đề cùng nguồn.
    for a in spec['assertions']:
        criterion = {'identity': 'character', 'asym': 'character', 'headwear': 'character',
                     'count': 'consistency', 'layout': 'composition', 'gaze': 'composition',
                     'action': 'composition', 'gesture': 'composition', 'size': 'composition',
                     'light': 'mood_lighting', 'skill': 'character', 'geometry': 'scale'}.get(a['type'])
        if criterion not in criteria:
            continue
        # Hồ sơ có nhiều đặc điểm: tách theo dấu phân cách, không so từ ngắn/bỏ dấu.
        if a['type'] == 'identity' and a['source'] == 'profile.must_keep':
            from . import assets, lock_exceptions
            profile = (profiles or {}).get(a['subject']) if profiles is not None else kho_profile.for_character(conn, pid, a['subject'])
            profile = lock_exceptions.apply_rules(profile, lock_exceptions.for_shot(data).get(a['subject']))
            if not str(profile.get('must_keep') or '').strip():
                raise ValueError('Thiếu đặc điểm hồ sơ chuẩn: ' + a['subject'])
            add(criterion, 'same face as standard reference', a['source'] + '.face', a['subject'])
            for i, clause in enumerate(re.split(r'[;,]', str(profile.get('must_keep') or ''))):
                if clause.strip(): add(criterion, clause, a['source'] + f'[{i}]', a['subject'])
        else:
            add(criterion, a['claim_vi'], a['source'], a['subject'])
            if a.get('observe') in ('side', 'cap', 'geo'):
                # Enum chung chưa mang số đo bên/chiều mũ/hình học của qc_rules.
                # Giữ VÀNG tới khi có bộ khai tương ứng; không thay luật cũ bằng suy đoán.
                checks[-1]['needs_specialized_observation'] = True
    cast = {str(n).upper() for n in data.get('characters') or []}
    for i, item in enumerate((data.get('byd') or {}).get('thanh_phan') or []):
        if not isinstance(item, dict) or not item.get('vat'):
            raise ValueError('BYĐ.thanh_phan thiếu vật chuẩn')
        if str(item['vat']).upper() not in cast and 'set_match' in criteria:
            add('set_match', item['vat'], f'byd.thanh_phan[{i}].vat',
                expected='khong_thay' if item.get('vai') == 'khong_duoc_co' else 'thay')
    from . import shot_intent        # V3.1 M1.1: vật v1 (chuỗi) đọc như {vat}; dữ liệu sai vẫn báo như trước
    for i, item in enumerate(shot_intent.vat_items(data.get('byd'))):
        if not isinstance(item, dict) or not item.get('vat'):
            raise ValueError('BYĐ.vat thiếu vật chuẩn')
        if 'set_match' in criteria:
            add('set_match', item['vat'], f'byd.vat[{i}].vat')
    # Các tiêu chí tổng quát vẫn được kiểm, không tự cho 1 vì thiếu câu hỏi.
    from . import prompts
    descriptions = {c['key']: c['description'] for c in json.loads(prompts._read('data', 'qc_checklist.json'))['criteria']}
    descriptions['character'] = 'Đúng nhân vật theo ảnh chuẩn Kho và hồ sơ chuẩn đã duyệt, đã áp ngoại lệ riêng của shot (mặt, tóc, trang phục, dấu hiệu nhận diện)'
    context_keys = {
        'character': ('characters', 'byd'),
        'composition': ('size', 'angle', 'blocking', 'action', 'performance'),
        'mood_lighting': ('mood', 'palette', 'lighting', 'time', 'weather'),
        'consistency': ('characters', 'byd'),
        'scale': ('characters', 'blocking', 'size'),
        'grounding': ('size', 'byd'),
        'set_match': ('location', 'blocking', 'byd', 'time', 'weather'),
    }
    from .llm_runner import NO_FEET_SIZES
    for criterion in criteria:
        if criterion == 'grounding' and str(data.get('size') or '').upper() in NO_FEET_SIZES:
            continue
        context = {k: data[k] for k in context_keys.get(criterion, ()) if k in data}
        detail = descriptions.get(criterion, criterion)
        if context:
            detail += ' · Chuẩn shot hiện hành (BYĐ đè yêu cầu gốc nếu có ngoại lệ): ' + json.dumps(context, ensure_ascii=False)
        add(criterion, detail, 'qc_checklist.' + criterion)
    if len({c['id'] for c in checks}) != len(checks):
        raise ValueError('Đặc tả trùng id')
    return checks


def schema(checks):
    return {'type': 'object', 'properties': {'observations': {'type': 'array', 'items': {
        'type': 'object', 'properties': {'id': {'type': 'string', 'enum': [c['id'] for c in checks]},
        'source': {'type': 'string'}, 'seen': {'type': 'string', 'enum': list(ENUM)},
        'region': {'type': ['array', 'null'], 'items': {'type': 'number'}, 'minItems': 4, 'maxItems': 4},
        'evidence': {'type': 'string'}}, 'required': ['id', 'source', 'seen', 'region', 'evidence'],
        'additionalProperties': False}},
        # Hai trường cũ được nhận nhưng không có vai trò trong kết luận.
        'criteria': {}, 'verdict': {}}, 'required': ['observations'], 'additionalProperties': False}


def judge(checks, obj, criteria):
    asked = {c['id']: c for c in checks}
    if not isinstance(obj, dict) or set(obj) - {'observations', 'criteria', 'verdict'}:
        raise ValueError('Trường ngoài schema quan sát')
    rows = obj.get('observations') if isinstance(obj, dict) else None
    if not isinstance(rows, list): raise ValueError('Thiếu observations')
    found = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'id', 'source', 'seen', 'region', 'evidence'}:
            raise ValueError('Quan sát sai schema')
        key = row['id']
        if not isinstance(key, str) or key not in asked or key in found: raise ValueError('Id lạ hoặc trùng')
        if row['source'] != asked[key]['source']: raise ValueError('Sai nguồn đặc tả')
        if row['seen'] not in ENUM: raise ValueError('Enum quan sát không hợp lệ')
        if not isinstance(row['evidence'], str) or not row['evidence'].strip(): raise ValueError('Thiếu bằng chứng')
        region = row['region']
        valid = (isinstance(region, list) and len(region) == 4 and
                 all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in region) and
                 region[0] < region[2] and region[1] < region[3])
        if not valid and not (region is None and row['seen'] == 'khong_chac'):
            raise ValueError('Vùng quan sát không hợp lệ')
        found[key] = row
    if set(found) != set(asked): raise ValueError('Thiếu id quan sát')
    yellow = [c['id'] for c in checks if found[c['id']]['seen'] == 'khong_chac' or c.get('needs_specialized_observation')]
    failures = [c for c in checks if found[c['id']]['seen'] not in (c['expected'], 'khong_chac') and not c.get('needs_specialized_observation')]
    scores = {k: (0.0 if any(c['criterion'] == k for c in failures) else 1.0) for k in criteria}
    return {'criteria': scores, 'yellow': yellow, 'issues': [c['detail'] for c in failures], 'observations': rows}


def _prepare(p, job, path, criteria, data):
    from . import llm_runner
    try:
        if not os.path.isfile(path):
            raise ValueError('Thiếu ảnh cần kiểm')
        for name in data.get('characters') or []:
            row = p.conn.execute('SELECT outfit_image_ids FROM characters WHERE project_id=? AND name=?',
                                 (job['project_id'], str(name))).fetchone()
            if row is not None and 'outfit_image_ids' in row.keys() and str(row['outfit_image_ids'] or '').strip():
                raise ValueError('Hồ sơ chuẩn cho OUTFIT riêng chưa được QC enum hỗ trợ: ' + str(name)
                                 + ' — cần người xem, không chấm theo trang phục mặc định Kho')
        checks = compile_checks(p.conn, job['project_id'], job['id'], data, criteria)
        cast = {str(n).upper() for n in data.get('characters') or []}
        from . import prompts
        from . import assets
        gaps = [g for g in assets.reference_gaps(p.conn, job['project_id'], data) if not assets.is_name_note(g)]   # rà 12/10: D17 notes never refuse QC
        if gaps: raise ValueError('Thiếu ảnh tham chiếu chuẩn: ' + '; '.join(gaps))
        refs = assets.without_atmosphere(assets.scene_references(p.conn, job['project_id'], data))   # 17/10: a sky is no QC standard
        if cast and not any(r['role'] == 'character' for r in refs):
            raise ValueError('Thiếu ảnh tham chiếu chuẩn nhân vật')
        from . import scene_storyboard
        missing = scene_storyboard.cast_missing(p.conn, job['project_id'], data, refs)
        if missing:
            raise ValueError('Thiếu ảnh tham chiếu trong gói: ' + ', '.join(missing))
        if any(not os.path.isfile(r['path']) for r in refs):
            raise ValueError('Thiếu file ảnh tham chiếu chuẩn')
        images = [(f"Ảnh cần kiểm job {job['id']}:", path)] + [
            (f"Ảnh chuẩn job {job['id']} — {r['label']}:", assets.thumbnail(r['path'], 900)) for r in refs]
        if any(not os.path.isfile(img) for _, img in images):
            raise ValueError('Thiếu file ảnh tham chiếu thực gửi')
    except ValueError as exc:
        raise llm_runner.LlmError(str(exc), code='qc_missing_input') from exc
    return checks, images


def observe_frames(p, frames, client, criteria):
    """Một lời gọi cho một khung hoặc cả cảnh; chỉ quan sát, không đổi job."""
    from . import llm_runner
    prepared = [(job, *_prepare(p, job, path, criteria, data)) for job, path, data in frames]
    checks = [c for _, cs, _ in prepared for c in cs]
    images = [img for _, _, imgs in prepared for img in imgs]
    prompt = ('Chỉ KHAI đặc điểm nhìn thấy trong ảnh cần kiểm, so với ảnh chuẩn gửi kèm. '
              'Mỗi id bắt đầu bằng job_id# chỉ kiểm ảnh cần kiểm của job đó; không nhầm ảnh chuẩn/ảnh job khác. '
              'thay = thấy đúng đặc điểm mô tả; khong_thay = thấy rõ đặc điểm không có/sai; '
              'khong_chac = bị che/không đủ bằng chứng. Vùng [x0,y0,x1,y1] chuẩn hóa 0..1, '
              'khong_chac cho phép region null. Không chấm điểm, không quyết đạt, không tự sửa. '
              'Đủ từng id, sao nguyên source, evidence mô tả vùng nhìn thấy. Schema JSON: '
              + json.dumps(schema(checks), ensure_ascii=False) + '\nĐặc điểm: '
              + json.dumps(checks, ensure_ascii=False))
    obj, tin, tout = llm_runner.ask_json(client, prompt, lambda o: judge(checks, o, criteria), images,
        note=llm_runner._retry_note(p, 'qc', frames[0][0]['project_id']))
    results = {}
    for job, cs, _ in prepared:
        ids = {c['id'] for c in cs}
        result = judge(cs, {'observations': [r for r in obj['observations'] if r['id'] in ids]}, criteria)
        results[job['id']] = result
    return {'results': results, 'input_tokens': tin, 'output_tokens': tout}


def observe_frame(p, job, client, path, criteria, data):
    obj = observe_frames(p, [(job, path, data)], client, criteria)
    return {**obj['results'][job['id']], 'input_tokens': obj['input_tokens'], 'output_tokens': obj['output_tokens']}


def hold(p, job_id, note, scene=False):
    """Khóa ghi trước kiểm trạng thái: không lấy lại quyết định của người trong lúc QC chạy."""
    from . import access
    from .states import JobState
    access.need_edit_job(p, job_id, 'ghi kết quả QC quan sát')
    p.conn.execute('BEGIN IMMEDIATE')
    try:
        state = p.state(job_id)
        allowed = (JobState.SUCCEEDED, JobState.PENDING_REVIEW) if scene else (JobState.SUCCEEDED,)
        if state not in allowed:
            p.conn.rollback()
            return 'already_processed'
        if scene:
            p.conn.execute('INSERT INTO qc_results (job_id, criterion, score, threshold_at_time, auto_decision) VALUES (?,?,?,?,?)',
                           (job_id, 'scene_qc_hold', 0.0, 1.0, 'hold'))
        if state == JobState.SUCCEEDED:
            p.transition(job_id, JobState.PENDING_REVIEW, actor='ai_agent', note=note)
        else:
            p.conn.commit()
        return 'pending_review'
    except Exception:
        p.conn.rollback()
        raise


def run(p, job, client, data_dir, path, criteria, data, images, autofix):
    result = observe_frame(p, job, client, path, criteria, data)
    if result['yellow']:
        issues = 'VÀNG — không chắc: ' + ', '.join(result['yellow'])
        decision = hold(p, job['id'], issues)
    else:
        issues = '; '.join(result['issues']) or None
        decision = p.apply_qc(job['id'], result['criteria'], issues=issues, autofix=autofix)
    return {'decision': decision, 'input_tokens': result['input_tokens'], 'output_tokens': result['output_tokens'], 'issues': issues,
            'observe': result}


def review_scene(p, pid, story_scene, client, data_dir, frames):
    """Layer 1 enum: một look/cảnh, chưa nghiệm thu nên giữ người; học việc chỉ ghi sổ."""
    from . import access, llm_runner, money_policy, project_budget, prompts, qc_scene, trainee
    access.need_edit(p, pid, 'chạy QC quan sát theo cảnh')
    todo = [r for r in frames if p.job(r['job_id'])['state'] in ('succeeded', 'pending_review')]
    if not todo:
        return {'applied': {}, 'results': {}}
    shadow = qc_scene.shadow()
    money_policy.note(p.conn, project_budget.warning(p.conn, pid, 'claude_qc', 0.03 * len(todo)), stage='qc', project_id=pid,
                      key=f'qc_observe:{pid}')
    with llm_runner.tagged('qc' if not shadow else 'trainee_qc_team', pid):
        obj = observe_frames(p, [(p.job(r['job_id']), r['path'], r['data']) for r in todo], client, prompts.qc_criteria())
    applied, results = {}, {}
    for k, r in enumerate(frames, 1):
        result = obj['results'].get(r['job_id'])
        if result is None:
            continue
        verdict = 'doubt' if result['yellow'] else 'fail' if result['issues'] else 'pass'
        results[str(r['job_id'])] = verdict
        if shadow:
            trainee.record(p.conn, 'scene_qc', pid, f"job:{r['job_id']}", 'flag' if verdict != 'pass' else 'pass',
                           would_do={'observe': result}, detail={'verdict': verdict}, job_id=r['job_id'], story_scene=story_scene)
            applied[f'K{k}'] = 'học việc (đã ghi)'
            continue
        flags = qc_scene.flags_of(data_dir, pid, r['job_id'])
        note = f'QC quan sát cảnh (chưa nghiệm thu): {verdict} — ' + '; '.join(result['issues'])
        if result['yellow']:
            note += ' VÀNG — ' + ', '.join(result['yellow'])
        if flags:
            note += ' · cờ lớp 0: ' + '; '.join(f['problem'] for f in flags)
        decision = hold(p, r['job_id'], note[:2000], scene=True)
        applied[f'K{k}'] = 'giữ cho người (' + verdict + ')' if decision == 'pending_review' else 'already_processed'
    return {'applied': applied, 'results': results, 'observations': obj['results'],
            'input_tokens': obj['input_tokens'], 'output_tokens': obj['output_tokens']}
