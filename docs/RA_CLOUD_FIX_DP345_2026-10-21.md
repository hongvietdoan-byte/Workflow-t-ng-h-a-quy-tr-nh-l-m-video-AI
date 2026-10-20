# C-FIX-DP345 — sửa rà DP3 / DP4 / DP5 (cloud-D, 21/10)

Nhánh `cloud/v31-fix-dp345` từ `origin/main` (đã có "Gộp cloud/v31-dp5" `9ff0e61`). Cờ giữ TẮT (`final_black_freeze`, `qc_evidence`,
`repair_router`). Không gọi API; video thử do ffmpeg lavfi tạo trong test.

## (1) VỪA — `core/final_qc.py` check_black_freeze bỏ đứng hình CỐ Ý
- `intended_holds(manifest, timeline, total)`: đoạn giữ khung có chủ đích đọc từ manifest bản dựng —
  `end_hold.held_s` (delivery._hold_end, `END_HOLD_S` 2,5 s: cuối timeline), `end_popup.held_s` (end_popup.apply hold: thêm sau timeline
  tới hết phim), `editor_fit` how `"hold"` (người sửa kéo dài shot: cuối shot đó).
- `check_black_freeze(video, timeline, manifest)`: trừ phần nằm trong đoạn cố ý; còn lại ≤ 1,5 s (+0,05 s lệch khung) → không báo; còn
  lại > 1,5 s → vẫn `freeze_frame` (warn) và nói "đã trừ X s giữ khung cố ý, còn Y s đứng không cố ý". `run()` truyền manifest.
- THẤP: blackdetect + freezedetect một lượt ffmpeg (một chuỗi `-vf`), `timeout` 600 s → quá giờ = `black_freeze_unmeasured` (không treo).

## (2) THẤP — `core/qc_evidence.py`
- `QC-A4-BLACK_FRAME` / `QC-A4-FREEZE_FRAME` trần **REVIEW** (G2-5: QC bản dựng không chặn xuất).
- `validate()` báo `severity … vượt trần … của mã` (trước đây chỉ `finding()` hạ mức; finding ghi tay vẫn lọt BLOCK).
- `tests/test_v31_dp4_qc_evidence.py::test_block_rules_d07`: luật hiệu chuẩn BLOCK nay kiểm trên mã tất định GIẢ có trần BLOCK
  (`mock.patch.dict(E.CODES)`) — BLACK_FRAME không còn BLOCK được; luật không bị nới.
- `core/repair_router.py`: chữ escalation "vẫn BLOCK sau 2 lần dựng" → "vẫn báo sau 2 lần dựng" (khớp trần mới).

## (3) THẤP — `core/pipeline.py` apply_qc
`if not passed and repair_router.enabled():` — cờ TẮT không dựng danh sách mã, không gọi `auto_limit` / `observe`.

## Test (`tests/test_v31_fix_dp345.py`, 10 ca — ĐỎ cả 10 trên code cũ → XANH)
`test_end_hold_of_a_short_last_shot_is_not_a_freeze` (shot cuối 0,8 s + end_hold), `test_end_popup_hold_is_not_a_freeze`,
`test_editor_fit_hold_mid_film_is_not_a_freeze`, `test_a_still_longer_than_the_hold_is_still_said`, `test_one_ffmpeg_pass_with_a_timeout`,
`test_a_hung_ffmpeg_is_unmeasured_not_stuck`, `test_run_passes_the_manifest`, `test_black_and_freeze_never_block[BLACK|FREEZE]`,
`test_repair_router_off_is_not_called` (kiểm mã nguồn: gọi observe nằm sau `enabled()`).
Vùng: test_v31_dp3/dp4/dp5, test_final_qc — 64 qua. Cả bộ not-slow: xem dòng kết quả cuối báo cáo.

## Rủi ro / việc mở
- Ánh xạ thời gian dựa vào `timeline` của manifest (giây đã cắt) — bản dựng có chuyển cảnh chồng (xfade) làm mốc lệch tối đa độ dài
  chuyển cảnh; khi đó phần không cố ý vẫn được tính đúng chiều (chỉ trừ phần trùng).
- `test_repair_router_off_is_not_called` là kiểm mã nguồn (dựng apply_qc thật quá nặng cho mục THẤP).
- Quy ước 7: luật cloud không mở Agent → tự rà theo `tools/related_areas.py`; phiên chính rà lại khi gộp.
