# Rà Đợt 7 · việc 2 — Tiểu Nhị và Lão Đại

- Nhánh `codex/d7-viec2-mockup`, base `5593cde`; chỉ mockup, ảnh QA, test mới và đúng dòng tests dashboard_ui trong areas.json, không tăng version.
- Áp dụng vòng làm việc theo plan, mức **RÀ NHẸ**; root đọc diff và ảnh trước commit; bắt 2 nhãn đã sửa: gen xong ghi đủ 7/7 và chờ người duyệt, region không trỏ tab đã xóa. Tự rà mục 2b.5: không nới assert, không data/env, đường dẫn test từ `__file__`, offline không mạng, không tác động pipeline, không tự gọi dịch vụ trả tiền.
- Tiểu Nhị: giữ gói lần trước bất biến; bản nháp riêng có bỏ/thêm Kho 419/nền 3D shot 9/ghim/hoàn tác. Hai lỗi ĐỎ theo ca job 649 và 645–651, sửa ngay → XANH → xem trước → duyệt dữ liệu → duyệt gen riêng.
- Đồng nghiệp không thấy phiếu/code; lỗi chặn có đúng thông báo đã báo admin. Tên #24, dấu phẩy thập phân; ô nhận 0,25 m và cảnh báo chưa đạt. Sau gen sửa ô giữ “đã gen bản trước”, cảnh báo phí lần 2 và hủy duyệt cũ. Đầu vào chưa đổi không cho gen lặp.
- Pet Lão Đại: dáng thường/có phiếu, bong bóng 3 phiếu, danh sách đủ nguyên nhân/bằng chứng/ảnh hưởng/cần gì/người/hạn 3 ngày/trạng thái/file-test-nhánh/đã sửa gì-test nào; sắp quá hạn vàng. Chi hôm nay/job kẹt/dự án gen xong. Nút Mở trên Dashboard chỉ mô phỏng trang đích; không duyệt trên pet.

## Bằng chứng

- Test ĐỎ trước: `py -m pytest -q -p no:cacheprovider tests/test_mockup_tieu_nhi_d7.py` → **2 failed** (thiếu công cụ gói và chưa có pet).
- XANH: nhóm `test_mockup_tieu_nhi_d7.py` + `test_mockup_video_3cot.py` → **6 passed / 0,12 s**.
- Playwright bundled, Chrome Chromium headless chính thức, chỉ file artifact của worktree; không điều khiển browser người dùng. Tiểu Nhị **1280×900 và 390×900**, pet **1280×900**: **0 console/pageerror, 0 request mạng, 0 cuộn ngang** trước/sau thao tác.
- Kiểm thao tác thực: bỏ nền, thêm mẫu, ghim, không thêm trùng, hoàn tác, nhập 0,25 và cảnh báo, xem trước, đồng ý dữ liệu, đồng ý tiền, không gửi trùng bằng nút, sửa sau gen và duyệt lần 2; đóng cảnh báo phải có lý do, đóng không gửi job; đầu-cuối chỉ chuẩn bị; chat rỗng dừng, chuỗi HTML hiển thị bằng textContent; Escape đóng khung; pet đổi dáng và mở đúng TN-024 mẫu.
- Ảnh đã xem trực tiếp: [Tiểu Nhị 1280](images/d7/d7_tieu_nhi_1280.png), [Tiểu Nhị 390](images/d7/d7_tieu_nhi_390.png), [Lão Đại 1280](images/d7/d7_lao_dai_pet_1280.png). Nhãn/nút rõ, không cắt chữ ngoài trang; pet nổi có chủ đích.

## Việc mở

Chỉ thiết kế offline, không phải pet Windows hay Dashboard hoạt động thật. Chưa thử sản xuất/API/Blender/auth/toast; giá là minh họa. Chưa chạy cả bộ Windows, chưa gộp/push; root phụ trách theo quy trình tích hợp. Bản nghiên cứu việc 1 không sửa ở nhánh này. CODEX_TASKS/TODO/PLAN để root cập nhật khi gộp.
