"""Tests run the dashboard without the sign-in screen unless a test switches it on (DASHBOARD_AUTH=on)."""
import os

os.environ.setdefault("DASHBOARD_AUTH", "off")
os.environ.setdefault("FEATURE_SETTINGS_FILE", os.path.join(__import__("tempfile").mkdtemp(prefix="feat_settings_"), "none.json"))
os.environ.setdefault("FF_SITE_AUTO", "0")                       # tests never reach out to the real website on their own
os.environ.setdefault("DASHBOARD_SYNC_BACKGROUND", "0")      # folder auto-sync runs inline so tests are deterministic
# S6.5 (2026-09-29): these two became verified (on by default); the older end-to-end tests describe the run without the budget gate and
# with the one-pass Director — each feature's own tests switch it on explicitly (tests/test_project_budget.py, test_director_two_pass.py)
os.environ.setdefault("FEATURE_PROJECT_BUDGET", "0")
os.environ.setdefault("FEATURE_DIRECTOR_TWO_PASS", "0")
os.environ.setdefault("FEATURE_DIALOGUE_TAKE", "0")
for _f in ("IMPACT_SHAKE", "MUSIC_BREATH", "SOUND_INTENT", "FLASHBACK_FX", "END_HOLD", "MUSIC_FIT", "AMBIENCE_BED", "SHOT_COLOR_MATCH"):
    os.environ.setdefault("FEATURE_" + _f, "0")       # 01/10: verified (on by default) — the older render tests describe the cut without them; their own tests switch each on        # 01/10: became verified; the older lip-sync tests describe the run without it
# 2026-09-29: tests that call plates3d.render took this computer's real Blender lock and hung for as long as a real render ran
# (tower pack) — tests get their own lock file (test_concurrency_v4 still sets its own per test)
import tempfile as _tempfile  # noqa: E402

os.environ.setdefault("PLATES3D_LOCK", os.path.join(_tempfile.mkdtemp(prefix="plates3d_test_"), "blender.lock"))
