"""Đ11v2: khai khối bằng JSON, kiểm số, hai lượt sửa có đầu vào mới."""
from copy import deepcopy
import json
import math
from . import blockout, features, llm_io

def enabled(inputs):
    return features.on('director_blockout') and inputs.get('_blockout_enabled') is not False

def scene_uses_blockout(conn, inputs):
    """Kho là nguồn quyết định: model3d thật giữ đường cũ, không dùng Nhánh C."""
    if not features.on('director_blockout'): return False
    row=conn.execute('SELECT profile FROM assets WHERE id=?',(inputs['place'],)).fetchone()
    if row is None: raise ValueError('chưa có hồ sơ bối cảnh Kho; chưa quyết định được Nhánh C')
    try:
        profile=json.loads(row[0] or '{}')
    except (ValueError,TypeError):
        raise ValueError('hồ sơ bối cảnh Kho hỏng; chưa quyết định được Nhánh C') from None
    if not isinstance(profile,dict): raise ValueError('hồ sơ bối cảnh Kho phải là object')
    model=profile.get('model3d')
    if model:
        if not isinstance(model,dict) or not isinstance(model.get('path'),str) or not model['path'].strip():
            raise ValueError('metadata model3d chưa đủ; cần kiểm hồ sơ trước khi dùng Nhánh C')
        return False
    return True

def append_prompt(prompt, inputs):
    if not enabled(inputs):
        return prompt
    constraints = {k:inputs[k] for k in ('previous_end','same_space','locked_blocks','cho_dung','vat_kich_ban') if k in inputs}
    return prompt + '\n\n## Sơ đồ khối bắt buộc\n' + (
        'Trả thêm blockout: {san:{kich_thuoc:[dài,rộng],z:0},huong_sang:0,khoi:[],loi_mo:[]}. '
        'Mỗi khoi: id,loai,tam:[x,y],z,huong,kich_thuoc:[[min,max],[min,max],[min,max]],'
        'mo_ta_ngan,nguon. loai thuộc '+','.join(blockout.TYPES)+
        '; nguon thuộc '+','.join(blockout.SOURCES)+'. Đơn vị mét, +x Đông,+y Bắc,+z lên. '
        'Khối chỉ là stand_in. Không có mô hình thật mới dùng nhánh C. '
        'Giữ previous_end ở đầu cảnh nếu same_space=true; đổi không gian/thời gian phải có ngoại lệ rõ. '
        'locked_blocks là {id:{field:value}} bắt buộc giữ; không tự gỡ khóa. Thiếu số ghi can_hoi, không đoán.\n'+
        json.dumps(constraints,ensure_ascii=False,allow_nan=False))

def issues_for(obj, inputs):
    if not isinstance(obj,dict):
        return [blockout._issue('do','blockout','cần object JSON')]
    p=obj.get('blockout')
    issues=blockout.check_geometry(p,cho_dung=inputs.get('cho_dung'),vat_kich_ban=inputs.get('vat_kich_ban'))
    if blockout.validate(p): return issues
    for field in ('cho_dung','vat_kich_ban'):
        if not isinstance(inputs.get(field),list):
            issues.append(blockout._issue('vang',field,'thiếu danh sách đầu vào; chưa kiểm đủ chỗ đứng/vật kịch bản'))
    locked=inputs.get('locked_blocks',{})
    if not isinstance(locked,dict) or not all(isinstance(k,str) and isinstance(v,dict) for k,v in locked.items()):
        return issues+[blockout._issue('do','locked_blocks','cần {id:{field:value}}, không tự bỏ khóa hỏng')]
    have={b['id']:b for b in p['khoi']}
    if 'same_space' not in inputs:
        issues.append(blockout._issue('do' if inputs.get('previous_end') else 'vang','same_space',
                        'chưa khai liên tục/đổi không gian; chưa kiểm kế thừa cuối cảnh trước'))
    elif not isinstance(inputs['same_space'],bool):
        issues.append(blockout._issue('do','same_space','phải là boolean, không suy từ chữ'))
    if inputs.get('same_space') and not inputs.get('previous_end'):
        issues.append(blockout._issue('do','previous_end','cùng không gian nhưng thiếu cuối cảnh trước; cần hỏi'))
    required=deepcopy(locked)
    if inputs.get('same_space') and inputs.get('previous_end'):
        previous=inputs['previous_end']
        errors=blockout.validate(previous)
        if errors:
            issues.append(blockout._issue('do','previous_end','cuối cảnh trước thiếu/sai số; cần hỏi lại'))
        else:
            for b in previous['khoi']:
                inherited={k:b[k] for k in ('tam','z','huong') if k in b}
                for k,v in inherited.items():
                    if k in required.get(b['id'],{}) and required[b['id']][k]!=v:
                        issues.append(blockout._issue('do','locked_blocks','khóa tay mâu thuẫn cuối cảnh trước; cần hỏi'))
                required[b['id']]={**inherited,**required.get(b['id'],{})}
    for key, fields in required.items():
        b=have.get(key)
        for k,v in fields.items():
            if b is None or b.get(k)!=v:
                issues.append(blockout._issue('do',f'blockout.{key}.{k}','không giữ vị trí kế thừa/khóa tay','locked'))
    return issues

def blocking_from_plan(obj, marks=None):
    """Một nguồn vị trí khối cho solver/clay; không đổi người/nhịp/khóa trong câu trả lời.
    Solver hiện dùng bán kính bao cho box, chưa ray tracing chân đế xoay.
    """
    bl=deepcopy(obj['blocking']); props=blockout.to_props(obj['blockout'])
    by_id={p['id']:p for p in props}
    existing={o['key']:o for o in bl['objects']}
    for key,o in existing.items():
        if o.get('kind') in ('nguoi','moc'): continue
        prop=by_id.get(key)
        if prop is None:
            raise llm_io.SchemaError(f'vật dàn cảnh {key} chưa có khối blockout cùng id')
        if (o.get('at')!=prop['at'][:2] or abs(o.get('h',0)-prop['size'][2])>.01
                or abs(o.get('z',0)-prop['at'][2])>.01):
            raise llm_io.SchemaError(f'vị trí/cỡ của {key} giữa blocking và blockout mâu thuẫn; dùng một nguồn số')
        o.update(d=math.hypot(*prop['size'][:2]),stand_in=True,source=prop['source'])
    for p in props:
        if p['id'] in existing and existing[p['id']].get('kind') in ('nguoi','moc'):
            raise llm_io.SchemaError(f"id khối {p['id']} trùng nhân vật/mốc; cần tách id")
        if p['id'] not in existing:
            bl['objects'].append({'key':p['id'],'kind':'block','at':p['at'][:2],'z':p['at'][2],
                                  'h':p['size'][2],'d':math.hypot(*p['size'][:2]),'label':p['label'],
                                  'source':p['source'],'stand_in':True})
    # Kiểm cả nhịp không được chọn làm shot: không để số model khai thoát khỏi
    # cùng một plan. Chưa giải sàn nhiều cao độ/tư thế; z khác sàn cần hỏi.
    from . import stage_solver
    for beat in [None, *(bl.get('beats') or {})]:
        objects=stage_solver.objects_from_blocking(bl, marks, beat)
        where=f"blocking.beats.{beat}" if beat is not None else 'blocking.objects'
        missing=set(by_id)-set(objects)
        if missing:
            raise llm_io.SchemaError(f"{where}: không tự giấu khối plan {', '.join(sorted(missing))}")
        for key,o in objects.items():
            prop=by_id.get(key)
            if prop is not None:
                if (o['xy']!=prop['at'][:2] or abs(o['z']-prop['at'][2])>.01
                        or abs(o.get('h',0)-prop['size'][2])>.01
                        or abs(o.get('r',0)*2-math.hypot(*prop['size'][:2]))>.01):
                    raise llm_io.SchemaError(f'{where}.{key}: vật khác vị trí/cỡ plan; không tự dời khối theo nhịp')
            elif o.get('kind')=='nguoi':
                if abs(o['z']-obj['blockout']['san'].get('z',0))>blockout.FLOOR_TOL:
                    raise llm_io.SchemaError(f'{where}.{key}: hiện chỉ kiểm người trên sàn phẳng; z khác sàn cần hỏi, chưa hỗ trợ đứng trên bậc/trong vật')
                problems=blockout.check_geometry(obj['blockout'],cho_dung=[o['xy']])
                red=[i for i in problems if i['muc']=='do' and i['path'].startswith('cho_dung')]
                if red:
                    raise llm_io.SchemaError('; '.join(f"{where}.{key}: {i['code']} — {i['loi']}" for i in red))
    return bl

def generate(inputs, *, call, estimate, prompt='', validate=None, prepared=False):
    """Adapter call/estimate phục vụ fake; thật phải dùng run_stage với client có ledger.
    Một lượt đầu + tối đa hai lượt sửa; mỗi lượt kiểm và estimate trước call.
    """
    if not enabled(inputs):
        return {'enabled':False,'calls':0}
    base=prompt if prepared else append_prompt(prompt,inputs)
    text=base; obj=None; issues=[]; estimates=[]; previous_errors=None
    for rnd in range(3):
        estimates.append(estimate())
        try:
            obj=call(text)
            if isinstance(obj,str):
                from .llm_runner import extract_json
                obj=extract_json(obj)
            issues=issues_for(obj,inputs)
            if validate is not None: validate(obj)
        except (ValueError,llm_io.SchemaError) as error:
            issues=[blockout._issue('do','answer',str(error)[:500])]
        if not any(i['muc']=='do' for i in issues):
            return {'enabled':True,'ok':True,'answer':obj,'issues':issues,'calls':rnd+1,'estimates':estimates}
        errors=json.dumps([i for i in issues if i['muc']=='do'],ensure_ascii=False,sort_keys=True)
        if errors==previous_errors:
            return {'enabled':True,'ok':False,'answer':obj,'issues':issues,'calls':rnd+1,'estimates':estimates,
                    'warning':'Cùng lỗi kiểm số lặp hai lần; cần hỏi Đạo diễn/người dùng, không gọi lại tiếp.'}
        previous_errors=errors
        # Phản hồi có đường dẫn/kiểm số, không nới schema hay giữ input y nguyên.
        text=base+'\nCâu trả lời trước:\n'+json.dumps(obj,ensure_ascii=False,default=str)+\
             '\nLượt sửa '+str(rnd+1)+'; lỗi code kiểm:\n'+json.dumps(issues,ensure_ascii=False)
    return {'enabled':True,'ok':False,'answer':obj,'issues':issues,'calls':3,'estimates':estimates,
            'warning':'Sân khấu khối chưa đạt sau hai lượt sửa; cần hỏi Đạo diễn/người dùng, không dựng tiếp.'}

def run_stage(conn, client, inputs, prompt, validate):
    """Client thật từ llm_runner.client_from_env(ledger=...); giữ tagged/cổng tiền từng call."""
    from . import llm_runner, cost, stage_director
    if not getattr(client,'ledger',None):
        raise ValueError('client Đạo diễn phải có sổ chi')
    tokens=[0,0]
    def call(text):
        # Không trả tiền lại khi lỗi mạng mà chưa chắc lời gọi trước không chạy.
        retries=getattr(client,'retries',None)
        try:
            if retries is not None: client.retries=0
            with llm_runner.tagged(stage_director.STAGE,inputs.get('pid')):
                reply=client.complete(text)
        finally:
            if retries is not None: client.retries=retries
        tokens[0]+=reply.input_tokens; tokens[1]+=reply.output_tokens
        return reply.text
    def estimate():
        value=cost.llm_estimate(conn,stage_director.STAGE,1)
        print(f'Đạo diễn khối: lời gọi kế ≈ {value*cost.LLM_MARGIN:.3f} USD (ước tính)')
        return value
    result=generate(inputs,call=call,estimate=estimate, prompt=prompt,validate=validate,prepared=True)
    result['tokens']=tokens
    return result
