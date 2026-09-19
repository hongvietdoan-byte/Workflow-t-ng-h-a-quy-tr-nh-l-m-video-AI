import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    operating_mode TEXT NOT NULL DEFAULT 'human_qc' CHECK (operating_mode IN ('auto','human_qc')),
    qc_auto_pass_threshold REAL NOT NULL DEFAULT 0.85,
    max_retry_count INTEGER NOT NULL DEFAULT 3,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scenes (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    idx INTEGER NOT NULL,
    title TEXT,
    state TEXT NOT NULL DEFAULT 'ready',
    data TEXT,
    UNIQUE (project_id, idx)
);
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    wardrobe TEXT,
    locked INTEGER NOT NULL DEFAULT 0,
    UNIQUE (project_id, name)
);
CREATE TABLE IF NOT EXISTS motion_prompts (
    id INTEGER PRIMARY KEY,
    scene_id INTEGER NOT NULL UNIQUE REFERENCES scenes(id),
    motion_prompt TEXT NOT NULL,
    camera TEXT,
    duration_sec REAL NOT NULL DEFAULT 5,
    negative_prompt TEXT,
    state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','approved'))
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    scene_id INTEGER NOT NULL REFERENCES scenes(id),
    type TEXT NOT NULL CHECK (type IN ('image_gen','video_gen','render','music')),
    state TEXT NOT NULL,
    parent_job_id INTEGER REFERENCES jobs(id),
    retry_count INTEGER NOT NULL DEFAULT 0,
    retry_reason TEXT,
    escalated INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    from_state TEXT,
    to_state TEXT NOT NULL,
    actor TEXT NOT NULL,
    note TEXT,
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS qc_results (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    criterion TEXT NOT NULL,
    score REAL NOT NULL,
    threshold_at_time REAL NOT NULL,
    auto_decision TEXT
);
CREATE TABLE IF NOT EXISTS review_log (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    reviewer_type TEXT NOT NULL CHECK (reviewer_type IN ('ai_agent','user')),
    decision TEXT NOT NULL CHECK (decision IN ('approve','reject')),
    note TEXT,
    decided_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS content_moderation_failures (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    provider TEXT NOT NULL,
    error_message TEXT NOT NULL,
    at TEXT NOT NULL
);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
