"""Khung "🧭 Trước khi chạy" ở Bước 1 (người dùng chốt 10/10): một chỗ nói trước những thứ sẽ tốn tiền, có thể giữ việc, điều kiện vận
hành và đầu vào còn thiếu — CHỈ ĐỌC, 0 USD, không gọi model. (Tên `before_run` vì core/preflight.py đã là kiểm IP / nội dung.)

collect(conn, data_dir, pid) -> {"groups": [{"key", "title", "items": [{"level": 'do'|'vang'|'info', "text", "fix"}]}], "counts"}.
Không ném lỗi: phần nào đọc lỗi → mục 'info' nói rõ không đọc được (docs/CHUAN_XAY_DUNG.md: không im lặng khi thiếu đầu vào).
Đọc bảng scenes MỘT lần cho cả khung (vẽ lại mỗi lượt rerun của Bước 1)."""
import json
import unicodedata
from typing import Dict, List, Optional

GROUPS = (("cost", "💵 Cờ tốn tiền đang bật"), ("hold", "⛔ Thứ có thể giữ việc"), ("ops", "⚙ Điều kiện vận hành"),
          ("inputs", "📥 Đầu vào còn thiếu"))
WHERE_FLAGS = "🧪 Tính năng thử (⚙ Cài đặt) — tắt cờ nếu không muốn trả"
WHERE_KHO = "📚 Kho → mở vật → hồ sơ chuẩn"

# Cờ đổi lời gọi tốn tiền: (khâu Claude để ước tính bằng core.cost.llm_estimate, số ảnh gửi kèm, đơn vị) hoặc chữ khi không có số sẵn.
PAID_FLAGS: Dict[str, Dict] = {
    "change_review": {"stage": "change_review", "unit": "thay đổi shot, không trần (mỗi thay đổi một lời gọi Claude)"},
    "director_rewrite": {"stage": "director_rewrite", "images": 1, "unit": "lần gen lại có ghi chú / lỗi QC (Claude viết lại prompt)"},
    "two_tier_quality": {"text": "video nháp 480p rồi bản cao — giá từng clip xem ở ước tính Bước 4; bản cuối chưa chạy thật lần nào"},
    "stage_camera": {"text": "không thêm lời gọi tốn tiền (render Blender 0 USD) nhưng đổi nền 3D gửi model ảnh — ảnh vẽ trên nền này "
                             "vẫn tính tiền như thường"},
    "director_camera_plan": {"text": "thêm lời gọi Claude (sơ đồ cảnh + duyệt render từng góc) — chưa có số ước tính sẵn"},
}

OPS_LINES = (
    ("Phải mở và đăng nhập Dashboard thì vòng nền (chạy tự động, Tổ rà soát, gen đang xếp hàng) mới chạy — đóng trình duyệt / tắt "
     "Dashboard là vòng nền dừng.", "Giữ một cửa sổ Dashboard đã đăng nhập trong lúc chạy"),
    ("Sau mỗi lần cập nhật code phải khởi động lại Dashboard — tiến trình cũ vẫn chạy code cũ.", "Tắt rồi mở lại Dashboard"),
    ("Ngân sách dự án chỉ cảnh báo, không chặn ảnh / clip bạn tự bấm gen (chỉ chạy tự động ở mức 'Tự chạy trong trần' dừng khi chạm trần).",
     "Theo dõi số đã chi ở thẻ ③ Chạy"),
)


def _item(level: str, text: str, fix: str = "") -> Dict:
    return {"level": level, "text": text, "fix": fix}


def _unreadable(what: str, e: Exception) -> Dict:
    return _item("info", f"Không đọc được {what}: {type(e).__name__}: {str(e)[:160]}", "Báo lại lỗi này (khung chỉ đọc, không chặn gì)")


def _loads(s) -> Dict:
    try:
        d = json.loads(s or "{}")
    except (ValueError, TypeError):
        return {}
    return d if isinstance(d, dict) else {}


def _key(text: str) -> str:
    """Giữ dấu (NFC, chữ thường, một khoảng trắng) — so tên CÓ dấu trước, tránh 'Ông' khớp nhầm 'Ong'."""
    return " ".join(unicodedata.normalize("NFC", str(text or "")).casefold().split())


# ---- 1. cờ tốn tiền ------------------------------------------------------------------------------------------------------------
def _short_label(label: str, n: int = 90) -> str:
    first = label.split(":")[0].strip()
    return first if len(first) <= n else first[: n - 1].rstrip() + "…"


def _cost_items(conn) -> List[Dict]:
    from . import cost, features
    out = []
    for name, spec in PAID_FLAGS.items():
        if name not in features.FEATURES or not features.on(name):
            continue
        label = _short_label(features.FEATURES[name]["label"])
        if "stage" in spec:
            try:
                usd = cost.llm_estimate(conn, spec["stage"], 1, images=spec.get("images", 0))
            except Exception:  # noqa: BLE001 - the flag is still listed, only the number is missing
                usd = None
            money = f"≈ {usd:.2f} USD / {spec['unit']} (ước tính)" if usd is not None else f"chưa có giá Claude — tính theo {spec['unit']}"
        else:
            money = spec["text"]
        out.append(_item("vang", f"`{name}` — {label}: {money}", WHERE_FLAGS))
    others = [k for k in features.on_unverified() if k not in PAID_FLAGS]
    if others:
        out.append(_item("info", f"{len(others)} cờ chưa thử thật khác đang bật: " + ", ".join(others[:12])
                         + (f" (+{len(others) - 12})" if len(others) > 12 else ""), WHERE_FLAGS))
    return out


# ---- 2. thứ có thể giữ việc -------------------------------------------------------------------------------------------------------
def _review_items(conn, pid: int) -> List[Dict]:
    from . import change_review
    try:
        rows = change_review.open_findings(conn, pid)
    except Exception as e:  # noqa: BLE001 - old database without the table
        if "no such table" in str(e):
            return [_item("info", "Tổ rà soát tác động: chưa có bảng change_findings trên CSDL này — chưa có mục nào", "")]
        return [_unreadable("mục Tổ rà soát tác động", e)]
    on = change_review.enabled()
    red = [r for r in rows if r.get("level") == "do"]
    out = []
    loose = [r for r in red if r.get("scene_id") is None]             # mục không gắn shot: blocking() (theo scene_id) không giữ
    red = [r for r in red if r.get("scene_id") is not None]
    if loose:
        out.append(_item("vang", f"{len(loose)} mục đỏ Tổ rà soát không gắn shot nào — không giữ gen, xem 📥 Việc cần bạn",
                         "📥 Việc cần bạn"))
    if red:
        shots = sorted({r["idx"] for r in red if r.get("idx") is not None})
        where = (" ở shot " + ", ".join(str(s) for s in shots[:10]) + (" …" if len(shots) > 10 else "")) if shots else ""
        if on:
            out.append(_item("do", f"{len(red)} mục đỏ Tổ rà soát còn mở{where} — gen tốn tiền của các shot này bị giữ",
                             "📥 Việc cần bạn: sửa shot rồi gen, hoặc bấm Bỏ qua"))
        else:
            out.append(_item("info", f"{len(red)} mục đỏ Tổ rà soát còn mở{where} — cờ change_review đang tắt nên không giữ gen",
                             "📥 Việc cần bạn"))
    try:
        wait = conn.execute("SELECT COUNT(*) FROM change_events WHERE project_id=? AND state='pending' AND scene_id IS NOT NULL",
                            (pid,)).fetchone()[0]
    except Exception:  # noqa: BLE001 - old database: nothing waits
        wait = 0
    if wait and on:
        out.append(_item("info", f"{wait} thay đổi đang chờ Tổ rà soát — shot liên quan chờ rà xong (vài chục giây, cần Dashboard mở)", ""))
    return out


def _budget_items(conn, pid: int) -> List[Dict]:
    from . import project_budget
    from .pipeline import Pipeline
    if not project_budget.enabled():
        return []
    data = project_budget.get(conn, pid) or {}
    total = float(data.get("total") or 0.0)
    if data.get("locked") and total:
        try:
            spent = sum(project_budget.spent_by_stage(conn, pid).values())
        except Exception as e:  # noqa: BLE001
            return [_unreadable("số đã chi của dự án", e)]
        if spent >= total:
            return [_item("do", f"Đã chạm trần ngân sách dự án ({spent:.2f} / {total:.2f} USD) — chạy tự động dừng chờ bạn nâng trần",
                          "Thẻ ③ Chạy: nâng trần kèm lý do rồi bấm Tiếp tục")]
        return []
    try:
        need = project_budget.needs_lock(Pipeline(conn), pid) and not project_budget.finished(conn, pid)
    except Exception as e:  # noqa: BLE001
        return [_unreadable("trạng thái khóa ngân sách", e)]
    if need:
        return [_item("vang", "Ngân sách dự án chưa duyệt & khóa — mức 'Tự chạy trong trần': chạy tự động chờ bước này trước khi gen ảnh",
                      "Nút chính ở đầu Bước 1 (✔ Duyệt & khóa trần ngân sách)")]
    return []


LIVE_JOB = ("queued", "running", "retryable")                         # job gen ảnh neo còn đang chạy (chưa có ảnh)


def _storyboard_items(conn, data_dir: str, pid: int, scenes: List[Dict]) -> List[Dict]:
    """Chế độ storyboard (cờ storyboard_api): shot không phải neo chờ ảnh neo của cảnh; neo chưa có việc gen nào → chờ mãi."""
    from . import scene_storyboard
    if not scene_storyboard.enabled():
        return []
    groups: Dict = {}
    for s in scenes:
        d = s["data"]
        if d.get("story_scene") and d.get("shot_no"):
            groups.setdefault(d["story_scene"], []).append(s)
    stuck, waiting = [], 0
    for key, shots in groups.items():
        if len(shots) < 2:
            continue
        anchor = scene_storyboard.anchor_of(shots)
        if scene_storyboard.anchor_picture(conn, data_dir, pid, anchor["id"]) is not None:
            continue
        g = {"shots": shots, "anchor": anchor, "story_scene": key}
        users = [s for s in shots if scene_storyboard.uses_anchor(g, s["id"])]
        if not users:
            continue
        live = conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state IN (" + ",".join("?" * len(LIVE_JOB))
                            + ")", (anchor["id"], *LIVE_JOB)).fetchone()
        if live:
            waiting += len(users)
        else:
            stuck.append((anchor["idx"], len(users)))
    out = []
    if stuck:
        out.append(_item("do", "Chế độ storyboard: " + "; ".join(f"{n} shot chờ ảnh neo shot {a} mà shot {a} chưa có job gen đang chạy" for a, n in stuck)
                         + " — các ảnh này chờ mãi", "Bước 2: gen ảnh shot neo trước (thêm vào gen thử / ▶ Gen ảnh)"))
    if waiting:
        out.append(_item("info", f"Chế độ storyboard: {waiting} shot chờ ảnh neo đang làm — gửi sau khi có ảnh neo", ""))
    return out


# ---- 4. đầu vào còn thiếu ---------------------------------------------------------------------------------------------------------
def _names(row: Dict) -> List[str]:
    import re
    return [n for n in [row["name"]] + re.split(r"[,;|]", row.get("aliases") or "") if n.strip()]


def _match(pool: List[Dict], name: str) -> Optional[Dict]:
    """Nhân vật trong shot ('KELLY') → vật Kho của dự án: cùng tên / tên gọi khác CÓ dấu trước; bỏ dấu chỉ khi đúng MỘT ứng viên."""
    from . import assets
    k = _key(name)
    for a in pool:
        if k in {_key(n) for n in _names(a)}:
            return a
    f = assets.fold(name)
    close = [a for a in pool if f and f in {assets.fold(n) for n in _names(a)}]
    return close[0] if len(close) == 1 else None


def _input_items(conn, pid: int, scenes: List[Dict]) -> List[Dict]:
    from . import assets, location_pack
    rows = [dict(r) for r in conn.execute("SELECT a.id, a.kind, a.name, a.aliases, a.profile FROM assets a JOIN project_assets pa "
                                          "ON pa.asset_id=a.id WHERE pa.project_id=?", (pid,))]
    by_id = {r["id"]: r for r in rows}
    people = [r for r in rows if r["kind"] in ("character", "pet")]
    used: Dict[int, List[int]] = {}                                   # asset id → số thứ tự shot
    places: Dict[int, List[int]] = {}
    unknown: Dict[str, List[int]] = {}                                # tên nhân vật trong shot không có trong Kho của dự án
    for s in scenes:
        d = s["data"]
        for n in d.get("characters") or []:
            if not isinstance(n, str) or not n.strip():
                continue
            a = _match(people, n)
            if a:
                used.setdefault(a["id"], []).append(s["idx"])
            else:
                unknown.setdefault(n.strip(), []).append(s["idx"])
        lid = d.get("location_asset")
        if isinstance(lid, int) and not isinstance(lid, bool) and lid > 0:
            places.setdefault(lid, []).append(s["idx"])
    missing = [lid for lid in places if lid not in by_id]
    if missing:
        for r in conn.execute("SELECT id, kind, name, aliases, profile FROM assets WHERE id IN (" + ",".join("?" * len(missing)) + ")",
                              missing):
            by_id[r["id"]] = dict(r)

    def shots(ids: List[int]) -> str:
        ids = sorted(set(ids))
        return "shot " + ", ".join(str(i) for i in ids[:8]) + (" …" if len(ids) > 8 else "")

    out = []
    for name, idxs in unknown.items():
        out.append(_item("vang", f"'{name}' không có trong Kho của dự án — ảnh vẽ theo chữ mô tả, dễ lệch giữa các shot ({shots(idxs)})",
                         "📚 Kho: thêm / gắn nhân vật vào dự án (hoặc sửa tên trong shot)"))
    for lid, idxs in places.items():
        if lid not in by_id:
            out.append(_item("vang", f"Shot ghi bối cảnh Kho #{lid} nhưng Kho không có mã này ({shots(idxs)})",
                             "Bước 1 · thẻ ② Director / sửa shot: chọn lại địa điểm"))
    for aid, idxs in used.items():                                    # must_keep chỉ cho nhân vật / pet (như core/change_audit)
        a = by_id[aid]
        if not str(_loads(a["profile"]).get("must_keep") or "").strip():
            out.append(_item("vang", f"{a['name']} (Kho #{aid}) chưa có `must_keep` trong hồ sơ chuẩn — model dễ vẽ lệch ({shots(idxs)})",
                             WHERE_KHO + " → Character Lock / phải giữ"))
    for lid, idxs in places.items():
        a = by_id.get(lid)
        if a is not None and a["kind"] == "location" and not location_pack.model3d(conn, lid):
            out.append(_item("vang", f"Bối cảnh {a['name']} (Kho #{lid}) chỉ có ảnh, chưa có sân khấu 3D — nền vẽ theo ảnh, góc máy "
                                     f"không đo được ({shots(idxs)})", "📚 Kho → bối cảnh → gắn model 3D (location_pack)"))
    if any(r["kind"] in assets.SIZED_KINDS and not _loads(r["profile"]).get("height_m") for r in rows):
        from . import place_refs
        seen: Dict[str, List[int]] = {}
        for s in scenes:
            for a in place_refs.shot_objects(conn, pid, s["data"]):
                if not (a.get("size") or {}).get("height_m"):
                    seen.setdefault(a["name"], []).append(s["idx"])
        for name, idxs in seen.items():
            out.append(_item("vang", f"Vật {name} chưa có kích thước thật (height_m) — model tự đoán, tỉ lệ dễ lệch giữa các shot "
                                     f"({shots(idxs)})", "📚 Kho → vật → kích thước thật"))
    return out


# ---- gom ------------------------------------------------------------------------------------------------------------------------
def collect(conn, data_dir: str, pid: int) -> Dict:
    """Mọi nhóm của khung; mỗi phần lỗi riêng thành mục 'info', không ném. Trong một lượt vẽ Dashboard (core.memo.per_rerun) tính
    một lần cho mỗi trạng thái CSDL."""
    from .memo import cached
    return cached(conn, ("before_run", pid, data_dir), lambda: _collect(conn, data_dir, pid))


def _collect(conn, data_dir: str, pid: int) -> Dict:
    items: Dict[str, List[Dict]] = {k: [] for k, _ in GROUPS}
    try:
        scenes = [{"id": r["id"], "idx": r["idx"], "data": _loads(r["data"])}
                  for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]
    except Exception as e:  # noqa: BLE001
        scenes = []
        items["inputs"].append(_unreadable("danh sách shot", e))
    for group, what, fn in (("cost", "cờ tính năng", lambda: _cost_items(conn)),
                            ("hold", "mục Tổ rà soát", lambda: _review_items(conn, pid)),
                            ("hold", "ngân sách dự án", lambda: _budget_items(conn, pid)),
                            ("hold", "chế độ storyboard", lambda: _storyboard_items(conn, data_dir, pid, scenes)),
                            ("inputs", "hồ sơ Kho của dự án", lambda: _input_items(conn, pid, scenes))):
        try:
            items[group] += fn()
        except Exception as e:  # noqa: BLE001 - the frame is information: one part failing is said, never breaks Bước 1
            items[group].append(_unreadable(what, e))
    items["ops"] = [_item("info", t, f) for t, f in OPS_LINES]
    groups = [{"key": k, "title": t, "items": items[k]} for k, t in GROUPS]
    counts = {lv: sum(1 for g in groups for i in g["items"] if i["level"] == lv) for lv in ("do", "vang", "info")}
    return {"groups": groups, "counts": counts}


def title(res: Dict) -> str:
    c = res.get("counts") or {}
    parts = [f"{c[k]} {w}" for k, w in (("do", "đỏ"), ("vang", "cần chú ý")) if c.get(k)]
    return "🧭 Trước khi chạy — " + (" · ".join(parts) if parts else "không có gì cần chú ý")


def details_md(res: Dict) -> str:
    icon = {"do": "🔴", "vang": "🟡", "info": "ℹ️"}
    lines = []
    for g in res.get("groups") or []:
        lines.append(f"**{g['title']}**")
        if not g["items"]:
            lines.append("- không có")
        for it in g["items"]:
            lines.append(f"- {icon.get(it['level'], '•')} {it['text']}" + (f" — *sửa ở: {it['fix']}*" if it.get("fix") else ""))
        lines.append("")
    return "\n".join(lines)
