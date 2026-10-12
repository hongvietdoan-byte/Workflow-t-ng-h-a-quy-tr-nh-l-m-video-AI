"""Đ12v5: lịch đồng thanh và đo onset cục bộ, không gọi model/ASR.

Onset năng lượng chỉ là proxy; không xác minh từ nên luôn báo VÀNG,
kể cả các cụm khớp 60 ms. Tệp từng người được giữ nguyên để khớp môi.
"""
import hashlib
import json
import sqlite3
from pathlib import Path
import ntpath
import math
import os
import subprocess
from array import array
from . import features

LIMIT = .06

def enabled():
    return features.on('unison_dialogue')

def speakers(line):
    names = line.get('unison')
    if names is None:
        return None
    if (not isinstance(names, list) or len(names) < 2 or
            any(not isinstance(n, str) or not n.strip() for n in names) or
            len({n.strip().casefold() for n in names}) != len(names) or
            str(line.get('speaker') or '').strip().casefold() not in {n.strip().casefold() for n in names}):
        raise ValueError('unison: cần ít nhất 2 người khác nhau, gồm speaker gốc')
    primary = str(line["speaker"]).strip()
    return [primary] + sorted([n.strip() for n in names if n.strip().casefold() != primary.casefold()], key=str.casefold)

def schedule(entries, lead=0., gap=.12):
    """Lịch từng giọng; nhóm có một điểm đầu, kết thúc bằng giọng dài nhất."""
    out, cursor, n = [], lead, 0
    while n < len(entries):
        e=entries[n]
        batch=[e]
        group=e.get('unison_group') if enabled() else None
        j=n+1
        if group is not None:
            while j<len(entries) and entries[j].get('unison_group')==group:
                batch.append(entries[j]); j+=1
        out.extend([round(cursor,3)]*len(batch))
        cursor+=max((x.get('duration_ms') or 0)/1000. for x in batch)+gap
        n=j
    return out

def compare_onsets(onsets, words):
    base=dict(state='yellow', limit_s=LIMIT, onset_within_limit=False)
    if len(onsets)<2 or any(len(x)!=words or not x for x in onsets):
        return dict(base,reason='Không đo được từng từ: số cụm năng lượng không khớp số từ hoặc thiếu một giọng')
    delta=max(max(x[i] for x in onsets)-min(x[i] for x in onsets) for i in range(words))
    return dict(base,max_delta_s=round(delta,6),onset_within_limit=delta<=LIMIT+1e-9,
                reason=('Cụm onset lệch quá 0,06 s; cần sửa nhịp từng giọng' if delta>LIMIT+1e-9 else
                        'Onset năng lượng trong 0,06 s; chưa xác minh vị trí từng từ (không ASR)'))

def energy_onsets(path, ffmpeg):
    """PCM 16 kHz, cửa sổ 10 ms; không nhận dạng chữ, không truy cập mạng."""
    if str(path).startswith(('\\\\','//')) or '://' in str(path):
        raise ValueError('Đồng thanh: âm thanh phải là tệp local')
    proc=subprocess.run([ffmpeg,'-v','error','-i',os.path.abspath(path),'-f','s16le','-ac','1','-ar','16000','pipe:1'],capture_output=True)
    if proc.returncode:
        raise ValueError('Không đọc được âm thanh để đo onset')
    pcm=array('h'); pcm.frombytes(proc.stdout)
    energies=[math.sqrt(sum(v*v for v in pcm[i:i+160])/len(pcm[i:i+160])) for i in range(0,len(pcm),160)]
    if not energies or max(energies)<50:
        return []
    threshold=max(50,max(energies)*.08)
    out,active,quiet=[],False,0
    for i,value in enumerate(energies):
        if value>=threshold:
            if not active: out.append(i*.01)
            active=True; quiet=0
        else:
            quiet+=1
            if quiet>=3: active=False
    return out

def measure(entries,directory,ffmpeg):
    try:
        if len(entries)<2 or any(not e.get('file') or not os.path.isfile(local_path(directory,e['file'])) for e in entries):
            return dict(state='yellow',reason='Thiếu một giọng đồng thanh hoặc tệp âm thanh')
        onsets=[energy_onsets(local_path(directory,e['file']),ffmpeg) for e in entries]
        # Các consumer trim silence đầu; đo lệch nội bộ trên cùng đồng hồ đó.
        return compare_onsets([[t-row[0] for t in row] if row else [] for row in onsets],
                              len(str(entries[0].get('text') or '').split()))
    except (ValueError,OSError) as exc:
        return dict(state='yellow',reason=str(exc))


ALGORITHM = 'trim-onset-v1'


def local_path(directory, name):
    """Chỉ tệp nằm trong assets; từ chối UNC/URL trước mọi thao tác đọc."""
    value = str(name or '')
    if not value or value.startswith(('\\\\', '//')) or '://' in value or ntpath.isabs(value):
        raise ValueError('Đồng thanh: đường âm thanh ngoài thư mục tài nguyên')
    if str(directory).startswith(('\\\\','//')) or '://' in str(directory):
        raise ValueError('Đồng thanh: thư mục tài nguyên phải local')
    root = Path(directory).resolve()
    target = (root / value).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Đồng thanh: đường âm thanh ngoài thư mục tài nguyên')
    return str(target)


def bind(conn, data_dir, pid):
    """Metadata rõ cho runner không nhận conn; không lưu connection/global."""
    from . import audio_lib, voice
    directory = audio_lib.assets_dir(data_dir, pid)
    plan = voice.planned_lines(conn, pid)
    if not enabled() and not any(ln.get('unison_group') is not None for ln in plan) and not any(e.get('unison_group') is not None for e in audio_lib.load(directory)):
        return
    source = next((r[2] for r in conn.execute('PRAGMA database_list') if r[1]=='main'), '')
    if source and (source.startswith(('\\\\','//')) or '://' in source):
        raise ValueError('Đồng thanh: nguồn hồ sơ phải là CSDL local')
    payload = dict(database=str(Path(source).resolve()) if source else None,
                   plan=plan, algorithm=ALGORITHM)
    destination = Path(directory)/'unison_context.json'
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if not destination.exists() or destination.read_text(encoding='utf-8') != text:
        destination.write_text(text, encoding='utf-8')


def current_plan(directory, pid, conn=None):
    from . import voice
    if conn is not None:
        return voice.planned_lines(conn,pid)
    context = Path(directory)/'unison_context.json'
    if not context.exists():
        raise ValueError('Đồng thanh: thiếu nguồn hồ sơ hiện tại; mở lại màn Giọng trước khi tạo video')
    try:
        source = json.loads(context.read_text(encoding='utf-8')).get('database')
        if not source or source.startswith(('\\\\','//')) or '://' in source or not Path(source).is_absolute():
            raise ValueError('Đồng thanh: nguồn hồ sơ không phải CSDL local; cần context hiện tại')
        with sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            return voice.planned_lines(db,pid)
    except (OSError,sqlite3.Error,json.JSONDecodeError) as exc:
        raise ValueError('Đồng thanh: không đọc được nguồn hồ sơ hiện tại') from exc


def original(entry):
    out=dict(entry)
    if out.get('solo_file'):
        out['file']=out['solo_file']
        out['duration_ms']=out.get('solo_duration_ms',out.get('duration_ms'))
    return out


def selected(items, plan, directory, strict=False, align=False):
    """Một cách chọn giọng cho cả take/generate/final, OFF ánh xạ dialogue_line."""
    out=[]
    for ln in plan:
        matches=[original(e) for e in items if e.get('kind')=='tts' and e.get('scene_id')==ln['scene_id'] and
                 e.get('speaker')==ln['speaker'] and e.get('text')==ln['text'] and
                 (e.get('line') if enabled() else e.get('dialogue_line',e.get('line')))==ln['line']]
        e=matches[-1] if matches else None
        grouped=ln.get('unison_group') is not None
        valid=bool(e and e.get('state')=='succeeded' and e.get('file'))
        if enabled():
            valid=valid and bool(ln.get('voice')) and e.get('voice_id')==(ln.get('voice') or {}).get('voice_id')
            valid=valid and (e.get('unison_group'),e.get('unison_speakers'))==(ln.get('unison_group'),ln.get('unison_speakers'))
        if valid:
            valid=os.path.isfile(local_path(directory,e['file']))
        if not valid:
            if strict and (grouped or (enabled() and any(x.get('unison_group') is not None and x.get('scene_id')==ln['scene_id'] for x in items))):
                raise ValueError('Đồng thanh: thiếu hoặc lỗi thời một giọng/hồ sơ/tệp; chưa gửi khớp môi')
            continue
        out.append(e)
    if enabled() and not strict:
        incomplete={ln.get('unison_group') for ln in plan if ln.get('unison_group') is not None and
                    not any(e.get('line')==ln['line'] and e.get('scene_id')==ln['scene_id'] for e in out)}
        out=[e for e in out if e.get('unison_group') not in incomplete]
    if align and enabled():
        out=aligned(out,directory)
    return out


def aligned(entries,directory):
    from . import ffmpeg_studio
    out=[]
    for e in entries:
        if e.get('unison_group') is None:
            out.append(e);continue
        source=local_path(directory,e['file'])
        ff=ffmpeg_studio.find_ffmpeg()
        onsets=energy_onsets(source,ff)
        if not onsets:
            raise ValueError('Đồng thanh: không đo được điểm bắt đầu giọng')
        trim=onsets[0]
        key=hashlib.sha256(Path(source).read_bytes()+json.dumps([e.get('voice_id'),ALGORITHM,trim]).encode()).hexdigest()[:24]
        name='unison_'+key+'.wav';target=local_path(directory,name)
        if not os.path.isfile(target):
            proc=subprocess.run([ff,'-v','error','-i',source,'-af',f'atrim=start={trim:.3f},asetpts=PTS-STARTPTS','-ac','1','-ar','44100',target],capture_output=True)
            if proc.returncode:
                raise ValueError('Đồng thanh: không canh được điểm bắt đầu giọng')
        out.append(dict(e,file=name,solo_file=e['file'],solo_duration_ms=e.get('duration_ms'),
                        duration_ms=max(1,(e.get('duration_ms') or 0)-round(trim*1000))))
    return out


def cache_state(directory):
    """Chỉ thêm hash khi có metadata mới; legacy OFF giữ hash cũ."""
    from . import audio_lib
    context=Path(directory)/'unison_context.json'
    grouped=[original(e) for e in audio_lib.load(directory) if e.get('unison_group') is not None]
    if not context.exists() and not grouped:
        return {}
    raw=context.read_text(encoding='utf-8') if context.exists() else ''
    live=[]
    if context.exists():
        payload=json.loads(raw); source=payload.get('database')
        if source:
            # current_plan đọc readonly, cùng validation như biên gửi.
            live=current_plan(directory, int(Path(directory).parent.name))
    stamps=[]
    for e in grouped:
        path=local_path(directory,e.get('file'))
        stamps.append([e.get('speaker'),hashlib.sha256(Path(path).read_bytes()).hexdigest() if os.path.isfile(path) else None])
    return dict(unison=dict(enabled=enabled(),algorithm=ALGORITHM,context=raw,live=live,sources=stamps))
