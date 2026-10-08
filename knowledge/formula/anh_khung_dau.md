# Công thức prompt ảnh khung đầu — 9 phần (+ luật chung)

Ảnh khung đầu là thứ video bám theo suốt clip: sai ở đây thì video sai theo, gen lại video không cứu được. Mỗi phần dưới đây ghi:
**bắt buộc khi nào · lấy từ trường nào (`scenes.data`) · ví dụ #22 · vì sao · code kiểm gì** (`core/prompt_formula.check_image`).
Ví dụ là câu thật của #22 để hiểu ý, không phải câu phải chép.

## 1. Phong cách
- **Khi nào**: luôn.
- **Từ đâu**: phong cách dự án (FF) — không phải trường của shot.
- **#22**: `Free Fire in-game 3D render, stylized proportions, moderate texture detail, clear gameplay lighting`.
- **Vì sao**: thiếu nó model vẽ ảnh kiểu phim/ảnh thật; các shot lệch chất liệu nhau.
- **Code**: không thấy "Free Fire / in-game 3D / 3D render / stylized proportions" → cảnh báo `phong_cach`.

## 2. Khung hình
- **Khi nào**: luôn.
- **Từ đâu**: `size` (ECU…GAME_TPS), `angle`, `shot`; khung dọc của dự án.
- **#22**: cỡ cảnh **kèm giới hạn cơ thể** — `medium close-up from mid-chest up, no legs` · `wide shot … full bodies with feet visible`;
  góc máy; `vertical frame`.
- **Vì sao**: chỉ ghi "medium shot" thì model tự quyết thấy đến đâu; ghi giới hạn cơ thể thì khung và tư thế phải khớp nhau.
- **Code**: thiếu cỡ cảnh → cảnh báo. **Khung ↔ tư thế mâu thuẫn** → ĐỎ: cỡ MCU/CU/"no legs"/"mid-chest up" (trong prompt hoặc `size`)
  mà prompt / `blocking` / `start_frame` / `performance.body` có tư thế cần thấy chân (sprawled, seated on the ground, legs stretched,
  full body, ngồi bệt…). Bằng chứng: #24 shot 4 "Medium close-up — from mid-chest up, no legs" + "body: sprawled on the ground, hands
  braced behind". Sửa: đổi cỡ cảnh sang MS/WS, hoặc tả tư thế bằng phần trên người.

## 3. Khóa nền
- **Khi nào**: khi shot có render 3D (`plate_spot`, `location_asset` có ảnh PLACE).
- **Từ đâu**: `plate_spot`, `plate_view` (hướng nền theo sơ đồ cảnh), mốc của map 3D.
- **#22**: `inside <chỗ đứng> exactly as the 3D render` + 2–4 mốc **đúng vị trí trong khung** (`clock tower … left of centre`, `house
  peeks above the right-hand side wall`) + `the PLACE render picture decides the whole background`.
- **Vì sao**: #24 có câu địa điểm chung chung "grass, palms, sea around" trái với render 3D gửi kèm — prompt thắng ảnh, nền trôi.
  #22 shot 3, 5 không khóa nền, chỉ đẹp nhờ cận mặt.
- **Lưu ý**: tả cái ĐÚNG, không nhắc tên thứ cấm ("Do NOT add palm trees…" — nhắc chữ của lỗi kéo lỗi lại, bài học L2 #22).
- **Code**: chưa kiểm (cần biết shot có render 3D — nhánh F2). Ghi ở đây để Đạo diễn viết.

## 4. Nối tiếp
- **Khi nào**: shot cùng setup với shot trước (`camera_setup` giống, hoặc "cùng khung").
- **#22**: `same camera and same spot as the previous shot`.
- **Vì sao**: không có câu này model đặt lại máy, hai shot liền nhau nhảy bố cục.
- **Code**: chưa kiểm.

## 5. Nhân vật
- **Khi nào**: mỗi người trong `characters`.
- **Từ đâu**: tên trong `characters`; trang phục từ hồ sơ Kho / ảnh OUTFIT (MỘT nguồn); `blocking` cho vị trí, hướng mặt.
- **#22**: TÊN + vị trí (`frame-left`) + hướng mặt/nhìn; trang phục **kể từng món có màu** (`red hoodie with the GREEN fire-breathing
  dinosaur print, black sleeves`); **trạng thái phụ kiện** (`mask worn UP over mouth and nose (never pulled down)`); khóa tóc riêng
  khi ảnh OUTFIT có người mẫu (`keeps Kelly's OWN hair … one solid colour`).
- **Vì sao**: #22 gõ tay trang phục mỗi shot → mũ Maxim "two small WHITE horns" (shot 2, 4) ↔ "small RED horns" (shot 7–9); in hình
  áo Kelly GREEN ↔ blue. Tóc người mẫu trong ảnh OUTFIT lẫn sang Kelly (544/545 bị loại).
- **Code**: `cross_shot` — cùng món đồ (horns, print, cap, hoodie, jacket, hair…) của cùng nhân vật khác màu giữa các shot → cảnh báo
  kèm số shot. Giới hạn: chỉ bắt "màu + ≤ 3 từ + tên món", gán cho tên nhân vật gần nhất phía trước.

## 6. Khoảnh khắc
- **Khi nào**: luôn khi có người (không cần với cận đồ vật / toàn cảnh mở không người).
- **Từ đâu**: `blocking` / `start_frame`, `action` (điểm bắt đầu của hành động), `performance`.
- **#22**: **một** trạng thái khớp khung: `mid-step, looking toward the bed off-screen right` · `crouching mid-dance`.
- **Vì sao**: ảnh là một khoảnh khắc; tả cả chuỗi hành động thì model vẽ trộn hoặc chọn sai lúc, video không có điểm bắt đầu đúng.
- **Code**: không có từ tư thế/trạng thái nào (leaning, mid-step, standing, đứng, cúi…) → cảnh báo `khoanh_khac`.

## 7. Luật FF
- **Khi nào**: luôn — luật tầng 1, mọi dự án Free Fire.
- **Nội dung**: tiết chế ghê (máu / tóc / xác chỉ gợi, trong tối, ngoài nét — người dùng chốt 09/10 cho MỌI dự án FF, không để Đạo
  diễn tự chọn); ≥ 18 tuổi; nhân vật đúng hồ sơ.
- **Vì sao**: #24 Đạo diễn tự thêm "black hair strands and blood stains on the rim … everything in focus" — không luật tiết chế.
- **Code**: có từ ghê (blood, gore, wound, corpse, severed, guts, máu, xác chết, vết thương…) mà không có câu tiết chế nào (only
  hinted / in shadow / out of focus / partly hidden / chỉ gợi / trong tối / mờ) → ĐỎ `luat_ff`. So chữ CÓ DẤU ("màu" không khớp "máu").
- **Luật người ↔ quái** (tầng!): câu "Natural human eyes, no glowing eyes" chỉ dành cho NGƯỜI. Prompt/dữ liệu/hồ sơ tả nhân vật mắt
  phát sáng, demon, ghost, creature, yêu nữ, quái… mà prompt có câu đó → ĐỎ `loai_nhan_vat`.

## 8. Ánh sáng
- **Khi nào**: luôn.
- **Từ đâu**: `lighting`, `time`, `practical_lights`.
- **#22**: nguồn + hướng: `soft window light from the side` · `bright warm midday sunlight from upper-front`.
- **Vì sao**: #22 shot 7 ("warm … upper-front") và 8–9 ("bright midday") cùng một cảnh liền mà ánh sáng khác → nhảy màu khi dựng.
- **Code**: không có nguồn sáng nào → cảnh báo `anh_sang`. (Đồng nhất giữa các shot: `continuity.lighting_warnings`.)

## 9. Chốt chất lượng
- **Khi nào**: luôn.
- **#22**: `everything in focus, not a movie still, not blurred background`.
- **Vì sao**: model hay làm mờ hậu cảnh kiểu phim; ảnh khung đầu mờ thì video mờ theo.
- **Lưu ý**: chốt "everything in focus" KHÔNG được đè lên chi tiết ghê (phần 7) — chi tiết đó phải ghi riêng là ngoài nét/trong tối.

## Luật chung cho mọi prompt (ảnh và motion)
- **Vật / bóng / sinh vật lao sát nhân vật** (streak/dash/fly/rush/lunge … in front of her face / right next to her): phải có
  **đường đi** (from … to …, khoảng cách) VÀ "never touches or passes through her". Thiếu cả hai → ĐỎ; thiếu một → cảnh báo. Bằng
  chứng: #24 shot 3 bản cao — bóng bay xuyên vào người ("streaking fast across the well mouth right in front of her face").
- **Câu tự mâu thuẫn trong cùng prompt** → ĐỎ `mau_thuan`: máy tĩnh ↔ đẩy/dolly/orbit; mắt phát sáng ↔ "no glowing eyes"; "no clock
  tower in frame" ↔ "clock tower visible".
- **Câu dính liền mất dấu chấm** (chữ thường liền ngay TÊN IN HOA + động từ: "not blurred background KELLY KL keeps…", #22 shot 6) →
  cảnh báo `cau_chu`: câu khóa ghép vào cuối, model đọc thành một câu.
- **Liệt kê vật cấm** ("Do NOT add palm trees, grass fields, cars", "no trees, no cars", "no plaza, tower, sky or sea") → cảnh báo
  `ta_cai_dung` (F1-C): bài học L2 #22 — nhắc chữ của lỗi kéo lỗi lại. Tả cái ĐÚNG ("chỉ có cầu thang, tường, tháp, nhà 3 tầng như
  render 3D"). Không báo: một phủ định đơn ("no legs or full body") và phủ định phong cách / chú thích (anime, blur, chữ, người).
- **Trang phục khác hồ sơ** (F1-C `outfit_vs_profile`): cùng món của cùng nhân vật mang màu hồ sơ Kho / ảnh OUTFIT không có (hồ sơ
  "GREEN dinosaur print" ↔ blocking "blue dinosaur print") → ĐỎ `nhan_vat`. Nguồn: mô tả + hồ sơ tài nguyên OUTFIT, không có OUTFIT thì
  `must_keep` của hồ sơ chuẩn / lock_rules (bỏ qua khi `may_change` cho đổi quần áo). Tóc không xét ở đây.

## Code ghép theo khuôn (F1-C, `core/prompt_template.py` + `runner.build_image_prompt`)
Thứ tự phần: phong cách (câu look) → khung → người + hành động (chữ Đạo diễn, blocking, ánh mắt, diễn, action_peak, pha kỹ năng) →
`Fix:` của lần gen lại → nền (trong nhà / khóa render / chữ địa điểm + hướng máy + số đo render) → ánh sáng cảnh → khóa (Identity lock,
nhìn từ phía, tiết chế ghê) → chốt chất lượng. Mỗi phần tự đóng câu. Dự án look FF: mệnh đề phong cách của Đạo diễn trùng câu look bị bỏ;
mệnh đề chất lượng ("everything in focus", "not blurred background") gom về cuối một lần.
