# V3.1 M5.1–M5.2 — Thiết kế repair router + release gate (20/10/2026)

> **Cấp 1 — CHỈ TÀI LIỆU, 0 USD.** Việc C-M51-52 (cloud-B). Nền `origin/main` = `7a8a19f5`. Theo G2-6 (M5 DUYỆT CÓ ĐIỀU KIỆN: **router mặc định
> TẮT**, pilot A offline 0 USD), D07 (QC Shadow/REVIEW, BLOCK chỉ luật tất định đã benchmark), `docs/CHUAN_XAY_DUNG.md` luật 6 (gen lại chỉ khi đầu vào
> đổi; tự động ảnh ≤ 3 / video ≤ 2; cùng lỗi 2 lần → dừng) + luật chi phí. Căn cứ: kế hoạch V3.1 §M5 (dòng M5.1/M5.2, mốc "tắt repair router");
> sổ lỗi `devsys/errors.json`; thiết kế M4.1 `docs/V3_1_M4_1_THIET_KE_BANG_CHUNG_QC_2026-10-20.md` (25 mã QC, `qc_runs` / `qc_findings`).

## 0. Tóm tắt
Hệ thống ĐÃ có các mảnh sửa — nhưng mỗi đường tự quyết theo điểm QC, không theo **mã lỗi**: trần `AUTO_REGEN_LIMIT` (`core/pipeline.py:33`), cấm gen
lại y nguyên (`Pipeline._no_auto_retry` 697, `quality_tier.regen_refusal` 775, KLD-1 `STALE_INPUT`), cùng lỗi lặp → dừng (697–715), Đạo diễn viết lại
prompt (`prompt_rewrite.before_retry` 520), trần bản cao (`quality_tier.RETRY_LIMIT` draft 2 / final 1), trần job toàn dự án (`autopilot._job_cap_check`
299). Thiếu: **bảng mã lỗi → hành động sửa cụ thể (đổi ĐẦU VÀO nào)**, lý do dừng có mã, và một **cổng phát hành** gom các điều kiện giao bản rải rác
(`final_qc` blocks, `delivered._evidence`, đối soát tiền). M5.1 = router **chỉ đề xuất** (cờ TẮT ⇒ hành vi cũ từng byte); M5.2 = checklist đo được,
chạy ở shadow trước, chặn bàn giao chỉ khi người dùng bật (Cấp 3).

## 1. AS-IS — điểm quyết định gen lại / giao bản (file:hàm)
| Điểm | File:hàm | Hành vi hiện tại | Router đụng? |
|---|---|---|---|
| Trần tự động | `core/pipeline.py` `AUTO_REGEN_LIMIT` (33), `auto_limit`, `_retries_exhausted` (1119) | ảnh 3 / video 2 theo chuỗi `parent_job_id`, `retry_count` chỉ lần máy tăng; người bấm = 0 | ĐỌC, không đổi hằng |
| Leo thang | `Pipeline._escalate` (1139), `_limit_said` → diag `AUTO_LIMIT_CODE`, 📥 `core/inbox.py` | job `escalated=1`, cảnh `needs_attention` | ghi thêm `repair_stop_code` |
| QC tự gen lại | `Pipeline._no_auto_retry` (697) | không câu sửa → không; look-drift only; trần; tiêu chí hỏng ⊆ lần trước → "cùng lỗi lặp lại" | thay khóa so sánh tiêu chí → `qc_code` |
| Thử lại sau lỗi | `Pipeline.retry` (451), `_spawn_retry` (1088), `resend` (489) | `PLAIN_RESEND` chỉ cho lỗi nhà cung cấp; `STALE_INPUT` cấm gửi y nguyên; `_final_hold` | không đổi |
| Gửi không rõ kết quả | `runner._submit_unknown` (599), `pipeline.SUBMIT_UNKNOWN` (48), `retry` 466–471 (cờ `poll_claim` — **BẬT máy chính**) | KHÔNG BAO GIỜ tự gửi lại; leo thang | router **bỏ qua hẳn** |
| Tạm dừng trước gửi | `runner._paused_now` (589, cờ `pause_before_submit` — **BẬT**) + `spend_gate.PAUSED` | job giữ hàng, không gửi | router không tạo job khi dự án dừng |
| Giữ chỗ tải kết quả | `core/poll_claim.py` (`job_poll_claims`) | 1 tiến trình xử lý kết quả | router chạy SAU khi kết quả đã được giữ chỗ + ghi |
| Gen lại y nguyên (video) | `quality_tier.regen_refusal` (775, cờ `two_tier_quality`) | từ chối khi câu sửa + ảnh + motion + model không đổi | router dùng làm kiểm cuối |
| Viết lại prompt | `prompt_rewrite.before_retry` (520) / `rewrite_for_retry` (457), cờ `prompt_rewrite` | Đạo diễn viết lại khi có câu sửa | hành động `REWRITE_PROMPT` gọi đúng hàm này |
| Trần job dự án | `autopilot._job_cap_check` (299), `JOB_CAP_NOTE` | ảnh × (1+3) + video × (1+2) job máy | giữ nguyên, router không vượt |
| Kiểm bản dựng | `core/final_qc.py:run` (191), autopilot 1361 (`blocks` → ATTENTION) | lỗi `block` → không "Xong" | thành mục G2 của cổng |
| Đã giao | `delivered.mark` (59) — kéo `project_reserve.release_quietly` + `subjects.schedule_auto_cleanup`; `delivered._evidence` (87: manifest có `final_qc`) | ghi `deliveries` | cổng chạy TRƯỚC `mark` |
| Độ phân giải giao | `final_cut.require_delivery_resolution` (136) | ném lỗi khi lệch | mục G2 |

## 2. M5.1 — Repair router (cờ `repair_router`, mặc định TẮT)
**Vào:** một `qc_findings` (M4.1) hoặc ghi chú lỗi job (`failure_note`) đã gán `qc_code` / mã dừng. **Ra:** `repair_plan` = `{qc_code, action,
input_delta, attempt_no, limit, stop_code|null, needs_person: bool, evidence_ref}` — ghi `job_events` note + diag `repair_plan`; cờ ở `shadow` chỉ ghi,
ở `on` mới gọi đúng hàm hiện có (`Pipeline.retry(fix=…)`, `prompt_rewrite.before_retry`, chọn lại ảnh tham chiếu…). Router **không** có đường gửi riêng:
mọi job vẫn qua `runner` (spend_gate, pause, poll_claim, `_ref_lint`, `video_pregen`).

### 2.1 Bảng mã lỗi → hành động (đổi đầu vào gì) → trần → dừng hỏi người
| `qc_code` | Hành động (`action`) | Đầu vào phải đổi (`input_delta`) | Trần tự động | Dừng hỏi người khi |
|---|---|---|---|---|
| QC-PKG-VI_TEXT | `FIX_PACKAGE` (0 USD, trước gửi) | dịch / bỏ chữ Việt khỏi prompt (`video_pregen`) | 1 sửa gói, 0 gen | sửa gói vẫn đỏ |
| QC-PKG-FORM_PICTURE_MISSING | `FIX_PACKAGE` | gắn ảnh form từ Kho (`_ref_lint`) | 1 | Kho thiếu ảnh form → hỏi (luật 1, không im lặng) |
| QC-PKG-PROMPT_TOO_LONG | `FIX_PACKAGE` | rút gọn theo `video_rules` trần ký tự | 1 | vẫn quá trần |
| QC-L1-IDENTITY_DRIFT / QC-L2-FORM_OUTFIT | `SWAP_REF` rồi `REWRITE_PROMPT` | ảnh tham chiếu nhân vật / form khác (BYĐ `kho_id`) + câu sửa trang phục | ảnh 3 / video 2 | lặp cùng mã lần 2; Seedance ref-only look-drift (`_look_drift_only`) → hỏi ngay |
| QC-L3-EXTRA_PEOPLE | `REWRITE_PROMPT` | câu "only N people" + negative | ảnh 3 / video 2 | lặp lần 2 |
| QC-L4-POSE_ACTION / QC-V4-MOTION_VS_BYD | `REWRITE_PROMPT` | motion prompt / câu hành động theo BYĐ | ảnh 3 / video 2 | lặp lần 2 · hành động khác ý đồ BYĐ → hỏi (đổi ý đồ) |
| QC-L6-SIZE_MISMATCH | `REFRAME` | khung cắt / câu cỡ cảnh (`framing_guard`) | ảnh 3 | qua vai / ý đồ (A5) → REVIEW, không tự sửa |
| QC-L7-PROP_MISSING | `REWRITE_PROMPT` + `SWAP_REF` | câu đạo cụ + ảnh vật (Kho) | ảnh 3 / video 2 | lặp lần 2 |
| QC-L9-HORIZON_MISMATCH / QC-L11-PLACE_MISMATCH | `REPLATE` | plate / camera 3D (`plate_camera`), nền khác | ảnh 3 | nền không trời (G20) → không sửa; không có plate → hỏi |
| QC-L13-CONTINUITY | **không tự sửa** (D07) | — | 0 | luôn REVIEW → 📥 (M3.4 đồ thị chỉ ra shot phụ thuộc) |
| QC-L14-ARTIFACT | `REGEN_NEW_SEED` + câu sửa | seed + câu "clean hands/face" (câu sửa bắt buộc ≠ lần trước) | ảnh 3 / video 2 | lặp lần 2 |
| QC-V1-DRIFT / QC-V2-JERK_FREEZE / QC-V2-STILL_OVER_1_5S | `REWRITE_PROMPT` (motion) hoặc `TRIM` (cắt đoạn đứng trong dựng, 0 USD) | motion prompt / điểm cắt | video 2 | TRIM đủ dùng → không gen; lặp lần 2 |
| QC-V3-LIP_SYNC | `RESYNC` (0 USD: lệch tiếng) rồi `REGEN` | độ lệch audio / clip | video 2 | lặp lần 2 |
| QC-A2-PEAK_OVER / QC-A4-LENGTH_MISMATCH / QC-A4-DELIVERY_RES / QC-A4-BLACK_FRAME | `RERENDER` (0 USD, dựng lại) | thông số dựng (limiter, độ dài, cỡ) | 2 lần dựng | vẫn BLOCK sau 2 lần |
| QC-A2-SILENT_GAP | không tự sửa | — | 0 | REVIEW (im lặng có thể là ý đồ) |
| QC-CR-INPUT_MISSING / QC-SYS-QC_CRASH | không phải lỗi shot | — | 0 | `qc_runs.partial/failed` → sửa QC, không gen |
| `submit_unknown` (không phải QC) | **KHÔNG làm gì** | — | 0 | luôn: người đối soát nhà cung cấp trước |

Hằng `REPAIR_ACTIONS` (mới, `core/repair_router.py`) là bảng này; test hợp đồng: mọi `qc_code` của M4.1 có đúng một dòng.

### 2.2 Luật dừng (theo thứ tự, mã dừng có trong `devsys/error_types.json` / diag)
1. `REPAIR_SUBMIT_UNKNOWN` — job ghi chú `SUBMIT_UNKNOWN` → không bao giờ tự tạo job (M1.2, giữ nguyên `retry` 466).
2. `REPAIR_PAUSED` — dự án dừng (`projects.paused`) → không tạo job; kế hoạch giữ lại, chạy khi bỏ dừng (khớp `pause_before_submit`).
3. `REPAIR_LIMIT` — `_retries_exhausted` (ảnh 3 / video 2; bản cao `RETRY_LIMIT` final 1) → `_escalate(limit=True)` như cũ.
4. `REPAIR_SAME_CODE_TWICE` — cùng `qc_code` ở 2 lần liên tiếp trong chuỗi (thay so sánh tập tiêu chí 711–715) → dừng, báo **lớp cần sửa** (Bible / ảnh
   tham chiếu / prompt / khung cắt — luật 6).
5. `REPAIR_NO_INPUT_DELTA` — `input_delta` rỗng hoặc `regen_refusal` từ chối → không gửi (luật 6 "mỗi lần phải đổi đầu vào").
6. `REPAIR_INTENT_CHANGE` — sửa đòi đổi ý đồ (BYĐ khác, hành động khác, `intent_exception` M4.1) → hỏi người (kế hoạch M5.1 "dừng khi đổi ý đồ").
7. `REPAIR_REVIEW_ONLY` — mã mức REVIEW chưa có hiệu chuẩn (D07) → chỉ đề xuất, không tự gen kể cả cờ `on`.
8. `REPAIR_JOB_CAP` / `REPAIR_BUDGET` — `_job_cap_check` / `spend_gate.assess` từ chối → dừng, báo đúng câu của cổng đó.
Mọi dừng → `_escalate` + 📥 "Cần bạn quyết" kèm `repair_plan` (người thấy đã thử gì, đổi gì, vì sao dừng). Người bấm tay vẫn không giới hạn (luật 6).

### 2.3 Tương tác với cờ đã BẬT máy chính
- `poll_claim`: router chạy trong tiến trình đang giữ chỗ job (sau `_poll_take`), một lần mỗi kết quả; khóa idempotent `repair_plan(job_id, qc_run_id)`
  — tiến trình thứ hai thấy kế hoạch đã có thì bỏ qua. `SUBMIT_UNKNOWN` = dừng loại 1.
- `pause_before_submit`: router có thể ghi kế hoạch khi dự án dừng nhưng job mới (nếu tạo) vẫn bị `_paused_now` giữ; đề xuất: không tạo job luôn (loại 2)
  để không tăng `retry_count` khi người chưa bỏ dừng.
- `two_tier_quality`: lần sửa trên bản NHÁP theo trần draft 2; bản CAO chỉ 1 lần tự gen lại kèm câu sửa (`quality_tier` 706) — router không nâng trần.

## 3. M5.2 — Release gate (cờ `release_gate`: TẮT → `shadow` → `guarded`)
Chạy trước `delivered.mark` (và trước `autopilot` đặt DONE). `shadow`: chỉ ghi `release_check` (JSON trong `outputs.manifest`) + 📥 "Bản giao"; `guarded`
(Cấp 3, người dùng bật): mục đỏ chặn `mark` — mở bằng **miễn trừ ký tên** (`{muc, ly_do, nguoi, at}` ghi audit, không xóa).

| # | Mục (đo được) | Nguồn đo (file:hàm) | Đạt khi |
|---|---|---|---|
| G1 | Mọi shot trong dựng đã DUYỆT | `final_cut.collect_clips_for_render` + `_is_chosen` (50); jobs `approved` | 100 % shot dựng có job `approved` (clip tay = ghi rõ `manual`) |
| G2 | Final QC không BLOCK | `final_qc.run` (`blocks == 0`), `require_delivery_resolution`, mã QC-A2/A4 | 0 finding BLOCK; REVIEW đã có người xem |
| G3 | Bản giao khớp nguồn | `delivery.status` / `_layer_change` (258) — không lớp "⚠ cũ" | không lớp cũ so với clip / âm / thiết lập |
| G4 | Đối soát chi phí | sổ chi (`core/cost.py`, `budget`) + công cụ `tools/clipai_cost_reconcile.py` (**chưa trên main** — trên `cloud/v31-fix-d19`) | |sổ − nhà cung cấp| ≤ 1 % hoặc ≤ 0,5 USD; `unpriced` / `ambiguous_job` = 0 hoặc có giải trình |
| G5 | Không gửi treo | jobs ghi chú `SUBMIT_UNKNOWN` chưa đối soát; `job_poll_claims` hết hạn | 0 |
| G6 | Lỗi nghiêm trọng mở = 0 | `devsys/errors.json` mục gắn dự án, mức CAO, trạng thái ∉ {VERIFIED, WONT_FIX} | 0 hoặc miễn trừ ký tên |
| G7 | Không REVIEW treo | `qc_findings` REVIEW chưa có người kết luận; 📥 `escalated=1` của dự án | 0 |
| G8 | Lineage đủ | `lineage` + `delivered._evidence` (manifest có `final_qc`) | mọi lớp có nguồn |

Hậu quả của `mark` (trả phần trích `project_reserve`, `subjects.schedule_auto_cleanup`) chỉ chạy khi cổng qua — và theo C3-3, dọn Kho vẫn chỉ DRY-RUN
(thiết kế M1.5 cập nhật C-FIX-D19). Báo cáo cổng = bảng 8 dòng xanh/đỏ + số liệu, hiện ở màn Bản giao.

## 4. Test plan
| Test | Nội dung |
|---|---|
| `tests/test_repair_router_table.py` | mọi `qc_code` M4.1 có đúng 1 dòng `REPAIR_ACTIONS`; mã REVIEW-only không có hành động tự gen; `submit_unknown` → NONE |
| `tests/test_repair_router_stops.py` | 8 luật dừng, thứ tự ưu tiên; `REPAIR_SAME_CODE_TWICE` trên chuỗi 2 job; `NO_INPUT_DELTA` khi `regen_refusal` từ chối |
| `tests/test_repair_router_compat.py` | cờ TẮT ⇒ `apply_qc` / `retry` / `_no_auto_retry` cùng kết quả + cùng job tạo ra (golden M1.9); `shadow` ⇒ 0 job mới |
| `tests/test_repair_router_flags.py` | `poll_claim` bật: 2 tiến trình → 1 kế hoạch; `pause_before_submit` bật + dự án dừng → 0 job, `retry_count` không tăng |
| `tests/test_release_gate.py` | 8 mục với fixture DB (shot chưa duyệt, final_qc block, lớp cũ, lệch tiền, submit_unknown, lỗi CAO mở, REVIEW treo); `shadow` không chặn `mark`; miễn trừ có audit |
| Hiện có phải xanh | `test_pipeline.py`, `test_autopilot.py`, `test_quality_tier.py`, `test_prompt_rewrite.py`, `test_final_qc.py`, `test_delivered.py` `test_v31_m12_poll_claim.py`, `test_v31_m13_pause_before_submit.py` |
Pilot vòng A (M5.3, 0 USD): replay chuỗi lỗi #31/#33 qua router ở `shadow`, so kế hoạch đề xuất với cách người đã sửa thật.

## 5. Rollback
`repair_router` TẮT (mặc định, G2-6) ⇒ không import đường mới, hành vi cũ từng byte. `release_gate` TẮT/`shadow` ⇒ `mark` như cũ. Không migration bắt buộc:
`repair_plan` ghi trong `job_events.note` + diag; `release_check` trong `outputs.manifest` (JSON có sẵn). Nếu sau cần bảng riêng = Cấp 3.

## 6. Việc mở / cần người dùng
1. Ngưỡng G4 (1 % / 0,5 USD) và ai được ký miễn trừ (chủ dự án hay chỉ chủ hệ thống).
2. `pause_before_submit`: đề xuất router KHÔNG tạo job khi dừng (khác đường retry hiện có — job vẫn được tạo rồi giữ). Cần chốt.
3. G4 phụ thuộc gộp `tools/clipai_cost_reconcile.py` (nhánh `cloud/v31-fix-d19`); họ Kling chưa đối soát (`scope=seedance_only`) → G4 cho Kling = REVIEW.
4. Bật `release_gate=guarded` và `repair_router=on` = Cấp 3, sau pilot A + benchmark M4.6 theo mã.
