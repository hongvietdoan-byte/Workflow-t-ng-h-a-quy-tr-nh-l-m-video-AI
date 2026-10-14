"""AppTest: cinq phiên dữ liệu giả, không API/Blender/CSDL production."""
from pathlib import Path
import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest
from core import clay_scheduler, clay_preview_service, features, plates3d
from tests.test_clay_scheduler import wait


@pytest.fixture
def ui(tmp_path,monkeypatch):
    from dashboard import admin, common
    model=tmp_path/'fixture.fbx';model.write_bytes(b'fake-model')
    monkeypatch.setattr(admin,'_fresh',lambda p:p)
    monkeypatch.setattr(common,'DATA',str(tmp_path/'data'))
    monkeypatch.setattr(plates3d,'find_blender',lambda:'fake-blender')
    monkeypatch.setattr(plates3d,'model_dir',lambda:str(tmp_path))
    monkeypatch.setattr(plates3d,'models',lambda folder:[{'name':'fixture','path':str(model),'size_mb':1}])
    monkeypatch.setattr(plates3d,'status_text',lambda:'')
    monkeypatch.setattr(plates3d,'summary',lambda m:'fixture terminé')
    monkeypatch.setattr(clay_scheduler,'_memory_available',lambda:64*1024**3)
    return admin


def app():
    return AppTest.from_string("from types import SimpleNamespace\nfrom dashboard import admin\nadmin.plates3d_panel(SimpleNamespace(conn=None),'fixture')").run()


def test_five_project_admin_submit_no_sync_render_and_poll(ui,tmp_path,monkeypatch):
    order=[]
    def execute(payload,folder,budget):
        order.append(payload['project_scope'])
        Image.new('RGB',(8,8),'gray').save(folder/'plate.png')
        return {'out_dir':str(folder),'plates':[{'name':'eye_000','file':'plate.png','render_sec':.01}]}
    with clay_scheduler.RenderQueue(execute,root=tmp_path,start=False) as service:
        monkeypatch.setattr(features,'on',lambda n:n=='clay_background_queue')
        monkeypatch.setattr(clay_preview_service,'get_service',lambda:service)
        monkeypatch.setattr(plates3d,'render',lambda *a,**k:pytest.fail('UI chạy Blender đồng bộ'))
        apps=[];entries=[]
        for _ in range(5):
            at=app();at.toggle(key='p3d_open').set_value(True).run()
            at.button(key='p3d_go').click().run()
            assert not at.exception
            apps.append(at);entries.append(dict(at.session_state['_p3d_queue']))
        assert service.snapshot()['pending']==5
        service.start()
        for entry in entries:assert wait(service,entry['ticket'])['state']=='done'
        assert order==[entry['scope'] for entry in entries]
        for at in apps:
            at.run()
            assert not at.exception
            assert Path(at.session_state['p3d_manifest']['out_dir'],'plate.png').exists()


def test_admin_off_keeps_existing_widgets_and_sync_branch(ui,tmp_path,monkeypatch):
    calls=[]
    def render(cfg):
        calls.append(cfg);folder=Path(cfg['out_dir']);folder.mkdir(parents=True)
        Image.new('RGB',(8,8),'gray').save(folder/'plate.png')
        return {'out_dir':str(folder),'plates':[{'name':'eye_000','file':'plate.png','render_sec':.01}]}
    monkeypatch.setattr(features,'on',lambda n:False)
    monkeypatch.setattr(clay_preview_service,'get_service',lambda:pytest.fail('OFF tạo worker'))
    monkeypatch.setattr(plates3d,'render',render)
    at=app();at.toggle(key='p3d_open').set_value(True).run();at.button(key='p3d_go').click().run()
    assert not at.exception and len(calls)==1
    assert at.button(key='p3d_add')


def test_admin_store_rejection_shown_without_queue_job(ui,tmp_path,monkeypatch):
    monkeypatch.setattr(features,'on',lambda n:n=='clay_background_queue')
    monkeypatch.setattr(plates3d,'find_blender',lambda:plates3d.STORE+'fake|C:/fake/blender.exe')
    with clay_scheduler.RenderQueue(lambda *a:{},root=tmp_path,start=False) as service:
        monkeypatch.setattr(clay_preview_service,'get_service',lambda:service)
        at=app();at.toggle(key='p3d_open').set_value(True).run()
        at.button(key='p3d_go').click().run()
        assert not at.exception
        assert any('Microsoft Store' in item.value for item in at.warning)
        assert service.snapshot()['pending']==0
