"""Store A opt-in trên connection manifest của server; không tự khởi tạo."""
import copy
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import access, features
from .stage_registry_resolver import validate_registry, resolve_shot, resolve_state, RegistryValidationError
from .stage_registry_schema import validate_bundle

KINDS = ('stages', 'segments', 'states', 'cameras', 'shots')
MAX_JSON = 2_000_000
MAX_HISTORY_ROWS = 5000
MAX_HISTORY_BYTES = 16_000_000
MAX_METADATA_ROWS = 10000
SCHEMA_SQL = [
    'CREATE TABLE IF NOT EXISTS stage_registry_schema(singleton INTEGER PRIMARY KEY CHECK(singleton=1),version INTEGER NOT NULL)',
    'CREATE TABLE IF NOT EXISTS stage_registry_revisions(project_id INTEGER NOT NULL,kind TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL CHECK(revision>0),payload TEXT NOT NULL,PRIMARY KEY(project_id,kind,id,revision),FOREIGN KEY(project_id) REFERENCES projects(id))',
    'CREATE TABLE IF NOT EXISTS stage_registry_heads(project_id INTEGER NOT NULL,kind TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(project_id,kind,id),FOREIGN KEY(project_id,kind,id,revision) REFERENCES stage_registry_revisions(project_id,kind,id,revision))',
    'CREATE TABLE IF NOT EXISTS stage_registry_requests(project_id INTEGER NOT NULL,operation TEXT NOT NULL,request_id TEXT NOT NULL,actor TEXT NOT NULL,hash TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(project_id,operation,request_id))',
    'CREATE TABLE IF NOT EXISTS stage_registry_audit(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL,operation TEXT NOT NULL,actor TEXT NOT NULL,created_at_utc TEXT NOT NULL,reason TEXT NOT NULL,result TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS stage_registry_outbox(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL,event TEXT NOT NULL,payload TEXT NOT NULL,acked INTEGER NOT NULL DEFAULT 0 CHECK(acked IN (0,1)))',
]
APPEND_ONLY = ('stage_registry_revisions', 'stage_registry_audit', 'stage_registry_requests')

def _trigger_sql(table, op):
    return f"CREATE TRIGGER IF NOT EXISTS {table}_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT,'append-only'); END"

def _sql_shape(sql):
    return re.sub(r"\s+", "", re.sub(r"(?i)IF\s+NOT\s+EXISTS\s+", "", sql)).lower().rstrip(";")

class RegistryStoreError(ValueError): pass
class RegistryNotReady(RegistryStoreError): pass
class RegistryConflict(RegistryStoreError): pass
class RegistryLocked(RegistryStoreError): pass
class RegistryTransactionError(RegistryStoreError): pass

def _positive(value):
    if type(value) is not int or not 0 < value < 2**63:
        raise RegistryStoreError('ID/revision phải là số nguyên dương SQLite.')
    return value

def _id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',value):
        raise RegistryStoreError('ID không hợp lệ.')
    return value

def _dump(value):
    try:
        raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
        size=len(raw.encode('utf-8'))
    except (ValueError,TypeError,RecursionError,UnicodeError): raise RegistryStoreError('JSON không hợp lệ.') from None
    if size>MAX_JSON: raise RegistryStoreError('JSON vượt giới hạn.')
    return raw


def _load(raw):
    try:
        if not isinstance(raw,str) or len(raw.encode('utf-8'))>MAX_JSON: raise ValueError
    except (ValueError,UnicodeError): raise RegistryStoreError('Dữ liệu lưu hỏng hoặc quá lớn.') from None
    def pairs(items):
        obj={}
        for key,value in items:
            if key in obj: raise ValueError
            obj[key]=value
        return obj
    def constant(value): raise ValueError
    try: return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)
    except (ValueError,RecursionError,UnicodeError): raise RegistryStoreError('Dữ liệu lưu hỏng.') from None


def _changes(a,b,path=''):
    if type(a)!=type(b): return {path}
    if isinstance(a,dict):
        out=set()
        for k in a.keys()|b.keys():
            p=f'{path}.{k}' if path else k
            out |= {p} if k not in a or k not in b else _changes(a[k],b[k],p)
        return out
    if isinstance(a,list):
        out=set()
        for i in range(max(len(a),len(b))):
            out |= {f'{path}[{i}]'} if i>=len(a) or i>=len(b) else _changes(a[i],b[i],f'{path}[{i}]')
        return out
    return {path} if a!=b else set()

def _overlap(a,b): return a==b or a.startswith(b+'.') or a.startswith(b+'[') or b.startswith(a+'.') or b.startswith(a+'[')

class StageRegistryStore:
    def __init__(self,p,*,opt_in=False):
        self.p=p; self.conn=p.conn; self.opt_in=opt_in

    def _gate(self):
        if self.opt_in is not True or not features.on('stage_registry_a'):
            raise RegistryNotReady('Registry A đang TẮT hoặc chưa opt-in.')

    def _acl(self,pid,edit=False):
        _positive(pid)
        (access.need_edit if edit else access.need_view)(self.p,pid,'thao tác Registry A')
        if self.conn.execute('SELECT 1 FROM projects WHERE id=?',(pid,)).fetchone() is None:
            raise RegistryStoreError('Không tìm thấy dự án.')

    def _ready(self):
        self._gate()
        try:
            row=self.conn.execute('SELECT version FROM stage_registry_schema WHERE singleton=1').fetchone()
            if row is None or row[0]!=1: raise RegistryNotReady('Schema Registry A không tương thích.')
            required={'stage_registry_revisions','stage_registry_heads','stage_registry_requests','stage_registry_audit','stage_registry_outbox'}
            names={r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not required<=names: raise RegistryNotReady('Registry A chưa bootstrap đầy đủ.')
            columns={'stage_registry_revisions':{'project_id','kind','id','revision','payload'},'stage_registry_heads':{'project_id','kind','id','revision'},'stage_registry_requests':{'project_id','operation','request_id','actor','hash','result'},'stage_registry_audit':{'id','project_id','operation','actor','created_at_utc','reason','result'},'stage_registry_outbox':{'id','project_id','event','payload','acked'}}
            for table,expected in columns.items():
                if {r[1] for r in self.conn.execute(f'PRAGMA table_info({table})')}!=expected:
                    raise RegistryNotReady('Schema Registry A không tương thích.')
            definitions={r[0]:r[1] for r in self.conn.execute("SELECT name,sql FROM sqlite_master WHERE type IN ('table','trigger') AND name LIKE 'stage_registry_%'")}
            for sql in SCHEMA_SQL:
                name=re.search(r'EXISTS ([a-z_]+)',sql).group(1)
                if _sql_shape(definitions.get(name,''))!=_sql_shape(sql):
                    raise RegistryNotReady('Schema Registry A không đúng constraints đã chốt.')
            expected_triggers={f'{table}_{op.lower()}' for table in APPEND_ONLY for op in ('UPDATE','DELETE')}
            actual_triggers={r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name LIKE 'stage_registry_%'")}
            if actual_triggers!=expected_triggers:
                raise RegistryNotReady('Registry A có trigger lạ hoặc thiếu guard.')
            for table in APPEND_ONLY:
                for op in ('UPDATE','DELETE'):
                    name=f'{table}_{op.lower()}'
                    if _sql_shape(definitions.get(name,''))!=_sql_shape(_trigger_sql(table,op)):
                        raise RegistryNotReady('Registry A thiếu guard append-only đúng hợp đồng.')
        except sqlite3.DatabaseError: raise RegistryNotReady('Registry A chưa sẵn sàng.') from None

    @contextmanager
    def _tx(self,write=False):
        if write and self.conn.in_transaction:
            raise RegistryTransactionError('Ghi Registry A cần connection không có transaction ngoài; caller tự commit/rollback trước.')
        owned=not self.conn.in_transaction
        try:
            if owned: self.conn.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield
            if owned: self.conn.commit()
        except sqlite3.DatabaseError:
            if owned: self.conn.rollback()
            raise RegistryStoreError('SQLite Registry A chưa sẵn sàng hoặc dữ liệu không hợp lệ.') from None
        except BaseException:
            if owned: self.conn.rollback()
            raise

    def bootstrap(self,pid):
        self._gate()
        with self._tx(True):
            self._acl(pid,True)
            for sql in SCHEMA_SQL: self.conn.execute(sql)
            self.conn.execute('INSERT OR IGNORE INTO stage_registry_schema VALUES(1,1)')
            for table in APPEND_ONLY:
                for op in ('UPDATE','DELETE'): self.conn.execute(_trigger_sql(table,op))
            self._ready()

    def _actor(self):
        u=access.user_of(getattr(self.p,'user',None)); return u['email'] if u else 'trusted-system'

    def _kind(self,kind):
        if kind not in KINDS: raise RegistryStoreError('Loại aggregate không hợp lệ.')
        return kind

    def _preflight(self,pid):
        count,size=self.conn.execute('SELECT COUNT(*),COALESCE(SUM(length(CAST(payload AS BLOB))),0) FROM stage_registry_revisions WHERE project_id=?',(pid,)).fetchone()
        if count>MAX_HISTORY_ROWS or size>MAX_HISTORY_BYTES:
            raise RegistryStoreError('Lịch sử Registry vượt trần đọc; cần phân trang/lưu trữ qua giao thức riêng.')

    def _heads(self,pid):
        self._preflight(pid)
        groups={}
        for kind,ident,count,lo,hi in self.conn.execute('SELECT kind,id,COUNT(*),MIN(revision),MAX(revision) FROM stage_registry_revisions WHERE project_id=? GROUP BY kind,id',(pid,)):
            self._kind(kind); _id(ident); _positive(hi)
            if lo!=1 or hi!=count: raise RegistryStoreError('Chuỗi revision lưu hỏng.')
            groups[kind,ident]=hi
        heads={}
        for kind,ident,revision in self.conn.execute('SELECT kind,id,revision FROM stage_registry_heads WHERE project_id=?',(pid,)):
            self._kind(kind); _id(ident); _positive(revision)
            heads[kind,ident]=revision
        if heads!=groups: raise RegistryStoreError('Head lưu hỏng, thiếu hoặc không phải revision hiện hành.')
        return heads

    def _revision(self,pid,kind,ident,revision):
        raw=self.conn.execute('SELECT payload FROM stage_registry_revisions WHERE project_id=? AND kind=? AND id=? AND revision=?',(pid,kind,ident,revision)).fetchone()
        if raw is None: raise RegistryStoreError('Mất revision đã ghim.')
        row=_load(raw[0])
        if (not isinstance(row,dict) or row.get('id')!=ident or type(row.get('revision')) is not int or row['revision']!=revision
                or type(row.get('project_id')) is not int or row['project_id']!=pid or row.get('parent_revision')!=(revision-1 if revision>1 else None)):
            raise RegistryStoreError('Revision lưu hỏng hoặc không khớp metadata.')
        return row

    def _head(self,pid,kind,ident):
        revision=self._heads(pid).get((kind,ident))
        return self._revision(pid,kind,ident,revision) if revision else None

    @staticmethod
    def _dependencies(kind,row):
        fields={'stages':{},'segments':{'stage':'stages','initial_state':'states','continuation_from_state':'states'},
                'states':{'segment':'segments','parent_state':'states'},'cameras':{'stage':'stages','state':'states'},
                'shots':{'stage':'stages','segment':'segments','state_start':'states','state_end':'states','camera':'cameras'}}
        refs=[]
        for field,target in fields[kind].items():
            pin=row.get(field)
            if pin is not None:
                if not isinstance(pin,dict) or set(pin)!={'id','revision'}: raise RegistryStoreError('Pin lưu hỏng.')
                refs.append((target,_id(pin['id']),_positive(pin['revision'])))
        if kind=='shots':
            if not isinstance(row.get('beats'),list): raise RegistryStoreError('Nhịp shot lưu hỏng.')
            for pin in row['beats']:
                if not isinstance(pin,dict) or set(pin)!={'id','revision'}: raise RegistryStoreError('Pin nhịp lưu hỏng.')
                refs.append(('states',_id(pin['id']),_positive(pin['revision'])))
        return refs

    def _bundle(self,pid,*,proposed=(),seeds=(),active=True,head_index=None):
        heads=dict(self._heads(pid) if head_index is None else head_index)
        overrides={(kind,row['id'],row['revision']):row for kind,row in proposed}
        for kind,row in proposed: heads[kind,row['id']]=row['revision']
        pending=list(seeds)+([(k,i,r) for (k,i),r in heads.items()] if active else [])
        loaded={}; total=0
        while pending:
            kind,ident,revision=pending.pop()
            if (kind,ident,revision) in loaded: continue
            self._kind(kind); _id(ident); _positive(revision)
            row=overrides.get((kind,ident,revision))
            if row is None: row=self._revision(pid,kind,ident,revision)
            total+=len(_dump(row).encode('utf-8'))
            if len(loaded)>=MAX_HISTORY_ROWS or total>MAX_HISTORY_BYTES:
                raise RegistryStoreError('Closure Registry vượt trần đọc.')
            loaded[kind,ident,revision]=row
            pending.extend(self._dependencies(kind,row))
        b=dict(schema_version=1,project_id=pid,**{k:[] for k in KINDS})
        for (kind,ident,revision),row in sorted(loaded.items()): b[kind].append(row)
        self._validate(b)
        return b

    def _validate(self,b):
        if validate_registry(b)['errors']: raise RegistryStoreError('Registry không hợp lệ theo cổng semantic.')

    def _external(self,b):
        # Chỉ dependencies của candidate live mới; lịch sử là metadata immutable.
        for shot in b['shots']:
            if self.conn.execute('SELECT 1 FROM scenes WHERE id=? AND project_id=?',(shot['scene_id'],b['project_id'])).fetchone() is None:
                raise RegistryStoreError('Cảnh không thuộc dự án.')
        for stage in b['stages']:
            asset_ids=[stage['source_asset_id']]
            for obj in stage['objects']:
                if 'look_id' in obj:
                    raise RegistryStoreError('Mapping bộ dạng/ảnh Kho chưa chốt; không nhận look pin trong store.')
                if 'asset_id' in obj: asset_ids.append(obj['asset_id'])
            for aid in asset_ids:
                row=self.conn.execute('SELECT project_id FROM assets WHERE id=?',(aid,)).fetchone()
                attached=self.conn.execute('SELECT 1 FROM project_assets WHERE project_id=? AND asset_id=?',(b['project_id'],aid)).fetchone()
                if row is None or (row[0] is not None and row[0]!=b['project_id']) or not attached:
                    raise RegistryStoreError('Tài nguyên không thuộc phạm vi dự án.')

    def _saved(self,pid,raw,operation=None):
        value=_load(raw)
        if not isinstance(value,dict) or set(value)!={'project_id','operation','revisions'} or type(value['project_id']) is not int or value['project_id']!=pid or value['operation'] not in ('apply','undo','unlock') or (operation is not None and value['operation']!=operation):
            raise RegistryStoreError('Metadata request/audit/outbox lưu hỏng.')
        revisions=value['revisions']
        if not isinstance(revisions,list) or not revisions or len(revisions)>MAX_HISTORY_ROWS:
            raise RegistryStoreError('Metadata revision lưu hỏng.')
        seen=set()
        for row in revisions:
            if not isinstance(row,dict) or set(row)!={'kind','id','revision'}: raise RegistryStoreError('Metadata revision lưu hỏng.')
            key=(self._kind(row['kind']),_id(row['id']),_positive(row['revision']))
            if key[:2] in seen: raise RegistryStoreError('Metadata revision trùng.')
            seen.add(key[:2])
            if self.conn.execute('SELECT 1 FROM stage_registry_revisions WHERE project_id=? AND kind=? AND id=? AND revision=?',(pid,*key)).fetchone() is None:
                raise RegistryStoreError('Metadata tham chiếu revision mất.')
        return value

    def _metadata_budget(self,pid,table,column):
        count,size=self.conn.execute(f'SELECT COUNT(*),COALESCE(SUM(length(CAST({column} AS BLOB))),0) FROM {table} WHERE project_id=?',(pid,)).fetchone()
        if count>MAX_METADATA_ROWS or size>MAX_HISTORY_BYTES: raise RegistryStoreError('Metadata Registry vượt trần đọc.')
        return count,size

    def head(self,pid,kind,ident):
        self._gate(); self._kind(kind); _id(ident)
        with self._tx():
            self._acl(pid); self._ready(); heads=self._heads(pid)
            revision=heads.get((kind,ident))
            if revision is None: return None
            b=self._bundle(pid,seeds=[(kind,ident,revision)],active=False,head_index=heads)
            return next(r for r in b[kind] if r['id']==ident and r['revision']==revision)

    def history(self,pid,kind,ident):
        self._gate(); self._kind(kind); _id(ident)
        with self._tx():
            self._acl(pid); self._ready(); self._preflight(pid)
            seeds=[(kind,ident,r[0]) for r in self.conn.execute('SELECT revision FROM stage_registry_revisions WHERE project_id=? AND kind=? AND id=? ORDER BY revision',(pid,kind,ident))]
            b=self._bundle(pid,seeds=seeds,active=False)
            return [r for r in b[kind] if r['id']==ident]

    def snapshot(self,pid,ident,revision,*,kind='shot'):
        self._gate(); _id(ident); _positive(revision)
        if kind not in ('shot','state'): raise RegistryStoreError('Loại snapshot không hợp lệ.')
        with self._tx():
            self._acl(pid); self._ready(); b=self._bundle(pid,seeds=[('shots' if kind=='shot' else 'states',ident,revision)],active=False)
            try: return (resolve_shot if kind=='shot' else resolve_state)(b,ident,revision)
            except RegistryValidationError: raise RegistryStoreError('Không có snapshot pin hợp lệ.') from None

    def request(self,pid,operation,request_id):
        self._gate(); _id(request_id)
        if operation not in ('apply','undo','unlock'): raise RegistryStoreError('Operation không hợp lệ.')
        with self._tx():
            self._acl(pid); self._ready(); self._metadata_budget(pid,'stage_registry_requests','result')
            r=self.conn.execute('SELECT result FROM stage_registry_requests WHERE project_id=? AND operation=? AND request_id=?',(pid,operation,request_id)).fetchone()
            return self._saved(pid,r[0],operation) if r else None

    def apply(self,pid,rows,expected_revisions,*,request_id,reason):
        return self._write(pid,rows,expected_revisions,request_id,reason,'apply')

    def _point(self,name):
        # Điểm monkeypatch dành tests; production không nhận callback từ caller/payload.
        pass

    def _write(self,pid,rows,expected,request_id,reason,operation,*,unlock_paths=None,target=None):
        self._gate(); _positive(pid); _id(request_id)
        if not isinstance(reason,str) or not reason.strip() or len(reason)>4096: raise RegistryStoreError('Cần lý do hợp lệ.')
        if not isinstance(rows,list) or not rows or len(rows)>MAX_HISTORY_ROWS:
            raise RegistryStoreError('Rows phải là danh sách có giới hạn.')
        if unlock_paths is not None and (not isinstance(unlock_paths,list) or not unlock_paths or any(not isinstance(p,str) for p in unlock_paths) or len(set(unlock_paths))!=len(unlock_paths)):
            raise RegistryStoreError('Danh sách đường mở khóa không hợp lệ hoặc trùng.')
        # Kiểm ngân sách trước deepcopy; validator thuần kiểm cây/alias/độ sâu.
        preliminary=dict(schema_version=1,project_id=pid,**{k:[] for k in KINDS})
        try:
            for kind,row in rows: preliminary[self._kind(kind)].append(row)
        except (TypeError,ValueError,KeyError): raise RegistryStoreError('Rows không hợp lệ.') from None
        shape=validate_bundle(preliminary)
        if any(e['code'] in ('budget','type','number','field') for e in shape['errors']):
            raise RegistryStoreError('Rows vượt hợp đồng JSON.')
        rows=copy.deepcopy(rows)
        try: keys=[(self._kind(k),_id(r['id'])) for k,r in rows]
        except (KeyError,TypeError): raise RegistryStoreError('Rows không hợp lệ.') from None
        if not keys or len(set(keys))!=len(keys) or not isinstance(expected,dict) or set(expected)!=set(keys):
            raise RegistryStoreError('CAS cần đầy đủ head bị chạm, không trùng.')
        for rev in expected.values():
            if rev is not None: _positive(rev)
        intent_rows=copy.deepcopy(rows)
        for _,r in intent_rows:
            for key in ('author_id','created_at_utc','revision','parent_revision','reason'): r.pop(key,None)
            if operation in ('undo','unlock'): r.pop('_user_locked',None); r.pop('provenance',None)
        intent={'rows':intent_rows if operation=='apply' else [[k,i] for k,i in sorted(keys)],'expected':[[k,i,expected[k,i]] for k,i in sorted(keys)],'reason':reason,'unlock':unlock_paths,'target':target}
        digest=hashlib.sha256(_dump(intent).encode()).hexdigest()
        with self._tx(True):
            self._acl(pid,True); self._ready(); actor=self._actor()
            prior=self.conn.execute('SELECT actor,hash,result FROM stage_registry_requests WHERE project_id=? AND operation=? AND request_id=?',(pid,operation,request_id)).fetchone()
            if prior:
                if prior[0]!=actor or prior[1]!=digest: raise RegistryConflict('Request đã được dùng với actor/nội dung khác.')
                self._bundle(pid)
                return self._saved(pid,prior[2],operation)
            heads=self._heads(pid); self._bundle(pid,head_index=heads); now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'); result=[]
            for kind,row in rows:
                ident=row['id']; current=heads.get((kind,ident)); old=self._revision(pid,kind,ident,current) if current else None
                if expected[kind,ident]!=current: raise RegistryConflict('Head đã đổi; cần đọc và duyệt diff lại.')
                if row.get('project_id')!=pid: raise RegistryStoreError('Revision khác dự án.')
                locks=copy.deepcopy(old['_user_locked']) if old else copy.deepcopy(row.get('_user_locked',{}))
                if old:
                    changed=_changes(old,row)
                    protected=set(locks)
                    if operation=='unlock':
                        if not isinstance(unlock_paths,list) or not unlock_paths or any(p not in locks for p in unlock_paths): raise RegistryStoreError('Đường mở khóa không hợp lệ.')
                        for path in unlock_paths: del locks[path]
                    elif any(_overlap(p,l) for p in changed for l in protected): raise RegistryLocked('Thay đổi đụng khóa người dùng; phải mở khóa rõ trước.')
                    # Payload không được sửa metadata khóa/provenance âm thầm.
                    if operation=='apply' and row.get('_user_locked')!=old['_user_locked']: raise RegistryLocked('Khóa chỉ đổi bằng lệnh rõ.')
                    if operation=='apply' and row.get('provenance')!=old['provenance']:
                        raise RegistryStoreError('Provenance hiện tại bất biến; không bỏ nội dung caller âm thầm.')
                    row['provenance']=copy.deepcopy(old['provenance'])
                else:
                    for lock in locks.values():
                        lock['author_id']=actor; lock['created_at_utc']=now
                row.update(schema_version=1,project_id=pid,revision=(current or 0)+1,parent_revision=current,author_id=actor,created_at_utc=now,reason=reason,_user_locked=locks)
                result.append({'kind':kind,'id':ident,'revision':row['revision']})
            self._bundle(pid,proposed=rows,head_index=heads)
            candidate=self._bundle(pid,proposed=rows,seeds=[(k,r['id'],r['revision']) for k,r in rows],active=False,head_index=heads)
            self._external(candidate)
            existing,size=self.conn.execute('SELECT COUNT(*),COALESCE(SUM(length(CAST(payload AS BLOB))),0) FROM stage_registry_revisions WHERE project_id=?',(pid,)).fetchone()
            if existing+len(rows)>MAX_HISTORY_ROWS or size+sum(len(_dump(row).encode('utf-8')) for _,row in rows)>MAX_HISTORY_BYTES:
                raise RegistryStoreError('Revision mới vượt trần lưu/đọc; không ghi một phần.')
            saved={'project_id':pid,'operation':operation,'revisions':result}
            saved_json=_dump(saved); saved_bytes=len(saved_json.encode('utf-8'))
            for table,column in (('stage_registry_requests','result'),('stage_registry_audit','result'),('stage_registry_outbox','payload')):
                count,size=self._metadata_budget(pid,table,column)
                if count+1>MAX_METADATA_ROWS or size+saved_bytes>MAX_HISTORY_BYTES:
                    raise RegistryStoreError('Metadata mới vượt trần lưu/đọc; không ghi revision.')
            for kind,row in rows:
                self.conn.execute('INSERT INTO stage_registry_revisions VALUES(?,?,?,?,?)',(pid,kind,row['id'],row['revision'],_dump(row))); self._point('revision')
                self.conn.execute('INSERT INTO stage_registry_heads VALUES(?,?,?,?) ON CONFLICT(project_id,kind,id) DO UPDATE SET revision=excluded.revision',(pid,kind,row['id'],row['revision'])); self._point('head')
            self.conn.execute('INSERT INTO stage_registry_audit(project_id,operation,actor,created_at_utc,reason,result) VALUES(?,?,?,?,?,?)',(pid,operation,actor,now,reason,saved_json)); self._point('audit')
            self.conn.execute('INSERT INTO stage_registry_outbox(project_id,event,payload) VALUES(?,?,?)',(pid,'registry_invalidated',saved_json)); self._point('outbox')
            self.conn.execute('INSERT INTO stage_registry_requests VALUES(?,?,?,?,?,?)',(pid,operation,request_id,actor,digest,saved_json)); self._point('request')
            return saved

    def undo(self,pid,kind,ident,target_revision,expected_revision,*,request_id,reason):
        self._gate(); _positive(target_revision)
        history=self.history(pid,kind,ident); row=next((r for r in history if r['revision']==target_revision),None)
        if row is None: raise RegistryStoreError('Không có revision đích.')
        current=self.head(pid,kind,ident); row['_user_locked']=current['_user_locked']; row['provenance']=current['provenance']
        return self._write(pid,[(kind,row)],{(kind,ident):expected_revision},request_id,reason,'undo',target=target_revision)

    def unlock(self,pid,kind,ident,paths,expected_revision,*,request_id,reason):
        row=self.head(pid,kind,ident)
        if row is None: raise RegistryStoreError('Không có head để mở khóa.')
        return self._write(pid,[(kind,row)],{(kind,ident):expected_revision},request_id,reason,'unlock',unlock_paths=paths)

    def outbox(self,pid):
        self._gate()
        with self._tx():
            self._acl(pid); self._ready(); self._metadata_budget(pid,'stage_registry_outbox','payload')
            out=[]
            for r in self.conn.execute('SELECT id,event,payload FROM stage_registry_outbox WHERE project_id=? AND acked=0 ORDER BY id',(pid,)):
                _positive(r[0])
                if r[1]!='registry_invalidated': raise RegistryStoreError('Event Registry lưu hỏng.')
                out.append({'id':r[0],'event':r[1],'payload':self._saved(pid,r[2])})
            return out

    def ack(self,pid,event_id):
        self._gate(); _positive(event_id)
        with self._tx(True):
            self._acl(pid,True); self._ready()
            row=self.conn.execute('SELECT event,payload,acked FROM stage_registry_outbox WHERE project_id=? AND id=?',(pid,event_id)).fetchone()
            if row is None: raise RegistryStoreError('Không có event thuộc dự án.')
            if row[0]!='registry_invalidated' or type(row[2]) is not int or row[2] not in (0,1): raise RegistryStoreError('Event Registry lưu hỏng.')
            self._saved(pid,row[1])
            self.conn.execute('UPDATE stage_registry_outbox SET acked=1 WHERE project_id=? AND id=?',(pid,event_id))

    def audit(self,pid):
        self._gate()
        with self._tx():
            self._acl(pid); self._ready()
            self._metadata_budget(pid,'stage_registry_audit','result')
            out=[]
            for r in self.conn.execute('SELECT id,operation,actor,created_at_utc,reason,result FROM stage_registry_audit WHERE project_id=? ORDER BY id',(pid,)):
                _positive(r[0])
                if not isinstance(r[2],str) or not r[2].strip() or len(r[2])>320 or any(ord(c)<32 for c in r[2]) or not isinstance(r[4],str) or not r[4].strip() or len(r[4])>4096:
                    raise RegistryStoreError('Audit metadata lưu hỏng.')
                try:
                    if not isinstance(r[3],str) or not r[3].endswith('Z'): raise ValueError
                    datetime.fromisoformat(r[3][:-1]+'+00:00')
                except (ValueError,TypeError): raise RegistryStoreError('Audit time lưu hỏng.') from None
                out.append({'id':r[0],'operation':r[1],'actor':r[2],'created_at_utc':r[3],'reason':r[4],'result':self._saved(pid,r[5],r[1])})
            return out
