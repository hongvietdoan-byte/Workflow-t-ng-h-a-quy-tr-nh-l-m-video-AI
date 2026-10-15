# HANDOFF — feat/khoa-co-verified (tạm, xóa ở commit cuối)
- Việc: cờ `verified: True` = KHÓA BẬT (core/features.py) + màn 🧪 + test; phần B: docs/handoff/DE_XUAT_KHOA_CO_2026-10-15.md
- Trạng thái: đang làm phần A (test đỏ → code).
- Lối thoát cho bộ test cũ: FEATURE_LOCK_TEST_BYPASS=1 (tests/__init__.py) chỉ có hiệu lực khi pytest đang chạy.
