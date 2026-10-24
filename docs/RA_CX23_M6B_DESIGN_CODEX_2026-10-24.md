# Rà thiết kế M6-B — Codex 1 — 24/10/2026

## Phạm vi và sản phẩm

CX23-M6B-DESIGN, nhánh `codex/v31-m6b-design`, nền `c5ca0cdc`. Sản phẩm `docs/THIET_KE_GOI_M6B_2026-10-24.md`: bốn vai VPA, Storyboard Artist, Sound Designer và Editor/VFX thuộc M6.5/M6.6/M6.8. Chỉ tài liệu Cấp 1; không thêm code, flag hoặc schema, không chạy engine/renderer/provider, không đọc DB/nhật ký thật.

## Đối chiếu và rà

- Đọc đề CX23-M6B-DESIGN, kế hoạch tổ làm phim, đánh giá M6-A và kế hoạch chính; Q-B/E1 đã chốt nên không hỏi lại. Ghi rõ phần M6.8 ở gói này theo đề mới dù kế hoạch kiến trúc cũ gọi M6-C.
- Đối chiếu file:hàm qua source hiện có cho cả bốn vai và các lớp registry/write guard/BYĐ/lineage/replay/gen auth. Root kiểm tĩnh 36 tham chiếu đầu bảng bằng AST: không thiếu file/tên; các tham chiếu CV bổ sung xác minh bằng source. Không import hoặc gọi hàm pipeline để kiểm tài liệu.
- Reviewer độc lập rà quyền, side effect, dependency, OFF golden/ON observer, phí, N/D và ba câu EP: **0 P1/P2 cần chặn commit tài liệu**. Root đọc bản sửa lần hai.
- Làm rõ trường SBA image_prompt/layout/layout_people/end_frames.prompt chỉ dẫn xuất từ blocking/camera pinned, không sửa canonical camera/sân khấu/BYĐ/end-state trái owner. Registry và guard M6.4 vẫn là nguồn quyền, role label không thành ACL.
- Coverage tự khai chỉ là claim; schema bằng chứng hợp lệ không chứng minh chất lượng hình/âm thanh/video. CV read/build/validate chỉ là điểm tái dùng cần audit; không gọi writer run/record trong observer 0 USD.
- Q-B chấp nhận prompt khác quyền gửi API, duyệt take/phim và cấp lượt. Shadow OFF phải byte legacy; ON 0 USD chỉ đọc snapshot và mẫu đã có/fixture, không tự gọi LLM/provider, gen, render, writer production hay tạo store/registry cạnh tranh.
- Nguồn A dùng adapter stage hiện có; không đặt API Astore giả là đã gộp. M6.2/M6.4 và pin/preview ảnh ghi dependency OPEN tại mốc đối chiếu. FFmpeg nặng không chạy trong rerun; queue/owned worker chưa đủ là dependency, không cam kết công suất từ fixture.
- `git diff --check` sạch. Không chạy pytest: thay đổi thuần tài liệu, đỏ→xanh chỉ là test plan cho giai đoạn code sau duyệt; không báo test giả đã xanh. Giữ nguyên areas.version và mọi cờ.

## Trạng thái

Đủ phạm vi tài liệu để báo XONG/chờ phiên chính gộp và trình EP. Chưa duyệt Cấp 2, chưa triển khai M6.5/M6.6/M6.8, chưa chạy shadow thật hoặc pilot/chất lượng production. Ba câu trình EP có phương án đề xuất, không được coi im lặng là duyệt. Không gộp main/restart live/API trả phí/ghi dữ liệu sản xuất.
