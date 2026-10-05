"""Storyboard of N frames in one go, the way Deepix's web Weave Canvas does it (its Storyboard node, read 2026-09-25 from
deepix.ingarena.net/weave/app.js): frame 1 is drawn with the shared references; frames 2..N are then drawn two at a time with the same
references + frame 1 as the continuity anchor (ref_mode "global"). Without shared references every frame takes frame 1 and the
previous frame (ref_mode "sequential"). Each frame is an ordinary Deepix picture (DeepixImageProvider.submit_storyboard_frame,
prompt_key 14), so it goes through the same ledger and picture cap as every picture.

Why: the shots of one scene share characters, place and light; drawing them as one storyboard keeps them together better than
separate pictures + a set check afterwards (kế hoạch V4, bàn giao Canvas).
"""
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional

from .providers import ProviderError


def mapping_text(refs: List[Dict], shared: int) -> str:
    """The 'Reference image mapping' note of the web storyboard: which picture is a user reference, which is the continuity anchor."""
    lines = []
    for i, r in enumerate(refs):
        head = f"Image {i + 1} ({r.get('label', '')})" if r.get("label") else f"Image {i + 1}"
        if i < shared:
            lines.append(f"{head}: user reference image {i + 1}; preserve visible identity, subject details, and style cues.")
        elif i == shared and shared:
            lines.append(f"{head}: first generated frame visual continuity anchor; inherit style, color palette, lighting mood, "
                         "character appearance, and world details.")
        elif i == 0:
            lines.append(f"{head}: first generated frame visual continuity anchor.")
        else:
            lines.append(f"{head}: previous generated frame continuity anchor; maintain temporal and visual continuity.")
    return "Reference image mapping:\n" + "\n".join(lines)


def _wait(provider, message_id: str, dest: str, poll: float, timeout: float, sleep: Callable) -> str:
    end = time.time() + timeout
    while time.time() < end:
        st = provider.status(message_id)
        if st.state == "succeeded":
            return provider.download(message_id, dest)
        if st.state == "failed":
            raise ProviderError(st.error_message or "storyboard frame failed", code=st.error_code or "task_failed")
        sleep(poll)
    raise ProviderError(f"storyboard frame {message_id} not done after {timeout:.0f}s", code="timeout")


def run(provider, frame_prompts: List[str], refs: List[Dict], story_text: str, out_dir: str, size: Optional[str] = None,
        model: Optional[str] = None, on_submit: Callable[[int, str], None] = lambda i, m: None, poll: float = 5.0,
        timeout: float = 600.0, sleep: Callable = time.sleep, parallel: int = 2, conn=None) -> Dict:
    """Draw the frames. refs = [{"path", "label"}] shared references (characters, place). Returns {"storyboard_id", "frames":
    [{"index", "path", "message_id", "error"}], "stopped"}. on_submit(index, message_id) is called for every frame sent (ledger).
    Rà soát A2 (S14.2): every frame asks the money lock BEFORE it is sent — a command-line run's --max-usd (core.script_cap; raises
    CapReached, the frames already sent are kept and fetched, "stopped" says why) and, with `conn`, budget.check_image (a service out of
    credit → ProviderError)."""
    from . import budget, script_cap
    os.makedirs(out_dir, exist_ok=True)
    sid = f"sb_{uuid.uuid4().hex[:10]}"
    n = len(frame_prompts)
    mode = "global" if refs else "sequential"
    frames: List[Dict] = [{"index": i + 1, "path": None, "message_id": None, "error": None} for i in range(n)]
    stopped: List[str] = []

    def send(i: int, frame_refs: List[Dict]) -> str:
        """Submit + ledger in the CALLING thread (the ledger's SQLite connection belongs to it — 2026-09-25 the first real run sent
        frames 2-4 from worker threads, the ledger write failed there and the three paid frames were lost with their ids)."""
        why = script_cap.send_refusal("image", getattr(provider, "name", ""), model, None, 1)
        if why:
            raise script_cap.CapReached(why)
        hard = budget.check_image(conn, getattr(provider, "name", ""), model, 1) if conn is not None else None
        if hard:
            raise ProviderError(hard, code="out_of_credit")
        mapping = mapping_text(frame_refs, len(refs)) if frame_refs else ""
        mid = provider.submit_storyboard_frame(frame_prompts[i], [r["path"] for r in frame_refs], story_text, sid, i, n, mode, mapping,
                                               size, model)
        frames[i]["message_id"] = mid
        on_submit(i, mid)
        return mid

    def fetch(i: int) -> None:
        frames[i]["path"] = _wait(provider, frames[i]["message_id"], os.path.join(out_dir, f"frame_{i + 1}.png"), poll, timeout, sleep)

    def draw(i: int, frame_refs: List[Dict]) -> None:
        send(i, frame_refs)
        fetch(i)

    try:
        draw(0, list(refs))
    except ProviderError as e:
        frames[0]["error"] = str(e)
        return {"storyboard_id": sid, "frames": frames, "stopped": None}
    first = {"path": frames[0]["path"], "label": "frame 1"}
    if mode == "global":
        sent = []
        for i in range(1, n):                              # sent one after the other here; only the waiting runs in parallel
            try:
                send(i, list(refs) + [first])
                sent.append(i)
            except script_cap.CapReached as e:         # the frames already sent are still fetched (paid for)
                for k in range(i, n):
                    frames[k]["error"] = str(e)
                stopped.append(str(e))
                break
            except ProviderError as e:
                frames[i]["error"] = str(e)
        with ThreadPoolExecutor(max_workers=max(1, parallel)) as pool:
            futures = {i: pool.submit(fetch, i) for i in sent}
            for i, fut in futures.items():
                try:
                    fut.result()
                except Exception as e:  # noqa: BLE001 - one frame failing never loses the others
                    frames[i]["error"] = str(e)
    else:
        prev = first
        for i in range(1, n):
            frame_refs = ([first] if i >= 2 else []) + [prev]
            try:
                draw(i, frame_refs)
            except script_cap.CapReached as e:
                for k in range(i, n):
                    frames[k]["error"] = str(e)
                stopped.append(str(e))
                break
            except ProviderError as e:
                frames[i]["error"] = str(e)
                break
            prev = {"path": frames[i]["path"], "label": f"frame {i + 1}"}
    return {"storyboard_id": sid, "frames": frames, "stopped": stopped[0] if stopped else None}
