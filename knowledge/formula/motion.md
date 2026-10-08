# Công thức prompt motion — 8 phần + 2 phần mới (#24)

Motion nói **cái thay đổi** từ khung đầu đến hết clip. Thứ đã có trong ảnh (nền, trang phục) chỉ nhắc gọn; hành động lên đầu. Mỗi
phần: **bắt buộc khi nào · lấy từ trường nào (`scenes.data`) · ví dụ #22 · vì sao · code kiểm gì** (`core/prompt_formula.check_motion`).

## 1. Điểm bắt đầu
- **Khi nào**: luôn (clip đi từ ảnh khung đầu).
- **#22**: `The clip starts exactly on the pose and framing of the first image`.
- **Vì sao**: không neo vào khung đầu thì model hay "nhảy" sang bố cục khác ở giây đầu.
- **Code**: không có "clip starts / starts on / first image / bắt đầu…" → cảnh báo `diem_bat_dau`.

## 2. Hành động
- **Khi nào**: luôn, trừ toàn cảnh mở / cận đồ vật không người.
- **Từ đâu**: `action`, `action_peak`, `performance` (body/face/eyes/timing).
- **#22**: chuỗi động từ có thứ tự + điểm dừng: `spins once on the spot, flicks the brim …, then lands a playful pose … and holds it`.
- **Vì sao**: động từ rời rạc không thứ tự → model chọn thứ tự tùy ý hoặc làm nhiều thứ cùng lúc.
- **Code**: không có động từ hành động nào → cảnh báo `hanh_dong`.
- **Trạng thái cuối** (đi kèm): `end_state` có mà motion không nói clip dừng ở đâu ("It ends with …", "holds it") → cảnh báo
  `trang_thai_cuoi` (#22 shot 1, 3, 5 thiếu; shot 2, 4, 6, 9 có).

## 3. Vật lý
- **Khi nào**: có người di chuyển (bước, xoay, nhảy).
- **#22**: `weight shifting heel-to-toe with no foot sliding` · `feet never slide`.
- **Vì sao**: lỗi trượt chân là lỗi I2V phổ biến nhất khi người đi lại.
- **Code**: chưa kiểm (khó biết chắc "có di chuyển" từ chữ) — Đạo diễn tự ghi.

## 4. Máy quay
- **Khi nào**: luôn.
- **Từ đâu**: `camera_move` (static, push_in…), `camera_complexity`.
- **#22**: kiểu + mức + khung giữ: `Static camera` · `almost static, only a very slow tiny drift, holding the same wide full-body framing`
  · `pulls straight back along the camera axis`.
- **Vì sao**: không nói máy thì model tự lia/đẩy; clip dài trên nền có mốc càng trôi.
- **Code**: không có từ máy quay → cảnh báo `may_quay`. Máy tĩnh ↔ đẩy/dolly/orbit trong cùng prompt → ĐỎ `mau_thuan`.

## 5. Thứ đứng yên
- **Khi nào**: khi cần giữ nền / người phụ.
- **#22**: `nothing else moves` · nền cố định + mốc giữ chỗ.
- **Code**: chưa kiểm.

## 6. Khóa nhận dạng
- **Khi nào**: đường chỉ-ảnh-tham-chiếu (ref-only, không có khung đầu cố định).
- **Từ đâu**: hồ sơ Kho (trang phục từng món, phụ kiện, tóc) — MỘT nguồn.
- **Vì sao**: không có khung đầu thì trang phục/tóc chỉ còn trông vào chữ.
- **Code**: `cross_shot` so màu từng món giữa các shot (cảnh báo).

## 7. Nguồn động tác
- **Khi nào**: có video mẫu (loại shot `dance_ref`).
- **#22**: `exactly the moves of the reference video, beat by beat` + `the dancer only gives the motion — never take her face, clothes or room`.
- **Vì sao**: không tách vai, model lấy luôn mặt/đồ/phòng của người nhảy mẫu.
- **Code**: shot nhảy theo video mẫu mà không có câu nguồn động tác → cảnh báo `nguon_dong_tac`.

## 8. Thoại
- **Khi nào**: shot có `dialogue`.
- **#22**: `says his line …; his mouth moves only while he speaks`.
- **Vì sao**: không nói thì miệng mấp máy suốt clip hoặc người khác nói.
- **Code**: có thoại mà motion không có "says / speaks / mouth / lips / nói…" → cảnh báo `thoai`.

## + Đường đi vật gần người (mới, #24)
- **Khi nào**: vật / bóng / sinh vật lao sát nhân vật.
- **Phải có**: điểm đầu → điểm cuối, khoảng cách, `never touches or passes through her`.
- **Vì sao**: #24 shot 3 bản cao — bóng bay xuyên vào người Kelly.
- **Code**: thiếu cả đường đi lẫn câu không chạm → ĐỎ; thiếu một → cảnh báo (`duong_di_vat_gan_nguoi`).

## + Loại nhân vật (mới, #24)
- **Khi nào**: luôn — luật người / quái / thú tách riêng.
- **Vì sao**: motion #24 shot 5: Đạo diễn ghi "eyes: glowing red" (yêu nữ), code gắn thêm "Natural human eyes, no glowing eyes." (luật
  chống mắt phát sáng cho NGƯỜI áp mù cho QUÁI, `seedance_refs.py`).
- **Code**: câu luật mắt người + nhân vật không phải người (prompt / dữ liệu / hồ sơ) → ĐỎ `loai_nhan_vat`; kèm ĐỎ `mau_thuan` khi
  cùng prompt có cả "glowing" lẫn "no glowing".

## Lớp dò "viết chồng thêm" (mục 4b)
- Sau mỗi lần Claude viết motion, Đạo diễn viết lại sau QC, người sửa tay: so với bản cũ của chính prompt đó (`growth_check`).
- Bản mới giữ ≥ 90 % câu cũ và chỉ dài thêm (≥ 20 % hoặc ≥ 2 câu mới) → cảnh báo `viet_chong`: prompt đang thành "nhiều câu nối dần
  theo từng lỗi" (đúng chỗ hỏng của #24), viết lại gọn theo khung.
- Câu mới mâu thuẫn câu cũ còn giữ (bảng cặp như trên) → ĐỎ. Ví dụ: cũ "camera push in" + thêm "Static camera."
- Bản viết lại thật (câu cũ đã thay) → không báo.

## Code ghép nhóm Seedance theo khuôn (F1-C, `seedance_refs.prompt`)
Điểm bắt đầu (luật cắt + khung storyboard từng shot) → hành động từng shot (`shot_motion`: hành động → kết → diễn → thoại → máy quay →
vật lý) → câu lặp NGUYÊN VĂN ở ≥ 2 shot viết một lần ("All shots: …" / "Shots 1, 3: …" — trang phục, nền) → thứ đứng yên → khóa nhận dạng
(vai từng ảnh; có ảnh OUTFIT thì "any other colour word for these garments is wrong") → render nơi chốn → luật (dấu chú thích).
Trần độ dài: `seedance_refs.prompt_limit(model)` (provider_rules `prompt_limit` → clipai.PROMPT_LIMITS); `_estimated_len` gọi chính
`prompt()` và tính cả ảnh OUTFIT.
