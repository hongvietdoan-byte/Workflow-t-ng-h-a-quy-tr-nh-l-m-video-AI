# Bàn giao CX23-M47B

- Nhánh: `codex/v31-m47b`; worktree: `D:\AI-Video-Pipeline\.codex-wt\v31-m47b`.
- Đã làm phần lõi C3-4, module UI override độc lập, siết `core/video_gate.py` / `dashboard/video_gate_ui.py`, và thêm helper lõi Q6(c) đọc vai từ BYĐ v2 trên toàn dự án. Nhân vật `chinh` ở bất kỳ shot nào mà chưa duyệt ảnh mốc thì BLOCK; override đúng mã lỗi và tập mục BYĐ chính hiện tại mở riêng mục đó; vai không chính/không khai vai thì WARN; thiếu BYĐ v2 hoặc mục vai chính không khớp nhân vật dự án thì REVIEW; cast hợp lệ không chính không khớp thì WARN; tên cast sai kiểu thì REVIEW. Tham số vai tập trung thành hằng số để EP đổi sau; không thêm schema.
- Bộ test liên quan hiện xanh: 64 passed trong 2.44 giây (`test_v31_m47b_overrides.py`, `test_video_gate.py`, `test_shot_intent.py`); 11 ca Q6(c), trong đó năm ca rà độc lập mới chạy đỏ trước sửa và xanh sau.
- Reviewer độc lập phát hiện cast chính/phụ không khớp nhân vật, waiver theo ID cũ không hết hạn khi BYĐ đổi, tên cast sai kiểu và vai hợp lệ chỉ-được-gọi-tên. Đã sửa bằng REVIEW/WARN, fingerprint, guard kiểu và đang chờ reviewer xác nhận diff cuối.
- M80C còn ĐANG LÀM; không sửa `dashboard/steps/step1.py`, `step1_v2.py`, `step2.py`, `step4.py`, hoặc `dashboard/send_preview_ui.py` trước khi M80C gộp.
- Sau M80C: lấy main mới nhất, cập nhật/rebase nhánh này, kiểm xung đột `devsys/areas.json`, nối caller override vào thẻ BYĐ/sổ lỗi/gói và gọi helper Q6(c) tại caller Bước 1; hoàn tất Q6(a). Caller thuộc M80C; không sửa `dashboard/steps/step1_characters.py` trong nhánh này.
- Cờ `qc_overrides` giữ OFF. Không chạy migration trên `data/manifest.sqlite`, không thử Dashboard production, không gọi API trả phí.
- Báo cáo phần độc lập: `docs/RA_CX23_M47B_CODEX_2026-10-23.md`; đây chưa phải báo cáo hoàn tất toàn việc.
