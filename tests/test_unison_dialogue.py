import pytest
from core import unison, dialogue_take, lipsync, features, llm_io
from unittest.mock import patch

def row(speaker, ms, group=1):
    return dict(speaker=speaker, text='Một hai ba', duration_ms=ms, file=speaker+'.wav', unison_group=group, unison_speakers=['A','B'])

def test_group_timing_and_take_length():
    entries=[row('A',1000), row('B',1600), dict(speaker='C',text='Sau',duration_ms=500,file='c.wav')]
    with patch.object(features,'on',return_value=True):
        assert lipsync.line_offsets(entries,1)==[1,1,2.75]
        segs=dialogue_take.segments(entries,1,.35)
        assert [s['start'] for s in segs]==[1,1,2.95]
        assert dialogue_take.length(segs)==4.05

def test_schema_and_invalid_group():
    llm_io._check_dialogue([dict(speaker='A',text='Một hai ba',unison=['A','B'])],'d')
    with pytest.raises(llm_io.SchemaError):
        llm_io._check_dialogue([dict(speaker='A',text='Một',unison=['A'])],'d')

def test_internal_onset_mismatch_cannot_pass():
    result=unison.compare_onsets([[.1,.4,.7],[.1,.49,.7]],3)
    assert result['state']=='yellow'
    assert result['max_delta_s']==pytest.approx(.09)
    assert unison.compare_onsets([[.1],[.1]],3)['state']=='yellow'

def test_proxy_never_claims_word_identity():
    result=unison.compare_onsets([[.1,.4,.7],[.12,.42,.72]],3)
    assert result['state']=='yellow'
    assert result['onset_within_limit'] is True
    assert 'từ' in result['reason']
import json
import os
import sqlite3
import math
import wave
from array import array
from core import voice, audio_lib, ffmpeg_studio, dialogue

@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv('FEATURE_UNISON_DIALOGUE','1')
    db=sqlite3.connect(tmp_path/'manifest.sqlite'); db.row_factory=sqlite3.Row
    db.executescript('CREATE TABLE scenes(id INTEGER,idx INTEGER,project_id INTEGER,data TEXT); CREATE TABLE characters(project_id INTEGER,name TEXT,voice_profile TEXT);')
    data=dict(shot_no=1,size='MS',characters=['A','B'],dialogue=[dict(speaker='A',text='Một hai ba',unison=['B','A'])])
    db.execute('INSERT INTO scenes VALUES(1,1,1,?)',(json.dumps(data),))
    for name,vid in [('A',11),('B',12)]:
        db.execute('INSERT INTO characters VALUES(1,?,?)',(name,json.dumps(dict(voice_id=vid,model='eleven_v3'))))
    db.commit()
    yield db,str(tmp_path)
    db.close()

class TTS:
    name='clipai'
    def __init__(self): self.calls=[]
    def generate_tts(self,text,voice_id,model,lang,**kwargs):
        self.calls.append((text,voice_id,model,kwargs))
        return 'tts_'+str(len(self.calls))

def voiced(db,data):
    items=voice.planned_lines(db,1)
    directory=audio_lib.assets_dir(data,1)
    rows=[dict(ln,voice_id=ln['voice']['voice_id'],kind='tts',state='succeeded',dialogue=True,duration_ms=1000+i*600,file=f'{i}.wav',use=False,volume=1,start=0) for i,ln in enumerate(items)]
    for e in rows: wav_bursts(os.path.join(directory,e['file']),[0.])
    audio_lib._save(directory,rows)
    unison.bind(db,data,1)
    return directory,rows

def test_tts_each_voice_ledger_cache_and_profile_change(project):
    db,data=project; provider=TTS()
    with patch.object(audio_lib,'audio_refusal',return_value=None) as gate, patch.object(audio_lib,'record_audio_usage') as ledger:
        result=voice.generate(db,1,provider,data,settle=False)
        assert result['sent']==2
        assert [x[1] for x in provider.calls]==[11,12]
        assert ledger.call_count==2 and gate.call_count==2
        assert all(c.args[0]==(db,1) and c.args[1].name=='clipai' for c in ledger.call_args_list)
        assert [c.kwargs for c in ledger.call_args_list]==[dict(quantity=10,unit='char',stage='tts_unison:A'),dict(quantity=10,unit='char',stage='tts_unison:B')]
        assert voice.generate(db,1,provider,data,settle=False)['skipped']==2
        assert len(provider.calls)==2
        db.execute('UPDATE characters SET voice_profile=? WHERE name=?',(json.dumps(dict(voice_id=13)), 'B'))
        assert voice.generate(db,1,provider,data,settle=False)['sent']==1
        assert [x[1] for x in provider.calls]==[11,12,13]

def test_one_event_duration_cue_and_final_simultaneous(project):
    db,data=project; directory,rows=voiced(db,data)
    assert dialogue.scene_lines(json.loads(db.execute('SELECT data FROM scenes').fetchone()[0]))==[('A','Một hai ba')]
    assert voice.scene_seconds(db,1,data)=={1:1.6}
    clip=dict(scene_id=1,path='dummy',requested_sec=5,_seconds=5)
    with patch.object(voice.final_cut,'collect_clips_for_render',return_value=[clip]):
        assert voice.place_on_timeline(db,1,data)==2
    entries=audio_lib.load(directory)
    assert [e['start'] for e in entries]==[voice.LEAD,voice.LEAD]
    assert len(audio_lib.mix_list(directory))==2  # both preserved derived voices
    cues=voice.cues(db,1,data)
    assert len(cues)==1 and cues[0].end-cues[0].start==pytest.approx(1.6)
    assert audio_lib.overlapping_tts(directory)==[]

def test_missing_voice_warns_and_cannot_request_partial_lipsync(project):
    db,data=project; directory,rows=voiced(db,data)
    audio_lib._save(directory,rows[:1])
    assert voice.scene_seconds(db,1,data)=={}
    assert 'Thiếu' in voice.unison_warnings(db,1,data)[0]['reason']
    with pytest.raises(ValueError,match='thiếu'):
        lipsync.shot_lines(data,1,1)

def test_post_multi_face_uses_take_or_generate(project):
    db,_=project; data=json.loads(db.execute('SELECT data FROM scenes').fetchone()[0])
    with patch.dict(os.environ,FEATURE_DIALOGUE_TAKE='0'):
        assert lipsync.method_for(data,post_ok=True)=='generate'
    assert 'sync.so' in lipsync.no_post_note(data)
    with patch.dict(os.environ,FEATURE_DIALOGUE_TAKE='1'):
        assert lipsync.method_for(data,post_ok=True)=='take'

def test_take_prompt_one_line_all_speakers_and_no_cross_scene_merge(project):
    _,_=project
    segs=dialogue_take.segments([row('A',1600),row('B',1000)])
    lines=dialogue_take.dialogue_lines(segs,{'A':'C1','B':'C2'})
    assert len(lines)==1 and 'SIMULTANEOUS' in lines[0] and 'C1' in lines[0] and 'C2' in lines[0]
    assert 'SIMULTANEOUSLY' in dialogue_take.lip_directive(segs,{})
    assert len(dialogue_take.dialogue_lines([dict(segs[0],scene_id=1),dict(segs[1],scene_id=2)],{}))==2
    assert len(dialogue_take.dialogue_lines([segs[0],segs[0]],{}))==2

def test_off_old_plan_segments_prompt_exact(project,monkeypatch):
    db,data=project; monkeypatch.setenv('FEATURE_UNISON_DIALOGUE','0')
    assert len(voice.planned_lines(db,1))==1
    entries=[row('A',1000),row('B',1600)]
    assert lipsync.line_offsets(entries,1)==[1,2.15]
    segs=dialogue_take.segments(entries,1,.35)
    assert segs==[dict(speaker='A',text='Một hai ba',file='A.wav',start=1,end=2),dict(speaker='B',text='Một hai ba',file='B.wav',start=2.35,end=3.95)]
    assert dialogue_take.dialogue_lines(segs,{'A':'C1','B':'C2'})==['[00:01 - 00:02] Dialogue (A / C1 lipsync @Audio1): "Một hai ba"','[00:02 - 00:04] Dialogue (B / C2 lipsync @Audio1): "Một hai ba"']

def wav_bursts(path,onsets):
    sr=16000
    pcm=array('h',(int(8000*math.sin(2*math.pi*300*i/sr)) if any(o<=i/sr<o+.09 for o in onsets) else 0 for i in range(sr)))
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm.tobytes())

def test_real_pcm_internal_mismatch_and_mix_request_inputs(project):
    db,data=project; directory,rows=voiced(db,data)
    ffmpeg=ffmpeg_studio.find_ffmpeg()
    for e,starts in zip(rows,([.1,.4,.7],[.1,.49,.7])):
        wav_bursts(os.path.join(directory,e['file']),starts)
    result=unison.measure(rows,directory,ffmpeg)
    assert result['state']=='yellow' and result['max_delta_s']==pytest.approx(.09,abs=.01)
    shot=lipsync.shot_audio(data,1,1,4,ffmpeg)
    assert shot['offsets']==[voice.LIP_LEAD,voice.LIP_LEAD]
    assert os.path.isfile(shot['path'])
    assert len(audio_lib.load(directory))==2  # both individual voices retained

def test_runner_take_actual_files_and_prompt_one_event(project,monkeypatch):
    from core.runner import VideoRunner
    db,data=project
    monkeypatch.setenv('FEATURE_LIP_SYNC','1');monkeypatch.setenv('FEATURE_DIALOGUE_TAKE','1')
    directory,entries=voiced(db,data)
    for e in entries: wav_bursts(os.path.join(directory,e['file']),[.1,.4,.7])
    runner=object.__new__(VideoRunner);runner.data_dir=data
    rows=[dict(id=1,data=json.loads(db.execute('SELECT data FROM scenes').fetchone()[0]))]
    job=dict(id=9,project_id=1)
    with patch.object(runner,'_group_secs',return_value=[4]),patch.object(runner,'_choice',return_value=dict(model='seedance-2.5')):
        segs=runner._take_segments(job,rows)
        assert [s['start'] for s in segs]==[voice.LIP_LEAD,voice.LIP_LEAD]
        assert all(s['file'].startswith('unison_') for s in segs)
        audio=runner._take_audio(job,rows)
        assert os.path.isfile(audio)
        prompt=dialogue_take.group_block(segs,['A','B'])
        assert prompt.count('Dialogue (')==1 and 'SIMULTANEOUS UNISON' in prompt
        assert 'Image' not in prompt  # Audio1 only; identity references remain the existing Seedance image package


def test_unison_reorder_does_not_repay_or_relabel(project):
    db,data=project;provider=TTS()
    with patch.object(audio_lib,'audio_refusal',return_value=None),patch.object(audio_lib,'record_audio_usage'):
        voice.generate(db,1,provider,data,settle=False)
        scene=json.loads(db.execute('SELECT data FROM scenes').fetchone()[0]);scene['dialogue'][0]['unison']=['A','B']
        db.execute('UPDATE scenes SET data=?',(json.dumps(scene),))
        assert voice.generate(db,1,provider,data,settle=False)['skipped']==2
        assert len(provider.calls)==2


def test_missing_profile_yellow_and_per_voice_status(project):
    db,data=project
    db.execute("DELETE FROM characters WHERE name='B'")
    assert voice.status(db,1,data)['no_voice']==['B']
    provider=TTS()
    with patch.object(audio_lib,'audio_refusal',return_value=None),patch.object(audio_lib,'record_audio_usage'):
        result=voice.generate(db,1,provider,data,settle=False)
        assert result['sent']==1 and result['no_voice']==['B']
        assert 'Thiếu' in voice.status(db,1,data)['unison_warnings'][0]['reason']


def test_lifecycle_toggle_and_alignment(project,monkeypatch):
    db,data=project; directory,rows=voiced(db,data)
    for e,o in zip(rows,[.1,.4]): wav_bursts(os.path.join(directory,e['file']),[o])
    unison.bind(db,data,1)
    monkeypatch.setenv('FEATURE_UNISON_DIALOGUE','0')
    assert [e['speaker'] for e in lipsync.shot_lines(data,1,1,conn=db)]==['A']
    monkeypatch.setenv('FEATURE_UNISON_DIALOGUE','1')
    aligned=lipsync.shot_lines(data,1,1,conn=db)
    ff=ffmpeg_studio.find_ffmpeg()
    assert max(unison.energy_onsets(os.path.join(directory,e['file']),ff)[0] for e in aligned)<=.01
    assert all(os.path.isfile(os.path.join(directory,e['solo_file'])) for e in aligned)
    db.execute("DELETE FROM characters WHERE name='B'")
    with pytest.raises(ValueError,match='giọng'): lipsync.shot_lines(data,1,1,conn=db)


def test_source_path_guard_before_io():
    with patch.object(os.path,'isfile') as stat:
        for value in [r'\\server\share\a.wav','https://host/a.wav','../outside.wav','C:/outside.wav']:
            with pytest.raises(ValueError): unison.local_path('assets',value)
        stat.assert_not_called()


def test_toggle_with_next_line_cache_and_stale_hash(project,monkeypatch):
    from core import delivery
    db,data=project
    scene=json.loads(db.execute('SELECT data FROM scenes').fetchone()[0])
    scene['dialogue'].append(dict(speaker='C',text='Sau'))
    db.execute('UPDATE scenes SET data=?',(json.dumps(scene),))
    db.execute('INSERT INTO characters VALUES(1,?,?)',('C',json.dumps(dict(voice_id=14))))
    db.commit()
    provider=TTS()
    with patch.object(audio_lib,'audio_refusal',return_value=None),patch.object(audio_lib,'record_audio_usage'):
        assert voice.generate(db,1,provider,data,settle=False)['sent']==3
        directory=audio_lib.assets_dir(data,1);items=audio_lib.load(directory)
        for i,e in enumerate(items):
            e.update(state='succeeded',file=f'voice{i}.wav',duration_ms=1000)
            wav_bursts(os.path.join(directory,e['file']),[0.])
        audio_lib._save(directory,items)
        first=delivery.audio_hash(data,1)
        monkeypatch.setenv('FEATURE_UNISON_DIALOGUE','0')
        assert delivery.audio_hash(data,1)!=first
        assert voice.status(db,1,data)['missing']==0
        assert [e['speaker'] for e in lipsync.shot_lines(data,1,1)]==['A','C']
        assert voice.generate(db,1,provider,data,settle=False)['sent']==0
        monkeypatch.setenv('FEATURE_UNISON_DIALOGUE','1')
        assert [e['speaker'] for e in lipsync.shot_lines(data,1,1)]==['A','B','C']
        assert voice.generate(db,1,provider,data,settle=False)['sent']==0
        assert len(provider.calls)==3
        # Live profile/schema không phụ thuộc refresh snapshot.
        before=delivery.audio_hash(data,1)
        db.execute("UPDATE characters SET voice_profile=? WHERE name='B'",(json.dumps(dict(voice_id=99)),));db.commit()
        assert delivery.audio_hash(data,1)!=before
        with pytest.raises(ValueError,match='giọng'): lipsync.shot_lines(data,1,1)


def test_actual_runner_missing_binding_profile_schema_and_file(project,monkeypatch):
    from core.runner import VideoRunner
    db,data=project;directory,entries=voiced(db,data)
    monkeypatch.setenv('FEATURE_LIP_SYNC','1');monkeypatch.setenv('FEATURE_DIALOGUE_TAKE','1')
    runner=object.__new__(VideoRunner);runner.data_dir=data
    def take():
        rows=[dict(id=1,data=json.loads(db.execute('SELECT data FROM scenes').fetchone()[0]))]
        with patch.object(runner,'_group_secs',return_value=[4]),patch.object(runner,'_choice',return_value=dict(model='seedance-2.5')):
            return runner._take_segments(dict(id=9,project_id=1),rows)
    assert len(take())==2
    os.remove(os.path.join(directory,entries[1]['file']))
    with pytest.raises(ValueError,match='giọng'):take()
    wav_bursts(os.path.join(directory,entries[1]['file']),[0.])
    db.execute("DELETE FROM characters WHERE name='B'");db.commit()
    with pytest.raises(ValueError,match='giọng'):take()
    db.execute('INSERT INTO characters VALUES(1,?,?)',('B',json.dumps(dict(voice_id=12))));db.commit()
    scene=json.loads(db.execute('SELECT data FROM scenes').fetchone()[0]);scene['dialogue'][0]['unison']=['A','C']
    db.execute('UPDATE scenes SET data=?',(json.dumps(scene),));db.commit()
    with pytest.raises(ValueError,match='giọng'):take()
    audio_lib._save(directory,[])
    with pytest.raises(ValueError,match='giọng'):take()
    audio_lib._save(directory,entries);os.remove(os.path.join(directory,'unison_context.json'))
    with pytest.raises(ValueError,match='nguồn'):take()
    audio_lib._save(directory,[])
    with pytest.raises(ValueError,match='nguồn'):take()


def test_aligned_cache_and_source_hash(project):
    from core import delivery
    db,data=project;directory,entries=voiced(db,data)
    for e,start in zip(entries,[.1,.4]):wav_bursts(os.path.join(directory,e['file']),[start])
    first=lipsync.shot_lines(data,1,1)
    stamps=[os.path.getmtime(os.path.join(directory,e['file'])) for e in first]
    assert lipsync.shot_lines(data,1,1)==first
    assert [os.path.getmtime(os.path.join(directory,e['file'])) for e in first]==stamps
    previous=delivery.audio_hash(data,1)
    wav_bursts(os.path.join(directory,entries[1]['file']),[.4,.7])
    assert delivery.audio_hash(data,1)!=previous
    changed=lipsync.shot_lines(data,1,1)
    assert changed[0]['file']==first[0]['file'] and changed[1]['file']!=first[1]['file']


def test_final_and_take_share_trimmed_files_and_clock(project):
    db,data=project;directory,entries=voiced(db,data)
    for e,start in zip(entries,[.1,.4]):wav_bursts(os.path.join(directory,e['file']),[start])
    take=lipsync.shot_lines(data,1,1)
    clip=dict(scene_id=1,path='dummy',requested_sec=5,_seconds=5)
    with patch.object(voice.final_cut,'collect_clips_for_render',return_value=[clip]):
        assert voice.place_on_timeline(db,1,data)==2
    final=[e for e in audio_lib.load(directory) if e['use']]
    assert [e['file'] for e in final]==[e['file'] for e in take]
    assert [e['duration_ms'] for e in final]==[e['duration_ms'] for e in take]
    assert final[0]['start']==final[1]['start']
    assert len(voice.cues(db,1,data))==1
    ff=ffmpeg_studio.find_ffmpeg()
    assert all(unison.energy_onsets(os.path.join(directory,e['file']),ff)[0]<=.01 for e in final)
    assert unison.measure(final,directory,ff)['state']=='yellow'


def test_legacy_off_to_on_only_new_secondary_is_paid(project,monkeypatch):
    db,data=project;provider=TTS()
    scene=json.loads(db.execute('SELECT data FROM scenes').fetchone()[0]);scene['dialogue'].append(dict(speaker='C',text='Sau'))
    db.execute('UPDATE scenes SET data=?',(json.dumps(scene),));db.execute('INSERT INTO characters VALUES(1,?,?)',('C',json.dumps(dict(voice_id=14))));db.commit()
    monkeypatch.setenv('FEATURE_UNISON_DIALOGUE','0')
    with patch.object(audio_lib,'audio_refusal',return_value=None),patch.object(audio_lib,'record_audio_usage'):
        assert voice.generate(db,1,provider,data,settle=False)['sent']==2
        monkeypatch.setenv('FEATURE_UNISON_DIALOGUE','1')
        assert voice.generate(db,1,provider,data,settle=False)['sent']==1
        assert [x[1] for x in provider.calls]==[11,14,12]
        directory=audio_lib.assets_dir(data,1)
        assert [(e['speaker'],e['line']) for e in audio_lib.load(directory)]==[('A',1),('C',3),('B',2)]
        for value in ['0','1']:
            monkeypatch.setenv('FEATURE_UNISON_DIALOGUE',value)
            assert voice.generate(db,1,provider,data,settle=False)['sent']==0
