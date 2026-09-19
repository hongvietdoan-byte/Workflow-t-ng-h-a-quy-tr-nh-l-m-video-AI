# Hướng dẫn chạy V0 (Claude Desktop + MCP)

## 1. Cài đặt
```
py -m pip install -r requirements.txt
py -m unittest discover -s tests -t .      # test phải qua hết
```
FFmpeg (cần cho render): `winget install --id Gyan.FFmpeg -e`; nếu shell chưa thấy `ffmpeg` thì đặt `FFMPEG_PATH`.

## 2. Cấu hình Claude Desktop (`claude_desktop_config.json`)
Đã cấu hình sẵn trên máy này (2026-09-19). File nằm ở `%APPDATA%\Claude\claude_desktop_config.json` (bản Store: cùng file qua `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude`). Bản sao lưu: `claude_desktop_config.json.bak-20260919`.

Mẫu khối `mcpServers` (thay `<REPO>` và đường dẫn Python bằng đường dẫn thật của máy, dùng `\\` trong JSON). Dùng `PYTHONPATH` thay vì `cwd` để không phụ thuộc thư mục làm việc:
```json
"mcpServers": {
  "project-db": {
    "command": "<PYTHON>\\python.exe", "args": ["-m", "mcp_servers.project_db"],
    "env": {"PYTHONPATH": "<REPO>", "PIPELINE_DB": "<REPO>\\data\\manifest.sqlite",
            "PIPELINE_DATA": "<REPO>\\data\\projects", "PYTHONIOENCODING": "utf-8"}
  },
  "qc-agent": {
    "command": "<PYTHON>\\python.exe", "args": ["-m", "mcp_servers.qc_agent"],
    "env": {"PYTHONPATH": "<REPO>", "PIPELINE_DB": "<REPO>\\data\\manifest.sqlite",
            "PIPELINE_DATA": "<REPO>\\data\\projects", "PYTHONIOENCODING": "utf-8"}
  },
  "ffmpeg-studio": {
    "command": "<PYTHON>\\python.exe", "args": ["-m", "mcp_servers.ffmpeg_studio"],
    "env": {"PYTHONPATH": "<REPO>", "FFMPEG_PATH": "<đường dẫn ffmpeg.exe>", "PYTHONIOENCODING": "utf-8"}
  }
}
```
`clipai` chưa đưa vào cấu hình (chưa có adapter thật). **Thoát hẳn Claude Desktop (kể cả khay hệ thống) rồi mở lại** để nạp cấu hình. Các tool xuất hiện trong tab Chat (biểu tượng công cụ).

## 3. Chạy thử trong Chat của Claude Desktop (human_qc)
Mở chat mới, dán lần lượt:
1. `Dùng project-db: tạo dự án "V0 demo" chế độ human_qc, rồi import kịch bản F:\...\samples\script_demo_1.docx` (thay đường dẫn đầy đủ tới file trong repo).
2. `Lấy get_director_prompt cho dự án đó, làm theo đúng prompt và trả JSON, rồi gọi submit_scene_analysis với JSON đó.`
3. `Chạy preflight_check và báo cảnh báo IP; nếu ổn thì approve_and_lock_bible.`
4. Tạo job ảnh (chưa có Deepix): `Với mỗi cảnh gọi create_image_job rồi mark_image_ready` (đặt ảnh thật vào `data/projects/<id>/images/job_<jobId>.png` nếu muốn Claude chấm điểm ảnh).
5. `Gọi get_qc_prompt(scene_id), chấm ảnh (đính kèm ảnh) theo prompt, rồi submit_qc_result.` → ở human_qc job vào `pending_review`; bạn quyết định: `approve_image` hoặc `reject_image` (ghi chú).
6. Bước 3: `Viết motion prompt theo prompts/03_video_motion.md, gọi submit_motion_prompts rồi approve_motion_prompt.`
7. Bước 4 (Clip AI): chưa có adapter thật — dừng ở đây; hoặc `list_ready_for_video` để xem cảnh sẵn sàng.
8. Khi có clip .mp4: `render_final_video` (cần FFmpeg).

Đã kiểm thử tự động toàn bộ các bước 1–5 qua MCP stdio thật (script kiểm thử đóng vai Claude).

## 4. Dashboard (giao diện hợp nhất, dùng song song hoặc thay cho gọi MCP)
```
py -m streamlit run dashboard/app.py
```
Đặt `PIPELINE_DB` / `PIPELINE_DATA` nếu muốn đổi vị trí dữ liệu (mặc định `data/manifest.sqlite`, `data/projects/`). Đặt `IMAGE_PROVIDER=mock` / `VIDEO_PROVIDER=mock` để thử luồng gen ảnh/video giả lập. Các bước cần Claude vẫn dán JSON tay cho tới khi có API key (V1).

Lưu ý: MCP và Dashboard dùng chung file `data/manifest.sqlite`, nên thao tác ở bên này sẽ thấy ở bên kia.
