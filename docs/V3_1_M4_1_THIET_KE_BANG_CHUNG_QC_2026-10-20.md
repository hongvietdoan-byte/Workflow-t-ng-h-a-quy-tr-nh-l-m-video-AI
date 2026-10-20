# V3.1 M4.1 — Thiết kế schema bằng chứng QC + mã lỗi thống nhất (20/10/2026)

> **Cấp 1 — CHỈ TÀI LIỆU, 0 USD, không sửa code.** Việc C-M41 (cloud-B). Nền `origin/main` = `2c18a3b1`.
> Căn cứ: `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md` §2 "**Bằng chứng QC:**" (dòng 66–68), §4 D07, §4a dòng "M4.x QC (D07)", M4.1–M4.7;
> sổ `v31-d07-qc-shadow-guarded-2026-10-20` (QC Shadow → Guarded; chỉ lỗi kỹ thuật có bằng chứng xác định được xét chặn sau nghiệm thu; ngữ nghĩa /
> góc máy / continuity / chuyển động không chắc → REVIEW; 20 + 20 chỉ là sàng lọc, không tự cấp BLOCK; override có người / lý do / bằng chứng / audit;
> bật chặn production duyệt riêng), `qc-team-off-2026-10-14`; V3 Phụ lục A.6–A.7 (mã lỗi sửa chọn lọc); `devsys/error_types.json` (loại lỗi
> L1–L15, V1–V4, A1–A4, R1); sổ lỗi `devsys/errors.json` (nhánh `cloud/v31-m04-m05`, C-M04-05).
> Triển khai M4.1 = Cấp 2 (gói M4); bật QC chặn / tự sửa trên production = Cấp 3.

## 0. Tóm tắt
- Hôm nay có **9 đường QC** ghi kết quả theo **5 dạng khác nhau** (điểm số `qc_results`, chuỗi `issues` trong ghi chú, diag, `trainee_log`, JSON riêng
  từng module). Không có `qc_run_id`, `qc_version`, `artifact_sha`, độ tin cậy hiệu chuẩn, hay liên kết mã sổ lỗi → không đo được báo nhầm theo mã,
  không biết finding nào thuộc lần chạy QC nào trên tệp nào.
- Thiết kế: một bảng **`qc_findings`** (bằng chứng, mỗi dòng một phát hiện) + **`qc_runs`** (mỗi lần chạy) + **mã lỗi QC thống nhất** `QC-<loại>-<TÊN>`
  ánh xạ (a) loại lỗi `devsys/error_types.json`, (b) mã sổ lỗi `P31-Gn` / `P33-An`, (c) mã sửa chọn lọc V3 A.7. Mức chỉ **BLOCK** cho luật kỹ thuật
  tất định ĐÃ qua benchmark + người duyệt; mọi thứ còn lại **REVIEW** (hoặc INFO).

## 1. AS-IS — các đường QC và chỗ ghi (file:hàm)
| # | Đường QC | file:hàm | Ai phán | Ghi vào | Tất định? |
|---|---|---|---|---|---|
| Q1 | QC ảnh theo tiêu chí (điểm 0–1) | `core/llm_runner.py:run_qc` (924), `run_qc_batch` (965); `core/autoqc.py` (nền) → `Pipeline.apply_qc` (`core/pipeline.py:507`) | Claude | `qc_results(job_id, criterion, score, threshold_at_time, auto_decision)` + ghi chú job (`issues`) | không |
| Q2 | QC clip theo tiêu chí | `core/claude_tasks.py:qc_video` (156), `qc_video_batch` (370) → `apply_qc` | Claude + số đo `clip_measure` | như Q1 + `measured` | không |
| Q3 | Số đo clip tầng 0 | `core/clip_measure.py` (`look_drift` 119, `jerks` 165: cuts/jerks/freezes, `lips_still`) | code | đưa vào Q2 làm bằng chứng ("Nothing here blocks on its own") | có (số đo), ý nghĩa không |
| Q4 | QC quan sát enum Đ14 | `core/qc_observe.py:compile_checks` (13), `judge` (106: `observations[{id, source, seen ∈ thay/khong_thay/khong_chac, region, evidence}]`), `hold` (199) | Claude khai, code quyết | `criteria` điểm 0/1 + `yellow` + `issues` → `apply_qc` | phần quyết: có |
| Q5 | QC theo cảnh | `core/qc_scene.py` (CHECKS identity/place/action/framing/continuity/artifacts; VERDICTS pass/fix/doubt; CAUSES prompt/reference/model/plan/none) | Claude | JSON cảnh + diag | không |
| Q6 | Tổ QC (C1 + luật) | `core/qc_team.py:review_frame`, `core/qc_spec.py:compile_frame` (93), `core/qc_measure.py` (faces, gaze, sky), `core/qc_rules.py:frame_verdict` (135; `SIDE_CAN_BLOCK = False`) | Claude + code luật | `trainee_log` (cờ `qc_team` TẮT, học việc) | một phần |
| Q7 | QC agent | `core/qc_agent.py` (cờ `qc_agent`, trần tiền cảnh) | Claude agent | verdicts JSON (`description`, `evidence`, `fix_en`) | không |
| Q8 | Logic chuỗi clip | `core/sequence_logic.py` (cờ `qc_sequence_logic`) | Claude | JSON nhóm + diag | không |
| Q9 | Cổng / kiểm kỹ thuật | `core/video_pregen.py` (ĐỎ trước khi trả tiền), `core/framing_guard.py`, `core/camera_match_qc.py` (horizon/cỡ mặt/mắt), `core/plate_layout_qc.py`, `core/final_qc.py` (`block`/`warn`: độ dài ±10/20 %, đỉnh > −1 dBTP, im lặng −45 dB ≥ 2,5 s, phụ đề), `core/final_cut.require_delivery_resolution` (135) | code | diag / job hold / chặn bàn giao | **có** |
| Q10 | Tổ rà soát tác động | `core/change_review.py` (luật code `change_audit` + Claude), `change_findings` | code + Claude | `change_findings` (mục "do" chặn gen) | một phần |
Bộ đo vàng hiện có: `core/qc_golden.py` (`dev_set` #8, `independent_set` 134 khung nhãn người dùng, `score`), `tests/golden/cases/` (10 ca).

## 2. Schema bằng chứng (TO-BE)
Bảng (migration additive — Cấp 3 khi chạy trên CSDL thật; shadow có thể ghi JSON vào `trainee_log`/tệp trước):
```
qc_runs(qc_run_id TEXT PK, project_id, scope ('image'|'clip'|'scene'|'sequence'|'final'|'pregen'), job_ids JSON, qc_path ('Q1'..'Q10'),
        qc_version TEXT, model TEXT NULL, provider TEXT NULL, prompt_sha TEXT NULL, rules_version TEXT, mode ('shadow'|'guarded'),
        started_at, finished_at, cost_usd REAL, status ('ok'|'failed'|'partial'), error TEXT NULL)
qc_findings(id PK, qc_run_id FK, artifact_id TEXT, artifact_sha TEXT, error_type TEXT, qc_code TEXT, registry_ids JSON,
        severity ('BLOCK'|'REVIEW'|'INFO'), evidence_type ('metadata'|'frame'|'segment'|'vlm'), evidence JSON,
        confidence REAL NULL, confidence_calibration JSON NULL, intent_exception JSON NULL, actionability JSON,
        source_refs JSON, status ('open'|'overridden'|'resolved'|'false_positive'), created_at)
qc_overrides → bảng `overrides` M4.7 (D09: CSDL), liên kết finding_id + người + lý do + revision
```
| Trường | Nghĩa / ràng buộc |
|---|---|
| `artifact_id` | `job:<id>` / `end_frame:<id>` / `cut:<project>:<rev>` / `package:<job>` (gói trước gửi) |
| `artifact_sha` | sha256 của tệp được chấm (ảnh / clip / bản dựng; gói = sha `sent_package`) — finding không áp cho bản khác |
| `error_type` | id trong `devsys/error_types.json` (L1…L15, V1…V4, A1…A4, R1) — một nguồn loại lỗi |
| `qc_code` | mã QC thống nhất (mục 3), ổn định qua phiên bản |
| `registry_ids` | mã sổ lỗi `devsys/errors.json` mà finding là một **lần xuất hiện** (D09: lỗi gốc ≠ lần xuất hiện) |
| `evidence_type` + `evidence` | `metadata` (ffprobe, số đo: `{"metric":"peak_dbtp","value":-0.4,"limit":-1.0}`), `frame` (`{"t":2.4,"region":[x0,y0,x1,y1],"crop_sha":…}`), `segment` (`{"t0","t1"}`), `vlm` (`{"observation_id","seen","evidence_text"}` — Q4 dạng chuẩn) |
| `confidence` + `confidence_calibration` | điểm thô + `{benchmark_id, precision, recall, n_pos, n_neg, at}` của **mã này**; thiếu hiệu chuẩn → `null` và không được BLOCK |
| `intent_exception` | `{byd_ngoai_le_id, ly_do}` (BYĐ `ngoai_le`, `video_qc_context.soft_criteria`) — finding vẫn ghi, severity hạ INFO |
| `actionability` | `{layer: byd|asset|image|video|audio|edit, repair_code (V3 A.7), auto_ok: false, fix_en}` — đầu vào repair router M5.1 |
| `source_refs` | file:hàm luật / prompt + version (vd `core/final_qc.py:PEAK_BLOCK@<sha>`) |

## 3. Mã lỗi QC thống nhất ↔ loại lỗi ↔ sổ lỗi
| `qc_code` | error_type | Đường hiện có | Tất định | Mức tối đa | Mã sổ lỗi liên quan | Sửa (A.7) |
|---|---|---|---|---|---|---|
| QC-L1-IDENTITY_DRIFT | L1 | Q1 `character`, Q2 `identity`, Q6 C1 | không | REVIEW | — | CHARACTER_IDENTITY_DRIFT |
| QC-L2-FORM_OUTFIT | L2 | Q4, Q6, `identity_declare.check` (A18, `CHAN_DO=False`) | không | REVIEW | P31-G37, P31-G27 | CHARACTER_IDENTITY_DRIFT |
| QC-L3-EXTRA_PEOPLE | L3 | Q6 `count` | không | REVIEW | — | — |
| QC-L4-POSE_ACTION | L4 | Q4, Q5 `action` | không | REVIEW | P31-G19 | ACTION_NOT_COMPLETED |
| QC-L6-SIZE_MISMATCH | L8/L6 | Q1 `composition`, `framing_guard`, qc_scene `measured_size` | đo mặt: có; ý nghĩa: không | REVIEW | **P33-A5** (qua vai đo nhầm), P31-G28 | — |
| QC-L7-PROP_MISSING | L7 | Q4 `set_match`/vat (sau M1.1), Q1 `set_match` | không | REVIEW | V21-R3, P31-G38, P31-G7 | PROP_MISSING |
| QC-L9-HORIZON_MISMATCH | L9 | `camera_match_qc` horizon | đo: có | REVIEW (WARN khi nền không trời) | **P31-G20** | — |
| QC-L11-PLACE_MISMATCH | L11 | Q5 `place`, `plate_layout_qc` | một phần | REVIEW | P31-G40, P31-G26 | — |
| QC-L13-CONTINUITY | L13 | Q5 `continuity`, Q8 | không | REVIEW | **P31-G52**, P31-G42, P31-G41–G45 | CONTINUITY_CONFLICT |
| QC-L14-ARTIFACT | L14 | Q1 `hands_face`, Q2 `artifacts` | không | REVIEW | — | — |
| QC-V1-DRIFT | V1 | `clip_measure.look_drift` | đo: có | REVIEW | — | — |
| QC-V2-JERK_FREEZE | V2 | `clip_measure.jerks` | đo: có | REVIEW | **P31-G51** | — |
| QC-V2-STILL_OVER_1_5S | V2 | (mới, M4.2) | đo: có | REVIEW | P31-G51 | — |
| QC-V3-LIP_SYNC | V3 | `clip_measure` lips, lipsync | không | REVIEW | P31-G16, P31-G10 | AUDIO_SYNC_ERROR |
| QC-V4-MOTION_VS_BYD | V4 | Q2 `motion_match`, `video_pregen._check_motion` | không | REVIEW | P31-G11 | ACTION_NOT_COMPLETED |
| QC-PKG-VI_TEXT | — (gói) | `video_pregen` (prompt còn chữ Việt) | **có** | BLOCK (đã chặn trước trả tiền) | P33-B7, P31-G12 | — |
| QC-PKG-FORM_PICTURE_MISSING | — (gói) | `runner._ref_lint` ĐỎ (sổ `video-form-picture-2026-10-19`) | **có** | BLOCK | P31-G27 | — |
| QC-PKG-PROMPT_TOO_LONG | — (gói) | trần ký tự `video_rules` | **có** | BLOCK (gói không hợp lệ với model) | P31-G13, P31-G54 | — |
| QC-A4-LENGTH_MISMATCH | A4 | `final_qc` LENGTH_WARN/BLOCK | **có** | BLOCK (> 20 %) / REVIEW | — | ENCODE_ERROR |
| QC-A2-PEAK_OVER | A2 | `final_qc` PEAK_BLOCK −1 dBTP | **có** | BLOCK | — | ENCODE_ERROR |
| QC-A2-SILENT_GAP | A2 | `final_qc` SILENT_DB/SILENT_S | **có** | REVIEW (im lặng có thể là ý đồ) | — | AUDIO_SYNC_ERROR |
| QC-A4-BLACK_FRAME / FREEZE_FRAME | A4 | (mới, M4.4 blackdetect/freezedetect) | **có** | BLOCK sau benchmark | — | ENCODE_ERROR |
| QC-A4-DELIVERY_RES | A4 | `final_cut.require_delivery_resolution` | **có** | BLOCK | — | ENCODE_ERROR |
| QC-CR-INPUT_MISSING | — | `change_review` đề rà thiếu dữ liệu | — | (lỗi của QC, không phải của shot) → `qc_runs.status=partial` | **P33-A6** | — |
| QC-SYS-QC_CRASH | — | mọi đường QC ném lỗi | — | không finding; `qc_runs.status=failed` + diag | V21-R3 | — |
Mã mới thêm vào bảng này + `devsys/errors.json` cùng commit; test hợp đồng: mọi `qc_code` có `error_type` hợp lệ, mọi `registry_ids` có trong sổ.

## 4. Luật mức (D07)
1. **BLOCK chỉ khi cả 4:** luật **tất định** (code, không model) · có `evidence_type` ∈ {metadata, segment} đo lại được · benchmark M4.6 của **mã đó** đạt
   (precision ≥ 0,95 trên ≥ 20 lỗi + ≥ 20 đạt — chỉ là sàng lọc tối thiểu, D07) · **người dùng duyệt** bật chặn mã đó (ghi sổ quyết định, Cấp 3).
2. Mọi mã từ model (VLM) hoặc lỗi ngữ nghĩa / góc máy / continuity / chuyển động → **REVIEW** (người xem), không tự BLOCK, không tự sửa (D07).
3. `intent_exception` khớp → INFO (vẫn lưu để đo).
4. `mode = shadow` (mặc định): mọi finding ghi, KHÔNG đổi `apply_qc` / không giữ job / không gen lại — đối chiếu với quyết định người để đo báo nhầm.
   `guarded`: BLOCK giữ job / chặn bàn giao như các cổng hiện có; REVIEW vào 📥 "Cần bạn quyết".
5. Override (M4.7): người + lý do + bằng chứng + revision; finding chuyển `overridden`, không xóa.
Ngoại lệ đã có giữ nguyên: `video_pregen` ĐỎ và `_ref_lint` ĐỎ hiện đã chặn trước khi trả tiền — xếp vào BLOCK (đã được người dùng chấp nhận theo quyết
định riêng), chỉ chuẩn hóa cách ghi.

## 5. Đường QC hiện có → schema mới (adapter, không đổi hành vi khi cờ TẮT)
| Đường | Chuyển đổi |
|---|---|
| Q1/Q2 `apply_qc` | mỗi tiêu chí < ngưỡng / < sàn → finding (`qc_code` theo bảng 3, `evidence_type=vlm`, `confidence=score`, `confidence_calibration=null`); `qc_results` giữ nguyên |
| Q3 `clip_measure` | mỗi `flag` → finding `metadata`/`segment` (t0/t1 từ `cuts/freezes`) |
| Q4 `qc_observe.judge` | mỗi observation `seen ∉ {expected, khong_chac}` → finding `vlm` (`evidence` = `region` + `evidence`); `khong_chac` → REVIEW |
| Q5/Q7/Q8 | verdict `fix`/`doubt` → finding REVIEW; `CAUSES` → `actionability.layer` |
| Q6 `qc_rules.frame_verdict` | giữ ở `trainee_log` + finding với `mode=shadow` |
| Q9 code | mỗi lần chặn / cảnh báo → finding tất định (`metadata`) + `source_refs` hằng số luật |
| Q10 change_review | `change_findings` giữ; thêm `registry_ids` |
Cờ: `qc_evidence` (TẮT) — bật thì ghi `qc_runs` / `qc_findings` song song (shadow); TẮT = không ghi gì mới (byte giống).
`qc_version` = `<module>@<git sha ngắn>+<rules_version>`; `prompt_sha` cho đường Claude.

## 6. Test plan
| Bộ | Nội dung |
|---|---|
| `tests/test_qc_evidence_schema.py` | validate finding: enum severity/evidence_type, `artifact_sha` 64 hex, `error_type` ∈ error_types.json, `registry_ids` ∈ errors.json, BLOCK bắt buộc `evidence_type ∈ {metadata, segment}` + calibration + mã nằm trong danh sách đã duyệt — thiếu → đỏ |
| `tests/test_qc_codes.py` | bảng mục 3: mỗi `qc_code` duy nhất, có error_type, mã sổ tồn tại; không mã VLM nào có `max = BLOCK` |
| `tests/test_qc_evidence_adapters.py` | mỗi Q1–Q10 với dữ liệu giả → finding đúng mã; cờ `qc_evidence` TẮT → `qc_results`/diag/`trainee_log` giống byte, 0 dòng mới |
| Báo nhầm đã biết (regression) | A5 (#33 S2 qua vai → không phải QC-L6 BLOCK; REVIEW + intent), A6 (#33 shot 6 → `qc_runs.partial`, không finding), G20 (nền không trời → không QC-L9), G16 (lời dẫn không "đang nói"), V21-R3 (`vat` chuỗi không crash) |
| Shadow không đổi hành vi | `apply_qc` cùng kết quả approved/rejected/escalated khi `qc_evidence` bật ở shadow |

## 7. Benchmark M4.6 (sàng lọc theo mã, không tự cấp BLOCK)
- Mỗi `qc_code`: ≥ 20 artifact LỖI + ≥ 20 artifact ĐẠT, nhãn người dùng (mẫu Google Sheet của `qc_golden.independent_set`), lấy từ dự án khác nhau
  (#24, #27, #31, #33 + dự án kế), ghi `artifact_sha` để không trùng; tách bộ phát triển (chỉnh luật) và bộ độc lập (kết luận) như `qc_golden`.
- Đo: precision, recall, báo nhầm/100 artifact, theo `qc_code` và theo đường QC; với VLM ghi model + prompt_sha; chi phí chạy benchmark ước tính trước qua
  `spend_gate` (Claude qua `claude_cli` = 0 USD API theo D02 / M0.11).
- Kết quả → `confidence_calibration` của mã; chỉ mã tất định đạt ngưỡng mới được ĐỀ XUẤT BLOCK, người dùng duyệt từng mã (Cấp 3).
- Dữ liệu nhãn: máy chính chụp (D08), cloud không có ảnh/clip thật.

## 8. Rollback
Cờ `qc_evidence` TẮT → không ghi bảng mới; mã BLOCK tắt từng mã (danh sách duyệt) → về REVIEW; bảng additive giữ dữ liệu (không DROP).

## 9. Việc mở / cần người dùng
1. Ngưỡng precision cho đề xuất BLOCK (đề xuất 0,95) và cỡ benchmark ngoài 20 + 20.
2. (đã kiểm) `final_qc` hiện để im lặng là "warn" (`core/final_qc.py:168`) → `QC-A2-SILENT_GAP` = REVIEW khớp hành vi cũ; độ dài > 20 % và đỉnh
   > −1 dBTP là "block" (`:36`, `:59`).
3. Thứ tự chuyển đường: đề xuất Q9 (tất định) → Q4 (enum có bằng chứng) → Q1/Q2 → Q5–Q8.
