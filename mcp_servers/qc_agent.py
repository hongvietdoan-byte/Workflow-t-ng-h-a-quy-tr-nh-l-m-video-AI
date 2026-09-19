"""MCP server: QC scoring flow + review actions (Approve / Reject / Cancel / Retry)."""
from mcp.server.mcpserver import MCPServer

from core import llm_io, prompts
from .common import get_pipeline

mcp = MCPServer("qc-agent")


@mcp.tool()
def create_image_job(scene_id: int) -> dict:
    """Create an image_gen job (used until the Deepix connector is wired in)."""
    return {"job_id": get_pipeline().create_job(scene_id, "image_gen")}


@mcp.tool()
def mark_image_ready(job_id: int) -> str:
    """Mark a job's image as generated (queued/running -> succeeded)."""
    p = get_pipeline()
    if p.state(job_id).value == "queued":
        p.start(job_id)
    p.succeed(job_id)
    return p.state(job_id).value


@mcp.tool()
def get_qc_prompt(scene_id: int) -> str:
    """Prompt bundle for scoring one scene image (attach the image in chat)."""
    return prompts.build_qc_bundle(get_pipeline(), scene_id)


@mcp.tool()
def submit_qc_result(job_id: int, qc_json: str) -> dict:
    """Validate QC scores, then decide by project operating_mode (auto / human_qc)."""
    p = get_pipeline()
    obj = llm_io.validate_qc_result(qc_json, prompts.qc_criteria())
    decision = p.apply_qc(job_id, obj["criteria"])
    return {"decision": decision, "state": p.state(job_id).value, "issues": obj.get("issues", [])}


@mcp.tool()
def approve_image(job_id: int, note: str = "") -> str:
    """User approves an image."""
    p = get_pipeline()
    p.approve(job_id, "user", note or None)
    return p.state(job_id).value


@mcp.tool()
def reject_image(job_id: int, note: str) -> dict:
    """Reject with a note (becomes the retry reason). Spawns a retry job or escalates."""
    return {"result": get_pipeline().reject(job_id, "user", note)}


@mcp.tool()
def cancel_job(job_id: int) -> str:
    """Cancel a queued or running job."""
    p = get_pipeline()
    p.cancel(job_id)
    return p.state(job_id).value


@mcp.tool()
def retry_failed_job(job_id: int, reason: str = "") -> dict:
    """Retry a failed job (creates a child job, or escalates when retries are exhausted)."""
    return {"new_job_id": get_pipeline().retry(job_id, reason or None)}


if __name__ == "__main__":
    mcp.run()
