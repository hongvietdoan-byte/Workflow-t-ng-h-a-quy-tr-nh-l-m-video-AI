import os
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
    outfit_image_ids TEXT,             -- asset_images ids of the outfit worn in this video (face/hair still from the ref pictures)
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
    kind TEXT NOT NULL CHECK (kind IN ('image','video','audio','llm')),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    tier TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    project_id INTEGER,
    stage TEXT,
    model TEXT,
    sources TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_write_tokens INTEGER
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
CREATE TABLE IF NOT EXISTS end_frames (
    id INTEGER PRIMARY KEY,            -- K1: the picture a shot must END on (core/end_frames.py); not a job, so no query that reads
    project_id INTEGER NOT NULL REFERENCES projects(id),   -- approved image_gen jobs as start pictures can pick it up by mistake
    scene_id INTEGER NOT NULL REFERENCES scenes(id),
    start_job_id INTEGER,              -- the approved start picture it was drawn from (a new start picture makes it outdated)
    state TEXT NOT NULL,               -- queued / running / ready / rejected / failed
    external_id TEXT,
    path TEXT,
    prompt TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
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
-- a resource the person removed from a project: never attached again automatically (assets.auto_attach)
CREATE TABLE IF NOT EXISTS project_assets_declined (
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
CREATE TABLE IF NOT EXISTS outputs (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('final','subtitle','endcard','ailabel','export')),
    path TEXT NOT NULL,
    parent_id INTEGER REFERENCES outputs(id),
    manifest TEXT NOT NULL,            -- what it was made from (clip job ids + file times, settings hash, ...) -> '⚠ cũ' check
    created_at TEXT NOT NULL,
    created_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_outputs_project ON outputs(project_id, kind, id);
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,              -- small settings of the whole app (v3: 'budget' = the test spending limit, core.budget)
    value TEXT
);
CREATE TABLE IF NOT EXISTS story_scenes (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    idx INTEGER NOT NULL,              -- the script's own scene number (kế hoạch v3: a scene becomes several shot rows in `scenes`)
    heading TEXT,
    text TEXT,
    data TEXT,                         -- Director fields of the whole scene (location, mood, sequence, ...)
    UNIQUE (project_id, idx)
);
CREATE TABLE IF NOT EXISTS style_presets (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    data TEXT NOT NULL,                -- a saved World Bible, reusable by other projects
    created_at TEXT NOT NULL,
    created_by TEXT
);
CREATE TABLE IF NOT EXISTS project_watchers (
    project_id INTEGER NOT NULL,       -- core/access.py: người được chủ dự án / Owner cho theo dõi dự án này
    email TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('view','edit')),   -- 'view' = chỉ xem, 'edit' = xem + sửa / gửi job / duyệt
    added_by TEXT,
    added_at TEXT NOT NULL,
    PRIMARY KEY (project_id, email)
);
CREATE INDEX IF NOT EXISTS idx_watchers_email ON project_watchers(email);
CREATE TABLE IF NOT EXISTS content_moderation_failures (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    provider TEXT NOT NULL,
    error_message TEXT NOT NULL,
    at TEXT NOT NULL
);
"""


def _migrate_usage_events(conn: sqlite3.Connection) -> None:
    """Older databases: usage_events had a required job_id, no audio kind, then no 'llm' kind (Claude API tokens, 2026-09-24).
    Rebuild it once (keeps rows)."""
    has_project = "project_id" in {r["name"] for r in conn.execute("PRAGMA table_info(usage_events)")}
    sql = (conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='usage_events'").fetchone() or [""])[0] or ""
    if has_project and "'llm'" in sql:
        return
    project = "e.project_id" if has_project else "j.project_id"
    conn.executescript(f"""
        ALTER TABLE usage_events RENAME TO usage_events_old;
        CREATE TABLE usage_events (
            id INTEGER PRIMARY KEY,
            job_id INTEGER REFERENCES jobs(id),
            project_id INTEGER REFERENCES projects(id),
            kind TEXT NOT NULL CHECK (kind IN ('image','video','audio','llm')),
            provider TEXT NOT NULL, model TEXT NOT NULL, tier TEXT NOT NULL,
            quantity REAL NOT NULL, unit TEXT NOT NULL, at TEXT NOT NULL);
        INSERT INTO usage_events (id, job_id, project_id, kind, provider, model, tier, quantity, unit, at)
            SELECT e.id, e.job_id, {project}, e.kind, e.provider, e.model, e.tier, e.quantity, e.unit, e.at
            FROM usage_events_old e LEFT JOIN jobs j ON j.id = e.job_id;
        DROP TABLE usage_events_old;
    """)
    conn.commit()


def _migrate_outputs(conn: sqlite3.Connection) -> None:
    """S0.14 T6 (2026-09-29): outputs.kind gains 'ailabel' (the "nội dung có dùng AI" layer). SQLite cannot change a CHECK, so the
    table is rebuilt once (rows and ids kept; foreign keys off while the self-referencing parent_id rows move)."""
    sql = (conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='outputs'").fetchone() or [""])[0] or ""
    if not sql or "'ailabel'" in sql:
        return
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.executescript("""
            ALTER TABLE outputs RENAME TO outputs_old;
            CREATE TABLE outputs (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                kind TEXT NOT NULL CHECK (kind IN ('final','subtitle','endcard','ailabel','export')),
                path TEXT NOT NULL,
                parent_id INTEGER REFERENCES outputs(id),
                manifest TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT);
            INSERT INTO outputs (id, project_id, kind, path, parent_id, manifest, created_at, created_by)
                SELECT id, project_id, kind, path, parent_id, manifest, created_at, created_by FROM outputs_old;
            DROP TABLE outputs_old;
            CREATE INDEX IF NOT EXISTS idx_outputs_project ON outputs(project_id, kind, id);
        """)
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=60)     # many background threads write: wait for the lock instead of failing
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")   # readers (the dashboard) no longer block writers and vice versa
        conn.execute("PRAGMA synchronous = NORMAL")
    # The schema + column checks below ran on every dashboard click. Now once per process and database file: skipped only when
    # the file carries the stamp of THIS code (`PRAGMA user_version`; any change to the schema/migration code changes it) AND its
    # schema has not changed since this process migrated it (`PRAGMA schema_version`, bumped by every CREATE/ALTER/DROP). A fresh,
    # older, recreated or hand-altered database is migrated as before.
    stamp = schema_stamp()
    key = None if path == ":memory:" else os.path.normcase(os.path.abspath(path))
    if stamp and key is not None and key in _MIGRATED:
        user_version, schema_version = (conn.execute("PRAGMA user_version").fetchone()[0],
                                        conn.execute("PRAGMA schema_version").fetchone()[0])
        if user_version == stamp and schema_version == _MIGRATED[key]:
            return conn
    _migrate(conn)
    if stamp:
        conn.execute(f"PRAGMA user_version = {int(stamp)}")
        conn.commit()
        if key is not None:
            _MIGRATED[key] = conn.execute("PRAGMA schema_version").fetchone()[0]
    return conn


_STAMP = []
_MIGRATED = {}          # database file -> its schema_version right after this process migrated it


def schema_stamp() -> int:
    """A number (1..2^31-1) that changes whenever SCHEMA, V2_COLUMNS or a migration function changes; 0 = cannot tell (then
    every connect migrates, the old behaviour)."""
    if not _STAMP:
        import hashlib
        import inspect
        try:
            from .budget_rounds import TABLE as rounds_table          # S14.6: the rounds table is created in _migrate too
            src = SCHEMA + repr(V2_COLUMNS) + rounds_table + "".join(inspect.getsource(f) for f in (_migrate, _migrate_v2, _migrate_usage_events,
                                                                                       _migrate_outputs))
            _STAMP.append(int(hashlib.sha1(src.encode("utf-8")).hexdigest()[:7], 16) or 1)
        except (OSError, TypeError):
            _STAMP.append(0)
    return _STAMP[0]


def _migrate(conn: sqlite3.Connection) -> None:
    """Create missing tables and add missing columns (idempotent)."""
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
    if "outfit_image_ids" not in char_cols:
        conn.execute("ALTER TABLE characters ADD COLUMN outfit_image_ids TEXT")
    if "video_audio" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN video_audio INTEGER NOT NULL DEFAULT 0")
    if "qc_reject_floor" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN qc_reject_floor REAL DEFAULT 0.5")
    _migrate_usage_events(conn)
    _migrate_outputs(conn)
    # S13.10: every ⌂ card / money bar reads usage_events per project (core.project_budget, core.cost) — without this it is a full scan per project
    conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_project ON usage_events(project_id, kind)")
    # S14.6 Gói K: 💵 mức dùng theo ngày / theo đợt đọc sổ chi theo thời gian; đợt ngân sách có lịch sử (core.budget_rounds)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_at ON usage_events(at)")
    from .budget_rounds import TABLE as _ROUNDS
    conn.execute(_ROUNDS)
    # 02/10: the library's per-entry reads (pictures of one entry, "has an approved picture") were full scans of asset_images — with 10× the
    # library the Dashboard's library screens took seconds
    conn.execute("CREATE INDEX IF NOT EXISTS idx_asset_images_asset ON asset_images(asset_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_game_kind ON assets(game, kind)")
    job_cols ={r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}
    for col in ("external_id", "result_path", "created_by", "origin"):     # origin 'auto' = made by the machine (S14.16 job cap)
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
    if "archived" not in cols:          # 📦 Cất dự án (2026-09-26): hidden from the picker and the autopilot, data kept
        conn.execute("ALTER TABLE projects ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
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
    _migrate_v2(conn)


V2_COLUMNS = {
    # NULL everywhere = the v1 behaviour (a database made before v2 keeps working unchanged)
    "projects": (("aspect", "TEXT"), ("genre", "TEXT"), ("genre_locked", "INTEGER NOT NULL DEFAULT 0"),
                 ("model_priority", "TEXT"), ("render_settings", "TEXT"), ("qc_policy", "TEXT"),
                 ("qc_video", "INTEGER NOT NULL DEFAULT 1"), ("autopilot_gates", "TEXT"), ("autopilot_saved_cfg", "TEXT"),
                 ("pilot", "TEXT"),
                 # kế hoạch v3: NULL shot_mode = one clip per script scene (v2); 'per_shot' / 'multishot' = the Director splits
                 # scenes into shots; style_profile = the Free Fire editing style the Director follows (knowledge/ff_styles)
                 ("shot_mode", "TEXT"), ("style_profile", "TEXT"), ("test_quality", "INTEGER NOT NULL DEFAULT 0"),
                 ("director_raw", "TEXT"),            # the last paid Director answer, kept even when saving it failed
                 ("director_intent_raw", "TEXT"),     # GĐ5 two-pass Director: Tầng A answer + every Tầng B scene answer (paid, kept)
                 ("look", "TEXT"),                    # ANIME | FF_INGAME (core/looks.py): the picture look, apart from the editing style
                 ("image_model", "TEXT"),             # Deepix picture model of the project (core/image_models.py); NULL = default
                 ("dialogue_trim", "INTEGER NOT NULL DEFAULT 0")),   # 1 = the Director may drop lines (never add / reword)
    "characters": (("lock_rules", "TEXT"), ("voice_profile", "TEXT"), ("anchor_approved", "INTEGER NOT NULL DEFAULT 0"),
                   ("user_edited", "TEXT"),
                   ("bible_check", "TEXT")),         # F1: {key: sha of pictures + description, ok, mismatches, fixed_description}         # fields the person edited by hand (description, wardrobe): the Director keeps them
    "jobs": (("input_hash", "TEXT"), ("source_job_id", "INTEGER"), ("model", "TEXT"),
             ("group_leader", "INTEGER"),
             ("task_seen", "INTEGER NOT NULL DEFAULT 0"), ("task_unseen", "INTEGER NOT NULL DEFAULT 0"),
             ("sent_refs", "TEXT"),    # K7: which pictures (whose, what role) went with the request
             ("sent_group", "TEXT")),  # M10: the Kling multi-shot group exactly as sent (split the clip by it, not by today's plan)   # W12: provider list checks     # v3 Kling multi-shot: the job that makes this shot's clip together with its group
    # G1/G2 (docs/KE_HOACH_TONG_2026-09-24.md): what a library picture shows, for which look, and whether a person approved it
    "assets": (("profile", "TEXT"),),        # T1: the character's standard profile, approved once, inherited by every project
    "asset_images": (("role", "TEXT"), ("look", "TEXT"), ("variant", "TEXT"), ("status", "TEXT NOT NULL DEFAULT 'approved'"),
                     ("removed_at", "TEXT"),      # S14.4: when the picture went to the library trash (status 'removed'); emptied after 30 days
                     ("removed_from", "TEXT")),   # the status it had before, given back by assets.restore_image
    "usage_events": (("deleted_project_id", "INTEGER"),
                     ("stage", "TEXT")),                      # what a Claude call was for (director, qc, motion, asset_vision…)        # spend of a deleted project stays readable (its id is never reused)
    "motion_prompts": (("image_job_id", "INTEGER"), ("spec_hash", "TEXT"), ("video_model", "TEXT"), ("check_flags", "TEXT"),
                       ("lint", "TEXT")),
    "end_frames": (("sent_refs", "TEXT"),   # which pictures went with the end frame request (like jobs.sent_refs)
                   ("fix", "TEXT")),        # the person's English fix of a redo (luật 6: a redo changes the input)
}


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """Dashboard v2 columns. The first time `jobs.source_job_id` appears, finished videos are linked to the image they were made
    from (the approved image of the scene created before the video), so a later image change shows the video as outdated."""
    backfill = False
    for table, columns in V2_COLUMNS.items():
        have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if not have:
            continue                     # the table is not in this database (a partial test schema)
        for col, ddl in columns:
            if col not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                backfill = backfill or (table, col) == ("jobs", "source_job_id")
    if backfill:
        conn.execute(
            "UPDATE jobs SET source_job_id=(SELECT MAX(i.id) FROM jobs i JOIN review_log r ON r.job_id=i.id AND r.decision='approve'"
            " WHERE i.scene_id=jobs.scene_id AND i.type='image_gen' AND i.id<jobs.id) WHERE type='video_gen'")
    conn.commit()
