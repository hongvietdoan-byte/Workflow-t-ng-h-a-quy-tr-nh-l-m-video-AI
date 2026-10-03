# So sánh với nền tảng / studio video AI trọn gói (nhóm A) — 2026-10-03

> Cập nhật và mở rộng `docs/SO_SANH_PHAN_MEM_NGOAI_2026-09-29.md`. **0 USD**: chỉ đọc web công khai, không đăng ký / đăng nhập / tải tệp / gọi API.
> Không sửa code, không sửa TODO.md. Mục 6 chỉ là **đề xuất** chờ người dùng chọn.

## 0. Cách làm và giới hạn
- Ngày đọc: **2026-10-03**. Mức nguồn: **[A]** hãng (trang chính thức / blog / thông cáo của hãng) · **[B]** bên thứ ba (bài review, trang giá tổng hợp — có thể sai hoặc cũ) · **[R]** repo của mình. Ô không có nguồn: **"không rõ"**. Lời trích ≤ 15 từ.
- **Không thử tay sản phẩm nào** → mọi thứ là *tính năng được công bố*, không phải chất lượng thật. Không thấy trên trang công khai ≠ không có.
- Nguồn [A] đọc được: Dreamina Seedance 2.5 (trang + thông cáo PR Newswire), Google Flow (blog.google tháng 2/2026), Higgsfield Cinema Studio 4.0 (blog hãng), Katalist (trang hãng), HeyGen / Synthesia (kết quả tìm kiếm từ trang hãng), Invideo (blog hãng), Runway (kết quả tìm kiếm từ trang hãng / changelog). **Không tải được**: trang LTX (lỗi header), trang giá Kling (không có số), changelog Runway (từ chối kết nối) → các số giá của LTX / Runway / Kling / Luma / Pika / OpusClip / CapCut / HeyGen **chỉ ở mức [B]**.
- **Không tìm được nguồn đủ tin cho**: "Captions" (app) — không có kết quả riêng, ghi "không rõ"; Luma / Pika chỉ có [B]; Katalist 2026 chỉ có trang giới thiệu.
- Giá thay đổi nhanh và các bài [B] mâu thuẫn nhau (ví dụ Veo 4: có nguồn nói đã ra tháng 4/2026, có nguồn nói Google chưa công bố) → **không dùng các con số này để lập ngân sách**, chỉ để so mô hình tính tiền.

## 1. Thay đổi so với bản 29/09 (tóm)
Khoảng cách chỉ 4 ngày nên "thay đổi" gồm: (a) thông tin mới tôi phát hiện thêm, (b) sản phẩm bản 29/09 chưa phủ.

| # | Thay đổi | Ảnh hưởng tới mình |
|---|---|---|
| 1 | **Seedance 2.5** ra mắt toàn cầu 31/07/2026 trên Dreamina / CapCut [A]: clip tới 30 s, chế độ video dài (beta) tới 180 s, tới 50 tài sản tham chiếu (30 ảnh / 10 video / 10 âm), **Intelligent Edit Mode** sửa theo mốc thời gian / nhân vật / vật không phải sinh lại, tích hợp phông xanh, mô hình trắng 3D, tài sản Blender / Maya, giá hãng ghi $0,097/s so với $0,066/s của 2.0 [A thông cáo] | Cùng model mình đang dùng qua ClipAI. **Sửa cục bộ** (X2/S4.12) giờ đã có ở model gốc — cần kiểm ClipAI có mở chức năng này qua API không. Giá 2.5 đắt hơn 2.0 ~47 % → phải phản ánh vào ước tính trước. |
| 2 | **Sora đã chết**: app + web tắt 26/04/2026, API Sora 2 tắt 24/09/2026 [B nhiều nguồn, gồm TechCrunch] | Không còn đối thủ để so; bản 29/09 không có Sora — giữ nguyên, ghi "đã ngừng". |
| 3 | **MiniMax H3 (Hailuo 3.0)** 31/07/2026 [B]: 2K, âm stereo sinh cùng hình, 4–15 s, tới 9 ảnh + 3 video + 3 âm tham chiếu, **sửa theo chỉ dẫn** (đổi vật, ánh sáng, thay thoại có môi mới), ~$0,13/s 2K, mở trọng số 03/08 [B] | Bản 29/09 chỉ có tin H3 đa shot; nay thêm "sửa theo chỉ dẫn" + trọng số mở. |
| 4 | **Higgsfield Cinema Studio 4.0** [A blog hãng]: clip tới 30 s, **trợ lý (Assistant) tách kịch bản thành shot có sẵn thông số máy**, **nhiều người cùng sinh trong một dự án**, **chia sẻ Element cho cả nhóm**, Canvas chung, Project Brief | Bản 29/09 mới có Popcorn / Soul ID. Phần làm việc nhóm là **mới**. |
| 5 | **Runway** [B + kết quả tìm kiếm trang hãng]: Gen-4.5, **Aleph 2** (sửa video), xuất **ProRes 4444 + PCM** hoặc PNG tuần tự, **Workflows** (ghép nhiều model thành đường ống gọi qua API), **Characters** (avatar thời gian thực) | Xuất ProRes / PNG tuần tự củng cố đề xuất "xuất ra phần mềm dựng" (X6). |
| 6 | **Google Flow tháng 2/2026** [A]: gộp Whisk + ImageFX vào Flow, lưới tài sản + **Collections**, công cụ lasso, sửa bằng ngôn ngữ ("xóa người đàn ông"), Extend, thêm / xóa vật, điều khiển máy, "@" gọi tài sản | Quản lý tài sản + sửa bằng chữ trong cùng chỗ là mẫu UI đáng tham khảo cho Kho tài nguyên. |
| 7 | **Kling 3.0 Turbo + Omni nâng cấp** (tính đến 17/06/2026) [B]; Kling 3.5: **không tìm thấy** | Không có gì đổi cho mình. |
| 8 | **Synthesia** 15/07/2026: Assistant (chat một câu → video có thương hiệu) + Express-3 [B qua tìm kiếm từ trang hãng]; **HeyGen** Avatar V (08/04/2026), Video Agent 2.0 **hiện bản kế hoạch (avatar, cảnh, hình) để duyệt trước khi dựng** [B qua trang hãng] | Mẫu "xem kế hoạch → duyệt → mới dựng" giống cổng duyệt Director của mình — xác nhận hướng đúng, không phải thiếu sót. |
| 9 | **Invideo AI** [A blog hãng]: "đội" tác tử (nhà sản xuất, storyboard, casting, trang phục, thiết kế bối cảnh, nhiều quay phim) chạy 6–8 tác tử song song, **mỗi shot chọn model riêng** (Veo / Kling / Seedance 2.0) | Gần nhất với "chọn model theo từng cảnh" + tổ làm phim của mình. Họ công bố cùng ý tưởng; mình hơn ở chỗ có **số đo thật** (A/B) và **khóa chi phí**. |
| 10 | **Katalist** 2026 [A]: Storyboarding Agent (nhiều biến thể mỗi cảnh), animatic có giọng đọc từng khung, Story Canvas (nhóm cùng làm), Video Studio có giọng + nhạc + SFX | Animatic có giọng — mình đã có (S2.4); hết "LTX không rõ có thoại thật" cho nhóm này. |
| 11 | **LTX** [B]: LTX-2.3 (03/2026) 4K dọc, keyframe, Audio-to-Video (khớp môi từ âm), **Retake** (đạo diễn lại một khoảnh khắc trong shot không sinh lại cả shot), Storyboard dựng lại nhanh hơn 5×; giá Lite 15 / Standard 35 / Pro 125 USD/tháng [B] | Retake = cùng loại với sửa cục bộ. |
| 12 | **Luma** Ray 3.14 [B]: 1080p, nhanh hơn 4×, rẻ hơn ~3× so Ray3 ở 720p; **bỏ gói miễn phí** (tính đến 09/2026) [B] | Không ảnh hưởng. |
| 13 | **Pika 2.5** [B]: Pikaframes tới 25 s, Pikascenes / Pikadditions / Pikaswaps / Pikatwists | Chủ yếu hiệu ứng; không liên quan pipeline. |

Không đổi / không kiểm lại được: Hedra, ElevenLabs, OpenArt, Kling Native Audio **không có tiếng Việt** (bản 29/09 [A] — chưa kiểm lại hôm nay).

## 2. Từng sản phẩm
Ký hiệu cột "Mạnh / yếu" theo các tiêu chí: **KB** kịch bản→shot · **NV** nhân vật / bối cảnh nhất quán · **SB** storyboard / animatic · **MS** đa shot · **LS** khớp môi / giọng · **ÂT** nhạc / SFX · **DỰNG** · **QC** · **GIÁ** chi phí / cổng duyệt · **NHÓM** làm việc nhóm / phân quyền · **UI**.

### 2.1 LTX Studio — kịch bản → phim trọn gói
- **Cập nhật 2026** [B]: LTX-2.3 (03/2026), 4K dọc, keyframe, Audio-to-Video, Retake, Elements / Projects, storyboard dựng nhanh hơn. Bản 29/09 [A]: tự tách kịch bản thành cảnh / shot, tự rút Element, sửa Element lan mọi chỗ, nhân vật gán giọng, SFX khớp hành động từ hình.
- **Tiền** [B]: Lite 15 / Standard 35 / Pro 125 USD/tháng + Enterprise, giảm 20 % theo năm; trả bằng credit hằng tháng.
- **Mạnh**: KB, NV (Elements), SB (storyboard khóa cấu trúc trước khi sinh → ít lãng phí), DỰNG (trình dựng web), ÂT. **Yếu / không rõ**: QC (không công bố), GIÁ (không rõ có trần theo dự án), NHÓM (có gói Enterprise, chi tiết phân quyền không rõ), LS tiếng Việt không rõ.

### 2.2 Runway (Gen-4.5 / Aleph 2 / Act-Two / Workflows)
- **Cập nhật** [B + tìm kiếm trang hãng]: Gen-4.5 (API từ 10/02/2026, 2–10 s); Aleph 2 sửa video; xuất ProRes 4444 / PNG tuần tự; Workflows (đường ống nhiều model qua API); Characters (avatar thời gian thực).
- **Tiền** [B]: credit; Gen-4.5 ≈ 12 credit/s (API $0,12/s), Aleph 2 ≈ 28 credit/s, Act-Two ≈ 5 credit/s; gói Free / Standard 15 / Pro 35 / Max 95 USD; Unlimited có Explore Mode (hàng chậm, không tốn credit) [A bản 29/09].
- **Mạnh**: DỰNG / sửa sau khi sinh (Aleph), diễn thật điều khiển nhân vật (Act-Two), xuất chất lượng cao, API / Workflows. **Yếu**: KB, SB, ÂT (không phải trọng tâm), QC không công bố.

### 2.3 Higgsfield (nền tảng tổng hợp + Cinema Studio 4.0)
- **Cập nhật** [A blog hãng]: Cinema Studio 4.0 (clip tới 30 s, xuất tới 1080p, chỉnh màu / hậu kỳ trước khi xuất); trợ lý tách kịch bản thành shot có thông số máy; **sinh đồng thời nhiều người**, **chia sẻ Element**, Canvas chung, Project Brief. [B]: Higgsfield Assist (gợi ý prompt, cảnh báo lỗi trước khi tốn credit), tích hợp Seedance 2.0.
- **Tiền** [B]: Starter 19 (270 credit), Plus 47–59 (1.200), Ultra 99–129 (3.000) USD/tháng; Cinema Studio ~25 credit / 5 s 720p, 50 credit / 5 s 1080p. Có báo cáo [B] về "Unlimited" có điều kiện kèm — chưa xác minh.
- **Mạnh**: NHÓM (mới nhất, rõ nhất trong nhóm A), KB (trợ lý), MS (điều khiển máy từng shot), tổng hợp nhiều model, NV (Soul ID). **Yếu**: QC không công bố; GIÁ chỉ là số dư credit.

### 2.4 Kling 3.x
- **Cập nhật**: 3.0 ra 05/02/2026 [B]; Kling 3.0 Turbo + Omni nâng cấp (tới 06/2026) [B]; Multi-Shot tới 6 shot / khoảng 15 s trong một lần, Elements, Start & End Frame, Native Audio (**không có tiếng Việt** [A bản 29/09]), 4K 60 fps [B]. Kling 3.5: không tìm thấy.
- **Tiền** [B]: Free (66 credit/ngày), Standard 6,99 (660), Pro 29,99 (3.000), Ultra 59,99 (8.000) USD/tháng; giá theo giây [A bản 29/09].
- **Mạnh**: MS, NV (Elements gắn giọng), giá. **Yếu**: LS tiếng Việt, KB / SB / DỰNG / QC (không phải sản phẩm dựng phim).

### 2.5 Dreamina / Seedance 2.5 (và CapCut)
- **Cập nhật** [A]: xem mục 1 dòng 1. Còn: Seedance 2.5 rolling out trên CapCut (Châu Âu, Châu Á, Trung Đông, Nam Mỹ) [A]; Dreamina AI Agent sắp tới 40 khung đồng bộ [A bản 29/09]. Ngôn ngữ cụ thể: hãng **không nêu** trong trang đọc được (mình đã có ghi chú riêng ở `reference_clipai_docs_2026_09`: 2.5 có tiếng Việt).
- **Tiền** [A thông cáo]: $0,097/s (2.5) vs $0,066/s (2.0), qua gói đăng ký đủ điều kiện. CapCut [B]: Standard 9,99 / Pro 19,99 USD/tháng (Pro có 4K + bộ AI đầy đủ).
- **Mạnh**: MS / clip dài, NV (50 tham chiếu), sửa cục bộ, DỰNG (CapCut là trình dựng thật). **Yếu**: QC, GIÁ trần, NHÓM (không rõ).

### 2.6 Google Flow (Veo 3.1)
- **Cập nhật** [A blog.google 02/2026]: gộp tạo ảnh vào Flow, lưới tài sản + Collections, lasso + sửa bằng chữ, Extend, thêm / xóa vật, điều khiển máy; từ trước: Ingredients, Frames to Video, Scenebuilder. **Veo 4**: nguồn [B] mâu thuẫn (một bên nói ra 04/2026, bên khác nói chưa công bố) → **không rõ**.
- **Tiền** [B]: gói Google AI Pro 19,99 → Ultra 249,99 USD/tháng; API Veo 3.1 Fast ~0,10–0,12 USD/s, Standard ~0,40 USD/s.
- **Mạnh**: UI (tài sản + sửa trong một chỗ), MS (Extend / Scenebuilder nối tiếp hành động), âm thanh sinh cùng. **Yếu**: KB, QC, NHÓM.

### 2.7 Sora
- **Đã ngừng** [B nhiều nguồn]: app / web tắt 26/04/2026; API tắt 24/09/2026. Không còn dùng để so.

### 2.8 Hailuo / MiniMax H3
- Xem mục 1 dòng 3 [B]. Giá ~0,13 USD/s (2K), ~0,09 USD/s (768p); ảnh tham chiếu thứ 6 trở đi 0,04 USD; âm tham chiếu miễn phí. Bản 29/09 [A]: Media Agent (kế hoạch 3 giai đoạn). **Mạnh**: MS, tham chiếu đa phương thức, sửa theo chỉ dẫn, trọng số mở. **Yếu**: không rõ tiếng Việt; QC / NHÓM không rõ.

### 2.9 Katalist
- [A]: kịch bản nhập / dán → storyboard có nhiều biến thể mỗi cảnh, giữ nhân vật / ống kính / bối cảnh; **animatic có giọng đọc từng khung**; Story Canvas làm nhóm; Video Studio có giọng + nhạc + SFX; xuất nhiều định dạng (bản 29/09: PPT / ZIP / Premiere / Final Cut). Giá: **không rõ** (không đọc được).
- **Mạnh**: SB, NHÓM, xuất ra phần mềm dựng. **Yếu**: MS / chất lượng video (dựa model ngoài), QC.

### 2.10 Invideo AI
- [A blog hãng]: "đội" tác tử vai trò (nhà sản xuất, storyboard, casting, trang phục, thiết kế, quay phim) chạy song song; **chọn model theo từng shot**; gắn nhân vật + giọng vào mọi lần sinh; nối clip để giữ mạch; gom lại cho bạn duyệt. Giá: **không rõ** (không đọc được).
- **Mạnh**: KB, MS, quy trình tác tử + duyệt. **Yếu**: QC / chi phí trần không công bố.

### 2.11 Pika (2.5) và Luma (Ray 3.14)
- **Pika** [B]: Pika 2.5 (02/2026), Pikaframes (tới 25 s), Pikascenes / Additions / Swaps / Twists / Effects, motion brush; Pikaformance (khớp môi theo âm) bản 29/09 [B]. **Luma** [B]: Ray 3.14, keyframe, Modify (video→video), lip sync, extend, loop, reframe, inpainting, Luma Agents; Plus 30 / Pro 90 / Ultra 300 USD/tháng, không còn gói miễn phí. Cả hai: **chỉ [B]**, mạnh về hiệu ứng / sửa; yếu về KB, SB, QC, NHÓM (không công bố).

### 2.12 HeyGen / Synthesia (video có người nói)
- **HeyGen** [B qua trang hãng]: Avatar V (04/2026), Video Agent 2.0 (xem kế hoạch → duyệt → dựng), dịch khớp môi 175+ ngôn ngữ; Creator 29 / Pro 49 / Business 149 + 20/ghế USD/tháng (Business có cộng tác nhóm, 4K, SCORM). **Synthesia** [B qua trang hãng]: Express-2 → Express-3, Assistant (15/07/2026). Cả hai: avatar người thật nói theo kịch bản — **không phải** phim hành động / game; tiếng Việt: [B] chất lượng giảm ở ngôn ngữ có thanh điệu → **không rõ** độ khớp thật. Mạnh: LS (người nói), NHÓM / phân quyền (Business / Enterprise), duyệt kế hoạch. Yếu: cảnh hành động, bối cảnh 3D, QC.

### 2.13 OpusClip / Captions / CapCut AI (cắt + phụ đề)
- **OpusClip** [B]: cắt video dài thành clip ngắn, tự reframe 9:16, phụ đề động, "điểm lan truyền", chèn B-roll, tiêu đề / hook; Free 60 phút, Starter 15, Pro 29 USD/tháng. **Captions**: không có nguồn riêng → **không rõ**. **CapCut AI** [B]: phụ đề tự động, chuyển cảnh, chỉnh màu; Standard 9,99, Pro 19,99 USD. Nhóm này làm **hậu kỳ cho video có sẵn** — chỉ liên quan K7 (phụ đề). Mình đã có phụ đề vùng an toàn TikTok.

## 3. Bảng so sánh theo khâu K1–K10
Mức: **Hơn** / **Ngang** / **Kém** / **Không rõ** (ở nhóm A, theo công bố). Lý do ngắn.

| Khâu | Mức | Lý do |
|---|---|---|
| K1 Kịch bản → shot | **Hơn** (với bằng chứng công bố) | Họ chia shot + gợi ý máy (LTX, Higgsfield Assist, Katalist, Invideo, HeyGen duyệt kế hoạch). Mình có Director hai lượt, nhịp truyện có nguyên nhân, "người xem lần đầu", dự tính chi phí. Có thể họ có bên trong mà không công bố. |
| K2 Nhân vật / bối cảnh | **Ngang** (nhân vật) / **Hơn** (bối cảnh 3D) | Elements / Soul ID / Kling Elements / Seedance 50 tham chiếu ≈ Kho + hồ sơ chuẩn của mình. **Kém ở chia sẻ Element cho nhóm + giọng gắn nhân vật**. Bối cảnh từ GLB / Blender: không ai công bố nhận 3D khách (Seedance 2.5 có "mô hình trắng 3D / Blender-Maya" [A] — **cần kiểm** có thể là đối thủ gần). |
| K3 Storyboard / animatic | **Ngang** | Katalist cũng có animatic có giọng đọc; LTX có animatic. Mình hơn ở QC ảnh trước cổng; kém ở nhiều biến thể / nhiều khung một lần và chỉnh tư thế bằng công cụ. |
| K4 Video | **Ngang / Kém** | Họ có Multi-Shot một lần (Kling, H3), Extend / Scenebuilder, clip 30–180 s (Seedance 2.5), tham chiếu 50 tài sản. Mình hơn ở chọn model theo cảnh dựa số đo thật (Invideo công bố ý tưởng giống). Kém ở nối tiếp hành động qua điểm cắt. |
| K5 Khớp môi | **Ngang** (tiếng Việt) / **Kém** (đa lựa chọn) | Họ nhiều lựa chọn (Higgsfield Lipsync Studio, Hedra, Pika, LTX Audio-to-Video, H3 sửa thoại); đa số không rõ tiếng Việt, Kling không có. Mình có giọng clone FF + Seedance nhận tham chiếu âm; đo khớp môi còn yếu. |
| K6 Giọng / nhạc / SFX | **Hơn** (kiểm soát) / **Kém** (video→SFX) | Âm thanh trước + −14 LUFS + sửa nhạc lặng: không ai công bố. Họ có SFX từ hình (LTX), âm stereo cùng pass (H3, Veo, Kling). |
| K7 Dựng | **Hơn** (tự động) / **Kém** (sửa + xuất) | Dựng tự động theo luật nghề + vùng an toàn TikTok: không ai công bố. Kém: không có trình dựng kéo thả, không xuất ProRes / PNG tuần tự / FCPXML (Runway, Katalist có). |
| K8 QC | **Hơn** | Không sản phẩm nào công bố QC tự động trước khi giao (quét 13 sản phẩm lần này). Giữ. |
| K9 Chi phí | **Hơn** | Họ có số dư credit + giá hiển thị; không ai công bố trần cứng theo dự án / mỗi lời gọi. Kém nhỏ: hàng chậm / rẻ cho bản nháp (Runway Explore, Higgsfield Assist cảnh báo trước khi tốn credit — cái sau là **gợi ý mình nên so với QC prompt trước khi gửi**). |
| K10 Vận hành / nhóm / UI | **Kém** (nhóm, UI) / **Hơn** (cổng duyệt tự động) | Higgsfield 4.0, Katalist, Invideo, HeyGen Business / Synthesia có làm việc nhóm; Flow có lưới tài sản + Collections + "@". Mình: một người dùng, nhiều phiên `?s=`. Hơn: Autopilot có cổng duyệt + cờ tính năng + AI Dev System. Phân quyền / bình luận theo khung: mình không có — **nhu cầu không rõ** (dự án một người). |

## 4. "Họ có mà mình chưa có" — xếp theo giá trị cho người dùng / công sức
Ký hiệu: 💻 code miễn phí · 💵 tốn tiền (cần duyệt + ước tính trước) · 👤 cần người dùng · 🔍 cần kiểm API ClipAI / tài liệu trước. Có đánh dấu ★ = mới so với bản 29/09.

| Ưu | Mục | Học từ | Loại | Ghi chú |
|---|---|---|---|---|
| 1 | **Sửa clip cục bộ thay vì sinh lại** (X2 cũ) | Seedance 2.5 Intelligent Edit ★, Runway Aleph 2, Flow, H3, LTX Retake ★ | 🔍 + 💵 | Giá trị cao nhất; đã là S4.12 ⏸. Model mình dùng (Seedance 2.5) công bố có → kiểm ClipAI có đưa ra API không. |
| 2 | **Nối hành động qua điểm cắt** (X1 cũ) | Flow Extend / Scenebuilder, Kling Start & End | 💻 + 💵 nhỏ | Lỗi 1.5 / 1.6 #8. Không đổi so với 29/09. |
| 3 | **Xuất timeline / ProRes / PNG tuần tự** ★ mở rộng X6 | Runway, Katalist | 💻 | FCPXML / EDL + tệp âm riêng cho người dựng trên Premiere. |
| 4 | **Giọng gắn hồ sơ nhân vật trong Kho** (X7 cũ) | LTX, Kling, Invideo ("gắn nhân vật + giọng vào mọi lần sinh") ★ | 💻 | |
| 5 | **Chia sẻ Element / Kho cho nhóm + sinh đồng thời** ★ | Higgsfield 4.0 | 💻 (nếu cần) / 👤 (quyết định có nhiều người dùng) | Chỉ đáng làm nếu người dùng định mở cho nhiều người; hiện không rõ. |
| 6 | **Trợ lý cảnh báo lỗi prompt trước khi tốn credit** ★ | Higgsfield Assist [B] | 💻 | Mình có QC lớp 0 / ước tính trước; có thể thêm "QC prompt trước khi gửi" cho các lỗi đã biết. Cần kiểm xem đã có phần nào. |
| 7 | **UI Kho tài nguyên: lưới + Collections + "@" gọi tài sản + sửa bằng chữ** ★ | Flow 02/2026 [A] | 💻 | Tham khảo cho dashboard (K10). |
| 8 | **Bản nháp rẻ → bản cuối** (X3 cũ) | Runway Explore, ClipAI Sample Mode | 🔍 | S4.11 ⏸. |
| 9 | **Clip dài một lần (30 s; 180 s beta) + tham chiếu tới 50** ★ | Seedance 2.5 | 🔍 + 💵 | Kiểm giới hạn thật trên ClipAI; có thể thay "gom nhóm shot". Chú ý giá 2.5 cao hơn 2.0. |
| 10 | **Tờ lưới nhiều khung một lần sinh** (X5 cũ) / **nhiều biến thể mỗi cảnh** ★ | Popcorn, Katalist | 💵 nhỏ | |
| 11 | **Bảng cách khớp môi theo shot** (X4 cũ) | Higgsfield Lipsync Studio, LTX Audio-to-Video ★ | 💻 | |
| 12 | **Diễn thật làm nguồn chuyển động** (X9 cũ) | Act-Two, Kling Motion Control | 👤 + 💵 | Cần người diễn. |
| 13 | **Tích hợp phông xanh / mô hình trắng 3D / Blender-Maya vào Seedance 2.5** ★ | Seedance 2.5 [A thông cáo] | 🔍 | **Có thể liên quan tới tháp đồng hồ 3D + ghép phông xanh của mình** (`project_tower_composite_lipsync`) — nên kiểm đúng tính năng này trước khi tự làm. |
| 14 | **Video → SFX** (X10 cũ) | LTX, ElevenLabs | 🔍 | |

**Không đề xuất**: HeyGen / Synthesia / Hedra / Pika / Luma / Runway làm công cụ chính (cần tài khoản mới, ngoài ClipAI, trái quyết định "mọi lời gọi qua ClipAI + sổ chi"); nhập kịch bản bằng tệp, bình luận theo khung, phân quyền (chưa thấy nhu cầu).

## 5. "Mình có mà họ không có" (lợi thế thật, theo công bố)
1. **QC tự động nhiều lớp tới bản dựng cuối** (ảnh 2 lớp, clip bằng số đo, bản dựng cuối) — không sản phẩm nào trong 13 công bố.
2. **Trần chi phí cứng 3 tầng + ước tính trước + dự tính cả dự án sau Director** — họ chỉ có số dư credit và bảng giá.
3. **Director hai lượt có người duyệt + nhịp truyện có nguyên nhân + "người xem lần đầu"** — họ có chia shot, nhưng không công bố khâu phản biện (HeyGen chỉ duyệt kế hoạch).
4. **Âm thanh trước, hình sau** + chuẩn độ to −14 LUFS / −1 dBTP + sửa nhạc lặng.
5. **Dựng tự động theo luật nghề** (chuyển cảnh trong chuyển động, hồi tưởng, cắt theo chuyển động, phụ đề vùng an toàn TikTok).
6. **Bối cảnh từ mô hình 3D thật** của game + hồ sơ chuẩn nhân vật FF (lưu ý mục 4 dòng 13: Seedance 2.5 có thể thu hẹp khoảng cách).
7. **Giọng clone đội FF bằng tiếng Việt** — Kling Native Audio không có tiếng Việt; HeyGen / Synthesia chất lượng giảm ở ngôn ngữ có thanh điệu [B].
8. **Chọn model theo từng cảnh dựa số đo A/B thật + sổ chi** — Invideo công bố cùng ý "chọn model theo shot", nhưng không công bố số đo hay trần chi.
9. **Kiến thức nghề riêng** (`knowledge/craft`, kỹ năng 3 vai) áp lên prompt — không sản phẩm nào công bố.

Lưu ý trung thực: nhiều mục "mình hơn" là **khâu kiểm và điều khiển**, còn mục "mình kém" là **khả năng model / công cụ sửa**. Tôi **không đo chất lượng hình** của bất kỳ sản phẩm nào.

## 6. Đề xuất (chờ người dùng chọn)
1. 🔍 Kiểm trên ClipAI (trang / tài liệu công khai, 0 USD): Seedance 2.5 **Intelligent Edit**, **Long Video**, **green-screen / 3D white-model / Blender-Maya** có qua API không, giá thật.
2. 💻 Xuất timeline + ProRes / PNG tuần tự cho Premiere (X6).
3. 💻 Giọng gắn hồ sơ nhân vật (X7).
4. 💻 "QC prompt trước khi gửi" nếu chưa đủ (so với Higgsfield Assist).
5. 💻 Tham khảo UI Flow cho Kho tài nguyên (lưới / Collections / "@").
6. Phần nhóm (chia sẻ Element, sinh đồng thời): chỉ khi người dùng muốn mở cho nhiều người.

## 7. Nguồn (đọc 2026-10-03)
- [A] Dreamina: [Seedance 2.5 launch](https://dreamina.capcut.com/resource/seedance-2-5-launch) · [PR Newswire](https://www.prnewswire.com/news-releases/dreamina-launches-seedance-2-5--the-tool-of-ai-video-generation-that-reduces-clip-stitching-visual-drift-and-rework-302841204.html) · [Seedance 2.5](https://dreamina.capcut.com/seedance/seedance-2-5) · [CapCut PC](https://www.capcut.com/resource/seedance-2-5-is-now-on-capcut-pc)
- [A] Google: [Flow updates 02/2026](https://blog.google/innovation-and-ai/models-and-research/google-labs/flow-updates-february-2026/) · [Veo 3.1 trong Flow](https://blog.google/innovation-and-ai/products/veo-updates-flow/)
- [A] Higgsfield: [Cinema Studio 4.0](https://higgsfield.ai/blog/cinema-studio-4-0)
- [A] Katalist: [Agentic storyboarder](https://www.katalist.ai/agentic-storyboarder) · [Trang chủ](https://www.katalist.ai/)
- [A] Invideo: [Multi-agent video](https://invideo.io/faq/what-is-the-best-ai-platform-for-multi-agent-video/) · [AI filmmaking](https://invideo.io/blog/ai-filmmaking/)
- [A, qua tìm kiếm] Runway: [Changelog](https://runway.com/changelog) · [API changelog](https://docs.dev.runwayml.com/api-details/api_changelog/) · HeyGen: [April 2026 release](https://www.heygen.com/blog/heygen-april-2026-release) · Synthesia: [Synthesia 3.0](https://www.synthesia.io/post/synthesia-3-0-the-next-era-of-video)
- [B] LTX: [Top features](https://ltx.io/blog/top-ltx-studio-features) (chỉ có tóm tắt tìm kiếm) · [Vidmuse review](https://vidmuse.ai/blog/ltx-studio-review) · [LTX pricing](https://omidsaffari.com/blog/ltx-studio-pricing)
- [B] Runway: [Rundown Gen-4.5](https://www.therundown.ai/tools/runway-gen-4-5) · [eesel pricing](https://www.eesel.ai/blog/runway-ai-pricing)
- [B] Higgsfield: [Krea pricing](https://www.krea.ai/blog/higgsfield-pricing-explained-2026-unlimited-credits-and-real-monthly-costs)
- [B] Kling: [Atlas Cloud review](https://www.atlascloud.ai/blog/tips/kling-3.0-review-features-pricing-ai-alternatives) · [Flowith pricing](https://flowith.io/blog/kling-3-pricing-credits-pro-ultra/)
- [B] Veo: [BuildFast review](https://www.buildfastwithai.com/blogs/google-veo-3-1-ai-video-generator) · [Veo 4 pricing](https://www.veo3gen.app/blog/veo-4-pricing-comparison-google-vs-alternatives)
- [B] Sora: [TechCrunch](https://techcrunch.com/2026/03/24/openais-sora-was-the-creepiest-app-on-your-phone-now-its-shutting-down/) · [Sora API shutdown](https://twinailabs.com/en/blog/sora-api-shutdown-september-2026)
- [B] Luma: [eesel](https://www.eesel.ai/blog/luma-ai-pricing) · Hailuo H3: [llm-stats](https://llm-stats.com/blog/research/minimax-h3-launch) · [Pixo](https://pixo.video/blog/what-is-minimax-h3) · Pika: [WeShop](https://www.weshop.ai/blog/pika-ai-review-2026-still-the-king-of-creative-ai-video-generation/) · OpusClip: [eesel](https://www.eesel.ai/blog/opusclip) · HeyGen vs Synthesia: [Creatify](https://creatify.ai/blog/heygen-vs-synthesia-(2026)-pricing-avatars-and-which-one-fits-your-team)
- Repo: `docs/SO_SANH_PHAN_MEM_NGOAI_2026-09-29.md`, `PLAN.md`, `CLAUDE.md`
