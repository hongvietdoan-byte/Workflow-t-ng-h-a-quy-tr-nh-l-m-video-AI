"""Đ11v2: xem clay cục bộ, một tấm duyệt; không gửi ảnh tới model hay ghi Kho."""
import math
import tempfile
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from . import blockout, blockout_sheet as sheet, features, plate_camera, plates3d, whitebox

def render_config(plan, out_dir, *, shot=None, spot=(0, 0, 0), facing=0, resolution=(640, 360), camera=None, people=()):
    issues = blockout.check_geometry(plan)
    if any(i['muc']=='do' for i in issues):
        raise ValueError('sơ đồ có lỗi ĐỎ: '+ '; '.join(i['loi'] for i in issues if i['muc']=='do'))
    aspect = resolution[0]/resolution[1]
    # Máy đã giải/khóa là nguồn duy nhất; chỉ dùng camera_for khi chưa có máy.
    cam = dict(camera or plate_camera.camera_for(shot or {'size':'WS'}, spot, facing,
                         height_m=whitebox.EYE/.93, aspect=aspect, name='camera')['camera'])
    cam['name']='camera'
    cams=[cam]
    span=max(plan['san']['kich_thuoc'])
    z=plan['san'].get('z',0)
    for n, yaw in enumerate((45,165,285),1):
        a=math.radians(yaw)
        cams.append({'name':f'clay_{n}', 'location':[span*math.sin(a),span*math.cos(a),z+span*.65],
                     'look_at':[0,0,z+1], 'lens':35})
    props=blockout.to_props(plan)
    for c in cams: c['props']=props
    actors=[]
    for i,p in enumerate(people):
        # Whitebox chuẩn: at=[fwd,right] từ gốc có view +y → [y,x].
        at=p['at']; z=at[2] if len(at)>2 else plan['san'].get('z',0)
        yaw=math.radians(p.get('facing',0)); face=[at[1]+math.cos(yaw),at[0]+math.sin(yaw)]
        anim=whitebox.plan({'spots':{'stage':{'at':[0,0,z],'view':[0,1,z]}}},'stage',
                    [{'name':p['key'],'at':[at[1],at[0]],'height':p['H'],'face':face}])
        actor=anim['actors'][0]
        actor['color']=list(whitebox.COLORS[i%len(whitebox.COLORS)][1])
        actors.append(actor)
    return {'blockout_clay':True, 'model':None, 'out_dir':str(Path(out_dir).resolve()), 'cameras':cams,
            'actors':actors,
            'floor':plan['san'], 'resolution':list(resolution), 'samples':8, 'engine':'auto', 'depth':False,
            'presets':[], 'terrain':False, 'ground':False, 'sky':{'mode':'A','sun_elevation':45,'sun_azimuth':(90-plan['huong_sang'])%360}}

def projection(plan, camera, out_png, resolution=(640,360)):
    """Phác pinhole đúng máy; nét cạnh có phần sau máy được bỏ, không giả ray tracing."""
    w,h=resolution
    image=Image.new('RGB',resolution,'#eef1f4'); d=ImageDraw.Draw(image)
    rows=[]
    for p in blockout.to_props(plan):
        footprint=blockout._rect(p['at'][:2],p['size'],p['rotation_deg'])
        vertices=[plate_camera.project(camera['location'],camera['look_at'],camera['lens'],w/h,[x,y,z])
                  for z in (p['at'][2],p['at'][2]+p['size'][2]) for x,y in footprint]
        for a,b in [(i,(i+1)%4) for i in range(4)]+[(i+4,(i+1)%4+4) for i in range(4)]+[(i,i+4) for i in range(4)]:
            if vertices[a] is not None and vertices[b] is not None:
                d.line([(vertices[a][0]*w,vertices[a][1]*h),(vertices[b][0]*w,vertices[b][1]*h)],fill='#526675',width=2)
        rows.append({'id':p['id'],'vertices':vertices})
    d.text((8,8),'Chiếu 2D · chưa đo che khuất',font=sheet._font(14),fill='#172b3a')
    image.save(out_png)
    return {'blocks':rows,'out_png':str(out_png)}

def render_sheet(plan, cho_dung, out_png, *, reference=None, renderer=None, camera=None, shot=None,
                 spot=(0,0,0), facing=0, resolution=(640,360), timeout=110, people=()):
    """OFF chỉ topview. ON render trong thư mục riêng, không dùng kết quả/lỗi cũ."""
    # Không stat/open UNC/URL: tránh vô tình đọc ảnh qua mạng Windows.
    for candidate in (out_png, reference):
        if candidate is not None and (str(candidate).startswith(('\\\\','//')) or '://' in str(candidate)):
            raise ValueError('tấm duyệt chỉ nhận đường dẫn cục bộ')
    target=Path(out_png); target.parent.mkdir(parents=True,exist_ok=True)
    if not features.on('blockout_clay_sheet'):
        result=sheet.render_top_view(plan,cho_dung,target)
        return dict(result,clay=False,enabled=False,reason='cờ blockout_clay_sheet đang tắt')
    with tempfile.TemporaryDirectory(prefix='d11_clay_',dir=target.parent) as tmp:
        folder=Path(tmp)
        top=sheet.render_top_view(plan,cho_dung,folder/'top.png')
        standing_people=[p for p in people if p.get('tu_the','dung')=='dung']
        limitations=[]
        if not people: limitations.append('Clay chỉ có khối bối cảnh; chưa nhận vị trí người.')
        if len(standing_people)!=len(people): limitations.append('Chưa render tư thế khác đứng; không thay bằng người đứng.')
        limitations.append('Kiểm chỗ người bằng tâm XY trên sàn phẳng; chưa kiểm toàn thân/tư thế hoặc sàn nhiều cao độ.')
        cfg=render_config(plan,folder,shot=shot,spot=spot,facing=facing,camera=camera,resolution=resolution,people=standing_people)
        views=[]; reason=''; projected=None
        try:
            man=(renderer or plates3d.render)(cfg,timeout=timeout)
            for c in cfg['cameras']:
                file=folder/f"plate_{c['name']}.png"
                # Renderer phải trả tệp thật; mở/decode ngay trước khi nhận clay.
                with Image.open(file) as im: im.load()
                views.append((c['name'],file))
        except Exception as error:
            # Không đưa log renderer/config tùy ý vào UI (có thể chứa khóa từ môi trường).
            reason=f'chưa render góc clay: {type(error).__name__}; không có Blender hoặc renderer thất bại'
            views=[]
            projected=projection(plan,cfg['cameras'][0],folder/'projection.png',resolution)
        panels=views or [('Góc camera · chiếu 2D',folder/'projection.png')]
        # PNG camera bền cho màn Camera; tệp tạm bị xóa sau return.
        camera_png=target.with_name(target.stem+'_camera.png').resolve()
        with Image.open(panels[0][1]) as im:
            im.convert('RGB').save(camera_png)
        legend=[{'id':p['id'],'label':p['label']} for p in cfg['cameras'][0]['props']]
        legend_lines=[line for p in legend for line in textwrap.wrap(f"{p['id']} — {p['label']}",width=110)]
        canvas=Image.new('RGB',(1880,max(1400,1125+len(legend_lines)*23)),'#f7f8fa'); d=ImageDraw.Draw(canvas)
        with Image.open(folder/'top.png') as im: canvas.paste(im,(0,50))
        d.text((20,15),reason or 'Tấm duyệt clay · khối thay thế chỉ giữ bố cục, tỉ lệ, che khuất',font=sheet._font(18),fill='#172b3a')
        for i,(name,file) in enumerate(panels):
            cell_w,cell_h=(320,420) if views else (640,420)
            x=1220+(i%2)*cell_w if views else 1220
            y=60+(i//2)*cell_h if views else 60
            d.text((x,y),name,font=sheet._font(16),fill='#172b3a')
            with Image.open(file) as im:
                panel=ImageOps.contain(im.convert('RGB'),(cell_w-12,cell_h-40))
                canvas.paste(panel,(x,y+25))
        d.text((20,1070),'Danh mục khối — xem vị trí trên sơ đồ; chưa đo khối nào bị che ở góc clay',
               font=sheet._font(16),fill='#172b3a')
        for i,line in enumerate(legend_lines):
            d.text((20,1100+i*23),line,font=sheet._font(16),fill='#172b3a')
        if reference is not None:
            try:
                with Image.open(reference) as im: canvas.paste(ImageOps.contain(im.convert('RGB'),(640,380)),(1220,965))
                d.text((1220,935),'Ảnh tham chiếu bối cảnh',font=sheet._font(16),fill='#172b3a')
            except (OSError,ValueError):
                d.text((1220,935),'Không đọc được ảnh tham chiếu',font=sheet._font(16),fill='#b27c15')
        canvas.save(target)
        return {'enabled':True,'clay':bool(views),'reason':reason,'views':[name for name,_ in views],
                'projection':({'blocks':projected['blocks']} if projected else None),'issues':top['issues'],
                'camera':cfg['cameras'][0],'out_png':str(target),
                'camera_png':str(camera_png),'camera_kind':'clay' if views else 'projection_2d',
                'label_mode':'legend_only','legend':legend,
                'limitations':limitations}
