# HANDOFF — S14.6 Gói K: đợt ngân sách + mức dùng theo ngày (nhánh `s14-6-budget-rounds`)

## Đã làm
- `core/budget_rounds.py` (mới): bảng `budget_rounds` (tạo trong `db._migrate` + `ensure()`), chỉ mục `idx_usage_events_at`.
  - `current / history / window`: chưa có đợt nào → đợt ảo "Trước 04/10" = mốc `budget.get()["since"]`.
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
