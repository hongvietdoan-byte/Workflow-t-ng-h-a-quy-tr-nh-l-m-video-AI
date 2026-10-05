# HANDOFF — S14.26 tự gắn giọng tiếng Việt (nhánh worktree-agent-a7ab348eb8e789ee2)

## Đã xong
- `core/voice_casting.py` (mới): khối prompt `voice_traits` (cờ `auto_voice_cast`, mặc định TẮT), `clean_traits` (enum nam/nữ/không rõ),
  `apply` luật 0 USD theo `data/voices_vi.json`, biến thể cao độ (ffmpeg sau TTS) + tốc độ ClipAI, `shared_voices`.
- Nối vào: `llm_io.store_scene_analysis`, `prompts` (2 bundle Director), `voice.set_profile/generate`, `audio_lib.refresh`,
  cột `characters.voice_traits`, cờ ở `core/features.py`, `devsys/areas.json`.
- Giao diện Character Bible (`dashboard/steps/step1_characters.py`, dùng chung UI cũ + v2): cột Giọng ghi "🔁 dùng chung", dòng
  "Vai dùng chung giọng", nút `vrule_{pid}` gắn theo luật 0 USD, mỗi nhân vật ghi 🧬 giới/tuổi/tính cách + 🤖 tự gắn + biến thể.
- Test `tests/test_voice_casting.py` 17 xanh.

## Đang dở
- Không.

## Bước kế
- Người điều phối: gộp main, chạy cả bộ test, bật cờ thử trên dự án mới; xóa file này khi gộp.
