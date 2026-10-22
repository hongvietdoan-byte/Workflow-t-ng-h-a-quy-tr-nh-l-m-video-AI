# Câu hỏi cần người dùng chốt — tổng hợp toàn kế hoạch (21/10/2026 tối)

> Một chỗ cho MỌI câu đang chờ Executive Producer chốt trong V3.1 (M0–M6) + cờ + bàn đạo diễn 3D. Mỗi câu có: bối cảnh 1–2 dòng,
> phương án, **khuyến nghị**, tài liệu gốc. Trả lời ngắn theo mã, ví dụ: `K1 duyệt · K2 duyệt · F-A duyệt · S-A A · M6-Q3 B 40 % …`.
> Phiên chính ghi câu trả lời vào sổ quyết định (`data/decisions.json`, quy ước 8) rồi mới làm. Không câu nào được tự làm khi chưa trả lời.

**Cấp quyền** (sổ `v31-permission-tiers-2026-10-20`): Cấp 2 = duyệt phạm vi code; Cấp 3 = đổi trạng thái production (bật/khóa/tắt cờ,
migration, API trả phí, xóa asset). Tiến độ hiện tại: 61 việc / 54 % (M0 100 %, M1 2 việc dở, M2 chờ golden, M3 ✅, M4 81 %, M5 45 %, M6 mới).

---

## A. Ưu tiên 1 — chặn tiền / ghi đè / mở khóa M2

| Mã | Câu hỏi | Phương án | Khuyến nghị | Cấp | Tài liệu |
|---|---|---|---|---|---|
| **G1** | Định nghĩa COMPAT của golden: dựng lại với **trạng thái cờ sản xuất hiện có**, chỉ **cờ mới V3.1 bắt buộc TẮT**, phải ra đúng byte gói đã gửi (thay vì "mọi cờ chưa kiểm chứng TẮT" — máy chính đang bật 83 cờ loại này nên 0 ca nào đạt). | (a) định nghĩa mới · (b) giữ cũ | **(a)** — đúng ý D08 "cờ mới TẮT = byte giống"; codex đang chạy nghiệm thu lần 3 theo (a) | Cấp 1 (tiêu chí nghiệm thu) | `docs/RA_CX21_GOLDEN_CODEX_2026-10-21.md`, `docs/CLOUD_TASKS.md` #### C-GOLDEN2 |
| **F-A** | Gói A sửa cờ (làm trước dự án #34): (1) `change_review` đóng cổng khi rà lỗi (hiện lỗi Claude → job tự gửi, G35); (2) `hero_takes` khai `costs` (gen thêm mà tính 0 USD); (3) `director_rewrite` thêm cờ con `director_rewrite_respect_lock` mặc định BẬT — Đạo diễn chỉ ĐỀ XUẤT cho trường người đã sửa; (4) **TẮT `scene_qc_claude`** (báo nhầm 12/21); (5) `chat_prompts` kiểm gói có D6 + lỗi hết tiền. | duyệt cả gói / duyệt từng mục | **duyệt cả gói** | code Cấp 2 + đổi trạng thái Cấp 3 | `docs/KE_HOACH_SUA_20_CO_2026-10-21.md` mục 1, 5 |
| **C-M25B** | Người sửa TAY motion prompt → trường khóa USER_LOCKED (chỉ khi cờ `field_guard` bật, chế độ shadow chỉ ghi chẩn đoán). Phiên chính đã chốt tạm theo M0.10. | giữ / đổi | **giữ** | Cấp 2 (đã code, cờ TẮT) | `docs/CLOUD_TASKS.md` #### C-M25B |

## B. Cờ — khóa / tắt / cơ chế chống tắt nhầm

Bằng chứng đủ 3 phần: `docs/BANG_CHUNG_CHOT_CO_2026-10-21.md` (phân quyền D01–D10 · dependency graph + test matrix · rủi ro `state()`).
Đánh giá 144 cờ: `docs/DANH_GIA_HIEU_QUA_CO_2026-10-21.md`.

| Mã | Câu hỏi | Phương án | Khuyến nghị | Cấp |
|---|---|---|---|---|
| **K1** | Khóa bật NGAY 2 cờ an toàn: `send_claim` (0 test đỏ khi ép bật, 0 lỗi #27→#33), `back_view_guard` (0 đỏ; chỉ tác dụng khi `seedance_ref_groups` bật). | duyệt / chưa | **duyệt** | Cấp 3 |
| **K2** | Khóa 4 cờ sau khi cloud-C sửa xong test (C-FLAGTEST8): `plate_view_sentence`, `video_pregen`, `chat_first`, `framing_guard`, `stage_camera` (+ `two_tier_quality`, `video_gate` sau Gói B). | duyệt trước, khóa khi test xanh / hỏi lại sau | **duyệt trước** — phiên chính khóa khi cả bộ test xanh, báo lại | Cấp 3 |
| **K3 (B4)** | `seedance_ref_groups` (tuyến video thật, hiện chỉ bật nhờ dashboard.env): khóa thì `end_frames` mất tác dụng với shot đủ điều kiện (`end_frames.py:32`). | (a) khóa, chấp nhận bỏ khung cuối ở tuyến ref · (b) sửa cho 2 cờ cùng chạy rồi khóa · (c) chưa khóa | **(b)** | quyết định sản phẩm + Cấp 2 |
| **K4** | Cơ chế baseline cờ (một tệp trạng thái cờ sản xuất trong git để mọi máy/worktree/cloud dùng chung + báo đỏ khi cờ từng bật nay tắt + tự đề nghị khóa sau 2 dự án sạch). Thứ tự an toàn đã mô phỏng: REMOVED → khóa → 🧪 → preset → env → **baseline có bảo vệ** → mặc định (0 cờ đổi máy chính, 0 cờ tốn tiền bị bật, 0 đổi bộ test). | (a) thứ tự E · (b) E + chỉ áp khi máy chưa có tệp cài đặt (F) · (c) chưa làm | **(b)** an toàn tuyệt đối cho máy chính | Cấp 2 |
| **K5** | Làm baseline (K4) trước hay song song Gói B? (khóa mà máy khác vẫn đọc mặc định code thì "khóa" không tới máy đó) | trước / song song | **song song** (độc lập file) | — |
| **K6** | Nút "↺ Bỏ mọi lựa chọn riêng" (xóa 86 lựa chọn một bấm, không hỏi, không sao lưu) → thêm xác nhận + sao lưu. | duyệt / không | **duyệt** | Cấp 2 nhỏ |
| **K7** | 5 cờ V3.1 không làm đỏ test nào khi bật (`stale_code_alarm`, `diag_merge`, `budget_notice_d01`, `send_estimate`, `refusal_skip_same_picture`) + cờ đã chờ từ trước (`qc_false_alarm_fix` + `horizon_needs_sky`). Bật trên máy chính để kiểm thật? `refusal_skip_same_picture` ĐỔI thứ tự người dùng chốt 27/09 → cần câu riêng. | bật tất (trừ refusal) / từng cờ / chưa | **bật 4 cờ chỉ-ghi/chỉ-hiện** (`stale_code_alarm`, `diag_merge`, `budget_notice_d01`, `send_estimate`); `qc_false_alarm_fix` + `horizon_needs_sky` bật sau C-FIX-THAP-4 phát lại #31/#33; `refusal_skip_same_picture` **chưa** | Cấp 3 |

## C. Gói sửa cờ B và C

| Mã | Câu hỏi | Khuyến nghị | Tài liệu |
|---|---|---|---|
| **F-B** | Gói B "sửa báo nhầm / nhãn / giá rồi KHÓA": `video_gate`, `two_tier_quality`, `motion_consistency_lint`, `end_frames`, `scene_qc`, `lip_sync` + `dialogue_take`, `bg_autoqc`… | duyệt code (Cấp 2); khóa từng cờ sau bằng chứng (Cấp 3) | `KE_HOACH_SUA_20_CO` mục 2 |
| **F-C** | Gói C "cờ bật mà vô tác dụng: nối hay bỏ" (`audio_first`, `story_check`, `voice_check_redo`, `stage_auto`, `stage_handheld_props`, `stage_crew_user_approve`, `continuity_layout`, `travel_truth`) — theo khuyến nghị từng dòng của bảng mục 3 | duyệt theo khuyến nghị từng dòng | `KE_HOACH_SUA_20_CO` mục 3 |
| **F-Q2** | `audio_first`: nối vào đường Dashboard thường (giọng trước, cắt hình theo giọng) hay bỏ? | theo bảng mục 3 | mục 5 câu 2 |
| **F-Q3** | `lip_sync`: duyệt 1 shot cận thật (≈ giá 1 clip Seedance 2.5 720p; số chính xác `pregen_check` in khi xin) để khóa cùng `dialogue_take`? | duyệt khi có dự án #34 | mục 5 câu 3 (Cấp 3 tiền) |
| **F-Q4** | `two_tier_quality`: khóa sau #34 nếu giá ước tính khớp sổ chi ± 5 %? | duyệt | mục 5 câu 4 |

## D. Bàn đạo diễn 3D trên Dashboard (M4.8)

Màn XEM (chỉ đọc) đã code xong (C-STAGE-VIEW, chờ phiên chính kiểm trên #31). Phần THAO TÁC: `docs/KE_HOACH_BAN_DAO_DIEN_3D_DASHBOARD_2026-10-21.md` mục 12.

| Mã | Câu hỏi | Khuyến nghị |
|---|---|---|
| **S-A** | Phương án: A nút trong màn XEM theo đợt · B trang riêng wizard · C chỉ nút Duyệt + Trả lại | **A** |
| **S-B** | Ai bấm Duyệt sân khấu: chỉ người dùng (phiên Claude bị ẩn nút) · hoặc phiên Claude khi người dùng nói duyệt trong chat (cần xác minh) | **chỉ người dùng** (giữ quyết định 16/10) |
| **S-C** | Cảnh đang chờ duyệt sân khấu thì nút Gen ảnh: cảnh báo VÀNG · chặn tới khi duyệt | **VÀNG** (không chặn cứng) |
| **S-D** | Bấm chia vai lại cho cảnh đã có ảnh: hỏi xác nhận riêng · cấm trên Dashboard | **hỏi xác nhận** |
| **S-E** | Đợt 3 (nút gọi Claude API): chỉ mở sau khi đo chi phí chia vai thật trên #31; trần mặc định = `usd_max` của cảnh | **đồng ý** |
| **S-F** | Previs trên Dashboard (Đợt 2) có cần không? (V2V 16/10 chưa theo được đường máy vòng) | **bỏ N12 tạm thời** |
| **S-G** | Chọn lần đo máy: tự chọn từng shot ("lấy m1 shot 10") · chỉ trả lại bằng câu ý đồ để Quay phim chọn | **chỉ câu ý đồ** (đỡ thao tác) |

## E. M6 — Tổ làm phim có chủ

`docs/KE_HOACH_TO_LAM_PHIM_CO_CHU_2026-10-21.md` (mục 4d, mục thứ tự ưu tiên).

| Mã | Câu hỏi | Phương án | Khuyến nghị | Cấp |
|---|---|---|---|---|
| **M6-Q3** | Ngân sách TỰ SỬA (tiền các vai tự gen lại không hỏi EP / dự án). Số thật: làm lại theo trần mới = 37 % lượt đầu (#27), 29 % (#31). | A số USD cố định · **B % tiền lượt đầu** · C không đặt (chỉ trần lượt/shot) | **B, mặc định 40 %**, EP đổi theo dự án; chốt an toàn: một vai hỏng liên tiếp ≥ 3 shot cùng mã lỗi → dừng tự sửa, phiếu lên | quyết định |
| **M6-A** | Duyệt phạm vi code Gói M6-A (M6.1 Role Registry chỉ đọc + M6.3 Generation Authorization SHADOW + M6.9 Continuity Validator SHADOW; 0 USD, cờ TẮT) — trình sau khi chốt M6-Q3 | duyệt / chờ | **duyệt** (giao cloud-C/E ngay) | Cấp 2 |
| **M6-B** | Gói M6-B (M6.2, M6.4, M6.5, M6.6) — trình khi golden đạt + M2 gộp | — | duyệt sau | Cấp 2 |

## F. Cấp 3 còn treo trong V3.1 (nhắc lại — không cần trả lời ngay)

| Mã | Việc | Trạng thái | Khi nào hỏi |
|---|---|---|---|
| C3-3 | Xóa asset Kho chủ thể | CHỈ DRY-RUN; mỗi lần xóa trình danh sách riêng | khi Kho gần đầy |
| C3-4 | Bảng CSDL `overrides` (M4.7) | duyệt có ĐK | khi M4.7 phần ghi sẵn sàng |
| C3-5 | Backfill Kho forms v2 (M2.3) | khảo sát + nháp | sau M2.3 gộp |
| C3-6 | Write guard ENFORCE (M2.5) | để sau | sau ≥ 1 dự án shadow |
| C3-7 | Bật cờ production M2 | để sau | sau golden + gộp M2, trình từng cờ |
| C3-8 | Gen chứng minh world map trả phí | để sau | sau map offline duyệt |
| C3-9 | QC tự BLOCK luật kỹ thuật | để sau | sau benchmark M4.6 |
| C3-10 | Repair router tự gen lại | để sau | sau pilot |
| C3-11 / M5.4 | Pilot vòng B 5–8 shot (#31) | nguyên tắc duyệt, CHƯA chi | trình `pregen_check` + trần trước khi chạy |
| C3-12 / M5.5 | Pilot vòng C 20–40 shot | để sau | sau pilot B đạt |
| sổ | Thêm trường `approval` (định hướng / thử nghiệm / quy trình / triển khai) cho `data/decisions.json` | đề xuất | khi tiện (kế hoạch V3.1 mục 4b) |

---

## Mẫu trả lời nhanh (theo khuyến nghị)

`G1 a · F-A duyệt · C-M25B giữ · K1 duyệt · K2 duyệt · K3 b · K4 b · K5 song song · K6 duyệt · K7 theo khuyến nghị · F-B duyệt · F-C theo khuyến nghị ·
S-A A · S-B người dùng · S-C VÀNG · S-D hỏi · S-E đồng ý · S-F bỏ N12 · S-G câu ý đồ · M6-Q3 B 40 % · M6-A duyệt`

Có thể trả lời "duyệt theo khuyến nghị, trừ …".
