# C-RA-FIX21 — rà độc lập CHỈ ĐỌC nhánh `codex/v31-fix-21` @ `4dedfe4f` (CX21-FIX) (cloud-D, 21/10)

**Kết luận: GỘP ĐƯỢC** — 6/6 mục đề CX21-FIX sửa đúng gốc, có test ĐỎ → XANH; 1 lỗi THẤP (không chặn gộp, sửa sau được).
Không sửa code. Diff `origin/main...codex/v31-fix-21`: 12 tệp (+430/−45).

## Bằng chứng chạy (Linux, Python 3.13, worktree của nhánh)
- `tests/test_cx21_fix.py` chạy trên code main cũ: **11 đỏ / 1 xanh** → trên nhánh: xanh.
- Vùng: test_cx21_fix, test_subject_capacity_d20, test_subject_auto_cleanup, test_subject_library_cleanup, test_subjects, test_decisions,
  test_video_pregen, test_inbox_clean, test_seedance_refs, test_sent_package — **236 qua, 1 đỏ CÓ SẴN trên main**
  (`test_sent_package::test_unreadable_picture_sha_null_said_and_still_sent`, chạy root). `python -m core.decisions check`: Khớp.
- Golden replay 3.14: không chạy được ở cloud (đúng CX21-GOLDEN (e)); chỉ đọc mã.

## Từng mục
1. **VỪA `core/subjects.py` capacity — ĐÚNG.** Dòng `processing` asset NULL: tìm theo `name` trong snapshot (duy nhất mới nhận); không thấy →
   UNKNOWN chỉ khi `sha` thuộc gói đang gửi, dòng khác giữ 1 chỗ (`reserved`) thay vì khóa cả Kho. `needed` tính cả processing đã thấy trong
   snapshot. Test (a) (b) (c): `test_processing_null_reconcile`, `test_processing_named_asset_already_occupies_one_slot`,
   `test_two_submit_passes_reconcile_null_without_duplicate`. Đổi kỳ vọng `test_subject_capacity_d20::test_processing_snapshot_evidence_only_blocks_unresolved`
   (None/missing → READY): đúng đề (b) — dòng đó là `other-sha`, không thuộc gói; KHÔNG phải nới test.
   **Cờ TẮT giữ byte cũ:** `capacity()` chỉ được gọi trong `_hosted_pictures` dưới `subject_capacity_guard` (grep: 1 chỗ gọi duy nhất); nhánh
   `_pregen_local and not guard` y hệt cũ khi cờ TẮT.
2. **THẤP SPEND_LOCK — ĐÚNG.** Cờ BẬT: `capacity()` (GET ≤ 20 trang) chạy trong `_prepare_kwargs` (ngoài khóa), mục hoãn mang
   `capacity_checked=True`; `_finish_kwargs` (trong SPEND_LOCK) bỏ kiểm lại. `_pregen_local` trả False trong `finally` → bước hoàn thiện vẫn tải
   lên thật. `mark_fallback`/`scene_ids` của `_reference_pictures` vẫn gắn đúng mục hoãn cuối. Kho đầy giữa hai bước (TOCTOU) vẫn được
   `picture_refs → library_full → CapacityWait` bắt. Test `test_capacity_get_before_finish_lock` (khẳng định khóa rảnh lúc gọi mạng).
3. **THẤP inbox — ĐÚNG** (sửa ở `subjects.rejected_frame_assets`, nơi inbox gọi): kiểm `sqlite_master`, không `CREATE TABLE` trên đường đọc.
   Test `test_inbox_cold_database_readonly`.
4. **THẤP decisions — ĐÚNG.** Mục `v31-d03c-c3-3-subject-cleanup-dry-run-2026-10-20` `replaces` D03b (D03b → `replaced`), `keeps` chép lại phần
   guard sức chứa còn hiệu lực; check `check_subject_cleanup_dry_run` trong tests/test_decisions.py; `core.decisions check` Khớp.
5. **THẤP golden — ĐÚNG.** `tests/golden/README.md` ghi manifest khóa sha CẢ CSDL + bản sao đóng băng + worker native 3.14 (`sys.prefix ==
   sys.base_prefix`, venv fail-closed) + SYSTEMROOT; test sha CSDL nguồn + mtime_ns cây `data/` không đổi; test venv fail-closed.
6. **VỪA `tools/merge_union.py` — ĐÚNG mục tiêu (không mất mục).** Hợp 3 phía từ `git show :1: :2: :3:`, dict theo khóa, list `{"id"}` theo id,
   scalar khác nhau → ValueError (không ghi), ghi lại định dạng areas.json (dict thụt 2, list vô hướng một dòng). **Thử bằng repo git tạm**
   (bên A `json.dumps(indent=2)` nhiều dòng + thêm mục, bên B giữ định dạng một dòng + thêm mục, merge xung đột): đủ cả `a_new.py`,
   `b_new.py`, `iA`, `iB` — không rơi mục.

## Lỗi
- **THẤP** `tools/merge_union.py` `merge_json`, nhánh list KHÔNG có `id` (dòng `result = list(ours); for item in theirs: …`): hợp kiểu union nên
  **mục một bên XÓA bị sống lại** khi bên kia cũng sửa list. Thử thật: A xóa `f2`, B thêm `fB` → kết quả `["f1","f2","f3","fB"]` (`f2` quay lại).
  Hậu quả: areas.json khai lại file/cờ/test đã bỏ → test devsys đỏ (thấy được, không im lặng). Sửa: dùng `base` —
  `result = [x for x in ours if x in theirs or x not in base] + [x for x in theirs if x not in ours and x not in base]` (giữ thứ tự ours; nếu
  `base` không phải list → như hiện tại), + test "một bên xóa, bên kia thêm".

## Không thuộc đề nhưng ghi nhận
- `merge_union.read_stage` trên Linux chạy git với `env={}` (không PATH/HOME) — thử thật chạy được; nếu git cần cấu hình người dùng (safe.directory)
  có thể lỗi rõ ràng (không ghi sai). Chấp nhận.
