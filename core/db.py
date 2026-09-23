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
    game TEXT NOT NULL DEFAULT 'FF',
    use_subjects INTEGER NOT NULL DEFAULT 0,
    storyboard_mode INTEGER NOT NULL DEFAULT 0,
    qc_autofix INTEGER NOT NULL DEFAULT 1,
    script_text TEXT,
    world_bible TEXT,
    sub_settings TEXT,
    music_mode TEXT,
    autopilot_state TEXT,
    autopilot_note TEXT,
    autopilot_beat REAL,
    autopilot_log TEXT,
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
    subject_asset_id TEXT,
    subject_asset_uri TEXT,
    subject_status TEXT,
    subject_name TEXT,
    ref_asset_id INTEGER,
    ref_image_id INTEGER,
    ref_image_ids TEXT,
    UNIQUE (project_id, name)
);
CREATE TABLE IF NOT EXISTS motion_prompts (
    id INTEGER PRIMARY KEY,
    scene_id INTEGER NOT NULL UNIQUE REFERENCES scenes(id),
    motion_prompt TEXT NOT NULL,
    camera TEXT,
    duration_sec REAL NOT NULL DEFAULT 5,
    negative_prompt TEXT,
    state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','approved')),
    ref_video_path TEXT,
    ref_video_type TEXT NOT NULL DEFAULT 'feature' CHECK (ref_video_type IN ('feature','base'))
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
    updated_at TEXT NOT NULL,
    created_by TEXT
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
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    name TEXT,
    role TEXT NOT NULL CHECK (role IN ('owner','admin','member')),
    pw_hash TEXT,
    perms TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    failed INTEGER NOT NULL DEFAULT 0,
    locked_until REAL,
    invite_hash TEXT,
    invite_expires REAL,
    created_at TEXT,
    created_by TEXT,
    last_login TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    email TEXT,
    action TEXT NOT NULL,
    detail TEXT
);
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    game TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    aliases TEXT,
    description TEXT,
    project_id INTEGER,
    created_by TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS ff_articles (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT,
    published INTEGER,
    url TEXT,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS asset_images (
    id INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    label TEXT,
    sort INTEGER,
    src_path TEXT,
    sha256 TEXT,
    src_size INTEGER,
    src_mtime INTEGER
);
CREATE TABLE IF NOT EXISTS set_analyses (
    sha256 TEXT PRIMARY KEY,           -- of the background picture: a re-synced copy of the same picture reuses the reading
    data TEXT NOT NULL,                -- core.layout set analysis (camera, horizon, ground, landmarks...)
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sound_sources (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    ignore TEXT,
    auto INTEGER NOT NULL DEFAULT 1,
    last_sync TEXT,
    last_signature TEXT,
    last_summary TEXT
);
CREATE TABLE IF NOT EXISTS sounds (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL,
    path TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL,
    mood TEXT,
    search TEXT,
    ext TEXT,
    size INTEGER,
    mtime INTEGER,
    duration REAL,
    tags TEXT,
    heard TEXT,
    heard_label TEXT,
    heard_score REAL,
    voice INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sounds_kind ON sounds(kind, category);
CREATE TABLE IF NOT EXISTS asset_sources (
    id INTEGER PRIMARY KEY,
    game TEXT NOT NULL,
    path TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'character',
    ignore TEXT,
    auto INTEGER NOT NULL DEFAULT 1,
    last_sync TEXT,
    last_signature TEXT,
    last_summary TEXT
);
CREATE TABLE IF NOT EXISTS project_assets (
    project_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    PRIMARY KEY (project_id, asset_id)
);
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    ref_id INTEGER NOT NULL,
    at TEXT NOT NULL,
    project_id INTEGER,
    stage TEXT NOT NULL,
    group_name TEXT NOT NULL,
    text TEXT NOT NULL,
    UNIQUE (source, ref_id)
);
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    group_name TEXT NOT NULL,
    key TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    source TEXT NOT NULL,
    evidence TEXT,
    state TEXT NOT NULL DEFAULT 'proposed',
    decided_at TEXT
);
CREATE TABLE IF NOT EXISTS learning_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diag_events (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    last_at TEXT NOT NULL,
    stage TEXT NOT NULL,
    severity TEXT NOT NULL,
    code TEXT,
    message TEXT NOT NULL,
    project_id INTEGER,
    scene_id INTEGER,
    job_id INTEGER,
    count INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_diag_last ON diag_events(last_at);
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
    conn = sqlite3.connect(path, timeout=60)     # many background threads write: wait for the lock instead of failing
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")   # readers (the dashboard) no longer block writers and vice versa
        conn.execute("PRAGMA synchronous = NORMAL")
    conn.executescript(SCHEMA)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(projects)")}
    if "paused" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN paused INTEGER NOT NULL DEFAULT 0")
    if "video_model" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN video_model TEXT")
    if "qc_review_floor" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN qc_review_floor REAL")
    for col, typ in (("autopilot_state", "TEXT"), ("autopilot_note", "TEXT"), ("autopilot_beat", "REAL"),
                     ("autopilot_log", "TEXT")):
        if col not in cols:
            conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {typ}")
    if "script_text" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN script_text TEXT")
    if "game" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN game TEXT NOT NULL DEFAULT 'FF'")
    if "qc_autofix" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN qc_autofix INTEGER NOT NULL DEFAULT 1")
    if "use_subjects" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN use_subjects INTEGER NOT NULL DEFAULT 0")
    char_cols = {r["name"] for r in conn.execute("PRAGMA table_info(characters)")}
    for col in ("subject_asset_id", "subject_asset_uri", "subject_status", "subject_name"):
        if col not in char_cols:
            conn.execute(f"ALTER TABLE characters ADD COLUMN {col} TEXT")
    for col in ("ref_asset_id", "ref_image_id"):
        if col not in char_cols:
            conn.execute(f"ALTER TABLE characters ADD COLUMN {col} INTEGER")
    if "ref_image_ids" not in char_cols:
        conn.execute("ALTER TABLE characters ADD COLUMN ref_image_ids TEXT")
    if "video_audio" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN video_audio INTEGER NOT NULL DEFAULT 0")
    if "qc_reject_floor" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN qc_reject_floor REAL DEFAULT 0.5")
    _migrate_usage_events(conn)
    job_cols = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}
    for col in ("external_id", "result_path", "created_by"):
        if col not in job_cols:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")
    user_cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
    if "perms" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN perms TEXT")
    img_cols = {r["name"] for r in conn.execute("PRAGMA table_info(asset_images)")}
    for col, typ in (("src_path", "TEXT"), ("sha256", "TEXT"), ("src_size", "INTEGER"), ("src_mtime", "INTEGER")):
        if col not in img_cols:
            conn.execute(f"ALTER TABLE asset_images ADD COLUMN {col} {typ}")
    if "music_mode" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN music_mode TEXT")
    if "sub_settings" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN sub_settings TEXT")
    if "world_bible" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN world_bible TEXT")
    if "autopilot_user" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN autopilot_user TEXT")
    if "created_by" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN created_by TEXT")
    sound_cols = {r["name"] for r in conn.execute("PRAGMA table_info(sounds)")}
    for column, ddl in (("tags", "TEXT"), ("heard", "TEXT"), ("heard_label", "TEXT"), ("heard_score", "REAL"), ("voice", "INTEGER NOT NULL DEFAULT 0")):
        if column not in sound_cols:
            conn.execute(f"ALTER TABLE sounds ADD COLUMN {column} {ddl}")
    if "storyboard_mode" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN storyboard_mode INTEGER NOT NULL DEFAULT 0")
    mp_cols = {r["name"] for r in conn.execute("PRAGMA table_info(motion_prompts)")}
    if "ref_video_path" not in mp_cols:
        conn.execute("ALTER TABLE motion_prompts ADD COLUMN ref_video_path TEXT")
    if "ref_video_type" not in mp_cols:
        conn.execute("ALTER TABLE motion_prompts ADD COLUMN ref_video_type TEXT NOT NULL DEFAULT 'feature'")
    return conn
