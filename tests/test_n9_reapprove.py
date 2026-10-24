"""N9: bằng chứng hồi quy trên file giả; không Blender/API/CSDL thật."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

import pytest


@pytest.fixture
def rerendered(tmp_path,request):
    options=getattr(request,'param',{})
    env={'HOME':str(tmp_path),'USERPROFILE':str(tmp_path),'TEMP':str(tmp_path),'TMP':str(tmp_path),
         'PATH':'','FEATURE_SETTINGS_FILE':str(tmp_path/'features.json'),'FEATURE_BASELINE_FILE':'',
         'FEATURE_STAGE_RERENDER_REAPPROVE':options.get('flag','1'),
         'FEATURE_STAGE_CREW_USER_APPROVE':options.get('user_approve','1')}
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(os,'environ',env))
        stack.enter_context(mock.patch.object(subprocess,'Popen',side_effect=AssertionError('native blocked')))
        stack.enter_context(mock.patch.object(subprocess,'run',side_effect=AssertionError('native blocked')))
        keyring=ModuleType('keyring')
        keyring.get_password=mock.Mock(side_effect=AssertionError('credential blocked'))
        missing = object()
        previous_keyring = sys.modules.get('keyring', missing)
        sys.modules['keyring'] = keyring
        def restore_keyring():
            if previous_keyring is missing:
                sys.modules.pop('keyring', None)
            else:
                sys.modules['keyring'] = previous_keyring
        stack.callback(restore_keyring)
        try:
            import winreg
        except ImportError:
            pass
        else:
            stack.enter_context(mock.patch.object(winreg,'OpenKey',side_effect=FileNotFoundError('registry blocked')))
        from core import stage_auto as sa, stage_crew as sc
        seg={'id':'fixture-seg','scene':'3','stage':'fixture-stage','entry':{},'shots':[{'idx':1}]}
        inputs={'people':[],'bo_qua':[]}
        fp=sa.fingerprint(inputs)
        base=Path(sa.base_dir(str(tmp_path),7,seg['stage']))
        out=base/'doan_3'; crew=out/'crew'; old=crew/'final';old.mkdir(parents=True)
        k1=tmp_path/'fixture-k1';k1.mkdir();(k1/'stage.json').write_text('{}',encoding='utf-8')
        answer={'blocking':{'fixture':'blocking'},'shot_specs':[{'shot':1}]}
        for name,data in [('answer.json',answer),('inputs.json',inputs),('v2.json',{'fixture':'approved'})]:
            (old/name).write_text(json.dumps(data),encoding='utf-8')
        state=sc.new_state(fp)
        state.update(phase='xong',blocking=answer['blocking'],specs=answer['shot_specs'],approved_by='nguoi_dung',
                     measure='crew/m1',full_measure='crew/m1',shot_measure={'1':'crew/m1'},
                     accepted={'1':'crew/m1'},shot_hist={'1':['crew/m1']},keep={'1':'fixture waiver'},waive={'1':['fixture']})
        (crew/'state.json').write_text(json.dumps(state),encoding='utf-8')
        state_before=(crew/'state.json').read_bytes()
        (out/'result.json').write_text(json.dumps({'round':'crew/final','crew':{'approved_by':'nguoi_dung'},'fp':fp}),encoding='utf-8')
        before={p.name:p.read_bytes() for p in old.iterdir()}
        result_before=(out/'result.json').read_bytes()
        destinations=[]
        def solve(blocking,specs,rd,*args,**kwargs):
            if options.get('measure_error'):
                raise ValueError('fixture measurement failed')
            destinations.append(Path(rd))
            Path(rd).mkdir(parents=True,exist_ok=True)
            (Path(rd)/'v2.json').write_text(json.dumps({'shots':[{'shot':1,'best':{'ok':True,'m':{'at':[1,2,3]}}}]}),encoding='utf-8')
            return {'beats':{}},{'shots':[] if options.get('missing_shot') else [{'shot':1,'best':{'ok':True,'m':{'at':[1,2,3]}}}]}
        for name,value in [('ensure_k1_seg',str(k1)),('inputs_for',(inputs,[])),('stored_state_before',None),
                           ('round_blocking',{}),('draw_beats',None),('cameras_from',({1:{'fixture':'new-camera','source':'fixture'}},{})),
                           ('post_checks',{}),('mannequin_colours',{}),('end_state',{}),('guides_missing',[]),('soft_checks',[]),('_say_guides',None),('_say',None)]:
            stack.enter_context(mock.patch.object(sa,name,return_value=value))
        stack.enter_context(mock.patch.object(sa,'tool',return_value=SimpleNamespace(v2_run=solve)))
        apply=stack.enter_context(mock.patch.object(sa,'apply',return_value=[1]))
        output=sa.rerender(None,7,seg,str(tmp_path))
        yield SimpleNamespace(output=output,apply=apply,old=old,before=before,out=out,crew=crew,
                              result_before=result_before,destinations=destinations,sa=sa,sc=sc,seg=seg,
                              ctx=dict(out=str(out),crew=str(crew),inputs=inputs,fp=fp,st={},seg=seg,k1=str(k1),missing=[]),
                              state_before=state_before,data=str(tmp_path),stack=stack)


def test_n9_pending_does_not_apply_camera_before_ep(rerendered):
    assert rerendered.apply.call_count==0
    assert not rerendered.output.get('applied')


def test_n9_does_not_mutate_approved_artifacts_or_result(rerendered):
    assert {p.name:p.read_bytes() for p in rerendered.old.iterdir()}==rerendered.before
    assert (rerendered.out/'result.json').read_bytes()==rerendered.result_before
    assert all(path!=rerendered.old for path in rerendered.destinations)


def test_n9_pending_state_uses_fresh_measure_and_clears_old_acceptance(rerendered):
    state=json.loads((rerendered.crew/'state.json').read_text(encoding='utf-8'))
    assert state['phase']=='duyet' and not state.get('approved_by')
    assert state.get('shot_measure',{}).get('1') not in (None,'crew/m1','crew/final')
    assert not state.get('accepted') and not state.get('keep') and not state.get('waive')



@pytest.mark.parametrize('rerendered',[{'flag':'0'}],indirect=True)
def test_flag_off_preserves_existing_direct_apply(rerendered):
    assert rerendered.apply.call_count==1
    assert rerendered.output['applied']==[1]
    assert json.loads((rerendered.crew/'state.json').read_text(encoding='utf-8'))['phase']=='xong'


@pytest.mark.parametrize('rerendered',[{'user_approve':'0'},{'measure_error':True},{'missing_shot':True}],indirect=True)
def test_measure_failure_or_disabled_ep_keeps_approved_state(rerendered):
    assert rerendered.output['missing'] and rerendered.apply.call_count==0
    assert (rerendered.crew/'state.json').read_bytes()==rerendered.state_before
    assert {p.name:p.read_bytes() for p in rerendered.old.iterdir()}==rerendered.before
    assert (rerendered.out/'result.json').read_bytes()==rerendered.result_before


def test_pending_rejects_second_n9_even_when_flags_disabled(rerendered):
    state=json.loads((rerendered.crew/'state.json').read_text(encoding='utf-8'))
    with mock.patch.object(os,'environ',{'FEATURE_STAGE_RERENDER_REAPPROVE':'0','FEATURE_STAGE_CREW_USER_APPROVE':'0'}):
        result=rerendered.sa.rerender(None,7,rerendered.seg,rerendered.data)
    assert result['missing'] and rerendered.apply.call_count==0
    assert json.loads((rerendered.crew/'state.json').read_text(encoding='utf-8'))==state


def test_pending_blocks_non_ep_answer_and_automatic_cached_result(rerendered):
    sa=rerendered.sa
    with mock.patch.object(sa,'_crew_ctx',return_value=rerendered.ctx), mock.patch.object(os,'environ',{
            'FEATURE_STAGE_RERENDER_REAPPROVE':'0','FEATURE_STAGE_CREW_USER_APPROVE':'0'}):
        result=sa.crew_answer(None,7,rerendered.seg,rerendered.data,{'duyet':True},source='claude_code')
        assert not result['ok']
        result=sa.run_segment_crew(None,7,rerendered.seg,rerendered.data,None,force=True)
        assert result.get('waiting') and not result.get('reused')
        text,problems,state=sa.crew_prompt(None,7,rerendered.seg,rerendered.data)
        assert not text and problems and state['phase']=='duyet'
    assert rerendered.apply.call_count==0


def test_pending_measure_selection_cannot_return_old_accepted_history(rerendered):
    state=json.loads((rerendered.crew/'state.json').read_text(encoding='utf-8'))
    fresh=state['shot_measure']['1']
    assert rerendered.sa._crew_pick(rerendered.ctx,state,'1')==fresh
    record=state['history'][-1]
    assert record['previous_approval']['approved_by']=='nguoi_dung'
    assert record['previous_approval']['accepted']=={'1':'crew/m1'}



def _ep_vote(rerendered):
    with mock.patch.object(rerendered.sa,'_crew_ctx',return_value=rerendered.ctx), mock.patch.object(
            rerendered.sa,'preflight',return_value=[]), mock.patch.object(rerendered.sc,'validator',return_value=lambda obj:obj):
        return rerendered.sa.crew_user_verdict(None,7,rerendered.seg,rerendered.data,True)


def test_ep_approval_uses_fresh_final_and_keeps_previous_final_immutable(rerendered):
    result=_ep_vote(rerendered)
    assert result['ok'] and rerendered.apply.call_count==1
    state=json.loads((rerendered.crew/'state.json').read_text(encoding='utf-8'))
    assert state['phase']=='xong' and not rerendered.sa.rerender_pending(state)
    approved=json.loads((rerendered.out/'result.json').read_text(encoding='utf-8'))
    assert approved['round'].startswith('crew/final_rerender_')
    assert approved['crew']['picked']['1']==state['shot_measure']['1']
    assert {p.name:p.read_bytes() for p in rerendered.old.iterdir()}==rerendered.before


def test_failed_ep_apply_keeps_pending_and_previous_result(rerendered):
    pending=(rerendered.crew/'state.json').read_bytes()
    rerendered.apply.side_effect=ValueError('fixture write refused')
    result=_ep_vote(rerendered)
    assert not result['ok'] and result['phase']=='duyet'
    assert (rerendered.crew/'state.json').read_bytes()==pending
    assert (rerendered.out/'result.json').read_bytes()==rerendered.result_before
    assert {p.name:p.read_bytes() for p in rerendered.old.iterdir()}==rerendered.before


def test_pending_blocks_single_mode_before_render_client_or_force(rerendered):
    sa=rerendered.sa
    with mock.patch.object(sa,'ensure_k1_seg',side_effect=AssertionError('render blocked')), mock.patch.object(
            os,'environ',{'FEATURE_STAGE_CREW':'0','FEATURE_STAGE_RERENDER_REAPPROVE':'0'}):
        result=sa.run_segment(None,7,rerendered.seg,rerendered.data,None,force=True)
    assert result.get('waiting') and not result.get('reused')
    assert not result['cams'] and rerendered.apply.call_count==0


@pytest.mark.parametrize('broken',['missing','malformed','wrong_approval'])
def test_claimed_crew_approval_with_broken_state_fails_closed(rerendered,broken):
    path=rerendered.crew/'state.json'
    if broken=='missing':
        path.unlink()
    elif broken=='malformed':
        path.write_text('{bad',encoding='utf-8')
    else:
        state=json.loads(rerendered.state_before)
        state['approved_by']='dao_dien'
        path.write_text(json.dumps(state),encoding='utf-8')
    result=rerendered.sa.rerender(None,7,rerendered.seg,rerendered.data)
    assert result['missing'] and rerendered.apply.call_count==0
    assert (rerendered.out/'result.json').read_bytes()==rerendered.result_before


def test_pending_repair_measure_does_not_overwrite_numbered_round_gap(rerendered):
    sa,sc=rerendered.sa,rerendered.sc
    for name in ('m1','m3'):
        folder=rerendered.crew/name;folder.mkdir(exist_ok=True)
        (folder/'v2.json').write_text('{"fixture":"approved round"}',encoding='utf-8')
    previous=(rerendered.crew/'m3'/'v2.json').read_bytes()
    state=json.loads((rerendered.crew/'state.json').read_text(encoding='utf-8'))
    state['phase']='quay_phim_duyet'
    (rerendered.crew/'state.json').write_text(json.dumps(state),encoding='utf-8')
    measured=[]
    def ingest(work,obj,measure,source):
        measured.append(measure({},[{'shot':1}])[0])
    with mock.patch.object(sa,'_crew_ctx',return_value=rerendered.ctx), mock.patch.object(sa,'preflight',return_value=[]), mock.patch.object(
            sc,'validator',return_value=lambda obj:obj), mock.patch.object(sc,'ingest',side_effect=ingest):
        result=sa.crew_answer(None,7,rerendered.seg,rerendered.data,{},source='claude_code')
    assert result['ok'] and measured[0].startswith('crew/m_rerender_')
    assert (rerendered.crew/'m3'/'v2.json').read_bytes()==previous


def test_offline_answer_pending_rejected_before_k1_or_write(rerendered):
    with mock.patch.object(rerendered.sa,'ensure_k1_seg',side_effect=AssertionError('K1 must not run')):
        result=rerendered.sa.offline_answer(None,7,rerendered.seg,rerendered.data,{})
    assert not result['ok'] and result['errors'] and rerendered.apply.call_count==0
    assert (rerendered.out/'result.json').read_bytes()==rerendered.result_before


def test_offline_prompt_pending_rejected_before_k1(rerendered):
    with mock.patch.object(rerendered.sa,'ensure_k1_seg',side_effect=AssertionError('K1 must not run')):
        text,problems=rerendered.sa.offline_prompt(None,7,rerendered.seg,rerendered.data)
    assert not text and problems


def test_crew_prompt_reset_cannot_clear_pending_before_ep(rerendered):
    pending=(rerendered.crew/'state.json').read_bytes()
    with mock.patch.object(rerendered.sa,'_crew_ctx',side_effect=AssertionError('ctx must not run')):
        text,problems,state=rerendered.sa.crew_prompt(None,7,rerendered.seg,rerendered.data,reset=True)
    assert not text and problems and state['phase']=='duyet'
    assert (rerendered.crew/'state.json').read_bytes()==pending


def test_public_run_pending_does_not_remove_approved_camera(rerendered):
    from core import camera_plan
    sa=rerendered.sa
    with mock.patch.object(sa,'enabled',return_value=True), mock.patch.object(sa,'segments',return_value=[rerendered.seg]), mock.patch.object(
            sa,'family_hints',return_value=[]), mock.patch.object(camera_plan,'drawn_shots',return_value=[]):
        result=sa.run(None,7,rerendered.data,force=True,again=True)
    assert result['held'] and not result['applied'] and not result['removed']
    assert rerendered.apply.call_count==0


def test_public_run_late_pending_wait_result_preserves_camera(rerendered):
    from core import camera_plan,stage_crew
    sa=rerendered.sa
    with mock.patch.object(sa,'enabled',return_value=True), mock.patch.object(sa,'segments',return_value=[rerendered.seg]), mock.patch.object(
            sa,'family_hints',return_value=[]), mock.patch.object(camera_plan,'drawn_shots',return_value=[]), mock.patch.object(
            sa,'_pending_rerender_state',return_value=None), mock.patch.object(stage_crew,'enabled',return_value=False), mock.patch.object(
            sa,'run_segment',return_value={'waiting':'fixture late pending','preserve_approved':True}):
        result=sa.run(None,7,rerendered.data,force=True,again=True)
    assert result['held'] and rerendered.apply.call_count==0


def test_ep_return_allows_repair_prompt_but_never_resets_pending(rerendered):
    sa,sc=rerendered.sa,rerendered.sc
    with mock.patch.object(sa,'_crew_ctx',return_value=rerendered.ctx), mock.patch.object(sa,'preflight',return_value=[]), mock.patch.object(
            sc,'validator',return_value=lambda obj:obj), mock.patch.object(sa,'_crew_view',return_value=(None,[],[])), mock.patch.object(
            sc,'prompt_for',return_value='fixture repair prompt'):
        returned=sa.crew_user_verdict(None,7,rerendered.seg,rerendered.data,False,tra_lai=[{'shot':1,'y_do':'fixture return'}])
        assert returned['ok'] and returned['phase']=='quay_phim_duyet'
        text,problems,state=sa.crew_prompt(None,7,rerendered.seg,rerendered.data)
        assert text=='fixture repair prompt' and not problems
        assert sa.rerender_pending(state)
        pending=(rerendered.crew/'state.json').read_bytes()
        text,problems,state=sa.crew_prompt(None,7,rerendered.seg,rerendered.data,reset=True)
        assert not text and problems
        assert (rerendered.crew/'state.json').read_bytes()==pending
    assert rerendered.apply.call_count==0
