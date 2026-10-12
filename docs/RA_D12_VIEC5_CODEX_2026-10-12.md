# RÀ KỸ Đ12 việc 5 — 12/10/2026
- Root đã đọc diff vòng sửa unison/voice/lipsync/delivery và phần ledger/schema/UI/areas. Commit lần này chỉ lưu phần dở trên nhánh riêng; GUI và nghiệm thu đầy đủ còn chờ sau Đ15v3, không ghi ✅ toàn việc.
Phạm vi: diff base `b8782dfe`, unison/tests mới, CODEX_TASKS Đ12v5, CHUẨN, bàn giao + callers runner/autopilot/delivery; chỉ đọc code, không API/data thật.
Kết luận: cần sửa 3 lỗi dưới đây trước commit. Không chạy lại nhóm/cả bộ; hai script tái hiện dùng SQLite/PCM trong thư mục temp (2,0 s + 3,0 s).
1. **[P1] OFF sau ON vẫn phát cả hai giọng nối tiếp** — `core/lipsync.py:144`, `core/voice.py:441`.
   Khi A/B đã có assets đồng thanh, tắt cờ: planned chỉ A nhưng `shot_lines` vẫn trả A/B; offsets thành `[1,2.15]`. Bản dựng OFF cũng dùng cả hai rows cũ, cue thành hai dòng; test OFF hiện chỉ dựng plan/segments độc lập nên bỏ sót lifecycle thật.
   Sửa: chọn assets theo plan/schema hiện tại ở chung một nơi cho lipsync/final; khi OFF bỏ secondary thuộc nhóm đã lưu, ánh xạ primary qua `dialogue_line` để không làm lệch những câu theo sau; giữ byte/hành vi cũ đối với assets legacy không metadata. Không xóa WAV và không gen lại chỉ vì toggle.
   Test: ON tạo A/B + câu C → OFF → shot/final/cues chỉ A,C đúng thứ tự; bật lại dùng đủ A/B,C, không thêm TTS. Đổi unison sau có assets phải loại rows không còn trong plan.
2. **[P1] Giọng đã mất/đổi profile vẫn được gửi vào take/generate** — `core/lipsync.py:147`, `core/voice.py:344`, `core/voice.py:525`.
   Guard chỉ so tập speaker của các rows thành công, không so profile hiện tại. Tái hiện: xóa profile B sau assets A/B → `status.no_voice=['B']` nhưng `shot_lines` trả đủ A/B. `scene_seconds`/`place_on_timeline` cũng không so voice_id và cảnh báo onset có thể dùng WAV giọng cũ khi profile đổi.
   Sửa: từ conn/plan hiện tại kiểm đủ speaker, voice_id, metadata và file thật trước lipsync; truyền context hoặc đọc DB qua helper có sẵn, không sửa runner. Dừng rõ ở biên gọi trả tiền khi thiếu/stale; final/status báo VÀNG có lý do, không dùng cặp WAV cũ như hợp lệ.
   Test: assets đầy đủ rồi xóa/đổi profile B, đổi schema và mất WAV → không gửi video partial/stale; cả nhóm mất assets cũng có guard thay vì trả [] để tiếp tục clip không voice.
3. **[P2] Chỉ đặt cùng timestamp, chưa canh điểm bắt đầu âm thanh** — `core/unison.py:29`, `core/lipsync.py:168`, `core/voice.py:454`.
   PCM thật A onset 0,10 s/B onset 0,40 s; `shot_audio` đặt cả hai offset 1,0 s nhưng WAV mix còn hai onset 1,10/1,40 s (lệch 300 ms). `measure` chỉ báo VÀNG, không tạo trim/delay nào; yêu cầu Đ12v5 ghi “mix canh cùng điểm đầu”.
   Sửa: chuẩn hóa silence đầu từng giọng bằng onset local (giữ WAV gốc) và dùng chung offset/derived WAV cho take/generate/final; cache theo source + profile + thuật toán; nội bộ từ còn lệch luôn VÀNG, không tự gen trả tiền hoặc tuyên bố xác minh chữ.
   Test: source silence 0,1/0,4 s → mix cùng onset ≤60 ms, mọi đường dùng cùng derived files/clock; đo mismatch nội bộ vẫn VÀNG.
Đã rà: OPT_IN_ONLY giữ experimental OFF; ledger stage truyền audio_lib→music→cost; sổ chi/cổng tiền cũ, permission p, areas version 60 và khai module/tests/cờ giữ nguyên, keys UI không đổi; không nới test cũ.
Giới hạn còn mở: `unison.measure:76` nhận path tuyệt đối/UNC từ metadata qua os.path.join nên “không truy cập mạng” chưa được enforce; nên guard resolved path nằm trong assets_dir trước isfile/ffmpeg (mock UNC, không thử mạng thật).
Cache bản dựng `delivery.audio_hash:131` chỉ nhìn assets đã đặt: cần test thay schema/toggle khiến bản cũ stale trước render; gộp sửa cùng lỗi 1, không khẳng định chất lượng #24.

## Vòng sửa gom (theo root, chưa commit)
- 3 finding đã xử lý trong unison/voice/lipsync/delivery; runner giữ nguyên. `unison_context.json` bind đường DB từ PRAGMA; runner đọc `mode=ro`, chỉ SELECT plan live, không globals/hardcode/migration. DB memory cần explicit conn, snapshot không được dùng như nguồn live.
- OFF ánh xạ `dialogue_line` giữ primary + câu theo sau; ON lại không gửi thêm TTS. Thiếu/bị đổi profile-ID/schema/WAV/binding/cả nhóm đều chặn tại actual `_take_segments` trước API; final bỏ cả nhóm thiếu thay vì phát partial.
- Derived WAV trim silence đầu, cache SHA nội dung + voice_id + phiên bản thuật toán; giữ `solo_file`/duration gốc. Final/take/generate dùng cùng file/clock; onset chỉ proxy, VÀNG chưa xác minh chữ. UNC/URL/absolute/escape assets bị guard trước I/O/ffmpeg.
- Hash bản dựng có flag, context/live plan và SHA nguồn; toggle/schema/profile/source đổi làm stale; legacy không metadata giữ hash cũ. Areas version 60, không đổi keys, không sửa test cũ ngoài fixture test mới có WAV thật + voice_id + fileDB để kiểm guard.
- ĐỎ focused 2 test (bind/path guard chưa có) → 16 rồi 19 test xanh; nhóm cuối 4 file: **50 passed /22,00s**. compileall + diff --check sạch. Không API/data thật/cả bộ/commit/push.
- Mở: thử thật #24 và QA chất lượng từng chữ chưa làm; chỉ trim đầu không sửa nhịp nội bộ. Root đọc diff vòng sửa trước commit theo quy trình.

- Root bắt thêm cache legacy sau nhóm đầu: OFF A+C→ON đỏ gửi3 thay1 → sửa stable logical+speaker + patch metadata 0USD; xanh4focused, chạy lại4file vì có sửa tiền mới. Legacy chỉ thêm B, OFF/ON không trả lại tiền.
