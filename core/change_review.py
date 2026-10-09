"""Tổ rà soát tác động (người dùng 10/10): "mỗi lần đổi bất kì điều gì trong khâu làm việc, đều cần 1 agent rà soát lại những khâu
liên quan đến nó". Đợt #24 (job 623–631): đổi máy 3D mà ảnh neo + phiên storyboard + câu tả cũ vẫn dùng → 9/9 ảnh vẽ nền cũ.

  1. Bắt thay đổi: trigger SQLite (core/db.py) ghi MỌI lần ghi scenes.data / assets.profile / asset_images vào `change_events`
     — mọi đường ghi (22 file ghi scenes trực tiếp), không phải nhớ gọi hàm.
  2. Lọc: chỉ trường có nghĩa với một khâu (WATCH) — trường sổ sách (dấu vân tay, QC…) → `skipped`, 0 USD.
  3. Luật code (core/change_audit, 0 USD) cho mọi shot bị ảnh hưởng (shot đổi, shot dùng nó làm ảnh neo, shot kề, mọi shot có nhân
     vật/đồ Kho vừa đổi).
  4. Agent Claude (khâu `change_review`): MỖI thay đổi một lời gọi — người dùng chốt KHÔNG trần, KHÔNG gom đợt (10/10). Có ước tính
     + sổ chi (llm_runner.tagged). Agent khai quan sát theo danh mục (khop / lech / khong_chac) + đề xuất; CODE quyết mức.
  5. Mục "do" mở → `blocking()` chặn gen tốn tiền của shot (runner) tới khi sửa / người bỏ qua; hiện ở 📥 Việc cần bạn.
Cờ `change_review`. Prompt: prompts/30_change_review.md.
"""
import json
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import diag, llm_io

FLAG = "change_review"
STAGE = "change_review"
PROMPT_FILE = "30_change_review.md"
KEEP_DAYS = 30

# trường của shot → các khâu phụ thuộc (đổi trường này thì phải rà những khâu này)
WATCH: Dict[str, Tuple[str, ...]] = {}
for _k in ("image_prompt", "blocking", "location", "location_asset", "layout", "size", "angle", "lens_mm", "weather", "plate_spot",
           "plate_view", "practical_lights", "stage_camera", "characters", "performance", "time", "lighting"):
    WATCH[_k] = ("nen", "anh", "neo", "lien_tuc", "motion", "khung_cuoi", "video")
for _k in ("action", "camera_move", "end_state", "continuous_with_next", "motion_en", "why", "emotional_intent", "beat"):
    WATCH[_k] = ("motion", "khung_cuoi", "video", "anh", "lien_tuc")
for _k in ("dialogue", "text", "on_screen_text"):
    WATCH[_k] = ("thoai", "motion", "video", "phu_de")
for _k in ("duration_s", "sound", "mood"):
    WATCH[_k] = ("dung", "nhac", "video")
ASSET_WATCH = ("identity", "must_keep", "may_change", "forbidden", "height_m", "build", "size", "wardrobe")


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _loads(s) -> Dict:
    try:
        v = json.loads(s or "{}")
        return v if isinstance(v, dict) else {}
    except (TypeError, ValueError):
        return {}


def changed_keys(before: Dict, after: Dict, watch: Sequence[str]) -> List[str]:
    return [k for k in watch if before.get(k) != after.get(k)]


def affected_scenes(conn, ev) -> List[int]:
    """Shot bị ảnh hưởng: shot đổi + shot kề (liên tục) + (nếu nó là ảnh neo storyboard) cả nhóm; đổi Kho → mọi shot có vật đó."""
    if ev["kind"] == "scene":
        row = conn.execute("SELECT project_id, idx FROM scenes WHERE id=?", (ev["scene_id"],)).fetchone()
        if row is None:
            return []
        ids = [r[0] for r in conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx BETWEEN ? AND ? ORDER BY idx",
                                          (row[0], row[1] - 1, row[1] + 1))]
        try:
            from . import scene_storyboard
            g = scene_storyboard.group_of(conn, row[0], ev["scene_id"]) if scene_storyboard.enabled() else None
            if g and g["anchor"]["id"] == ev["scene_id"]:
                ids += [s["id"] for s in g["shots"]]
        except Exception:  # noqa: BLE001 - storyboard grouping problem: the neighbours are still checked
            pass
        return list(dict.fromkeys([ev["scene_id"]] + ids))
    name = conn.execute("SELECT name FROM assets WHERE id=?", (ev["asset_id"],)).fetchone()
    if not name:
        return []
    out = []
    for sid, data in conn.execute("SELECT s.id, s.data FROM scenes s JOIN projects p ON p.id=s.project_id "
                                  "WHERE COALESCE(p.archived, 0)=0" if _has_col(conn, "projects", "archived") else
                                  "SELECT id, data FROM scenes"):
        d = _loads(data)
        if name[0] in (d.get("characters") or []) or str(ev["asset_id"]) == str(d.get("location_asset")) or \
                name[0].lower() in str(d.get("image_prompt") or "").lower():
            out.append(sid)
    return out


def _has_col(conn, table, col) -> bool:
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})"))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _add(conn, ev_id, pid, sid, source, level, khau, msg, de_xuat=None) -> bool:
    """Ghi một mục; mục mở trùng (cùng shot, nguồn, khâu, lời) không ghi lại."""
    if conn.execute("SELECT 1 FROM change_findings WHERE status='open' AND COALESCE(scene_id,0)=? AND source=? AND khau=? AND msg=?",
                    (sid or 0, source, khau, msg)).fetchone():
        return False
    conn.execute("INSERT INTO change_findings(event_id, project_id, scene_id, source, level, khau, msg, de_xuat, at) "
                 "VALUES (?,?,?,?,?,?,?,?,?)", (ev_id, pid, sid, source, level, khau, msg, de_xuat, _now()))
    return True


def _project_of(conn, sid) -> Optional[int]:
    r = conn.execute("SELECT project_id FROM scenes WHERE id=?", (sid,)).fetchone()
    return r[0] if r else None


def _code_level(f: Dict) -> str:
    """Mức của một mục luật code trong Tổ rà soát: 'ảnh vẽ trên nền cũ' và 'render nền chưa theo máy / khối đạo cụ' là đúng việc mà
    job vẽ lại + bước tự render nền làm → VÀNG (agent rà 10/10 lỗi 1: để đỏ thì chặn luôn job sửa nó, kẹt mãi)."""
    if f["khau"] == "anh" or (f["khau"] == "nen" and ("chưa theo máy" in f["msg"] or "khối đạo cụ" in f["msg"])):
        return "vang"
    return f["muc"]


def refresh_code(conn, data_dir: str, sid: int) -> List[Dict]:
    """Chạy lại luật code cho MỘT shot (0 USD): mục code không còn thấy → đóng 'resolved' (render lại nền, vẽ xong ảnh… không tạo
    change_event nào — agent rà 10/10 lỗi 1); trả các mục đang thấy."""
    from . import change_audit
    pid = _project_of(conn, sid)
    if pid is None:
        return []
    found = change_audit.audit_shot(conn, data_dir, pid, sid)
    msgs = {(f["khau"], f["msg"]) for f in found}
    for row in conn.execute("SELECT id, khau, msg FROM change_findings WHERE scene_id=? AND source='code' AND status='open'",
                            (sid,)).fetchall():
        if (row[1], row[2]) not in msgs:
            conn.execute("UPDATE change_findings SET status='resolved', resolved_at=?, resolved_by='code' WHERE id=?", (_now(), row[0]))
    return found


def code_rules(conn, data_dir: str, ev_id: int, scene_ids: List[int]) -> int:
    """Luật code (0 USD) cho mọi shot bị ảnh hưởng; mục code cũ của shot không còn thấy → tự đóng (đã sửa)."""
    from . import change_audit
    n = 0
    for sid in scene_ids:
        pid = _project_of(conn, sid)
        if pid is None:
            continue
        found = change_audit.audit_shot(conn, data_dir, pid, sid)
        msgs = {(f["khau"], f["msg"]) for f in found}
        for row in conn.execute("SELECT id, khau, msg FROM change_findings WHERE scene_id=? AND source='code' AND status='open'",
                                (sid,)).fetchall():
            if (row[1], row[2]) not in msgs:
                conn.execute("UPDATE change_findings SET status='resolved', resolved_at=?, resolved_by='code' WHERE id=?",
                             (_now(), row[0]))
        for f in found:
            n += _add(conn, ev_id, pid, sid, "code", _code_level(f), f["khau"], f["msg"])
    return n


# ---- agent Claude ------------------------------------------------------------------------------------------------------------
LEVELS = ("do", "vang")
OBS = ("khop", "lech", "khong_chac")


def _short(v, n=700) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def build_prompt(conn, ev, keys: List[str], scene_ids: List[int], code_found: List[Dict]) -> str:
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "prompts", PROMPT_FILE), encoding="utf-8") as f:
        head = f.read()
    before, after = _loads(ev["before"]), _loads(ev["after"])
    L = [head, "", "---", "", f"## Thay đổi #{ev['id']} ({ev['kind']})"]
    for k in keys:
        L.append(f"- `{k}`: TRƯỚC = {_short(before.get(k))}\n  SAU = {_short(after.get(k))}")
    if ev["kind"] != "scene":
        r = conn.execute("SELECT name, kind FROM assets WHERE id=?", (ev["asset_id"],)).fetchone()
        L.append(f"- vật Kho #{ev['asset_id']}: {r[0] if r else '?'} ({r[1] if r else '?'})")
    L += ["", "## Các shot liên quan (bản HIỆN TẠI)"]
    for sid in scene_ids[:12]:
        row = conn.execute("SELECT idx, data FROM scenes WHERE id=?", (sid,)).fetchone()
        if row is None:
            continue
        d = _loads(row[1])
        fields = {k: d.get(k) for k in ("characters", "size", "angle", "camera_move", "action", "blocking", "image_prompt", "motion_en",
                                        "end_state", "dialogue", "stage_camera", "plate_view") if d.get(k) not in (None, "", [], {})}
        L.append(f"### shot {row[0]} (id {sid}){' ← shot vừa đổi' if sid == ev['scene_id'] else ''}")
        L += [f"- {k}: {_short(v, 500)}" for k, v in fields.items()]
    names = set()
    for sid in scene_ids:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()
        names |= set(_loads(row[0] if row else None).get("characters") or [])
    for nm in sorted(names):
        r = conn.execute("SELECT id, profile, description FROM assets WHERE upper(name)=upper(?)", (nm,)).fetchone()
        if r:
            p = _loads(r[1])
            L.append(f"- Kho #{r[0]} {nm}: must_keep = {_short(p.get('must_keep') or r[2] or '(trống)', 400)}")
    if code_found:
        L += ["", "## Luật code đã thấy (khỏi lặp lại)"] + [f"- shot {f.get('shot')}: [{f['muc']}] {f['khau']}: {f['msg']}" for f in code_found]
    return "\n".join(L)


def validate(obj) -> Dict:
    if not isinstance(obj, dict) or not isinstance(obj.get("muc"), list):
        raise llm_io.SchemaError("cần {muc: [...]}")
    for it in obj["muc"]:
        if not isinstance(it, dict) or it.get("quan_sat") not in OBS or not it.get("khau") or not it.get("ly_do"):
            raise llm_io.SchemaError("mỗi mục cần khau, shot, quan_sat ∈ khop/lech/khong_chac, ly_do")
        if it.get("muc_do") not in (None, "do", "vang"):
            raise llm_io.SchemaError("muc_do ∈ do / vang")
    return obj


def decide(it: Dict) -> Optional[str]:
    """Code quyết mức từ quan sát của agent: chỉ 'lech' mới thành mục; 'do' chỉ khi agent nói lệch VÀ khâu đó tốn tiền gen."""
    if it.get("quan_sat") != "lech":
        return "vang" if it.get("quan_sat") == "khong_chac" and it.get("muc_do") == "do" else None
    return "do" if it.get("muc_do") == "do" and it.get("khau") in ("anh", "nen", "neo", "video", "khung_cuoi", "motion") else "vang"


def claude_review(conn, ev, keys, scene_ids, code_found, client) -> float:
    """Một lời gọi cho các shot của MỘT dự án (thay đổi Kho chạm nhiều dự án → mỗi dự án một lời gọi, vì 'shot 3' chỉ có nghĩa trong
    một dự án — agent rà 10/10 lỗi 3)."""
    from . import cost, llm_runner
    text = build_prompt(conn, ev, keys, scene_ids, code_found)
    pid = _project_of(conn, scene_ids[0]) if scene_ids else (ev["project_id"] or None)
    try:
        est = cost.llm_estimate(conn, STAGE, 1)
        diag.record(conn, "system", "info", f"Rà soát tác động thay đổi #{ev['id']} ({', '.join(keys)}) — ước tính "
                    f"≈ {est * cost.LLM_MARGIN:.3f} USD" if est is not None else "chưa có giá Claude", "change_review_est", pid)
    except Exception:  # noqa: BLE001 - a price table problem never stops the review (luật chi phí: said)
        pass
    with llm_runner.tagged(STAGE, pid):
        obj, tin, tout = llm_runner.ask_json(client, text, validate)
    usd = 0.0
    try:
        from . import budget
        p = cost.load_pricing()
        usd = (budget.token_price(p, cost.llm_model(), "input", tin) or 0) + (budget.token_price(p, cost.llm_model(), "output", tout) or 0)
    except Exception:  # noqa: BLE001
        pass
    by_idx = {}
    for sid in scene_ids:
        r = conn.execute("SELECT idx FROM scenes WHERE id=?", (sid,)).fetchone()
        if r:
            by_idx[r[0]] = sid
    seen = set()
    for it in obj["muc"]:
        lvl = decide(it)
        sid = by_idx.get(it.get("shot")) if isinstance(it.get("shot"), int) else None
        if lvl:
            _add(conn, ev["id"], _project_of(conn, sid) if sid else pid, sid, "claude", lvl, it["khau"], it["ly_do"], it.get("de_xuat"))
            seen.add((sid, it["khau"]))
    if ev["kind"] == "scene" and ev["scene_id"]:          # shot vừa đổi được rà lại: mục Claude cũ của CHÍNH nó không còn → đã sửa
        for row in conn.execute("SELECT id, khau FROM change_findings WHERE source='claude' AND status='open' AND scene_id=?",
                                (ev["scene_id"],)).fetchall():
            if (ev["scene_id"], row[1]) not in seen:
                conn.execute("UPDATE change_findings SET status='resolved', resolved_at=?, resolved_by='claude' WHERE id=?",
                             (_now(), row[0]))
    return usd


ROUND_LIMIT = 5             # thay đổi mỗi lượt vòng nền (agent rà 10/10 lỗi 7: 20 × lời gọi 10–30 s làm nghẽn tải / gửi job)
ROUND_SECONDS = 90.0


def process_pending(conn, data_dir: str, client=None, limit: int = ROUND_LIMIT, log: Callable[[str], None] = lambda m: None,
                    budget_s: float = ROUND_SECONDS) -> Dict:
    """Một lượt worker: mỗi thay đổi đang chờ → lọc → luật code → agent Claude (nếu bật + có client). Không bao giờ ném lỗi.
    Không có Claude → 'code_only' (luật code đã chạy); có Claude lại thì các thay đổi đó được Claude rà sau."""
    res = {"skipped": 0, "reviewed": 0, "failed": 0, "usd": 0.0}
    t0 = time.time()
    states = ("pending", "code_only") if client is not None else ("pending",)
    rows = conn.execute(f"SELECT * FROM change_events WHERE state IN ({','.join('?' * len(states))}) ORDER BY state DESC, id LIMIT ?",
                        (*states, limit)).fetchall()
    for ev in rows:
        if time.time() - t0 > budget_s:
            break
        try:
            before, after = _loads(ev["before"]), _loads(ev["after"])
            if ev["kind"] == "scene":
                keys = changed_keys(before, after, list(WATCH))
            elif ev["kind"] == "asset":
                keys = changed_keys(before, after, ASSET_WATCH)
            else:
                keys = ["anh_kho"]
            if not keys:
                conn.execute("UPDATE change_events SET state='skipped', reviewed_at=? WHERE id=?", (_now(), ev["id"]))
                res["skipped"] += 1
                continue
            scene_ids = affected_scenes(conn, ev)
            if ev["state"] == "pending":
                code_rules(conn, data_dir, ev["id"], scene_ids)
            from . import change_audit
            usd = 0.0
            if client is not None and scene_ids:
                by_pid: Dict[int, List[int]] = {}
                for sid in scene_ids:
                    by_pid.setdefault(_project_of(conn, sid) or 0, []).append(sid)
                for pid_, sids in by_pid.items():             # mỗi dự án một lời gọi (idx shot chỉ có nghĩa trong một dự án)
                    code_found = [f for sid in sids[:12] for f in change_audit.audit_shot(conn, data_dir, pid_, sid)]
                    usd += claude_review(conn, ev, keys, sids, code_found, client)
            conn.execute("UPDATE change_events SET state=?, keys=?, reviewed_at=?, cost_usd=cost_usd+? WHERE id=?",
                         ("reviewed" if client is not None or not scene_ids else "code_only", json.dumps(keys), _now(), usd, ev["id"]))
            res["reviewed"] += 1
            res["usd"] += usd
        except Exception as e:  # noqa: BLE001 - one change's problem never stops the others (said)
            conn.execute("UPDATE change_events SET state='failed', note=?, reviewed_at=? WHERE id=?",
                         (f"{type(e).__name__}: {e}"[:400], _now(), ev["id"]))
            diag.record(conn, "system", "warn", f"Rà soát thay đổi #{ev['id']} lỗi: {type(e).__name__}: {e}", "change_review_fail",
                        ev["project_id"])
            res["failed"] += 1
        conn.commit()
    conn.execute("DELETE FROM change_events WHERE state<>'pending' AND reviewed_at < ?",
                 (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - KEEP_DAYS * 86400)),))
    conn.commit()
    return res


def blocking(conn, scene_id: int, data_dir: Optional[str] = None) -> Optional[str]:
    """Lý do chặn gen tốn tiền của shot: thay đổi của shot còn chờ rà (agent rà 10/10 lỗi 6: sửa xong bấm Gen ngay thì chưa ai rà) hoặc
    mục 'do' còn mở. data_dir có → chạy lại luật code của shot trước (mục đã hết tự đóng). None = được gửi. Cờ tắt → không chặn."""
    if not enabled():
        return None
    wait = conn.execute("SELECT id FROM change_events WHERE scene_id=? AND state='pending' ORDER BY id LIMIT 1", (scene_id,)).fetchone()
    if wait:
        return f"Tổ rà soát tác động đang rà thay đổi #{wait[0]} của shot này (vài chục giây) — gửi ngay sau khi rà xong"
    if data_dir:
        try:
            refresh_code(conn, data_dir, scene_id)
            conn.commit()
        except Exception:  # noqa: BLE001 - a rule problem never decides the hold by itself: the stored findings decide
            pass
    rows = conn.execute("SELECT khau, msg FROM change_findings WHERE scene_id=? AND status='open' AND level='do' ORDER BY id",
                        (scene_id,)).fetchall()
    if not rows:
        return None
    return ("Tổ rà soát tác động: " + "; ".join(f"{r[0]}: {r[1]}" for r in rows[:3])
            + (f" (+{len(rows) - 3})" if len(rows) > 3 else "") + " — sửa rồi gen, hoặc bấm Bỏ qua ở 📥 Việc cần bạn")


def open_findings(conn, project_id: int) -> List[Dict]:
    return [dict(r) for r in conn.execute("SELECT f.*, s.idx FROM change_findings f LEFT JOIN scenes s ON s.id=f.scene_id "
                                          "WHERE f.project_id=? AND f.status='open' ORDER BY f.level, s.idx, f.id", (project_id,))]


def close(conn, finding_id: int, status: str, who: Optional[str]) -> None:
    if status not in ("resolved", "dismissed"):
        raise ValueError(status)
    conn.execute("UPDATE change_findings SET status=?, resolved_at=?, resolved_by=? WHERE id=?", (status, _now(), who, finding_id))
    conn.commit()
