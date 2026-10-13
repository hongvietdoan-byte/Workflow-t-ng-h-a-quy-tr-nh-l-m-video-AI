"""Test run isolated from the machine's own (not in git) data — hộp thư 12/10 09:38: on the main machine (D:\\AI-Video-Pipeline, the
production checkout) 4 tests failed only there and passed in a clean worktree, because tests read — and `tests/_flags.py` WROTE then
restored — the real `data/feature_settings.json` (🧪 choices of production) and counted the person's uploaded documents in
`data/knowledge_user/` (Director knowledge 150 803 chars > 150 000).

Every test run gets its own empty 🧪 settings file and uploaded-knowledge folder. A test that needs its own still sets the env var /
patches as before (it wins: mock.patch.dict / monkeypatch run after this). PIPELINE_TEST_REAL_DATA=1 keeps the machine's data
(only for a deliberate check).

Parallel (pytest-xdist, `-n 8`): this file is imported once per worker process, so each worker gets its own folder above — no shared
🧪 file between workers (hộp thư 13/10 việc 3)."""
import os
import shutil
import sys
import tempfile

import pytest

if os.environ.get("PIPELINE_TEST_REAL_DATA") != "1":
    _ISOLATED = tempfile.mkdtemp(prefix="pipeline_test_data_")
    os.environ["FEATURE_SETTINGS_FILE"] = os.path.join(_ISOLATED, "feature_settings.json")
    os.environ["KNOWLEDGE_USER_DIR"] = os.path.join(_ISOLATED, "knowledge_user")
    os.makedirs(os.environ["KNOWLEDGE_USER_DIR"], exist_ok=True)


_REAL_TEMP = tempfile.gettempdir()      # %TEMP% of the machine, read before _temp_in_tmp_path moves tempfile into tmp_path
# 13/10 (người dùng): after every run the leftovers of EARLIER runs are deleted from %TEMP% — director_lease lease files of `:memory:`
# databases and Python's tmpXXXXXXXX folders — only when older than the age below, so a run in another worktree right now keeps its files
_OLD_TEMP = (("director-*.sqlite*", 3600), ("pipeline_test_data_*", 3600), ("tmp????????", 86400))


def _remove_old_temp(now=None):
    import glob
    import re
    import time
    now = now or time.time()
    removed = 0
    for pattern, age in _OLD_TEMP:
        for path in glob.glob(os.path.join(_REAL_TEMP, pattern)):
            name = os.path.basename(path)
            if pattern.startswith("tmp") and not (re.fullmatch(r"tmp[a-z0-9_]{8}", name) and os.path.isdir(path)):
                continue                       # only Python's mkdtemp folders, never another program's tmp files
            try:
                if now - os.path.getmtime(path) < age:
                    continue
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
                removed += 1
            except OSError:                    # in use / locked / already gone
                pass
    return removed


def pytest_unconfigure(config):
    path = globals().get("_ISOLATED")
    if path:
        shutil.rmtree(path, ignore_errors=True)
    if not hasattr(config, "workerinput") and os.environ.get("PIPELINE_TEST_KEEP_TEMP") != "1":   # the xdist controller only, once
        _remove_old_temp()


# core.runner keeps per-process memory keyed by job id; `:memory:` test databases restart job ids at 1, so a hold reason left by one test
# reached the next test of the same worker (-n 8, test_layout_follow) — every test starts with it empty (tests/test_xdist_isolation.py)
_RUNNER_MEMORY = ("WAIT_REASONS", "PREGEN_HELD", "_PREGEN_SAID", "_RENDER_RETRIED")


@pytest.fixture(autouse=True)
def _fresh_runner_memory():
    mod = sys.modules.get("core.runner")
    if mod is not None:
        for name in _RUNNER_MEMORY:
            getattr(mod, name).clear()
    yield


# 13/10: tests never write into the machine's %TEMP% — every tempfile.mkdtemp / NamedTemporaryFile / director_lease's `:memory:` lease
# file goes into the test's own tmp_path (pytest keeps only its last 3 runs). Before this each full run left ~370 director-*.sqlite and
# many tmp* folders in %TEMP% (~435 000 files filled drive C on 12/10).
@pytest.fixture(autouse=True)
def _temp_in_tmp_path(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    yield
