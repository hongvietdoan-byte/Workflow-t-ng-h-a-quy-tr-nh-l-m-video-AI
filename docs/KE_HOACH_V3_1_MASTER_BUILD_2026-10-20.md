# Kế hoạch V3.1 — Master Build Plan (20/10/2026) — NGUỒN DUY NHẤT VỀ TIẾN ĐỘ BUILD V3.1

> Đợt ưu tiên: M1 (G2-2 duyệt 20/10 — ưu tiên M1 + golden M1.9 trước M2; song song M0.4–M0.5 sổ lỗi G2-1; M0.6–M0.11 ở làn cloud)

> **21/10 — thêm M6 "AI Video Production Team"** (Executive Producer chốt ĐỊNH HƯỚNG KIẾN TRÚC, chưa duyệt code): kế hoạch chi tiết
> `docs/KE_HOACH_TO_LAM_PHIM_CO_CHU_2026-10-21.md`; triển khai XEN KẼ theo phụ thuộc với M1–M5 (không làm hết M6 trước M2, không chờ M2 100 %).

> **Nguồn:** `E:/Tai xuong/AI_VIDEO_PIPELINE_MASTER_PLAN_V3_1_2026_10_20.pdf` (người dùng 20/10, 11 trang) — chuyển sang markdown để AI Dev
> System (`devsys/plans.json`, kiểu `viec_s`) tính tiến độ từ danh sách việc ở mục 5. Hợp nhất: KH-gốc 17/10, V2.1 R2/R3
> (`docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md` §1–§15), V3 (`docs/KE_HOACH_AI_VIDEO_PIPELINE_V3_2026-10-20.md` + Phụ lục A), báo cáo lỗi
> #31/#33, `docs/audit/P1_BASELINE_VERIFICATION.md`, `docs/CHUAN_XAY_DUNG.md`, `CLAUDE.md`.
> **Trạng thái (người dùng 20/10, văn bản "QUYẾT ĐỊNH NGƯỜI DÙNG — AI VIDEO PIPELINE V3.1"):** phê duyệt ĐỊNH HƯỚNG có điều kiện, **không**
> phê duyệt triển khai toàn bộ M0–M5. **D01–D10 ĐÃ CHỐT 20/10** (văn bản "PHÊ DUYỆT D01–D10"; mục 4) — là chính sách / định hướng kiến trúc,
> KHÔNG phải lệnh triển khai code. Mỗi việc ghi cấp quyền
> (mục 4b): Cấp 1 làm ngay (tài liệu / thiết kế / test chỉ đọc), Cấp 2 cần duyệt phạm vi code trước, Cấp 3 xin riêng (migration, cờ production,
> API trả phí, QC chặn, pilot trả phí). Sổ quyết định: `v31-permission-tiers-2026-10-20` và 4 mục định hướng (mục 4b).

## 1. Đánh giá của Claude (20/10, đối chiếu repo `main` = `cbc0ea27`)

**Kết luận: dùng được làm kế hoạch build, với 3 điều chỉnh.** V3.1 tốt hơn V3 ở chỗ: gom lỗi theo nguyên nhân gốc thành 7 workstream
thay vì vá từng mã; làm theo lát dọc (schema → builder → preflight → ledger → QC → Dashboard → regression); sổ lỗi có mã bất biến + alias
+ vòng đời (VERIFIED chỉ khi có bằng chứng chạy thật); giữ đúng giới hạn tự gen lại của CHUAN_XAY_DUNG (ảnh ≤ 3, video ≤ 2); không gửi lại
task "không rõ đã gửi chưa"; BYĐ suy ra cho shot chèn là DRAFT; có schema `scene_world_map` và schema bằng chứng QC; mỗi milestone có cổng
nghiệm thu + rollback.

V3.1 **bắt đúng một mâu thuẫn của V3**: V3 đề xuất A14 "trích ngân sách dự án = 0 thì chặn" — trái chính sách tiền 04/10
(`docs/CHUAN_XAY_DUNG.md` dòng 56–62, `core/money_policy.py`: trần chỉ CẢNH BÁO; chỉ chặn khi hết tiền thật / tạm dừng / trần job/ngày
autopilot). → A14 chỉ sửa thông điệp cảnh báo, **không chặn**, trừ khi người dùng đổi chính sách (D01).

**Ba điều chỉnh:**
1. **Máy trạng thái job (WS1 §4.1) làm tối thiểu.** V3.1 đề xuất thêm 6 trạng thái (CLAIMED, SUBMITTING, SUBMITTED, POLLING,
   ARTIFACT_READY, SUBMIT_UNKNOWN). `core/states.py` hiện có 9 trạng thái (`queued, running, succeeded, failed, retryable, pending_review,
   approved, rejected, cancelled`) dùng khắp Dashboard, autopilot, bg_poll, CSDL. Đổi enum là thay đổi rộng, rủi ro cao. Làm: giữ `JobState`;
   nguyên tử hóa bằng UPDATE có điều kiện + bảng `job_send_claims` đã có (`core/send_claim.py`); "không rõ đã gửi" = đường `not_found`
   hiện có (không tự gửi lại) + ghi rõ lý do; chỉ thêm trạng thái mới nếu test chứng minh cần.
2. **Tách M2 thành hai lát** (M2 BYĐ/Kho/khóa/lineage và M2 payload/router/âm thanh nằm cùng milestone nhưng là việc riêng, mỗi việc một
   commit + test) — M2 của V3.1 gom WS2 + WS4 quá lớn cho một lần nghiệm thu.
3. **Sổ lỗi nối với sổ có sẵn:** `devsys/error_types.json` (loại lỗi L1…, cách đo), `devsys/stages.json` (khâu L1–L16),
   `core/known_issues.py` (lỗi của khâu đang tắt). Sổ lỗi mới ghi *lần xảy ra + nguyên nhân gốc*, trỏ tới loại lỗi và khâu, không chép lại.
   Lưu JSON trong `devsys/errors.json` (git, đọc được mọi tài khoản/phiên — như `data/decisions.json`); khuyến nghị D09 = JSON.

Nhận xét nhỏ: bảng §11 của PDF bị lệch hàng khi in (nhóm mã ↔ workstream) → sổ lỗi là bảng ánh xạ chính thức, báo cáo coverage 100 % ở M0.
Mốc lịch sử `3ecf053b`/`186a2cc9` trong PDF đã cũ — M0.1 kiểm lại HEAD thật.

## 2. Kiến trúc: 7 workstream (tóm tắt V3.1 §0–§9)

| WS | Phạm vi | Lỗi chính |
|---|---|---|
| WS0 | Nền bằng chứng: sổ lỗi trung tâm, audit, baseline, golden gói | G5, G23, G25 (khuyết), G58 lặp, mọi mã |
| WS1 | Thực thi + chi phí: vòng đời job, provider, tạm dừng, retry, sổ chi | A1–A3, A13–A15, G30–G36, G39, G55–G58; A7–A9, G31 |
| WS2 | Sự thật có cấu trúc: BYĐ v2, Kho, danh tính asset, chèn shot, khóa tay, lineage | G4–G6, G21–G23, G38; A4, A12; R3 `vat` |
| WS3 | Liên tục không gian/thời gian: world map, blocking, máy, đạo cụ, cross-shot | G1–G3, G41–G50, G52; B3–B5, A10 |
| WS4 | Hợp đồng gen: một builder gói, preflight ảnh/video, router, video ref, âm thanh | G7, G10–G17, G19, G24, G26–G29, G37, G53, G54; B7–B9, A11 |
| WS5 | QC đa tầng có bằng chứng + Dashboard; shadow → guarded | G20, G34, G51, G52; A5, A6 |
| WS6 | Sửa chọn lọc + phát hành: repair router, trần retry, final QC | — |

**Hợp đồng dữ liệu xuyên suốt (V3.1 §2):** ảnh Kho > profile Kho > Bible > Lock (forms/outfit/hair/face có cấu trúc, `kho_id` + revision truy
vết); BYĐ `byd_v=2` (parser v1 chung; giờ/thời tiết tại shot là nguồn chuẩn, trigger đồng bộ bản chép); `scene_world_map` + `stage_facts`
(không mang đạo cụ qua thế giới khác; máy là phép chiếu từ world state); continuity expected (BYĐ + world) / observed (QC, append-only) /
resolved (người duyệt); `_build_package` dùng chung cho gửi thật / xem trước / replay / golden; `jobs + send_claim + usage_events +
sent_package` (không gửi lại khi trạng thái UNKNOWN, đối soát trước retry); sổ lỗi: mã bất biến + nguyên nhân gốc, diag kỹ thuật giữ riêng.

**`scene_world_map` tối thiểu:** `schema_version, scene_id, world_id, unit=m, axes, origin, map_revision, geometry_asset_revision,
entities[{entity_id, kho_id, kind, transform, dimensions, valid_from, valid_to, source}], landmarks, occluders, approved_by, approved_at`.
Blocking mỗi shot: `shot_id, camera_pose, lens/FOV, target, visible_landmarks, character_positions, prop_states, state_before/state_after`.
Thiếu hình học → UNKNOWN + yêu cầu duyệt, không tự bịa tọa độ.

**Bằng chứng QC:** `error_type, severity, evidence_type (metadata/frame/segment/VLM), confidence_calibration, artifact_id, artifact_sha,
qc_run_id, qc_version, intent_exception, actionability, source_refs`. Lỗi hình học/ngữ nghĩa → REVIEW khi chưa đủ bằng chứng; chỉ luật kỹ
thuật tất định mới được cân nhắc BLOCK sau benchmark.

**Sổ lỗi (WS0):** mã bất biến `P31-G1`, `P33-A1` + alias lịch sử; `root_cause_id` nối nhiều lần xảy ra. Trường: `id, alias, title,
source_document, project/shot/job ids, stage (L1–L16), category, root_cause_hypothesis/confirmed, evidence, severity, status, first_seen,
last_seen, affected_flows, owner, fix_commit, tests, real_run_evidence, plan_workstream, dependencies, reopen_history`. Trạng thái
`OPEN → IN_PROGRESS → FIXED_UNVERIFIED → VERIFIED`; `REOPENED`, `WONT_FIX` có lý do. Không VERIFIED chỉ vì test offline qua. Mã khuyết (G25)
để trống, không bịa.

Chi tiết từng workstream: PDF V3.1 §3–§9 + V3 Phụ lục A (P1 golden, BYĐ v2, Dashboard/overrides, continuity_state, QC 5 lớp + benchmark,
mã lỗi sửa chọn lọc).

## 3. Lộ trình và cổng nghiệm thu (V3.1 §10, §13)

| Milestone | Nội dung | Cổng nghiệm thu | Rollback |
|---|---|---|---|
| M0 Đóng băng & thiết kế | audit HEAD/cờ/schema; schema sổ lỗi + nhập mã; AS-IS/TO-BE; chốt D01–D10; ma trận test | sổ lỗi 100 % mã có nguồn, không trùng; quyết định ghi `decisions`; HEAD/cờ xác minh | không đụng production |
| M1 Nền tin cậy | WS0 sổ lỗi + golden; WS1 job/chi phí/provider; parser `vat` v1 | test 2 worker + crash/reconcile; 0 job trả tiền trùng; ước tính so sổ chi; parser QC cũ | tắt cờ / revert; không tự gửi lại UNKNOWN |
| M2 Hợp đồng sản xuất | WS2 BYĐ v2/Kho/khóa/lineage + WS4 builder/replay/preflight/router | #24/#27 cờ TẮT giống golden từng byte; #31/#33 correctness; khóa tay không bị ghi đè | tắt cờ con, migration tương thích |
| M3 Thế giới & liên tục | WS3 world map/whitebox/blocking + expected state; nối WS4 | người dùng duyệt map cảnh 4/6/8 #31 + tháp #33; kiểm hình học offline; gen chứng minh xin riêng | tắt định tuyến map, dùng ref cũ |
| M4 QC & Dashboard | WS5 bằng chứng QC, benchmark shadow, Dashboard xem gói/override/chi phí | benchmark độc lập theo mã; rà báo nhầm; override có audit | QC chỉ shadow |
| M5 Sửa & pilot | WS6 repair router, trần retry, final QC; pilot end-to-end | pilot thật có duyệt, không gen thừa, không sửa ngoài phụ thuộc; final QC; báo cáo chi phí | tắt repair router |
| M6 Tổ làm phim có chủ (21/10) | Role Registry, Handoff Contract, Generation Authorization (ảnh 3 / video 2 lượt mỗi shot), Video Prompt Artist + Storyboard Artist shadow, vai 3D / âm thanh / dựng / continuity, Dashboard điều phối + tốc độ theo profiling | mỗi trường một vai chủ; cổng lượt khớp tính tay trên replay #27/#31; VPA coverage 100 % + EP chọn ≥ 2/3 so mù; `lineage.summary` #31 < 0,3 s; cờ TẮT = golden byte giống | cờ từng phần TẮT (shadow trước) |

**Bắt buộc mỗi thay đổi (V3.1 §13.1, CHUAN_XAY_DUNG):** kiểm thao tác tay, autopilot, v2 cảnh, v3 từng shot, nhiều shot, clone dự án, chạy
lại Đạo diễn; `py tools/related_areas.py` + agent rà khu vực liên quan trước commit (quy ước 7); `pregen_check --project N` trước khi xin gen
tốn tiền; test giả không phải chất lượng thật. M0–M4 (audit, code, test giả, Blender offline) = 0 USD API; Q3 soạn forms, benchmark VLM, gen
chứng minh, pilot = ước tính qua `spend_gate` + xin duyệt.

## 4. Quyết định D01–D10 — ĐÃ CHỐT 20/10 (chính sách / định hướng, chưa phải lệnh triển khai)

Phân tích phương án: `docs/V3_1_D01_D10_CHO_DUYET_2026-10-20.md`. Sổ: `data/decisions.json` id `v31-d01-…` → `v31-d10-…`.

| ID | Chọn | Điều kiện bổ sung của người dùng | Sổ quyết định |
|---|---|---|---|
| D01 Tiền | A | Ngân sách dự kiến chỉ cảnh báo, không tự chặn khi allocation = 0; giữ chặn: hết tiền thật, tạm dừng, trần job/ngày autopilot, giới hạn tự gen lại. Dự toán chính xác hơn, cảnh báo rõ trước gửi, đối soát chi phí thật. Không tự đổi chính sách tiền | `v31-d01-money-policy-2026-10-20` (+ check `check_no_budget_lock_gate`) |
| D02 Provider Claude | A + khóa theo job | Job lưu provider thực tế + phiên bản cấu hình; job đang chạy không đổi provider; hết quota dừng + báo, không tự sang API trả phí; `claude_cli` = 0 USD API nhưng có giới hạn; migration tương thích dự án cũ | `v31-d02-claude-provider-per-project-2026-10-20` |
| D03 Kho chủ thể | A | Preflight kiểm sức chứa thật nếu provider cho; không xác định được → báo rõ; không tự xóa asset / đổi model ngoài quy tắc; người dùng quyết dọn; bảo vệ asset dự án khác còn tham chiếu | `v31-d03-subject-library-full-stop-2026-10-20` |
| D04 Khóa dữ liệu | B | 3 trạng thái ở CẤP TRƯỜNG; một write guard; kiểm revision (tác vụ cũ không ghi đè mới); xung đột → diff / duyệt; không sửa USER_LOCKED kể cả khi AI cho là sai; audit người/tiến trình, giờ, revision, thay đổi; Shadow trước | `v31-d04-field-level-write-guard-2026-10-20` (thay `v31-user-edit-protection-direction-2026-10-20`) |
| D05 Kho forms | A | 6 điều kiện M2.3; ảnh chuẩn Kho ưu tiên; metadata AI có provenance, không ghi đè người dùng; adapter v1/v2, schema version, regression, kiểm mọi đường đọc; backfill + API trả phí duyệt riêng | `v31-d05-kho-structured-forms-2026-10-20` (thay `v31-kho-forms-direction-2026-10-20`) |
| D06 World map | B | Không bắt buộc 3D; 3D → tọa độ thật; không 3D → 2D / quan hệ tương đối; thiếu → UNKNOWN; version, provenance, quan hệ shot, **invalidation**; duyệt trước khi chặn gen; offline #31/#33 trước | `v31-d06-scene-world-map-flexible-2026-10-20` (thay `v31-scene-world-map-trial-2026-10-20`) |
| D07 QC | A | Benchmark theo từng nhóm lỗi; kỹ thuật có bằng chứng → xét chặn sau nghiệm thu; ngữ nghĩa / góc máy / continuity / chuyển động không chắc → REVIEW; 20+20 chỉ là sàng lọc, không tự cấp BLOCK; override có người, lý do, bằng chứng, audit; bật chặn / tự sửa production duyệt riêng | `v31-d07-qc-shadow-guarded-2026-10-20` |
| D08 Fixture | A | Chỉ đọc, máy chính hoặc snapshot nhất quán (đang chạy job → snapshot); ghi SHA, cờ, schema version, model/provider, payload, thứ tự ref, hash; tách compatibility / correctness | `v31-d08-fixture-capture-readonly-2026-10-20` |
| D09 Lưu trữ | C | errors.json = định nghĩa + vòng đời; diag_events / jobs = lần phát sinh; bảng overrides CSDL. Mã bất biến; lỗi gốc ≠ lần xuất hiện; liên kết nhiều dự án; tách đã sửa code / qua test / xác minh chạy thật; không tự đóng khi chỉ có unit test; override liên kết mã lỗi / finding, người, revision; kiểm ghi đồng thời, schema, rollback; migration overrides duyệt riêng | `v31-d09-error-registry-json-overrides-db-2026-10-20` |
| D10 Phạm vi | A | Ngoài core V3.1 nhưng giữ trong định hướng dài hạn; chỉ giữ interface / extension point; không phát sinh việc / chi phí M0–M5 | `v31-d10-premiere-bg-replace-outside-core-2026-10-20` |

### 4a. Điều kiện bổ sung vào nghiệm thu / regression / rollback

| Milestone | Nghiệm thu thêm (từ D01–D10) | Regression thêm | Rollback |
|---|---|---|---|
| M0.4–M0.5 sổ lỗi (D09) | mã bất biến + không trùng; lỗi gốc tách lần xuất hiện; trạng thái FIXED_UNVERIFIED / TESTED / VERIFIED tách bạch; lỗi chỉ có unit test không được đóng | test hợp đồng sổ (trùng mã, VERIFIED thiếu bằng chứng chạy thật → đỏ) | file JSON trong git: revert |
| M1.4 provider (D02) | job ghi provider + phiên bản cấu hình lúc tạo; đổi cấu hình giữa chừng không đổi job đang chạy; hết quota → dừng, 0 lời gọi API trả phí | 2 dự án 2 provider cùng tiến trình; job đang chạy + đổi cấu hình; hết quota claude_cli | cột trống = hành vi env cũ |
| M1.5 Kho chủ thể (D03) | không xác minh được sức chứa → báo, không gửi im lặng; không xóa asset; asset dự án khác đang tham chiếu được bảo vệ | provider giả báo đầy / không trả số / asset dùng chung | tắt kiểm (cờ) |
| M1.6–M1.7 tiền (D01) | 0 điểm chặn mới theo ngân sách; cảnh báo trước gửi có số; đối soát sổ chi ↔ provider; lệch ước tính ≤ 10 % khi đủ dữ liệu giá | `check_no_budget_lock_gate` vẫn xanh; allocation = 0 chỉ cảnh báo | revert bảng giá |
| M1.9 golden (D08) | fixture có SHA, cờ, schema version, model/provider, payload, thứ tự ref, hash; snapshot khi máy chính đang chạy job; golden ≠ đúng | compat (cờ TẮT = byte) tách correctness | xóa fixture |
| M2.3 Kho forms (D05) | 6 điều kiện; ảnh chuẩn > metadata AI; provenance; không ghi đè người dùng; mọi đường đọc Director/BYĐ/ảnh/video/QC qua adapter | dự án cũ (v1) giống byte; v2 đúng forms | adapter đọc v1 |
| M2.5 write guard (D04) | cấp trường; revision chống ghi đè; USER_LOCKED không bị AI sửa; xung đột → diff; audit đủ; Shadow trước | tác vụ cũ ghi sau tác vụ mới; mọi đường ghi (Director, CLI, Dashboard, batch, autopilot, chèn shot, chạy lại Director) | guard TẮT (shadow) |
| M3.x world map (D06) | 3D / 2D / UNKNOWN; version + provenance + invalidation khi geometry / BYĐ đổi; map chưa duyệt không chặn gen | #31 cảnh 4/6/8, #33 tháp offline | tắt định tuyến map |
| M4.x QC (D07) | báo cáo benchmark theo nhóm lỗi; chỉ luật kỹ thuật có bằng chứng được xét chặn; override có người / lý do / bằng chứng / audit | ca báo nhầm A5 / A6 / G20 | QC về shadow |
| M4.7 overrides (D09) | override liên kết mã lỗi / finding + người + revision; ghi đồng thời an toàn | 2 người override cùng shot | bảng để nguyên, UI cũ |
| Tồn đọng (D10) | không việc / chi phí nào trong M0–M5 | — | — |

## 4b. Quyết định người dùng đã chốt 20/10 + phân quyền

| Sổ quyết định (`data/decisions.json`) | Nội dung | Mức duyệt | Được làm bây giờ |
|---|---|---|---|
| `v31-permission-tiers-2026-10-20` | 3 cấp quyền; đồng ý định hướng ≠ được sửa code | đã chốt | áp cho mọi việc dưới |
| `v31-kho-forms-direction-2026-10-20` (M2.3) | Kho forms/outfit/hair/face + provenance, 6 điều kiện | định hướng | thiết kế + test đề xuất; KHÔNG migration production |
| `v31-user-edit-protection-direction-2026-10-20` (M2.5) | AUTO / USER_LOCKED / REVIEW_REQUIRED mọi đường ghi; báo xung đột | định hướng | đặc tả + audit đường ghi + chuẩn bị test; KHÔNG đổi write path |
| `v31-scene-world-map-trial-2026-10-20` (M3.1) | world map không bắt buộc; 3D hoặc 2D; UNKNOWN; version + provenance; duyệt trước khi chặn | thử nghiệm có điều kiện | thiết kế + thử offline SAU khi M3 được duyệt triển khai; KHÔNG bật production |
| `v31-m6-crew-architecture-2026-10-21` (M6) | Tổ làm phim: Executive Producer → Director → 7 vai chuyên trách + Continuity Validator; Kỹ sư chỉ code; Role Registry + Handoff Contract; dùng chung cơ chế V3.1 | định hướng kiến trúc | tài liệu, audit, roadmap, test plan; KHÔNG code pipeline |
| `v31-m6-generation-limits-policy-2026-10-21` (M6.3) | ảnh ≤ 3 lượt (1+2), video ≤ 2 lượt (1+1) mỗi shot/chu kỳ, tính chung, không đặt lại; 6 điều kiện tự sửa; Generation Authorization | chính sách tự động hóa | chưa bật tự gen trả phí; code hiện hành `AUTO_REGEN_LIMIT` giữ tới khi M6.3 được duyệt |
| `v31-pilot-three-rounds-2026-10-20` (M5.3) | 3 vòng A offline / B 5–8 shot / C 20–40 shot | quy trình, chưa duyệt chi phí | test plan, benchmark, dự toán; KHÔNG chạy B/C |

**Xung đột với sổ cũ:** không mục nào bị thay (`replaces` = null). Lưu ý cần giữ đồng bộ khi triển khai: `budget-gate-removed-2026-10-15`
(D01 phương án B/C sẽ phải `replaces` mục này); `stage-auto-plan-2026-10-15`, `stage-crew-plan-2026-10-16` (M3 mở rộng, không thay);
`video-form-picture-2026-10-19` (đọc `forms[]` qua adapter v1/v2); `qc-team-off-2026-10-14` (khớp D07); `byd-auto-shot-number-2026-10-15`
(phải đi qua guard M2.5). V3 cũ đề xuất A14 "chặn khi trích ngân sách = 0" mâu thuẫn chính sách 04/10 → bỏ, chờ D01.

**Đề xuất mở rộng schema sổ (CHƯA áp dụng — chờ người dùng):** sổ hiện chỉ có `status` active / replaced nên mức duyệt đang ghi trong chữ
`text` / `changes` (test `test_v31_direction_decisions_say_they_are_not_implementation_approval` giữ điều này). Đề xuất thêm trường tùy chọn
`approval` ∈ {`dinh_huong`, `thu_nghiem`, `quy_trinh`, `trien_khai`} (thiếu = `trien_khai` → mục cũ không đổi nghĩa) + `core/decisions.problems`
kiểm giá trị; không đổi `STATUSES`.

**Milestone theo quyền:**
- **Chuẩn bị offline được ngay (Cấp 1):** M0.6, M0.7, M0.9 (thiết kế Kho forms), M0.10 (đặc tả bảo vệ dữ liệu + audit đường ghi), M0.11
  (test plan + dự toán 3 vòng pilot), M0.12 (gói xin duyệt phạm vi M1).
- **Chờ duyệt phạm vi code (Cấp 2):** M0.4–M0.5 (sổ lỗi — kèm D09), toàn bộ M1–M4, M5.1–M5.2.
- **D01–D10 đã chốt (20/10):** các việc trước đây chờ quyết định nay chỉ còn chờ duyệt PHẠM VI code (Cấp 2) / chi phí (Cấp 3) — chốt chính sách không làm việc nào thành xong.
- **Cấp 3 (xin riêng):** migration (M2.3 backfill, bảng overrides, cột provider), bật cờ production, API trả phí, M5.4–M5.5 pilot B/C.

## 5. Danh sách việc (AI Dev System đọc mục này)

<!-- tien-do -->
| Đợt | Việc | Xong | Đang làm | Chờ người dùng | Bỏ | Tiến độ |
|---|---|---|---|---|---|---|
| M0 Đóng băng và thiết kế (0 USD) | 12 | 12 | 0 | 0 | 0 | 100 % |
| M1 Nền tin cậy (0 USD, provider giả) | 9 | 8 | 1 | 0 | 0 | 92,1 % |
| M2 Hợp đồng sản xuất có cấu trúc | 10 | 0 | 0 | 0 | 0 | 0 % |
| M3 Thế giới và liên tục | 5 | 5 | 0 | 0 | 0 | 100 % |
| M4 QC có bằng chứng và Dashboard | 8 | 6 | 2 | 0 | 0 | 81,2 % |
| M5 Sửa chọn lọc và pilot | 5 | 2 | 1 | 0 | 0 | 54,5 % |
| M6 Tổ làm phim có chủ (AI Video Production Team) | 13 | 0 | 1 | 0 | 0 | 1,8 % |
| M7 Cờ và cấu hình (Executive Producer chốt 21/10) | 8 | 3 | 0 | 0 | 0 | 31,2 % |
| **Tổng** | **70** | **36** | **5** | **0** | **0** | **50,3 %** |

Đợt hiện tại: **M1** · việc kế: **M2.1** BYĐ v2: byd_v, vat[] object, shot_intent.read có provenance, mức BLOCK/REVIEW/WARN
<!-- /tien-do -->

Trạng thái: ⬜ chưa làm · 🔄 đang làm · ⏸ chờ người dùng · ✅ xong · ✖ bỏ. Mỗi việc xong ghi commit + bằng chứng.

### M0 — Đóng băng và thiết kế (0 USD)
- [ ] M0.1 · Audit HEAD, cờ máy chính, schema CSDL, provider/model → biên bản docs/audit/M0_BASELINE_2026-10-20.md · nặng:1 · ✅ · biên bản docs/audit/M0_BASELINE_2026-10-20.md: HEAD/cờ/schema/provider đo trên máy chính
- [ ] M0.2 · Kiểm 6 lỗi báo đã sửa (G7, G8, G10, G24, G27, G35) có trên HEAD + test tương ứng · nặng:1 · ✅ · 8 commit trên HEAD, 11 file test 331 qua → sổ lỗi FIXED_UNVERIFIED
- [ ] M0.3 · Chốt D01–D10: người dùng chọn từng mục trong docs/V3_1_D01_D10_CHO_DUYET_2026-10-20.md, rồi ghi sổ + test · nặng:1 · ✅ · người dùng chốt 20/10; sổ v31-d01…v31-d10 + test_v31_d01_to_d10_recorded_as_policy_not_implementation
- [ ] M0.4 · Schema sổ lỗi devsys/errors.json + test hợp đồng (mã không trùng, VERIFIED cần commit+test+bằng chứng, OPEN cần workstream) · nặng:2 · ✅ · cloud-B C-M04-05 gộp 20/10: devsys/errors.json 86 mục (G25 khuyết) + errors.py check; cả bộ 6293 qua
- [ ] M0.5 · Nhập G1–G58, A1–A15, B1–B12 có nguồn; báo cáo coverage 100 % (G25 khuyết ghi rõ) · nặng:2 · ✅ · cloud-B C-M04-05 gộp 20/10: devsys/errors.json 86 mục (G25 khuyết) + errors.py check; cả bộ 6293 qua
- [ ] M0.6 · Bảng AS-IS/TO-BE WS0–WS6 theo file:hàm (IMPL/PART/MISS/UNK) · nặng:2 · ✅ · cloud tài khoản khác, gộp 20/10 (e43acf20…e767e9d3); rà nhẹ (chỉ tài liệu)
- [ ] M0.7 · Ma trận test bắt buộc cho từng milestone theo CHUAN_XAY_DUNG + devsys/areas.json · nặng:1 · ✅ · cloud tài khoản khác, gộp 20/10 (e43acf20…e767e9d3); rà nhẹ (chỉ tài liệu)
- [ ] M0.8 · AI Dev System: trang sơ đồ tiến độ vẽ từ kế hoạch + sổ khâu (+ sổ lỗi khi có), tô màu theo trạng thái việc · nặng:2 · ✅ · người dùng yêu cầu trực tiếp 20/10; devsys/plan_map.py + trang 🗺; quy ước 7 đã rà, 11 lỗi đã sửa
- [ ] M0.9 · Thiết kế Kho forms/outfit/hair/face + provenance theo 6 điều kiện M2.3 (schema version, adapter v1/v2, kế hoạch migration, regression) — chỉ tài liệu · nặng:2 · ✅ · cloud tài khoản khác, gộp 20/10 (e43acf20…e767e9d3); rà nhẹ (chỉ tài liệu)
- [ ] M0.10 · Đặc tả AUTO/USER_LOCKED/REVIEW_REQUIRED + audit MỌI đường ghi scenes.data/Kho thật (file:hàm) + thiết kế test — chỉ tài liệu · nặng:2 · ✅ · cloud tài khoản khác, gộp 20/10 (e43acf20…e767e9d3); rà nhẹ (chỉ tài liệu)
- [ ] M0.11 · Test plan + tiêu chí 3 vòng pilot (A offline, B 5–8 shot, C 20–40 shot) + dự toán B/C — chỉ tài liệu · nặng:1 · ✅ · cloud tài khoản khác, gộp 20/10 (e43acf20…e767e9d3); rà nhẹ (chỉ tài liệu)
- [ ] M0.12 · Gói xin duyệt phạm vi M1 (file/module, hợp đồng, tác động đường cũ, test, cờ/rollback, chi phí) — Cấp 2 · nặng:1 · ✅ · người dùng duyệt 20/10: docs/V3_1_GOI_DUYET_CAP2_CAP3_2026-10-20.md mục C; sổ v31-cap2-milestone-packages-approved + v31-cap3-items-decided

### M1 — Nền tin cậy (0 USD, provider giả)
- [ ] M1.1 · Parser vat v1 str→{vat} cho qc_observe (R3, #31 shot 30) · nặng:1 · ✅ · gộp 36fcb4bd (20/10); cả bộ not-slow 6136 qua; FIXED_UNVERIFIED tới khi QC thật chạy #30/#31 (#31 còn thiếu hồ sơ LÍNH ĐỊCH ÁO CHOÀNG — dữ liệu Kho)
- [ ] M1.2 · Succeed/poll nguyên tử liên tiến trình + ghi tệp tạm rồi đổi tên (A1, A15) · nặng:3 · ✅ · gộp 60b9da80 (20/10; cả bộ 6222 qua, 1 test UI chập chờn qua khi chạy riêng); cờ poll_claim BẬT máy chính 20/10 (C3-2); FIXED_UNVERIFIED tới khi chạy thật
- [ ] M1.3 · Kiểm tạm dừng ngay trước provider.submit, cả đường thử lại/lùi model (G36) · nặng:2 · ✅ · gộp 60b9da80; cờ pause_before_submit BẬT máy chính 20/10 (C3-2); còn mở: vì sao lần thử lại đầu vẫn đi Seedance
- [ ] M1.4 · Provider Claude theo dự án, clean_env bỏ key API, hết lượt gói = dừng có giờ mở (A2, A3, A13, G33, G57) · nặng:3 · ✅ · M1.4a 222bf9c5 + M1.4b (cloud-B code, cloud-C rà kỹ 1 CAO + 4 VỪA đã sửa) gộp 20/10 dde800b4, cả bộ 6361 qua; migration cột provider ĐÃ áp CSDL máy chính 20/10 (C3-1, sao lưu trước) — FIXED_UNVERIFIED tới khi chạy thật
- [ ] M1.5 · Kiểm Kho chủ thể trước gửi video, dừng + đề xuất dọn (G30, G32, G58) · nặng:2 · ✅ · CX20-5+5b gộp 21/10 (tích hợp 14a65fd4), cờ subject_capacity_guard TẮT, xóa chỉ DRY-RUN; rà kỹ: 1 VỪA (processing NULL) + 3 THẤP → CX21-FIX
- [ ] M1.6 · Ước tính giá đúng gói gửi: tier nháp, phụ phí ref, nâng 1080p, claude_cli = 0, giá video trong pregen_check (A7–A9, G31) · nặng:2 · ✅ · gộp 20/10 (cloud-B code + cloud-C C-FIX + phiên chính sửa CAO thẻ clip v2), cờ send_estimate TẮT; cả bộ 6470 qua — bật cờ = xin người dùng
- [ ] M1.7 · Dashboard báo chạy code cũ (G55), gộp diag lặp (G56), regen kiểm data_dir (G39), thông điệp ngân sách (A14 theo D01) · nặng:1 · ✅ · gộp 20/10 (cloud-B + C-FIX báo code cũ theo dấu vân tay file), cờ TẮT; cả bộ 6470 qua
- [ ] M1.8 · tools/project_error_report.py: gom diag_events + jobs + job_events thành đề xuất mục sổ lỗi cuối dự án · nặng:2 · ✅ · Codex Đ20 việc 1 gộp 20/10 (tools/project_error_report.py, 9 test)
- [ ] M1.9 · Golden gói B0–B2: replay ảnh + video, test compatibility / correctness, fixture có HEAD/cờ/CHANGES · nặng:3 · 🔄 · EP 21/10 duyệt cổng mới so A/B (sổ v31-ep-golden-ab-acceptance-2026-10-21) sau 4 lần không đạt so lịch sử → C-GOLDEN5 + CX21-GOLDEN5 · CX20-2b gộp 21/10 (14a65fd4, rà kỹ đạt, 3 THẤP → CX21-FIX); nghiệm thu lần 1+2 21/10 KHÔNG ĐẠT (0 CODE_MISMATCH; lần 2: 68/68 thiếu đầu vào — final theo draft_job_id, định nghĩa COMPAT vs 83 cờ BẬT, model theo job, pregen_fingerprint) → C-GOLDEN2 cloud-C; chưa gộp nhánh M2 tới khi đạt · CX20-2 khung chụp/so gộp 20/10; CX20-2b replay mức _build_package đang làm (Codex) → phiên chính chụp #24/#27 → mở M2

### M2 — Hợp đồng sản xuất có cấu trúc
- [ ] M2.1 · BYĐ v2: byd_v, vat[] object, shot_intent.read có provenance, mức BLOCK/REVIEW/WARN · nặng:3 · ⬜
- [ ] M2.2 · Field readers A2a–A2f + byd vào lineage khi cờ bật (G4, G22) · nặng:3 · ⬜
- [ ] M2.3 · Triển khai Kho forms/outfit/hair/face (G38) theo thiết kế M0.9 — code Cấp 2, backfill/migration Cấp 3 · nặng:2 · ⬜ · G2-3 duyệt có ĐK (sau M0.9, M0.10, M1.9); backfill = C3-5 chỉ khảo sát + nháp
- [ ] M2.4 · insert_scene_after kế thừa bối cảnh + BYĐ DRAFT; chỉ mang đạo cụ có trong BYĐ (G6, G21, G1) · nặng:2 · ⬜
- [ ] M2.5 · Triển khai AUTO/USER_LOCKED/REVIEW_REQUIRED mọi đường ghi theo đặc tả M0.10 (A4), shadow trước — Cấp 2 · nặng:2 · ⬜ · G2-3 duyệt có ĐK (shadow); enforce = C3-6 để sau
- [ ] M2.6 · sent_package nhãn theo rel_path/asset_id (G5) · nặng:1 · ⬜
- [ ] M2.7 · Image preflight trong ImageRunner._pregen, chung mã lỗi với video_pregen · nặng:3 · ⬜
- [ ] M2.8 · Router theo khả năng model: không gộp nhóm khi cần khung đầu (G28, G37, B9); ngân sách ký tự (G13, G54) · nặng:2 · ⬜
- [ ] M2.9 · Lời dẫn ngoài khớp môi mọi caller (G15–G17, G53); fit_durations hiện danh sách duyệt (G14); thông điệp khung cuối (A11); BYĐ qua claude_cli (A12) · nặng:2 · ⬜
- [ ] M2.10 · Gói gửi tối giản (người dùng 21/10): prompt ngắn ref-first (mỗi tài nguyên 1 dòng vai trò + 2–4 câu hành động/máy, không tả lại thứ ảnh đã có) + BỘ ẢNH tham chiếu tối ưu theo shot (đúng vai, bỏ ref thừa / trùng / mâu thuẫn — video có khung đầu không gửi lại ảnh nhân vật/bối cảnh trùng khung) + cách dùng kết hợp; đo 0 USD trên gói thật #31/#33 → builder lean SHADOW cờ TẮT → A/B pilot (Cấp 3) · nặng:3 · ⬜ · số đo 21/10: ảnh #31 TB 5.380 ký tự / 6,2 ref, #33 11.059 ký tự; video #31 3.029 ký tự, video tới 15 ref, 9 ref trùng sha; Weave Canvas: prompt video 1 câu + khung đầu/cuối

### M3 — Thế giới và liên tục
- [ ] M3.1 · scene_world_map thử nghiệm (3D hoặc 2D, UNKNOWN, version/provenance, người duyệt map) trên #31/#33 — sau khi M3 được duyệt, không bật production · nặng:3 · ✅ · DP8 cloud-D gộp 21/10 (core/world_map.py, cờ world_map TẮT, offline, JSON tệp); THẤP byd 3D → C-FIX-THAP-5
- [ ] M3.2 · Người nộm height_m trong whitebox; pitch eye/slightly_high; kiểm depth che (G2, G3, A10, G49) · nặng:2 · ✅ · gộp 21/10 (14a65fd4), cờ TẮT, rà nhẹ (báo cáo cloud/codex + test xanh)
- [ ] M3.3 · Câu vị trí sinh từ world map, không tả tay từng shot (G41–G50, G46) · nặng:3 · ✅ · gộp 21/10 (14a65fd4), cờ TẮT, rà nhẹ (báo cáo cloud/codex + test xanh)
- [ ] M3.4 · continuity_state expected/observed/resolved + đồ thị phụ thuộc theo thực thể · nặng:3 · ✅ · gộp 21/10 (14a65fd4), cờ TẮT, rà nhẹ (báo cáo cloud/codex + test xanh)
- [ ] M3.5 · Bỏ kiểm chân trời khi nền không có trời (G20) · nặng:1 · ✅ · DP2 cloud-C gộp 20/10, cờ horizon_needs_sky TẮT (bật = xin người dùng sau C-FIX-THAP-1)

### M4 — QC có bằng chứng và Dashboard
- [ ] M4.1 · Schema bằng chứng QC + mã lỗi thống nhất · nặng:2 · ✅ · DP4 cloud-C gộp 20/10 (core/qc_evidence.py, cờ qc_evidence TẮT; bảng mới chỉ migrate tay)
- [ ] M4.2 · Video QC: đứng yên > 1,5 s = REVIEW, khớp khung 0, vật còn giữ (G51); chuyển cảnh trong video ref (B8) · nặng:2 · ✅ · C-M42 cloud-C gộp 20/10, cờ video_qc_shadow TẮT, chỉ ghi REVIEW
- [ ] M4.3 · Cross-shot logic qua qc_sequence_logic ở chế độ shadow (G52, G42) · nặng:2 · ✅ · C-M43 cloud-C gộp 20/10, cờ continuity_shadow TẮT, chỉ ghi REVIEW
- [ ] M4.4 · Final QC blackdetect/freezedetect · nặng:1 · ✅ · DP3 cloud-C gộp 20/10, cờ final_black_freeze TẮT (chỉ warn); sửa end_hold → C-FIX-DP345
- [ ] M4.5 · Sửa báo nhầm A5 (qua vai), A6 (thiếu ref_video_path) + regression · nặng:1 · ✅ · DP1 cloud-C gộp 20/10, cờ qc_false_alarm_fix TẮT (bật = xin người dùng sau C-FIX-THAP-1)
- [ ] M4.6 · Benchmark độc lập theo mã lỗi (≥ 20 lỗi + 20 đạt mỗi nhóm luật) · nặng:2 · ✅ · gộp 21/10 (14a65fd4), cờ TẮT, rà nhẹ (báo cáo cloud/codex + test xanh)
- [ ] M4.7 · Dashboard: BYĐ, thẻ gói sẽ gửi, sổ lỗi, overrides + siết 3 cổng (Q6) · nặng:3 · 🔄 · phần XEM (C-M47A cloud-C) gộp 21/10, cờ TẮT; overrides = C3-4 chờ
- [ ] M4.8 · Bàn đạo diễn 3D trên Dashboard (thêm 21/10 — người dùng hỏi vì sao V3.1 thiếu): (a) màn XEM chỉ đọc cờ stage_view_ui (C-STAGE-VIEW cloud-E); (b) phương án + nút thao tác (chia vai, duyệt/trả lại, previs, render lại nền, chọn phương án máy) — kế hoạch riêng chờ duyệt Cấp 2 · nặng:3 · 🔄 · EP 21/10 chốt S-A…S-G (sổ v31-ep-stage-desk-actions-2026-10-21): phương án A theo đợt — Đợt 1 nút 0 USD làm được, nút API = Cấp 3 · K5 'Claude/người dùng xem tấm ghép trên Dashboard' đã duyệt 15/10 (stage-auto-plan Q3) nhưng chưa từng làm

### M5 — Sửa chọn lọc và pilot
- [ ] M5.1 · Repair router theo mã lỗi, trần ảnh ≤ 3 / video ≤ 2, dừng khi đổi ý đồ · nặng:3 · ✅ · DP5 cloud-C gộp 20/10, cờ repair_router TẮT, chỉ đề xuất (tự gửi = C3-10 để sau)
- [ ] M5.2 · Release gate: shot duyệt, final QC, đối soát chi phí, lỗi nghiêm trọng mở = 0 hoặc có miễn trừ ký tên · nặng:2 · ✅ · DP6 cloud-C gộp 20/10, cờ release_gate TẮT (chỉ cảnh báo, không chặn xuất)
- [ ] M5.3 · Pilot vòng A Offline Regression: replay lỗi #31/#33 (payload, continuity, QC, lineage, phục hồi), 0 USD · nặng:2 · 🔄 · DP12 khung tools/pilot_a.py gộp 21/10 (rà nhẹ, 0 USD); còn CHẠY vòng A ở máy chính sau golden đạt
- [ ] M5.4 · Pilot vòng B 5–8 shot, duyệt từng đợt — dự toán + người dùng đồng ý trước API trả phí (Cấp 3) · nặng:2 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — C3-11 duyệt nguyên tắc, CHƯA duyệt chi tiêu
- [ ] M5.5 · Pilot vòng C 20–40 shot: chất lượng, tỉ lệ gen lại, continuity, chi phí, can thiệp tay (Cấp 3) · nặng:2 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — C3-12 để sau

### M6 — Tổ làm phim có chủ (AI Video Production Team)
- [ ] M6.0 · Audit vai trò, caller tạo job, đường ghi theo vai, hiệu suất Dashboard (P0); sổ quyết định M6; check "Kỹ sư không ghi nội dung production" · nặng:1 · 🔄 · 21/10: kế hoạch docs/KE_HOACH_TO_LAM_PHIM_CO_CHU_2026-10-21.md mục 0 (E1–E7: lượt gen/shot, Claude/khâu, lineage.summary #31 7,6–11,3 s); sổ v31-m6-*; còn audit caller + profiling đủ khối · ưu tiên 1/13 (EP Q6 21/10)
- [ ] M6.1 · Role Registry data/crew_roles.json + core/crew.py (đọc): quyền đọc/ghi, đầu vào/ra, công cụ, nghiệm thu, lỗi phụ trách, leo thang · nặng:2 · ⬜ · DUYỆT Cấp 2 Gói M6-A 21/10 (sổ v31-ep-m6-pack-a-approved-2026-10-21; cờ TẮT, shadow, 0 USD) · Gói M6-A (trình khi EP chốt Q3) · ưu tiên 2/13 (EP Q6 21/10)
- [ ] M6.2 · Handoff Contract shadow (jsonl): id dự án/shot, revision, phụ thuộc, sản phẩm, bằng chứng QC, trạng thái duyệt · nặng:2 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — cần M1.9, M2.6 · ưu tiên 6/13 (EP Q6 21/10)
- [ ] M6.3 · Generation Authorization + Repair Budget dùng chung trước provider.submit (ảnh 3 / video 2 lượt, không đặt lại, 6 điều kiện) — shadow trước · nặng:3 · ⬜ · DUYỆT Cấp 2 Gói M6-A 21/10 (sổ v31-ep-m6-pack-a-approved-2026-10-21; cờ TẮT, shadow, 0 USD) · cần M1.2/M1.3/M1.6/M5.1 (đã ✅); EP chốt 21/10: Q1 nâng 1080p không tính lượt, Q2 EP bấm có trừ lượt, Q4 cho lùi model trong danh sách duyệt; còn chờ Q3 ngân sách tự sửa (đề xuất 40 % tiền lượt đầu) · Gói M6-A · ưu tiên 3/13 (EP Q6 21/10)
- [ ] M6.4 · Write guard theo vai (actor = role trong guard M2.5), mỗi trường một vai chủ · nặng:2 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — cần M2.5 gộp · ưu tiên 7/13 (EP Q6 21/10)
- [ ] M6.5 · Video Prompt Artist dưới Director: BYĐ v2 + ảnh duyệt + ràng buộc model → prompt + coverage; code chỉ kiểm; Shadow so prompt builder cũ · nặng:3 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — cần M2.1, M1.9 · ưu tiên 5/13 (EP Q6 21/10)
- [ ] M6.6 · Storyboard Artist: ảnh khung đầu nhìn plate + Kho, tự kiểm có bằng chứng độc lập; Shadow · nặng:2 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — cần M2.1, M2.7 · ưu tiên 8/13 (EP Q6 21/10)
- [ ] M6.7 · 3D Artist: đứng tên sân khấu / plate / world map khi có, nhận phiếu nền lệch · nặng:2 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — cần M3.1–M3.3, M4.8 · ưu tiên 11/13 (EP Q6 21/10)
- [ ] M6.8 · Sound Designer + Editor/VFX: TTS/SFX/nhạc/khớp môi; ghép VFX + dựng kiểu #27 thành khâu Bước 5 · nặng:2 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — cần M2.9, M4.4 · ưu tiên 10/13 (EP Q6 21/10)
- [ ] M6.9 · Continuity Validator (năng lực, code trước): continuity_state + qc_evidence + định tuyến lỗi về vai chủ · nặng:2 · ⬜ · DUYỆT Cấp 2 Gói M6-A 21/10 (sổ v31-ep-m6-pack-a-approved-2026-10-21; cờ TẮT, shadow, 0 USD) · M3.4/M4.1/M4.3 đã ✅ · Gói M6-A · ưu tiên 4/13 (EP Q6 21/10)
- [ ] M6.10 · Dashboard điều phối cho Executive Producer: sửa theo vai, yêu cầu ngôn ngữ tự nhiên, phiếu lỗi, payload, so phiên bản, lượt + ngân sách, duyệt vượt quyền · nặng:3 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — cần M4.7, M6.1–M6.3 · ưu tiên 9/13 (EP Q6 21/10)
- [ ] M6.11 · Tốc độ Dashboard theo profiling: nhớ lineage giữa lần vẽ lại, đo từng khối, fragment + nạp lười; chỉ số thời gian tới shot đạt chuẩn · nặng:2 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — EP Q5 21/10: chưa làm, chờ các việc V3.1 M1–M5 hoàn thành; số đo E5 giữ làm mốc · ưu tiên 12/13 (EP Q6 21/10)
- [ ] M6.12 · Replay offline #24/#27/#31 + pilot có kiểm soát + nghiệm thu thực tế (pilot trả phí = Cấp 3) · nặng:2 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — cần M5.3, M6.3, M6.5, M6.6 · ưu tiên 13/13 (EP Q6 21/10)

### M7 — Cờ và cấu hình (Executive Producer chốt 21/10)
> Nguồn: `docs/CAU_HOI_CHOT_TONG_HOP_2026-10-21.md` + văn bản "QUYẾT ĐỊNH EXECUTIVE PRODUCER — TỔNG HỢP V3.1 VÀ M6" (21/10); sổ `v31-ep-*-2026-10-21`.
> Bằng chứng: `docs/DANH_GIA_HIEU_QUA_CO_2026-10-21.md`, `docs/BANG_CHUNG_CHOT_CO_2026-10-21.md`, `docs/KE_HOACH_SUA_20_CO_2026-10-21.md`.
> Mỗi gói: test, bằng chứng thực thi, acceptance criteria, rollback, rủi ro mở. Đổi trạng thái cờ production / khóa cờ = Cấp 3 TỪNG CỜ (trình bằng chứng).
- [ ] M7.1 · Gói A sửa cờ (F-A): change_review đóng cổng khi rà lỗi (G35), hero_takes khai costs, director_rewrite respect_lock (trường người sửa), chat_prompts kiểm D6 + hết tiền · nặng:3 · ⬜ · Cấp 2 DUYỆT 21/10; đổi trạng thái cờ = Cấp 3
- [ ] M7.2 · Baseline cờ chỉ khi chưa có cấu hình riêng (K4 b) + effective config + config hash + cảnh báo drift; nút reset có preview / xác nhận / sao lưu / khôi phục (K6) · nặng:2 · ✅ · C-M72 + C-M72-FIX gộp 21/10 (rà kỹ: 0/144 cờ đổi máy có cài đặt; 2 lỗi đã sửa; cả bộ 6937 qua) · Cấp 2 DUYỆT 21/10; song song M7.4, nghiệm thu tích hợp trước khi khóa cờ môi trường khác (K5)
- [ ] M7.3 · seedance_ref_groups + end_frames cùng hoạt động (K3 b, B4 end_frames.py:32) · nặng:2 · ⬜ · Cấp 2 DUYỆT 21/10
- [ ] M7.4 · Gói B sửa cờ (F-B): video_gate, two_tier_quality (±5 % + tiêu chí chất lượng), motion_consistency_lint, end_frames, scene_qc, lip_sync + dialogue_take, bg_autoqc… · nặng:3 · ⬜ · Cấp 2 DUYỆT 21/10; khóa từng cờ sau correctness + benchmark + chi phí
- [ ] M7.5 · Gói C (F-C): audit + thiết kế + BẢNG QUYẾT ĐỊNH từng cờ (audio_first tùy chọn thử nghiệm — F-Q2) trình EP trước khi đổi hành vi production · nặng:1 · ✅ · C-M75 bảng quyết định Gói C gộp 21/10 (KE_HOACH_SUA_20_CO mục 6) — TRÌNH EP duyệt từng dòng · chỉ tài liệu
- [ ] M7.6 · Test không phụ thuộc mặc định 8 cờ đề nghị khóa (155 test nhóm A) · nặng:2 · ✅ · C-FLAGTEST8 cloud-C gộp 21/10: cả bộ 6914 qua; ép 8 cờ khóa BẬT 164 → 7 đỏ (đều là test "cờ mặc định TẮT" — đổi khi khóa thật)
- [ ] M7.7 · Kiểm chứng + khóa TỪNG cờ: K1 send_claim, back_view_guard (dependency, 2 worker, crash/reconcile, replay production); K2 video_pregen, chat_first, framing_guard, stage_camera, plate_view_sentence (+ two_tier_quality, video_gate sau M7.4); K7 bốn cờ chỉ-ghi (stale_code_alarm, diag_merge, budget_notice_d01, send_estimate) · nặng:2 · ⬜ · CHỜ PHỤ THUỘC / BẰNG CHỨNG (chưa cần EP quyết; khi đủ điều kiện phiên chính mới trình) — Cấp 3 từng cờ — trình khi đủ bằng chứng; refusal_skip_same_picture CHƯA bật; qc_false_alarm_fix + horizon_needs_sky chờ replay #31/#33
- [ ] M7.8 · Kiểm tuyến QC thay thế rồi trình tắt scene_qc_claude (Cấp 3 riêng) · nặng:1 · ⬜ · F-A: tắt KHÔNG nằm trong duyệt code

## 6. Nhật ký

- 21/10 (sau): EP trả lời M6 — Q1 nâng nháp 480p→1080p KHÔNG tính lượt; Q2 EP tự bấm gen lại CÓ trừ lượt; Q4 CÓ cho lùi model tự động trong danh sách duyệt; Q5 M6.11 tốc độ chưa làm, chờ M1–M5 xong; Q6 thứ tự ưu tiên 1–13 + Gói M6-A (M6.1, M6.3, M6.9) / M6-B (sau golden + M2) / M6-C. Q3 (ngân sách tự sửa) đã giải thích bằng số #27/#31, chờ EP chọn. Sổ: `v31-m6-generation-limits-policy-b-2026-10-21` thay bản đầu.

- 21/10: Executive Producer gửi "PHÊ DUYỆT KIẾN TRÚC M6 — AI VIDEO PRODUCTION TEAM" (chốt định hướng, chưa duyệt code) → thêm M6 (mục 3, 4b, 5), kế hoạch `docs/KE_HOACH_TO_LAM_PHIM_CO_CHU_2026-10-21.md`, sổ `v31-m6-crew-architecture-2026-10-21` + `v31-m6-generation-limits-policy-2026-10-21`, `devsys/plan_map.json` gắn khâu M6. Lệch cần chốt: trần code hiện = TỰ gen lại 3/2 (tổng 4/3, đặt lại khi người bấm) ≠ chính sách mới tổng 3/2 không đặt lại → khi triển khai M6.3 ghi D01c thay D01b. Dừng, chờ EP đánh giá.

- 20/10 (tối): người dùng 'CHỈ ĐẠO XỬ LÝ RỦI RO V3.1 VÀ KẾ HOẠCH S' → `docs/V3_1_GOI_SUA_VA_RUI_RO_2026-10-20.md`: gói M1.1 (vat v1, chỉ `qc_observe` crash; dữ liệu thật #30 ×4, #31 idx 33), audit đường gọi Claude + biện pháp tạm + gói M1.4 (key Anthropic có ở biến User; an toàn nhờ chặn hết tiền), gói M1.5 + phương án Kho chủ thể chạy song song + quyết định `v31-d03b` (tự dọn nháp cũ / dự án xong-cất > 3 ngày; thay `v31-d03`), lỗi mới G59 (tự dọn Kho 13/10 chưa từng chạy được), regression lời dẫn M2.9, đối soát giá 1080p (6,36 = riêng bước nâng, tính theo token; 2,80 = ước tính ClipAI lúc gửi), ma trận 6 rủi ro, bảng 14 việc S (không phải 16), thứ tự build. Chờ duyệt phạm vi code.

- 20/10 (sau): người dùng chốt D01–D10 (văn bản "PHÊ DUYỆT D01–D10") → sổ `v31-d01`…`v31-d10`; D04/D05/D06 `replaces` 3 mục định hướng cùng ngày; điều kiện bổ sung vào mục 4a. M0.3 ✅. Dừng: chờ người dùng duyệt gói triển khai tiếp theo.

- 20/10: người dùng gửi văn bản quyết định V3.1 → ghi 5 mục sổ (mục 4b), bảng D01–D10 chờ duyệt, tách việc thiết kế Cấp 1 (M0.9–M0.12) khỏi triển khai; M0.4/M0.5 ⏸ chờ duyệt phạm vi + D09; pilot tách 3 vòng (M5.3–M5.5). Dừng ở đây theo văn bản: không tự triển khai code pipeline, không gọi API trả phí.

- 20/10: chuyển PDF V3.1 vào repo, đánh giá (mục 1), đăng ký `devsys/plans.json` id `V31` (`"chinh": true` → trang "Kế hoạch đang chạy" của AI Dev System đọc kế hoạch này; kế hoạch S vẫn ở bảng mọi kế hoạch).
- 20/10: M0.1 + M0.2 xong (biên bản `docs/audit/M0_BASELINE_2026-10-20.md`); M0.8 trang "🗺 Sơ đồ tiến độ" (`devsys/plan_map.py`).
