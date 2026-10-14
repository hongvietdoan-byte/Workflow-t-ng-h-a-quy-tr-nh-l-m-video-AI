"""Đ18.4c PARTIAL: inventory/dry-run offline; không activate/import DB hoặc suy Kho.

Nguồn chỉ định tường minh, raw bytes immutable; mappings là kế hoạch chưa ghi.
Không import store, provider, credential, resolver hoặc đọc môi trường.
"""
import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

KINDS = frozenset({'stage','grid','blocking','shot_specs','setups','scene_data','approvals','binary'})
MAX_FILES=64
MAX_FILE_BYTES=8*1024*1024
MAX_TOTAL_BYTES=32*1024*1024
MAX_DEPTH=48
MAX_NODES=200000
MAX_STRING=65536
MIGRATION_VERSION=1

class ImportInventoryError(ValueError):
    """Lỗi chỉ thông báo hợp đồng, không echo raw source/path/payload."""

@dataclass(frozen=True)
class SourceSpec:
    kind: str
    legacy_key: str
    relative_path: str
    round_id: str | None = None

@dataclass(frozen=True)
class RawSource:
    kind: str
    legacy_key: str
    relative_path: str
    round_id: str | None
    source_hash: str
    raw_bytes: bytes

@dataclass(frozen=True)
class MappingProposal:
    kind: str
    legacy_key: str
    source_hash: str
    migration_version: int
    candidate_id: str
    proposed_revision: int = 1
    status: str = 'unresolved'

@dataclass(frozen=True)
class InventoryIssue:
    severity: str
    code: str
    source_key: str
    message: str

@dataclass(frozen=True)
class DryRunReport:
    project_id: int
    migration_version: int
    inventory_hash: str
    sources: tuple[RawSource,...]
    mappings: tuple[MappingProposal,...]
    issues: tuple[InventoryIssue,...]
    status: str = 'PARTIAL'
    ready_for_apply: bool = False


def _key(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',value):
        raise ImportInventoryError('Legacy key/round ID phải opaque ASCII 1–128 ký tự.')
    return value


def _limit(value,ceiling):
    if type(value) is not int or not 0<value<=ceiling:
        raise ImportInventoryError('Giới hạn phải nguyên dương và không vượt trần inventory.')
    return value


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def _relative(value):
    if not isinstance(value,str) or not value or len(value)>1024 or '\\' in value or '\x00' in value or ':' in value:
        raise ImportInventoryError('Đường nguồn tương đối không hợp lệ.')
    path=PurePosixPath(value)
    if path.is_absolute() or PureWindowsPath(value).drive or any(p in ('','.', '..') for p in value.split('/')):
        raise ImportInventoryError('Đường nguồn escaping hoặc không canonical.')
    for part in path.parts:
        base=part.split('.')[0].upper()
        if part.endswith(('.', ' ')) or any(ord(c)<32 or c in '<>"|?*' for c in part) or base in {'CON','NUL','PRN','AUX'} or re.fullmatch(r'(?:COM|LPT)[0-9¹²³]',base):
            raise ImportInventoryError('Đường nguồn có alias/device Windows hoặc ký tự không canonical.')
    return path


def _path_key(value):
    return str(_relative(value)).casefold()


def _candidate(project_id,version,source):
    return 'a_'+hashlib.sha256(_canonical([project_id,version,source.kind,source.legacy_key,source.source_hash])).hexdigest()[:40]


def _inventory_identity(project_id,version,sources):
    identity=[project_id,version,[(x.kind,x.legacy_key,x.relative_path,x.round_id,x.source_hash) for x in sources]]
    return hashlib.sha256(_canonical(identity)).hexdigest()


def _stable_id(value):
    if type(value) is int: return 0<value<2**63
    try: _key(value); return True
    except ImportInventoryError: return False


def _known_scale(value):
    if isinstance(value,dict):
        if value.get('confidence')!='measured' or not isinstance(value.get('source'),str) or not value['source'].strip(): return False
        value=value.get('value')
    try: return type(value) in (int,float) and math.isfinite(value) and value>0
    except OverflowError: return False


def _link(path):
    return path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction())


def _ancestors_clean(path):
    for candidate in (path,*path.parents):
        if _link(candidate): raise ImportInventoryError('Không nhận symlink/junction nguồn hoặc ancestor root.')


def _verify_open_scope(root,path,expected):
    _ancestors_clean(path)
    _ancestors_clean(root)
    resolved=path.resolve(strict=True)
    if resolved!=expected or not resolved.is_relative_to(root):
        raise ImportInventoryError('Đường nguồn đổi/escape khi mở hoặc đọc.')


def _read(root,relative,max_bytes):
    rel=_relative(relative); path=root
    try:
        for part in rel.parts:
            path=path/part
            if _link(path): raise ImportInventoryError('Không nhận symlink/junction trong nguồn.')
        resolved=path.resolve(strict=True)
        if not resolved.is_relative_to(root): raise ImportInventoryError('Nguồn nằm ngoài root được chỉ định.')
        before=path.stat()
        if not stat.S_ISREG(before.st_mode) or before.st_size>max_bytes:
            raise ImportInventoryError('Nguồn không phải tệp thường hoặc vượt trần bytes.')
        with path.open('rb') as stream:
            opened=os.fstat(stream.fileno())
            _verify_open_scope(root,path,resolved)
            if (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):
                raise ImportInventoryError('Nguồn đổi khi mở; cần inventory lại.')
            raw=stream.read(max_bytes+1)
        _verify_open_scope(root,path,resolved)
        after=path.stat()
        if _link(path) or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) or len(raw)!=before.st_size:
            raise ImportInventoryError('Nguồn đổi khi đọc; cần inventory lại.')
        if len(raw)>max_bytes: raise ImportInventoryError('Nguồn vượt trần bytes.')
        return raw
    except OSError: raise ImportInventoryError('Không đọc được nguồn explicit.') from None


def _decode(raw,max_depth,max_nodes):
    def object_pairs(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise ImportInventoryError('JSON có key trùng; raw không được diễn giải mơ hồ.')
            out[k]=v
        return out
    try:
        obj=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=object_pairs,
                       parse_constant=lambda value: (_ for _ in ()).throw(ImportInventoryError('JSON có số không hữu hạn.')))
    except (UnicodeError,ValueError,RecursionError): raise ImportInventoryError('Nguồn JSON không hợp lệ hoặc quá sâu.') from None
    stack=[(obj,0)]; count=0
    while stack:
        node,depth=stack.pop();count+=1
        if count>max_nodes or depth>max_depth: raise ImportInventoryError('JSON vượt trần nodes/depth.')
        if isinstance(node,dict):
            for key in node:
                if len(key)>MAX_STRING: raise ImportInventoryError('JSON key vượt trần string.')
            stack.extend((value,depth+1) for value in node.values())
        elif isinstance(node,list): stack.extend((value,depth+1) for value in node)
        elif isinstance(node,str) and len(node)>MAX_STRING: raise ImportInventoryError('JSON string vượt trần.')
        elif isinstance(node,float) and not math.isfinite(node): raise ImportInventoryError('JSON có số không hữu hạn.')
    return obj,count


def _issues(source,obj):
    found=[]
    def add(code,message,severity='unresolved'):
        found.append(InventoryIssue(severity,code,source.legacy_key,message))
    add('conversion_pending','Chỉ kiểm kê/raw/mapping; chuyển semantic và apply cần bước reconcile được duyệt.')
    if source.kind in ('stage','grid'):
        units=obj.get('units') if isinstance(obj,dict) else None
        if isinstance(obj,dict) and isinstance(obj.get('world_frame'),dict): units=obj['world_frame'].get('units')
        if units!='m': add('missing_units','Thiếu hoặc chưa xác minh đơn vị mét; không tự nhân hệ số.')
        if not isinstance(obj,dict) or not _stable_id(obj.get('id')): add('missing_stable_id','Thiếu ID stage stable; cần người ghép.')
        frame=obj.get('world_frame') if isinstance(obj,dict) else None
        scale=obj.get('scale') if isinstance(obj,dict) else None
        if isinstance(frame,dict): scale=frame.get('scale',scale)
        if not _known_scale(scale):
            add('missing_scale','Scale chưa xác minh; không mặc định 1.')
    if source.kind=='blocking' and (isinstance(obj,str) or isinstance(obj,dict) and isinstance(obj.get('blocking'),str)):
        add('textual_blocking','Blocking văn bản chỉ giữ raw; cần người ghép state/IDs.')
    stack=[obj]
    while stack:
        node=stack.pop()
        if isinstance(node,dict):
            if node.get('kind') in ('actor','nguoi') and not (type(node.get('actor_id')) is int and 0<node['actor_id']<2**63):
                add('missing_actor_id','Thiếu actor ID xác minh; không suy từ nhãn/idx/tên.')
            if 'look_id' in node or 'look_revision' in node:
                add('look_domain_pending','Domain bộ dạng/ảnh/pin Kho chờ người dùng chốt; không mapping vào asset/ảnh.')
            if any(k in node for k in ('subject','end_actor','state','parent_state','POV','pov_subject_id','move','beats','at','in','hidden','_user_locked')):
                add('state_semantics_pending','State/beat/POV/move/lock giữ raw; adapter cần xác minh nghĩa và pin.')
            stack.extend(node.values())
        elif isinstance(node,list):stack.extend(node)
    # Gộp diagnostic theo mã/source; raw giữ toàn bộ các lần xuất hiện.
    return list({(i.severity,i.code,i.source_key):i for i in found}.values())


def dry_run(root,project_id,sources,*,migration_version=MIGRATION_VERSION,
            max_file_bytes=MAX_FILE_BYTES,max_total_bytes=MAX_TOTAL_BYTES,
            max_depth=MAX_DEPTH,max_nodes=MAX_NODES):
    """Không scan root/latest, không write DB/tệp. Sources là SourceSpec explicit.

    Hash bao gồm project, version, kind/key/relative path/round và SHA256 raw bytes;
    không timestamp/mtime/latest. Candidate ID chỉ là đề xuất source mapping,
    chưa A aggregate và không phải Kho ID. Tất cả report luôn PARTIAL.
    """
    if type(project_id) is not int or not 0<project_id<2**63: raise ImportInventoryError('Project ID phải số nguyên dương SQLite.')
    _limit(migration_version,255)
    _limit(max_file_bytes,MAX_FILE_BYTES);_limit(max_total_bytes,MAX_TOTAL_BYTES)
    _limit(max_depth,MAX_DEPTH);_limit(max_nodes,MAX_NODES)
    if not isinstance(sources,(list,tuple)) or not 0<len(sources)<=MAX_FILES:
        raise ImportInventoryError('Cần danh sách nguồn explicit, tối đa 64 tệp.')
    ordered=[];seen=set();paths=set()
    for spec in sources:
        if not isinstance(spec,SourceSpec) or not isinstance(spec.kind,str) or spec.kind not in KINDS: raise ImportInventoryError('SourceSpec/kind không hợp lệ.')
        _key(spec.legacy_key)
        if spec.round_id is not None:_key(spec.round_id)
        path_key=_path_key(spec.relative_path)
        key=(spec.kind,spec.legacy_key)
        if key in seen or path_key in paths: raise ImportInventoryError('Nguồn/key bị trùng; không chọn ngầm một bản.')
        seen.add(key);paths.add(path_key);ordered.append(spec)
    ordered.sort(key=lambda s:(s.kind,s.legacy_key,s.relative_path))
    try:
        root_text=os.fspath(root)
        if not isinstance(root_text,str) or root_text.startswith(('\\', '//')) or '://' in root_text:
            raise ImportInventoryError('Root phải là nguồn local, không UNC/device/network.')
        root=Path(root_text)
        if not root.is_absolute() or _link(root) or not root.is_dir(): raise ImportInventoryError('Root phải thư mục tuyệt đối không symlink/junction.')
        _ancestors_clean(root)
        root=root.resolve(strict=True)
    except (OSError,TypeError,ValueError): raise ImportInventoryError('Root inventory không hợp lệ.') from None
    raw_sources=[];mapping=[];issues=[];total=0;node_count=0;approved=set();rounds=set()
    for spec in ordered:
        raw=_read(root,spec.relative_path,min(max_file_bytes,max_total_bytes-total));total+=len(raw)
        if total>max_total_bytes: raise ImportInventoryError('Inventory vượt trần tổng bytes.')
        digest=hashlib.sha256(raw).hexdigest()
        source=RawSource(spec.kind,spec.legacy_key,spec.relative_path,spec.round_id,digest,raw);raw_sources.append(source)
        candidate=_candidate(project_id,migration_version,source)
        mapping.append(MappingProposal(spec.kind,spec.legacy_key,digest,migration_version,candidate))
        if spec.round_id is not None:rounds.add(spec.round_id)
        if spec.kind=='binary':
            issues.append(InventoryIssue('unresolved','binary_preserved',spec.legacy_key,'Binary giữ bytes/hash; chưa diễn giải hay dùng làm pin ảnh.'))
            continue
        obj,count=_decode(raw,max_depth,max_nodes);node_count+=count
        if node_count>max_nodes: raise ImportInventoryError('Inventory vượt trần tổng nodes.')
        issues.extend(_issues(source,obj))
        if spec.kind=='approvals':
            pin=obj.get('approved_round') if isinstance(obj,dict) else None
            if isinstance(pin,str) and pin and len(pin)<=128: approved.add(pin)
            else:issues.append(InventoryIssue('unresolved','approval_metadata_pending',spec.legacy_key,'Approval chỉ là lịch sử raw; thiếu pin round được duyệt rõ.'))
    if len(approved)>1 or len(rounds)>1 and (len(approved)!=1 or not approved<=rounds) or approved and not approved<=rounds:
        issues.append(InventoryIssue('conflict','approved_round_ambiguous','inventory','Nhiều/khác round hoặc không có round duyệt xác minh; không chọn latest.'))
    elif not approved:
        issues.append(InventoryIssue('unresolved','approved_round_unknown','inventory','Chưa có pin round duyệt explicit; không tự duyệt A.'))
    digest=_inventory_identity(project_id,migration_version,raw_sources)
    issues.sort(key=lambda i:(i.source_key,i.severity,i.code))
    return DryRunReport(project_id,migration_version,digest,tuple(raw_sources),tuple(mapping),tuple(issues))


def restore_payloads(report):
    """Trả cặp relative_path/bytes để đối chiếu restore trên bản sao; KHÔNG ghi tệp.

    Không nhận altered raw/hash hoặc duplicate/escaping path. Caller cần quyền
    và kế hoạch restore riêng trước mọi ghi production.
    """
    if not isinstance(report,DryRunReport) or type(report.project_id) is not int or not 0<report.project_id<2**63:
        raise ImportInventoryError('Cần DryRunReport/project hợp lệ.')
    _limit(report.migration_version,255)
    if report.status!='PARTIAL' or report.ready_for_apply is not False:
        raise ImportInventoryError('Inventory chỉ PARTIAL; không nhận report sẵn sàng apply.')
    if type(report.sources) is not tuple or not 0<len(report.sources)<=MAX_FILES or type(report.mappings) is not tuple or len(report.mappings)!=len(report.sources) or type(report.issues) is not tuple or len(report.issues)>MAX_FILES*16:
        raise ImportInventoryError('Report không immutable hoặc vượt trần collection.')
    seen=set();keys=set();total=0;out=[]
    # Preflight tất cả bytes/types/metadata trước hash/decode, không I/O.
    for source in report.sources:
        if not isinstance(source,RawSource) or not isinstance(source.kind,str) or source.kind not in KINDS:
            raise ImportInventoryError('RawSource không hợp lệ.')
        _key(source.legacy_key)
        if source.round_id is not None: _key(source.round_id)
        path_key=_path_key(source.relative_path); key=(source.kind,source.legacy_key)
        if path_key in seen or key in keys or type(source.raw_bytes) is not bytes or len(source.raw_bytes)>MAX_FILE_BYTES:
            raise ImportInventoryError('Raw snapshot/đường/budget không nhất quán.')
        if not isinstance(source.source_hash,str) or not re.fullmatch(r'[0-9a-f]{64}',source.source_hash):
            raise ImportInventoryError('Hash raw không hợp lệ.')
        total+=len(source.raw_bytes)
        if total>MAX_TOTAL_BYTES: raise ImportInventoryError('Raw restore vượt trần bytes.')
        seen.add(path_key);keys.add(key)
    if tuple(sorted(report.sources,key=lambda x:(x.kind,x.legacy_key,x.relative_path)))!=report.sources:
        raise ImportInventoryError('Nguồn report không canonical sorted.')
    nodes=0
    for source,proposal in zip(report.sources,report.mappings):
        if hashlib.sha256(source.raw_bytes).hexdigest()!=source.source_hash:
            raise ImportInventoryError('Raw snapshot/hash không nhất quán.')
        if source.kind!='binary':
            _,count=_decode(source.raw_bytes,MAX_DEPTH,MAX_NODES);nodes+=count
            if nodes>MAX_NODES: raise ImportInventoryError('Raw restore vượt trần nodes.')
        expected=MappingProposal(source.kind,source.legacy_key,source.source_hash,report.migration_version,_candidate(report.project_id,report.migration_version,source))
        if not isinstance(proposal,MappingProposal) or type(proposal.migration_version) is not int or type(proposal.proposed_revision) is not int or proposal!=expected:
            raise ImportInventoryError('Mapping report không khớp raw scope.')
        out.append((source.relative_path,source.raw_bytes))
    if report.inventory_hash!=_inventory_identity(report.project_id,report.migration_version,report.sources):
        raise ImportInventoryError('Inventory hash không khớp metadata/project/version/raw.')
    for issue in report.issues:
        if not isinstance(issue,InventoryIssue) or issue.severity not in ('unresolved','conflict') or not isinstance(issue.message,str) or len(issue.message)>4096:
            raise ImportInventoryError('Diagnostic report không hợp lệ.')
        _key(issue.code);_key(issue.source_key)
    return tuple(out)
