"""Pre-flight IP / content check (Step 1) — warn before spending credits on blocked characters."""
import json
import os
import re
import sqlite3
from typing import Dict, List

BLOCKLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ip_blocklist.json")


def load_blocklist(path: str = BLOCKLIST_PATH) -> List[Dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["entries"]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def check_text(text: str, entries: List[Dict]) -> List[Dict]:
    haystack = _norm(text)
    hits = []
    for e in entries:
        for term in [e["name"], *e.get("aliases", [])]:
            if re.search(rf"(?<!\w){re.escape(_norm(term))}(?!\w)", haystack):
                hits.append({"entry": e["name"], "matched": term, "reason": e.get("reason", "")})
                break
    return hits


def check_characters(conn: sqlite3.Connection, project_id: int, entries: List[Dict]) -> List[Dict]:
    warnings = []
    for row in conn.execute("SELECT name, description, wardrobe FROM characters WHERE project_id=?", (project_id,)):
        text = " ".join(filter(None, [row["name"], row["description"], row["wardrobe"]]))
        for hit in check_text(text, entries):
            warnings.append({"character": row["name"], **hit})
    return warnings


def record_failure(conn: sqlite3.Connection, job_id: int, provider: str, message: str) -> None:
    """Log a provider risk-control failure (e.g. 'Failure to pass the risk control system')."""
    conn.execute("INSERT INTO content_moderation_failures (job_id, provider, error_message, at)"
                 " VALUES (?,?,?,datetime('now'))", (job_id, provider, message))
    conn.commit()
