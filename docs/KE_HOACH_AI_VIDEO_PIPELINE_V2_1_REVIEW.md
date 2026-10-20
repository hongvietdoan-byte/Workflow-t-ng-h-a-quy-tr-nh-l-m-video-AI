# Kế hoạch AI Video Pipeline V2.1 — Bản rà soát cập nhật R2 (17/10/2026; xác minh baseline 18/10)

> **Trạng thái: CHỈ AUDIT + KẾ HOẠCH. CHƯA DUYỆT, CHƯA TRIỂN KHAI.** Không sửa code production, không migration, không bật cờ, không gọi
> dịch vụ có phí. Đề bài: `docs/handoff/YEU_CAU_V2_1_2026-10-17.txt`. Kế hoạch gốc (không sửa): `docs/KE_HOACH_TRUONG_CAU_TRUC_VA_HOI_QUY_GOI_2026-10.md`
> (gọi tắt **KH-gốc**, tham chiếu theo mục §). Tài liệu này **chỉ ghi phần thay đổi / bổ sung**; phần nào không nhắc thì giữ nguyên KH-gốc.
>
> Mốc code kiểm: `main` = `b39e005b` (worktree audit). Không có `data/` thật trong worktree → mọi kết luận cần CSDL / cờ máy chính ghi
> **UNKNOWN** kèm lý do. Test chạy offline duy nhất: `tests/test_replay_payload_p30.py` + `tests/test_shot_intent*.py` → 35 qua (3,7 s).

Ký hiệu trạng thái: **IMPL** = IMPLEMENTED · **PART** = PARTIAL · **MISS** = MISSING · **UNK** = UNKNOWN.

---

> **Cập nhật R2 — nguồn: ghi chú 17/10 tối trong chính tài liệu:** báo cáo cho biết nhánh `claude/wizardly-elbakyan-596555` và sửa POV `4775eab4` **đã gộp main**, 6.096 test qua. Đây là **trạng thái được báo cáo**, chưa được xác minh lại trên repository trong lần biên tập R2. Các bảng audit tại `b39e005b` bên dưới là **ảnh chụp lịch sử**, không được dùng làm kết luận về HEAD hiện tại. **Q5 được coi là thỏa theo báo cáo, nhưng phải xác minh HEAD/ancestry và test trước B1.**

> **Xác minh R2 — 18/10 (phiên ai-video-pipeline-upgrade-plan-04b569, chỉ đọc, 0 USD; biên bản `docs/audit/P1_BASELINE_VERIFICATION.md`):** HEAD `186a2cc9` chứa POV `4775eab4` (ancestry) và toàn bộ nội dung nhánh wizardly (SHA `3a2a6eb9` bị làm phẳng khi rebase — kiểm theo nội dung: trigger `trg_scene_noi_chon(_new)` có trong code **và** trong CSDL máy chính, `sync_noi_chon`, quyết định `time-weather-single-source-2026-10-17`, `tools/pregen_check.py`); 11 file test nền 244 qua → **Q5 ĐÃ THỎA**. Cờ máy chính, dữ liệu #24/#27/#31 đã chụp mốc. **Phát hiện mới:** `qc_observe_enum` đang **BẬT** ở máy chính và #31 shot 30 có `byd.vat = ["AWM"]` (chuỗi) → R3 đang xảy ra (QC shot đó luôn lỗi `BYĐ.vat thiếu vật chuẩn`), xem §9 R3.

## 1. Executive Summary

1. **Hướng KH-gốc đúng, nhưng 6 giả định cần sửa** trước khi làm (chi tiết §11):
   (a) B4 phải so với `jobs.sent_package` (gói đầy đủ, có sha) chứ không phải `jobs.sent_refs`; (b) L12 **đã có** lớp kiểm trước trả tiền
   (`video_pregen`, cờ chưa `verified`), chỉ **ảnh (L8) là không có** (`runner._Runner._pregen` trả False); (c) Kho **không có** trường
   `forms` có cấu trúc — enum `dang` ở A1 phụ thuộc Q3; (d) `vat[]` chưa từng có schema (prompt 31 không định nghĩa, `validate` không kiểm
   hình dạng) và `qc_observe` đã giả định `vat[]` là dict có khóa `vat` → **lỗi ngầm** khi bật `qc_observe_enum`; (e) `lineage` không đưa
   `byd` vào vân tay ảnh/clip → khi `byd_fields` điều khiển gói, sửa BYĐ sẽ **không** làm ảnh "⚠ cũ"; (f) Q2 **đã được chốt trên nhánh
   chưa gộp** (`time-weather-single-source-2026-10-17` + trigger CSDL đồng bộ), cách làm khác KH-gốc (đồng bộ bản chép, không "bỏ").
2. **Không cần xây Continuity Engine mới.** Phần lõi trạng thái đã có rải rác: `lineage` (vân tay + stale), `end_frames` (khung cuối +
   vân tay `end_state`), `layout_follow` (`continuity_from`), `side_truth` / `travel_truth` / `stage_facts` (sự thật hình học do code viết).
   `core/continuity.py` thì chỉ là cảnh báo regex. Phần D thiết kế lớp **Expected/Observed/Resolved state** mỏng nối các module này.
3. **QC đã có nhiều mảnh** (autoqc, qc_scene, qc_team + qc_golden benchmark, video_qc_context, clip_measure, plate_layout_qc,
   camera_match_qc, final_qc). Thiếu: preflight ảnh (L8), mã lỗi thống nhất, kiểm khung đen/đứng hình, cross-shot state, export Premiere.
4. **Thứ tự khuyến nghị:** P0 (tài liệu này) → P1 = B0–B2 (golden, 0 USD) → P2 = A0–A3 → P3 = B4/A5/C → P4 = D+E (thiết kế→benchmark) → P5 = F.
   **P1-B1 chỉ bắt đầu sau khi xác minh trên máy chính rằng hai thay đổi Q5 đã có trong HEAD, cờ máy chính đã được snapshot và các test nền đạt** (trigger có thể đổi `scenes.data` — fixture chụp sai mốc sẽ lệch).

## 2. Current Architecture Verification (Phase 0)

### 2.1 Luồng thật BYĐ → gửi model → QC → dựng

| # | Bước | Module (file:hàm) | Vào → Ra | Cờ | Kiểm trước trả tiền | Retry / resume / dấu vết | TT |
|---|---|---|---|---|---|---|---|
| 1 | Đạo diễn khai BYĐ | `core/director_byd.py:settle` (dòng 115–161), `prompts/31_director_byd.md` | shot plan → `scenes.data.byd` + `byd_kiem` | `shot_intent` (`verified: False`, features.py:560) | `shot_intent.validate` (schema + kho_id có thật) ≤ `MAX_ROUNDS` vòng, sổ chi `director_byd` | `byd_kiem.vong`, ⚙ diag | IMPL |
| 2 | Schema BYĐ | `core/shot_intent.py:validate` (193–234), `from_shot_spec` (237) | dict → issues do/vang | — | — | — | PART: không `byd_v`; `vat[]` không kiểm hình dạng; `dang` chữ tự do (104–121) |
| 3 | Asset resolution (nhân vật/dạng) | `core/assets.py:1703` → `character_forms.for_shot` (66–92) | chữ shot + mô tả Kho style (`_DECLARE` regex, dòng 23) → form | — | không | — | PART (đọc chữ, không đọc `byd.dang`) |
| 4 | Asset resolution (đạo cụ) | `core/prop_lock.py:locks/_holders/_present` (235–260, 378), `characters.weapon_asset_id` (`set_weapon` 218) | khóa súng theo dự án (cấu trúc) + người có mặt theo chữ (`_GUN_ACTION` 261) | `project_prop_lock` | không | — | PART |
| 5 | Chọn ảnh Kho | `assets._named_extras` (1815), `scene_storyboard.shared_references` (190), `_USES_HELD` (240) | khớp tên bỏ dấu | — | không | — | PART (chữ) |
| 6 | Lắp gói ảnh (L8) | `core/runner.py:ImageRunner._submit_args` (class 3183), khóa nhân vật 2834–2890 (`lock_exceptions` đọc `byd.ngoai_le`) | scene → (prompt, refs) | nhiều | **không**: `_Runner._pregen` trả False (runner.py:601–603) | `jobs.sent_refs`, `jobs.sent_package` (`_write_sent_package` 609) | PART |
| 7 | Lắp gói video (L12) | `VideoRunner._submit_args` (1911), `_pregen` (932) → `core/video_pregen.py` | motion + khung đầu/cuối + ref | `video_pregen` (`verified: False`) | **có** (khung đầu sha, khung cuối ↔ `byd.hanh_dong.ket_thuc`, thời lượng, ref, vân tay) | cùng builder `_build_package` (579) | PART (cờ chưa kiểm thật) |
| 8 | Gửi / chống gửi trùng | `submit_pending` (366) + `core/send_claim.py` | job queued → external_id | `send_claim` (`verified: False`) | `change_review` hold, `video_gate` | `jobs.retry_count/retry_reason/parent_job_id/reject_reason`, `usage_events(job_id)` | IMPL |
| 9 | QC ảnh | `core/autoqc.py`, `qc_scene.py`, `qc_team.py`, `qc_observe.py`, `plate_layout_qc.py`, `camera_match_qc.py` | ảnh → điểm/nhãn | `scene_qc`, `qc_team` (TẮT 14/10), `qc_observe_enum` (opt-in) | — | `reviews.json` (data_dir) | PART |
| 10 | QC video | `video_qc_context.py`, `clip_measure.measure` (463), `video_analysis.py` | clip → số đo | — | — | — | PART |
| 11 | Stale / lineage | `core/lineage.py:_scan` (214), `IMAGE_KEYS` / `IMAGE_SHOT_KEYS` / `MOTION_SHOT_KEYS` (14–25) | vân tay đầu vào ↔ hiện tại | — | — | `jobs.input_hash` | IMPL (nhưng **không có `byd`** trong khóa) |
| 12 | Dựng / timeline | `final_cut.py`, `rough_cut.py`, `timeline_view.py`, `ffmpeg_studio.py`, `delivery.py` | clip → bản giao | `rough_cut_review` | — | `outputs` (vân tay) | IMPL |
| 13 | QC bản cuối | `core/final_qc.py:run` (191): độ dài, nhạc, peak, hiệu ứng, SRT, shot ngắn, im lặng, phụ đề che mặt | file cuối → issues | — | — | — | PART (không khung đen / đứng hình) |
| 14 | Export Premiere | grep `premiere|fcpxml|xmeml|.edl` trong core/tools/dashboard = 0 | — | — | — | — | MISS (làm tay) |

### 2.2 Công cụ & sổ

| Mục | Bằng chứng | TT |
|---|---|---|
| Replay gói ảnh | `tools/replay_payload.py:replay` (218–256) gọi đúng `ImageRunner._submit_args`, provider giả, chặn ghi `data/`; `compare` (153) chỉ so **câu chính** (prop lock / shape / travel) + **tên file ref** với `sent_package` | PART: chỉ ảnh, không video; không gọi `_submit_kwargs`; cần `data/` thật + junction |
| Fixture gói thật | `tests/fixtures/p30_payload.json` + `tests/test_replay_payload_p30.py` (2 lỗi) | PART |
| `payload_golden.py`, `byd_backfill.py`, `core/text_vs_field.py`, cờ `byd_fields` | không tồn tại (ls / grep `byd_fields` features.py = 0) | MISS |
| `tools/pregen_check.py` | chỉ có trên nhánh `wizardly-elbakyan` (chưa gộp) | PART |
| Sổ khâu | `devsys/stages.json`: 20 mục (L1–L16, L14a–d, L15a–b); L8/L12 `kiem_truoc: []`, L13 `kiem_truoc: ["d100"]` (video_pregen) | IMPL |
| Sổ khu vực | `devsys/areas.json`: shot_intent / character_forms / prop_lock / continuity / director_byd ∈ `step1`; runner ∈ step2/step4/core_infra; replay_payload ∈ step2; sent_package/lineage ∈ core_infra | IMPL |
| Bảng jobs / usage | `core/db.py` 90–117 (`jobs`, `usage_events(job_id, kind, provider, model, tier, quantity, unit)` — **không** có scene_id / lý do); cột thêm 857–867 (`input_hash, sent_refs, sent_package, quality_tier, draft_job_id, reject_reason…`) | IMPL |
| Sổ thay đổi | `change_events` + trigger `trg_change_scene` (db.py 539, 661) bắt **mọi** đường ghi `scenes.data` (Dashboard, CLI, SQL tay); `change_findings` (555), `ui_actions` (582) | IMPL |
| Lý do loại | `core/lessons.REJECT_REASONS` (98–106): 7 nhóm + khác | IMPL (taxonomy thô) |
| Benchmark QC | `core/qc_golden.py` (dev_set / independent_set / score: recall chặn + báo nhầm) | IMPL |

### 2.3 Dashboard (3 chỗ lỏng KH-gốc sơ đồ 2)

| Chỗ | Bằng chứng | Audit trail hiện có | TT |
|---|---|---|---|
| "Tôi đã xem, vẫn gen ảnh" | `dashboard/steps/step2.py:224/228` → `batch.queue_images(confirmed=True)` → `diag.record(..., "gate_override")` (`core/batch.py:54–59`) | chỉ một dòng diag: **không** actor, lý do, snapshot gói | PART |
| Bỏ qua cổng video | `dashboard/video_gate_ui.py:30/47`, `core/video_gate.py:skip` (51: `len(reason) < 3`) → `video_gate_skips(who, reason, at)` | có actor + lý do; không mã lỗi, không snapshot | PART |
| "✔ Duyệt & khóa → Storyboard" | `dashboard/steps/step1_v2.py:173` → `step1._lock_and_go` (498) → `llm_io.lock_character_bible` (không kiểm `anchor_approved`); chỉ hiện dòng "Chưa duyệt ảnh mốc" | không | MISS (chặn) |
| BYĐ trên Dashboard | grep `byd` trong `dashboard/` = 0 | — | MISS |
| Thẻ gói sẽ gửi | grep `sent_package|sent_refs` trong `dashboard/` = 0 | — | MISS |

### 2.4 Kiểm "báo cáo trong KH-gốc" (đề bài mục 1)

| Báo cáo KH-gốc | Kết quả xác minh | TT |
|---|---|---|
| 16 khâu L1–L16 | 20 mục trong `devsys/stages.json` (gộp L14a–d, L15a–b) — khớp | IMPL |
| BYĐ trong `core/shot_intent.py` có `thanh_phan[].dang`, `noi_chon.{kho_id,spot,thoi_gian,thoi_tiet}`, `vat` | Có (`empty` 45–50, `_check_dang` 109). `vat` chỉ là danh sách không schema | PART |
| `runner._submit_args` là đường gửi duy nhất | Đúng cho cả ảnh và video; gói ghi qua cùng `_build_package` (579) cho ledger + `video_pregen` | IMPL |
| `replay_payload.py` đã có | Có, chỉ ảnh | PART |
| Các khâu L5/L7/L8/L12 không đọc BYĐ | grep `byd` trong runner / character_forms / prop_lock / scene_storyboard / plate_choice / plate_anchor / assets / scene_establish / shot_text_checks / shot_normalize = **0**. Ngoại lệ đang đọc: `lock_exceptions` (`byd.ngoai_le` → khóa nhân vật, runner 2834/2873), `video_pregen` (`hanh_dong`), `identity_declare.byd_view` (451), `qc_observe` (56–66), `prompt_formula` (434, ngữ cảnh LLM) | IMPL (phát hiện đúng) |
| #31 36/36 BYĐ, 24 shot khai dạng; `shot_intent` BẬT ở máy chính | cần `data/manifest.sqlite` + `data/feature_settings.json` | UNK (worktree không có data) |
| 391 `re.compile` trong core | đếm lại: **386** (main b39e005b) | PART (lệch nhỏ) |
| Q5: phiên sửa gốc (1)(2) đụng character_forms / prop_lock | Nhánh `wizardly-elbakyan` **không** đụng hai file này; đụng `shot_intent.py`, `db.py`, `location_pack.py`, `step2.py`, `decisions.json` (§4 Q5) | PART |

### 2.5 Phiên khác đang sửa (chỉ ghi nhận, không phối hợp sửa)

> **Ghi chú 18/10:** bảng dưới là ảnh chụp lịch sử 17/10 (giữ để truy vết). Trạng thái hiện hành: cả hai đã lên main — xem khối "Xác minh R2" đầu tài liệu.

| Nhánh / commit | Trạng thái thật (`git fetch` 17/10) | File chạm liên quan V2.1 |
|---|---|---|
| `origin/claude/wizardly-elbakyan-596555` @ `3a2a6eb9` | **CHƯA gộp** (`merge-base --is-ancestor` → không); 1 commit, 18 file, +727/−46; HANDOFF ghi: chưa rà quy ước 7, chưa chạy cả bộ | `core/shot_intent.py` (+`sync_noi_chon`), `core/db.py` (trigger `trg_scene_noi_chon(_new)`, sửa `trg_change_scene`), `core/location_pack.py` (`render_moved`), `core/batch.py`, `core/cost.py`, `dashboard/steps/step2.py`, `data/decisions.json`, `tools/pregen_check.py` |
| `4775eab4` "Máy POV đặt tại mắt…" (sửa `plate_camera.camera_for` 180°) | chỉ ở nhánh local `claude/ai-video-pipeline-todo-0db507`, chưa lên main | `core/plate_camera.py`, **`core/plate_choice.py`**, `core/location_pack.py` → đụng đích A2c/A2d |

## 3. Gap Analysis

| Yêu cầu V2.1 | Hiện có | Khoảng trống | Ưu tiên |
|---|---|---|---|
| B: golden payload toàn gói 3 dự án | replay ảnh + p30 fixture (2 lỗi) | capture/update/CHANGES, input đóng băng, ảnh giả, `needs_pixels`, ma trận cờ, **replay video** | P1 |
| B: tách Compatibility ↔ Correctness | — | hai bộ test riêng (§6.B) | P1 |
| A: BYĐ có version | không có `byd_v` | đọc theo version + provenance + VÀNG khi fallback | P2 |
| A: `vat[]` có cấu trúc | danh sách không schema; `qc_observe` đòi dict `{vat}` (raise ValueError 58/64) | schema `{kho_id, nguoi, cach, bien_the}` **giữ khóa `vat` (tên)** để không vỡ `qc_observe` | P2 |
| A: `dang` = mã dạng Kho | `dang` chữ tự do; Kho chỉ khai dạng bằng dòng chữ (`character_forms._DECLARE`) | trường `forms` có cấu trúc ở Kho (phụ thuộc Q3) | P2 |
| A: outfit/hair/face có cấu trúc | `assets.profile` {identity, must_keep, may_change, forbidden, height_m, build, digest}; `characters.wardrobe` (chữ), `outfit_image_ids`, Kho kind `outfit` | tách `outfit/hair/face` **trong `assets.profile`** + quan hệ form/variant | P2 |
| A: BLOCK/REVIEW/WARN + override audit | do/vang (shot_intent), diag, `video_gate_skips`, `change_findings` | bảng override thống nhất (actor, ts, lý do, mã, snapshot gói) | P2/P3 |
| C: metrics | `jobs`, `usage_events(job_id)`, `reject_reason`, `change_findings`, `ui_actions`, `qc_golden.score` | view tính cost/accepted shot, retry cost, QC pass, override rate; `usage_events` thiếu scene/lý do → join qua `job_id` | P3 |
| D: state machine | `lineage`, `end_frames`, `layout_follow`, `side_truth`, `travel_truth`; `continuity.py` regex | Expected/Observed/Resolved state + đồ thị phụ thuộc; `byd` vào vân tay | P4 |
| E: QC 5 lớp | xem §7.E | preflight ảnh, mã lỗi, khung đen/đứng hình, cross-shot, Premiere | P4 |
| F: repair router | `regen.py`, `qc_policy` (max_retry), `projects.max_retry_count`, `send_claim`, `spend_gate` | taxonomy mã lỗi, router theo tầng, fingerprint đầu vào cho mọi artifact | P5 |

## 4. Decisions Q1–Q6

| Q | Khuyến nghị V2.1 | Điều kiện đề bài | Kết quả kiểm | Còn phải quyết |
|---|---|---|---|---|
| **Q1** B trước A | **Đồng ý, B trước A**, nhưng B1 (chụp fixture) **sau khi gộp nhánh wizardly** | Không có phụ thuộc cản trở | Không có phụ thuộc code A→B: B chỉ cần `replay_payload` + `_submit_args` (đã có). Cản trở duy nhất: trigger `trg_scene_noi_chon` đổi `scenes.data.byd.noi_chon` → chụp trước gộp thì baseline lệch. B0 (dò đường mở ảnh) làm ngay được | Không |
| **Q2** time/weather tại shot | **Đồng ý (a)** — và **đã được chốt** ở nhánh chưa gộp: quyết định `time-weather-single-source-2026-10-17` + trigger đồng bộ bản chép `byd.noi_chon` | Kiểm consumer thực tế | Consumer đọc **trường shot**: `plate_env.time_of/weather_of`, `location_pack`, `scene_establish`, `ambience`, `qc_spec`, `shot_text_checks`, `tools/render_plates`. Consumer đọc **BYĐ**: `prompt_formula:414/434` (ngữ cảnh LLM — đọc cả hai), `tools/dryrun_k0b_p24` (180–187). Không module dựng gói nào đọc `byd.noi_chon.thoi_*` | KH-gốc nói "bỏ trường BYĐ, chỉ so"; nhánh làm "giữ + đồng bộ bằng trigger". V2.1 theo nhánh (đã có quyết định) — bản chép không còn để "so lệch"; VÀNG lệch chỉ áp cho dữ liệu cũ trước trigger |
| **Q3** tách outfit/hair/face | **Đồng ý, có điều kiện:** tách **trong `assets.profile`** (đã là nguồn hồ sơ chuẩn T1, `profile_digest` đọc), thêm `forms[]` có cấu trúc cho mục Kho style/nhân vật; script soạn nháp (Claude ≈ 0,05 USD — **phải xin duyệt riêng**) → bảng duyệt → ghi | Có duyệt dữ liệu chuyển đổi | Hiện không có trường outfit/hair/face/forms; `without_clothes` (121) tách chữ → nguồn lỗi 5/22 | Người dùng duyệt chi phí 0,05 USD + bảng chuyển đổi |
| **Q4** giữ #24/#27 baseline; backfill #24 sau | **Đồng ý.** #27 (không BYĐ) và #24 (BYĐ v1) chỉ hồi quy đường cũ; backfill #24 chỉ sau khi A2a–A2f qua golden #31 | Không làm đổi baseline | Golden của #24/#27 chạy ở chế độ cờ máy chính + `byd_fields` TẮT/BẬT: v1 phải **giống byte** vì đọc theo version (v1 → đường cũ) | Không |
| **Q5** đồng bộ thay đổi liên quan | **Đã được báo cáo là gộp main** ở ghi chú tối 17/10; **cần kiểm chứng lại HEAD** chứa cả thay đổi trigger và POV, rồi mới B1/A2c/A2d. Không còn coi “chờ merge” là công việc mở mặc định. | Kiểm `git rev-parse HEAD`, `git merge-base --is-ancestor` cho commit thực tế, diff các file liên quan và chạy test nền | §2.5 là ảnh chụp lịch sử trước merge. **18/10 đã xác minh:** POV theo ancestry, wizardly theo nội dung + trigger trong CSDL + 244 test nền qua (`docs/audit/P1_BASELINE_VERIFICATION.md`) | **Không — đã thỏa** |
| **Q6** siết 3 cổng | **Đồng ý, kèm override audit thống nhất** (§6.A3): (a) ô "vẫn gen" chỉ bật sau mở thẻ gói; (b) lý do ≥ 15 ký tự (`video_gate.py:51` + UI 30/47 — phải đổi **cả hai** chỗ); (c) "Duyệt & khóa" chặn khi `anchor_approved=0` trừ tick có lý do | Có override audit được | Hiện chỉ (b) có actor + lý do; (a) chỉ diag; (c) không chặn | Người dùng xác nhận (c) không làm kẹt dự án chỉ có nhân vật phụ không ảnh mốc |

## 5. Updated Architecture (đích V2.1)

```
BYĐ v2 (scenes.data.byd, byd_v)   ──validate──►  issues BLOCK/REVIEW/WARN ──► override_log (mới)
   │  (v1 / thiếu → đường cũ + provenance + VÀNG)
   ▼
Field readers (A2a–A2f)  ─── dùng lại: character_forms, prop_lock(weapon_table), assets, plate_choice, plate_anchor, scene_establish
   ▼
runner._submit_args (ảnh/video)  ──► _build_package (một builder) ──► [dry-run] Thẻ "Gói sẽ gửi" / replay / golden
   │                                                       └────────► [thật] jobs.sent_package (ledger) ── so sánh ── thẻ
   ▼
_pregen: video_pregen (đã có) + image_preflight (mới, cùng mã lỗi)  ──► gửi (send_claim, spend_gate)
   ▼
QC ảnh / video (autoqc, qc_scene, clip_measure…) → failure code + evidence  ──► state Observed (UNKNOWN nếu thiếu)
   ▼
Continuity state (Expected từ BYĐ + stage facts / Observed từ QC / Resolved = người duyệt)  ──► lineage: stale theo đồ thị
   ▼
Repair router (F) → tầng BYĐ/asset/ảnh/video/âm/dựng → job mới có parent_job_id + input fingerprint (giữ bản cũ)
   ▼
final_cut / delivery → final_qc (+ khung đen/đứng hình) → export (+ Premiere XML: tùy chọn, P5+)
```

Nguyên tắc giữ từ KH-gốc §2 (không lặp lại). Bổ sung: **mọi đường xem gói (thẻ, replay, golden, pregen) dùng `_build_package`**; mọi
quyết định chặn/override ghi một chỗ; mọi artifact có vân tay đầu vào trong `lineage`.

## 6. Phần A / B / C — cập nhật (chỉ phần đổi so với KH-gốc)

### 6.B Payload Golden Regression (làm trước) — thay KH-gốc §4

| Bước | Đổi / bổ sung so với KH-gốc |
|---|---|
| **B0** dò đường mở ảnh | Như §4.3 KH-gốc; thêm: ghi lại mọi `open`/`Image.open`/`cv2` **và** `sent_package.sha256_of` (ledger đọc file để băm). Các module có PIL/cv2 trên đường gói cần dò: `assets` (381/614/1098), `location_pack`, `place_refs`, `skill_objects`, `layout`, `plate_env`, `palette`, `seedance_refs`. Kết quả = danh sách `needs_pixels` có căn cứ, không đoán |
| **B1** chụp | `tools/payload_golden.py --capture` **tái dùng** `tools/replay_payload.build_sandbox/replay` (không viết lại). Thêm **replay video** (`VideoRunner._submit_args` + `_submit_kwargs`) — KH-gốc chỉ có ảnh. Gói rút gọn theo **schema `sent_package` v1** (prompt, refs[{param, role, label, file, sha256}], provider, model, params) để so 1:1 với ledger thật. Ghi kèm `co` (ảnh chụp cờ máy chính) và `git_sha` |
| **B2** test | Tách hai bộ: **`test_payload_compat.py`** (Compatibility: cờ máy chính, `byd_fields` TẮT → giống byte fixture; khác = ĐỎ) và **`test_payload_correctness.py`** (Correctness: danh sách lỗi đã biết 15–17/10 — mỗi lỗi một khẳng định cụ thể, vd "shot 13 #31 có ảnh súng", "khóa giữ 'never"; được phép `xfail(strict=True)` tới khi A sửa, để khi sửa xong mà quên gỡ xfail thì đỏ). **Golden không phải bằng chứng đúng** — chỉ bộ Correctness nói "đúng" |
| Cập nhật fixture | Như KH-gốc (`--update --why`, `CHANGES.md`) + bắt buộc: diff theo shot/trường in vào commit message, **không tự chấp nhận**: test đỏ nếu sha fixture không có dòng CHANGES **có tên người duyệt** |
| Ma trận cờ | (a) cờ máy chính; (b) + `byd_fields` BẬT; (c) mỗi cờ con A2a…A2f bật riêng (để cô lập shot đổi). **Cờ máy chính = UNK trong worktree** → B1 phải chạy ở máy có `data/` (Lớp 2) rồi đóng băng |
| Skip | Test cần `data/` → `pytest.skip("needs_data: …")` có lý do; một test đếm skip (như KH-gốc §4.3) |

### 6.A BYĐ v2 + Structured Fields — sửa KH-gốc §3

| Mục | Đổi so với KH-gốc |
|---|---|
| A0 đối chiếu | Thêm: đối chiếu `byd.vat` thật của #24/#31 (hình dạng: chuỗi hay dict) — quyết định migration `vat`; đếm số shot `qc_observe` sẽ raise |
| A1 schema | `byd_v: 2` (thiếu = v1). **`vat[]`**: `{vat (tên, giữ để tương thích qc_observe), kho_id, nguoi, cach: cam\|deo\|dat\|nem, bien_the?}`; v1 chuỗi → đọc như `{vat: "<chuỗi>"}` + VÀNG `vat_v1`. **`dang`**: giữ 3 dạng hiện có (chữ / danh sách / `{nhip: …}`, shot_intent 109) — chỉ thêm kiểm "∈ `forms` Kho" **khi Kho có `forms`** (sau Q3), chưa có thì VÀNG `dang_khong_kiem_duoc`. `noi_chon.trong_nha`: code suy từ `runner.indoor_spot` (3115). `khung.moc_nen` như KH-gốc. Nhóm mới `khung` phải thêm vào `GROUPS` (39) — **v1 validate sẽ báo "trường lạ"** nếu không đọc theo version |
| Đọc theo version | Hàm một nguồn `shot_intent.read(data, field) -> (value, provenance, warn)`; provenance ∈ `byd_v2` / `byd_v1` / `suy_tu_spot` / `doc_chu (fallback)`. Fallback luôn ghi diag `byd_fallback` — **không im lặng** |
| Regex → VÀNG | Như KH-gốc §3.3; nhấn mạnh: `text_vs_field` **không** đổi ảnh, khóa, câu. Đo báo nhầm ở C |
| A2b đạo cụ | Dùng `prop_lock.weapon_table` (khóa súng theo người, có cấu trúc) làm **mặc định**; `vat[]` shot là ghi đè theo shot. Không xây bảng mới |
| A2c/A2d | **Sau** khi `4775eab4` (POV) lên main — cùng sửa `plate_choice.py` |
| Outfit/hair/face (Q3) | Trường trong `assets.profile` (`outfit`, `hair`, `face`) + `forms[]: {ma, ten_en, image_role: character_form, outfit_override?}`; `character_forms.for_shot` đọc `byd.dang` → `forms[ma]`; `without_clothes` chỉ còn lưới an toàn có VÀNG |
| Backfill #31 | `tools/byd_backfill.py` như KH-gốc + in cột **provenance** từng ô; ô suy không chắc để trống; ghi chỉ sau duyệt; ghi đi qua `llm_io.update_scene` (để trigger + `change_events` + `change_review` thấy) |
| Mức chặn | BLOCK: schema sai, `kho_id` không có, `vat.nguoi` không có trong `thanh_phan`. REVIEW: lệch ý đồ ↔ số đo (`moc_nen` vs `landmark_facts`), `dang` ngoài `forms`. WARN: `text_vs_field`, fallback v1 |
| **A3' override log** (mới) | Bảng `overrides(id, at, actor, source nguoi/claude, scope image_gate/video_gate/lock/byd, scene_id, job_id, code, reason, payload_sha, payload_snapshot)`; `video_gate_skips` giữ để tương thích, ghi song song. **Migration cần duyệt** (P3) |
| `lineage` | Thêm khóa `byd` (chỉ phần ảnh hưởng gói: `thanh_phan, vat, noi_chon, khung`) vào vân tay ảnh **chỉ khi `byd_fields` bật** (giữ hash cũ khi tắt — như cách `IMAGE_SHOT_KEYS` làm, lineage.py 17–25) |

### 6.C Metrics + Dashboard — bổ sung KH-gốc §5

| Chỉ số mới | Công thức / nguồn |
|---|---|
| Phân loại lỗi | `jobs.reject_reason` (`lessons.REJECT_REASONS`) + `goc: chu_tu_do\|hinh_hoc\|khac` |
| False positive mỗi luật | VÀNG `text_vs_field` mà người trả `khong_phai_loi` (đã có mã ở `reject_reason`) |
| Cost per accepted shot | Σ `usage_events` (join `jobs` qua `job_id` → scene) ÷ số shot có video `approved` |
| Retry cost | Σ tiền các job có `parent_job_id` hoặc `retry_count>0` |
| QC pass rate | `reviews.json` / `qc_golden.score` theo dự án |
| Override rate | `overrides` (A3') ÷ số lần gặp cổng |
| B4 thẻ "Gói sẽ gửi" | dựng bằng `_build_package` chạy khô; khi đã gửi so với **`jobs.sent_package`** (prompt + refs + sha), không chỉ `sent_refs` |
| A5 BYĐ trên Dashboard | đọc `scenes.data.byd`; thay đổi CLI/CSDL hiện ngược nhờ `change_events` + trigger `trg_change_scene` (đã có) |

## 7. Phần D / E / F mới — CHỈ THIẾT KẾ

### 7.D Continuity Engine (mở rộng tối thiểu, không viết engine mới)

| Thành phần | Nguồn tái dùng | Bổ sung |
|---|---|---|
| Expected state | BYĐ v2 (`thanh_phan.dang`, `vat.nguoi/cach`, `hanh_dong.bat_dau/ket_thuc`, `noi_chon`), `stage_facts`, `side_truth`, `travel_truth` | `state_before → action → state_after` mỗi shot cho thực thể {character, form, outfit, prop, location, camera} |
| Observed state | QC ảnh/video (`qc_observe` enum, `clip_measure`, `plate_layout_qc`) | thiếu quan sát → `UNKNOWN`, không đoán |
| Resolved state | người duyệt / override log | — |
| Đồ thị phụ thuộc | `layout_follow.continuity_from`, `end_frames` (shot đổi trạng thái cần khung cuối), `hanh_dong.ket_thuc` | cạnh = "shot B dùng state_after của shot A" theo **logic truyện** (cùng thực thể, cùng cảnh/tiếp diễn), không theo thứ tự timeline |
| Gen song song | mặc định độc lập; chỉ shot có cạnh mới chờ | không ép frame cuối làm ref |
| Stale | `lineage` (đã có) + khóa `byd` (§6.A) + vân tay `end_state` (`end_frames.stamp_end_state`) | đổi state_after của A → đánh dấu B stale qua đồ thị |
| Nơi lưu (đề xuất) | `scenes.data.state` (JSON, không migration bảng) | — |

### 7.E Automated QC

| Lớp | Đã có (tái dùng) | Thiếu / thiết kế | Đầu ra |
|---|---|---|---|
| Preflight | `shot_intent.validate`, `video_pregen` (video), `change_review.blocking`, `batch.image_gates`, `pregen_check` (nhánh) | **image_preflight** trong `ImageRunner._pregen` (hiện False) dùng chung mã với video_pregen | BLOCK/REVIEW/WARN |
| Image QC | `autoqc`, `qc_scene`, `qc_team`(TẮT), `qc_observe`, `plate_layout_qc`, `camera_match_qc`, `qc_measure` | gom về failure code §7.F; evidence = crop/bbox/số đo | PASS/FAIL/UNKNOWN + evidence |
| Video QC | `clip_measure.measure`, `video_qc_context`, `video_analysis`, ffprobe (`runner`, `video_pregen`) | object persistence, action completed vs `hanh_dong.ket_thuc` | code + timestamp |
| Cross-shot | `continuity.axis/layout/motif_warnings` (regex) | so state_after A ↔ state_before B (D) | conflict report |
| Final QC | `final_qc.run` (độ dài, nhạc, peak, SRT, im lặng, phụ đề che mặt) | khung đen / đứng hình (ffmpeg `blackdetect`/`freezedetect`), chuyển cảnh | final report |
| Benchmark | `qc_golden` (dev/independent, recall chặn + báo nhầm) | thêm ca thật lỗi 15–17/10 + ca biên (heat haze, silhouette, cúi/cũi) | — |

Không có "điểm tổng" thay điều kiện bắt buộc; confidence VLM ghi là **chưa hiệu chuẩn**; ca bất định → người duyệt (khớp quyết định
`qc_team` TẮT tới khi ≥ 75 %).

### 7.F Selective Repair

| Mã lỗi | Tầng sửa (router) | Ví dụ nguồn phát hiện |
|---|---|---|
| SCHEMA_INVALID | BYĐ (Đạo diễn sửa ≤ 2 vòng — `director_byd`) | `shot_intent.validate` |
| ASSET_ID_MISMATCH | Asset/Kho (không gen) | validate kho_id, A2e |
| CHARACTER_IDENTITY_DRIFT | ảnh (ref/khóa) → gen lại ảnh | qc_scene/qc_team C1 |
| PROP_MISSING | asset/ref đạo cụ → ảnh | qc_observe `set_match`, A2b |
| ACTION_NOT_COMPLETED | video (khung cuối / motion) | video QC vs `hanh_dong.ket_thuc` |
| CONTINUITY_CONFLICT | state → shot phụ thuộc | D |
| AUDIO_SYNC_ERROR | âm thanh / lipsync | `clip_measure` lip, `final_qc` |
| ENCODE_ERROR | dựng (0 USD) | ffprobe / final_qc |

Lưu vết: dùng `jobs` (`parent_job_id`, `retry_count`, `retry_reason`, `external_id`, `input_hash`, `sent_package`, `state`) — **không thêm
bảng artifact mới** cho ảnh/video; artifact dựng dùng `outputs` (đã có vân tay). Chống retry trùng: `send_claim` + so `input_hash` (luật
"gen lại phải đổi đầu vào", CHUAN_XAY_DUNG). Trần: `qc_policy.max_retry` + `projects.max_retry_count` + `spend_gate`/`project_budget`. Sửa
làm đổi ý đồ (đổi BYĐ, đổi dạng/đạo cụ) → dừng chờ người. Rebuild chọn lọc theo `lineage.stale_scene_ids`; bản cũ vào `trash` (đã có, `regen.py`).

## 8. Implementation Roadmap

| Phase | Phạm vi | File/module dự kiến | Phụ thuộc | Rủi ro | Test | Acceptance | Rollback | Chi phí | Điểm dừng duyệt |
|---|---|---|---|---|---|---|---|---|---|
| **P0** | Audit (tài liệu này) | `docs/KE_HOACH_AI_VIDEO_PIPELINE_V2_1_REVIEW.md` | — | kết luận sai do thiếu data (UNK) | — | mọi kết luận có file:hàm | xóa file | 0 | **Người dùng duyệt V2.1 + Q1–Q6** |
| **P1** | B0–B2 golden | mới: `tools/payload_golden.py`, `tests/test_payload_compat.py`, `tests/test_payload_correctness.py`, `tests/fixtures/payload_golden/*` + `CHANGES.md`; sửa nhẹ: `tools/replay_payload.py` (tách hàm video) | **xác minh** HEAD đã gồm `wizardly-elbakyan` + POV; máy có `data/` để chụp; snapshot cờ | fixture chụp khi cờ máy đổi; đường cần pixel | compat 3 dự án × ma trận cờ; cố ý đổi `_MARK_SEG` → đỏ đúng shot (ca 9.2 KH-gốc) | Lớp 1 xanh không cần `data/`; Lớp 2 xanh ở máy chính; danh sách `needs_pixels` in ra | xóa file mới (không đụng production) | 0 | duyệt fixture đầu tiên (diff = rỗng so replay) |
| **P2** | A0–A3 + A3' | `core/shot_intent.py` (v2, `read`), `prompts/31_director_byd.md`, `core/director_byd.py`, `character_forms`, `prop_lock`, `assets`, `scene_storyboard`, `plate_choice`, `plate_anchor`, `scene_establish`, `runner`, `shot_text_checks`, `shot_normalize`, `core/text_vs_field.py`, `core/features.py` (`byd_fields` + cờ con), `core/lineage.py`, `tools/byd_backfill.py`, `data/decisions.json` + `tests/test_decisions.py` | P1 xanh; Q3 duyệt (cho `forms`) | đổi gói ngoài ý muốn; `qc_observe` raise với `vat` v1 | compat (cờ TẮT = byte) + correctness hết xfail lỗi đã biết + `tests/test_byd_v2.py` | KPI: #31 shot trái trường = 0 (đo bằng replay); cờ TẮT giống byte | tắt `byd_fields`/cờ con (code giữ đường cũ) | 0 code; Q3 soạn nháp ≈ 0,05 USD; Đạo diễn v2 < 0,30 USD/dự án (ước tính KH-gốc §8) — **xin duyệt trước** | (1) duyệt bảng backfill #31; (2) duyệt bảng chuyển đổi Q3; (3) duyệt bật `byd_fields` cho dự án kế |
| **P3** | B4 + A5 + C + Q6 + bảng `overrides` | `dashboard/payload_card_ui.py`, `dashboard/byd_ui.py`, `dashboard/steps/step2.py`, `step4.py`, `step1_v2.py`, `dashboard/video_gate_ui.py`, `core/video_gate.py`, `core/batch.py`, `core/db.py` (migration `overrides`), `devsys/stages.json` (L8 kiem_truoc) | P2 (thẻ hiện trường); migration duyệt | thẻ dùng logic song song; cổng siết làm kẹt | thẻ shot 3 #31 = `replay --shot 3`; so `sent_package`; override ghi đủ trường | thẻ khớp replay 100 %; mọi override có actor/lý do/snapshot | revert UI; bảng mới không ai đọc → để nguyên | 0 | duyệt migration `overrides`; duyệt (c) chặn khóa |
| **P4** | D + E (thiết kế → benchmark → code sau duyệt) | `core/continuity_state.py` (mới, mỏng), `ImageRunner._pregen` (image_preflight), `core/final_qc.py` (blackdetect/freezedetect), `core/qc_golden.py` (ca mới) | P2 (BYĐ v2 làm Expected) | VLM sai; quá nhiều UNKNOWN | benchmark gắn nhãn (đạt/lỗi thật/biên) | recall chặn + báo nhầm đo được, không dùng điểm tổng | cờ riêng TẮT | QC model trên benchmark: **ước tính trước, xin duyệt** | duyệt bộ nhãn benchmark |
| **P5** | F repair | `core/repair_router.py` (mới), `core/regen.py`, `core/qc_policy.py` | P4 mã lỗi | retry vòng lặp tốn tiền | ca giả: mỗi mã lỗi → đúng tầng; trần retry | retry có trần, rebuild chỉ stale, bản cũ giữ | cờ TẮT; trash | mỗi sửa tốn tiền qua `spend_gate` | duyệt từng lần đổi ý đồ |

## 9. Risk Register

| # | Rủi ro | Khả năng | Ảnh hưởng | Giảm thiểu |
|---|---|---|---|---|
| R1 | Fixture chụp trên HEAD/cờ khác với máy production → baseline sai | Cao | Cao | Xác minh ancestry HEAD sau báo cáo merge, snapshot cờ máy chính và trigger trước B1 (Q5) |
| R2 | Cờ máy chính ≠ cờ test (bài học 16/10) | TB | Cao | capture đọc cờ thật + ghi `co` vào fixture; worktree = UNK |
| R3 | `qc_observe` raise khi `vat` là chuỗi (qc_observe.py:62–64) | **ĐANG XẢY RA** (18/10: `qc_observe_enum` BẬT ở máy chính; #31 shot 30 `vat=["AWM"]`) | TB (QC shot đó luôn `failed`, có báo) | sửa ngay parser v1 `str → {vat}` cho `qc_observe` (nhỏ, tách khỏi P2, cần duyệt + quy ước 7); schema v2 giữ khóa `vat`; A0 đếm |
| R4 | Sửa BYĐ không làm ảnh "cũ" sau `byd_fields` | Cao nếu quên | Cao (gen trên gói cũ) | thêm `byd` vào `lineage` có điều kiện (§6.A) |
| R5 | Đụng file với phiên khác hoặc sửa dựa trên commit audit cũ (`plate_choice`, `location_pack`, `shot_intent`, `db.py`) | TB | TB | Kiểm HEAD/worktree hiện tại; mỗi bước một commit; `py tools/related_areas.py` + agent rà quy ước 7 |
| R6 | Golden bị coi là "đúng" | TB | Cao | tách compat ↔ correctness (§6.B) |
| R7 | Siết cổng làm kẹt sản xuất | TB | TB | override có audit; (c) có tick lý do |
| R8 | Trigger CSDL đổi format JSON `scenes.data` (HANDOFF nhánh ghi) → diff golden giả | TB | TB | normalize JSON khi so (sort_keys) |
| R9 | Benchmark QC nhỏ, nhãn lệch | Cao | TB | dùng `qc_golden.independent_set`; ghi confidence chưa hiệu chuẩn |
| R10 | Chi phí ẩn (Đạo diễn v2, Q3, QC benchmark) | Thấp | TB | ước tính trước + sổ chi + xin duyệt từng bước (quy ước 6) |

## 10. Acceptance & Rollback (tổng)

| Mục | Acceptance | Rollback |
|---|---|---|
| Compatibility | cờ máy chính, `byd_fields` TẮT → #24/#27/#31 giống fixture từng byte (prompt + refs + sha + model) | revert commit; fixture cũ trong git |
| Correctness | mọi lỗi đã biết 15–17/10 trong bộ correctness hết xfail khi `byd_fields` BẬT | tắt cờ con tương ứng |
| BYĐ v2 | v1/thiếu trường → đường cũ + diag `byd_fallback` (đếm > 0 khi chạy #24) | tắt `byd_fields` |
| Thẻ gói | khớp `replay_payload` và `jobs.sent_package` | ẩn thẻ (UI) |
| Override | 100 % lần vượt cổng có actor/ts/lý do/mã/snapshot | bảng mới để nguyên, UI cũ |
| KPI C | lỗi lọt cổng gốc chữ tự do −50 %; #31 shot trái trường = 0 | — |
| Chung | không lời gọi tốn tiền nào ngoài sổ chi; mọi "đã sửa" có bằng chứng chạy thật (quy ước 6) | — |

## 11. Khác biệt với kế hoạch gốc

| # | KH-gốc | V2.1 | Lý do / bằng chứng |
|---|---|---|---|
| 1 | B4 so với `jobs.sent_refs` (§4.4) | so với **`jobs.sent_package`** | `core/sent_package.py` (ledger đầy đủ, sha), `runner._write_sent_package` 609 |
| 2 | L8 và L12 "không có lớp kiểm trước trả tiền" (§0) | chỉ **L8** không có; L12 có `video_pregen` (chưa verified) | `runner.py:601–603` vs `932`; `stages.json` L13 `d100` |
| 3 | `dang` = mã trong `forms` Kho (§3.1) | Kho **chưa có** `forms`; enum chỉ áp sau Q3 | `character_forms._DECLARE` 23; không trường forms |
| 4 | `vat[]` "thay danh sách chữ" | schema mới **giữ khóa `vat`** + đọc v1 chuỗi | `qc_observe.py:62–66` đòi dict `{vat}` |
| 5 | Q2: bỏ `byd.noi_chon.thoi_*`, chỉ so | giữ + **đồng bộ bằng trigger** (đã có quyết định trên nhánh) | nhánh `wizardly` `core/db.py` trigger, `shot_intent.sync_noi_chon` |
| 6 | Không nhắc vân tay | thêm `byd` vào `lineage` khi `byd_fields` bật | `lineage.py:14–25` không có `byd` |
| 7 | Replay chỉ ảnh | thêm replay **video** | `replay_payload.replay` chỉ `ImageRunner` |
| 8 | Một bộ test golden | tách **Compatibility / Correctness** | đề bài mục 4 |
| 9 | Override chỉ "lý do ≥ 15 ký tự" | bảng `overrides` thống nhất + snapshot gói | `batch.py:57` chỉ diag |
| 10 | Q3 tách outfit/hair/face "trong Kho" chung chung | đặt trong **`assets.profile`** (nguồn hồ sơ T1) + `forms[]` | `profile_digest.py`, `assets.py:1405` |
| 11 | A2b đọc `vat[]` | `weapon_table` là mặc định, `vat[]` ghi đè | `prop_lock.weapon_table` 225 |
| 12 | Q5: phiên kia đụng character_forms/prop_lock | **không đụng**; đụng `shot_intent/db/location_pack/step2`; POV đụng `plate_choice` | `git diff main...origin/claude/wizardly-elbakyan-596555 --stat`; `4775eab4` |
| 13 | Không có D/E/F, P4/P5 | thêm thiết kế D/E/F tái dùng module có sẵn | §7 |
| 14 | 391 `re.compile` | 386 ở `b39e005b` | grep đếm |

## 12. Open Questions (cần người dùng trả lời)

1. **Duyệt kiến trúc R2 và cho phép P1 (chưa cho phép P2–P5)** theo bảng §4; Q5 cần xác minh trên HEAD trước capture; Q2 theo cách đồng bộ bằng trigger?
2. **Q3:** đồng ý đặt `outfit/hair/face/forms[]` trong `assets.profile` và chi ≈ 0,05 USD cho Claude soạn nháp chuyển đổi?
3. **Q6(c):** chặn "Duyệt & khóa" khi thiếu ảnh mốc áp cho **mọi** nhân vật hay chỉ nhân vật `chinh` theo BYĐ?
4. **Migration bảng `overrides`** (P3) — chấp nhận thêm bảng, hay chỉ mở rộng `video_gate_skips` + diag?
5. **Export Premiere** (XML/EDL) có nằm trong phạm vi V2.1 không, hay giữ làm tay?
6. Chụp fixture (B1) ở **máy chính có `data/`** (0 USD, chỉ đọc) — cho phép sau khi **xác minh HEAD đã chứa các thay đổi Q5**, chụp snapshot cờ và bảo đảm không ghi vào CSDL production?

## 13. Bảng bằng chứng (file:hàm/dòng)

| Kết luận | Bằng chứng | TT |
|---|---|---|
| BYĐ schema + validate | `core/shot_intent.py:empty` 45, `_check_dang` 109, `_kho_ids` 181, `validate` 193, `from_shot_spec` 237 | IMPL/PART |
| Không `byd_v`, `vat` không kiểm hình dạng | `shot_intent.py:193–234` (chỉ `_kho_ids` đọc `vat[].kho_id` nếu là dict) | PART |
| Đạo diễn khai + sửa ≤ 2 vòng | `core/director_byd.py:settle` 115–161, `tagged(STAGE)` 130 | IMPL |
| Cờ `shot_intent`/`video_pregen`/`send_claim` chưa verified; `byd_fields` không có | `core/features.py` 560, 568, 63; grep `byd_fields` = 0 | MISS (byd_fields) |
| Khâu dựng gói không đọc BYĐ | grep `byd` = 0 ở runner/character_forms/prop_lock/scene_storyboard/plate_choice/plate_anchor/assets/scene_establish/shot_text_checks/shot_normalize | IMPL (xác nhận) |
| Dạng nhân vật đọc chữ Kho | `core/character_forms.py:_DECLARE` 23, `for_shot` 66–92, `without_clothes` 121 | PART |
| Khóa súng có cấu trúc theo dự án | `core/prop_lock.py:set_weapon` 218, `weapon_table` 225, `_holders` 235; chữ: `_present` 247, `_GUN_ACTION` 261 | PART |
| Ảnh không có kiểm trước gen | `core/runner.py:_Runner._pregen` 601–603 (return False); video: `VideoRunner._pregen` 932 | MISS (ảnh) |
| Một builder gói | `runner._build_package` 579–592, `_write_sent_package` 609 | IMPL |
| Ledger gói | `core/sent_package.py` (V=1, build 167, safe_build 209); `core/db.py` 866 `jobs.sent_package` | IMPL |
| Replay ảnh | `tools/replay_payload.py:replay` 218, `compare` 153, `build_sandbox` 168 | PART |
| Fixture gói thật | `tests/fixtures/p30_payload.json`, `tests/test_replay_payload_p30.py` (chạy xanh) | PART |
| jobs/usage_events | `core/db.py` 90–117, 857–867 | IMPL |
| change_events trigger | `core/db.py` 539, 661 | IMPL |
| Continuity = regex | `core/continuity.py` 16–35, `axis_warnings` 94, `layout_warnings` 214 | PART |
| Lineage thiếu byd | `core/lineage.py` 14–25, `_scan` 214 | PART |
| Cổng Dashboard | `dashboard/steps/step2.py` 224/228; `core/batch.py` 54–59; `core/video_gate.py:skip` 51; `dashboard/video_gate_ui.py` 30/47; `dashboard/steps/step1.py:_lock_and_go` 498 | PART/MISS |
| BYĐ / gói trên Dashboard | grep `byd`, `sent_package`, `sent_refs` trong `dashboard/` = 0 | MISS |
| qc_observe đòi `vat` dict | `core/qc_observe.py` 62–66; gọi từ `qc_scene.py:619`, `llm_runner.py:927` dưới `qc_observe_enum` (opt-in, features.py 340/766) | PART (lỗi ngầm) |
| Final QC thiếu khung đen | `core/final_qc.py` 26–241; grep `blackdetect|freezedetect` core = 0 | PART |
| Premiere | grep `premiere|fcpxml|xmeml|.edl` = 0 | MISS |
| Benchmark QC | `core/qc_golden.py` | IMPL |
| Taxonomy loại | `core/lessons.py:REJECT_REASONS` 98 | IMPL (thô) |
| Retry trần | `core/qc_policy.py` 9–35 (`max_retry`), `core/db.py` 32 `max_retry_count` | IMPL |
| Nhánh Q5 tại **mốc audit cũ** chưa gộp | `git merge-base --is-ancestor origin/claude/wizardly-elbakyan-596555 origin/main` → false tại audit `b39e005b`; ghi chú tối báo **đã gộp**, cần xác minh HEAD | HISTORICAL / VERIFY |
| POV tại **mốc audit cũ** chưa lên main | `git branch -a --contains 4775eab4` tại audit cũ; ghi chú tối báo **đã gộp**, cần xác minh HEAD | HISTORICAL / VERIFY |
| Số đếm #31/#24, cờ máy chính | cần `data/` | UNK |


---

## 14. Phụ lục R2 — Chỉnh sửa bắt buộc trước phê duyệt thực thi

> **Phân biệt nguồn:** Các kết luận module/file ở §2–§13 là **báo cáo audit của Claude** tại `b39e005b`; ghi chú tối 17/10 là **báo cáo merge/test mới hơn**. Những quy tắc dưới đây là **đề xuất thiết kế bổ sung trong lần review R2**, chưa được kiểm tra trong repository và chưa được triển khai.

### 14.1. Freeze baseline và xử lý Q5 nhất quán

- Giữ nguyên §2.5, §4 các bằng chứng `git` cũ để truy vết lịch sử, **không diễn giải chúng là trạng thái HEAD hiện tại**.
- Trước B1, chạy trên **đúng máy/worktree dùng capture**: `git rev-parse HEAD`, `git status --short`, xác minh ancestry hoặc diff thực tế của thay đổi trigger `wizardly` và POV `4775eab4`, chạy lại test nền liên quan. Lưu kết quả vào `docs/audit/P1_BASELINE_VERIFICATION.md` (đường dẫn đề xuất).
- Nếu commit đã squash/rebase, kiểm chứng **nội dung thay đổi** bằng file/diff và test, không chỉ dựa vào `merge-base` với SHA cũ.
- Đóng băng: HEAD, phiên bản schema CSDL, snapshot feature flags, cấu hình provider/model, bộ input dự án, hash file ảnh/ref. Nếu thiếu `data/` thật, ghi `UNKNOWN` và **không chụp golden giả**.
- B0 có thể chạy trước xác minh; B1 capture và B2 kiểm tương thích chỉ được chạy khi đủ điều kiện. B1 phải là thao tác chỉ đọc với CSDL production; mọi artifact fixture ghi ra workspace test riêng.

### 14.2. Sửa tương thích `vat[]` — không chờ tới lúc bật QC mới phát hiện

- A0 thống kê hình dạng `byd.vat` thực tế của #24/#27/#31 và đường đọc của `qc_observe`, `shot_intent`, `prop_lock`.
- Định nghĩa parser tập trung cho v1/v2: `str` → `{vat: <tên>}` kèm provenance `byd_v1`; dict v2 phải kiểm `vat`, `kho_id`, `nguoi`, `cach` theo quy tắc tương ứng. Dữ liệu sai không được silently cast thành `[]`.
- Thêm test cho: chuỗi v1, dict v2, danh sách rỗng, `None`, dict thiếu khóa, `nguoi` không thuộc `thanh_phan`, `kho_id` không tồn tại, trường `cach` không hợp lệ, `qc_observe_enum` bật/tắt.
- **Cổng nghiệm thu P2:** Không có exception do sai kiểu `vat` trong fixture v1/v2; trường hợp dữ liệu thiếu cho ra WARN/REVIEW/BLOCK theo hợp đồng, không gây crash.

### 14.3. Hợp đồng trạng thái Continuity (P4) — version và quyền ghi

Không được xem `scenes.data.state` là một dict tự do cho cả Đạo diễn, QC và người duyệt cùng sửa. Nếu dùng vị trí lưu này, phải tách namespace và version:

```json
{
  "continuity_state": {
    "schema_version": 1,
    "byd_revision": 4,
    "expected": {"source": "byd_v2", "value": {}},
    "observations": [
      {
        "qc_run_id": "QC_001",
        "artifact_id": "VIDEO_007_V2",
        "model_version": "unverified",
        "value": {},
        "unknown_fields": ["left_hand"]
      }
    ],
    "resolution": {
      "status": "PENDING_REVIEW",
      "selected_observation_id": null,
      "actor": null,
      "reason": null
    }
  }
}
```

- `expected`: chỉ thay khi BYĐ/ý đồ thay và phải mang revision; QC **không được ghi đè**.
- `observations`: append-only theo artifact/QC run; `UNKNOWN` là hợp lệ, không suy diễn `PASS`.
- `resolution`: chỉ ghi bởi workflow phê duyệt có actor/timestamp/evidence; override phải đi qua audit log chung.
- Khi BYĐ hoặc artifact thay, `resolution` cũ phải bị đánh dấu **STALE** theo fingerprint; không được kế thừa duyệt từ phiên bản trước.
- Cần kiểm kích thước JSON, xung đột cập nhật `scenes.data`, trigger hiện có và tác động lên `lineage` trước khi chốt nơi lưu. Nếu ghi nhiều/đồng thời, xem xét bảng phụ thay vì ép vào `scenes.data`.
- **Cổng nghiệm thu P4:** Test chứng minh expected không bị QC sửa; observation cũ không duyệt nhầm artifact mới; cross-shot chỉ tạo cạnh dependency có bằng chứng logic truyện.

### 14.4. Benchmark QC — điều kiện định lượng và vận hành an toàn

Trước khi dùng Automated QC để chặn gen/dựng hoặc kích hoạt repair:

1. Tạo bộ nhãn gồm ca PASS, FAIL, UNKNOWN, lỗi nghiêm trọng và ca biên; tách `dev_set`/`independent_set` bằng `qc_golden` hiện có. Định danh shot, artifact, nguồn bằng chứng và người gắn nhãn. Tránh rò rỉ các biến thể của cùng shot qua hai tập.
2. Báo cáo **theo từng failure code**: số ca, confusion matrix, recall lỗi cần chặn, false-positive rate trên shot đạt, tỷ lệ UNKNOWN, chi phí QC/shot, độ trễ và mức đồng thuận người duyệt.
3. **Ngưỡng đề xuất để thử nghiệm (chưa được hiệu chuẩn):** trên independent set có tối thiểu 20 ca lỗi nghiêm trọng và 20 ca đạt liên quan đến một nhóm luật trước khi xem xét tự động BLOCK nhóm đó; mục tiêu recall ≥ 95% với lỗi nghiêm trọng và false-positive rate ≤ 5% trên shot đạt. Đây là **mục tiêu thử nghiệm**, không phải chứng nhận chất lượng: với mẫu nhỏ cần xem cả khoảng tin cậy, phân tích lỗi và quyết định của người duyệt. Nếu không đủ dữ liệu hoặc không đạt, tiếp tục Shadow/REVIEW.
4. Bắt đầu **Shadow Mode**: QC ghi report nhưng không chặn; sau đó **Guarded Mode**: chỉ rule kỹ thuật deterministic đã kiểm chứng được BLOCK; semantic QC chuyển REVIEW; cuối cùng mới cân nhắc auto-repair theo từng failure code.
5. Chưa được bật lại `qc_team` chỉ vì đạt một tỷ lệ tổng hợp; phải xác định tiêu chí `≥75%` trong code đang đo điều gì, rồi kiểm benchmark độc lập theo loại lỗi và chi phí báo nhầm.
6. Lưu evidence với timestamp/frame, `artifact_id`, `qc_run_id`, `qc_version`, input hash; model confidence chỉ là tín hiệu chưa hiệu chuẩn.

**Cổng nghiệm thu P4:** Có báo cáo benchmark tái lập được, kết quả theo mã lỗi, người duyệt ký xác nhận danh sách luật được phép BLOCK; các luật chưa đủ bằng chứng giữ REVIEW/UNKNOWN.

### 14.5. Ranh giới phê duyệt và phạm vi triển khai

- **Duyệt tài liệu R2 không đồng nghĩa duyệt code hoặc chi phí.** Nếu người dùng chấp thuận, chỉ mở **P1-B0–B2** theo các điều kiện ở §14.1; P2–P5 vẫn là thiết kế chờ duyệt riêng.
- **P1**: không gọi API có phí, không migration, không sửa dữ liệu dự án production; cần quyền chỉ đọc dữ liệu thực tế để capture. Cập nhật fixture phải có diff, lý do, người duyệt và test correctness độc lập.
- **P2**: Q3 phải duyệt cấu trúc và bảng chuyển đổi trước khi ghi; mọi chi phí Claude soạn nháp và Đạo diễn v2 phải xin duyệt riêng.
- **P3**: migration `overrides` phải có script up/down hoặc chiến lược forward-compatible, kiểm trigger và dữ liệu cũ; không tự động bật cổng chặn khi chưa nghiệm thu.
- **P4**: thiết kế/benchmark trước, không tự động bật QC semantic chặn production; kiểm soát ngân sách và quyền truy cập media.
- **P5**: chỉ cho auto-repair từng nhóm lỗi đã chứng minh được; không tự sửa BYĐ làm đổi ý đồ; giữ retry cap, spend gate, chống duplicate job và rollback artifact.

### 14.6. Đề xuất trả lời các câu hỏi còn mở (CHƯA PHÊ DUYỆT)

| Câu hỏi | Khuyến nghị R2 | Trạng thái |
|---|---|---|
| Q1 | B trước A, B1 chỉ sau khi xác minh HEAD/cờ máy chính | Đề xuất |
| Q2 | Giữ `time/weather` shot là nguồn chuẩn, trigger đồng bộ bản chép BYĐ theo quyết định đã được báo cáo | Đề xuất; cần xác minh trigger |
| Q3 | `outfit/hair/face/forms[]` trong `assets.profile`, chỉ soạn nháp bằng API sau duyệt chi phí riêng | Chờ duyệt |
| Q4 | #24/#27 baseline, backfill sau khi #31 và v2 qua test | Đề xuất |
| Q5 | Đã gộp; xác minh 18/10 trên HEAD `186a2cc9` (ancestry POV + nội dung wizardly + 244 test) | **Đã xác minh** |
| Q6(c) | Bắt buộc ảnh mốc cho nhân vật chính theo BYĐ; nhân vật phụ chỉ chặn nếu shot yêu cầu ref bắt buộc, còn lại REVIEW/override có audit | Đề xuất; cần xác nhận quy tắc xác định nhân vật chính |
| `overrides` | Ưu tiên bảng riêng, lưu actor/time/code/reason/payload hash/snapshot, migration P3 duyệt riêng | Chờ duyệt |
| Premiere | Giữ export XML/EDL ngoài phạm vi bắt buộc V2.1; xem là P5+ tùy chọn | Đề xuất |
| Capture B1 | Cho phép read-only ở máy chính sau xác minh baseline; không gọi API có phí | Chờ duyệt |

### 14.7. Checklist trước khi giao Claude Code

- [x] Xác minh HEAD mới và bằng chứng Q5; cập nhật mục §2.5 lịch sử bằng ghi chú mới, không xóa dấu vết cũ. (18/10, `docs/audit/P1_BASELINE_VERIFICATION.md`)
- [x] Xác minh cờ máy chính, dữ liệu #24/#27/#31, trigger và schema CSDL. (18/10, cùng biên bản; chụp lại lúc capture)
- [ ] Xác định phạm vi P1 và quyền chỉ đọc trước khi chạy capture.
- [ ] Chốt parser/test `vat[]` v1/v2 trước khi bật các consumer mới.
- [ ] Phê duyệt Q3, Q6(c), migration và mọi chi phí theo từng phase khi tới giai đoạn tương ứng.
- [ ] Không triển khai P2–P5 khi mới duyệt P1.

**Kết luận R2:** Kế hoạch đủ rõ để **đề xuất duyệt có điều kiện P1** sau khi xác minh baseline; **chưa phải lệnh triển khai**. Những bổ sung Continuity/QC/Repair là thiết kế định hướng, chưa phải chức năng đã được xác nhận trong code.

---

## 15. Phụ lục R3 — Lỗi #31 / #33 chưa có trong kế hoạch + phân tích hướng sửa (20/10/2026)

> **Trạng thái: CHỈ KẾ HOẠCH, CHƯA DUYỆT, CHƯA SỬA CODE, 0 USD.** Nguồn lỗi: `docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md` (G1–G49;
> G50 ở commit `65f4e860`), `docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md` (A1–A10, B1–B12), gói bàn giao 19/10 trong `TODO.md`.
> Mốc code đọc: `main` = `3ecf053b`. Vị trí code (file:dòng) đọc trên mốc này — **mở lại file trước khi sửa**.
> §2–§14 viết 17–18/10, trước khi #31 phát sinh G26–G50 (19/10) và trước #33 → không mục nào của §2–§14 nhắc mã lỗi của hai dự án.

### 15.1 Ánh xạ lỗi ↔ kế hoạch

| Nhóm | Lỗi | Tình trạng |
|---|---|---|
| **Đã sửa code** (không cần kế hoạch) | G8 (`40f8a865` `model3d.stretch`), G10 (`ed612528` lời dẫn không khớp môi), G24 (`35277c3e` gỡ `closeup_start_frame`), G27 (`bda12fee` gói video gửi ảnh dạng + vật Kho), G35 (`cdead4bd`, `99db024d` rà soát lỗi thì giữ), G7 (`pov_gun_ok`: `core/prop_lock.py:337`, `core/prompt_formula.py:709`) | XONG |
| **V2.1 §2–§14 che trực tiếp** | G23 + G29 (B1 replay video), G4 (A2e đọc trường BYĐ), G22 (R4: `byd` vào `lineage`) | Chờ duyệt P1/P2 |
| **V2.1 che một phần** | G9 / G18 / G34 (`text_vs_field` → VÀNG/REVIEW); G5 (thẻ gói so `sent_package` — lỗi khóa basename chưa nêu); G11 / G19 / G26 / G41–G46 (D Continuity — chỉ thiết kế, chưa có hướng sân khấu/sơ đồ chung); clip đơ 13/16 (E `freezedetect` chỉ ở bản cuối); A5 (§14.4 benchmark QC) | Bổ sung ở §15.2 |
| **Chưa có** | #33: A1–A4, A6–A10, B8, B9. #31: G1–G3, G6, G13–G17, G20, G21, G28, G30–G33, G36–G39, G42, G47–G50 | §15.2 |

Lỗi nội dung đã xử lý tay trong dự án (#33 B1–B7, B10–B12; #31 G11–G13, G18, G19, G34, G41–G44) không cần code riêng, trừ khi nằm trong nhóm dưới.

### 15.2 Kế hoạch sửa theo nhóm (N1–N7)

Mỗi mục: **gốc → sửa → test → nghiệm thu**. Mọi sửa đi qua quy ước 7 (`py tools/related_areas.py` + agent rà) và CHUAN_XAY_DUNG.

#### N1 — Vận hành Claude / tiến trình / tạm dừng (ưu tiên CAO: đã gây trả tiền thừa)

| Mã | Gốc (file) | Sửa đề xuất | Test | Nghiệm thu |
|---|---|---|---|---|
| A1 | `core/bg_poll.py:300` khóa tệp chỉ giữ MỘT *vòng nền* mỗi CSDL; script riêng gọi `runner.poll_once` (`core/runner.py:648`) trực tiếp → hai tiến trình cùng chuyển job sang `succeeded` | Chuyển `running→succeeded` bằng **UPDATE có điều kiện** (`WHERE id=? AND state='running'`, chỉ bên `rowcount==1` tải/ghi file + chạy QC); bên thua ghi diag `poll_lost_race`. Ghi file qua tệp tạm + `os.replace` để QC không đọc file dở | 2 tiến trình giả cùng poll 1 job: đúng 1 lần ghi, 0 `InvalidTransition`, 0 job tự gen lại | tái hiện #33 job 1162→1163 bằng provider giả |
| A2, G33 | `LLM_PROVIDER` đọc một lần từ `dashboard.env` cho mọi dự án và vòng nền Tổ rà soát | Nhà cung cấp Claude chọn theo **dự án** (`projects.llm_provider`, rỗng = env); vòng nền `change_review` dùng client của dự án; Anthropic hết tiền → giữ mục ĐỎ (đã có nhờ G35), không tự đổi provider | dự án A = anthropic, B = claude_cli trong cùng tiến trình | rà #33 không còn `failed` vì Anthropic |
| A3 | `core/llm_runner.py:1334 ClaudeCliClient.clean_env` bỏ biến phiên Claude nhưng giữ `ANTHROPIC_API_KEY` → CLI dùng key API hết tiền | Thêm `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` vào danh sách bỏ | test env | 1 dòng + test |
| A4 | `director_rewrite` / `chat_prompts` ghi đè `image_prompt` người đã chỉnh; `_user_locked` chỉ được `camera_plan`, `compare`, `dialogue` tôn trọng | Hàm chung `locks.guard(data, new_fields)` dùng ở MỌI đường Claude ghi `scenes.data`; trường khóa → không ghi, báo VÀNG "Đạo diễn muốn đổi …". Người sửa tay trên Dashboard tự thêm trường vào `_user_locked` | ca #33 shot 1–3 | 0 lần ghi đè trường khóa (đếm diag) |
| G36 | `core/runner.py:404/413` chỉ kiểm `paused` đầu lượt và sau lần gửi đầu; lần thử lại sau từ chối / lùi model không kiểm lại | Kiểm `paused` **ngay trước `provider.submit`** trong `SPEND_LOCK`; nhánh thử lại / lùi model đi qua cùng cổng | tạm dừng giữa lúc chuẩn bị gói | 0 job gửi sau thời điểm tạm dừng |
| G39 | `core/regen.py:9 regenerate_video(…, data_dir)` nhận sai thư mục vẫn chạy (tạo `data/31/trash`) | Kiểm `data_dir` có thư mục dự án, sai → `ValueError` | test | — |
| G30, G32 | Kho chủ thể ClipAI đầy 100/100 → ảnh không thành asset → bộ lọc "người thật" → lùi Kling | Trước gửi video: đếm chỗ trống Kho chủ thể (`core/subjects.py`), thiếu → **chặn có lý do** + danh sách asset của dự án đã kết thúc để người dùng duyệt dọn (không tự xóa) | provider giả báo đầy | 0 lần lùi Kling vì Kho đầy |

#### N2 — Giá / ước tính (ưu tiên CAO: chạm trần giữa đợt)

| Mã | Gốc | Sửa | Nghiệm thu |
|---|---|---|---|
| A7 | `core/cost.py:55 clip_price` không có phụ phí video ref (thực tế ≈ 1,37×) và giá nâng 1080p (+24 %) | Thêm khóa giá `model:tier:ref` + giá nâng bản cao vào `pricing`; hệ số hiệu chỉnh tự tính từ `usage_events` các dự án gần nhất (như hệ số KLĐ 07/10, `cost.py:108`), hiện cạnh giá | ước tính #33 lệch sổ chi ≤ 10 % |
| A8 | `cost.py:295 estimate_videos_by_scene` lấy tier từ profile; nháp gửi tier của `core/batch.py:182 _draft_tier` | Dùng chung `_draft_tier` | giá nút Gen = tier gói gửi |
| A9, G31 | `tools/pregen_check.py` + `cost.estimate_images` cộng Claude theo giá API kể cả khi `claude_cli` | Claude = 0 USD ("dùng gói") khi provider dự án = `claude_cli`; thêm ước tính VIDEO vào `pregen_check` (cùng hàm nút Gen video) | `pregen_check` in đủ ảnh + video |

#### N3 — Hình học 3D / vị trí xuyên shot (gốc chất lượng lớn nhất)

| Mã | Gốc | Sửa |
|---|---|---|
| G1 | `core/stage_auto.py:373–377` mang MỌI đạo cụ cảnh trước sang cảnh sau "cùng sân khấu" | Chỉ mang vật có trong `byd.thanh_phan` / `vat` của shot sau hoặc khai là vật cố định; không bao giờ qua ranh giới thế giới (song song ↔ thực) |
| G2 | Nền 3D không có mốc tỉ lệ người | Người nộm đúng `height_m` (Kho) tại chỗ đứng blocking trong render K1/whitebox → ảnh bố cục riêng (không làm nền gửi đi); so % khung trong prompt ↔ số đo |
| G3, A10, G49 | `core/plate_camera.py:26 HIGH_TILT_DEG = 30` cố định; góc `eye` vẫn ngước/chúi lớn | Thêm mức `slightly_high` (≈ 10–12°); `eye` ép \|pitch\| ≤ 5°; kiểm `depth.png` (> 60 % điểm < 2 m = bị che → giữ shot) |
| G46 (+ G41/G43/G44/G45/G47/G48/G50, #33 B3) | Vị trí vật/người xuyên shot chỉ tả bằng chữ từng shot; mỗi ảnh gen độc lập | **Sơ đồ mặt bằng theo cảnh** (vẽ tay 19/10 trên `top_raw.png`) thành dữ liệu cấu trúc trong `stage_facts`: mỗi shot đọc vị trí từ sơ đồ chung, câu vị trí sinh bằng code. Gộp với D (Expected state). Vật mốc cố định (tháp, trời) đặt qua nền 3D, không qua chữ |
| G20 | `core/camera_match_qc.py` so chân trời cả khi ảnh trong nhà / nhìn từ trên cao | Nền 3D không có trời (đo trên plate) → bỏ khóa `horizon`, ghi UNKNOWN thay vì ĐỎ |

#### N4 — Gói video / model video

| Mã | Gốc | Sửa |
|---|---|---|
| G13 | Gói nhóm vượt 5000 ký tự (`core/adapters/clipai.py:205`, `core/dialogue_take.py:19`) | Motion writer biết ngân sách ký tự theo số shot trong nhóm; vượt → tách nhóm, không cắt chữ |
| G28, G37, #33 B9 | Seedance chế độ ref/nhóm không khóa khung đầu, bám khoảng cách máy của ref | Shot cần khung đầu đúng (dạng đặc biệt, cận mặt) → không gộp nhóm (đã làm tay `video_route=single` S14–S17) — thành luật trong `model_router`; `framing_guard` ĐỎ ở khung 0 → không tự duyệt |
| #33 B8 | Seedance chép cả đoạn chuyển cảnh ở đầu video ref | Đo cắt cảnh trong video ref trước gửi (`clip_measure` cuts) → VÀNG + đề xuất cắt |
| G38 | Ảnh vật Kho dạng triển khai sai (tường keo phẳng) | Kho: `forms[]` có thứ tự (Q3) — đi cùng P2 |
| G14 | `core/voice.py:436 fit_durations` kéo MỌI shot có lời dẫn | Chỉ kéo shot có lời dài hơn thời lượng; hiện danh sách + tiền chênh để người dùng duyệt |

#### N5 — Shot chèn tay / BYĐ

| Mã | Gốc | Sửa |
|---|---|---|
| G6, G21 | `core/llm_io.py:838 insert_scene_after` không chép bối cảnh, không có BYĐ | Chép `location_asset/location/time/weather/lighting/mood` của shot `after_idx`; BYĐ khởi tạo bằng `shot_intent.from_shot_spec` + VÀNG "BYĐ suy ra, cần Đạo diễn"; shot ở bối cảnh có 3D mà thiếu nền → `pregen_check` ĐỎ |
| G42 | Lời dẫn đi trước hình | REVIEW khi lời dẫn nhắc hành động thuộc `hanh_dong` của shot SAU — thuộc E cross-shot |

#### N6 — Khớp môi / lời dẫn (nợ G15–G17)

| Mã | Gốc | Sửa |
|---|---|---|
| G15 | `core/lipsync.py:116 mark` chỉ ghi thêm; mục cũ không dọn khi method về `skip` | Ghi đè theo scene_id |
| G16 | `core/claude_tasks.py:323 speaking = bool(data.get("dialogue"))` | Dùng `speaker_lint.is_narrator` như G10 |
| G17 | `core/quality_tier.py` coi `lip_sync is True` là shot khó trước `method_for` | Dùng `lipsync._method` |

#### N7 — QC báo nhầm / thiếu dữ liệu

| Mã | Gốc | Sửa |
|---|---|---|
| A5 | QC lớp 0 đo cỡ cảnh theo mặt người gần nhất (`scene_qc`, `core/features.py:291`) | Bỏ kiểm cỡ cảnh khi shot qua vai / sau lưng (đọc `byd.khung` / `camera`); thêm ca vào `qc_golden` |
| A6 | Đề rà của Tổ rà soát thiếu `motion_prompts.ref_video_path` | Đưa `ref_video_path` + `ref_video_type` vào ngữ cảnh rà (`core/change_review.py`) |
| Clip đơ 13/16; QC chấm 0,96 cho clip đơ | `core/clip_measure.py:36 FREEZE` chỉ bắt "đứng rồi giật", không bắt đứng yên kéo dài | Số đo "chuyển động thấp > 1,5 s" mỗi clip (luật motion nhanh 19/10) → REVIEW; nối `qc_sequence_logic` (cờ TẮT, `b269e88f`) vào E Video QC |

### 15.3 Phân tích

1. **N1 + N2 không phụ thuộc BYĐ v2** → làm được ngay, tách khỏi P1–P5 thành **P0.5**. Thay đổi nhỏ, test bằng provider giả, 0 USD.
   Lý do: A1 / G36 / G30 đã gây trả tiền thừa thật; A7 / A8 làm chạm trần `--max-usd` giữa đợt (#33).
2. **N3 là gốc chất lượng lớn nhất** (≥ 10 lần vẽ lại ảnh #31 vì G41–G50). Hướng "sơ đồ mặt bằng theo cảnh" trùng D (Expected state) → **gộp D với N3**: Expected state về vị trí lấy từ sơ đồ, không chỉ từ BYĐ. G1 cần BYĐ `thanh_phan/vat` (P2).
3. **N4 / N7 nối vào E và F:** G28/G37 là luật định tuyến (không cần QC mới); clip đơ cần số đo mới ở `clip_measure`.
4. **N5 / N6 nhỏ, độc lập** — gộp vào P2 (N5 đụng BYĐ) và P3 (N6).
5. **Rủi ro:** A1 đụng đường ghi job (lõi) → test 2 tiến trình + chạy cả bộ; A2 đổi chọn provider → chạm mọi khâu Claude (quy ước 7 trả nhiều khu vực); A4 có thể chặn sửa hợp lệ của Đạo diễn → bắt đầu bằng VÀNG, đo, rồi mới chặn.
6. **Chi phí:** N1, N2, N5, N6, N7 = 0 USD (provider giả). N3 = render Blender 0 USD + một đợt gen thử ảnh để chứng minh (xin duyệt riêng).

### 15.4 Thứ tự đề xuất

**P0.5 (mới):** N1 + N2 → **P1** golden (giữ) → **P2** BYĐ v2 + N5 + G1 → **P3** Dashboard / override + N6 → **P4** D + N3 (sơ đồ mặt bằng) + E + N4 / N7 → **P5** F.
Bản hợp nhất: `docs/KE_HOACH_AI_VIDEO_PIPELINE_V3_2026-10-20.md`.
