"""Meshy: character pictures → a textured 3D model → a rig, saved on this computer (user 01/10: Pro plan, API; the 3D model fixes which
side every asymmetric detail is on, so renders of any direction can be the reference a back / side shot needs — QC GĐ3 showed Claude
cannot tell left from right in a picture).

Official docs (read 01/10): base https://api.meshy.ai/openapi/v1, `Authorization: Bearer <MESHY_API_KEY>` (kept in the user's
environment, never in a file or the chat); POST /multi-image-to-3d (1–4 views of ONE object, the first is the front), GET …/:id until
SUCCEEDED, download `model_urls`; POST /rigging (textured humanoid, input_task_id); GET /balance. Files are kept 3 days by Meshy (non-
Enterprise) → downloaded at once. Pro: 20 requests/s, 10 tasks at a time (429 beyond). Failed tasks give the credits back.
Credits (pricing page): image / multi-image → 3D with texture 30, rigging 5.

Money (docs/CHUAN_XAY_DUNG.md): every task is written to `meshy_tasks` BEFORE it is sent (credits estimated), the credits Meshy reports
replace the estimate; refused before sending when: one call > MAX_CALL_CREDITS, the character already has MAX_TRIES_PER_CHARACTER models
(1 + 2 redo — luật 6), the round's total would pass the cap the person set (USD, app_settings 'meshy'), or the account balance is short.
A send whose answer was lost (network) is kept as UNKNOWN and counted, never silently re-sent.

  plan(conn, asset_id)            the views to send (cut from the approved sheet's turnaround, else the approved front picture), the
                                  texture sentence from the approved profile, credits / USD, the problems that stop it
  submit_model / submit_rig       one paid call each, after the checks
  refresh(conn, client)           poll the open tasks, download what finished into data/models3d/<NAME>_<asset>/<task>/
  views_to_library(conn, task)    Meshy's front / right / back / left renders → the library's review box (roles full_body / side / back)
"""
import base64
import io
import json
import os
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

BASE = "https://api.meshy.ai/openapi/v1"
CREDITS = {"model": 30, "rig": 5}
MAX_CALL_CREDITS = 40
MAX_TRIES_PER_CHARACTER = 3
RETENTION_DAYS = 3
SETTINGS_KEY = "meshy"
DEFAULT_CAP_USD = 150.0              # user 01/10: "trần 150$ cho 3 nhân vật"
VIEW_EDGE = 1536                     # longest side of a view sent (a sheet crop is smaller and stays as is)
OPEN = ("SENDING", "PENDING", "IN_PROGRESS", "SUCCEEDED")
TEXTURE_PROMPT_MAX = 800

TABLE = """
CREATE TABLE IF NOT EXISTS meshy_tasks (
    id INTEGER PRIMARY KEY,
    task_id TEXT,
    kind TEXT NOT NULL,                  -- model / rig
    asset_id INTEGER NOT NULL,
    parent_task TEXT,                    -- the model a rig was made from
    status TEXT NOT NULL,                -- SENDING / PENDING / IN_PROGRESS / SUCCEEDED / DOWNLOADED / FAILED / CANCELED / UNKNOWN
    credits_est REAL NOT NULL,
    credits REAL,                        -- what Meshy reported (0 for a failed task)
    request TEXT,                        -- what was asked, without the pictures' bytes
    folder TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)"""


class MeshyError(Exception):
    """A message that can be shown to the person (never contains the key)."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_table(conn) -> None:
    conn.execute(TABLE)
    conn.commit()


def usd_per_credit() -> float:
    """Pro is a monthly credit plan; the USD value of one credit is the person's to set (MESHY_USD_PER_CREDIT), 0.02 = $20 / 1 000."""
    try:
        return float(os.environ.get("MESHY_USD_PER_CREDIT", "0.02"))
    except ValueError:
        return 0.02


def settings(conn) -> Dict:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (SETTINGS_KEY,)).fetchone()
    try:
        saved = json.loads(row[0]) if row else {}
    except ValueError:
        saved = {}
    return {"cap_usd": DEFAULT_CAP_USD, **saved}


def save_settings(conn, **fields) -> Dict:
    data = {**settings(conn), **fields}
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (SETTINGS_KEY, json.dumps(data)))
    conn.commit()
    return data


def _credits_of(row) -> float:
    if row["status"] in ("FAILED", "CANCELED"):
        return float(row["credits"] or 0)
    return float(row["credits"] if row["credits"] is not None else row["credits_est"])


def spent_credits(conn, asset_id: Optional[int] = None) -> float:
    ensure_table(conn)
    sql, args = "SELECT * FROM meshy_tasks", ()
    if asset_id is not None:
        sql, args = sql + " WHERE asset_id=?", (asset_id,)
    return round(sum(_credits_of(r) for r in conn.execute(sql, args).fetchall()), 2)


def tries(conn, asset_id: int) -> int:
    ensure_table(conn)
    return conn.execute("SELECT COUNT(*) FROM meshy_tasks WHERE asset_id=? AND kind='model' AND status NOT IN ('FAILED','CANCELED')",
                        (asset_id,)).fetchone()[0]


def check(conn, asset_id: int, kind: str, credits: float, balance: Optional[float]) -> Optional[str]:
    """Why this call may not be sent, or None."""
    if credits > MAX_CALL_CREDITS:
        return f"một lần gọi ước {credits:g} credit > trần mỗi lần {MAX_CALL_CREDITS}"
    if kind == "model" and tries(conn, asset_id) >= MAX_TRIES_PER_CHARACTER:
        return (f"nhân vật này đã có {MAX_TRIES_PER_CHARACTER} lần dựng 3D (1 + 2 làm lại) — đổi đầu vào / sửa ảnh trước, người nâng trần "
                "mới được thử thêm")
    cap_usd = float(settings(conn)["cap_usd"])
    after = (spent_credits(conn) + credits) * usd_per_credit()
    if after > cap_usd + 1e-9:
        return f"vượt trần Meshy của đợt: đã dùng + lần này ≈ ${after:.2f} > ${cap_usd:.2f}"
    if balance is None:
        return "không đọc được số credit còn trong tài khoản Meshy — không gửi khi chưa biết còn đủ"
    if balance < credits:
        return f"tài khoản Meshy còn {balance:g} credit < {credits:g} cần cho lần này"
    return None


# ---- the inputs ---------------------------------------------------------------------------------------------------------------------
def texture_prompt(name: str, profile: Dict) -> str:
    """The approved profile, said to the texturer: what must stay, with every LEFT / RIGHT detail as written (the views show them)."""
    text = (f"Free Fire in-game 3D character {name}, realistic game render, no outlines. "
            f"Keep exactly: {profile.get('must_keep') or profile.get('identity') or ''}")
    if profile.get("forbidden"):
        text += f". Never: {profile['forbidden']}"
    return text[:TEXTURE_PROMPT_MAX]


def _images(conn, asset_id: int) -> List[Dict]:
    return [dict(r) for r in conn.execute("SELECT id, path, role, status, variant FROM asset_images WHERE asset_id=? ORDER BY id",
                                          (asset_id,)).fetchall()]


FRONT_ROLES = ("full_body", "front_standard")


def library_views(imgs: List[Dict]) -> tuple:
    """(views, source) from APPROVED library pictures of one batch (same `variant`, e.g. the in-game screenshots of 01/10): a front
    (full body) + at least one side or back, ordered front · side · back · other side (Meshy: the first is the front, ≤ 4). ([], None)
    when no batch has that."""
    from PIL import Image
    from . import assets
    groups: Dict[str, List[Dict]] = {}
    for i in imgs:
        if i["status"] == "approved" and i["role"] in FRONT_ROLES + ("side", "back"):
            groups.setdefault(i.get("variant") or "", []).append(i)
    best = None
    for variant, items in groups.items():
        fronts = sorted((i for i in items if i["role"] in FRONT_ROLES), key=lambda i: FRONT_ROLES.index(i["role"]))
        sides = [i for i in items if i["role"] == "side"]
        backs = [i for i in items if i["role"] == "back"]
        if not fronts or not (sides or backs):
            continue
        chosen = [fronts[0]] + sides[:1] + backs[:1] + sides[1:2]
        if best is None or len(chosen) > len(best[1]):
            best = (variant, chosen)
    if best is None:
        return [], None
    names = {"side": "side", "back": "back"}
    views = [{"view": "front" if k == 0 else names.get(i["role"], i["role"]), "box": None, "image_id": i["id"],
              "image": Image.open(assets.resolve(i["path"])).convert("RGB")} for k, i in enumerate(best[1][:4])]
    return views, f"{len(views)} ảnh Kho đã duyệt ({best[0] or 'không ghi nguồn'}: #{', #'.join(str(v['image_id']) for v in views)})"


def plan(conn, asset_id: int, sheet_image_id: Optional[int] = None, work_dir: Optional[str] = None,
         texture_override: Optional[str] = None) -> Dict:
    """What would be sent for this character and why it may not be. The views, in this order: approved library pictures of several
    sides from one batch (in-game screenshots), else cut from an approved design sheet (or the sheet the person picked), else the
    approved front picture alone (Meshy then guesses the back). `texture_override`: the person's own texture sentence (a skin the
    profile does not describe, e.g. Wolfrahh in white) — then an unapproved / missing profile no longer stops it."""
    from . import assets, sheet_views
    a = conn.execute("SELECT id, name FROM assets WHERE id=?", (asset_id,)).fetchone()
    if a is None:
        raise MeshyError(f"không có tài nguyên #{asset_id}")
    prof = assets.get_profile(conn, asset_id)
    problems = []
    override = (texture_override or "").strip()[:TEXTURE_PROMPT_MAX]
    if not prof.get("approved") and not override:
        problems.append("hồ sơ chuẩn của nhân vật chưa được duyệt — câu texture lấy từ hồ sơ (hoặc tự viết câu texture)")
    imgs = _images(conn, asset_id)
    sheets = [i for i in imgs if i["role"] == "design_sheet" and (i["id"] == sheet_image_id or
                                                                   (sheet_image_id is None and i["status"] == "approved"))]
    views, source = [], None
    if sheet_image_id is None:                          # real in-game views of several sides beat a cut-out of a drawn sheet
        views, source = library_views(imgs)
    for s in sheets if not views else []:
        cut = sheet_views.from_asset_image(assets.resolve(s["path"]))
        if cut:
            views, source = cut, f"bảng #{s['id']} (cắt 4 hướng)"
            break
    if not views:
        front = [i for i in imgs if i["role"] == "front_standard" and i["status"] == "approved"]
        if front:
            from PIL import Image
            p = assets.resolve(front[0]["path"])
            views, source = [{"view": "front", "box": None, "image": Image.open(p).convert("RGB")}], f"ảnh chuẩn #{front[0]['id']} (1 ảnh)"
        else:
            problems.append("không có bảng nhiều góc cắt được, cũng không có ảnh chính diện đã duyệt")
    if sheets and source and "1 ảnh" in source:
        problems.append("có bảng nhiều góc nhưng không tự cắt được 4 hướng — cắt tay hoặc vẽ bảng xoay riêng")
    paths = []
    if views and work_dir:
        from . import sheet_views as sv
        paths = sv.save(views, work_dir, f"{a['name']}_{asset_id}")
    credits = CREDITS["model"]
    return {"asset_id": asset_id, "name": a["name"], "source": source, "views": views, "view_paths": paths,
            "texture_prompt": override or texture_prompt(a["name"], prof), "texture_by_person": bool(override), "height_m": prof.get("height_m") or 1.75,
            "credits": credits, "usd": round(credits * usd_per_credit(), 2), "problems": problems}


def data_uri(image) -> str:
    """PNG data URI (Meshy accepts base64 data URIs for .jpg / .png); big pictures are brought down to VIEW_EDGE."""
    img = image.copy()
    if max(img.size) > VIEW_EDGE:
        img.thumbnail((VIEW_EDGE, VIEW_EDGE))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# ---- the client ---------------------------------------------------------------------------------------------------------------------
def api_key() -> Optional[str]:
    key = os.environ.get("MESHY_API_KEY")
    if not key and os.name == "nt":                     # saved with setx after the dashboard was started
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key = winreg.QueryValueEx(k, "MESHY_API_KEY")[0]
        except OSError:
            key = None
    return (key or "").strip() or None


class Client:
    """The Meshy REST API. `transport(method, url, headers, body, timeout) -> HttpResponse` is injectable (tests); the key goes only
    to api.meshy.ai, never to the signed download links."""

    def __init__(self, key: str, transport: Optional[Callable] = None, base: str = BASE):
        from .adapters.http import urllib_transport
        self.key, self.base, self.transport = key, base.rstrip("/"), transport or urllib_transport

    def _call(self, method: str, path: str, body: Optional[Dict] = None, timeout: float = 60) -> Dict:
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        raw = json.dumps(body).encode("utf-8") if body is not None else None
        resp = self.transport(method, self.base + path, headers, raw, timeout)
        try:
            data = json.loads(resp.body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            data = {}
        if resp.status >= 400:
            msg = data.get("message") or data.get("error") or resp.body[:200].decode("utf-8", "replace")
            hint = {401: "mã API sai hoặc đã thu hồi", 402: "hết credit", 429: "quá giới hạn gọi / quá 10 việc cùng lúc"}.get(resp.status, "")
            raise MeshyError(f"Meshy {resp.status}{' — ' + hint if hint else ''}: {msg}")
        return data

    def balance(self) -> float:
        return float(self._call("GET", "/balance").get("balance"))

    def create_model(self, views: List[str], texture_prompt: str, pose_mode: str = "a-pose") -> tuple:
        """(task id, endpoint): one view → /image-to-3d, 2–4 → /multi-image-to-3d (the first is the front)."""
        body = {"ai_model": "latest", "pose_mode": pose_mode, "should_texture": True, "enable_pbr": False,
                "texture_prompt": texture_prompt}
        if len(views) == 1:
            path, body["image_url"] = "/image-to-3d", views[0]
        else:
            path, body["image_urls"] = "/multi-image-to-3d", views[:4]
        return str(self._call("POST", path, body, timeout=180)["result"]), path

    def create_rig(self, input_task_id: str, height_m: float) -> str:
        return str(self._call("POST", "/rigging", {"input_task_id": input_task_id, "height_meters": float(height_m)})["result"])

    def get(self, endpoint: str, task_id: str) -> Dict:
        return self._call("GET", f"{endpoint}/{task_id}")

    def download(self, url: str) -> bytes:
        resp = self.transport("GET", url, {}, None, 300)               # signed link: no key
        if resp.status >= 400:
            raise MeshyError(f"tải file lỗi {resp.status}")
        return resp.body


def meshy_client(transport=None) -> Optional[Client]:
    key = api_key()
    return Client(key, transport) if key else None


# ---- the ledger + the calls ----------------------------------------------------------------------------------------------------------
def _insert(conn, kind: str, asset_id: int, credits: float, request: Dict, parent: Optional[str] = None) -> int:
    ensure_table(conn)
    cur = conn.execute("INSERT INTO meshy_tasks (kind, asset_id, parent_task, status, credits_est, request, created_at, updated_at)"
                       " VALUES (?,?,?,?,?,?,?,?)", (kind, asset_id, parent, "SENDING", credits,
                                                     json.dumps(request, ensure_ascii=False), _now(), _now()))
    conn.commit()
    return cur.lastrowid


def _update(conn, row_id: int, **fields) -> None:
    fields["updated_at"] = _now()
    conn.execute(f"UPDATE meshy_tasks SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), row_id))
    conn.commit()


def _send(conn, row_id: int, send: Callable[[], str]) -> str:
    from .providers import ProviderError
    try:
        task_id = send()
    except ProviderError as e:                                          # network: Meshy may have made it — counted, not re-sent
        _update(conn, row_id, status="UNKNOWN", error=f"mất kết nối khi gửi ({e}); kiểm trên meshy.ai rồi ghi tay")
        raise MeshyError("mất kết nối khi gửi — có thể Meshy vẫn nhận việc; đã ghi 'UNKNOWN' và tính tiền, không tự gửi lại") from None
    except MeshyError as e:
        _update(conn, row_id, status="FAILED", credits=0, error=str(e))
        raise
    _update(conn, row_id, task_id=task_id, status="PENDING")
    return task_id


def submit_model(conn, client: Client, p: Dict, view_ids: Optional[List[int]] = None) -> Dict:
    """One paid call: the plan's views (or the chosen subset, by index) → 3D. Checks first; the row is written before sending."""
    if p["problems"]:
        raise MeshyError("chưa gửi được: " + "; ".join(p["problems"]))
    views = [v for k, v in enumerate(p["views"]) if view_ids is None or k in view_ids]
    if not views:
        raise MeshyError("không có ảnh nào để gửi")
    try:
        bal = client.balance()
    except MeshyError:
        bal = None
    why = check(conn, p["asset_id"], "model", p["credits"], bal)
    if why:
        raise MeshyError(why)
    req = {"source": p["source"], "views": [v["view"] for v in views], "boxes": [v.get("box") for v in views],
           "texture_prompt": p["texture_prompt"], "pose_mode": "a-pose"}
    row = _insert(conn, "model", p["asset_id"], p["credits"], req)
    endpoint = {}

    def send():
        task_id, path = client.create_model([data_uri(v["image"]) for v in views], p["texture_prompt"])
        endpoint["path"] = path
        return task_id
    task_id = _send(conn, row, send)
    req["endpoint"] = endpoint["path"]
    _update(conn, row, request=json.dumps(req, ensure_ascii=False))
    return {"row": row, "task_id": task_id}


def submit_rig(conn, client: Client, model_row: int) -> Dict:
    m = conn.execute("SELECT * FROM meshy_tasks WHERE id=?", (model_row,)).fetchone()
    if m is None or m["kind"] != "model" or m["status"] != "DOWNLOADED":
        raise MeshyError("chỉ gắn khung xương cho mô hình đã dựng xong và đã tải về")
    from . import assets
    height = assets.get_profile(conn, m["asset_id"]).get("height_m") or 1.75
    try:
        bal = client.balance()
    except MeshyError:
        bal = None
    why = check(conn, m["asset_id"], "rig", CREDITS["rig"], bal)
    if why:
        raise MeshyError(why)
    row = _insert(conn, "rig", m["asset_id"], CREDITS["rig"], {"input_task_id": m["task_id"], "height_meters": height,
                                                                "endpoint": "/rigging"}, parent=m["task_id"])
    task_id = _send(conn, row, lambda: client.create_rig(m["task_id"], height))
    return {"row": row, "task_id": task_id}


# ---- polling + downloads ------------------------------------------------------------------------------------------------------------
def models_root() -> str:
    """data/models3d next to the library (ASSET_DIR's parent), absolute — never under the working folder of whoever started it."""
    from . import assets
    folder = os.path.join(os.path.dirname(assets.root()), "models3d")
    return folder if os.path.isabs(folder) else os.path.join(assets.REPO, folder)


def folder_for(conn, asset_id: int, task_id: str) -> str:
    name = conn.execute("SELECT name FROM assets WHERE id=?", (asset_id,)).fetchone()[0]
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name))
    return os.path.join(models_root(), f"{safe}_{asset_id}", task_id)


def _files_of(kind: str, task: Dict) -> Dict[str, str]:
    """name on disk → signed URL, for what is worth keeping."""
    out = {}
    if kind == "model":
        for fmt, url in (task.get("model_urls") or {}).items():
            if url and fmt in ("glb", "fbx", "obj", "usdz"):
                out[f"model.{fmt}"] = url
        for k, tex in enumerate(task.get("texture_urls") or []):
            for m, url in (tex or {}).items():
                if url:
                    out[f"texture_{k}_{m}.png"] = url
        for view, url in (task.get("thumbnail_urls") or {}).items():
            if url:
                out[f"view_{view}.png"] = url
        if task.get("thumbnail_url"):
            out.setdefault("view_front.png", task["thumbnail_url"])
    else:
        res = task.get("result") or {}
        for k in ("rigged_character_glb_url", "rigged_character_fbx_url"):
            if res.get(k):
                out["rigged." + k.split("_")[-2]] = res[k]
        for k, url in (res.get("basic_animations") or {}).items():       # flat: walking_glb_url, running_armature_fbx_url …
            fmt = k[:-4].rsplit("_", 1)[-1] if k.endswith("_url") else ""
            if url and fmt in ("glb", "fbx"):
                out[f"anim_{k[:-(len(fmt) + 5)]}.{fmt}"] = url
    return out


def refresh(conn, client: Client, now: Optional[float] = None) -> List[str]:
    """Poll every open task once; download a finished one at once (Meshy keeps files 3 days). Returns one line per change."""
    ensure_table(conn)
    notes = []
    for r in conn.execute("SELECT * FROM meshy_tasks WHERE status IN ('PENDING','IN_PROGRESS','SUCCEEDED') AND task_id IS NOT NULL")\
            .fetchall():
        endpoint = json.loads(r["request"] or "{}").get("endpoint") or ("/rigging" if r["kind"] == "rig" else "/multi-image-to-3d")
        try:
            t = client.get(endpoint, r["task_id"])
        except MeshyError as e:
            notes.append(f"#{r['id']}: {e}")
            continue
        status = t.get("status") or r["status"]
        credits = t.get("consumed_credits")
        if status in ("FAILED", "CANCELED"):
            err = (t.get("task_error") or {}).get("message") or status
            _update(conn, r["id"], status=status, credits=float(credits or 0), error=err)
            notes.append(f"#{r['id']} {r['kind']}: {status} — {err} (Meshy hoàn credit)")
            continue
        if status != "SUCCEEDED":
            _update(conn, r["id"], status=status)
            notes.append(f"#{r['id']} {r['kind']}: {status} {t.get('progress', 0)} %")
            continue
        folder = folder_for(conn, r["asset_id"], r["task_id"])
        os.makedirs(folder, exist_ok=True)
        saved, failed = [], []
        for name, url in _files_of(r["kind"], t).items():
            try:
                data = client.download(url)
            except MeshyError as e:
                failed.append(f"{name}: {e}")
                continue
            with open(os.path.join(folder, name), "wb") as f:
                f.write(data)
            saved.append(name)
        with open(os.path.join(folder, "task.json"), "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in t.items() if not str(k).endswith("_url") and k not in ("model_urls", "texture_urls",
                                                                                                  "thumbnail_urls", "result")},
                      f, ensure_ascii=False, indent=1)
        done = bool(saved) and not failed
        _update(conn, r["id"], status="DOWNLOADED" if done else "SUCCEEDED", folder=folder,
                credits=float(credits) if credits is not None else None, error="; ".join(failed) or None)
        notes.append(f"#{r['id']} {r['kind']}: xong — {len(saved)} tệp ở {folder}" + (f"; lỗi tải {len(failed)} tệp" if failed else ""))
    cutoff = (now or time.time()) - RETENTION_DAYS * 86400
    for r in conn.execute("SELECT * FROM meshy_tasks WHERE status='SUCCEEDED'").fetchall():
        made = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
        if made < cutoff:
            notes.append(f"#{r['id']}: ⚠ quá {RETENTION_DAYS} ngày chưa tải đủ — Meshy có thể đã xóa file")
    return notes


VIEW_ROLES = {"front": "full_body", "back": "back", "left": "side", "right": "side"}


def views_to_library(conn, model_row: int) -> Dict:
    """Meshy's own renders of the finished model (front / right / back / left) → the library, waiting for a person (pending, variant
    '3D Meshy'): approved, a back / side shot can be sent the picture of that side."""
    from . import assets
    r = conn.execute("SELECT * FROM meshy_tasks WHERE id=?", (model_row,)).fetchone()
    if r is None or r["status"] != "DOWNLOADED" or not r["folder"]:
        raise MeshyError("mô hình chưa tải về")
    added, skipped = [], []
    for view, role in VIEW_ROLES.items():
        p = os.path.join(r["folder"], f"view_{view}.png")
        if not os.path.exists(p):
            continue
        with open(p, "rb") as f:
            data = f.read()
        try:
            assets.add_image(conn, r["asset_id"], f"meshy_{view}.png", data, src_path=p, status="pending", role=role, look="ingame",
                             variant="3D Meshy", limit=40)
            added.append(view)
        except assets.AssetError as e:
            skipped.append(f"{view}: {e}")
    return {"added": added, "skipped": skipped}


def tasks(conn, asset_id: Optional[int] = None) -> List[Dict]:
    ensure_table(conn)
    sql, args = "SELECT * FROM meshy_tasks", ()
    if asset_id is not None:
        sql, args = sql + " WHERE asset_id=?", (asset_id,)
    return [dict(r) for r in conn.execute(sql + " ORDER BY id DESC", args).fetchall()]
