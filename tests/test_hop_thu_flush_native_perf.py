"""Đo lô nhỏ trên máy Windows bằng Git bare giả; không hộp thư thật."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from types import ModuleType
from unittest import mock

import pytest


GIT = Path('C:/Program Files/Git/cmd/git.exe') if os.name == 'nt' else Path('/usr/bin/git')


@pytest.mark.skipif(not GIT.is_file(), reason='Chưa có Git native đã xác định')
def test_cold_flush_thousand_old_three_new_under_twenty_seconds(tmp_path):
    home = tmp_path / 'fake-home'
    home.mkdir()
    env = {'HOME': str(home), 'USERPROFILE': str(home), 'TEMP': str(tmp_path), 'TMP': str(tmp_path),
           'SystemRoot': 'C:/Windows', 'PYTHONUTF8': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_TERMINAL_PROMPT': '0', 'GIT_ALLOW_PROTOCOL': 'file',
           'PATH': str(GIT.parent) + (';C:/Windows/System32' if os.name == 'nt' else ':/usr/bin:/bin')}
    with mock.patch.object(os, 'environ', env), mock.patch.object(
            socket.socket, 'connect', side_effect=AssertionError('network disabled')):
        keyring = ModuleType('keyring')
        keyring.get_password = mock.Mock(side_effect=AssertionError('credential disabled'))
        previous = sys.modules.get('keyring')
        sys.modules['keyring'] = keyring
        try:
            from tools import hop_thu as ht
            from tools import hop_thu_store as store
            def git(root, *args):
                r = subprocess.run([str(GIT), *args], cwd=root, env=env, capture_output=True,
                                   text=True, encoding='utf-8', errors='replace', timeout=30)
                assert r.returncode == 0, 'Git fixture thất bại'
                return r.stdout.strip()
            remote, seed, repo = tmp_path/'remote.git', tmp_path/'seed', tmp_path/'repo'
            git(tmp_path, 'init', '--bare', '-q', '-b', 'main', str(remote))
            git(tmp_path, 'clone', '-q', str(remote), str(seed))
            folder = seed/'hop_thu/su_kien'
            folder.mkdir(parents=True)
            for index in range(1000):
                event = {'kind': 'tin', 'lane': 'codex', 'to': 'phien-chinh',
                         'ts': '2026-10-24T10:00:00+07:00', 'text': f'fixture cũ {index}'}
                (folder/f'old-{index:04d}.json').write_text(json.dumps(event), encoding='utf-8')
            git(seed, 'add', 'hop_thu')
            git(seed, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@localhost', 'commit', '-qm', 'base')
            git(seed, 'push', '-q', 'origin', 'HEAD:main')
            git(tmp_path, 'clone', '-q', '-b', 'main', str(remote), str(repo))
            base = git(repo, 'rev-parse', 'HEAD')
            (repo/'staged.py').write_text('fixture = True\n', encoding='utf-8')
            git(repo, 'add', 'staged.py')
            index_before = git(repo, 'write-tree')
            new = []
            for number in range(3):
                path = ht.write_event(repo, 'codex', 'tin', to='phien-chinh', text=f'fixture mới {number}')
                store.queue_path(repo, path)
                new.append(path.relative_to(repo).as_posix())
            started = time.monotonic()
            result = store.flush_pending(repo, ht._git)
            elapsed = time.monotonic() - started
            changed = git(remote, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'main').splitlines()
            assert set(changed) == set(new)
            assert result['paths'] == 3
            assert git(repo, 'rev-parse', 'HEAD') == base
            assert git(repo, 'write-tree') == index_before
            assert not list((store.local_dir(repo)/'pending').glob('*.json'))
            assert elapsed < 20, 'Lô 3 sự kiện chưa đạt mục tiêu 20 giây'
            print(f'flush_native old=1000 new=3 elapsed_s={elapsed:.3f}')
        finally:
            if previous is None:
                sys.modules.pop('keyring', None)
            else:
                sys.modules['keyring'] = previous
