import json
import sqlite3
from unittest.mock import patch

import pytest
from core import shot_lessons as sl


@pytest.fixture
def stage(tmp_path):
    d = tmp_path / 'stage'
    d.mkdir()
    bl = {'objects': [{'key': 'p', 'kind': 'nguoi', 'at': [0, 0]}],
          'beats': {'a': {'p': {'hanh_dong': 'đi', 'den': [1, 0]}},
                    'b': {'p': {'at': [1, 0]}}, 'c': {'p': {'at': [0, 0]}}}}
    (d / 'blocking.json').write_text(json.dumps(bl), encoding='utf-8')
    (d / 'shot_specs.json').write_text(json.dumps([{'shot': 1, 'nhip': 'a'}, {'shot': 3, 'nhip': 'c'}]), encoding='utf-8')
    return d


def database(tmp_path, rows):
    path = tmp_path / 'db # % nhịp.sqlite'
    with sqlite3.connect(path) as conn:
        conn.executescript('CREATE TABLE projects(id INTEGER PRIMARY KEY); CREATE TABLE scenes(project_id INTEGER, idx INTEGER, data TEXT); INSERT INTO projects VALUES (24);')
        conn.executemany('INSERT INTO scenes VALUES (?, ?, ?)', [(p, i, json.dumps(data)) for p, i, data in rows])
    return path


def test_partial_specs_db_order_and_project(stage, tmp_path, capsys):
    db = database(tmp_path, [(24, 3, {'byd': {'truyen': {'nhip': 'c'}}}), (99, 2, {}),
                            (24, 1, {}), (24, 2, {'byd': {'truyen': {'nhip': 'b'}}})])
    with patch('core.features.on', return_value=True), patch.object(sl, 'movement_gaps', return_value=[]) as check:
        assert sl.main(['nhip', str(stage), '--db', str(db), '--project', '24']) == 0
    assert check.call_args.args[1] == ['a', 'b', 'c']
    assert '0 mục VÀNG' in capsys.readouterr().out


def test_unknown_shot_splits_sequence(stage, tmp_path, capsys):
    db = database(tmp_path, [(24, 1, {}), (24, 2, {'title': 'b'}), (24, 3, {})])
    with patch('core.features.on', return_value=True):
        sl.main(['nhip', str(stage), '--db', str(db), '--project', '24'])
    output = capsys.readouterr().out
    assert 'shot 2' in output and 'thiếu ánh xạ' in output
    assert 'kết thúc ở' not in output


@pytest.mark.parametrize('kind', ['missing', 'corrupt', 'project', 'no_project_arg'])
def test_bad_database_warns(stage, tmp_path, capsys, kind):
    db = tmp_path / 'absent.sqlite'
    args = ['nhip', str(stage), '--db', str(db)]
    if kind == 'corrupt':
        db.write_text('hỏng', encoding='utf-8')
    if kind == 'project':
        db = database(tmp_path, [])
        args[-1] = str(db)
    if kind != 'no_project_arg':
        args += ['--project', '999']
    with patch('core.features.on', return_value=True):
        sl.main(args)
    assert '[VÀNG]' in capsys.readouterr().out
    if kind in ('missing', 'no_project_arg'):
        assert not db.exists()


def test_enabled_no_db_warns(stage, capsys):
    with patch('core.features.on', return_value=True):
        sl.main(['nhip', str(stage)])
    assert 'thứ tự suy từ shot_specs' in capsys.readouterr().out


def test_flag_off_db_never_opened(stage, capsys):
    with patch('core.features.on', return_value=False), patch('sqlite3.connect', side_effect=AssertionError('opened')):
        sl.main(['nhip', str(stage), '--db', 'missing.sqlite', '--project', '24'])
    assert 'cần bật cờ shot_lessons_db_order' in capsys.readouterr().out


def test_flag_off_old_cli_identical(stage, capsys):
    with patch('core.features.on', return_value=False):
        sl.main(['nhip', str(stage)])
    assert 'thứ tự suy' not in capsys.readouterr().out


def test_drift_approved_db_mapping(stage, tmp_path, capsys):
    db = database(tmp_path, [(24, 2, {'byd': {'truyen': {'nhip': 'b'}}})])
    with patch('core.features.on', return_value=True), patch.object(sl, 'layout_drift', return_value=[]) as check:
        sl.main(['drift', str(stage), str(stage), '--approved', '2,9', '--db', str(db), '--project', '24'])
    assert check.call_args.args[2] == {2: 'b'}
    assert 'shot 9' in capsys.readouterr().out


def test_correct_order_has_no_false_movement_warning(stage, tmp_path, capsys):
    db = database(tmp_path, [(24, 3, {}), (24, 2, {'byd': {'truyen': {'nhip': 'b'}}}), (24, 1, {})])
    before = db.read_bytes()
    with patch('core.features.on', return_value=True):
        sl.main(['nhip', str(stage), '--db', str(db), '--project', '24'])
    assert capsys.readouterr().out == '0 mục VÀNG\n'
    assert db.read_bytes() == before


def test_readonly_connection_and_cwd_independence(stage, tmp_path, monkeypatch):
    db = database(tmp_path, [(24, 1, {})])
    connect = sqlite3.connect
    opened = []
    def readonly(database_uri, **kwargs):
        conn = connect(database_uri, **kwargs)
        with pytest.raises(sqlite3.OperationalError, match='readonly'):
            conn.execute('DELETE FROM scenes')
        opened.append(database_uri)
        return conn
    monkeypatch.chdir(tmp_path)
    with patch('core.features.on', return_value=True), patch('sqlite3.connect', side_effect=readonly):
        sl.main(['nhip', str(stage), '--db', db.name, '--project', '24'])
    assert len(opened) == 1
    assert '%23' in opened[0] and '%25' in opened[0]


@pytest.mark.parametrize('data, expected', [
    ({'byd': {'truyen': {'nhip': 'b'}}}, 'mâu thuẫn'),
    ({'byd': {'truyen': {'nhip': 'unknown'}}}, 'mâu thuẫn'),
    (['not a mapping'], 'hỏng'),
])
def test_invalid_mapping_warns_instead_of_checking(stage, tmp_path, capsys, data, expected):
    db = database(tmp_path, [(24, 1, data)])
    with patch('core.features.on', return_value=True), patch.object(sl, 'movement_gaps') as check:
        sl.main(['nhip', str(stage), '--db', str(db), '--project', '24'])
    assert expected in capsys.readouterr().out
    check.assert_not_called()


def test_db_missing_schema_warns(stage, tmp_path, capsys):
    db = tmp_path / 'schema.sqlite'
    with sqlite3.connect(db):
        pass
    with patch('core.features.on', return_value=True):
        sl.main(['nhip', str(stage), '--db', str(db), '--project', '24'])
    assert 'no such table' in capsys.readouterr().out


def test_feature_default_off(monkeypatch):
    from core import features
    monkeypatch.delenv('FEATURE_SHOT_LESSONS_DB_ORDER', raising=False)
    assert features.FEATURES['shot_lessons_db_order']['verified'] is False
