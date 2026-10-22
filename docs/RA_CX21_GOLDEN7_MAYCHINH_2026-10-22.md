# CX21-GOLDEN7 — nghiệm thu golden A/B trên MÁY CHÍNH (22/10/2026): **ĐẠT**

Chạy một lượt trên máy chính Windows (Python 3.14.6 native), 0 USD: chỉ dựng gói để so byte, không gửi provider nào, không ghi `data/` thật.
Cách chạy theo báo cáo Codex (`origin/codex/v31-golden7:docs/RA_CX21_GOLDEN7_CODEX_2026-10-22.md`) và thư chốt `db0ccfac`
(sổ `v31-ep-golden-ab-acceptance-2026-10-21` + `v31-ep-g1-golden-compat-production-baseline-2026-10-21`).

## SHA đã pin (worktree detached riêng, không đụng bản chính đang chạy Dashboard)

| Vai | Nguồn | SHA |
|---|---|---|
| A | main (pin theo đề) | `a117497d306024c026804247e0f9f9f67ffdaaf7` |
| B | `origin/cloud/v31-m2-tichhop` | `9746a6ea38d874baf226765cfd378db01eca988d` |
| Công cụ | `origin/cloud/v31-golden5` (C-GOLDEN7) | `621661a8d3bf1e653a15f9c4a67cdd2918f5b0ae` |

Bản chính `D:/AI-Video-Pipeline` lúc chạy ở `b4cd91ec` (đã chứa `a117497d`); chỉ đọc `core/features.py`, `dashboard.env` (chỉ các dòng `FEATURE_*`),
`data/feature_settings.json`, `data/manifest.sqlite` (backup API, `mode=ro`).

## 1. Đối chứng âm (native) — XANH

`tests/test_golden5.py::test_real_worker_two_code_trees_same_and_one_line_changed` trong worktree công cụ: **1 passed (41,5 s)**.
Chạy TRƯỚC snapshot / lượt thật.

## 2. Catalog cờ + baseline

| Nguồn | Số cờ |
|---|---:|
| Live máy chính (b4cd91ec) | 150 |
| A | 150 |
| B | 153 |
| Công cụ | 153 |
| **Hợp A ∪ B** | **159** (khớp chốt) |
| **Experimental V3.1** (`verified: False` + nhãn V3.1) | **32** (khớp chốt) |

- 32 experimental (TẮT explicit): `budget_notice_d01, byd_v2_levels, continuity_shadow, continuity_state, continuity_validator, crew_registry,
  diag_merge, field_guard, final_black_freeze, fit_durations_review, gen_auth_shadow, horizon_needs_sky, image_pregen, insert_inherit,
  narration_offscreen, pause_before_submit, poll_claim, qc_evidence, qc_false_alarm_fix, refusal_skip_same_picture, release_gate, repair_router,
  router_first_frame, send_estimate, send_preview_panel, sent_package_relpath, stage_props_byd, stale_code_alarm, video_qc_shadow,
  whitebox_height_dummy, world_map, world_map_sentences`. Gồm đủ 5 cờ đề nêu (`director_rewrite_respect_lock`, `stage_view_ui` thuộc 9 cờ
  A∪B không có ở live → theo chốt `db0ccfac` là cờ mới V3.1 TẮT; 9 cờ này đều nằm trong 32).
  Nguồn quyết định: thư chốt `db0ccfac` (cloud-claude 22/10 03:31) theo sổ `v31-ep-golden-ab-acceptance-2026-10-21`.
- Baseline = `core.features.state()` của code live, môi trường = 36 dòng `FEATURE_*` của `dashboard.env` + `data/feature_settings.json`;
  `on` → true, còn lại → false. 159 cờ, 113 BẬT.
- 6 cờ đang 🎓 học việc trên sản xuất → **false**: `camera_setups, continuous_takes, qc_team, scene_establishing, scene_qc_trusted, storyboard_auto_trust`.
- **2 cờ experimental đang BẬT trên sản xuất, bị ép TẮT theo chốt**: `pause_before_submit`, `poll_claim` (xem Rủi ro).

## 3. Lệnh đã chạy

```
git worktree add --detach D:/golden7/tool 621661a8   # + D:/golden7/a a117497d, D:/golden7/b 9746a6ea
cd D:/golden7/tool && PYTHONUTF8=1 py -m pytest "tests/test_golden5.py::test_real_worker_two_code_trees_same_and_one_line_changed" -q
cd D:/AI-Video-Output/golden-snapshot-7mc && PYTHONUTF8=1 py run_ab_mc.py
#  run_ab_mc.py: dựng flags.json (trên) → sqlite backup mode=ro ra manifest.sqlite → G.main_ab(['--ab','--db',snap,'--ref-root','D:/AI-Video-Pipeline',
#   '--flags',flags.json,'--code-a',A,'--code-b',B,'--project',24,27,31,33,'--output',ab_all.json])
```

Mã thoát **0**, 2 567 s. 158 ca (#24: 24, #27: 44, #31: 78, #33: 12) — khớp số ca của GOLDEN6.

## 4. Kết quả

| Dự án | Ca | SAME | DIFF | ONE_FAIL | BOTH_FAIL |
|---|---:|---:|---:|---:|---:|
| #24 | 24 | 15 | 0 | 0 | 9 |
| #27 | 44 | 25 | 0 | 0 | 19 |
| #31 | 78 | 71 | 0 | 0 | 7 |
| #33 | 12 | 6 | 0 | 0 | 6 |
| **Tổng** | **158** | **117** | **0** | **0** | **41** |

**Bằng chứng nạp đúng cây:** cả 117 SAME + 31 BOTH_FAIL có `loaded_a` ⊂ `D:\golden7\a` và `loaded_b` ⊂ `D:\golden7\b` (`core.runner`, `core.sent_package`);
0 ca nạp sai cây. 10 BOTH_FAIL còn lại không có `loaded` (xem dưới).

**BOTH_FAIL theo nhóm (A và B ra cùng lý do ở mọi ca):**

| Lý do | Ca | Job |
|---|---:|---|
| `prepare giữ (_hold)` | 31 | #24: 671–676, 687, 688 (9, approved); #27: 854, 856, 857, 861, 870, 871, 880–882, 886, 887, 900, 906, 914 (approved) + 874, 877 (failed); #33: 1190–1194, 1196 (succeeded) |
| `worker thiếu dependency hoặc schema` — `{"kind":"operation","path":"<outside-root>"}` | 10 | #27: 790, 839 (approved), 879 (rejected); #31: 1027, 1049–1051, 1054–1056 (pending_review) |

Cột lịch sử (tham khảo): DIFF_FROM_SENT 108, SAME_EXCEPT_FINGERPRINT 5, NOT_BUILT 39, NO_SENT 6 — chỉ so với gói gửi 11–13/10, không tính vào cổng.

## 5. Kết luận: **ĐẠT**

Đối chứng âm xanh + 0 DIFF + 0 ONE_FAIL + mỗi dự án ≥ 1 SAME (15 / 25 / 71 / 6) + bằng chứng `loaded` đủ ở mọi ca dựng được (117/117).
Theo bước 6 của `docs/handoff/KIEM_MAY_CHINH_TU_CLOUD.md`: mở khóa điều phối gộp một lần `cloud/v31-m2-tichhop` + m24 + golden5 (+ m73, m210, golden4).

## 6. Rủi ro / việc mở

1. **10 BOTH_FAIL "operation" không có chẩn đoán rõ.** Worker gặp một thao tác bị cấm mà không ghi đường dẫn (`forbidden()` không có `denied`
   trước đó: `subprocess.Popen`, `provider.submit/upload_image/submit_final_from_sample`, hoặc `CachedLibrary` Kho chủ thể thiếu dòng
   `seedance_subject_pictures` / gọi `list_assets`). Ngoại lệ xảy ra SAU khi nạp `core` nhưng nhánh `except` ở `tools/golden_db_replay.py:919`
   bỏ mất cả `loaded` lẫn `positions` khi exception có thuộc tính `diagnostic`. A và B cùng lỗi nên không che DIFF ở 117 ca đã so, nhưng 10 ca
   này (#31 pending_review, #27) **không được so**. Đề xuất cloud-C:
   - `tools/golden_db_replay.py:372-374` `forbidden()`: ghi `kind` cụ thể theo nơi gọi (vd. `forbidden("subject_library")`, `"provider_submit"`, `"subprocess"`).
   - `tools/golden_db_replay.py:919`: luôn kèm `positions[-8:]` và `loaded` (giữ biến `loaded` ở phạm vi `_worker`, trả qua thuộc tính exception)
     để BOTH_FAIL loại này vẫn có bằng chứng nạp đúng cây + vị trí lỗi.
2. **`pause_before_submit`, `poll_claim` BẬT trên sản xuất nhưng bị so ở trạng thái TẮT** (theo chốt: mọi cờ V3.1 experimental TẮT). Golden
   không chứng minh A≡B khi hai cờ này BẬT. Nếu chúng chạm đường dựng gói, cân nhắc một lượt phụ bật hai cờ này.
3. Baseline tái dựng từ cấu hình hiện tại (không phải ảnh chụp lúc gửi); job chưa gửi dùng envelope giả `provider=fake` cho cả hai bên → nhánh
   Kho chủ thể ClipAI không được so ở các ca đó (giới hạn đã biết của C-GOLDEN5).
4. A pin `a117497d`; main hiện đã tới `49cd1c72`. Main cần giữ catalog đứng yên tới khi gộp xong M2 (bài học GOLDEN7).

## Tệp kết quả (ngoài git)

`D:/AI-Video-Output/golden-snapshot-7mc/`: `ab_all.json`, `flags.json`, `preflight.json`, `run-plan.json`, `exit-code.json`, `run_ab_mc.py`,
`manifest.sqlite` (snapshot mode=ro). Không commit CSDL / gói / prompt.
