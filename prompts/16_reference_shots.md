# Phân tích shot video tham khảo (Free Fire)

Bạn là biên tập viên dựng phim. Đính kèm là các **bảng khung hình**: mỗi ô là khung giữa của một shot, ghi số shot và thời gian. Hãy gắn nhãn TỪNG shot để Director học cách video Free Fire được dựng (cỡ cảnh, góc, chuyển động máy, vai trò của shot, chữ/giao diện/hiệu ứng).

Chỉ ghi điều nhìn thấy trong khung hình. Không đoán nội dung ngoài khung. Chỉ trả về **một JSON hợp lệ**.

## Từ vựng cố định (dùng đúng các từ này để số liệu so sánh được giữa các video)
- `size`: `ECU` cận đặc tả (mắt, tay, vật nhỏ) · `CU` cận mặt · `MCU` trung cận (ngực trở lên) · `MS` trung (hông trở lên) · `WS` toàn (cả người + bối cảnh) · `EWS` toàn rộng (bối cảnh là chính, người nhỏ) · `GAME_TPS` camera game (góc thứ ba sau lưng nhân vật, có hoặc không có giao diện game) · `GRAPHIC` đồ họa/tiêu đề/logo phủ toàn khung
- `angle`: `eye` ngang mắt · `low` hất lên · `high` chúc xuống · `overhead` từ trên xuống · `dutch` nghiêng · `ots` qua vai · `pov` góc nhìn nhân vật
- `camera_move`: `static` · `push_in` · `pull_out` · `pan` · `tilt` · `track` (đi theo) · `orbit` (quay vòng) · `handheld` · `crane` · `whip` (lia nhanh) · `zoom` — một khung hình tĩnh không thấy chuyển động thì chọn khả năng cao nhất theo bố cục; không chắc thì `static`
- `role`: `hook` mở móc (gây tò mò ngay đầu) · `setup` thiết lập (ai, ở đâu) · `action` hành động · `reaction` phản ứng (mặt/cử chỉ đáp lại) · `insert` chèn chi tiết (vật, kỹ năng, hiệu ứng cận) · `dialogue` thoại (người đang nói) · `transition` chuyển (nối hai đoạn) · `ending` kết (câu chốt, logo, kêu gọi)
- `transition_in` (cách vào shot, nếu đoán được): `cut` · `fade` · `whip` · `flash` · `match` · `dissolve` · `wipe`
- `text_on_screen`, `game_ui`, `vfx`: true/false — có chữ lớn trên hình (tiêu đề, chữ chương, phụ đề cách điệu) · có giao diện game (HUD, bảng hạ gục, nút) · có hiệu ứng kỹ năng/phép/VFX nổi bật

## Định dạng đầu ra
```json
{
  "shots": [
    {"i": 1, "size": "WS", "angle": "low", "camera_move": "push_in", "role": "hook", "subject": "Kenta tạo dáng, tiêu đề lớn",
     "text_on_screen": true, "game_ui": false, "vfx": false, "transition_in": "cut", "note": ""}
  ],
  "overall": {
    "style_guess": "ANIME_CGI | REAL_CGI_VFX | INGAME | KELLY_SHOW | SHORT_FILM | FAN_3D",
    "structure": {"open": "mở bằng gì (1 câu)", "body": "thân dựng thế nào (1–2 câu)", "close": "kết thế nào (1 câu)"},
    "look": "render / màu / ánh sáng / chất hình (1–2 câu, dùng được cho World Bible)",
    "dialogue_handling": "thoại được dựng thế nào: shot/đáp, cận người nói, có phụ đề không (1 câu, để trống nếu không có thoại)",
    "notable": ["tối đa 5 thủ pháp dựng đáng học: nhịp, chữ chương, chèn hiệu ứng, match cut..."]
  }
}
```
Mỗi shot trong danh sách "# Các shot" phải có đúng một mục, cùng số `i`.
