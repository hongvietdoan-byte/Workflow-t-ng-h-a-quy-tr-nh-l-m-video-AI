# S0.15 lượt 2 — Từ spotting tới prompt nhạc: đối chiếu từng dòng code nhạc hiện có (2026-09-29)

> Lượt 1: `nhac_nen.md` (15 kỹ thuật), `nhac_theo_the_loai.md` (8 thể loại), `nhac_bai_hoc_pipeline.md` (10 bài học — đối chiếu `music_timing`
> ở mức ý tưởng). Lượt 2 làm 3 việc lượt 1 chưa làm: (1) lấy **cách ghi spotting của người làm nghề** làm khung cho brief; (2) đưa **số đo thật
> của 14 video mẫu S0.12** (`research/craft/s0_12/TONG_HOP.md` mục 4–8) vào làm bằng chứng — nguồn ngoài cho vertical drama vẫn thiếu;
> (3) đọc **từng dòng** `core/music_timing.py`, `core/music.py`, `core/music_fit.py`, `core/claude_tasks.music_brief`, `prompts/04_music_brief.md`,
> `core/sound_intent.py` và chỉ ra chỗ gán nghĩa cố định. Không sửa code trong việc này. Mọi kỹ thuật = tư liệu có điều kiện.
> Nguồn mới #51–#53 ở `research/craft/NGUON.md`.

## 1. Spotting sheet của người làm nghề — khung cho một "cue"

Hai nguồn độc lập, cùng hướng:
- **Heather Fenoughty** (composer, 2021) [51]: 4 bước — (a) **có cần nhạc không**: nhạc chỉ vào khi "add or change something" có chủ ý;
  (b) **chức năng** của cue (đẩy tông, gợi nơi/thời, trôi thời gian, đóng/mở đoạn, phát triển chủ đề, *chữa lỗi dựng*); (c) **vào/ra ở đâu,
  vào/ra kiểu gì** — đột ngột (gây chú ý) hay dần (tác động ngầm); (d) ghi thành bảng.
- **pitch.dog** (2026-09-17) [52]: đầu phiếu ghi **đúng bản dựng** (tên file + phiên bản, độ dài, trạng thái âm thanh, hệ thời gian, ngày, đề xuất
  hay đã chốt); mỗi cue: mã cố định, vào/ra + kiểu biên, **thay đổi bên trong cue**, **1 câu chức năng**, **kiểu dừng** (cắt / mờ / kéo xuống),
  trạng thái. Hai ý quan trọng: *chỗ nhạc dừng hoặc không bao giờ vào cũng là quyết định, phải ghi*; khi bản dựng đổi, **ra phiếu mới, ghi mốc nào
  dời và vì sao — không dời đều mọi mốc** bằng một độ lệch.
- ModWheel (lượt 1, #31): mốc ra quan trọng ngang mốc vào.

**Pipeline đang có gì tương ứng:**

| Trường spotting | Pipeline | Nhận xét |
|---|---|---|
| Bản dựng + thời gian thật | `render_timeline` / `sections(seconds=…)` | ✅ đúng nghề (lượt 1 bài 1) |
| Không dời đều khi bản dựng đổi | `music_fit.segments` dời **từng đoạn** lên đúng cảnh thật (co giãn ±13 %, lặp, mờ) | ✅ trùng khuyến nghị [52] — bằng chứng ngoài cho thiết kế #8 |
| Vào/ra, thay đổi bên trong | `turns` + `beats()` (ngoặt, hồi tưởng, đỉnh cảm xúc, `sound.music`) | ✅ có |
| **Có cần nhạc không** (cả phim / từng đoạn) | `music_mode` none/library/AI cho **cả phim**; từng đoạn: chỉ `sound.music=cut` (tối đa `MAX_OFF_S` 8 s) | ⚠ nhạc mặc định **phủ từ 0 tới hết**; "không nhạc" dài là ngoại lệ bị giới hạn — ngược với câu hỏi đầu tiên của spotting |
| **Câu chức năng** của cue | không có trường; `_style()` chỉ ra *màu nhạc* | ⚠ thiếu "vì sao nhạc ở đây" |
| **Kiểu vào/ra** (đột ngột / dần) | cố định: mọi chỗ ngoặt "flows … over about one bar", nhạc mờ vào 0,3 s | ⚠ một kiểu cho mọi chỗ |
| Ghi lại chỗ cố ý không nhạc | `sound_intent` + manifest | ✅ một phần |

## 2. Bằng chứng tự đo (S0.12, 14 video, "nghe bằng số" — chưa nghe bằng tai) — tóm lại để đối chiếu

Từ `TONG_HOP.md` (độ tin "khá" theo ghi chú ở đó):
1. **Hai kiểu nền**: liên tục (97–100 % thời lượng có nhạc: 04, 06–09, 11–13, 16) và **thưa / bật tắt** (14–69 %: 01, 10, 14, 15); một phim có thể
   đổi kiểu theo cảnh (10, 17). **Không có luật "AI drama = nhiều nhạc"** — kênh / cảnh chọn.
2. **Tắt nhạc ngắn dưới câu then chốt, nhạc về ở gần một điểm cắt** — 6 video, 9+ lần, dùng cho lật mặt, punchline hài, thú nhận, kết nhiệm vụ →
   nghĩa do ngữ cảnh.
3. **Âm nhấn trùng điểm cắt** (8 video); **nhạc trồi ở shot mở không gian / nhân vật thoát ra**, ở drama thường sau một nhịp lặng (6 video).
4. **Lặng ở chỗ chuyển thời gian / thực tại** (mơ → tỉnh, trọng sinh; 5 video).
5. Hài (11) dùng marimba / accordion cả trong cảnh "nhà ma" — khớp nguồn nghề "nhạc cụ báo tông" (lượt 1 #44).

## 3. Chỗ code nhạc đang gán nghĩa cố định / khái quát từ #8 (tìm được khi đọc từng dòng)

| # | Chỗ | Đang làm | Vì sao là vấn đề (theo quy tắc dự án) |
|---|---|---|---|
| C1 | `music_timing.brief()` dòng `head` | Mọi dự án: "a …-second **vertical Free Fire short drama**" + "**One simple, memorable love motif** carries the whole film: introduced softly, strained in the conflict, bare in the memory, full at the end" | Cấu trúc câu chuyện **tình yêu của #8** thành khung mặc định cho mọi phim; **không đọc `genre`** của dự án (khác đường Claude `claude_tasks.music_brief` có gửi thể loại). Phim hành động / hài / MV sẽ nhận "love motif". |
| C2 | `MOTIF` + `beats()` | Hồi tưởng luôn = "love motif on a music-box / soft piano, dreamy and warm"; **shot cuối luôn** = "resolution: the love motif in full, warm and hopeful" | Hồi tưởng có thể là chấn thương, kết có thể bỏ lửng / bi kịch / cliffhanger (S0.12: "未完待续", kết bằng cú ngã). Gán một nghĩa cho một kỹ thuật. |
| C3 | `score_draft()` | Chấm bản nháp bằng **độ to TĂNG** ở mỗi mốc ngoặt | Mốc ngoặt có thể là **rơi vào lặng** (S0.12 mục 2, 4; lượt 1 "khoảng lặng") — bản nháp làm đúng ý đó bị chấm điểm thấp. Nên chấm "thay đổi rõ" theo hướng brief yêu cầu (lên hoặc xuống). Docstring đã nói "or change clearly" nhưng công thức chỉ cộng mức tăng. |
| C4 | `DRAMA_BPM_MAX = 110` | Trần BPM áp cho **mọi** dự án | Sửa từ #8 (drama). Hành động / MV / quảng cáo game có thể cần nhanh hơn; nên theo thể loại / ý đồ, không một trần chung. |
| C5 | `MOOD_STYLES` | Mood → 1 câu màu nhạc cố định, khớp đầu tiên thắng; ngoài danh sách → "tense hybrid" nếu có chữ hành động, còn lại "understated underscore" | Lượt 1 bài 2, 7 đã nêu; bổ sung: cùng mood nhưng **chức năng khác** (che giấu vs dồn nén) ra cùng nhạc; nhạc không biết "vì sao" nó ở đó (thiếu câu chức năng — mục 1). |
| C6 | `prompts/04_music_brief.md` | "cao trào rơi đúng cảnh hero; kết thúc gọn trước card cuối"; "không lời" mặc định | Hợp nhiều phim nhưng là mặc định cứng; MV dẫn bằng bài hát (có lời) và phim kết lửng thì khác. Có thể viết thành **mặc định có điều kiện** ("nếu … thì …"). |
| C7 | Nhạc phủ liên tục | Một bản nhạc cho cả phim, chỉ khoét lỗ ≤ 8 s | S0.12 cho thấy kiểu "thưa, bật tắt" là lựa chọn thật của nhiều phim; pipeline chưa có cách chọn kiểu nền **theo cảnh**. `MAX_OFF_S` sinh ra để sửa lỗi #8 ("mất nhạc nền") — đúng cho #8, nhưng là trần chung. |

Ghi chú công bằng: các điểm này đều có lý do từ góp ý người dùng ở #8 (ghi trong comment code). Vấn đề không phải "sai", mà là **nghiệm của một
phim đã thành mặc định cho mọi phim** — đúng loại lỗi S0.13 đã rà ở knowledge/ nhưng chưa rà ở code nhạc.

## 4. Brief nhạc → prompt nhạc: đề xuất cấu trúc (tổng hợp lượt 1 + lượt 2)

Hai lớp tách rời (lượt 1 bài 2): **Đạo diễn viết spotting** (tiếng Việt, theo cảm xúc + chức năng) → **lớp dịch** sang prompt model nhạc.

Mỗi cue (một đoạn nhạc liền) trong spotting:
```
cue: 1M2 · vào 0:08.0 (kiểu: dần qua 1 ô nhịp | đột ngột | sau lặng 0,6 s) · ra 0:20.5 (cắt | mờ | kéo xuống dưới thoại)
cần nhạc?: có — vì … | không — vì … (lặng có chủ ý)
chức năng (1 câu): dồn nén trước lời thú nhận / che giấu nỗi sợ / trôi thời gian …
cảm xúc: … · nhạc cụ báo tông (nếu có): …
thay đổi bên trong: 0:14.2 nhạc rút gần như tắt dưới câu then chốt; 0:17.9 âm nhấn trùng cắt
dưới thoại?: nhiều / ít
```
Lớp dịch sang model nhạc (ElevenLabs composition plan / Seed Audio — lượt 1 #38, #39): mỗi cue → một chunk (text + duration_ms +
positive/negative styles), chunk "không nhạc" → không gửi, để trống trên timeline. Nguồn TQ lượt 1 (#16–18): ghi rõ instrumental khi có thoại;
"phong cách + nhạc cụ + cảm xúc + tempo" là khung ngắn đủ ý.

## 5. Khác nhau theo thể loại — bổ sung lượt 2 (điều kiện, không luật)

| Thể loại | Lượt 1 nói | Lượt 2 thêm (bằng chứng) | Hệ quả cho brief |
|---|---|---|---|
| Short drama dọc | cue dày, sting ở cliffhanger — độ tin thấp | S0.12 đo: cả hai kiểu nền đều có; lặng dưới câu then chốt; nhạc **không** ngắt qua thẻ "未完待续" ở 11 | kiểu nền là **lựa chọn** theo kênh / cảnh, không mặc định |
| Hài | "giữ mặt nghiêm", nhạc cụ báo tông | 11: marimba / accordion cả trong cảnh "sợ"; nhạc tắt dưới punchline rồi về ở cắt | nhạc cụ báo tông + lặng trước punchline là 2 lựa chọn |
| Hành động | biết lùi lại | 03, 05 nền liên tục (mục 9 TONG_HOP) | trần BPM 110 (C4) không hợp |
| MV | hình theo nhạc | 08: nhạc trồi theo cấu trúc bài | nhạc có trước → brief đảo chiều (hình theo nhạc), `score_draft` không áp |
| Phim ngắn quay thật | — | 16, 17: độ dày âm thanh như đường cong kịch (mở thưa 48 quãng lặng → cao trào 100 %) | "thưa → dày" là một cấu trúc chọn được |
| CGI / game | motif ngắn lặp, đổi màu theo pha | — (chưa đo mẫu mới) | giữ lượt 1 |

## 6. Gợi ý kiểm được (không sửa code trong việc này — chờ người dùng chọn)

| # | Gợi ý | Căn cứ | Cách kiểm | Chi phí |
|---|---|---|---|---|
| M1 | `brief()` đọc `genre` + ý đồ dự án; bỏ "vertical Free Fire short drama" / "love motif" cứng — motif là **tùy chọn** Đạo diễn đặt (tên + nhạc cụ + khi nào xuất hiện), không có thì không nhắc | C1, C2 | test: dự án genre ACTION không có chữ "love motif" trong prompt; dự án có `music_motif` thì có; #8 dựng lại brief vẫn ra motif (không lùi) | 0 |
| M2 | Nghĩa của hồi tưởng / kết lấy từ Đạo diễn (trường `sound.music_why` hoặc `ending_tone`), mặc định trung tính | C2 | test: shot cuối có `ending_tone="cliffhanger"` → không có "resolution … hopeful" | 0 |
| M3 | `score_draft` chấm "thay đổi đúng hướng": mốc brief ghi "drops / almost silent" → thưởng mức **giảm**; còn lại thưởng tăng | C3, S0.12 mục 2 | test tổng hợp: 2 file sóng giả (một tăng, một giảm ở mốc) × 2 brief → điểm đúng chiều | 0 |
| M4 | Trần BPM theo thể loại (drama 110; hành động / MV / quảng cáo rộng hơn) thay hằng số chung | C4 | test `choose_bpm` với genre khác nhau | 0 |
| M5 | Thêm "câu chức năng" + "kiểu vào/ra" cho mỗi đoạn (từ Đạo diễn, tùy chọn) vào brief; chưa có thì giữ cách cũ | mục 1 [51][52] | test: đoạn có `music_function` → câu đó có trong prompt; độ dài prompt ≤ 1990 vẫn giữ | 0 |
| M6 | Cho chọn **kiểu nền theo cảnh**: liên tục / thưa (nhạc chỉ ở cue được spot) — `MAX_OFF_S` chỉ áp khi cảnh ở kiểu liên tục | C7, S0.12 mục 1 | test `sound_intent`: cảnh "thưa" cho phép lặng > 8 s mà không báo lỗi; cảnh "liên tục" giữ luật cũ | 0 code; nghe thử cần render (miễn phí) + người dùng nghe |
| M7 | `prompts/04_music_brief.md` viết lại thành mặc định có điều kiện ("nhạc là nền dưới thoại **khi** có thoại…", "kết gọn **trừ khi** kết lửng") + yêu cầu trả thêm `cues[]` theo khung mục 4 | C6 | test schema: JSON có `cues` hợp lệ; thiếu thì fallback như cũ | 0 (gọi Claude khi chạy thật: có phí nhỏ) |
| M8 | Phiếu spotting xuất ra đọc được (Bước 5): bảng cue mục 4 kèm "bản dựng nào, ngày" — để người dùng góp ý trước khi gen nhạc | [52] | test: file `SPOTTING.md` sinh từ brief, có header bản dựng | 0 |

Ưu tiên đề xuất: **M1 + M3** (sửa gán nghĩa cố định rõ nhất, rẻ, test được ngay), rồi M5/M7 (thêm "vì sao" cho nhạc), M6 cần người dùng nghe.

## 7. Còn thiếu
- Vẫn **chưa có phỏng vấn composer làm vertical drama** có tên (EN lẫn TQ): tìm 2026-09-29 không ra; 梁雨箫 (music director 《做我的老板，做我的妻子》)
  chỉ thấy qua snippet, bài gốc Zhihu chặn 403. Bằng chứng cho short drama dọc hiện dựa vào số đo S0.12 của chính dự án.
- Stinger trong game: vẫn chưa có composer game có tên nói trực tiếp (lượt 1 bài 8).
- Số đo S0.12 là "nghe bằng số" (demucs + AudioSet) — chưa nghe bằng tai; dùng làm giả thuyết có điều kiện.

## 8. Kết quả làm M1–M8 (2026-09-29, nhánh B7b — người dùng duyệt "làm nốt hoàn thiện")

Module mới `core/music_intent.py` (đọc giọng điệu / motif / kiểu kết của **dự án này**, không gọi model); `core/music_timing.brief()` dùng nó.
Test: `tests/test_music_intent.py` (22 test, theo từng M) + `tests/test_music_story.py` (fixture #8 thêm ý đồ "tình yêu" — motif tình yêu
giờ chỉ có khi truyện nói về tình yêu).

| M | Làm gì · ở đâu | Test |
|---|---|---|
| M1 | `music_intent.read_tone`: `music.tone` của Đạo diễn > thể loại là giọng điệu (MV, quảng cáo) > chữ trong mood / ý đồ các cảnh (hài · chính kịch · hành động; hòa thì hài thắng); không đọc được → **brief trung tính + ghi chú** (luật 1). Dòng đầu brief: dọc / Free Fire chỉ khi dự án 9:16 / game FF; danh từ phim theo giọng điệu. Motif: Đạo diễn đặt `music.motif`, hoặc chính kịch có chuyện tình → "love motif"; còn lại không nhắc. `MOOD_STYLES` không còn "the love motif" cứng (`{theme}`), mood hài đứng trước "urgent", "playful" của phim hài = "playful lightness" (không "uneasy") | `ToneTests` (6) |
| M2 | `music_intent.ending`: `music.ending` (resolve/open/cliffhanger/button/hit/close) > chính kịch: cảnh cuối ấm/hóa giải → resolve, không → open > mặc định theo giọng điệu (hài: button). Hồi tưởng: có motif → motif, "dreamy and warm" chỉ khi phim kết ấm, không thì "distant and fragile"; không motif → "a thinner, distant colour". Mọi câu kết giữ cụm "final hit at" để `music_fit` đọc được mốc kết. Chọn trường gốc `music` thay cho `ending_tone` / `sound.music_why` ở gợi ý gốc (một chỗ cho cả tone / motif / ending) | `EndingTests` (2) + `test_the_directors_music_block_wins` |
| M3 | `score_draft(..., dirs)` / `pick_best(..., dirs)`: mỗi điểm đổi đoạn chấm theo hướng brief yêu cầu — `down` thưởng mức **giảm** (trung bình 1 s sau), `up` thưởng tăng (như cũ), `change` thưởng thay đổi rõ bất kỳ chiều. `brief()["turn_dirs"]`: cảnh mở bằng `sound.music=cut` → down, còn lại so mức năng lượng của màu nhạc. Autopilot + `tools/pilot_run.py music` truyền `dirs` | `DraftScoreTests` (4) — sóng giả (vá `loudness`), không cần ffmpeg |
| M4 | Trần BPM theo giọng điệu (`TONES[...]["bpm_max"]`: chính kịch 110 = `DRAMA_BPM_MAX` cũ, hài 132, hành động / MV / quảng cáo 140, chưa rõ 120) | `TempoTests` — đoạn dài đúng 1 ô nhịp ở 128 BPM: hài chọn 128, chính kịch ≤ 110 |
| M5 | Trường tùy chọn trên `sound` của shot: `music_fn` (danh sách đóng tension/hide/release/reveal/time/place/comic/memory → câu tiếng Anh trong "Story moments"), `enter` soft/sudden (sudden → "Except at …: the change comes at once"); `sound_intent.clean` giữ / báo giá trị sai; prompt 17, 19 + director.md Đ9 thêm dòng mô tả | `FunctionAndEntryTests` (2); `music_fit.planned` vẫn đọc đúng các mốc; prompt ≤ 1990 |
| M6 | `sound.bed` sparse/continuous (theo thứ tự shot như cut/in): khoảng lặng bắt đầu trong đoạn "sparse" không bị cắt ở `MAX_OFF_S` (không `auto_in`), `music_plan` trả `sparse_off`, `final_qc.check_music` không chặn các khoảng đó, `warnings` không nhắc; brief ghi "very sparse, mostly resting". Nhạc vào bản dựng vẫn qua cờ `sound_intent` (TẮT) — **chưa nghe thử** (luật 5) | `SparseBedTests` (3) |
| M7 | `prompts/04_music_brief.md` viết lại: mặc định có điều kiện ("khi có thoại…", "kết gọn trừ khi kết lửng", motif / hồi tưởng / BPM theo phim) + khung spotting (cần nhạc không · chức năng · vào/ra) + `tone`, `cues[]` tùy chọn. `claude_tasks.music_brief` gửi thêm dòng "# Giọng điệu" (có lý do) và `sound` từng cảnh; `clean_cues` giữ cue hợp lệ, bỏ + ghi chú cue sai, thiếu `cues` = như cũ. Chưa gọi Claude thật (có phí nhỏ khi bấm nút) | `ClaudeBriefTests` (2, client giả) |
| M8 | `music_timing.spotting()` / `write_spotting()` → `SPOTTING.md` cạnh bản nháp (autopilot ghi khi gửi bản nháp theo nhịp dựng; `pilot_run music` cũng ghi): đầu phiếu = bản dựng nào (#id · ngày · tệp, hoặc "theo bảng shot"), giọng điệu + lý do, motif, kết, BPM; bảng cue 1M1… vào/ra/kiểu vào/hướng đổi/chức năng/bên trong; chỗ cố ý lặng. Bước 5: caption giọng điệu, cảnh báo ghi chú, ô mở "📋 Phiếu spotting" | `SpottingTests` (2) |

Không có gợi ý nào bị bỏ. Không cờ mới: M5/M6 là trường tùy chọn của Đạo diễn; phần nhạc vào bản dựng vẫn đi qua cờ `sound_intent` (TẮT như cũ).

### Bằng chứng: dựng lại brief từ CSDL thật (mở `?mode=ro`, không tạo nhạc)
Ghi chú: dự án **#10** ("A/B hành động S4.6 · Chia đôi") là một gag hài nhưng trong CSDL **không có** genre, mood, ý đồ cảm xúc hay
đầu cảnh — code không có chữ nào để đọc ra "hài". Vì vậy bằng chứng dùng thêm **#3** (kịch bản hài "Kenta xuyên tường cướp kill?!", mood
"tense but comedic", "comedic twist, cheeky") và thử #10 với khối `music` của Đạo diễn trên **bản sao trong bộ nhớ**.

| Dự án | Trước (code cũ) | Sau |
|---|---|---|
| #8 drama (theo bản dựng 84,5 s) | "vertical Free Fire short drama", love motif, 100 BPM, kết "resolution … warm and hopeful" | **giữ nguyên** (tone drama 5/6 cảnh; motif tình yêu vì ý đồ cảnh 6 nói "tình yêu"; kết resolve vì cảnh cuối "ấm áp"); khác duy nhất: "the motif on a lone cello" → "the love motif …"; `turn_dirs` = up, down, up, down, change |
| #3 hài (74 s) | "short drama", love motif, 108 BPM, "urgent … rising dread" cho cảnh "tense but comedic", "uneasy lightness", kết "love motif … hopeful" | "short comedy", **124 BPM**, không motif, câu "Comic timing: … stop dead right before a punchline", "comic: light pizzicato…", "playful lightness…", "quick comic stops and restarts…", kết "a short comic button" |
| #10 (không mood) | "short drama", love motif, kết "love motif … hopeful" (cho một gag chia bánh bao) | "short film", không motif, "the music closes simply" + **ghi chú "giọng điệu chưa rõ"** (Bước 5 hiện cảnh báo, autopilot ghi log) |
| #10 + `music: {tone: comedy, ending: button}` + shot "Chia đôi." `sound: {music: breath, music_fn: comic}` (bản sao) | — | "short comedy", trần 132, "0:28.0 comic timing: straight-faced, stops before the punchline", kết "comic button"; phiếu spotting 1M1–1M4 |
| #8 + `music: {ending: open}` (bản sao) | — | "left unresolved at the end", hồi tưởng "distant and fragile", "Stop on an unresolved final hit at 1:24.5" |

Chưa thử thật: chưa tạo bản nháp nhạc nào theo brief mới (tốn credit) và chưa nghe; `score_draft` hướng "down" mới kiểm bằng sóng giả.
