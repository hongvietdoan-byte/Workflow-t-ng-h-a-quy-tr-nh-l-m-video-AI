# Kiểm lại 22 tính năng "chưa kiểm thật" trên Khủng Long Đỏ (#22) — 08/10/2026

Chỉ đọc, 0 USD: dùng bản sao `data/manifest.sqlite` (chụp 08/10), `data/projects/22/*`, `dashboard.env`, `data/feature_settings.json`, mã `core/*`, tài liệu `docs/kld_runs/*`, `docs/BAN_GIAO_2026-10-07_KHUNG_LONG_DO_PHIEN_CLAUDE.md`, `docs/DU_AN_KHUNG_LONG_DO_2026-10-06.md`, `docs/RA_KLD_*`. Không sửa `core/features.py`, không ghi `verified`; mọi "đề xuất verified" cần người dùng duyệt.

## 0. Cách đọc và giới hạn

- **Cấu hình ổn định suốt #22**: `dashboard.env` sửa lần cuối 01/10 (trước dự án), `data/feature_settings.json` bật `ui_v2`, `auto_voice_cast`, `idea_to_script`, `place_render_refs` từ trước 07/10 16:09 (bản sao `feature_settings.before_kld_ab_20261007_160920.json`), thêm `seedance_sample_mode` lúc 16:10 ngày 07/10. Chạy `core.features.on()` với env nạp từ `dashboard.env` → đúng 22 cờ bật và chưa verified (`on_unverified()` trả 22).
- **#22 là dự án chạy tay** (`projects.autopilot_state/gates/log = NULL`, không có `story_check.json`, không có dấu `voice_redo_done`/`.lipsync_nokey`): mọi pha nằm trong `core/autopilot.py` không chạy. `shot_mode = per_shot`, 9 shot / 2 cảnh kịch bản, `storyboard_mode = 1`, ảnh `gpt-image-2.5-sunburst`, `test_quality = 1` (Thử rẻ).
- **Không có A/B từng cờ**: 22 cờ bật cùng lúc, lượt 1→2→3 đổi nhiều thứ cùng lúc (model ảnh, prompt, nền 3D). "Giúp" ở đây = cờ đã chạy thật + kết quả được người dùng nhận; KHÔNG chứng minh nhân quả. "Gây hại/nhiễu" chỉ khi có số đo ngược chiều.
- Số liệu chung #22 (DB): ảnh 9 duyệt / 29 loại / 11 hủy; video 9 duyệt / 25 loại / 11 hủy; `diag_events` project 22 theo stage/code liệt kê ở từng cờ.

## 1. Bảng tổng 22 dòng

Ký hiệu cột kết luận: **V** = ứng viên `verified` (cần người dùng duyệt) · **M** = đóng một phần, chưa đủ · **G** = giữ thử · **T** = tắt / bỏ khỏi cấu hình đang dùng · **?** = không có dấu vết, thiếu bằng chứng.

| # | Cờ | Bật hiệu lực trên #22? | Dấu vết chạy trên #22 | Kết quả | KL |
|---|---|---|---|---|---|
| 1 | audio_first | Bật nhưng chỉ nằm trong autopilot (`autopilot._voice_first_phase`) — #22 không chạy autopilot | Không có (`autopilot_gates` NULL, không có khóa timeline) | Không có dấu vết | ? |
| 2 | auto_voice_cast | Có (cờ ghi đè màn 🧪 + Director) | diag `director/auto_voice_cast` ×2 (06/10 15:10, 15:22): "MAXIM, KELLY"; giọng 72 (nam) / 70 (nữ) trong `audio_assets/assets.json` | Giúp phần gắn giọng; nhánh biến thể cao độ chưa chạy (chỉ 2 vai khác giới) | M |
| 3 | camera_setups | Bật, nhưng gộp shot bị `seedance_ref_groups` thay (known_issues) | Director gán `camera_setup` A,B,C,C,D,D,A,A,A; mọi `video_route=single`, 0 job có `group_leader/sent_group` | Chỉ thêm nhãn, không gộp clip nào | T |
| 4 | continuous_takes | Chặn: `_stretch()` trả None khi `_refs_group()` đúng (mọi shot đi chỉ-ảnh-tham-chiếu) | Không có | Vô hiệu trong cấu hình này | T |
| 5 | end_frames | Chặn: `end_frames.needed()` = False khi `seedance_ref_groups` bật + shot eligible; pha vẽ khung cuối chỉ ở autopilot | Bảng `end_frames` 0 dòng cho #22 dù 4 shot có `end_state` | Vô hiệu (đúng thiết kế, tiết kiệm ảnh) | T |
| 6 | film_crew | Có | Director 6 lượt Claude; `director_raw` có `tradeoffs` (nét riêng của bộ mới); diag `dp_calls` (Tầng B), `director_review` "2 cảnh đạt ý đồ" | Chạy thật, đầu ra dùng được; không tách được phần công của bộ luật | V |
| 7 | j_cut | Bật nhưng nhánh bị bỏ qua: cả 2 câu thoại (shot 3, 5) là shot khớp môi → `voice.py` đi nhánh `synced` | `assets.json`: câu 1 đặt 5,50 s, câu 2 đặt 12,04 s = đúng mốc khớp môi (khởi điểm + 1,0 s), không dịch 0,25 s | Không có tác dụng trên #22 | ? |
| 8 | lip_sync | Có (+ `dialogue_take` đã verified) | `lipsync/index.json`: shot 250, 252 `method=generate`, giọng 1,0 s; diag `lipsync_not_applied` ×1 (job 506 bị gửi Kling, đã đổi) | Đo khớp môi kém: job 539 tương quan 0,03; job 541 tương quan 0,44 (< 0,65) | G |
| 9 | motion_trim | Có (chặn shot thoại / nối liền) | `videos/NN_raw.mp4` + `NN.mp4`: shot 1,2,4,6 (4,04 → 2,5/2,0/2,5/3,0 s), 7,8,9 (12,04 → 11,5 s) bị cắt đuôi; đo mốc đầu cắt = 0,0 s ở cả 7 clip | Chỉ thực hiện cắt đuôi, chưa lần nào dời đầu | ? |
| 10 | place_render_refs | Có (cờ ghi đè màn 🧪, người dùng đồng ý 06/10) | 9/9 ảnh duyệt có ref `place_render`; diag `place_match` ×26 (17 info, 9 warn); video có Image render (đường Codex `c8f7a69`) | Giúp: nền đúng render 3D (độ khớp 0,35–0,51 ở ảnh duyệt), video nhảy đúng nền 11,5 s | V |
| 11 | profile_digest | Có (nhưng không dùng cho MAXIM KL / KELLY KL vì có ảnh OUTFIT) | `profile.digest` (hash b34b…, 21bb…) trong hồ sơ KELLY/MAXIM; không có diag riêng | Không tách được tác dụng | ? |
| 12 | qc_team | Có | 37 khung được chấm (`qc_scene/team.json`), 41 lượt Claude (`usage_events` stage `qc_team`: 68,4k input, 43,6k output, 104k cache đọc) | Nhiễu: chặn 6/9 khung người dùng duyệt (sai hồ sơ KL), chỉ khớp người 27/37 (73 %) ≈ mức "luôn chặn" (76 %) | T |
| 13 | scene_establishing | Có | 3 ảnh toàn cảnh (stage `establishing`: 2 Seedream, 1 GPT); `establish/index.json` | Ảnh AI toàn cảnh không có mặt trong khung duyệt nào; cảnh trong nhà từng kéo shot ra ngoài trời | T |
| 14 | scene_qc | Có (lớp 0 bằng code; lớp 1 Claude riêng `scene_qc_claude` chưa bật) | `qc_scene/layer0.json` 46 khung; 7 lần tự vẽ lại do `shot_size` (job 485, 486–488, 492, 500, 501, 534) | Cả 9 khung duyệt đều bị cờ sai/lạc hậu; 0 bản tự vẽ lại được duyệt | T |
| 15 | seedance_ref_groups | Có | Mọi clip duyệt đi chỉ-ảnh-tham-chiếu từng shot (prompt "Image N is the storyboard frame…"); 0 nhóm 2–4 shot (`sent_group` NULL) | Chế độ từng shot chạy được, không bị bộ lọc từ chối; nhóm gộp chưa chạy | M |
| 16 | seedance_sample_mode | Có (cờ ghi đè, 07/10 16:10) | `usage_events` stage `quality_sample`: A 720p 4 s (0,92 USD) + B mẫu 480p 4 s (0,41 USD), cảnh 253 | Hộp thử riêng, không đổi phim; B bản cuối 1080p chưa gửi | G |
| 17 | seedance_subjects | Có | diag `video/subjects` ×26 (đều `info`, 0 lần lùi về ảnh đánh dấu); 8/9 clip duyệt qua Kho chủ thể; 33 ảnh `active` | Giúp: không cần dấu đỏ, 0 từ chối | V |
| 18 | shot_transitions | Có | Manifest bản giao #34: 4 cạnh `edge_3..6` (chớp trắng giữa shot 3→4, 5→6) | Người dùng xem, nhận bản; mới chỉ dùng `flash` | M |
| 19 | story_check | Bật nhưng chỉ ở autopilot (`_story_check_phase`) + hiển thị kết quả | Không có `story_check.json`, không có diag `story_check*` | Không có dấu vết | ? |
| 20 | storyboard_api | Có | 7/9 ảnh duyệt có ref `storyboard` + `frame 1 (scene anchor)`; cảnh 1 (6 shot) và cảnh 2 (3 shot nhảy) | Dùng thật, giữ liền mạch; lỗi "khoảnh khắc MỚI" đã sửa bằng mã | V |
| 21 | storyboard_auto_trust | Bật nhưng chỉ ở autopilot; và `look_trust` = chưa tin | `effectiveness.look_trust(FF_INGAME, gpt-image-2.5-sunburst)`: 122 cặp, khớp người 69,7 %, trusted=False | Không có dấu vết, không thể kích hoạt | T |
| 22 | voice_check_redo | Bật nhưng chỉ ở autopilot (`_voice_check_phase`) | Không có diag `voice_check`, không có `voice_redo_done`; TTS `resends: 0` | Không có dấu vết | ? |

Tổng hợp: **V = 4** (film_crew, place_render_refs, seedance_subjects, storyboard_api) · **M = 3** (auto_voice_cast, seedance_ref_groups, shot_transitions) · **G = 2** (lip_sync, seedance_sample_mode) · **T = 7** (camera_setups, continuous_takes, end_frames, qc_team, scene_establishing, scene_qc, storyboard_auto_trust) · **? = 6** (audio_first, j_cut, motion_trim, profile_digest, story_check, voice_check_redo). Cộng: 4 + 3 + 2 + 7 + 6 = 22.

## 2. Chi tiết từng cờ

### 2.1 audio_first — `?`
- **Hiệu lực**: `FEATURE_AUDIO_FIRST=1`; chỗ gọi duy nhất `core/autopilot.py:1346` (`_voice_first_phase`), chạy khi dự án chạy tự động. #22 chạy tay → không chạy.
- **Dấu vết**: `projects.autopilot_gates` NULL; không có khóa `timeline_locked`. Giọng TTS 2 câu tạo tay (asset 31132, 31133), shot thoại kéo thành 4,04 s bởi `voice`/dựng chứ không phải khâu audio-first.
- **Kết quả**: không có dấu vết. `why` ("chưa chạy trên dự án thật") **chưa đóng**.
- **Còn thiếu**: một dự án chạy tự động (autopilot) có ≥ 1 câu thoại, đối chiếu tổng giây khóa vs bản dựng.

### 2.2 auto_voice_cast — `M`
- **Hiệu lực**: bật bằng màn 🧪 (`feature_settings.json`). `core/voice_casting.py`, Director ghi `voice_traits` cùng lượt.
- **Dấu vết**: diag `director/auto_voice_cast` 06/10 15:10 và 15:22 "Tự gắn giọng (0 USD, data/voices_vi.json): MAXIM, KELLY". `assets.json`: MAXIM → voice 72 ("voice boy ingame VN"), KELLY → voice 70 ("⭐ Voice Kelly VN · nữ"), 2/2 câu `succeeded`, `resends: 0`.
- **Kết quả**: gắn đúng giới, 0 USD; người dùng không chê giọng ở bản 2/3 (bản 2 ghi "thoại tự nhiên"). Nhánh "quá 2 vai cùng giới → biến thể cao độ ±2–3 nửa cung (ffmpeg)" **không chạy** (chỉ 2 vai khác giới).
- **Đề xuất**: nửa đầu của `why` ("chưa chạy Director thật với khối voice_traits") đã đóng; nửa sau (nghe thử biến thể cao độ trên 4 giọng VN) chưa. Chỉ nên `verified` nếu người dùng đồng ý tách/bỏ nhánh pitch, hoặc sau 1 dự án ≥ 3 vai cùng giới. Giữ thử.

### 2.3 camera_setups — `T`
- **Hiệu lực**: bật (`prompts.py:190` cho Director; `shots.setups_on` cần per_shot). `core/known_issues.py:85` ghi rõ: "bị nhóm Seedance thay khi cờ seedance_ref_groups bật".
- **Dấu vết**: `scenes.data.camera_setup` = A, B, C, C, D, D (cảnh 1), A, A, A (cảnh 2) → Director có viết nhãn; shot 3–4 cùng C, 5–6 cùng D nhưng vẫn gen 6 clip riêng (`video_route=single`, 0 `group_leader/sent_group`). Nhãn còn được `plate_camera` dùng để chia sẻ hướng máy nền 3D.
- **Kết quả**: vô hại nhưng không tiết kiệm clip nào; hiệu ứng thật chỉ là nhãn.
- **Đề xuất**: tắt trong cấu hình đang chạy (thừa) — **kiểm trước** `plate_camera.py:147` / `director_report.py` vì chúng đọc `camera_setup` (nhãn vẫn có thể cần). Điều kiện `why` ("thử thêm ở cảnh thoại dày") không được #22 đóng.

### 2.4 continuous_takes — `T`
- **Hiệu lực**: `runner._stretch` (core/runner.py:1003) trả None nếu `_refs_group(group)`; mọi shot #22 `eligible` → luôn None. Ngoài ra cần `camera_setups` gộp được.
- **Dấu vết**: không có. **Kết quả**: vô hiệu. Điều kiện `why` (model có diễn trọn 8–15 s đúng thứ tự không) **chưa đóng**.
- **Đề xuất**: chỉ thử được ở dự án không dùng `seedance_ref_groups`; tắt ở cấu hình hiện tại.

### 2.5 end_frames — `T`
- **Hiệu lực**: `end_frames.needed()` False khi `features.on("seedance_ref_groups") and seedance_refs.eligible(data)` ("clip chỉ-ảnh-tham-chiếu không nhận khung cuối"). Pha vẽ khung cuối thuộc autopilot (`_end_frame_phase`).
- **Dấu vết**: bảng `end_frames` 0 dòng; 4 shot có `end_state` (248, 250, 251, 252, 253, 256…) nhưng không vẽ khung cuối → không tốn ảnh.
- **Kết quả**: vô hiệu đúng thiết kế. `why` (thử thật Kling end_frame) **chưa đóng**. Đề xuất tắt khi dùng ref_groups.

### 2.6 film_crew — `V` (ứng viên)
- **Hiệu lực**: `prompts.py:250/346/385`, `knowledge.py:123` — Director thay 3 tài liệu cũ bằng `roles/director.md`, Quay phim (Tầng B) đọc `roles/dp.md`.
- **Dấu vết**: llm_calls stage `director` 6 lượt (06/10 15:09–15:22, 191k input / 46k output tokens, cache 52k); diag `dp_calls` "Quay phim (Tầng B): 2 lượt cho cảnh [1, 2]"; `director_review` "2 cảnh đạt ý đồ"; `projects.director_raw` có khối `tradeoffs` (ví dụ cảnh 2: chọn MAXIM làm `focus` duy nhất, bù bằng `dp_notes`) — khối ghi tradeoffs là đặc trưng của bộ mới. 2 lần `bad_json_retry` là lỗi schema (idx cảnh, tên focus), Director tự sửa lượt 2.
- **Kết quả**: chạy thật, 9 shot dùng được, người dùng nhận phim. Lỗi khung (shot 4/6 "cùng khung" sai, prompt "medium shot + dép" cạnh "Framing: MCU") được phân tích ở `DU_AN_KHUNG_LONG_DO` mục 6 là do dữ liệu/ảnh neo/khóa nhận dạng, không quy cho bộ luật.
- **Đóng `why`?** Điều "chưa có lần Director thật nào chạy với bộ mới" **đã đóng**. Chưa có A/B so với bộ 3 tài liệu cũ — nếu người dùng cần so sánh, phải đo trên dự án cũ.

### 2.7 j_cut — `?`
- **Hiệu lực**: `voice.py:403`; điều kiện `scene_id not in synced`. Cả hai cảnh thoại (250, 252) có `lipsync/index.json` `state=done` → `synced` → nhánh J-cut bị bỏ.
- **Bằng chứng số**: câu 1 `start=5.5` = 4,5 (đầu shot 3) + 1,0; câu 2 `start=12.04` = 11,04 + 1,0 (đúng mốc khớp môi, không có lệch 0,25 s).
- **Kết quả**: không tác dụng trên #22. `why` (nghe thử bản có J-cut trên giọng Việt lồng) **chưa đóng**; cần dự án có thoại không khớp môi (shot trung/toàn).

### 2.8 lip_sync — `G`
- **Hiệu lực**: `lipsync.enabled()`; không dùng sync.so (người dùng 26/09) → shot cận đánh dấu tạo kèm giọng Seedance (reference_audio).
- **Dấu vết**: `lipsync/index.json` 250 (job 539) và 252 (job 541) `method=generate`, offset 1,0 s; `shot_250.wav`, `shot_252.wav`; diag `lipsync_not_applied` job 506 (shot thoại bị gửi Kling — lỗi đường gửi, đã đổi sang Seedance). Diag `clip_measure`: job 539 "miệng không theo giọng ở MAXIM 1.0–3.59 s (tương quan 0.03)", job 541 "KELLY 1.0–3.19 s (tương quan 0.44)". Ghi lượt 1: 0,14 / 0,45; lượt 2: 0,03 / 0,44 (docs/kld_runs/README.md).
- **Kết quả**: giọng đúng người, đúng mốc, nhưng miệng gần như không bám giọng (< 0,65). Seedance 2.5 chế độ chỉ-ảnh-tham-chiếu chưa nhép theo giọng (memory `reference_outfit_hair_leak…`). Người dùng nhận phim nhưng không có lời nhận xét riêng về khớp môi.
- **Đóng `why`?** "Thử 1 shot cận giọng Việt (~$0,60)" đã đóng (có số đo), nhưng số đo cho thấy không đạt. **Không `verified`**; giữ thử, đo lại sau khi chuyển shot thoại sang nhóm "take" (`dialogue_take`) nếu muốn đạt 0,65.

### 2.9 motion_trim — `?`
- **Hiệu lực**: `shots.motion_start/…` (`core/shots.py:456, 515`). Có cờ → clip tham chiếu đơn (lone ref) bị cắt theo giây dự kiến; không cờ → giữ nguyên ("kept whole").
- **Dấu vết**: `data/projects/22/videos/`: cặp `NN_raw.mp4` / `NN.mp4`: 01 (4,04 → 2,5), 02 (→ 2,0), 04 (→ 2,5), 06 (→ 3,0), 07/08/09 (12,04 → 11,5). 03/05 (thoại) không cắt — đúng luật loại shot thoại. So khung đầu: mốc bắt đầu tốt nhất = 0,0 s ở cả 7 clip (tôi đo bằng OpenCV, 0 USD).
- **Kết quả**: mới thực hiện cắt đuôi, chưa lần nào dời đầu clip (phần rủi ro `why`: model chèn cảnh khác cuối clip đo là "chuyển động mạnh"). Không có diag riêng.
- **Còn thiếu**: một clip mà bộ chọn dời > 0 s rồi người xem kiểm. Ghi chú: người dùng đề xuất `trim_start` cho Editor (BAN_GIAO mục 6) — cùng vấn đề.

### 2.10 place_render_refs — `V` (ứng viên)
- **Hiệu lực**: có, bật bằng màn 🧪; người dùng đồng ý bật 06/10 (`DU_AN` mục 6). `runner.py:1616/1690/1746/1782`, `location_pack.py:188`, `scene_establish`.
- **Dấu vết**: `jobs.sent_refs` của cả 9 ảnh duyệt (525–528, 533, 535, 556–558) chứa ref `place_render` (`plate.png`); diag `image/place_match` 26 dòng: nền khớp ở ảnh duyệt 525 (0,51), 556 (0,37), 557 (0,35), 558 cảnh báo 0,31 < 0,35; vài khung nội thất "không đo được". Từ commit `c8f7a69` (07/10 15:32) render 3D cũng đi kèm video (prompt "Image 4 is the PLACE render for Shot 1…"; Codex đã kiểm shot 7–9 có Image 6 = render).
- **Kết quả**: giúp — bản 2 "nền đúng render 3D"; đoạn nhảy giữ đúng nền 11,5 s sau khi sửa nền (BAN_GIAO mục 4: `bac_thang_giua`, `plate_view.background=124`, khóa nền trong prompt).
- **Mặt trái cần ghi**: vẫn phải sửa tay dữ liệu (plate_spot, dựng lại nền `location_pack.ensure_plates` — lỗi phiên Claude #3), nền ảnh lượt đầu đo 0,01–0,32 (lệch) ở nhiều khung bị loại.
- **Đóng `why`?** "Chưa chạy thật trả tiền" **đã đóng**. Đề xuất `verified` (phạm vi: cảnh có mô hình 3D); còn mở: đường vẽ thủ công không dựng lại nền khi đổi chỗ đứng (mục "việc để sau").

### 2.11 profile_digest — `?`
- **Hiệu lực**: `prompts.short_lock_block` (video) và `runner.py:1436` (ảnh, `lock_medium`), nhưng KHÔNG dùng cho nhân vật có ảnh OUTFIT (`MAXIM KL`, `KELLY KL`, mã chú thích ở runner.py:1430+). Chỉ MAXIM/KELLY đồ thường (shot 1–3, 5, một phần cảnh nhảy) dùng.
- **Dấu vết**: hồ sơ KELLY/MAXIM có khối `digest` (lock_short ≤ 200, lock_medium ≤ 500, nguồn `code`); không có diag riêng; prompt ảnh Director viết sẵn ngắn gọn.
- **Kết quả**: không tách được; lỗi "mũ đen thay mũ sừng" vốn do khóa nhận dạng của hồ sơ đồ thường (ghi `DU_AN` mục 6, đã sửa `370dacc`, không phải lỗi riêng của digest). `why` (model ảnh giữ đúng nhân vật với bản ngắn không) **chưa đo**.

### 2.12 qc_team — `T`
- **Hiệu lực**: có (`qc_scene.py:420`: chuyên viên Nhân vật + bảng luật code; mọi khung vẫn chờ người).
- **Dấu vết**: 37 khung trong `qc_scene/team.json`; 41 lượt Claude (`usage_events` stage `qc_team`).
- **Số đo** (so quyết định người trên 37 khung): chặn+người loại 24; chặn+người duyệt **6** (job 527, 533, 535, 556, 557, 558); cho qua+người duyệt 3 (525, 526, 528); cho qua+người loại 4 (477, 485, 492, 493). Khớp 27/37 = 73 %; người loại 28/37 = 76 % nên "luôn chặn" cũng đạt 76 %.
- **Nguyên nhân gốc lỗi chặn**: chuyên viên so với hồ sơ chuẩn đồ thường của KELLY KL/MAXIM KL ("áo croptop trắng + jacket vàng", "jacket da bạc") trong khi cả dự án là bộ Khủng Long Đỏ; ví dụ job 556: "Kelly… hoodie đỏ, không phải croptop trắng…"; job 527: "áo hoodie khủng long thay áo da bạc". Tức là kiểm nhầm trang phục theo thiết kế.
- **Hậu quả**: vô hại với quyết định (không tự duyệt/vẽ lại) nhưng thêm nhiễu + khoảng 220 nghìn token Claude (62k input mới, 92k cache đọc, 26k cache ghi, 40k output theo `team.json`); có tác dụng phụ là làm bảng duyệt chứa "block" sai.
- **Đề xuất**: tắt (hoặc sửa hồ sơ `lock_rules` của biến thể KL trước khi dùng lại). Điều kiện `why` ("mọi khung vẫn chờ người, chưa tự duyệt") giữ nguyên.

### 2.13 scene_establishing — `T`
- **Hiệu lực**: có (`runner.py:1627`, `scene_establish.py`).
- **Dấu vết**: diag `image/establishing` ×3 (job 476/cảnh 1, 482/cảnh 2, 550/cảnh 2); `establish/index.json` cảnh 1 `scene_1.png` (AI vẽ từ 3 ảnh Kho), cảnh 2: `scene_2.png` hiện là render 3D đồng trục do người dùng yêu cầu 07/10 (bản AI vẽ từ ngoài tường lưu `scene_2_ve_tu_ngoai_tuong_bo.png`).
- **Kết quả**: ảnh toàn cảnh AI kéo ảnh sai: `DU_AN` mục 6 (5) "ảnh toàn cảnh (nhà nhìn từ ngoài) gửi làm nền" và "vẽ thành ngôi nhà nhìn từ ngoài, 16:9 trong dự án dọc (chưa sửa gốc)". Sau sửa, ảnh duyệt cảnh 1 (525–528, 533, 535) không còn ref `location`; ảnh duyệt cảnh 2 (556–558) dùng `scene_2.png` = render 3D. Tức là **không có khung duyệt nào dùng ảnh toàn cảnh do AI vẽ**.
- **Đề xuất**: tắt khi đã bật `place_render_refs` (render 3D thay thế, 0 USD); `why` ("thử cảnh ngày, qua luồng chính") được trả lời tiêu cực cho cảnh trong nhà.

### 2.14 scene_qc — `T`
- **Hiệu lực**: có (`known_issues.py:24/47`, lớp 0 bằng code; lớp 1 Claude `scene_qc_claude` KHÔNG bật).
- **Dấu vết**: `qc_scene/layer0.json` 46 khung: 22 cờ `shot_size`, 17 `stacked_tiers`, 3 `no_face`. Tự vẽ lại (`origin=auto`) 7 ảnh vì lệch cỡ cảnh: job 485 (từ 476), 486–488 (cùng đợt, hủy do "Request timed out"), 492, 500, 501, 534. Chi diag `image/redraw` ×7 (error).
- **Số đo**: 5 ảnh tự vẽ lại chạy xong đều bị người loại; 3 bị hủy; **0** được duyệt. Cả 9 khung người duyệt đều mang cờ lớp 0 (shot_size: 525, 527, 528, 533, 535; no_face: 526; stacked_tiers: 556–558 — nhưng bản đồ có cầu thang nhiều tầng, người dùng chọn `bac_thang_giua`, nên cờ lạc hậu). Lỗi cũ: câu sửa tự vẽ lại XÓA câu sửa của người (đã sửa `370dacc`).
- **Kết quả**: lớp 0 "đo mặt cao khung" lệch với mắt người (người duyệt MS/MLS khi shot xin MCU); chi khoảng 7 ảnh (≈ 0,35 USD theo giá ≈ 0,05/ảnh) không ra bản dùng.
- **Đề xuất**: tắt tự vẽ lại theo `shot_size`; giữ cờ đo ở dạng ghi chú nếu cần. Chưa đủ để `verified`.

### 2.15 seedance_ref_groups — `M`
- **Hiệu lực**: có (`seedance_refs.enabled` per_shot + cờ). `eligible()` đúng cho mọi shot (`video_route=single`, không `kling`, không phải `face_closeup` vì `closeup_start_frame` không bật).
- **Dấu vết**: prompt gửi Seedance dạng "Image N is the storyboard frame / is KELLY KL: identity only / OUTFIT / PLACE render" (xem `experiments/quality_samples.json` cảnh 253); 8/9 clip duyệt có diag `subjects`; `sent_group` NULL cho cả 45 video job → không có nhóm nhiều shot. Không có diag từ chối bộ lọc / `task_failed` ngoài 1 lần "Account balance not enough" (job 504).
- **Kết quả**: đường "chỉ ảnh tham chiếu, từng shot" chạy đúng ở luồng chính, cảnh ban ngày; khuyết điểm đã biết: miệng không bám giọng (0,03/0,44), mặt mịn hơn khung (clip 561: ×0,12; 568: ×0,24; 569: ×0,23 — diag `clip_measure` hỏi "anime / búp bê?").
- **Đóng `why`?** Đã đóng "luồng chính"; **chưa** đóng nhóm gộp 2–4 shot (0 lần) và cảnh tháp đêm. Có thể đề xuất `verified` cho chế độ từng shot nếu người dùng chấp nhận tách phạm vi; hiện xếp M.

### 2.16 seedance_sample_mode — `G`
- **Hiệu lực**: có (cờ màn 🧪 07/10 16:10) — chỉ bật hộp "So độ nét" ở tab Video, KHÔNG đổi clip phim.
- **Dấu vết**: `usage_events` stage `quality_sample`: A 720p 4 s + B mẫu 480p 4 s; `experiments/quality_samples.json` cảnh 253 kind `direct` 0,92448 USD (+ draft 0,4112 USD); `quality_253_direct.mp4`, `quality_253_draft.mp4`. B bản cuối 1080p (2,08 USD) **chưa gửi** (BAN_GIAO mục 2/6).
- **Kết quả**: vô hại (trần cặp 4 USD, tiêu 1,34). `why` ("bản cuối chưa chạy thật") **chưa đóng**; A+ (phóng AI) đã bỏ (`decision_no_ai_upscale_in_pipeline`). Cần người dùng quyết có gửi B final hay bỏ hẳn S4.11.

### 2.17 seedance_subjects — `V` (ứng viên)
- **Hiệu lực**: có (`runner.py:784`, `seedance_refs.py:286`); nhà cung cấp ClipAI có `supports_subjects`.
- **Dấu vết**: diag `video/subjects` ×26, cả 26 mức `info` ("gửi N ảnh qua Kho chủ thể (tải mới X, dùng lại Y)"), 0 cảnh báo lùi về ảnh đánh dấu; job duyệt 537, 538, 539, 540, 549, 568, 569, 561 đều có; bảng `seedance_subject_pictures` 33 dòng `active` (dự án 22: khung P22_S248…S256, MAXIM_KL, KELLY_KL_OUTFIT, `P22_place_1_*`).
- **Kết quả**: 9 shot, 2 nhân vật + OUTFIT + render nền, 0 từ chối của bộ lọc. Thời gian active ≈ vài giây như thử #15.
- **Đóng `why`?** "Mới 1 shot / 1 nhân vật; chưa qua luồng chính (nhóm nhiều shot, 3 người)" — luồng chính + 2 nhân vật đã đóng; nhóm nhiều shot / 3 người chưa. Đề xuất `verified` với ghi chú phạm vi đó.

### 2.18 shot_transitions — `M`
- **Hiệu lực**: có (`delivery.py:391`); `transition_in = flash` ở shot 4 và 6.
- **Dấu vết**: manifest `outputs` #34 (07/10 13:13): `shot_transitions` gồm `edge_3` (tail flash), `edge_4` (head flash), `edge_5`, `edge_6` → `output/_edges/edge_*.mp4`; `DU_AN` mục 6 đo bằng số: khung trắng đúng 7,5 s / 14,04 s.
- **Kết quả**: phim xác nhận đạt, chớp trắng đúng chỗ hô biến. Mới chỉ `flash`; "lia nhòe / lao vào khung" (rủi ro `why`) không dùng. Đề xuất `verified` nếu người dùng chấp nhận phạm vi flash, hoặc tách cờ; hiện M.

### 2.19 story_check — `?`
- **Hiệu lực**: chỉ `autopilot._story_check_phase` (+ trang Kịch bản hiển thị `story_check.json` nếu có).
- **Dấu vết**: không có `data/projects/22/story_check.json`, không có diag `story_check*`. **Kết quả**: không có dấu vết. `why` (người xem Claude có bắt đúng chỗ khó hiểu) **chưa đóng**; cần chạy lượt K trên dự án có kịch bản đã biết điểm khó.

### 2.20 storyboard_api — `V` (ứng viên, yếu)
- **Hiệu lực**: có (`scene_storyboard.enabled()` + Deepix `supports_storyboard`, `runner.py:1637/1731`).
- **Dấu vết**: `sent_refs` có role `storyboard` (`sb_<hash>`) + `previous_scene "frame 1 (scene anchor)"` ở 526, 527, 528, 533, 535 (cảnh 1) và 557, 558 (cảnh 2); 556 (shot đầu của cảnh 2) có `storyboard`; chỉ 525 (neo cảnh 1) không có anchor. 7/9 ảnh duyệt có ảnh neo.
- **Kết quả**: dùng thật trên cảnh 6 shot 2 người + cảnh nhảy 3 shot. Lỗi do cơ chế neo: `DU_AN` mục 6 (1) "ảnh neo shot 1 kèm câu 'vẽ khoảnh khắc MỚI, góc máy KHÁC'" làm shot 4/6 sai "cùng khung" (sửa `370dacc`); sau đó vẫn tốn 7 và 10 lượt ảnh ở shot 4 và 6. Không có đối chứng không-storyboard.
- **Đóng `why`?** "Mới 1 cảnh, chưa thử cảnh đông người / hành động" — đã thử 2 cảnh có 2 người và hành động; nên ghi `verified` kèm điều kiện "ảnh neo không được ép đổi góc" đã sửa. Người dùng cân nhắc (độ tin: vừa).

### 2.21 storyboard_auto_trust — `T`
- **Hiệu lực**: chỉ `autopilot._qc_trusted` (core/autopilot.py:648).
- **Số đo**: `effectiveness.look_trust('FF_INGAME','gpt-image-2.5-sunburst')` = 122 cặp, khớp 69,7 %, người loại 88, tỷ lệ bỏ lọt 3,4 %, `trusted=False` → bật cờ nhưng không bao giờ kích hoạt ở trạng thái này. `why` ("≥ 90 % trên ≥ 50 ảnh") chưa đạt: 69,7 % < 90 %.
- **Đề xuất**: tắt (nguy cơ bỏ cổng duyệt nếu số đo trôi); không có dấu vết trên #22.

### 2.22 voice_check_redo — `?`
- **Hiệu lực**: chỉ `autopilot._voice_check_phase` (`core/autopilot.py:1313`). Nút tab Motion "🎙 Giọng thoại" dùng `voice_check.check_project` tay, không qua cờ.
- **Dấu vết**: không có diag `voice_check`, không có `voice_redo_done`; TTS 2 câu `resends: 0`. Không có dấu vết; `why` (ngưỡng đo trên giọng Việt thật) **chưa đóng**.

## 3. Việc còn thiếu bằng chứng (gom theo hành động)

1. **Autopilot trên dự án có thoại** (đóng audio_first, story_check, voice_check_redo, end_frames pha, storyboard_auto_trust): chạy một dự án nhỏ (≥ 2 câu thoại, ≥ 1 shot nội thất) bằng chế độ tự chạy; kiểm `autopilot_gates.timeline_locked`, `story_check.json`, diag `voice_check`, bảng `end_frames`.
2. **J-cut**: cần thoại ở shot không khớp môi (trung/toàn) — #22 toàn khớp môi nên nhánh không chạy.
3. **motion_trim**: một clip lone-ref mà hành động chính đến muộn để bộ chọn dời > 0 s; người xem kiểm không có cảnh lạ ở đuôi.
4. **profile_digest**: ảnh nhân vật đồ thường dùng bản ngắn vs bản đầy đủ, đo `identity` bằng QC/mắt người (GĐ8).
5. **auto_voice_cast**: nghe thử biến thể cao độ ở dự án có ≥ 3 vai cùng giới.
6. **seedance_ref_groups / seedance_subjects**: một nhóm 2–4 shot hoặc cảnh 3 nhân vật qua Kho chủ thể.
7. **shot_transitions**: một chỗ nối `whip` / `zoom_through` xem trên bản dựng thật.
8. **seedance_sample_mode**: người dùng quyết gửi B final 1080p (2,08 USD) hay bỏ S4.11.
9. **lip_sync**: nếu muốn `verified`, cần đạt ≥ 0,65 trên ≥ 2 shot (thử `dialogue_take` nhóm; `kld_runs` cho thấy 0,03/0,44).
10. **qc_team, scene_qc, scene_establishing**: sửa gốc (hồ sơ `lock_rules` của biến thể KL theo trang phục; ngưỡng cỡ cảnh theo MCU/MS thực tế; dừng ảnh toàn cảnh AI khi đã có render 3D) rồi đo lại trên một dự án mới.

## 4. Gợi ý thao tác (không làm trong phiên này)

- Duyệt `verified` sau khi người dùng xem lại: **place_render_refs, seedance_subjects, film_crew, storyboard_api** (phạm vi ghi ở từng mục). Mỗi cờ cần: ngày duyệt, đường dẫn báo cáo (file này) và ghi chú phạm vi trong cột `why`.
- Tắt khỏi cấu hình đang chạy (không xóa code): **qc_team, scene_qc (tự vẽ lại), scene_establishing, storyboard_auto_trust, camera_setups, continuous_takes, end_frames** — trước khi tắt `camera_setups` kiểm `plate_camera.py` / `director_report.py` đọc nhãn.
- Sau khi tắt, `on_unverified()` sẽ giảm từ 22 xuống còn khoảng 11 cờ đang chạy thật nhưng chưa chốt.
