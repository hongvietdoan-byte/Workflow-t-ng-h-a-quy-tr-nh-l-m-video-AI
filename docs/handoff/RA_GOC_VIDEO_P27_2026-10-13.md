# Rà gốc khâu GEN VIDEO — dự án #27 tập 1 (13/10/2026)

Phiên con CHỈ ĐỌC, 0 USD. Nguồn: `data/manifest.sqlite` (jobs / job_events / review_log / sent_package / scenes.data), code worktree
`danh-gia-devsys-2026-491348` (main 13/10). Bổ sung cho `P27_TAP1_TONG_KET_2026-10-13.md` mục 6 (11 lỗi đã biết — không lặp lại, chỉ
nói khi cờ sửa CHƯA che hết).

Số liệu: 115 job video; 72 job không đạt (53 loại, 11 hủy, 8 hỏng), 34 duyệt, 9 chờ duyệt.
Lưu ý thời điểm: gần như mọi job hỏng chạy 12/10 16:53 → 13/10 06:41 UTC; các cờ sửa (framing_guard, skill_object_guard,
ref_mark_off_face, plate_anchored_image) commit 13/10 16:06–19:14 giờ VN = SAU các job đó → chưa có job nào chạy với cờ bật; đánh giá
"cờ che gốc" dưới đây là đọc code + thử lại trên dữ liệu của chính các job hỏng.

## (a) Bảng gốc × số lần × shot/job

| # | Gốc | Lần | Shot · job | Bằng chứng ngắn |
|---|-----|----|-----------|-----------------|
| G1 | **Ảnh đầu đã duyệt nhưng sai, chỉ lộ ra khi xem video → đổi ảnh → video cũ bỏ** (nền không đúng 3D: Tháp Đồng Hồ→Cổng Trời; đốm đỏ / bóng mờ / giày) | 19 loại + 6 hỏng/hủy stale | s1 813 · s2 824 · s3 783 784 811 814 840 · s4 785 807 825 841 · s8 822 · s9 823 · s10 847 · s11 848 · s12 808 · s13 809 · s16 797 · s17 890 895 · s18 872 · s22 803 | "bản 1080p từ ảnh nền cũ (Tháp Đồng Hồ)"; "ảnh khung đầu đổi nền Cổng Trời"; 15/22 shot có ảnh duyệt lại 13/10 SAU khi đã gen video |
| G2 | **Sửa motion prompt sau khi gen (người dùng/Đạo diễn) → video cũ + bạn cùng nhóm Seedance phải gen lại** | 10 loại + 2 stale | s3 844 · s6 865 · s8 791 · s9 792 · s10 793 834 · s11 794 835 · s16 837 902 · s19 800 | "làm lại vì motion prompt / thời lượng / model / âm thanh đã đổi" |
| G3 | **Nhóm Seedance ghép 2 shot: 1 shot hỏng kéo shot đã đạt gen lại** | ≥ 8 (chồng G1/G2) | (5,6) 788→879 (người dùng "dùng lại bản v1"), 865, 867 · (8,9) 791/792, 822/823, 852/853 · (10,11) 793/794, 834/835, 847/848 · (3,4) 784/785, 811/807 | shot 6 đã duyệt v1, nhóm gen lại vì shot 5 → bỏ 879 |
| G4 | **QC tự sửa BẢN CAO (final) → Đạo diễn viết lại prompt → bản cao con bị chặn stale** (vòng lặp chắc chắn hỏng) | 3 loại + 3 hỏng | s2 876→877 · s20 859→874 · s22 860→875 | 876 QC 0,80<0,82 "tự sửa" → 877 "stale_input: bản cao bị chặn: đầu vào đã đổi sau khi duyệt nháp" |
| G5 | **Bản cao xếp hàng khi chưa được bảo / từ nháp sắp cũ** (lỗi 6.7 đã giao) | 6 hủy + 2 loại | s5 815 855 · s12 817 · s14 818 · s16 819 · s20 820 · s21 873 · s22 821 | "người dùng: chưa gửi gen bản cao (13/10)" ×6 |
| G6 | **Máy lùi / đổi bố cục / vẽ lại kiến trúc** — plate 3D được prompt cho "quyền trên ảnh khung đầu" trong khi plate KHÁC góc máy | 4 | s17 858 890(ý) 912 · s18 896 ("máy trôi khỏi tường") | 912: "lùi máy + thêm mặt đồng hồ"; QC chấm 0,95 / 1,00 "đạt" |
| G7 | **Khung cuối khác khoảng cách máy / người → nhảy cóc, kéo lùi, cắt cảnh** | 5 | s16 888 891 898 907 · s3 782 | 898 "Kelly bị kéo lùi rồi keo mới mọc"; 907 "nhảy cóc ra xa ở 0,6 s" (khung cuối end_284_21 Kelly khuất, không thấy mặt) |
| G8 | **Vật kỹ năng (tường keo skin thang máy) bị vẽ sai**: thành thang máy thật / mất skin / thấp / bay | 5 | s16 866 883 889 891 908 | 891 "cửa thang máy mở nhìn xuyên"; 908 "mất skin thang máy (tấm thép trơn)" |
| G9 | **Dấu "+" đỏ của ảnh ref chép lên mặt** | 3 | s8 852 · s9 853 · s18 896 | QC 852: "red cross/plus mark … on Kelly's face in all frames"; tệp ref `job_894_…_marked_none_…_marked.png` = ẢNH KHUNG ĐẦU bị đánh dấu mắt |
| G10 | **Trạng thái nhân vật không giữ suốt shot / giữa shot liền mạch** (bóng mờ, giày trắng, đốm đỏ) | 5 | s5/6 788 · s8/9 816 852 853 (cuối shot 9 mất bóng mờ) · s10 862 · s16 849 (giày) | "shot 9 mất bóng mờ cuối clip"; "bóng mờ shot 6 / giày trắng shot 16" |
| G11 | **Motion không tới end_state / hành động nhiều nhịp trong 1–1,5 s / performance lệch hành động** | 3 loại (+ ≥ 10 lần QC gợi ý trên bản đã duyệt) | s20 859 (1,5 s: thụp→bật→chạy) · s22 860 · s2 876 · gợi ý: s1 804/813/832/861, s7 790, s9 823/864/881, s12 808, s15 796/871 | s1 perf.body "hands tense around the rifle grip" trong shot POV (FF không cầm súng POV); s15 perf.body "…ném dứt khoát bằng một tay" (hành động của shot 16) |
| G12 | **Chạy tại chỗ: khung cuối "vài bước" mâu thuẫn chạy nước rút** | 1 | s3 782 (Kling 2 s, shot 1,2 s) | "nền trượt, Kelly/đồng đội/cổng đứng yên" |
| G13 | **Ảnh ref sai luật ClipAI (tỉ lệ)** | 1 | s17 798 | "ảnh 4 (488×1280) tỉ lệ 0.38 — cần 0.4–2.5" |
| G14 | Đổi ý đồ kịch bản giữa chừng (không phải lỗi máy) | 4 | s16 883 889 (3 lần đổi ý tường keo/thời lượng) · s19 838 · s18/17 899 901 | "shot 16 mới — ném nhanh, keo mọc ngay…" |

Tổng: ~**43/72 (60 %) là lãng phí do đầu vào đổi SAU khi gen (G1+G2+G3+G4+G5)** — không phải model video kém. Phần lỗi của chính
model video (G6–G13) ≈ 28 lần, tập trung shot 16 (vật kỹ năng + khung cuối) và 17 (plate ↔ khung đầu).
Shot 3 (9 job): 1 lỗi model (782) + 8 do G1/G2/G3. Shot 16 (14 job): G1 1, G2 2, G8 5, G7 4, G10 1, G14 2. Shot 17 (10 job): G6 3, G1 2, G13 1.

## (b) Danh sách lỗi (công thức, không vá shot)

### V1 — Prompt video cho plate 3D "quyền trên ảnh khung đầu" (gốc G6) · nhóm file A (seedance_refs)
- **file:dòng**: `core/seedance_refs.py:464-469` — "Image N is the PLACE render … It decides architecture over conflicting text or
  storyboard details".
- **Triệu chứng**: s17 858/912 máy lùi + vẽ tháp/mặt đồng hồ; QC 0,95–1,00.
- **Gốc**: plate s17 (`refs_clean/plate_b8e180be52…`) là máy SÁT ĐẤT nhìn thẳng chân tháp; ảnh đầu job_910 là góc CAO sau lưng Kelly,
  tháp xa hơn. Hai khung khác máy → model "hòa giải" bằng cách lùi/đổi bố cục. Cờ `plate_anchored_image` chỉ sửa khâu VẼ ẢNH
  (`runner.py:3039-3073`, `plate_anchor.py`), KHÔNG đụng câu này của prompt video → **cờ không che gốc ở khâu video**.
- **Sửa**: (1) video: ảnh khung đầu đã duyệt là nguồn duy nhất về bố cục + kiến trúc trong khung; plate chỉ "cho phần lộ thêm khi máy
  di chuyển". (2) shot `camera_move=static` (hoặc push-in nhẹ) → KHÔNG gửi plate cho video. (3) trước gửi: nếu có plate và ảnh đầu không
  được vẽ từ plate đó (không có dấu `plate_anchored` trên job ảnh) → VÀNG, không gửi plate.
- **Test**: `tests/test_seedance_place_text.py::test_static_shot_sends_no_place_render` (đỏ: place_text có "decides architecture");
  `::test_place_text_never_overrides_storyboard` (đỏ trước, xanh sau: câu chứa "Image 1 decides framing and architecture").

### V2 — Đo bố cục sau gen: ngưỡng khung 0 sát biên + không bắt vẽ lại kiến trúc khi KHÔNG lùi máy (G6) · nhóm B (framing_guard)
- **file:dòng**: `core/framing_guard.py:35-37` (F0_CORNER 0,07; Seedance đạt 0,049–0,057; hỏng 912 = 0,088), `:222-241` (chỉ so tỉ lệ nền).
- **Gốc**: cờ `framing_guard` bắt 912 (sát ngưỡng) nhưng 858 "thêm mặt đồng hồ" không lùi máy sẽ lọt; chỉ đo khung 0 + zoom, không đo
  khung CUỐI so ảnh đầu (kiến trúc mọc thêm dần).
- **Sửa**: thêm đo `last_frame vs start picture` trên vùng nền (che hộp người YuNet/hộp thân): tỉ lệ điểm khớp nền < ngưỡng → `frame_end`
  ĐỎ; đưa ảnh khung đầu + khung cuối clip cạnh nhau cho QC với câu hỏi cụ thể "kiến trúc có thêm/bớt gì".
- **Test**: `tests/test_framing_guard.py::test_end_frame_architecture_drift_flags` (fixture khung cuối 858 từ `tests/fixtures/framing_p27/`).

### V3 — Kiểm khung cuối trước gửi bỏ qua khi không thấy mặt (G7) · nhóm B
- **file:dòng**: `core/framing_guard.py:155-163` — `ratio None` (không thấy mặt ở khung cuối) → `ok=True` kèm note; `runner.py:1254-1270`.
- **Triệu chứng**: end_284_21 (Kelly khuất sau tường) được giữ → 907 nhảy cóc 0,6 s.
- **Gốc**: thiếu thước đo cỡ người khi mặt bị che; "không đo được" bị coi là đạt (trái CHUAN_XAY_DUNG "không im lặng khi thiếu đầu vào").
- **Sửa**: ok=None → VÀNG + KHÔNG gửi khung cuối mặc định với shot có người di chuyển; đo thêm hộp thân/đầu (YuNet → fallback chiều cao
  silhouette người từ mask phân đoạn hoặc chiều cao vật mốc). Shot có vật kỹ năng mọc lên (`skill_objects.rises`) → không gửi khung cuối,
  đi tuyến GHÉP (`tools/skill_object_composite.py`) mặc định.
- **Test**: `tests/test_framing_guard.py::test_end_frame_without_face_is_not_ok` (end_284_21 vs job_836: ok không phải True).

### V4 — skill_object_guard thay "elevator skin" bằng "metal-panel skin" → tái tạo đúng lỗi 908 (G8) · nhóm C (skill_objects)
- **file:dòng**: `core/skill_objects.py:23-35` (`_EN_FIXES`), `:147-159` guard_prompt.
- **Triệu chứng**: 891 thang máy thật (cửa mở); 908 khi bỏ chữ → "tấm thép trơn, mất skin".
- **Gốc**: chữ là nguồn duy nhất của skin — ảnh ref gửi kèm là `Bom keo 1.png` (quả bom, `assets/367/1.png`), không có ảnh BỀ MẶT tường
  skin. Cờ hiện tại chỉ đổi giữa hai lỗi.
- **Sửa**: (1) Kho: vật kỹ năng phải có ảnh "dạng triển khai" (tường đã mọc, skin) → gửi làm ref có vai trò `object_deployed` + câu
  "the surface pattern of Image N is printed decoration on a solid block"; thay chữ bằng "the skin pattern shown in Image N" (không
  "metal-panel"). (2) Thiếu ảnh dạng triển khai → ĐỎ trước gửi với shot `rises`, gợi ý tuyến GHÉP. (3) Mặc định shot `rises` → ghép code
  (shot 16 đã chứng minh).
- **Test**: `tests/test_skill_objects.py::test_guard_keeps_skin_reference_not_plain_metal` (đỏ: kết quả chứa "metal-panel skin");
  `::test_rising_skill_object_without_deployed_picture_blocks`.

### V5 — Dấu "+" lên mặt: ảnh khung đầu bị đánh dấu MẮT khi Kho chủ thể không nhận; cờ lùi về eye_plus sau từ chối (G9) · nhóm A + D (runner)
- **file:dòng**: `core/runner.py:907-920` (`_finish_kwargs` mark_fallback), `:1399-1412`; `core/seedance_refs.py:234-241, 263-277`
  (`step_mark_back` → "eye_plus").
- **Gốc**: Kho chủ thể đầy (lỗi 6.11) → dự phòng đánh dấu cả ẢNH KHUNG ĐẦU + ảnh nhân vật bằng dấu trên mắt (`…_marked_none_…_marked.png`).
  Cờ `ref_mark_off_face` đổi sang góc, nhưng sau 1 lần bị từ chối "người thật" lại quay về eye_plus = lỗi cũ → **che một phần**.
- **Sửa**: thang dự phòng: hosted → banner (không dấu) → corner_plus → đổi tuyến Kling (start+end frame, không ref); KHÔNG bao giờ
  eye_plus cho ảnh có mặt nhân vật cận (`face_closeup` (đã gỡ 18/10 cùng cờ closeup_start_frame)) hay ảnh khung đầu. Sau gen: `clip_measure.ref_mark` có cờ → giữ cho người (hiện chỉ
  gợi ý ở nháp).
- **Test**: `tests/test_seedance_marks.py::test_refusal_never_returns_to_eye_plus_on_face`; `::test_start_frame_never_eye_marked`.

### V6 — QC tự sửa bản cao → vòng chắc chắn hỏng (G4) · nhóm E (pipeline/quality_tier)
- **file:dòng**: `core/pipeline.py:539-546` (autofix khi `not auto`, áp cho cả final); `core/quality_tier.py:167` (`tier_for_new_job` cho con
  của final = final) + chặn stale ở runner.
- **Gốc**: bản cao phải tái tạo đúng nháp đã duyệt; QC chấm lại bản cao theo motion (cùng lỗi nháp người dùng đã chấp nhận: 876 = cùng
  gợi ý của nháp 833) → Đạo diễn viết v2 → bản cao con bị chặn "đầu vào đã đổi" → mất 3 bản 1080p (~0,5 USD/s) + 3 job hỏng.
- **Sửa**: final/direct-từ-nháp: QC chỉ so **bản cao ↔ nháp đã duyệt** (cùng bố cục/nhân vật); không bao giờ autofix; dưới ngưỡng → giữ
  cho người kèm "nháp đã có cùng lỗi?" (so qc_results của draft_job_id). Muốn sửa → tạo NHÁP mới, không tạo final con.
- **Test**: `tests/test_quality_tier_qc.py::test_final_below_threshold_never_autofixes` (đỏ: trả "auto_fix" + job con final).

### V7 — Ảnh đầu được duyệt mà chưa kiểm những thứ video sẽ lộ ra (G1 — 25 job) · nhóm F (image QC / Dashboard duyệt)
- **file:dòng**: duyệt ảnh → xếp video không có cổng "ảnh đã khớp plate + hồ sơ trạng thái"; `core/plate_anchor.py` (cờ chỉ mới thêm câu nền
  + đo sau vẽ cho ảnh MỚI); hồ sơ trạng thái nhân vật (bóng mờ, giày, đốm) không được kiểm trong ảnh.
- **Gốc**: 15/22 shot phải duyệt lại ảnh 13/10 sau khi đã gen video (nền sai 3D, trạng thái sai). Kéo theo bỏ video + bản cao.
- **Sửa**: cổng trước khi xếp video: (1) ảnh có kết quả `plate_anchor` đạt (hoặc người bấm bỏ qua có lý do); (2) checklist trạng thái
  nhân vật theo continuity group (bóng mờ/giày/đạo cụ) do QC ảnh chấm có tiêu chí riêng; (3) nháp video chỉ gen khi CẢ nhóm ảnh liền mạch
  đã duyệt (tránh gen shot 3 trước khi shot 2 đổi nền).
- **Test**: `tests/test_video_gate.py::test_queue_video_blocked_until_plate_check_passed`; `::test_group_queued_only_when_all_images_approved`.

### V8 — Nhóm Seedance: shot đã duyệt bị gen lại theo bạn cùng nhóm (G3) · nhóm A
- **file:dòng**: `core/seedance_refs.py:96-124` (`_groups` chỉ theo continuity key + độ dài), `:534-541` (`next_route` chỉ khi bị từ chối).
- **Gốc**: không có trạng thái "phần đã duyệt giữ nguyên"; đổi 1 shot → nhóm gen lại cả clip (879, 865, 867; 10/11 ba vòng).
- **Sửa**: một shot trong nhóm có phần đã được NGƯỜI duyệt → shot còn lại đi `route=single` (giữ khung đầu = khung cuối phần đã duyệt
  để nối); đo nối bằng `framing_guard.similarity` giữa khung cuối phần A và khung 0 phần B.
- **Test**: `tests/test_seedance_groups.py::test_approved_member_is_not_regenerated`.

### V9 — Không kiểm trước gửi: performance lệch hành động / nhiều nhịp trong ít giây (G11) · nhóm A + G (prompt_formula)
- **file:dòng**: `core/seedance_refs.py:920-964` (`shot_motion` ghép `performance.body` nguyên văn); `core/prompt_formula.py:519`
  (lint có `diem_bat_dau`, chưa có lint nhất quán/nhịp).
- **Bằng chứng**: s1 POV mà perf.body "hands tense around the rifle grip" (luật FF: POV tay không, `motion_physics`) → QC lặp ở 804/813/
  832/861; s15 perf.body có "ném" (shot 16); s6 perf.body "finally stops rigid looking up" (shot 7); s20 1,5 s gồm 3 nhịp → 859 không tới
  end_state.
- **Sửa**: lint trước gửi (0 USD): (1) động từ trong performance không có trong action/end_state của shot mà có ở shot kề → VÀNG "lấn shot";
  (2) áp luật POV/vũ khí lên CẢ performance; (3) số nhịp (đếm "then/rồi/,") > giây × 1 → VÀNG gợi ý tách shot hoặc tăng thời lượng (đã có
  `MIN_ACTION_SHOT` cho nhóm, chưa có cho đơn).
- **Test**: `tests/test_prompt_formula.py::test_performance_bleed_from_next_shot_warns` (s15), `::test_pov_performance_weapon_flagged` (s1),
  `::test_too_many_beats_for_seconds` (s20).

### V10 — Trạng thái nhân vật chỉ có trong chữ, ảnh danh tính là dạng thường (G10) · nhóm A
- **file:dòng**: `core/seedance_refs.py:287-311` (`identity_pictures` luôn ảnh thư viện dạng thường); `:443-444` (câu "giữ nguyên" không nói
  trạng thái).
- **Gốc**: shot 4–11 Kelly "bóng mờ" nhưng ref là Kelly đặc → cuối clip model trôi về ảnh ref (mất bóng mờ cuối shot 9).
- **Sửa**: trường `state` theo continuity group (vd `KELLY: ghost`) → (1) câu khóa "KELLY stays a blurred ghost until the last frame" trong
  khối "what stays still"; (2) ảnh danh tính lấy từ ảnh khung đầu đã duyệt (crop) cho dạng đặc biệt; (3) QC + đo sau gen so khung cuối.
- **Test**: `tests/test_seedance_prompt.py::test_character_state_locked_for_whole_clip`.

### V11 — QC video không thấy plate / khung cuối dự kiến, chỉ 6 khung (G6, G7) · nhóm E
- **file:dòng**: `core/claude_tasks.py:166-182` (ảnh QC = 6 khung + ảnh đầu + 4 ref).
- **Gốc**: 912 lùi máy + mặt đồng hồ, 858, 782 chạy tại chỗ đều QC ≥ 0,93. QC chấm theo motion, không được hỏi "bố cục/kiến trúc so ảnh đầu".
- **Sửa**: thêm khối "Đo bằng máy" bắt buộc khi `framing` có cờ → hạ trần điểm `motion_match`/`artifacts`; thêm câu hỏi kiểm bố cục với
  ảnh khung đầu đặt cạnh khung cuối; chạy tại chỗ: dùng `zoom`/dịch nền từ framing_guard (nền trượt mà vật mốc không lớn lên).
- **Test**: `tests/test_qc_video.py::test_framing_flag_caps_score` (dùng measured giả của 912).

### V12 — Khung cuối mâu thuẫn quãng đường hành động khi stretch ≤ 1,3 (G12) · nhóm D
- **file:dòng**: `core/motion_physics.py:101` (`in_place_risk` chỉ dựa tỉ lệ giây sinh/giây shot); `runner.py:1277-1290`.
- **Đánh giá cờ `locomotion_end_frame`**: che 782 (2 s / 1,2 s = 1,67 > 1,3) ✔; không che shot chạy dài có khung cuối "vài bước".
- **Sửa**: shot chạy/đi có khung cuối → đo vật mốc lớn lên giữa ảnh đầu và khung cuối (framing_guard scale): chạy nước rút mà scale ≈ 1 →
  không gửi khung cuối.
- **Test**: `tests/test_motion_physics.py::test_sprint_end_frame_same_scale_dropped`.

### V13 — Ảnh ref sai luật tỉ lệ chỉ bị bắt LÚC GỬI (G13) · nhóm A
- **file:dòng**: `core/seedance_refs.py:314` `_rule_ok_picture` (chọn ảnh khác trong pool) — 798 vẫn hỏng vì pool chỉ có ảnh 488×1280.
- **Sửa**: thiếu ảnh hợp luật → tự pad ảnh lên tỉ lệ 0,4 (nền trơn) thay vì hỏng job; ghi VÀNG.
- **Test**: `tests/test_seedance_refs.py::test_narrow_reference_padded_to_rule`.

## Cờ đã bật 13/10 — có che gốc không

| Cờ | Gốc | Che? | Ghi chú |
|----|-----|------|---------|
| plate_anchored_image | G1 (nền ảnh) / G6 | Một phần | Chỉ khâu ảnh; prompt video vẫn cho plate thắng khung đầu (V1) |
| framing_guard | G6, G7 | Một phần | Sau gen bắt 912 (sát ngưỡng), 907 (nhảy mặt ×3,6); trước gửi lọt khung cuối không thấy mặt (V3); không bắt vẽ thêm kiến trúc (V2) |
| skill_object_guard | G8 | Không — đổi lỗi 891 thành lỗi 908 | V4 |
| ref_mark_off_face | G9 | Một phần | Lùi về eye_plus sau từ chối; khung đầu vẫn bị đánh dấu khi Kho đầy (V5) |
| locomotion_end_frame | G12 | Có (782) | Lọt trường hợp stretch ≤ 1,3 (V12) |
| tts_lowercase_caps | — | ngoài khâu video | — |
| end_state_fresh (TẮT) | G2 một phần | — | `motion_en.end_state` hầu hết None (chỉ s19–21 có) → đọc `_en` từ end_state; nên bật trước tập 2 để sửa end_state không gửi bản dịch cũ |

## Nhóm file để gom vòng sửa
- **A** `core/seedance_refs.py` (+ `tests/test_seedance_*`): V1, V5 (mark ladder), V8, V9 (shot_motion), V10, V13
- **B** `core/framing_guard.py`, `core/runner.py:1254-1270`: V2, V3
- **C** `core/skill_objects.py` (+ Kho: ảnh dạng triển khai): V4
- **D** `core/runner.py:907-920, 1277-1412`, `core/motion_physics.py`: V5 (fallback), V12
- **E** `core/pipeline.py:539-546`, `core/quality_tier.py`, `core/claude_tasks.py:166-206`: V6, V11
- **F** cổng duyệt ảnh → xếp video (Dashboard + `core/plate_anchor.py`): V7
- **G** `core/prompt_formula.py`: V9 lint

Thứ tự đề xuất (theo số job tiết kiệm): V7 + V8 + V6 (≈ 43 job lãng phí) → V1 + V3 + V4 (shot 16/17) → V5, V9, V10 → V2, V11, V12, V13.
