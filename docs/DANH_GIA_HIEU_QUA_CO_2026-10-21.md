# Đánh giá hiệu quả cờ tính năng — 21/10/2026

Phiên agent chỉ đọc (0 USD). Không đổi cờ, không ghi `data/`, không gọi API trả phí. Nguồn: `D:\AI-Video-Pipeline`
(nhánh `main` cục bộ 66aeeccf; `core/features.py` trùng 144 cờ với nhánh tích hợp hiện tại) — `core/features.py`,
`data/feature_settings.json` + 25 bản sao lưu `data/feature_settings.*` / `data/backup/feature_settings.*`, dòng `FEATURE_*` của
`dashboard.env` + 11 bản sao lưu (chỉ đọc dòng FEATURE_), `data/manifest.sqlite` mở `file:…?mode=ro` (`diag_events`, `jobs.sent_package`,
`change_findings`, `trainee_log`, `video_gate_skips`, `mistakes`, `deliveries`), `devsys/errors.json` (86 lỗi), `data/decisions.json`,
`git log -p core/features.py`, `docs/KIEM_22_TINH_NANG_KLD_2026-10-08.md`, `docs/handoff/DE_XUAT_KHOA_CO_2026-10-15.md`,
`docs/handoff/RA_QUYET_DINH_LOI_LAP_2026-10-15.md`, `docs/DANH_GIA_P31_LECH_3D_TI_LE_2026-10-18.md`, `docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md`, TODO.md.

## 0. Tóm tắt

- **Trạng thái máy chính (đo bằng `features.report()` + dòng FEATURE_ của dashboard.env):** 144 cờ — 115 bật, 6 học việc, 23 tắt.
  23 cờ 🔒 khóa (`verified`), **92 cờ chưa verified đang bật** (82 nhờ màn 🧪 `data/feature_settings.json`, 9 nhờ `dashboard.env`, 1 chỉ nhờ `default_on`; thêm 4 học việc từ env + 2 từ 🧪).
- **Cùng code đó trên một máy/thư mục KHÔNG có hai tệp kia** (worktree, cloud, Codex, máy đồng nghiệp, bộ test): chỉ **31/144 cờ bật, 113 tắt**;
  `fix_flags_off(34)` = 24 cờ báo ĐỎ. Đây là chỗ "cờ tốt ở dự án cũ, sang dự án sau bị tắt".
- **Trên máy chính chưa lần nào cờ đang bật bị tắt** giữa #24→#27→#31→#33: 25 bản sao lưu 07/10→20/10 có số cờ bật tăng đều 4→86.
  Ngoại lệ duy nhất là `closeup_start_frame`, bị gỡ bằng code 18/10 (REMOVED, người dùng quyết). Cái "tắt" người dùng thấy là
  cờ **chưa bao giờ được bật** cho dự án kế: cờ mới sinh ra TẮT; lệnh khóa thì bị đảo lại (mục 1).
- **Đề xuất cho 144 cờ:** 22 🔒 giữ khóa · **8 khóa thêm** · 64 giữ bật để theo dõi (chưa đủ bằng chứng) · 20 sửa rồi bật/khóa ·
  6 tắt-bỏ · 2 giữ học việc · 21 kiểm chứng nhanh (19 cờ V3.1 + `stage_crew` + `qc_sequence_logic`) · 1 giữ tắt theo quyết định (`ai_label`).
- **Cơ chế (mục 5):** một bản trạng thái cờ sản xuất (baseline) lưu trong git; chụp trạng thái cờ theo dự án; báo ĐỎ khi cờ đã bật ở
  dự án trước mà nay tắt; tự đề nghị khóa sau 2 dự án sạch; bộ test chạy theo baseline sản xuất.

## 1. Gốc "dự án sau bị tắt"

### 1.1 Cờ lưu theo MÁY + THƯ MỤC CODE, không theo dự án

| Chỗ | Hành vi | Hệ quả |
|---|---|---|
| `core/features.py:897 settings_path()` | `FEATURE_SETTINGS_FILE` nếu có, không thì `<thư mục chứa core/>/data/feature_settings.json` | Mỗi worktree (đang có 211 cái trong `.claude/worktrees`, **không cái nào có tệp này**), mỗi máy cloud/Codex/đồng nghiệp có tệp riêng hoặc không có. Tệp nằm ngoài git |
| `core/features.py:1040 state()` | Thứ tự: REMOVED → 🔒 verified → lựa chọn 🧪 → preset → `FEATURE_<X>` (env) → `default_state()` | Không có khóa nào theo dự án. Tạo dự án mới không đụng tới cờ (không có lời gọi `save_settings` nào ở đường tạo dự án; chỉ `dashboard/header.py`, `core/before_run.enable_fix_flags`, `trainee_ui`) |
| `core/features.py:1075 default_state()` | `verified` hoặc `default_on` mới "on" | Cờ chưa verified (113) TẮT ở mọi nơi không có tệp 🧪 / dashboard.env |
| `dashboard.env` (ngoài git) | 32 dòng `FEATURE_X=1` từ 27/09–01/10 (`seedance_ref_groups`, `lip_sync`, `j_cut`, `motion_trim`…) | 9 cờ chưa verified bật + 4 học việc chỉ có trên máy chính |
| Preset (`PRESETS`, `header.py:684`) | `state()` xét lựa chọn riêng TRƯỚC preset → đổi sang "Ổn định" KHÔNG tắt cờ đã chọn riêng | Không phải gốc |
| `dashboard/header.py:732` nút "↺ Bỏ mọi lựa chọn riêng (theo preset)" | Một bấm xóa cả 86 lựa chọn + 2 chế độ học việc, không hỏi lại, không sao lưu | **Rủi ro tiềm ẩn**: 84 cờ đang bật về TẮT ngay. Chưa xảy ra (25 bản sao lưu không thấy) |
| `tests/__init__.py:5,16–21` + `tests/conftest.py:21` | Bộ test chạy với tệp cài đặt rỗng, ép 11 cờ verified về 0, `_TEST_BYPASS = True` | Mặc định của test = mọi cờ TẮT, ngược sản xuất. Lỗi chỉ hiện khi cờ BẬT thì lọt test (vụ `stage_auto` 16/10 hỏng 2 lần, 0,68 USD; G29 `pregen_check` bỏ qua D6) |

### 1.2 Bốn kịch bản gây "tắt" (đã xảy ra)

1. **Cờ sửa lỗi mới sinh ra TẮT, không ai bật trước dự án kế.** Luật 5 `docs/CHUAN_XAY_DUNG.md` + docstring `features.py:1–3`: cờ chưa thử thật thì tắt.
   Phiên sửa lỗi dự án N thêm cờ `verified: False`; tới dự án N+1 thì cờ vẫn tắt: **#24→#27 6/16 cờ, #27→#31 7/7 cờ**
   (`RA_QUYET_DINH_LOI_LAP_2026-10-15.md` mục A1/B). Có vá C1 (`features.fix_flags_off` + `core/before_run.py:127–149`: báo ĐỎ ở 🧭) nhưng
   **chỉ cho cờ có khai `fixes_projects`**. **0/19 cờ V3.1 (20–21/10) khai `fixes_projects`** dù mỗi cờ sửa một lỗi #31/#33 có mã
   (`horizon_needs_sky` ↔ P31-G20, `qc_false_alarm_fix` ↔ P33-A5/A6…). Vì vậy dự án #34 sẽ không có dòng ĐỎ nào cho chúng.
2. **Lệnh khóa của người dùng bị đảo lại.** 13/10 20:06 commit `9998b46b` "20 cờ verified=True" (người dùng: cờ dùng tốt thì auto bật) →
   362 test đỏ → **revert `6dd57420` lúc 20:17 cùng ngày**. Sau đó việc dời sang nhánh `claude/co-verified-20`, không gộp
   (TODO.md:208). 15/10 có đề xuất khóa (`DE_XUAT_KHOA_CO_2026-10-15.md`: nhóm 1 = `send_claim`), rồi quyết định
   `flag-lock-list-after-p31-2026-10-15` = "đợi sau #31 rồi mới khóa". **Sau #31 chưa ai chấm.** Kết quả: 92 cờ chỉ BẬT nhờ một tệp trên một máy.
   Nay khóa thêm rẻ hơn: chỉ cần thêm tên cờ vào danh sách ép `FEATURE_X=0` ở `tests/__init__.py:17–21` (cách đã làm cho 11 cờ verified ngày 01/10).
3. **Chạy ngoài máy chính = cờ mặc định.** Worktree, cloud, Codex, `tools/golden_db_replay.py` / `ui_v2_acceptance.py`
   (`FEATURE_SETTINGS_FILE` = tệp rỗng), và mọi bản thử "chạy được" ở đó đều chạy với 31 cờ. `tools/pregen_check.py:162–183` và
   `tools/replay_payload.py:180–188` có chép tệp thật. Đo bằng tệp rỗng + không env: 31 bật / 113 tắt.
4. **Học việc không bao giờ lên "bật".** `trainee_log` có 366 dòng (qc_team 120, scene_qc 199, scene_establishing 47) và **0 dòng được
   chấm** (`match` NULL toàn bộ). Lần chấm duy nhất là chạy tay 14/10 (qc_team 49 %). Cờ học việc vì thế kẹt mãi, không có số để lên bật.

Thêm: `dashboard.env` còn `FEATURE_QC_TEAM=1` trong khi 🧪 ghi học việc (2 nguồn, RA_QUYET_DINH A14). `dialogue_take` 🔒 cần `lip_sync`,
cờ này chỉ bật bằng dashboard.env → ở máy khác cờ khóa vô tác dụng. `stage_handheld_props`, `stage_crew_user_approve` đang bật nhưng
vô tác dụng (`unmet_all()`).

### 1.3 Mốc thời gian bật cờ trên máy chính (bản sao lưu)

| Ngày | Số cờ bật ở 🧪 | Thay đổi |
|---|---|---|
| 27/09–01/10 | (env) 24→36 dòng | bật qua dashboard.env; 3 cờ hại → 0, rồi gỡ khỏi code S14.9 |
| 07/10 | 4 | |
| 12/10 (trước #27) | 11→22 | video_pregen, change_review_frames, qc_observe_enum, ambient_motion, auto_send_self_fix, short_lock_outfit, p24_lessons, project_prop_lock, bg_autoqc, continuity_layout, shot_intent |
| 13/10 | 24→34 | send_claim, shot_popup, back_view_guard, framing_guard, locomotion_end_frame, plate_anchored_image, ref_mark_off_face, skill_object_guard, tts_lowercase_caps, end_state_fresh |
| 15/10 10:29→13:08 (trước #31) | 38→83 | 7 cờ #27 (C1) + **38 cờ "bật hết để kiểm chứng ở #31"** |
| 16/10 | 84 | scene_qc |
| 20/10 19:40 (sau #33) | 86 | stage_handheld_props, poll_claim, pause_before_submit; gỡ closeup_start_frame (REMOVED) |

Không có lần nào một cờ đang bật chuyển sang tắt (`flags: false`) trong 25 bản.

## 2. Số liệu nền theo dự án (CSDL chỉ đọc)

| Dự án | Ngày job | Ảnh: job / duyệt / loại | Video: job / duyệt / loại | Ghi chú |
|---|---|---|---|---|
| #8 | 26–28/09 | 120 / 33 / 77 | 75 / 33 / 27 | dựng qua final_cut Dashboard (`outputs`) |
| #22 KLD | 06–07/10 | 49 / 9 / 29 | 45 / 9 / 25 | KIEM_22 chấm 22 cờ |
| #24 | 08–11/10 | 65 / 26 / 26 | 54 / 21 / 22 | khâu cuối bằng script |
| #27 | 12–13/10 | 112 / 34 / 78 | 115 / 43 / 53 | khâu cuối bằng script |
| #28–#30 | 14/10 | thử D6 | | |
| #31 | 17–19/10 | 102 / 39 / 48 | 85 / 2 / 28 (18 hủy) | lý do loại ảnh: nền lệch map 3D 30, bố cục/chỗ đứng 27, đạo cụ Kho sai 9; người dùng 19/10: "hầu như tất cả shot không đạt" |
| #33 | 19–20/10 | 37 / 6 / 27 | 28 / 6 / 9 | giao 20/10, 36,66 USD; bước Claude chạy claude_cli trong tiến trình riêng |

Cờ hậu kỳ (nhạc, j_cut, chuyển cảnh…) chỉ chạy thật khi dựng bằng `final_cut` của Dashboard: **#8 và #22**. #24/#27/#33 dựng bằng
script riêng, nên bằng chứng hậu kỳ dừng ở 01/10–08/10.

## 3. Bảng 144 cờ

Cột: **verified** (dOn = `default_on`, OPT = `OPT_IN_ONLY` tự tiêu tiền) · **máy chính** (nguồn) · **tốn tiền** = `costs` khai trong code ·
**bật từ** = bản sao lưu sớm nhất có cờ bật (≤ ngày) hoặc ngày dòng env · **dự án đã chạy khi bật** = dự án có job sau ngày đó ·
**bằng chứng** = diag_events theo mã của cờ (tổng lượt, dự án), quét `jobs.sent_package`, `change_findings`, lỗi `devsys/errors.json` gắn tên cờ.
"CHƯA ĐỦ BẰNG CHỨNG" = không có mã diag/dấu vết đo riêng → cách đo ghi ở cột lý do.

| # | cờ | verified | máy chính | tốn tiền | bật từ | dự án đã chạy khi bật | bằng chứng 0 USD | đề xuất | lý do |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `subject_capacity_guard` | chưa | ⬜ tắt (mặc định code) | — | — | — | lỗi: P31-G30:FIXED_UNVERIFIED, P31-G32:FIXED_UNVERIFIED | **🧪 KIỂM CHỨNG nhanh** | Phát lại 0 USD #31 job 1057–1072 (Kho 100/100, G30/G32) bằng tools/replay_payload.py: job phải CHỜ thay vì gửi ảnh đánh dấu/lùi Kling (2,70 USD). |
| 2 | `motion_sfx` | chưa · OPT | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | OPT_IN; why: chưa nối caller Bước 5 → bật mà chưa có tác dụng. |
| 3 | `blockout_clay_sheet` | chưa · OPT | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | OPT_IN; chưa nghiệm thu ảnh Kho thật; 0 dấu vết. |
| 4 | `director_blockout` | chưa · OPT | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | OPT_IN; từng làm hỏng stage_auto #31 lần 2 (16/10, test chạy cờ tắt) — đã sửa ab0abe9a (nhánh theo Kho). |
| 5 | `continuity_from_ui` | chưa · OPT | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | OPT_IN; ô giao diện; 0 dấu vết. |
| 6 | `shot_popup` | chưa · OPT | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | OPT_IN hậu kỳ tùy chọn; popup #24/#27 làm tay. |
| 7 | `package_overrides` | chưa | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | why: chưa nối runner/Dashboard → bật mà vô tác dụng. |
| 8 | `layout_drift_review` | chưa | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | why: chưa nối đường ghi tay/Dashboard → vô tác dụng. |
| 9 | `short_lock_outfit` | chưa | ✅ bật (🧪) | — | ≤12/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Bật 12/10; 0 USD; không lỗi nhưng không đo. Đo 0 USD: so prompt #31 có/không ảnh OUTFIT. |
| 10 | `tickets_admin_ui` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Trang 8502; support_tickets 0 dòng → chưa dùng thật. |
| 11 | `lao_dai_pet` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chỉ đọc; chưa kiểm GUI. |
| 12 | `bg_autoqc` | chưa · OPT | ✅ bật (🧪) | có | ≤12/10 | #27 #28 #29 #30 #31 #33 | bg_autoqc 187 (24,27,28,29,30,31); bg_autoqc_stuck 29 (24,27,31); lỗi: P31-G57:IN_PROGRESS | **🔧 SỬA rồi bật/khóa** | OPT_IN tự tiêu tiền; 187 lượt / 6 dự án nhưng bg_autoqc_stuck 29 lần, P31-G57. Sửa kẹt rồi giữ bật (không khóa vì tự tiêu tiền). |
| 13 | `layout_from_follow` | chưa | ✅ bật (🧪) | có | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | costs; sửa lỗi #27; 0 dấu vết diag riêng sau #27. |
| 14 | `subject_auto_cleanup` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | Khóa; hành vi đã đổi thành DRY-RUN (quyết định v31-d03c 20/10), không xóa thật. |
| 15 | `framing_guard` | chưa | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | framing_guard 26 (29,28,31); lỗi: P31-G28:OPEN | **🔒 KHÓA BẬT** | Bật 13/10; ĐỎ 26 lần #28/#29/#31 + 116 gợi ý nháp; bắt đúng lỗi thật P31-G28 (clip không bắt đầu đúng khung đầu, job 1043). Đo OpenCV 0 USD. |
| 16 | `back_view_guard` | chưa | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | gói gửi có câu: #27 35 | **🔒 KHÓA BẬT** | Câu "giữ lưng về máy" vào 35 gói gửi #27; không còn lỗi quay mặt ở #31/#33; 0 USD, chỉ thêm câu khi shot quay lưng. |
| 17 | `end_state_fresh` | chưa | ✅ bật (🧪) | có | ≤13/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | costs (dịch lại qua sổ chi); 0 lỗi; không đếm được số lần kích hoạt. |
| 18 | `stale_code_alarm` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Chỉ báo: chạy 8501 ở HEAD + một cổng phụ ở sha cũ → phải báo. Bật ngay (không đổi workflow). |
| 19 | `diag_merge` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Chép diag_events #31 (change_review_hold 5 710 lượt, plate_stale 408) vào CSDL tạm, chạy gộp → ≤ 1 dòng/(mã, shot, 24 h). Bật ngay. |
| 20 | `budget_notice_d01` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Chỉ đổi câu: bản sao #33 (mức dự tính 0 USD) → không còn "$0.00". Bật ngay. |
| 21 | `tts_lowercase_caps` | chưa | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | 0 USD; mới thử 1 câu. Đo 0 USD: tools/audio_listen.py trên câu IN HOA #31/#33. |
| 22 | `send_claim` | chưa | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | send_claimed 1 (27) | **🔒 KHÓA BẬT** | Bật từ 12/10, chạy #27→#33; chặn đúng gửi trùng (diag send_claimed #27); 0 lỗi devsys; 0 USD, chống mất tiền (đề xuất 15/10 nhóm 1). |
| 23 | `poll_claim` | chưa | ✅ bật (🧪) | — | ≤20/10 | #33 | lỗi: P33-A1:FIXED_UNVERIFIED, P33-A15:FIXED_UNVERIFIED | **GIỮ BẬT theo dõi** | Bật 20/10 (C3-2) sau test 2 tiến trình; chưa có job thật nào sau đó → khóa sau dự án kế nếu 0 lần poll đôi. |
| 24 | `world_map_sentences` | chưa | ⬜ tắt (mặc định code) | — | — | — | lỗi: P31-G41:OPEN, P31-G44:OPEN, P31-G45:OPEN, P31-G46:IN_PROGRESS | **🧪 KIỂM CHỨNG nhanh** | Sau world_map: shadow trên #31 so câu vị trí hiện tại, phải bắt lại G41/G44/G45/G46 (đã biết đáp án). |
| 25 | `world_map` | chưa | ⬜ tắt (mặc định code) | — | — | — | lỗi: P31-G41:OPEN, P31-G44:OPEN, P31-G45:OPEN, P31-G46:IN_PROGRESS | **🧪 KIỂM CHỨNG nhanh** | Offline #31 cảnh 4/6/8 → người dùng duyệt map. Chỉ ghi file, không đổi gói gửi. |
| 26 | `pause_before_submit` | chưa | ✅ bật (🧪) | — | ≤20/10 | #33 | lỗi: P31-G36:IN_PROGRESS | **GIỮ BẬT theo dõi** | Bật 20/10 (C3-2); chưa có job thật → khóa sau dự án kế. |
| 27 | `send_estimate` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | pregen_check trên bản sao #33: ước tính mới lệch ≤ 10 % sổ chi thật (nháp có ref 1,37×, bản cao +24 %). |
| 28 | `refusal_skip_same_picture` | chưa | ⬜ tắt (mặc định code) | — | — | — | lỗi: P31-G32:FIXED_UNVERIFIED | **🧪 KIỂM CHỨNG nhanh** | Phát lại chuỗi #31 1057→1065→1071; đổi thứ tự người dùng chốt 27/09 → cần người dùng duyệt trước khi bật. |
| 29 | `locomotion_end_frame` | chưa | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | end_frame_distance 1 (31) | **GIỮ BẬT theo dõi** | Bật 13/10; 1 diag end_frame_distance #31; chưa đo riêng shot chạy. |
| 30 | `auto_send_self_fix` | chưa · OPT | ✅ bật (🧪) | có | ≤12/10 | #27 #28 #29 #30 #31 #33 | bg_auto_send 211 (24,27,28,29,30,31) | **GIỮ BẬT theo dõi** | OPT_IN tự tiêu tiền; bg_auto_send 211 lượt / 6 dự án, 0 lỗi gắn → hiệu quả tốt; không khóa (tự tiêu tiền), đưa vào baseline máy. |
| 31 | `support_tickets` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | 0 phiếu thật. |
| 32 | `chat_prompts` | chưa | ✅ bật (🧪) | có | ≤14/10 | #28 #29 #30 #31 #33 | chat_prompt 99 (29,30,31); chat_prompt_fail 98 (30,31,33); chat_prompt_refused 32 (29,30,31); chat_prompt_cap 14 (29,31); lỗi: P31-G29:OPEN, P33-A4:OPEN | **🔧 SỬA rồi bật/khóa** | D6 thắng thử 14/10 nhưng #29–#33: chat_prompt_fail 98, refused 32, vượt trần 14; G29 (pregen_check bỏ qua D6), #33 A4 phải tắt riêng. Sửa kiểm gói có D6 + lỗi hết tiền. |
| 33 | `motion_prose` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Dùng khi D6 tắt/vượt trần (#33 dùng nhiều); clip đơ 19/10 → xem lại câu "hold/slow" trong công thức. |
| 34 | `side_truth` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | side_truth 4 (30) | **GIỮ BẬT theo dõi** | diag side_truth 4 lượt (#30); chưa gen thật ngoài #30. |
| 35 | `travel_truth` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | travel_truth 4 (30,31); lỗi: P31-G41:OPEN | **🔧 SỬA rồi bật/khóa** | Bật 15/10; diag 4 lượt #30/#31; P31-G41 (hướng chạy) vẫn MỞ → bổ sung bằng world_map_sentences rồi đánh giá lại. |
| 36 | `script_pose_fix` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chỉ kiểm bằng test + dữ liệu #27/#28; 0 lỗi. |
| 37 | `mix_bus` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chỉ đo tín hiệu tổng hợp; bản giao #31/#33 dựng ngoài final_cut. |
| 38 | `post_fx_render` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chỉ thử clip tổng hợp. |
| 39 | `ref_beats_tool` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Công cụ CLI bật tay. |
| 40 | `shot_lessons_db_order` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Công cụ CLI chỉ đọc. |
| 41 | `seedance_sample_mode` | chưa | ✅ bật (🧪) | — | ≤08/10 | #24 #27 #28 #29 #30 #31 #33 | — | **⛔ TẮT-BỎ** | Hộp thử A/B 720p/480p (#22) đã được two_tier_quality thay; giữ chỉ thêm một đường gửi → đưa vào REMOVED. |
| 42 | `voice_check_redo` | chưa | ✅ bật (dashboard.env) | — | ≤27/09 | #8 #22 #24 #27 #28 #29 #30 #31 #33 | voice_check 149 (8) | **🔧 SỬA rồi bật/khóa** | Chỉ chạy trong autopilot (KIEM_22: 0 dấu vết, resends 0); khi đo sai thì trả tiền TTS. Nối + đo hoặc bỏ. |
| 43 | `film_crew` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | #8/#22 chạy thật, KIEM_22 kết luận V. |
| 44 | `director_two_pass` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | director_review 8 (8,22,24,27,28,30,31); dp_calls 9 (8,22,24,27,28,30,31) | **🔒 GIỮ KHÓA** | #8 duyệt 6/6 cảnh; chạy mọi dự án sau. |
| 45 | `voice_direction` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | #8: 23 câu đúng giọng. |
| 46 | `loudness_normalize` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | Bản giao #8 −14 LUFS. #24/#27/#33 dựng bằng script riêng nên cờ hậu kỳ không được chạy lại. |
| 47 | `shot_color_match` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | A/B #8 01/10, người dùng chọn bản CÓ. |
| 48 | `j_cut` | chưa | ✅ bật (dashboard.env) | — | ≤27/09 | #8 #22 #24 #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Bật env từ 27/09; #22 vô tác dụng (thoại khớp môi đi nhánh synced); dựng bằng Dashboard chỉ có #8/#22. |
| 49 | `music_breath` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | A/B #8 01/10. |
| 50 | `music_story_arc` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | Người dùng chốt 08/10 + 14/10. |
| 51 | `sound_intent` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | A/B #8 01/10. |
| 52 | `flashback_fx` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | A/B #8 01/10. |
| 53 | `end_hold` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | A/B #8 01/10. |
| 54 | `continuous_takes` | chưa | 🎓 học việc (dashboard.env) | — | ≤29/09 | #22 #24 #27 #28 #29 #30 #31 #33 | — | **⛔ TẮT-BỎ** | Học việc từ 08/10, KIEM_22 kết luận T: vô hiệu khi seedance_ref_groups bật (tuyến chính) → bỏ. |
| 55 | `shot_transitions` | chưa | ✅ bật (dashboard.env) | — | ≤29/09 | #22 #24 #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | #22 bản giao dùng flash, người dùng nhận (KIEM_22 M) → khóa sau 1 bản giao nữa qua final_cut. |
| 56 | `story_check` | chưa | ✅ bật (dashboard.env) | — | ≤29/09 | #22 #24 #27 #28 #29 #30 #31 #33 | story_unclear 1 (31) | **🔧 SỬA rồi bật/khóa** | Chỉ chạy trong autopilot (KIEM_22 "?"); 1 diag story_unclear #31. Nối vào đường thường hoặc bỏ. |
| 57 | `rough_cut_review` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chỉ đo; chưa chạy trên bản dựng thật. |
| 58 | `audio_first` | chưa | ✅ bật (dashboard.env) | — | ≤29/09 | #22 #24 #27 #28 #29 #30 #31 #33 | — | **🔧 SỬA rồi bật/khóa** | Chỉ chạy trong autopilot (KIEM_22: 0 dấu vết); #24–#33 không chạy autopilot → bật mà vô tác dụng. Nối vào đường Dashboard thường hoặc bỏ. |
| 59 | `music_fit` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | A/B #8 01/10. |
| 60 | `impact_shake` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | A/B #8 01/10. |
| 61 | `ambience_bed` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | A/B #8 01/10. |
| 62 | `speed_ramp` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chưa xem trên clip thật. |
| 63 | `motion_trim` | chưa | ✅ bật (dashboard.env) | — | ≤27/09 | #8 #22 #24 #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | #22 chỉ cắt đuôi 7 clip, chưa dời đầu lần nào. |
| 64 | `profile_digest` | chưa | ✅ bật (dashboard.env) | — | ≤27/09 | #8 #22 #24 #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Không tách được tác dụng (#22). |
| 65 | `camera_setups` | chưa | 🎓 học việc (dashboard.env) | — | ≤27/09 | #8 #22 #24 #27 #28 #29 #30 #31 #33 | — | **⛔ TẮT-BỎ** | Học việc, KIEM_22 T: chỉ thêm nhãn, không gộp clip; vai trò đã sang stage_camera/director_camera_plan → bỏ. |
| 66 | `seedance_ref_groups` | chưa | ✅ bật (dashboard.env) | — | ≤27/09 | #8 #22 #24 #27 #28 #29 #30 #31 #33 | — | **🔒 KHÓA BẬT** | Tuyến gen video thật của mọi dự án từ #22 (ref-only từng shot); tắt = đổi tuyến video. Đang bật bằng dashboard.env nên máy khác TẮT. |
| 67 | `scene_qc` | chưa | ✅ bật (🧪) | — | ≤16/10 | #31 #33 | trainee_log 199 dòng, 0 chấm | **🔧 SỬA rồi bật/khóa** | Bật 16/10 (tắt thì QC cũ quay lại). #31 chấm 0,96 cho clip gần đứng hình; #33 A5 đo nhầm cỡ cảnh → tự gen lại thừa. Bật qc_false_alarm_fix + video_qc_shadow để bù. |
| 68 | `project_budget` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | budget 125 (8,10,33); money_warning 254 (18,24,27,31,32,33) | **🔒 GIỮ KHÓA** | #8: khóa cứng chặn đúng ở trần. |
| 69 | `scene_qc_claude` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | — | **⛔ TẮT-BỎ** | Bật hàng loạt 15/10 không bằng chứng mới; nghiệm thu duy nhất (#8) KHÔNG đạt: bỏ lọt 6, báo nhầm 12/21 khung tốt; mỗi cảnh tự gọi Claude. Tắt tới khi nghiệm thu lại. |
| 70 | `next_glow` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | Chỉ giao diện, người dùng duyệt 07/10. |
| 71 | `chat_first` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | — | **🔒 KHÓA BẬT** | Chỉ giao diện Bước 1, 0 USD; đã dùng thật (7 phiên script_chat trong app_settings). |
| 72 | `idea_to_script` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | Cổng S11.2 đạt 4,20/5. |
| 73 | `horizon_needs_sky` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Phát lại video_gate trên #31 job 963/980 (2 lần bỏ qua) + S22/S39: phải ĐẠT; shot ngoài trời cũ vẫn bị đo. Đạt → bật + KHÓA video_gate. |
| 74 | `qc_false_alarm_fix` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Chấm lại QC lớp 0 trên #33 S2 (A5) + #877 (A6): hết báo nhầm; các khung khác không đổi kết luận. |
| 75 | `video_qc_shadow` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Shadow (ffmpeg/OpenCV 0 USD) trên 39 clip nháp #31 + 6 clip #33: phải bắt shot 13 đơ 6 s (G51), đối chiếu nhận xét 19/10 → hiệu chuẩn ngưỡng (M4.6). Chỉ ghi → bật ngay. |
| 76 | `continuity_shadow` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Shadow trên 39 clip #31 theo thứ tự truyện: phải ra G51 (súng biến mất), G52 (nhặt súng trên thềm cao). Chỉ ghi → bật ngay. |
| 77 | `send_preview_panel` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Chỉ giao diện: tools/ui_snapshot.py trên bản sao #33 Bước 4, so "Gói sẽ gửi" với sent_package thật. |
| 78 | `continuity_state` | chưa | ⬜ tắt (mặc định code) | — | — | — | lỗi: P31-G1:IN_PROGRESS | **🧪 KIỂM CHỨNG nhanh** | Shadow trên BYĐ #31 cảnh 3–8: phải bắt G1 (khối mang sang cảnh 8). Chỉ ghi → bật ngay. |
| 79 | `whitebox_height_dummy` | chưa | ⬜ tắt (mặc định code) | — | — | — | lỗi: P31-G3:IN_PROGRESS | **🧪 KIỂM CHỨNG nhanh** | Render Blender cục bộ #31 shot 28 (G3: khai eye mà pitch +17,3°) với người nộm đúng height_m. 0 USD. |
| 80 | `final_black_freeze` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Chạy trên bản giao #27 v6 + #33 TikTok (không được báo nhầm) và clip #31 shot 13 (phải bắt). |
| 81 | `qc_evidence` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Cần migration Cấp 3; trước đó ghi JSON <dự án>/qc_* trên bản sao #31 → so 9 đường QC cùng schema. |
| 82 | `repair_router` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Chỉ đề xuất: chạy trên 108 lần loại có lý do của #31 → so đề xuất với việc người đã làm. |
| 83 | `release_gate` | chưa | ⬜ tắt (mặc định code) | — | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | Shadow checklist 8 mục trên #33 (đã giao): phải giải thích được từng mục. |
| 84 | `qc_observe_enum` | chưa · OPT | ✅ bật (🧪) | — | ≤12/10 | #27 #28 #29 #30 #31 #33 | lỗi: V21-R3:FIXED_UNVERIFIED | **GIỮ BẬT theo dõi** | OPT_IN; lỗi V21-R3 (crash khi vat là chuỗi) FIXED_UNVERIFIED. |
| 85 | `qc_team` | chưa | 🎓 học việc (🧪) | — | ≤15/10 | #31 #33 | trainee_log 120 dòng, 0 chấm | **🎓 GIỮ học việc** | Khớp người 49 % (14/10) < 75 % (quyết định qc-team-off-until-75). trainee_log 120 dòng chưa từng được chấm (match NULL) → sửa vòng chấm. |
| 86 | `qc_agent` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Bản trong app chưa nghiệm thu (chỉ thử bằng agent phiên 27/09). |
| 87 | `scene_qc_trusted` | chưa | 🎓 học việc (🧪) | — | ≤16/10 | #31 #33 | — | **🎓 GIỮ học việc** | Học việc từ 15/10; chưa có dòng trainee_log riêng → chưa có dữ liệu chấm. |
| 88 | `scene_establishing` | chưa | 🎓 học việc (dashboard.env) | — | ≤28/09 | #8 #22 #24 #27 #28 #29 #30 #31 #33 | establishing 11 (8,10,22); trainee_log 47 dòng, 0 chấm | **⛔ TẮT-BỎ** | Học việc, KIEM_22 T: ảnh toàn cảnh AI không có trong khung duyệt nào, từng kéo cảnh trong nhà ra ngoài trời; place_render_refs đã thay → bỏ. |
| 89 | `lip_sync` | chưa | ✅ bật (dashboard.env) | — | ≤27/09 | #8 #22 #24 #27 #28 #29 #30 #31 #33 | lipsync_no_post 18 (8); lipsync_not_applied 2 (22); lipsync_audio 4 (8); lỗi: P31-G17:OPEN | **🔧 SỬA rồi bật/khóa** | Bật bằng dashboard.env; #22 tương quan môi 0,03/0,44 (< 0,65); P31-G17 (quality_tier coi lip_sync=True là có khớp môi), G10 (lời dẫn bị coi là thoại). Sửa rồi chạy 1 shot cận thật (quyết định lip-sync-lock-after-real-run) → khóa. |
| 90 | `seedance_subjects` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | subjects 204 (22,24,27,29,28,31,33) | **🔒 GIỮ KHÓA** | diag subjects 204 lượt / 7 dự án. Khi Kho đầy 100/100 (#31 G30) mất tác dụng → cần subject_capacity_guard. |
| 91 | `dialogue_take` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | lỗi: P31-G10:FIXED_UNVERIFIED | **🔧 SỬA rồi bật/khóa** | Khóa nhưng VÔ TÁC DỤNG khi lip_sync tắt (REQUIRES); lip_sync chỉ bật bằng dashboard.env máy chính và còn lỗi P31-G17/G10 → sửa lip_sync rồi khóa cùng. |
| 92 | `anchor_by_spot` | chưa · OPT | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | storyboard_anchor_unapproved 39 (31,33); storyboard_anchor_skipped 111 (24,27,28,29,30,31) | **GIỮ BẬT theo dõi** | OPT_IN; storyboard_anchor_unapproved 39 lượt (#31/#33). |
| 93 | `storyboard_api` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | #22: 7/9 ảnh duyệt có ref storyboard; dùng mọi dự án sau. |
| 94 | `place_render_refs` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | place_render 33 (24,27,28,30,31); place_match 381 (22,24,27,28,29,30,31,33) | **🔒 GIỮ KHÓA** | #22: 9/9 ảnh duyệt có render 3D; diag place_render/place_match ở 8 dự án. |
| 95 | `end_frames` | chưa | ✅ bật (🧪) | — | ≤12/10 | #27 #28 #29 #30 #31 #33 | end_frame_missing 9 (31); end_frame_skill_object 39 (31,33); lỗi: P33-A11:OPEN | **🔧 SỬA rồi bật/khóa** | Bật ở 🧪 (nhãn why còn ghi học việc); #33 A11: thông điệp "ném keo" sai 28 lần; end_frame_missing 9 lần #31. Sửa thông điệp/nhãn, giữ bật. |
| 96 | `ui_v2` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | — | **🔒 GIỮ KHÓA** | Giao diện mặc định từ 05/10. |
| 97 | `storyboard_auto_trust` | chưa | 🎓 học việc (dashboard.env) | — | ≤27/09 | #8 #22 #24 #27 #28 #29 #30 #31 #33 | — | **⛔ TẮT-BỎ** | Học việc, chỉ chạy autopilot, look_trust 69,7 % < 90 % → không thể kích hoạt; bỏ khỏi dashboard.env. |
| 98 | `ai_label` | chưa | ⬜ tắt (mặc định code) | — | — | — | — | **GIỮ TẮT (quyết định)** | Người dùng duyệt 29/09: chỉ bật khi phát ở thị trường bắt nhãn AI. |
| 99 | `speaker_tags` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chỉ cho Kling — nay Kling chỉ là đường lùi → gần như không kích hoạt. |
| 100 | `hero_takes` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | — | **🔧 SỬA rồi bật/khóa** | Gen THÊM một bản cho shot ⭐ = tốn tiền nhưng KHÔNG khai costs: True (nút bật hàng loạt cờ 0 USD có thể bật nhầm). Khai costs rồi để người dùng chọn. |
| 101 | `skill_dossier` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Director đọc hồ sơ; không đo riêng. |
| 102 | `seedance_video_edit` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chỉ khi người bấm; thử 1 clip #8. |
| 103 | `director_rewrite` | chưa | ✅ bật (🧪) | — | ≤10/10 | #24 #27 #28 #29 #30 #31 #33 | director_rewrite 19 (24,27,31,33); director_rewrite_fallback 54 (27,31,33); lỗi: P31-G57:IN_PROGRESS, P33-A4:OPEN | **🔧 SỬA rồi bật/khóa** | #33 A4: tự viết lại image_prompt người đã chỉnh (dời tháp), người dùng phải tắt trong tiến trình gen; G57 fallback khi không có provider. Sửa: không ghi đè trường người đã khóa. |
| 104 | `change_review_frames` | chưa | ✅ bật (🧪) | có | ≤12/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | costs; đi theo change_review (xem SỬA). |
| 105 | `change_review` | chưa | ✅ bật (🧪) | có | ≤11/10 | #24 #27 #28 #29 #30 #31 #33 | change_review_hold 5710 (27,31,33); change_review_fail 234 (27,31,33); change_review_est 892 (24,27,28,29,30,31,33); change_findings #31: ĐỎ 82 xử lý / 80 bỏ qua; review_fail 39 bỏ qua; lỗi: P31-G34:OPEN, P31-G35:FIXED_UNVERIFIED, P31-G56:OPEN | **🔧 SỬA rồi bật/khóa** | #31: 162 mục ĐỎ có 80 bị bỏ qua (49 %) + 39 review_fail bị bỏ; G35: Claude lỗi mà cổng MỞ → job tự gửi; G56: change_review_hold 5 710 lượt. Có ích (251 VÀNG đã xử lý) nhưng phải sửa fail-closed + báo nhầm. |
| 106 | `change_review_motion` | chưa | ✅ bật (🧪) | có | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | costs; đi theo change_review. |
| 107 | `video_gate` | chưa · dOn | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | plate_layout 167 (28,29,30,31,33); video_gate_skips 2 (báo nhầm G20) | **🔧 SỬA rồi bật/khóa** | default_on; 2 lần người dùng phải bỏ qua cổng vì báo nhầm lệch nền khi ảnh không có trời (bảng video_gate_skips, P31-G20) → bật horizon_needs_sky rồi KHÓA. |
| 108 | `qc_framing_cap` | chưa · dOn | ✅ bật (🧪) | có | ≤15/10 | #31 #33 | qc_framing_cap 17 (31) | **GIỮ BẬT theo dõi** | costs; 17 lần ở #31 nhưng QC vẫn cho qua clip đơ (0,96) → cần video_qc_shadow. |
| 109 | `stage_camera` | chưa | ✅ bật (🧪) | — | ≤10/10 | #24 #27 #28 #29 #30 #31 #33 | stage_facts 102 (24,31); plate_layout 167 (28,29,30,31,33); lỗi: P31-G1:IN_PROGRESS | **🔒 KHÓA BẬT** | Đường 3D chính #24/#31/#33 (21 file đọc cờ); tắt = quay về tả nền bằng chữ (lỗi lặp số 1). G1 là lỗi của stage_auto, không phải cờ này. |
| 110 | `stage_auto` | chưa | ⬜ tắt (mặc định code) | có | — | — | stage_auto 34 (31); lỗi: P31-G1:IN_PROGRESS, P31-G3:IN_PROGRESS, P31-G8:FIXED_UNVERIFIED | **🔧 SỬA rồi bật/khóa** | fixes_projects [31] → đang ĐỎ ở 🧭 cho dự án #34. Chạy tay #31 bằng tools/stage_auto.py (diag 34 lượt), hỏng 2 lần 16/10 (0,68 USD); G1/G3 đang sửa, G8 chờ kiểm. Bật cho dự án kế sau preflight 0 USD. |
| 111 | `stage_crew` | chưa · OPT | ⬜ tắt (mặc định code) | có | — | — | CHƯA ĐỦ BẰNG CHỨNG | **🧪 KIỂM CHỨNG nhanh** | OPT_IN, tốn Claude; chưa thử. Ca ngoại tuyến: #31 shot 10 cảnh 3 (Kelly chắn xe nôi 237 %) — so bảng đối chiếu số đo với bộ kiểm cũ. |
| 112 | `stage_handheld_props` | chưa · OPT | ✅ bật (🧪) | — | ≤20/10 | #33 | — | **🔧 SỬA rồi bật/khóa** | Bật 20/10 nhưng VÔ TÁC DỤNG: cần stage_auto (đang tắt) — unmet_all() báo. |
| 113 | `stage_crew_user_approve` | chưa · dOn | ✅ bật (mặc định code) | — | mặc định | mọi dự án từ khi khóa/mặc định | — | **🔧 SỬA rồi bật/khóa** | default_on nhưng VÔ TÁC DỤNG: cần stage_crew (tắt). |
| 114 | `director_camera_plan` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | director_camera_plan 44 (24,31) | **GIỮ BẬT theo dõi** | #24/#31: 44 lượt (20 VÀNG, 1 ĐỎ). |
| 115 | `shot_intent` | chưa | ✅ bật (🧪) | — | ≤12/10 | #27 #28 #29 #30 #31 #33 | director_byd 6 (24,28,30,31); lỗi: V21-R3:FIXED_UNVERIFIED | **GIỮ BẬT theo dõi** | BYĐ dùng ở #24/#28/#30/#31, nhiều cờ dựa vào; thiếu BYĐ ở shot chèn tay (G21) và #33 (A12) → sửa nguồn BYĐ rồi khóa. |
| 116 | `video_pregen` | chưa | ✅ bật (🧪) | — | ≤12/10 | #27 #28 #29 #30 #31 #33 | video_pregen 126 (27,29,28,31,33); video_pregen_hold 4 (27,29); lỗi: P31-G21:OPEN, P33-A12:OPEN | **🔒 KHÓA BẬT** | Bật 12/10: 126 lượt kiểm / 5 dự án (#27–#33), 4 lần giữ; báo nhầm cũ đã hạ VÀNG. Kèm sửa nhiễu P33-A12 (VÀNG "chưa có BYĐ" 22 lần ở #33). |
| 117 | `murch_knowledge` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chỉ thêm tri thức prompt; không đo riêng. |
| 118 | `auto_voice_cast` | chưa | ✅ bật (🧪) | — | ≤07/10 | #22 #24 #27 #28 #29 #30 #31 #33 | auto_voice_cast 2 (22); auto_voice_missing 2 (27,31) | **GIỮ BẬT theo dõi** | #22 có ích (KIEM_22 M); auto_voice_missing #27/#31. |
| 119 | `asset_checklist` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Lượt Claude trước Director; chưa nghiệm thu 2 kịch bản. |
| 120 | `kelly_knowledge` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Tri thức prompt; không đo. |
| 121 | `kld_lessons_prompts` | chưa | ✅ bật (🧪) | có | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | costs; bài học #22; không đo riêng. |
| 122 | `p24_lessons` | chưa | ✅ bật (🧪) | có | ≤12/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | costs; bài học #24; không đo riêng. |
| 123 | `lesson_judge` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Bóng; lesson_reviews 0 dòng → chưa chạy lần nào. |
| 124 | `palette_check` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chỉ thử ảnh tổng hợp. |
| 125 | `risk_tags` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | lessons 12 dòng cũ; chưa đủ ngưỡng. |
| 126 | `feedback_to_mistakes` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | user_feedback 0 dòng → chưa kích hoạt lần nào (mistakes #31/#33 tăng nhờ lý do loại C2, không nhờ cờ này). |
| 127 | `outfit_strip_model` | chưa | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Sửa lỗi #22; không đo sau đó. |
| 128 | `asset_english_names` | chưa · OPT | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | asset_english_name 6 (33) | **GIỮ BẬT theo dõi** | OPT_IN; 6 VÀNG ở #33. |
| 129 | `film_grammar_check` | chưa · OPT | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | OPT_IN; 0 dấu vết. |
| 130 | `camera_match_qc` | chưa · OPT | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | OPT_IN; 0 dấu vết. |
| 131 | `continuity_layout` | chưa | ✅ bật (🧪) | — | ≤12/10 | #27 #28 #29 #30 #31 #33 | — | **🔧 SỬA rồi bật/khóa** | Bật 12/10, chỉ VÀNG, không có dấu vết đo; lỗi giữa shot #31 (G51/G52) không bắt được → thay bằng continuity_state/continuity_shadow. |
| 132 | `ambient_motion` | chưa | ✅ bật (🧪) | có | ≤12/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | costs; người dùng 11/10 "video không được đơ" → ghi sổ quyết định + default_on. |
| 133 | `prompt_formula` | có | ✅ bật (khóa) | — | khóa | mọi dự án từ khi khóa/mặc định | prompt_formula 264 (24,27,28,30,31,33); lỗi: P31-G7:FIXED_UNVERIFIED | **🔒 GIỮ KHÓA** | diag prompt_formula 264 lượt / 6 dự án; chặn câu mâu thuẫn trước khi trả tiền (#33 B6). |
| 134 | `project_prop_lock` | chưa | ✅ bật (🧪) | — | ≤12/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Bật 12/10; vẫn 9 lần loại "đạo cụ Kho sai" ở #31. |
| 135 | `skill_object_guard` | chưa | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | skill_object_words 90 (28,29,30,31); skill_object_compose 28 (29,28,31) | **GIỮ BẬT theo dõi** | Bật 13/10; skill_object_words 90 lượt #28–#31; "đạo cụ Kho vẽ sai" vẫn 9 lần loại ở #31. |
| 136 | `ref_mark_off_face` | chưa | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | Chỉ tác dụng khi Kho đầy; #31 Kho đầy nhưng chưa đo dấu có rời mặt không. |
| 137 | `plate_view_sentence` | chưa · dOn | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | gói gửi có câu: #31 53, #33 16 | **🔒 KHÓA BẬT** | default_on 15/10; câu PLACE render có trong 53 gói gửi #31 + 16 gói #33 (quét sent_package); 0 lỗi gắn cờ. |
| 138 | `group_keep_approved` | chưa · dOn | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | default_on; chưa có dấu vết đo. |
| 139 | `motion_consistency_lint` | chưa · dOn | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | — | **🔧 SỬA rồi bật/khóa** | default_on, không tách được dấu vết; 19/10 người dùng: clip #31 đơ/giữ tư thế mà lint không bắt → thêm luật chặn "hold/pause/poised/slowly" rồi khóa. |
| 140 | `character_state_lock` | chưa · dOn | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | gói gửi có câu: 0 | **GIỮ BẬT theo dõi** | default_on; 0 gói gửi có câu khóa trạng thái (#27–#33) → chưa kích hoạt lần nào. |
| 141 | `ref_rule_early` | chưa · dOn | ✅ bật (🧪) | — | ≤15/10 | #31 #33 | CHƯA ĐỦ BẰNG CHỨNG | **GIỮ BẬT theo dõi** | default_on; chưa có ca ảnh sai tỉ lệ được ghi. |
| 142 | `plate_anchored_image` | chưa | ✅ bật (🧪) | — | ≤13/10 | #27 #28 #29 #30 #31 #33 | plate_anchor_words 118 (31,33); plate_anchor_background 15 (31) | **GIỮ BẬT theo dõi** | plate_anchor_words 118 lượt (#31/#33) nhưng "nền lệch map 3D" vẫn là lý do loại ảnh số 1 ở #31 (30 lần). |
| 143 | `qc_sequence_logic` | chưa | ⬜ tắt (mặc định code) | có | — | — | lỗi: P31-G52:OPEN | **🧪 KIỂM CHỨNG nhanh** | Tốn Claude (claude_cli 0 USD API). Bản chạy tay 19/10 trên 39 clip #31 (scripts_19-10/qc_sequence) đã tìm ra G52 → bằng chứng tốt; chạy lại qua cờ trên bản sao CSDL #31, so với 7 lỗi người dùng chỉ ra. |
| 144 | `two_tier_quality` | chưa | ✅ bật (🧪) | — | ≤09/10 | #24 #27 #28 #29 #30 #31 #33 | tier_to_draft 3 (31); qc_draft_suggest 116 (24,27,29,28,31) | **🔧 SỬA rồi bật/khóa** | #31 nháp 480p + #33 nâng 6 bản cao 1080p thật (22,91 USD): chạy được. Nhãn "MỌI shot nháp" lệch quyết định 13/10 (RA_QUYET_DINH A3), giá bản cao lệch +24 % (#33 A7) → sửa nhãn + send_estimate rồi KHÓA. |

## 4. Đề xuất gom theo nhóm

| Nhóm | Số | Cờ |
|---|---|---|
| 🔒 GIỮ KHÓA (đã verified) | 22 | subject_auto_cleanup, film_crew, director_two_pass, voice_direction, loudness_normalize, shot_color_match, music_breath, music_story_arc, sound_intent, flashback_fx, end_hold, music_fit, impact_shake, ambience_bed, project_budget, next_glow, idea_to_script, seedance_subjects, storyboard_api, place_render_refs, ui_v2, prompt_formula |
| 🔒 KHÓA BẬT (đặt `verified: True`) | 8 | send_claim, video_pregen, framing_guard, plate_view_sentence, stage_camera, seedance_ref_groups, back_view_guard, chat_first |
| 🔧 SỬA rồi bật/khóa | 20 | video_gate, two_tier_quality, motion_consistency_lint, change_review, director_rewrite, chat_prompts, bg_autoqc, lip_sync, dialogue_take, end_frames, scene_qc, stage_auto, stage_handheld_props, stage_crew_user_approve, travel_truth, continuity_layout, hero_takes, audio_first, story_check, voice_check_redo |
| GIỮ BẬT theo dõi (chưa đủ bằng chứng) | 64 | xem bảng; gồm toàn bộ cờ tri thức prompt (murch/kelly/kld/p24), cờ sửa lỗi #27/#28 chưa có số đo riêng, cờ OPT_IN tự tiêu tiền (auto_send_self_fix…), poll_claim + pause_before_submit (bật 20/10, chưa có job) |
| ⛔ TẮT-BỎ | 6 | scene_qc_claude (tắt), seedance_sample_mode, continuous_takes, camera_setups, storyboard_auto_trust, scene_establishing (đưa vào REMOVED) |
| 🎓 GIỮ học việc | 2 | qc_team, scene_qc_trusted |
| 🧪 KIỂM CHỨNG nhanh | 21 | 19 cờ V3.1 + stage_crew + qc_sequence_logic (mục 4.3) |
| GIỮ TẮT (quyết định) | 1 | ai_label |

### 4.1 Mười cờ đáng khóa nhất (theo thứ tự)

1. `send_claim`: chặn gửi trùng job (tiền thật), chạy #27→#33, 0 lỗi.
2. `video_pregen`: 126 lượt kiểm trước gen / 5 dự án, giữ đúng 4 lần; còn nhiễu VÀNG khi thiếu BYĐ (sửa kèm).
3. `framing_guard`: bắt đúng P31-G28 (clip không bắt đầu ở khung đầu đã duyệt), 0 USD.
4. `plate_view_sentence`: có trong 69 gói gửi thật #31/#33, 0 lỗi.
5. `stage_camera`: đường 3D chính; tắt là quay về lỗi lặp số 1.
6. `seedance_ref_groups`: tuyến video thật từ #22; hiện chỉ bật bằng dashboard.env, máy khác sẽ đổi tuyến.
7. `back_view_guard`: 35 gói gửi #27, không còn lỗi quay mặt.
8. `chat_first`: chỉ giao diện, đã dùng thật.
9. `video_gate`: ngay sau khi bật `horizon_needs_sky` (2 lần báo nhầm G20 là lý do duy nhất chưa khóa).
10. `two_tier_quality`: bản cao chạy thật ở #33; sửa nhãn + ước tính giá rồi khóa.

Ngay sau đó: `poll_claim`, `pause_before_submit` (khóa sau 1 dự án có job), `shot_intent` (sửa nguồn BYĐ).

### 4.2 Cờ nguy hiểm: tắt hoặc chặn ngay

| Cờ | Vì sao nguy hiểm | Đề xuất |
|---|---|---|
| `scene_qc_claude` | Mỗi cảnh tự gọi Claude khi đủ khung; nghiệm thu duy nhất (#8) KHÔNG đạt (báo nhầm 12/21 khung tốt); bật hàng loạt 15/10 không có bằng chứng mới | **TẮT** tới khi nghiệm thu lại |
| `director_rewrite` | #33 A4: ghi đè image_prompt người đã chỉnh tay (dời tháp, thêm mặt đồng hồ), người dùng phải tắt trong tiến trình gen | Tắt ở dự án đang chỉnh tay tới khi có "không ghi đè trường người khóa" |
| `change_review` | G35: Claude lỗi (hết tiền) mà cổng giữ vẫn MỞ → job tự gửi trả tiền; ĐỎ #31 bị bỏ qua 49 % | Sửa fail-closed TRƯỚC dự án kế (đang bật) |
| `hero_takes` | Gen thêm bản (tốn tiền) mà không khai `costs: True` → nút "bật hàng loạt cờ 0 USD" (`before_run.costly_fix_flag`) không nhận ra | Khai costs ngay |
| `chat_prompts` | Mỗi lần gửi thêm 1 lượt Claude; 98 lỗi + 32 từ chối ở #29–#33; pregen_check không dựng gói có D6 (G29) | Giữ bật nhưng sửa kiểm gói; tắt khi provider hết tiền |
| `dialogue_take` 🔒 + `lip_sync` | Khóa giả: cờ khóa vô tác dụng ở máy không có `FEATURE_LIP_SYNC=1`; G17 quality_tier hiểu sai | Sửa REQUIRES/khóa cùng sau 1 shot thật |

### 4.3 Nhóm cờ mới V3.1 (20–21/10) — kiểm chứng nhanh để không kẹt TẮT

19 cờ V3.1 (+ `stage_crew`, `qc_sequence_logic`) đều TẮT vì luật 5 + quyết định `v31-permission-tiers-2026-10-20` (bật cờ ảnh hưởng workflow
đang chạy = Cấp 3). Tách 3 bậc:

| Bậc | Cờ | Đề xuất |
|---|---|---|
| A. Chỉ ghi / chỉ hiển thị (không đổi gói gửi, không chặn) | stale_code_alarm, diag_merge, budget_notice_d01, video_qc_shadow, continuity_shadow, continuity_state, world_map, send_preview_panel, qc_evidence (ghi JSON), repair_router (chỉ đề xuất), release_gate (shadow) | Xin MỘT gói Cấp 3 "bật toàn bộ shadow" sau 1 lượt phát lại 0 USD trên bản sao #31/#33 (cột lý do trong bảng). Không đổi phim nên bật được ngay cho dự án #34 |
| B. Bớt báo nhầm / đúng giá (đổi kết luận cổng, không tốn tiền) | horizon_needs_sky, qc_false_alarm_fix, send_estimate, final_black_freeze, subject_capacity_guard | Mỗi cờ có ca đáp án đã biết (G20, A5/A6, A7–A9, G51, G30/G32): phát lại → đạt → bật + **khai `fixes_projects: [31]` / `[33]`** để C1 báo ĐỎ ở #34 nếu còn tắt |
| C. Đổi gói gửi / thứ tự / tốn tiền | world_map_sentences, refusal_skip_same_picture, whitebox_height_dummy, stage_crew, qc_sequence_logic | Chạy shadow/ngoại tuyến ở #31 trước; refusal_skip_same_picture đổi thứ tự người dùng chốt 27/09 → hỏi người dùng; qc_sequence_logic đã có bằng chứng tay 19/10 → nên là cờ đầu tiên của bậc C |

Hạn chót đề xuất: mỗi cờ V3.1 khai `verify_by` (dự án hoặc ngày). Quá hạn mà chưa phát lại → tự hiện ở 🧭 "cờ chờ kiểm chứng".

## 5. Cơ chế để cờ đã kiểm chứng không bị tắt ở dự án sau (chỉ đề xuất, chưa code)

1. **Baseline cờ sản xuất trong git** (`data/feature_baseline.json`, sinh từ `features.report()` máy chính, commit theo quyết định).
   `default_state()` đọc baseline trước khi rơi về `verified`/`default_on`; `data/feature_settings.json` chỉ còn ghi chỗ máy này KHÁC baseline.
   Worktree/cloud/Codex/đồng nghiệp tự có đúng trạng thái sản xuất. Gộp luôn 36 dòng `FEATURE_` của dashboard.env vào baseline.
2. **Chụp cờ theo dự án**: lúc tạo dự án / qua Bước 1 / mỗi lần gửi job, ghi băm `features.report()` (cột `jobs.flags_hash` + bảng
   `project_flag_snapshots`). Báo cáo kết thúc dự án và đánh giá cờ đọc từ đây thay cho dò bản sao lưu.
3. **ĐỎ ở 🧭 Trước khi chạy khi cờ BẬT ở dự án trước nay đang TẮT** (mở rộng `fix_flags_off`, không cần `fixes_projects`): so snapshot dự án gần
   nhất có job với `state()` hiện tại. Có nút "bật lại như #N" (cờ `costs` vẫn hỏi giá).
4. **Tự đề nghị khóa**: cờ bật ở ≥ 2 dự án có job thật, 0 lỗi `devsys/errors.json` mở gắn tên cờ, mã diag của cờ không có `error`
   bị người bỏ qua > 20 % → 🧪 hiện "Đề nghị khóa" + bằng chứng; người dùng bấm → ghi `data/flag_locks.json` (trong git, có `evidence_job_ids`).
   `locked()` đọc thêm tệp này, nên không phải sửa `verified` trong code và không đụng 362 test.
5. **Test theo sản xuất**: ngoài bộ "cờ tắt" hiện có, chạy một lượt bộ test chính với baseline (fixture `FEATURE_SETTINGS_FILE` = baseline)
   — gốc của revert 13/10 và vụ stage_auto 16/10.
6. **Khai báo bắt buộc cho cờ mới**: `fixes_projects` (hoặc `fixes_errors: ["P31-G20"]`) + `verify_plan` + `verify_by`; test devsys chặn cờ mới thiếu.
   Cờ chỉ-ghi (shadow) khai `shadow_only: True`: được mặc định bật (Cấp 3 duyệt một lần cho cả lớp).
7. **Học việc phải được chấm**: `trainee.score_project` chạy tự động khi giao/cất dự án; 366 dòng hiện có chưa chấm dòng nào.
8. **Nút "↺ Bỏ mọi lựa chọn riêng"** (`header.py:732`): bắt xác nhận + sao lưu tự động `data/backup/feature_settings.before_reset_<giờ>.json`,
   hoặc bỏ nút khi đã có baseline.
9. **Cờ khóa phụ thuộc cờ chưa khóa** (`dialogue_take`→`lip_sync`): test devsys chặn (verified mà REQUIRES chưa verified).

## 6. Phương pháp và giới hạn

- Ngày "bật từ" lấy theo mtime bản sao lưu (bản sao chụp TRƯỚC thay đổi, nên cờ đã bật chậm nhất vào ngày đó). Cờ env lấy ngày bản sao
  `dashboard.env` đầu tiên có dòng.
- Mã diag gắn cờ: lấy mã ở code đọc cờ + mã trùng tên. Một số mã dùng chung nhiều cờ (vd `plate_layout`), nên số lượt là cận trên.
- Quét `sent_package` theo câu đặc trưng chỉ làm cho `plate_view_sentence`, `back_view_guard`, `character_state_lock`. Cờ khác muốn đếm lần
  kích hoạt thì cần bước (2) mục 5, hoặc thêm diag `info` khi cờ đổi gói.
- Không mở ảnh/clip; bằng chứng chất lượng lấy từ lý do loại (`jobs.reject_reason`), `change_findings`, nhận xét người dùng trong docs/memory.
- Cờ hậu kỳ không có dữ liệu sau #22 (bản giao #24/#27/#33 dựng bằng script).
