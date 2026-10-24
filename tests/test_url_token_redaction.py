"""Token giả duy nhất; không đọc môi trường/phiên thật hay gọi mạng."""
import os
import sqlite3
from unittest import mock

import pytest


@pytest.fixture
def safe(tmp_path):
    with mock.patch.object(os, 'environ', {'HOME': str(tmp_path), 'USERPROFILE': str(tmp_path)}):
        from core import auth, diag
        with mock.patch.object(diag, 'LOST', {'count': 0}):
            yield auth, diag


@pytest.mark.parametrize('key', ['s', '%73', 'S'])
@pytest.mark.parametrize('value', ['fixture-session-short', '%46%49%58%54%55%52%45' * 7])
def test_session_query_hidden_without_losing_other_query_parameters(safe, key, value):
    _, diag = safe
    source = f'https://fixture.invalid/?pid=7&{key}={value}&step=2'
    result = diag.redact(source)
    assert value not in result
    assert result == f'https://fixture.invalid/?pid=7&{key}=***&step=2'


def test_record_masks_session_before_database_write(safe):
    _, diag = safe
    with mock.patch.object(diag, '_write') as write:
        diag.record(None, 'system', 'warn', 'GET /?s=%46%49%58&pid=7')
    assert write.call_args.args[3] == 'GET /?s=***&pid=7'


def test_fallback_stderr_masks_query_in_error_as_well_as_message(safe, capsys):
    _, diag = safe
    with mock.patch.object(diag, '_db_file', return_value=None):
        diag._keep_lost(None, 'fixture line', sqlite3.OperationalError('fixture /?s=%46%49%58&pid=7'))
    text = capsys.readouterr().err
    assert '%46%49%58' not in text and '?s=***&pid=7' in text


def test_unrelated_query_names_and_paths_stay_unchanged(safe):
    _, diag = safe
    source = 'https://fixture.invalid/assets/s=fixture?steps=2&pid=7#section'
    assert diag.redact(source) == source


def test_repeated_query_values_and_fragment_boundary(safe):
    _, diag = safe
    assert diag.redact('/?s=fixture-one&s=fixture-two#heading') == '/?s=***&s=***#heading'


def test_logout_revokes_session_and_expiry_stays_twelve_hours(safe):
    auth, _ = safe
    c = sqlite3.connect(':memory:'); c.row_factory = sqlite3.Row
    c.executescript('CREATE TABLE users(email TEXT,name TEXT,role TEXT,perms TEXT,active INTEGER);'
                    'CREATE TABLE sessions(token_hash TEXT,email TEXT,expires_at REAL);')
    c.execute("INSERT INTO users VALUES('fixture@example.test','fixture','member','[]',1)")
    c.execute('INSERT INTO sessions VALUES(?,?,?)', (auth._hash('fixture-session'), 'fixture@example.test', 2000))
    c.commit()
    try:
        with mock.patch.object(auth, '_now', return_value=1000):
            assert auth.identity(c, 'fixture-session') is not None
            auth.logout(c, 'fixture-session')
            assert auth.identity(c, 'fixture-session') is None
        assert auth.SESSION_SECONDS == 12 * 3600
    finally:
        c.close()
