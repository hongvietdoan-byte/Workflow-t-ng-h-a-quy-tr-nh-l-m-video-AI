"""MCP server: project database, script import, Director analysis, pre-flight, Step 1 lock."""
from typing import List

from mcp.server.mcpserver import MCPServer

from core import llm_io, preflight, prompts, script_parser
from .common import get_pipeline

mcp = MCPServer("project-db")


@mcp.tool()
def create_project(name: str, operating_mode: str = "human_qc", threshold: float = 0.85) -> dict:
    """Create a project. operating_mode: 'auto' or 'human_qc'."""
    return {"project_id": get_pipeline().create_project(name, operating_mode, threshold)}


@mcp.tool()
def set_operating_mode(project_id: int, mode: str) -> str:
    """Switch a project between 'auto' and 'human_qc'."""
    get_pipeline().set_mode(project_id, mode)
    return mode


@mcp.tool()
def set_qc_threshold(project_id: int, threshold: float) -> float:
    """Set the QC auto-pass threshold used in 'auto' mode."""
    get_pipeline().set_threshold(project_id, threshold)
    return threshold


@mcp.tool()
def import_script(project_id: int, docx_path: str) -> dict:
    """Step 1: split a script.docx into scenes and store them."""
    p = get_pipeline()
    scenes = script_parser.parse_docx(docx_path)
    ids = script_parser.import_scenes(p, project_id, scenes)
    return {"scenes": len(ids), "headings": [s.heading for s in scenes]}


@mcp.tool()
def get_director_prompt(project_id: int) -> str:
    """Prompt bundle (system prompt + knowledge + scenes) for the Director analysis."""
    return prompts.build_director_bundle(get_pipeline(), project_id)


@mcp.tool()
def submit_scene_analysis(project_id: int, analysis_json: str) -> dict:
    """Validate and store the Director's JSON (Character Bible + scene specs)."""
    obj = llm_io.store_scene_analysis(get_pipeline(), project_id, analysis_json)
    return {"characters": len(obj["characters"]), "scenes": len(obj["scenes"])}


@mcp.tool()
def preflight_check(project_id: int) -> List[dict]:
    """Warn about characters that may match IPs blocked by Kling risk control."""
    return preflight.check_characters(get_pipeline().conn, project_id, preflight.load_blocklist())


@mcp.tool()
def approve_and_lock_bible(project_id: int) -> dict:
    """Step 1 review point: lock the Character Bible and open Step 2."""
    return {"scenes_ready": llm_io.lock_character_bible(get_pipeline(), project_id)}


@mcp.tool()
def list_jobs(project_id: int, state: str = "") -> List[dict]:
    """List jobs (optionally filtered by state) with retry and escalation info."""
    query = "SELECT id, scene_id, type, state, retry_count, retry_reason, escalated FROM jobs WHERE project_id=?"
    args = [project_id]
    if state:
        query += " AND state=?"
        args.append(state)
    return [dict(r) for r in get_pipeline().conn.execute(query + " ORDER BY id", args)]


if __name__ == "__main__":
    mcp.run()
