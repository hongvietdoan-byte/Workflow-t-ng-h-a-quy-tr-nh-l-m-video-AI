# So sánh pipeline với phần mềm dựng phim AI bên ngoài (S8.3) — 2026-09-29

> Việc S8.3 của `docs/KE_HOACH_SUA_SAU_DU_AN_8.md`. **0 USD**: chỉ đọc trang web công khai (không đăng nhập, không đăng ký, không gọi API
> trả tiền), cộng đọc repo. Phần chấm điểm S8.0 / S8.2 chờ lần chạy K — không làm ở đây. Rút việc vào TODO là S8.4 (chưa làm; mục 5 dưới
> đây chỉ là **đề xuất** chờ người dùng chọn).

## 0. Cách làm và giới hạn
- Ngày đọc mọi nguồn: **2026-09-29**. Lời trích ≤ 15 từ, còn lại tóm bằng lời mình.
- Mức nguồn: **[A]** trang / tài liệu chính thức của hãng · **[B]** bài đánh giá, blog bên thứ ba, trang tổng hợp (có thể sai hoặc cũ) ·
  **[R]** tài liệu trong repo (ClipAI do người dùng gửi, đo thật của mình).
- **Không thấy trên trang công khai ≠ không có.** Ô nào không có nguồn ghi **"không rõ"**. Không thử tay sản phẩm nào → không có số đo chất
  lượng; mọi so sánh là **tính năng được công bố**, không phải chất lượng thật.
- Hai trang LTX (`ltx.io/blog/...`) không tải được (lỗi header) và trang trợ giúp Runway Act-Two trả 403 → phần LTX / Act-Two dựa trên
  trang tính năng [A] khác của hãng qua kết quả tìm kiếm và bài [B].

## 1. Các khâu của pipeline mình (bản đồ dùng để so)
Lấy từ `PLAN.md` (mục 3), `docs/KE_HOACH_SUA_SAU_DU_AN_8.md` (S0–S9) và `devsys/areas.json` (16 khu vực).

| # | Khâu | Mình đang làm gì (tóm) | Khu vực `areas.json` |
|---|---|---|---|
| K1 | Kịch bản → Director chia shot | Claude Director **hai lượt** (Đạo diễn duyệt), bảng nhịp truyện có `beat.cause`, `action_peak`, `transition_in`, agent **"người xem lần đầu"** (S3.2), bộ kỹ năng 3 vai Đạo diễn / Quay phim / Dựng có căn cứ, kiến thức nghề `knowledge/craft/`, phong cách tham khảo là **gợi ý** | step1, knowledge |
| K2 | Nhân vật / bối cảnh nhất quán | Kho tài nguyên + hồ sơ chuẩn nhân vật FF, Character / World Bible, **bối cảnh 3D thật** (GLB tháp đồng hồ → Blender render ảnh nền tầm mắt, câu bố cục bắt buộc S5.1–S5.4), dấu vân tay ⚠ "cũ" khi đổi bối cảnh | assets, plates3d, core_infra |
| K3 | Storyboard / animatic | Deepix vẽ từng khung (ảnh trước làm tham chiếu), ghi rõ ai có trong khung, QC ảnh lớp 0 (code) + lớp 1 / agent QC (Claude), **cổng duyệt storyboard**, **animatic** 0 USD (S2.4) | step2 |
| K4 | Video | Chọn model **theo từng cảnh** (Kling / Seedance 2.0 / Fast / 2.5 qua ClipAI), ảnh tham chiếu có đánh dấu, khung đầu cho cận / hành động, gom nhóm shot Seedance "Shot 1 / Shot 2", đoạn diễn liên tục theo góc máy (S3.4), câu khóa phong cách in-game, câu vật lý theo loại hành động | step4 |
| K5 | Khớp môi | Seedance nhận giọng khi tạo / một clip cả đoạn thoại (c) (`core/dialogue_take.py`), sync.so để sẵn nhưng không bật; đo khớp môi bằng điểm ảnh chưa phân biệt được (S4.5) | lipsync |
| K6 | Giọng / nhạc / SFX | TTS tiếng Việt **giọng clone đội FF** (`data/voices_vi.json`), chỉ đạo giọng, **âm thanh trước** (TTS nháp → khóa timeline, cờ `audio_first`), nhạc theo ý đồ + tự sửa lặng / lặp, SFX neo theo shot, −14 LUFS, limiter −1 dBTP | step3, step5 |
| K7 | Dựng | ffmpeg: chuyển cảnh vẽ trong 2 clip kề, hồi tưởng, cắt theo chuyển động, phụ đề **vùng an toàn TikTok**, timeline tổng (S9.6) | step5 |
| K8 | QC | QC ảnh 2 lớp, agent QC Claude Vision, QC clip (dấu đỏ lọt, `look_drift`, lẫn khung shot kề), **QC bản dựng cuối bằng máy** (`core/final_qc.py`) | step2, step4, step5, autopilot |
| K9 | Chi phí | Sổ chi `usage_events`, **ước tính trước khi bấm**, dự tính cả dự án ngay sau Director (S6.1), **khóa cứng 3 tầng** (mỗi lời gọi / mỗi việc / dự án), đo tỉ lệ đọc cache Claude | budget, diag |
| K10 | Vận hành | Autopilot có cổng duyệt, cờ tính năng + trạng thái "đã kiểm", AI Development System chấm 16 khu vực | autopilot, devsys, dashboard_ui |

## 2. Sản phẩm đã xem
| Mã | Sản phẩm | Loại | Nguồn chính |
|---|---|---|---|
| CL | **ClipAI / Deepix** (web, không qua API) | nền tảng mình đang dùng | [R] `docs/CLIPAI_FEATURES.md`, `docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md` mục 4 |
| LTX | **LTX Studio** (Lightricks) | studio kịch bản → phim trọn gói | [A] ltx.io/studio, help.ltx.io; [B] Luma, Vidmuse |
| RW | **Runway** (Gen-4 References, Act-Two, Aleph / Edit Studio) | model + công cụ | [A] runway.com, help.runwayml.com; [B] ChatForest |
| HF | **Higgsfield** (Popcorn, Cinema Studio, Soul ID, Lipsync Studio) | nền tảng tổng hợp nhiều model | [A] higgsfield.ai blog |
| KL | **Kling 3.0** (Multi-Shot, Elements, Native Audio) | model + web | [A] kling.ai quickstart |
| JM | **即梦 / Dreamina** (Seedance 2.0, Seedream, AI Agent / Octo) | web ByteDance / CapCut | [A] dreamina.capcut.com, volcengine.com; [B] Zhihu |
| GF | **Google Flow** (Veo 3.1) | công cụ làm phim | [A] blog.google |
| MM | **MiniMax Hailuo** (H3 multi-shot, Media Agent) | model + agent | [A] minimax.io; [B] getimg, Pixo |
| KT | **Katalist** | kịch bản → storyboard | [A] katalist.ai |
| OA | **OpenArt** (One-Click Story) | nền tảng tổng hợp | [A] bfl.ai (đối tác); [B] TechCrunch, tin ngành |
| HD | **Hedra** (Character-3) | khớp môi / nhân vật nói | [A] hedra.com |
| PK | **Pika** (Pikaformance) | khớp môi theo âm thanh | [B] các trang giới thiệu, video hãng |
| EL | **ElevenLabs** (Dubbing / Voiceover Studio) | giọng + SFX + timeline | [A] elevenlabs.io docs |

## 3. So sánh theo khâu

### K1 · Kịch bản → Director shot list
| | Nội dung |
|---|---|
| **Họ có** | LTX tự tách kịch bản thành cảnh / shot, gợi ý khung máy, và **tự rút nhân vật / vật / nơi thành Element** [A LTX]. Katalist nhận kịch bản CSV / Word / PowerPoint, tự chia shot + nhận nhân vật [A KT]. Seedance 2.0 trên 即梦: "自动识别文字中的叙事节点" → gán cỡ cảnh / chuyển động máy [A volcengine]. Dreamina AI Agent sắp khung theo thứ tự điện ảnh hợp lý [A]. Hailuo Media Agent: kế hoạch 3 giai đoạn tới tác tử làm trọn từ ý tưởng tới bản dựng [A MiniMax X]. |
| **Mình thiếu** | Nhập kịch bản dạng **tệp** (Word / PowerPoint / CSV) — mình dán chữ. Không rõ đây có phải nhu cầu thật của người dùng. |
| **Mình hơn** | Không sản phẩm nào công bố: Director **hai lượt có người duyệt**, bảng nhịp truyện có **nguyên nhân cú xoay**, agent **"người xem lần đầu"** chỉ đọc cái hiện trên màn hình, bộ kỹ năng 3 vai có lý do + căn cứ, dự tính chi phí ngay sau Director. Họ dừng ở mức "chia shot + gợi ý máy". (không rõ — có thể có bên trong mà không quảng bá) |
| **Nên học** | Chế độ **Auto / Manual** của Higgsfield Popcorn: Auto để model tự rải mạch truyện qua các khung, Manual chỉ đạo từng khung [A HF] — mình có tương đương (Director tự chia + sửa tay shot); **không cần làm thêm**. |

### K2 · Nhân vật / bối cảnh nhất quán
| | Nội dung |
|---|---|
| **Họ có** | **LTX Elements**: nhân vật / nơi / vật lưu một lần, gọi tên trong prompt; **sửa Element là lan ra mọi chỗ đã gắn**; nhân vật được **gán giọng** [A help.ltx.io]. **Kling Elements 3.0**: 2–4 ảnh hoặc video nhân vật, "Bind Subject to Enhance Consistency", **giọng gắn vào Element** [A kling.ai]. **Higgsfield Soul ID**: học danh tính từ 20+ ảnh trong vài phút, sau đó không cần gửi ảnh tham chiếu mỗi lần [A HF]. Runway Gen-4 References: một ảnh tham chiếu giữ danh tính qua nhiều shot [A/B RW]. OpenArt dùng FLUX Kontext giữ nhân vật từ một ảnh [A bfl.ai]. |
| **Mình thiếu** | (1) Kho chủ thể chính thức của ClipAI cho **mọi** ảnh nhân vật gửi Seedance — đang ⏸ S4.7. (2) Giọng chưa là **thuộc tính của nhân vật trong Kho** dùng chung mọi dự án (mình gán giọng theo dự án qua `cast_voices`). (3) Danh tính "đã học" kiểu Soul ID — không có qua ClipAI. |
| **Mình hơn** | **Bối cảnh từ mô hình 3D thật** (GLB → Blender, câu bố cục bắt buộc, đo "tầng tường") — không sản phẩm nào ở trên công bố nhận file 3D của khách làm nền (ClipAI có plugin Blender bản macOS [R], Higgsfield Cinema Studio có "3D scene access" [A HF] nhưng là cảnh dựng trong app). Dấu vân tay ⚠ "cũ" khi đổi bối cảnh = tương đương "sửa Element lan ra" của LTX nhưng **báo cho người dùng** thay vì âm thầm vẽ lại. |
| **Nên học** | **Giọng gắn vào hồ sơ nhân vật** trong Kho (LTX / Kling) → dự án mới tự nhận giọng, `cast_voices` chỉ chọn cho nhân vật chưa có. |

### K3 · Storyboard / animatic
| | Nội dung |
|---|---|
| **Họ có** | **Higgsfield Popcorn**: tới 8 khung liên kết **mỗi lần sinh**, tới 4 ảnh tham chiếu (nhân vật + nơi + đạo cụ) [A HF]. **Dreamina Agent**: tới 40 khung đồng bộ một lượt [A]. **Seedance 2.0 / 即梦**: sinh **tờ lưới 9 ô** rồi làm video mạch lạc từ đó [B Zhihu / CSDN]; Seedream vẽ khung, Seedance dựng động [A volcengine]. **LTX**: storyboard → animatic, âm nhạc / SFX xếp ngay trên timeline storyboard [A ltx.io]. **Katalist**: chỉnh khung máy, góc, **tư thế nhân vật**, bố cục, đạo cụ từng khung; Generative Fill; xuất PowerPoint / ZIP / slideshow / Premiere, Final Cut [A KT]. |
| **Mình thiếu** | (1) Sinh **nhiều khung liên kết trong một lần gọi** — mình vẽ từng khung, ảnh trước làm tham chiếu (tốn lượt, nhất quán kém hơn lý thuyết). (2) Chỉnh **tư thế** từng khung bằng công cụ (mình sửa bằng chữ + vẽ lại). (3) Xuất storyboard ra PowerPoint / PDF để gửi người khác. |
| **Mình hơn** | **QC ảnh tự động 2 lớp** + agent QC trước cổng duyệt; animatic có **thoại TTS thật + nhạc + phụ đề** ở 0 USD (LTX có animatic nhưng không rõ có thoại thật hay không). |
| **Nên học** | **Thử "tờ lưới nhiều khung một lần sinh"** (Popcorn / 9 ô Seedance) cho một cảnh ngắn: 1 ảnh lưới 3×3 → cắt thành khung → so nhất quán + giá với vẽ từng khung. |

### K4 · Video (tham chiếu / khung đầu–cuối / nhiều shot)
| | Nội dung |
|---|---|
| **Họ có** | **Kling 3.0**: Custom Multi-Shot (chỉnh nội dung + độ dài từng shot) hoặc để model "automatically plan shot transitions", tổng 3–15 s; Start & End Frames [A kling.ai]. **MiniMax H3**: nhiều shot một lần sinh, tới 9 ảnh + 3 video + 3 âm tham chiếu [B getimg / Pixo]. **Google Flow**: Ingredients (nhiều ảnh), Frames to Video (đầu + cuối), **Extend** nối tiếp hành động của clip trước tới ≥ 1 phút, **Jump To** đọc cách clip trước kết thúc để sinh shot kế [A blog.google]. **Higgsfield Cinema Studio**: từng shot chỉnh thể loại, ánh sáng, ống kính, tiêu cự, khẩu độ, chuyển động máy; "speed ramp" [A HF]. **Runway Act-Two / Kling Motion Control**: diễn thật (quay mình) để điều khiển nhân vật [A RW]. |
| **Mình thiếu** | (1) **Nối tiếp hành động từ khung cuối clip trước** như Extend / Jump To — chính là lỗi "khựng, giật ở điểm cắt" của #8 (góp ý 1.5 / 1.6); mình đang giải bằng đoạn diễn liên tục theo góc máy (S3.4, chưa chạy thật). (2) **Diễn thật làm nguồn chuyển động** (performance capture) cho động tác khó — kỹ năng Kenta "không model nào tạo" (A/B S4.6). |
| **Mình hơn** | Chọn model **theo từng cảnh** qua đo A/B thật (Kling khung đầu tốt + rẻ nhất cho chạy, #10) — nền tảng tổng hợp (Higgsfield, OpenArt) cho chọn model nhưng người dùng tự chọn; câu khóa phong cách in-game và câu vật lý cơ thể theo loại hành động là kiến thức riêng của mình. |
| **Nên học** | (a) Khi hai shot liền là **cùng một hành động qua điểm cắt**, dùng **khung cuối clip trước làm khung đầu clip sau** (Kling Start & End / Flow Jump To) — rẻ hơn S3.4 vì không gen dư giây; A/B trên 1 cặp shot. (b) **Kling Multi-Shot tự cắt** (tối đa 15 s) làm lựa chọn thứ hai bên cạnh gom nhóm Seedance. (c) Video diễn tay làm tham chiếu chuyển động (G-MV8 đã ghi) — cho kỹ năng Kenta. |

### K5 · Khớp môi
| | Nội dung |
|---|---|
| **Họ có** | **Kling 3.0 Native Audio**: thoại nhiều nhân vật ("three or more characters"), giọng gắn Element; ngôn ngữ **Trung, Anh, Nhật, Hàn, Tây Ban Nha — không có tiếng Việt** [A kling.ai]. **Hedra Character-3**: ảnh + âm thanh → nhân vật nói, tới 10 phút, "40+" ngôn ngữ [A hedra.com / B]. **Pikaformance**: ảnh + âm → diễn mặt (mày, má, mắt), nhanh + rẻ theo hãng [B]. **Higgsfield Lipsync Studio**: **10 model khớp môi** trong một chỗ, từ nhanh–rẻ tới Veo 3 [A HF]. **Runway Act-Two**: mỗi nhân vật một đoạn diễn mặt riêng trên cùng video nhân vật → cùng nền, cùng ánh sáng [A RW, qua kết quả tìm kiếm]. |
| **Mình thiếu** | (1) **Nhiều lựa chọn khớp môi theo shot** kèm giá (nhanh–rẻ vs đẹp) — mình chỉ có Seedance nhận giọng + sync.so (tắt). (2) Khớp môi **sau khi tạo** cho ảnh / clip bất kỳ bằng tiếng Việt: Hedra ghi 40+ ngôn ngữ nhưng **không rõ có tiếng Việt**. (3) Đo khớp môi bằng mốc môi (S4.5 còn tồn). |
| **Mình hơn** | Giọng tiếng Việt **clone đội FF** có sẵn + chỉ đạo giọng; Seedance 2.5 nhận tham chiếu âm tiếng Việt [R `reference_clipai_docs_2026_09`]. Kling Native Audio **không** dùng được cho tiếng Việt → lợi thế đi qua Seedance là đúng. |
| **Nên học** | Bảng **"cách khớp môi theo shot"** ở Bước 4: mỗi shot nói thấy mặt → (a) Seedance kèm giọng / (b) khớp sau / (c) né (quay lưng, xa) + giá mỗi cách — giống Lipsync Studio nhưng trong trần. Các model ngoài ClipAI (Hedra, Pika) **cần tài khoản mới** → chỉ xét khi người dùng muốn. |

### K6 · Giọng / nhạc / SFX
| | Nội dung |
|---|---|
| **Họ có** | **LTX**: SFX "analyzes your visual content" rồi khớp hành động trên hình; nhạc từ thư viện hoặc tải lên; TTS; xếp trên timeline [A ltx.io]. **ElevenLabs Studio**: một timeline chung thoại + phụ đề + nhạc + SFX + video; tạo SFX bằng prompt ngay trên track; tách giọng khỏi nền khi lồng tiếng; có TTS tiếng Việt [A elevenlabs.io]. **OpenArt Music Video**: tải bài hát → phân tích lời → hình khớp [A/B]. **Kling / Veo / H3**: âm thanh sinh cùng video [A]. ClipAI: Eleven Music v2.5, Seed Audio 1.0 [R]. |
| **Mình thiếu** | (1) **SFX sinh từ hình** (video → SFX) — mình dùng thư viện âm thanh neo theo shot. (2) **Tách giọng / nền** khi dùng âm thanh sinh kèm video (nếu clip Seedance có tiếng nền lẫn). |
| **Mình hơn** | **Âm thanh trước, hình sau** (TTS nháp khóa timeline, cổng độ dài ±10 %); nhạc theo ý đồ, tự sửa lặng > 8 s / lặp, dời nhạc về đầu cảnh thật; chuẩn độ to −14 LUFS + −1 dBTP — không sản phẩm nào ở trên công bố chuẩn độ to / kiểm tra này (không rõ). |
| **Nên học** | Thử **video → SFX** cho shot hành động (va chạm, bước chân) khi thư viện không có âm hợp — qua model âm thanh có sẵn trên ClipAI nếu có (cần kiểm; không rõ). Công cụ `tools/audio_listen.py` (demucs) đã tách được giọng / nền → dùng lại khi cần. |

### K7 · Dựng
| | Nội dung |
|---|---|
| **Họ có** | LTX: trình dựng trên web, timeline có track thoại / nhạc / SFX [A]. **Chỉnh sửa sau khi sinh**: Runway **Aleph / Edit Studio** đổi góc máy, ánh sáng, thêm / xóa vật trên clip có sẵn [A runway.com]; Google Flow **Insert / Remove** (dựng lại nền khi xóa) [A blog.google]; ClipAI **Advanced Edit** sửa từng chỗ bằng vẽ / ghi chú [R]. Katalist xuất sang **Premiere / Final Cut** [A KT]. |
| **Mình thiếu** | (1) **Sửa clip thay vì sinh lại** — S4.12 ⏸. (2) **Xuất timeline cho phần mềm dựng** (EDL / FCPXML / Premiere) để người dựng chỉnh tay — mình chỉ xuất mp4 + .srt. (3) Trình dựng kéo thả (mình có timeline tổng chỉ xem). |
| **Mình hơn** | Dựng **tự động theo luật nghề** (chuyển cảnh vẽ trong chuyển động, hồi tưởng, cắt theo chuyển động, giữ shot kết, phụ đề vùng an toàn TikTok) — các sản phẩm trên để người dùng tự dựng. |
| **Nên học** | **Xuất timeline sang Premiere** (FCPXML hoặc EDL + thư mục clip + .srt + track âm riêng): miễn phí, hợp người dùng làm trailer trên Premiere. Advanced Edit (S4.12) giữ nguyên ưu tiên. |

### K8 · QC
| | Nội dung |
|---|---|
| **Họ có** | Không tìm thấy sản phẩm nào **công bố** QC tự động (kiểm lỗi hình, trôi mặt, khung lẫn, độ to) trước khi giao — **không rõ**. Cách của họ là người xem + sinh lại / sửa (Aleph, Advanced Edit). |
| **Mình thiếu** | Đo khớp môi (S4.5). |
| **Mình hơn** | **Rõ nhất ở khâu này**: QC ảnh 2 lớp, agent QC Claude Vision có sổ tay + bộ nhãn, QC clip bằng số đo (dấu đỏ lọt 17/17, lẫn khung 4/33, `look_drift`), QC bản dựng cuối bằng máy. |
| **Nên học** | Không có gì mới để học; giữ. Có thể nối QC clip → **gợi ý sửa bằng Advanced Edit** thay vì sinh lại khi lỗi cục bộ (sau S4.12). |

### K9 · Kiểm soát chi phí
| | Nội dung |
|---|---|
| **Họ có** | Mô hình **credit trả trước**; Kling ghi giá theo giây (1080p có âm 12 credit/s, không âm 8) [A kling.ai]; Higgsfield ghi credit từng model (Veo 3 khớp môi 58 credit / clip 1080p) [A HF]; **Runway Explore Mode**: gói Unlimited sinh không giới hạn ở tốc độ chậm, credit cho hàng nhanh [A help.runwayml.com]; ClipAI **Sample Mode** bản mẫu 480p → duyệt → 1080p [R]. |
| **Mình thiếu** | **Hàng rẻ / chậm cho bản nháp** kiểu Explore Mode / Sample Mode — đã có S4.11 ⏸ (cần thử API). |
| **Mình hơn** | Ước tính **trước khi bấm**, dự tính cả dự án chia khâu, **khóa cứng 3 tầng**, dừng vẫn giữ kết quả, đo cache Claude. Không sản phẩm nào công bố trần theo dự án (không rõ) — họ chỉ có số dư credit. |
| **Nên học** | Hiện giá theo **credit ClipAI + USD** song song nếu người dùng đối chiếu với web ClipAI (nhỏ, tùy người dùng). |

### K10 · Cộng tác / chia sẻ
| | Nội dung |
|---|---|
| **Họ có** | Katalist: link trình chiếu công khai, gói nhiều người [A KT]; LTX: pitch deck cho phim / TV [A ltx.io]; Volcengine: cộng tác nhiều nhóm có phân quyền [A]. |
| **Mình** | Dashboard nhiều phiên (mã `?s=`), không có bình luận theo khung / shot. Nhu cầu không rõ — dự án hiện một người dùng. |

## 4. Tổng hợp: hơn / kém
**Mình hơn (giữ):** Director hai lượt + người xem lần đầu + kỹ năng 3 vai có căn cứ · QC tự động nhiều lớp tới bản dựng cuối · ước tính + khóa
cứng chi phí · âm thanh trước và chuẩn độ to · dựng tự động theo luật nghề + phụ đề vùng an toàn TikTok · bối cảnh từ mô hình 3D thật ·
giọng tiếng Việt clone đội FF (Kling Native Audio không có tiếng Việt).

**Mình kém:** sinh nhiều khung / nhiều shot **một lần** (Popcorn, Dreamina, Kling Multi-Shot, H3) · **nối tiếp hành động** qua điểm cắt
(Flow Extend / Jump To) · **sửa clip** thay vì sinh lại (Aleph, Flow Insert/Remove, ClipAI Advanced Edit) · **nhiều lựa chọn khớp môi** ·
**diễn thật làm nguồn chuyển động** (Act-Two / Motion Control) · xuất sang phần mềm dựng · giọng gắn vào hồ sơ nhân vật · danh tính "đã học".

Lưu ý: phần "mình hơn" chủ yếu là **khâu kiểm và điều khiển**; phần "mình kém" chủ yếu là **khả năng model / nền tảng** — nhiều thứ phụ thuộc
ClipAI có mở qua API hay không.

## 5. Đề xuất mượn (chờ người dùng chọn — S8.4 mới đưa vào TODO)
Ký hiệu: 💻 miễn phí (code) · 💵 tốn tiền (cần duyệt + ước tính trước) · 🔍 cần kiểm API ClipAI trước.

| Ưu tiên | Mã đề xuất | Việc | Học từ | Liên quan việc sẵn có | Loại |
|---|---|---|---|---|---|
| 1 | X1 | **Nối hành động qua điểm cắt**: shot sau dùng khung cuối clip trước làm khung đầu khi hai shot là một hành động liên tục; A/B 1 cặp shot so với S3.4 | Flow Jump To / Extend, Kling Start & End [A] | lỗi 1.5 / 1.6 #8, S3.4 | 💻 + 💵 nhỏ |
| 2 | X2 | **Sửa clip lỗi cục bộ** (mặt, tay) thay vì sinh lại; QC clip gợi ý "sửa" hay "sinh lại" | Aleph, Flow Remove, ClipAI Advanced Edit | S4.12 ⏸ | 🔍 + 💵 |
| 3 | X3 | **Bản nháp rẻ → bản cuối** | ClipAI Sample Mode, Runway Explore | S4.11 ⏸ | 🔍 |
| 4 | X4 | **Bảng cách khớp môi theo shot** (Seedance kèm giọng / khớp sau / né) + giá mỗi cách, chọn ở Bước 4 | Higgsfield Lipsync Studio | S4.2, S4.6 (c) | 💻 |
| 5 | X5 | **Tờ lưới nhiều khung một lần sinh** cho một cảnh → cắt khung → so nhất quán + giá với vẽ từng khung | Popcorn, 即梦 9 ô, Dreamina | step2 | 💵 nhỏ |
| 6 | X6 | **Xuất timeline sang Premiere** (FCPXML / EDL + clip + .srt + track âm) | Katalist | step5 | 💻 |
| 7 | X7 | **Giọng là thuộc tính nhân vật trong Kho**, dự án mới tự nhận | LTX Elements, Kling voice binding | S2.1, `voices_vi.json` | 💻 |
| 8 | X8 | **Kling Multi-Shot** (tự cắt ≤ 15 s) làm lựa chọn gom nhóm thứ hai bên cạnh Seedance | Kling 3.0 | S4.8, model_router | 🔍 + 💵 |
| 9 | X9 | **Diễn tay làm tham chiếu chuyển động** cho kỹ năng / động tác khó (Kenta) | Act-Two, Kling Motion Control | G-MV8, S4.6 | 💵 |
| 10 | X10 | Video → SFX cho shot hành động khi thư viện thiếu | LTX SFX, ElevenLabs | step5 | 🔍 |

**Không đề xuất:** Soul ID / Hedra / Pika / Runway (cần tài khoản mới, ngoài ClipAI — trái quyết định "mọi lời gọi qua ClipAI + sổ chi";
chỉ xét nếu người dùng muốn) · nhập kịch bản bằng tệp, cộng tác, pitch deck (chưa thấy nhu cầu).

## 6. Nguồn (đọc 2026-09-29)
- LTX: [LTX Studio](https://ltx.io/studio) · [Introduction to Elements](https://help.ltx.io/hc/en-us/articles/33578393195922-Introduction-to-Elements) · [Storyboard generator](https://ltx.io/studio/platform/ai-storyboard-generator) · [Animatics](https://ltx.io/studio/platform/animatics-software) · [Add audio & VFX](https://ltx.io/studio/platform/add-audio-to-video) · [AI lip sync](https://ltx.io/studio/platform/ai-lip-sync) · [B: Luma review](https://lumalabs.ai/news/ltx-studio-review)
- Runway: [Act-Two multi-character (help, 403 khi đọc)](https://help.runwayml.com/hc/en-us/articles/41748090660499-Creating-Multi-Character-Dialogues-with-Act-Two) · [Introducing Aleph](https://runway.com/research/introducing-runway-aleph) · [Edit Studio](https://help.runwayml.com/hc/en-us/articles/51683104370451-Creating-with-Edit-Studio) · [Unlimited / Explore Mode](https://help.runwayml.com/hc/en-us/articles/37309724921747-Why-does-the-Unlimited-plan-have-credits) · [B: ChatForest Gen-4](https://chatforest.com/reviews/runway-gen-4-ai-video-generation-multi-shot-consistency/)
- Higgsfield: [Script → storyboard & shot list](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) · [Popcorn](https://higgsfield.ai/blog/The-AI-Storyboard-Generator-That-Feels-Like-Directing) · [Cinema Studio](https://higgsfield.ai/blog/cinema-studio-guide) · [Lipsync / talking videos](https://higgsfield.ai/blog/make-ai-lipsync-videos) · [Avatar generators (Soul ID, Lipsync Studio)](https://higgsfield.ai/blog/best-ai-avatar-generators-talking-videos)
- Kling: [Kling VIDEO 3.0 Model Guide](https://kling.ai/quickstart/klingai-video-3-model-user-guide)
- 即梦 / Dreamina: [Seedance 2.0 多镜头叙事 (Volcengine)](https://www.volcengine.com/article/40396) · [Dreamina AI video agent](https://dreamina.capcut.com/ai-video/ai-video-agent) · [Dreamina script to storyboard](https://dreamina.capcut.com/resource/script-to-storyboard) · [B: Zhihu Seedance 2.0 短剧](https://zhuanlan.zhihu.com/p/2011197758191730921) · [B: CSDN Seedance 2.0 指南](https://blog.csdn.net/qq_73472828/article/details/160726102)
- Google Flow: [Veo 3.1 updates in Flow](https://blog.google/innovation-and-ai/products/veo-updates-flow/) · [5 tips for Flow](https://blog.google/technology/ai/flow-video-tips/)
- MiniMax: [Hailuo Video Agent](https://www.minimax.io/news/video-agent) · [Hailuo 2.3 & Media Agent](https://www.minimax.io/news/minimax-hailuo-23) · [B: getimg H3](https://getimg.ai/models/minimax-h3)
- Katalist: [AI Storyboard Generator](https://www.katalist.ai/ai-storyboard-generator)
- OpenArt: [OpenArt × FLUX.1 Kontext](https://bfl.ai/blog/openart-with-flux1-kontext)
- Hedra: [Character 3](https://www.hedra.com/models/video/hedra/character-3)
- Pika: [B: Pikaformance](https://pikaais.com/pikaformance/)
- ElevenLabs: [Dubbing Studio](https://elevenlabs.io/docs/eleven-creative/products/dubbing/dubbing-studio) · [Voiceover Studio](https://elevenlabs.io/docs/eleven-creative/audio-tools/voiceover-studio) · [Vietnamese TTS](https://elevenlabs.io/text-to-speech/vietnamese)
- Repo: `PLAN.md`, `docs/KE_HOACH_SUA_SAU_DU_AN_8.md`, `devsys/areas.json`, `docs/CLIPAI_FEATURES.md`, `docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md`, `docs/AB_HANH_DONG_S4_6_2026-09-29.md`
