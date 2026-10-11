# Ca vàng Đ10.5 (cờ change_review_frames) — Rà tác động theo khung đầu, quá trình, khung cuối

Đ10.5, ca #24 ngày 11/10/2026 dựng lại từ mô tả hộp thư; không đọc dữ liệu sản xuất.
Cờ `change_review_frames` mặc định TẮT. Kiểm ngoại tuyến chỉ chứng minh đề đúng cấu trúc, chưa chứng minh Claude hết báo nhầm.

| Ca vàng | Đầu vào / ngữ cảnh | Quan sát mong đợi |
|---|---|---|
| Mục 84/111 — đứng rồi ngã | START blocking/image_prompt đứng; TRANSITION chao rồi ngã; END nằm | Không báo lệch vì đầu đứng khác cuối nằm; chỉ so các trường cùng khung |
| Mục 109 — 4 s, bốn nhịp | Một câu motion chứa 0–1 đứng, 1–2 chao, 2–3 ngã, 3–4 nằm; duration_s=4 | Đếm bốn nhịp, không kết luận một pha theo số câu |
| Mục 90/92/93, 102/105 — biến đổi có chủ ý | BYĐ thành phần dạng 1, bat_dau đứng, dinh biến hình, ket_thuc dạng 2, ngoại lệ chủ ý biến hình | Giữ đầy đủ BYĐ để không ép dạng/tư thế cuối có ngay trong ảnh đầu |

Nguồn: `docs/CODEX_TASKS.md` Đ10 việc 5. Ca thứ ba là tình huống tái dựng để kiểm ngữ cảnh theo mô tả báo nhầm khung,
không khẳng định đã lấy nguyên nội dung các mục sản xuất.
Test: `tests/test_change_review_frames.py` (ba ca vàng + snapshot UTF-8 OFF lấy trước khi sửa + cờ mặc định).
Ảnh đã duyệt thuộc START; đề này chỉ chứa chữ, không gửi ảnh. Không có bằng chứng ảnh → `khong_chac`.
