"""MCP server: Step 4 video generation (submit / heartbeat poll / cancel).

Uses the provider selected by VIDEO_PROVIDER (clipai | mock). Without a provider the tools return a clear
error instead of pretending.
"""
import os
from typing import List

from mcp.server.mcpserver import MCPServer

from core import llm_io
from core.adapters import factory
from core.runner import VideoRunner
from .common import get_pipeline

mcp = MCPServer("clipai")


def _runner() -> VideoRunner:
    provider = factory.video_provider()
    if provider is None:
        raise RuntimeError("No video provider configured. Set VIDEO_PROVIDER=clipai and CLIPAI_TOKEN "
                           "(or VIDEO_PROVIDER=mock for simulated demos).")
    data_dir = os.environ.get("PIPELINE_DATA", os.path.join("data", "projects"))
    return VideoRunner(get_pipeline(), provider, data_dir)


@mcp.tool()
def create_video_jobs(project_id: int) -> dict:
    """Create video_gen jobs for scenes with an approved image and approved motion prompt."""
    p = get_pipeline()
    created = 0
    for r in llm_io.ready_for_video(p, project_id):
        exists = p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen'"
                                " AND state NOT IN ('cancelled','rejected')", (r["scene_id"],)).fetchone()
        if not exists:
            p.create_job(r["scene_id"], "video_gen")
            created += 1
    return {"created": created}


@mcp.tool()
def submit_and_poll(project_id: int) -> dict:
    """Submit queued jobs and poll running ones once."""
    runner = _runner()
    submitted = runner.submit_pending(project_id)
    return {"submitted": submitted, **runner.poll_once(project_id)}


@mcp.tool()
def run_heartbeat(project_id: int, interval_sec: float = 90) -> dict:
    """Loop submit/poll every interval until nothing is queued or running (or the project is paused)."""
    _runner().run(project_id, interval=interval_sec)
    rows = get_pipeline().conn.execute("SELECT state, COUNT(*) c FROM jobs WHERE project_id=? AND type='video_gen'"
                                       " GROUP BY state", (project_id,)).fetchall()
    return {r["state"]: r["c"] for r in rows}


@mcp.tool()
def cancel_video_job(job_id: int) -> str:
    """Cancel a queued/running video job (also cancels the provider task)."""
    runner = _runner()
    runner.cancel_job(job_id)
    return runner.p.state(job_id).value


@mcp.tool()
def list_video_failures(project_id: int) -> List[dict]:
    """Risk-control / moderation failures logged for this project's jobs."""
    rows = get_pipeline().conn.execute(
        "SELECT f.job_id, f.provider, f.error_message, f.at FROM content_moderation_failures f"
        " JOIN jobs j ON j.id=f.job_id WHERE j.project_id=? ORDER BY f.id", (project_id,))
    return [dict(r) for r in rows]


if __name__ == "__main__":
    mcp.run()
