"""MCP server: local FFmpeg render (concat / crossfade / music mux)."""
from typing import List, Optional

from mcp.server.mcpserver import MCPServer

from core import ffmpeg_studio

mcp = MCPServer("ffmpeg-studio")


@mcp.tool()
def render_final_video(clips: List[str], output: str, durations: Optional[List[float]] = None,
                       transition: str = "cut", music: Optional[str] = None) -> str:
    """Concat clips in order (transition: 'cut' or 'crossfade'), optionally mux a music track."""
    return ffmpeg_studio.render_final(clips, output, durations, transition, music=music)


if __name__ == "__main__":
    mcp.run()
