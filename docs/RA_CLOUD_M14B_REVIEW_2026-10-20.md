# Rà độc lập M1.4b (C-RA-M14B, làn cloud-C) — 20/10/2026

Đối tượng: `origin/cloud/v31-m14b`@`cd171eaf` (cloud-B). Nền: gộp `origin/main`@`efb6758` vào (không xung đột). Đối chiếu: đề bài "#### C-M14B"
(`docs/CLOUD_TASKS.md`), `docs/V3_1_M1_4B_THIET_KE_2026-10-20.md` (bản C-FIX-D19: NULL = theo môi trường, không hold), sổ `v31-d02-…`, C3-1.
Không áp migration CSDL thật, không gọi API thật. Nhánh sửa: `claude/zen-meitner-1vu42y` (nhánh do phiên cloud cấp — chứa M1.4b + main + bản sửa;
không tạo `cloud/v31-m14b-fix` vì phiên này chỉ được push nhánh của nó).

## Kết luận
Nhánh đúng hướng D02: provider theo dự án, NULL = môi trường, không tự sang API trả phí, migration không tự chạy, devsys mặc định `claude_cli`.
Tìm **1 CAO + 4 VỪA** (đã sửa hết, test đỏ → xanh) và **3 THẤP** (2 sửa kèm, 1 ghi lại).

| # | Mức | Lỗi | file:dòng (nhánh gốc) | Sửa | Test (`tests/test_v31_m14b_review_fix.py`) |
|---|---|---|---|---|---|
| 1 | **CAO** | Hết lượt / hết tiền mà không đọc được giờ mở lại (vd `out_of_credit`, lời CLI kiểu `…limit reached|1760000000`, `resets Oct 21, 4am`) → dừng **vĩnh viễn** mọi lời gọi `claude_cli` của CSDL (mọi dự án, QC nền, Đạo diễn); `quota_reopen` không có nơi gọi, lời báo chỉ tới "mở lại trong ⚙" không tồn tại | `core/llm_provider.py:quota_halted` 256–272, `_RESET` 197 | không có giờ mở → sau `PROBE_MINUTES`=60 cho đi MỘT lời gọi thử (claude_cli = 0 USD API; còn hết lượt thì CLI báo lại + ghi dấu mới); regex đọc được "resets Oct 21, 4am"; thẻ 💵 Tiền hiện dấu dừng 🔴 + nút "mở lại Claude" (quyền `settings`) | `QuotaWithoutResetTime` ×4 |
| 2 | VỪA | Tổ rà soát: hết lượt giữa lượt → từng thay đổi thành `failed` (giữ gen, phải bấm thử lại từng shot) và lượt gọi tiếp mọi thay đổi | `core/change_review.py:_review_group` 469–474, `process_pending` 495–498 | mã `usage_limit`/`out_of_credit` → thay đổi đang rà thành `code_only` (luật code đã chạy — như "không có Claude"), DỪNG lượt, các thay đổi sau giữ `pending`, 1 dòng diag `change_review_halt` | `ChangeReviewStopsTheRound` |
| 3 | VỪA | `qc_video_batch` không dừng khi hết lượt gói (chỉ auth/config/out_of_credit/ledger) | `core/claude_tasks.py:379` | thêm `usage_limit` | `VideoBatchStopsOnUsageLimit` |
| 4 | VỪA | QC hàng loạt dùng client DỰ ÁN cho mọi job (autoqc ảnh, autopilot `run_qc_batch` / `qc_video_batch`) — trái thiết kế bảng caller (`run_qc_batch`, `qc_video_batch` phải theo từng J) và khác autoqc video | `core/autoqc.py:_work` 127–147, `core/autopilot.py:474, 1178` | `run_qc_batch` / `qc_video_batch` nhận `client_for_job`; `JobClients.or_default(client)`: job có ảnh chụp → provider đó, job NULL → client đang chạy (như trước M1.4b); autoqc ảnh `per_job` như video; `JobClients.for_job` không dựng được → `LlmError(config)` có lý do (trước: đưa `None` → hỏng từng clip, chuyển chờ người) | `BatchQcUsesTheJobsSnapshot` ×2 |
| 5 | VỪA | Autopilot dừng vì hết lượt: ghi chú cắt 80 ký tự CUỐI → mất giờ mở lại; `claude_cli` hết tiền lại bảo "nạp tài khoản Anthropic" | `core/autopilot.py:_stop_if_claude_blocked` 524–540 | đọc lý do + giờ mở từ `llm_provider.quota_halted` (tham số `conn`, 4 nơi gọi truyền `p.conn`) | `AutopilotSaysWhenClaudeReopens` ×2 |
| 6 | THẤP | autoqc ảnh báo thiếu Claude bằng `missing_hint()` (môi trường) thay vì của dự án | `core/autoqc.py:128` | `missing_hint_for(conn, pid)` | (cùng lần sửa #4) |
| 7 | THẤP | Thẻ 💵 không báo Claude đang dừng | `dashboard/header.py:money_card` | cờ 🔴 khi có dấu dừng còn hiệu lực | (cùng #1) |
| 8 | THẤP — **chưa sửa** | `change_review.process_pending` chỉ rà lại `code_only` khi client MÔI TRƯỜNG có; dự án khai provider riêng mà máy không đặt `LLM_PROVIDER` → `code_only` của dự án đó không được Claude rà lại. Máy chính có `LLM_PROVIDER=claude_cli` nên chưa xảy ra; sửa đúng cần biết trước dự án nào có client (tránh quay vòng) | `core/change_review.py:485` | đề xuất: `states` gồm `code_only` khi `client_for` có, lọc theo dự án dựng được client | — |
| 9 | THẤP — ghi lại | `cost.cache_stats` nay đếm cả lượt `claude_cli` (không có token cache) → tỉ lệ đọc cache thấp đi | `core/cost.py:676` | sau C3-1 lọc `provider='anthropic'` | — |

## Đã kiểm, KHÔNG lỗi
- Không còn đường nào tự ra `anthropic` khi dự án NULL + env `claude_cli`: `client_for_project` → `client_from_env` → `client_for_provider("claude_cli")`.
  Có key + `LLM_PROVIDER` rỗng → None (test gốc `test_empty_provider_and_a_key_never_becomes_the_paid_api` xanh).
- Subprocess CLI không nhận key (`clean_env`, test gốc xanh). Lượt CLI ghi `llm_calls` (provider claude_cli), KHÔNG ghi `usage_events` (0 USD).
- Migration: không nằm trong `_migrate`/`V2_COLUMNS` → mở CSDL không tự thêm cột; thiếu cột → hành vi cũ; `down` từ chối khi còn dữ liệu trừ `force`;
  worker code cũ trên CSDL có cột mới: cột bổ sung NULL, không ràng buộc → không vỡ. Đúng C3-1.
- Job đang chạy giữ snapshot (`client_for_job`); gen lại giữ provider cha (`snapshot_job(parent)`).
- devsys: mặc định `claude_cli`, `--max-usd` chỉ bắt buộc cho `anthropic`; điểm `claude-cli` tính là chấm thật (không bắt đầu bằng `mock`).
- Caller còn `client_from_env`: chỉ đường không có dự án (công cụ dòng lệnh, `dashboard/admin.py` bài học, `adapters/check`, `asset_vision`/`research`
  toàn kho) — đúng "S explicit" của thiết kế; `bg_poll.change_review_round` dùng env làm mặc định + `client_for(pid)` cho dự án khai riêng.
- Test không bị nới: các thay đổi test của nhánh gốc chỉ đổi tên hàm / tham số (`test_prompt_rewrite`, `test_devsys`, `test_ui_prompt_versions`).

## Bằng chứng chạy (Linux cloud, 0 USD)
- `tests/test_v31_m14b_review_fix.py`: trước sửa **10 failed** (đúng lý do từng lỗi) → sau sửa **10 passed**.
- Cả bộ `pytest -m "not slow" -n auto tests`: **6310 passed, 5 failed, 12 skipped, 22 xfailed**. 5 đỏ (`test_end_popup_p24`, `test_cost_route_e1::…recut`,
  `test_ffmpeg_studio::…punches`, `test_qc_observe_d14::…byte_equal_baseline`, `test_sent_package::…unreadable_picture`) đỏ y hệt trên `main` cùng máy
  (môi trường cloud: chạy root, thiếu font/ffmpeg) — không do M1.4b.
- CHƯA chạy: cả bộ Windows, `-m slow` (`test_access`, `test_editor_apply`, `test_editor_review`, `test_rough_cut`, `test_ui_v2_acceptance`), agent rà quy
  ước 7 (luật cloud: không mở phiên con) — phiên chính làm khi gộp.

## Việc mở cho phiên chính
- Gộp: nhánh `claude/zen-meitner-1vu42y` = M1.4b + main + bản sửa + tài liệu C-M2X. C3-1 (migration thật sau sao lưu) vẫn là việc của phiên chính.
- Quyết định THẤP #8 (sửa ngay hay để M2.5).
