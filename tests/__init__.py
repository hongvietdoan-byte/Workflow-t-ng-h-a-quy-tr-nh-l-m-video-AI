"""Tests run the dashboard without the sign-in screen unless a test switches it on (DASHBOARD_AUTH=on)."""
import os

os.environ.setdefault("DASHBOARD_AUTH", "off")
