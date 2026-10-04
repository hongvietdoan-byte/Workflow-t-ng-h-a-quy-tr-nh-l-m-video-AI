"""What a project carries over and what goes stale (kế hoạch sau #8, S3.8).

1. A place changed after the Director planned: #8's tower description / pictures were changed after the shot plan, and the plan kept
   the old tower. The places attached when the Director answered are fingerprinted into its answer (`places_at_plan`); Step 1 names the
   scenes at a place whose text or pictures changed since, next to "↻ Chia shot lại cảnh này" (a paid re-plan stays the person's click).
2. A new project starts from the way of working already settled in the person's latest project (shot mode, look, reference styles,
   picture model, render settings) instead of the factory defaults (#8 was set up by hand again)."""
import hashlib
import json
from typing import Dict, List

INHERIT = ("shot_mode", "look", "style_profile", "image_model", "render_settings", "qc_policy")


def places_fingerprint(conn, project_id: int) -> Dict[str, str]:
    """{asset id: hash of its text + picture files} of the places attached to the project."""
    out = {}
    for a in conn.execute("SELECT a.id, a.name, a.description, a.profile FROM assets a JOIN project_assets pa ON pa.asset_id=a.id "
                          "WHERE pa.project_id=? AND a.kind='location'", (project_id,)).fetchall():
        pics = [r[0] for r in conn.execute("SELECT path FROM asset_images WHERE asset_id=? AND status IS NOT 'removed'"   # S14.4: Kho trash = gone
                                                 " ORDER BY id", (a["id"],)).fetchall()] \
            if _has_table(conn, "asset_images") else []
        key = json.dumps([a["name"], a["description"], a["profile"], pics], ensure_ascii=False, sort_keys=True)
        out[str(a["id"])] = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return out


def _has_table(conn, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def changed_places(conn, project_id: int) -> List[Dict]:
    """Places whose text / pictures changed (or that were attached / removed) since the Director's plan, with the shots set there.
    [] when the plan has no fingerprint (older plans) or nothing changed."""
    row = conn.execute("SELECT director_raw FROM projects WHERE id=?", (project_id,)).fetchone()
    try:
        then = json.loads((row["director_raw"] if row else None) or "{}").get("places_at_plan")
    except ValueError:
        then = None
    if not isinstance(then, dict):
        return []
    now = places_fingerprint(conn, project_id)
    out = []
    for aid in sorted(set(then) | set(now)):
        if then.get(aid) == now.get(aid):
            continue
        a = conn.execute("SELECT name FROM assets WHERE id=?", (int(aid),)).fetchone()
        name = a["name"] if a else f"#{aid}"
        what = "mới gắn" if aid not in then else ("đã gỡ" if aid not in now else "đổi mô tả / ảnh")
        scenes = sorted({json.loads(r["data"] or "{}").get("story_scene") or r["idx"]
                         for r in conn.execute("SELECT idx, data FROM scenes WHERE project_id=?", (project_id,)).fetchall()
                         if name.lower() in str(json.loads(r["data"] or "{}").get("location") or "").lower()})
        out.append({"asset_id": int(aid), "name": name, "what": what, "scenes": scenes})
    return out


def inherit(conn, new_pid: int, created_by: str) -> List[str]:
    """Copy the settled way of working from the creator's latest other project (not archived) into a new project. Returns the fields
    copied (said on the page). Nothing is copied that the new project already set."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(projects)")}
    fields = [f for f in INHERIT if f in cols]
    if not fields or not created_by:
        return []
    arch = " AND COALESCE(archived,0)=0" if "archived" in cols else ""
    src = conn.execute(f"SELECT {', '.join(fields)} FROM projects WHERE created_by=? AND id<>?{arch} ORDER BY id DESC LIMIT 1",
                       (created_by, new_pid)).fetchone()
    if src is None:
        return []
    cur = conn.execute(f"SELECT {', '.join(fields)} FROM projects WHERE id=?", (new_pid,)).fetchone()
    copied = []
    for f in fields:
        if src[f] not in (None, "") and cur[f] in (None, ""):
            conn.execute(f"UPDATE projects SET {f}=? WHERE id=?", (src[f], new_pid))
            copied.append(f)
    conn.commit()
    return copied
