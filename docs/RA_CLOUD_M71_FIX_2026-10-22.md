# C-M71-FIX — lỗi rà kỹ M71 + rò tệp test (cloud-C, 22/10; chuyển từ cloud-E)

- Nhánh: `cloud/v31-m71-fix`, tách từ `origin/main`.
- 0 USD. Không đổi cờ production.

## 1. VỪA — D6 tạm ngừng theo NGUỒN Claude, không chung mọi dự án (`core/chat_prompt.py`)
- `quota_scope(conn, job)` trả về provider của job (`llm_provider.job_provider`): lấy ảnh chụp lúc tạo job, không có thì lấy theo dự án / môi trường (M1.4b).
- Khóa tạm ngừng đổi thành `chat_prompt_quota:<provider>`.
  - Dự án A (`anthropic`) báo out_of_credit chỉ tạm ngừng D6 của các job cùng nguồn.
  - Dự án B có Claude riêng (`claude_cli`) vẫn chạy.
- Không tách thêm theo model hay cấu hình: hết tiền / hết lượt là chuyện của cả TÀI KHOẢN. Key Anthropic dùng chung biến môi trường, nên cùng provider nghĩa là cùng tài khoản (rà mục a).
- `_pause`, `_paused_until`, `_quota_paused`, `saved_view` (cho `pregen_check --payload` / `replay_payload`) đều đi theo scope của job.
- Không còn chỗ nào đọc khóa chung cũ (đã grep toàn repo). Khóa cũ trên máy chính tự hết hạn sau 600 giây.

## 2. THẤP — mục ĐỎ "rà lỗi" tự đóng khi sự kiện của nó `skipped` (`core/change_review.py` `_hold_failed`)
- Trước đây chỉ tự đóng khi sự kiện `e.state='reviewed'`. Hai trường hợp sau làm mục đỏ kẹt tới khi người bấm Bỏ qua:
  - tắt cờ `change_review_motion` → `process_pending` đổi motion `code_only` (kể cả dòng hết tiền) sang `skipped`;
  - rà lại ra keys rỗng (cũng thành `skipped`).
- Nay `skipped` cũng tự đóng mục.
- Khi cờ motion tắt, `_blocking` vốn đã không giữ cổng cho motion (C4), nên đóng mục là đúng thiết kế (rà mục b).

## 3. THẤP — LIMIT không bị dự án không có Claude ăn mất (`process_pending`, nhánh `client_for`)
- Trước khi áp LIMIT: đọc `client_for(pid)` một lần cho mỗi dự án có dòng `code_only` hết tiền, rồi chỉ chọn nhóm của dự án CÓ Claude.
- Trước đây, từ 5 nhóm `code_only` (id nhỏ) của dự án không có Claude trở lên sẽ chiếm hết suất, và nhóm của dự án có Claude không bao giờ tới lượt.
- `clients` được dùng lại trong vòng lặp. `client_for` chỉ dựng object, không gọi mạng.

## 4. Ghi chú — `data/flag_baseline.json` (M7.2)
- Baseline ghi `hero_takes` / `scene_qc_claude` = on. Hai cờ này nay có `costs: True`, nên `_guarded` hạ chúng về OFF trên máy MỚI (máy chưa có tệp 🧪). Đúng thiết kế: cờ tốn tiền không tự bật từ baseline.
- **Đề xuất cho phiên chính:** chụp lại baseline (`--baseline-capture`) trên máy chính để tệp khớp trạng thái thật.
- Không tự đổi cờ production.

## 5. Rò tệp test vào `data/ref_padded` THẬT — tìm gốc + sửa
- **Gốc** (dò bằng probe theo từng test trên cả bộ, `-n auto`):
  - 16 tệp test có `os.environ.pop("PIPELINE_DATA")` ở tearDown (`test_dashboard`, `test_users`, `test_auth`…). Lệnh này xóa luôn thư mục data cách ly mà `tests/__init__.py` đặt cho cả lượt.
  - Test chạy SAU trong cùng worker (vd `test_forms_and_render_slot` với CSDL `:memory:`) rơi về mặc định `data/projects`. Hệ quả: `seedance_refs.pad_to_rule` ghi `*_pad.png` vào `data/ref_padded` của repo.
  - `test_v31_dp12_pilot_a` chỉ nhắc chuỗi `data/ref_padded`; nó không ghi gì.
- **Hệ quả đã xảy ra:** 72 tệp `data/ref_padded/*_pad.png` lọt vào git qua các commit gộp (9687151a, b3d4e143, e01f710b).
- **Sửa** (`tests/conftest.py`, fixture autouse):
  1. Mỗi test bắt đầu lại với PIPELINE_DATA cách ly nếu biến bị xóa. Gán thẳng `os.environ`, không dùng monkeypatch, để setUpClass của lớp kế cũng có.
  2. `seedance_refs.PAD_DIR` trỏ vào `tmp_path` của test. Test kiểm đường mặc định (`test_padded_copy_goes_to_the_running_data_folder`) tự đặt `PAD_DIR=None`.
  3. `git rm --cached data/ref_padded` + thêm `data/ref_padded/` vào `.gitignore`. Không code / test nào cần tệp có sẵn ở đó.
- **Bằng chứng:**
  - Chạy cả bộ khi đã TẮT sửa → 4 tệp mới trong `data/ref_padded`.
  - Bật sửa → **0 tệp**.
  - Test thứ tự trong `tests/test_v31_m71_fix.py` (test trước pop PIPELINE_DATA, test sau kiểm `pad_dir` nằm ngoài repo): ĐỎ trên conftest cũ, XANH sau sửa.
- **Còn lại** (không bắt buộc): sửa dần 16 test `pop` để khôi phục giá trị cũ. Conftest đã chặn hậu quả.

## Test
- Test mới: `tests/test_v31_m71_fix.py` (6) + `tests/test_change_review.py` (2). Trên code cũ: 4 test nhắm đúng lỗi đều ĐỎ.
- Test liên quan (change_review, chat_prompt*, seedance_send_s2, world_rules, auth, dashboard, forms_and_render_slot): 282 xanh.
- Full suite (cloud 3.13, `-m "not slow" -n auto`): **7079 passed**. 25 đỏ đều là golden cần native Python 3.14 (nền). Sau khi chạy cả bộ, `data/ref_padded` có 0 tệp.

## Rà soát (quy tắc 7)
- Không có lỗi CAO hay VỪA.
- Đã làm theo 2 đề xuất: scope chỉ theo provider; conftest gán thẳng `os.environ`.
- Ghi nhận, không sửa:
  - `diag` "noclaude" ghi cho mọi dự án có dòng hết tiền mỗi lượt nền;
  - sự kiện motion đã `skipped` lúc cờ tắt không được rà lại khi bật cờ — nhất quán với hành vi cũ.
