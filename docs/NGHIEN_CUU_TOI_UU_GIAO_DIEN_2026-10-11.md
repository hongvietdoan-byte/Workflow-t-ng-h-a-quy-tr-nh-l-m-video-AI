# Tối ưu màn Video và Kho — ĐỢT 2 việc 4

Ngày khảo sát 10/10/2026; tên file 11/10 theo đề bài. Chỉ mockup HTML, dữ liệu/giá giả, SVG nội bộ; chưa sửa Dashboard.
Nguồn yêu cầu: `origin/ghi-chu-giao-dien-fatebreaker:docs/GHI_CHU_GIAO_DIEN_SO_FATEBREAKER_2026-10-10.md`.

## 1. Đo mốc hiện tại, phân biệt phép đo và ước lượng

Đã chạy `PYTHONUTF8=1 py tools/ui_v2_acceptance.py clicks` trên Windows, code base `7764122`:

| Phép đo | Kết quả | Phạm vi |
|---|---:|---|
| Dự án mới → yêu cầu video đầu, v2 | **12 lần bấm + 2 lần nhập** | AppTest, mọi provider mock, DB tạm; job video ở trạng thái running, chưa phải clip thật đã tải |
| FEATURE_UI_V2=0 hiện tại | 12 lần bấm | Không còn là giao diện cũ; mốc lịch sử trước G-a = 14 |
| Đường ap_start | 3 lần bấm | Chỉ tới nút bắt đầu tự động; AppTest báo idle, không đo hoàn tất video nền |
| Mockup này | 1 lần bấm từ shot đã mở → yêu cầu gen: Gen clip | Có thể xem gói mà không bấm; không dựng dự án mới. Chưa có số end-to-end riêng cho mockup |

Đường 12 bấm: tạo dự án → phân tích → Director → khóa Bible → gen ảnh → duyệt ảnh → xác nhận → viết motion → duyệt motion → xác nhận → Video → gen video. Không bỏ cổng duyệt để giảm số bấm.

**Đối chiếu code mới nhất, không lấy ảnh cũ làm số đo hiện hành:**

- `dashboard/steps/step4.py:115–120` đã chia `ordered` thành **3 thẻ mỗi hàng**; ghi chú so FateBreaker nói một cột là mô tả bản trước.
- `video_card_v2` từ dòng 488: tên/trạng thái, QC, readiness, model, quality, clip, giá, note, ô sửa, hai hàng nút. Nội dung thay đổi theo trạng thái/cờ/ghi chú.
- `_clip_view` và `_takes_strip` trong cùng file đã có fragment/chip phiên bản; nên bổ sung trạng thái và “đang dùng”, không dựng một hệ phiên bản thứ hai.
- `dashboard/design/screens/video.css`: video/ảnh cao tối đa 340 px; chiều cao toàn thẻ không cố định. `theme.css` có quy tắc chuyển 2 cột ở màn hẹp.

Màn **1440×900**, zoom 100%, sidebar đóng là mốc đề xuất. Không chạy trình duyệt Dashboard theo đề bài, vì vậy **chưa có số cuộn pixel thật của Dashboard**. Không gọi các ước lượng dưới đây là kết quả đo browser:

| Đại lượng | Dashboard code hiện hành | Mockup `video_3cot.html` |
|---|---|---|
| Shot hiện đủ khung/nút | 3 thẻ/hàng theo code; thường 1 hàng nếu mỗi thẻ cao 500–700 px | 1 shot chi tiết, 9 chỉ mục shot |
| 9 shot | 3 hàng, duyệt 9 nút; khi mỗi màn chứa 1 hàng cần 2 lần dịch xuống theo hàng | 9 nút duyệt + 8 lần chọn shot nếu bắt đầu shot 1; 0 cuộn trang **theo ngân sách CSS**, không khẳng định giảm tổng click |
| Mật độ khung lớn | 3/hàng; số hàng lọt màn phụ thuộc header/thẻ | 1/không gian làm việc; 9 thumbnail chỉ dùng điều hướng, không tính là 9 khung lớn |
| Ngân sách chiều cao | Không suy ra chính xác từ max-height video | 64 header + 64 stepper + 32 padding main + 570 workspace + 16 gap + 114 filmstrip + khoảng 34 footer = **894 px** |
| Ngân sách dải phim ngang | Không áp dụng | 9×140 + 8×10 + 24 padding + 2 border = **1366 px**, trong vùng 1392 px |

Panel dùng overflow:auto: nếu chữ wrap hoặc mở prompt/chi tiết, có thể cuộn **trong panel**; 0 cuộn trang chỉ là mục tiêu CSS. Trước triển khai phải đo boundingClientRect/scrollHeight và ghi video thao tác trên 1440×900 và 1024×768, 9 shot ở cả pending_review/failed/approved. Mockup giả không phát media; nút chỉ cập nhật thông báo mô phỏng.

## 2. Mẫu tương tác từ nguồn công khai

Chọn nguồn chính thức; không sao chép nội dung hoặc giao diện:

| Nguồn | Mẫu đáng áp dụng | Cách áp dụng cho pipeline |
|---|---|---|
| [Frame.io V4 Comparison Viewer](https://help.frame.io/en/articles/9952618-comparison-viewer) | Chọn hai tài nguyên/phiên bản, so cạnh nhau, điều khiển liên kết | Bản đang xem khác bản đang dùng; so V1/V2, feedback gắn đúng job, không tự duyệt bản khác |
| [Premiere Project panel views](https://helpx.adobe.com/premiere/desktop/get-started/customize-the-project-panel/customization-options-for-the-project-panel.html) | List/Icon cho hai nhu cầu; hover scrub ở Icon | Dải shot ngắn để nhảy nhanh; preview rê chuột là tùy chọn, không tự phát toàn bộ 9 clip |
| [Premiere thumbnail controls](https://helpx.adobe.com/premiere/desktop/get-started/use-touch-and-gesture-controls/use-thumbnail-controls-in-the-project-panel.html) | Điều khiển phát/scrub ngay thumbnail | Thêm preview 0 USD, giữ nút phát rõ cho bàn phím và cảm ứng; không gọi gen từ hover |
| [Runway organize assets](https://help.runwayml.com/hc/en-us/articles/23998498329107-How-to-organize-assets) | Nhóm tài nguyên, chọn nhiều để thao tác | Lọc Kho theo loại/vai; duyệt nhóm chỉ sau checklist và xác nhận, không suy rằng công cụ nguồn có cổng duyệt giống pipeline |

Suy luận thiết kế: so phiên bản và truy nguồn ưu tiên hơn tăng mật độ chữ. Không chép prompt thô ở trung tâm, bỏ stepper, hoặc giấu giá. Phím mũi tên đổi shot/Space phát/Enter duyệt là **đề xuất**, phải chặn khi focus đang nhập chữ; chưa nối vào mockup hoặc Dashboard. Batch duyệt vẫn cần xác nhận và phải bỏ qua shot có lỗi chặn.

## 3. Streamlit: khả thi và giới hạn

Môi trường khảo sát `streamlit 1.64.0`; tài liệu web mặc định đang hiển thị 1.65.0. Không mặc định mọi tham số mới có trong bản cài.

- [st.columns](https://docs.streamlit.io/develop/api-reference/layout/st.columns): bố cục ba vùng bằng tỷ lệ `[.6,1,1]` khả thi; tránh lồng nhiều tầng và kiểm responsive. Không sao chép trực tiếp độ rộng pixel của HTML sang thẻ Streamlit. Giữ key hiện hữu; đổi key phải khai `RENAMED`.
- [Fragments](https://docs.streamlit.io/develop/concepts/architecture/fragments): chỉ rerun khung clip/phiên bản để giảm tải. State động đặt trong session_state; fragment không tự nhận thay đổi đối số và widget không đặt vào container tạo ngoài fragment. Đổi shot cần chủ động cập nhật selection và cache đúng scene/job.
- [Custom components](https://docs.streamlit.io/develop/concepts/custom-components): dải phim cần keyboard/hover/scrub và trả selection thì component hai chiều là phương án phù hợp. `components.html` hiển thị HTML đơn thuần không thay thế hợp đồng widget Python; không dựa vào JS tìm DOM cha để gọi API. Chỉ làm component khi lợi ích đã đo, kiểm API bản 1.64 trước khi chọn v2.

Lộ trình ít rủi ro: giữ grid hiện tại → thêm nhãn phiên bản/gói gửi → mở workspace một shot bằng lựa chọn scene → dải phim native nút ảnh → cuối cùng mới cân nhắc component. Giá lấy từ cost hiện hữu, gói gửi lấy đúng `jobs.sent_package` K1a; chưa có gói thì hiện “chưa có gói gửi”, không dựng vai ảnh từ nhãn UI.

## 4. Xếp hạng triển khai sau khi duyệt mockup

| Ưu tiên | Đề xuất · giá trị/công sức | File dự kiến | Rủi ro và kiểm |
|---|---|---|---|
| 1 | Gói gửi ảnh + vai, giá trị rất cao / vừa | `dashboard/steps/step4.py`, `dashboard/design/screens/video_ui.py` | K1a phải có trước; gắn đúng job thay vì đầu vào mới; test package thiếu/cũ, không gửi nhầm ảnh |
| 2 | Phiên bản có trạng thái + đang dùng, cao / nhỏ | `dashboard/steps/step4.py` `_clip_view`, `_takes_strip` | Đang xem ≠ approved/selected; key va_/vkeep_ giữ; test rerun fragment và đổi scene |
| 3 | Kho Nguồn ↔ hồ sơ, cao / vừa | `dashboard/admin.py:asset_library_panel`, `dashboard/header.py` hộp thoại Kho | R1 không sửa tự động/không trả tiền tự động; dấu tiếng Việt/mã Kho; sửa dữ liệu cần backup và quyền |
| 4 | Checklist 4 dòng + chi tiết, cao / nhỏ | `dashboard/readiness_ui.py`, `dashboard/design/screens/video_ui.py` | Không làm mất lỗi chặn/readiness; test trạng thái đỏ/vàng/chưa có số |
| 5 | Workspace một shot + dải phim, cao / lớn | `dashboard/steps/step4.py`, `dashboard/design/screens/video.css`, `dashboard/design/theme.css` | Hồi quy widget key, responsive, focus, 9 shot; đo lại click/scroll/density; không mất gen hàng loạt |
| 6 | So hai bản + shortcut/hover, vừa / lớn | module component mới sau duyệt + `dashboard/steps/step4.py` | Tải media nhiều, playback đồng bộ, CSP/focus/accessibility; component chưa có quyết định thiết kế |

Mục tiêu: giảm cuộn khi sửa một shot và giảm lỗi đối chiếu, **không tuyên bố** workspace nhanh hơn grid cho duyệt 9 shot liên tiếp. Thực nghiệm A/B cần so cả thao tác chỉ duyệt và thao tác sửa đầu vào; giữ yêu cầu ước tính tiền và test key cũ. Chưa triển khai Dashboard, chưa đo latency/performance bằng browser, chưa dùng dữ liệu thật.
