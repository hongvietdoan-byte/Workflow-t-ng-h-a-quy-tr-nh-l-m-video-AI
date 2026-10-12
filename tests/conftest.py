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
import tempfile

if os.environ.get("PIPELINE_TEST_REAL_DATA") != "1":
    _ISOLATED = tempfile.mkdtemp(prefix="pipeline_test_data_")
    os.environ["FEATURE_SETTINGS_FILE"] = os.path.join(_ISOLATED, "feature_settings.json")
    os.environ["KNOWLEDGE_USER_DIR"] = os.path.join(_ISOLATED, "knowledge_user")
    os.makedirs(os.environ["KNOWLEDGE_USER_DIR"], exist_ok=True)


def pytest_unconfigure(config):
    path = globals().get("_ISOLATED")
    if path:
        shutil.rmtree(path, ignore_errors=True)
