# Tự rà Đ18 việc 4 — đề bài registry A

Ngày 14/10/2026, nhánh `codex/d18-viec4-de-bai`, base `46ac70ba`; **RÀ NHẸ, chỉ tài liệu** theo vòng làm việc mục 2b.5. Chưa build/pytest/thử thật/gộp/main.

## Phạm vi đã kiểm

- Đọc CLAUDE/CHUAN/vòng làm việc 2b.5; thư TODO14/10 18:09 và quyết định18:01, nguồn sân khấu Đ18, thiết kế Đ11 mục9 đủ20dòng (18 bản gọn; #12/#20 để sau), phương pháp mục2/9/14, CODEX_TASKS Đ11+Đ18, tổng hợp14/10.
- Đối chiếu số dòng và nội dung các module grid/solver/facts/blockout*/plate_camera/camera_plan/tools stage_grid; ghi base để không coi số dòng là vĩnh viễn. Chưa đọc data thật. Queue portable là dependency ngoài base do root cung cấp, chưa claim main/production.
- Registry A chưa tồn tại: không biến Đ18v1–3 đã main thành nguồn A có sẵn. A chọn13/10 thay câu lịch sử chờA/B/C; đề thay storage editor riêng mục5 bằng canonical A, không hai head song song.
- Mọi lựa chọn storage SQLite/schema/API/outbox/cờ đều đề xuất chờ duyệt; không biến quyền viết đề thành quyền build. B/animatic/bộ góc/editor cùng A; không mở editor2D, preset/import-export/fullanimation.

## Checklist 2b.5 và kết quả

| Loại lỗi | Kết quả tự kiểm |
|---|---|
| Nới test che lỗi | Không đổi test; docs-only không dựng test đỏ giả. Đề build yêu cầu đỏ→xanh và không nới |
| Path tương đối/cwd/data worktree | Canonical connection/data_dir do caller cấp, artifact resolve project root; migration chỉ nguồn chọn, fake fixtures; không đọc data/dashboard.env |
| Vỡ autopilot/bulk | Caller matrix tay/autopilot/v2/v3/multi-shot/clone/replan; opt-in sau thử thật; OFF identical prompt/refs/grouping/hash/jobs/calls |
| Bật mặc định | Cờ đề xuất OFF/OPT_IN_ONLY; giữ anchor_by_spot TẮT, own_camera không neo |
| Bỏ dấu/tên ngắn khớp nhầm | ID ổn định theo scope; không dùng tên display hoặc fuzzy tên/spot để gộp |
| Sandbox/mạng/secrets | Không chạy API/test. Đề fake env patch.object thay OBJECT, mock credentials/provider, subprocess whitelist, pytest --tb=no, không dump secrets |
| Tiêu đề/nhãn bị coi nội dung | Envelope/lược đồ/provenance tách raw text; blocking văn bản không parse thành số đo, fixture không claim production |
| Paid call chưa đồng ý | Không call; đề bắt dự toán/sổ chi/trần và đồng ý riêng trước thử ảnh/clip. Duyệt proposal không đồng ý gen |

## Điểm tự rà đã chỉnh trước bàn giao

1. Ghi rõ override A13/10 và thay storage editor riêng, loại hai nguồn chuẩn.
2. Bổ sung parent state DAG/self/crossscope, timeline cắt xen/quay lại, clone/reorder remap và approval/cache.
3. Bổ sung factor/relative model→mét để không nhân scale hai lần; status geometry measured/assumed/unknown.
4. Phân biệt portable queue dependency chưa main, 5 active/1 heavy worker và 25 admission fixture (1 running+24 pending), không production max.
5. Root đọc toàn đề + diff và bổ sung CAS nhiều aggregate/read transaction nhất quán, bootstrap không chạy khi OFF, continuation giữa các đoạn cùng revision nguồn và test chu trình. RÀ NHẸ tài liệu đã xong; không dựng agent rà kỹ giả cho tài liệu.

Nghiệm thu tài liệu: `git diff --check` và diff/stat do root đọc trước commit; không bằng chứng code đã sửa/chất lượng production. Các nhánh build tương lai đụng quyền/dữ liệu/job/tiền phải RÀ KỸ và cả bộ Windows xanh trước gộp. Việc mở: người dùng duyệt đề và lựa chọn kỹ thuật; registry/Editor/Camera/animatic chưa triển khai theo đề này.
