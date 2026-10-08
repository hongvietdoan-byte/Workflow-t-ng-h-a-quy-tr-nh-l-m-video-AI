# Phân shot (dự án chia shot — kế hoạch v3)

Dự án này sản xuất **theo shot**, không theo cảnh: mỗi cảnh kịch bản phải được chia thành nhiều shot ngắn, mỗi shot = 1 ảnh khung đầu + 1 clip video. Ngoài các trường của cảnh như hướng dẫn ở trên, **mỗi cảnh trong `scenes` phải có thêm `shots`** (danh sách theo thứ tự trên phim).

## Cách chia
- Đọc từng beat của cảnh (muốn gì – cản trở – bước ngoặt), mỗi thay đổi hành động, mỗi câu thoại, mỗi phản ứng quan trọng → một shot. Dùng ngữ pháp dựng Free Fire và phong cách của dự án ở phần kiến thức (số liệu là **khoảng tham khảo**, không phải con số cố định).
- **Nhịp do kịch bản quyết định**: shot hành động/phản ứng/chèn ngắn; shot thoại dài bằng thời gian nói câu đó (~3,5 âm tiết/giây + 0,5 s); thiết lập, kết, money shot được dài hơn. Tổng thời lượng các shot nên khớp thời lượng kịch bản yêu cầu (nếu có ghi).
- Mở video bằng **hook**; kết bằng **ending** (tạo dáng, nhìn máy quay, câu chốt). Sau câu thoại/hành động quan trọng nên có **reaction**. Đổi cỡ cảnh có lý do; tránh 4 shot liền cùng cỡ.
- **Truyền cảm xúc cho rõ — ba cách, dùng khi đúng chỗ (không phải luật đếm):**
  - **Phản ứng trước, nguyên nhân sau** khi muốn người xem *hỏi* "chuyện gì vậy?": shot mặt nhân vật sững lại / hoảng lên → rồi mới
    cho thấy cái họ thấy. Câu hỏi giữ người xem ở lại; thấy nguyên nhân trước thì người xem chỉ *xác nhận*. Nguyên nhân phải lộ ngay
    shot kế (≤ 2 s) — để lâu người xem rối chứ không tò mò. Đây là một cách làm "ai biết gì": người xem biết *sau* nhân vật.
  - **Giữ lại sau cú đánh cảm xúc:** ngay tại hoặc ngay sau khoảnh khắc mạnh (`performance.intensity` ≥ 4), có **một shot 2–4 s** trên
    mặt/phản ứng để người xem kịp thấm; cắt đi ngay thì cảm xúc trôi mất (lần chạy 4: shot im lặng 0,5 s bị cắt quá nhanh). Cố ý dồn nhịp
    (pha hành động) thì ghi lý do trong `why` — code báo khi cả chuỗi khoảnh khắc mạnh không có shot nào ≥ 2 s.
  - **Móc nhỏ giữa video:** video dài hơn ~20 s thì mỗi đoạn ~10–15 s kết bằng một chi tiết **dở dang** (câu nói bị ngắt, tay chạm vào
    vật, ánh mắt nhìn ra ngoài khung) để người xem muốn xem tiếp; đỉnh cảm xúc cuối có thể cắt ngay ở đỉnh thay vì kể nốt.
- **Âm thanh là một phần của cảm xúc, quyết cùng lúc với hình** (trường `sound`, chỉ ở shot cần): nhạc **ngắt** khi mối đe dọa xuất hiện
  hay lúc bình yên giả tạo (im lặng làm âm nhỏ nhất thành to), **lặng ngắn** ngay trước cú ngoặt để cú đánh rơi đúng, nhạc **vào lại**
  khi lật thế; và âm của **cơ thể/vật** mà khoảnh khắc cần (tiếng thở dồn, nuốt nước bọt, tiếng lên đạn, tiếng bíp). Tự hỏi: tắt tiếng đi
  hình còn kể được không — và bật tiếng lên, âm thanh có đẩy thêm được gì không?
- Thoại: **mỗi câu nằm trọn trong một shot**; không cắt ngang câu. Một shot có thể chứa 0, 1 hoặc vài câu ngắn liền nhau của cùng cảnh.
- **Không có khớp môi (BẮT BUỘC khi khớp môi TẮT — nếu khối "Thời lượng bắt buộc" ghi "Khớp môi đang BẬT" thì theo khối đó)**: giọng tiếng Việt được lồng sau, miệng nhân vật trong video không nói đúng câu đó. Shot có `dialogue` **KHÔNG được** là `ECU`/`CU`/`MCU` mà người nói có trong `characters` và nhìn thấy mặt (angle `eye`/`low`/`high`/`dutch`). Thay bằng: `MS`/`WS`; góc `ots` (qua vai người nghe, người nói ở trung cảnh); người nói quay nghiêng/quay lưng/đang hành động; hoặc đặt câu thoại lên **shot phản ứng của người nghe** (người nói ngoài khung — vẫn ghi `speaker` là người nói nhưng không đưa họ vào `characters`). Cận mặt người nói chỉ dùng cho khoảnh khắc **im lặng** (nước mắt rơi, sững người) — tách thành shot riêng không thoại.
- **Kịch bản ghi rõ góc máy thì giữ đúng**: "GÓC CAMERA SAU VAI X" / "qua vai X" → `angle: "ots"`, X có trong `characters` (vai/lưng mờ ở tiền cảnh); "CẬN CẢNH" → `CU` (không thoại, xem luật trên); "CHÍNH DIỆN" → nhân vật nhìn về máy; "TOÀN CẢNH" → `WS`. Chỉ đổi khi luật khớp môi buộc phải đổi — khi đó đổi cỡ cảnh, giữ tinh thần góc máy.
- **"Bóng tối" / "một mình" không phải nền đen trơn**: kịch bản ghi "đứng trong bóng tối" = cảnh ĐÊM hoặc thiếu sáng **trong một bối cảnh thật
  của dự án** (ghi rõ nơi nào, mốc nào nhìn thấy mờ phía sau), ánh sáng tối (low-key) — không dùng "void", "black background", "abstract
  space". Nền trừu tượng chỉ khi kịch bản ghi rõ là giấc mơ/không gian tượng trưng. (Chạy thử 2A: 4 shot mở đầu ra nền đen, người xem thấy
  như chưa làm xong.) Cảnh mở đầu và cảnh kết "quay lại cảnh cinematic" dùng CÙNG một nơi.
- **Chữ trên màn hình không phải thoại**: dòng "HỆ THỐNG: …", thông báo game, chữ kết/tiêu đề → ghi vào `on_screen_text` của shot (danh sách chuỗi), **không** đưa vào `dialogue`, không đặt người dẫn chuyện (NARRATOR) cho nó. Hình ảnh cũng không vẽ chữ (thêm ở hậu kỳ).
- **Độ dài shot**: shot dưới 2 giây chỉ cho chèn/phản ứng thật nhanh (tối đa khoảng 1/5 số shot) — model video luôn làm clip tối thiểu dài hơn rồi cắt, shot quá ngắn tốn tiền mà không thêm gì; gộp các nhịp nhỏ liền nhau vào một shot.
  - **Không có shot im lặng dưới 1 giây** (trừ `insert` trong pha hành động nhanh). Toàn cảnh `WS`/`EWS` **≥ 1,5 giây** (0,5 giây người xem không kịp đọc 3 người trong khung).
  - Nhịp im lặng ngắn (quay lại, khựng lại, nhìn nhau) **gộp vào đầu/cuối shot thoại kề bên** thay vì tách shot: "Kenta quay lại rồi nói…" là MỘT shot.
  - Không mở mỗi cảnh bằng một shot thiết lập 0,5 giây theo thói quen — chỉ thiết lập khi đổi địa điểm, và đủ dài để đọc.
- Chữ tiêu đề, chữ chương, logo, giao diện game **không** thành shot (làm ở hậu kỳ) — không dùng cỡ `GRAPHIC`.
- Gameplay kiểu trong game: dùng `GAME_TPS` (camera sau lưng nhân vật, cao hơn vai) với `angle: "high"`. `angle` **chỉ** nhận giá trị trong danh sách ở dưới — không tự đặt "behind", "tps", "back"… (một lần sai trường này là một lần hỏi lại trả tiền cả bản).
- Các shot liền mạch cùng địa điểm/thời điểm thuộc cùng `sequence` của cảnh; shot nào **nối liền hình với shot kế tiếp** (cùng hành động kéo dài qua điểm cắt) thì `continuous_with_next: true`.

## Trường của mỗi shot
```json
{"size": "ECU|CU|MCU|MS|MLS|WS|EWS|GAME_TPS", "angle": "eye|low|high|overhead|dutch|ots|pov",
 "camera_move": "static|push_in|pull_out|pan|tilt|track|orbit|handheld|crane|whip|zoom",
 "role": "hook|setup|action|reaction|insert|dialogue|transition|ending",
 "duration_s": 2.5,
 "action": "tiếng Việt, 1 hành động chính của shot",
 "start_frame": "tiếng Anh: ai ở đâu trong khung lúc bắt đầu shot (trái/giữa/phải, tiền/hậu cảnh, hướng mặt, tư thế)",
 "end_state": "tiếng Anh, chỉ khi shot đổi trạng thái rõ (vị trí/tư thế cuối shot); không thì bỏ",
 "action_peak": "tiếng Anh, shot hành động: tư thế ĐANG giữa động tác ở khung đầu (vd 'mid-stride, weight on the left foot, arms swinging'); shot tĩnh thì bỏ",
 "image_prompt": "tiếng Anh: KHUNG ĐẦU của shot — cỡ cảnh, góc, nhân vật, bối cảnh, ánh sáng, theo khung hình dự án",
 "characters": ["TÊN trong Character Bible có mặt trong khung"],
 "dialogue": [{"speaker": "TÊN", "text": "câu thoại nguyên văn tiếng Việt",
               "delivery": {"emotion": "tiếng Anh ngắn", "intensity": 3, "pace": "slow|normal|fast", "pause_before": "true|short|long",
                            "stress": "chữ cần nhấn", "tag": "whispers"}}],
 "on_screen_text": ["chữ hiện trên màn hình (thông báo hệ thống, chữ kết) — không đọc thành tiếng; bỏ khi không có"],
 "performance": {"intensity": 3, "face": "tiếng Anh: mặt làm gì", "eyes": "nhìn đâu, chớp thế nào", "body": "tư thế, tay",
                 "timing": "đổi thế nào theo thời gian", "listener": "người nghe phản ứng gì", "motive": "tiếng Việt: vì sao"},
 "sound": {"music": "keep|cut|in|breath", "sfx": ["tiếng Anh ngắn: âm khoảnh khắc cần"], "why": "tiếng Việt: âm này đẩy cảm xúc gì"},
 "why": "tiếng Việt, 1 câu: vì sao cỡ/góc/chuyển động này", "motif": "nhãn ngắn khi shot vần với shot khác",
 "lens_mm": 35, "weather": "clear", "plate_spot": "tên chỗ đứng", "lip_sync": false,
 "plate_view": {"background": "landmark|away|left|right|spot:<tên>|<độ>", "why": "tiếng Việt"},
 "practical_lights": [{"kind": "lamp|fire|screen|neon|torch|headlight|window", "where": "behind_left…", "color": "warm", "why": "…"}],
 "hook_mid": false, "money_shot": false, "speed": 0.5, "freeze_end_s": 0.5,
 "continuous_with_next": false, "hero": false,
 "transition_in": "cut|match|occlusion|flash|dip|whip|zoom_through|j_cut|l_cut",
 "difficulty": "easy|complex|unknown", "difficulty_why": "tiếng Việt, 1 câu: căn cứ của nhãn độ khó"}
```
- **`difficulty` + `difficulty_why` (mọi shot — độ khó khi gen video, người dùng chốt 08/10):** nhãn này quyết định đường làm clip:
  `easy` → gen thẳng bản chất lượng cao (không nháp, đỡ một lượt thử); `complex` hoặc `unknown` → gen nháp chất lượng thấp trước, đạt
  rồi mới gen bản cao. Nghĩ theo câu hỏi: *model video có làm đúng ngay lần đầu không, và căn cứ ở đâu?*
  - `easy` khi mọi thứ trong khung đều là việc model làm tốt: **một người**, động tác đơn giản (đứng, nhìn, quay đầu, bước chậm), máy tĩnh
    hoặc chuyển động nhẹ (đẩy chậm, lia ngắn), không có câu thoại phải khớp môi, không kỹ năng / hiệu ứng, không nhảy. *Vì sao:* những shot
    này hầu như không phải gen lại — nháp chỉ tốn thêm một lượt.
  - `complex` khi có thứ model hay làm hỏng: **nhiều người tương tác** (chạm nhau, đối mặt, truyền vật), **nhảy / múa**, **kỹ năng / hiệu
    ứng** (cần ảnh / video tham chiếu), **khớp môi** cận mặt, **tay** làm việc tỉ mỉ (cầm, bấm, trao vật), **máy di chuyển lớn** (track,
    orbit, crane, whip), **nền 3D khó** (góc nhìn lạ, nhiều vật mốc phải đúng). *Vì sao — số đo thật:* #8 shot thoại khớp môi trung bình
    gen lại 1 lần/shot, #22 shot nhảy / kỹ năng 3 lần/shot; nháp rẻ cho phép sửa trước khi trả giá bản cao.
  - `unknown` khi thiếu căn cứ để chắc (chưa có ảnh tham chiếu kỹ năng, chưa biết model xử lý động tác này ra sao, kịch bản tả mơ hồ).
    Không đoán `easy` cho yên tâm — `unknown` vẫn đi đường nháp, an toàn hơn.
  - `difficulty_why`: một câu nêu **căn cứ cụ thể** của shot này ("1 người đứng nhìn, máy tĩnh, không thoại" / "2 người nhảy đối mặt,
    máy orbit"). Code kiểm chéo bằng các trường của shot (số người, từ khóa động tác, `camera_move`, `lip_sync`, thoại, kỹ năng, nền 3D):
    shot ghi `easy` mà các trường cho thấy khó sẽ bị hạ thành `unknown`; không bao giờ hạ `complex`.
- **`performance` (diễn xuất — mọi shot có người, nhất là thoại/phản ứng/móc/kết):** tả **hành vi nhìn thấy được**, không chỉ tên cảm xúc
  ("sad" → "lips pressed into a trembling smile, eyes wet, blinking fast"). `intensity` 1 gần như không thấy · 2 kìm nén · 3 rõ nhưng tự nhiên ·
  4 mạnh · 5 đỉnh của phim (chỉ 1–2 shot). Ghi **độ mạnh của khoảnh khắc** — kể cả ở cận: code tự vẽ cận CU/ECU nhỏ hơn một bậc, đừng tự hạ. Người nghe cũng diễn (`listener`). Không có model video nào tự biết nhân vật
  muốn gì — thiếu trường này model tự chọn biểu cảm (chạy thật #6: ra "giận, há miệng" thay vì "cười nhếch").
- **`delivery` (chỉ đạo giọng lồng, từng câu, khi câu cần sắc thái rõ):** cảm xúc, cường độ, nhịp; `pause_before` = ngắt trước câu;
  `stress` = một chữ có trong câu; `tag` chỉ một trong: whispers, sighs, shouts, laughs, crying, sarcastic, excited, curious, nervous,
  angry, sad, calm, gulps, clears throat. Không đổi chữ của câu.
- **`sound`** (tùy chọn — chỉ shot mà âm thanh mang cảm xúc; bỏ hẳn ở shot bình thường): `music` — `cut` nhạc tắt hẳn từ đầu shot này
  tới shot có `in`; `in` nhạc vào lại từ đầu shot; `breath` lặng ~0,6 s ngay trước shot rồi nhạc vào đúng shot; `keep` (mặc định) giữ
  nguyên. `sfx` — tối đa 3 âm cụ thể người xem phải nghe rõ ở shot này (`"heavy breathing"`, `"gun cock click"`, `"swallow"`), không ghi
  nhạc hay âm nền chung. Đỉnh cảm xúc (cường độ 5) mà âm thanh không có ý đồ nào → code nhắc. Nhớ `in` sau `cut` (quên thì nhạc tắt tới hết phim).
  Tùy chọn: `music_fn` (tension | hide | release | reveal | time | place | comic | memory — nhạc ở đây để làm gì), `enter` (soft |
  sudden, ở shot đầu cảnh), `bed` (sparse = từ shot này nhạc cố ý thưa, lặng được lâu hơn 8 s; continuous = hết đoạn thưa).
- **`motif`** (tùy chọn): một nhãn ngắn (vd "qua vai Kenta", "vòng cổ đen") cho các shot "vần" với nhau — cùng nhãn ở ít nhất 2 shot
  (lần đầu gieo, lần sau biến tấu); code báo motif chỉ xuất hiện một lần.
- **`action_peak`** (shot có hành động cơ thể — chạy, ngã, đánh, xoay người, nhảy): khung đầu vẽ nhân vật **đang ở giữa động tác**, clip
  bắt đầu khi chuyển động đã chạy (dp.md Q12). Ảnh khung đầu dáng đứng thẳng làm model video "khởi động" từ tư thế đứng — #8: chạy giả,
  khựng ở mỗi điểm cắt. Không dùng cho shot mà sự đứng yên chính là ý đồ.
- **`transition_in`** (tùy chọn, mặc định `cut`): cách vào shot này từ shot trước — chọn theo ý đồ chỗ nối, không có nghĩa cố định:
  `match` (hình / động tác vần nhau qua điểm cắt), `occlusion` (chuyển cảnh che máy **thiết kế trong chuyển động** của hai shot: vật / người
  đi ngang ống kính, máy lia theo vật, máy tiến vào vật che kín khung — tả trong `action` / `start_frame` của cả hai shot), `flash` (chớp
  trắng — nhảy thời gian, ký ức, cú sốc…), `dip` (tối đi rồi sáng lại — thời gian trôi, kết một chương…), `whip` (lia nhanh nhòe — dồn nhịp,
  đổi nơi cùng lúc…), `zoom_through` (lao vào khung — bước sang thế giới / trạng thái khác…), `j_cut` / `l_cut` (âm của shot sau vào trước
  / âm shot trước kéo sang). Phần lớn chỗ nối là `cut`; chuyển cảnh đặc biệt dùng nhiều thì mất tác dụng.
- **`why`:** một câu cho người duyệt: shot cho người xem biết/cảm gì → vì sao cỡ/góc/chuyển động này → nối với shot trước thế nào.
- **`lens_mm`** (chỉ khi cần khác mặc định theo cỡ cảnh): 24 đặt gần phóng to tiền cảnh, kéo dãn không gian; 85–135 nén hậu cảnh, tách chủ thể — dùng cho ý đồ nào là **tùy cảnh**, ghi vào `why`. **`weather`**, **`plate_spot`**,
  **`plate_view`** (hướng máy = cái gì ở nền, kèm lý do — theo kịch bản, không theo chỗ đứng), **`practical_lights`**
  (cảnh đêm: `[]` = chỉ trăng, hoặc đèn có lý do): chỉ khi có khối "Gói bối cảnh" (tên + luật ở đó); `weather` có thể ghi ở cảnh cho cả cảnh. **`lip_sync`**:
  chỉ khi khớp môi đang BẬT (xem khối Thời lượng). Bỏ trường nào không dùng.
- **`hook_mid: true`** (video > 20 s): shot kết một đoạn ~10–15 s bằng một chi tiết **dở dang** (câu bị ngắt, tay chạm vào vật, ánh
  mắt nhìn ra ngoài khung) để người xem ở lại sang đoạn sau; code báo đoạn > 15 s không có móc nào.
- **`money_shot: true`** (một shot, video quảng bá): khoảnh khắc thứ đang quảng bá hiện rõ nhất (kỹ năng bật, trang phục toàn thân) —
  làm ảnh bìa. Khác `hero` (cao trào/twist, model video tốt nhất).
- **`speed`** (0,25–0,9) / **`freeze_end_s`** (≤ 1,5 s): **chỉ shot không thoại** — quay chậm khoảnh khắc đỉnh của hành động (viên đạn
  rời nòng, cú nhảy kỹ năng, giọt nước mắt rơi) hoặc dừng hình ở cú chốt. `duration_s` là độ dài **trên phim**; clip chỉ cần
  (duration_s − freeze) × speed giây hành động. Tối đa 1–2 lần mỗi phim — dùng nhiều thì mất tác dụng. Shot có thoại / khớp môi: code bỏ.
- **Gốc JSON thêm:** `"tradeoffs": [{"kind", "chose", "gave_up", "why", "scene"}]` (`kind`: `dropped_line` (bỏ câu) · `length` (lệch khung giây) · `speech_time` (shot thiếu thời gian nói) · `script_angle` (bỏ góc máy kịch bản ghi) · `other`) mỗi khi hy sinh một ưu tiên thấp hơn (bỏ câu, lệch thời lượng,
  đổi góc kịch bản ghi…) — code kiểm, thiếu là lỗi; `"script_notes": [{"scene", "kind", "note"}]` — ghi chú cho người viết kịch bản (câu
  thiếu lý do, hụt logic, twist chưa được gieo): **chỉ đề xuất** dạng "vị trí → người xem sẽ thấy gì → câu hỏi", không viết câu thoại mới.
- `duration_s` từ 0,5 đến 15 giây. Shot ngắn hơn thời lượng tối thiểu của model video sẽ được gen dài hơn rồi cắt — cứ đặt đúng độ dài phim cần.
- `hero: true` cho 1–3 shot then chốt của cả video (cao trào, cú twist) — được dùng model video tốt nhất.
- Giữ nguyên văn mọi câu thoại của kịch bản, đúng người nói, đúng thứ tự; không thêm câu mới. (Chỉ khi khối "Thời lượng bắt buộc" ghi **được phép bỏ bớt câu thoại** thì mới được bỏ câu — vẫn không thêm, không sửa chữ câu giữ lại.)
- **Khi được phép bỏ câu thoại — thứ tự cắt khi thừa thời lượng**: (1) gộp/bỏ shot im lặng ngắn và shot thiết lập; (2) rút shot phản ứng/chèn; (3) chỉ khi vẫn thừa mới bỏ câu thoại. Câu được bỏ phải là câu **không ai đáp lại** và hình ảnh đã nói thay. **Không bỏ** câu mà câu kế tiếp đáp lại (cặp hỏi–đáp, lời xin–lời từ chối: bỏ "Kelly, nghe anh giải thích…" thì "Không cần." thành câu hụt; muốn bỏ thì bỏ cả cặp). **Không bỏ** câu gieo manh mối cho twist/kết, câu thể hiện nhân vật đã cố làm gì (vd cố giải thích — đó là cái khiến cú twist đau). Đọc lại đoạn thoại còn lại như người xem: mỗi câu vẫn có lý do để được nói ra.
- Các trường của cảnh (`location`, `time`, `mood`, `lighting`, `sequence`, `emotional_intent`, `beat`…) vẫn điền như cũ; `image_prompt`/`shot` của cảnh có thể mô tả chung cảnh.
