"""Tests run the dashboard without the sign-in screen unless a test switches it on (DASHBOARD_AUTH=on)."""
import os

os.environ.setdefault("DASHBOARD_AUTH", "off")
os.environ.setdefault("FF_SITE_AUTO", "0")                       # tests never reach out to the real website on their own
os.environ.setdefault("DASHBOARD_SYNC_BACKGROUND", "0")      # folder auto-sync runs inline so tests are deterministic
# S6.5 (2026-09-29): these two became verified (on by default); the older end-to-end tests describe the run without the budget gate and
# with the one-pass Director — each feature's own tests switch it on explicitly (tests/test_project_budget.py, test_director_two_pass.py)
os.environ.setdefault("FEATURE_PROJECT_BUDGET", "0")
os.environ.setdefault("FEATURE_DIRECTOR_TWO_PASS", "0")
