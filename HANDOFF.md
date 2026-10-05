# HANDOFF — S14.26 tự gắn giọng tiếng Việt (nhánh worktree-agent-a7ab348eb8e789ee2)

## Đã xong
- `core/voice_casting.py` (mới): khối prompt `voice_traits` (cờ `auto_voice_cast`, mặc định TẮT), `clean_traits` (enum nam/nữ/không rõ),
  `apply` luật 0 USD theo `data/voices_vi.json`, biến thể cao độ (ffmpeg sau TTS) + tốc độ ClipAI, `shared_voices`.
- Nối vào: `llm_io.store_scene_analysis` (sau khi lưu), `prompts` (2 bundle Director), `voice.set_profile/generate`, `audio_lib.refresh`,
  cột `characters.voice_traits` (db), cờ ở `core/features.py`, `devsys/areas.json`.
- Test `tests/test_voice_casting.py` 16 xanh.

## Đang dở
- Giao diện Character Bible (`dashboard/steps/step1_characters.py`): hiện tính cách/giới, '🤖 tự gắn', vai dùng chung giọng.

## Bước kế
- UI + test AppTest nhẹ; báo cáo.
