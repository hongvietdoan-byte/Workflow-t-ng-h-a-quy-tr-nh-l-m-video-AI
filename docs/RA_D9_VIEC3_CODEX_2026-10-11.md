# Rà kỹ Đ9 việc 3 — chỉ phần backend

Phạm vi: thay đổi chưa commit `tools/lao_dai/`, `tests/test_lao_dai.py`, cờ `lao_dai_pet`, đăng ký areas. Nền `5cd515b`, phụ thuộc kho phiếu `df62cc7`; không rà lại phụ thuộc. Đối chiếu `CODEX_TASKS.md` Đ9 việc 3, thiết kế Đ7 mục 4 và quy trình mục 2b.5.

## Lỗi đã gom sửa một vòng

1. Trung bình — `SnapshotBroker.__init__`: `Path.resolve()` nhận đường dẫn tương đối nên chọn CSDL theo CWD của launcher/worktree. Sửa: chỉ chấp nhận cấu hình đường dẫn tuyệt đối, báo lỗi rõ trước mở SQLite. Test đổi CWD + đường dẫn tương đối đỏ trước, xanh sau.
2. Thấp — `allowed_url`: `parse_qs` bỏ tham số giá trị rỗng, làm `token=`, `ticket` lặp với một giá trị rỗng hoặc `step=` lọt kiểm allowlist. Sửa: giữ giá trị rỗng khi parse; kiểm hiện hữu từ chối khóa lạ, lặp và rỗng. Ba ca hồi quy đỏ trước, xanh sau.

Bằng chứng Windows/CSDL tạm: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_lao_dai.py tests/test_tickets.py`: ĐỎ 4 hỏng / 39 qua; sau sửa XANH 43 qua / 1,28 s. Không nới assert, không API tốn tiền, không dữ liệu thật.

## Quyền và giới hạn kết luận

Không thấy lỗi chặn còn lại trong phạm vi backend: cấp token kiểm `auth.identity` Owner từ session server; mỗi snapshot kiểm lại session/role/active/expiry, token có TTL tối đa 300 s và băm trong RAM; từ chối khi cờ TẮT. Broker chỉ bind 127.0.0.1, GET `/snapshot`, Bearer header, không endpoint cấp token mạng, không ghi log token/query; nonGET bị từ chối. Connection `mode=ro` + `query_only` + transaction, không schema init; test byte CSDL không đổi và DB thiếu không tự tạo. Logic từ chối snapshot thiếu/sai định dạng cơ bản, toast chỉ mã/trạng thái/mốc hạn; URL chỉ HTTP loopback 8501/8502, khóa query theo cổng, không credential/fragment/đường khác.

**Chưa hoàn tất Đ9 việc 3**: chưa GUI/khay/toast Windows thật, kho token OS, kênh cấp session/token tích hợp server, launcher hay QA DPI/hai màn hình/sleep-resume. `issue(session)` chỉ là API Python nội bộ; chưa có kênh tích hợp an toàn thì không có pilot chạy được. Chưa chạy cả bộ; root cần đọc phần sửa và thực hiện quy trình gộp. Không commit/push ở phiên rà.
