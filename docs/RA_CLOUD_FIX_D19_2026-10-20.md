# Báo cáo C-FIX-D19 (sửa lỗi rà C-RA-D19 trên 3 nhánh Codex Đ19) — 20/10/2026

- Nhánh: `cloud/v31-fix-d19` = `origin/main` + gộp `codex/d19-viec2-doi-soat`, `codex/d19-viec3-provider`, `codex/d19-viec4-subjects` (gộp từng nhánh;
  xung đột `docs/CODEX_TASKS.md` giữ cả hai dòng kết quả; bỏ `HANDOFF.md` và dòng `TODO.md` ngoài mục 📨). Code chỉ đụng `tools/clipai_cost_reconcile.py` + test.
- Việc 2 (công cụ đối soát, vẫn CHỈ ĐỌC, không API trả phí):
  - CAO: `validate_pricing` nhận giá `null` (= chưa biết); task dùng mức chưa giá → `ledger_usd=None` + cảnh báo `unpriced:<model>:<tier>`; kiểu sai vẫn bị
    từ chối. Chạy được với `data/pricing.json` THẬT (test đọc file thật, mã thoát 0).
  - VỪA: clip NHÓM (thành viên chung `external_id`, cột `group_leader`) → task gán job DẪN, sổ chi cộng mọi thành viên, `group_members` chia tiền task theo
    `clip_span.length` (thiếu → chia đều + cảnh báo `group_split_equal`); tổng tiền task tính MỘT lần; ≥ 2 job dẫn → vẫn `ambiguous_job`.
  - THẤP: bản cao có `draft_job_id` mà gói không có `draft_task` → `kind=new_final` (gen mới, `quality_tier.NEW_GEN`), không còn tính là bước nâng; `main`
    in loại lỗi + mã do công cụ đặt (vd `ValueError invalid_pricing`) — chi tiết lạ (SQLite/JSON) vẫn không in; báo cáo ghi `scope=seedance_only` + câu
    "chỉ họ Seedance (task Kling chưa đối soát)".
  - Test `tests/test_clipai_cost_reconcile.py`: 7 ca mới (6 ĐỎ trước sửa, 1 ca chứng minh vẫn ambiguous khi 2 job dẫn) → 33/33 XANH; 1 ca cũ đổi câu báo
    lỗi mong đợi (thêm loại + mã, theo đề "không nuốt lỗi"), vẫn kiểm không lộ nội dung tệp.
- Việc 3 (`docs/V3_1_M1_4B_THIET_KE_2026-10-20.md`): bỏ "hold toàn bộ LLM" (`LEGACY_LLM_CONTEXT_UNKNOWN`) → job / dự án cũ NULL theo môi trường như trước
  (khớp code `cloud/v31-m14b`); dẫn chiếu M1.4a đã gộp (`missing_hint`, `STOP_CODES`, `clean_env`, `cli_error_code`); deploy không cần pha hold; down ưu tiên
  để cột, `migrate_llm_provider_down` chỉ gỡ khi không dữ liệu / `force`.
- Việc 4 (`docs/V3_1_M1_5_THIET_KE_KHO_CHU_THE_2026-10-20.md`): khối "Cập nhật C-FIX-D19": (1) mọi xóa = dry-run + người duyệt TỪNG plan (`plan_hash`,
  dùng một lần, không scheduler tự apply); (2) cùng commit sửa G59 phải chuyển `subjects.run_auto_cleanup` (cờ cũ `subject_auto_cleanup`, verified=True)
  sang CHỈ LIỆT KÊ — 0 lời gọi delete, có test; (3) job không cần ảnh Kho không vào `QUEUE_CAPACITY`.
- Không chạy cả bộ (chỉ đổi 1 công cụ chỉ đọc + test của nó); phiên chính rà + gộp.
