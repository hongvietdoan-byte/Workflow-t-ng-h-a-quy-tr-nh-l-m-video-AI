# Rà và sửa Đ8 việc 2 — 11/10/2026

- Nhánh `codex/d8-viec2-ky-thuat`, gốc `df7c4233fccd8b94dc161b8a4bf5fc2c2b0ce7bb`; chưa commit/push.
- RÀ KỸ bắt 1 P2: OUTFIT tồn tại nhưng file rỗng/>10 MB/không đọc được vẫn bỏ digest, dù lớp gửi loại ảnh.
- Sửa `core/prompts.py:571`: dùng lại `core.adapters.deepix.reference_problem`; chỉ bỏ digest khi ít nhất một ảnh của chính actor qua kiểm hiện hữu.
- `lock_text` không đổi; guard người khác giữ; cờ OFF không đọc OUTFIT và prompt giống cũ từng byte.
- `tests/test_d8_technical.py`: thêm ba ca empty/oversize/unreadable; test OUTFIT hợp lệ dùng PNG tạm thật. Không nới assertion.
- Đỏ: **3 failed, 65 passed, 1 xfailed**; xanh: **68 passed, 1 xfailed**.
- Cùng lệnh: `py -m pytest -q -p no:cacheprovider tests/test_d8_technical.py tests/test_change_review.py tests/test_p24_lessons_1110.py tests/test_profile_digest.py tests/test_end_frames.py` (`PYTHONUTF8=1`).
- Producer v3 ghi finding VÀNG riêng; không thêm pending event/API hay đổi giữ job ĐỎ. OFF trước đọc baseline/CSDL qua hook.
- end_frames vẫn không sửa; xfail strict kiểm ref detail trong gói thực gửi WS; báo cáo riêng không xác nhận dữ liệu/chất lượng thật.
- Mở: baseline bất biến gắn job ảnh duyệt và đường ghi Dashboard/v2/v4; ghi rõ trong HANDOFF/báo cáo end_frames.
- Mở: `reference_problem` hiện kiểm kích thước/đường dẫn, chưa decode ảnh hỏng nhỏ; không mở rộng scope kiểm decode.
- Chưa thử thật, chưa cả bộ Windows; không đọc/ghi dữ liệu thật/env, không API/Blender/file #24. Root đọc phần sửa trước bước tích hợp.
