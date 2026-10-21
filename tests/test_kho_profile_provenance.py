import os
import sqlite3
from unittest.mock import patch
import pytest

@pytest.fixture
def db():
    with patch.object(os, 'environ', {}):
        c = sqlite3.connect(':memory:')
        c.row_factory = sqlite3.Row
        c.executescript('CREATE TABLE assets(id INTEGER PRIMARY KEY, name TEXT, profile TEXT); CREATE TABLE asset_images(id INTEGER PRIMARY KEY, asset_id INTEGER, path TEXT, status TEXT);')
        c.execute("INSERT INTO assets VALUES(1,'Kelly','{}')")
        yield c

def test_missing_fields_are_not_invented(db):
    from core import kho_profile as k
    with patch.object(os, 'environ', {'FEATURE_KHO_FORMS_V2':'1'}):
        p = k.read(db, 1)
        assert p['hair'] is None and p['face'] is None
        assert p['gaps']

def test_ai_cannot_overwrite_and_revision_cas(db):
    from core import kho_profile as k
    human = {'kind':'human', 'who':'fixture'}
    ai = {'kind':'ai', 'who':'fixture-model', 'model':'fixture', 'from_text':'fixture'}
    with patch.object(os, 'environ', {'FEATURE_KHO_FORMS_V2':'1'}):
        k.save(db, 1, {'hair':{'text_en':'black bob'}}, human, 0)
        p = k.save(db, 1, {'hair':{'text_en':'blonde'}}, ai, 1)
        assert p['hair']['text_en'] == 'black bob'
        assert p['proposals']['hair']['text_en'] == 'blonde'
        with pytest.raises(k.ProfileError):
            k.save(db, 1, {}, human, 0)

def test_approved_image_beats_ai_text(db):
    from core import kho_profile as k
    p = {'schema_version':2, 'hair':{'text_en':'blonde', 'ref_image_ids':[7], '_p':{'source':'ai','model':'fixture','from_text':'fixture','state':'REVIEW_REQUIRED'}}}
    db.execute("INSERT INTO asset_images VALUES(7,1,'fixture.png','approved')")
    import json
    db.execute('UPDATE assets SET profile=?', (json.dumps(p),))
    with patch.object(os, 'environ', {'FEATURE_KHO_FORMS_V2':'1'}):
        read = k.read(db, 1)
        assert 'blonde' not in k.lock_text_en(read)
        assert read['hair']['_p']['state'] == 'REVIEW_REQUIRED'

def test_nested_human_form_cannot_be_replaced_by_ai(db):
    from core import kho_profile as k
    form={'ma':'ghost_form','ten_en':'ghost form','image_ids':[]}
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        first=k.save(db,1,{'forms':[form]}, {'kind':'human','who':'fixture'},0)
        second=k.save(db,1,{'forms':[]},{'kind':'ai','who':'fixture','model':'fixture','from_text':'fixture'},1)
        assert second['forms']==first['forms'] and second['approved'] is True
        assert second['proposals']['forms']==[]

def test_malformed_v2_is_reported_and_not_approved(db):
    from core import kho_profile as k
    db.execute('UPDATE assets SET profile=?', ('{"schema_version":2,"approved":true,"outfit":{"sets":["bad"]}}',))
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        p=k.read(db,1)
        assert p['approved'] is False and p['gaps'] and p['forms']==[]

def test_capture_records_revision_read_not_later_revision(db):
    from core import kho_profile as k
    import json
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        k.save(db,1,{'hair':{'text_en':'black bob'}},{'kind':'human','who':'fixture'},0)
        class Builder:
            @k.capture_inputs
            def _submit_args(self, job):
                return k.read(db,1)['hair']['text_en']
        runner=Builder();job={'id':7}
        assert runner._submit_args(job)=='black bob'
        k.save(db,1,{'hair':{'text_en':'short black bob'}},{'kind':'human','who':'fixture'},1)
        assert k.package_inputs(runner,job)==[{'kho_id':1,'revision':1}]

def test_off_profile_v2_uses_legacy_writer_byte_behavior(db):
    from core import assets
    db.execute('UPDATE assets SET profile=?', ('{"schema_version":2,"revision":4,"hair":{}}',))
    # Cờ OFF giữ đúng writer v1, không tự kích hoạt guard.
    with patch.object(os,'environ',{}), patch.object(assets,'SIZED_KINDS',()):
        db.execute('ALTER TABLE assets ADD COLUMN kind TEXT')
        p=assets.set_profile(db,1,{'identity':'fixture'},False)
        assert 'schema_version' not in p and p['identity']=='fixture'
