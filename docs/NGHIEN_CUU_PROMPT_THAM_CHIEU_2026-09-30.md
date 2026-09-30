# Nghiên cứu: prompt + ảnh + video tham chiếu cho chuẩn — kỹ năng Kenta và cảnh 3 nhân vật (2026-09-30)

Người dùng: "Cần rà soát và xem xét lại để tìm ra cách prompt kèm sử dụng ảnh + video tham chiếu sao cho chuẩn xác nhất — đặt vào trường
hợp có 3 nhân vật cùng 1 cảnh thì sao? Hãy phân tích và nghiên cứu chứ không đoán mò."

Tài liệu này chỉ ghi điều **đọc được từ tài liệu chính thức** hoặc **đo được trong lần thử #11**. Chỗ nào chưa kiểm chứng ghi rõ
**[chưa kiểm]**.

## 0. Nguồn đã đọc

| # | Nguồn | Ghi chú |
|---|---|---|
| A | Kling AI — Omni Video Generation (API mới), https://kling.ai/document-api/api/video/3-0-omni/video-omni | đọc 30/09 |
| B | Kling AI — Omni Video (bản API cũ `image_list` / `element_list` / `video_list` — **bản ClipAI đang chuyển tiếp**), …/video-omni/legacy | đọc 30/09 |
| C | Kling VIDEO 3.0 Omni User Guide, https://kling.ai/quickstart/klingai-video-3-omni-model-user-guide | đọc 30/09 |
| D | KLING VIDEO O1 User Guide (3.0 Omni nói phần video tham chiếu "giống O1"), https://app.klingai.com/global/quickstart/klingai-video-o1-user-guide | đọc 30/09 |
| E | BytePlus ModelArk — Dreamina Seedance 2.5 tutorial, https://docs.byteplus.com/en/docs/ModelArk/2607688 | đọc 30/09 |
| F | Skill ClipAI 1.3.1 (`Get this Skill to Claude/clipai-1.3.1/clipai/reference.md`) — API cổng ClipAI | có trong máy |
| G | Skill ClipAI 1.3.1 `references/seedance-2.5-prompt-optimizer.md` — **chép nguyên từ skill chính thức `sd25-pe` 0.1.0** | có trong máy |
| H | Thử #11 (dự án thử Kenta, 30/09): 3 clip Kling khung đầu + cuối, 2 clip Kling + video tham chiếu, 6 lần bị từ chối | `TODO.md` (3)–(5) |

Trang docs ClipAI (`clipai.ingarena.net/docs`) hôm nay trả 403 — dùng ghi chép 28/09 (`docs/CAP_NHAT_CLIPAI_2026-09-28.md`).

## 1. Sự thật từ tài liệu

### 1.1 Kling 3.0 Omni (qua ClipAI = API bản cũ, nguồn B + F)

1. **Gọi tên tài sản trong prompt:** `<<<image_1>>>`, `<<<element_1>>>`, `<<<video_1>>>` (bản cũ; bản mới A dùng `@image_1`, `@video_1`,
   `@TênElement`). "The Omni model can achieve various capabilities through Prompt with elements, images, videos" — tài sản không được gọi
   tên thì prompt không giao việc cho nó.
2. **Ảnh tham chiếu:** trong `image_list`, ảnh **không có `type`** = ảnh tham chiếu (nhân vật, cảnh, phong cách); `type: first_frame /
   end_frame` = khung đầu / cuối. ≥ 300 px, tỉ lệ 1:2,5–2,5:1, ≤ 10 MB.
3. **Element** (chủ thể dựng sẵn từ tối đa 4 ảnh nhiều góc, có thể gắn giọng): `element_list: [{element_id}]`. Hướng dẫn C: "In complex
   group scenes … the model can independently lock and maintain the features of each character" — đây là **cách chính thức cho nhiều nhân
   vật**. Ví dụ chính thức 3 chủ thể: "@Grace sits on the sofa eating cookies as @Alan walks in holding @Samoyed".
4. **Giới hạn số lượng (nguyên văn B):**
   - có khung đầu / đầu + cuối → **tối đa 3 element** (kling-v3-omni);
   - không video tham chiếu, chỉ element nhiều ảnh → ảnh tham chiếu + element **≤ 7**;
   - **có video tham chiếu** → ảnh tham chiếu + element nhiều ảnh **≤ 4**; không dùng element dạng video.
5. **Video tham chiếu `feature` làm được gì (D, nguyên văn):** "generate the previous/next shot within the same context. Or … create a
   completely new scene referencing **actions or camera movements** in the video". Mẫu chính thức:
   - động tác: *"Animate the character in [@Image 1] with the same motion as the character in the [@Video]"*;
   - máy quay: *"Take [@Image] as the start frame. Generate a new video following the camera movement of the [@video]"*.
   **Tài liệu không nói Kling chép hiệu ứng (effect / VFX) từ video.**
6. **Luật video (B):** MP4/MOV; **3–15,5 s**; rộng/cao **700–4553 px**, diện tích ≤ 8 294 400; **24–60 fps**; tối đa 1 video; có video thì
   `sound` = off. (ClipAI còn đòi điểm ảnh vuông SAR 1:1 — đo được ở H.)
7. **Giá:** có video đầu vào × 1,5 (D: 720p 6 → 9 credit/s). Đo ở H: cost 18 → 27 cho clip 3 s.
8. Omni **không có ô negative riêng**: "prompt … can include positive and negative descriptions".

### 1.2 Seedance 2.5 (nguồn E + G + F)

1. **Gọi tên:** `@Image 1`, `@Video 1`, `@Audio 1` (E) — bản tiếng Trung `@图片1`, `@视频1`, `@音频1` (G). Thứ tự = thứ tự trong `content`.
   E: "Specify what each asset provides, such as appearance, action, or timbre, **and what should not be referenced**."
2. **Mỗi tài sản đúng một việc, mỗi nhân vật một dòng** (G, "不可违反的原则" + mục 4): cấm câu gộp kiểu "A và B tham chiếu @图片1, @图片2";
   phải "A 对应 @图片1，只采用五官、发型和服装" / "B 对应 @图片2 …" + "两人的外貌、服装、动作、站位和台词不互相交换". Tài sản có mà
   không dùng phải liệt kê trong `【未采用素材】`.
3. **Video tham chiếu có thể mang:** động tác, máy quay, nhịp, thời gian, cảnh, phong cách (G); E có ví dụ dùng video cho **lực va chạm /
   hiệu ứng**: *"…the juicy texture and granular impact are amplified, referring to the impact of @Video3"*. Bắt buộc nói **không lấy** gì:
   "不采用视频中的人物身份、服装和场景".
4. **Đã có video mô tả đúng động tác thì KHÔNG tả lại từng động tác** (G mục 4): "只说明继承哪些维度，不必逐动作复述；**重复改写可能与
   素材本身冲突**" (viết lại có thể mâu thuẫn với chính video).
5. **Khung đầu + ảnh khác cùng lúc:** chế độ "first frame" chỉ nhận 1–2 ảnh (E); muốn khung đầu + nhân vật + video thì dùng **omni
   reference** và nói trong prompt "`@图片1作为首帧。`" (G mục "关键帧锚点": ảnh khung đầu vẫn là ảnh tham chiếu thường, câu vai trò phải giữ
   nguyên văn, không làm yếu thành "tham khảo bố cục").
6. **Không thêm câu cấm không liên quan** (G "最终自检": "没有自动添加与用户需求无关的负向约束"); ghi chép ClipAI 28/09: tài sản mâu thuẫn
   thì **thay tài sản**, không thêm câu phủ định.
7. **Vị trí người:** neo vào vật cố định (tường, cửa, bàn) — "不要只写屏幕左侧或右侧" (G "空间与站位").
8. **Thoại nhiều người:** mỗi giai đoạn ghi người nói + `{lời}` + người khác "自然闭口聆听"; giọng mẫu `@音频N` từng người.
9. **Luật tài sản (E):** ảnh 300–6000 px, tỉ lệ 0,4–2,5, ≤ 30 ảnh; video **2–30 s** mỗi đoạn, ≤ 10 đoạn, **tổng ≤ 30 s**, tổng điểm ảnh
   407 696–8 295 044, 24–60 fps; âm thanh ≤ 10, tổng ≤ 30 s; tổng tài sản ≤ 50. Khuyên dùng 1–8 chủ thể ảnh.
10. **Bẫy phân loại (E):** chế độ `auto` có thể hiểu prompt là **sửa video** / **kéo dài video** nếu có chữ "add / remove / replace /
    change / continue / extend" → ra clip sai loại. Prompt tạo mới phải tránh các từ đó khi có video tham chiếu.
11. Bộ lọc người thật: nhân vật ảo tả thực hay bị nhận nhầm — cách chính thức là **Kho chủ thể** (FF đã có thỏa thuận bản quyền; ghi chép 28/09).

## 2. Lần thử #11 sai ở đâu — đối chiếu tài liệu

| Việc đã làm | Tài liệu nói | Hậu quả thấy được |
|---|---|---|
| Prompt Kling **không gọi tên** `<<<video_1>>>`, chỉ ghi "The reference video is …" | phải gọi `<<<video_1>>>` (1.1-1) | video bị dùng lỏng — lốc mờ, ngắn |
| Kling `feature` để chép **hiệu ứng kỹ năng** | Kling chỉ hứa động tác / máy quay / shot trước-sau (1.1-5) | hiệu ứng yếu, chỉ khớp hướng bay |
| Vừa gửi video vừa **tả lại hiệu ứng rất dài** + danh sách "Avoid" 20 mục | Seedance: không tả lại khi video đã có, không thêm câu cấm không liên quan (1.2-4, 1.2-6) | chữ và video kéo nhau; nhắc "red slash, shield…" có thể gợi chính thứ đó [chưa kiểm riêng] |
| Adapter Kling **không gửi ảnh nhân vật** (chỉ khung đầu/cuối) | Kling nhận ảnh tham chiếu không `type` + element (1.1-2, 1.1-3) | nhân vật chỉ giữ nhờ khung đầu — shot không có khung đầu tốt sẽ trôi mặt |
| 3 lần bị từ chối (< 3 s, < 700 px, SAR) | đều ghi trong B | mất 1 vòng; đã thêm kiểm vào adapter |
| Khung cuối vẽ riêng → nền trôi | Seedance: khung đầu/cuối phải cùng khung hình (G 7) — ảnh vẽ lại thường không giữ | clip vòng 1 biến hình giữa chừng |

**Kết luận:** lỗi chính không nằm ở hồ sơ kỹ năng mà ở **cách gửi**: sai model cho việc chép hiệu ứng, không gọi tên tài sản, tả trùng với
video.

## 3. Cách làm đề xuất (theo tài liệu)

### 3.1 Chọn model theo việc

| Việc | Model | Lý do (nguồn) |
|---|---|---|
| Shot có **hiệu ứng kỹ năng** chép từ video game | **Seedance 2.5** (720p) | video chép được động tác, nhịp, phong cách, "impact" (1.2-3); ≤ 10 video, ≤ 30 ảnh; khung đầu qua câu vai trò (1.2-5) |
| Shot **nhiều nhân vật** giữ mặt, không hiệu ứng lạ | **Kling 3.0 Omni + 3 element** hoặc Seedance 2.5 + Kho chủ thể | element khóa từng người (1.1-3); tối đa 3 element khi có khung đầu |
| Chép **động tác cơ thể** (chạy, nhảy) từ video | Kling `feature` mẫu "Animate … with the same motion as … @Video" | mẫu chính thức (1.1-5) |
| Chép **đường máy quay** | Kling `feature` mẫu "Take @Image as the start frame … camera movement of @video" | mẫu chính thức |

### 3.2 Chuẩn bị tài sản

- **Nhân vật:** mỗi người 1 ảnh chính diện nền trơn (định danh) + tối đa 3 góc (element Kling / nhiều dòng Seedance cho **cùng** 1 người,
  ghi "共同定义同一实体"). Không dùng ảnh có 2 người để định danh 1 người.
- **Video kỹ năng:** cắt đúng đoạn hiệu ứng, **cắt cận quanh nhân vật** (hiệu ứng to trong khung), bỏ chữ giao diện nếu được; ≥ 3 s (Kling)
  / ≥ 2 s (Seedance), cạnh ≥ 700 px, SAR 1:1, 24–60 fps (adapter đã kiểm 3 luật Kling). Video có nhân vật game → có thể vướng bộ lọc
  người thật **[chưa kiểm với Seedance]**.
- **Nơi chốn:** 1 ảnh (render 3D đúng góc — cờ `place_render_refs`) hoặc khung đầu.
- **Khung đầu:** ảnh đã duyệt của shot (Deepix).

### 3.3 Mẫu prompt — shot kỹ năng 1 nhân vật (Seedance 2.5)

```
【生成目标】 Kenta 在木屋之间的土路上释放"龙卷突袭"：半透明青色全息光刃挥出，风旋包裹全身后化作地面风环，月牙形风刃飞向前方的白色胶墙。
【参考素材职责】
@图片1作为首帧。该首帧定义土路、木屋、胶墙位置、Kenta 背对镜头站立的位置与姿态和中景机位。
@图片2用于 Kenta 的五官、发型、蓝色斗篷和横挂在腰后的红柄武士刀，不采用图片背景。
@视频1用于技能特效的形状、颜色、透明度、出现顺序和节奏（光刃挥出 → 包裹全身的半透明风旋 → 地面风环 → 肩高月牙风刃飞出），
不采用视频中的人物身份、服装、场景、镜头和界面文字。
【事件脚本】 开始时 Kenta 右手持光刃静止。随后按@视频1的节奏释放技能。结束时风刃接近胶墙，Kenta 双脚未移动。
【保持一致】 Kenta 身份与服装、武士刀始终在刀鞘中横挂腰后、机位固定、胶墙完整。
```
(Tiếng Việt / tiếng Anh cũng được — E dùng tiếng Anh "@Image 1 … @Video 1"; G khuyên giữ nguyên nhãn người dùng dùng. Không tả lại hiệu
ứng chi tiết vì video đã mang — chỉ liệt kê **thứ tự giai đoạn** để khớp video.)

### 3.4 Cảnh 3 nhân vật (Kelly, Kenta, Maxim) — cùng một clip

**Seedance 2.5** (khuyên dùng khi có hiệu ứng):
```
【参考素材职责】
@图片1作为首帧。该首帧定义……（bố cục, ai đứng đâu so với tường keo / cửa / thùng gỗ）
@图片2对应 Kelly，只采用五官、短发和黄色运动服。
@图片3对应 Kenta，只采用五官、发型、蓝色斗篷和横挂腰后的红柄武士刀。
@图片4对应 Maxim，只采用五官、发型和服装。
三人的外貌、服装、动作、站位和台词不互相交换。
@视频1只用于 Kenta 技能特效的形状、颜色、透明度和节奏，不采用视频中的人物、场景、镜头和界面文字。
@音频1用于 Kelly 的音色；@音频2用于 Maxim 的音色。
【未采用素材】 （liệt kê số ảnh / video không dùng）
【主体与关系】 Kelly 蹲在胶墙后侧；Kenta 站在土路中央、面向胶墙；Maxim 站在木屋门口。 (neo vào vật, không dùng trái/phải khung)
【事件脚本】 阶段一：Kenta 按@视频1释放技能……；Kelly 与 Maxim 自然闭口。阶段二：Kelly 用越南语说：{…}；其他人自然闭口聆听。
【保持一致】 三人身份与服装、武士刀在鞘、胶墙完整、机位。
```
Giới hạn: 1 khung đầu + 3 ảnh người + 1 video + 2–3 âm thanh — trong hạn (≤ 30 ảnh, ≤ 10 video). Nếu mặt bị bộ lọc chặn → Kho chủ thể.

**Kling 3.0 Omni** (không cần chép hiệu ứng từ video):
```
Take <<<image_1>>> as the start frame. <<<element_1>>> (Kelly) crouches behind the white gloo wall; <<<element_2>>> (Kenta) stands on the
dirt path facing the wall; <<<element_3>>> (Maxim) stands at the wooden house door. …
```
Giới hạn cứng: có khung đầu → **tối đa 3 element** (vừa đủ 3 người); **có video tham chiếu → ảnh + element ≤ 4 và video chỉ chép động
tác / máy quay** → 3 người + video kỹ năng + khung đầu là **vượt giới hạn / sai việc** với Kling. Element phải tạo trên web ClipAI
(Elements chỉ có trên web — ghi nhớ 2026-09-2x) rồi dùng `element_id` qua API **[chưa kiểm ClipAI có trả element_id của web]**.

**Thay thế khi quá tải:** chia shot — shot hiệu ứng (Kenta + video kỹ năng) riêng, shot phản ứng 3 người riêng (G: "không nhồi nhiều hành
động / đổi máy vào thời lượng ngắn").

## 4. Việc sửa code đề xuất (chưa làm — chờ duyệt)

1. **Adapter Kling:** gửi ảnh nhân vật / nơi chốn làm ảnh tham chiếu (`image_list` không `type`) trong giới hạn 7 / 4; prompt tự thêm câu
   vai trò có `<<<image_N>>>`, `<<<video_1>>>` theo mẫu chính thức (động tác / máy quay).
2. **Adapter Seedance:** câu vai trò theo mẫu G (một dòng một tài sản, "không lấy …", `【未采用素材】`); khung đầu = câu "@Image 1 作为首帧"
   trong chế độ omni reference; video tham chiếu có dòng vai trò riêng; tránh từ khóa sửa / kéo dài.
3. **Hồ sơ kỹ năng:** thêm `video_ref` (đoạn cắt đúng luật) + câu vai trò ngắn "shape, colour, transparency, order, rhythm of the skill
   effect … not person/scene/camera/HUD"; **bỏ** đoạn tả hiệu ứng dài + danh sách "Avoid" khi có video; giữ tả chữ khi không có video.
4. **Router model:** shot có `skill_phase` + có video hồ sơ → Seedance 2.5; shot nhiều người không hiệu ứng → Kling + element (khi có).
5. **Kiểm trước khi gửi** (đã có cho Kling): thêm luật Seedance (2–30 s, tổng ≤ 30 s, điểm ảnh 407 696–8 295 044, 24–60 fps).

## 5. Thử để kiểm chứng (tốn tiền — chờ duyệt)

| # | Thử | Kiểm điều gì | Ước tính |
|---|---|---|---|
| T1 | Seedance 2.5, shot 1 Kenta: khung đầu (job 470) + ảnh Kenta + video kỹ năng, prompt mẫu 3.3, 5 s | chép hiệu ứng từ video; bộ lọc người thật với video game | 5 s × ~$0,23 ≈ $1,15 (giá 2.5 chưa có nguồn chính xác, × 1,25) |
| T2 | Kling cùng shot, prompt có `<<<image_1>>>` + `<<<video_1>>>` theo mẫu "same motion as …", 3 s | gọi tên tài sản có đổi kết quả không (so với lần #11) | ≈ $0,27 |
| T3 | Cảnh 3 người, Seedance 2.5, mẫu 3.4, không hiệu ứng, 5 s | giữ 3 mặt / không đổi người | ≈ $1,15 |

T1 + T2 ≈ $1,4; T3 làm sau nếu T1 đạt.
