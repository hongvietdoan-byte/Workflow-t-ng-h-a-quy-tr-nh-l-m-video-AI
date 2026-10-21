"""V3.1 M6.3 Generation Authorization — SHADOW (Gói M6-A, sổ v31-ep-m6-pack-a-approved-2026-10-21).

Một hàm `authorize` gọi NGAY trước provider.submit ở đường gửi job ảnh / video của shot (`runner._submit_pending` — mọi đường tạo job:
nút Dashboard, autopilot, QC tự sửa, repair router, thử lại / lùi model đều xếp job vào hàng rồi đi qua chỗ này). SHADOW: chỉ GHI quyết
định (cho phép / sẽ chặn + lý do) vào `<data_dir>/<pid>/crew/gen_auth_shadow.jsonl` — KHÔNG chặn, không ghi CSDL, không đổi gói gửi.

Chính sách (sổ v31-m6-generation-limits-policy-b-2026-10-21 + v31-ep-m6-self-repair-budget-40-2026-10-21, kế hoạch
docs/KE_HOACH_TO_LAM_PHIM_CO_CHU_2026-10-21.md mục 4):
  - mỗi shot / chu kỳ: ảnh ≤ 3 lượt, video ≤ 2 lượt (gồm lần đầu), tính chung mọi vai / model / worker / đường gọi; KHÔNG đặt lại khi
    sửa prompt, đổi model, restart, người bấm (không dùng retry_count). Lượt = job đã có task ở provider (external_id) hoặc submit
    chưa rõ (submit_unknown); job có bằng chứng provider không tạo (not_created) không tính; bước nâng nháp → bản cao (Q1) không tính.
    Chu kỳ mới chỉ khi EP cấp lượt (`<pid>/crew/grants.jsonl`: {"scene_id", "kind", "at", "by", "reason"}) — lượt trước lúc cấp không tính;
  - EP tự bấm CÓ trừ lượt (Q2): hết lượt → cần EP xác nhận vượt (needs_ep), ngân sách tự sửa chỉ áp cho job TỰ ĐỘNG (origin 'auto');
  - ngân sách tự sửa = 40 % tiền lượt đầu (sổ chi) của dự án; tiền làm lại (lượt 2+) đã chi + lượt này vượt → sẽ chặn;
  - 3 shot liên tiếp tự sửa cùng mã lỗi → dừng tự sửa (dấu hiệu lỗi hệ thống);
  - không tự gửi lại khi shot có submit chưa rõ chưa đối soát; không gửi trùng khi shot đang có job chạy;
  - tự sửa không đổi dữ liệu cảnh đã khóa (thay đổi cảnh sau lượt đầu); tự sửa phải có nguyên nhân;
  - model ngoài phạm vi đã duyệt (dự án / shot chưa chọn, dự án chưa gửi thật) → sẽ chặn (Q4: lùi trong phạm vi thì được).

Cờ `gen_auth_shadow` (mặc định TẮT): tắt = không làm gì. Lỗi của cổng shadow không bao giờ làm hỏng lượt gửi."""
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

FLAG = "gen_auth_shadow"
LIMITS = {"image_gen": 3, "video_gen": 2}
REPAIR_PCT = 0.40
SAME_CAUSE_STREAK = 3
NOT_CREATED = "not_created"                        # core.runner.NOT_CREATED
SUBMIT_UNKNOWN = "submit_unknown"                  # core.pipeline.SUBMIT_UNKNOWN
RESEND_NOTE = "gửi lại: nhà cung cấp không tạo task"   # core.runner.RESEND_NOTE (not_created / relink_failed: job con thay lượt cũ)
# ý đồ / dữ liệu đã khóa của shot (BYĐ + kế hoạch) — KHÔNG gồm prompt ảnh / motion (vòng tự sửa được viết lại) và trường sổ sách
LOCKED_KEYS = ("byd", "characters", "location", "location_asset", "layout", "blocking", "action", "end_state", "emotional_intent",
               "beat", "why", "dialogue", "text", "on_screen_text", "duration_s", "continuity_from", "continuous_with_next")
CODES = ("OK", "ATTEMPTS_EXHAUSTED", "BUDGET_EXCEEDED", "SAME_CAUSE_STREAK", "PROVIDER_UNVERIFIED", "DUPLICATE_INFLIGHT", "LOCKED_CHANGE",
         "NO_CAUSE", "MODEL_NOT_APPROVED")


@dataclass
class Decision:
    allow: bool
    code: str                                      # mã chặn đầu tiên, hoặc OK
    attempts_used: int
    attempts_limit: int
    budget_left_usd: Optional[float]
    needs_ep: bool
    reason_vi: str
    codes: List[str] = field(default_factory=list)  # MỌI lý do sẽ chặn
    counted: bool = True                           # lượt này có tính vào trần không (Q1: nâng nháp → không)
    auto: bool = False


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _now() -> str:
    """UTC, cùng dạng jobs.created_at (sổ cấp lượt grants.jsonl ghi `at` cũng theo UTC ISO)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_upgrade(job) -> bool:
    """Q1: bản cao NÂNG từ nháp đã duyệt (gói đã gửi call = submit_final_from_sample — cùng task nháp, cùng bố cục / chuyển động):
    không tính lượt. Bản cao gen MỚI (nháp hết hạn / không nâng được / có câu sửa) là lượt mới, có tính. Job chưa gửi → False (lúc gửi
    runner nói thẳng qua `upgrade=`)."""
    try:
        if (job["quality_tier"] or "") != "final" or not job["draft_job_id"]:
            return False
        return json.loads(job["sent_package"] or "{}").get("call") == "submit_final_from_sample"
    except (IndexError, KeyError, ValueError, TypeError, AttributeError):
        return False


def _failed_note(conn, job_id: int) -> str:
    row = conn.execute("SELECT note FROM job_events WHERE job_id=? AND to_state='failed' ORDER BY id DESC LIMIT 1", (job_id,)).fetchone()
    return (row[0] or "") if row else ""


def _grants(data_dir: Optional[str], pid: int) -> List[Dict]:
    if not data_dir:
        return []
    out = []
    try:
        with open(os.path.join(data_dir, str(pid), "crew", "grants.jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def _cycle_from(grants: List[Dict], scene_id: int, kind: str) -> Optional[str]:
    times = [g.get("at") for g in grants if g.get("scene_id") == scene_id and g.get("kind") == kind and g.get("at")]
    return max(times) if times else None


def cycle_start(data_dir: Optional[str], pid: int, scene_id: int, kind: str) -> Optional[str]:
    """Thời điểm (UTC ISO) EP cấp lượt gần nhất cho shot / loại (chu kỳ mới) — lượt trước đó không tính. None = chu kỳ đầu.
    grants.jsonl: {"scene_id", "kind", "at" (UTC ISO như jobs.created_at), "by", "reason"} — chưa có code ghi (M6-B)."""
    return _cycle_from(_grants(data_dir, pid), scene_id, kind)


def attempts(conn, scene_id: int, kind: str, *, exclude_job_id: Optional[int] = None, since: Optional[str] = None) -> List:
    """Các job ĐÃ TÍNH lượt của shot / loại (cũ → mới): có task ở provider hoặc submit chưa rõ; trừ not_created (provider không tạo)
    và bước nâng nháp → bản cao (Q1)."""
    rows = conn.execute("SELECT * FROM jobs WHERE type=? AND (? IS NULL OR id<>?) AND (? IS NULL OR created_at>=?) AND (scene_id=? OR "
                        "(sent_group IS NOT NULL AND json_valid(sent_group) AND EXISTS (SELECT 1 FROM json_each(jobs.sent_group) g "
                        "WHERE CAST(json_extract(g.value, '$.id') AS INTEGER)=?))) ORDER BY id",
                        (kind, exclude_job_id, exclude_job_id, since, since, scene_id, scene_id)).fetchall()
    # C-M63-FIX: clip NHÓM (Seedance / multi-shot) do shot đầu gửi mang phần của shot này (sent_group) — tính cho shot này; job đi kèm
    # của chính shot đã nhận cùng task (external_id của leader) thì không đếm 2 lần
    own_ext = {r["external_id"] for r in rows if r["scene_id"] == scene_id and r["external_id"]}
    out = []
    for r in rows:
        if r["scene_id"] != scene_id and r["external_id"] in own_ext:
            continue
        if is_upgrade(r):
            continue
        note = _failed_note(conn, r["id"])            # mọi trạng thái: job not_created / submit_unknown sau resend thành cancelled
        if note.startswith(NOT_CREATED):
            continue
        if conn.execute("SELECT 1 FROM jobs WHERE parent_job_id=? AND retry_reason LIKE ? LIMIT 1", (r["id"], RESEND_NOTE + "%")).fetchone():
            continue                                  # relink_failed / not_created: job con mang lượt này — không đếm 2 lần
        if r["external_id"] or note.startswith(SUBMIT_UNKNOWN):
            out.append(r)
    return out


_PRICING_CACHE: Dict = {}
PRICING_TTL_S = 60
_BUDGET_CACHE: Dict = {}


def _pricing():
    """Bảng giá — nạp lại tối đa mỗi PRICING_TTL_S (C-M63-FIX: trước nạp mỗi lượt gửi, trong SPEND_LOCK)."""
    import time
    hit = _PRICING_CACHE.get("v")
    if hit is not None and time.monotonic() - hit[0] < PRICING_TTL_S:
        return hit[1]
    from . import cost
    try:
        pricing = cost.load_pricing()
    except Exception:  # noqa: BLE001 - shadow: không có bảng giá → không tính tiền (nói trong lý do)
        pricing = None
    pricing = None if not isinstance(pricing, dict) or pricing.get("_error") else pricing   # bảng giá hỏng ≠ ngân sách 0
    _PRICING_CACHE["v"] = (time.monotonic(), pricing)
    return pricing


def _usd_of_jobs(conn, job_ids: List[int], pricing) -> float:
    if not job_ids or pricing is None:
        return 0.0
    from .budget import row_usd
    q = ",".join("?" * len(job_ids))
    total = 0.0
    for r in conn.execute(f"SELECT * FROM usage_events WHERE job_id IN ({q})", job_ids).fetchall():
        if str(r["provider"] or "").startswith("mock"):
            continue
        usd = row_usd(pricing, r)
        total += usd or 0.0
    return total


def repair_budget(conn, project_id: int, data_dir: Optional[str] = None, pricing=None) -> Dict:
    """{"first_usd", "repair_usd", "limit_usd", "left_usd", "pct"} — tiền lượt đầu / làm lại theo SỔ CHI (usage_events) của các lượt đã
    tính; ngân sách = REPAIR_PCT × lượt đầu (EP đổi tỷ lệ theo dự án: app_settings `gen_auth_repair_pct:<pid>`)."""
    pricing = pricing if pricing is not None else _pricing()
    # C-M63-FIX: cache theo lượt — CSDL không đổi (total_changes + data_version) thì dùng lại (trước: N+1 truy vấn mỗi lượt gửi, trong SPEND_LOCK)
    try:
        key = (id(conn), project_id, data_dir, conn.total_changes, conn.execute("PRAGMA data_version").fetchone()[0], id(pricing))
    except Exception:  # noqa: BLE001 - kết nối lạ: không cache
        key = None
    if key is not None and _BUDGET_CACHE.get("key") == key:
        return dict(_BUDGET_CACHE["value"])
    value = _repair_budget(conn, project_id, data_dir, pricing)
    if key is not None:
        _BUDGET_CACHE.update(key=key, value=dict(value))
    return value


def _repair_budget(conn, project_id: int, data_dir: Optional[str], pricing) -> Dict:
    pct = REPAIR_PCT
    try:
        row = conn.execute("SELECT value FROM app_settings WHERE key=?", (f"gen_auth_repair_pct:{project_id}",)).fetchone()
        if row and row[0] not in (None, ""):
            pct = float(row[0])
    except Exception:  # noqa: BLE001 - bảng / giá trị lạ: tỷ lệ mặc định
        pass
    first, repair = [], []
    grants = _grants(data_dir, project_id)            # đọc sổ cấp lượt MỘT lần
    for s in conn.execute("SELECT DISTINCT scene_id, type FROM jobs WHERE project_id=? AND scene_id IS NOT NULL AND type IN "
                          "('image_gen', 'video_gen')", (project_id,)).fetchall():
        done = attempts(conn, s[0], s[1], since=_cycle_from(grants, s[0], s[1]))
        first += [r["id"] for r in done[:1]]
        repair += [r["id"] for r in done[1:] if (r["origin"] or "") == "auto"]   # 4d: thao tác EP tự bấm KHÔNG ăn vào ngân sách tự sửa
    first_usd, repair_usd = _usd_of_jobs(conn, first, pricing), _usd_of_jobs(conn, repair, pricing)
    limit = first_usd * pct
    return {"first_usd": round(first_usd, 4), "repair_usd": round(repair_usd, 4), "limit_usd": round(limit, 4),
            "left_usd": round(limit - repair_usd, 4), "pct": pct, "priced": pricing is not None}


def _cause_of_take(conn, take) -> str:
    """Mã lỗi của MỘT lượt đã ra (lượt bị làm lại): lý do loại C2 (`reject_reason`, ghi lên job BỊ loại), không có thì mã đầu của
    ghi chú hỏng (job_events failed: 'mã: câu')."""
    if take is None:
        return ""
    rr = (take["reject_reason"] or "").strip()
    if rr:
        return rr
    note = _failed_note(conn, take["id"]).strip()
    head = note.split(":", 1)[0].strip() if ":" in note else ""
    return head if head and " " not in head else ""


def _cause(conn, job, done: Optional[List] = None) -> str:
    """Nguyên nhân của lượt làm lại này = mã lỗi của lượt TRƯỚC: job cha (parent_job_id) hoặc lượt đã tính gần nhất của shot."""
    parent = conn.execute("SELECT * FROM jobs WHERE id=?", (job["parent_job_id"],)).fetchone() if job["parent_job_id"] else None
    cause = _cause_of_take(conn, parent)
    if not cause and done:
        cause = _cause_of_take(conn, done[-1])
    return cause


def _same_cause_streak(conn, project_id: int, kind: str, cause: str, scene_id: int) -> bool:
    """3 shot liên tiếp (khác nhau, mới nhất trước) tự sửa cùng mã lỗi — tính cả lượt này."""
    if not cause:
        return False
    seen, causes = {scene_id}, [cause]
    for r in conn.execute("SELECT * FROM jobs WHERE project_id=? AND type=? AND origin='auto' AND parent_job_id IS NOT NULL "
                          "ORDER BY id DESC LIMIT 50", (project_id, kind)).fetchall():
        if r["scene_id"] in seen:
            continue
        seen.add(r["scene_id"])
        causes.append(_cause(conn, r))
        if len(causes) >= SAME_CAUSE_STREAK:
            break
    return len(causes) >= SAME_CAUSE_STREAK and len(set(causes)) == 1


def approved_models(conn, project_id: int, scene_id: Optional[int], kind: str) -> set:
    """Model trong phạm vi đã duyệt (tạm, tới Role Registry M6.1): model dự án chọn (projects.image_model / video_model), model shot chọn
    (model_router.scene_choice) và model dự án đã gửi thật. Q4: lùi model tự động chỉ hợp lệ khi model đích nằm trong tập này."""
    chosen = set()
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if proj is not None:
        chosen.add(proj["image_model"] if kind == "image_gen" else proj["video_model"])
    used = conn.execute("SELECT DISTINCT model FROM jobs WHERE project_id=? AND type=? AND external_id IS NOT NULL", (project_id, kind))
    chosen |= {r[0] for r in used.fetchall()}
    if kind == "video_gen" and scene_id:
        try:
            from . import model_router
            chosen.add(model_router.scene_choice(conn, scene_id).get("model"))
        except Exception:  # noqa: BLE001 - shot không chọn được → chỉ dùng phần còn lại
            pass
    chosen.discard(None)
    chosen.discard("")
    return chosen


def _locked_changes(conn, scene_id: int, since: str) -> List[str]:
    """Khóa ý đồ / dữ liệu đã khóa (LOCKED_KEYS) đổi sau `since` (change_events kind 'scene' — trigger ghi MỌI lần ghi scenes.data,
    kể cả prompt Đạo diễn viết lại / takes / seedance_refs: chỉ khóa thuộc ý đồ mới tính). So theo giây UTC (19 ký tự đầu)."""
    from . import change_review
    out: List[str] = []
    for r in conn.execute("SELECT before, after FROM change_events WHERE scene_id=? AND kind='scene' AND substr(at, 1, 19)>? ORDER BY id",
                          (scene_id, (since or "")[:19])).fetchall():
        for k in change_review.changed_keys(_json(r[0]), _json(r[1]), LOCKED_KEYS):
            if k not in out:
                out.append(k)
    return out


def _json(text) -> Dict:
    try:
        v = json.loads(text or "{}")
        return v if isinstance(v, dict) else {}
    except (TypeError, ValueError):
        return {}


def _est_usd(conn, job, model: Optional[str], pricing) -> Optional[float]:
    from . import cost
    try:
        if job["type"] == "image_gen":
            return cost._number((pricing or {}).get("per_image", {}).get(model)) if pricing else None
        return cost.send_clip_usd(conn, job["scene_id"], pricing, parent_job_id=job["parent_job_id"])   # bậc của lượt thử lại
    except Exception:  # noqa: BLE001 - không ước tính được → không tính tiền lượt này (nói trong lý do)
        return None


def authorize(conn, job, *, model: Optional[str] = None, upgrade: Optional[bool] = None, data_dir: Optional[str] = None,
              est_usd: Optional[float] = None) -> Decision:
    """Quyết định cho MỘT lượt gửi job ảnh / video của shot. Chỉ đọc CSDL + tệp sổ cấp lượt. Không bao giờ ném lỗi ra ngoài shadow()."""
    kind, pid, sid = job["type"], job["project_id"], job["scene_id"]
    limit = LIMITS.get(kind, 0)
    auto = (job["origin"] or "") == "auto"
    upgrade = is_upgrade(job) if upgrade is None else upgrade
    model = model or job["model"]
    pricing = _pricing()
    since = cycle_start(data_dir, pid, sid, kind) if sid else None
    done = attempts(conn, sid, kind, exclude_job_id=job["id"], since=since) if sid else []
    used = len(done)
    codes, why = [], []
    if not upgrade and limit and used + 1 > limit:
        codes.append("ATTEMPTS_EXHAUSTED")
        why.append(f"shot đã dùng {used}/{limit} lượt {'ảnh' if kind == 'image_gen' else 'video'} (tính chung mọi vai / model / người) — "
                   + ("EP xác nhận vượt + lý do (sổ cấp lượt)" if not auto else "chuyển EP cấp lượt"))
    budget, left = None, None
    if auto and used >= 1 and not upgrade:
        budget = repair_budget(conn, pid, data_dir, pricing)
        est = est_usd if est_usd is not None else _est_usd(conn, job, model, pricing)
        left = budget["left_usd"]
        if budget["priced"] and left - (est or 0.0) < 0:
            codes.append("BUDGET_EXCEEDED")
            why.append(f"ngân sách tự sửa {budget['pct']:.0%} lượt đầu = {budget['limit_usd']:.2f} USD, đã dùng {budget['repair_usd']:.2f}"
                       f" + lượt này ≈ {(est or 0):.2f} USD")
        cause = _cause(conn, job, done)
        if not cause:
            codes.append("NO_CAUSE")
            why.append("tự sửa không có nguyên nhân rõ (không lý do loại / câu lỗi)")
        elif _same_cause_streak(conn, pid, kind, cause, sid):
            codes.append("SAME_CAUSE_STREAK")
            why.append(f"{SAME_CAUSE_STREAK} shot liên tiếp tự sửa cùng mã '{cause}' — dấu hiệu lỗi hệ thống, dừng tự sửa + phiếu")
        locked = _locked_changes(conn, sid, done[0]["created_at"]) if done else []
        if locked:
            codes.append("LOCKED_CHANGE")
            why.append(f"ý đồ / dữ liệu khóa của shot đổi sau lượt đầu ({', '.join(locked[:4])}) — tự sửa không được đổi")
    if sid:
        unknown = [r for r in done if not r["external_id"]]          # submit chưa rõ, chưa nối lại task
        if auto and unknown:
            codes.append("PROVIDER_UNVERIFIED")
            why.append(f"job {unknown[-1]['id']} gửi chưa rõ kết quả, chưa đối soát — không tự gửi lại")
        busy = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type=? AND state='running' AND id<>? LIMIT 1",
                            (sid, kind, job["id"])).fetchone()
        if busy:
            codes.append("DUPLICATE_INFLIGHT")
            why.append(f"shot đang có job {busy[0]} chạy ở provider")
    ok_models = approved_models(conn, pid, sid, kind)
    if model and ok_models and model not in ok_models:                # dự án chưa chọn / chưa gửi gì: không có phạm vi để so
        codes.append("MODEL_NOT_APPROVED")
        why.append(f"model {model} ngoài phạm vi đã duyệt của dự án ({', '.join(sorted(ok_models)) or 'chưa có'})")
    needs_ep = bool({"ATTEMPTS_EXHAUSTED", "BUDGET_EXCEEDED", "LOCKED_CHANGE", "SAME_CAUSE_STREAK", "MODEL_NOT_APPROVED"} & set(codes))
    return Decision(allow=not codes, code=codes[0] if codes else "OK", attempts_used=used, attempts_limit=limit, budget_left_usd=left,
                    needs_ep=needs_ep, reason_vi="; ".join(why) or "đủ điều kiện", codes=codes, counted=not upgrade, auto=auto)


def shadow(conn, job, *, model: Optional[str] = None, upgrade: Optional[bool] = None, data_dir: Optional[str] = None,
           group: Optional[List[int]] = None, route: Optional[str] = None) -> Optional[Decision]:
    """SHADOW: tính quyết định và GHI vào `<data_dir>/<pid>/crew/gen_auth_shadow.jsonl` — không chặn, không ghi CSDL. Cờ tắt → None,
    không đọc gì. `group` = các shot KHÁC cùng đi trong lượt gửi nhóm (multi-shot / nhóm Seedance): mỗi shot một dòng quyết định (trần
    lượt tính theo shot), dòng của leader trả về. Một job còn trong hàng (lỗi tạm, gửi lại nhịp sau) có thể có nhiều dòng — đọc theo
    `latest_per_job`. Mọi lỗi bị nuốt (quan sát, không phải điều khiển) nhưng nói ra stderr."""
    try:
        if not enabled() or job is None or job["type"] not in LIMITS:
            return None
        d = authorize(conn, job, model=model, upgrade=upgrade, data_dir=data_dir)
        lines = [{"at": _now(), "job_id": job["id"], "scene_id": job["scene_id"], "kind": job["type"], "model": model or job["model"],
                  **({"route": route} if route else {}), **asdict(d)}]
        for sid in group or []:
            member = dict(job)
            member["scene_id"] = sid
            md = authorize(conn, member, model=model, upgrade=upgrade, data_dir=data_dir)
            lines.append({"at": _now(), "job_id": job["id"], "scene_id": sid, "kind": job["type"], "model": model or job["model"],
                          "group_of": job["scene_id"], **asdict(md)})
        if data_dir:
            folder = os.path.join(data_dir, str(job["project_id"]), "crew")
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "gen_auth_shadow.jsonl"), "a", encoding="utf-8") as f:
                f.write("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines))
        return d
    except Exception as e:  # noqa: BLE001 - cổng shadow không bao giờ làm hỏng lượt gửi
        import sys
        print(f"[gen_auth] shadow lỗi job {job['id'] if job is not None else '?'}: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def shadow_send(conn, *, project_id: int, scene_id: Optional[int], kind: str, model: Optional[str], route: str,
                data_dir: Optional[str]) -> Optional[Decision]:
    """C-M63-FIX: các đường gửi tiền KHÔNG qua runner (`spend_gate.slot.send` thẳng: khung cuối, phép thử chất lượng, khớp môi, ảnh
    toàn cảnh, bộ ảnh nhân vật, thử nghiệm multi-shot) — cùng cổng shadow, một job GIẢ (không id, origin 'auto') cho shot / loại;
    dòng jsonl mang `route`. Không chặn, không ghi CSDL; cờ tắt → None (không đọc gì)."""
    if not enabled():
        return None
    job = {"id": None, "type": kind, "project_id": project_id, "scene_id": scene_id, "model": model, "origin": "auto",
           "parent_job_id": None, "retry_reason": None, "reject_reason": None, "quality_tier": None, "draft_job_id": None,
           "sent_package": None, "created_at": _now(), "route": route}
    return shadow(conn, job, model=model, data_dir=data_dir, route=route)


def latest_per_job(rows: List[Dict]) -> List[Dict]:
    """Dòng mới nhất mỗi (job, shot) — job còn trong hàng được ghi lại mỗi nhịp gửi."""
    last: Dict = {}
    for r in rows:
        last[(r.get("job_id"), r.get("scene_id"))] = r
    return list(last.values())


def read_shadow(data_dir: str, project_id: int) -> List[Dict]:
    """Các quyết định shadow đã ghi của dự án (cũ → mới)."""
    out = []
    try:
        with open(os.path.join(data_dir, str(project_id), "crew", "gen_auth_shadow.jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out
