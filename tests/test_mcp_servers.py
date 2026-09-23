import asyncio
import json
import os
import tempfile
import unittest


def call(server, name, **args):
    result = asyncio.run(server.call_tool(name, args))
    assert not result.is_error, result
    text = result.content[0].text
    try:
        return json.loads(text)
    except ValueError:
        return text


class McpServerTests(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        os.environ["PIPELINE_DB"] = self.db

    def tearDown(self):
        os.environ.pop("PIPELINE_DB", None)
        try:
            os.remove(self.db)
        except OSError:
            pass

    def test_tools_are_registered(self):
        from mcp_servers import clipai, ffmpeg_studio, project_db, qc_agent

        def names(module):
            return {t.name for t in asyncio.run(module.mcp.list_tools())}

        self.assertIn("import_script", names(project_db))
        self.assertIn("submit_qc_result", names(qc_agent))
        self.assertIn("render_final_video", names(ffmpeg_studio))
        self.assertIn("run_heartbeat", names(clipai))

    def test_clipai_refuses_without_provider(self):
        from mcp_servers import clipai
        os.environ.pop("VIDEO_PROVIDER", None)
        from mcp.server.mcpserver.exceptions import UnexpectedToolError
        with self.assertRaises(UnexpectedToolError):
            asyncio.run(clipai.mcp.call_tool("submit_and_poll", {"project_id": 1}))

    def test_end_to_end_human_qc_flow(self):
        from mcp_servers import qc_agent
        from mcp_servers.common import get_pipeline

        p = get_pipeline()
        pid = p.create_project("t", "human_qc")
        scene = p.create_scene(pid, 1, "S1")
        job = call(qc_agent.mcp, "create_image_job", scene_id=scene)
        job_id = job["job_id"]
        call(qc_agent.mcp, "mark_image_ready", job_id=job_id)
        keys = ["character", "hands_face", "composition", "mood_lighting", "consistency", "scale", "grounding", "set_match"]
        qc = json.dumps({"criteria": {k: 0.95 for k in keys}})
        res = call(qc_agent.mcp, "submit_qc_result", job_id=job_id, qc_json=qc)
        self.assertEqual(res["decision"], "pending_review")
        call(qc_agent.mcp, "approve_image", job_id=job_id)
        self.assertEqual(get_pipeline().state(job_id).value, "approved")


if __name__ == "__main__":
    unittest.main()
