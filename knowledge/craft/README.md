# Kho kỹ thuật chuyên môn `knowledge/craft/` (S0.11, lượt 2 — 2026-09-29)

> Kho **tư liệu** cho ba nghề Đạo diễn / Quay phim / Dựng: mỗi kỹ thuật = cách làm + **nhiều** ý đồ có thể phục vụ (có điều kiện ngữ cảnh) +
> ví dụ có mốc giây từ mẫu đã phân tích + nguồn. Viết theo `PHUONG_PHAP_PHAN_TICH.md` (4 tầng: quan sát → ý đồ → kỹ thuật → gợi ý).
> **Không phải bảng tra.** Không nạp tự động vào prompt (code chưa đọc thư mục này) — Đạo diễn / Quay phim / Dựng (`knowledge/roles/`,
> `knowledge/editor/` — riêng `knowledge/editor/` chỉ nạp các khối `<!-- review -->` vào bước duyệt bản thô) chỉ lấy sang khi đã đủ điều kiện "gợi ý cho pipeline" (≥ 2 mẫu khác nhau hoặc nguồn chuyên gia xác nhận).

## Bốn nguyên tắc của người dùng (bắt buộc khi đọc / thêm)
1. **Kỹ thuật không có nghĩa mặc định.** Không viết "X = Y". Viết "ở [mẫu, mốc giây], X được dùng để Y, vì [ngữ cảnh]".
2. **Không khái quát từ 1 mẫu.** 1 mẫu → chỉ ghi "đã thấy ở …" (tầng 2); ≥ 2 mẫu khác kênh / khác phim → "cách làm lặp lại" kèm điều kiện.
3. **Luật từ phim tham khảo chỉ là gợi ý theo phong cách** — trộn được, không bắt buộc (vd "MV cắt theo phách" đã bị 2 MV bác, xem `dung.md`).
4. **Chuyển cảnh che máy phải thiết kế trong chuyển động** (vật / người đi ngang ống kính, máy lia theo vật, máy tiến vào vật che kín khung)
   — không phải chèn bù một cận vật ở khâu dựng (`chuyen_canh.md`).

## Các nhóm
| File | Nhóm | Số mục |
|---|---|---|
| `may_quay.md` | Máy quay: cỡ cảnh / độ dài giữ khung, ống kính, độ sâu trường ảnh, ánh sáng có nguồn, mức "động" của máy | 6 |
| `goc_may.md` | Góc: ngang mắt, thấp, cao / từ trên, qua vai, nhìn thẳng ống kính, nghiêng | 6 |
| `chuyen_dong_may.md` | Chuyển động máy: tĩnh, đẩy / lùi, zoom, lia, bám theo, cầm tay, cần cẩu, xoay trục, vòng cung, dolly zoom, cú máy dài | 11 |
| `chuyen_canh.md` | Chuyển cảnh: cắt cứng, che máy trong chuyển động, đường máy trong một clip, chớp trắng / loé sáng, shot nối bối cảnh, nhảy thời gian / thực tại, cắt khớp | 7 |
| `dung.md` | Dựng: thứ tự ưu tiên điểm cắt, nhịp theo kịch, cụm shot ngắn, giữ shot dài, tiết chế cắt hành động, cắt xen, cắt theo câu vs phách, mở bằng cảnh tương lai, lớp chữ trong hình, ranh giới tập, đoạn kể không lời | 11 |
| `am_thanh.md` | Âm thanh: thiết kế từ lúc viết cảnh, tắt nhạc dưới khoảnh khắc then chốt, im lặng có chủ đích, âm nhấn trùng cắt, tim đập, nhạc nền liền vs thưa, màu nhạc theo nhịp, nhạc ở shot mở không gian (có phản ví dụ), đoạn thiết lập không nhạc, âm ngoài khung / J-L, giọng nội tâm, motif âm (giả thuyết) | 12 |

Mỗi mục có dòng **Độ tin**: *chắc* (số đo + ≥ 3 mẫu hoặc nguồn chuyên gia đọc trọn) · *khá* (≥ 2 mẫu khác kênh) · *có thể* (1–2 mẫu, chưa
nghe tai) · *giả thuyết* (chưa có mẫu, chỉ từ nguồn / suy luận — ghi rõ).

## Mẫu đã phân tích (S0.12) — mã dùng trong ví dụ
File đầy đủ ở `research/craft/s0_12/NN_*.md`; tổng hợp `research/craft/s0_12/TONG_HOP.md`. Cách ghi mốc: `[07 138–154s]` = video 07, giây gốc
của đoạn 1 (bắt đầu 0:00); `[07 đ2 +33–40s]` = đoạn 2, **giây tính trong file đoạn tải về** (mốc gốc chỉ ước tính ±10–30 s do cắt theo keyframe).
Số đo: điểm cắt `ffmpeg scene`, chuyển động máy OpenCV, âm `ebur128` + `silencedetect` + `tools/audio_listen.py` ("nghe bằng số" — chưa nghe tai).

| Mã | Mẫu | Loại |
|---|---|---|
| 01 | 《夫人又在掉馬甲了》 AI心動劇場 | AI drama 9:16 |
| 02 | TOMORROW (Omeleto) | phim ngắn CGI 3D |
| 03 | WARLIKE (BIGFILMS) | hành động |
| 04 | 《我的婆婆是軟柿子》 | AI drama 9:16 |
| 05 | RISE (Worlds 2018) | cinematic game CGI |
| 06 | 《逃不出大哥手掌心》 | AI drama 16:9 |
| 07 | DramaBox "Doting Snake Lord" | AI drama huyền huyễn 9:16 |
| 08 | "Fortnight" (Taylor Swift) | MV quay thật, đen trắng |
| 09 | 《大師兄》 | phim ngắn AI võ hiệp 16:9 |
| 10 | DramaBox "Your Dumped Housewife Is Your Boss" | AI drama 9:16 |
| 11 | TopDrama "Top Actor… Dating Show" | AI drama hài lãng mạn 9:16 |
| 12 | Knight Drama 《剛離婚，首富老爸找上門》 | AI drama "vả mặt" 9:16 |
| 13 | 《天命神算》 | AI 漫剧 tranh động 16:9 |
| 14 | SuperDrama (trọng sinh) | AI drama 9:16 |
| 15 | DramaBox "Wrong Stepbrother" | AI drama 9:16 |
| 16 | FEELING THROUGH (Omeleto) | phim ngắn quay thật |
| 17 | STALLED (Omeleto) | phim ngắn quay thật, hài sci-fi |
| 18 | Night of the Foxes | phim ngắn quay thật |
| 19 | Kings of Triad (Kevin Le) | hành động võ thuật |
| 23 | "we can't be friends" (Ariana Grande) | MV kể chuyện |
| 25 | Leaf of Faith (CGMeetup) | phim ngắn CGI không lời |
| 20 | NIGHT SHIFT (Lorenz Ruwwe) | hành động quay thật, hẻm Sài Gòn, tiếng Việt |
| 21 | Kodama (Short of the Week) | hành động samurai + VFX, rất tối |
| 22 | "Not Like Us" (Kendrick Lamar) | MV rap kể chuyện |
| 24 | New Born — LUNA (Kling AI) | **MV làm bằng AI** |
| 26 | Crunch (CGMeetup) | phim ngắn CGI 3D |
| 27 | The Last Bastion (Blizzard) | phim ngắn CGI game, không thoại |
| 28 | RESET (Max Barskih) | **phim ngắn AI** sử thi |
| CM | Clip mẫu ClipAI (MV 201 s) | `docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md` |

Video 20–28 viết file 2026-09-29 tối; ví dụ của chúng ghi ở dòng "**Ví dụ thêm (S0.12 mẫu 20–28)**" trong từng mục. Phim tối (20, 21):
số shot phụ thuộc ngưỡng cắt — xem file từng video.

## Nguồn
Mã `[Qn]` / `[En]` là của `knowledge/sources.md`; mã `[Sn]` và `#n` là của `research/craft/NGUON.md`. **Đọc trọn ở lượt 2 (2026-09-29, WebFetch):**

| Mã | Tác giả — vai trò | Bài | Độ tin |
|---|---|---|---|
| C1 | Jay Holben — nhà quay phim, cây bút American Cinematographer (ASC) | "Shot Craft: Tools for Camera Movement", 05/04/2024 — theasc.com/article/shot-craft-camera-movement/ (= `[Q20]`) | cao |
| C2 | Randy Thom — giám đốc sáng tạo âm thanh Skywalker Sound, 2 Oscar | "Designing a Movie for Sound" — filmsound.org/articles/designing_for_sound.htm | cao |
| C3 | Evan Schiff — dựng *Nobody*, *John Wick 3*; phỏng vấn Steve Hullfish | "Art of the Cut — Nobody", Frame.io, 19/05/2021 — blog.frame.io/2021/05/19/art-of-the-cut-evan-schiff-nobody/ | cao |
| C4 | Walter Murch, ACE — dựng *Apocalypse Now*; phỏng vấn Steve Hullfish | "Art of the Cut — Walter Murch with clarifications on his books", 10/02/2020 — provideocoalition.com/aotc-murch-books/ | cao |

Đã đọc trọn ở lượt 1 (NGUON.md ghi "fetch trọn trang"): Runway "AI Camera Prompts" `[S1]`, Kling "AI Camera Control Guide" `[S3]`, Luma
"Camera Concepts" `[S4]`, StudioBinder "Camera Movements" `[S6]`. Nguồn chỉ có tóm tắt tìm kiếm (theasc.com trang chủ, LBBOnline, Team Deakins
chung) **không** dùng làm căn cứ ở kho này — mục nào chỉ dựa vào chúng được ghi *giả thuyết*.

## Đối chiếu với kiến thức đang dùng (mâu thuẫn đã thấy; E4 đã sửa 2026-09-29 — `knowledge/editor/` là tài liệu cho người/Claude, **chỉ các khối `<!-- review -->` của `editing.md` được nạp, vào bước duyệt bản thô** (`core/editor_review.py`); `role_text` chỉ đọc `director.md` + `dp.md`)
- `knowledge/editor/editing.md` E4: "cắt mỗi ô nhịp = thong thả, mỗi 1–2 phách = căng" — là **một cách** dựng theo nhạc; hai MV kể chuyện đo
  được (22 đoạn 1, 23 đoạn 1) cắt **không bám phách** (trúng phách 27% / 39% so với ngẫu nhiên 27% / 31%). → Ghi ở `dung.md` mục "Cắt theo câu
  vs theo phách"; **đã sửa E4 (người dùng duyệt 2026-09-29)**: điểm cắt bám câu / cảnh hoặc phách là lựa chọn theo ngữ cảnh.
- `knowledge/roles/dp.md` Q1 câu mở "thấp = áp đảo, anh hùng; cao = nhỏ lại…" đã có dòng "ý nghĩa góc không cố định" (S0.13) — kho này thêm
  ví dụ mốc giây (17, 25, CM) cho thấy góc thấp phục vụ cả "đe doạ trực diện" lẫn "tầm mắt nhân vật nhỏ".
- `research/craft/MAU_S0_12.md` dự đoán "MV cắt theo beat" — bị bác như trên.
- Bản nháp lượt 1 (`research/craft/draft/`) giữ nguyên làm lịch sử; mục nào đã vào kho thì kho là bản đúng.

## Còn mở (việc sau, không chặn)
- Nghe bằng tai các chỗ ghi "nghe bằng số" (danh sách ở `TONG_HOP.md` mục Tồn đọng).
- ~~Viết ví dụ từ 20–22, 24, 26–28~~ (xong 2026-09-29 tối, 21 dòng ví dụ ở 5 nhóm). Thêm mẫu cho các mục còn *giả thuyết* (ống kính tele / rộng, dutch, orbit, dolly zoom,
  whip pan) — chưa đo được bằng OpenCV hiện có.
- Nguồn còn chặn tải: ClipAI docs (403), Volcengine Ark (cần đăng nhập) — phần "với video AI" dựa vào `dp.md` Q5 và `research/craft/trung_quoc/PROMPT.md`.
