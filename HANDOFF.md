# HANDOFF — học cách prompt chuyển động như Claude (D6 #28 vs #29, 14/10)

## Đã xong (0 USD)
- So 5 cặp prompt video (#28 job 931–935 vs #29 926–930) + ảnh 916/921, 920/925 (đọc chỉ-đọc manifest máy chính).
  - #29 shot 3–4 (job 928/929) KHÔNG phải D6: diag `chat_prompt_cap` → rơi về bản code ghép → cũng gần đứng hình như #28. Đường code ghép phải tự tốt.
  - Ảnh shot 1: cỡ Kelly như nhau (~56 % khung, đo 3D). Khác ở CHỖ: #28 Kelly đã đứng trên bậc (bậc đi lên XA máy) → "chạy về phía máy" vô lý; #29 ở chân cầu thang, trước mặt sân phẳng trống.
  - Shot 5: #29 kém (ảnh đầu đã ngồi sâu, chữ "lowers further / settled / holds"); #29 còn giữ nhãn "Acting:", viết "clock tower", bỏ câu quay lưng.
- Hướng dẫn D6: `knowledge/model_guides/seedance.md` mục 11–15, `image.md` mục 11–12 (cách nghĩ + căn cứ).
- Code ghép (fallback): cờ MỚI `motion_prose` (TẮT, verified False) — `core/motion_prose.py` + móc ở `core/seedance_refs.shot_motion`:
  diễn xuất thành câu kể "KELLY acts it out — <thân>, <nhịp>; the face shows …, eyes …"; máy track/follow/dolly/truck + có chạy/đi +
  `travel_truth.camera_mode` biết chiều → "camera tracks backward ahead of KELLY, holding the same distance as KELLY comes toward it" /
  "camera follows behind KELLY, moving along with KELLY at the same distance"; không biết → giữ "camera track". Cờ tắt: chữ cũ từng byte.
- Test `tests/test_motion_prose.py` (đỏ 4 → xanh 7). Bộ liên quan 370 passed (-n 8).
- Kiểm trên dữ liệu thật: scenes 292/295/296 #28 dựng lại `shot_motion` với cờ máy chính (script scratch, chỉ đọc) — xem báo cáo.
  (`tools/replay_payload.py` chỉ dựng gói ẢNH, không dựng prompt video.)
- `devsys/areas.json`: thêm `core/motion_prose.py` + cờ `motion_prose` vào khu step4 (không tăng version).

## Vòng sửa sau rà độc lập (14/10)
- `camera_phrase`: "lead" chỉ khi động từ di chuyển + "toward the camera" hoặc chữ máy lùi ("glancing at the camera" không tính);
  ≥ 2 nhân vật → None; máy sau lưng + chữ chỉ nói chạy trái/phải (không đi xa / về phía trước) → None (#28 shot 4 giờ giữ "camera track");
  bỏ "truck" khỏi `_TRACKING`.
- Test: 4 đỏ → xanh (liếc máy, 2 nhân vật, truck, chạy ngang máy sau lưng); test cờ TẮT so `==` cả chuỗi RUN_TOWARD + HIDE_BACK
  (chụp bằng seedance_refs của origin/main 39625903, khớp từng byte).
- Hướng dẫn D6 (seedance 11–15, image 11) + why của cờ: ghi rõ căn cứ = 1 cặp #28/#29, nhiều biến cùng đổi, chưa tách; "quá 2 điểm
  nhấn" hạ thành giả thuyết; bỏ "model hay giữ người giữa khung".

## related_areas (`py tools/related_areas.py core/motion_prose.py core/seedance_refs.py core/features.py`)
- Khu chứa file đổi: step4 (motion_prose, seedance_refs), core_infra (features).
- Khu gọi tới: autopilot, step1, step3 (claude_tasks → shot_motion lưu motion_prompt), budget (cost ước tính độ dài nhóm bằng shot_motion),
  lipsync, step2 (end_frames), plates3d, step5, diag, knowledge, dashboard_ui. Khu dùng chung cờ: autopilot, step1, step2, step3.
- Đã tự rà: không chỗ nào đọc lại chữ "Acting —" / "camera track" từ prompt (prompt_formula đọc `performance` từ data; `_CAM_MOVE`
  nhận "camera tracks"); ước tính độ dài nhóm (cost) gọi cùng shot_motion nên tự tính phần chữ dài thêm (~+70 ký tự/shot track).
- CHƯA chạy agent rà riêng (quy ước 7) — phiên chính giao trước khi gộp.

## Đang dở / bước kế
- Chưa gen thật: bật `motion_prose` cho 1 shot chạy (vd #28 shot 1 nháp 480p) đo optical flow so 5,8 / 13,0 trước khi bật mặc định.
- Đổi `seedance.md`/`image.md` làm đổi dấu vân tay D6 → job chưa gửi sẽ gọi lại Claude (≤ MAX_CALLS_PER_JOB=2) — tốn 1 lượt/shot.
- Chưa làm: động cơ (`performance.motive`, đang tiếng Việt) vào bản code ghép — cần dịch qua motion_en (claude_tasks.translate_motion_fields).
- Ảnh khung đầu code ghép vẫn có mâu thuẫn "small in the distance" (blocking) ↔ "56 % khung, never bigger" (đo 3D) — chỉ ghi vào image.md.
- Shot 5 #28: end_state "head turned into three-quarter profile" ↔ câu "face is never seen" — mâu thuẫn sẵn có, chưa sửa.
