# Rà CX22-REPORT — Codex 1 — 24/10/2026

## Phạm vi

Công cụ `tools/project_report.py` tạo Markdown và JSON sidecar trong `docs/reports` của `--root`; không gọi mạng/provider và không bootstrap CSDL. Bảy mục: tóm tắt, tiến độ code/cổng riêng, khối lượng, bốn loại chi phí, chất lượng, rủi ro, việc EP/quy hoạch hai tuần (đề xuất).

Nguồn phiên và CSDL phải chỉ định rõ bằng `--session-dir` và `--db`. Phiên xây dựng/test **chưa đọc nhật ký Claude hay manifest.sqlite thật**. Bản báo cáo dữ liệu thật và PDF thật do phiên chính chạy sau rà an toàn.

## Bằng chứng đỏ → xanh

- Commit RED `86e9a859`: 8 lỗi import fixture vì công cụ chưa có; không diễn đạt thành tám lỗi nghiệp vụ.
- Lượt đầu sau code: 6 qua, 1 bỏ qua symlink Windows, 1 lỗi fixture đọc UTF-8 bằng codec mặc định. Sửa test chỉ định UTF-8, không nới assertion.
- Lượt tiếp: 16 qua, 1 bỏ qua, 1,45 giây. Bao gồm CLI subprocess độc lập không PYTHONPATH, canary nội dung/email/path, cumulative message ID xuyên file, tháng Asia/Saigon, role/cache thiếu UNKNOWN, agent lồng nhau, readonly DB/hash, ledger schema thật thiếu USD, holds TTL, EP legacy thiếu phase, reply kind `tra_loi`, mẫu số rejected-only.
- Lượt gom sau rà thứ nhất: 19 qua, 1 bỏ qua, 1,88 giây. Thêm tự đọc kỳ trước -7, scope DB/session, PDF local giả lập, dừng chỉ cây renderer sở hữu khi timeout. Không chạy browser/PDF thật.
- Vòng rà 3 P2: **6 đỏ trong 1,42 giây**. Bốn ca cutoff/activity chạy trên production chưa sửa. Hai ca hardlink là **negative control có kiểm soát**, thay writer trong process test bằng đúng kiểu write_text trước sửa, vì coder đã sửa hardlink trước lúc thêm fixture; không claim hai ca đó là TDD nguyên bản.
- Sau vòng sửa: **26 qua, 1 bỏ qua trong 4,04 giây**, chỉ file test_report. Có fixture writer WAL còn mở: ledger mới commit chỉ trong WAL vẫn đọc được, SHA main DB và WAL trước/sau bằng nhau khi writer không ghi thêm. Không suy điều này thành hash live phải bằng khi có writer khác hoạt động.

## An toàn và nghĩa số liệu

- SQLite URI `mode=ro`, `PRAGMA query_only=ON`, `BEGIN`; truy vấn bảng/cột allowlist, đóng kết nối trong finally. Không import `core.db`, không migration.
- `usage_events` thật có quantity/unit/model, **không có USD**: chi thực tế UNKNOWN, có số dòng ledger làm bằng chứng độ phủ. Không quy đổi giá hiện tại thành hóa đơn, không cộng thêm llm_calls vào token phiên.
- Dự toán chỉ đọc total của `project_budget:<id>`; không coi `simple_auto_limit` là dự toán. Holds chỉ là phần `llm_holds` còn TTL 30 phút; không đánh đồng job queued hoặc project_reserves với giữ chỗ job.
- Token chỉ xuất tháng/model máy/vai/số đếm. Phiên repo có thể là phát triển hoặc vận hành QC/video: hai nhánh build_tokens/video_operation_tokens ghi UNKNOWN khi không có linkage, không gán tất cả JSONL thành xây công cụ. llm_calls chưa dùng phân loại và không cộng trùng. Dedupe message.id xuyên file bằng max snapshot cumulative; ID thiếu/xung đột, usage/cache/role thiếu → UNKNOWN và coverage; số phiên/ngày cũng UNKNOWN khi coverage không đủ, không báo zero chắc chắn. Không xuất content, payload, path, email hoặc session ID.
- Tiến độ dùng `devsys.plan_progress`, không tự diễn giải code% thành cổng%. Số test tĩnh là số hàm định nghĩa, không phải số cases hoặc số xanh/đỏ.
- Đạt lần đầu dùng lịch sử job_events: mẫu số shot đã có approved/rejected; tử số approved ngay phán quyết đầu với một running, chưa failed. Retry counter reset không thay lịch sử. Có N/D và số thiếu lịch sử; thiếu → UNKNOWN.
- So kỳ trước chỉ JSON cùng schema/scope nguồn và ngày trước, không phân tích văn xuôi. Source scope gồm root/DB/session và định nghĩa kỳ. Ledger/artifact/giao có timestamp được chốt theo ngày; thiếu ngày/múi giờ → UNKNOWN. Dự toán và holds không có history thì không phục hồi ngày quá khứ; kế hoạch/lỗi/quyết định ghi rõ snapshot lúc đo. Không truyền baseline thì tìm đúng sidecar ngày -7.
- Output tạo tempfile trong docs/reports rồi os.replace, không truncate hardlink có thể chia inode với file ngoài phạm vi; chặn ngày traversal và symlink; test symlink thật bị bỏ qua khi Windows không cấp quyền tạo liên kết, không claim đã nghiệm thu trường hợp đó trên máy này.
- Native Git/PDF dùng env whitelist và HOME/profile tách biệt; không kế thừa credentials. PDF chỉ code/mock ở phiên này, renderer thật chưa chạy. Tắt header/footer để không in file URI; CSS A4 ngang/8–9 pt, wrap và thead lặp; timeout chỉ dừng cây PID renderer vừa mở, không dừng browser dùng chung.

## Giới hạn cần phiên chính nghiệm thu

1. Chạy báo cáo thật sau rà: root là worktree, DB thật explicit, session-dir là đúng một folder dự án; không glob home hoặc sibling project. Kiểm DB/WAL hash trước/sau qua guard chỉ đọc hiện có. SQLite WAL mode=ro có thể cần sidecar locking; không dùng immutable=1 vì sẽ bỏ dữ liệu WAL.
2. Chạy và xem PDF local thật; mock PDF trong test chỉ chứng minh args/env/đường dẫn, không chứng minh layout PDF.
3. Chưa có artifact test xanh/đỏ đủ cấu trúc: ghi UNKNOWN thay chạy test hoặc suy từ tên hàm.
4. Từng hàng model/thư mục/mốc có nguồn/ngày đo, delta riêng chưa tính thì ghi UNKNOWN; delta metric tổng chỉ khi baseline tương thích.
5. Dữ liệu token thiếu cache/role có thể làm tổng UNKNOWN dù có phần đếm đọc được. Không đoán zero, không suy số token từ hạn mức tài khoản.

Không gộp main, không restart live, 0 USD.
