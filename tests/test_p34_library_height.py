"""Sửa height Kho chung trên CSDL giả, bảo toàn v1/v2 và quyền/CAS."""
import json
import os
import sqlite3
from unittest import mock

import pytest

with mock.patch.object(os,"environ",{}):
    from core import assets


@pytest.fixture(autouse=True)
def isolated(tmp_path):
    with mock.patch.object(os,"environ",{"HOME":str(tmp_path),"USERPROFILE":str(tmp_path),"DASHBOARD_AUTH":"on"}):
        yield


@pytest.fixture
def conn():
    c=sqlite3.connect(":memory:"); c.row_factory=sqlite3.Row
    c.executescript("CREATE TABLE assets(id INTEGER PRIMARY KEY,kind TEXT,name TEXT,profile TEXT,project_id INTEGER);"
                    "CREATE TABLE users(email TEXT,role TEXT,active INTEGER,perms TEXT);"
                    "CREATE TABLE audit_log(at TEXT,email TEXT,action TEXT,detail TEXT);")
    c.execute("INSERT INTO users VALUES('fixture@example.test','member',1,'[\"assets\"]')")
    c.commit()
    yield c
    c.close()


def add_asset(c,profile,project=None):
    raw=json.dumps(profile)
    c.execute("INSERT INTO assets VALUES(1,'character','fixture',?,?)",(raw,project)); c.commit()
    return raw


def test_v1_writer_preserves_all_unknown_fields(conn):
    old={"must_keep":"fixture","approved":True,"width_m":.4,"extension":{"nested":[1,2]},"_p":{"fixture":"opaque"}}
    add_asset(conn,old)
    result=assets.set_profile(conn,1,dict(old,height_m=1.8),approved=True)
    assert result["extension"] == old["extension"] and result["_p"] == old["_p"]
    assert result["width_m"] == .4 and result.get("schema_version",1) == 1


def test_v1_writer_rejects_stale_raw_snapshot(conn):
    raw=add_asset(conn,{"must_keep":"fixture","extension":{"version":1}})
    changed=json.dumps({"must_keep":"new fixture","extension":{"version":2}})
    conn.execute("UPDATE assets SET profile=? WHERE id=1",(changed,)); conn.commit()
    with pytest.raises(assets.AssetError):
        assets.set_profile(conn,1,{"height_m":1.8},approved=False,expected_profile_snapshot=raw)
    assert conn.execute("SELECT profile FROM assets WHERE id=1").fetchone()[0] == changed

USER = {"email":"fixture@example.test","role":"owner"}


def test_height_partial_preserves_profile(conn):
    from core import library_height as height
    old={"must_keep":"fixture","approved":True,"extension":{"version":1},"history":[{"why":"fixture"}]}
    raw=add_asset(conn,old)
    result=height.save_height(conn,1,1.8,user=USER,confirmed=True,expected_profile_snapshot=raw)
    assert all(result[key] == value for key,value in old.items())
    assert result["height_m"] == 1.8


@pytest.mark.parametrize("value",[None,True,"bad",float("nan"),float("inf"),0,31])
def test_height_rejects_invalid(conn,value):
    from core import library_height as height
    raw=add_asset(conn,{})
    with pytest.raises(assets.AssetError):
        height.save_height(conn,1,value,user=USER,confirmed=True,expected_profile_snapshot=raw)
    assert conn.execute("SELECT profile FROM assets").fetchone()[0] == raw


@pytest.mark.parametrize("change",["UPDATE users SET active=0","UPDATE users SET perms='[]'","UPDATE users SET role='viewer'"])
def test_height_fresh_permission_not_cached_owner(conn,change):
    from core import library_height as height
    raw=add_asset(conn,{})
    conn.execute(change); conn.commit()
    with pytest.raises(assets.AssetError):
        height.save_height(conn,1,1.8,user=USER,confirmed=True,expected_profile_snapshot=raw)
    assert conn.execute("SELECT profile FROM assets").fetchone()[0] == raw


def test_height_requires_identity_and_confirmation(conn):
    from core import library_height as height
    raw=add_asset(conn,{})
    for user,confirmed in [(None,True),(USER,False)]:
        with pytest.raises(assets.AssetError):
            height.save_height(conn,1,1.8,user=user,confirmed=confirmed,expected_profile_snapshot=raw)


@pytest.mark.parametrize("raw",['{bad','[]','{"schema_version":3}'])
def test_malformed_source_never_overwritten(conn,raw):
    from core import library_height as height
    conn.execute("INSERT INTO assets VALUES(1,'character','fixture',?,NULL)",(raw,));conn.commit()
    with pytest.raises(assets.AssetError):
        height.save_height(conn,1,1.8,user=USER,confirmed=True,expected_profile_snapshot=raw)
    assert conn.execute("SELECT profile FROM assets").fetchone()[0] == raw


def test_project_asset_cannot_be_edited(conn):
    from core import library_height as height
    raw=add_asset(conn,{},project=1)
    with pytest.raises(assets.AssetError):
        height.save_height(conn,1,1.8,user=USER,confirmed=True,expected_profile_snapshot=raw)


def test_failed_cas_does_not_open_transaction(conn):
    raw=add_asset(conn,{})
    conn.execute("UPDATE assets SET profile='{} ' WHERE id=1");conn.commit()
    with pytest.raises(assets.AssetError):
        assets.set_profile(conn,1,{"height_m":1.8},approved=False,expected_profile_snapshot=raw)
    assert not conn.in_transaction


def test_failed_cas_preserves_caller_transaction(conn):
    raw=add_asset(conn,{})
    conn.execute("UPDATE assets SET name='caller pending' WHERE id=1")
    with pytest.raises(assets.AssetError):
        assets.set_profile(conn,1,{"height_m":1.8},approved=False,expected_profile_snapshot=raw+' ')
    assert conn.in_transaction
    conn.rollback()
    assert conn.execute('SELECT name FROM assets').fetchone()[0] == 'fixture'


def test_save_refuses_pending_caller_transaction(conn):
    from core import library_height as height
    raw=add_asset(conn,{})
    conn.execute("UPDATE assets SET name='pending' WHERE id=1")
    with pytest.raises(assets.AssetError):
        height.save_height(conn,1,1.8,user=USER,confirmed=True,expected_profile_snapshot=raw)
    assert conn.in_transaction
    conn.rollback()
    assert conn.execute('SELECT name FROM assets').fetchone()[0] == 'fixture'


def test_v2_keeps_revision_actor_and_extension(conn):
    from core import library_height as height
    old={"schema_version":2,"revision":4,"approved":False,"extension":{"fixture":1}}
    raw=add_asset(conn,old)
    result=height.save_height(conn,1,1.8,user=USER,confirmed=True,expected_profile_snapshot=raw)
    assert result['schema_version']==2 and result['revision']==5
    assert result['extension']==old['extension']
    assert result['_p']['height_m']['by']==USER['email']
    assert result['_p']['height_m']['state']=='USER_LOCKED'
    with pytest.raises(assets.AssetError):
        height.save_height(conn,1,1.9,user=USER,confirmed=True,expected_profile_snapshot=raw)


@pytest.mark.parametrize('value',[' OFF ','0','false','no'])
def test_local_auth_off_uses_existing_contract(conn,value):
    from core import library_height as height
    raw=add_asset(conn,{})
    with mock.patch.object(os,'environ',{'DASHBOARD_AUTH':value}):
        result=height.save_height(conn,1,1.8,user=None,confirmed=True,expected_profile_snapshot=raw)
    assert result['height_m']==1.8


def test_listing_uses_selected_shared_asset_and_project_shots(conn):
    from core import library_height as height
    raw=add_asset(conn,{})
    conn.executescript('CREATE TABLE characters(project_id INTEGER,name TEXT,ref_asset_id INTEGER);'
                       'CREATE TABLE scenes(project_id INTEGER,idx INTEGER,data TEXT);')
    conn.execute("INSERT INTO characters VALUES(1,'vai',1)")
    conn.execute("INSERT INTO assets VALUES(2,'character','vai','{}',NULL)")
    conn.execute('INSERT INTO scenes VALUES(1,1,?)',(json.dumps({'characters':['vai','LỜI DẪN']}),))
    conn.execute('INSERT INTO scenes VALUES(2,1,?)',(json.dumps({'characters':['other']}),))
    conn.commit()
    entries,problems=height.missing_heights(conn,1,[1])
    assert entries==[{'id':1,'name':'fixture','snapshot':raw}] and not problems
    assert not conn.in_transaction


def test_v1_text_keys_remain_available(conn):
    add_asset(conn,{})
    result=assets.set_profile(conn,1,{'height_m':1.8},approved=False)
    assert all(key in result for key in assets.PROFILE_KEYS)



def test_ui_requires_shared_confirmation_and_keeps_render_snapshot(conn):
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    import sys
    from core import library_height as height
    source=Path('dashboard/stage_desk_ui.py').read_text(encoding='utf-8-sig')
    tree=ast.parse(source)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_height_fix_panel')
    entries=[{'id':1,'name':'fixture','snapshot':'{}'}]
    class FakeUI:
        def __init__(self,confirmed): self.confirmed=confirmed;self.labels=[];self.keys=[];self.reruns=0
        def caption(self,*args): pass
        def expander(self,*args): return mock.MagicMock()
        def number_input(self,label,**kwargs): self.keys.append(kwargs['key']);return 1.8
        def checkbox(self,label,**kwargs): self.labels.append(label);return self.confirmed
        def button(self,label,**kwargs): return not kwargs['disabled']
        def success(self,*args): pass
        def rerun(self): self.reruns+=1
    for confirmed in (False,True):
        ui=FakeUI(confirmed)
        namespace={'st':ui}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<height-ui>','exec'),namespace)
        common=SimpleNamespace(allowed=lambda permission:permission=='assets')
        import dashboard  # `from dashboard import common` đọc thuộc tính gói khi dashboard.common đã nạp ở test khác
        with mock.patch.dict(sys.modules,{'dashboard.common':common}), mock.patch.object(dashboard,'common',common,create=True), mock.patch.object(height,'missing_heights',return_value=(entries,[])), mock.patch.object(height,'save_height') as save:
            namespace['_height_fix_panel'](conn,1,[1],'fixture',USER,False)
        assert save.call_count==int(confirmed)
        assert ui.reruns==int(confirmed)
        assert any('Kho CHUNG' in label for label in ui.labels)
        if confirmed:
            assert save.call_args.kwargs['expected_profile_snapshot']=='{}'
            assert save.call_args.kwargs['user']==USER
        assert '{}' not in ui.keys[0]


def test_invalid_asset_kind_is_not_a_height_target(conn):
    from core import library_height as height
    raw=add_asset(conn,{})
    conn.execute("UPDATE assets SET kind='prop'");conn.commit()
    with pytest.raises(assets.AssetError):
        height.save_height(conn,1,1.8,user=USER,confirmed=True,expected_profile_snapshot=raw)


def test_missing_list_is_readonly_and_ignores_known_height(conn):
    from core import library_height as height
    raw=add_asset(conn,{'height_m':1.8})
    conn.executescript('CREATE TABLE scenes(project_id INTEGER,idx INTEGER,data TEXT);'
                       'CREATE TABLE characters(project_id INTEGER,name TEXT,ref_asset_id INTEGER);')
    conn.execute("INSERT INTO characters VALUES(1,'fixture',1)")
    conn.execute('INSERT INTO scenes VALUES(1,1,?)',(json.dumps({'characters':['fixture']}),));conn.commit()
    assert height.missing_heights(conn,1,[1])==([],[])
    assert conn.execute('SELECT profile FROM assets').fetchone()[0]==raw
    assert not conn.in_transaction
