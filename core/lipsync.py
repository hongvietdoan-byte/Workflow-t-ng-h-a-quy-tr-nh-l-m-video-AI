"""Lip sync for the whole video (kế hoạch V4 GĐ3; research: docs/NGHIEN_CUU_KHOP_MOI.md). Feature `lip_sync`, off until tested.

Every shot where a line is spoken and the speaker's face can be seen gets its mouth matched to OUR Vietnamese voice line:
  "generate"  Seedance draws the clip speaking to the line (reference_audio at generation) — for the close-ups the Director marks
              `lip_sync: true` (the most visible mouths; Seedance 2.0 720p $0.15/s)
  "post"      the finished clip's mouth is redrawn to the line by a lip-sync service (sync.so lipsync-2-pro ~ $0.084/s) — works on
              any model's clip, any language (driven by the sound), 3D / AI video; the rest of the frame is kept (location packs stay)
  "take"      (feature dialogue_take, S4.2 — option (c) of the S4.6 A/B) the shot goes in its Seedance 2.5 reference GROUP clip with ONE
              voice track of every voiced line of the group at its second of the clip, the lines + speakers + seconds written in the
              prompt (core/dialogue_take.group_block); a shot alone gets its own line the same way. Any shot where a speaker's face
              is seen — medium and two-person shots too, which had no lip sync without sync.so
  "skip"      nobody speaks, the speaker has their back to the camera / is off screen, or a wide shot
Both need the shot's own audio: `shot_audio` cuts it from the voiced lines, placed at the same seconds the final timeline uses
(voice.LEAD / GAP), padded with silence to the clip's length; `voice.place_on_timeline` keeps those exact seconds for a lip-synced shot.
"""
import json
import os
import subprocess
import time
from typing import Dict, List, Optional

from . import audio_lib, dialogue, features, voice

FEATURE = "lip_sync"
_NO_FACE = ("EWS", "GAME_TPS")
_CLOSE = ("ECU", "CU", "MCU")
# How long a sent post lip sync may stay 'running' before it is given up (the clip keeps its mouth, said): sync.so answers in minutes;
# a task 'COMPLETED' without an outputUrl is reported as running by the adapter and used to be polled forever (S14.3 B1b).
RUNNING_LIMIT_S = float(os.environ.get("LIPSYNC_RUNNING_LIMIT_MIN", "60")) * 60


def enabled() -> bool:
    return features.on(FEATURE)


def post_available() -> bool:
    """Post lip sync needs a sync.so key. The user decided (2026-09-26) not to open a sync.so account: lip sync goes through Seedance
    "generate with the voice" (reference_audio) only, so without SYNC_API_KEY no shot is ever planned as "post"."""
    return bool(os.environ.get("SYNC_API_KEY", "").strip())


def method_for(data: Dict, post_ok: Optional[bool] = None) -> str:
    """How this shot's mouth gets matched (see module doc). post_ok None = whether a sync.so key is set (post_available). Without
    post lip sync, a close shot (CU/ECU/MCU) that sees the speaker's face is made WITH the voice (Seedance reference_audio); a wider
    one keeps the clip's own mouth ("skip" — the mouth is small there)."""
    post_ok = post_available() if post_ok is None else post_ok
    method = _method(data)
    if method in ("post", "generate") and take_on():
        return "take"
    if method == "post" and not post_ok:
        return "generate" if str(data.get("size") or "MS").upper() in _CLOSE else "skip"
    return method


def take_on() -> bool:
    return features.on("dialogue_take")


def voiced(method: str) -> bool:
    """The clip is made WITH the voice (Seedance reference_audio): "generate" (one shot) or "take" (the group's dialogue track)."""
    return method in ("generate", "take")


def no_post_note(data: Dict) -> Optional[str]:
    """The Bước 4 / diag note of a shot that would have been post-synced (sync.so) but no key is set, else None."""
    if post_available() or _method(data) != "post":
        return None
    how = method_for(data, post_ok=False)
    return ("khớp môi sau cần sync.so — không dùng; shot này " + ("tạo video kèm giọng (Seedance reference_audio)" if how == "generate"
                                                                 else "để nguyên miệng của clip (cỡ cảnh rộng, miệng nhỏ)"))


def _method(data: Dict) -> str:
    lines = dialogue.scene_lines(data)
    if not lines:
        return "skip"
    speakers = {str(s).upper() for s, _ in lines}
    cast = {str(c).upper() for c in (data.get("characters") or [])}
    if cast and not (speakers & cast):
        return "skip"                                             # the speaker is off screen (voice over another shot)
    size = str(data.get("size") or "MS").upper()
    words = f"{data.get('start_frame') or ''} {data.get('blocking') or ''}".lower()
    if size in _NO_FACE or any(w in words for w in ("back to camera", "from behind", "quay lưng")):
        return "skip"
    if data.get("lip_sync") is False:
        return "skip"
    if data.get("lip_sync") == "generate" or (data.get("lip_sync") is True and size in _CLOSE):
        return "generate"
    return "post"


def _dir(data_dir: str, pid: int) -> str:
    d = os.path.join(data_dir, str(pid), "lipsync")
    os.makedirs(d, exist_ok=True)
    return d


def index(data_dir: str, pid: int) -> Dict[str, Dict]:
    try:
        with open(os.path.join(data_dir, str(pid), "lipsync", "index.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(data_dir: str, pid: int, idx: Dict) -> None:
    with open(os.path.join(_dir(data_dir, pid), "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)


def mark(data_dir: str, pid: int, scene_id: int, **fields) -> None:
    idx = index(data_dir, pid)
    idx[str(scene_id)] = {**idx.get(str(scene_id), {}), **fields}
    _save(data_dir, pid, idx)


def synced_scene_ids(data_dir: str, pid: int) -> set:
    """Shots whose clip speaks to its line (their voice must stay at the exact seconds of the segment)."""
    return {int(k) for k, v in index(data_dir, pid).items() if v.get("state") == "done"}


def line_offsets(entries: List[Dict]) -> List[float]:
    """Where each line starts inside its shot — the same rule as voice.place_on_timeline for a shot whose previous shot is quiet."""
    out, cursor = [], voice.LEAD
    for e in entries:
        out.append(round(cursor, 3))
        cursor += (e.get("duration_ms") or 0) / 1000.0 + voice.GAP
    return out


def shot_lines(data_dir: str, pid: int, scene_id: int) -> List[Dict]:
    items = audio_lib.load(audio_lib.assets_dir(data_dir, pid))
    return sorted([e for e in items if e.get("kind") == "tts" and e.get("scene_id") == scene_id and e.get("state") == "succeeded"
                   and e.get("file")], key=lambda e: e.get("line") or 0)


def shot_audio(data_dir: str, pid: int, scene_id: int, length_s: float, ffmpeg: str) -> Optional[Dict]:
    """The shot's voice as one file of the clip's length: each line at its offset, silence around. None when no line is voiced."""
    lines = shot_lines(data_dir, pid, scene_id)
    if not lines:
        return None
    offsets = line_offsets(lines)
    adir = audio_lib.assets_dir(data_dir, pid)
    out = os.path.join(_dir(data_dir, pid), f"shot_{scene_id}.wav")
    cmd = [ffmpeg, "-y", "-loglevel", "error"]
    for e in lines:
        cmd += ["-i", os.path.join(adir, e["file"])]
    parts = "".join(f"[{i}:a]adelay={int(o * 1000)}|{int(o * 1000)},aresample=44100[a{i}];" for i, o in enumerate(offsets))
    mix = "".join(f"[a{i}]" for i in range(len(lines)))
    flt = parts + f"{mix}amix=inputs={len(lines)}:normalize=0,apad,atrim=0:{max(length_s, offsets[-1] + 0.5):.3f}[out]"
    cmd += ["-filter_complex", flt, "-map", "[out]", "-ac", "1", "-ar", "44100", out]
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if proc.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(f"không cắt được giọng của shot: {(proc.stderr or '')[-300:]}")
    return {"path": out, "offsets": offsets, "lines": [e.get("line") for e in lines], "seconds": round(length_s, 2)}


def plan(conn, pid: int) -> List[Dict]:
    """[{scene_id, idx, method}] for every shot (the dashboard / director report show the split)."""
    out = []
    for s in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        out.append({"scene_id": s["id"], "idx": s["idx"], "method": method_for(json.loads(s["data"] or "{}"))})
    return out


# ---- post lip sync on finished clips ------------------------------------------------------------------------------------------
def post_tick(p, pid: int, data_dir: str, provider, ffmpeg: str, log=lambda m: None) -> Dict[str, int]:
    """Send every finished clip of a "post" shot (its voice is ready) to the lip-sync provider once, poll, and put the synced clip in
    place of the clip (the original kept as <idx>_prelipsync.mp4). Each send goes through the money gate (core.spend_gate: paused
    project → PipelinePaused, trial caps, the project's locked 'videos' budget; ledger kind video, label 'lipsync', seconds); a task
    still 'running' after RUNNING_LIMIT_S is given up with a note."""
    from . import diag, spend_gate
    from .providers import ProviderError
    counts = {"sent": 0, "done": 0, "failed": 0, "running": 0}
    idx = index(data_dir, pid)

    def say(severity: str, code: str, message: str, scene_id: int, job_id=None) -> None:
        diag.record(p.conn, "video", severity, message, code, pid, scene_id, job_id)

    for s in conn_rows(p, pid):
        data = json.loads(s["data"] or "{}")
        if method_for(data, post_ok=True) != "post":
            continue
        rec = idx.get(str(s["id"])) or {}
        job = p.conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN ('succeeded','approved')"
                             " ORDER BY id DESC LIMIT 1", (s["id"],)).fetchone()
        if job is None or not job["result_path"] or not os.path.exists(job["result_path"]):
            continue
        if rec.get("state") == "done" and rec.get("job_id") == job["id"]:
            continue
        if rec.get("state") == "running" and rec.get("job_id") == job["id"]:
            sent_at = rec.get("sent_at")
            if not isinstance(sent_at, (int, float)):            # a record from before the time limit: its clock starts now
                mark(data_dir, pid, s["id"], sent_at=time.time())
            elif time.time() - sent_at > RUNNING_LIMIT_S:
                mins = int(RUNNING_LIMIT_S // 60)
                msg = (f"khớp môi shot {s['idx']}: quá hạn chờ {mins} phút mà sync.so chưa trả kết quả (task {rec.get('task')}; "
                       "trạng thái COMPLETED thiếu outputUrl cũng tính là đang chờ) — bỏ, giữ clip gốc; kiểm task trên sync.so, "
                       f"đổi hạn bằng LIPSYNC_RUNNING_LIMIT_MIN")
                mark(data_dir, pid, s["id"], state="failed", error=msg)
                say("error", "lipsync_timeout", msg, s["id"], job["id"])
                log(f"Khớp môi shot {s['idx']}: quá hạn chờ — giữ clip gốc")
                counts["failed"] += 1
                continue
            try:
                st = provider.status(rec["task"])
            except ProviderError as e:                            # one network error must not put the whole run in ERROR
                say("warn" if e.transient else "error", e.code or "lipsync_status", f"khớp môi shot {s['idx']}: hỏi trạng thái lỗi ({e})"
                    + (" — sẽ hỏi lại" if e.transient else ""), s["id"], job["id"])
                if not e.transient:
                    mark(data_dir, pid, s["id"], state="failed", error=str(e))
                    counts["failed"] += 1
                else:
                    counts["running"] += 1
                continue
            if st.state == "succeeded":
                target = job["result_path"]
                raw = os.path.splitext(target)[0] + "_prelipsync.mp4"
                tmp = os.path.splitext(target)[0] + "_lipsync_dl.mp4"
                try:                                              # download FIRST: a failed download must never lose the clip
                    got = provider.download(rec["task"], tmp) or tmp
                except ProviderError as e:
                    say("warn" if e.transient else "error", e.code or "lipsync_download", f"khớp môi shot {s['idx']}: tải kết quả lỗi "
                        f"({e}) — clip gốc giữ nguyên" + (", sẽ tải lại" if e.transient else ""), s["id"], job["id"])
                    if not e.transient:
                        mark(data_dir, pid, s["id"], state="failed", error=str(e))
                        counts["failed"] += 1
                    else:
                        counts["running"] += 1
                    if os.path.exists(tmp):
                        os.remove(tmp)
                    continue
                if not os.path.exists(raw):
                    os.replace(target, raw)                        # the original is kept as <idx>_prelipsync.mp4
                os.replace(got, target)
                mark(data_dir, pid, s["id"], state="done", original=raw)
                counts["done"] += 1
                log(f"Khớp môi xong shot {s['idx']}")
            elif st.state == "failed":
                mark(data_dir, pid, s["id"], state="failed", error=st.error_message)
                say("warn", "lipsync_failed", f"khớp môi shot {s['idx']} thất bại ({st.error_message}) — giữ clip gốc", s["id"], job["id"])
                counts["failed"] += 1
            else:
                counts["running"] += 1
            continue
        if rec.get("state") == "failed" and rec.get("job_id") == job["id"]:
            continue                                              # said once; a new clip (new job) is tried again
        from .final_cut import clip_seconds
        length = clip_seconds(job["result_path"], None) or 5.0
        try:
            seg = shot_audio(data_dir, pid, s["id"], length, ffmpeg)
        except Exception as e:  # noqa: BLE001 - ffmpeg could not cut the voice: said, the clip keeps its mouth
            say("warn", "lipsync_audio", f"khớp môi shot {s['idx']}: không cắt được giọng ({e})", s["id"], job["id"])
            continue
        if seg is None:
            say("warn", "lipsync_audio", f"khớp môi shot {s['idx']}: câu thoại chưa có giọng — chưa gửi", s["id"], job["id"])
            continue
        # S14.1 A1b: the money gate — paused project, trial caps, the project's locked 'videos' budget (a model without a price is
        # refused BEFORE sending: an unpriced 'videos' row would block every clip of a locked project), check + send + ledger under
        # SPEND_LOCK; 'out_of_credit' halts the service.
        with spend_gate.spend(p.conn, "video", provider.name, project_id=pid, model=provider.model, tier="post", units=length,
                              budget_stage="videos", ledger_stage="lipsync") as slot:
            if slot.paused:
                slot.raise_if_over(f"khớp môi shot {s['idx']}")    # PipelinePaused: autopilot.tick says it and waits
            if slot.over:
                log(f"Khớp môi dừng: {slot.over}")
                say("warn", "budget", f"khớp môi dừng: {slot.over}", s["id"], job["id"])
                break
            try:
                task = slot.send(provider.submit, job["result_path"], seg["path"])
            except ProviderError as e:
                say("warn" if e.transient else "error", e.code or "lipsync_submit", f"khớp môi shot {s['idx']}: gửi lỗi ({e})"
                    + (" — sẽ gửi lại lần sau" if e.transient else " — giữ clip gốc"), s["id"], job["id"])
                if e.transient:
                    break
                mark(data_dir, pid, s["id"], state="failed", job_id=job["id"], error=str(e))
                counts["failed"] += 1
                continue
            # B1b: the paid task is written down BEFORE anything else can fail (a lost task = sent and paid again next tick)
            mark(data_dir, pid, s["id"], state="running", task=task, job_id=job["id"], offsets=seg["offsets"], method="post",
                 sent_at=time.time())
            slot.record(length, job_id=job["id"])
        counts["sent"] += 1
    return counts


def conn_rows(p, pid: int):
    return p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
