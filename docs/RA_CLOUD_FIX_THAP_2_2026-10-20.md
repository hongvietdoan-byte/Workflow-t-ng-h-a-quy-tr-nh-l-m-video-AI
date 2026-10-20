# C-FIX-THAP-2 — sửa VỪA của C-FIX-THAP-1 + 2 THẤP (làn cloud-C, 20/10/2026)

Nhánh `cloud/v31-fix-thap-2` (từ `origin/main`@`1e00321a`, đã có fix-thap-1). Cờ giữ TẮT. 0 USD.

| # | Mức | Lỗi (rà phiên chính) | Sửa | Test |
|---|---|---|---|---|
| 1 | VỪA | `qc_scene._behind_any` bị THAP-1 thu hẹp bỏ `image_prompt` / `action` — chính trường chứa chữ của ca thật P33-A5 (#33 S2); test DP1 bị nới (fixture chuyển sang `blocking`) | GIỮ regex hẹp (chỉ chữ về MÁY), TRẢ `image_prompt` / `action` vào trường dò; fixture DP1 về `image_prompt`, test DP1 về "mọi trường" | 4 ca âm ở image_prompt / action ("the sun behind her shoulders", "rút súng sau lưng", "a tower behind her", "the sun behind her") vẫn kiểm cỡ; ca S2 ở `image_prompt` bỏ kiểm. Bỏ ca "camera behind the crates" của THAP-1 (đúng là chữ về máy) |
| 2 | THẤP | bộ nhớ `_SERIES` của `clip_measure.motion_series` không khóa (autoqc nền + bấm tay cùng đo) | `threading.Lock` quanh đọc / đuổi / ghi; phần đo chậm ở ngoài khóa | 8 luồng × 200 lần, 12 tệp, đuổi liên tục → 0 lỗi, ≤ 4 mục |
| 3 | THẤP | `code_version.banner`: dòng bản ghi cũ (chỉ sha) vẫn nói "tệp .py đã đổi" | mỗi cổng một lý do: có dấu vân tay → "tệp .py … đã đổi"; chỉ sha → "bản ghi cũ chỉ có sha a ≠ HEAD b — chưa biết tệp .py có đổi"; câu đầu "có thể chạy code cũ" | 1 ca 2 cổng (cũ + mới) |

Chạy: `test_v31_fix_thap_1`, `test_v31_dp1_qc_false_alarms`, `test_v31_m17_ops_notices`, `test_v31_m42_video_qc_shadow`, `test_clip_measure*`,
`test_v31_fix_m16_17`: 83 qua. Cả bộ `-m "not slow" -n auto` (Linux cloud): 6551 qua, 4 đỏ = các ca đỏ sẵn trên `main` cùng máy.
