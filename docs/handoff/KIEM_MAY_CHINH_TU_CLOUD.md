# Việc phiên CLOUD đã rà / gộp — máy chính KIỂM LẠI trực tiếp (người dùng 22/10)

Phiên cloud `cloud-claude` (claude.ai/code session_0199VQqnF6CAfLBQHaMV8TDF) điều phối TẠM thay phiên chính từ 22/10 00:50 (phiên chính đứt
Remote Control). Cloud KHÔNG có `data/`, Blender, khóa API, Windows → mọi "đã kiểm" dưới đây là **test Linux + Agent rà đọc diff**, chưa chạy
thật. File này cập nhật mỗi lượt điều phối; máy chính đánh dấu cột "Máy chính" khi kiểm xong (✅ đạt / ❌ lỗi + ghi chú).

## Bước chung mỗi lần mở máy chính (làm TRƯỚC các mục dưới)
1. `cd D:\AI-Video-Pipeline` → `git pull` → khởi động lại 8501 (đổi `core/`, `dashboard/`) và 8502 (đổi `devsys/`).
2. Cả bộ test Windows: `py -m pytest -q -n 8 -p no:cacheprovider -rf` — so với số hỏng ghi ở mục đợt gộp (Linux có vài ca hỏng sẵn do môi trường).
3. `/status` trong phiên chính: thấy env `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (mục P3) — chưa thấy thì khởi động lại phiên một lần.
4. Đọc `PYTHONUTF8=1 py tools/hop_thu.py bang`; muốn nhận lại điều phối → ghi tin "NHẬN LẠI ĐIỀU PHỐI" `--to cloud-claude` TRƯỚC khi gộp/giao.

## ⭐ VIỆC ĐẦU TIÊN CỦA MÁY CHÍNH — nghiệm thu golden A/B (CX21-GOLDEN7, đường găng mở khóa gộp toàn bộ M2)
Codex hết hạn mức tuần (92 %) → bàn giao Claude máy chính chạy MỘT lượt (hộp thư giao `--to phien-chinh`, ưu tiên 0):
1. Đọc `git show origin/codex/v31-golden7:docs/RA_CX21_GOLDEN7_CODEX_2026-10-22.md` + thư chốt 03:31 (commit db0ccfac, `hop_thu bang`).
2. Worktree công cụ `cloud/v31-golden5` @ 621661a8; A = main @ a117497d (pin, ghi SHA), B = `cloud/v31-m2-tichhop` @ 9746a6ea.
3. Native negative control trước (`tests/test_golden5.py::test_real_worker_two_code_trees_same_and_one_line_changed`) — ĐỎ thì dừng.
4. Snapshot CSDL MỚI `mode=ro`; baseline = cờ production thật, catalog hợp A∪B 159, 32 experimental TẮT explicit (gồm `director_rewrite_respect_lock`,
   `stage_view_ui`, `crew_registry`, `continuity_validator`, `gen_auth_shadow`) — theo sổ `v31-ep-golden-ab-acceptance-2026-10-21`.
5. `main_ab --ab` 158 ca #24/#27/#31/#33 + loaded paths. ĐẠT = negative control xanh + 0 DIFF + 0 ONE_FAIL + mỗi dự án ≥ 1 SAME. 0 USD.
6. ĐẠT → `hop_thu.py xong CX21-GOLDEN7 …` → điều phối gộp một lần `cloud/v31-m2-tichhop` + m24 + golden5 (+ m73, m210, golden4). CHƯA ĐẠT → báo cáo, giao sửa cloud-C.

## A. Đợt gộp 22/10 sáng (nhánh tích hợp `tich-hop-2210` → main)

| Mã | Nhánh @ commit | Cloud đã kiểm | Máy chính kiểm | Máy chính |
|---|---|---|---|---|
| C-M81B | cloud/v31-m81b @ fabeeafb | tài liệu M8.1 mục 8c + PDF; gộp sạch | mở `docs/pdf/M8_1_Che_do_Don_gian.pdf` trên điện thoại, đọc mục 8c | |
| CX21-GOLDEN6 / GOLDEN4 | codex/v31-golden6, codex/v31-golden4 | chỉ báo cáo; GOLDEN6 CHƯA ĐẠT (validator catalog) → giao C-GOLDEN7 + CX21-GOLDEN7 | không cần — chờ CX21-GOLDEN7 | |
| C-STAGE-VIEW | cloud/v31-stage-view @ 9617f2b8 | gỡ xung đột `tests/golden/package_inputs.json` (merge_union); cả bộ test; Agent rà | bật `stage_view_ui` ở 🧪 trên BẢN SAO / dự án thử → mở màn Xem sân khấu 3D #31: mỗi cảnh một khung, không nút ghi/dựng, báo thiếu nền rõ lệnh; tắt lại | |
| C-M61-M69 | cloud/v31-m61-m69 @ e74ba672 | gỡ xung đột areas.json + package_inputs.json; cả bộ test; Agent rà | cờ `crew_registry` + `continuity_validator` TẮT: không tạo tệp mới trong `data/projects/<id>/crew/`; (tùy) bật thử trên dự án thử → chỉ ghi jsonl shadow, không đổi CSDL | |
| C-M71 (Gói A sửa cờ) | cloud/v31-m71 @ 1691d07d | gỡ xung đột `core/before_run.py` (giữ `_drift_items` của main + `_cost_items(conn, pid)` của M71); cả bộ test; **Agent rà kỹ (tiền)** | (1) Bước "trước khi chạy": danh sách cờ tốn tiền có 6 cờ mới `costs` (không bị bật hàng loạt 0 USD); (2) `py tools/pregen_check.py --payload --project <id>` in dòng "D6:" mỗi shot; (3) Bước 4 🧭 hero_takes báo giá khớp ô 💰 | |

**Kết quả cả bộ test Linux đợt này:** 7089 qua, 32 hỏng → so cùng các tệp trên main sạch: 31 hỏng Y HỆT main (test_golden_db_replay ×13, test_golden_replay ×8, test_s1446_retired_lessons ×2 … — môi trường Linux), 1 hỏng MỚI `test_pending_flags_expire_when_the_branch_lands` → đã sửa (gỡ `pending_flags` của ô `sb.stage3d` trong devsys/pipeline_maps.json vì C-STAGE-VIEW đã gộp), devsys 285 qua. **Máy chính:** cả bộ Windows — golden_db_replay / golden_replay có hỏng không (nếu Windows XANH thì đúng là lỗi môi trường Linux).

**Agent rà kỹ:** 0 CAO · 1 VỪA (khóa hết tiền D6 `QUOTA_KEY` dùng chung mọi dự án) · 3 THẤP (2 chỗ kẹt mục ĐỎ change_review khi sự kiện skipped / LIMIT 5; baseline cờ hero_takes/scene_qc_claude giờ costs → máy MỚI hạ OFF) → giao **C-M71-FIX** cloud-E (kèm sửa rò tệp test DP12 ghi `data/ref_padded/` thật). Gỡ xung đột before_run.py: Agent xác nhận đúng.

## A2. Lượt 22/10 01:21 — C-M63-FIX (cloud-C) @ cloud/v31-m63-fix 7a68a597

| Mã | Cloud đã kiểm | Máy chính kiểm | Máy chính |
|---|---|---|---|
| C-M63-FIX (gen_auth.shadow_send ở 6 đường gửi thẳng: khung cuối, phép thử chất lượng, khớp môi, ảnh toàn cảnh, bộ ảnh nhân vật, experiments; đếm lượt clip nhóm; autoqc xóa mã dừng khi lượt mới) | gộp sạch; cả bộ Linux 7099 qua, 31 hỏng = y hệt main; **Agent rà kỹ: 0 CAO**, 1 VỪA (attempts() quét toàn bảng jobs khi cờ BẬT — chậm) + 4 THẤP → giao **C-M63-FIX2** cloud-D | cờ `gen_auth_shadow` TẮT (mặc định): gửi khung cuối / khớp môi / phép thử chất lượng một lần trên dự án thử bằng provider giả → KHÔNG có tệp `data/projects/<id>/crew/gen_auth_shadow.jsonl` mới, job đi như cũ; (tùy) bật cờ trên bản sao → mỗi lần gửi thêm đúng 1 dòng jsonl, không chặn | |

## A3. Lượt 22/10 04:37 — C-M71-FIX (cloud/v31-m71-fix e887f4de) + C-M63-FIX2 (cloud/v31-m63-fix2 26ba0395), cloud-C

| Mã | Cloud đã kiểm | Máy chính kiểm | Máy chính |
|---|---|---|---|
| C-M71-FIX — D6 tạm ngừng theo NGUỒN Claude của job (`chat_prompt_quota:<anthropic/claude_cli/…>`), mục ĐỎ rà lỗi tự đóng khi sự kiện skipped, lọc dự án có Claude trước LIMIT 5, test không ghi `data/` thật (conftest), **gỡ 72 tệp `data/ref_padded/1_*_pad.png` khỏi git + .gitignore** | cả bộ Linux 7116 qua / 31 hỏng = y hệt main; chạy test KHÔNG còn sinh tệp rác `data/ref_padded`; **Agent rà kỹ: 0 CAO, 0 VỪA**, 3 THẤP → C-FIX3-THAP cloud-C. 72 tệp gỡ = rác test (tên `1_<hash>`), `pad_to_rule` tự sinh lại khi thiếu | sau `git pull`: 72 tệp `data/ref_padded/1_*_pad.png` biến mất — bình thường (bộ đệm tự sinh lại); gửi một clip Seedance có ảnh ref cần đệm (dự án thử, provider giả) → tệp `_pad.png` được tạo lại; cả bộ test Windows không để lại tệp mới trong `data/ref_padded/` | |
| C-M63-FIX2 — gen_auth đọc job dự án MỘT lần (hết quét toàn bảng trong SPEND_LOCK), job làm lại → bên làm lại, `_busy` thấy clip nhóm, end_frames chỉ hỏi model khi cờ bật, quality_samples lỗi shadow không kẹt 'sending' | như trên; Agent rà kỹ: đúng gốc, không hồi quy cờ TẮT | không cần riêng (shadow, cờ `gen_auth_shadow` TẮT) | |

**Chờ golden đạt, CHƯA gộp:** cloud/v31-m2-tichhop (M21, M25, M25B, M26, M29, DP9, DP10, GOLDEN2), cloud/v31-m24, cloud/v31-golden5, cloud/v31-m73,
cloud/v31-m210, cloud/v31-golden4 (ba nhánh sau dựng trên nền tích hợp M2).

## B. PR của phiên cloud đã gộp main trước đó (14/10 → 21/10) — CHƯA kiểm thật

| PR | Nội dung | Máy chính kiểm | Máy chính |
|---|---|---|---|
| #18 | `music_story_arc` BẬT mặc định; `delivery.fit_music_to_film` (một bài ngắn hơn phim kéo dài vừa khít, giữ đoạn kết gốc; quá ngắn → lặp + VÀNG `music_fill`) | dựng Bước 5 một dự án có 1 bài nhạc ngắn hơn phim: nghe đoạn nối không giật, kết bài trùng hết phim; manifest có `music_fill` | |
| #19 | `anchor_by_spot` neo shot RỘNG nhất tại chỗ khác neo cả cảnh; G0 một sơ đồ mỗi chỗ đứng (`<cảnh>@<chỗ>`); `tools/scene_layout_audit.py` | `py tools/scene_layout_audit.py --project <tập 2>` → bảng 🔴/🟡/🟢; bật `anchor_by_spot` → gen ảnh nháp các shot cùng chỗ: diag có ảnh neo `previous_scene` của shot rộng nhất tại chỗ, không còn `storyboard_anchor_skipped` VÀNG | |
| #20 | Phiên chính 70 % context: tự nén cùng phiên (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70`), hook SessionStart `startup|clear|compact`; skill mục 4 cấm `clear_session` | lần nén đầu: Remote Control còn nối, hook in "PHIÊN NÀY VỪA TỰ NÉN CONTEXT", phiên tự làm tiếp theo gói | |

## C. Việc cloud-claude đã GIAO (theo dõi trên `hop_thu bang`)

| Mã | Làn | Đề | Ghi chú |
|---|---|---|---|
| C-GOLDEN7 | cloud-C (ưu tiên 0) | docs/CLOUD_TASKS.md#### C-GOLDEN7 | validator `--ab` theo catalog cây đang dựng; lỗi cấu hình = mã 2 |
| CX21-GOLDEN7 | codex (C-GOLDEN7 XONG 621661a8 trên cloud/v31-golden5; 02:59 bỏ điều kiện GỘP — chạy thẳng trên nhánh, quota codex còn ~10 %) | docs/CODEX_TASKS.md### CX21-GOLDEN7 | chạy lại A/B; ĐẠT → gộp tích hợp M2 một lần |
| C-FIX3-THAP | cloud-C (ưu tiên 3, việc nhỏ) | docs/CLOUD_TASKS.md#### C-FIX3-THAP | 3 lỗi THẤP sau rà M71-FIX/M63-FIX2 |
| C-M63-FIX2 | cloud-C (ưu tiên 2; chuyển từ cloud-D im > 1 giờ, 02:58) — ĐÃ GỘP 04:4x | docs/CLOUD_TASKS.md#### C-M63-FIX2 | lỗi rà kỹ C-M63-FIX |
| C-M71-FIX | cloud-C (ưu tiên 1; chuyển từ cloud-E im > 1 giờ, 02:58) | docs/CLOUD_TASKS.md#### C-M71-FIX | lỗi rà kỹ M71 + rò tệp test DP12 |
| C-M83-TOOL | cloud-E (ưu tiên 2) | docs/CLOUD_TASKS.md#### C-M83-TOOL | công cụ đo tải 10 người (Playwright + provider giả); lượt đo thật M8.3 = máy chính |

## D. Ghi chú lượt 22/10 02:58
- C-GOLDEN7 (cloud-C) XONG @ cloud/v31-golden5 621661a8 — CHƯA gộp (công cụ golden gộp cùng tích hợp M2 khi CX21-GOLDEN7 ĐẠT). Máy chính: không cần làm gì
  tới khi codex báo kết quả; ĐẠT → phiên điều phối gộp cloud/v31-m2-tichhop + m24 + golden5 (+ m73, m210, golden4 dựng trên nền đó) một lần.
- cloud-E và cloud-D không nhận việc > 1 giờ (lịch tự vận hành có thể đã dừng) → đã báo người dùng mở lại làn. C-M83-TOOL vẫn để cloud-E.
- 22/10 03:31 — codex HỎI CX21-GOLDEN7 (BLOCKED: catalog live máy chính 146 cờ, main mới có `director_rewrite_respect_lock`, `stage_view_ui`, `crew_registry`,
  `continuity_validator` sau đợt gộp c66d6c2d). cloud-claude TRẢ LỜI theo sổ `v31-ep-golden-ab-acceptance-2026-10-21` + `v31-ep-g1-golden-compat-production-baseline-2026-10-21`:
  cờ mới V3.1 = experimental TẮT, catalog hợp A∪B 159, experimental 32. **Máy chính:** sau `git pull` các cờ này có trong 🧪 ở trạng thái TẮT — đúng, không bật.
- 22/10 05:2x — C-FIX3-THAP (cloud/v31-fix3-thap d2c14404) **KHÔNG gộp**: Agent rà kỹ bắt lỗi VỪA — tắt cờ `change_review_motion` có thể đóng mục ĐỎ và
  thả job tốn tiền có thay đổi SCENE chưa ai rà (scene + motion cùng lỗi, sau đó sửa scene đạt). Trả cloud-C sửa trên cùng nhánh (C-FIX3-THAP-B, ưu tiên 1).
  **Máy chính:** không có gì đổi trên main từ việc này; KHÔNG tắt `change_review_motion` trên máy chính tới khi C-FIX3-THAP-B gộp.
- 22/10 06:5x — C-FIX3-THAP + C-FIX3-THAP-B (cloud/v31-fix3-thap): Agent rà kỹ lại: lỗi VỪA (thả job có thay đổi scene chưa rà khi tắt cờ motion) ĐÃ HẾT, 0 CAO/VỪA mới.
  1 THẤP về tiền: "✓ Đã sửa" trên mục rà LỖI âm thầm gọi Claude rà lại không báo giá → giao **C-FIX4** cloud-C (ưu tiên 1). **Máy chính:** tới khi C-FIX4 gộp, trên
  mục ĐỎ loại "rà lỗi" dùng nút "Rà lại" (có giá) hoặc "Bỏ qua", KHÔNG bấm "✓ Đã sửa". Sau pull: mở Tổ rà soát một dự án có mục rà lỗi motion, tắt `change_review_motion`
  ở 🧪 trên bản sao → mục motion đóng, mục scene cũ hơn (nếu có) vẫn giữ.
