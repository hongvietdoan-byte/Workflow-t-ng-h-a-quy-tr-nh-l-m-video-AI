# Rà Đ18 việc 3 — Codex 12/10/2026

## Hiệu quả trước khi xây
Dùng thường xuyên khi đoạn phim quay lại chỗ cũ; ô trực tiếp giảm bước sửa JSON nhưng không tự chứng minh vị trí đúng. Ô tối thiểu dùng chung Bước 1/2, không thêm hệ chọn tài nguyên hay model; thao tác 0 USD. Rủi ro: chọn ảnh chưa duyệt hoặc nguồn tương lai cũ, quyền ghi, cache widget sau bỏ. Cờ `continuity_from_ui` TẮT/OPT_IN_ONLY, chưa thử sản xuất.

## Đối chiếu code và phạm vi
`core/llm_io.update_scene` khoảng 443 kiểm `access.need_edit`, khóa người sửa/lineage/change_review; không dựng đường ghi riêng. `core/runner.layout_frame_job` khoảng 2296 chọn ảnh duyệt trước rồi ảnh chờ; component dùng đúng bộ chọn này. `core/layout_follow.wait_reason` dùng lại khi cờ follow bật. Không sửa runner, policy tương lai, dữ liệu thật, TODO/PLAN hoặc cờ theo máy.
Bước 1 thẻ shot `scene_list` và Bước 2 `image_card` gọi một component. Chọn shot trước, cùng địa điểm lên đầu; nguồn hiện tại đứng sau vẫn hiển thị, không âm thầm bỏ. Nguồn mất vẫn hiển thị cảnh báo và được bỏ. Lưu/Bỏ qua update_scene; read-only ở UI và quyền server từ backend. Ảnh truy vấn theo project, đường ảnh job trong DATA của phiên.

## Đỏ → xanh
- Đỏ: module chưa tồn tại (collection ImportError), 6 test gồm sắp xếp/tương lai/quyền/ảnh/OFF/opt-in.
- Xanh lần đầu: 23 test liên quan 2,65 s.
- Thêm AppTest select-save-remove-future: phát hiện fixture SQLite tạo khác thread; harness dùng DB tạm + kết nối thread riêng, mọi mock khôi phục để không ảnh hưởng test sau. Không nới assert.
- Sửa widget Bỏ xóa key trước rerun; cảnh báo không khẳng định mọi job vẫn gửi khi follow đang giữ chờ.
- Nhóm cuối: `py -m pytest -q -p no:cacheprovider tests/test_continuity_ui_d18.py tests/test_layout_from_p27.py tests/test_layout_follow.py`: **24 passed / 3,88 s**, PYTHONUTF8=1. Tổng 4 lượt do bổ sung AppTest và sửa harness, vượt khuyến nghị 2–3 lượt; không chạy cả bộ.

## Tự rà skill 2b.5 / caller
Không đổi key widget cũ; key mới có scope/ project/shot. OFF trả trước truy vấn/vẽ; không bật qua preset chung. Không API hay auto-gen. Không bỏ dấu so từ ngắn; ưu tiên cùng địa điểm dựa dữ liệu gốc. Không đường tương đối mới trong component (DATA truyền từ phiên như runner); fake harness DATA/DB tạm. Không ảnh project khác qua truy vấn JOIN. areas khai component/test/flag vào bước1+2, giữ version66. Related_areas đọc vùng bước1/2 và caller cờ chung; mã backend không đổi. Independent review và ảnh thật component 1440/1280 còn chờ root, không nhận là hoàn tất.

## Rà độc lập Đ18v3 (Codex)
Đọc diff cuối worker, skill 2b.5, CLAUDE mục 7 và kết quả related_areas. Đối chiếu update_scene need_edit/khóa/lineage/change_review; layout_frame_job chọn job và JOIN project; layout_follow.wait_reason, cả đường Dashboard v1/v2, preset OPT_IN_ONLY. Không gọi API, không đọc dữ liệu thật, không chạy cả bộ.

**P2 còn mở — ô không xuất hiện ở Bước 2 giao diện v2.** `dashboard/steps/step2.py:371` gọi `SB.image_group_v2`; đường này không qua `image_card` (hook mới ở dòng 425). `dashboard/design/screens/storyboard_cards.py:217–263` dựng thẻ v2 riêng và chưa gọi continuity_ui. Vì vậy cờ ON ở giao diện v2 vẫn không có ô chọn/Lưu/Bỏ, dù test component độc lập xanh. Sửa tối thiểu: nối component vào image_group_v2 cạnh phần phiên bản/trạng thái, scope riêng hoặc step2 chung, read_only=not is_latest (component tự ghép quyền dự án). Test regression gọi thẻ v2 với dữ liệu giả/mock phần không liên quan, spy render phải được gọi với đúng pid/idx và read_only cho bản mới/cũ; test OFF không tạo widget. Browser QA phải kiểm đường thẻ v2 thực tế sau sửa.

Chưa thấy lỗi quyền ghi server, phạm vi dự án ảnh, bỏ nguồn mất, giữ nguồn tương lai hiện có, hoặc bật preset tự động trong diff còn lại. Test hiện tại chứng minh callback component, chưa đủ thay cho integration v2. Nguồn mới vẫn chỉ chọn shot trước theo đặc tả; không sửa policy backend tương lai. Không sửa code trong vòng rà.

## Sửa sau rà độc lập
Đã nối component thật vào `dashboard/design/screens/storyboard_cards.py` ngay sau version strip, giữ scope step2 và read_only=not is_latest; mọi quyền dự án vẫn do component + update_scene kiểm. Khai caller này vào code step2 trong areas, giữ version66. Regression AppTest dựng thẻ v2 thật trên DB tạm, hai job cancelled (không bấm nút paid), spy wraps component thật: bản mới, bản cũ chỉ xem, flagOFF không widget. Ba case đỏ do reached=[] trước hook; xanh nhóm 3 file **27 passed / 6,56 s**. Vòng rà có 3 lượt pytest (2 đỏ: lượt thứ hai chỉ lấy traceback ngắn xác nhận đúng lỗi; 1 xanh nhóm). Không nới test cũ. Root cần đọc diff sửa và kiểm ảnh browser v2 trước commit; ảnh component riêng chưa thay thế ảnh thẻ v2.
- Root đọc diff sửa hook v2 + test + areas, chốt không còn finding mở. Browser QA Chrome thật 1440/1280 (cao1700), component và thẻ Storyboard v2 thật với DB/ảnh/DATA/ASSET_DIR tạm, mock chi tiết QC/giá ngoài phạm vi: 0 pageerror, 0 stException, không tràn ngang. Root xem cả hai PNG docs/images/d18/continuity_*.png. Không kiểm sản xuất/model thật.
