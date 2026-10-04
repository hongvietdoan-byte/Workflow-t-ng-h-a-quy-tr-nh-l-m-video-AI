# HANDOFF — S14.6 Gói K: đợt ngân sách + mức dùng theo ngày (nhánh `s14-6-budget-rounds`)

## Đã làm
- `core/budget_rounds.py` (mới): bảng `budget_rounds` (tạo trong `db._migrate` + `ensure()`), chỉ mục `idx_usage_events_at`.
  - `current / history / window`: chưa có đợt nào → đợt ảo tên theo ngày mốc thật (`first_name`, vd. "Đợt từ 30/09/2026") = mốc `budget.get()["since"]`.
  - `start_new(conn, actor, name, planned_usd, planned_llm_usd, reason)`: chỉ Owner, lý do + tên bắt buộc; đặt mốc + mức dự tính
    qua `money_reset.set_planned("trial")` và `("claude")` (không viết lại logic), đóng đợt cũ với tóm tắt (`summarize`: theo loại
    ảnh/video/âm thanh/Claude USD + số lượt, theo dự án, dòng chưa có giá → ước tính dư money_policy), mở đợt mới, audit `budget_round`.
  - `daily / day_detail / projects_in / unpriced_note`: ngày theo giờ VN (UTC+7), bỏ nhà cung cấp mock, lọc đợt + dự án.
- `dashboard/design/screens/money_days.py` (mới): nút `mc_days` trong thẻ 💵 → hộp thoại `dlg_money_days` (bảng theo ngày
  `md_round`/`md_project`/`md_day`, các đợt đã đóng, khối "▶ Bắt đầu đợt ngân sách mới" chỉ Owner `md_new_*`, `confirm_all`).
- `dashboard/header.py` money_card: gọi nút (chỉ người có quyền `settings` hoặc `monitor` — sổ chi mọi dự án; người "chỉ xem" không thấy, giữ test_access_ui) + hộp thoại; `dashboard/common.py`: thêm `dlg_money_days` vào `DIALOG_FLAGS`.
- `devsys/areas.json`: thêm `core/budget_rounds.py` + `tests/test_budget_rounds.py` (không tăng version).

## Test
- `tests/test_budget_rounds.py` (10), `tests/test_money_days_ui.py` (4, AppTest UI v2) — đỏ trước, xanh sau.
- Đo trên bản sao CSDL thật (2395 dòng sổ chi): daily cả sổ 0,03 s, chi tiết một ngày 0,005 s.

## Chưa làm / lưu ý
- KHÔNG mở đợt trên CSDL thật — người dùng tự bấm (💵 Tiền → 📅 Mức dùng theo ngày · đợt ngân sách → ▶ Bắt đầu đợt ngân sách mới).
- Mở đợt chỉ đặt lại thanh đợt thử + Claude; thanh dự án / theo người vẫn ở khối "↺ Đặt lại thanh tiền" cũ.

## Sửa sau rà soát độc lập (04/10)
1. `start_new` nguyên tử: kiểm đầu vào + `summarize` trước; đóng + mở đợt trong một giao dịch (`rollback` khi lỗi); chỉ sau đó mới
   đặt thanh qua money_reset. Thanh nào lỗi → `BarsNotReset` (đợt đã ghi trọn, câu lỗi nêu thanh + cách sửa). Mốc đợt được đồng bộ
   theo mốc thanh đợt thử sau khi đặt lại.
2. Mở đợt kèm 2 tùy chọn MẶC ĐỊNH BẬT: thanh các dự án đang có ngân sách (`reset_targets`, sửa mức từng dòng `md_new_plan_<pid>`) và
   thanh theo người (`md_new_users`); câu xác nhận liệt kê đúng các thanh (`bars_text`).
3. Dòng chưa có giá không ước tính được (âm thanh) tách nhóm "không ước tính được (N lượt)", không cộng tổng, ô không hiện $0.00.
4. `db.schema_stamp` băm cả `budget_rounds.TABLE`.  5. `dialog_if_open` kiểm quyền `settings`/`monitor` (`money_days.can_view`).
6. Khối "↺ Đặt lại thanh tiền" cũ: ô `shell-mr-trial` bị khóa (giữ khóa), câu chỉ sang "▶ Bắt đầu đợt ngân sách mới".
7. Tên đợt đầu theo ngày mốc thật (giờ VN); không mốc → "Từ đầu sổ chi".
- Còn lại (chưa đổi, ngoài phạm vi rà): nút "▶ Bắt đầu đợt thử" trong ⚙ Đợt thử & Claude (`budget_start`) vẫn dời mốc thanh đợt thử
  mà không mở đợt → có thể lệch mốc đợt; nên chuyển sang budget_rounds ở lượt sau.
