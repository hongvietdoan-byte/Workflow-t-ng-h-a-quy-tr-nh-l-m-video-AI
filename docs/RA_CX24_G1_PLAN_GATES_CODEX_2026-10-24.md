# CX24-G1-PLAN-GATES — Codex 1, pha parser/tooling

- Nhánh `codex/v31-plan-gates`, nền `d9c06243` từ origin/main. Đề `docs/CODEX_TASKS.md` CX24-G1; nguồn cổng: `docs/GIAM_SAT_KE_HOACH_V31_2026-10-24.md` §3 và §4.
- Acceptance: giữ status/commit/trọng số/% code cũ; thêm lớp cổng độc lập, dòng cũ mặc định ⬜; cổng Dashboard cần ảnh/ui_step; việc kế bỏ CHỜ PHỤ THUỘC/⏸; CLI hai cột; thêm cổng M0–M8 mà không sửa ✅ code.
- Kế hoạch ngắn: parser và fixture đỏ → cột tổng/đợt + CLI xanh → bổ sung dòng kế hoạch bảo thủ → nối UI sau dependency DEVSYS-FIX gộp. Không cherry-pick nhánh dependency và không sửa `devsys/app.py` trong pha này.

## Kết quả pha này

- `devsys/plan_progress.py`: thêm `gate_status`, `gate_declared`, `gate_evidence`, `gate_warning`; khai báo thiếu/trùng/sai hoặc thiếu bằng chứng thì không cộng cổng. Task Dashboard nhận diện theo danh sách mốc rubric và title Dashboard/giao diện.
- `summary()` giữ `total` và từng wave `pct` = code để tương thích caller cũ; thêm `total_code`, `total_gate`, `pct_gate`, `gate_done`, `gate_warnings`. Cổng không cộng nửa; ✖ không nằm mẫu số.
- CLI/bảng Markdown hiện % code và % cổng, cùng cảnh báo khai báo cổng. Việc kế bỏ dòng CHỜ PHỤ THUỘC và ⏸.
- Bổ sung cổng cho 75 dòng M0–M8 theo giám sát; M1–M8 giữ ⬜ vì cổng đầy đủ chưa có bằng chứng. M0 lấy xác nhận báo cáo §3, riêng M0.8 giữ ⬜ do thiếu ảnh/ui_step. **Không đổi trạng thái code nào.** Đây là lớp khai báo bằng chứng, không truy cập hay xác minh lại dữ liệu thật.
- Nền hiện tại có 54 việc code ✅, 4 🔄; tổng code **72,9 %**, cổng **10,3 %**; M0 cổng **88,9 %**. Khác số 73,5 % của báo cáo lịch sử vì main nền đã có cập nhật M4.8; không tự điều chỉnh code để khớp số lịch sử.
- Sửa docstring cũ `dashboard/stage_desk_ui.py`: N12 previs đã tồn tại; ghi thêm N14/N15/N16 theo caller hiện có. Không đổi ORDER, widget key hay hành vi.
- Test mới đăng ký trong `devsys/areas.json`, giữ nguyên version nền; không thêm cờ/provider/API.

## Đỏ → xanh, rà nhẹ

- Trước sửa: **11 failed / 0,36 giây**, file fixture mới kiểm thiếu lớp cổng/skip dependency.
- Sau sửa gom regression mới + PlanProgressTests + PlanFocusTests + PlanMapTests: **30 passed / 1,14 giây**. Tổng hai lượt pytest; không nới test và không chạy cả bộ.
- Có ca Dashboard chỉ commit chưa đủ; ảnh/ui_step được chấp nhận; thiếu/khai trùng cổng không tăng %; cổng không đạt trước code; write_table lặp idempotent và giữ dòng task gốc.
- Native Python spawn explicit whitelist + HOME/TEMP giả; thay OBJECT os.environ bằng dict giả trước pytest/target imports; `--tb=no`, không showlocals/envdump; không đọc khóa/API/DB thật.
- Tự rà phần đổi: status/commit/weight cũ nguyên vẹn; tránh coi unit test là cổng thật; parser không mở path evidence (chỉ kiểm khai báo), không thay quyền/luồng gen/cờ. Root rà nhẹ diff trước gộp.
- `related_areas.py` xác nhận khu vực devsys + step2 (step2 chỉ docstring); không có caller khu vực khác. Test chậm bắt buộc ở bước gộp: test_devsys.py, test_devsys_v2.py, test_hop_thu.py.

## Còn mở — chưa XONG toàn task

- **Chưa nối** hai lớp trên trang 📋 Kế hoạch và 🗺 Sơ đồ tiến độ, chưa tô màu code/cổng khác nhau, chưa GUI QA. `devsys/app.py` chờ CX24-DEVSYS-FIX được gộp; tránh tranh app với CX24-GIAM-SAT.
- Source bằng chứng hiện là khai báo trong kế hoạch, không tự chứng minh file ảnh là ca dùng thật: phiên chính/giám sát kiểm chứng nội dung nguồn, không dùng bảng để tự bật cờ.
- Bên gộp chạy checks theo related_areas và full Windows phù hợp; sau nối/gộp code devsys phiên chính restart 8502, health 8501/8502. Codex 1 không thao tác live.
