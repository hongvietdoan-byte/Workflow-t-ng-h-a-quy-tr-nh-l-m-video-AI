# Giám sát độc lập kế hoạch V3.1 — đợt 1 (24/10/2026)

> Người viết: agent giám sát độc lập (chỉ đọc, 0 USD). Không sửa code, dữ liệu hay cờ, không commit. Mốc `main` lúc đo: `f96acd5d` (24/10 12:20).
> Nguồn: `docs/KE_HOACH_AI_VIDEO_PIPELINE_V3_2026-10-20.md` (gọi tắt **V3**), `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md` (gọi tắt **MB**),
> `devsys/errors.json`, `data/decisions.json`, `docs/DOI_SOAT_KHAU_2026-10-23.md`, hộp thư, git log 7 ngày.
> Không có bằng chứng thì ghi "chưa xác minh".

## 1. Bảng điểm

| Trục | Điểm (0–10) | Trọng số | Tóm tắt |
|---|---:|---:|---|
| 1. Đúng hướng | **5,0** | 0,40 | Mọi đợt đều nối được tới mục tiêu gốc. Nhưng 37/55 việc ✅ mới đạt cổng ở mức code/offline, và 0/5 mục tiêu đo được (V3 §2) đã được đo trên dữ liệu thật |
| 2. Lỗi / lỗ hổng trong quá trình build | **4,5** | 0,35 | Có 1 test đỏ trên main, sổ lỗi lệch kế hoạch 73 mục, M4.8 ✅ trước khi kiểm thật, 55/74 quyết định chưa có check. Không có lỗ hổng tiền nào ở mức CHẶN |
| 3. Chất lượng Dashboard theo mốc | **4,0** | 0,25 | M8.0 an toàn tiền tốt (38 test xanh, cờ BẬT). M4.8 đang được dùng thật. M4.7 vẫn ẩn sau cờ TẮT, M8.2–M8.4 (chế độ Cơ bản, chịu tải) chưa bắt đầu |
| **Chung** | **4,6** | | công thức bên dưới |

**Công thức:** Chung = 0,40 × T1 + 0,35 × T2 + 0,25 × T3 = 0,40 × 5,0 + 0,35 × 4,5 + 0,25 × 4,0 = 2,00 + 1,575 + 1,00 = **4,575 ≈ 4,6**.

### Các khoản trừ

**Trục 1 (10 − 5,0):**
- −2,0: 37/55 việc ✅ có cổng nghiệm thu chưa đạt thật. Đó là các việc cờ TẮT hoặc shadow chưa đo, chỉ có unit/offline test, hoặc ghi "CHƯA kiểm máy chính". Đếm từng đợt ở mục 3. Bằng chứng: MB:37–108, kết quả đo `features.state` ở mục 4.
- −1,5: 0/5 mục tiêu đo được của V3 §2 (V3:23–29) đã được đo trên dữ liệu thật:
  - MT2 "ước tính lệch ≤ 10 %": cờ `send_estimate` đang off, chưa có số đối soát (`docs/DANH_GIA_HIEU_QUA_CO_2026-10-21.md:125` "CHƯA ĐỦ BẰNG CHỨNG").
  - MT3 KPI "lỗi lọt cổng −50 %": MB **không có việc nào đo KPI này** (grep "KPI|lọt cổng|−50 %" trong MB = 0 dòng).
  - MT4 sơ đồ mặt bằng: `world_map` off, người dùng chưa duyệt map cảnh 4/6/8 (`docs/RA_CLOUD_DP8_2026-10-21.md:31`).
  - MT5 "clip đứng yên > 1,5 s gắn REVIEW trên 12 clip nháp #31" (V3 §8): `video_qc_shadow` off, không có báo cáo chạy.
  - MT1 "0 tiền thừa": 0 mục sổ lỗi ở VERIFIED.
- −0,5: M4.6 "Benchmark ≥ 20 lỗi + 20 đạt mỗi nhóm" ghi ✅ (MB:72) nhưng mới có khung. `data/qc_bench/` không tồn tại. `docs/RA_CLOUD_M46_2026-10-20.md:16` ghi "người dùng gán ≈ 1 000 dòng" là việc còn mở.
- −0,5: phạm vi phình. M6/M7/M8 thêm 26/75 việc (35 %) trước khi có pilot thật đầu tiên (M5.4 ⬜), nên tiến độ % bị loãng (MB:6–15).
- −0,5: M7.7 "Kiểm chứng + khóa TỪNG cờ" (MB:108) vẫn ⬜. Đây là nút cổ chai duy nhất biến code đã gộp thành mục tiêu đạt được, nhưng chưa có việc đang làm (CX24-M77-EVID còn CHỜ, ưu tiên 4).

**Trục 2 (10 − 5,5):**
- −1,5: sổ lỗi lệch kế hoạch. 73 mục OPEN/IN_PROGRESS có `plan_task` trỏ vào việc đã ✅ (ví dụ P31-G51→M4.2, P31-G13→M2.8, P31-G41→M3.3, P33-A7→M1.6). Toàn sổ: 0 VERIFIED, 16 FIXED_UNVERIFIED, 13 IN_PROGRESS, 60 OPEN, 2 WONT_FIX (`py devsys/errors.py check`).
- −1,0: test đỏ sẵn trên main: `tests/test_devsys_pipeline_maps.py::test_devsys_page_renders_four_tabs_and_three_maps` (1 failed, 75 passed).
  - Nguyên nhân thấy được: từ `da6d3a17` (23/10 14:39), M2.10 chuyển ⏸, và trang Kế hoạch vẽ radio `ans-choice-w-M2.10` đứng trước radio điều hướng. Test giả định `at.radio[0]` là radio điều hướng (`tests/test_devsys_pipeline_maps.py:242`).
  - Đã có việc CX24-DEVSYS-FIX (Codex 1, ĐANG LÀM).
- −1,0: M4.8 được đánh ✅ lúc 24/10 01:32 (`77fab4fa`) với ghi chú "CHƯA kiểm Dashboard thật" (MB:74). Lần dùng thật đầu tiên trên #34 tìm ra lỗi N5 tấm ghép dùng lần đo cũ (hộp thư 24/10 09:46), phải sửa ở `5deb6da0`.
- −0,5: 55/74 quyết định active không có `enforced_by`. Trong đó có 3 quyết định về tiền kiểm được bằng code mà chưa có check:
  - `ep-2210-qf-money-safety-first-2026-10-22`: đã có `tests/test_safe_paid_buttons.py` nhưng chưa nối vào sổ.
  - `ep-2310-qd3-auto-spend-limit-2026-10-23`: chưa có code (grep `auto_spend|hạn mức chi` trong core/dashboard/tools = 0) và cũng chưa ghi `pending`.
  - `v31-m6-generation-limits-policy-b-2026-10-21`.
- −0,5: golden A/B M1.9 chỉ so được 117/158 ca. 41 BOTH_FAIL (26 %) không so được (MB:45). Phần đó chưa có tương thích byte.
- −0,5: khoảng trống giữa các làn:
  - CX22-G1-EP-ROLE ở trạng thái ĐANG LÀM từ 23/10 10:38 (`26c4d09e`), nhưng không có nhánh `codex/*ep-role*` và không có commit code. Theo bảng phân công 24/10 12:09, việc này còn xếp sau M47B.
  - M6.0 🔄 (MB:84) trong khi việc giao CX23-M60-AUDIT vẫn CHỜ, chưa ai nhận.
- −0,25: nhiễu quy trình. 838/1781 commit trong 7 ngày (47 %) là "hộp thư"; 231 commit merge.
- −0,25: `plan_progress` báo "việc kế: M5.4" (MB:17), trong khi M5.4 đang chờ phụ thuộc và Cấp 3 → gợi ý việc kế sai.

**Trục 3 (10 − 6,0):**
- −2,0: M8.2 chế độ Cơ bản chưa bắt đầu. Cờ `simple_mode` chưa tồn tại (`features.state('simple_mode')` → KeyError). Người không chuyên chưa có màn riêng.
- −1,5: M4.7 phần XEM đã gộp nhưng cờ `send_preview_panel` off (`dashboard/send_preview_ui.py:1`), nên người dùng không thấy. Phần GHI (overrides + siết 3 cổng) đang làm (CX23-M47B, nhánh `origin/codex/v31-m47b` commit cuối 23/10 22:16).
- −1,0: M8.3/M8.4 (10 người, màn chính < 2 s) chưa đo (MB:117–118 ⬜).
- −0,5: M4.8 lộ lỗi ở lần dùng thật đầu (xem trục 2). Docstring `dashboard/stage_desk_ui.py:9` vẫn ghi "Không có N12 previs (Đợt 2)" trong khi `ORDER` ở dòng 25 đã có N12/N14/N15/N16.
- −0,5: M8.0 cờ `safe_paid_buttons` BẬT, nhưng `why_state` ghi "chưa thử thật".
- −0,5: Dashboard vẫn do phiên chính / phiên con bấm thay người dùng (#34, hộp thư 24/10 09:46–10:05). Chưa có bằng chứng người không chuyên tự đi hết một luồng.

## 2. Danh sách phát hiện (xếp theo mức)

Không có phát hiện mức CHẶN: không thấy đường gửi job trả phí nào bỏ qua xác nhận. `tests/test_safe_paid_buttons.py` 38 passed, và `py -m core.decisions check` khớp (gồm `check_stage_desk_paid_gate`, `check_no_budget_lock_gate`).

| # | Mức | Trục | Mô tả | Bằng chứng | Đề xuất | Ai làm |
|---|---|---|---|---|---|---|
| 1 | LỚN | 1 | "✅" trong MB nghĩa là "code đã gộp, cờ TẮT/shadow", không phải "cổng nghiệm thu đạt". 37/55 việc ✅ chưa đạt cổng thật, nên con số 73,5 % đánh giá cao tiến độ thật | MB:37–108; mục 3 báo cáo này | Tách trạng thái ✅ thành ✅code / ✅cổng (hoặc thêm cột "cổng thật") trong `tools/plan_progress.py` và trang 🗺 | Codex (devsys) |
| 2 | LỚN | 1 | Chưa mục tiêu đo được nào của V3 §2 được đo trên dữ liệu thật; MT3 (KPI −50 %) không có việc nào đo | V3:23–29, V3 §8:139; grep MB = 0 | Thêm việc "đo 5 KPI gốc trên bản sao #31/#33 (0 USD)" làm cổng trước M5.4 | Phiên chính lập việc → Codex đo |
| 3 | LỚN | 2 | Sổ lỗi không theo kịp: 73 mục OPEN/IN_PROGRESS dưới việc ✅; 65 mục chưa có test (PILOT_A:39) | `devsys/errors.json`; `docs/PILOT_A_KET_QUA_2026-10-23.md:39` | Khi gộp một việc ✅, bắt buộc chuyển mã lỗi liên quan sang FIXED_UNVERIFIED + `tests`, hoặc ghi lý do; thêm check vào `errors.py` | Codex (CX23-M53-MAY đang làm phần test) |
| 4 | LỚN | 2 | Test devsys đỏ trên main từ 23/10 14:39; cùng lúc 77fab4fa (24/10) ghi "cả bộ 8265 passed" — mâu thuẫn, chưa xác minh vì sao | lệnh pytest mục 5; `da6d3a17`; MB:74 | Sửa test chọn radio theo key/label, không theo chỉ số; kiểm cách chạy "cả bộ" có bỏ sót file này không | Codex 1 (CX24-DEVSYS-FIX) |
| 5 | LỚN | 1 | M4.6 ✅ nhưng chưa có dữ liệu benchmark (`data/qc_bench/` không tồn tại) | MB:72; `docs/RA_CLOUD_M46_2026-10-20.md:16` | Hạ về 🔄 hoặc tách M4.6a khung ✅ / M4.6b dữ liệu ⬜ | Phiên chính |
| 6 | LỚN | 2/3 | M4.8 ✅ trước khi kiểm Dashboard thật; lần dùng thật đầu tiên lộ lỗi N5 | MB:74; `5deb6da0`; hộp thư 24/10 09:46 | Luật: việc có màn Dashboard chỉ ✅ khi có 1 lần dùng thật (ảnh chụp hoặc nhật ký ui_step) | Codex (rubric) + phiên chính |
| 7 | LỚN | 1 | M7.7 (khóa từng cờ) chưa có ai làm; khoảng 25 cờ V3.1 off, nên code đã gộp chưa phục vụ sản xuất | MB:108; mục 4 | Nâng CX24-M77-EVID lên ưu tiên 2, trình EP từng cờ theo lô | Phiên chính → EP quyết |
| 8 | LỚN | 3 | Người không chuyên chưa dùng được: M8.2 chưa có cờ, M4.7 XEM off, M8.3/M8.4 chưa đo | mục 4; MB:116–118 | Giữ thứ tự M80C ✅ → M82 pha A; xin EP bật thử `send_preview_panel` trên #34 | Codex 1 + EP quyết bật cờ |
| 9 | NHỎ | 2 | 55/74 quyết định active không `enforced_by`; 3 quyết định tiền kiểm được nhưng chưa có check/pending | `data/decisions.json` | Nối `ep-2210-qf…` với `test_safe_paid_buttons`; ghi `pending` cho `qd3` | Codex |
| 10 | NHỎ | 2 | Golden A/B: 41/158 BOTH_FAIL không so được byte | MB:45; `docs/RA_CX21_GOLDEN7_MAYCHINH_2026-10-22.md` | Phân loại 41 ca (thiếu đầu vào hay lỗi replay), đưa vào sổ lỗi | Codex |
| 11 | NHỎ | 2 | Làn treo: CX22-G1-EP-ROLE ĐANG LÀM khoảng 26 giờ, 0 nhánh; M6.0 🔄 nhưng việc CHỜ | `hop_thu.py bang`; `26c4d09e` | Nhãn ĐANG LÀM quá 12 giờ mà không có commit → tự về CHỜ (hộp thư cảnh báo) | Codex (hop_thu) |
| 12 | NHỎ | 2 | Hộp thư chiếm 47 % commit, làm git log khó rà | git log 7 ngày | Gom tin hộp thư theo lô hoặc nhánh riêng | Phiên chính quyết |
| 13 | NHỎ | 2 | "việc kế: M5.4" trong khi M5.4 đang chờ phụ thuộc | MB:17 | `plan_progress` bỏ qua việc "CHỜ PHỤ THUỘC" khi chọn việc kế | Codex |
| 14 | NHỎ | 2 | Hai nghĩa "M8.4" (an toàn tiền ở KH 21/10 và tối ưu tải ở MB) vẫn PENDING_VERIFICATION | MB:114, MB:118 | EP xác nhận nghĩa đen; đổi tên ở KH 21/10 | EP quyết |
| 15 | NHỎ | 3 | Docstring `stage_desk_ui.py:9` cũ ("không có N12") | `dashboard/stage_desk_ui.py:9,25` | Sửa chữ khi đụng file lần tới | Codex |
| 16 | NHỎ | 1 | Làn cloud-D/E HẾT VIỆC từ 21–22/10 trong khi Codex có 16 việc chờ | `hop_thu.py bang` | Nếu cloud còn hạn mức, giao việc tài liệu (CX23-M6B-DESIGN) | Phiên chính |

## 3. Bảng đợt M0–M8: tiến độ vs cổng nghiệm thu đạt thật

"Cổng (offline)" = tiêu chí cổng MB §3/§4a có bằng chứng test/offline. "Cổng (chạy thật)" = có bằng chứng trên dữ liệu thật hoặc máy chính. Đây là ước lượng theo số tiêu chí, có ghi tiêu chí.

| Đợt | Tiến độ (plan_progress) | Việc ✅ chưa đạt cổng thật | Cổng (offline) | Cổng (chạy thật) | Tiêu chí còn thiếu |
|---|---:|---:|---:|---:|---|
| M0 | 100 % | 0/12 | 3/3 | 3/3 | — (sổ lỗi hợp lệ; quyết định ghi sổ; HEAD/cờ audit M0_BASELINE) |
| M1 | 100 % | 7/9 (M1.1–M1.7 FIXED_UNVERIFIED hoặc cờ off) | 2/4 | 0/4 | 0 job trùng chạy thật; ước tính ≤ 10 % so sổ chi |
| M2 | 87 % | 9/9 (cờ off/shadow) | 1/3 (compat byte qua golden A/B) | 0/3 | correctness #31/#33 khi bật cờ; khóa tay (guard shadow off) |
| M3 | 100 % | 5/5 (cờ off) | 1/3 (hình học offline) | 0/3 | người dùng duyệt map 4/6/8 #31 + tháp #33; gen chứng minh |
| M4 | 90,6 % | 7/7 (M4.1–4.6 off; M4.8 chưa kiểm thật lúc ✅) | 0,5/3 | 0/3 | benchmark có dữ liệu; override có audit (M4.7 GHI) |
| M5 | 54,5 % | 2/2 (cờ off) | 1/5 (pilot A DAT_OFFLINE) | 0/5 | pilot thật B/C; final QC bật; báo cáo chi phí |
| M6 | 26,8 % | 3/3 (shadow, "CHƯA kiểm máy chính") | chưa xác minh (≤ 1/5) | 0/5 | vai chủ mỗi trường; cổng lượt replay #27/#31; VPA; lineage < 0,3 s |
| M7 | 81,2 % | 3/6 (M7.1, M7.3, M7.4) | M7.2 0/144 drift đo máy chính | 0 cờ được khóa | M7.7, M7.8 |
| M8 | 33,3 % | 1/2 (M8.0 "chưa thử thật") | 1/3 (test quét nút tiền xanh) | 0/3 | M8.2 nghiệm thu; 10 người < 2 s |
| **Tổng** | **73,5 %** | **37/55** | | | |

## 4. Kiểm Dashboard theo mốc

- 8501 `_stcore/health` = ok; 8502 (devsys) = ok.
- **Chưa kiểm giao diện thật**: không có Playwright (`py -c "import playwright"` → ModuleNotFoundError), nên không chụp ảnh và thư mục `docs/images/giam_sat_2026-10-24/` không được tạo. Phần dưới là kiểm tĩnh và đọc trạng thái cờ trên máy này.

| Mốc | Màn | Cờ | Trạng thái cờ (`features.state`) | Nút tốn tiền có xác nhận | Người không chuyên |
|---|---|---|---|---|---|
| M4.7 XEM | `dashboard/send_preview_ui.py` | `send_preview_panel` | off → ẩn | chỉ xem, không gửi | chưa (ẩn) |
| M4.7 GHI | — | — | chưa gộp (CX23-M47B) | — | — |
| M4.8 | `dashboard/stage_view_ui.py`, `stage_desk_ui.py` | `stage_view_ui` + `stage_desk_ui` | on (do người dùng chọn) | N11 có xác nhận; `check_stage_desk_paid_gate` ✅ | dùng thật trên #34, do phiên Claude bấm |
| M8.0 | `dashboard/paid_confirm.py`, `paid_batch_preview.py` | `safe_paid_buttons` | on ("chưa thử thật") | `tests/test_safe_paid_buttons.py` 38 passed | có lợi cả hai chế độ |
| M8.1 | tài liệu + mockup `docs/images/m81/` | — | — | — | thiết kế đã duyệt |
| M8.2 | chưa có | `simple_mode` | chưa tồn tại (KeyError) | — | chưa |
| M8.3/M8.4 | — | — | ⬜ | — | chưa đo |

Cờ V3.1 khác đang off: byd_fields, kho_forms_v2, world_map, crew_registry, continuity_validator, repair_router, release_gate, send_estimate, subject_capacity_guard, lean_package, ref_end_frames, video_qc_shadow, continuity_shadow, qc_evidence, stale_code_alarm, diag_merge, budget_notice_d01, horizon_needs_sky, qc_false_alarm_fix, final_black_freeze, ui_step_log. Đang on: poll_claim, pause_before_submit.

## 5. Lệnh đã chạy (0 USD)

- `PYTHONUTF8=1 py tools/plan_progress.py`: bảng trùng MB:4–17.
- `py -m core.decisions check`: "Khớp".
- `py devsys/errors.py check`: "Hợp lệ", 91 mục.
- `pytest tests/test_devsys_pipeline_maps.py tests/test_decisions.py`: **1 failed, 75 passed**.
- `pytest tests/test_safe_paid_buttons.py`: 38 passed.
- `py tools/hop_thu.py bang`; `git log --since=7.days`; `curl` health 8501/8502.
- Script đọc `features.state/why_state`, đếm `enforced_by` và đối chiếu `plan_task` sổ lỗi với ✅ (chỉ đọc).

## 6. RUBRIC ĐỀ XUẤT (để Codex mã hóa vào devsys — CX24-GIAM-SAT)

Mỗi tiêu chí đọc được bằng máy; điểm trục = 10 − tổng trừ (sàn 0). Mỗi lần trừ phải kèm bằng chứng file:dòng, commit hoặc lệnh.

**Trục 1 — Đúng hướng (trọng số 0,40)**
- R1.1 Mỗi việc trong MB §5 phải có trường `muc_tieu` ∈ {MT1…MT5, NEN (hạ tầng)}. Việc thiếu trường này: −0,2/việc (trần −1).
- R1.2 Tỉ lệ ✅ chưa đạt cổng thật = (việc ✅ có chữ "cờ TẮT", "shadow", "CHƯA kiểm", "FIXED_UNVERIFIED" mà không có bằng chứng bật/đo) / tổng ✅. Trừ = 3 × tỉ lệ.
- R1.3 Mỗi mục tiêu V3 §2 chưa có số đo thật: −0,3. Mỗi mục tiêu không có việc đo trong MB: thêm −0,2.
- R1.4 Việc ✅ có từ khóa "khung", "chưa có dữ liệu" hoặc thư mục dữ liệu nêu trong việc không tồn tại: −0,5/việc.
- R1.5 Việc là cổng chuyển code → sản xuất (M7.7, pilot) mà ⬜ và không có ai ĐANG LÀM: −0,5.

**Trục 2 — Lỗi / lỗ hổng (trọng số 0,35)**
- R2.1 Test đỏ trên main (chạy bộ test devsys + decisions + safe_paid_buttons): CHẶN nếu thuộc test tiền, nếu không thì −1/file.
- R2.2 Mã lỗi OPEN/IN_PROGRESS có `plan_task` đã ✅: −0,02/mục (trần −1,5).
- R2.3 Quyết định active thuộc nhóm tiền/cổng (id chứa money|spend|paid|gate|limit) không có `enforced_by` hoặc `pending`: −0,2/mục.
- R2.4 Hộp thư ĐANG LÀM quá 12 giờ mà không có commit trên nhánh tương ứng: −0,25/việc. Việc 🔄 trong MB mà việc giao còn CHỜ: −0,25/việc.
- R2.5 Cờ mới (có trong `features` nhưng không có ở baseline) không có test cờ tắt = byte cũ: −0,5/cờ.
- R2.6 Quét nút/đường gửi trả phí không qua `paid_button`/`spend_gate`: CHẶN.
- R2.7 Golden: ca BOTH_FAIL > 10 % tổng: −0,5.

**Trục 3 — Dashboard theo mốc (trọng số 0,25)**
- R3.1 Mỗi việc có phần Dashboard (danh sách: M4.7, M4.8, M6.10, M8.0–M8.4): màn chưa có −1; có nhưng cờ off và chưa từng bật thử −0,75; ✅ khi chưa có lần dùng thật (ui_step hoặc ảnh chụp) −0,5.
- R3.2 `_stcore/health` 8501 khác ok: CHẶN đo giao diện (chỉ kiểm tĩnh và ghi rõ).
- R3.3 Có Playwright: chụp ≤ 4 màn chính. Không có: ghi "chưa kiểm giao diện thật" (không trừ điểm, nhưng hạ độ tin cậy).
- R3.4 Người không chuyên: không có chế độ Cơ bản (cờ `simple_mode`) −2; chưa đo M8.3 −1.

**Điểm chung** = 0,40 × T1 + 0,35 × T2 + 0,25 × T3. Bất kỳ CHẶN nào → ghi "CHẶN" cạnh điểm chung, không làm tròn che đi.
**Kích hoạt:** mỗi khi một đợt đổi % trong `plan_progress` hoặc có việc chuyển ✅. Hiển thị trên 3 trang devsys (`devsys/app.py` page_plan :958, page_plan_map :1033, page_pipeline_maps :1064) dưới dạng cột "cổng thật".

## 7. Chưa kiểm được và vì sao

- **Giao diện thật 8501**: không có Playwright; không bấm, không chụp. Chỉ có health ok và kiểm tĩnh code `dashboard/`.
- **Trạng thái cờ trong tiến trình Dashboard đang chạy**: chỉ đọc `features.state` ở tiến trình mới. Nếu server chạy với biến môi trường `FEATURE_*` khác thì có thể lệch (chưa xác minh).
- **Cả bộ test**: theo đề bài chỉ chạy 3 file. Chưa xác minh vì sao báo cáo "cả bộ 8265 passed" (77fab4fa) lại không thấy test devsys đỏ.
- **Dữ liệu sản xuất / sổ chi thật**: không đọc CSDL, nên MT1/MT2 không đo được ở đây (chưa xác minh).
- **Nhánh và worktree Codex local** (`.codex-wt/`), các làn cloud: chỉ thấy qua nhánh remote và hộp thư.
- **Các báo cáo RA_* cloud 20–22/10**: chỉ đọc chọn lọc (M46, DP8, M63_FIX, M63_FIX2). Chất lượng từng lần rà chưa được chấm lại.
