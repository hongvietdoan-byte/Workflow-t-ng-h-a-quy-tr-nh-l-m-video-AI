# Đề xuất khóa thêm cờ (verified = 🔒 khóa bật) — 15/10/2026

Phiên chỉ đọc (0 USD), không đặt `verified` cho cờ nào. Nguồn danh sách: cờ **chưa verified** đang bật trên máy chính —
`D:\AI-Video-Pipeline\data\feature_settings.json` mục `flags` = true (S) và dòng `FEATURE_X=1` trong `dashboard.env` (E; chỉ đọc dòng FEATURE_).
Có 56 cờ. Bằng chứng: `why` trong `core/features.py` (số dòng = dòng khai cờ), `TODO.md`, `docs/TODO_LICH_SU.md`, `docs/handoff/*`,
CSDL máy chính đọc chỉ-đọc (`diag_events`, `job_send_claims`).

Luật phân nhóm: **(1) ĐỀ XUẤT KHÓA** = chạy thật ≥ 1 dự án, không lỗi / báo nhầm được ghi; **(2) CHƯA ĐỦ** bằng chứng (chưa chạy thật,
mới test/giả lập, hoặc có lỗi/báo nhầm/giới hạn được ghi); **(3) KHÔNG nên khóa** = tự tiêu tiền (OPT_IN_ONLY, `costs`, lời gọi trả tiền
tự chạy), học việc 🎓, hoặc người dùng đã quyết tắt.

Tổng: nhóm 1 = **1** · nhóm 2 = **33** · nhóm 3 = **22**.

**Lưu ý REQUIRES:** `dialogue_take` (đã verified → giờ 🔒) cần `lip_sync` (chưa verified, bật bằng `FEATURE_LIP_SYNC=1` ở máy chính).
Không đặt `verified` cho `lip_sync` vì chưa có bằng chứng (`features.py:375`; TODO.md:175–176 đo lệch môi 0,45 s ở #24). Người dùng quyết:
khóa `lip_sync` sau 1 lần chạy thật, hoặc bỏ `verified` khỏi `dialogue_take`.

## Nhóm 1 — ĐỀ XUẤT KHÓA (1)

| cờ | bằng chứng + nguồn | tốn tiền? |
|---|---|---|
| send_claim | Bật 12/10 trên máy chính (TODO.md:135); chạy thật #27: CSDL `diag_events` code `send_claim*` 1 dòng #27 "job đã sang 'running' ở nơi khác — không gửi" (chặn đúng gửi trùng); không lỗi được ghi. Giới hạn đã biết (không phải lỗi): không chặn 2 job gen lại KHÁC nhau (TODO.md:119) | 0 USD (chống tốn) |

## Nhóm 2 — CHƯA ĐỦ bằng chứng (33)

| cờ | bằng chứng + nguồn | tốn tiền? |
|---|---|---|
| video_pregen | Chạy thật #27 (38 diag), #28/#29; nhưng **báo nhầm được ghi**: chặn 'thiếu nhịp đỉnh' cùng tư thế (đã sửa → VÀNG, TODO.md:21); 'tệp ảnh bị thay' không gỡ bằng duyệt lại (TODO.md:134). Ứng viên mạnh sau 1 dự án sạch (#31) | 0 USD |
| project_prop_lock | Chạy thật #27 (TODO.md:151, kiểm shot 21 TODO.md:130); **giới hạn được ghi**: nhiều súng chỉ VÀNG, từ màu mâu thuẫn còn trong prompt → ảnh ánh vàng (TODO.md:88–92) | 0 USD |
| shot_intent | BYĐ #24 điền thật 9/9 OK (TODO.md:201); nhưng BYĐ #28 ghi quỳ sai → phải thêm `script_pose_fix` (features.py:106); chỉ tác dụng khi Đạo diễn chạy lại (TODO.md:139) | thêm token Claude trong lượt Đạo diễn (người bấm) |
| framing_guard | Bật 13/10 (TODO.md:606), diag #28/#29; "ĐỎ 4/10" + Seedance vẫn lùi máy (TODO.md:20–21), miễn zoom-out còn ở nhánh chờ (TODO.md:19); why: chưa chạy trong sản xuất (features.py:51) | 0 USD |
| skill_object_guard | Bật 13/10; diag `skill_object_words` #28–#30; lỗi lặp "đạo cụ Kho vẽ sai" #22–#30 vẫn mở (RA_QUYET_DINH_LOI_LAP_2026-10-15.md:40); why: chưa gen thật với chữ mới (features.py:652) | 0 USD |
| ref_mark_off_face | why: kiểu corner_plus chưa thử qua bộ lọc người thật (features.py:661) | 0 USD |
| plate_anchored_image | why + TODO.md:31: chưa chạy thật (features.py:699) | 0 USD |
| locomotion_end_frame | Code xong, chưa có lần chạy được ghi (TODO.md:38; features.py:65) | 0 USD |
| tts_lowercase_caps | why: mới thử tay 1 câu (features.py:60) | 0 USD |
| back_view_guard | Sửa lỗi #27 shot 4 (TODO.md:135); chưa có lần gen thật được ghi (features.py:55) | 0 USD |
| continuity_layout | Bật 13/10 cho #27 (TODO.md:36, 84); chỉ VÀNG, không có diag / kết quả đo được ghi (features.py:629) | 0 USD |
| travel_truth | #30 vẽ lại shot 1 vẫn sai hướng, mâu thuẫn chữ↔nền phải chặn trước gen (TODO.md:13–19); why: chưa gen thật (features.py:98) | 0 USD |
| side_truth | Diag 4 dòng #30 (thử); why: chưa gen thật với câu mới (features.py:90) | 0 USD |
| script_pose_fix | why: mới kiểm bằng test + dữ liệu #27/#28 (features.py:106) | 0 USD |
| video_gate | `default_on` C1 15/10, chưa từng bật trước đó (RA_QUYET_DINH_LOI_LAP_2026-10-15.md:14); làm clip đang xếp hàng phải CHỜ người (dòng 62) | 0 USD |
| plate_view_sentence | `default_on` 15/10, chưa từng chạy (RA_QUYET_DINH…:14; features.py:668) | 0 USD |
| character_state_lock | `default_on` 15/10, chưa gen thật (features.py:687) | 0 USD |
| ref_rule_early | `default_on` 15/10, chưa gửi thật bản đệm (features.py:693) | 0 USD |
| motion_consistency_lint | `default_on` 15/10, chưa chạy thật (RA_QUYET_DINH…:14; features.py:681) | 0 USD |
| group_keep_approved | `default_on` 15/10, chưa chạy thật (RA_QUYET_DINH…:14; features.py:675) | 0 USD |
| auto_voice_cast | Bật thử 05/10, "nghe ổn mới đổi verified" (TODO.md:502–504); diag `auto_voice_missing` #27; biến thể cao độ chưa nghe (features.py:547) | 0 USD |
| short_lock_outfit | Bật 12/10 cho #27 (TODO.md:150); why: chưa thử thật (features.py:34); không có kết quả đo | 0 USD |
| package_overrides | why: chưa thử thật, chưa nối Dashboard (features.py:24); TODO.md:112 "chờ người dùng" | 0 USD |
| layout_drift_review | why: lõi kiểm bằng ảnh giả, chưa nối runner (features.py:29) | 0 USD |
| seedance_sample_mode | Bản mẫu 480p chạy KLD (TODO.md:407); bản cuối 1080p chưa chạy thật (TODO.md:464) | công cụ trả tiền khi người bấm |
| lip_sync | Đo lệch môi #24 (TODO.md:175–176); why: chưa thử giọng Việt (features.py:375). Là cờ `dialogue_take` 🔒 cần (xem lưu ý REQUIRES) | ảnh hưởng lựa chọn gen |
| audio_first | Bật qua dashboard.env từ 29/09 (TODO_LICH_SU.md:115); why: mới thử bằng test (features.py:244); không có kết quả đo | 0 USD |
| story_check | Bật qua env từ 29/09; why: chưa biết bắt đúng chỗ người xem khó hiểu (features.py:230) | lượt Claude trong Biên kịch (người bấm) |
| profile_digest | Bật qua env (TODO_LICH_SU.md:287); why: chưa đo model giữ đúng nhân vật với bản ngắn (features.py:279) | 0 USD |
| j_cut | Bật qua env; why: chưa nghe thử trên giọng Việt (features.py:173; TODO.md:422) | 0 USD |
| motion_trim | Bật qua env; thử #7 shot 3 hợp lý nhưng "chưa đo được" (TODO.md:524, 530); rủi ro mất clip ghi ở TODO_LICH_SU.md:206 | 0 USD |
| shot_transitions | Bật qua env; chưa có chỗ áp dụng / chưa đo (TODO.md:524, 530; features.py:223) | 0 USD |
| seedance_ref_groups | Bật qua env; mới thử 1 cảnh bằng công cụ riêng (features.py:290); làm bỏ qua khung cuối + 3 cờ học việc mất tác dụng (TODO_LICH_SU.md:72; dashboard/design/screens/trainee_ui.py NO_EFFECT_WITH) | đổi cách gen |

## Nhóm 3 — KHÔNG nên khóa (22)

| cờ | lý do + nguồn | tốn tiền? |
|---|---|---|
| auto_send_self_fix | OPT_IN_ONLY (vòng nền tự gửi job trả tiền) | có |
| bg_autoqc | OPT_IN_ONLY; diag `bg_autoqc_stuck` 16 (#24/#27) | có (Claude QC) |
| qc_observe_enum | OPT_IN_ONLY | có |
| shot_popup | OPT_IN_ONLY (hậu kỳ tùy chọn) | có |
| ambient_motion | `costs` (before_run.costly_fix_flag) | có |
| change_review | `costs`; diag `change_review_hold` 35 / `_fail` 5 ở #27 | có |
| change_review_frames | `costs` | có |
| director_rewrite | `costs`; why: chưa chạy thật Claude (features.py:469); diag `director_rewrite_fallback` 13 ở #27 | có |
| end_state_fresh | `costs` (dịch lại qua sổ chi) | có |
| p24_lessons | `costs` | có |
| qc_framing_cap | `costs` (PAID_FLAGS) | có |
| stage_camera | `costs` | có |
| two_tier_quality | `costs`; bản cuối chưa chạy thật, nhãn ghi lệch quyết định 13/10 (RA_QUYET_DINH…:16) | có |
| chat_prompts | Mỗi lần gửi thêm MỘT lượt Claude (features.py:76) nhưng **không khai `costs`** — nên khai; diag `chat_prompt_refused` 4, `_fail` 1 (#29/#30) | có (chưa khai) |
| voice_check_redo | Tự gen lại TTS; why: "cờ sai thì trả tiền TTS vô ích" (features.py:137) | có |
| camera_setups | 🎓 học việc | — |
| continuous_takes | 🎓 học việc | — |
| end_frames | 🎓 học việc | — |
| scene_establishing | 🎓 học việc | — |
| scene_qc | 🎓 học việc | — |
| storyboard_auto_trust | 🎓 học việc | — |
| qc_team | 🎓 học việc; người dùng 14/10 TẮT tới khi đo ≥ 75 % (RA_QUYET_DINH…:26 — dashboard.env còn `FEATURE_QC_TEAM=1`, file 🧪 ghi false) | — |
