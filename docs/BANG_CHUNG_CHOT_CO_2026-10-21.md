# Bằng chứng trước khi chốt cờ — 21/10/2026

> Người dùng yêu cầu 3 bằng chứng trước khi chốt đề xuất ở `docs/DANH_GIA_HIEU_QUA_CO_2026-10-21.md` (khóa 8 cờ, sửa 20 cờ, 19 cờ V3.1 mới,
> cơ chế baseline chống tắt nhầm). Tất cả đo 0 USD, chỉ đọc; chưa đổi cờ nào.

## 1. D01–D10 và quy định phân quyền V3.1 hiện hành

Nguồn: `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md` mục 4 + 4b; `data/decisions.json`.

### 1.1 Phân quyền (đang hiệu lực)
| Mục sổ | Nội dung | Ảnh hưởng tới quản lý cờ |
|---|---|---|
| `v31-permission-tiers-2026-10-20` | Đồng ý định hướng ≠ được sửa code. Cấp 1: đọc/audit, thiết kế, test chỉ đọc. Cấp 2: code — trước MỖI gói trình phạm vi file, hợp đồng dữ liệu, tác động đường cũ, regression, cờ/rollback; chỉ làm sau khi duyệt. Cấp 3 (xin riêng): migration/sửa dữ liệu production, **bật cờ ảnh hưởng workflow**, API trả phí, xóa asset, QC chặn, pilot trả phí | Khóa/tắt cờ sản xuất = **Cấp 3**; code cơ chế baseline = **Cấp 2** |
| `v31-cap2-milestone-packages-approved-2026-10-20` | M1–M4 duyệt có điều kiện; **Cấp 2 không cấp quyền** migration, xóa asset, bật cờ production, API trả phí; "cờ TẮT tương thích workflow cũ" | Cơ chế baseline không được làm đổi trạng thái cờ hiện hành |
| `v31-c3-2-flags-on-main-2026-10-20` | Ví dụ Cấp 3 đã làm đúng: bật `poll_claim`, `pause_before_submit` sau khi người dùng nói "bật theo đề xuất"; sao lưu + rollback | Mẫu thủ tục cho mỗi lần khóa/tắt cờ |
| `flag-lock-list-after-p31-2026-10-15` | Danh sách khóa thêm đợi sau #31 kiểm chứng; không đặt verified trước khi #31 xong | Quyết định khóa mới phải `replaces` mục này |
| `p27-fix-flags-on-2026-10-13` | Bật mặc định 7 cờ sửa lỗi #27 (default_on, verified False) | Giữ nguyên |

### 1.2 D01–D10 (chốt 20/10 — chính sách / định hướng, KHÔNG phải lệnh triển khai)
| Mã | Phương án | Nội dung | Sổ quyết định |
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

### 1.3 Kết luận
- Không mục nào trong D01–D10 cấp quyền tự khóa / tự tắt cờ. D07 còn nói rõ: bật chặn / tự sửa của QC cần nghiệm thu + duyệt.
- Mỗi việc: **khóa 8 cờ**, **tắt 2 cờ nguy hiểm** = Cấp 3 → một câu duyệt riêng của người dùng + mục sổ mới (`replaces` `flag-lock-list-after-p31-2026-10-15`)
  + sao lưu `data/feature_settings.json` + rollback.
- **Cơ chế baseline / cảnh báo cờ bị tắt** = code Cấp 2 → trình phạm vi (file, thứ tự `state()`, test bất biến, rollback) trước khi viết.
- Không phiên nào (kể cả phiên chính) được tự làm các việc trên.

## 2. Dependency graph + test matrix (8 cờ khóa · 20 cờ sửa · 19 cờ V3.1)

_(đang chạy — bổ sung khi agent đo xong 2 lần cả bộ test với cờ ép BẬT)_

## 3. Rủi ro khi đổi thứ tự ưu tiên trong `features.state()`

Mô phỏng trên BẢN SAO cài đặt cờ thật của máy chính (script dựng lại `state()` theo lớp, đã kiểm khớp `state()` thật trên cả 144 cờ).


0 USD, chỉ đọc. Code đọc ở `D:\AI-Video-Pipeline` (HEAD `0655c434`). Dữ liệu mô phỏng là bản sao trong `%TEMP%\staterisk\`:
`feature_settings.main.json` (bản sao `data/feature_settings.json`), `dashboard_env_FEATURE_only.txt` (chỉ 36 dòng `FEATURE_` của dashboard.env),
`backups/` (25 bản sao lưu). Script: `sim.py`, `probe.py`, `probe2.py`. Kết quả thô: `ket_qua.json`, `ket_qua_probe2.json`, baseline chụp được:
`baseline_from_main.json`. Script **dựng lại state() bằng các lớp** và tự kiểm: mô hình "HIỆN TẠI" khớp `features.state()` thật trên đủ 144 cờ (có `assert`).

### 3.1. Thứ tự hiện tại (file:dòng, `core/features.py`)

| Hàm | Dòng | Thứ tự / hành vi |
|---|---|---|
| `settings()` | 912–936 | Đọc `settings_path()` (897: `FEATURE_SETTINGS_FILE` hoặc `<repo>/data/feature_settings.json`), cache theo mtime. `flags` = bool; `modes` chỉ nhận `"trainee"` cho cờ có `trainee: True` và không có trong `flags`; cờ REMOVED → `dropped` |
| `state()` | 1040–1072 | 1) `REMOVED` → off · 2) `locked()` → on · 3) 🧪 `modes` → trainee · 4) 🧪 `flags` → on/off · 5) preset `stable` → on chỉ khi `verified`; `experimental` → env=0 thì off, cờ học việc → trainee, `OPT_IN_ONLY`/`HARMFUL` → off trừ env=1 · 6) env `FEATURE_X`: cờ học việc + (=1 hoặc =trainee) → trainee; =1 → on; =0 hoặc =trainee → off · 7) `default_state()` |
| `default_state()` | 1075–1081 | REMOVED → off; `verified` hoặc `default_on` → on; còn lại off |
| `locked()` | 1009–1011 | `verified` và không REMOVED và không `_lock_bypassed()` |
| `_lock_bypassed()` | 1002–1006 | `_TEST_BYPASS is True` — chỉ `tests/__init__.py:15` đặt |
| `locked_off_ignored()` | 1019–1037 | Chỉ BÁO lựa chọn tắt/học việc cũ của cờ khóa (🧪 hoặc env=0) — bị bỏ qua. Máy chính hiện: **0** |
| `on()` / `shadow()` / `active()` | 1084 / 1090 / 1095 | `state()=="on"` / `=="trainee"` / `!="off"` |
| `OPT_IN_ONLY` | 879–880 | 14 cờ tự tiêu tiền: preset experimental không bật; chỉ 🧪 hoặc env=1 bật |
| `REMOVED` | 884–893 | 5 cờ, luôn off |
| `source()` | 1200–1211 | Cùng thứ tự: removed/locked/settings/preset/env/default |
| `save_settings()` | 939–990 | Ghi nguyên tử (tmp + `os.replace`). Từ chối tắt/học việc cờ khóa (kiểm hết trước khi ghi). `None` = xóa lựa chọn riêng. **Không sao lưu** |

Env đi vào tiến trình thế nào: `tools/launch_dashboard.ps1:57–63` nạp `dashboard.env` (ghi đè biến Process); script dùng
`core/adapters/check.py:48 load_dashboard_env()` (`setdefault`, môi trường thắng). Script **không** gọi hàm đó thì không thấy dòng `FEATURE_`:
trên máy chính đã lệch **13 cờ** ngay hôm nay (lip_sync, j_cut, seedance_ref_groups, audio_first… và 4 học việc → off).

#### Mọi đường GHI trạng thái cờ
- `features.save_settings` (lõi duy nhất ghi `data/feature_settings.json`):
  - `dashboard/header.py:684` chọn preset · `:727` công tắc từng cờ (🧪) · `:732–733` nút **"↺ Bỏ mọi lựa chọn riêng (theo preset)"**:
    `flags={k: None…}`, `modes={k: None…}` — một bấm, không hỏi lại, không sao lưu.
  - `dashboard/design/screens/trainee_ui.py:35` chế độ bật/học việc/tắt của cờ học việc.
  - `core/before_run.py:144–149` `enable_fix_flags` (nút "Bật các cờ sửa lỗi" ở 🧭 — chỉ ghi True, chỉ cờ 0 USD).
  - `tests/_flags.py` (`flags_on/off/trainee/clear`) — ghi tệp 🧪 của lượt test (tệp tạm).
- Env: `dashboard.env` (36 dòng FEATURE_, sửa tay), biến môi trường; `tests/__init__.py:5,16–21` (`setdefault` FEATURE_SETTINGS_FILE rỗng + 11 cờ =0 + `_TEST_BYPASS=True`);
  `tests/conftest.py:21` (tệp 🧪 riêng mỗi lượt/worker); ~44 tệp test tự `FEATURE_SETTINGS_FILE`/`save_settings`.
- Đổi tệp 🧪 mà tiến trình đọc: `tools/pregen_check.py:162–183` + `tools/replay_payload.py:180–188, 312–317` (CHÉP tệp thật vào thư mục thử),
  `tools/golden_db_replay.py:360`, `tools/ui_snapshot.py:338`, `tools/ui_v2_acceptance.py:371` (tệp rỗng).
- Chép tay/khôi phục bản sao lưu `data/backup/feature_settings.*`, `data/feature_settings.backup_*` (25 bản; không có bản nào ghi `false` cho cờ khóa).
- Code: sửa `verified` / `default_on` / `REMOVED` / `OPT_IN_ONLY` trong `FEATURES`.

### 3.2. Mô phỏng

Trạng thái hiệu lực hiện nay (máy chính = tệp 🧪 + dòng FEATURE_ dashboard.env): **115 bật · 6 học việc · 23 tắt**; nguồn: 84 🧪, 23 khóa, 13 env, 24 mặc định.
Preset `custom`, 86 lựa chọn (đều True) + 2 học việc (`qc_team`, `scene_qc_trusted`). Máy trống (không tệp 🧪, không env): 31/0/113.
Bộ test (không tệp, 11 cờ env=0, `_TEST_BYPASS`): 20/0/124.

Baseline = trạng thái hiệu lực máy chính chụp lúc này (144 mục). Thứ tự thử (REMOVED luôn đứng đầu):

- **A** 🧪 > khóa > baseline > preset > env > mặc định
- **B** khóa > 🧪 > baseline > preset > env > mặc định
- **C** baseline > khóa > 🧪 > … (cố ý sai)
- **D** khóa > 🧪 > preset > env > baseline > mặc định (đúng đề xuất mục 5 của DANH_GIA: baseline đọc trong `default_state()`)
- **E** = D + bảo vệ: baseline chỉ lấp chỗ trống; không bao giờ BẬT (kể cả học việc) cờ `OPT_IN_ONLY` hoặc `costs`; cờ có chế độ học việc
  tối đa `trainee`; tắt hẳn khi `_TEST_BYPASS` hoặc `FEATURE_BASELINE=0`
- **F** = E nhưng chỉ dùng baseline khi máy **không có** tệp `data/feature_settings.json` (baseline = "hạt giống" cho máy mới)

Số cờ ĐỔI trạng thái hiệu lực so với hiện tại:

| Ngữ cảnh | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| Máy chính (Dashboard, có dashboard.env) — baseline vừa chụp | **0** | **0** | **0** | **0** | **0** | **0** |
| Máy chính, script không nạp dashboard.env | 13 | 13 | 13 | 13 | 13 | 0 |
| Máy trống (worktree/cloud/Codex) | 90 | 90 | 90 | 90 | 68 | 68 |
| … trong đó cờ tốn tiền/OPT_IN bị bật | **22** | **22** | **22** | **22** | **0** | **0** |
| Bộ test (tests/__init__.py) | 101 | 101 | 101 | **90** | 0 | 0 |
| Máy chính sau khi `git pull` một baseline mới bật thêm 3 cờ đang tắt mặc định | 3 | 3 | 3 | 3 | 3 | **0** |
| Máy chính nếu "tỉa" tệp 🧪 chỉ còn chỗ khác baseline (mục 5.1 đề xuất) | 0 | 0 | 0 | 2 | **24** | **76** |

"0 trên máy chính" ở cả A/B/C là **tự nhiên** (baseline = chính trạng thái hiện tại) — nó không chứng minh thứ tự an toàn. Khác biệt chỉ lộ ra khi
có thay đổi về sau (mục 3). Máy chính hôm nay không có cờ khóa nào bị 🧪 ghi tắt nên A cũng ra 0; nhưng A cho 🧪 thắng khóa — một tệp cũ / sửa tay
`"x": false` sẽ tắt cờ 🔒 (đảo luật 15/10).

22 cờ tốn tiền bị bật trên máy trống ở A–D: ambient_motion, anchor_by_spot, asset_english_names, auto_send_self_fix, bg_autoqc, blockout_clay_sheet,
camera_match_qc, change_review, change_review_frames, change_review_motion, chat_prompts, continuity_from_ui, director_blockout, end_state_fresh,
film_grammar_check, kld_lessons_prompts, layout_from_follow, motion_sfx, p24_lessons, qc_observe_enum, shot_popup, stage_handheld_props
(13 trong `OPT_IN_ONLY`, có `bg_autoqc`/`auto_send_self_fix` = vòng nền tự gửi job tốn tiền không ai bấm).

### 3.3. Kịch bản rủi ro

| # | Kịch bản | Kết quả mô phỏng | Kết luận |
|---|---|---|---|
| S1 | Người dùng tắt tay ở 🧪 một cờ có trong baseline (`package_overrides`) | A/B/D/E/F: còn TẮT · **C: BẬT lại** | Lựa chọn riêng phải đứng trên baseline |
| S2 | Baseline cũ (dựng từ bản 12/10, hoặc 20/10 trước C3-2) + lựa chọn hiện nay | A/B/D/E/F: 0 cờ đổi · **C: 61 cờ / 2 cờ tắt mất** | Baseline cũ chỉ vô hại khi đứng dưới 🧪 |
| S2b | Tệp 🧪 lùi về bản 12/10 (khôi phục nhầm) | Hiện nay: 61 cờ lệch; A/B/C: 0; D: 1; E: 17; F: 61 | Baseline giảm thiệt hại khôi phục nhầm, nhưng cũng che mất việc khôi phục |
| S3 | dashboard.env `FEATURE_VOICE_CHECK_REDO=0` (cờ đang bật nhờ env) | Hiện tại: off · D/E/F: off · **A/B/C: vẫn BẬT** (baseline đè env) | Baseline đặt trên env làm dòng `=0` vô tác dụng |
| S3b | env `=1` cho cờ baseline ghi tắt (`subject_capacity_guard`) | D/E/F: on · **A/B/C: off** | Như trên |
| S3c | Xóa một dòng `FEATURE_X=1` / bấm "bỏ lựa chọn riêng" một cờ để TẮT nó | D/E: cờ rơi về baseline = vẫn BẬT (không còn về mặc định code) | Đổi ngữ nghĩa "xóa lựa chọn": phải ghi rõ trong 🧪 |
| S4 | Nút "↺ Bỏ mọi lựa chọn riêng" | Hiện tại: **76 cờ đổi** (đều về tắt). A/B/C: 0 · D: 2 (scene_qc, end_frames → học việc vì env) · E: 24 (22 cờ tốn tiền về tắt + 2 học việc) · F: 76 | Baseline làm nút đỡ nguy hiểm hơn; vẫn cần xác nhận + sao lưu |
| S4b | Bỏ lựa chọn riêng rồi chọn preset "Ổn định" | Hiện tại 23 bật; D/E/F: 23 (đúng preset) · **A/B/C: 115 bật — preset chết** (98 cờ lệch) | Baseline phủ đủ 144 cờ mà đặt trên preset/env thì mọi lớp dưới thành vô tác dụng |
| S5 | Cờ mới thêm vào code sau lần chụp baseline | Không có trong baseline → rơi về env/mặc định (tắt) | Baseline không giải quyết "cờ mới sinh ra tắt" (kịch bản 1 DANH_GIA) |
| S6 | Cờ học việc / OPT_IN / costs bị baseline bật nhầm trên máy khác | A–D: **22 cờ tốn tiền bật**; E/F: 0. Học việc: baseline có 6 trainee, không cờ nào `costs`; E/F hạ `scene_qc`, `end_frames` (bật thật ở máy chính nhờ 🧪) xuống học việc | Bảo vệ bắt buộc. Lưu ý: học việc vẫn CHẠY vai (vd scene_qc/qc_team gọi Claude — nay qua claude_cli) |
| S7 | Bộ test | A/B/C: 101 cờ đổi (đè cả env=0 của tests/__init__) · D: 90 · E/F: 0 | D lặp lại vụ 13/10 (revert 362 test đỏ). `tests/test_feature_settings.LockedVerifiedTests` đặt `_TEST_BYPASS=False` → khi đó điều kiện "tắt khi bypass" mất tác dụng: cần thêm `FEATURE_BASELINE_FILE` trỏ tệp rỗng trong `tests/__init__.py` |
| S8 | `git pull` baseline mới (sinh ở máy khác hoặc bật thêm cờ) | A–E: cờ máy chính đang ở nguồn "mặc định" đổi theo (thử 3 cờ → 3 đổi; có 20 cờ như vậy, gồm `ai_label` đang tắt theo quyết định) · F: 0 | Đây là đường duy nhất baseline có thể đổi lựa chọn hiện hành trên máy chính ở thứ tự D/E |
| S9 | "Tỉa" tệp 🧪 chỉ giữ chỗ khác baseline (mục 5.1 đề xuất) | D: 2 · E: 24 · F: 76 cờ đổi | KHÔNG tỉa. Tệp 🧪 giữ nguyên mọi lựa chọn |

### 3.4. Đề xuất

**Thứ tự khuyến nghị:** `REMOVED → 🔒 khóa → 🧪 modes/flags → preset (stable/experimental) → env FEATURE_X → baseline (có bảo vệ) → verified/default_on`.
Tức là baseline chỉ thay phần "mặc định code" trong `default_state()` (thứ tự D) cộng các điều kiện của E; nếu người dùng muốn bảo đảm tuyệt đối
"máy chính không bao giờ đổi" thì dùng thêm điều kiện F (chỉ áp baseline khi máy chưa có `data/feature_settings.json`), đổi lại máy chính
không tự nhận cờ mới từ baseline (vẫn bật qua 🧪/🧭 như nay).

Điều kiện bảo vệ (đều kiểm được bằng test):
1. Baseline **không bao giờ** đứng trên 🧪 hay khóa; không đứng trên env/preset (S3/S4b).
2. Baseline không bật (on hay trainee) cờ `OPT_IN_ONLY` hoặc `costs: True`; cờ có chế độ học việc tối đa `trainee`; không nhận cờ REMOVED/không có trong FEATURES.
   Test bất biến: duyệt tệp baseline, 0 mục vi phạm.
3. Tắt baseline trong test: `tests/__init__.py` đặt `FEATURE_BASELINE_FILE` = tệp rỗng (không dựa vào `_TEST_BYPASS`). Bộ "test theo sản xuất" là lượt riêng, có chủ đích.
4. **Test bất biến "0 cờ đổi trên máy chính"**: công cụ sinh baseline (`py -m core.features --baseline-diff`) tính `state()` trước/sau với tệp 🧪 +
   dashboard.env thật, in danh sách cờ đổi; commit baseline chỉ khi danh sách rỗng hoặc người dùng duyệt từng cờ (Cấp 3). Sinh baseline chỉ
   từ máy chính (kiểm có tệp 🧪 thật + dashboard.env), không sinh ở worktree/cloud.
5. Không tỉa/viết lại tệp 🧪 khi thêm baseline (S9). Không di chuyển dòng FEATURE_ từ dashboard.env vào baseline mà xóa dòng env khi chưa chạy bước 4.
6. Sao lưu trước mọi lần ghi lớn: `save_settings` nhiều cờ (nút reset, `enable_fix_flags`) ghi `data/backup/feature_settings.before_<lý do>_<giờ>.json`;
   nút "↺ Bỏ mọi lựa chọn riêng" bắt xác nhận + nói rõ sau khi bấm cờ về **baseline** chứ không về mặc định code.
7. `source()`/`why_state()`/`report()` thêm nguồn `"baseline"` để 🧪 nói đúng vì sao cờ bật (không im lặng — CHUAN_XAY_DUNG luật 1).
8. Script ngoài Dashboard: nên gọi `load_dashboard_env()` hoặc đọc baseline; hiện đã lệch 13 cờ so với Dashboard (không do baseline, nhưng cùng loại rủi ro).
