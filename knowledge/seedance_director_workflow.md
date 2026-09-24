# Seedance — quy trình tối ưu prompt theo "Seedance Director" (bổ sung)

Nguồn: kỹ năng "Seedance Director — Prompt Optimization Skill" 1.0, cập nhật theo bản 1.0.2 ngày 2026-09-24 (chắt lọc, bổ sung cho `seedance_prompting.md`, không thay thế). Chỉ dùng khi video model là Seedance. Mục tiêu: làm cảnh **thực thi được** mà không đổi ý tác giả.

**Nguyên tắc gốc:** tối ưu cách thực thi, không tối ưu ý định. Không được: thêm cú ngoặt cốt truyện, đổi quan hệ nhân vật, thêm nhân vật/lời thoại/đạo cụ lớn không cần thiết, đổi thể loại, đổi kết. Thiếu chi tiết bắt buộc thì suy luận **nhỏ nhất** đủ để cảnh mạch lạc; nếu suy luận làm đổi nghĩa thì giữ nguyên sự mơ hồ.

## Các bước kiểm (làm trong đầu, không in ra)
1. **Khóa ý định:** sự kiện, quan hệ, thể loại, giọng, phong cách, lời thoại quan trọng, đạo cụ, hành động bắt buộc, trạng thái kết thúc, ràng buộc của người dùng. Không sửa những thứ này trừ khi tự mâu thuẫn.
2. **Nhãn thực thể:** gán C1, C2 (người), P1 (đạo cụ), V1 (xe)...; giữ nguyên cách đặt tên/đánh số của người dùng. Không đặt nhãn cho vật phụ.
3. **Vai trò tham chiếu:** nói rõ mỗi ảnh/video/audio tham chiếu điều khiển cái gì (danh tính, trang phục, bối cảnh, chuyển động máy, nhịp). Đừng cho rằng một ảnh điều khiển mọi thứ. Không bịa tham chiếu không có.
4. **Nhất quán nhân vật:** chỉ nêu thuộc tính cần cho liên tục (danh tính, tóc, trang phục, vị trí, vật đang cầm, trạng thái thương tích). Mô tả một lần, sau đó chỉ ghi thay đổi. (Trong pipeline này ảnh khung đầu đã cố định ngoại hình.)
5. **Dàn vị trí (blocking) trước máy quay:** vị trí đầu, hướng nhìn, khoảng cách, tiền/trung/hậu cảnh, đường di chuyển, điểm tương tác, vào/ra cảnh. Bắt buộc khi có từ 3 nhân vật quan trọng. Sửa: hướng nhìn bất khả thi, đổi chỗ không lý do, dịch chuyển tức thời, nhân vật che tầm nhìn cần thiết của máy.
6. **Cảm xúc → hành vi nhìn thấy được:** "C1 hồi hộp" không thực thi được; viết "C1 siết quai túi bằng cả hai tay, liếc ra cửa, rồi nhìn lại C2 trước khi đáp". Chỉ 1–2 hành vi dễ đọc, không xếp chồng vi biểu cảm.
7. **Đạo cụ có chủ:** ai sở hữu, ai cầm, bắt đầu ở đâu, đổi tay lúc nào, kết thúc ở đâu ("C1 giữ điện thoại ở tay phải đến giây 12 rồi úp xuống bàn; C2 không chạm vào"). Đặc biệt: điện thoại, vũ khí, túi, sản phẩm, giấy tờ, chìa khóa, đồ ăn, dụng cụ, xe.
8. **Nhân quả liền mạch:** C1 thấy C2 → C1 dừng bước → C2 nhận ra khoảng dừng → C2 quay lại. Dùng chuỗi có thứ tự, đừng liệt kê hành động rời rạc hay viết những việc phụ thuộc nhau như xảy ra đồng thời.
9. **Logic máy quay:** mỗi nhịp máy xác định: cỡ cảnh, chủ thể, vị trí máy, chuyển động, lý do đổi cảnh. Bỏ các cụm rỗng ("máy quay điện ảnh", "cảnh quay tuyệt đẹp") nếu không kèm chỉ dẫn vật lý cụ thể.
10. **Mốc thời gian theo nhịp kịch tính**, không chia đều máy móc ([0–4s] thiết lập, [4–9s] tương tác, [9–14s] phản ứng...). Cảnh đơn giản dùng ít mốc; mỗi mốc phải là một thay đổi có nghĩa, không có mốc rỗng.
11. **Kiểm mật độ hành động:** Seedance dễ bất ổn khi quá nhiều việc xảy ra cùng lúc (hành động nhiều người, máy, thoại, đạo cụ, môi trường, hiệu ứng, vi biểu cảm). Nếu dày: giữ hành động chính, đơn giản hóa nhân vật phụ, giảm vi biểu cảm, bớt chuyển động máy, xếp thành chuỗi thay vì chồng, tách hành động dài thành nhịp rõ. Không đổi câu chuyện để giảm độ phức tạp.
12. **Gỡ mơ hồ:** ai làm, vật nào, ai sở hữu, ai đang nói, ở đâu, trước hay sau, tham chiếu điều khiển gì. Hai thực thể cùng khớp đại từ thì dùng tên/nhãn.
13. **Kiểm soát ảo giác chỉ ở chỗ dễ hỏng:** không nhân đôi nhân vật, không thừa chi, không đổi trang phục, không đổi chủ đạo cụ, không thêm người, không đổi thiết kế sản phẩm/bố cục môi trường, không biến một cảnh liền thành chia đôi màn hình, không bịa thoại/hành động. **Không dán một danh sách phủ định chung chung** vào mọi prompt.

## Khi cảnh quá phức tạp cho một lần tạo
Đừng lặng lẽ xóa nội dung. Giữ mục tiêu và mọi hành động quan trọng, giảm hành vi phụ, giản lược máy, giảm chuyển động đồng thời; chỉ khi bắt buộc mới đề xuất tách thành các clip. Mỗi clip tự đứng được: **nêu lại trạng thái đầu** ("Đầu clip này C1 đã đứng cạnh cửa lớp, quay mặt về phía C2"), không viết "tiếp tục clip trước".

## Lời thoại
Giữ nguyên lời thoại của người dùng, luôn nêu rõ ai nói; nhiều người thì gắn nhãn theo nhân vật. Chỉ chỉnh lời khi người dùng yêu cầu.

## Hình thức đầu ra ưa dùng (khi làm rõ được)
VIDEO (tỉ lệ, độ dài, phong cách) → THAM CHIẾU → NHÂN VẬT/CHỦ THỂ → BỐI CẢNH → DÀN VỊ TRÍ → NGUYÊN TẮC MÁY & DIỄN XUẤT → TIMELINE ([0–Xs] Camera / Action / Performance / Dialogue / Sound) → LIÊN TỤC → TRÁNH (chỉ rủi ro thật). Không phải cảnh nào cũng cần đủ mọi mục; cảnh đơn giản chỉ cần một đoạn văn. Viết bằng ngôn ngữ của người dùng, câu trực tiếp kiểu sản xuất ("C1 quay sang C2 và bước tới một bước"), rõ hơn là văn hoa.

## Ảnh tham chiếu: mỗi ảnh MỘT vai trò (bản 1.0.2 — "reverse asset planning")
Áp dụng cho mọi ảnh gửi kèm (Seedance, cả ảnh tham chiếu Deepix ở bước ảnh):
- **Chỉ dùng ảnh tham chiếu khi nó chặn một rủi ro thật:** danh tính nhân vật chính/lặp lại, bối cảnh có bố cục ảnh hưởng dàn vị trí, đạo cụ/xe quan trọng cho liên tục, phong cách không tả nổi bằng chữ, trạng thái đầu phải khớp giữa các clip tách rời. Không làm ảnh cho vật phụ, bối cảnh chung chung, người qua đường.
- **Mỗi ảnh một vai trò chính, nói rõ nó điều khiển gì và KHÔNG điều khiển gì:** ảnh nhân vật = mặt, tóc, tỉ lệ cơ thể, trang phục — không điều khiển bố cục/góc máy; ảnh bối cảnh = kiến trúc, bố trí, lối vào ra — không điều khiển người, cỡ cảnh; ảnh phong cách = cách render, màu, chất liệu, ánh sáng — **không** được đè lên danh tính, trang phục, hình học cảnh. Khi vai trò có thể chồng nhau, nói rõ ảnh nào thắng (danh tính → ảnh nhân vật, bố cục → ảnh bối cảnh, render → ảnh phong cách).
- **Ảnh tham chiếu tốt:** nhân vật — một người, mặt không bị che, kiểu tóc/bóng dáng đọc rõ, đúng trang phục liên tục, toàn thân hoặc 3/4, sáng đều, nền đơn giản; không ghép nhiều ảnh, không người lạ, không nhòe chuyển động. Bối cảnh — cảnh rộng sạch **từ một hướng hữu ích**, không có nhân vật chính, không cài sẵn đường máy hay sự kiện.
- **Gắn nhãn thống nhất:** khối "REFERENCE ASSETS" ở đầu prompt (`@image1: C1 identity, face, hairstyle, proportions, and wardrobe only`); mọi nhãn trong danh sách phải xuất hiện trong prompt và ngược lại; không có nhãn mồ côi.
- **Nhiều clip tách rời:** dùng lại cùng bộ ảnh ổn định và nêu lại trạng thái đầu từng clip; thay đổi ngoại hình vĩnh viễn giữa hai clip → ảnh "trạng thái đầu" mới, ghi rõ, không lặng lẽ thay ảnh danh tính gốc.
- Liên hệ GĐ6: ảnh layout (nền chụp từ trên cao + hình cắt tí hon) được gửi làm ảnh số 1 mà không giới hạn vai trò → nó điều khiển luôn cỡ cảnh và tỉ lệ (R7). Theo nguyên tắc trên, layout chỉ được điều khiển vị trí tương đối, không điều khiển cỡ người/cỡ cảnh (xem F7).
