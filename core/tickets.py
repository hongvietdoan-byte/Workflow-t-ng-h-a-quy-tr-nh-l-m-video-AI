"""Kho phiếu cùng manifest; caller cung cấp Identity từ session server đã xác thực.

Không xem Identity tự tạo hoặc tên actor là bằng chứng đăng nhập. Adapter HTTP
phải resolve session qua core.auth trước gọi; pet chỉ được dùng admin_snapshot.
Không gọi API, gen, ghi ledger hoặc sửa dữ liệu sản xuất từ module này.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from . import auth, budget, diag, features

JSON_FIELDS = {'impact', 'cause', 'workaround', 'evidence_refs', 'technical', 'verification'}
KINDS = {'code', 'budget', 'shared_asset', 'operation', 'unknown'}
CODE_PATH = ['new', 'triaged', 'waiting_admin', 'assigned', 'investigating', 'fixing',
             'verifying', 'waiting_merge', 'deployed', 'resolved', 'closed']
ACTION_PATH = ['new', 'triaged', 'waiting_admin', 'approved', 'applied', 'verified', 'closed']

class TicketError(ValueError):
    """Thông báo có thể hiện cho admin, không chứa payload hoặc khóa."""

def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def _hash(value):
    return hashlib.sha256(_json(value).encode('utf8')).hexdigest()

def _time(value=None):
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)  # SQLite datetime('now') là UTC.
    return value.astimezone(timezone.utc)

@contextmanager
def _transaction(conn):
    # RELEASE ngoài transaction tự commit; trong transaction giữ quyền caller.
    name = 'ticket_' + uuid.uuid4().hex
    conn.execute('SAVEPOINT ' + name)
    try:
        yield
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT ' + name)
        conn.execute('RELEASE SAVEPOINT ' + name)
        raise
    else:
        conn.execute('RELEASE SAVEPOINT ' + name)

def _safe(value):
    """Chỉ payload lọc; không nhận base64, path máy hoặc secret key."""
    if isinstance(value, dict):
        for key, item in value.items():
            if any(word in str(key).lower() for word in ('token', 'password', 'api_key', 'secret')):
                raise TicketError('Không lưu khóa bí mật trong phiếu')
            _safe(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _safe(item)
    elif isinstance(value, str):
        path = value.replace('\\', '/')
        if 'base64,' in value or re.search(r'[A-Za-z]:/', path) or path.startswith(('//', '/Users/', '/home/')):
            raise TicketError('Chỉ lưu tham chiếu bằng chứng đã lọc, không đường dẫn máy/base64')
        if not re.fullmatch(r'[0-9a-f]{40,64}', value) and diag.redact(value) != value:
            raise TicketError('Bằng chứng chưa lọc thông tin bí mật')

def _actor(actor, owner=False):
    if owner:
        if not isinstance(actor, auth.Identity) or actor.role != 'owner' or not actor.email.strip():
            raise TicketError('Cần danh tính Owner từ session đã xác thực phía server')
        return actor.email
    value = actor.email if isinstance(actor, auth.Identity) else actor
    if not isinstance(value, str) or not value.strip():
        raise TicketError('Thiếu người thực hiện')
    _safe(value)
    return value.strip()

def _decode(row):
    result = dict(row)
    for field in JSON_FIELDS:
        result[field] = json.loads(result[field])
    return result

def get(conn, ticket_id):
    row = conn.execute('SELECT * FROM support_tickets WHERE id=?', (ticket_id,)).fetchone()
    if row is None:
        raise TicketError('Không tìm thấy phiếu')
    return _decode(row)

def list_tickets(conn):
    if not features.on('support_tickets'):
        return []
    return [_decode(r) for r in conn.execute('SELECT * FROM support_tickets ORDER BY due_at, created_at')]

def _merge_refs(old, new):
    out = dict(old)
    for key, values in new.items():
        if not isinstance(values, list):
            raise TicketError('Bằng chứng phải là danh sách tham chiếu')
        out[key] = list(old.get(key, []))
        for value in values:
            if value not in out[key]:
                out[key].append(value)
    return out

def _event(conn, before, after, actor, reason, action, now):
    conn.execute('INSERT INTO ticket_events VALUES (?,?,?,?,?,?,?,?,?)',
                 (str(uuid.uuid4()), after['id'], now.isoformat(), actor, action,
                  _hash(before) if before else None, _hash(after), reason, _json(after['evidence_refs'])))
    conn.execute('INSERT INTO audit_log(at,email,action,detail) VALUES(?,?,?,?)',
                 (now.isoformat(), actor, 'support_ticket.' + action,
                  _json({'ticket_id':after['id'], 'before_hash':_hash(before) if before else None,
                         'after_hash':_hash(after), 'reason':reason})))

def _update(conn, before, after):
    fields = [key for key in after if key != 'id']
    values = [_json(after[key]) if key in JSON_FIELDS else after[key] for key in fields]
    cur = conn.execute('UPDATE support_tickets SET '+','.join(key+'=?' for key in fields)+
                       ' WHERE id=? AND revision=?', (*values, before['id'], before['revision']))
    if cur.rowcount != 1:
        raise TicketError('Phiếu đã thay đổi; tải lại trước khi quyết định')

def open_or_merge(conn, *, title, kind, source_actor, root_cause, project_id=None,
                  scene_id=None, job_id=None, taxonomy_revision='1', error_type=None,
                  severity='error', impact=None, cause=None, requested_action=None,
                  owner_actor=None, assigned_to=None, workaround=None, evidence_refs=None,
                  technical=None, now=None):
    if not features.on('support_tickets'):
        return None
    actor = _actor(source_actor)
    if kind not in KINDS or not title.strip() or not root_cause.strip():
        raise TicketError('Thiếu tiêu đề, loại phiếu hoặc nguyên nhân định danh')
    at = _time(now)
    refs = _merge_refs({}, evidence_refs or {})
    cause = cause or {'confidence':'guess', 'summary':root_cause, 'evidence_refs':refs}
    if cause.get('confidence') not in ('guess', 'confirmed'):
        raise TicketError('Nguyên nhân cần mức đoán hoặc đã xác nhận')
    if cause['confidence'] == 'confirmed' and not any((cause.get('evidence_refs') or {}).values()):
        raise TicketError('Nguyên nhân đã xác nhận cần bằng chứng')
    fingerprint = _hash([kind, project_id, root_cause, str(taxonomy_revision)])
    payload = dict(title=title.strip().lower(), kind=kind, error_type=error_type,
                   taxonomy_revision=str(taxonomy_revision), severity=severity,
                   project_id=project_id, scene_id=scene_id, job_id=job_id, fingerprint=fingerprint,
                   source_actor=actor, created_at=at.isoformat(), due_at=(at+timedelta(hours=72)).isoformat(),
                   original_due_at=(at+timedelta(hours=72)).isoformat(), owner_actor=owner_actor,
                   state='new', impact=impact or {'money_usd':None, 'money_unknown':True}, cause=cause,
                   requested_action=requested_action, assigned_to=assigned_to, workaround=workaround or {},
                   evidence_refs=refs, technical=technical or {}, verification={}, resolution=None,
                   closed_by=None, closed_at=None, revision=1)
    _safe(payload)
    with _transaction(conn):
        # Một câu INSERT conflict không đè phiếu; revision CAS bảo vệ merge.
        keys = ['id', *payload]
        ident = str(uuid.uuid4())
        vals = [ident, *(_json(v) if k in JSON_FIELDS else v for k,v in payload.items())]
        inserted = conn.execute('INSERT INTO support_tickets('+','.join(keys)+') VALUES ('+
                                ','.join('?' for _ in keys)+') ON CONFLICT(fingerprint) DO NOTHING', vals).rowcount
        if inserted:
            after = get(conn,ident)
            _event(conn,None,after,actor,'lập phiếu','open',at)
        else:
            before = _decode(conn.execute('SELECT * FROM support_tickets WHERE fingerprint=?',(fingerprint,)).fetchone())
            after = dict(before)
            after['evidence_refs'] = _merge_refs(before['evidence_refs'],refs)
            after['revision'] += 1
            _update(conn,before,after)
            _event(conn,before,after,actor,'bổ sung bằng chứng','merge',at)
    return after

def allowed_transitions(ticket):
    path = ACTION_PATH if ticket['kind'] in ('budget','shared_asset') else CODE_PATH
    state = ticket['state']
    if state in ('blocked','waiting_info','reopened'):
        return {'triaged'}
    choices = {path[path.index(state)+1]} if state in path and state != 'closed' else set()
    if state == 'waiting_admin' and ticket['kind'] in ('budget','shared_asset'):
        choices.add('rejected')
    if state == 'rejected':
        choices.add('closed')
    if state in ('closed','resolved','verified','rejected'):
        choices.add('reopened')
    elif state not in ('blocked','waiting_info'):
        choices.update(('blocked','waiting_info'))
    return choices

def transition(conn, id, to, actor, reason, expected_state, *, expected_revision=None,
               technical=None, verification=None, resolution=None, now=None):
    if not features.on('support_tickets'):
        return None
    who = _actor(actor,owner=True)
    if not reason.strip():
        raise TicketError('Cần lý do chuyển trạng thái')
    at = _time(now)
    with _transaction(conn):
        before=get(conn,id)
        if before['state'] != expected_state or (expected_revision is not None and before['revision'] != expected_revision):
            raise TicketError('Phiếu đã thay đổi; tải lại trước khi quyết định')
        if to not in allowed_transitions(before):
            raise TicketError('Chuyển trạng thái không hợp lệ')
        after=dict(before)
        for field, value in [('technical',technical),('verification',verification)]:
            if value is not None:
                after[field] = {**before[field], **value}
        if to == 'deployed' and not (after['technical'].get('deploy_commit') and
                                     after['verification'].get('health') is True and after['verification'].get('real_case')):
            raise TicketError('Triển khai cần commit, health và bằng chứng kiểm ca thật')
        after.update(state=to,revision=before['revision']+1)
        if resolution is not None:
            after['resolution']=resolution
        if to == 'closed':
            after.update(closed_by=who,closed_at=at.isoformat())
        if to == 'reopened':
            after.update(closed_by=None,closed_at=None)
        _safe(after); _safe(reason)
        _update(conn,before,after)
        _event(conn,before,after,who,reason,expected_state+'->'+to,at)
    return after

def extend_due(conn, id, new_due, actor, reason, *, expected_revision, now=None):
    if not features.on('support_tickets'):
        return None
    who=_actor(actor,owner=True)
    if not reason.strip():
        raise TicketError('Gia hạn cần lý do')
    at=_time(now)
    due=_time(new_due)
    with _transaction(conn):
        before=get(conn,id)
        if before['revision'] != expected_revision:
            raise TicketError('Phiếu đã thay đổi; tải lại trước khi gia hạn')
        if due <= _time(before['due_at']) or due <= at or before['state']=='closed':
            raise TicketError('Hạn mới phải muộn hơn hạn hiện tại và phiếu phải đang mở')
        after={**before,'due_at':due.isoformat(),'revision':before['revision']+1}
        _safe(reason)
        _update(conn,before,after)
        _event(conn,before,after,who,reason,'extend_due',at)
    return after

def due_status(ticket, now=None):
    if ticket['state']=='closed':
        return 'closed'
    left = _time(ticket['due_at']) - _time(now)
    return 'red' if left <= timedelta() else 'yellow' if left <= timedelta(hours=24) else 'green'

def user_projection(ticket, *, project_id=None):
    # Caller phải kiểm ACL dự án; scope thiếu thì fail closed.
    if project_id is None or ticket.get('project_id') != project_id:
        return None
    blocked = bool(ticket.get('impact',{}).get('blocked_shots') or ticket.get('impact',{}).get('blocked_projects'))
    return {'error':ticket['title'], 'message':'đã báo admin, dự án tạm dừng ở shot này' if blocked else ''}

def admin_snapshot(conn, *, now=None, pricing=None, data_dir=None):
    at=_time(now)
    out={'schema_version':1, 'enabled':features.on('support_tickets'), 'available':True,
         'at':at.isoformat(), 'ticket_counts':{}, 'due':{'yellow':0,'red':0},
         'spend_today':{'usd':None,'pending':None,'pending_unknown':True,'unknown':[]}, 'stuck_jobs':[],
         'gen_done_projects':[], 'ticket_summaries':[], 'blocked_count':0, 'warnings':[]}
    if not out['enabled']:
        return out
    try:
        rows=list_tickets(conn)
        out['ticket_counts']=dict(Counter(r['state'] for r in rows))
        out['ticket_summaries']=[{'id':r['id'],'revision':r['revision'],'title':r['title'],'kind':r['kind'],
                                  'state':r['state'],'due_at':r['due_at'],'due_status':due_status(r,at),
                                  'project_id':r['project_id'],'blocked':bool(r['impact'].get('blocked_shots') or r['impact'].get('blocked_projects'))} for r in rows]
        out['blocked_count']=sum(r['blocked'] for r in out['ticket_summaries'] if r['state']!='closed')
        out['due']=dict(Counter({key:sum(due_status(r,at)==key for r in rows) for key in ('yellow','red')}))
        # Sổ chi dùng cả SQLite UTC và ISO UTC; ngày đầu vào khớp cả hai.
        since=at.replace(hour=0,minute=0,second=0,microsecond=0).strftime('%Y-%m-%d')
        spent=budget.spent(conn,pricing=pricing,since=since)
        out['spend_today'].update(usd=spent['usd'],unknown=spent['unknown'])
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'llm_holds' in tables:
            out['spend_today']['pending']=conn.execute('SELECT COALESCE(SUM(usd),0) FROM llm_holds WHERE julianday(at)>=julianday(?)',((at-timedelta(minutes=budget.HOLD_MINUTES)).isoformat(),)).fetchone()[0]
        else:
            out['warnings'].append('Chưa có sổ giữ tiền: pending chưa rõ')
        runner=sys.modules.get('core.runner')
        waits=getattr(runner,'WAIT_REASONS',{}) if runner else {}
        if runner is None:
            out['warnings'].append('WAIT_REASONS chưa có trong tiến trình này')
        for j in conn.execute("SELECT id,project_id,type,state,updated_at,created_at FROM jobs WHERE state IN ('running','queued','retryable')"):
            age=(at-_time(j['updated_at'] or j['created_at'])).total_seconds()/60
            limit=diag.STUCK_MIN.get(j['type'],None) if j['state']=='running' else diag.QUEUED_MIN
            if limit is not None and age>limit:
                hit=waits.get(j['id'])
                out['stuck_jobs'].append({'job_id':j['id'],'project_id':j['project_id'],'state':j['state'],
                                          'age_minutes':round(age,1),'reason':diag.redact(hit[0]) if hit else None})
        # DONE của autopilot là hoàn tất dựng; gen xong khi mọi shot có clip terminal,
        # có thể còn chờ người duyệt; không coi bộ shot rỗng là xong.
        for p in conn.execute('SELECT id FROM projects'):
            pid=p['id']
            scenes=conn.execute('SELECT id FROM scenes WHERE project_id=?',(pid,)).fetchall()
            if not scenes:
                continue
            complete=True
            for scene in scenes:
                latest=conn.execute("SELECT state,result_path,sent_package FROM jobs WHERE scene_id=? AND type='video_gen' ORDER BY id DESC LIMIT 1",(scene['id'],)).fetchone()
                if not latest or latest['state'] not in ('succeeded','approved','pending_review') or not latest['result_path']:
                    complete=False;break
                motion=conn.execute('SELECT motion_prompt,image_job_id FROM motion_prompts WHERE scene_id=?',(scene['id'],)).fetchone()
                image=conn.execute("SELECT result_path FROM jobs WHERE id=? AND state='approved'",(motion['image_job_id'],)).fetchone() if motion else None
                try:
                    package=json.loads(latest['sent_package'] or '{}')
                    if not isinstance(package,dict):
                        raise ValueError('Gói gen không phải object')
                    refs=package.get('refs', [])
                    if not isinstance(refs,list) or any(not isinstance(r,dict) for r in refs):
                        raise ValueError('Tham chiếu gói gen không hợp lệ')
                    image_path=image['result_path'] if image else None
                    if image_path and not os.path.isabs(image_path):
                        image_path=os.path.join(data_dir,image_path) if data_dir else None
                    from .sent_package import sha256_of
                    image_sha=sha256_of(image_path) if image_path else None
                except (OSError, ValueError, TypeError):
                    out['warnings'].append('Dự án '+str(pid)+': không đọc được bằng chứng/gói gen hiện hành')
                    complete=False;break
                # Thiếu dấu đầu vào hiện hành thì chưa thể xác nhận gen xong.
                if not motion or not image or not image_sha or package.get('prompt') != motion['motion_prompt'] or not any(r.get('param')=='image_path' and r.get('sha256')==image_sha for r in refs):
                    out['warnings'].append('Dự án '+str(pid)+': chưa xác nhận gói gen khớp đầu vào hiện hành')
                    complete=False;break
            if complete and not conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND state IN ('queued','running','retryable') LIMIT 1",(pid,)).fetchone():
                out['gen_done_projects'].append(pid)
    except (sqlite3.Error, ValueError, KeyError) as exc:
        out['available']=False
        out['warnings'].append('Không đọc được snapshot: '+type(exc).__name__)
    return out
