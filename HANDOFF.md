# HANDOFF — S14.2 (A2 nhãn giá + J6 + budget_start + khóa --max-usd script)

Nhánh `s14-2-price-labels` (từ `b15522a`). Không sửa TODO.md, không push, không merge main.

## Đã làm
1. **A2 — nút tốn tiền ghi giá ước tính (tính dư)** trên nhãn hoặc dòng chú thích ngay trước:
   - Hàm mới ở `core/cost.py`: `image_button_tag` (có `retake_conn` cộng lượt Đạo diễn viết lại prompt khi cờ `director_rewrite` bật),
     `video_button_tag`, `video_batch_tag`, `llm_button_tag`, `llm_tokens_tag`; `clip_estimate(..., seconds=)`.
     Chưa có giá → "chưa có giá — ước tính dư ≈ … USD" (money_policy); không có giá nào cùng loại → "chưa có giá".
   - Nhãn: step1_characters (trang phục 2 ảnh, nghe thử giọng, Lock, kiểm Bible, chọn giọng), step1_director (Director/chạy lại,
     hỏi lại cảnh lỗi, rà thoại, chia shot lại), step1_run (▶ Tiếp tục = phần còn lại), step2 (thẻ ảnh v1 + chi tiết ảnh + duyệt
     storyboard), step3 (TTS, đặt thời lượng theo giọng, tạo lại câu lỗi), step4 (Gen video), step5 (Xuất bản đầy đủ — chỉ đổi nhãn
     trong `_deliver_button`, KHÔNG đụng `delivery_panel`), storyboard_cards v2 (dòng chú thích giá trên hàng nút ↻ Vẽ lại; duyệt
     storyboard), admin (chắt lọc cẩm nang). Mọi `key=` giữ nguyên.
   - Test quét `tests/test_price_label_scan.py` (AST: nút có hàm tốn tiền trong nhánh phải có giá; danh sách ALLOWED rỗng).
2. **J6** — `step5.editor_review_panel`: thiếu Claude → `st.error` nói lý do + cách xử lý (ANTHROPIC_API_KEY / LLM_PROVIDER=claude_cli).
3. **budget_start** — `core/budget_rounds.start_trial` (đi qua `start_new`: chỉ Owner, lý do bắt buộc, đóng đợt + mở "Đợt thử dd/mm
   HH:MM"; trần ảnh/âm thanh lưu sau khi mở được) + UI `dashboard/design/screens/money_days.trial_start_button` (giữ khóa
   `budget_start`, thêm ô `budget_start_why`). Câu sửa của `BarsNotReset` không còn chỉ sang nút cũ.
   **CHƯA NỐI vào `dashboard/header.py`** (file bị cấm sửa ở phiên này). Việc còn lại ở header.py `_dialog_budget` — thay khối
   `if c1.button("▶ Bắt đầu đợt thử …", key="budget_start", …): budget.save(...); budget.restart(...); st.rerun()` bằng:
   ```python
   from dashboard.design.screens import money_days
   if money_days.trial_start_button(p.conn, me(), usd, cap, acap, c1):
       st.rerun()
   ```
   (`me()` = actor dict có `role`, như `MD.dialog_if_open(me())` ở header.py:518.)
   Không đổi khóa nên không cần bảng RENAMED.
4. **Khóa cứng `--max-usd`** — `core/script_cap.py` (`ScriptCap`, `from_args`, `require`, `add_argument`, `NO_CAP`), móc vào
   `budget.check_image/video/audio`, `cost.record_usage`, `llm_runner` (trước lời gọi Claude: input + ≤ 4000 token ra; sau: giá thật).
   Không có trần bật (dashboard) → không đổi gì. Áp cho 27 script `tools/` + `tools/experiments/`; danh sách trắng có lý do ở
   `tests/test_script_cap.py` (voice_trial, audio_s26_s115: chỉ âm thanh chưa có giá USD; audit_run, recover_clips, s411_s412_probe: chỉ đọc).

## Test
- Đỏ → xanh: `tests/test_price_label_scan.py` (28 nút thiếu giá → 0; J6), `tests/test_budget_rounds.py::RoundTests::test_start_trial_*`,
  `test_trial_start_button_*`, `tests/test_script_cap.py` (quét script: 25 script thiếu trần → 0).
- Sửa test cũ: `tests/test_ui_deliver.py` (nhãn Xuất bản đầy đủ có " · ≈ 0.00 USD (ước tính)").

## Rủi ro / lưu ý
- `tools/monthly_research.py` giờ BẮT BUỘC `--max-usd` → lịch Task Scheduler cũ (nếu có) phải thêm `--max-usd 1.0`.
- `pilot_run.py`: mọi lệnh trừ status/approve/relink cần `--max-usd`.
- Nhãn Claude dùng trung bình đo của khâu "director" cho các việc nhỏ (rà thoại, Lock…) → số có thể cao hơn thật (tính dư, cố ý).
- Script thử nghiệm cũ: chạm trần ở lời gọi Claude giữa chừng → CapReached dừng script (tóm tắt in lúc thoát); file đã ghi được giữ.
- `areas.json`: thêm `core/script_cap.py`, `tests/test_price_label_scan.py`, `tests/test_script_cap.py` vào khu vực `budget` (không tăng version).

## Sửa theo rà soát độc lập A2 (05/10, sau `git merge main` có S14.19)
1. (chặn) `devsys/app.py`: nút "Chấm N khu vực bằng Claude" spawn qua `scorer.score_command` (+ `--max-usd` = `usd_max` làm tròn lên
   cent); `scorer.run_state(log)` → lần chấm bị từ chối / DỪNG / lỗi hiện `st.error` + nhật ký trên trang. Test `DevsysScoreSpawn`.
2. (lỗ khóa) `core/storyboard_frames.run(..., conn=)`: mỗi khung hỏi `script_cap` (CapReached) + `budget.check_image` (hết tiền)
   TRƯỚC khi gửi; khung đã gửi vẫn được lấy về, `res["stopped"]` nói lý do. storyboard_test / scene_wide_test truyền `conn=p.conn`.
   `test_spend_gate_scan` PENDING_B thêm `storyboard_frames.run` (chưa có project_budget — S14.1 A1 phần còn lại). Test `ScriptCapTests`.
3. (a) `runner.submit_pending`: trần script đã dừng → hủy job queued (lịch sử ghi lý do), hết job đang chạy → CapReached kết thúc vòng chờ.
   (b) `cap.start()` cài excepthook: CapReached in một câu tiếng Việt, không traceback (mã thoát ≠ 0).
   (c) ví dụ lệnh / câu "thêm --yes" trong script + dòng S16 kế hoạch ghi `--max-usd`.
   (d) `llm_tag` ghi "(ước tính)"; `video_batch_tag` thêm "tự gen lại tối đa 2 lần ≈ …" (AUTO_REGEN_LIMIT video).
   (e) test quét giá: `form_submit_button`, `on_click=` (lambda / def), `idea_to_script.*`; PRICE = `≈\s*\$?[\d,.]+|chưa có giá`.
   (f) `cost._memo`: giá nhãn (video_batch_tag, lượt viết lại prompt của image_button_tag) nhớ tới khi CSDL đổi (total_changes + data_version).
