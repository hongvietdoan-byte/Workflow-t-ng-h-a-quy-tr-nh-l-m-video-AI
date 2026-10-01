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
- 2026-10-01: **Nối API Meshy (code xong, 0 credit).** Lý do: Tổ QC GĐ3 cho thấy Claude không nhận ra trái/phải trong ảnh (đúng ~50 %) →
  mô hình 3D cố định bên của mọi chi tiết, render hướng nào cũng đúng → ảnh chuẩn sau lưng / nghiêng cho shot quay lưng + QC so ảnh cùng
  hướng. Người dùng duyệt: được phép đưa ảnh nhân vật lên Meshy (tài khoản Pro, credit gói tháng), trần đợt **150 USD / 3 nhân vật**, lưu
  `data/models3d/`, có gắn khung xương; mã API người dùng tự `setx MESHY_API_KEY` (không qua chat).
  Tài liệu chính thức đã đọc: quick-start, image/multi-image to 3D, rigging, pricing (3D có texture 30, rig 5 credit; lỗi hoàn credit),
  balance, rate limits (Pro 20 req/s, 10 việc cùng lúc), file giữ 3 ngày. Code: `core/meshy.py` (sổ `meshy_tasks` ghi TRƯỚC khi gửi;
  trần mỗi lần 40 credit, mỗi nhân vật 3 lần dựng, trần đợt USD theo `MESHY_USD_PER_CREDIT` mặc định 0,02; số dư đọc trước khi gửi, không
  đọc được → không gửi; mất kết nối khi gửi → UNKNOWN, tính tiền, không tự gửi lại; tải file ngay khi xong; 4 ảnh render của Meshy →
  hộp chờ duyệt của Kho với vai trò toàn thân / sau lưng / nghiêng), `core/sheet_views.py` (cắt ô TURNAROUND của bảng thiết kế thành 4
  ảnh trước / ¾ / nghiêng / sau, bỏ chữ; hình dính nhau → không đoán), dashboard ⚙ → Kho → **🧍 Nhân vật 3D**, launcher đọc
  `MESHY_API_KEY`. Test `tests/test_meshy.py` 12 (máy chủ giả). Đã xem bằng mắt: cắt Kelly + Maxim sạch; khung chạy trên dashboard demo.
  **Bảng thiết kế trong Kho:** Kelly khớp hồ sơ → dùng được; Maxim áo da đen ≠ hồ sơ (bạc xám — người dùng: hồ sơ đúng) → cần bảng mới;
  Kenta là ngoại hình cũ trước OB55 (bị cấm) → người dùng gửi thêm ảnh, Deepix vẽ bảng xoay OB55 (việc còn từ 24/09). Ảnh cắt từ bảng
  1536×1024 chỉ ≈ 160×420 px/hình — bảng mới nên vẽ riêng 4 hình, ảnh lớn.
- 2026-10-01 (tiếp): **Người dùng gửi ảnh in-game nhiều góc** → không cần Deepix vẽ bảng: Maxim (trước / nghiêng / sau — áo da bạc xám đúng
  hồ sơ; lưng áo có hình mũ bảo hiểm xanh nứt, mặt trước mũ có logo sao — hồ sơ chưa ghi, chờ người dùng quyết có thêm không), Kenta OB55
  (trước / nghiêng trái / sau / nghiêng phải — găng giáp + sao bên TRÁI, băng + găng hở ngón bên PHẢI, khớp hồ sơ), **Wolfrahh đồ trắng**
  (skin — biến thể "đồ trắng (in-game)" của #59, hồ sơ #59 chưa có; quần trắng in cánh đen: chân TRÁI cánh ở đùi, chân PHẢI cánh ở cẳng).
  Đã cắt bỏ huy hiệu "Lv. / Phần Thưởng", đưa vào Kho **chờ duyệt** (vai trò toàn thân / nghiêng / sau, nhóm biến thể riêng). Meshy chọn
  ảnh theo thứ tự: bộ ảnh Kho đã duyệt cùng một nhóm (trước + nghiêng/sau, ≤ 4, mặt trước đầu) → cắt bảng → 1 ảnh chính diện; câu texture
  người tự viết được (skin hồ sơ chưa tả) — khi đó không cần hồ sơ duyệt.
- 2026-10-01 (chạy thật, người dùng yêu cầu tự động hết): **4 nhân vật có mô hình 3D + khung xương** trong `data/models3d/` — Kelly (cắt
  bảng #25), Maxim (3 ảnh in-game), Kenta OB55 (4 ảnh in-game), Wolfrahh đồ trắng (4 ảnh in-game, câu texture tự viết). Tổng **215 credit**
  (dựng 30 × 5 lần, giảm lưới 5 × 5, gắn khung xương 5 × 6, tô lại 10), còn 1 285. Bài học: (1) mô hình Meshy ra 1,0–1,8 triệu mặt → gắn
  khung xương bị từ chối (≤ 320 000) → phải **giảm lưới (150 000) trước**; (2) Meshy chỉ trả 1 ảnh mặt trước → render 6 hướng bằng Blender
  trên máy (`tools/render_character_views.py`, 0 credit) để kiểm và làm ảnh chuẩn; (3) **câu texture có chữ LEFT/RIGHT làm Meshy lẫn bên** —
  Kenta lần 1: băng vải tay phải thành giáp; **tô lại texture không sửa được hình khối** (còn làm găng tay trái thành hở ngón) → dựng lại với
  câu KHÔNG có chữ trái/phải ("một cẳng tay quấn băng… tay kia găng giáp…", để ảnh quyết bên) → đúng. Kiểm bằng render: chi tiết hai bên
  đúng bên ở cả 4 (Maxim thiếu hình lưng áo — hồ sơ chưa ghi). 24 ảnh render 6 hướng (Kenta bản v2) đã vào Kho **đã duyệt** (người dùng);
  4 ảnh mặt trước Meshy tự tạo ("3D Meshy") để chờ duyệt (thừa).
