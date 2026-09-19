# Hướng dẫn chạy V0 (Claude Desktop + MCP)

## 1. Cài đặt
```
py -m pip install -r requirements.txt
py -m unittest discover -s tests -t .      # 36 test phải qua
```
FFmpeg (chỉ cần cho render): cài FFmpeg rồi thêm vào PATH hoặc đặt biến môi trường `FFMPEG_PATH`.

## 2. Cấu hình Claude Desktop (`claude_desktop_config.json`)
Thay `<REPO>` bằng đường dẫn thư mục dự án (dùng `\\` trong JSON). `PIPELINE_DB` là file SQLite dùng chung.
```json
{
  "mcpServers": {
    "project-db": {
      "command": "py", "args": ["-m", "mcp_servers.project_db"],
      "cwd": "<REPO>", "env": {"PIPELINE_DB": "<REPO>\\data\\manifest.sqlite"}
    },
    "qc-agent": {
      "command": "py", "args": ["-m", "mcp_servers.qc_agent"],
      "cwd": "<REPO>", "env": {"PIPELINE_DB": "<REPO>\\data\\manifest.sqlite"}
    },
    "clipai": {
      "command": "py", "args": ["-m", "mcp_servers.clipai"],
      "cwd": "<REPO>", "env": {"PIPELINE_DB": "<REPO>\data\manifest.sqlite"}
    },
    "ffmpeg-studio": {
      "command": "py", "args": ["-m", "mcp_servers.ffmpeg_studio"], "cwd": "<REPO>"
    }
  }
}
```
Khởi động lại Claude Desktop. (Nếu `cwd` không được hỗ trợ ở bản của bạn, dùng đường dẫn tuyệt đối tới `py -m` với `PYTHONPATH=<REPO>`.)

## 3. Luồng V0 (human_qc mặc định)
1. `create_project` → `import_script(docx_path)`.
2. `get_director_prompt` → dán vào chat Claude, nhận JSON → `submit_scene_analysis`.
3. `preflight_check` (xem cảnh báo IP) → sửa nếu cần → `approve_and_lock_bible`.
4. Gen ảnh: *chờ kết nối Deepix* — tạm dùng `create_image_job` + `mark_image_ready` khi đã có ảnh (tự tạo/nhập tay).
5. `get_qc_prompt(scene_id)` + đính kèm ảnh vào chat → JSON điểm → `submit_qc_result` → (human_qc) `approve_image` / `reject_image`.
6. Bước 3: `submit_motion_prompts` (prompt mẫu `prompts/03_video_motion.md`) → `approve_motion_prompt`. Bước 4: `create_video_jobs` → `submit_and_poll` / `run_heartbeat`; *adapter Clip AI thật chưa có* — chỉ chạy được bản giả lập với `VIDEO_PROVIDER=mock` (không tạo video thật).
7. `render_final_video` khi đã có clip (cần FFmpeg).

## 4. Dashboard (giao diện hợp nhất, dùng song song hoặc thay cho gọi MCP tay)
```
py -m streamlit run dashboard/app.py
```
Đặt `PIPELINE_DB` / `PIPELINE_DATA` nếu muốn đổi vị trí dữ liệu (mặc định `data/manifest.sqlite`, `data/projects/`). Các bước cần Claude vẫn dán JSON tay cho tới khi có API key (V1).
