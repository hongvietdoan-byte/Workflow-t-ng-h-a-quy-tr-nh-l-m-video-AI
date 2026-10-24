"""N6 vẫn kiểm EP; pending mới không bị kẹt khi tắt cờ duyệt cũ."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture
def setup(tmp_path):
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(os, 'environ', {'HOME':str(tmp_path), 'USERPROFILE':str(tmp_path)}))
        from core import stage_desk as desk, stage_auto, stage_crew, camera_plan
        seg={'id':'doan_1','scene':'1','stage':'fixture','shots':[]}
        stack.enter_context(mock.patch.object(desk,'segment',return_value=seg))
        stack.enter_context(mock.patch.object(desk,'seg_dir',return_value=str(tmp_path)))
        stack.enter_context(mock.patch.object(stage_crew,'user_approves',return_value=False))
        stack.enter_context(mock.patch.object(camera_plan,'drawn_shots',return_value=[]))
        stack.enter_context(mock.patch.object(desk,'_sync',side_effect=lambda *args:args[-1]()))
        stack.enter_context(mock.patch.object(desk,'_say'))
        need=stack.enter_context(mock.patch.object(desk,'_need_ep'))
        verdict=stack.enter_context(mock.patch.object(stage_auto,'crew_user_verdict',return_value={'ok':True}))
        folder=tmp_path/'crew'; folder.mkdir()
        yield desk,need,verdict,folder/'state.json'


def test_pending_n6_remains_available_when_old_approval_flag_is_off(setup):
    desk,need,verdict,path=setup
    path.write_text(json.dumps({'phase':'duyet','rerender_reapproval':{'pending':True}}),encoding='utf-8')
    result=desk.approve(None,7,str(path.parent.parent),'1',{'kind':'human','who':'fixture'}, {'email':'fixture'})
    assert result['ok'] is True and verdict.call_count==1
    assert need.call_count==1


def test_pending_never_bypasses_canonical_ep_guard(setup):
    desk,need,verdict,path=setup
    path.write_text(json.dumps({'phase':'duyet','rerender_reapproval':{'pending':True}}),encoding='utf-8')
    need.side_effect=desk.DeskError('fixture EP required')
    result=desk.approve(None,7,str(path.parent.parent),'1',{'kind':'tool','who':'fixture'}, {'email':'fixture'})
    assert result['ok'] is False and verdict.call_count==0


def test_old_flag_off_contract_without_pending_is_unchanged(setup):
    desk,need,verdict,path=setup
    path.write_text(json.dumps({'phase':'duyet'}),encoding='utf-8')
    result=desk.approve(None,7,str(path.parent.parent),'1',{'kind':'human','who':'fixture'}, {'email':'fixture'})
    assert result['ok'] is False and verdict.call_count==0


def test_new_flag_is_unverified_non_paid_and_off(setup):
    from core import features
    assert 'stage_rerender_reapprove' in features.FEATURES
    flag=features.FEATURES['stage_rerender_reapprove']
    assert flag.get('verified') is False and flag.get('costs') is False
    assert features.default_state('stage_rerender_reapprove')=='off'


def test_reset_cannot_discard_pending_ep_review(setup):
    desk,need,verdict,path=setup
    from core import stage_auto
    path.write_text(json.dumps({'phase':'duyet','rerender_reapproval':{'pending':True}}),encoding='utf-8')
    before=path.read_bytes()
    with mock.patch.object(desk,'_need_edit',return_value=None), mock.patch.object(
            desk,'reset_preview',return_value={'say':'fixture'}), mock.patch.object(
            desk,'_marks',return_value={}), mock.patch.object(stage_auto,'_crew_reset') as reset:
        result=desk.reset(None,7,str(path.parent.parent),'1',{'kind':'human','who':'fixture'},confirm=True,user={})
    assert not result['ok'] and result.get('errors')
    assert reset.call_count==0 and path.read_bytes()==before
