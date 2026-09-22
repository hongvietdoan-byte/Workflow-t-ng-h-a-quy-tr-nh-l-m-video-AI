# Nghiên cứu: Previz 3D (Deepix + Blender + Meshy + Clip AI)

**Trạng thái (chốt 2026-09-23): hướng 3 — nghiên cứu dần, dùng trong tương lai.** Không chặn hướng chính (tối ưu ảnh + text, xem `PLAN.md` 3.7). Ghi thêm phát hiện/thử nghiệm vào file này theo ngày.

## Vì sao cần
Mỗi cảnh = 1 ảnh gen độc lập giữ được mặt/trang phục nhưng không giữ được **không gian**: vị trí nhân vật giữa các shot, tỉ lệ người/cảnh, chân chạm đất, độ giống bối cảnh in-game, góc máy mà kho không có ảnh. AI vẽ lại toàn bộ khung hình nên dễ ra nhân vật quá to, đứng lơ lửng, bối cảnh lệch. Previz 3D dựng bố cục bằng hình khối thật trước, AI chỉ vẽ phần hình ảnh.

## Ý tưởng luồng
1. **Map FF 3D → Blender (chạy tự động bằng script, miễn phí):** nhập GLB/FBX, tự tìm mặt đất (raycast), tự kiểm tra đơn vị bằng vật mốc (cửa/xe/container), xuất bản đồ nhìn từ trên + danh sách object/khu vực. Không đánh dấu tay.
2. **Director viết blocking bằng lời** (khu vực, vị trí so với mốc, cỡ cảnh, độ cao camera) → code đặt nhân vật (ma-nơ-canh ~1,75 m hoặc model 3D nhân vật) đúng trên mặt đất + camera theo cỡ cảnh. Vị trí lưu trong 3D → đổi góc máy vẫn nhất quán, shot ngược góc tự đúng.
3. **Render ảnh layout** (màu + độ sâu) → **Deepix** vẽ ảnh cuối từ layout + ảnh nhân vật trong kho (nhận diện/trang phục vẫn từ ảnh + text).
4. **Clip AI:** ảnh cuối làm khung đầu; chuyển động camera/nhân vật render từ Blender làm `reference_video` (Seedance 2.5 nhận white model/blockout làm khung camera).

## Thành phần và nguồn
| Thành phần | Vai trò | Ghi chú |
|---|---|---|
| **Map 3D FF** | Hình khối bối cảnh thật | Map fan dựng trên mạng để thử nội bộ, ví dụ Sketchfab: [Old Bermuda Three 3D Places](https://sketchfab.com/3d-models/free-fire-old-bermuda-three-3d-places-b9689ecf44ee4dac97b788e4e2b2ccca) (~362k tam giác, 3 khu), [Bermuda Remastered (3DKINGFF)](https://sketchfab.com/3d-models/bermuda-remastered-free-fire-8aa9f5f66fad44188369a12dbc6419c7) (~23k tam giác, thô), [Bermuda Remastered untextured](https://sketchfab.com/3d-models/bermuda-remastered-free-fire-untextured-6c119e3cb3204eabbfe32c2f634c0ec2), [The Circuit](https://sketchfab.com/3d-models/free-fire-burmuda-map-the-circuit-3d-model-6897d14634a548f098170032abf3aaef), [CGTrader Bermuda](https://www.cgtrader.com/3d-models/exterior/cityscape/bermuda-map-free-fire-3d-model-blender-free-fire-3d-map-80777880-635d-45b2-a465-2aea258ad751). Bản phát hành cần asset chính thức từ team game. |
| **Model 3D nhân vật FF** | Dáng người/tỉ lệ/tư thế đúng | Người dùng cho rằng có sẵn trên mạng; ưu tiên hơn Meshy vì giống in-game. Không giải quyết được việc thay trang phục (trang phục vẫn làm bằng ảnh + text). |
| **Blender** | Dựng cảnh, đặt nhân vật/camera, render layout/độ sâu/video blockout | Miễn phí, chạy headless bằng Python. Chạy trên máy người dùng (file map/nhân vật để trong `data/`, không lên GitHub). |
| **Meshy (tài khoản Pro có API)** | Rig tự động + 500+ chuyển động/tư thế cho model chưa có rig; tạo 3D từ nhiều ảnh cho nhân vật/đạo cụ không tìm được file | Theo tìm kiếm: Image-to-3D có texture ~30 credit, rig 5, animation 3 (có nguồn nói auto-rig + chuyển động có sẵn miễn phí); Pro 1.000 credit/tháng. Không dựng được cả map. Tải ảnh nhân vật FF lên Meshy = đưa IP Garena lên dịch vụ ngoài bằng tài khoản cá nhân → kiểm tra chính sách công ty; dùng chế độ private. Key trong `MESHY_API_KEY`, không vào repo. [Docs](https://docs.meshy.ai/en), [Rigging API](https://docs.meshy.ai/en/api/rigging-and-animation). |
| **Deepix** | Vẽ ảnh cuối từ layout | **Rủi ro lớn nhất:** API không có tham số khoá bố cục (mask/strength/ControlNet) → phải thử 3–5 ảnh xem có bám layout không. Dự phòng: dán lại vùng bối cảnh gốc ngoài vùng nhân vật. |
| **Clip AI (Seedance 2.5)** | Video từ khung đầu + video blockout | Theo tài liệu: Seedance nhận `reference_video`; Seedance 2.5 quảng bá hỗ trợ white model/blockout. [Blender workflow – Dreamina](https://dreamina.capcut.com/seedance/seedance-2-5-blender-workflow), [plugin Blender/Maya – VP Land](https://www.vp-land.com/stories/dreamina-launches-seedance-2-5-with-30-second-clips-and-maya-and-blender-plugins). |

## Liên quan hướng 2 (Bàn đạo diễn Clip AI)
Bàn đạo diễn nhiều khả năng làm được phần lớn luồng này **từ ảnh** (dựng white model từ 1–3 ảnh bối cảnh) mà không cần map/Blender. Nếu hướng 2 dùng được thì hướng 3 chỉ cần khi cần độ chính xác cao hơn (map in-game thật, tỉ lệ mét thật). Xem `docs/CLIPAI_FEATURES.md`.

## Câu hỏi nghiên cứu còn mở
1. Deepix có bám ảnh layout 3D không (ma-nơ-canh xám vs model nhân vật có texture)?
2. Map fan có đủ chi tiết/đúng đơn vị không; lấy được asset chính thức không?
3. Model nhân vật FF tải về có rig chuẩn người không; Meshy rig có ổn với model FF không?
4. Seedance 2.5 giữ được bố cục blockout từ Blender render bao nhiêu?
5. Công sức thực tế mỗi kịch bản 60 giây so với hướng ảnh + text?

## Thí nghiệm nhỏ đề xuất (khi có thời gian)
1 khu nhỏ của map, 2 nhân vật, 3 shot (toàn cảnh góc cao, trung cảnh ngang mắt, shot ngược góc): Blender render layout → Deepix 3–5 ảnh → so với ảnh + text. Tốn ~5 ảnh Deepix.

## Nhật ký
- 2026-09-23: khởi tạo file từ trao đổi phiên rà soát; chưa thử nghiệm gì. Máy cloud của Claude bị chặn Sketchfab, Meshy docs, Dreamina, BytePlus — phải tải/thử trên máy người dùng.
