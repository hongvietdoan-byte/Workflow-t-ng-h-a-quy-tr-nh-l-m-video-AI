"""Tests run the dashboard without the sign-in screen unless a test switches it on (DASHBOARD_AUTH=on)."""
import os

os.environ.setdefault("DASHBOARD_AUTH", "off")
os.environ.setdefault("DASHBOARD_SYNC_BACKGROUND", "0")      # folder auto-sync runs inline so tests are deterministic
