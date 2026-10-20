# Đ20 việc 1 — đề xuất sổ lỗi WS0

- Nhánh `codex/d20-viec1-so-loi`, nền `51acfea1`; commit xem `git log -1` (báo cáo cùng commit).
- Thêm `tools/project_error_report.py`: `--db <bản-sao.sqlite> --project 33 [--json]`; Markdown mặc định. SQLite URI `mode=ro`, `query_only`, một snapshot đọc. Không ghi CSDL/sổ, không gọi provider, không đọc env/bảng giá/dữ liệu thật.
- Gom mã diag (kể cả counter đã gộp), lỗi job qua note lần failed cuối (kể cả job đã retry), chuyển sai theo `core.states.TRANSITIONS`, succeeded lặp; liên kết job/shot/scenes, first/last/count. Job lỗi đang lấy lần failed cuối mỗi job; không phải thống kê toàn bộ mọi lần retry.
- JSON là **đề xuất** đủ trường WS0, `OPEN`, id PROPOSAL riêng; chưa có căn cứ nguyên nhân/stage thì null. Mã G/A/B chỉ nằm trong `suggested_error_codes` có file/dòng nguồn dự án, không tự nhận alias lịch sử. Không gán VERIFIED bằng test offline.
- Bằng chứng chỉ chứa tên bảng/id; không xuất message/note/payload. Markdown cảnh báo số tiền các nhóm cùng job có thể chồng nhau.
- Tiền: cộng `cost_usd` hoặc ledger `unit=USD`; schema hiện tại quantity/second/item/token không có giá USD → null/UNKNOWN + cảnh báo. Không coi 0 USD khi thiếu giá; chưa tích hợp tái định giá theo pricing. Thiếu bảng bắt buộc/cột thiết yếu báo rõ, usage_events tùy chọn báo rõ.
- ĐỎ: `tests/test_project_error_report.py` 4 ERROR `ModuleNotFoundError` trước khi có công cụ.
- XANH: lượt 2 = 6 passed; lượt 3 = **7 passed / 0,74 giây**. Lệnh `PYTHONUTF8=1 py -3.14 -m pytest -q tests/test_project_error_report.py --tb=no -p no:cacheprovider`. Test chỉ dựng SQLite tạm, patch.object thay os.environ giả trong import/call; không spawn provider/credential/model. Không assert/in env hay bí mật.
- Ca thử: diag trùng mã/count; lỗi trả tiền; succeeded hai lần; schema thật jobs.scene_id, diag.at/last_at, lỗi trong job_events.note; tiền thiếu giá UNKNOWN; bảng thiếu; file không tồn tại không bị tạo; provenance A1; JSON CLI; transition queued→approved và đơn vị USD. Hash byte CSDL trước/sau bằng nhau.
- `related_areas.py`: vùng diag; không có caller sản xuất tới module mới. Do area diag chứa `tests/test_access.py`, công cụ yêu cầu test chậm ở bước tích hợp. Khai code/test trong areas, **giữ version 87**.
- Tự rà 2b.5: không nới test; đường dẫn db resolve tuyệt đối; nguồn docs theo __file__; không thay luồng tay/autopilot/batch; không cờ bật mặc định; khớp mã nguồn nguyên dạng, không bỏ dấu; không network/API/chi tiền. Caller mới chỉ test; import duy nhất ngoài stdlib là core.states (enum/map thuần).
- Chưa chạy CSDL thật/chưa cả bộ; chờ agent rà độc lập quy ước 7 + cả bộ Windows trước gộp. Chưa push.
