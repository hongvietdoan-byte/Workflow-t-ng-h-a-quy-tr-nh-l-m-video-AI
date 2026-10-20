# V3.1 M4.6 — Đặc tả bộ benchmark QC theo mã lỗi (20/10/2026)

> **Cấp 1 — CHỈ TÀI LIỆU, 0 USD.** Việc C-M46 (cloud-B). Nền `origin/main` = `4293cba8`. Theo D07 `v31-d07-qc-shadow-guarded-2026-10-20` (≥ 20 lỗi + 20
> đạt MỖI nhóm chỉ là **sàng lọc**, không tự cấp BLOCK; ngữ nghĩa / góc máy / continuity / chuyển động → REVIEW; bật chặn production duyệt riêng) +
> D08 `v31-d08-fixture-capture-readonly-2026-10-20` (chụp dữ liệu thật CHỈ ĐỌC trên máy chính / snapshot). Mã QC theo thiết kế M4.1
> `docs/V3_1_M4_1_THIET_KE_BANG_CHUNG_QC_2026-10-20.md` §3 (25 mã) + §7; sổ lỗi `devsys/errors.json` (86 mục); bộ đo vàng cũ `core/qc_golden.py`.

## 0. Tóm tắt
Bộ đo vàng hiện có (`qc_golden`) đo theo **kết luận khung** (chặn / nhỏ / đạt, 6 nhóm Sheet), không theo mã lỗi, và chỉ có ảnh. M4.6 = bộ **theo `qc_code`**:
mỗi mã một danh sách artifact có nhãn người dùng (LỖI / ĐẠT / KHÔNG XÉT), tách bộ phát triển và bộ độc lập, đo báo nhầm / bỏ sót / hiệu chuẩn độ tin
cậy, kết quả ghi `confidence_calibration` của mã (M4.1). **Cloud không có `data/`** (ảnh, clip, CSDL) → mọi ca thật do máy chính trích (D08); cloud chỉ
viết đặc tả + công cụ đọc. Ca **tổng hợp** (sinh bằng ffmpeg / chuỗi gói, 0 USD) được phép cho mã tất định, phải đánh dấu `synthetic=true` và không
tính vào ngưỡng BLOCK quá 50 % mẫu.

## 1. Danh sách mã và nguồn ca
Cột "Nguồn ca thật": tài liệu / sổ lỗi chỉ ra ca; **MC** = cần máy chính trích (artifact trong `data/projects/<pid>/`, job trong CSDL). "Đủ 20+20?" =
ước tính từ tài liệu hiện có — "thiếu" nghĩa là phải chờ dự án kế hoặc dùng ca tổng hợp (chỉ mã tất định).

| `qc_code` | Loại | Nguồn ca thật (tài liệu → ca) | Cần MC | Ca tổng hợp được? | Đủ 20+20? |
|---|---|---|---|---|---|
| QC-L1-IDENTITY_DRIFT | VLM | `qc_golden.independent_set` nhóm "Nhân vật" (134 khung, nhãn Sheet 01-10) + `docs/qc_agent_2026-09-27/labels_v2.json` (#8, bộ PHÁT TRIỂN); #33 B1 (ảnh mẫu thân dài) | có | không | có thể (nhãn cũ cần ánh xạ lại mã) |
| QC-L2-FORM_OUTFIT | VLM | P31-G37 (shot 28 Kelly áo vàng mất dạng bóng mờ), P31-G27 (gói chỉ 1 ảnh mặt), P31-G38 (shot 35/36 tường keo) | có | không | thiếu lỗi (≈ 5) |
| QC-L3-EXTRA_PEOPLE | VLM | P31-G50 (1017/1015: 17 Sứ giả), P33-B8 (lộ con mèo — gần L3) | có | không | thiếu |
| QC-L4-POSE_ACTION | VLM | P31-G19 (khung đầu vẽ trạng thái CUỐI), P31-G43, P31-G44 | có | không | thiếu |
| QC-L6-SIZE_MISMATCH | đo mặt + ý | P33-A5 (S2 qua vai đo nhầm = **ca ĐẠT báo nhầm** bắt buộc), P31-G28, P33-B9 | có | một phần (khung cắt sẵn) | có thể |
| QC-L7-PROP_MISSING | VLM | P31-G7 (POV bỏ ảnh súng), P31-G38, V21-R3 (`vat` chuỗi → crash = QC-SYS, không phải L7) | có | không | thiếu |
| QC-L9-HORIZON_MISMATCH | đo | P31-G20 (ảnh không/ít trời → **ca ĐẠT báo nhầm**), P31-G40 (ảnh 1000), P33-A10 (high 30°) | có | có (plate render cố định) | có thể |
| QC-L11-PLACE_MISMATCH | một phần | P31-G26 (nhìn về tháp nhưng máy quay khác), P31-G40, P33-B5 | có | không | thiếu |
| QC-L13-CONTINUITY | VLM | P31-G52 (`scripts_19-10/qc_sequence/result.json`, chuỗi 39 clip), P31-G41–G46 (xác 26–29, keo + địch 34–36) | có | không | lỗi: có (39 clip); đạt: có |
| QC-L14-ARTIFACT | VLM | `independent_set` nhóm "Kỹ thuật" | có | không | có thể |
| QC-V1-DRIFT | đo | `clip_measure.look_drift` trên clip #31/#33; P33-B9 | có | không | có thể |
| QC-V2-JERK_FREEZE | đo | P31-G51 (12 clip nháp 19/10: 13 đơ 6 s, 16 địch không phản ứng) | có | có (clip giật / đứng ffmpeg) | lỗi thiếu → bổ sung tổng hợp |
| QC-V2-STILL_OVER_1_5S | đo (mới M4.2) | P31-G51 | có | **có** (`tpad`/`freezeframe`) | có (tổng hợp ≤ 50 %) |
| QC-V3-LIP_SYNC | VLM + đo | P31-G10 / G16 / G53 (lời DẪN bị coi là thoại → **ca ĐẠT báo nhầm**), clip có thoại #31/#33 | có | không | thiếu lỗi |
| QC-V4-MOTION_VS_BYD | VLM | P31-G11 (motion tả cảnh khác khung đầu), P33-B10 ("cats") | có | không | thiếu |
| QC-PKG-VI_TEXT | tất định | P33-B7 (motion còn chữ Việt), P31-G12 (địa danh có dấu) — gói đã lưu `sent_package` | có (gói) | **có** (chuỗi) | có |
| QC-PKG-FORM_PICTURE_MISSING | tất định | P31-G27, sổ `video-form-picture-2026-10-19` | có (gói) | **có** | có |
| QC-PKG-PROMPT_TOO_LONG | tất định | P31-G13 (gói nhóm > 5000), P31-G54 (3256 > 3192 — ca ranh giới) | có (gói) | **có** | có |
| QC-A4-LENGTH_MISMATCH | tất định | `final_qc.check_length` trên bản dựng #24/#27/#31 (`outputs`) | có | **có** | có |
| QC-A2-PEAK_OVER | tất định | `final_qc.check_peak` trên bản dựng | có | **có** (âm chuẩn hóa −0,5 / −1,5 dBTP) | có |
| QC-A2-SILENT_GAP | tất định (ý đồ không) | `final_qc.check_silence`, `rough_cut` 248 | có | có | có (REVIEW mãi — §4) |
| QC-A4-BLACK_FRAME / FREEZE_FRAME | tất định (mới M4.4) | bản dựng có chuyển cảnh đen | có | **có** (`color=black`) | có |
| QC-A4-DELIVERY_RES | tất định | P33-B11 (bản ghép 1080×2730), `final_cut.require_delivery_resolution` | có | **có** | có |
| QC-CR-INPUT_MISSING | lỗi của QC | P33-A6 (#877 shot 6 "không có video tham chiếu") | có | có | đo `partial` đúng, không đo P/R |
| QC-SYS-QC_CRASH | lỗi của QC | V21-R3 (`qc_observe` 62–64) | không (fixture) | **có** | đo 0 crash, không đo P/R |

**Ca báo nhầm đã biết là bắt buộc** trong bộ ĐẠT của mã tương ứng (regression M4.1 §6): A5 → L6, G20 → L9, G10/G16/G53 → V3, A6 → CR, V21-R3 → SYS.
Dự án nguồn: #24, #27, #31, #33 (+ #8 / dòng Sheet 01-10 cho ảnh) và dự án kế; mỗi mã lấy từ **≥ 2 dự án**, không quá 60 % mẫu từ một dự án.

## 2. Bản ghi ca (`data/qc_bench/<qc_code>.jsonl`, máy chính; cloud chỉ có schema + fixture tổng hợp)
`{case_id, qc_code, artifact_kind: image|clip|package|render, artifact_sha (64 hex, khử trùng), project_id, scene_idx, job_id, source_ref
("docs/DANH_GIA_P31…:dòng" | "errors.json:P31-G51"), label: LOI|DAT|KHONG_XET, label_by, label_at, label_note, split: dev|independent,
synthetic: bool, capture: {commit_sha, flags_snapshot, schema_version, provider/model, prompt_sha} (D08)}`.
Ảnh / clip KHÔNG commit vào repo; chỉ đường dẫn tương đối + sha. Cùng `artifact_sha` không vào hai split.

## 3. Quy trình gán nhãn (người dùng xác nhận)
1. **Trích (MC, chỉ đọc, 0 USD):** công cụ `tools/qc_bench_cases.py --project N --code QC-…` (đề xuất, chỉ đọc CSDL + thư mục; không gọi model) liệt kê
   ứng viên từ: job bị từ chối kèm `reject_reason` / `mistakes`, `qc_results` dưới sàn, mục sổ lỗi có `job_ids`, danh sách ca trong `DANH_GIA_*`.
   Snapshot CSDL trước khi đọc (máy đang chạy job → ưu tiên snapshot, D08).
2. **Nhãn đề xuất:** máy ghi nhãn GỢI Ý (từ sổ lỗi / reject_reason) — chỉ là gợi ý, `label_by="goi_y"`, không vào số đo.
3. **Người dùng xác nhận** trên Google Sheet mẫu "Gắn nhãn bộ đo QC" (cùng định dạng `qc_golden.independent_set`: cột mã QC, ảnh/clip, LỖI/ĐẠT/KHÔNG XÉT,
   ghi chú); chỉ dòng người dùng điền mới thành `label_by=<email>`. Mỗi mã: tối thiểu 20 LỖI + 20 ĐẠT đã xác nhận.
4. **Tách split trước khi chỉnh luật:** 50 % dev (được nhìn khi chỉnh ngưỡng / prompt) / 50 % independent (khóa, chỉ dùng kết luận) — theo dự án nếu đủ.
5. Bất đồng (người dùng đổi nhãn) → ghi lịch sử nhãn, không xóa; nhãn cũ của `labels_v2` / Sheet 01-10 được **ánh xạ** sang mã (bảng ánh xạ nhóm Sheet
   → `qc_code` ghi kèm, ca mơ hồ = KHONG_XET).

## 4. Chỉ số (theo `qc_code`, và theo đường QC Q1–Q8 của M4.1 §1)
- Precision, recall, **báo nhầm / 100 artifact ĐẠT**, **bỏ sót / 100 artifact LỖI**, tỉ lệ "không chắc" (doubt/REVIEW) — như `qc_golden.score` nhưng
  theo mã; doubt KHÔNG tính là bắt được (giữ luật S7.1).
- Khoảng tin cậy Wilson 95 % cho precision và recall (20 mẫu: 20/20 → cận dưới ≈ 0,84 — vì vậy 20+20 chỉ là sàng lọc).
- **Hiệu chuẩn độ tin cậy** (mã có `confidence`): bảng tin cậy 5 ngăn + ECE; ghi `{benchmark_id, precision, recall, n_pos, n_neg, ece, at}` vào
  `confidence_calibration` (M4.1 §2). Mã thiếu mẫu → `null` → không được BLOCK.
- VLM: ghi model + `prompt_sha` + provider (Claude qua `claude_cli` = 0 USD API theo D02 / M0.11); chi phí khác ước tính trước qua `spend_gate`.
- Báo cáo `docs/BENCHMARK_QC_<ngày>.md`: mỗi mã một dòng (n LỖI / n ĐẠT / P / R / báo nhầm / bỏ sót / ECE / trạng thái: CHUA_DU_MAU | SANG_LOC_DAT |
  DE_XUAT_BLOCK).

## 5. Ngưỡng xét BLOCK (chỉ luật kỹ thuật tất định)
Mã chỉ được **ĐỀ XUẤT** BLOCK khi đủ CẢ: (a) cột "Loại" = tất định (code, không model) và `evidence_type ∈ {metadata, segment}`; (b) bộ independent ≥ 20
LỖI + ≥ 60 ĐẠT người xác nhận (tổng hợp ≤ 50 %); (c) precision ≥ 0,95 VÀ cận dưới Wilson ≥ 0,85; (d) 0 báo nhầm trên các ca báo nhầm đã biết của mã;
(e) recall ≥ 0,90. Đề xuất → người dùng duyệt **từng mã** (Cấp 3) → mã vào danh sách BLOCK của `qc_evidence` (M4.1 §4). Ứng viên: QC-PKG-* (đã chặn
trước trả tiền — benchmark xác nhận), QC-A2-PEAK_OVER, QC-A4-LENGTH_MISMATCH (> 20 %), QC-A4-DELIVERY_RES, QC-A4-BLACK_FRAME. **Không bao giờ đề
xuất:** mọi mã VLM, QC-L13, QC-V*, QC-A2-SILENT_GAP (im lặng có thể là ý đồ), QC-CR / QC-SYS — dù số đo đẹp (D07). Mã VLM đạt sàng lọc chỉ được nâng
từ "không tin" lên REVIEW có điểm tin cậy hiển thị.

## 6. Kiểm của bộ benchmark (test, cloud làm được)
`tests/test_qc_bench_schema.py`: mọi bản ghi đúng schema §2, `qc_code` ∈ bảng M4.1, `artifact_sha` không trùng giữa split, ca báo nhầm đã biết có mặt
trong bộ ĐẠT của mã, `synthetic` ≤ 50 % khi trạng thái DE_XUAT_BLOCK; `tests/test_qc_bench_metrics.py`: P/R/Wilson/ECE trên bộ nhỏ cố định (đối chiếu
`qc_golden.score` cho cùng dữ liệu). Fixture tổng hợp (gói chữ Việt, gói quá dài, âm quá đỉnh, khung đen) sinh trong test, không lưu file lớn.

## 7. Việc cần máy chính / người dùng
1. MC trích ứng viên cho 25 mã từ #24/#27/#31/#33 (chỉ đọc, snapshot CSDL) + đường dẫn `scripts_19-10/qc_sequence/result.json` (G52).
2. Người dùng gán nhãn trên Sheet — ước lượng ≥ 25 × 40 = 1 000 dòng; ưu tiên 8 mã tất định (≈ 320 dòng) trước vì chỉ chúng có thể thành BLOCK.
3. Chốt ngưỡng §5 (0,95 / 0,85 / 0,90, 60 ĐẠT) — M4.1 §9 việc mở 1.
4. Mã "thiếu" (L2, L3, L4, L7, L11, V3, V4) chờ dự án kế; đến lúc đó trạng thái CHUA_DU_MAU, giữ REVIEW.
