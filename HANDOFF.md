# HANDOFF — sửa gốc 3 lỗi lọt kiểm trước gen ảnh #31 (17/10) + lệnh kiểm trước gen

Nhánh: `claude/wizardly-elbakyan-596555` (cắt từ main 40ff268a). CHƯA gộp main.

## Đã xong (code + test riêng xanh: `py -m pytest tests/test_pregen_root_1710.py` 13 qua; đỏ 11/13 trên code gốc)
1. Một định nghĩa "nền 3D cũ": `core/location_pack.render_moved` + `LOCKED_RULE` (dấu meta.json) dùng ở `ensure_plates` (render lại
   bản cũ đã dời máy ĐÃ KHÓA — gốc 7 shot #31 phải `--fresh-shot`; bằng chứng: diag 15/10 18:43 máy ảnh toàn shot 21 bị "đưa máy tiến",
   17/10 "máy đã khóa, không dời"), `stale_plates`, `refresh_due`, `stale_plate` (memo/shot); `change_audit` gọi chung.
   Nền cũ CHẶN nút Gen: `batch.image_gates(p, pid, data_dir)` block đỏ + `plates_stale`; step2/queue_images gọi `place_refs.ensure_async` (0 USD).
2. `byd.noi_chon` theo time/weather: trigger CSDL `trg_scene_noi_chon(_new)`, `trg_change_scene` bỏ qua phần chép; `shot_intent.sync_noi_chon`
   trong `llm_io.update_scene`; quyết định `time-weather-single-source-2026-10-17` + `check_time_weather_single_source`.
3. Giá một con số: `cost.estimate_images` có `parts/qc/total` (+ `picture_qc_usd` dùng chung `_estimate_run`); nút Gen = ô 💰.
4. `tools/pregen_check.py --project N [--payload]`; dòng ở CLAUDE.md (7b) + skill vong-lam-viec-theo-plan.
   Chạy trên #31 (17/10 ~18h): 21 ảnh ≈ 3,74 USD (16 khung đầu 0,83 + 5 khung cuối 0,26 + D6 1,27 + QC 1,37); 0 nền cũ; shot 9 bị Tổ rà soát giữ.

## Đang dở / bước kế
- Agent rà quy ước 7 đã giao nhưng CHƯA có kết quả (hạn mức) → giao lại: `py tools/related_areas.py` trên diff `main...claude/wizardly-elbakyan-596555`,
  chú ý trigger CSDL (json_set đổi định dạng chữ scenes.data, migration schema_stamp), vòng render lặp, memo stale_plate, tổng _estimate_run.
- CHƯA chạy xong cả bộ test `-n 8` → chạy, sửa đỏ.
- Sửa lỗi rà → commit → gộp main → push → khởi động lại Dashboard (trigger mới áp khi migrate) → `py tools/pregen_check.py --project 31`.
- Cập nhật dòng bàn giao TODO.md thành XONG.
