# QC đồng bộ cả bộ ảnh (game-asset-set-generator skill — "Three-Layer QA" + "Style Fingerprint", chắt lọc cho cảnh phim)
Dùng cho nút "🎨 Kiểm tra đồng bộ cả bộ ảnh": Claude nhìn MỘT tấm ghép các ảnh đã duyệt của dự án (theo thứ tự cảnh).

## Dấu vân phong cách (so mọi ảnh với nhau và với World Bible)
Chất liệu render (ảnh thật, 3D điện ảnh, vẽ tay, cel-shading…) · ngôn ngữ hình khối (tròn/góc cạnh, tỉ lệ thật/cường điệu) · bảng màu và độ sáng (tông chủ đạo, ấm/lạnh, bão hòa, tương phản, màu cấm) · phản ứng chất liệu (kim loại sơn, vải, nhựa, năng lượng) · ánh sáng (hướng, độ mềm, nhiệt độ màu, viền sáng, bóng đổ) · máy (góc, cảm giác ống kính) · viền và mật độ chi tiết · mood.

## Ba lớp kiểm
1. **Trung thành tham chiếu:** ảnh có cùng chất liệu render và độ hoàn thiện với ảnh tham chiếu/World Bible? Hình khối và tỉ lệ được chuyển sang, không bị thay bằng "tả thực chung chung"? Màu, ánh sáng, mood khớp?
2. **Đồng bộ cả bộ:** mọi ảnh trông như cùng một phim? Quy tắc góc máy/phối cảnh nhất quán trong một nhóm cảnh? Bảng màu và dải sáng nằm trong World Bible? Chất liệu cùng một logic? Mật độ chi tiết tương đương giữa các cảnh cùng tầm quan trọng? Ánh sáng giữa các cảnh cùng địa điểm/giờ có liên tục?
3. **Dùng được:** có chữ lạ, logo giả, watermark, người thừa, đạo cụ thừa? Cảnh nào cần gen lại?

Ảnh đẹp nhưng lạc phong cách so với cả bộ = ngoại lệ → đề xuất gen lại ĐÚNG ảnh đó, giữ nguyên các ảnh đạt.
