# CX23-M82 pha A — checkpoint WIP của Codex 1

**Chưa XONG, chưa đủ nghiệm thu, không bật cờ.** Nhánh `codex/v31-m82`.

## Phần đã triển khai

- `simple_mode` mặc định TẮT. `dashboard.basic.render()` OFF trả False trước import/render màn; chưa sửa entrypoint `dashboard/app.py`/`header.py`.
- Helper `core/simple_budget.py`: metadata `simple_auto_limit:<pid>` tách trần cảnh báo `project_budget:<pid>`; kiểm EP theo public policy hiện hành `stage_desk.is_executive_producer`, recheck user active/role và dự án; không coi quyền edit là EP. Xác nhận giá hiện tại, no-op khi duyệt lặp cùng số, không nâng ngầm; SAVEPOINT giữ giao dịch caller, audit chỉ ghi mã dự án/số tiền.
- Khung Streamlit năm màn Ý tưởng+ngân sách / Kịch bản / Ảnh / Video / Tải bản giao, HOLD/lỗi/tạm dừng. Tiền tổng một vị trí mở chi tiết; 80% tính cả giữ chỗ; không ghi dữ liệu lúc dựng snapshot (nếu chưa có bảng giữ chỗ thì hiển thị 0, không gọi API tạo bảng).
- Model đọc dữ liệu và bộ đếm E4 dùng `gen_auth.project_jobs/attempts_in/cycle_start`; không dùng retry_count hay reset khi đổi mode/model/prompt.
- Callback OFF/thiếu xác nhận/người thiếu quyền đều dừng trước provider/queue; tái dùng `batch`, runner, `paid_confirm`, `approve_preview` hiện hành; không thêm worker/vòng autopilot. Fingerprint+tập cảnh+giá gắn với bước xác nhận, thay input làm hủy hộp hỏi cũ; callback kiểm lại trước gửi. Không dùng confirmed=True để vượt cổng ảnh.
- Media/download chỉ nhận file nằm dưới thư mục dự án sau resolve, không mở đường dẫn tùy ý từ DB.
- File mã/test/fixture và cờ đăng ký areas, **giữ version nền 92**.

## Đỏ → xanh và giới hạn bằng chứng

- Test đầu: **2 failed + 7 errors / 0,43 giây** (module/helper/cờ chưa tồn tại).
- Helper/cờ: **9 passed / 0,24 giây**.
- Khung năm màn: **12 passed / 4,60 giây**, gồm AppTest thực thi cả năm màn với snapshot giả, provider chưa được gọi.
- Guard bổ sung: **14 passed / 4,34 giây**, gồm OFF/no confirmation/giá-fingerprint đổi dừng trước provider, gửi xác nhận bằng runner giả giữ actor người và không override cổng ảnh.
- Python 3.14 Windows, pytest `--tb=no -p no:cacheprovider`. Thay OBJECT `os.environ` bằng dict giả qua `patch.object` trước import pytest/target; fixtures DB in-memory/snapshot giả, provider/price giả. Không đọc/in khóa, không dump env, không API trả phí.
- Chưa chạy cả bộ, chưa có bằng chứng production, chưa đo tám hành động hay chất lượng/người dùng. Không chạy lại test sau lượt 14 xanh vì checkpoint tiếp chỉ cập nhật tài liệu/đăng ký fixture.

## Các phần chưa đủ để nghiệm thu

1. API core batch/runner chưa có targetedsend theo đúng tập cảnh/job đã duyệt. Hiện gặp cảnh hết lượt thì giữ chờ toàn lô; **chưa đạt yêu cầu HOLD từng mục không chặn mục khác**. Chờ root/phiên chính phối hợp owner core; không tự đổi file ngoài phân công dashboard.
2. Proposal đang dùng `project_budget.propose` cũ, **chưa đủ dự toán xấu nhất + ngân sách tự sửa 40%** theo thiết kế qd3. Chưa được gọi là báo giá toàn phim đã hoàn chỉnh.
3. Q-A/Phương án khác/chọn hướng có lý do chưa nối đầy đủ; các lối sửa thẻ, retry/reject/reopen/voice/music và phụ đề thuộc pha B chưa nối; bản ghép xem thử sau duyệt clip còn mở. Không tuyên bố mục tiêu ≤8 hành động đã đạt.
4. Khung dùng policy EP hiện hành; sau G1 của Codex 3 lên main phải đối chiếu adapter quyền. Chưa RÀ KỸ độc lập M82.
5. UI QA 1440/390 chưa hoàn tất, **chưa có PNG**. Đã đọc computer-use SKILL/guidance/confirmations, khởi tạo Sky và list_apps được; IAB/browser inventory rỗng. Thử Chrome native đúng window được trả về bị công cụ dừng: “could not determine the current browser URL on Windows with enough confidence to enforce policy”. Dừng UI, không retry/bypass.

Fixture `tests/basic_mode_preview.py` dùng snapshot giả, mọi đường gửi/ghi bị mock; không phải ứng dụng production. Preview đã mở bằng explicit whitelist env, PID45972 cổng8529. Sau khi kiểm commandline chứa đúng `streamlit run tests/basic_mode_preview.py --server.port 8529` và không có listener khác, đã dừng đúng tiến trình sở hữu. Không còn server/test đang chạy.

## Bàn giao

Theo thư mới 12:31, Codex 1 ưu tiên G1-PLAN-GATES → M47B UI → M82. Root giao G1 cho agent khác; nhánh này dừng WIP có HANDOFF, giữ cờ OFF. Chỉ root push nhánh, không gộp main/live pull/restart, không dữ liệu thật, không sửa G1/core caller ngoài phạm vi.
