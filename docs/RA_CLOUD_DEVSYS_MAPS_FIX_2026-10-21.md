# C-DEVSYS-MAPS-FIX — sửa lỗi rà nhánh sơ đồ dây chuyền (cloud-C, 21/10)

- Nhánh: `cloud/v31-devsys-maps` (nối tiếp C-DEVSYS-MAPS).
- 0 USD, không đụng CSDL thật. Cờ `ui_step_log` vẫn TẮT + `verified: False`.

## VỪA 1 — bỏ qua cổng / gen lại vượt trần = ĐỎ kèm mã (đề mục 6)
- `core/ui_step.RESULTS["skip"] = "error"`. Gọi `skip` mà không truyền mã thì tự gắn mã `gate_skipped`.
- Mã bước mới:
  - `gate_skipped`: vẫn gen dù cổng chặn;
  - `regen_over_limit`: làm lại job đã vượt trần gen lại tự động;
  - `regen_same_input`: gen lại bị từ chối vì đầu vào y nguyên, hoặc job dừng vì lý do đó.
- `dashboard/steps/step2.py` (nút gen ảnh `gen_img_{pid}`): khi cổng chặn mà người vẫn gen, bước ghi `skip` kèm `error_code="gate_skipped"`.
- "↺ Làm lại từ đầu" (4 chỗ `restart_job`: step2 × 2, `storyboard_cards`, step4) gọi `C.log_over_limit`.
  - Key ghi theo màn: `lam_lai_anh` (ô `sb.card`) và `lam_lai_video` (ô `vd.gen`).
  - Mã chọn theo `p._retries_exhausted(job)`, tính TRƯỚC khi bấm.
- step4 "↻ Gen lại video": mã `regen_same_input` lấy từ lỗi thật của lượt bấm (thông điệp bắt đầu bằng `không gen lại:` ở `core/regen.py`). Không còn đoán lại sau khi lượt đã chạy.

## VỪA 2 — CSDL khóa không còn giữ nút / lệnh
- Trước đây `ui_step` ghi qua `diag.record`: thử lại 3 lần, mỗi lần chịu timeout 60 s của kết nối trang. Đo trên code cũ: test giữ `BEGIN IMMEDIATE` chạy **6 phút**.
- Nay `ui_step._write` mở kết nối riêng (`timeout` = `busy_timeout` = 1000 ms) và ghi MỘT lần.
  - Ghi không được thì bỏ dòng đó; dòng mất được nói ra stderr và ghi vào `<db>.diag_lost.log` (qua `diag._keep_lost`).
  - Lỗi chỉ rollback kết nối riêng, không rollback kết nối của nơi gọi (trừ CSDL trong bộ nhớ, nơi ghi trên chính kết nối đó).
  - Kết nối gọi đang giữ giao dịch ghi (công cụ CLI) thì ghi trên CHÍNH kết nối đó, như hành vi cũ, để kết nối riêng không phải chờ chính nó.

## VỪA 3 — cờ sai tên trên sơ đồ
- Ô `sb.stage3d` vẫn khai cờ `stage_view_ui` (đúng tên ở nhánh C-STAGE-VIEW), thêm `"pending_flags": {"stage_view_ui": "C-STAGE-VIEW"}`.
  - `devsys/pipeline_maps.py` hiện "cờ … chờ nhánh C-STAGE-VIEW gộp" và không tính cờ này vào `unknown_flags`.
- Test `test_real_map_builds_and_everything_named_exists` siết thêm `assert not m["unknown_flags"]`.
- Test mới `test_pending_flags_expire_when_the_branch_lands`: khi nhánh đó đã gộp thì báo đỏ để gỡ `pending_flags`.

## THẤP
- `core/ui_step.run_cli(tool, _main, argv)` ghi `cli_step` SAU khi chạy, theo kết quả thật:
  - lỗi hoặc `sys.exit` khác 0 → `error` kèm lý do (nếu lỗi xảy ra giữa giao dịch: rollback rồi mới ghi);
  - công cụ tự nói `step["result"]` / `step["why"]`;
  - nhánh return sớm không làm gì → `warn`.
- `stage_auto`:
  - 4 nhánh return sớm (sai tham số, shot đã vẽ) ghi `warn`;
  - 2 câu trả lời LỖI ghi `error`;
  - chưa có `--yes` (chỉ in ước tính) thì không ghi gì.
- `stage_previs --plan-only` không ghi. Các `sys.exit` xảy ra trước khi biết cảnh ("không có cảnh", "chưa có lượt") cũng không ghi — chấp nhận được.
- `replay_payload`: `ui_step.cli(..., flag_checked=True)`. Chỉ kiểm cờ của máy `<main>` (qua `_main_flag_on`), không kiểm lại cờ của repo đang chạy lệnh.
- `tools/audit_run.py` (mục 8) và `tools/kld_round_stats.py` (mục 4) lọc bỏ `stage NOT IN ('ui_step', 'cli_step')`.
- Bằng chứng trên sơ đồ đổi sang key nút hoặc tên hàm cụ thể:
  - `btn_analyse_{pid}`, `"🤖 Lập kế hoạch"`, `lock_go_{pid}`, `gen_img_{pid}`, `dr_{jid}`, `board_ok_{pid}`;
  - `send_preview.video_package(`, nút Ý tưởng của `step1_idea.py`;
  - `def capture(`, `def collect_clips_for_render(`, `def build_report(`.
  - Ô `bg.popup` ("không có kiểm"): bằng chứng = dòng `end_popup.held_s` của `final_qc`, thêm `loose: true`. Ô này đổi xanh → **vàng**, đúng nhãn của nó.
- **14/49 ô `loose` do người ghi tay** (13 ô cũ + `bg.popup`). Màu "lỏng" của các ô này là nhận định tay ở mốc 17/10, không tính từ code.

## Rà soát (quy tắc 7) — agent báo 6 mục, đã sửa hết
1. VỪA: key `lam_lai_tu_dau` không có ô nào trên sơ đồ, nên đỏ không lên. Sửa: tách key theo màn + test "mọi key `log_step` có trên sơ đồ".
2. THẤP–VỪA: lệnh lỗi giữa giao dịch làm `run_cli` tự khóa, dòng error bị mất. Sửa: rollback trước khi ghi error; ghi ok trên chính kết nối đó. Có test.
3. THẤP: nhánh return sớm vẫn ghi ok. Sửa: `warn` / `error` / không ghi, như trên.
4. THẤP: `_write` rollback kết nối của nơi gọi. Sửa + test.
5. THẤP: mã `regen_same_input` có thể gán sai. Sửa: lấy từ lỗi thật; với "Làm lại từ đầu" thì phân biệt vượt trần / gen lại y nguyên.
6. THẤP: `pending_flags` không có hạn. Đã thêm test hết hạn.

## Test
- `tests/test_devsys_pipeline_maps.py`: thêm 15 test.
  - Trên code cũ: **11 đỏ**, trong đó test CSDL khóa chạy 6 phút.
  - Sau sửa, cùng `test_diag` / `test_stage_auto` / `test_stage_previs`: 166 xanh.
- Full suite: xem mục dưới.
