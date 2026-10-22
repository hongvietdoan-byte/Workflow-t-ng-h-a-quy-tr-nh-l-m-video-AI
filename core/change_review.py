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
           "plate_view", "practical_lights", "stage_camera", "characters", "performance", "time", "lighting", "continuity_from"):
    WATCH[_k] = ("nen", "anh", "neo", "lien_tuc", "motion", "khung_cuoi", "video")
for _k in ("action", "camera_move", "end_state", "continuous_with_next", "motion_en", "why", "emotional_intent", "beat"):
    WATCH[_k] = ("motion", "khung_cuoi", "video", "anh", "lien_tuc")
for _k in ("dialogue", "text", "on_screen_text"):
    WATCH[_k] = ("thoai", "motion", "video", "phu_de")
for _k in ("duration_s", "sound", "mood"):
    WATCH[_k] = ("dung", "nhac", "video")
# C4 (rà chuỗi 13/10): lần sửa motion prompt (trigger trg_change_motion, kind 'motion') — chỉ rà khi bật cờ MOTION_FLAG
MOTION_WATCH = ("motion_prompt",)
WATCH["motion_prompt"] = ("motion", "khung_cuoi", "video")
MOTION_FLAG = "change_review_motion"
SHOT_KINDS = ("scene", "motion")     # thay đổi của MỘT shot (trường shot hoặc motion prompt) — gộp chung một lần rà
# V3.1 M2.2 (rà kỹ 23/10): nhóm BYĐ v2 vào ảnh / nền như các trường chữ — CHỈ khi cờ mẹ byd_fields bật (tắt: WATCH y cũ)
BYD_WATCH: Dict[str, Tuple[str, ...]] = {f"byd.{g}": WATCH["image_prompt"] for g in ("thanh_phan", "vat", "khung")}


def watch() -> Dict[str, Tuple[str, ...]]:
    from . import byd_fields
    return {**WATCH, **BYD_WATCH} if byd_fields.mother_on() else WATCH


ASSET_WATCH = ("identity", "must_keep", "may_change", "forbidden", "height_m", "build", "size", "wardrobe")


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def motion_enabled() -> bool:
    from . import features
    try:
        return enabled() and features.on(MOTION_FLAG)
    except KeyError:
        return False


def _loads(s) -> Dict:
    try:
        v = json.loads(s or "{}")
        return v if isinstance(v, dict) else {}
    except (TypeError, ValueError):
        return {}


def _field(d: Dict, k: str):
    if k.startswith("byd."):                       # BYD_WATCH: một nhóm trong byd
        from . import shot_intent
        b = shot_intent.byd_of(d)
        return b.get(k[4:]) if b is not None else None
    return d.get(k)


def changed_keys(before: Dict, after: Dict, watch: Sequence[str]) -> List[str]:
    return [k for k in watch if _field(before, k) != _field(after, k)]


def affected_scenes(conn, ev) -> List[int]:
    """Shot bị ảnh hưởng: shot đổi + shot kề (liên tục) + (nếu nó là ảnh neo storyboard) cả nhóm; đổi Kho → mọi shot có vật đó."""
    if ev["kind"] in SHOT_KINDS:
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
                # anchor_by_spot: shot KHÔNG khai chỗ của cùng cảnh vẫn theo nhóm cũ (không theo chỗ) và có thể neo vào shot này
                for s in scene_storyboard.scene_shots(conn, row[0], g["story_scene"]):
                    other = scene_storyboard.group_of(conn, row[0], s["id"])
                    if other and other["anchor"]["id"] == ev["scene_id"]:
                        ids.append(s["id"])
        except Exception:  # noqa: BLE001 - storyboard grouping problem: the neighbours are still checked
            pass
        from . import layout_follow                      # hộp thư 12/10 19:17: the shots that keep this shot's layout (continuity_from)
        if layout_follow.enabled():
            ids += layout_follow.followers(conn, row[0], row[1])
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


def record_stage_blocking_change(conn, project_id: int, old_dir: str, new_dir: str, moved=(), *, proposal=False, approved_blocking=None, approved_specs=None) -> int:
    """V3 gọi sau ghi blocking, trước giải/render; baseline là tệp bản đã duyệt rõ ràng.
    proposal=True ghi đề xuất kèm thư mục lượt, không đóng finding thay đổi đã áp dụng.

    Tệp không có trigger scenes.data. Chỉ VÀNG, 0 USD; nguồn riêng tránh refresh_code
    đóng nhầm. Caller sở hữu transaction; không đổi shot/job hay tự duyệt.
    """
    from . import features, shot_lessons
    if not enabled() or not features.on("layout_drift_review"):
        return 0
    import os
    rows = conn.execute("SELECT s.id,s.idx FROM scenes s WHERE s.project_id=? AND EXISTS "
                        "(SELECT 1 FROM jobs j WHERE j.scene_id=s.id AND j.type='image_gen' AND j.state='approved')",
                        (project_id,)).fetchall()
    if not rows:
        return 0
    by_idx = {r['idx']: r['id'] for r in rows}
    found = []
    try:
        def read(directory, name):
            with open(os.path.join(directory, name), encoding='utf-8') as f:
                return json.load(f)
        if approved_blocking:
            with open(approved_blocking, encoding='utf-8') as f:
                old = json.load(f)
            with open(approved_specs, encoding='utf-8') as f:
                specs = json.load(f)
        else:
            old, specs = read(old_dir, 'blocking.json'), read(old_dir, 'shot_specs.json')
        new = read(new_dir, 'blocking.json')
        specs = specs.get('shots', specs) if isinstance(specs, dict) else specs
        beats = {s['shot']: s.get('nhip') for s in specs}
        cams = {}
        try:
            for s in read(old_dir, 'v2.json').get('shots', []):
                if s.get('best'):
                    m = s['best']['m']
                    cams[s['shot']] = {'at': m['at'], 'aim': m['aim']}
        except (OSError, ValueError, KeyError, TypeError):
            pass
        for idx in by_idx:
            if idx not in beats:
                found.append({'shot': idx, 'msg': f'shot {idx} (đã duyệt): thiếu ánh xạ nhịp trong shot_specs bản đã duyệt — chưa kiểm bố cục'})
            elif idx not in cams:
                found.append({'shot': idx, 'msg': f'shot {idx} (đã duyệt): thiếu máy bản đã duyệt trong v2.json — chưa kiểm đổi bên trái/phải'})
        found += shot_lessons.layout_drift(old, new, {i: beats[i] for i in by_idx if i in beats}, moved=moved, cams=cams)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        found = [{'shot': i, 'msg': f'shot {i} (đã duyệt): chưa kiểm được bố cục sân khấu — {type(e).__name__}: {e}'} for i in by_idx]
    source = 'layout_drift_proposal' if proposal else 'layout_drift'
    n = 0
    for idx, sid in by_idx.items():
        msgs = {f['msg'] for f in found if f['shot'] == idx}
        if proposal:
            msgs = {f'Đề xuất sân khấu chưa áp dụng ({os.path.abspath(new_dir)}): {msg}' for msg in msgs}
        for r in conn.execute("SELECT id,msg FROM change_findings WHERE scene_id=? AND source=? AND status='open'", (sid, source)).fetchall():
            if proposal:
                continue
            if r['msg'] not in msgs:
                conn.execute("UPDATE change_findings SET status='resolved',resolved_at=?,resolved_by='layout_drift' WHERE id=?", (_now(), r['id']))
        for msg in sorted(msgs):
            n += _add(conn, None, project_id, sid, source, 'vang', 'lien_tuc', msg,
                      'Giữ bố cục bản đã duyệt hoặc xem và duyệt lại ảnh shot này.')
    return n


def _code_level(f: Dict) -> str:
    """Mức của một mục luật code trong Tổ rà soát: 'ảnh vẽ trên nền cũ' và 'render nền chưa theo máy / khối đạo cụ' là đúng việc mà
    job vẽ lại + bước tự render nền làm → VÀNG (agent rà 10/10 lỗi 1: để đỏ thì chặn luôn job sửa nó, kẹt mãi). 17/10: nền cũ vẫn
    CHẶN gen — ở chỗ không kẹt: runner._stale_plates giữ job + render lại (cùng một định nghĩa location_pack.stale_plates) và
    batch.image_gates báo ĐỎ ở nút Gen; "nền 3D chưa dùng được" (lỗi / chờ hướng) runner cũng tự giữ (place_refs.broken / needs)."""
    if f["khau"] == "anh" or (f["khau"] == "nen" and ("chưa theo máy" in f["msg"] or "khối đạo cụ" in f["msg"]
                                                     or "chưa dùng được" in f["msg"])):
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
    if enabled():
        # rà kỹ 10/10 lỗi 3: shot cũ (#24 shot 4 "its dark mouth facing us") không có change_event nào → câu Director trái sự thật hình
        # học chưa từng được ghi, blocking() không giữ, prompt tự mâu thuẫn. Chỉ mục khâu 'cau' của stage_facts; mục người dùng đã
        # Bỏ qua (dismissed) không ghi lại.
        for f in found:
            if f["khau"] == "cau" and f["msg"].startswith(GEO_MSG) and not conn.execute(
                    "SELECT 1 FROM change_findings WHERE COALESCE(scene_id,0)=? AND source='code' AND khau=? AND msg=? "
                    "AND status='dismissed'", (sid, f["khau"], f["msg"])).fetchone():
                _add(conn, None, pid, sid, "code", _code_level(f), f["khau"], f["msg"], f.get("de_xuat"))
    return found


GEO_MSG = "câu Director trái sự thật hình học"     # core/change_audit.audit_shot — mục 'cau' của core/stage_facts


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
            n += _add(conn, ev_id, pid, sid, "code", _code_level(f), f["khau"], f["msg"], f.get("de_xuat"))
    return n


# ---- agent Claude ------------------------------------------------------------------------------------------------------------
LEVELS = ("do", "vang")
OBS = ("khop", "lech", "khong_chac")


def _short(v, n=700) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def build_prompt(conn, ev, keys: List[str], scene_ids: List[int], code_found: List[Dict]) -> str:
    import os
    from . import features, kho_profile
    frames = features.on("change_review_frames")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "prompts", "30_change_review_frames.md" if frames else PROMPT_FILE), encoding="utf-8") as f:
        head = f.read()
    before, after = _loads(ev["before"]), _loads(ev["after"])
    L = [head, "", "---", "", f"## Thay đổi #{ev['id']} ({ev['kind']})"]
    for k in keys:
        L.append(f"- `{k}`: TRƯỚC = {_short(before.get(k))}\n  SAU = {_short(after.get(k))}")
    if ev["kind"] not in SHOT_KINDS:
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
        # Lỗi 5 (#27 shot 16, 13/10): MỘT nguồn sự thật cho khâu motion = motion prompt GỬI ĐI (motion_prompts). motion_en chỉ là bản
        # dịch trường Đạo diễn mà code dùng để VIẾT prompt — người sửa tay prompt thì motion_en còn tả bản cũ, agent so bản cũ → giữ
        # oan. Có prompt → hiện prompt, bỏ motion_en; chưa có → motion_en (nguồn của bản code sắp viết).
        try:
            mp = conn.execute("SELECT motion_prompt, state FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
        except Exception:  # noqa: BLE001 - a bare database without the motion table: motion_en as before
            mp = None
        if mp is not None and str(mp[0] or "").strip():
            fields.pop("motion_en", None)
            fields["motion_prompt"] = f"[{'đã duyệt' if mp[1] == 'approved' else 'chờ duyệt'}] {mp[0]}"
        if features.on("qc_false_alarm_fix"):    # V3.1 M4.5 (P33-A6, #33 #877): agent báo "không có video tham chiếu" vì đề thiếu trường này
            try:
                ref = conn.execute("SELECT ref_video_path, ref_video_type FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
            except Exception:  # noqa: BLE001 - an old database without the columns: said as unknown, never as "none"
                ref = ("?", None)
            path = ref[0] if ref is not None else None
            fields["video tham chiếu"] = ("(không có)" if not path else "(không đọc được)" if path == "?" else
                                          os.path.basename(str(path)) + (f" [{ref[1]}]" if ref[1] else ""))
        L.append(f"### shot {row[0]} (id {sid}){' ← shot vừa đổi' if sid == ev['scene_id'] else ''}")
        labels = {"blocking": "khung đầu", "image_prompt": "khung đầu", "action": "đầu → đỉnh → cuối",
                  "motion_en": "đầu → đỉnh → cuối", "end_state": "khung cuối"} if frames else {}
        labels = {**labels, "motion_prompt": "bản GỬI ĐI cho model video"}
        L += [f"- {k}{' (' + labels[k] + ')' if k in labels else ''}: {_short(v, 500)}" for k, v in fields.items()]
        if frames:
            if d.get("duration_s") is not None:
                L.append(f"- duration_s: {_short(d['duration_s'])}")
            if d.get("byd"):
                # Giữ cả thành phần/dạng, ngoại lệ và nhịp; cắt 500 chữ dễ mất ket_thuc.
                L.append(f"- byd (đầu → đỉnh → cuối): {json.dumps(d['byd'], ensure_ascii=False)}")
    names = set()
    for sid in scene_ids:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()
        names |= set(_loads(row[0] if row else None).get("characters") or [])
    for nm in sorted(names):
        r = conn.execute("SELECT id, profile, description FROM assets WHERE upper(name)=upper(?)", (nm,)).fetchone()
        if r:
            p = kho_profile.read(conn,r[0]) if kho_profile.enabled() else _loads(r[1])
            if kho_profile.enabled() and p.get('schema_version') == 2:
                p['must_keep'] = kho_profile.lock_text_en(p)
                lock = p['must_keep'] or '(trống: hồ sơ v2 chưa có khóa đã duyệt)'
            else:
                lock = p.get('must_keep') or r[2] or '(trống)'
            L.append(f"- Kho #{r[0]} {nm}: must_keep = {_short(lock, 400)}")
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
    if ev["kind"] in SHOT_KINDS and ev["scene_id"]:       # shot vừa đổi được rà lại: mục Claude cũ của CHÍNH nó không còn → đã sửa
        # R9 (rà S4): chỉ đóng mục thuộc khâu mà các khóa VỪA ĐỔI chạm tới (WATCH) — prompt chỉ hỏi về các khóa đó, nên Claude không
        # nhắc lại mục ảnh/nền/thoại cũ KHÔNG có nghĩa là đã sửa (sửa motion không được mở chặn gen của mục ảnh còn sai)
        touched = {kh for k in keys for kh in watch().get(k, ())}
        for row in conn.execute("SELECT id, khau FROM change_findings WHERE source='claude' AND status='open' AND scene_id=?",
                                (ev["scene_id"],)).fetchall():
            if row[1] in touched and (ev["scene_id"], row[1]) not in seen:
                conn.execute("UPDATE change_findings SET status='resolved', resolved_at=?, resolved_by='claude' WHERE id=?",
                             (_now(), row[0]))
    return usd


QUOTA_CODES = ("usage_limit", "out_of_credit")   # rà C-RA-M14B: lỗi của TÀI KHOẢN Claude, không phải của thay đổi — dừng lượt
QUOTA_NOTE = "quota:"       # C-M71 A1: change_events.note của lần rà dừng vì hết tiền / hết lượt (code_only nhưng CHƯA được Claude rà)
ROUND_LIMIT = 5             # thay đổi mỗi lượt vòng nền (agent rà 10/10 lỗi 7: 20 × lời gọi 10–30 s làm nghẽn tải / gửi job)
ROUND_SECONDS = 90.0


def _group_by_scene(conn, rows, states) -> List[Tuple[Dict, List[int]]]:
    """Gộp các thay đổi đang chờ của CÙNG shot thành một lần rà (người dùng 10/10: Director/người sửa một shot nhiều lần liền thì chỉ
    trả một lời gọi): trước = bản của lần ghi cũ nhất, sau = bản của lần ghi mới nhất; lấy cả lần ghi cùng shot nằm ngoài LIMIT.
    Không gom theo thời gian. Thay đổi Kho / ảnh Kho giữ riêng từng cái."""
    q = ','.join('?' * len(states))
    out: List[Tuple[Dict, List[int]]] = []
    done = set()
    for ev in rows:
        if ev["kind"] not in SHOT_KINDS or not ev["scene_id"]:
            out.append((dict(ev), [ev["id"]]))
            continue
        if ev["scene_id"] in done:
            continue
        done.add(ev["scene_id"])
        grp = conn.execute(f"SELECT * FROM change_events WHERE kind IN ('scene', 'motion') AND scene_id=? AND state IN ({q}) ORDER BY id",
                           (ev["scene_id"], *states)).fetchall()
        merged = dict(grp[-1])
        merged["kind"] = "scene" if any(g["kind"] == "scene" for g in grp) else "motion"
        # C4: ảnh chụp shot (kind scene: cả scenes.data) và motion prompt (kind motion: chỉ khóa motion_prompt) gộp theo TỪNG nguồn —
        # trước = lần ghi cũ nhất của nguồn đó, sau = lần ghi mới nhất (không trộn ảnh chụp đầy đủ với một khóa lẻ)
        before, after = {}, {}
        for kind in ("scene", "motion"):
            part = [g for g in grp if g["kind"] == kind]
            if part:
                before.update(_loads(part[0]["before"]))
                after.update(_loads(part[-1]["after"]))
        merged["before"], merged["after"] = json.dumps(before, ensure_ascii=False), json.dumps(after, ensure_ascii=False)
        merged["state"] = "pending" if any(g["state"] == "pending" for g in grp) else grp[-1]["state"]
        merged["had_code_only"] = any(g["state"] == "code_only" for g in grp)
        out.append((merged, [g["id"] for g in grp]))
    return out


PLAN_KEYS = ("image_prompt", "size", "shot_no", "byd", "motion_en", "plate_spot")


def _before_director(conn, ev) -> bool:
    """Neither side of the change has any field of the Director's plan: the shot is still the script split (Director not run yet) —
    nothing to review against."""
    before, after = _loads(ev["before"]), _loads(ev["after"])
    return not any(before.get(k) or after.get(k) for k in PLAN_KEYS)


def _review_group(conn, data_dir: str, ev, ids: List[int], client, res: Dict) -> None:
    """Rà MỘT nhóm thay đổi (một shot, hoặc một thay đổi Kho): lọc → luật code → agent Claude (nếu có client). Không ném lỗi.
    Dùng chung cho vòng nền (process_pending) và rà ngay tại chỗ (review_scene_now — C1 rà soát 14/10)."""
    mark = f"id IN ({','.join('?' * len(ids))})"
    try:
        before, after = _loads(ev["before"]), _loads(ev["after"])
        if ev["kind"] in SHOT_KINDS:
            keys = changed_keys(before, after, list(watch()))
        elif ev["kind"] == "asset":
            keys = changed_keys(before, after, ASSET_WATCH)
        else:
            keys = ["anh_kho"]
        if keys and ev["kind"] == "scene" and _before_director(conn, ev):
            keys = []                     # thử D6 #28 14/10: tách cảnh → 'characters rỗng' ĐỎ trước khi Đạo diễn chạy (chưa có kế hoạch)
        if not keys:
            if ev["kind"] in SHOT_KINDS and ev.get("had_code_only"):    # đổi rồi hoàn tác: mục code cũ của shot kề tự đóng
                code_rules(conn, data_dir, ev["id"], affected_scenes(conn, ev))
            conn.execute(f"UPDATE change_events SET state='skipped', reviewed_at=? WHERE {mark}", (_now(), *ids))
            res["skipped"] += len(ids)
            conn.commit()
            return
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
        conn.execute(f"UPDATE change_events SET state=?, keys=?, reviewed_at=? WHERE {mark}",
                     ("reviewed" if client is not None or not scene_ids else "code_only", json.dumps(keys), _now(), *ids))
        conn.execute("UPDATE change_events SET cost_usd=cost_usd+? WHERE id=?", (usd, ev["id"]))   # tiền vào lần ghi cuối
        res["reviewed"] += len(ids)
        res["usd"] += usd
    except Exception as e:  # noqa: BLE001 - one change's problem never stops the others (said)
        if getattr(e, "code", None) in QUOTA_CODES:   # rà C-RA-M14B: hết lượt / hết tiền — không phải lỗi của thay đổi này: luật code đã
            # chạy → code_only (Claude rà lại khi có), không 'failed'; dừng cả lượt. C-M71 A1 (G35): ghi chú QUOTA_NOTE để blocking() GIỮ
            # (khác code_only "không cấu hình Claude" — thiết kế cũ, không giữ) tới khi Claude rà lại / người bấm Bỏ qua
            conn.execute(f"UPDATE change_events SET state='code_only', note=?, reviewed_at=? WHERE {mark} AND state='pending'",
                         (f"{QUOTA_NOTE}{e.code}: {e}"[:400], _now(), *ids))
            conn.commit()
            res["halted"] = str(e)
            return
        conn.execute(f"UPDATE change_events SET state='failed', note=?, reviewed_at=? WHERE {mark}",
                     (f"{type(e).__name__}: {e}"[:400], _now(), *ids))
        diag.record(conn, "system", "warn", f"Rà soát thay đổi #{ev['id']} lỗi: {type(e).__name__}: {e}", "change_review_fail",
                    ev["project_id"])
        res["failed"] += len(ids)
    conn.commit()


def process_pending(conn, data_dir: str, client=None, limit: int = ROUND_LIMIT, log: Callable[[str], None] = lambda m: None,
                    budget_s: float = ROUND_SECONDS, client_for: Optional[Callable] = None) -> Dict:
    """Một lượt worker: mỗi thay đổi đang chờ → lọc → luật code → agent Claude (nếu bật + có client). Không bao giờ ném lỗi.
    Không có Claude → 'code_only' (luật code đã chạy); có Claude lại thì các thay đổi đó được Claude rà sau.
    client_for(project_id) (V3.1 M1.4b): Claude của dự án của thay đổi (provider theo dự án); không truyền → `client` cho mọi thay đổi."""
    res = {"skipped": 0, "reviewed": 0, "failed": 0, "usd": 0.0}
    t0 = time.time()
    clients: Dict = {}
    states = ("pending", "code_only") if client is not None else ("pending",)   # code_only chỉ rà lại khi có Claude chung (không quay vòng)
    q = ','.join('?' * len(states))
    pick = f"state IN ({q})"
    if client is None and client_for is not None:
        # Rà kỹ C-M71 (VỪA 2): không có Claude chung nhưng dự án có Claude riêng — lần rà dừng vì HẾT TIỀN / HẾT LƯỢT (code_only + QUOTA_NOTE)
        # vẫn được rà lại (lời báo "vòng nền tự rà lại" đúng sự thật); code_only "không có Claude" giữ như cũ (không quay vòng)
        states = ("pending", "code_only")
        # C-M71-FIX (THẤP 3): lọc dự án CÓ Claude TRƯỚC khi áp LIMIT — trước nhóm code_only của dự án không có Claude bị `continue` mà
        # vẫn ăn suất LIMIT → ≥ LIMIT nhóm như vậy làm nhóm hết tiền của dự án CÓ Claude không bao giờ tới lượt
        pids = [r[0] for r in conn.execute(f"SELECT DISTINCT project_id FROM change_events WHERE state='code_only' AND note LIKE "
                                           f"'{QUOTA_NOTE}%'").fetchall()]
        clients = {pid: client_for(pid) for pid in pids}
        ok = sorted(int(pid) for pid, c in clients.items() if c is not None and pid is not None)
        pick = (f"(state='pending' OR (state='code_only' AND note LIKE '{QUOTA_NOTE}%' AND project_id IN ({','.join(map(str, ok))})))"
                if ok else "state='pending'")
    # LIMIT đếm theo NHÓM (một shot = một dòng), không theo lần ghi: một shot ghi 6 lần không chiếm hết lượt của shot khác
    if not motion_enabled():                    # C4: cờ change_review_motion tắt → lần sửa motion prompt không rà (như trước cờ)
        # C-FIX3-THAP: cả 'failed' (Claude timeout / lỗi) — trước mục ĐỎ "rà lỗi" của sự kiện motion failed vẫn mở và vẫn chặn khi cờ
        # tắt; nay sự kiện thành skipped → _hold_failed tự đóng mục (C-M71-FIX)
        conn.execute("UPDATE change_events SET state='skipped', reviewed_at=?, note=? || COALESCE(' — trước: ' || note, '') WHERE "
                     "kind='motion' AND state IN ('pending', 'code_only', 'failed')",   # giữ lời lỗi gốc (rà C-FIX3-THAP)
                     (_now(), f"cờ {MOTION_FLAG} tắt — sửa motion prompt không rà (bỏ hẳn, kể cả lần đã lỗi; bật lại cờ không rà lại)"))
        conn.commit()
    rows = conn.execute(f"SELECT * FROM change_events WHERE id IN (SELECT MIN(id) FROM change_events WHERE {pick} GROUP BY "
                        f"CASE WHEN kind IN ('scene', 'motion') AND scene_id IS NOT NULL THEN 'S' || scene_id ELSE 'E' || id END) "
                        f"ORDER BY state DESC, id LIMIT ?", (*(states if pick.startswith("state IN") else ()), limit)).fetchall()
    for ev, ids in _group_by_scene(conn, rows, states):
        if time.time() - t0 > budget_s:
            break
        c = (clients[ev["project_id"]] if ev["project_id"] in clients else client_for(ev["project_id"])) if client_for is not None else client
        if c is None and ev["state"] != "pending":   # VỪA 2: dự án vẫn không có Claude — code_only để nguyên (không quay vòng)
            continue
        _review_group(conn, data_dir, ev, ids, c, res)
        if res.get("halted"):                    # mọi thay đổi sau cũng gặp đúng lỗi này: chờ giờ mở lại, các thay đổi giữ 'pending'
            diag.record(conn, "system", "warn", "Tổ rà soát tác động dừng lượt — Claude: " + res["halted"][:300], "change_review_halt",
                        ev["project_id"])
            break
    conn.execute("DELETE FROM change_events WHERE state<>'pending' AND reviewed_at < ?",
                 (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - KEEP_DAYS * 86400)),))
    conn.commit()
    return res


def review_scene_now(conn, data_dir: str, scene_id: int, client=None) -> Dict:
    """C1 (rà soát R14, người dùng 14/10): rà NGAY TẠI CHỖ mọi thay đổi đang chờ của MỘT shot (bản motion máy tự viết lại trước lần gen
    lại) thay vì để vòng nền rà sau — lần gen lại không bị `blocking()` giữ một vòng nền. Cùng đường rà với vòng nền (_review_group:
    lọc → luật code → Claude qua sổ chi). client None → chỉ luật code, thay đổi thành 'code_only' (không giữ gen; vòng nền có Claude
    rà sau). Không bao giờ ném lỗi."""
    res = {"skipped": 0, "reviewed": 0, "failed": 0, "usd": 0.0}
    states = ("pending", "code_only") if client is not None else ("pending",)
    q = ','.join('?' * len(states))
    rows = conn.execute(f"SELECT * FROM change_events WHERE kind IN ('scene', 'motion') AND scene_id=? AND state IN ({q}) "
                        f"ORDER BY id LIMIT 1", (scene_id, *states)).fetchall()
    for ev, ids in _group_by_scene(conn, rows, states):
        _review_group(conn, data_dir, ev, ids, client, res)
        if res.get("halted"):                    # C-M71 A1: như vòng nền — nói ra có mã (blocking() giữ shot, không tự gửi)
            diag.record(conn, "system", "warn", "Tổ rà soát tác động (rà ngay) dừng — Claude: " + res["halted"][:300] + " — shot bị "
                        "giữ tới khi Claude rà lại hoặc bạn bấm Bỏ qua ở 📥", "change_review_halt", ev["project_id"])
            conn.commit()
    return res


UPGRADE_KHAU = ("video", "motion", "khung_cuoi")    # C9: khâu mà lệnh NÂNG từ nháp đã duyệt còn đi qua (prompt / khung cuối / clip)


def _stamp(at) -> str:
    """Hai kiểu giờ UTC trong CSDL ('…Z' của change_* và '…+00:00' của review_log) → so được đến giây."""
    return str(at or "")[:19]


FAIL_KHAU, FAIL_SOURCE = "ra_soat", "review_fail"


READ_FAIL = "Tổ rà soát tác động: không đọc được trạng thái rà của shot"   # giữ TẠM (khóa CSDL…): autopilot chờ nhịp sau, không chờ người
# C-M71 A1: lần rà CHƯA xong vì lỗi — 'failed' (Claude lỗi / timeout / trả rỗng hay sai mẫu) hoặc code_only do hết tiền / hết lượt
_UNREVIEWED = f"(state='failed' OR (state='code_only' AND note LIKE '{QUOTA_NOTE}%'))"
# C-FIX3-THAP-B: lần rà lỗi e (bí danh e) đã có mục 'rà lỗi' CHE: mục ghi SAU lần lỗi đó, trên chính e hoặc lần mới hơn cùng shot (một
# nhóm rà lỗi = một mục, gắn lần mới nhất), còn mở HOẶC do người đóng (Bỏ qua / Rà lại / dọn dự án đã giao). Mục tự đóng
# ('change_review': lần của mục đã rà xong / bị bỏ) KHÔNG che các lần khác của nhóm → chúng ra mục mới
# Mỗi shot chỉ MỘT mục mở: lần lỗi mới chưa được che → GẮN LẠI mục đang mở vào nó (không thêm mục — Bỏ qua / Rà lại một lần phủ cả shot).
# {e} = bí danh / tên bảng change_events của câu ngoài (UPDATE dùng tên bảng — không cần bí danh trong UPDATE)
_COVERED = ("EXISTS (SELECT 1 FROM change_findings f WHERE f.source='review_fail' AND f.scene_id={e}.scene_id AND f.event_id>={e}.id "
            "AND substr(f.at, 1, 19)>=substr(COALESCE({e}.reviewed_at, ''), 1, 19) {extra}AND (f.status='open' OR "
            "COALESCE(f.resolved_by, '')<>'change_review'))")


# các lần lỗi mục (tham số: scene_id, event_id của mục, id mục) che: id ≤ lần của mục, không bị mục KHÁC còn mở / đã Bỏ qua che
_RERUN_WHERE = (f"scene_id=? AND {_UNREVIEWED} AND id<=? AND NOT "
                + _COVERED.format(e="change_events", extra="AND f.id<>? AND f.status<>'resolved' "))


def _hold_failed(conn, scene_id: int, kinds: str) -> None:
    """G35 (#31 19/10, job 1061): lần rà của shot LỖI (vd. Claude hết tiền) mà cổng vẫn mở → job tốn tiền gửi đi khi chưa ai rà. Lần
    rà lỗi MỚI NHẤT của shot CHƯA có mục che (_COVERED, C-FIX3-THAP-B) thành mục ĐỎ (một mục cho mỗi lần lỗi; Bỏ qua / Rà lại đóng nó, không ghi
    lại). Mục khâu 'ra_soat' không thuộc UPGRADE_KHAU → lệnh nâng bản cao từ nháp đã duyệt (C9) chỉ báo VÀNG như mục đỏ cũ.
    C-M71 A1: cả lần rà dừng vì Claude hết tiền / hết lượt (code_only + QUOTA_NOTE) cũng giữ; mục rà lỗi tự đóng CHỈ khi CHÍNH lần thay
    đổi của nó đã được Claude rà đạt (rà kỹ CAO 1: lần rà đạt của thay đổi SAU không thấy thay đổi lỗi — 'failed' không vào nhóm).
    Rà kỹ VỪA 3: gọi mỗi nhịp → chỉ ghi khi có gì để ghi; không commit hộ giao dịch dở của người gọi."""
    owns = not getattr(conn, "in_transaction", False)
    wrote = False
    done = conn.execute("SELECT f.id FROM change_findings f JOIN change_events e ON e.id=f.event_id WHERE f.scene_id=? AND f.source=? "
                        "AND f.status='open' AND e.state IN ('reviewed', 'skipped')", (scene_id, FAIL_SOURCE)).fetchall()
    # C-M71-FIX (THẤP 2): thay đổi của mục đã thành 'skipped' (cờ change_review_motion tắt → motion code_only kể cả dòng hết tiền bị bỏ;
    # rà lại ra keys rỗng) cũng tự đóng — trước chỉ 'reviewed' → mục ĐỎ kẹt tới khi người bấm Bỏ qua
    if done:
        conn.execute(f"UPDATE change_findings SET status='resolved', resolved_at=?, resolved_by='change_review' WHERE id IN "
                     f"({','.join('?' * len(done))})", (_now(), *[r[0] for r in done]))
        wrote = True
    # C-FIX3-THAP-B (rà kỹ): trước chỉ xét lần lỗi id > lần rà đạt gần nhất → lần lỗi CHƯA ra mục (chưa ai gọi blocking) mà lần sửa sau đã rà đạt,
    # hoặc mục của nhóm gắn lần motion vừa bị bỏ (cờ change_review_motion tắt) → không bao giờ ra mục → cổng mở khi thay đổi chưa ai rà.
    # Nay: lần rà lỗi mới nhất CHƯA có mục che (_COVERED) → mục ĐỎ
    ev = conn.execute(f"SELECT id, project_id, note, reviewed_at, state FROM change_events e WHERE scene_id=? AND {_UNREVIEWED} AND kind "
                      f"IN {kinds} AND NOT {_COVERED.format(e='e', extra='')} ORDER BY id DESC LIMIT 1", (scene_id,)).fetchone()
    if ev is not None:
        if ev[4] == "code_only":
            msg, fix = (f"rà soát chưa chạy — Claude hết tiền / hết lượt ({str(ev[2])[len(QUOTA_NOTE):][:200]}) — vòng nền tự rà lại "
                        "khi Claude mở lại", "Nạp tiền / chờ giờ mở lại rồi bấm Rà lại; hoặc Bỏ qua nếu chấp nhận gen khi chưa rà")
        else:
            msg, fix = (f"rà soát lỗi: {ev[2] or 'không rõ lỗi'} — nạp tiền rồi bấm ↻ Rà lại",
                        "Kiểm số dư Anthropic rồi bấm Rà lại; hoặc Bỏ qua nếu chấp nhận gen khi chưa rà")
        cur = conn.execute("SELECT id FROM change_findings WHERE scene_id=? AND source=? AND status='open' ORDER BY id DESC LIMIT 1",
                           (scene_id, FAIL_SOURCE)).fetchone()
        if cur is not None:   # C-FIX3-THAP-B (rà VỪA 1-2): gắn lại mục đang mở (trước _add bỏ qua lời trùng → lần lỗi mới không ai che)
            conn.execute("UPDATE change_findings SET event_id=MAX(COALESCE(event_id, 0), ?), msg=?, de_xuat=?, at=? WHERE id=?",
                         (ev[0], msg, fix, _now(), cur[0]))     # không kéo lùi (rà THẤP: lật e4↔e5 mỗi nhịp)
            wrote = True
        else:
            wrote |= _add(conn, ev[0], ev[1] or _project_of(conn, scene_id), scene_id, FAIL_SOURCE, "do", FAIL_KHAU, msg, fix)
    if wrote and owns:
        conn.commit()


def rerun_targets(conn, finding_id: int) -> int:
    """Số lần thay đổi lỗi mà "↻ Rà lại" của mục này sẽ đưa về chờ rà (0 = không còn gì để rà — không tốn Claude). Không ghi gì."""
    row = conn.execute("SELECT event_id, scene_id FROM change_findings WHERE id=? AND source=?", (finding_id, FAIL_SOURCE)).fetchone()
    if row is None:
        return 0
    return conn.execute(f"SELECT COUNT(*) FROM change_events WHERE {_RERUN_WHERE}", (row[1], row[0], finding_id)).fetchone()[0]


def rerun_tag(conn) -> str:
    """Chữ giá của nút "↻ Rà lại" (luật chi phí: báo TRƯỚC khi bấm), theo quy ước nút Claude S14.2 A2 (cost.llm_button_tag: × LLM_MARGIN,
    chưa có giá → ước tính dư): các lần lỗi của mục cùng một shot → vòng nền rà chung MỘT nhóm = một lời gọi Claude stage change_review."""
    from . import cost
    try:
        return cost.llm_button_tag(conn, STAGE, 1)
    except Exception:  # noqa: BLE001 - bảng giá lỗi: nút vẫn hiện, nói rõ
        return " · Claude: chưa có giá"


def rerun_failed(conn, finding_id: int, who: Optional[str]) -> None:
    """Nút "Rà lại" của mục rà lỗi (G35): lần thay đổi lỗi về 'pending' (cổng giữ 'đang rà' tới khi vòng nền rà xong), mục đóng."""
    row = conn.execute("SELECT event_id, scene_id FROM change_findings WHERE id=? AND source=?", (finding_id, FAIL_SOURCE)).fetchone()
    if row is None:
        raise ValueError(finding_id)
    # C-FIX3-THAP-B: các lần lỗi mục này che (id ≤ lần của mục, không có mục KHÁC che) — trước cận id > lần rà đạt gần nhất làm nút hỏng khi lần sửa
    # sau đã rà đạt ("không còn trong sổ" sai sự thật, mục chỉ còn Bỏ qua). Mục khác chỉ "che" khi còn mở hoặc người Bỏ qua (dismissed):
    # mục đã Rà lại / ✓ Đã sửa ('resolved') không cản lần rà lại này (rà VỪA 1: hai mục mở cũ, Rà lại mục sau làm mục trước báo lỗi sai)
    n = conn.execute(f"UPDATE change_events SET state='pending', note=NULL WHERE {_RERUN_WHERE}", (row[1], row[0], finding_id)).rowcount
    if not n:          # lần lỗi đã bị dọn (KEEP_DAYS) → không có gì để rà lại: giữ mục, người dùng Bỏ qua nếu chấp nhận
        raise ValueError("lần thay đổi lỗi không còn trong sổ — không rà lại được; bấm Bỏ qua nếu chấp nhận gen khi chưa rà")
    conn.execute("UPDATE change_findings SET status='resolved', resolved_at=?, resolved_by=? WHERE id=?", (_now(), who, finding_id))
    conn.commit()


def blocking(conn, scene_id: int, data_dir: Optional[str] = None, since: Optional[str] = None,
             notes: Optional[List[str]] = None) -> Optional[str]:
    """Lý do chặn gen tốn tiền của shot: thay đổi của shot còn chờ rà (agent rà 10/10 lỗi 6: sửa xong bấm Gen ngay thì chưa ai rà) hoặc
    mục 'do' còn mở. data_dir có → chạy lại luật code của shot trước (mục đã hết tự đóng). None = được gửi. Cờ tắt → không chặn.
    C9 (rà chuỗi 13/10): `since` = lúc NGƯỜI duyệt nháp mà job bản cao nâng lên — chỉ mục đỏ MỚI hơn lúc đó VÀ thuộc khâu UPGRADE_KHAU
    mới giữ; mục đỏ khác (vd. khâu ảnh / nền cũ) không giữ mà ghi vào `notes` (người gọi báo VÀNG, không im lặng)."""
    if not enabled():
        return None
    try:
        return _blocking(conn, scene_id, data_dir, since, notes)
    except Exception as e:  # noqa: BLE001 - C-M71 A1: không đọc được bảng rà thì KHÔNG mở cổng (giữ, có lý do) — không ném làm hỏng lượt gửi
        return f"{READ_FAIL} ({type(e).__name__}: {str(e)[:160]}) — thử lại sau"


def _blocking(conn, scene_id: int, data_dir: Optional[str], since: Optional[str], notes: Optional[List[str]]) -> Optional[str]:
    kinds = "('scene', 'motion')" if motion_enabled() else "('scene')"   # C4: cờ tắt → sửa motion không giữ
    wait = conn.execute(f"SELECT id FROM change_events WHERE scene_id=? AND state='pending' AND kind IN {kinds} ORDER BY id LIMIT 1",
                        (scene_id,)).fetchone()
    if wait:
        return f"Tổ rà soát tác động đang rà thay đổi #{wait[0]} của shot này (vài chục giây) — gửi ngay sau khi rà xong"
    try:
        _hold_failed(conn, scene_id, kinds)
    except Exception as e:  # noqa: BLE001 - G35: not knowing whether a review failed never opens the gate
        return f"{READ_FAIL} ({type(e).__name__}: {e}) — thử lại sau"
    if data_dir:
        try:
            refresh_code(conn, data_dir, scene_id)
            conn.commit()
        except Exception:  # noqa: BLE001 - a rule problem never decides the hold by itself: the stored findings decide
            pass
    rows = conn.execute("SELECT khau, msg, at FROM change_findings WHERE scene_id=? AND status='open' AND level='do' ORDER BY id",
                        (scene_id,)).fetchall()
    if since is not None:
        keep = [r for r in rows if r[0] in UPGRADE_KHAU and _stamp(r[2]) >= _stamp(since)]
        if notes is not None:
            notes += [f"{r[0]}: {r[1]}" for r in rows if r not in keep]
        rows = keep
    if not rows:
        return None
    return ("Tổ rà soát tác động: " + "; ".join(f"{r[0]}: {r[1]}" for r in rows[:3])
            + (f" (+{len(rows) - 3})" if len(rows) > 3 else "") + " — sửa rồi gen, hoặc bấm Bỏ qua ở 📥 Việc cần bạn")


def open_findings(conn, project_id: int) -> List[Dict]:
    return [dict(r) for r in conn.execute("SELECT f.*, s.idx FROM change_findings f LEFT JOIN scenes s ON s.id=f.scene_id "
                                          "WHERE f.project_id=? AND f.status='open' ORDER BY f.level, s.idx, f.id", (project_id,))]


FIXED_ON_FAIL = ("Mục rà soát LỖI: thay đổi chưa được Claude rà — bấm \"↻ Rà lại\" (tốn Claude, có ước tính trên nút) hoặc \"Bỏ qua\" "
                 "nếu chấp nhận gen khi chưa rà")


def close(conn, finding_id: int, status: str, who: Optional[str]) -> None:
    if status not in ("resolved", "dismissed"):
        raise ValueError(status)
    if status == "resolved" and rerun_targets(conn, finding_id):
        # C-FIX4: mục rà LỖI còn thay đổi chưa rà → "đã sửa" KHÔNG đóng (đóng = che các lần lỗi → cổng mở khi chưa ai rà, C-FIX3-THAP-B)
        # và KHÔNG âm thầm gọi Claude (trước: tự rerun_failed — tốn tiền không báo giá, trái luật chi phí). Người chọn: "↻ Rà lại" (nút có
        # ước tính) hoặc "Bỏ qua" (chấp nhận gen khi chưa rà). Lần lỗi không còn trong sổ (KEEP_DAYS) → đóng như mục thường (0 USD)
        raise ValueError(FIXED_ON_FAIL)
    conn.execute("UPDATE change_findings SET status=?, resolved_at=?, resolved_by=? WHERE id=?", (status, _now(), who, finding_id))
    conn.commit()
