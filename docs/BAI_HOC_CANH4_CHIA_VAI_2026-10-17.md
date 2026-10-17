# Bài học — dàn lại cảnh 4 #31 qua chia vai (17/10)

Phiên sửa-chia-vai, 0 USD. Chưa ghi `stage_camera`, chưa `--crew-approve` (người dùng bật chế độ siêu nhanh, phiên điều phối lo cảnh 4 theo cách thường).

## 1. Vân tay cảnh 4 lệch — đúng, không phải lỗi code
- `stage_auto._crew_ctx(...)["fp"]` của cảnh 4 = `4880ffbae883f92a`, `result.json` lưu `9e256dc5f57f5fb5`. Chỉ một trường khác: `user_notes[7]`
  (vị trí CUỐI cảnh 3, `prev_state`): Kelly `(+0.55,+0.10)` → `(+0.45,+0.05)`, thêm tư thế `dung`.
- Gốc: `doan_3/result.json` ghi lại lúc 20:36 (round `crew/final`) SAU khi cảnh 4 chạy (10:50). `stored_state_before` lấy vị trí cuối đang lưu
  của cảnh liền trước **trên cùng sân khấu** (`kho265`: cảnh 2–3–4; cảnh 5–8 khác sân khấu nên không lệch).
- **Quy tắc:** dàn lại một cảnh thì mọi cảnh đứng SAU nó trên cùng sân khấu có vân tay mới → phải dàn lại. Chốt cảnh trước rồi mới dàn cảnh sau.
- Cờ `stage_handheld_props` không liên quan (lệch cả khi cờ tắt).

## 2. Lỗi code đã sửa (commit `b6132b9f`)
`core/stage_crew.py` `compare_table`: người ngoài khung có `size_pct`/`seen_pct` = `None` (khóa còn, giá trị rỗng) → `o.get('size_pct', 0):g` vỡ
`TypeError` khi dựng đề bài "Quay phim duyệt". Sửa `o.get(...) or 0`; test `test_table_object_out_of_frame_has_none_size`.

## 3. Lượt "Quay phim duyệt" chấm `khop` quá dễ — thiếu đối chiếu
Chỉ nhìn bảng số đo → đạt. Phải thêm:
- **Vị trí người GIỮA CÁC NHỊP:** shot 14 địch ở 4 ngả (bắc/đông/nam/tây), shot 15 Yêu nữ + Sứ giả đã nằm ở ngã bắc (dịch 15–24 m, hai shot nối liền).
- **Đối chiếu ghi chú khung / `end_state` của kịch bản:** shot 15 ghi địch "đổ gục SAU lưng" Kelly qua nhiều ngả; dàn cảnh đặt cả ba địch ĐỨNG TRƯỚC mặt Kelly.
- **Ý đồ shot thiết lập:** shot 14 "quan sát bốn kẻ địch" chỉ thấy 1/4 (máy nhìn bắc); Kelly giữa khung chứ không "tiền cảnh trái, sau hàng rào".

## 4. Bế tắc luật: shot 15 (hạ 3 địch ở 3 ngả)
`core/stage_director.py` `must_see` + luật K3 (`script_rules`): mọi nhân vật được NÊU TÊN trong câu hành động của shot `action` phải vào khung
một máy; không có đường miễn (`bo_luat` chỉ miễn luật khung Blender). Hệ quả: Đạo diễn buộc gom địch về một chỗ → mâu thuẫn kịch bản.
Hướng đã bàn (chưa làm, dừng vì siêu nhanh): (A) thêm khai ngoại lệ "ngoài khung có chủ ý" + lý do (đổi code + test); (B) dồn địch bắc ở shot 14;
(Cách 1) tách shot 15 thành 3 shot mỗi shot một địch — lưu ý kịch bản gốc `why` cố ý KHÔNG tách ("tránh cắt vụn làm loãng cao trào"), Seedance 2.5
ra tối thiểu 4 s nên 3 shot 2,3 s vẫn tính ≈ 12 s; (Cách 2) previs Blender cú chạy gặp/hạ từng địch làm ref V2V (cùng công cụ nhánh previs-sau-lung).

## 5. Mẹo vận hành
- `--beats` chỉ vẽ lượt ĐÃ LƯU (`result.json`); trước khi duyệt xem ảnh nhìn từ trên của lượt đang dở ở `doan_N/crew/m1/top_beats.png` + `v2_shot*_clay_raw.png`.
- Đường dẫn Windows trong lệnh Git Bash: dùng `/`, không `\` (một `\` bị nuốt làm `ensure_k1_seg` tạo thư mục rác ở gốc repo).
- Sửa file trong worktree: dùng đường dẫn worktree, không đường dẫn checkout chính (hook chặn).
- Chia vai cảnh có `placed_without_handheld`: giữ đầu vào cũ (không có súng); dàn lại có súng = `--crew-reset --cam-tay`.
- Thử nghiệm A/B shot nên làm trên DỰ ÁN THỬ nhân bản (`core.compare.clone_project`, mẫu `tools/experiments/place_refs_trial.py`), không đánh số lại shot của #31.
