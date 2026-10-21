# C-RA-DP9-M29 — Rà kỹ chỉ đọc nhánh DP9 (cloud-D) + C-M29 (cloud-E) (cloud-C, 21/10)

- Đã rà `origin/cloud/v31-dp9` @ ca4bd441 (M2.7 image preflight) và `origin/cloud/v31-m29` @ c4da3ee9 (M2.9 lời dẫn ngoài khớp môi).
- Chỉ đọc: không sửa nhánh của làn khác. Mỗi nhánh chạy test trong worktree tạm, 0 USD.

**Kết luận: cả hai nhánh GỘP ĐƯỢC.** Không có lỗi CAO. Có 2 điểm VỪA liên nhánh, phải xử lý lúc gộp cùng C-M21 (`cloud/v31-m21`, chưa gộp).

## Đối chiếu tiêu chí đề
| Tiêu chí | DP9 | M29 |
|---|---|---|
| Cờ TẮT = giống byte | ✅ `_blocked` / `_pregen` tách hàm nhưng giữ đúng lời cũ (`plate_line`, `layout_reason`, `formula_reason`; test `test_blocked_words_unchanged`, `test_flag_off_never_runs_the_check`); `_pregen_dropped` chỉ ghi khi cờ bật; cờ đã có trong golden `package_inputs.json` | ✅ mọi caller rẽ theo `lipsync.offscreen_on()` / `voice.fit_review_on()`; cờ tắt → đường cũ nguyên văn (`plan_fit` cùng phép tính `fit_durations`); 2 cờ đã có trong golden |
| 0 điểm chặn mới | ✅ `_pregen_shadow` không trả True, không giữ job; điểm chặn cũ (nền 3D lẫn máy) giữ nguyên, shadow bỏ mã `nen_3d` để không báo trùng | ✅ không thêm chặn. Cờ `fit_durations_review` bật còn **bớt** giữ: `pending_fits` bỏ shot chỉ có lời dẫn |
| Preflight chỉ REVIEW/VÀNG, có mã sổ lỗi | ⚠ dòng diag ghi `REVIEW (shadow, không giữ — sẽ là ĐỎ/VÀNG khi bật chặn)` — đạt phần mức. **Mã sổ lỗi chỉ có cho 3/10 mã** (`khoi_giu_cho`→P31-G1, `ky_tu`→G13/G54, `khung_dau`→G28); dòng shadow không ghi mã sổ (THẤP-1) | — |
| Không đụng poll/submit runner (M1.2/M1.3) | ✅ chỉ `_blocked`, `_pregen`, `_finish_args`, `_stamp` (lớp chuẩn bị trước gửi) | ✅ chỉ `_take_audio` / audio khớp môi (chuẩn bị) + chữ diag; có tôn trọng `_preview` của M4.7 |
| M2.9 nghiệm thu `tests/test_narration_regression.py` | — | ✅ fixture `offscreen` 2 nhánh: TẮT → G15/G16/G17/G53 vẫn `xfail(strict=True)` đúng mã (chứng minh lỗi cũ còn); BẬT → gỡ xfail, xanh. Chạy: 261 qua, 21 xfail, đều ở `offscreen_off` |

Test đã chạy:
- **DP9:** `test_image_pregen`, `test_video_pregen`, `test_place_refs`, `test_plate_package_single_angle`, `test_prompt_formula`, `test_sent_package`, `test_golden_replay` → 190 qua; 9 đỏ đều đã biết ở cloud (8 golden cần Python 3.14 + `unreadable_picture`).
- **M29:** `test_narration_regression`, `test_v31_m29_narration`, `test_fit_durations_review`, `test_director_byd`, `test_quality_tier`, `test_seedance_refs`, `test_skill_objects`, `test_price_label_scan` → 261 qua, 21 xfail, 0 đỏ.

## Phát hiện
### VỪA-1 (liên nhánh DP9 × C-M21): `image_pregen._check_byd` đọc `data.get("byd")` thẳng
C-M21 có test AST `tests/test_v31_m21_byd_v2.py::test_every_core_reader_goes_through_the_adapter`: ngoài `shot_intent.py`, không file `core/` nào được đọc BYĐ thẳng. Gộp DP9 + C-M21 thì test này **đỏ**.

**Sửa lúc gộp** (một dòng): `byd = shot_intent.byd_of(data)` thay cho `data.get("byd")` + `isinstance`.

### VỪA-2 (liên nhánh DP9/M2.4 × C-M21): BYĐ nháp dùng `_p.draft` / `_p.from`
- `image_pregen._check_byd` coi `byd._p.draft` = BYĐ nháp (M2.4, shot chèn).
- Schema M2.1 của C-M21 cho `_p` = `{by ∈ director|human|backfill|code, model, at, revision}`, có `_p.by` bắt buộc ở v2. Một BYĐ v2 nháp chỉ có `{"draft": true}` sẽ bị `validate` báo `_p.by` = BLOCK.
- **Cần thống nhất với C-M24 (cloud-E, M2.4)** theo một trong hai cách:
  - (a) M2.1 thêm `draft` / `from` vào `_p`, với `by: "code"`; hoặc
  - (b) BYĐ nháp = `_field_state.byd = REVIEW_REQUIRED` (M2.5) thay cho cờ trong `_p`.
- Đề xuất (a): ít đổi nhất, khớp mục 2.1 M2.1 "BYĐ DRAFT của shot chèn = REVIEW".

### THẤP
1. **DP9:** `ERRORS` chỉ ánh xạ 3 mã; `nen_3d`, `cong_thuc`, `bo_cuc_kho`, `tham_chieu`, `van_tay`, `byd` chưa có lỗi gốc; dòng shadow không mang id sổ. Ngoài ra `ky_tu` khai trong `CODES` nhưng chưa lớp nào kiểm (đã ghi "M2.8 / DP10").
2. **DP9:** `_pregen_shadow` dựng gói lần thứ hai: băm sha mọi ảnh ref ở mỗi lần `_pregen`. Khi cờ bật, I/O gấp đôi. Cờ tắt không ảnh hưởng.
3. **DP9:** `_check_refs` dùng luật adapter Deepix (`MAX_REFERENCES`, `reference_problem`) cho mọi provider ảnh. Cap đã đi qua `image_models.max_refs(model)` nên ổn với model đã khai; luật đọc ảnh vẫn là của Deepix.
4. **M29 (A11):** hai thông điệp ⚙ Chẩn đoán (`end_frame_skill_object`, `skill_object_compose`) đổi chữ **không theo cờ**. Không đổi gói gửi, không test / công cụ nào tìm chuỗi cũ (đã grep). Chỉ ghi để biết.
5. **M29 × C-M25:** `voice.apply_fit` (đường mới ghi `motion_prompts.duration_sec`) giống `fit_durations` cũ: không đọc khóa `duration_s` của người (lỗ hổng L2-like). Gộp cùng C-M25 thì nên thêm `write_guard.observe(…, {"duration_s": to}, actor)`: người bấm Áp dụng = `human`, tự động = `auto`.

## Gộp (dự báo xung đột)
DP9, M29, C-M21, C-M25, C-M25B, C-GOLDEN2 đều thêm cờ vào cùng chỗ trong `core/features.py`, `tests/golden/package_inputs.json` (image + video) và `devsys/areas.json`. Xung đột chỉ là chỗ thêm mục: **giữ cả hai bên**. `core/runner.py`: DP9 (ImageRunner) và M29 / M47A / M25 (VideoRunner) sửa ở các khối khác nhau.
