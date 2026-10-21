# C-FIX-THAP-5 — các lỗi THẤP rà 21/10 (cloud-C, 21/10)

Nhánh `cloud/v31-fix-thap-5` (tạo từ origin/main). Các cờ liên quan vẫn để TẮT, không đổi mặc định.

## (1) `core/final_qc` — chuyển cảnh chồng
**Lỗi:** với kiểu `crossfade` hoặc `dip_to_black` (`OVERLAP_STYLES`), bản dựng ngắn hơn tổng timeline đúng `fade × (n−1)`. `intended_holds` và `_shot_at` vẫn cộng thẳng timeline, nên mốc giữ khung cố ý (`end_hold`, `editor_fit` "hold") lệch đi. Hậu quả: báo nhầm `freeze_frame` và gắn nhầm số shot.

**Sửa:**
- Thêm `_overlap(manifest)`: đọc `manifest.transition` và `manifest.fade` (delivery đã ghi sẵn hai trường này), tính giống `final_cut.total_seconds`.
- Thêm `_shot_ends`: điểm kết thúc của shot i trên bản dựng = tổng giây timeline − overlap × i.
- `intended_holds` và `_shot_at(…, manifest)` dùng `_shot_ends`; `check_black_freeze` truyền manifest vào. Với kiểu `cut` kết quả giữ nguyên như cũ.

## (2) `core/world_map`
**Lỗi:** `build` gọi `build_3d` mà không truyền BYĐ, nên khi BYĐ đổi thì map 3D không bị đánh dấu hết hiệu lực. Ngoài ra `entities_at(m, None)` gặp `valid_from` là số thì ném `TypeError`.

**Sửa:**
- `build_3d(…, byd=)` truyền BYĐ sang `sources`. Khi BYĐ đổi: revision + 1, bản cũ chuyển vào history với `invalidated.why = byd_changed`.
- `entities_at(m, None)` trả mọi thực thể.

## (3) QC shadow trên thẻ clip
**Lỗi:** `shadow_of` đọc 3 tệp và bảng ở mỗi lần rerun, trên mọi thẻ clip.

**Sửa:** thêm `send_preview.shadow_cached`, cache theo khóa (data_dir, dự án, job, shot, mtime của `video_qc.jsonl` / `qc_evidence.jsonl` / `continuity_shadow.json`, rowid qc_run lớn nhất của dự án). Cache tối đa 512 mục; đầy thì xóa hết. UI chuyển sang dùng `shadow_cached`.

## (4) `devsys/areas.json`
Khu core_infra: thêm `tests/test_v31_g36b_refusal_skip.py` và `tests/test_v31_fix_thap_5.py`.

## Bằng chứng
- `tests/test_v31_fix_thap_5.py` có 9 test. 8 test được commit riêng khi còn đỏ, sau khi sửa thì xanh cả 9.
- Các test liên quan vẫn xanh: DP3, C-FIX-DP345, DP8, M47A, devsys.
- Bộ test đầy đủ: 6600 passed; 4 failed cũ (đỏ cả trên main).
