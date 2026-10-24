"""M610B: fixture thuần, không đọc dữ liệu hay credential máy chính."""
import copy
import importlib
import os
import sys
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest


@contextmanager
def _credential_stubs():
    sentinel = object()
    names = ('keyring', 'winreg', 'core.providers')
    previous = {name: sys.modules.get(name, sentinel) for name in names}
    try:
        for name in names:
            sys.modules[name] = Mock()
        yield
    finally:
        for name, old in previous.items():
            if old is sentinel:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


@pytest.fixture
def api():
    with patch.object(os, 'environ', {'PYTHONUTF8': '1'}), _credential_stubs():
        module = importlib.import_module('core.qc_handoff')
        with patch('core.crew.load', side_effect=AssertionError('không đọc registry')), \
             patch('builtins.open', side_effect=AssertionError('không I/O')), \
             patch('core.handoff.record', side_effect=AssertionError('không gọi writer')), \
             patch('core.handoff.latest', side_effect=AssertionError('không đọc handoff')):
            yield module


@pytest.fixture
def inputs():
    reg = {'version': 1, 'fallback_owner': 'director',
           'roles': [
               {'id': 'director', 'writes': []},
               {'id': 'sba', 'writes': ['scenes.data.image_prompt'],
                'owns_errors': {'codes': ['QC_IMAGE*']}},
               {'id': 'engineer', 'writes': [], 'owns_errors': {'categories': ['system']}}],
           'fields': {'scenes.data.image_prompt': {'owner': 'sba'}},
           'layer_fields': {'image_prompt': 'scenes.data.image_prompt'}}
    snapshot = {'project_id': 31, 'scene_id': 12, 'shot_no': 2,
                'revision': {'scene_rev': 7, 'byd_v': 3, 'fields': {'image_prompt': 4}},
                'source_fingerprint': 'fixture-M62-full-source',
                'dependencies': [{'kind': 'byd', 'revision': 3}],
                'products': [{'path': 'output/shot2.png', 'sha256': 'a' * 64}]}
    finding = {'qc_code': 'QC_IMAGE_CAST', 'registry_ids': [],
               'actionability': {'layer': 'image_prompt'},
               'qc_evidence': {'id': 'qc:run1:cast', 'status': 'open',
                               'path': 'qc/run1.json', 'sha256': 'b' * 64}}
    return dict(snapshot=snapshot, findings=[finding], registry=reg, errors=[],
                validator_version='fixture-validator@1', enabled=True)


def test_off_does_not_touch_inputs(api):
    class Poison:
        def __iter__(self):
            raise AssertionError('OFF đã chạm input')
    assert api.build(findings=Poison(), snapshot=Poison()) == []


def test_m62_projection_and_immutable_inputs(api, inputs):
    before = copy.deepcopy(inputs)
    row, = api.build(**inputs)
    assert inputs == before
    assert row['status'] == 'SHADOW_ONLY'
    assert row['payload']['to_role'] == 'sba'
    assert row['payload']['revision'] == inputs['snapshot']['revision']
    assert row['payload']['qc_evidence'] == [inputs['findings'][0]['qc_evidence']]
    assert row['payload']['approval_state'] == 'returned'
    assert 'handoff_id' not in row and 'handoff_id' not in row['payload']
    assert row['routing']['fix_field'] == 'scenes.data.image_prompt'
    row['payload']['revision']['fields']['image_prompt'] = 99
    assert inputs == before


def test_dedup_same_finding_and_explicit_prior_keys(api, inputs):
    inputs['findings'] *= 2
    rows = api.build(**inputs)
    assert len(rows) == 1
    assert api.build(**inputs, seen_keys=[rows[0]['dedup_key']]) == []
    reordered = copy.deepcopy(inputs)
    reordered['snapshot'] = dict(reversed(list(inputs['snapshot'].items())))
    assert api.build(**reordered) == rows


@pytest.mark.parametrize('change', ['project_id', 'scene_id', 'shot_no', 'revision',
                                    'source_fingerprint', 'validator', 'evidence', 'role', 'scene_rev', 'byd_v'])
def test_dedup_tracks_full_identity(api, inputs, change):
    old = api.build(**inputs)[0]['dedup_key']
    if change == 'revision':
        inputs['snapshot']['revision']['fields']['image_prompt'] += 1
    elif change in ('scene_rev', 'byd_v'):
        inputs['snapshot']['revision'][change] += 1
    elif change == 'validator':
        inputs['validator_version'] += '-new'
    elif change == 'evidence':
        inputs['findings'][0]['qc_evidence']['sha256'] = 'c' * 64
    elif change == 'role':
        inputs['registry']['fields']['scenes.data.image_prompt']['owner'] = 'director'
    elif change == 'source_fingerprint':
        inputs['snapshot'][change] += '-new'
    else:
        inputs['snapshot'][change] += 1
    assert api.build(**inputs)[0]['dedup_key'] != old


def test_registry_category_fallback_and_cannot_fix(api, inputs):
    finding = inputs['findings'][0]
    finding['actionability'] = {}
    finding['qc_code'] = 'UNKNOWN_GATE'
    assert api.build(**inputs)[0]['routing']['note']
    assert api.build(**inputs)[0]['payload']['to_role'] == 'director'
    finding['registry_ids'] = ['E1']
    inputs['errors'] = [{'id': 'E1', 'category': 'system'}]
    assert api.build(**inputs)[0]['payload']['to_role'] == 'engineer'
    finding['actionability']['layer'] = 'image_prompt'
    inputs['registry']['roles'][1]['writes'] = []
    assert api.build(**inputs)[0]['routing']['owner_cannot_fix'] is True


@pytest.mark.parametrize('case', ['registry', 'errors', 'revision', 'qc_extra', 'hash',
                                  'validator', 'snapshot', 'findings', 'unknown_role', 'nan'])
def test_explicit_invalid_inputs_fail_closed(api, inputs, case):
    if case in ('registry', 'errors', 'validator', 'snapshot', 'findings'):
        inputs[{'validator': 'validator_version'}.get(case, case)] = None
    elif case == 'revision':
        inputs['snapshot']['revision']['_rev'] = 0
    elif case == 'qc_extra':
        inputs['findings'][0]['qc_evidence']['why'] = 'không thuộc hợp đồng M62'
    elif case == 'hash':
        inputs['findings'][0]['qc_evidence']['sha256'] = 'missing'
    elif case == 'unknown_role':
        inputs['registry']['fields']['scenes.data.image_prompt']['owner'] = 'missing'
    else:
        inputs['findings'][0]['score'] = float('nan')
    with pytest.raises(ValueError):
        api.build(**inputs)


def test_flag_catalog_default_and_experimental_off(api):
    from core import features
    with patch.object(features, 'settings', return_value={'flags': {}, 'preset': 'custom'}), \
         patch.object(features, 'baseline_state', return_value=None):
        assert features.FEATURES[api.FLAG]['verified'] is False
        assert features.FEATURES[api.FLAG]['costs'] is False
        assert features.default_state(api.FLAG) == 'off'
        assert features.on(api.FLAG) is False
        assert features._state(api.FLAG, {'flags': {}, 'preset': 'experimental'}) == 'off'


def test_aggregate_by_role_evidence_identity_and_canonical_order(api, inputs):
    f2 = copy.deepcopy(inputs['findings'][0])
    f2['qc_code'] = 'QC_IMAGE_OTHER'
    f2['qc_evidence']['id'] = 'qc:run1:other'
    old = api.build(**inputs)[0]
    inputs['findings'].append(f2)
    row, = api.build(**inputs)
    assert len(row['payload']['qc_evidence']) == 2
    assert len(row['routing']['findings']) == 2
    assert row['scope_key'] == old['scope_key']
    assert row['evidence_fingerprint'] != old['evidence_fingerprint']
    assert row['dedup_key'] != old['dedup_key']
    inputs['findings'].reverse()
    assert api.build(**inputs) == [row]
    assert len(api.build(**inputs, seen_keys=[old['dedup_key']])) == 1


@pytest.mark.parametrize('bad', ['0', 0, 1, None])
def test_enabled_must_be_explicit_bool(api, inputs, bad):
    inputs['enabled'] = bad
    with pytest.raises(ValueError):
        api.build(**inputs)


@pytest.mark.parametrize('case', ['empty_registry', 'empty_roles', 'bad_fields', 'bad_layers',
                                  'bad_errors', 'bad_owns', 'bad_writes', 'bad_id', 'bad_path'])
def test_malformed_explicit_snapshots_fail(api, inputs, case):
    if case == 'empty_registry':
        inputs['registry'] = {}
    elif case == 'empty_roles':
        inputs['registry']['roles'] = []
    elif case == 'bad_fields':
        inputs['registry']['fields'] = []
    elif case == 'bad_layers':
        inputs['registry']['layer_fields'] = {'bad': 'unknown'}
    elif case == 'bad_errors':
        inputs['errors'] = {'E1': 'malformed'}
    elif case == 'bad_owns':
        inputs['registry']['roles'][1]['owns_errors'] = {'codes': 'string'}
    elif case == 'bad_writes':
        inputs['registry']['roles'][1]['writes'] = 'string'
    elif case == 'bad_id':
        inputs['snapshot']['project_id'] = True
    else:
        inputs['findings'][0]['qc_evidence']['path'] = '../escape.json'
    with pytest.raises(ValueError):
        api.build(**inputs)



def test_new_finding_same_id_only_evidence_not_dropped(api, inputs):
    inputs['findings'][0]['qc_evidence'] = {'id': 'M62-id-only'}
    old, = api.build(**inputs)
    second = copy.deepcopy(inputs['findings'][0])
    second['qc_code'] = 'QC_IMAGE_NEW_ERROR'
    inputs['findings'].append(second)
    row, = api.build(**inputs, seen_keys=[old['dedup_key']])
    assert row['scope_key'] == old['scope_key']
    assert row['evidence_fingerprint'] == old['evidence_fingerprint']
    assert row['content_fingerprint'] != old['content_fingerprint']
    assert row['dedup_key'] != old['dedup_key']
    assert len(row['routing']['findings']) == 2
    assert len(row['payload']['qc_evidence']) == 1
    assert 'via' not in row['routing']
    assert 'fix_field' not in row['routing']
