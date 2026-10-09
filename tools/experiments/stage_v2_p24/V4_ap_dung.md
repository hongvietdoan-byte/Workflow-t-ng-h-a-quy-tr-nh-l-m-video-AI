# V4 — #24: góc máy đã duyệt (9/9 đạt) → áp vào kịch bản (CHƯA áp, chờ người dùng duyệt báo giá)

Nguồn: `data/projects/24/stage_v2/v2.json` (bản tay đã qua 4 quyết định của người dùng 09/10). Tọa độ so với O (plaza_front), +y Bắc.

| shot | ý đồ | máy (ô · cao · pitch · hướng · ống) | chuyển động → câu cho prompt video | thứ chính thấy % |
|---|---|---|---|---|
| 1 | mở cảnh: Kelly tiến về giếng giữa quảng trường (tháp có hay không đều được — người dùng 09 | L8 · 1.28 m · -5° · 338° · 24 mm | máy tĩnh | kelly 92.9, gieng 93.3 |
| 2 | nhìn ngang phía Đông, máy cao cúi: Kelly ở mép giếng cúi nhìn vào lòng giếng (thấy nghiêng | L12 · 1.78 m · -21° · 246° · 24 mm | máy tĩnh | kelly 92.9, gieng 53.3 |
| 3 | qua vai phải Kelly nhìn xuống miệng giếng (bóng lướt qua); vai Kelly che một phần giếng là | K10 · 1.78 m · -20° · 325° · 35 mm | máy tĩnh | kelly 85.7, gieng 33.3 |
| 4 | sau lưng-chéo Kelly ngã ngửa, máy thấp sát lưng cô, giếng sừng sững phía trước (người dùng | L9 · 0.6 m · 1° · 326° · 24 mm | máy tĩnh | kelly 92.9, gieng 100 |
| 5 | ref emote: máy sát đất trước giếng, yêu nữ thò tay bám mép gần miệng giếng, nhô đầu lên nh | J11 · 0.5 m · 22° · 350° · 24 mm | máy tĩnh | yeunu 78.6, gieng 53.3 |
| 6 | góc nhìn Kelly ngồi bệt: yêu nữ trườn qua thành giếng bò về phía cô; Kelly sợ bò lùi → máy | K10 · 0.93 m · -24° · 350° · 24 mm | POV of Kelly (eye height 0.93 m), camera slowly dollies back 1.0 m, slight handheld shake as if crawling backward | yeunu 75 |
| 7 | góc nhìn Kelly (đã lùi 1 m) ngước lên: yêu nữ đứng dậy trước giếng; Kelly tiếp tục bò lùi  | K9 · 0.93 m · 5° · 350° · 24 mm | POV of Kelly (eye height 0.93 m), camera slowly dollies back 1.0 m, slight handheld shake as if crawling backward | yeunu 92.9 |
| 8 | cận yêu nữ quỳ ôm mặt khóc — bỏ mốc cho gọn khung | K11 · 1.12 m · -7° · 320° · 50 mm | máy tĩnh | yeunu 74.1 |
| 9 | toàn cảnh cuối hơi cao phía Đông: Kelly nhỏ ngồi bên trái, yêu nữ quỳ bên phải trước giếng | L11 · 1.68 m · -36° · 271° · 24 mm | máy tĩnh | kelly 89.3, yeunu 92.9 |

**Áp gồm (0 USD, sau cờ, RÀ KỸ vì đổi cache nền mọi dự án):** (1) `plate_camera` nhận camera từ `setups.json` (thay `camera_for`) → render lại nền 3D 9 shot (Blender, 0 USD);
(2) sửa `blocking`/`action` shot 4–7 theo nhịp mới (Kelly ngã ngửa xa giếng; yêu nữ bám mép gần → bò ra → đứng trước giếng); (3) câu chuyển động shot 6–7 vào motion prompt.
**Báo giá vẽ lại 9 ảnh khung đầu:** ≈ 0,47 USD (gpt-image-2.5, 0,052 USD/ảnh) + QC; xấu nhất (tự vẽ lại ≤ 3/ảnh) ≈ 1,9 USD. Video: báo giá riêng sau khi duyệt ảnh.
