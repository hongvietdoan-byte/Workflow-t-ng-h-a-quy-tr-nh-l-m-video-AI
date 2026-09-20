import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    operating_mode TEXT NOT NULL DEFAULT 'human_qc' CHECK (operating_mode IN ('auto','human_qc')),
    qc_auto_pass_threshold REAL NOT NULL DEFAULT 0.85,
    max_retry_count INTEGER NOT NULL DEFAULT 3,
    paused INTEGER NOT NULL DEFAULT 0,
    video_model TEXT,
    qc_review_floor REAL,
    qc_reject_floor REAL DEFAULT 0.5,
    video_audio INTEGER NOT NULL DEFAULT 0,
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
    external_id TEXT,
    result_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    project_id INTEGER REFERENCES projects(id),
    kind TEXT NOT NULL CHECK (kind IN ('image','video','audio')),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    tier TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    at TEXT NOT NULL
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


def _migrate_usage_events(conn: sqlite3.Connection) -> None:
    """Older databases: usage_events had a required job_id and no audio kind. Rebuild it once (keeps rows)."""
    if "project_id" in {r["name"] for r in conn.execute("PRAGMA table_info(usage_events)")}:
        return
    conn.executescript("""
        ALTER TABLE usage_events RENAME TO usage_events_old;
        CREATE TABLE usage_events (
            id INTEGER PRIMARY KEY,
            job_id INTEGER REFERENCES jobs(id),
            project_id INTEGER REFERENCES projects(id),
            kind TEXT NOT NULL CHECK (kind IN ('image','video','audio')),
            provider TEXT NOT NULL, model TEXT NOT NULL, tier TEXT NOT NULL,
            quantity REAL NOT NULL, unit TEXT NOT NULL, at TEXT NOT NULL);
        INSERT INTO usage_events (id, job_id, project_id, kind, provider, model, tier, quantity, unit, at)
            SELECT e.id, e.job_id, j.project_id, e.kind, e.provider, e.model, e.tier, e.quantity, e.unit, e.at
            FROM usage_events_old e LEFT JOIN jobs j ON j.id = e.job_id;
        DROP TABLE usage_events_old;
    """)
    conn.commit()


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(projects)")}
    if "paused" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN paused INTEGER NOT NULL DEFAULT 0")
    if "video_model" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN video_model TEXT")
    if "qc_review_floor" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN qc_review_floor REAL")
    if "video_audio" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN video_audio INTEGER NOT NULL DEFAULT 0")
    if "qc_reject_floor" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN qc_reject_floor REAL DEFAULT 0.5")
    _migrate_usage_events(conn)
    job_cols = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}
    for col in ("external_id", "result_path"):
        if col not in job_cols:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")
    return conn
