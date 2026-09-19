# Ghi chú nghiên cứu: nguyên tắc rút ra từ các nguồn (diễn đạt lại, v0.1)

Nguồn ở `knowledge/sources.md`. Mỗi nguyên tắc ghi nguồn gốc để truy lại; đây là tri thức để nạp vào Director, không phải bản sao nội dung.

## A. Cách tổ chức phân tích kịch bản (Bước 1)
1. **Đi từ tổng quan xuống chi tiết** (Dramatron, MovieAgent): chốt logline/ý chính → nhân vật → địa điểm → cảnh → shot. Các bước sau dùng kết quả bước trước làm ràng buộc, nên ít mâu thuẫn hơn.
2. **Tách 3 việc song song rồi hợp nhất** (OpenStory): ranh giới cảnh, "bible" (nhân vật/địa điểm/đạo cụ) và danh sách shot; mỗi phần độc lập nhưng tham chiếu cùng mã cảnh.
3. **Cảnh phải có công thức trước khi viết prompt** (visual-skills): ai muốn gì (desire), điều cản trở (obstacle), bố cục không gian, tiêu điểm hình ảnh, thời lượng. Cảnh không đổi gì thì cân nhắc cắt.
4. **Mỗi shot có ít nhất một trong 3 việc**: đổi cảm xúc, thúc đẩy cốt truyện, hoặc tăng căng thẳng. Shot chỉ để trang trí thì bỏ.
5. **Ba chi tiết cho mỗi shot** (visual-skills): áp lực môi trường (gió, mưa, đám đông), một vi hành động của cơ thể (siết tay, nuốt khan), một điểm neo âm thanh/hình ảnh.
6. **Ngân hàng tham chiếu nhân vật** (MovieAgent, PenShot): giữ một bản mô tả bất biến (và ảnh tham chiếu khi có) cho mỗi nhân vật; mọi prompt lấy lại đúng bản đó. PenShot thêm trí nhớ phân tầng để tránh đổi trang phục giữa các đoạn.
7. **Truy vết hai chiều** (PenShot): mỗi shot/prompt liên kết ngược tới đoạn kịch bản gốc để dễ kiểm tra khi có lỗi.

## B. Viết image/video prompt
8. **Cụ thể hơn tính từ** (visual-skills, ai-shortfilm-prompts): thay "cinematic, beautiful" bằng sự kiện vật lý cụ thể (bụi, mưa, chất liệu, hướng sáng). Tránh từ khen rỗng.
9. **Khung 5 tầng** (ai-shortfilm-prompts): chủ đề/phong cách → nhân vật và môi trường → không khí hình ảnh và màu → chuyển động camera → nhịp/thời gian theo shot.
10. **Nêu cả khuyết điểm có chủ ý** (ai-shortfilm-prompts): vết mòn, bất đối xứng làm ảnh bớt "nhựa".
11. **Camera có lý do** (visual-skills): mỗi chuyển động camera trả lời "điều gì vừa thay đổi?". Không di chuyển camera chỉ để có chuyển động.
12. **Kết cảnh yên lặng, có điểm neo hình ảnh** cuối (visual-skills, ai-shortfilm-prompts): tránh kết bằng nổ lớn hoặc thoại.
13. **Motion prompt dựa trên ảnh đã render** (OpenStory): mô tả chuyển động dựa vào tư thế thực trong ảnh đã duyệt, không đoán từ văn bản; vì vậy Bước 3 luôn nhìn ảnh.
14. **Chia thời lượng theo khả năng model** (PenShot, ai-shortfilm-prompts): clip ngắn một hành động; cảnh dài chia nhiều shot có timing.
15. **Cú pháp phủ định khác nhau theo model** (ai-shortfilm-prompts): một số model không hiểu "no X" trong prompt chính và cần ô negative prompt riêng. *Cần kiểm tra với từng model qua Clip AI trước khi khóa.*
16. **Thử bộ lọc IP theo từng model** (ai-shortfilm-prompts): mỗi model có bộ lọc khác nhau; dùng log `content_moderation_failures` để xây blocklist theo model.

## C. Từ vựng chuẩn để chấm và đối chiếu (ShotBench, 8 chiều)
| Chiều | Ý nghĩa | Ví dụ giá trị |
|---|---|---|
| Shot size | phạm vi khung hình | extreme wide, wide, medium, close-up, extreme close-up |
| Shot framing | vị trí/cân bằng chủ thể trong khung | centered, rule of thirds, over-the-shoulder, two-shot |
| Camera angle | góc nhìn | low, eye-level, high, dutch, overhead |
| Lens size | tiêu cự → độ sâu, méo | wide (24mm), normal (35–50mm), telephoto (85mm+) |
| Lighting type | vai trò nguồn sáng | key, fill, back/rim, practical |
| Lighting condition | môi trường sáng | sunrise, overcast, night, low-key, high-key |
| Composition | bố cục hình ảnh | leading lines, symmetry, depth layers, negative space |
| Camera movement | chuyển động | static, pan, tilt, dolly/push-in, tracking, orbit, crane, handheld |

Dùng 8 chiều này khi viết `shot`/`lighting`, khi QC Agent chấm `composition`, và khi người duyệt góp ý (nói rõ "sai chiều nào").

## D. Điều không nên làm theo (bài học)
- Đừng để AI thay hoàn toàn phán đoán sáng tạo (Dramatron: người viết thấy cấu trúc cứng đôi khi gò bó → dùng như khung, người duyệt quyết định).
- Đừng tin số sao của repo về prompt video: đối chiếu bằng bộ đánh giá của dự án.
