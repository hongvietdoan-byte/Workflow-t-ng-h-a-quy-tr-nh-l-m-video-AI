# Vòng sửa nhánh `claude/gop-1510` (giây đọc + shot dễ 720p) — 15/10/2026

Nhánh = origin/main + `claude/giay-doc-that` (2e3e7cf3) + `claude/shot-de-720p` (7f3c7c4e). Cả bộ test: 5654 passed, 1 failed
(`tests/test_ambient_motion.py::test_off_byte_exact` — bản chụp gói prompt Đạo diễn, prompt 01/17/20 đổi có chủ đích).
Rà KỸ đã xong; một phiên sửa MỚI làm hết danh sách dưới, MỘT vòng.

## Quyết định người dùng (15/10) phải theo
- Shot ĐƠN GIẢN → gen thẳng Seedance 2.5 720p, dựng phóng ffmpeg 1080. Shot KHÓ → nháp 480 → người duyệt → nâng 1080.
- Code ép KHÓ: video ref, shot kỹ năng, khớp môi/take thoại, **≥ 3 nhân vật**, **hero / money shot**. **KHÔNG** ép khó chỉ vì 2 nhân vật
  hoặc thoại + cử động tay (bản hiện tại ép qua điểm kiểm chéo `shot_complexity` > 1 → bỏ phần đó cho đường đi; nhãn hiển thị có thể giữ).
- Clip 720p gen thẳng **cũng phải người duyệt qua chat** (không tự duyệt khi QC đạt).

## Danh sách sửa (từ phiên rà)
1. **CAO — ước giây phình (tiền).** `data/speech_rates.json` lấy p10 âm tiết/giây trên độ dài cả FILE (có lặng) rồi `dialogue.needed_seconds`
   cộng thêm BREATH 0,5 s → lặng tính 2 lần (giọng 70: câu 23 âm tiết ước 12,6 s; mặc định 6,2 s). Sửa: đo trên `speech_s` (đã cắt lặng,
   tool đã đo), dùng p50 (hoặc p25), sàn `max(p, 0.8*RATE)`, không cộng BREATH lên số đo đã gồm lặng; ghi lại bảng bằng
   `tools/measure_speech_rate.py --write` trỏ vào audio TTS thật ở `D:\AI-Video-Pipeline\data\` (0 USD). Test: mỗi giọng trung vị
   (ước − file_s thật) ≤ +0,5 s; giọng 70 câu 23 âm tiết ≤ ~8 s.
2. **VỪA — cắt clip nhóm Kling multishot.** `core/shots.py:779` `group_parts` còn dùng `billed_shot_seconds`; runner gửi `billed_seconds`
   (runner.py:1072/1877/1943) → cắt lệch. Sửa: `group_parts(group, conn=None)` dùng `billed_seconds(conn, r)` cho shot không `exact`;
   `split_group_clip` + runner.py:2277-2278 truyền conn. Test: nhóm [4 kéo 7, 4] → [(0,7),(7,4)].
3. **VỪA — nhãn code cũ thành nhãn Đạo diễn.** `core/shot_complexity.py:104-123` reconcile: dữ liệu trước 15/10 không có `difficulty_by`
   nhưng có ghi chú "Đạo diễn chưa ghi độ khó…" → sau `apply` thành `director`. Sửa: `by_check = difficulty_by == "check" or (not
   difficulty_by and note.startswith("Đạo diễn chưa ghi độ khó"))`. Test: dữ liệu cũ sau apply → `label_from_director` None.
4. **THẤP — ví dụ prompt.** `prompts/01_director_scene_analysis.md:56` ví dụ `"difficulty": "easy"` → đổi `"unknown"`; `label_from_director`:
   'easy' mà `difficulty_why` rỗng → None (đi nháp).
5. **Dự án cũ đổi đường (chặt):** chỉ coi là nhãn Đạo diễn khi `difficulty_by == "director"` (reconcile mới ghi); còn lại → KHÓ + lý do.
6. **Duyệt 720p:** `core/autopilot.py:1031-1045` `_approve_unflagged` đang để ai_agent tự duyệt clip gen thẳng → clip direct phải chờ
   NGƯỜI duyệt như nháp (autopilot chờ có lý do, không hỏng). Test.
7. **THẤP — ước giây không đồng nhất.** `needed_seconds` chưa truyền ctx ở `core/shots.py:147` (pacing_warnings), `core/llm_runner.py:1171`
   → truyền `dialogue.speech_ctx`.
8. **THẤP — take theo nhóm.** `model_router.py:317` cờ `take` tính theo nhóm còn `hard_signs` theo shot → shot góc rộng trong nhóm take lọt
   gen thẳng; sửa: nhóm có take → cả nhóm khó (đã có `group_route` — đưa take vào).
9. **Bản chụp prompt:** dựng lại `tests/fixtures/ambient_motion_off.json`; kiểm diff chỉ khác đúng đoạn nhãn độ khó (ghi vào báo cáo).

## Luật
`docs/CHUAN_XAY_DUNG.md`; test đỏ → xanh; gom test 1 lệnh, ≤ 3 lần; không push, không sửa TODO.md; commit trên `claude/gop-1510`.
Sau vòng sửa: phiên chính đọc diff phần sửa + cả bộ test → gộp main → `devsys/areas.json` version +1 → khởi động lại 8501 + 8502.
