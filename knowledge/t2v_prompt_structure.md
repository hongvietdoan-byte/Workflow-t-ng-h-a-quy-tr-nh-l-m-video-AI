# Cấu trúc prompt cho model tạo video (World Bible + khung 7 đoạn)

Nguồn: AI Film Direction & Prompt Workflow Kit 1.0.0 (text-to-video-prompt, chắt lọc). Dùng cho bước Motion prompt và để giữ nhất quán giữa các cảnh.

**Ý chính:** model tạo video không cần viết tắt kiểu "MS / eye_level / dolly_in"; nó cần **một thế giới vật lý có thể dựng lại trong đầu**. Cái làm video "không giống AI" là manh mối vật lý và chất liệu thật, không phải tính từ. "Một chiến binh rất ngầu" ra nhân vật nhựa; "giáp mảnh sơn mài, dây lụa thấm nước sậm màu, khe kim loại có vết xước và vết nước, bước đi thấy sức nặng" ra nhân vật đáng tin.

## Tầng 1 — World Bible (khóa nhất quán, dùng chung cả dự án)
AI video hay **trôi giữa các cảnh** (ánh sáng, tông màu, chất liệu mỗi cảnh một kiểu). Cách chữa: khóa một bộ tham số dùng chung, mọi cảnh kế thừa (không chép lại nguyên văn nhưng không được mâu thuẫn):
- **palette:** màu chủ đạo + màu điểm nhấn + phủ định rõ (vd "xanh đô thị lạnh và xám nhạt là chủ đạo, đỏ đèn phanh làm điểm nhấn; no bloom, no artificial glow").
- **lighting_logic:** ánh sáng **đến từ đâu** và cư xử thế nào; gọi tên theo **nguồn sáng**, không theo cảm xúc ("chỉ đèn natri đường phố, đèn pha xe, đèn giao thông chớp; mưa giảm tầm nhìn").
- **era_lore:** ràng buộc thời đại/thế giới để không lệch thời.
- **physics:** trọng lực, thời tiết, cách vật liệu chuyển động.
- **texture_finish:** hạt phim, dải tương phản, chất ống kính (ống thật, không bóng loáng kiểu CGI).
Trong dự án này World Bible của dự án (nếu có) được đưa vào prompt; cảnh nào cũng phải tương thích.

## Tầng 2 — Prompt một cảnh theo 7 đoạn cố định
1. **Thời gian/địa điểm/thời tiết:** một câu khẳng định. (ĐÊM. Ngã tư Manhattan giữa cơn mưa lớn.)
2. **Nguồn sáng:** gọi tên nguồn + hiệu ứng khí quyển (sương, mưa, bụi). Không viết "không khí u ám".
3. **Xử lý màu:** kế thừa palette; nêu phủ định rõ (no bloom / no oversaturation).
4. **Máy quay/vị trí máy:** vị trí, độ cao, tiêu cự tương đương (vd 40mm), độ sâu trường ảnh, hiệu ứng mặt kính (vệt mưa, vệt sáng).
5. **Chủ thể + hành động:** ai, làm gì, theo hướng nào so với máy. **Một hành động liên tục** (model chỉ giỏi một chuyển động chính mỗi lần).
6. **Chất liệu/vật lý:** vật liệu cư xử thế nào (ướt thì sậm màu, cũ thì xước, nặng thì bước chân trầm). **Đoạn này quyết định giống hay không giống AI, không được bỏ.**
7. **Chuyển động môi trường:** thế giới xung quanh chuyển động (dòng xe, nước bắn, tia sáng bất chợt) để cảnh "sống".

**Đổi ký hiệu đạo diễn sang lời cho model:** ECU = cận cực cận, khung đầy [chi tiết]; CU/MCU = cận, mặt/ngực đầy khung; MS = trung cảnh từ eo/đầu gối lên; LS/ELS = toàn/viễn, chủ thể nhỏ trong môi trường; eye_level = máy ngang mắt; low = máy thấp nhìn lên; high/birds_eye = máy cao/nhìn thẳng xuống; dutch = máy nghiêng; dolly_in = máy đẩy chậm vào; dolly_out = máy lùi ra để lộ không gian; tracking = máy chạy ngang bám theo; handheld = rung tay nhẹ, có người cầm; crane_up = máy nâng lên; rack_focus = lấy nét dịch từ tiền cảnh sang hậu cảnh.

**Tiêu cự và cảm xúc:** ~24mm rộng: không gian, khoảng cách phóng đại, môi trường bao lấy chủ thể; 40–50mm: gần mắt người, đáng tin; ~85mm: nén, cô lập chủ thể, thân mật; 135mm+: nén mạnh, cảm giác nhìn trộm, hậu cảnh mờ.

## Quy tắc viết
1. Thì hiện tại, câu khẳng định, dày thông tin; không dùng "sẽ", "có thể".
2. **Tả ánh sáng bằng nguồn, không bằng cảm xúc** ("một bóng đèn natri phía trên" đúng; "ánh sáng đáng sợ" sai).
3. **Một cảnh một hành động liên tục.** Nhiều hành động cùng lúc sẽ nhòe.
4. **Phủ định rõ để bỏ thẩm mỹ mặc định** của model (quầng sáng, bóng loáng CGI, quá bão hòa): no bloom, no artificial glow, no oversaturation.
5. Đoạn chất liệu là bắt buộc.
6. Kế thừa World Bible: tái dùng cùng cách diễn đạt palette/nguồn sáng giữa các cảnh.
7. Seedance 2.0: gói cảnh thành đoạn ≤15 giây, mỗi đoạn tạo một lần; nhất quán giữa các đoạn dựa vào World Bible.

## Tránh
Prompt yếu: "Một chiến binh chạy về phía máy quay trên phố mưa ban đêm. Điện ảnh, kịch tính, chất lượng cao, 4k." — toàn tính từ (cinematic/dramatic/4k gần như không có thông tin), không nguồn sáng, không chất liệu, không vị trí máy, không vật lý.
