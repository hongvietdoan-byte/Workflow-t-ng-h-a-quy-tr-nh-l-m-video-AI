"""Thử gộp nhiều shot vào một lần gen video — P1 / P2 / P3 của docs/PHAN_TICH_GOP_SHOT_2026-09-27.md. KHÔNG gọi Claude.

    py tools/experiments/group_test.py --project 8 --scene 2 frames      vẽ khung đầu các shot của cảnh (Deepix, như Bước 2, không QC Claude)
    py tools/experiments/group_test.py --project 8 --scene 2 plan        in prompt + giây + giá từng lần gen (không gửi gì)
    py tools/experiments/group_test.py --project 8 --scene 2 submit      gửi P1, P2, P3 (qua trần tiền + sổ chi như dashboard)
    py tools/experiments/group_test.py --project 8 poll                  hỏi trạng thái, tải clip về <data>/<pid>/experiments/

Chạy từ thư mục dashboard (D:\\AI-Video-Pipeline): đọc dashboard.env + khóa API trong môi trường người dùng như Start-Dashboard.bat.
Kết quả ghi vào <data>/<pid>/experiments/experiments.json (kind "group_test") — hiện ở Bước 4 → 🧪 Thử nghiệm.
  P1  Seedance Fast: khung đầu = ảnh shot đầu nhóm, khung cuối = ảnh shot cuối nhóm, prompt "Shot 1: … Shot N: …"
  P2  Seedance Fast: CHỈ ảnh tham chiếu — ảnh từng shot (Image 1..N) + ảnh danh tính nhân vật, không khung đầu
  P3  Kling std multi-shot: khung đầu nhóm + multi_prompt (mỗi shot ≥ 3 s — luật Kling)
  P4  Kling std khung đầu + khung cuối (một đường máy liền) — để có bằng chứng: nội suy hai góc khác nhau ra cắt hay ra biến hình
  P2m như P2 nhưng ảnh tham chiếu được đánh dấu "CHARACTER SHEET REFERENCE" + dấu cộng đỏ trên một mắt (cách qua bộ lọc người thật
      của Seedance — viraltwin.app; ByteDance: ảnh tham chiếu nhân vật hư cấu) — chỉ hợp chế độ tham chiếu (dấu không được lọt vào khung đầu)
  S2  không gộp: mỗi shot một clip Kling std, khung đầu = ảnh storyboard của shot (mốc so sánh chất lượng + tiền)
  S3  lai: Kling multi-shot chỉ cho các shot liền nhau có CÙNG bộ nhân vật; còn lại dùng clip S2
Chọn phương án: --methods P2m,S2,S3 (mặc định P1,P2,P3,P4).
"""
import argparse
import json
import math
import os
import sys
import time
from typing import Optional
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

GROUP_SHOTS = 3          # tài liệu Seedance: 2–4 shot mỗi lần gen
METHODS = ("P1", "P2", "P3", "P4")
MODELS = {"P1": ("seedance-fast", "720p"), "P2": ("seedance-fast", "720p"), "P3": ("kling", "std"), "P4": ("kling", "std"),
          "P2m": ("seedance-fast", "720p"), "S2": ("kling", "std"), "S3": ("kling", "std")}
KLING_PROMPT = 500           # Kling single-shot prompt budget used by the adapter


def load_env(root: str) -> None:
    """dashboard.env (không bí mật) + CLIPAI_TOKEN / DEEPIX_TOKEN / ANTHROPIC_API_KEY từ môi trường người dùng — như launcher."""
    path = os.path.join(root, "dashboard.env")
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                t = line.strip()
                if t and not t.startswith("#") and "=" in t:
                    k, v = t.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"'))
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                for name in ("CLIPAI_TOKEN", "DEEPIX_TOKEN", "ANTHROPIC_API_KEY"):
                    if not os.environ.get(name):
                        try:
                            os.environ[name] = winreg.QueryValueEx(key, name)[0]
                        except OSError:
                            pass
        except OSError:
            pass


def shots_of_scene(p, pid: int, scene: int):
    rows = []
    for r in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)):
        d = json.loads(r["data"] or "{}")
        if d.get("story_scene") == scene:
            rows.append({"id": r["id"], "idx": r["idx"], "data": d})
    return rows


def groups(rows):
    return [rows[i:i + GROUP_SHOTS] for i in range(0, len(rows), GROUP_SHOTS)]


def frame_path(p, data_dir: str, pid: int, scene_id: int):
    row = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state IN ('succeeded','approved','pending_review')"
                         " ORDER BY id DESC LIMIT 1", (scene_id,)).fetchone()
    if row is None:
        return None
    path = os.path.join(data_dir, str(pid), "images", f"job_{row['id']}.png")
    return path if os.path.exists(path) else None


def shot_text(d: dict, i: int) -> str:
    """One shot of a grouped prompt, from the Director's own fields (English picture words; the Vietnamese action as the event)."""
    from core.shots import SIZE_WORDS
    perf = d.get("performance") if isinstance(d.get("performance"), dict) else {}
    acting = "; ".join(f"{k}: {perf[k]}" for k in ("face", "eyes", "body", "timing") if perf.get(k))
    talk = " ".join(f"{x.get('speaker')} speaks (mouth moving, no sound)." for x in d.get("dialogue") or [] if isinstance(x, dict))
    move = str(d.get("camera_move") or "static").replace("_", " ")
    return (f"Shot {i} ({SIZE_WORDS.get(d.get('size'), d.get('size'))}, {d.get('angle', 'eye')} angle, camera {move}, "
            f"about {float(d.get('duration_s') or 2):.1f} s): {str(d.get('image_prompt') or '').strip().rstrip('.')}. "
            + (f"Acting — {acting}. " if acting else "") + talk).strip()


def mark_reference(path: str, out_dir: Optional[str] = None) -> str:
    """A copy of the picture (in out_dir, default beside it) marked as reference material: a white banner "CHARACTER SHEET REFERENCE"
    on top and a thick red plus sign over one eye of every face found (YuNet; none found: the upper middle). Only for reference-only
    sends. The pipeline's own marking (core.seedance_refs.mark) — one implementation for the test and the real run."""
    from core import seedance_refs
    return seedance_refs.mark(path, out_dir or os.path.dirname(path))


def s3_groups(rows):
    """S3: consecutive shots with the same set of characters go together (≤ 3), the rest alone."""
    out, cur = [], []
    for r in rows:
        key = tuple(sorted(r["data"].get("characters") or []))
        if cur and key == tuple(sorted(cur[-1]["data"].get("characters") or [])) and len(cur) < GROUP_SHOTS:
            cur.append(r)
            continue
        if cur:
            out.append(cur)
        cur = [r]
    return out + ([cur] if cur else [])


def build(p, data_dir: str, pid: int, group, method: str, look: str):
    """(kwargs for provider.submit, seconds, prompt) of one grouped generation."""
    from core import assets
    frames = [frame_path(p, data_dir, pid, r["id"]) for r in group]
    if not all(frames):
        raise SystemExit("thiếu ảnh khung của một shot — chạy bước 'frames' trước")
    film = sum(float(r["data"].get("duration_s") or 0) for r in group)
    shots = [shot_text(r["data"], i) for i, r in enumerate(group, 1)]
    cut = (f"One clip with {len(group)} shots cut in this order, hard cuts between shots, same place, same light, same "
           f"characters and outfits throughout. {look}")
    if method == "S2":                         # one shot, one Kling clip from its own storyboard frame
        d = group[0]["data"]
        return ({"image_path": frames[0]}, max(3, math.ceil(float(d.get("duration_s") or 3) - 1e-6)),
                (look + " " + shot_text(d, 1).replace("Shot 1 ", "", 1))[:KLING_PROMPT])
    if method in ("P3", "S3"):
        per = [max(3, math.ceil(float(r["data"].get("duration_s") or 3) - 1e-6)) for r in group]
        multi = [{"prompt": (look + " " + s)[:500], "duration": d} for s, d in zip(shots, per)]
        return {"image_path": frames[0], "multi_prompt": multi}, sum(per), "\n".join(m["prompt"] for m in multi)
    if method == "P4":
        seconds = max(3, math.ceil(film - 1e-6))
        short = " ".join(f"Shot {i}: {str(r['data'].get('action') or '').strip()}" for i, r in enumerate(group, 1))
        prompt = (f"{look} Starts on the first image and ends on the last image. {short}")[:KLING_PROMPT]
        return {"image_path": frames[0], "last_frame": frames[-1]}, seconds, prompt
    seconds = max(4, math.ceil(film - 1e-6))
    if method == "P1":
        prompt = cut + "\n" + "\n".join(shots)
        return {"image_path": frames[0], "last_frame": frames[-1]}, seconds, prompt
    # P2: every shot's own storyboard picture + the identity picture of each character in the group
    names = []
    for r in group:
        for n in r["data"].get("characters") or []:
            if n not in names:
                names.append(n)
    links = assets.link_characters(p.conn, pid, names)
    ids = [(n, (links.get(n) or {}).get("ref")) for n in names]
    ids = [(n, ref["path"]) for n, ref in ids if ref and os.path.exists(ref.get("path", ""))][: 9 - len(frames)]
    refs = frames + [path for _, path in ids]
    if method == "P2m":
        marked = os.path.join(data_dir, str(pid), "experiments", "marked")
        refs = [mark_reference(x, marked) for x in refs]
    mapping = " ".join(f"Image {i} is the storyboard frame of Shot {i}: Shot {i} starts with exactly this composition, framing and "
                       f"these character positions." for i in range(1, len(frames) + 1))
    mapping += " " + " ".join(f"Image {len(frames) + k} is {n}: identity only (face, hair, outfit) — not the framing."
                              for k, (n, _) in enumerate(ids, 1))
    prompt = cut + "\n" + mapping + "\n" + "\n".join(shots)
    return {"image_path": frames[0], "reference_only": refs}, seconds, prompt


def cmd_frames(p, data_dir: str, pid: int, scene: int) -> None:
    from core import features, location_pack
    from core.adapters import factory
    from core.runner import ImageRunner
    rows = shots_of_scene(p, pid, scene)
    if features.on("location_plates"):
        location_pack.ensure_photo_plates(p.conn, pid, data_dir)                       # tier 2 plates (free, code only)
        if location_pack.plan(p.conn, pid):
            print("cần nền 3D (Blender) — chạy nền trước:", location_pack.ensure_plates(
                p.conn, pid, data_dir, os.path.dirname(os.path.abspath(data_dir)), log=print).keys())
    for r in rows:
        if not p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen'", (r["id"],)).fetchone():
            p.create_job(r["id"], "image_gen")
    runner = ImageRunner(p, factory.image_provider(), data_dir)
    ids = {r["id"] for r in rows}
    t0 = time.time()
    while time.time() - t0 < 1800:
        runner.submit_pending(pid)
        runner.poll_once(pid)
        states = {r["id"]: r["state"] for r in p.conn.execute("SELECT scene_id id, state FROM jobs WHERE project_id=? AND type='image_gen'",
                                                              (pid,)) if r["id"] in ids}
        print(time.strftime("%H:%M:%S"), states, flush=True)
        if states and all(s in ("succeeded", "approved", "pending_review", "failed", "escalated") for s in states.values()):
            break
        time.sleep(15)
    for r in rows:
        print(r["data"].get("shot_no"), frame_path(p, data_dir, pid, r["id"]))


def cmd_plan(p, data_dir: str, pid: int, scene: int, provider=None, methods=METHODS) -> list:
    from core import budget, cost, looks
    look = looks.image_sentence(p.project(pid)).strip()
    out = []
    rows = shots_of_scene(p, pid, scene)
    plan_groups = {"S2": [[r] for r in rows], "S3": [g for g in s3_groups(rows) if len(g) > 1]}
    for m in methods:
        for gi, group in enumerate(plan_groups.get(m) or groups(rows), 1):
            kwargs, seconds, prompt = build(p, data_dir, pid, group, m, look)
            model, tier = MODELS[m]
            canonical = {"seedance-fast": "dreamina-seedance-2-0-fast-260128", "kling": "kling-v3-omni"}[model]
            usd = cost.clip_price(cost.load_pricing(), canonical, tier, seconds)
            out.append({"method": m, "group": gi, "shots": [r["data"].get("shot_no") for r in group], "model": model, "tier": tier,
                        "canonical": canonical, "seconds": seconds, "usd": usd, "prompt": prompt, "kwargs": kwargs,
                        "film_s": round(sum(float(r["data"].get("duration_s") or 0) for r in group), 2)})
            print(f"{m} nhóm {gi} shot {out[-1]['shots']}: {seconds} s trả tiền / {out[-1]['film_s']} s phim ≈ ${usd:.2f} "
                  f"({len(prompt)} ký tự)")
    print(f"Tổng ≈ ${sum(o['usd'] or 0 for o in out):.2f}; trần: {budget.status(p.conn)['left']} USD còn lại")
    return out


def cmd_submit(p, data_dir: str, pid: int, scene: int, methods=METHODS) -> None:
    from core import budget, experiments, formats
    from core.adapters import factory
    from core.cost import record_usage
    provider = factory.video_provider()
    aspect = formats.spec(formats.project_aspect(p.project(pid)) or "9:16")["clip"]
    items = experiments.load(data_dir, pid)
    done = {(e.get("method"), e.get("group")) for e in items if e.get("kind") == "group_test" and e.get("scene") == scene}
    for o in cmd_plan(p, data_dir, pid, scene, methods=methods):
        if (o["method"], o["group"]) in done:
            print("đã gửi trước đó:", o["method"], o["group"])
            continue
        kwargs = dict(o["kwargs"])
        image = kwargs.pop("image_path")
        tier = o["tier"]
        extra = {"kling_mode": tier} if o["model"] == "kling" else {"resolution": tier}
        from core.providers import ProviderError
        entry = {"kind": "group_test", "scene": scene, "method": o["method"], "group": o["group"], "shots": o["shots"],
                 "seconds": o["seconds"], "film_s": o["film_s"], "model": o["canonical"], "tier": tier, "usd": o["usd"],
                 "prompt": o["prompt"], "external_id": None, "state": "running", "file": None, "sequence": scene,
                 "scenes": o["shots"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        with budget.SPEND_LOCK:
            over = budget.check_video(p.conn, provider.name, o["canonical"], tier, o["seconds"])
            if over:
                print("TRẦN CHẶN:", over)
                return
            try:
                entry["external_id"] = provider.submit(image, o["prompt"] if o["method"] not in ("P3", "S3") else "", None, o["seconds"],
                                                       o["model"], aspect_ratio=aspect, **extra, **kwargs)
                record_usage(p.conn, None, "video", provider.name, o["canonical"], tier, o["seconds"], "second", pid)
            except ProviderError as e:          # refused at creation: nothing billed; kept as a result of the test (not retried)
                entry.update(state="failed", message=f"[{e.code}] {e}"[:400], usd=0.0)
        items.append(entry)
        experiments._save(data_dir, pid, items)
        print(o["method"], o["group"], entry["state"], entry["external_id"] or entry.get("message", "")[:160])


def relink(provider, data_dir: str, pid: int) -> int:
    """Past ClipAI's concurrency limit a create answers with a 12-digit QUEUE id and the real task later gets a new id (W12b): find
    it by the prompt that was sent, created after sending, not tied to another entry. Returns how many were relinked."""
    from core import experiments
    items = experiments.load(data_dir, pid)
    taken = {e.get("external_id") for e in items}
    n = 0
    for e in items:
        ext = e.get("external_id") or ""
        if e.get("kind") != "group_test" or e["state"] not in ("running", "failed") or len(ext.partition(":")[2]) != 12:
            continue
        if e["state"] == "failed" and "không thấy task" not in (e.get("message") or ""):
            continue
        sent = datetime.fromisoformat(e["at"]).timestamp() if e.get("at") else None
        found = getattr(provider, "find_by_prompt", lambda *a, **k: None)(ext, e.get("prompt") or "", sent, taken)
        if found:
            e.update(queue_id=ext, external_id=found, state="running", message=None)
            taken.add(found)
            n += 1
    if n:
        experiments._save(data_dir, pid, items)
    return n


def cmd_poll(p, data_dir: str, pid: int) -> None:
    from core import experiments
    from core.adapters import factory
    provider = factory.video_provider()
    t0 = time.time()
    while time.time() - t0 < 2400:
        if relink(provider, data_dir, pid):
            print("nối lại mã chờ tạm → task thật", flush=True)
        experiments.refresh(provider, data_dir, pid)
        items = [e for e in experiments.load(data_dir, pid) if e.get("kind") == "group_test"]
        print(time.strftime("%H:%M:%S"), [(e["method"], e["group"], e["state"]) for e in items], flush=True)
        if all(e["state"] != "running" for e in items):
            break
        time.sleep(30)
    for e in experiments.load(data_dir, pid):
        if e.get("kind") == "group_test":
            print(e["method"], e["group"], e["state"], e.get("file") or e.get("message"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--scene", type=int, default=2)
    ap.add_argument("step", choices=("frames", "plan", "submit", "poll"))
    ap.add_argument("--methods", default=",".join(METHODS))
    a = ap.parse_args()
    root = os.getcwd()
    load_env(root)
    from core.db import connect
    from core.pipeline import Pipeline
    data_dir = os.environ.get("PIPELINE_DATA") or os.path.join("data", "projects")
    p = Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))
    methods = tuple(x.strip() for x in a.methods.split(",") if x.strip())
    {"frames": lambda: cmd_frames(p, data_dir, a.project, a.scene),
     "plan": lambda: cmd_plan(p, data_dir, a.project, a.scene, methods=methods),
     "submit": lambda: cmd_submit(p, data_dir, a.project, a.scene, methods=methods),
     "poll": lambda: cmd_poll(p, data_dir, a.project)}[a.step]()


if __name__ == "__main__":
    main()
