# Rà Đợt 6 việc 3 — Codex, 11/10/2026

- Base: `858804f`; nhánh `codex/d6-viec3-thu-tu-shot`; commit mã: `d92e848`.
- CLI `nhip`/`drift` thêm `--db`/`--project`, đọc SQLite bằng URI `mode=ro`, lọc dự án và sắp `scenes.idx`. Không mở dữ liệu sản xuất.
- Ánh xạ nhịp dùng trường có producer thật: `core.shot_intent.from_shot_spec` ghi `scenes.data.byd.truyen.nhip`; shot_specs chỉ bổ sung ánh xạ khai rõ. Thiếu/hỏng/mâu thuẫn nhịp báo VÀNG, ngắt đoạn so chuyển động; drift bỏ shot không có ánh xạ hợp lệ.
- Không có DB: cảnh báo “thứ tự suy từ shot_specs”. Cờ `shot_lessons_db_order` mặc định TẮT: CLI cũ giữ hành vi; truyền tham số DB khi tắt chỉ cảnh báo, chưa đọc DB.
- Không đổi công thức `beat_order`, `stage_solver`, đường gửi job, dashboard hoặc khóa nhân vật. Module đã đăng ký trong areas.json; không tăng version.

## Bằng chứng và rà

- Đỏ trước: 9 failed / 62 passed; sửa xong 71 passed. Thêm kiểm readonly/đường dẫn: 77 passed / 1 failed do spy test trùng tên tham số URI; sửa spy, không nới assertion.
- Rà độc lập xác nhận nhóm cuối: **78 passed in 0.78s**.
- Lệnh (Windows, PYTHONUTF8=1): `py -m pytest -q -p no:cacheprovider tests/test_shot_lessons_db_order.py tests/test_p24_lessons_1110.py tests/test_stage_solver.py`.
- Rà độc lập đọc diff và producer BYĐ: không phát hiện lỗi cần sửa; kiểm readonly, đúng project, thứ tự, mapping thiếu/mâu thuẫn, cờ OFF, drift. Root đọc lại diff theo mục 2b.5: không thấy lỗi chặn commit; `git diff --check` xanh.
- `related_areas` có phụ thuộc cờ dùng chung: cả bộ Windows và test chậm vẫn bắt buộc ở bước tích hợp của Claude. Chưa chạy cả bộ, chưa kiểm dự án thật, chưa gộp main hoặc bật cờ.

## Bàn giao tích hợp cả Đợt 6

- Ba nhánh cùng base `858804f`; khi gộp phải giữ đủ ba cờ mới trong core/features.py và ba dòng kết quả CODEX_TASKS.md. Hai nhánh đầu cũng sửa areas.json: giữ cả hai đăng ký và tăng version một lần ở nhánh tích hợp.
- Báo cáo việc 1 nằm trên nhánh `codex/d6-viec1-post-fx`, việc 2 trên `codex/d6-viec2-ref-beats`.
- Chưa gọi API, chạy Blender, sửa data/dashboard.env hoặc khởi động lại dịch vụ. Giữ cờ OFF đến khi kiểm tích hợp và người dùng duyệt thử thật.
