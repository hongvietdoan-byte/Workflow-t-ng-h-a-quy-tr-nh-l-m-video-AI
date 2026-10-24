# Bàn giao CX23-M47B — Codex 3

- Nhánh: `codex/v31-m47b`; worktree: `D:\AI-Video-Pipeline\.codex-wt\v31-m47b`.
- M80C và M48-D2 đã gộp main ngày 24/10. Merge snapshot `c558befa` vào nhánh M47B đã được chốt/push ở `3b7f4395`; nhánh hiện chậm hơn `origin/main` 35 commit. Không có thay đổi sau `c558befa` trong các file lõi M47B; Codex 1 cần rebase/merge main mới trước khi nối UI.
- Nền C3-4 + Q6(c) ở commit `24ba86fd`. Diff lõi hiện cập nhật Q6(c): BYĐ v2, tên có dấu/không dấu an toàn, ứng viên tên trong cast/thoại/hành động, cảnh báo thiếu ảnh mốc/Kho, ref Kho theo ID hoặc quy tắc match duy nhất của pipeline. Cờ `qc_overrides` vẫn OFF.
- Kiểm tra mục tiêu: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_v31_m47b_overrides.py tests/test_video_gate.py tests/test_shot_intent.py` → **83 passed in 6.43s**. Reviewer độc lập chốt **không có finding chặn**; heuristic tên prose chỉ phát hiện tên đứng trước động từ thuộc whitelist, còn cast/speaker/trường cấu trúc là đường chính.
- Bộ nhanh toàn repo (`-m "not slow"`) đạt **8277 passed, 12 failed, 8 skipped, 22 xfailed, 176 subtests passed**; lỗi thuộc các nhóm devsys page, feature settings, browser mockup D11 và golden replay, ngoài diff M47B. Gửi `tin` để Codex 1 nối UI; task M47B vẫn mở đến khi UI hoàn tất và phiên chính nghiệm thu.
- Giữ cờ OFF; chỉ dùng fixture, không đọc/ghi dữ liệu thật, không chạy migration trên `data/manifest.sqlite`, không gọi API/dịch vụ trả phí.
- Báo cáo tiến độ: `docs/RA_CX23_M47B_CODEX_2026-10-23.md`.

---
# HANDOFF — CX23-M48-D2 (23/10, nhánh `codex/v31-m48-d2`)

- Trạng thái: hoàn tất code N12/N14/N15/N16; 223 test liên quan xanh; đang chuẩn bị commit/push nhánh và báo `xong` qua hộp thư.
- N12 tách runner previs dùng SQLite chỉ đọc, giữ sản phẩm cũ, từ chối shot được chọn mà lượt hiện tại chưa đo; progress UI hiển thị shot thực tế và đường dẫn clay/depth/plan.
- N14 chỉ nhận lần đo thuộc lịch sử đúng shot; N15 ẩn/chặn khi `world_map` tắt; N16 chỉ ghi họ sân khấu theo đủ gợi ý VÀNG qua đường ghi Kho hiện có, không tự gộp.
- Bằng chứng: bộ hồi quy mục tiêu 223 passed; `py -m core.decisions check` khớp; `py tools/related_areas.py` liệt kê plates3d, step2, devsys và caller autopilot/step4/core_infra; `git diff --check` sạch.
- Cờ `stage_desk_ui` giữ TẮT/OPT_IN_ONLY. Chưa chạy Blender thật, chưa kiểm thử Dashboard live, không gọi API trả phí hoặc dùng dữ liệu thật.
- Rà độc lập phát hiện hai điểm P2 về chọn shot và hiển thị đầu ra; đã sửa và thêm test đỏ→xanh.
- Việc kế sau khi báo M48 xong: kiểm tra lại hộp thư; nhận CX23-M82 nếu vẫn là việc kế được giao. Không nhận trước khi M48 hoàn tất.

---

# HANDOFF — M8.0b phần còn M8.0 An toàn tiền (nhánh worktree-agent-a76909ef8d083efe1, 23/10)

- ĐÃ XONG (0 USD, sau cờ safe_paid_buttons; cờ TẮT = nhãn/hành vi như cũ):
  1. ~35 nút chỉ-giá → P.paid_button (giá + 1 xác nhận); _PRICE_ONLY bỏ; test quét đỏ khi nút tốn tiền mới thiếu xác nhận.
  2. "Duyệt hết" ảnh/storyboard/motion/clip: dashboard/approve_preview.py — xem trước danh sách + HOLD (lineage cũ) + giá bước kế,
     rồi hẹn 30 s hoàn tác (paid_confirm.schedule/undo_bar); tới hạn chạy lại kiểm tập chờ/OK trước khi duyệt.
  3. pilot_release hẹn 30 s; tới hạn kiểm lại pilot (bật, chưa mở, cùng cảnh, đã xong) rồi mới release.
  4. Khóa paid_ask_* treo: begin_run (đếm lượt app.py) + mark_drawn; xóa khóa không vẽ ở lượt trước.
- Test: tests/test_m80b_money_rest.py (mới), test_safe_paid_buttons, test_price_label_scan, test_ui_video/test_ui_storyboard test_m80b_*;
  test cũ bấm nút đã đổi → pin_off("safe_paid_buttons"). tools/ui_v2_acceptance.py: phép đếm click đo với cờ TẮT (xác nhận là cố ý).
- DỞ / RỦI RO: bộ quét PAID_CALLS chưa có p.retry/p.reject/regen.regenerate_video/p.restart_job/p.reopen_approved/voice.*/music.submit_drafts
  (~23 nút từng thẻ: dd_, r_, dretry_, reopen_, vregen_, tts_gen_, mdraft_, reject_all…) — chưa đổi; chat_first: duyệt hết 1-click
  nay thành xem trước khi cờ bật; chưa kiểm tay trên Dashboard thật.
- BƯỚC KẾ: rà + gộp main (phiên chính), khởi động lại Dashboard 8501, kiểm tay; mở rộng PAID_CALLS cho nhóm nút trên (M8.0c).

# HANDOFF — C-M48-DESK-UI (nhánh claude/v31-m48-desk-ui, 22/10)

- XONG code + test; chưa gộp main, chưa ghi hộp thư/TODO (phiên chính làm). Báo cáo: docs/RA_CLOUD_M48_DESK_UI_2026-10-22.md.
- File: dashboard/stage_desk_ui.py (mới), dashboard/stage_view_ui.py (gọi render_scene), core/features.py (cờ stage_desk_ui TẮT),
  tests/golden/package_inputs.json, devsys/areas.json, tests/test_v31_m48_desk_ui.py (19 test).
- Kiểm lại: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_v31_m48_desk_ui.py tests/test_v31_stage_view.py tests/test_v31_m48_desk_core.py`
- Việc mở: bấm thử thật trên #31 (máy chính); cân nhắc đưa stage_desk_ui vào OPT_IN_ONLY.

---

# HANDOFF — golden replay Windows (22/10, tạm dừng theo lệnh người dùng, hạn mức tuần 91 %)

Nhánh `claude/golden-replay-windows` (từ origin/main 85189242). Commit công cụ: c21dac7b. CHƯA gộp main, CHƯA có báo cáo docs/.

## Đã xong
- Rà 79cfb019: hướng ĐÚNG gốc (Windows 3.12+ os.path.exists/isfile/isdir là hàm C của nt, không qua os.stat đã bọc → hỏi tồn tại
  'data/…' TƯƠNG ĐỐI nhìn vào scratch = False, không vào manifest). **GOLDEN7 máy chính (10:30–11:13) chạy TRƯỚC bản vá (11:40)** →
  117/0/0/41 được đo trong tình trạng đó, cần đo lại. Đã thay bằng `_stat_path_probes()` vô điều kiện (một đường code mọi OS).
- Sửa thêm trong `tools/golden_db_replay.py`: hỏi tồn tại lần 2 không rơi sang băm sha; ghi/mkdir vào thư mục chỉ có ở ref-root
  (`_scratch_parents`, `wrapped_mkdir`, chặn junction ra ngoài); --ab: `mark()` dựng lại ảnh bằng code cây đang so thay cache lịch sử ở
  ref-root (trước che DIFF); `refuse(kind)` loại thao tác cụ thể; `_failure_answer`/`worker_answer` luôn kèm positions + loaded.
- 10 BOTH_FAIL 'operation' (#27 790/839/879, #31 1027/1049–1051/1054–1056, đều video_gen): gốc = ảnh chưa có dòng
  `seedance_subject_pictures` → code thật sẽ TẢI LÊN Kho chủ thể ClipAI (vd #31 'XE NÔI' asset 442/2.png, #27 khung shot) — hành vi
  thật giống nhau ở A và B, công cụ cấm nên mất ca. Xử lý: chỉ ở --ab giả asset tất định `golden-ab-<sha16>` + `simulated_uploads`
  (compare_ab so cả trường này; run_ab đếm `simulated_upload_cases`); capture/replay thường vẫn cấm. Thử tay 4 ca → BUILT.
- Test đỏ→xanh (tests/test_golden_replay_windows.py, 7 test, kiểm bằng đột biến): relative_existence_probes, write_into_a_folder…,
  subject_upload_simulated…, forbidden_operation_names…, makedirs_new_folder…, ab_rebuilds_marked_pictures…, simulated_uploads_that_differ.
  test_golden_db_replay::test_missing_dependency_appearing nhận thêm dạng {stat: None}. Test golden: 180 passed / 1 skip (symlink).
  Cả bộ -m "not slow" (trước 3 sửa cuối từ rà agent): 7885 passed, 0 failed. Rà agent (quy ước 7) đã làm; các điểm chính đã sửa.

## Dở
- Golden A/B lại (A=a117497d, B=9746a6ea ở D:/golden8/a|b; snapshot+flags cũ golden-snapshot-7mc; ref-root D:/AI-Video-Pipeline) đang
  chạy nền lúc dừng: lượt chính → `D:/AI-Video-Output/golden-snapshot-8mc/ab_main.json` (+ exit_main.json); lượt phụ
  pause_before_submit + poll_claim BẬT (cờ đặt được trong tiến trình qua file cờ) → `ab_flags_on.json`. Script:
  `run_ab8.py` (scratchpad phiên; nội dung = flags_on bỏ 2 cờ khỏi experimental + True). Số chưa có khi viết tệp này.

## Bước kế
1. Đọc ab_main.json / ab_flags_on.json: total, simulated_upload_cases, DIFF/ONE_FAIL (first_diff), BOTH_FAIL theo reason/diagnostic.kind.
2. Chạy lại cả bộ một lần (3 sửa cuối: mark --ab, wrapped_mkdir, so simulated_uploads) — test golden đã xanh.
3. Viết docs/RA_GOLDEN_REPLAY_WINDOWS_2026-10-22.md, commit, fetch+merge origin/main, push main (chỉ tools/tests/docs → không cần khởi động lại Dashboard).
4. Việc mở: listdir/scandir sau khi ghi chỉ thấy scratch (che ref-root, hai bên như nhau); golden_capture.py:261-271 nhánh except chưa
   dùng _failure_answer; refuse() nay làm ca core nuốt ngoại lệ thành INSUFFICIENT (trước BUILT) — ghi trong báo cáo.
5. Dọn worktree D:/golden8/a, D:/golden8/b sau khi xong.

## Kết quả golden lại (xong 22/10, công cụ c21dac7b, mã thoát 0 cả hai, ~2 650 s mỗi lượt)
| Lượt | SAME | DIFF | ONE_FAIL | BOTH_FAIL | Kho chủ thể giả | ĐẠT |
|---|---:|---:|---:|---:|---:|---|
| Chính (cấu hình cũ, pause_before_submit + poll_claim TẮT) | 127 | 0 | 0 | 31 | 21 ca | có |
| Phụ (pause_before_submit + poll_claim BẬT) | 127 | 0 | 0 | 31 | 21 ca | có |
So GOLDEN7 117/0/0/41: 10 ca 'operation' nay đều SAME (#27 +3, #31 +7 → #31 78/78). 31 BOTH_FAIL còn lại đều 'prepare giữ (_hold)'
(như cũ). Theo dự án: #24 15/0/0/9, #27 28/0/0/16, #31 78/0/0/0, #33 6/0/0/6. Tệp: D:/AI-Video-Output/golden-snapshot-8mc/ab_main.json, ab_flags_on.json.

---

# Bàn giao — CX24-G4-QUYET-DINH

- Làn: Codex 3; nhánh `codex/v31-quyet-dinh-check`.
- Nhánh đã nhập `origin/main` tới `d76d3588` (M82 pha A, M53-MAY, G1-PLAN-GATES và các cập nhật mới); merge commit nhánh G4 `c33aaf53` đã push.
- Đã nối Q-F với `tests/test_safe_paid_buttons.py`, M6 policy B với ca E4 (gồm clip nhóm tính giới hạn riêng từng shot), QD3 với `check_qd3_auto_spend_limit`. Sau khi M82 pha A gộp `core.simple_budget`, đã bỏ `pending` cũ khỏi `data/decisions.json`.
- Bằng chứng mới nhất: `py -m core.decisions check` → **Khớp**; `py -m pytest -q -p no:cacheprovider tests/test_decisions.py` → **43 passed / 25.18s**.
- Báo cáo ứng viên: `docs/RA_CX24_G4_QUYET_DINH_CODEX_2026-10-24.md`; còn 52 quyết định chưa nối, có đề xuất check; không sửa nội dung quyết định cũ.
- Chỉ dùng fixture tạm; không gọi API trả phí, không ghi dữ liệu dự án thật. G4 hoàn tất trên nhánh, chờ phiên chính rà/gộp; việc kế là CX24-G3-SO-LOI. M47B vẫn chờ Codex 1 nối UI.
