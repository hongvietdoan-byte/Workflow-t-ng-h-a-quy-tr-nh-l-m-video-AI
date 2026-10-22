# Nghiên cứu Weave Canvas (Deepix) — áp vào M2.10 và M8.1

Ngày: 21–22/10/2026 · Chi phí: 0 USD · Cách làm: CHỈ XEM trang công khai
`https://deepix.ingarena.net/weave/deepix-canvas-demo` trong trình duyệt tích hợp. Không bấm Run/Export/Reset, không sửa canvas,
không đăng nhập, không nhập dữ liệu. Trang demo mở được mà KHÔNG đòi đăng nhập hay chấp nhận điều khoản (có popup "Happy with this
result?" che màn, không bấm).

**Ký hiệu nguồn** (mỗi mục đều ghi):
- **[UI]** = đọc thẳng DOM/textarea/nhãn nút/tooltip của trang đang mở.
- **[JS]** = đọc mã phía trình duyệt cùng miền (`/weave/app.js`, `/js/components/common/referenceMentionUtils.js`,
  `ModelSelectorManager.js`) và bảng chữ tiếng Anh `window.i18n` — là mã thật nhưng KHÔNG chạy, nên mô tả hành vi là "theo mã".
- **[SUY]** = suy luận của người viết, chưa kiểm chứng.

---

## 1. Tóm tắt nhanh

1. Demo là chuỗi 9 nút, 13 dây: Prompt → Ảnh chính (2D → chibi 3D) + Ảnh tham chiếu tải lên → **Storyboard 4 khung** → **3 nút Video
   Seedance 2.5** (mỗi nút nhận 2 khung kề nhau) + 1 nút SFX → **Ghép audio-video** [UI].
2. Prompt rất ngắn: story 191 ký tự, khung 379–419, video **28–99 ký tự**, SFX 114, ghép 72 [UI]. So với ta: ảnh #31 TB 5.380,
   #33 11.059; video 3.000–4.000 → Weave ngắn hơn **13–55 lần** ở ảnh và **30–140 lần** ở video.
3. Tham chiếu gọi bằng `@Image N` theo **thứ tự nối dây**; hệ thống TỰ nối thêm một khối "Reference image mapping" mỗi ảnh 1 dòng
   (~120 ký tự/ảnh) vào lời gọi [JS]. Người viết chỉ viết ý; vai trò ảnh do hệ thống ghi.
4. Video có 3 kiểu nhận ảnh: **Start frame / End frame / Reference** — và hai kiểu frame vs reference **loại trừ nhau** trên cùng một
   nút video [JS i18n]. Giới hạn theo model: Seedance 2.5 ảnh 30 / video 10 / audio 10 / tổng 50 [JS].
5. Storyboard: người viết 1 đoạn chuyện → dịch vụ tách (Dify) ra N prompt khung (4/6/8) → vẽ khung 1 trước, các khung sau dùng
   **ảnh tham chiếu + khung 1 làm "neo liên tục"**, chạy tối đa 2 khung song song; không có ảnh tham chiếu thì vẽ tuần tự, mỗi khung
   dựa khung đầu + khung trước [JS].
6. Đổi ảnh nguồn ("Replace") chỉ thay ảnh ở nút đó; **không có đánh dấu "cũ"**, không có "chạy lại phía sau", không có "Run all".
   Người dùng tự bấm Run từng nút sau [JS — không tìm thấy logic stale/downstream].
7. UX người không chuyên: mỗi nút có đúng 1 nút **Run**, thông số là các "chip" bấm chọn, báo lỗi bằng câu thường có cách sửa,
   khen/chê kết quả có lý do chọn sẵn + "Regenerate" / "Try another model" [UI + JS i18n].

---

## 2. Các loại nút (node)

Thanh công cụ trái [UI]: Image · Storyboard · Video · Voice · Sound Effect · Audio-Video Composition · Skills · Add Text · Upload
Media · Assets · Pan. Mã khai báo 15 kiểu nút [JS `nodeTypes`]: `prompt`, `text2img`, `imageGen`, `img2img`, `storyboard`,
`text2video`, `videoGen`, `img2video`, `uploadImage`, `uploadVideo`, `uploadAudio`, `assets`, `tts`, `sfx`, `composition`
(nhà cung cấp: deepix cho ảnh/storyboard/ghép, "keling" (ClipAI) cho video, elevenlabs cho voice/SFX).

Mỗi nút hiển thị: tiêu đề · loại · trạng thái (Idle / Generating / Done / Failed) · ô prompt (thu/mở "Expand prompt") · hàng chip
thông số · đếm dây "N in · M out" · nút Run · Lock / Delete / Download [UI].

### 2.1 Prompt (văn bản)
- Trường: 1 textarea. Nút chạy ghi "Save Text" [JS i18n]. Cổng ra "text" chỉ nối vào **cổng Prompt input** của nút khác [JS].
- Nối dây prompt → nút đích **chép nguyên văn** prompt sang nút đích (`syncPromptConnectionsInState`) [JS]; vì vậy "Main Visual"
  có prompt giống hệt nút Prompt (209 ký tự) [UI].

### 2.2 Image (imageGen) — "Main Visual" trong demo
- Cổng vào: **Reference image** (ảnh) + **Prompt input** (chữ) [UI]. Cổng ra: ảnh ("Click to add next step, long-press to connect").
- Chip [UI]: model `GPT Image 2.5 Flare` · cỡ `Auto` · định dạng `PNG` · số ảnh `1 images` · nút **Agent** · **Run**.
- Model ảnh có trong mã [JS]: GPT Image 2.5 Flare (mặc định), GPT Image 2.5 Sunburst, GPT Image 2, GPT Image 1, Seedream 5.0 pro / lite,
  Nano Banana / 2 / pro, Qwen Image 2.0 pro. Số ảnh/lần 1/2/4. Cỡ: Auto, nhiều tỉ lệ cố định tới 4K, hoặc Custom (≥64 px, bội 16,
  cạnh dài ≤3840, tỉ lệ ≤3:1). Có "Thinking mode" và nền Opaque/Transparent [JS i18n].
- **Agent** = tối ưu prompt tự động (bật mặc định theo thông báo phát hành): "Agent considers your description, reference images,
  model, and size to understand your creative intent". Khi Agent hỏng → "Generating with your original description" (không chặn) [JS i18n].
- Công cụ sau khi có ảnh [UI]: Retry · View details · Good result / Bad result · Remove background · Enhance image · Layer image
  · Regional edit · Save to assets · Download original.
- Lời gọi thật [JS `createDeepixImageBatch`]: có ref → `image-to-image`, không → `text-to-image`; kiểm tra số ref ≤ giới hạn model;
  kiểm tra mọi `@Image N` trong prompt có ảnh tương ứng, sai thì chặn: "Reference @Image 3 was not found. Please choose an @
  reference again."; nối thêm khối "Reference image mapping".

### 2.3 Upload Image ("Reference Image" trong demo)
- Không có prompt hiển thị; prompt ẩn: "Reference image for preserving character identity and style." (60 ký tự) [JS demo].
- Nút: Replace · Remove background · Enhance image · Layer image · Regional edit · Lock · Delete [UI].
- Ảnh tải lên bị nén nếu quá lớn; storyboard từ chối ảnh >10 MB [JS i18n].

### 2.4 Storyboard
- Cổng vào: Reference image (ảnh) + Prompt input. Demo nhận 2 ảnh: Reference Image (= `@Image 1`) và Main Visual (= `@Image 2`) —
  nhãn "References 2/6" [UI].
- Thân nút: lưới 2×2 khung, mỗi khung có ảnh + textarea "Adjust this frame prompt..." (sửa được) + "View details" +
  **"Regenerate this frame"** + chấm kéo "Drag to connect storyboard frame N" (mỗi khung là một cổng ra riêng) [UI].
- Chip: model `GPT Image 2.5 Flare` · `Auto` · `PNG` · `4 frames` (chọn 4/6/8) · Good storyboard / Bad storyboard · Run [UI][JS].
- Cách sinh [JS `runDeepixStoryboardNode`, `splitFreeCanvasStoryToScenes`]:
  1. Prompt chuyện + (nếu prompt có `@Image`) khối mapping + câu luật: *"When splitting the story into frames, preserve explicit
     @Image references exactly. Do not merge different referenced subjects into one character…"* → gửi dịch vụ Dify
     (`event_type: storyboard`, `special_request` = số khung) → nhận N prompt khung.
  2. Có ảnh tham chiếu ("global"): vẽ **khung 1** với các ảnh tham chiếu; rồi các khung 2..N chạy **≤2 song song** với ảnh tham chiếu
     + khung 1. Dòng vai trò khung 1 trong mapping: *"first generated frame visual continuity anchor; inherit style, color palette,
     lighting mood, character appearance, and world details."*
  3. Không có ảnh tham chiếu ("sequential"): vẽ tuần tự; khung k dùng khung 1 + khung k−1 (*"previous generated frame continuity
     anchor; maintain temporal and visual continuity."*). Một khung hỏng → các khung sau đánh "Skipped".
  4. Mỗi lời gọi khung gửi kèm `story_text`, `frame_index`, `group_size`, `storyboard_size_profile: "clipai-video"`, `ref_mode`.
- Prompt khung do **hệ thống sinh**; người dùng sửa từng khung và vẽ lại riêng khung đó.

### 2.5 Video (videoGen)
- Cổng vào [UI]: **Start frame** · **End frame** · Prompt input · **Reference image input 2/30** · Reference video input 0/10 ·
  Reference audio input 0/10. Cổng ra: video.
- Chip [UI]: `Seedance 2.5` · task `Media reference` (khác: Video edit, Video extension) · `5s` · `720p` · `16:9` · `Silent` ·
  `1 videos` · Run.
- Model video [JS]: Seedance 2.5 (`dreamina-seedance-2-5-260628`, mặc định), Seedance 2.0 / 2.0 fast, Kling v3 omni, Kling video O1,
  MiniMax H3. Thời lượng: Seedance 2.5 4–30 s; Seedance 2.0 & MiniMax 4–15 s; Kling 3–15 s. Phân giải Seedance 480p/720p/1080p
  (mặc định 720p). Tỉ lệ Seedance 16:9, 4:3, 1:1, 3:4, 9:16, 21:9, adaptive. Kling: chế độ std/pro/4k, tiếng on/off.
- Giới hạn tham chiếu theo model [JS `VIDEO_MODEL_MEDIA_LIMITS`]:

  | Model | ảnh | video | audio | tổng |
  |---|---|---|---|---|
  | Seedance 2.5 | 30 | 10 | 10 | 50 |
  | Seedance 2.0 / 2.0 fast | 9 | 3 | 3 | – |
  | MiniMax H3 | 9 | 3 | 3 | – (bắt buộc ≥1 ảnh) |
  | Kling v3 omni / video O1 | 10 | 1 | 0 | – |

- Luật nối [JS i18n]: *"This video already has a start or end frame, so it cannot also use a reference image"* và ngược lại —
  **khung đầu/cuối và ảnh tham chiếu loại trừ nhau** trên cùng nút. Khi gửi, ảnh sắp xếp first_frame → end_frame → reference_image.
- Demo (quan sát lạ) [UI+JS]: prompt video ghi "Use storyboard frame 1 as the start frame and frame 2 as the end frame…", nhưng dây
  thật trong demo có vai **reference** (cổng Start/End frame không sáng, "Reference image input 2/30" sáng). Chip hiện `5s` nhưng
  dòng meta "3s · 16:9 · Seedance 2.5" (demo đặt duration = 3). → chữ trong prompt KHÔNG quyết định vai ảnh; vai do dây.

### 2.6 Voice (tts) và Sound Effect (sfx)
- Voice: ElevenLabs `eleven_v3`; chip voice / stability / similarity / speed [JS]. Không có trong demo.
- SFX [UI]: `eleven_text_to_sound_v2` · `9` (giây, 0,5–30 hoặc auto) · `0.3` (prompt influence) · `Off` (loop) · `MP3 44100_128`.
  Chỉ có cổng Prompt input.

### 2.7 Audio-Video Composition
- Cổng vào: **Video track** (nhiều video, theo thứ tự) + **Audio track** (hiện chỉ 1 clip audio thêm) [UI][JS i18n].
- Thân nút: trình phát + timeline 0–28 s, hàng Video ×3 + Sound Effect; Mute từng track, "Add audio track", "Download composition
  video" [UI]. Gợi ý khi >N clip: "Consider splitting them into multiple composition nodes for better stability" [JS i18n].
- Prompt ghép (72 ký tự) chỉ là ghi chú; ghép là thao tác máy, không AI [SUY từ "Canvas Composition" model label].

---

## 3. Sơ đồ luồng demo (ASCII)

```
[Prompt: Character Reference Prompt] --prompt--> [Image: Main Visual (GPT Image 2.5 Flare)]
        209 ký tự, chép sang                      ảnh chibi 3D (original.png)
                                                         |
[Upload: Reference Image (refrence.png)] --ref @Image 1--+--ref @Image 2-->
                                                         v
                         [Storyboard: 4 frames (GPT Image 2.5 Flare), References 2/6]
                          story 191 ký tự  →  Dify tách  →  4 prompt khung 379–419 ký tự
                          khung1 ─ khung2 ─ khung3 ─ khung4   (mỗi khung = 1 cổng ra)
                            │  \    │  \    │  \    │
                            v   v   v   v   v   v   v
                       [Video 1]   [Video 2]   [Video 3]      Seedance 2.5 · 720p · 16:9 · Silent · 3s
                       f1+f2       f2+f3       f3+f4          (vai dây = reference)
                       99 ký tự    99 ký tự    28 ký tự
                            \          |          /
                             video_track ×3 (theo thứ tự)
                                       v
[SFX: eleven_text_to_sound_v2, 9s] --audio_track--> [Audio-Video Composition, 9 s] → Download MP4
```

13 dây: 1 prompt · 2 reference vào storyboard · 6 storyboard-frame → video · 3 video_track · 1 audio_track [UI+JS].

---

## 4. Toàn văn prompt trong demo

| # | Nút | Ai viết | Ký tự | Nguyên văn |
|---|---|---|---|---|
| P1 | Character Reference Prompt (Prompt) | người | 209 | Transform this 2D cartoon character into a premium stylized 3D chibi character while preserving the original character's identity, facial features, hairstyle, outfit colors, proportions, and iconic expression. |
| P2 | Main Visual (Image) | chép từ P1 qua dây | 209 | (giống P1) |
| P3 | Reference Image (Upload, ẩn) | hệ thống/mẫu | 60 | Reference image for preserving character identity and style. |
| P4 | Storyboard — chuyện | người | 191 | A warm realistic anime sequence at dawn: one joyful boy in @Image 2 runs through a quiet residential street, approaches the boy in  @Image 1, and the two boys collide into a laughing embrace. |
| P5 | Khung 1 | hệ thống tách | 407 | A panoramic view of the street at dawn, with soft sunlight streaming onto the pavement. In Figure 1, a boy dressed in light clothing runs down the street with a beaming smile, against the backdrop of a quiet residential neighborhood. The shot is taken from a low, eye-level angle, highlighting his light, nimble strides and joyful expression. The visual style is consistent with a realistic anime aesthetic. |
| P6 | Khung 2 | hệ thống tách | 419 | Mid-shot: The camera follows the direction of the boy from Figure 1 as he runs. His figure gradually approaches the boy from Figure 2, who is walking ahead. The street is lined with trees casting dappled shadows, and sunlight filters through the leaves to form patches of light. The atmosphere is lighthearted and joyful. The shot features slight motion blur to emphasize the sense of speed and the impending encounter. |
| P7 | Khung 3 | hệ thống tách | 381 | Close-up: The boy from Figure 1 excitedly spreads his arms and lunges toward the boy from Figure 2. Both boys' expressions are filled with surprise and laughter. The action is frozen at the moment just before they embrace. The background is slightly blurred, with the focus centered on their faces and movements. Sunlight illuminates their faces from the side, casting a warm glow. |
| P8 | Khung 4 | hệ thống tách | 379 | A medium-close-up: The two boys have already collided and are now embracing and laughing. The frame captures the moment of their smiles and friendship; both boys in Figure 1 and Figure 2 wear happy expressions. Sunlight bathes them, while the street background is softly blurred. The overall atmosphere is warm and cheerful, with bright, unified tones in a realistic anime style. |
| P9 | Video 1 | người (mẫu) | 99 | Use storyboard frame 1 as the start frame and frame 2 as the end frame to generate a coherent shot. |
| P10 | Video 2 | người (mẫu) | 99 | Use storyboard frame 2 as the start frame and frame 3 as the end frame to generate a coherent shot. |
| P11 | Video 3 | người | 28 | They happily hug each other. |
| P12 | Sound Effect | người | 114 | A soft 9-second background music bed for a rainy lake scene, gentle and continuous for the storyboard composition. |
| P13 | Composition | người (ghi chú) | 72 | Compose 3 storyboard videos in sequence and add the sound effects track. |

Phần **hệ thống tự nối** vào lời gọi (không hiện trên UI) [JS]:
```
Reference image mapping:
Image 1 (@Image 1): <tên file>; user reference image 1; preserve visible identity, subject details, and style cues.
Image 2 (@Image 2): <tên file>; user reference image 2; preserve visible identity, subject details, and style cues.
```
(~120 ký tự/ảnh). Khung storyboard còn thêm dòng "first generated frame visual continuity anchor…" / "previous generated frame
continuity anchor…".

Nhận xét:
- Prompt khung KHÔNG tả lại ngoại hình nhân vật (không màu tóc, quần áo) — chỉ gọi "boy in Figure 1/2" + cỡ cảnh, góc máy, ánh sáng,
  cảm xúc. Ngoại hình hoàn toàn để ảnh lo [UI].
- **Lệch đánh số** trong demo: chuyện nói "boy in @Image 2 runs… approaches the boy in @Image 1", nhưng khung 1 lại viết
  "In Figure 1, a boy … runs" → người chạy thành Figure 1. Prompt khung demo là chuỗi cứng `DEMO_FRAME_PROMPTS` (dịch từ bản tách
  tiếng Trung "图1" → "Figure 1") [JS]. Bài học: đánh số ảnh dễ trôi khi qua một bước AI viết lại → cần kiểm tra máy (xem §7.1-e).
- Prompt video chỉ 28–99 ký tự: khung đầu/cuối đã chứa bố cục, nhân vật, bối cảnh; chữ chỉ nói chuyển động/ý đồ.

---

## 5. Cách gắn và gọi tên tham chiếu

| Việc | Weave Canvas | Nguồn |
|---|---|---|
| Gắn ảnh | kéo dây từ nút ảnh vào cổng "Reference image" / "Start frame" / "End frame" của nút đích | [UI] |
| Số thứ tự | `Image N` = thứ tự dây vào, hiện dải ảnh nhỏ "References 2/6" (tối đa 4 ảnh xem trước + "+n") | [UI][JS] |
| Gọi trong prompt | gõ `@` → menu chọn ảnh → chèn `@Image N` (nhận cả `@Ảnh N`, `@图N`, `@Imagen N`) | [JS referenceMentionUtils] |
| Chưa nối ảnh mà gõ @ | "Connect an image first" | [JS i18n] |
| @ sai số | chặn trước khi gửi: "Reference @Image N was not found…" | [JS] |
| Quá giới hạn | chặn: "Reference images exceed this model limit: 7/6. Remove extra references or switch models." | [JS i18n] |
| Vai trò ảnh | do LOẠI CỔNG (first_frame / last_frame / reference / reference_video / reference_audio / video_track / audio_track), không do chữ | [JS edgeRoles] |
| Dòng vai trò gửi model | 1 dòng/ảnh, mẫu cố định "preserve visible identity, subject details, and style cues" | [JS] |
| Ảnh khung storyboard | mỗi khung là 1 cổng ra riêng, kéo thẳng vào Start/End frame video | [UI] |

---

## 6. Đổi ảnh nguồn — các nút sau xử lý ra sao

- **Replace** trên nút Upload: thay asset tại chỗ, trạng thái Running → Done, toast "File replaced". Mã chỉ cập nhật nút đó
  (`replaceFileNodeFromUpload`/`replaceFileNodeFromMaterial`) [JS].
- Không tìm thấy trong mã từ khóa/logic "stale", "outdated", "downstream", "run all", "run selected" [JS — tìm 0 kết quả]. Các nút
  phía sau **giữ kết quả cũ, không có dấu cũ**; muốn cập nhật phải bấm Run từng nút theo thứ tự [SUY từ mã, chưa chạy].
- Chữ thì khác: dây prompt chép văn bản tức thì sang nút đích khi lưu/nạp [JS].
- Storyboard: sửa 1 khung + "Regenerate this frame" (vẽ lại riêng khung đó); ảnh ref hết hạn → "Reference images expired, please
  regenerate the entire storyboard" [JS i18n].
- Lưu kết quả có khôi phục: ảnh sinh ra mà đăng ký/lưu canvas lỗi → nút "Recover result" / "Retry save", "the image will not be
  generated again" [JS i18n].
- Video chờ lâu: *"Stopped waiting, but the task is still generating. Click Run again later to pick up the result without being
  charged twice."* — bấm Run lại nhận kết quả cũ, không tính tiền hai lần [JS i18n].

→ Điểm yếu của Weave mà ta **không nên chép**: không đánh dấu phụ thuộc. Ta đã có ý S-D (đánh dấu cũ đúng ảnh/clip phụ thuộc) —
giữ nguyên hướng đó.

---

## 7. UX cho người không chuyên

| Điểm | Weave | Nguồn |
|---|---|---|
| Số thao tác tạo 1 clip từ ảnh có sẵn | thả ảnh → bấm chấm cổng ra "Click to add next step" chọn "Video generation" (tạo nút + dây + prompt gợi ý sẵn) → Run = **3 thao tác** | [UI tooltip + JS `continuation.videoFromImagePrompt`] |
| Prompt gợi ý khi tạo bước tiếp | "Use "{{title}}" as the start frame and generate a natural, coherent video with camera motion." / "Split "{{title}}" into 4 continuous shots while keeping the character, scene, and mood consistent." | [JS i18n] |
| Chữ trên nút | động từ đời thường: Generate Image / Generate Storyboard / Generate Video / Compose / Replace / Regenerate this frame | [JS i18n] |
| Thông số | chip bấm chọn (model, 5s, 720p, 16:9, Silent, 1 videos), mặc định an toàn (720p, Seedance 2.5) | [UI] |
| Chặn sớm | sai @, quá số ref, nối sai cổng ("Image nodes can only connect to image, start-frame, or end-frame inputs") — chặn ngay khi nối/gửi | [JS i18n] |
| Báo lỗi video | câu thường + cách sửa: "The face angle in the reference is too large. Use a clearer front-facing image." · "The reference image may contain a real person's face… Cover the face and try again" · "triggered a copyright review. Avoid brand logos, film, anime or game characters…" | [JS i18n] |
| Lỗi một phần | "3/4 images generated, 1 failed"; khung storyboard hỏng: "Generation failed", sau đó "Skipped" | [JS i18n] |
| Khen/chê | popup "Happy with this result? · Like it if it works for you · Dislike it and tell us why"; chê → "What went wrong?" chọn: Doesn't match prompt / Distorted people or hands / Wrong style / **Ignored reference image** / Low quality… ; storyboard: **Characters change between frames / Art style changes between frames / Frames don't flow as a story / Repetitive or monotonous shots**; sau đó "You can regenerate or try another model" + nút Regenerate / Try another model | [UI + JS i18n] |
| Giá | KHÔNG hiện trên nút canvas demo; thông báo phát hành nói chi phí hiện dưới mỗi kết quả ảnh + lọc chi phí theo ngày ở trang chủ | [UI không thấy; JS i18n] |
| Quyền / đăng nhập | demo không cần đăng nhập; tạo canvas mới cần đăng nhập; video cần xin quyền qua nhóm Seatalk | [JS i18n] |
| Khác | Lock node, Smart layout, Align, Undo/Redo, Export JSON canvas | [UI][JS] |

---

## 8. So sánh với pipeline của ta

Số đo ta: `docs/data/goi_gui_31_33_2026-10-21.md` (gói thật đã gửi ClipAI).

| Chỉ số | Weave demo | #31 | #33 | Ghi chú |
|---|---|---|---|---|
| Prompt ảnh (ký tự) | 209 (ảnh) · 379–419 (khung) + ~120/ref mapping | TB 5.380 (max 11.473) | TB 11.059 (max 13.419) | Ta dài gấp 13–55 lần |
| Prompt video (ký tự) | 28–99 | TB 3.029 (max 4.858) | TB 4.045 | gấp 30–140 lần |
| Số ref ảnh | 1–2 (+ khung 1 làm neo) | TB 6,2, max 9 | TB 5,8, max 7 | |
| Số ref video | 2 (khung kề nhau) | TB 4,9, max 15 | TB 8,5, max 13 | ta gửi khung đầu VÀ ảnh nhân vật/bối cảnh cùng lúc |
| Vai ảnh | do cổng (4 vai cố định) | 8 vai (character, object, place_render, character_form, atmosphere_sky, previous_scene…) | 3 vai | |
| Mô tả ngoại hình trong chữ | không | có (nhiều câu "same face, hairstyle…", luật chống trộn) | có | |
| Luật lặp lại trong mỗi prompt | không (luật nằm ở hệ thống tách storyboard 1 lần) | có (đoạn "Each person keeps ONLY…", "pick ONE visual anchor…") | có | |
| Liên tục giữa shot | khung 1 làm neo cho mọi khung; khung trước làm neo khi không có ref | previous_scene (13 lần #31, 30 lần #33) | | tương đương ý, ta dùng ít hơn |
| Khung đầu + ref cùng nút video | **cấm** (loại trừ) | 67/67 gói video có start_frame + thêm ref | 15/15 | Seedance 2.5 của Weave không cho trộn |
| Đổi ảnh → đánh dấu phụ thuộc | không | (kế hoạch S-D) | | ta nên hơn Weave ở điểm này |

Kết luận [SUY]: Weave dựa vào **ảnh làm nguồn sự thật**, chữ chỉ mô tả hành động/máy/không khí. Ta đang để chữ "nhắc lại" những gì ảnh
đã có, và thêm nhiều luật phòng thủ chép lặp mỗi gói → tốn ký tự, dễ mâu thuẫn ảnh. Riêng việc Weave cấm trộn khung đầu với ảnh tham
chiếu trên cùng nút video là tín hiệu mạnh rằng ta gửi "khung đầu + 4–13 ảnh tham chiếu" có thể đang làm model phân vân [SUY — cần A/B].
Lưu ý: demo Weave là cảnh đơn giản (2 nhân vật, 1 con phố), chưa chứng minh được cho cảnh nhiều nhân vật + bối cảnh 3D cố định như
#31/#33 — nên áp dụng có đo, không thay hẳn.

---

## 9. ĐỀ XUẤT cho M2.10 — gói gửi tối giản (ref-first)

Tất cả dưới cờ SHADOW TẮT, đo 0 USD trên gói thật #31/#33 trước, A/B trả phí chỉ khi EP duyệt giá (theo sổ v31-ep-m210…).

### 9.1 Khuôn prompt ẢNH (đích ≤ 900 ký tự, trần cứng 1.500)
```
[Khối vai trò — hệ thống sinh, 1 dòng/ảnh, ≤ 110 ký tự/dòng]
Image 1 (@Image 1): background — keep this exact place, camera and layout.
Image 2 (@Image 2): KELLY — face, hair, build.
Image 3 (@Image 3): KELLY ghost form — body surface and glow.
Image 4 (@Image 4): SKORP — object, exact look.
[Khối cảnh — người/Đạo diễn viết, 2–4 câu]
Medium close-up, eye level. @Image 2 stands in the hedge gap of @Image 1, catching her breath, SKORP lowered in her right hand.
Dusk light from the left, cold mist.
```
- Bỏ khỏi chữ: mọi mô tả mặt/tóc/quần áo đã có trong ảnh; các đoạn luật chung ("never swap or blend…", "pick ONE anchor…") → gom
  thành **1 câu cố định** cuối gói (≤ 150 ký tự) chỉ khi có ≥ 2 người.
- Vai trò ảnh lấy từ bảng vai cố định (≤ 6 vai: `background`, `person`, `person_form`, `object`, `sky`, `previous_shot`) — giống
  Weave lấy vai từ cổng, không để Đạo diễn tự viết vai.
- Gọi tên trong câu cảnh bằng `@Image N` (hoặc tên + số), **kiểm tra máy**: mọi `@Image N` phải có ảnh, mọi ảnh phải được gọi ít
  nhất 1 lần hoặc là `background`/`sky` (Weave chặn @ sai; ta thêm chặn ảnh thừa).

### 9.2 Khuôn prompt VIDEO (đích ≤ 400 ký tự)
- **Có khung đầu** (start_frame): gửi khung đầu (+ khung cuối nếu có) và **KHÔNG gửi lại** ảnh nhân vật/bối cảnh đã nhìn thấy trong
  khung; chữ = 1–3 câu chuyển động + máy + nhịp. Ví dụ: "Kelly's breathing slows, shoulders relax, eyes settle on camera. Static
  eye-level medium close-up, 3 s."
- **Ngoại lệ có đo**: chỉ thêm ref khi vật/nhân vật **xuất hiện mới trong clip** mà khung đầu không có (vd: kẻ địch bước vào) — tối đa
  2 ref thêm, dòng vai trò "appears later in the clip".
- Clip nhiều shot: thử kiểu Weave = **1 nút video / 1 cặp khung kề nhau** (start = khung shot k, end = khung shot k+1) thay vì 1 prompt
  dài nhiều shot — đưa vào A/B như nhánh C.

### 9.3 Bộ ảnh tối ưu theo shot (máy tính, 0 USD)
1. Bỏ ảnh trùng sha (đã thấy 9 ref trùng sha trong số đo 21/10).
2. Mỗi người ≤ 1 ảnh mặt + ≤ 1 ảnh dạng đặc biệt; vật ≤ 1 ảnh.
3. Video có khung đầu → bỏ ref nhân vật/bối cảnh đã có trong khung (theo danh sách người trong shot).
4. Trần: ảnh ≤ 5 ref; video ≤ 3 ref ngoài khung đầu/cuối.
5. Thứ tự: background → người (theo thứ tự xuất hiện trong câu) → vật → sky → previous_shot (Weave: thứ tự cổng quyết định số).

### 9.4 Đo 0 USD (trước A/B)
- Chạy builder lean SHADOW trên 136 gói ảnh + 82 gói video thật: in ký tự TB/trung vị/max, số ref, số ảnh bị bỏ + lý do, số `@`
  không khớp. Đích: ảnh TB ≤ 900 ký tự, video ≤ 400, ref ảnh TB ≤ 4,5, ref video ngoài khung ≤ 1.
- Bảng đối chiếu từng gói: thông tin nào bị bỏ (để Đạo diễn/EP xem có mất ý không).

### 9.5 A/B trả phí (chỉ khi EP duyệt giá, chạy `tools/pregen_check.py` trước)
- 3 nhánh × cùng shot: A = gói hiện tại; B = lean ref-first; C = lean + video theo cặp khung đầu/cuối. Chấm: giữ nhân vật, giữ bối
  cảnh 3D, đúng hành động, độ chuyển động (không đơ). Cỡ mẫu nhỏ, giá báo trước theo sổ chi.

---

## 10. ĐỀ XUẤT cho M8.1 — chế độ Đơn giản

### 10.1 Thẻ cảnh (mượn nút Storyboard + Video của Weave)
```
┌─ Cảnh 3 · Kelly thở dốc trong khe rào ───────────── [Đã xong ✓] ┐
│ [ảnh khung]   Ảnh dùng:  (Kelly) (Kelly ma) (SKORP) (Cổng Trời) [+] │
│               Câu cảnh: "Kelly thở dốc, hạ SKORP xuống"   [Sửa]   │
│ [clip 3s]     Video: 3 giây · 720p · có tiếng          [Đổi]      │
│ 👍 Ưng   👎 Chưa ưng      [Vẽ lại ảnh]  [Làm lại video]           │
└────────────────────────────────────────────────────────────────────┘
```
- Mỗi cảnh 1 thẻ: ảnh khung + clip + "Ảnh dùng" (chip ảnh tham chiếu, lấy từ bộ ảnh M2.10) + 1 câu cảnh (khối cảnh M2.10). Ẩn prompt
  đầy đủ (nút "Xem chi tiết" cho chế độ Chuyên gia).
- Thông số dạng chip, mặc định an toàn (giống Weave: 720p, Seedance 2.5, im lặng/có tiếng).
- Bước kế tiếp gợi ý sẵn (Weave "Click to add next step") → ta: nút "Làm video từ ảnh này" tạo sẵn câu "Bắt đầu từ ảnh này, chuyển
  động tự nhiên".

### 10.2 Đổi ảnh tham chiếu = gắn ảnh + 1 câu
1. Bấm chip ảnh → "Thay ảnh" (chọn từ Kho / tải lên) hoặc [+] "Thêm ảnh" → chọn vai trong danh sách ngắn (Nhân vật / Dạng đặc biệt /
   Đồ vật / Bầu trời / Bối cảnh) — vai từ danh sách như cổng Weave, không gõ.
2. Gõ 1 câu (tuỳ chọn): "Kelly cầm SKORP bằng tay phải".
3. Máy kiểm tra ngay (như Weave chặn @ sai / quá giới hạn): ảnh thừa, ảnh trùng, quá trần ref của model, ảnh người thật (cảnh báo
   Seedance), khung đầu + ref mâu thuẫn.
4. **Hơn Weave**: hiện ngay danh sách thứ bị cũ theo S-D — "Đổi ảnh này sẽ làm cũ: ảnh cảnh 3, 4 · clip 3, 4 — Vẽ lại 4 mục,
   ước ~X USD" → 1 nút "Vẽ lại các mục cũ" (mỗi lần gen vẫn qua bước xin duyệt giá như hiện nay). Thẻ cũ có viền cam "Cần vẽ lại".

### 10.3 Khi lỗi (nối C-M81B)
- Dịch lỗi model sang câu thường + cách sửa, mỗi câu kèm **1 nút hành động** (mượn danh sách lỗi video Weave):

  | Lỗi | Câu hiển thị | Nút |
  |---|---|---|
  | lọc người thật | "Ảnh tham chiếu có thể bị coi là mặt người thật. Che mặt hoặc dùng ảnh đã đánh dấu." | Đổi ảnh |
  | an toàn / bản quyền | "Nội dung bị bộ lọc chặn. Bỏ logo/nhân vật có bản quyền khỏi ảnh hoặc câu." | Sửa câu |
  | quá giới hạn ref | "Cảnh này dùng 7 ảnh, model chỉ nhận 6. Bỏ bớt 1 ảnh." | Mở Ảnh dùng |
  | quá hạn chờ | "Vẫn đang tạo. Bấm 'Lấy kết quả' sau — không tính tiền lại." | Lấy kết quả |
  | tạo được 3/4 | "3/4 ảnh xong, 1 lỗi." | Vẽ lại ảnh lỗi |
- Học Weave: **"Lấy kết quả không tính tiền hai lần"** (nhận lại task đang chạy thay vì gửi mới) và **"Lưu lỗi ≠ gen lỗi"** (Retry
  save / Recover result không gen lại). Đề xuất ta kiểm tra: nút làm lại trên Dashboard có dò task đang chạy/đã xong trước khi gửi
  mới không [SUY — cần rà code].
- 👎 Chưa ưng → chọn lý do có sẵn (mượn danh sách Weave, Việt hoá): "Không giống nhân vật", "Bỏ qua ảnh tham chiếu", "Nhân vật đổi
  giữa các cảnh", "Sai bối cảnh 3D", "Người đứng đơ", "Méo tay/mặt" → mỗi lý do map sang 1 hành động gợi ý (đổi ảnh / sửa câu / vẽ lại
  / đổi model) và ghi vào nhật ký bài học (Tổ rà soát / vai chịu trách nhiệm).

### 10.4 Số đo đề xuất cho M8.1
- Thao tác để đổi 1 ảnh tham chiếu và vẽ lại các mục phụ thuộc: đích ≤ 4 bấm (Weave: Replace + Run từng nút, không biết nút nào cũ).
- Thao tác để sửa 1 cảnh lỗi: ≤ 3 bấm từ thẻ cảnh.
- Số ký tự người dùng phải đọc/viết mỗi cảnh: ≤ 1 câu (≤ 120 ký tự).

---

## 11. Những gì CHƯA xem được / giới hạn

- Không bấm mở menu chọn model/chip (tránh sửa canvas) → danh sách model/thời lượng lấy từ mã, không từ menu hiển thị.
- Không thấy giá trên canvas demo; chưa biết đơn giá Seedance/GPT Image trên Deepix.
- Không xem được hệ thống prompt bên Dify (tách storyboard) — chỉ thấy đầu vào gửi đi.
- Không có trang tài liệu/trợ giúp công khai cùng miền được mở trong phiên này; chỉ dùng trang demo + mã JS cùng miền.
- Một lần đọc mã đã vô tình tải lại tệp gtag (googletagmanager.com, tệp trang đã tự nạp) khi lặp qua `document.scripts` — chỉ đọc,
  không gửi dữ liệu; các lần sau giới hạn trong deepix.ingarena.net.
