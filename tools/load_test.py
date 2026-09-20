"""Load test for the automatic mode: how many projects/jobs can this dashboard run at the same time?

Uses MOCK providers with simulated network latency, so it costs nothing and measures only OUR side:
threads, SQLite contention, the tick loop. It says nothing about Deepix / Clip AI / Claude rate limits.

  py tools/load_test.py                      # steps 1, 2, 5, 10, 20, 40 projects
  py tools/load_test.py 10 30 60 --latency 0.2 --scenes-from samples/script_demo_1.docx
"""
import argparse
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import autopilot, llm_runner, script_parser  # noqa: E402
from core.db import connect  # noqa: E402
from core.music import MockAudioProvider  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402
from core.providers import MockImageProvider, MockVideoProvider  # noqa: E402
from core.runner import ImageRunner, VideoRunner  # noqa: E402

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "samples", "script_demo_1.docx")


class Slow:
    """Wraps a mock provider and sleeps on every call, like a network round trip."""

    def __init__(self, inner, latency):
        self._inner, self._latency = inner, latency

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if name in ("submit", "status") and callable(attr):
            def call(*a, **k):
                time.sleep(self._latency)
                return attr(*a, **k)
            return call
        return attr


def fake_render(p, pid, data_dir, music_path):
    out = os.path.join(data_dir, str(pid), "output", "FINAL_VIDEO.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(b"x")
    return out


def run_once(n_projects, latency, poll, max_parallel, timeout, script):
    tmp = tempfile.mkdtemp()
    db, data = os.path.join(tmp, "m.sqlite"), os.path.join(tmp, "projects")
    p = Pipeline(connect(db))
    ids = []
    for i in range(n_projects):
        pid = p.create_project(f"load {i}", "human_qc", 0.85, 2)
        paragraphs = script_parser.read_docx_paragraphs(script)
        script_parser.import_scenes(p, pid, script_parser.split_scenes(paragraphs))
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        ids.append(pid)

    def factory(pipeline, data_dir):
        return autopilot.Context(data_dir, ImageRunner(pipeline, Slow(MockImageProvider(polls_to_finish=2), latency), data_dir),
                                 VideoRunner(pipeline, Slow(MockVideoProvider(polls_to_finish=3), latency), data_dir),
                                 llm_runner.MockLlm(), MockAudioProvider(), fake_render)

    os.environ["AUTOPILOT_DAILY_JOBS"] = "0"      # no cap: we are measuring, not protecting
    mgr = autopilot.Manager(db, data, factory, poll_sec=poll, max_parallel=max_parallel)
    t0 = time.time()
    for i in ids:
        autopilot.start(p, i)
        mgr.start(i)
    peak_threads = peak_jobs = 0
    watcher = Pipeline(connect(db))
    while time.time() - t0 < timeout:
        peak_threads = max(peak_threads, mgr.running_count())
        try:
            peak_jobs = max(peak_jobs, watcher.conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE state IN ('queued','running','retryable')").fetchone()[0])
            states = [autopilot.status(watcher, i)["state"] for i in ids]
        except Exception:  # noqa: BLE001 - the watcher itself can hit a locked database: that is a finding too
            states = ["?"]
        if all(s not in ("running", "queued") for s in states):
            break
        time.sleep(0.05)
    wall = time.time() - t0
    final = [autopilot.status(watcher, i) for i in ids]
    done = sum(1 for s in final if s["state"] == "done")
    jobs = watcher.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    bad = [s["note"] for s in final if s["state"] != "done"]
    locked = sum(1 for s in bad if "locked" in s.lower())
    return {"projects": n_projects, "done": done, "wall": wall, "jobs": jobs, "jobs_per_s": jobs / wall if wall else 0,
            "peak_threads": peak_threads, "peak_jobs": peak_jobs, "not_done": len(bad), "locked": locked,
            "sample": bad[0][:120] if bad else ""}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("sizes", nargs="*", type=int, default=[1, 2, 5, 10, 20, 40])
    ap.add_argument("--latency", type=float, default=0.1, help="seconds per provider call (simulated network)")
    ap.add_argument("--poll", type=float, default=0.1, help="seconds between ticks of one project")
    ap.add_argument("--parallel", type=int, default=0, help="projects at once (default: all of them)")
    ap.add_argument("--timeout", type=float, default=180)
    ap.add_argument("--scenes-from", default=SAMPLE)
    a = ap.parse_args()
    print(f"latency={a.latency}s poll={a.poll}s (mock providers, temp SQLite file)")
    print(f"{'projects':>8} {'done':>5} {'wall_s':>7} {'jobs':>6} {'jobs/s':>7} {'peak_thr':>8} {'peak_jobs':>9} {'locked':>6}  first problem")
    for n in a.sizes:
        r = run_once(n, a.latency, a.poll, a.parallel or n, a.timeout, a.scenes_from)
        print(f"{r['projects']:>8} {r['done']:>5} {r['wall']:>7.1f} {r['jobs']:>6} {r['jobs_per_s']:>7.1f} {r['peak_threads']:>8} "
              f"{r['peak_jobs']:>9} {r['locked']:>6}  {r['sample']}", flush=True)
        if r["not_done"] > r["projects"] // 2:
            print("more than half failed: stopping the ramp")
            break


if __name__ == "__main__":
    main()
