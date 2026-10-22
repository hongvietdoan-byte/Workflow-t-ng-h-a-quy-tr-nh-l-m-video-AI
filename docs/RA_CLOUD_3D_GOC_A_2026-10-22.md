# C-3D-GOC-A — Khâu 3D sửa theo GỐC (cloud-C, 22/10) — bước 0 + R2 + R3 + R4

Năm gốc của 23 lỗi 3D / vị trí / máy (sổ `devsys/errors.json`, mục gốc `V31-GOC1`…`V31-GOC5`; các dòng dưới là `source_document` của chúng — KHÔNG chèn dòng phía trên):
- GỐC R1 — vị trí không có MỘT nguồn sự thật xuyên shot (G46, G1, G41, G43, G44, G45, G47, G50). Owner artist_3d. Gói C-3D-GOC-B (cloud-D).
- GỐC R2 — hình học máy ↔ người ↔ sàn bằng hằng số / chữ thay vì đo (G2, G3, G49, P33-A10, P33-B5). Owner cinematographer.
- GỐC R3 — chữ viết tự do không khớp cái máy thấy (G26, G11, G9, P33-B3, P33-B7, P33-B10). Owner video_prompt_artist (+ storyboard_artist).
- GỐC R4 — BYĐ mâu thuẫn trường khác / thiếu BYĐ (G18, P33-A12). Owner director.
- GỐC R5 — Kho: vật một dạng, tỉ lệ mô hình, nền ghép (G8, P33-B4) — chờ CX21-M23. Owner artist_3d.

## 1. Bước 0 — sổ lỗi (commit 077d4bf1)
5 mục gốc `V31-GOC1…5` (category `root_cause`, `source_document` = dòng 4–8 trên). 23 lỗi: `owner` theo `data/crew_roles.json` + `root_cause_id`
(nhóm R1 giữ `P31-G46` làm gốc trung gian — `P31-G46` → `V31-GOC1`). `python -m devsys.errors check` hợp lệ (91 mục); test sổ lỗi xanh.

## 2. Thiết kế — MỘT bộ kiểm cho MỌI shot (`core/camera_invariants.py`)
Thuần Python, 0 USD, không gọi model, không ghi dữ liệu, KHÔNG đổi gói gửi (kết quả = phát hiện VÀNG có số + câu thay). Không cờ mới.
Một nguồn ngưỡng: dải nghiêng lấy `stage_grid.RULE_TH` (L7, L3) + `whitebox` (M3.2) — không hằng mới.

| Bất biến | Hàm | Đo bằng |
|---|---|---|
| R2-PITCH: độ nghiêng ∈ dải của angle khai (eye cúi ≤ 12° / ngửa ≤ 5°; slightly_high cúi 8–12°; high cúi 20–45°; overhead ≥ 45°; low ngửa 8–45°) | `check_pitch` | look_at − location |
| R2-FRAMING: đoạn thân của cỡ cảnh chiếm `FRAMING.fill` khung ±15 % THEO HÌNH CHIẾU | `check_framing`, `body_share` | chiếu đỉnh đầu + đường cắt cỡ cảnh |
| R2-FLOOR: sàn dưới máy ≥ 0,3 m; chân trên sàn đo được (±0,15 m); không có mép sàn ≥ 5 cm lọt khung giữa máy và chân | `check_floor` | `floor_at(x, y)` = tia xuống sàn (Blender / giả) |
| R2-PCT: câu "N% of the frame height" ↔ hình chiếu (±10 điểm); câu thay sinh từ hình chiếu | `check_frame_pct`, `pct_sentence` | `body_share` |
| R3-NOT-IN-FRAME / SIDE / TOP-CUT / RELATIVE: chữ nhắc mốc ↔ mốc trong khung? bên nào? đỉnh bị cắt? đặt vật bằng chữ so với mốc | `view_of`, `text_vs_view` | chiếu đáy / giữa / đỉnh mốc (`stage.json` marks `*_chan/*_dinh`, khối của máy) |
| R3-MOTION-REVEAL / UNSEEN: motion khớp KHUNG ĐẦU | `motion_vs_view` | tầm nhìn máy lúc mở clip |
| R3-VI-TEXT: chữ có dấu trong prompt tiếng Anh → câu thay (glossary / bỏ dấu) | `vi_leaks` | chữ |
| R3-REF-LEAK: chủ thể video mẫu ngoài câu chặn → "like the reference video" | `ref_leaks` | chữ |
| R4-SIZE / ANGLE / MOVE / CAST: BYĐ.may / thanh_phan ↔ size / angle / camera_move / characters | `byd_vs_fields` | trường shot |
| R4-NO-BYD: MỘT dòng cho cả dự án thiếu BYĐ | `byd_coverage` | — |

Sửa GỐC trong máy nền (sau cờ có sẵn `whitebox_height_dummy`, TẮT = như cũ từng byte):
- `plate_camera.camera_for` có mức `slightly_high` (cúi `whitebox.SLIGHTLY_HIGH_DEG` = 10°) — A10 "không có góc hơi cao".
- Máy `high` / `slightly_high` cũ giữ khoảng cách NGANG rồi nâng máy → người nhỏ hơn cỡ cảnh 20–30 % (đo: MS cao 61 % khung thay vì 82 %).
  Cờ BẬT: cùng độ nghiêng, máy + điểm nhắm giải theo HÌNH CHIẾU (`_slant_for_fill`, chia đôi lồng nhau): đỉnh đầu ở `HEADROOM` cỡ cảnh,
  đoạn thân cỡ cảnh chiếm đúng `fill`; xiên < `MIN_DIST_M` → ống dài hơn (như F2); `why["slant"]` ghi số cũ → mới. EWS high giữ sàn
  "đầu + 2,5 m" (luật 12/10); ECU high không giải được → ghi `fixes`, giữ máy cũ (bộ kiểm báo). Cờ vào `OPT_IN_ONLY` (preset Thử nghiệm không tự bật).
- `prompt_formula._LEGS`: "its whole / full body" (tả đồ vật / con vật) không còn là tư thế cả người — G9 (#31 shot 17 bị chặn đỏ).

Đường dùng: `tools/camera_invariants.py --project N [--stage …/stage.json] [--ref-word cats] [--json]` (CSDL mở `mode=ro`; mã thoát 1 = có
phát hiện VÀNG, 2 = không đọc được). `shot_report(...)` gộp mọi bất biến cho một shot (cho Sân khấu 3D gọi khi đã có chỗ đứng + chiều cao + tia sàn).

## 3. Test (`tests/test_v31_3d_goc_a.py`, 65 test)
- Biến thể sinh bằng code, seed 1–5 × 120–200 ca: 5 bối cảnh giả lập (mê cung #31 có ô cỏ 0,13 m + tháp 42 m + biệt thự; tháp #33 có 5 bậc
  thềm 0,3 m; phòng kín 4 × 5 m (ngoài tường không sàn); ngoài trời; sàn bậc 0,3 m/1,5 m) × chỗ đứng, hướng, cỡ cảnh (8), góc (5), ống
  (mặc định / 18 / 28 / 50 / 85 mm), chiều cao 1,1–2,0 m, bên trái/giữa/phải. Oracle tầm nhìn = `plate_camera.project` (phép chiếu thứ
  hai, độc lập với `stage_grid.project` mà module dùng).
- Replay 0 USD bằng số trong tài liệu lỗi (#31 shot 28 / 35 / 13 / S31 / shot 2 / 17; #33 high 30°, góc thềm, mắt xoáy, tên có dấu, "cats",
  22 shot thiếu BYĐ): cái cũ bị bắt, máy sinh bởi `camera_for` (cờ BẬT) qua.

## 4. Bảng lỗi → gốc → bất biến → test biến thể → trạng thái
| Lỗi | Gốc | Bất biến | Test biến thể / replay | Trạng thái đề xuất |
|---|---|---|---|---|
| P31-G2 người sai tỉ lệ nền | R2 | R2-FRAMING + R2-PCT | `test_variants_camera_for_meets_r2_or_says_why`, `test_variants_old_high_camera_is_caught`, `test_frame_pct_sentence_follows_projection` | FIXED_UNVERIFIED (máy high giữ % khung khi cờ BẬT; câu % chưa SINH tự động trong prompt — chỉ phát hiện + câu thay) |
| P31-G3 eye mà ngước/chúi | R2 | R2-PITCH | `test_variants_camera_for_meets_r2_or_says_why`, `test_replay_p31_g3_eye_camera_tilted` | FIXED_UNVERIFIED (phát hiện ở mọi máy; Sân khấu 3D chưa tự giải lại theo dải) |
| P31-G49 bậc cỏ dưới chân / máy sát | R2 | R2-FLOOR + R2-FRAMING | `test_variants_floor_step_between_camera_and_feet`, `test_variants_feet_and_camera_on_the_measured_floor`, `test_replay_p31_g49_shot13_camera_over_grass_too_close` | FIXED_UNVERIFIED (cần tia sàn Blender thật cho `floor_at`) |
| P33-A10 high 30° cố định | R2 | R2-PITCH + slightly_high | `test_flag_off_slightly_high_is_the_old_eye_camera`, `test_replay_p33_a10_high_is_not_one_fixed_tilt` | FIXED_UNVERIFIED (sau cờ whitebox_height_dummy) |
| P33-B5 đỉnh tháp bị cắt | R2/R3 | R3-TOP-CUT | `test_replay_p33_b5_tower_top_cut_and_b3_placed_by_words` | FIXED_UNVERIFIED (phát hiện) |
| P31-G26 chữ "tháp" mà máy quay chỗ khác | R3 | R3-NOT-IN-FRAME / SIDE | `test_variants_landmark_sentence_follows_what_the_camera_sees`, `test_variants_side_words_follow_the_projection`, `test_replay_p31_g26_tower_behind_the_camera` | FIXED_UNVERIFIED (phát hiện + câu thay; chưa tự thay trong prompt) |
| P31-G11 motion khác khung đầu | R3 | R3-MOTION-REVEAL / UNSEEN | `test_replay_p31_g11_motion_reveals_what_the_first_frame_shows` | IN_PROGRESS (chỉ phần mốc / vật có toạ độ; "tường cong ↔ thẳng" cần đọc ảnh) |
| P31-G9 "its whole body" chặn nhầm | R3 | `_LEGS` không khớp "its …" | `test_replay_p31_g9_its_whole_body_is_not_a_pose` | FIXED_UNVERIFIED |
| P33-B3 đặt vật bằng chữ so với mốc | R3 | R3-RELATIVE | `test_replay_p33_b5_tower_top_cut_and_b3_placed_by_words` | FIXED_UNVERIFIED (phát hiện) |
| P33-B7 chữ Việt trong motion | R3 | R3-VI-TEXT | `test_replay_p33_b7_vietnamese_names_get_a_replacement` | FIXED_UNVERIFIED (câu thay; cổng cũ vẫn chặn khi gửi) |
| P33-B10 "cats" ngoài câu chặn | R3 | R3-REF-LEAK | `test_replay_p33_b10_reference_subject_outside_the_guard` | FIXED_UNVERIFIED |
| P31-G18 BYĐ ↔ camera_move | R4 | R4-MOVE / SIZE / ANGLE / CAST | `test_replay_p31_g18_byd_still_but_camera_pans`, `test_byd_vs_each_field` | FIXED_UNVERIFIED (phát hiện; Đạo diễn chọn bên đúng) |
| P33-A12 thiếu BYĐ 22 dòng | R4 | R4-NO-BYD (một dòng) | `test_replay_p33_a12_one_line_for_a_project_without_byd` | IN_PROGRESS (gốc thật = Đạo diễn BYĐ chạy qua claude_cli, ngoài gói này) |
| R1 (G46, G1, G41, G43–G45, G47, G50) | R1 | — | — | C-3D-GOC-B (cloud-D) |
| R5 (G8, P33-B4) | R5 | — | — | chờ CX21-M23 |

Trạng thái trong sổ lỗi chưa đổi ở commit này (FIXED chỉ khi phiên chính gộp + replay xanh trên máy chính); đề xuất ở cột cuối.

## 5. Nghiệm thu máy chính (Blender thật, 0 USD)
```
git fetch origin cloud/v31-3d-goc-a && git checkout cloud/v31-3d-goc-a
PYTHONUTF8=1 py -m pytest -q tests/test_v31_3d_goc_a.py tests/test_plate_camera_p24_angles.py tests/test_v31_m32_height_dummy.py
PYTHONUTF8=1 py tools/camera_invariants.py --project 31 --stage <data>/projects/31/stage/<cảnh>/k1_o/stage.json --json out31.json
PYTHONUTF8=1 py tools/camera_invariants.py --project 33 --ref-word cats --json out33.json
# cờ whitebox_height_dummy BẬT trong thư mục thử (không phải data thật): render lại nền 1 shot high + 1 shot slightly_high của #33
#   (tools/render_plates.py như pregen) và so % khung nhân vật trên plate.png với FRAMING (MS ≈ 82 %).
```

## 6. Rà quy ước 7 (agent, chỉ đọc) — đã sửa
- CAO: cờ BẬT, máy high cắt đầu CU/ECU, đẩy đầu MS/MLS vào thanh app → giải cả điểm nhắm theo HEADROOM; test `test_variants_high_keeps_headroom_and_distance_floor`.
- EWS high bị kéo dưới sàn "đầu + 2,5 m" → loại EWS khỏi giải xiên. Khoảng cách xiên < MIN_DIST_M → ống dài hơn + `fixes`. `why["distance"]` số cũ → thêm `why["slant"]`.
- Preset Thử nghiệm tự bật cờ (giờ đổi nền gửi model) → `whitebox_height_dummy` vào `OPT_IN_ONLY`; `why` của cờ cập nhật.
- Báo sai R3-SIDE ("her right hand", "phải" = must, "con trai") → chỉ cụm vị trí trong khung; R3-TOP/RELATIVE/REVEAL xét ±60 ký tự quanh mốc,
  "on top of" không phải đỉnh, "appears determined" không phải lộ ra. R4-ANGLE bỏ qua `do_cao` mặc định "ngang" khi Đạo diễn chưa khai máy;
  R4-CAST khóa sân khấu thường ("kelly", "gieng") không đối được → KHÔNG RÕ (trước: bỏ im). `vi_leaks` không gộp qua dấu phẩy / mạo từ,
  glossary khớp nguyên cụm. Mục gốc V31-GOC* có `stage` (+ category `may` / `byd`) để Role Registry định tuyến đúng owner (test crew registry).
- Không lỗi: cờ TẮT y nguyên (cache nền băm dict máy → máy đổi thì nền tự render lại); Blender không gọi `camera_for`; `_LEGS` chỉ dùng ở lint ảnh.

## 7. Còn mở (cần phiên chính quyết)
- `slightly_high` chưa thuộc `shots.ANGLES` / `camera_plan.ANGLES` / prompt DP → luồng thật chưa khai được (chỉ đường code / test). Thêm enum =
  đổi validate + prompt DP (khâu step1) — chưa làm ở gói này.
- `docs/BANG_CHUNG_CHOT_CO_2026-10-21.md` (dòng 120, 165, 345) còn ghi cờ "không nằm trên đường sản xuất" — nay có (nền 3D khi bật).
- `check_floor` chỉ lấy mẫu đường thẳng máy → chân (gờ lệch ngang trong khung bị sót); `frame_h_m` vẫn số khoảng cách cũ (ảnh toàn hơi rộng).
- Câu thay R2-PCT / R3 chưa tự nối vào prompt (chỉ phát hiện + câu thay) — muốn tự thay cần cờ (khóa catalog tới CX21-GOLDEN7).
- Giàn GAME_TPS khai high/overhead: máy vẫn cúi 12° (bộ kiểm báo) — chọn: đổi máy hay cấm khai.
