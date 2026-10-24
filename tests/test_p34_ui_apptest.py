"""P34: AppTest thật, backend giả 100%, không CLI/API/DB hoặc process thật."""
from contextlib import ExitStack
import json
import os
import socket
import subprocess
import sys
import threading
from types import ModuleType, SimpleNamespace
from unittest import mock

import pytest


def _height_page():
    from dashboard import stage_desk_ui
    stage_desk_ui._height_fix_panel(None, 7, [10], 'fixture', {'email':'fixture@example.test'}, False)


def _proposal_page():
    import streamlit as st
    from dashboard import stage_desk_ui
    if 'fixture_N4_ok' not in st.session_state:
        st.session_state['fixture_N4_ok'] = True
    stage_desk_ui._cli_proposal_controls(None,7,'fixture-data','3','fixture','fixture@example.test',
                                       {'email':'fixture@example.test'},False)
    st.text_area('JSON N4',key='fixture_N4_json')
    st.checkbox('Xác nhận N4',key='fixture_N4_ok')


def _auth_page():
    from types import SimpleNamespace
    from dashboard import header
    header._pipeline_cli_status(SimpleNamespace(conn=None),7)


def _review_page():
    from types import SimpleNamespace
    from dashboard import change_review_ui
    conn=SimpleNamespace(execute=lambda *args:SimpleNamespace(fetchone=lambda:(0,0)))
    change_review_ui.render(SimpleNamespace(conn=conn),7,key='fixture')


@pytest.fixture
def safe(tmp_path):
    fake={'HOME':str(tmp_path),'USERPROFILE':str(tmp_path),'PYTHONUTF8':'1',
          'TEMP':str(tmp_path),'TMP':str(tmp_path),'PATH':'',
          'FEATURE_SETTINGS_FILE':str(tmp_path/'features.json'),'FEATURE_BASELINE_FILE':'',
          'DASHBOARD_AUTH':'on','FEATURE_SAFE_PAID_BUTTONS':'1'}
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(os,'environ',fake))
        stack.enter_context(mock.patch.object(subprocess,'Popen',side_effect=AssertionError('native process blocked')))
        stack.enter_context(mock.patch.object(subprocess,'run',side_effect=AssertionError('native command blocked')))
        # asyncio/AppTest dùng socketpair trên Windows; chỉ cho phép connect
        # nội bộ đúng lúc tạo self-pipe, mọi kết nối ứng dụng vẫn bị chặn.
        connect, pair = socket.socket.connect, socket.socketpair
        plumbing = threading.local()
        def guarded_connect(sock,address):
            if getattr(plumbing,'pair',False) and address[0] in ('127.0.0.1','::1'):
                return connect(sock,address)
            raise AssertionError('network blocked')
        def self_pipe(*args,**kwargs):
            plumbing.pair=True
            try:
                return pair(*args,**kwargs)
            finally:
                plumbing.pair=False
        stack.enter_context(mock.patch.object(socket,'socketpair',side_effect=self_pipe))
        stack.enter_context(mock.patch.object(socket.socket,'connect',new=guarded_connect))
        try:
            import winreg
        except ImportError:
            pass
        else:
            stack.enter_context(mock.patch.object(winreg,'OpenKey',side_effect=FileNotFoundError('registry blocked')))
        keyring=ModuleType('keyring')
        for name in ('get_password','set_password','delete_password'):
            setattr(keyring,name,mock.Mock(side_effect=AssertionError('credential access blocked')))
        missing = object()
        previous_keyring = sys.modules.get('keyring', missing)
        sys.modules['keyring'] = keyring
        def restore_keyring():
            if previous_keyring is missing:
                sys.modules.pop('keyring', None)
            else:
                sys.modules['keyring'] = previous_keyring
        stack.callback(restore_keyring)
        from streamlit.testing.v1 import AppTest
        from core import library_height, stage_cli_proposal, stage_desk, llm_provider, cli_auth_status, access, change_review
        from dashboard import stage_desk_ui, header, common, paid_confirm, change_review_ui
        stack.enter_context(mock.patch.object(llm_provider,'resolve',return_value=('claude_cli',None)))
        # Cổng model bị chặn dù backend mock vô tình bị tháo.
        stack.enter_context(mock.patch.object(stage_cli_proposal.llm_runner,'ask_json',side_effect=AssertionError('model blocked')))
        yield SimpleNamespace(stack=stack,AppTest=AppTest,height=library_height,proposal=stage_cli_proposal,
                              desk=stage_desk,provider=llm_provider,auth=cli_auth_status,access=access,
                              cr=change_review,ui=stage_desk_ui,header=header,common=common,paid=paid_confirm)


def _app(safe,page):
    at=safe.AppTest.from_function(page,default_timeout=30).run()
    assert not at.exception
    return at


def _button(at,key):
    return next(button for button in at.button if button.key==key)


def test_height_actual_widgets_default_confirmation_snapshot_and_rerun(safe):
    allowed=safe.stack.enter_context(mock.patch.object(safe.common,'allowed',return_value=True))
    listing=safe.stack.enter_context(mock.patch.object(safe.height,'missing_heights',return_value=(
        [{'id':1,'name':'fixture','snapshot':'{"approved":false}'}],[])))
    save=safe.stack.enter_context(mock.patch.object(safe.height,'save_height'))
    at=_app(safe,_height_page)
    assert at.number_input[0].value==0.0
    assert not at.checkbox[0].value and at.button[0].disabled
    at.number_input[0].set_value(1.8).run()
    assert at.button[0].disabled and save.call_count==0
    at.checkbox[0].check().run()
    assert 'Kho CHUNG' in at.checkbox[0].label and not at.button[0].disabled
    reads=listing.call_count
    at.button[0].click().run()
    assert not at.exception and save.call_count==1 and listing.call_count>=reads+2
    assert save.call_args.args==(None,1,1.8)
    assert save.call_args.kwargs['confirmed'] is True
    assert save.call_args.kwargs['expected_profile_snapshot']=='{"approved":false}'
    assert allowed.called


def test_proposal_actual_paid_two_steps_draft_pin_and_n4_reset(safe):
    revision='fixture-revision'
    safe.stack.enter_context(mock.patch.object(safe.proposal,'quote',return_value={
        'ok':True,'revision':revision,'tag':' · hạn mức gói CLI; visible_only'}))
    generate=safe.stack.enter_context(mock.patch.object(safe.proposal,'generate',return_value={
        'ok':True,'revision':revision,'answer':{'phase':'director','fixture':1}}))
    ingest=safe.stack.enter_context(mock.patch.object(safe.desk,'load_answer'))
    at=_app(safe,_proposal_page)
    key='fixture_N4_cli_'+revision
    assert _button(at,key).disabled
    at.checkbox(key='fixture_N4_cli_consent_'+revision).check().run()
    _button(at,key).click().run()
    assert not at.exception and generate.call_count==0
    assert any('dùng hạn mức gói' in warning.value for warning in at.warning)
    _button(at,key+'_yes').click().run()
    assert not at.exception and generate.call_count==1 and ingest.call_count==0
    assert json.loads(at.text_area(key='fixture_N4_json').value)=={'phase':'director','fixture':1}
    assert at.session_state['fixture_N4_proposal_revision']==revision
    assert not at.checkbox(key='fixture_N4_ok').value
    assert generate.call_args.kwargs['expected_revision']==revision
    assert generate.call_args.kwargs['confirmed'] is True


def test_cli_status_actual_email_runtime_refresh_force(safe):
    safe.stack.enter_context(mock.patch.object(safe.header,'allowed',return_value=True))
    status=safe.stack.enter_context(mock.patch.object(safe.auth,'get_status',return_value={
        'status':'logged_in','email':'fixture@example.test','command':'C:/fixture/claude.cmd','config_dir':'C:/fixture/config'}))
    at=_app(safe,_auth_page)
    assert any('fixture@example.test' in text.value for text in at.text)
    assert any('Đã đăng nhập' in text.value for text in at.text)
    assert {block.value for block in at.code}=={'C:/fixture/claude.cmd','C:/fixture/config'}
    assert status.call_args.kwargs['force'] is False
    _button(at,'pipeline_cli_auth_refresh_7').click().run()
    assert not at.exception and status.call_args.kwargs['force'] is True


def test_cli_status_settings_denied_never_resolves_or_checks(safe):
    safe.stack.enter_context(mock.patch.object(safe.header,'allowed',return_value=False))
    status=safe.stack.enter_context(mock.patch.object(safe.auth,'get_status'))
    at=_app(safe,_auth_page)
    assert not at.button and not at.text and not at.code
    assert status.call_count==0 and safe.provider.resolve.call_count==0


def _review_backend(safe,ep):
    patches=[(safe.cr,'enabled',True),(safe.access,'can_edit',True),(safe.common,'auth_on',True),
             (safe.common,'access_user',{'email':'fixture@example.test','role':'member'}),
             (safe.common,'me',{'email':'fixture@example.test'}),(safe.common,'op_claude_seen',False),
             (safe.desk,'is_executive_producer',ep),(safe.cr,'refresh_failed_findings',None),
             (safe.cr,'failed_review_summary',[{'idx':10,'reason':'fixture failed'}]),
             (safe.cr,'open_findings',[{'id':4,'idx':10,'level':'do','khau':'fixture',
                                       'source':safe.cr.FAIL_SOURCE,'msg':'fixture failed','de_xuat':''}]),
             (safe.cr,'rerun_targets',1),(safe.cr,'rerun_tag',' · fixture estimate'),
             (safe.cr,'failed_review_snapshot','fixture-stamp')]
    for module,name,value in patches:
        safe.stack.enter_context(mock.patch.object(module,name,return_value=value))
    return safe.stack.enter_context(mock.patch.object(safe.cr,'dismiss_failed_review'))


def test_review_failed_banner_ep_reason_snapshot_skip_actual_widgets(safe):
    dismiss=_review_backend(safe,True)
    at=_app(safe,_review_page)
    assert any('Rà soát LỖI' in error.value and 'fixture failed' in error.value for error in at.error)
    skip='fixture_skip_4_fixture-stamp'
    assert _button(at,skip).disabled and dismiss.call_count==0
    at.text_input(key='fixture_reason_4_fixture-stamp').set_value('fixture reason').run()
    assert not _button(at,skip).disabled
    _button(at,skip).click().run()
    assert not at.exception and dismiss.call_count==1
    assert dismiss.call_args.kwargs['reason']=='fixture reason'
    assert dismiss.call_args.kwargs['expected_snapshot']=='fixture-stamp'
    assert dismiss.call_args.kwargs['actor']=={'kind':'human','who':'fixture@example.test'}


def test_review_non_ep_cannot_skip_failed_review_actual_widgets(safe):
    dismiss=_review_backend(safe,False)
    at=_app(safe,_review_page)
    assert not at.text_input
    assert not any('skip' in (button.key or '') for button in at.button)
    assert any('Chỉ Executive Producer' in caption.value for caption in at.caption)
    assert dismiss.call_count==0

