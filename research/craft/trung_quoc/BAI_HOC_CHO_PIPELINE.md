# Bài học cho pipeline — từ nguồn tiếng Trung (S phiên 2026-09-29)

> Tối đa 15 bài học, mỗi bài gắn **mức bằng chứng** (cao/vừa/thấp, theo độ tin nguồn ở `NGUON_TQ.md`) + **nguồn**. Đây là gợi ý
> (tầng 4 theo `PHUONG_PHAP_PHAN_TICH.md`) — cần đối chiếu thêm với cách ClipAI/Seedance đã xác nhận trước khi đổi code.

## Prompt / kỹ thuật sinh (Director, DP)

1. **Chọn cách viết mốc thời gian theo đúng model đang gọi**: "Shot N" cho Seedance 2.0/Fast, mốc giây nguyên số liên tục
   cho Seedance 2.5 — không trộn lẫn. Đây chính là nguyên nhân lỗi 1.5 (trôi hành động) đã ghi trong
   `docs/CAP_NHAT_CLIPAI_2026-09-28.md`; nguồn tiếng Trung [1] xác nhận lại chi tiết cách viết mốc giây liên tục, không nhảy
   cóc. **Bằng chứng: cao** (tài liệu chính thức Volcengine, đọc trọn văn). Áp dụng: prompt DP/mẫu Shot.
2. **Chỉ định vai trò từng tư liệu tham chiếu tường minh khi có ≥2 chủ thể**, kèm số thứ tự đúng theo lượt xuất hiện lần đầu
   của nhân vật — lệch thứ tự dễ khiến AI gán nhầm nhân vật. **Bằng chứng: cao** (tài liệu chính thức [1], khớp với quan sát
   độc lập của nguồn cộng đồng [14]). Áp dụng: mẫu prompt Seedance trong `core/adapters` (S4.9 đã có ý tương tự, bổ sung thêm
   yêu cầu thứ tự xuất hiện lần đầu).
3. **Ưu tiên mô tả hành động khái quát, chỉ chi tiết hoá 1–2 điểm nhấn**, tránh liệt kê nhiều động tác nhỏ trong 1 shot ngắn
   — nguyên nhân trực tiếp của lỗi "nhồi 3–4 hành động vào ≤15s" ở dự án #8. **Bằng chứng: cao** ([1], chính thức). Áp dụng:
   hướng dẫn viết prompt cho DP/Director.
4. **Tránh cảm xúc mô tả cực đoan ("cuồng nhiệt", "cực sốc") — đổi sang từ nhẹ hơn ("kinh ngạc")** để giảm lỗi mắt phát sáng
   bất thường; đặt câu ràng buộc "mắt người bình thường, không phát sáng" ở vị trí ưu tiên cao trong prompt khi cảnh có cảm
   xúc mạnh (cận mặt, phản转). **Bằng chứng: cao** ([1], có case ảnh trước/sau minh hoạ). Áp dụng: mẫu prompt cận mặt/cảm xúc.
5. **Kiểm soát nhạc/phụ đề bằng phủ định phải liệt kê hết từ đồng nghĩa và lặp ở cả đầu lẫn cuối prompt** (vd với "không
   nhạc nền": liệt kê nhạc/BGM/phối nhạc/nhạc cụ/giai điệu…); và tách thoại theo khuôn "nhân vật thoại (cảm xúc): nội dung"
   để giảm khả năng model tự sinh phụ đề dư. **Bằng chứng: cao** ([1]). Áp dụng: prompt Seed Audio / Seedance có thoại tiếng
   Việt (liên quan lỗi 1.7, 1.8 trong TODO).
6. **Với tác vụ phức tạp (nhiều loại tham chiếu + biên tập + hiệu ứng cùng lúc), tách thành nhiều lần sinh đơn giản rồi ghép
   ở hậu kỳ**, thay vì cố gộp 1 lần gọi — tài liệu chính thức khuyến cáo trực tiếp và có ví dụ minh hoạ lỗi khi gộp. **Bằng
   chứng: cao** ([1]). Áp dụng: quy tắc chung khi viết prompt cho cảnh khó (ví dụ cảnh tháp FF, khớp môi + hiệu ứng).
7. **Giảm độ phân giải ảnh tham chiếu xuống ngang hoặc dưới độ phân giải output** để giảm lỗi vân "vân tay"/nhiễu texture ở
   vùng cỏ/lá/chi tiết dày. **Bằng chứng: cao** ([1], có case cụ thể). Áp dụng: bước chuẩn bị ảnh tham chiếu trước khi gửi
   Seedance.

## Nhất quán nhân vật/cảnh

8. **Cân nhắc chuẩn bị "thẻ hồ sơ nhân vật" gộp mô tả văn bản + nhiều góc ảnh (chính diện/bán thân 2 bên/cận trang phục/cận
   mặt, nền trắng thuần) làm ảnh tham chiếu chính**, thay vì chỉ 1 ảnh mặt — cách này khớp về nguyên lý với khuyến nghị chính
   thức [1] mục tham chiếu đa góc của Seedance 2.5. **Bằng chứng: vừa** (nguồn cộng đồng [14], nhưng khớp nguyên lý với nguồn
   chính thức [1]). Áp dụng: có thể thử cho nhân vật Kelly/Kenta/Maxim, đối chiếu với kho chủ thể ClipAI hiện có — **không
   thay thế kho chủ thể chính thức**, chỉ là gợi ý bổ sung nội dung ảnh đưa vào kho.
9. **Chuẩn bị trước bố cục không gian cảnh (ảnh top-down + bộ nhiều góc giữ nguyên kết cấu) trước khi sinh video nhiều góc
   máy của cùng 1 cảnh**, để tránh AI "tưởng tượng lại" không gian mỗi lần đổi góc. **Bằng chứng: vừa** (nguồn cộng đồng
   [14], chưa kiểm chứng độc lập). Áp dụng: cân nhắc cho cảnh lặp lại nhiều góc (ví dụ quảng trường tháp FF).

## Quy trình / QC

10. **Chuẩn bị kho tài sản nhân vật/cảnh trước khi vào bước sinh video hàng loạt** — nhiều nguồn độc lập (chính thức [1] +
    thực chiến [7][14]) đều đặt bước này sớm, coi là nguyên nhân chính giảm số lần sinh lại. **Bằng chứng: cao** (đồng thuận
    2 nguồn độc lập trở lên). Áp dụng: đã đúng hướng với quyết định dùng kho chủ thể ClipAI (S4.7); củng cố thêm ưu tiên làm
    trước, không làm song song/làm sau.
11. **QC theo từng shot trước khi render hàng loạt (preview → sửa mô tả lỗi → sinh lại đúng shot đó)**, tránh render lại cả
    mẻ khi chỉ 1 shot lỗi. **Bằng chứng: vừa** (kinh nghiệm cá nhân [8], hợp lý về logic chi phí). Áp dụng: quy trình review
    trước khi batch render trong dashboard.
12. **Theo dõi ROI/chi phí quảng cáo (buy volume) tách biệt khỏi chi phí sản xuất khi đánh giá hiệu quả** — nguồn kinh tế
    độc lập [6] cho thấy hạ chi phí sản xuất không tự động tạo ra lãi; phần lớn đội đầu ngành TQ cũng chỉ ~20% có lãi dù chi
    phí đã giảm 10 lần. **Bằng chứng: cao** (báo kinh tế, phỏng vấn nhiều bên, có số liệu ROI cụ thể). Áp dụng: không dùng
    "chi phí sản xuất rẻ hơn" làm thước đo thành công duy nhất khi báo cáo cho người dùng.

## Nội dung / kịch bản

13. **Với thể loại short drama dọc phát nhanh, cân nhắc thiết kế hook cuối mỗi đoạn/tập và đổi nhịp ở điểm phản转** — nhưng
    chỉ áp dụng khi định dạng ra là short drama dọc trả phí theo tập; **không áp** "mở đầu = cao trào ngay" như luật cứng cho
    MV hay phim ngắn khác của dự án (theo đúng nguyên tắc "tách clip này làm khỏi nên làm" ở `PHUONG_PHAP_PHAN_TICH.md`).
    **Bằng chứng: vừa** (nguồn tổng hợp/blogger, chưa có số liệu A/B test độc lập). Áp dụng: chỉ khi làm nội dung dạng short
    drama dọc trả phí, không áp cho MV/phim ngắn hiện tại của dự án.

## Nhạc nền (bổ sung theo yêu cầu 2026-09-29)

14. **Đổi playlist/phong cách nhạc theo giai đoạn cảm xúc trong cùng 1 cảnh/tập (mở đầu bí ẩn → căng thẳng dồn nén → nhịp
    nhanh lúc "sướng" → nghi vấn cuối), không dùng 1 nhạc nền cố định suốt cả cảnh dài theo kiểu gán cứng cho thể loại** —
    nhạc là công cụ dẫn nhịp cắt (đổi track = tín hiệu chuyển đoạn/phản转) và kéo cảm xúc, không phải nền âm cho có. Ánh xạ
    thể loại↔nhạc cụ ở `NHAC_NEN.md` mục 2 chỉ là ví dụ minh hoạ (nguồn thương mại), cần điều chỉnh theo từng cảnh cụ thể của
    dự án chứ không copy nguyên bảng. **Bằng chứng: vừa** (nguồn tổ chức bán nhạc [16], có thể thiên lệch bán hàng, nhưng
    logic "nhạc dẫn nhịp cắt" khớp với nguồn craft tiếng Anh đã có — mục "External rhythm" và cắt theo cảm xúc của Murch
    trong `research/craft/NGUON.md` #10, #11). Áp dụng: brief nhạc S1.15, cân nhắc chia lệnh Seed Audio theo từng đoạn cảm
    xúc thay vì 1 lệnh cho cả cảnh dài nếu muốn nhạc đổi theo phản转.
15. **Khi dùng công cụ nhạc AI, ghi rõ "instrumental/không lời" cho nhạc nền có thoại đè lên, và dùng cấu trúc prompt ngắn
    "phong cách + nhạc cụ + cảm xúc + tempo"** để tránh model sinh giọng hát chồng lời thoại nhân vật. **Bằng chứng: thấp**
    (nguồn cá nhân mang tính quảng cáo công cụ [17], chỉ lấy phần cấu trúc chung — không khuyến nghị công cụ trong nguồn).
    Áp dụng: kiểm tra khi brief nhạc cho Seed Audio/Eleven Music, đảm bảo không lời khi cảnh có thoại.

## Khoảng trống — chưa đủ căn cứ để thành bài học, cần đọc thêm trước khi áp dụng
- Vai trò/sơ đồ tổ chức đội TQ cụ thể (ai là "prompt engineer", ai duyệt cuối) — chưa có nguồn.
- Cách dùng Kling chính thức (camera language riêng, khác Seedance thế nào) — tài liệu chính thức chưa tải được nội dung.
- Số liệu BPM/âm lượng chính xác theo giai đoạn cảm xúc — mới có 1 ví dụ lẻ, chưa đủ để rút thành quy tắc.
