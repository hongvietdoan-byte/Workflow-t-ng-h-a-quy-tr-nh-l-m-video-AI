# Bàn giao — khung "🧭 Trước khi chạy" (Bước 1, người dùng chốt 10/10)

Nhánh: `worktree-agent-aae46a38b6bfcc920` (chưa push, chưa sửa TODO.md).

## Đã làm (0 USD, chỉ đọc, không gọi model)
- `core/before_run.py` — `collect(conn, data_dir, pid)` → 4 nhóm (cost / hold / ops / inputs), mỗi mục `level` do|vang|info + `text` + `fix`;
  `title()` (tiêu đề tóm tắt số mục), `details_md()`. Phần nào đọc lỗi → mục 'info' nói rõ, không ném.
  - **Tên khác đề bài**: `core/preflight.py` đã có (kiểm IP/nội dung, dùng ở nơi khác) → đặt `before_run` để không trộn hai việc.
  - Cờ tốn tiền: change_review, director_rewrite (ước tính `cost.llm_estimate` theo sổ chi thật, không có giá → nói "chưa có giá"),
    two_tier_quality, stage_camera, director_camera_plan (chữ, không bịa số) + một dòng info các cờ chưa thử thật khác đang bật.
  - Giữ việc: mục đỏ Tổ rà soát (cờ tắt → info "không giữ gen"; thiếu bảng → "chưa có"), thay đổi chờ rà, ngân sách (chưa khóa ở mức
    Tự chạy trong trần / chạm trần), chế độ storyboard (cờ storyboard_api: shot chờ ảnh neo mà neo chưa xếp gen → đỏ).
  - Đầu vào: nhân vật (scenes.data `characters`, so tên CÓ dấu trước, bỏ dấu chỉ khi đúng 1 ứng viên) + `location_asset` thiếu `must_keep`;
    vật (prop/weapon) thiếu `height_m` (dùng `place_refs.shot_objects` như readiness); bối cảnh không có `location_pack.model3d` = "chỉ có ảnh".
- `dashboard/before_run_ui.py` — một expander mặc định đóng, không nút.
- `dashboard/steps/step1_v2.py` — gọi một lần ngay sau hero, TRƯỚC khi rẽ luồng `chat_first` (nên chỉ hiện đúng một lần ở cả hai luồng); chỉ khi đã có cảnh.
- `devsys/areas.json` — thêm 2 file vào khu vực step1 (không tăng version).
- `tests/test_before_run.py` — 5 test.

## Sửa theo phiên rà (7 lỗi, mỗi lỗi một test trong tests/test_before_run.py)
1. Mục đỏ Tổ rà soát không gắn shot (scene_id NULL) → 'vang' "không giữ gen" (blocking() chỉ giữ theo shot).
2. Đếm thay đổi chờ rà chỉ tính event có scene_id (thay đổi Kho không giữ gen).
3. must_keep chỉ kiểm nhân vật / pet (như core/change_audit), không kiểm bối cảnh.
4. Nhân vật trong shot không có trong Kho của dự án → 'vang' "'X' không có trong Kho của dự án".
5. Storyboard: neo "đang làm" chỉ tính job queued/running/retryable; câu "chưa có job gen đang chạy".
6. `collect` bọc `core.memo.cached` (một lần mỗi lượt vẽ + trạng thái CSDL).
7. stage_camera: bỏ vế "chưa render nền thật".

## Việc mở
- Quy ước 7 CLAUDE.md: phiên rà đã đọc nhánh, 7 lỗi đã sửa (mục trên).
- Chưa xem trên Dashboard thật (chỉ test + AppTest của Bước 1 xanh).
