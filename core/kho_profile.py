"""Một cửa đọc hồ sơ Kho; v1/cờ tắt giữ nguyên dữ liệu và đường chọn cũ.

Không migration, không I/O nhà cung cấp. CAS dùng mẫu data IS của package_overrides.
"""
import copy
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
import logging
from . import assets, features, character_forms

_log = logging.getLogger(__name__)

class ProfileError(ValueError):
    pass

def enabled():
    return features.on('kho_forms_v2')

def validate(profile, conn=None, asset_id=None):
    """Chặn hồ sơ sai trước khi ghi; không tự sửa dữ liệu nguồn."""
    if not isinstance(profile, dict):
        raise ProfileError('Hồ sơ phải là object')
    if type(profile.get('schema_version')) is not int or profile.get('schema_version') != 2:
        raise ProfileError('schema_version phải bằng 2')
    if type(profile.get('revision', 0)) is not int or profile.get('revision', 0) < 0:
        raise ProfileError('revision không hợp lệ')
    def provenance(meta, require_state=True):
        if not isinstance(meta,dict) or meta.get('source') not in ('human','ai','image','import') or (require_state or 'state' in meta) and meta.get('state') not in ('AUTO','USER_LOCKED','REVIEW_REQUIRED'):
            raise ProfileError('provenance thiếu hoặc sai source/state')
        if meta['source'] == 'ai' and (not isinstance(meta.get('model'),str) or not meta['model'].strip() or not (meta.get('from_image_ids') or meta.get('from_text'))):
            raise ProfileError('AI phải khai model và nguồn')
    root_meta=profile.get('_p',{})
    if not isinstance(root_meta,dict):
        raise ProfileError('provenance cấp hồ sơ phải là object')
    for key,meta in root_meta.items():
        provenance(meta,require_state=key != 'profile')
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
    for item_set in sets:
        items=item_set.get('items',[])
        if not isinstance(items,list) or any(not isinstance(item,dict) for item in items):
            raise ProfileError('outfit.items phải là danh sách object')
        from . import identity_declare
        if any(issue.get('muc') == 'do' for issue in identity_declare.validate_khai_bao_chu(items)):
            raise ProfileError('outfit.items sai khai báo trang phục')
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
        provenance(p)
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

def _mentions_form(text, label):
    """Khớp tên dạng theo ranh giới từ Unicode, không khớp ice trong Alice."""
    phrase=r'\s+'.join(re.escape(word) for word in str(label or '').split())
    return bool(phrase and re.search(r'(?<!\w)'+phrase+r'(?!\w)',text,re.IGNORECASE))


def scalar_form(value):
    """Chỉ một dạng rõ ràng; nhiều dạng/theo nhịp cần người quyết cách chọn ảnh."""
    if isinstance(value, str):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
        return value[0]
    return None


def _requested(scene):
    """BYĐ `thanh_phan[]`: {tên HOA: dạng}, {tên HOA: kho_id}."""
    from . import shot_intent
    participants, _, _ = shot_intent.read(scene or {}, 'thanh_phan', [])
    if not isinstance(participants, list):
        return {}, {}
    rows = [(str(t.get('vat') or t.get('ten') or t.get('name') or '').strip().upper(), t) for t in participants if isinstance(t, dict)]
    return {n: t.get('dang') for n, t in rows}, {n: t.get('kho_id') for n, t in rows}


def _shot_forms(p, asset_id, scene, cast, own=None):
    """Một quy tắc chọn dạng cho cả forms_for_shot và selected_images: {tên: dạng}.
    BYĐ chốt một dạng → dạng đó; BYĐ khai nhiều dạng/theo nhịp hoặc dạng khác → không chọn; không BYĐ mà chữ cảnh nhắc
    từ 2 dạng trở lên cho cùng một tên → không tự chọn (cần người duyệt). Dạng không `applies_to` (vật) chỉ gán cho `own`."""
    scene = scene or {}
    text = ' '.join(str(scene.get(k) or '') for k in ('text','image_prompt','location')).lower()
    requested, requested_ids = _requested(scene)
    found = {}
    for f in p.get('forms', []):
        if f.get('_p',{}).get('state') != 'USER_LOCKED':
            continue
        applies = {str(n).strip().upper() for n in f.get('applies_to', [])}
        targets = applies & cast if applies else ({own} if own else set())
        targets = {n for n in targets if (requested_ids.get(n) is None or type(requested_ids[n]) is int and requested_ids[n] == asset_id)
                   and (not requested.get(n) or scalar_form(requested[n]) == f['ma'])}
        matched = any(_mentions_form(text,f[k]) for k in ('ma','ten_en','ten_vi') if f.get(k))
        for n in targets:
            explicit = scalar_form(requested.get(n)) == f['ma']
            if explicit or matched:
                found.setdefault(n, []).append((f, explicit))
    out, review = {}, []
    for n, cands in found.items():
        pick = [f for f, explicit in cands if explicit] or [f for f, _ in cands]
        if len(pick) == 1:
            out[n] = pick[0]
        else:
            review.append(n)
    if review:
        _log.warning('Kho dạng: chữ cảnh nhắc nhiều dạng cho %s (Kho %s), không tự chọn — cần BYĐ chốt một dạng', ', '.join(sorted(review)), asset_id)
    return out, review


def forms_for_shot(conn, project_id, scene, chosen=None):
    from . import byd_fields
    out = _forms_for_shot(conn, project_id, scene, chosen)
    if byd_fields.enabled('a2a'):                       # V3.1 M2.2 A2a: BYĐ thanh_phan[].dang quyết dạng (cờ tắt: không đọc gì)
        out = _byd_dang(conn, project_id, scene, chosen, out)
    return out


NORMAL_FORMS = ('thuong', 'binh thuong', 'normal', 'default')
"""A2a: `dang` nghĩa là dạng thường (prompt 31 ví dụ "thuong") — người KHÔNG ở dạng đặc biệt nào, kể cả khi chữ shot nhắc tên dạng."""


def _byd_dang(conn, project_id, scene, chosen, out):
    """A2a (G37): v2 + `dang` một giá trị → dạng đó (mục Kho style khai cho người đó, tên / bí danh trùng nguyên; hồ sơ v2 theo `ma`)
    hoặc dạng thường; nhiều dạng / theo nhịp → KHÔNG tự chọn (byd_field_mismatch, cần người chốt); dạng không có trong Kho → bỏ + nói.
    v1 / v2 không khai `dang` → giữ kết quả đường cũ (chữ cảnh) + byd_fallback khi đường cũ có chọn dạng."""
    from . import byd_fields, shot_intent
    scene = scene or {}
    cast = [str(n).strip().upper() for n in scene.get('characters') or []]
    if not byd_fields.is_v2(scene):
        if out:
            byd_fields.note(conn, 'a2a', scene, 'dạng của ' + ', '.join(sorted(out)) + ' đoán theo chữ cảnh (shot chưa có BYĐ v2 `dang`)',
                            project_id=project_id)
        return out
    parts, _, _ = shot_intent.read(scene, 'thanh_phan', [])
    said = {str(t.get('vat') or '').strip().upper(): t for t in parts if isinstance(t, dict)} if isinstance(parts, list) else {}
    res = dict(out)
    pool = None
    for name in dict.fromkeys(cast):
        t = said.get(name)
        dang = t.get('dang') if t else None
        if dang in (None, '', [], {}):
            if name in out:
                byd_fields.note(conn, 'a2a', scene, f'BYĐ v2 không khai `dang` cho {name} — dạng đoán theo chữ cảnh', project_id=project_id)
            continue
        one = scalar_form(dang)
        if one is None:
            res.pop(name, None)
            byd_fields.note(conn, 'a2a', scene, f'{name} khai nhiều dạng / dạng theo nhịp — không tự chọn dạng, cần người chốt',
                            kind=byd_fields.MISMATCH, project_id=project_id)
            continue
        cur = out.get(name)
        if cur is not None and cur.get('ma') == one:
            continue                                     # hồ sơ v2 (M2.3) đã chọn đúng dạng BYĐ khai
        if assets.fold(one.replace('_', ' ')) in NORMAL_FORMS:
            res.pop(name, None)
            continue
        if pool is None:
            pool = [a for a in (assets.project_assets(conn, project_id) if chosen is None else chosen)
                    if a.get('kind') == 'style' and name in character_forms.declared(a.get('description'))]
        hit = [a for a in pool if character_forms.names_match(a, one)]
        if len(hit) == 1:
            res[name] = character_forms.entry(hit[0])
        else:
            res.pop(name, None)
            byd_fields.note(conn, 'a2a', scene, f"BYĐ khai dạng '{one}' cho {name} nhưng Kho " +
                            ('có nhiều mục trùng tên' if hit else 'không có mục dạng trùng tên') + ' — không gửi dạng, cần người xem',
                            kind=byd_fields.MISMATCH, project_id=project_id)
    return res


def _forms_for_shot(conn, project_id, scene, chosen=None):
    if not enabled():
        return character_forms.for_shot(conn, project_id, scene, chosen)
    chosen = assets.project_assets(conn, project_id) if chosen is None else chosen
    profiles = {a['id']: read(conn, a['id']) for a in chosen}
    legacy = [a for a in chosen if profiles[a['id']].get('schema_version',1) != 2]
    out = character_forms.for_shot(conn, project_id, scene, legacy)
    scene = scene or {}
    cast = {str(n).strip().upper() for n in scene.get('characters', [])}
    for a in chosen:
        p = profiles[a['id']]
        if p.get('schema_version') != 2:
            continue
        for n, f in _shot_forms(p, a['id'], scene, cast)[0].items():
            image = next((i for iid in f.get('image_ids',[]) for i in a.get('images',[]) if i['id']==iid and i.get('status')=='approved'),None)
            value = dict(f, form=f.get('ten_en') or f['ma'], label=f.get('ten_vi') or f.get('ten_en') or f['ma'], words=f.get('words_en') or '', asset_id=a['id'], image=image, kho_id=a['id'], revision=p['revision'])
            out.setdefault(n,value)
    return out

def forms_for_rows(conn, project_id, rows):
    from . import byd_fields
    if not enabled() and not byd_fields.enabled('a2a'):
        return character_forms.for_rows(conn,project_id,rows)
    out, present = {}, {}
    for i,r in enumerate(rows or [],1):
        d = r['data'] or {}
        for n in d.get('characters') or []:
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
    s = next((s for s in p['outfit_sets'] if s['id']==default and s.get('_p',{}).get('state')=='USER_LOCKED'),None)
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

def validate_dang(conn, project_id, name, dang, *, asset_id=None):
    """API BYĐ cho C-M21: chỉ cảnh báo, không bịa enum khi Kho chưa khai."""
    if not enabled():
        return []
    a = assets.link_characters(conn,project_id,[name]).get(name)
    if asset_id is not None and (type(asset_id) is not int or not a or a['id'] != asset_id):
        return [{'muc':'vang','ma':'dang_kho_khong_khop','loi':'Mã Kho BYĐ không khớp mục Kho nhân vật đang chọn trong dự án; chưa kiểm dạng'}]
    p = read(conn,a['id']) if a else {}
    forms = p.get('forms') or []
    if not forms:
        return [{'muc':'vang','ma':'dang_khong_kiem_duoc','loi':'Kho chưa khai forms'}]
    if dang not in {f['ma'] for f in forms}:
        return [{'muc':'vang','ma':'dang_khong_trong_kho','loi':'Dạng không thuộc forms Kho'}]
    return []

def pending_review(profile):
    """Các trường chưa USER_LOCKED làm hồ sơ v2 chưa duyệt được (cùng luật `approved` của save)."""
    out = []
    for key in ('face', 'hair'):
        f = profile.get(key)
        if isinstance(f, dict) and f.get('_p', {}).get('state') != 'USER_LOCKED':
            out.append(key)
    out += [f"forms:{f.get('ma')}" for f in profile.get('forms') or [] if isinstance(f, dict) and f.get('_p', {}).get('state') != 'USER_LOCKED']
    out += [f"outfit:{s.get('id')}" for s in (profile.get('outfit') or {}).get('sets') or [] if isinstance(s, dict) and s.get('_p', {}).get('state') != 'USER_LOCKED']
    out += [key for key, m in (profile.get('_p') or {}).items() if key != 'profile' and isinstance(m, dict) and m.get('state') != 'USER_LOCKED']
    return out


def save(conn, asset_id, changes, actor, expected_revision, *, approved=None, reason=None):
    """Ghi có actor, giữ trường khóa, lưu đề xuất và CAS nguyên JSON (không migration)."""
    if not isinstance(actor,dict) or actor.get('kind') not in ('human','ai','auto','tool') or not isinstance(actor.get('who'),str) or not actor['who'].strip():
        raise ProfileError('Cần actor hợp lệ')
    if type(expected_revision) is not int or expected_revision < 0:
        raise ProfileError('expected_revision không hợp lệ')
    if not isinstance(changes,dict):
        raise ProfileError('Thay đổi hồ sơ phải là object')
    row = conn.execute('SELECT profile FROM assets WHERE id=?',(asset_id,)).fetchone()
    if row is None:
        raise ProfileError('Không tìm thấy mục Kho')
    raw = row['profile']
    try:
        old = json.loads(raw) if raw else {}
    except (ValueError,TypeError):
        raise ProfileError('Hồ sơ nguồn không phải JSON hợp lệ') from None
    if not isinstance(old,dict):
        raise ProfileError('Hồ sơ nguồn phải là object')
    if old.get('schema_version',1) != 1:
        validate(old,conn,asset_id)
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
    p['approved'] = bool(fields) and not pending_review(p)
    if reason and str(reason).strip():
        # Kế hoạch V4 4.4: đổi hồ sơ ghi lý do — writer v2 giữ `history` như writer v1.
        p['history'] = list(old.get('history') or []) + [{'date': datetime.now(timezone.utc).date().isoformat(), 'why': str(reason).strip(), 'by': actor['who']}]
    if approved is not None:
        p['approved'] = bool(approved) and p['approved']
    validate(p,conn,asset_id)
    # Không commit transaction caller: rollback ngoài phải hoàn tác cả hồ sơ.
    conn.execute('SAVEPOINT kho_profile_write')
    try:
        changed = conn.execute('UPDATE assets SET profile=? WHERE id=? AND profile IS ?',(json.dumps(p,ensure_ascii=False),asset_id,raw)).rowcount
        if changed != 1:
            raise ProfileError('revision đã đổi; tải lại')
        detail = {'kho_id':asset_id,'actor_kind':actor['kind'],
                  'before_revision':expected_revision,'revision':p['revision'],
                  'changed_keys':sorted(k for k in changes if old.get(k) != p.get(k)),
                  'before_hash':hashlib.sha256((raw or '').encode('utf-8')).hexdigest(),
                  'after_hash':hashlib.sha256(json.dumps(p,ensure_ascii=False).encode('utf-8')).hexdigest()}
        conn.execute('INSERT INTO audit_log(at,email,action,detail) VALUES(?,?,?,?)',
                     (datetime.now(timezone.utc).isoformat(),actor['who'],'kho_profile',json.dumps(detail,ensure_ascii=False)))
        conn.execute('RELEASE kho_profile_write')
    except Exception as exc:
        conn.execute('ROLLBACK TO kho_profile_write')
        conn.execute('RELEASE kho_profile_write')
        if isinstance(exc,sqlite3.Error):
            raise ProfileError('Không ghi được hồ sơ và audit; đã hoàn tác lần lưu') from None
        raise
    return p

def selected_images(asset, scene=None, name=None):
    """Ảnh v2 theo dạng (cùng quy tắc forms_for_shot: BYĐ trước, chữ cảnh sau) rồi mặt/tóc; None = dùng selector cũ.
    Hồ sơ v2 hỏng → None + cảnh báo (không chặn dựng gói)."""
    if not enabled():
        return None
    raw = asset.get('profile') or {}
    try:
        p = json.loads(raw) if isinstance(raw,str) else raw
        if not isinstance(p, dict) or p.get('schema_version') != 2:
            return None
        validate(p)
    except (ProfileError, ValueError, TypeError, KeyError, AttributeError) as exc:
        _log.warning('Kho %s: hồ sơ v2 hỏng (%s) — dùng cách chọn ảnh cũ; sửa hồ sơ ở ⚙ → 📁 Kho', asset.get('id'), exc)
        return None
    forms = [f for f in p.get('forms',[]) if f.get('_p',{}).get('state')=='USER_LOCKED']
    scene = scene or {}
    own = str(name or asset.get('name') or '').strip().upper()
    cast = {own} if name else ({str(n).strip().upper() for n in scene.get('characters', [])} | {own})
    picked, review = _shot_forms(p, asset.get('id'), scene, cast, own)
    requested, _ = _requested(scene)
    chosen = list({f['ma']: f for f in picked.values()}.values())
    if len(chosen) > 1:
        chosen = []                      # hai tên cùng mục Kho nhưng khác dạng: không tự chọn
    elif not chosen and not review and not requested.get(own) and forms and not forms[0].get('applies_to'):
        chosen = [forms[0]]              # dạng mặc định của vật khi cảnh không nhắc/không chốt dạng nào
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
    owners = [conn.execute('SELECT asset_id FROM asset_images WHERE id=?',(i,)).fetchone() for i in ids]
    if any(row is None for row in owners):
        raise ProfileError('Ảnh trang phục không còn trong Kho; chọn lại ảnh trước khi lưu')
    if any(row['asset_id'] != a['id'] for row in owners):
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
    chosen = next((s for s in sets if s.get('id')==outfit.get('default') and s.get('_p',{}).get('state')=='USER_LOCKED'),None)
    if chosen is None:
        return [], [{'muc':'vang','mon':None,'loi':'Hồ sơ v2 chưa khai trang phục mặc định'}]
    return identity_declare.declare_from_profile({'khai_bao_chu':chosen.get('items',[])})
