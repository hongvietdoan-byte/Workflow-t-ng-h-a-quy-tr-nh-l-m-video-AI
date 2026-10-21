"""Một cửa đọc hồ sơ Kho; v1/cờ tắt giữ nguyên dữ liệu và đường chọn cũ.

Không migration, không I/O nhà cung cấp. CAS dùng mẫu data IS của package_overrides.
"""
import copy
import json
import re
from datetime import datetime, timezone
from . import assets, features, character_forms

class ProfileError(ValueError):
    pass

def enabled():
    return features.on('kho_forms_v2')

def validate(profile, conn=None, asset_id=None):
    """Chặn hồ sơ sai trước khi ghi; không tự sửa dữ liệu nguồn."""
    if not isinstance(profile, dict):
        raise ProfileError('Hồ sơ phải là object')
    if profile.get('schema_version', 1) != 2:
        raise ProfileError('schema_version phải bằng 2')
    if type(profile.get('revision', 0)) is not int or profile.get('revision', 0) < 0:
        raise ProfileError('revision không hợp lệ')
    seen = set()
    forms = profile.get('forms', [])
    if not isinstance(forms, list):
        raise ProfileError('forms phải là danh sách')
    fields = [profile[k] for k in ('face', 'hair') if k in profile]
    outfit = profile.get('outfit', {})
    if not isinstance(outfit, dict) or not isinstance(outfit.get('sets', []), list):
        raise ProfileError('outfit.sets không hợp lệ')
    sets = outfit.get('sets', [])
    if any(not isinstance(s,dict) for s in sets):
        raise ProfileError('outfit.sets phải chứa object')
    if any(not isinstance(s.get('id'),str) for s in sets):
        raise ProfileError('outfit id phải là chữ')
    if len({s.get('id') for s in sets}) != len(sets) or any(not s.get('id') for s in sets):
        raise ProfileError('outfit id thiếu/trùng')
    if outfit.get('default') and outfit['default'] not in {s['id'] for s in sets}:
        raise ProfileError('outfit.default không tồn tại')
    for f in forms:
        if not isinstance(f, dict) or not re.fullmatch(r'[a-z0-9]+(_[a-z0-9]+)*', str(f.get('ma', ''))) or f['ma'] in seen:
            raise ProfileError('Mã dạng thiếu/sai/trùng')
        seen.add(f['ma'])
        if not isinstance(f.get('applies_to', []), list) or not isinstance(f.get('keeps', []), list):
            raise ProfileError('applies_to/keeps phải là danh sách')
    for f in fields + forms + sets:
        if not isinstance(f, dict):
            raise ProfileError('Trường cấu trúc phải là object')
        p = f.get('_p', {})
        if not isinstance(p,dict):
            raise ProfileError('provenance phải là object')
        for key in ('text_en','color','length','style','eyes','ten_en','ten_vi','words_en'):
            if key in f and not isinstance(f[key],str):
                raise ProfileError(f'{key} phải là chữ')
        if p.get('source') not in ('human', 'ai', 'image', 'import') or p.get('state') not in ('AUTO','USER_LOCKED','REVIEW_REQUIRED'):
            raise ProfileError('provenance thiếu hoặc sai source/state')
        if p['source'] == 'ai' and (not p.get('model') or not (p.get('from_image_ids') or p.get('from_text'))):
            raise ProfileError('AI phải khai model và nguồn')
        for key in ('image_ids', 'ref_image_ids'):
            ids = f.get(key, [])
            if not isinstance(ids, list) or any(type(i) is not int or i <= 0 for i in ids):
                raise ProfileError('image_ids không hợp lệ')
            if conn is not None:
                for i in ids:
                    row = conn.execute("SELECT asset_id,status FROM asset_images WHERE id=?", (i,)).fetchone()
                    if row is None or row['status'] == 'removed' or (asset_id is not None and row['asset_id'] != asset_id):
                        raise ProfileError('Ảnh không thuộc mục Kho hoặc đã bị xóa')
    return True

def read(conn, asset_id):
    raw = assets.get_profile(conn, asset_id)
    if not enabled():
        return raw
    if not isinstance(raw,dict):
        return {'schema_version':2,'approved':False,'forms':[],'outfit_sets':[],'face':None,'hair':None,'gaps':['Hồ sơ không phải object'],'kho_id':asset_id,'revision':0}
    p = copy.deepcopy(raw)
    if raw.get('schema_version',1) != 1:
        try:
            validate(raw,conn,asset_id)
        except (ProfileError, TypeError, KeyError) as exc:
            return {'schema_version':2,'approved':False,'forms':[],'outfit_sets':[],'face':None,'hair':None,'gaps':[str(exc)],'kho_id':asset_id,'revision':raw.get('revision',0)}
    p.update(kho_id=asset_id, revision=raw.get('revision', 0), schema_version=raw.get('schema_version', 1))
    p['gaps'] = []
    p['provenance'] = {}
    for key in ('face', 'hair'):
        p.setdefault(key, None)
        if p[key] is None:
            p['gaps'].append(f'{key}: hồ sơ chưa tách')
        else:
            field = p[key]
            meta = field.get('_p', {})
            approved_refs = [i for i in field.get('ref_image_ids', []) if conn.execute("SELECT 1 FROM asset_images WHERE id=? AND asset_id=? AND status='approved'", (i,asset_id)).fetchone()]
            if meta.get('source') == 'ai' and approved_refs:
                field['_p'] = dict(meta, state='REVIEW_REQUIRED')
                field['_image_priority'] = True
            p['provenance'][key] = copy.deepcopy(field.get('_p', {}))
    p['outfit_sets'] = copy.deepcopy(p.get('outfit', {}).get('sets', []))
    p.setdefault('forms', [])
    if p['schema_version'] == 1 and raw.get('khai_bao_chu'):
        p['outfit_sets'] = [{'id':'legacy', 'items':copy.deepcopy(raw['khai_bao_chu']), 'nguon':'khai_bao_chu'}]
    return _record(p)

def lock_text_en(profile, form=None, outfit=None):
    if profile.get('schema_version', 1) != 2:
        bits = [f"keep {profile['must_keep']}" if profile.get('must_keep') else '', f"never {profile['forbidden']}" if profile.get('forbidden') else '', f"about {profile['height_m']:g} m tall" if profile.get('height_m') else '']
        text = '; '.join(b for b in bits if b)
        return character_forms.without_clothes(text) if form else text
    bits = []
    for key in ('face', 'hair'):
        field = profile.get(key)
        if field and not field.get('_image_priority') and field.get('_p',{}).get('state') == 'USER_LOCKED' and field.get('text_en'):
            bits.append(field['text_en'])
    if profile.get('build'):
        bits.append(str(profile['build']))
    if profile.get('height_m'):
        bits.append(f"about {profile['height_m']:g} m tall")
    if form and form.get('words'):
        bits.append(form['words'])
    if outfit and outfit.get('text_en'):
        bits.append(outfit['text_en'])
    return '; '.join(bits)

def for_character(conn, project_id, name):
    if not enabled():
        return assets.standard_for(conn, project_id, name)
    asset = assets.link_characters(conn, project_id, [name]).get(name)
    if asset is None:
        return None
    p = read(conn, asset['id'])
    if not p.get('approved'):
        return None
    p['asset'] = asset['name']
    if p['schema_version'] == 2:
        # Mọi reader chữ cũ nhận cùng trường cấu trúc, không gửi metadata AI chưa duyệt.
        p['identity'] = lock_text_en(p)
        p['must_keep'] = lock_text_en(p)
    return p

def forms_for_shot(conn, project_id, scene, chosen=None):
    if not enabled():
        return character_forms.for_shot(conn, project_id, scene, chosen)
    chosen = assets.project_assets(conn, project_id) if chosen is None else chosen
    legacy = [a for a in chosen if read(conn,a['id']).get('schema_version',1) != 2]
    out = character_forms.for_shot(conn, project_id, scene, legacy)
    scene = scene or {}
    cast = {str(n).strip().upper() for n in scene.get('characters', [])}
    text = ' '.join(str(scene.get(k) or '') for k in ('text','image_prompt','location')).lower()
    requested = {str(t.get('vat') or t.get('ten') or t.get('name') or '').strip().upper():t.get('dang') for t in (scene.get('byd') or {}).get('thanh_phan', []) if isinstance(t,dict)}
    for a in chosen:
        p = read(conn,a['id'])
        if p.get('schema_version') != 2:
            continue
        for f in p['forms']:
            targets = {str(n).strip().upper() for n in f.get('applies_to', [])} & cast
            if not targets:
                continue
            explicit = any(requested.get(n) == f['ma'] for n in targets)
            matched = any(str(f.get(k) or '').lower() in text for k in ('ma','ten_en','ten_vi') if f.get(k))
            if not explicit and not matched:
                continue
            image = next((i for iid in f.get('image_ids',[]) for i in a.get('images',[]) if i['id']==iid and i.get('status')=='approved'),None)
            value = dict(f, form=f.get('ten_en') or f['ma'], label=f.get('ten_vi') or f.get('ten_en') or f['ma'], words=f.get('words_en') or '', asset_id=a['id'], image=image, kho_id=a['id'], revision=p['revision'])
            for n in targets:
                out.setdefault(n,value)
    return out

def forms_for_rows(conn, project_id, rows):
    if not enabled():
        return character_forms.for_rows(conn,project_id,rows)
    out, present = {}, {}
    for i,r in enumerate(rows or [],1):
        d = r['data'] or {}
        for n in d.get('characters',[]):
            present.setdefault(str(n).strip().upper(),[]).append(i)
        for n,f in forms_for_shot(conn,project_id,d).items():
            out.setdefault(n,dict(f,shots=[]))['shots'].append(i)
    for n,f in out.items():
        f['all'] = sorted(set(f['shots'])) == sorted(set(present.get(n,[])))
    return out

def outfit_for(conn, project_id, name, scene=None):
    pics = assets.outfit_images(conn,project_id,name)
    if pics:
        return {'id':'project', 'images':pics, 'image_ids':[i['id'] for i in pics], 'label':assets.outfit_label(conn,project_id,name)}
    if not enabled():
        return None
    asset = assets.link_characters(conn,project_id,[name]).get(name)
    if asset is None:
        return None
    p = read(conn,asset['id'])
    if p['schema_version'] != 2:
        return None
    form = forms_for_shot(conn,project_id,scene).get(name.strip().upper()) if scene else None
    if form and form.get('outfit_override'):
        return dict(form,id=form['ma'],images=[form['image']] if form.get('image') else [])
    default = p.get('outfit',{}).get('default')
    s = next((s for s in p['outfit_sets'] if s['id']==default),None)
    if s:
        images = [i for iid in s.get('image_ids',[]) for i in asset.get('images',[]) if i['id']==iid and i.get('status')=='approved']
        return dict(s,images=images,kho_id=asset['id'],revision=p['revision'])
    return None

def outfit_images(conn, project_id, name):
    if not enabled():
        return assets.outfit_images(conn,project_id,name)
    return (outfit_for(conn,project_id,name) or {}).get('images',[])

def outfit_label(conn, project_id, name):
    if not enabled():
        return assets.outfit_label(conn,project_id,name)
    return (outfit_for(conn,project_id,name) or {}).get('label')

def validate_dang(conn, project_id, name, dang):
    """API BYĐ cho C-M21: chỉ cảnh báo, không bịa enum khi Kho chưa khai."""
    if not enabled():
        return []
    a = assets.link_characters(conn,project_id,[name]).get(name)
    p = read(conn,a['id']) if a else {}
    forms = p.get('forms') or []
    if not forms:
        return [{'muc':'vang','ma':'dang_khong_kiem_duoc','loi':'Kho chưa khai forms'}]
    if dang not in {f['ma'] for f in forms}:
        return [{'muc':'vang','ma':'dang_khong_trong_kho','loi':'Dạng không thuộc forms Kho'}]
    return []

def save(conn, asset_id, changes, actor, expected_revision, *, approved=None):
    """Ghi có actor, giữ trường khóa, lưu đề xuất và CAS nguyên JSON (không migration)."""
    if actor.get('kind') not in ('human','ai','auto','tool') or not actor.get('who'):
        raise ProfileError('Cần actor hợp lệ')
    row = conn.execute('SELECT profile FROM assets WHERE id=?',(asset_id,)).fetchone()
    if row is None:
        raise ProfileError('Không tìm thấy mục Kho')
    raw = row['profile']
    old = json.loads(raw) if raw else {}
    if old.get('revision',0) != expected_revision:
        raise ProfileError('revision đã đổi; tải lại')
    p = copy.deepcopy(old)
    human = actor['kind']=='human'
    for key,value in changes.items():
        if key in ('revision','schema_version','proposals','approved','history','_p'):
            raise ProfileError('Trường hệ thống không được ghi trực tiếp')
        prev = old.get(key)
        state = (prev.get('_p',{}) if isinstance(prev,dict) else old.get('_p',{}).get(key,{})).get('state','USER_LOCKED' if old.get('approved') else 'AUTO')
        nested = (prev if isinstance(prev,list) else prev.get('sets',[]) if key == 'outfit' and isinstance(prev,dict) else [])
        if any(isinstance(f,dict) and f.get('_p',{}).get('state') in ('USER_LOCKED','REVIEW_REQUIRED') for f in nested):
            state = 'USER_LOCKED'
        if not human and state in ('USER_LOCKED','REVIEW_REQUIRED'):
            if prev != value:
                p.setdefault('proposals',{})[key]=copy.deepcopy(value)
            continue
        meta = {'source':'human' if human else 'ai', 'by':actor['who'], 'at':datetime.now(timezone.utc).isoformat(), 'state':'USER_LOCKED' if human else 'REVIEW_REQUIRED'}
        if not human:
            meta.update({k:actor[k] for k in ('model','from_image_ids','from_text') if k in actor})
        value = copy.deepcopy(value)
        if isinstance(value,dict):
            value['_p']=meta
        elif key == 'forms' and isinstance(value,list):
            if any(not isinstance(f,dict) for f in value):
                raise ProfileError('forms phải chứa object')
            value = [dict(f,_p=meta) for f in value]
        else:
            p.setdefault('_p',{})[key]=meta
        if key == 'outfit' and isinstance(value,dict):
            old_sets = {s['id']: s for s in (prev or {}).get('sets', [])} if isinstance(prev,dict) else {}
            # Lưu một set không đồng nghĩa duyệt lại các set khác trong bản chép outfit.
            value['sets'] = [copy.deepcopy(old_sets[s['id']]) if s.get('id') in old_sets and s == old_sets[s['id']]
                             else dict(s,_p=meta) for s in value.get('sets',[])]
        p[key]=value
    p.update(schema_version=2,revision=expected_revision+1)
    fields = [p[k] for k in ('face','hair') if p.get(k)] + p.get('forms',[]) + p.get('outfit',{}).get('sets',[])
    p['approved'] = bool(fields) and all(f.get('_p',{}).get('state')=='USER_LOCKED' for f in fields) and all(m.get('state')=='USER_LOCKED' for m in p.get('_p',{}).values() if isinstance(m,dict))
    if approved is not None:
        p['approved'] = bool(approved) and p['approved']
    validate(p,conn,asset_id)
    changed = conn.execute('UPDATE assets SET profile=? WHERE id=? AND profile IS ?',(json.dumps(p,ensure_ascii=False),asset_id,raw)).rowcount
    if changed != 1:
        raise ProfileError('revision đã đổi; tải lại')
    conn.commit()
    return p

def selected_images(asset, scene=None):
    """Ảnh v2 theo dạng vật (thứ tự khai) rồi mặt/tóc; None = dùng selector cũ."""
    if not enabled():
        return None
    raw = asset.get('profile') or {}
    p = json.loads(raw) if isinstance(raw,str) else raw
    if p.get('schema_version') != 2:
        return None
    validate(p)
    forms = p.get('forms',[])
    text = ' '.join(str((scene or {}).get(k) or '') for k in ('text','image_prompt','location')).lower()
    explicit = [f for f in forms if any(str(f[k]).lower() in text for k in ('ma','ten_en','ten_vi') if f.get(k))]
    chosen = explicit[:1] or ([forms[0]] if forms and not forms[0].get('applies_to') else [])
    ids = [i for f in chosen for i in f.get('image_ids',[])]
    ids += [i for key in ('face','hair') for i in (p.get(key) or {}).get('ref_image_ids',[])]
    images = {i['id']:i for i in asset.get('images',[]) if i.get('status')=='approved'}
    out = []
    for i in ids:
        if i in images and images[i] not in out:
            out.append(images[i])
    return out or None

def save_outfit_to_kho(conn, project_id, name, actor):
    if actor.get('kind') != 'human':
        raise ProfileError('Chỉ người dùng được lưu trang phục dự án vào Kho')
    a = assets.link_characters(conn,project_id,[name]).get(name)
    if a is None:
        raise ProfileError('Nhân vật chưa gắn Kho')
    p = assets.get_profile(conn,a['id'])
    pics = assets.outfit_images(conn,project_id,name)
    if not pics:
        raise ProfileError('Dự án chưa chọn ảnh trang phục')
    # Không tự chuyển quyền sở hữu ảnh của một mục Kho khác.
    ids = [i['id'] for i in pics]
    if any(conn.execute('SELECT asset_id FROM asset_images WHERE id=?',(i,)).fetchone()['asset_id'] != a['id'] for i in ids):
        raise ProfileError('Ảnh trang phục thuộc mục Kho khác; cần chọn đúng mục trước khi lưu')
    outfit = copy.deepcopy(p.get('outfit') or {'sets':[]})
    set_id = f'project_{project_id}'
    outfit['sets'] = [s for s in outfit['sets'] if s['id'] != set_id] + [{'id':set_id,'label':assets.outfit_label(conn,project_id,name),'image_ids':ids,'items':[]}]
    outfit.setdefault('default',set_id)
    save(conn,a['id'],{'outfit':outfit},actor,p.get('revision',0))
    return set_id

# Thu đúng revision đã ĐỌC khi dựng gói; không đọc lại hồ sơ khi ghi sổ gửi.
from contextvars import ContextVar
from functools import wraps
_READS = ContextVar('kho_profile_reads', default=None)

def _record(profile):
    target = _READS.get()
    if target is not None and profile.get('schema_version') == 2 and profile.get('kho_id') is not None:
        aid, rev = profile['kho_id'], profile['revision']
        if aid in target and target[aid] != rev:
            raise ProfileError('Hồ sơ Kho đổi trong khi dựng gói; tải lại trước khi gửi')
        target[aid] = rev
    return profile

def capture_inputs(fn):
    @wraps(fn)
    def wrapped(self, job, *args, **kwargs):
        if not enabled():
            return fn(self,job,*args,**kwargs)
        all_reads = self.__dict__.setdefault('_kho_inputs',{})
        if fn.__name__ == '_submit_args':
            all_reads[job['id']] = {}
        target = all_reads.setdefault(job['id'],{})
        token = _READS.set(target)
        try:
            return fn(self,job,*args,**kwargs)
        finally:
            _READS.reset(token)
    return wrapped

def package_inputs(runner, job):
    return [{'kho_id':aid,'revision':rev} for aid,rev in sorted(getattr(runner,'_kho_inputs',{}).get(job['id'],{}).items())]

def lineage_inputs(conn, project_id, scene):
    if not enabled():
        return []
    out = {}
    token = _READS.set(out)
    try:
        for n in scene.get('characters',[]):
            for_character(conn,project_id,n)
            outfit_for(conn,project_id,n,scene)
        forms_for_shot(conn,project_id,scene)
    finally:
        _READS.reset(token)
    return [{'kho_id':aid,'revision':rev} for aid,rev in sorted(out.items())]

def for_scene_character(conn, project_id, name, scene):
    p = for_character(conn,project_id,name)
    if not p or not enabled() or p.get('schema_version') != 2:
        return p
    form = forms_for_shot(conn,project_id,scene).get(str(name).strip().upper())
    outfit = outfit_for(conn,project_id,name,scene)
    p['must_keep'] = lock_text_en(p,form,outfit)
    if form:
        p['form'] = form
    return p

def declaration(profile):
    """Ô món của trang phục cấu trúc, không suy lại quần áo v1 trong hồ sơ v2."""
    from . import identity_declare
    outfit = profile.get('outfit') or {}
    sets = outfit.get('sets') or profile.get('outfit_sets') or []
    chosen = next((s for s in sets if s.get('id')==outfit.get('default')),None)
    if chosen is None:
        return [], [{'muc':'vang','mon':None,'loi':'Hồ sơ v2 chưa khai trang phục mặc định'}]
    return identity_declare.declare_from_profile({'khai_bao_chu':chosen.get('items',[])})
