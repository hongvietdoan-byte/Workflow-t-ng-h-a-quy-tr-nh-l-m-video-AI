# Nguồn tham khảo đã kiểm chứng (kiểm tra ngày 2026-09-19)

Số liệu lấy từ GitHub API tại thời điểm kiểm tra. **Chỉ dùng ý tưởng và cấu trúc, diễn đạt lại bằng lời của dự án; không sao chép nguyên văn.** Repo không có license = mặc định giữ mọi quyền, chỉ đọc tham khảo. CC-BY-4.0 nếu dùng lại nội dung phải ghi công.

| # | Nguồn | Sao | License | Hoạt động | Độ tin cậy | Dùng để làm gì |
|---|---|---|---|---|---|---|
| 1 | [google-deepmind/dramatron](https://github.com/google-deepmind/dramatron) | 1.1k | Apache-2.0 | push 07/2024 (ổn định) | Cao (DeepMind, có nghiên cứu người dùng) | Cấu trúc phân tầng: logline → nhân vật → cốt truyện → địa điểm → thoại. Mẫu cho Bước 1 |
| 2 | [HITsz-TMG/FilmAgent](https://github.com/HITsz-TMG/FilmAgent) (nay đổi tên VideoClaw) | 1.8k | MIT | push 08/2026 | Cao về ý tưởng (có bài báo); phần sản phẩm hóa mới hơn | Vai trò đạo diễn/biên kịch/quay phim phối hợp, có người kiểm duyệt |
| 3 | [openstory-so/openstory](https://github.com/openstory-so/openstory) | 637 | MIT | push 09/2026 | Trung bình–cao (đang phát triển tích cực) | Quy trình 5 pha script → storyboard: tách cảnh, "bibles", shot list, motion prompt dựa trên ảnh đã render |
| 4 | [jnMetaCode/ai-shortfilm-prompts](https://github.com/jnMetaCode/ai-shortfilm-prompts) | 429 | MIT | push 09/2026 | Trung bình (cộng đồng, có bộ tự kiểm 10 mục) | Khung prompt 5 tầng, mẫu 21 thể loại, cách tự kiểm |
| 5 | [smixs/visual-skills](https://github.com/smixs/visual-skills) | 403 | CC-BY-4.0 | push 09/2026 | Trung bình (cộng đồng; nội dung dựng phim có cơ sở như quy tắc Murch) | Kịch tính học, blocking, montage; cú pháp riêng từng model (Seedance/Kling/Veo) |
| 6 | [showlab/MovieAgent](https://github.com/showlab/MovieAgent) | 363 | không có | push 03/2025 | Cao về học thuật (bài báo arXiv 2503.07314) | Lập kế hoạch phân tầng đạo diễn → cảnh → shot; ngân hàng tham chiếu nhân vật |
| 7 | [neopen/story-shot-agent](https://github.com/neopen/story-shot-agent) (PenShot) | 203 | MIT | push 09/2026 | Trung bình | Chia kịch bản thành shot theo giới hạn thời lượng model; bộ nhớ nhất quán nhân vật; QA agent |
| 8 | [Vchitect/ShotBench](https://github.com/Vchitect/ShotBench) | 106 | không có | push 09/2025 | Cao về học thuật (benchmark, chú thích chuyên gia) | Phân loại 8 chiều điện ảnh dùng làm từ vựng chuẩn cho QC/eval |
| 9 | [geekjourneyx/awesome-ai-video-prompts](https://github.com/geekjourneyx/awesome-ai-video-prompts) | 78 | MIT | push 01/2026 | Thấp–trung bình (danh mục tổng hợp) | Mục lục các hướng dẫn chính thức và mẫu prompt để đối chiếu |
| 10 | [Picrew/awesome-llm-story-generation](https://github.com/Picrew/awesome-llm-story-generation) | 108 | không có | push 06/2026 | Thấp–trung bình (danh mục bài báo) | Mục lục bài báo/dự án tạo truyện–kịch bản để đọc sâu thêm |

## Đã xem nhưng không dùng
- `cliprise/awesome-ai-video-generator-prompts` (18 sao, không license, dạng quảng bá/tổng hợp): giá trị thấp.
- `NAMDIE/SKRIPTON` (0 sao, repo mới, Apache-2.0): ý tưởng "prompt pack tự thực thi" hay nhưng chưa được kiểm chứng.
- `YidanPan/Movie-Agent` (1 sao): chưa đủ độ tin cậy.

## Lưu ý về độ tin cậy
- Phần lớn repo về prompt video AI là dự án cộng đồng mới (2026) với số sao khiêm tốn; giá trị nằm ở nguyên tắc dựng phim chung, không ở cú pháp cụ thể của từng model.
- **Cú pháp/giới hạn từng model (Seedance, Kling, MiniMax) phải lấy từ tài liệu chính thức của model hoặc của Clip AI**, và kiểm tra bằng bộ đánh giá `eval/`, không tin hoàn toàn vào repo cộng đồng.
- Kiểm tra lại số liệu này định kỳ (mỗi quý) vì các model và repo thay đổi nhanh.

## Bộ kỹ năng nội bộ đã chắt lọc (2026-09-21)
- "AI Film Direction & Prompt Workflow Kit" 1.0.0 (film-director, motion-director, narration-writer, style-analyst) → `film_director_method.md`, `t2v_prompt_structure.md`, `motion_complex_shots.md`, tính năng World Bible.
- "Seedance Director — Prompt Optimization Skill" 1.0 → `seedance_director_workflow.md`.
- Đây là tài liệu nội bộ do người dùng cung cấp, chưa được kiểm chứng bằng bộ đánh giá `eval/`.
- **Cập nhật 2026-09-24:** "AI Film Direction & Prompt Workflow Kit" **2.0.0** (4 kỹ năng gộp thành một gói, dùng chung "pipeline contract" schema 1.3) — nội dung phần lớn trùng bản 1.0.0 đã chắt lọc; phần mới đã đưa vào: `render_style` trong World Bible (bắt buộc với anime) + bảng ký hiệu máy đầy đủ (`t2v_prompt_structure.md`), 3 nguyên lý tri giác (`motion_complex_shots.md`). "Seedance Director" **1.0.2** — phần mới "reverse asset planning" (mỗi ảnh tham chiếu một vai trò, nói rõ điều khiển gì / không điều khiển gì) → `seedance_director_workflow.md`, áp dụng cho cả ảnh tham chiếu Deepix (liên quan F7/F9).

## GĐ4 (kế hoạch V4) — nguồn của bộ kỹ năng 3 vai (đọc 2026-09-25)
Dùng cho `knowledge/roles/director.md` [Đn], `knowledge/roles/dp.md` [Qn], `knowledge/editor/editing.md` + `safe_zones.md` [En]. Chỉ tóm lược
bằng lời của dự án, không chép nguyên văn. Loại: **CT** chính thức · **S** sách/tổ chức nghề/chuẩn · **HT** học thuật · **TC** thứ cấp ·
**CĐ** cộng đồng. Sách (Weston, Mamet, McKee, Block, Katz, Brown, Murch, Dmytryk) **chỉ đọc qua tóm lược/bài của tác giả** — tin cậy trung bình.
**Mẹo prompt model video từ nguồn thứ cấp chỉ là giả thuyết cần thử** (CHUAN_XAY_DUNG luật 5).

### Đạo diễn [Đn]
| # | Nguồn | URL | Loại · tin cậy |
|---|---|---|---|
| Đ1 | Judith Weston, "Directing the Actor" (bài của tác giả) | actioncutprint.com/files/DirectingActor-JudithWeston.pdf | S · cao |
| Đ2 | Ghi chú sách *Directing Actors* (Weston) | kortina.nyc/notes/directing-actors/ | TC · tb |
| Đ3 | Mamet, memo cho biên kịch *The Unit* | nofilmschool.com/2010/10/david-mamet-drama-a-memo-the-unit-writers | S qua TC · tb–cao |
| Đ4 | *On Directing Film* (Mamet), tóm lược | en.wikipedia.org/wiki/On_Directing_Film | TC · tb |
| Đ5 | McKee Story Principles (tóm lược *Story*) | desertscreenwritersgroup.wordpress.com (mckee-story-principles.pdf) | TC · tb |
| Đ6 | Save the Cat! | savethecat.com/get-started | CT · cao |
| Đ7 | Hitchcock/Truffaut: hồi hộp và bất ngờ | nofilmschool.com/alfred-hitchcock-and-francois-truffaut-explain-surprise-vs-suspense | TC · tb–cao |
| Đ8 | Bruce Block, *The Visual Story* — Contrast & Affinity | taylorfrancis.com (10.4324/9781315794839-2) | S · cao |
| Đ9 | Film Book Notes: *The Visual Story* | filmbooknotes.blogspot.com/2013/05 | CĐ · tb |
| Đ10 | Ruskin — Pathetic Fallacy | victorianweb.org/technique/pathfall.html | HT · tb–cao |
| Đ11 | Chekhov's Gun (Britannica) | britannica.com/topic/Chekhovs-gun | S · cao |
| Đ12 | Murch "Rule of Six" (StudioBinder) | studiobinder.com/blog/walter-murch-rule-of-six/ | TC · tb |
| Đ13 | Paul Ekman Group — Micro Expressions | paulekman.com/resources/micro-expressions/ | CT · cao |
| Đ14 | Michael Caine "don't blink" (Acting Magazine) | actingmagazine.com/2018/07/… | TC · tb |
| Đ15 | Backstage — lắng nghe trong diễn xuất | backstage.com/magazine/article/craft-listen-… | TC · tb |
| Đ16 | TikTok Ads Help — Creative best practices | ads.tiktok.com/help/article/creative-best-practices | CT · cao (số đo trên quảng cáo) |
| Đ17 | TikTok for Business — Creative Codes | ads.tiktok.com/business/en-US/blog/creative-best-practices-top-performing-ads | CT · cao |
| Đ18 | YouTube — Viewed vs Swiped Away | support.google.com/youtube/community-video/273390203 | CT · tb–cao |
| Đ19 | TechCrunch — YouTube giải thích thuật toán Shorts (2023) | techcrunch.com/2023/08/25/… | TC · tb |
| Đ20 | ElevenLabs — TTS best practices | elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices | CT · cao |
| Đ21 | ElevenLabs — Text to Speech (playground) | elevenlabs.io/docs/eleven-creative/playground/text-to-speech | CT · cao |
| Đ22 | ElevenLabs — Prompting Eleven v3 | elevenlabs.io/docs/best-practices/prompting/eleven-v3 | CT · cao |
| Đ23 | ElevenLabs — audio tags với v3 | elevenlabs.io/docs/help-center/…/how-do-audio-tags-work-with-eleven-v3-alpha | CT · cao |
| Đ24 | Kling AI — Prompt Guide (blog) | kling.ai/blog/kling-ai-prompt-guide | CT (marketing) · tb–cao |
| Đ25 | fal.ai — Kling 3.0 prompting guide | blog.fal.ai/kling-3-0-prompting-guide/ | TC · tb |
| Đ26 | fal.ai — Seedance 2.0 prompting guide | fal.ai/learn/tools/seedance-2-0-prompting-guide | TC · tb |
| Đ27 | John Yorke — How to give script notes | johnyorkestory.com/2017/07/how-to-give-script-notes/ | S · tb–cao |
| Đ28 | No Film School — notes on a script | nofilmschool.com/how-to-give-notes-on-a-script | TC · tb |
| Đ29 | Katz, *Film Directing Shot by Shot* (mô tả) | store.ascmag.com/products/film-directing-shot-by-shot | S (mô tả) · tb |
| Đ30 | The Audio Cafe — ADR voice acting | theaudiocafe.co.uk/blog/film/adr-voice-acting/ | CĐ · thấp–tb |
| Đ31 | "AI Director's Master Handbook (2026 Edition)" — Google Doc người dùng gửi 2026-09-26 (bản trả lời của một chatbot AI, không nguồn) | docs.google.com/document/d/1nqL7rcAFXNYgaDK8WTPavy8Y-3en2-3R4UUf9C7716Y | CĐ (máy sinh) · thấp |
| Đ32 | "Free Fire In-Game Visual Replication Plan v1.0" (26/09/2026, nội bộ; 2 video gameplay, 1 nhân vật, 1 nhà kho) | `Get this Skill to Claude/Tài nguyên tham khảo…/` (ngoài git) | nội bộ · tb |

[Đ31] chỉ lấy **ý có lý do tự đứng được** và khớp nguồn đã có: phản ứng trước nguyên nhân sau (cách làm của "biết sau", Hitchcock [Đ7]),
shot giữ sau cú đánh cảm xúc (Murch [Đ12]), móc nhỏ giữa video, âm thanh quyết cùng cảm xúc (J/L-cut [E3]). **Không dùng**: các con số
không nguồn ("nhịp hình sin", "âm thanh 50% cảm xúc", "phản ứng 80% cảm xúc"), bảng phân cảnh mẫu (ghi 30 s nhưng cộng lại 13 s), shot
0,4–0,6 s (mỗi shot vẫn trả tiền một clip dài hơn nhiều). [Đ32] → `knowledge/ff_gameplay_visual.md` (tư liệu hiểu hình ảnh gameplay, không
phải kho cảnh để ghép).

Không có nguồn chính thức: vòng lặp (loop) và độ dài tối ưu cho video tự nhiên; mốc "móc 1–3 s" của Shorts; tài liệu Seedance/Kling về vi
biểu cảm; ElevenLabs riêng cho tiếng Việt. ElevenLabs tự mâu thuẫn về `speed` với v3 ([Đ20] ↔ [Đ21]) → thử thật trước khi bật `voice_direction`.

### Quay phim [Qn]
| # | Nguồn | URL | Loại · tin cậy |
|---|---|---|---|
| Q1 | Mascelli, *The Five C's* (tóm tắt) | robertcmorton.com/the-5-cs-of-cinematography/ | S (tóm tắt) · tb |
| Q2 | Bordwell & Thompson, *Film Art* (qua bài Low-angle shot) | en.wikipedia.org/wiki/Low-angle_shot | S gián tiếp · tb |
| Q3 | Google — Veo prompt guide | docs.cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide | CT · cao |
| Q4 | Google — Ultimate prompting guide Veo 3.1 | cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1 | CT · cao |
| Q5 | Runway — Camera terms, prompts & examples | help.runwayml.com/hc/en-us/articles/46749315925395 | CT · cao |
| Q6 | Runway — Gen-4 video prompting guide | help.runwayml.com/hc/en-us/articles/39789879462419 | CT · cao |
| Q7 | Runway — Image to video prompting guide | help.runwayml.com/hc/en-us/articles/48324313115155 | CT · cao |
| Q8 | BytePlus — Seedance 2.0 prompt guide | docs.byteplus.com/en/docs/modelark/2222480 | CT · cao |
| Q9 | BytePlus — Seedance 2.5 prompt guide | docs.byteplus.com/en/docs/ModelArk/2607689 | CT · cao |
| Q10 | BytePlus — Seedance 1.0 pro prompt guide | docs.byteplus.com/en/docs/ModelArk/1631633 | CT · cao |
| Q11 | BytePlus — Seedance 1.5 pro prompt guide | docs.byteplus.com/en/docs/ModelArk/2168087 | CT · cao |
| Q12 | Kling — Text-to-video prompt guide | kling.ai/quickstart/text-to-video-prompt-guide | CT · cao |
| Q13 | Kling — Image-to-video guide | kling.ai/quickstart/image-to-video-guide | CT · cao |
| Q14 | Kling — Camera control guide | kling.ai/quickstart/ai-camera-control-guide | CT · cao |
| Q15 | Kling — VIDEO 3.0 model guide | kling.ai/quickstart/klingai-video-3-model-user-guide | CT · cao |
| Q16 | Kling — VIDEO 3.0 Omni guide | kling.ai/quickstart/klingai-video-3-omni-model-user-guide | CT · cao |
| Q17 | Kling blog — AI camera control | kling.ai/blog/ai-camera-control-movement-prompts-guide | CT (marketing) · tb |
| Q18 | Kling blog — Prompt guide | kling.ai/blog/kling-ai-prompt-guide | CT (marketing) · tb |
| Q19 | J. Holben (ASC) — Understanding lens distortion | theasc.com/article/understanding-lens-distortion/ | S · cao |
| Q20 | J. Holben (ASC) — Shot Craft: camera movement | theasc.com/article/shot-craft-camera-movement/ | S · cao |
| Q21 | Blender Manual — Cameras | docs.blender.org/manual/en/latest/render/cameras.html | CT · cao |
| Q22 | Blain Brown, *Cinematography: Theory and Practice* (qua tóm tắt) | routledge.com (Brown, 9780367373450) | S gián tiếp · tb |
| Q23 | 180-degree rule | en.wikipedia.org/wiki/180-degree_rule | CĐ · tb |
| Q24 | 30-degree rule (+ coverage đối thoại) | en.wikipedia.org/wiki/30-degree_rule | CĐ · tb |
| Q25 | Bruce Block, *The Visual Story* (tóm tắt) | routledge.com (Block, 9781138014152) | S gián tiếp · tb |
| Q26 | Katz, *Shot by Shot* (mô tả) | store.ascmag.com/products/film-directing-shot-by-shot | S (mô tả) · tb |
| Q27 | StudioBinder — Lighting ratios; motivated lighting | studiobinder.com/blog/lighting-ratios/ | TC · tb |
| Q28 | Videomaker — Color temperature | videomaker.com/article/c13/14939-color-temperature-for-video/ | TC · tb |
| Q29 | Dan Mears DoP — Vertical video guide | danmears.tv/vertical-video/ | CĐ · thấp–tb |
| Q30 | StudioBinder — How to make a shot list | studiobinder.com/blog/how-to-make-a-shot-list/ | TC · tb |
| Q31 | Nesky, 50 Game Camera Mistakes (ghi chép GDC 2014) | shermanrose.uk/knowledge/programming/games/50-game-camera-mistakes/ | CĐ · tb |
| Q32 | K. Gartner — Virtual cinematography for VR trailers | gamedeveloper.com/business/virtual-cinematography-for-vr-trailers | TC · tb |
| Q33 | Third-person shooter / over-the-shoulder | en.wikipedia.org/wiki/Third-person_shooter | CĐ · thấp–tb |
| Q34 | Runway — Creating with Seedance 2.0 | help.runwayml.com/hc/en-us/articles/50488490233363 | CT (bên thứ 3) · cao |
| Q35 | PremiumBeat / No Film School — motivated camera movement | premiumbeat.com/blog/cinematography-tip-motivated-camera-movement/ | TC · thấp–tb |

Không có nguồn chính thức: ngôn ngữ máy trailer game TPS/Free Fire; bố cục 9:16 và khoảng trống đầu/nhìn; tỉ lệ key:fill, nhiệt độ màu hoàng
hôn/đêm trăng (chỉ thứ cấp). Hướng dẫn gốc Kling (docs.qingque.cn) chỉ chạy JavaScript — luật "một chuyển động mỗi shot" của Kling lấy từ blog;
Seedance 2.0 thì có trong tài liệu chính thức [Q8]. Bảng FOV trong `dp.md` tính từ công thức (`plate_camera.vfov`).

### Dựng [En]
| # | Nguồn | URL | Loại · tin cậy |
|---|---|---|---|
| E1 | Artlist — Rule of six & eye trace (tóm tắt Murch) | artlist.io/blog/eye-trace-and-rule-of-six-editing/ | TC · tb |
| E2 | NYFA — Dmytryk's 7 rules of cutting | nyfa.edu/student-resources/what-you-can-learn-from-edward-dmytryks-7-rules-of-cutting/ | TC (trường phim) · tb |
| E3 | StudioBinder — J-cut / L-cut / match cut | studiobinder.com/blog/what-is-a-j-cut-in-film/ | TC · tb |
| E4 | Cutting, DeLong, Nothelfer (2010), *Psychological Science* | journals.sagepub.com/doi/10.1177/0956797610361679 | HT · cao |
| E5 | TikTok — Creative best practices for performance ads | ads.tiktok.com/help/article/creative-best-practices | CT · cao |
| E6 | TikTok — TopView ad specifications | ads.tiktok.com/help/article/tiktok-reservation-topview | CT · cao |
| E7 | TikTok — Auction In-Feed Ads | ads.tiktok.com/help/article/tiktok-auction-in-feed-ads | CT · cao |
| E8 | TikTok × Kantar — sound on TikTok (2021) | ads.tiktok.com/business/en-US/blog/kantar-report-… | CT (nền tảng tự công bố) · tb |
| E9 | Meta Ads Guide — Instagram Reels video | facebook.com/business/ads-guide/update/video/instagram-reels | CT · cao |
| E10 | Meta for Business — Reels ads | facebook.com/business/ads/facebook-instagram-reels-ads | CT · cao |
| E11 | Instagram Help — Reel size & aspect ratios | facebook.com/help/instagram/1038071743007909/ | CT · cao |
| E12 | Google Ads Help — square & vertical video (hình vùng an toàn) | support.google.com/google-ads/answer/9128498 | CT · cao |
| E13 | YouTube Help — Recommended upload encoding settings | support.google.com/youtube/answer/1722171 | CT · cao |
| E14 | YouTube Help — Upload YouTube Shorts | support.google.com/youtube/answer/12779649 | CT · cao |
| E15 | YouTube Help — Stable volume | support.google.com/youtube/answer/14106294 | CT · cao |
| E16 | Production Advice — YouTube Stats for Nerds | productionadvice.co.uk/stats-for-nerds/ | TC (chuyên môn) · tb |
| E17 | Spotify for Artists — Loudness normalization | support.spotify.com/us/artists/article/loudness-normalization/ | CT · cao |
| E18 | AES TD1008 | aes.org/wp-content/uploads/2024/01/20210924_TD1008_v3.13.pdf | S (chuẩn; số đọc gián tiếp) · cao |
| E19 | Telos Alliance — Understanding loudness for streaming | docs.telosalliance.com/docs/understanding-loudness-for-streaming-audio | TC (hãng) · tb |
| E20 | EBU R128 | tech.ebu.ch/publications/r128 | S (chuẩn) · cao |
| E21 | EBU R128 s1 (nội dung ngắn) | tech.ebu.ch/docs/r/r128s1.pdf | S (chuẩn, qua trích đoạn) · cao |
| E22 | FFmpeg Filters Documentation | ffmpeg.org/ffmpeg-filters.html | CT · cao |
| E23 | Netflix English Timed Text Style Guide | partnerhelp.netflixstudios.com/hc/en-us/articles/217350977 | CT · cao |
| E24 | Netflix Subtitle Timing Guidelines | partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394 | CT · cao |
| E25 | BBC Subtitle Guidelines | bbc.co.uk/accessibility/forproducts/guides/subtitles/ | CT · **không tải được** |
| E26 | Foundry Nuke — LightWrap | learn.foundry.com/nuke/content/reference_guide/draw_nodes/lightwrap.html | CT (hãng) · cao |
| E27 | Blackmagic — Colorist Guide DaVinci Resolve 18 | documents.blackmagicdesign.com/UserManuals/DaVinci-Resolve-18-Colorist-Guide.pdf | CT (qua tìm kiếm) · cao/tb |
| E28 | Frame.io — Skin tones in DaVinci Resolve | blog.frame.io/2020/10/05/skin-tones-in-davinci-resolve/ | TC · tb |
| E29 | Sound on Sound — high-pass filter / de-essing | soundonsound.com/sound-advice/q-why-does-my-mic-have-high-pass-filter | TC (tạp chí nghề) · tb–cao |
| E30 | Netflix Sound Mix Specifications v1.6 | partnerhelp.netflixstudios.com/hc/en-us/articles/360001794307 | CT (qua trích đoạn) · tb |
| E31 | PremiumBeat — Timing music to video edits | premiumbeat.com/blog/timing-music-for-video-editing/ | TC · thấp–tb |
| E32 | Vidpros — Music too loud in video | vidpros.com/fix-background-music-too-loud-video/ | CĐ · thấp |
| E33 | Behaviour Digital — Meta Reels safe zone 2026 | behaviour.digital/post/meta-reels-safe-zone-… | CĐ · thấp |
| E34 | AdManage.ai — TikTok ad specs / safe zones | admanage.ai/blog/tiktok-ad-specs | CĐ · thấp–tb |
| E35 | Facebook IQ — Sight, sound and mobilisation (2017) | en-gb.facebook.com/business/news/insights/sight-sound-and-mobilization | CT · cao |

Không có số chính thức: LUFS của YouTube/TikTok/Instagram/Facebook; vùng an toàn cho Shorts thường (chỉ có số cho quảng cáo); px vùng an toàn
TikTok (chỉ trong file mẫu); tỉ lệ xem tắt tiếng của Meta; mức dB thoại/nhạc/SFX và mức hạ nhạc; cỡ chữ tối thiểu.
