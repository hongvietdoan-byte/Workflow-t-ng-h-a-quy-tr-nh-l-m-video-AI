# Rà ĐỢT 19 việc 3 — 20/10/2026

- Root RÀ NHẸ độc lập tài liệu/source và sửa 1 điểm thiết kế: cache client bound phải chứa job/operation, tránh dùng nhầm ledger giữa hai job cùng dự án/cấu hình. Bổ sung credential_profile_id công khai không hash secret, nguyên tắc rotation cùng tài khoản/mismatch giữ chờ và ma trận ACL viewer/editor/Owner; đều là đề xuất chưa được duyệt triển khai. Test plan thêm ca cache/account/ACL; không chạy test giả cho tài liệu, không sửa code.

- Nhánh `codex/d19-viec3-provider`, nền `7c41073c`; CHỈ TÀI LIỆU, chưa commit theo chỉ đạo điều phối.
- Thiết kế `docs/V3_1_M1_4B_THIET_KE_2026-10-20.md`: schema nullable legacy, revision immutable không secret, project/job/scope factories, job frozen kể cả retry/child, RPC/context/cache, quota và ledger CLI 0 USD/token NULL, migration up/down bảo toàn, test plan, quyền Cấp 2/3.
- Bằng chứng nguồn: rg các điểm client_from_env/ledger_factory/AnthropicClient/llm_client/fresh_client ở core/dashboard/tools/devsys/research = **76 hit /44 file** (gồm tài liệu/declaration/static); quét ngoài các thư mục không-test không thêm hit. Phụ lục lưu từng file:hàm:dòng + đích, không coi hit là API call count.
- Đối chiếu thêm consumer injected: chat_prompt/rewrite, change_review, director_blockout, camera_plan, autoqc/batch, video_analysis và reference_analysis, UI ready/actions, Kho/nghiên cứu, scripts, devsys ngoại lệ API xác nhận. image_block static không phải call mạng.
- M1.4a còn ở nhánh Claude, không sửa production/llm_runner hoặc test của Claude. Cần quét lại nguồn sau khi gộp dependency; D02 là chính sách không phải lệnh triển khai.
- Findings thiết kế đã xử lý: legacy provider NULL không cho fallback project/default; down không xóa cột hay rollback về fallback key trả phí; scope global không giả pid=0; CLI không giá API/không biến token thiếu thành0; call ledger và usage_events cần transaction/idempotency riêng.
- Tự rà: không import/chạy Python, không SQL/migration, không pytest giả ĐỎ; chỉ đọc source tracked và ghi tài liệu worktree. Không real env/credential/token/header, data/projects, API, cờ, live, TODO, PLAN, areas, commit/push/main.
- Kiểm `git diff --check` sạch; root đã RÀ NHẸ độc lập phần thiết kế và source liên quan như ghi đầu báo cáo. Chưa kiểm hành vi runtime (đúng phạm vi design-only).
- Mở: duyệt scope default/quyền chỉnh, quota_domain không secret, trạng thái legacy hold, chính sách resume khi reset không biết, maintenance/up/down và phạm vi code Cấp2; migration production/API xin Cấp3 riêng.
