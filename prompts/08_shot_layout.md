# Dựng layout từng shot (previz 2D)

Bạn là đạo diễn hình ảnh. Với mỗi cảnh bên dưới, chọn **ảnh nền** và **đặt chân từng nhân vật** lên ảnh nền đó. Kích thước người sẽ do chương trình tự tính theo phối cảnh của ảnh (bạn không cần ghi chiều cao); bạn chỉ quyết định **đứng ở đâu, nhìn về đâu**. Chỉ trả về **một JSON hợp lệ**, không giải thích.

## Quy tắc
- Toạ độ là phân số của ảnh nền: x 0 (trái) → 1 (phải), y 0 (trên) → 1 (dưới). `foot` = điểm giữa hai bàn chân, **phải nằm trong vùng `ground`** của ảnh đó.
- Người gần camera có chân thấp hơn trong ảnh (y lớn hơn) và sẽ to hơn; người xa có y nhỏ hơn (gần đường chân trời) và nhỏ hơn. Chọn y theo cỡ cảnh: cận/trung cảnh → chân ở sát mép dưới hoặc dưới khung (tối đa 1); toàn cảnh → chân ở giữa vùng mặt đất.
- Làm theo `blocking` của cảnh (trái/giữa/phải, tiền/hậu cảnh, hướng nhìn). Trong cùng `sequence`, **giữ trục 180°**: người ở bên trái khung vẫn ở bên trái ở các shot sau, trừ khi blocking nói họ di chuyển; hướng di chuyển giữ nhất quán.
- Không đặt hai người chồng lên nhau; người đối thoại thường quay mặt vào nhau (`left`/`right`).
- `background`: chọn **id ảnh** trong danh sách ảnh ứng viên của cảnh, ưu tiên ảnh có góc máy gần với `shot` (cận/trung cảnh ngang mắt → ảnh `eye`/`low`; toàn cảnh, thiết lập không gian → ảnh `high`). Các shot trong cùng `sequence` nên dùng ảnh nền nhất quán (cùng ảnh, hoặc ảnh cùng khu vực theo hướng ngược lại cho shot ngược góc).
- `redraw`: `true` khi không có ảnh nào đúng góc máy cần (ví dụ shot trung cảnh ngang mắt nhưng chỉ có ảnh chụp từ cao); khi đó `redraw_note` (tiếng Anh) nói cần vẽ lại nền thế nào, giữ mốc nào (ví dụ "redraw the same street at eye level, keep the red container on the right and the water tower behind"). Vẫn đặt chân người theo ảnh đã chọn.
- `facing`: `left`, `right`, `camera` hoặc `away` (theo khung hình, không theo nhân vật).
- `pose`: tiếng Anh, ngắn (ví dụ "aiming a rifle", "running toward frame-right").
- Cảnh không có người: `people` rỗng.

## Định dạng
```json
{"shots": [{"idx": 1, "background": 12, "redraw": false, "redraw_note": "",
            "people": [{"name": "Kelly", "foot": [0.3, 0.92], "facing": "right", "pose": ""}]}]}
```
