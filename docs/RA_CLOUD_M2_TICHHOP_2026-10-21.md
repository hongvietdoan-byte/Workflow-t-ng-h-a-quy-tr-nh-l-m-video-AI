# C-M2-TICHHOP — Nhánh tích hợp M2 + sửa 4 lỗi VỪA rà chéo (cloud-C, 21/10)

- Nhánh: `cloud/v31-m2-tichhop`, tạo từ origin/main @d7849ffb.
- 0 USD; không đụng CSDL thật; không có migration.
- Cờ mới của các nhánh đều TẮT. Cờ TẮT = hành vi như main (riêng M21-2 THẤP, xem "Còn mở").

## Merge (theo thứ tự đề)
| Nhánh | sha nhánh | Merge commit | Xung đột |
|---|---|---|---|
| `cloud/v31-m21` | 6581bde7 | b42e2581 | — |
| `cloud/v31-m25` | b405b2d2 | 680ee07f | `features.py`, `areas.json`, `package_inputs.json` → `tools/merge_union.py` |
| `cloud/v31-m25b` | 94a606b4 | dff77b09 | `areas.json` → merge_union |
| `cloud/v31-m26` | 0212786e | 1af6ec12 | — |
| `cloud/v31-m29` | c4da3ee9 | 823f5a2d | `package_inputs.json` → merge_union |
| `cloud/v31-dp9` | ca4bd441 | 9bbbe52f | `package_inputs.json` → merge_union |
| `cloud/v31-dp10` | e5a4a1ac | 9c10c585 | `features.py`, `areas.json`, `package_inputs.json` → merge_union |
| `cloud/v31-golden2` | 3f6db2de | d1ecc668 | `areas.json` → merge_union |
| `cloud/v31-m24` | 1971d85f | e61228d8 | `core/shot_intent.py` `validate` (sửa tay: giữ luật v2 của M2.1, `_p` chỉ hợp lệ ở v2 — xem VỪA-2) + 2 JSON → merge_union |

Sau mỗi lần dùng merge_union đã kiểm `features.py` parse được và không còn dấu xung đột.

## 4 lỗi VỪA đã sửa (mỗi lỗi: commit test đỏ riêng → commit sửa)
1. **VỪA-1** (rà DP9 × M21), ae60ed48:
   - `image_pregen._check_byd` và `model_router.needs_first_frame` (của DP10, cùng lỗi) đọc BYĐ thẳng.
   - Nay đọc qua `shot_intent.byd_of` / `read("khung.moc_nen.y_do")`.
   - Test đỏ có sẵn: `test_v31_m21_byd_v2::test_every_core_reader_goes_through_the_adapter` → xanh.
2. **VỪA-2** (DP9/M2.4 × M2.1), test d4d91c98 → sửa 881b240b — một nguồn provenance:
   - `_p` của M2.1 thêm `draft` (bool) + `from` (scene id), có validate.
   - BYĐ nháp = v2 (`byd_v: 2`), vì `_p` chỉ hợp lệ ở v2.
   - Cổng ảnh / video đọc qua `shot_intent.is_draft` / `draft_source`.
   - Test: `DraftProvenanceTests` (3 ca) + `test_draft_is_schema_known_and_picked_for_repair`.
3. **M21-1**, test eeace88d → sửa e4501586 — thêm `shot_intent.byd_or_raw` + `BydTypeError(ValueError)` với `code = byd_sai_kieu`, `level = REVIEW`, dùng ở `qc_observe.compile_checks`, `lock_exceptions.shot_label` / `for_shot`, `film_grammar._exception`:
   - cờ `byd_v2_levels` TẮT: BYĐ chuỗi / danh sách vỡ AttributeError **y main**;
   - cờ BẬT: ném BydTypeError có mã, mức REVIEW — nói ra, không im lặng; `qc_observe._prepare` bắt ValueError → VÀNG, không gọi VLM;
   - BYĐ thiếu / rỗng → như cũ.
   - Test: `tests/test_v31_m2_tichhop.py` (26 ca).
4. **M25-1**, test c59d1c57 → sửa c2669686:
   - `write_guard` đang trong giao dịch của nơi gọi thì giữ dòng diag shadow (`_PENDING`); `flush(conn)` ghi sau commit / rollback của nơi gọi, kèm lần `observe` / `lock` kế ngoài giao dịch. Không còn commit hộ nửa lô.
   - `lock()` không commit khi nơi gọi đang trong giao dịch.
   - Đã thêm `flush` sau commit ở 11 chỗ gọi: `llm_io.store_motion_prompts`, `audio_first`, `seedance_refs`, `previz`, `tools/byd_fill` ×2, `prompt_formula` ×2, `prompt_rewrite` ×3.
   - Test:
     - lô 3 shot, shot 2 bị khóa, shot 3 ném lỗi → kết nối khác không thấy nửa lô, cả khi cờ bật lẫn tắt; diag ghi sau rollback + flush;
     - diag ghi sau commit;
     - lock không commit hộ.
   - Đã sửa một test cũ: `test_v31_m25_write_guard::test_l6…` gọi `_write` giữa giao dịch. Test nay commit + flush trước khi đọc diag, và kiểm thêm "giữa giao dịch chưa ghi". Đây là hành vi mới có chủ đích.
   - Điểm phụ "người sửa motion rồi AI đè → diag": `test_v31_m25b_motion_lock` + `test_l1_motion_prompt_by_ai_on_locked` xanh trên nhánh tích hợp.

## Bộ test đầy đủ (cloud Linux, Python 3.13)
`7101 passed, 38 skipped, 22 xfailed`. 5 failed, **đều đỏ sẵn trên main**:
- `test_devsys_plan_map` (M4.8 chưa map);
- `recut_by_hand`;
- `punches`;
- `end_popup_p24`;
- `unreadable_picture`.

Golden: skip đúng (golden2 `needs_native_314`) — phiên chính nghiệm thu golden #24/#27 trên nhánh này ở máy chính (Python 3.14).

## Rà khâu liên quan (luật 7)
Xem mục cuối (agent rà 4 sửa).

## Còn mở
- **M21-2 (THẤP, không thuộc 4 VỪA):** `validate()` nhận khóa `byd_v` không qua cờ.
- **M25-3 (THẤP):** `prompt_rewrite._set_prompt` đọc thêm một câu SELECT khi cờ tắt.
