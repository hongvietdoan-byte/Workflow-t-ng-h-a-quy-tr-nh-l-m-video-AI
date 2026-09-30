# Kế hoạch sửa sau dự án #8 (2026-09-28) — NGUỒN DUY NHẤT VỀ TIẾN ĐỘ ĐỢT NÀY

> Người dùng duyệt 2026-09-28. Phân tích gốc: `docs/TONG_KET_DU_AN_8_2026-09-28.md`.
> Trần đợt: 50 USD · Claude 3 USD · từ 2026-09-28T08:00:00+00:00 · **30/09 người dùng duyệt thêm: 15 USD cho các bài thử (hỏi từng bài) + 25 USD cho K.2**
> Xem tiến độ: web **AI Development System** (`Start-DevSystem.bat`, cổng 8502) → trang **📋 Kế hoạch đang chạy**, hoặc `py tools/plan_progress.py`.
> **% do code tính** từ danh sách việc dưới đây (✅ tính đủ, 🔄 tính nửa, ✖ không tính; trọng số nặng:1/2/3). Xong một việc → đổi trạng thái
> trong cùng commit với code, ghi mã commit + bằng chứng, rồi `py tools/plan_progress.py --write`.
> Trạng thái: ⬜ chưa làm · 🔄 đang làm · ⏸ chờ người dùng · ✅ xong · ✖ bỏ (kèm lý do).

**Luật chung mọi đợt:** test qua hết → commit + push `main` → `git pull` ở `D:\AI-Video-Pipeline` → cập nhật `TODO.md` → báo kết quả (kèm dòng
"Tiến độ: tổng X % · đợt hiện tại Y % · việc kế: …") và **dừng chờ người dùng** trước đợt kế · không sửa code khi đang có lượt chạy trả tiền ·
"xong" phải có bằng chứng chạy thật · Claude Code tự xem + nghe bản dựng trước khi báo xong đợt có video/âm thanh.

## Tiến độ
<!-- tien-do -->
| Đợt | Việc | Xong | Đang làm | Chờ người dùng | Bỏ | Tiến độ |
|---|---|---|---|---|---|---|
| P0 Theo dõi tiến độ | 2 | 2 | 0 | 0 | 0 | 100 % |
| S1 Dựng & âm thanh | 15 | 13 | 0 | 0 | 1 | 96 % |
| S0 Học từ phim drama tham khảo | 15 | 15 | 0 | 0 | 0 | 100 % |
| S9 Dashboard gọn, dễ nhìn | 6 | 6 | 0 | 0 | 0 | 100 % |
| S2 Timeline theo âm thanh + animatic | 6 | 5 | 0 | 0 | 0 | 81,8 % |
| S3 Director kể chuyện + Quay phim | 8 | 7 | 0 | 0 | 1 | 100 % |
| S4 Video chất lượng | 12 | 6 | 2 | 0 | 0 | 55 % |
| S5 Bối cảnh theo file 3D Tháp Đồng Hồ | 7 | 6 | 1 | 0 | 0 | 95 % |
| S6 Ước tính, ngân sách, dashboard | 6 | 5 | 0 | 0 | 1 | 100 % |
| S7 Agent QC | 2 | 1 | 0 | 0 | 0 | 66,7 % |
| S10 Kỹ năng nhân vật & tham chiếu | 12 | 12 | 0 | 0 | 0 | 100 % |
| K Chạy kiểm kịch bản hài 20–30 s — ⏸ KHÔNG ƯU TIÊN (người dùng 30/09: các việc test kịch bản không làm trước nữa) | 3 | 0 | 0 | 3 | 0 | 0 % |
| S8 Chấm lại bằng AI Development System (cuối cùng) | 5 | 2 | 0 | 0 | 0 | 42,9 % |
| **Tổng** | **99** | **80** | **3** | **3** | **3** | **86,4 %** |

Đợt hiện tại: **S1** · việc kế: **S1.15** Tùy chọn model nhạc Eleven Music v2.5 (cập nhật ClipAI)
<!-- /tien-do -->

## Danh sách việc (thứ tự người dùng đã duyệt)

### P0 — Theo dõi tiến độ
- [x] P0.1 · File kế hoạch trong repo + bộ đọc % (`devsys/plan_progress.py`, `tools/plan_progress.py`) · nặng:1 · ✅ · file này + tools/plan_progress.py, test PlanProgressTests (1305 test qua)
- [x] P0.2 · Trang "📋 Kế hoạch đang chạy" trong AI Development System + test · nặng:2 · ✅ · trang đầu của devsys; AppTest mọi trang qua

### S1 — Dựng & âm thanh
- [x] S1.1 · Bỏ hẳn bảng tên nhân vật; HUD không vào .srt; ghi luật dùng lại sau này · nặng:1 · ✅ · 5a5e381 · dựng lại #8: .srt không còn KELLY/KENTA/MAXIM
- [x] S1.2 · Hiệu ứng âm thanh neo theo shot, tính lại giây mỗi lần dựng · nặng:2 · ✅ · 5a5e381 · dựng lại #8: súng/va chạm/bíp ở 62,9–63,2 s = shot 26 (bản cũ 43,3 s)
- [x] S1.3 · Ý đồ nhạc tự sửa (cut lặp) + chặn nhạc lặng > 8 s · nặng:2 · ✅ · 5a5e381 · dựng lại #8: nhạc tắt tối đa 8 s (36,9–44,9 · 53,7–61,7 · 66,1–67,9), bản cũ 31 s
- [x] S1.4 · Nhạc khớp độ dài phim thật · nặng:2 · ✅ · 5a5e381 · dựng lại #8: nhạc 67,8 s lặp có crossfade, còn −22 dB ở 80–83 s (bản cũ lặng); tìm thêm lỗi bộ hạ nhạc dừng theo câu cuối → đã sửa
- [x] S1.5 · Phụ đề không đè mặt (chỉ lên trên khi dải trên trống) · nặng:2 · ✅ · 5a5e381 · dựng lại #8: câu 41,4 s nằm dưới, không đè mặt (ảnh docs/video_check_2026-09-28/v2_s1_kiem_tra.jpg)
- [x] S1.6 · Limiter −1 dBTP + mã hóa âm một lần · nặng:2 · ✅ · 5a5e381 · dựng lại #8: đỉnh −1,9 dBTP, −14,6 LUFS; AAC một lần
- [x] S1.7 · Ngữ pháp hồi tưởng ở khâu Dựng (cờ flashback_fx) · nặng:2 · ✅ · 5a5e381 · dựng lại #8: shot 28 có flash trắng + màu ký ức (ảnh v2_s1_kiem_tra.jpg)
- [x] S1.8 · Shot kết giữ hình ≥ 2,5 s · nặng:1 · ✅ · 5a5e381 · dựng lại #8: shot 33 giữ 2,5 s
- [x] S1.9 · QC bản dựng cuối bằng máy (core/final_qc.py) · nặng:3 · ✅ · 5a5e381 · bản cũ: 9 lỗi chặn; bản dựng lại: 1 lỗi chặn (độ dài +33 % → S2) + 4 cần xem
- [x] S1.10 · Dựng lại #8 từ clip sẵn có (v2) · nặng:1 · ✅ · df6d2c7 · v2 ở D:/AI-Video-Output/2026-09-28_du-an-8/v2; người dùng xem, góp ý 2 điểm → S1.11, S1.12
- [x] S1.11 · Phụ đề theo vùng an toàn TikTok (góp ý người dùng về v2) · nặng:2 · ✅ · a4858b9 · mặc định TikTok: trên 8 %, dưới 27 %, hai bên 13,5 %; bỏ vị trí "thấp"; ảnh docs/video_check_2026-09-28/v3_phu_de_vung_tiktok.jpg
- [x] S1.12 · Nhạc mềm + đi theo cảnh (góp ý người dùng về v2) · nặng:3 · ✅ · 82ce1b2 · dốc tắt/vào, lặng dài thì nhạc trở lại nhỏ; cờ music_fit dời từng đoạn nhạc về đầu cảnh thật (10,1 · 24,3 · 45,7 · 62,9 · 72,0 s); v3 đo liền mạch
- [x] S1.13 · Người dùng xem/nghe bản v3 · nặng:1 · ✅ · người dùng: "ok rồi" (2026-09-28)
- [ ] S1.14 · Soạn nhạc mới theo nhịp truyện cho #8 (người dùng cho phép, sáng tạo theo diễn biến) · nặng:2 · ✖ · người dùng 30/09: bỏ, không làm tiếp (bản v4 giữ ở D:/AI-Video-Output/2026-09-28_du-an-8/v4_nhac_moi)
- [x] S1.15 · Tùy chọn model nhạc Eleven Music v2.5 (cập nhật ClipAI) · nặng:1 · ✅ · 01/10 nhánh C: `music_v2_5` có trong API; 1 bài (≈ 0,22 USD) cùng brief #8 — to hơn 3,8 LU, gần như phẳng (LRA 6,5 vs 16,4), bám mốc brief kém hơn music_v2 → giữ mặc định music_v2 (adapter nhận model=, tên lạ bị từ chối trước khi trả tiền); người dùng có thể nghe D:/AI-Video-Output/2026-10-01_s2-6_s1-15/music_30779.mp3 để xác nhận · trước đó: người dùng 30/09 duyệt làm (tốn tiền: ước tính + trần riêng trước khi gửi) · chờ người dùng duyệt đề xuất docs/CAP_NHAT_CLIPAI_2026-09-28.md

### S0 — Học từ phim drama tham khảo
- [x] S0.1 · Chọn 5 đoạn mẫu trong phim đã gửi + phong cách DRAMA_DOC · nặng:1 · ✅ · DRAMA_DOC trong core/reference_analysis.py; 1 phim (Q0); đoạn 1 = 0:00–3:00, đoạn 2 = thoại trong 20–30 phút (agent chọn)
- [x] S0.2 · Máy đo trong trình duyệt cho 5 đoạn (agent) · nặng:2 · ✅ · 5 đoạn đo trong trình duyệt (397 shot, 720 s); âm thanh không đo được (YouTube chặn)
- [x] S0.3 · Gắn nhãn tờ ảnh + thống kê (agent) · nặng:2 · ✅ · nhãn 397 shot; soát 10 nhãn lượt 1: 7 đúng → agent sửa 13 nhãn lệch 1 vị trí (lỗi chép tay); lượt 2 bị quảng cáo cản, agent tự xác nhận theo phụ đề
- [x] S0.4 · Xem – nghe trọn đoạn, phiếu 10 mặt (agent) · nặng:2 · ✅ · phiếu 10 mặt + dấu hiệu hồi tưởng + bảng tên + cỡ cảnh theo loại đoạn: research/ff_styles/DRAMA_DOC/PHIEU_bzsP_ArSIUA.md
- [x] S0.5 · Báo cáo nghiên cứu + so với #8 + luật · nặng:2 · ✅ · người dùng: gợi ý tham khảo, không luật bắt buộc; dùng hỗn hợp nhiều phong cách (2026-09-28)
- [x] S0.6 · Luật được duyệt vào bộ kỹ năng · nặng:1 · ✅ · knowledge/ff_styles/DRAMA_DOC.md ghi rõ GỢI Ý; dự án chọn NHIỀU phong cách tham khảo; Director đọc dạng gợi ý được trộn / làm khác
- [x] S0.7 · Chỉ số mục tiêu data/drama_targets.json + test · nặng:2 · ✅ · data/style_hints.json: số đo chỉ hiện 💡 ở Kiểm bản dựng khi dự án chọn phong cách đó, không chặn, không tính 'cần xem'
- [x] S0.8 · Phiếu so sánh bản dựng vs phim tham khảo · nặng:1 · ✅ · phiếu 10 mặt trong báo cáo S0.5 mục 4; đã chấm #8 cũ và v4
- [x] S0.9 · Tư liệu kỹ thuật từ clip mẫu ClipAI (`MV_NARRATIVE`, Đ12 / Q12 / E12) — sửa 2026-09-29 theo góp ý người dùng: tư liệu + ý đồ ở đúng chỗ, không công thức · nặng:1 · ✅ · docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md mục 6
- [x] S0.10 · Phương pháp phân tích chính xác: quan sát (mốc giây) → ý đồ trong ngữ cảnh (giả thuyết + độ tin) → đối chiếu nhiều mẫu + tài liệu → mới thành kiến thức; kiểm mâu thuẫn với kiến thức sẵn có · nặng:1 · ✅ · knowledge/craft/PHUONG_PHAP_PHAN_TICH.md (duyệt 2026-09-29; thứ tự học: phim ngắn → short drama → hành động → MV → CGI kỹ xảo)
- [x] S0.11 · Kho kỹ thuật chuyên môn `knowledge/craft/` (máy quay, góc, chuyển động máy, chuyển cảnh, dựng, âm thanh): mỗi kỹ thuật = cách làm + nhiều ý đồ có thể phục vụ + điều kiện + ví dụ ≥ 2 mẫu + nguồn tài liệu (tóm lời mình) · nặng:3 · ✅ · lượt 1: research/craft/NGUON.md + draft 5 nhóm; lượt 2 (2026-09-29, nhánh C2): knowledge/craft/README.md + 6 nhóm, 53 kỹ thuật có ví dụ mốc giây từ 21 mẫu S0.12 + clip mẫu ClipAI, đọc trọn 4 bài gốc (Holben ASC, Randy Thom, Evan Schiff, Murch); mục chưa có mẫu ghi "giả thuyết"; E4 (cắt theo phách) đã sửa (TODO 29/09 (17)); ví dụ 20–28 đã thêm (TODO 29/09 (22f))
- [x] S0.12 · Xem nhiều mẫu đa thể loại (drama dọc, MV, quảng cáo game, phim ngắn, hoạt hình FF…) gắn nhãn theo kho kỹ thuật S0.11 · nặng:3 · ✅ · 2026-09-29 tối: đủ **27 video** (01–28, bỏ 1 video không tải được), số đo ở research/craft/s0_12/so_do/, 19 mẫu hình ở TONG_HOP.md; bàn giao đã xong (TODO 29/09 (20)). Việc nghe tai các mốc (người dùng) + đo khớp môi 24 + đo 28 đoạn 3:00–8:00 là việc phụ ở TONG_HOP "Tồn đọng" — không chặn
- [x] S0.13 · Rà kiến thức đang dùng (director / dp / editing / ff_styles) tìm chỗ gán nghĩa cố định hoặc khái quát từ 1 mẫu → sửa thành tư liệu có điều kiện · nặng:1 · ✅ · agent rà 16 chỗ (cinematography_basics 3, dp.md Q2/Q3/Q5/Q8 4, director.md Đ4/N5 2, film_director_method 3, video_motion_vocab 1, genre_guides 3) → đã sửa hết; 1340 test qua
- [x] S0.14 · Nghiên cứu nguồn tiếng Trung về phim AI (AI短剧 9:16, workflow, nội dung, prompt ngắn đủ ý, cảnh xịn; Seedance/即梦/可灵 tài liệu chính thức, WaytoAGI, bài ngành) → research/craft/trung_quoc/ · nặng:3 · ✅ · lượt 1: 18 nguồn (Seedance 2.5 提示词指南 đọc trọn…), quy trình 9 bước, 15 bài học; lượt 2 (2026-09-29): +12 nguồn (#19–30) — Kling 3.0 hướng dẫn chính thức (Multi-Shot, Element Binding, thoại 5 ngôn ngữ, không tiếng Việt), đạo diễn 陈坤 《山海奇镜》, 抽卡师 潮新闻 (2–3 lần gen thường, 10+ cảnh khó, nhóm 15 s), WaytoAGI, luật 微短剧 9/2026; 6 gợi ý kiểm được T1–T6 (research/craft/trung_quoc/LUOT_2.md) — chờ người dùng xem; thiếu: biên kịch có tên thật · 30/09: xong T1–T6 (T1–T3 gộp 29/09; T3 A/B bỏ — người dùng 30/09, phần chính đã có ở seedance_ref_groups / dialogue_take; T4 cờ `hero_takes` core/hero_takes.py + 7 test; T5 ở S10.11; T6 cờ `ai_label`)
- [x] S0.15 · Nghề nhạc phim: spotting, nhạc dẫn cảm xúc / dẫn dắt / tạo nhịp, khác nhau theo thể loại (short drama dọc, phim ngắn, hành động, hài, MV, CGI…), cách brief nhạc → prompt model nhạc; đối chiếu music_timing / sound_intent hiện có · nặng:2 · ✅ · lượt 1: 15 kỹ thuật, 8 thể loại, 10 bài học, nguồn #31–50; lượt 2 (2026-09-29): khung spotting người làm nghề (#51–52) + số đo 14 video S0.12, đọc từng dòng music_timing / music / music_fit / 04_music_brief → 7 chỗ gán nghĩa cố định từ #8 (C1 "love motif" + "Free Fire short drama" cứng, không đọc genre; C3 score_draft chỉ thưởng tăng độ to…), 8 gợi ý kiểm được M1–M8 (research/craft/draft/nhac_luot2_doi_chieu.md) — người dùng duyệt làm hết 29/09 → **M1–M8 đã làm** (nhánh B7b): `core/music_intent.py` đọc giọng điệu / motif / kiểu kết của dự án (hài ≠ chính kịch ≠ hành động ≠ MV), trần BPM theo giọng điệu, `score_draft` chấm theo hướng (lên/xuống), `sound` thêm music_fn/enter/bed (thưa nhạc), prompt 04 có điều kiện + cues, phiếu SPOTTING.md; dựng lại brief #8 (giữ nguyên), #3 hài (short comedy 124 BPM, không love motif), #10 (không mood → trung tính + ghi chú) — nhac_luot2_doi_chieu.md mục 8; chưa tạo/nghe nhạc thật; thiếu: composer vertical drama có tên

### S9 — Dashboard gọn, dễ nhìn
- [x] S9.1 · Nút thu gọn phần Kịch bản · nặng:1 · ✅ · xong: 1a Kịch bản thu thành 1 dòng tóm tắt + nút ▸ Mở / ▾ Thu gọn (test_dashboard)
- [x] S9.2 · Thành phần chung ui.fold · nặng:1 · ✅ · xong: ui.fold (dashboard/ui.py)
- [x] S9.3 · Kiểm kê khung → 3 tầng hiển thị (người dùng duyệt) · nặng:2 · ✅ · người dùng duyệt hết bảng E (2026-09-28)
- [x] S9.4 · Áp kiểm kê cho 5 bước + thanh đầu, dải "Việc tiếp theo" · nặng:3 · ✅ · 1c3ce9d · dải Việc tiếp theo 5 bước + các khung theo bảng; đo #8: Bước 1 mặc định 3.347 px so với 11.924 px mở hết (−72 %, mục tiêu −40 %)
- [x] S9.5 · Tách step1.py thành phần nhỏ · nặng:2 · ✅ · step1.py 1.397 dòng → step1 / _run / _prep / _characters / _director (≤ 378 dòng mỗi file); 1337 test qua
- [x] S9.6 · Gộp timeline tổng + sửa giao diện S6.4 · nặng:2 · ✅ · 2026-09-29: màn 🗺 Timeline tổng ở Bước 5 (core/timeline_view.py: shot · thoại · nhạc bật/tắt · hiệu ứng · phụ đề, thu gọn mặc định; #8: 83 s, 33 shot, 23 câu, 4 hiệu ứng, nhạc tắt 3 đoạn) + S6.4 xong

### S2 — Timeline theo âm thanh + animatic
- [x] S2.1 · Chọn giọng ở Bước 1 · nặng:1 · ✅ · 2026-09-29: chạy tự động chọn giọng (Claude cast_voices) ngay sau Director; thiếu giọng → dừng hỏi trước khi làm ảnh (cờ audio_first)
- [x] S2.2 · TTS nháp sau Director → chỉnh thời lượng → khóa timeline · nặng:3 · ✅ · 2026-09-29: core/audio_first.py + pha voicefirst (cờ audio_first, tắt mặc định); test; chưa chạy thật (TTS tốn tiền — lần chạy kiểm K)
- [x] S2.3 · Cổng độ dài ±10 % · nặng:1 · ✅ · 2026-09-29: audio_first.length_check / gate_message, cổng 'length' (Tiếp tục = chấp nhận); test
- [x] S2.4 · Animatic ở cổng storyboard · nặng:3 · ✅ · 2026-09-29: core/animatic.py + nút Bước 2 (khung Storyboard); chạy thật trên #8: 33 shot, 63,7 s, 23 câu thoại, nhạc, phụ đề, ~40 s, 0 USD (data/projects/8/output/ANIMATIC_sub.mp4)
- [x] S2.5 · Clip đơn cắt theo chuyển động · nặng:1 · ✅ · 2026-09-29: clip Seedance đơn lẻ cắt ở đoạn động nhất, không dưới mức sàn hành động (cờ motion_trim); test
- [ ] S2.6 · Thử Seed Audio 1.0 làm track thoại cả cảnh (3 giọng mẫu, mốc 100 ms, mốc phụ đề) · nặng:2 · ✖ · người dùng 01/10: bỏ (Seed Audio lỗi 400 qua API; giữ TTS từng câu); 01/10 nhánh C: API có (`/api/sound/generate` provider seedance, model seed-audio-1.0) nhưng nhà cung cấp trả 400 hai lần (đổi đầu vào lần 2) → dừng; CHỜ NGƯỜI DÙNG tạo 1 lần trên web (Audio → All-in-one Voice, 3 file mẫu, bật Subtitles) để đối chiếu yêu cầu thành công rồi chạy lại (còn 1 lượt); docs/KET_QUA_S2_6_S1_15_2026-10-01.md · trước đó: người dùng 30/09 duyệt làm (tốn tiền: ước tính + trần riêng trước khi gửi) · chờ người dùng duyệt (cập nhật ClipAI)

### S3 — Director kể chuyện + Quay phim
- [x] S3.1 · Bảng nhịp truyện bắt buộc · nặng:2 · ✅ · 2026-09-29 (điều chỉnh theo góp ý 'không khuôn cố định'): beat.cause — cú xoay nêu nguyên nhân và chỗ người xem thấy (hoặc 'giấu tới …'); thiếu → 💡 ở Bước 1 (director_report.turns_without_cause); prompt 01/19 + director.md; test
- [x] S3.2 · Agent "người xem lần đầu" · nặng:2 · ✅ · 2026-09-29: core/story_check.py + prompt 22 (chỉ đọc cái hiện trên màn hình), pha storycheck (cờ story_check), hiện ở Bước 1; mock + 3 test; chưa chạy Claude thật
- [x] S3.3 · action_peak → storyboard vẽ tư thế hành động · nặng:1 · ✅ · 2026-09-29: trường action_peak (prompt 17/20) → câu 'đang giữa động tác' trong prompt ảnh khung đầu; test
- [x] S3.4 · Đoạn diễn liên tục theo góc máy, cắt xen · nặng:3 · ✅ · 2026-09-29: mỗi vị trí máy quay trọn đoạn diễn (từ shot đầu tới shot cuối của góc đó), mỗi shot cắt đúng chỗ trong đoạn (cờ continuous_takes + camera_setups); 3 test; chưa chạy thật (tốn giây video hơn — cần A/B)
- [x] S3.5 · Cổng Quay phim (cỡ cảnh, chuyển động máy) · nặng:2 · ✅ · 2026-09-29, điều chỉnh theo nghiên cứu (drama máy tĩnh 98 %, cận liền nhau): không ép ≤ 2 cùng cỡ / mỗi cảnh phải chuyển động; 💡 khi máy chuyển động mà thiếu why; chuyển động máy đã vào prompt video
- [x] S3.6 · transition_in từng shot + khâu Dựng thực hiện · nặng:2 · ✅ · 2026-09-29: flash / dip / whip / zoom_through vẽ trong 2 clip kề (độ dài không đổi), cut / match / occlusion / J / L giữ cắt thẳng (cờ shot_transitions); sửa lỗi cũ _flashbacks tìm clip theo đường dẫn gốc; 4 test
- [ ] S3.7 · hook_mid / money_shot / ý đồ nhạc: vi phạm → Director sửa · nặng:1 · ✖ · 2026-09-29: bỏ theo nguyên tắc 'gợi ý, không ép' — móc / money shot là gợi ý (💡 ở Bước 1), nhạc tắt quên vào lại đã tự sửa bằng code (S1.3); bắt Director làm lại tốn lượt Claude
- [x] S3.8 · Đổi bối cảnh → chạy lại Director; dự án mới kế thừa cách làm · nặng:2 · ✅ · 2026-09-29: dấu vân tay bối cảnh lúc Director chia shot (places_at_plan) → Bước 1 báo cảnh dùng bản cũ + nút chia shot lại; dự án mới kế thừa shot_mode / look / phong cách / model ảnh / cài đặt dựng; 3 test

### S4 — Video chất lượng
- [x] S4.1 · Shot cận có mặt → khung đầu thay vì ref-only · nặng:2 · ✅ · 2026-09-29: cờ mới `closeup_start_frame` (TẮT, chờ A/B S4.6): ECU/CU/MCU có nhân vật ra khỏi nhóm tham chiếu, đi Kling từ ảnh storyboard đã duyệt; test
- [x] S4.2 · Khớp môi mọi shot người nói thấy mặt (theo A/B) · nặng:2 · ✅ · người dùng 01/10 xem clip khớp môi (c): OK — chốt cách (c), `dialogue_take` giữ BẬT; 01/10 nhánh A1 (#14, 1,38 USD, Seedance 2.5, luồng chính trọn: take audio → group_block → cắt dò điểm 2,875 s → shift −0,125 → place_on_timeline): miệng mở đúng lượt, ngậm khi ngắt; tương quan miệng–giọng 0,42–0,53 (cách (a) #8: 0,025) nhưng < ngưỡng 0,65 → CHỜ NGƯỜI DÙNG xem/nghe D:/AI-Video-Output/2026-10-01_s4-2_s4-6/*_co-giong.mp4 để chốt; sửa 3 lỗi (thử rẻ hạ take xuống Fast; closeup_start_frame kéo cận đang nói sang Kling; clean_edges không cập nhật shift — chưa có bằng chứng chạy thật); docs/KET_QUA_S4_2_S4_6_2026-10-01.md · trước đó: 2026-09-29: người dùng chọn (c) in-game. Code xong: cờ `dialogue_take` (BẬT ở dashboard.env, chưa kiểm luồng chính) — shot thoại thấy mặt (cả MS / nhiều người, trước "skip") = "take": vào clip nhóm Seedance 2.5, MỘT track giọng cả nhóm (runner._take_audio), câu thoại + người nói + mốc giây trong prompt (dialogue_take.group_block), sau cắt ghi `shift` (chỗ cắt thật − dự kiến) để voice.place_on_timeline đặt giọng đúng miệng; 5 test. Còn: chạy thật 1 cảnh thoại qua dashboard
- [x] S4.3 · Câu khóa phong cách "không anime" · nặng:1 · ✅ · 2026-09-29: looks.video_sentence — mọi prompt video của dự án in-game mở đầu bằng "Style lock: Garena Free Fire in-game 3D character render… not anime, not 2D, not cel-shaded, not live action" (không chứa chữ bị gỡ); test
- [x] S4.4 · Mẫu motion prompt theo loại hành động · nặng:1 · ✅ · 2026-09-29: core/motion_physics.py — 10 loại hành động (đánh, ngã, nhảy, múa, chạy, ném, ngồi/đứng, đi, quay người, cầm nắm) → MỘT câu vật lý (trọng tâm, chỗ chạm, phần chuyển động trễ); vào prompt shot tham chiếu + `physics_hint` cho Claude viết motion; test
- [x] S4.5 · QC clip so storyboard + luồng quang + khớp môi · nặng:3 · ✅ · 2026-09-29: core/clip_measure.py hiệu chỉnh trên 33 clip #8: `look_drift` (độ chi tiết mặt so ảnh storyboard: clip 01 anime 0,30 vs 11 clip đúng 0,49–0,87 → ngưỡng 0,40), `cut_inside` / `jerk` (luồng quang + tương quan màu) tìm đúng 4/33 clip lẫn khung shot kề (01, 03, 11, 24 — kiểm bằng mắt, 0 báo nhầm) → **sửa gốc**: shots.clean_edges bỏ khung lẫn ở mép khi cắt clip nhóm; số đo vào prompt QC clip. **Khớp môi (29/09 tối)**: `clip_measure.lip_sync` — mốc môi MediaPipe Face Landmarker (wheel `mediapipe` 1.0.1 chạy Python 3.14 + mô hình `data/models/face_landmarker.task` 3,6 MB) trên từng mặt YuNet cắt + phóng to, độ mở môi trong / chiều cao mặt tương quan với giọng trong từng câu thoại: #10 lượt thoại (c) Maxim + Kenta khớp 0,72–0,96, cùng giọng dời giờ ≤ 0,58, 4 shot #8 (miệng lệch giọng ~1 s) 0,04–0,18 → cờ `lips_off_voice` (< 0,65); đo **đúng thời điểm**, chưa chứng minh âm tiết (giọng khác đặt đúng giờ tới 0,87); lượt Kelly 0,30 / 0,12 bị cờ (môi hé suốt lúc người khác nói / đứng dậy mất mặt); `tools/lip_sync_calibrate.py`; chưa chạy trong lượt QC video thật (tốn lượt Claude)
- [x] S4.6 · A/B trả tiền: cận · hành động 3 model · khớp môi (a)/(b) · nặng:2 · ✅ · 01/10 nhánh A1: A/B cận xong (1,44 USD, 2 shot CU Kelly × 2 cách) — chỉ ảnh tham chiếu giữ mặt tốt hơn (0,905/0,712 vs Kling khung đầu 0,756/0,685; shot đêm Kling trôi mặt), không ra anime cả hai → giữ `closeup_start_frame` TẮT (bằng chứng 2 shot, chưa phải luật) · trước đó: 2026-09-29: **phần hành động xong** (#10, 9 clip, 5,42 USD; `docs/AB_HANH_DONG_S4_6_2026-09-29.md`): chạy lớn → Kling khung đầu tốt + rẻ nhất; kỹ năng Kenta không model nào tạo; Seedance Fast vẽ dấu đỏ đánh dấu lên mặt Kelly. **Vòng 2** (3,46 USD): Fast cần dấu trên mặt mới qua bộ lọc (băng chữ / dấu góc bị từ chối); hiệu ứng kỹ năng vẽ sẵn vào khung đầu + cuối → Kling giữ được (vòng gió, vệt chém); khớp môi (c) một clip cả đoạn thoại cho đúng người nói đúng lượt (in-game giữ bố cục tốt hơn tả thực). Người dùng đã chọn (c) (bàn giao 29/09 chiều); (b) sync.so bỏ (người dùng 26/09). Còn: A/B cận (ref-only vs khung đầu, quyết cờ `closeup_start_frame`). 30/09: A/B kỹ năng bằng video tham chiếu chuyển sang đợt S10. 30/09 (nhánh C3): mục "Kết luận S4.6" trong tài liệu A/B; **sửa gốc khung đầu thừa nhân vật** — storyboard chỉ gửi ảnh người có trong shot (`shared_references(cast_of=)`), khung 1 chỉ lấy bối cảnh (`anchor_note`); dựng lại yêu cầu 3 shot #10 trước/sau, 6 test; ảnh thật chờ lượt vẽ kế
- [x] S4.7 · Kho chủ thể cho mọi ảnh nhân vật gửi Seedance, bỏ mẹo dấu đỏ trên mắt · nặng:2 · ✅ · người dùng 01/10 xem 3 clip kho chủ thể: OK; 01/10 nhánh A2 (#15): kho chủ thể dùng được — 2/2 ảnh FF in-game active, 3/3 lần gửi qua bộ lọc người thật KHÔNG cần dấu đỏ, giữ mặt tốt; cờ mới `seedance_subjects` (TẮT; nhớ subject theo sha256, tất cả-hoặc-không, sửa list_assets đọc mọi trang); còn: thử 1 nhóm 3 người (≈ 1 USD) rồi quyết bật; docs/KET_QUA_S4_7_S4_10_2026-10-01.md · trước đó: người dùng 30/09 duyệt làm (tốn tiền: ước tính + trần riêng trước khi gửi) · chờ người dùng duyệt (tài liệu ClipAI chính thức)
- [x] S4.8 · Prompt Seedance 2.0/Fast theo 'Shot 1 / Shot 2' thay vì mốc giây · nặng:1 · ✅ · 2026-09-29: seedance_refs.prompt(model=) — 2.0/Fast chỉ số shot, 2.5 giây nguyên liên tục; test
- [x] S4.9 · Prompt theo tài liệu chính thức (vai trò ảnh theo thứ tự xuất hiện, hành động khái quát, biểu cảm dịu + chặn mắt phát sáng, ảnh tham chiếu ≤ 1280 px) · nặng:1 · ✅ · 2026-09-29: seedance_refs (soften, busy_shots ⚠, REF_MAX_SIDE), knowledge/seedance_prompting.md; 1345 test qua; chưa chạy thật (cần lần sinh video kế)
- [x] S4.10 · A/B Seedance 2.5 (720P) vs Fast: cận, chạy, thoại có tham chiếu âm thanh tiếng Việt · nặng:2 · ✅ · 01/10 nhánh A2 (3 clip 4 s, 2,32 USD gồm S4.7): Fast KHÔNG dùng cho shot thoại thấy mặt (miệng mấp máy cả lúc im); 2.5 + âm thanh tham chiếu một mình trễ 1,33 s; 2.5 + mốc giây (khối S4.2) 0,39, trễ 0,62 s, ngậm khi hết câu — chưa đạt 0,65; hướng tiếp: mốc 0,1 s / dời giọng theo miệng đo được ở khâu dựng (miễn phí) · trước đó: người dùng 30/09 duyệt làm (tốn tiền: ước tính + trần riêng trước khi gửi) · chờ người dùng duyệt (~3–4 USD)
- [ ] S4.11 · Chế độ bản mẫu (Sample Mode): xác minh API, bản mẫu → duyệt → bản cuối 1080P · nặng:2 · ✖ · người dùng 01/10: bỏ (bản cuối 1080p không chạy; bản mẫu qua API đã xác minh — cờ `seedance_sample_mode` giữ TẮT); 01/10 nhánh B (#16): API CÓ — bản mẫu `draft: true` 480p (0,42 USD, cận Kelly đạt, giữ render 3D) và bản cuối `draft_task` 1080p (xác minh 0 USD bằng mã giả); bản cuối chưa chạy (≈ 2,08 USD > trần nhánh) → CHỜ NGƯỜI DÙNG duyệt ≈ 2,1 USD (bản mẫu hết hạn ~07/10); mẫu+cuối 4 s ≈ 2,50 vs thẳng 720p ≈ 0,92 → chỉ lợi khi cần 1080p + thử nhiều; cờ `seedance_sample_mode` TẮT; docs/KET_QUA_S4_11_S4_12_2026-10-01.md · trước đó: người dùng 30/09 duyệt làm (tốn tiền: ước tính + trần riêng trước khi gửi) · PDF đã có: mẫu chỉ 480p (Seedance 2.5), bản cuối chỉ 1080p, mẫu hết hạn ~7 ngày; còn thử API
- [x] S4.12 · Advanced Edit: sửa clip lỗi (cận Kelly #8) thay vì sinh lại — kiểm API, thử 1 clip · nặng:1 · ✅ · 01/10 nhánh B: API CÓ (Seedance 2.5 `omni_reference_task_type: edit`), thử 1 lần 0,47 USD — clip ra mất điểm cắt, mặt gần như không đổi → KHÔNG đưa vào luồng; cờ `seedance_video_edit` TẮT; chỉ thử lại với clip nguồn 1 shot ≥ 4 s không điểm cắt · trước đó: người dùng 30/09 duyệt làm (tốn tiền: ước tính + trần riêng trước khi gửi) · chờ người dùng duyệt (docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md, ~0,5 USD)

### S5 — Bối cảnh theo file 3D Tháp Đồng Hồ
- [x] S5.1 · Render bộ ảnh chuẩn từ GLB ở tầm mắt + câu bố cục · nặng:2 · ✅ · 2026-09-29: tools/tower_pack.py — 16 ảnh tầm mắt ngày/đêm trên mặt sàn đo được, loại 2 chỗ đứng nằm dưới mái che; D:/AI-Video-Output/2026-09-29_bo-boi-canh-thap-dong-ho. 29–30/09: làm lại trên **file 3D chính thức** (ClockTower + Cổng Trời, thay bản FFXN), ánh sáng trưa nắng ấm J; Kho #263/#265 = 12 ảnh render (docs/THU_PLACE_RENDER_REFS_2026-09-30.md)
- [x] S5.2 · Chặn prompt thiếu câu bố cục · nặng:1 · ✅ · 2026-09-29: job ảnh bị giữ (miễn phí) khi cảnh ghi nơi Kho có mô tả bố cục mà dự án chưa gắn; câu bố cục không còn bị cắt ở 300 ký tự; test
- [x] S5.3 · Địa điểm đổi → khung thành "cũ" · nặng:1 · ✅ · 2026-09-29: dấu vân tay bối cảnh (mô tả + ảnh) trong mã đầu vào ảnh; ảnh làm trước 29/09 không báo nhầm; test
- [x] S5.4 · Lớp 0 đo "tầng tường" · nặng:2 · ✅ · 2026-09-29: đếm đường ngang dài ở nền (hiệu chỉnh trên dữ liệu thật: render tháp 0–3, khung nhiều tầng #8 5–10) → cờ stacked_tiers khi bối cảnh Kho tả là phẳng; test
- [x] S5.5 · 💵 Thử 1 cảnh `place_render_refs` (3–5 shot ở Tháp, render 3D đúng góc làm ảnh tham chiếu) — thay việc vẽ lại khung FFXN cũ; so độ khớp nền với mốc 0,073 · nặng:1 · ✅ · 30/09 tối vẽ lại 1/2 (tổng 0,572 USD): 5/5 khung đổi đúng loại nơi (cỏ + nhà đá mái đỏ thay quảng trường lát đá), độ khớp TB 0,202 → 0,242; bố cục nền chưa theo render (nhà nhỏ ở hậu cảnh, góc ngược shot 22 không theo) — kết luận + việc tồn (sửa cách đo, bỏ câu Setting chung khi có render) ở docs/THU_PLACE_RENDER_REFS_2026-09-30.md mục 7; trước đó: 30/09 chiều: thử trả tiền #13 (0,312 USD): ảnh toàn cảnh khớp render, 5/5 khung shot theo chữ cũ "stone plaza + tower" thay vì render → sửa `auto_spot` (cả cảnh một chỗ) + câu "render quyết định nơi chốn" (`place_refs.PRECEDENCE`); số background_match không phân biệt được (0,202 vs 0,208) — chờ người dùng cho vẽ lại 5 khung ≈ 0,26 USD (docs/THU_PLACE_RENDER_REFS_2026-09-30.md mục 7); chạy khô #8 xong 30/09 (33/33 shot có render + câu số đo); ≈ 0,5 USD, hỏi trước
- [x] S5.6 · Render tháp GLB thành video white-model làm tham chiếu cho Seedance 2.5 · nặng:1 · ✅ · 2026-09-29 (người dùng: 'tự làm kèm video'): 3 đường máy (đi bộ vào, vòng quanh, cần cẩu) × bản chất liệu + white-model; đã sửa đường đi bộ xuyên tường
- [x] S5.7 · Hướng máy + đèn đêm ở bối cảnh 3D theo kịch bản (người dùng 29/09) · nặng:2 · ✅ · 2026-09-29: core/plate_choice.py — shot ghi plate_view (nền: landmark/away/left/right/spot:/độ + lý do) + practical_lights (đêm: [] hoặc ≤ 3 đèn); chỗ đứng 'tùy kịch bản' thiếu hướng → không render, shot chờ; đèn đặt thật trong Blender, vào khóa cache + dấu vân tay ảnh + câu ánh sáng prompt; render thử 2 nền lower_yard đêm ở D:/AI-Video-Output/2026-09-29_bo-boi-canh-thap-dong-ho/theo_kich_ban; 3 hướng cố định cũ chỉ còn là tư liệu; 30/09 gắn vào luồng place_render_refs (render tham chiếu theo shot) + hướng 'scenery'; còn: chỉ chỗ đứng dưới mái che trong FBX mới rồi script-view + thử thật 1 shot · 30/09 người dùng chốt: (c) không bắt buộc chỗ đứng nào "hướng theo kịch bản"; KHÔNG căn đèn Blender — render chỉ là tham chiếu nơi chốn, ánh sáng ảnh do model vẽ theo câu ánh sáng của Director (place_refs.PRECEDENCE); render đêm chỉ cần đọc được hình khối (bản chỉ trăng FBX đạt, D:/AI-Video-Output/2026-09-30_den-dem-fbx/); kiểm ở shot đêm thật đầu tiên — chỉ xử lý render khi model bị kéo sai ánh sáng

### S6 — Ước tính, ngân sách, dashboard
- [x] S6.1 · Dự tính tổng dự án ngay khi Director trả bảng shot · nặng:2 · ✅ · 2026-09-29: Bước 1 hiện 💵 dự tính chia khâu (project_budget.propose) ngay dưới kết quả Director + dòng tóm tắt lượt chạy; nghiệm thu lệch ≤ 20 % chờ lần chạy kiểm
- [ ] S6.2 · Màn timeline tổng · nặng:2 · ✖ · gộp vào S9.6 (không sửa giao diện hai lần)
- [x] S6.3 · Hiện cờ chưa kiểm ảnh hưởng bản dựng · nặng:1 · ✅ · 2026-09-29: features.on_unverified() + khung 🧪 ở Bước 5 liệt kê cờ đang bật chưa kiểm; test
- [x] S6.4 · E-mail khỏi URL, job ảnh khi chờ cổng, trần rõ, cảnh báo khởi động lại · nặng:2 · ✅ · 2026-09-29: mã phiên `?s=` thay e-mail (Owner chỉ nhận từ máy), thanh đầu 'đã dùng / trần / còn', cảnh báo code đổi; chờ ở cổng storyboard / gen thử thì ảnh vẽ lại bạn yêu cầu tự gửi + nhận (autopilot.serve_waiting + Manager.wake, cùng trần / khóa; không tạo mới, không tự duyệt); test
- [x] S6.5 · Ghi verified cho cờ đã chứng minh · nặng:1 · ✅ · 2026-09-29 người dùng duyệt: director_two_pass (Đạo diễn duyệt 6/6), voice_direction (23 câu đúng giọng), loudness_normalize (−14 LUFS), project_budget (khóa cứng chặn đúng) — đã kiểm → mặc định bật; test end-to-end cũ đặt 2 cờ tắt, test riêng bật tường minh
- [x] S6.6 · Áp tài liệu prompt caching vào ước tính · nặng:1 · ✅ · 2026-09-29: kiểm lại tài liệu (4 breakpoint, lookback 20, Sonnet 5 tối thiểu 1024 token, ghi ×1,25/×2, đọc ×0,1, ảnh cache được); cost.cache_stats đo tỉ lệ đọc cache từng khâu từ usage thật, hiện ở bảng ngân sách; đo #8: khâu qc 0 %

### S7 — Agent QC
- [x] S7.0 · Agent QC giữ cache (không cắt ảnh giữa hội thoại) · nặng:2 · ✅ · 2026-09-29: bỏ cắt ảnh cũ (prune); hội thoại chỉ dài thêm, quá 16 ảnh thì mở phiên mới từ brief (vẫn đọc cache) + bản tóm ghi chú / kết luận + kết quả công cụ vừa gọi; test. Sổ chi thật trước khi sửa: qc_agent đọc cache 46,9 %, qc 0 %, video 17,7 %; Director hai lượt chưa có dòng usage trong sổ để kiểm → đo ở lần chạy K; mục tiêu ≥ 70 % đo ở S7.1 (tốn tiền)
- [ ] S7.1 · Nghiệm thu lại agent QC · nặng:1 · 🔄 · 01/10 (người dùng đã gia hạn khóa API): chạy cảnh 1 #8 (0,13 USD, 6 lượt, 1,3 phút, 0,033 USD/khung) — 1 nhỏ đúng (cỡ cảnh MCU/CU), K4 đạt đúng, **K2/K3 chặn NHẦM** (nhãn đạt): agent cho rằng tay gần máy ở góc qua vai sau lưng Kenta bị lật trái–phải, nhưng xem ảnh: vai huy hiệu sao + găng giáp nằm phía TRÁI khung so với thân Kenta = tay trái đúng khi nhìn từ sau → lỗi suy luận trái–phải của agent (báo nhầm 2/4 = 50 % > chuẩn 10 %). Cảnh 2 (có 2 khung chặn) CHƯA chạy: trần cả lần 0,45 chặn (0,13 + trần cảnh 2 0,34) — cần duyệt thêm ≈ 0,34 USD. Log D:/AI-Video-Output/s7_1_qc_eval_2026-10-01.log, ảnh D:/AI-Video-Output/s7_1_canh1_k2_k3_kenta.jpg

### S10 — Kỹ năng nhân vật & tham chiếu
- [x] S10.0 · Hồ sơ kỹ năng Kenta + cờ `skill_dossier` + nghiên cứu cách gửi ảnh / video tham chiếu + thử #11 (T1–T3) · nặng:3 · ✅ · 2026-09-30: data/skills/KENTA (20 khung 30 khung/giây, storyboard, skill.json, video_ref); core/skill_dossier.py; docs/NGHIEN_CUU_PROMPT_THAM_CHIEU_2026-09-30.md (tài liệu chính thức Kling / Seedance 2.5); knowledge/reference_assets_prompting.md (Director / DP / motion đọc); adapter Kling ảnh tham chiếu không type + 3 luật video; T1 Seedance 2.5 + video kỹ năng = hiệu ứng gần game nhất (dự án thử #11, 5,91 USD)
- [x] S10.1 · Công cụ dựng hồ sơ kỹ năng `tools/skill_dossier_build.py` (video chính thức → khung dày, cắt cận, storyboard, video_ref đúng luật, nháp skill.json; tách HUD) · nặng:2 · ✅ · 30/09: lệnh sparse / dense / build, thông số ghi ở skill.json `build`; cắt video tham chiếu tự đạt ≥ 3 s, rộng ≥ 700, ≥ 407 696 điểm ảnh, SAR 1:1; test
- [x] S10.2 · Hồ sơ kỹ năng Orion — người dùng duyệt · nặng:2 · ✅ · 30/09: data/skills/ORION theo mô tả chính thức trong game (Huyết Cầu Bảo Hộ: 3 s, 5 m, không tấn công, chậm 5%) + xem từng khung 16–25 s; người dùng sửa 2 điểm (dây đỏ chỉ khi có địch — gây sát thương + hút máu; bùng dây MỘT lần ngay trước khi hết) → đã áp (final_burst)
- [x] S10.3 · Bộ ảnh chuẩn Orion vào Kho #43 — người dùng duyệt · nặng:1 · ✅ · 30/09 chiều (người dùng duyệt): 2 ảnh trùng đã gỡ, ảnh chính diện #1033 (front_standard) + bảng 4 góc #1034 (design_sheet) đã vào Kho (commit 5b37801); gán nốt #106 half_body, #46 bảng thiết kế lớn = design_sheet xếp sau #1034 (bộ chuẩn gửi model = #1033 + #1034, kiểm bằng `assets.standard_set`); Kho đủ 6 ảnh nên khung kỹ năng không vào Kho — đường kỹ năng dùng tờ kỹ năng sạch của data/skills/ORION. Kho còn thiếu: ảnh sau lưng, ảnh chuẩn anime. Ghi chú cũ: Kho #43 đã đủ 6 ảnh (chưa gán vai) — gán design_sheet #46, half_body #753, close_up #756; #754 trùng hệt #106, #755 trùng hệt #753 → chờ người dùng xóa 2 ảnh trùng để thêm ảnh in-game `KHO TÀI NGUYÊN/Nhân vật/Orion/ORION_front_ingame_cat.png` (front_standard) + khung kỹ năng (related)
- [x] S10.4 · Bộ chọn model + gửi tài sản tự động: shot có kỹ năng → Seedance 2.5, khung đầu + ảnh từng người + video_ref từng kỹ năng, câu vai trò theo mẫu chính thức; adapter nhận nhiều video · nặng:3 · ✅ · 30/09: model_router (kể cả chế độ thử rẻ vẫn 2.5), VideoRunner đường kỹ năng (không gộp nhóm, báo thiếu ảnh định danh), skill_dossier.shot_skills / video_ref / reference_block; 2 kỹ năng trong 1 shot = 2 @Video theo thứ tự; tests/test_skill_route.py
- [x] S10.5 · Luật Seedance trước khi gửi (video 2–30 s, tổng ≤ 30 s, điểm ảnh, fps, ≤ 30 ảnh, ≤ 10 video) · nặng:1 · ✅ · 30/09: `clipai.reference_video_problems` theo từng nhà cung cấp (Kling: 1 video 3–15,5 s, CẢ rộng và cao 700–4553 px; Seedance: 2–30 s, tổng ≤ 30 s, 407 696–8 295 044 điểm ảnh, 2.0 ≤ 3 / 2.5 ≤ 10 video; cả hai 24–60 fps, SAR 1:1) — bắt được lỗi thật: video Orion 764×552 Kling sẽ từ chối → công cụ cắt cạnh ngắn ≥ 704 px
- [x] S10.6 · White-model thô: Blender khối trụ màu mỗi người + đường máy trên bản đồ 3D thật → video xếp chỗ đứng · nặng:2 · ✅ · 30/09: core/whitebox.py (người đặt theo mét trước / phải so với máy của một chỗ đứng trong gói 3D, `to` = di chuyển, `face` = nhìn máy / nhìn người khác; máy mặc định nhắm giữa nhóm) + render_plates khối trụ màu có mũi chỉ hướng; câu vai trò "khối đỏ = KENTA…" theo mẫu chính thức; chạy thật Tháp plaza_front 3 người: 54 s Blender, 720×1280, 3,4 s, SAR 1:1 — D:/AI-Video-Output/2026-09-30_thu-ky-nang-kenta/whitebox/; test
- [x] S10.7 · Luật Director: 2 người có kỹ năng, trường `interactions`, chia nhịp A tung → B đáp → kết quả; bảng kiểm va chạm chưa có trong hồ sơ · nặng:2 · ✅ · 30/09: knowledge/reference_assets_prompting.md mục "Hai nhân vật cùng có kỹ năng chủ động" (5 luật có lý do); director_block in thời lượng + tương tác đã thấy; shot_problems báo va chạm 2 kỹ năng chưa có trong `interactions` (chẩn đoán skill_contradiction); interactions Kenta + Orion; test
- [x] S10.8 · 💵 T4: 1 clip Kenta + Orion cùng tung kỹ năng (2 video) — hai hiệu ứng có lẫn nhau không · nặng:2 · ✅ · 30/09 dự án #12, qua pipeline thật: KHÔNG lẫn; hai kỹ năng diễn nối nhau thay vì cùng lúc; tìm + sửa 2 lỗi (tỉ lệ ảnh, truyền video 2 lần)
- [x] S10.9 · 💵 T5: 3 người, khung đầu đủ người + white-model — người thứ ba giữ chỗ và mặt · nặng:2 · ✅ · 30/09: 3/3 người giữ mặt, đồ, chỗ đứng 5 s, không thêm người lạ
- [x] S10.10 · 💵 T6: nhiều khung then chốt theo thứ tự giai đoạn · nặng:1 · ✅ · 30/09: thứ tự giai đoạn đúng (T1 đảo); lưỡi hologram biến sớm, màng lốc thoáng qua
- [x] S10.11 · Việc miễn phí tồn: Data Pack P5 (402 dừng cứng) + P3 (Structured Outputs), E1, E2, A4 / A5 / A14 / A21, S0.14 T5 · nặng:2 · ✅ · 30/09: E1 (lỗi chỉ hiện lời, mã lỗi ở chú thích) ✅, E2 (chốt 8 ảnh tham chiếu) ✅, P5 (hết tiền → khóa dịch vụ, nút mở lại) ✅; A4 `tradeoffs.kind` lạ → báo ở bàn đo + đọc theo chữ, chữ dự phòng không nhận "khung hình" / "đọc câu" ✅; A5 thiếu `money_shot` chỉ báo khi thể loại COMMERCIAL ✅; A14 cửa sổ phủ định kiểm trục dừng ở dấu phẩy / chấm ✅; A21 lý do loudnorm chuyển chế độ động đọc từ số đo lượt đầu (không đo được LRA / LRA rộng / đỉnh cao) ✅; S0.14 T5 điều kiện cân nhắc cận mặt + khớp môi trong director.md Đ3 ✅ (tests/test_ton_dong_a_r1_r4.py, 10 test); **P3 không chuyển** — đo CSDL thật: 7 lần hỏi lại / 179 lời gọi Claude, 0 lần JSON hỏng; tài liệu chính thức: Structured Outputs có `enum` nhưng không có `minimum/maximum`/`minLength` → chỉ 1/7 (sai enum `angle`) chặn được bằng schema; giữ validator + hỏi lại

### K — Chạy kiểm kịch bản hài 20–30 s — ⏸ KHÔNG ƯU TIÊN (người dùng 30/09: các việc test kịch bản không làm trước nữa)
- [ ] K.1 · Soạn kịch bản hài 20–30 s có **Kenta + Orion cùng dùng kỹ năng** (người dùng 30/09) · nặng:1 · ⏸ · viết lại bản A (docs/KICH_BAN_KIEM_K1_2026-09-29.md) theo hồ sơ kỹ năng Kenta + Orion (đợt S10) và luật chia nhịp kỹ năng; người dùng duyệt · tạm gác — không ưu tiên (người dùng 30/09); làm sau cùng khi người dùng gọi
- [ ] K.2 · Chạy trọn trên dashboard, chất lượng cao, trần duyệt một lần · nặng:3 · ⏸ · trần người dùng duyệt 30/09: ≤ 25 USD (khóa ngân sách dự án trước) · tạm gác — không ưu tiên (người dùng 30/09); làm sau cùng khi người dùng gọi
- [ ] K.3 · Đo lại bảng mục 0 + phiếu so sánh phim tham khảo · nặng:1 · ⏸ · tạm gác — không ưu tiên (người dùng 30/09); làm sau cùng khi người dùng gọi

### S8 — Chấm lại bằng AI Development System (cuối cùng)
- [ ] S8.0 · Chấm 16 khu vực (2 agent độc lập, 0 USD) · nặng:2 · ⬜ · 30/09: không chờ K nữa (K tạm gác) · người dùng 30/09 tối: chấm SAU khi người dùng chạy xong các lệnh tốn tiền (docs/LENH_TON_TIEN_CHO_DUYET.md) — để có bằng chứng chạy thật
- [x] S8.1 · Trường feedback chi tiết cho từng khoản trừ · nặng:1 · ✅ · 2026-09-29: `feedback` tùy chọn mỗi khoản trừ (vì sao · sửa · file · nghiệm thu · 💻/💵/👤 · ưu tiên), định dạng ở devsys/feedback_format.md NGOÀI rubric.md (điểm cũ không thành "thang cũ"), gửi kèm người chấm, hiện dưới từng khoản trừ trên web; test
- [ ] S8.2 · Báo cáo đánh giá + danh sách việc theo điểm lấy lại · nặng:1 · ⬜
- [x] S8.3 · So sánh với phần mềm dựng phim AI bên ngoài · nặng:2 · ✅ · 2026-09-29 (0 USD, chỉ đọc web công khai): docs/SO_SANH_PHAN_MEM_NGOAI_2026-09-29.md — 13 sản phẩm (ClipAI web, LTX, Runway, Higgsfield, Kling 3.0, 即梦/Dreamina, Google Flow, MiniMax, Katalist, OpenArt, Hedra, Pika, ElevenLabs) × 10 khâu; mình hơn ở Director/QC/chi phí/âm thanh, kém ở sinh nhiều khung-shot một lần, nối hành động qua cắt, sửa clip, lựa chọn khớp môi; 10 đề xuất X1–X10 chờ người dùng chọn (S8.4)
- [ ] S8.4 · Rút việc nên học vào TODO · nặng:1 · ⬜

---

# Chi tiết từng đợt (bản người dùng duyệt)

## Chi tiết · S0 — Học từ phim drama tham khảo (0 USD, làm trước S3/S4)
Người dùng gợi ý tham khảo phim drama ngắn trên YouTube, ví dụ https://www.youtube.com/watch?v=bzsP_ArSIUA ("Từ Hôn Năm Người Bạn Đời Định
Mệnh", ReelShort lồng tiếng Việt, dọc 9:16, 2 giờ 54 phút).

**Đo thử 192 s đầu (đo trong trình duyệt, không tải video; so khác biệt màu từng khung để dò điểm cắt):**
| Chỉ số | Phim tham khảo | #8 | Ý nghĩa |
|---|---|---|---|
| Số shot / 192 s | 94 | — | ~1 cắt mỗi 2 s |
| Độ dài shot trung vị | **1,87 s** | 1,93 s (kế hoạch) | **nhịp cắt ngắn không phải lỗi** — drama dọc cũng cắt nhanh như vậy |
| 10 % / 90 % | 1,03 s / 3,33 s | nhiều shot 0,5–1 s | shot < 1 s hiếm (6/94) |
| Shot > 4 s | 4/94 | 0 | vài nhịp giữ hình dài ở khoảnh khắc cảm xúc |

**Điều chỉnh kết luận:** góp ý 1.5/1.6 ("khựng, giật") **không do shot ngắn** mà do mỗi shot được gen riêng → chuyển động bắt đầu lại từ đầu ở
mỗi điểm cắt. Phim thật quay **một đoạn diễn liên tục từ nhiều góc rồi cắt xen**, nên hành động chảy qua điểm cắt (cắt theo hành động).
→ S3.4 đổi hướng: không kéo dài shot, mà **gen đoạn diễn liên tục dài hơn cho mỗi góc máy rồi cắt ngắn nối theo hành động**.

### S0 chi tiết — nghiên cứu toàn diện (người dùng yêu cầu mức khá chi tiết, nhiều mặt)

**Hạ tầng dùng lại:** `core/reference_analysis.py` đã có đủ khung (dò cắt, 1 khung/shot, tờ ảnh 12 khung, nhãn cỡ cảnh `SIZES` / góc
`ANGLES` / chuyển động `MOVES` / vai trò shot `ROLES` / chuyển cảnh `TRANSITIONS`, `save_record` → `research/ff_styles/<STYLE>/`, `style_stats`)
và đường "YouTube cắt trong trình duyệt, gắn nhãn trong phiên chat". Thêm phong cách mới **`DRAMA_DOC`** (drama ngắn dọc). Chỉ giữ **dữ liệu
chữ** (mốc giây, nhãn, số đo), không lưu hình / âm của phim; trích lời ≤ 15 từ.

**Mẫu nghiên cứu (người dùng chốt Q0: chỉ 1 phim):** phim đã gửi, lấy **5 loại đoạn**: (1) 3 phút mở đầu, (2) một cảnh thoại hai người,
(3) một cảnh hành động / xô xát, (4) một hồi tưởng, (5) một cú ngoặt + kết tập (cliffhanger). ~15 phút phim, ~400 shot có nhãn.

**Ba lớp đo:**
- **Máy đo trong trình duyệt (0 USD):** điểm cắt (đã chạy được), độ sáng / màu trung bình từng shot, mức chuyển động trong shot (khác biệt
  khung liên tiếp), thử đo **độ to âm thanh theo giây** qua Web Audio (nếu trình phát cho phép; không được thì bỏ, ghi rõ).
- **Nhãn bằng mắt (Claude Code xem tờ ảnh 12 khung, 0 USD API):** cỡ cảnh, góc máy, vai trò shot, chuyển động máy, chuyển cảnh, có phụ đề /
  chữ hiệu ứng / tên nhân vật hay không, vị trí mắt trong khung dọc.
- **Xem – nghe trọn đoạn (Claude Code + người dùng xem lại mẫu):** diễn xuất, nhạc, hiệu ứng âm, cách dẫn truyện.

**Phiếu nghiên cứu — 10 mặt, mỗi mặt có chỉ số đo + câu hỏi định tính:**
| Mặt | Đo / ghi lại | Liên quan lỗi #8 |
|---|---|---|
| A. Cấu trúc truyện | móc 3 s đầu làm gì; bao lâu có một cú ngoặt; setup → payoff cách nhau bao lâu; cách giới thiệu nhân vật (có bảng tên không); kết tập kiểu gì; độ dài tập | 1.9 truyện cụt, 1.1 bảng tên |
| B. Thoại & lồng tiếng | câu/phút, độ dài câu, khoảng lặng giữa câu, người nói có luôn trong khung không, cắt sang người nghe khi nào | 1.2 độ dài, 1.7 khớp môi |
| C. Quay phim | phân bố cỡ cảnh (theo loại cảnh), góc, qua vai trong thoại, cận phản ứng, insert, tỉ lệ máy động / tĩnh, loại chuyển động, vị trí mắt, độ sâu trường ảnh | 1.6 đơn điệu 21/33 MS |
| D. Diễn xuất & chuyển động | cử chỉ khi nói, dáng theo cảm xúc, hành động (chạy, ngã, đánh) dài bao lâu và cắt mấy góc, chuyển động có liền qua điểm cắt không | 1.5 khựng, dáng sai |
| E. Dựng | phân bố độ dài shot **theo loại cảnh** (thoại / hành động / cảm xúc), cắt theo hành động, J/L-cut, nhịp giữ hình dài, speed ramp, freeze, montage | 1.5, 1.6 |
| F. Chuyển cảnh & hồi tưởng | kiểu chuyển cảnh giữa cảnh, đổi nơi có establishing không, hồi tưởng vào/ra thế nào (màu, hiệu ứng, âm, chữ) | 1.9 hồi tưởng |
| G. Âm thanh | % thời gian có nhạc, nhạc tắt khi nào / bao lâu, stinger ở cú ngoặt, SFX nhấn, âm nền, độ to tương đối thoại–nhạc | 1.8 mất nhạc, rè |
| H. Chữ trên màn hình | vị trí / cỡ / màu / font phụ đề, số dòng, thời gian hiện, né mặt thế nào, chữ hiệu ứng, tiêu đề | 1.1, 1.8 chữ đè mặt |
| I. Màu & ánh sáng | màu theo cảm xúc, ngày/đêm, hồi tưởng, độ tương phản mặt | 1.3, 1.9 |
| J. Bối cảnh | số bối cảnh / tập, thời lượng mỗi nơi, cách thiết lập không gian | 1.4 |

| Mã | Việc | Kết quả |
|---|---|---|
| S0.1 | Chọn 5 đoạn mẫu trong phim đã gửi (Q0), thêm `DRAMA_DOC` vào `STYLES` | danh sách nguồn + mốc giây |
| S0.2 | Máy đo trong trình duyệt cho mọi đoạn → `save_record` | số đo lớp 1 |
| S0.3 | Gắn nhãn tờ ảnh (Claude Code) → `merge_labels` → `style_stats` | bảng phân bố cỡ cảnh / góc / vai trò / chuyển cảnh |
| S0.4 | Xem – nghe trọn đoạn, điền phiếu 10 mặt | ghi chú định tính kèm mốc giây |
| S0.5 | Viết `docs/NGHIEN_CUU_DRAMA_THAM_KHAO_<ngày>.md`: mỗi mặt = số đo + **bảng so với #8** (khoảng cách) + 2–5 luật cụ thể có căn cứ | báo cáo cho người dùng duyệt |
| S0.6 | Luật được duyệt → `knowledge/roles/director.md`, `knowledge/editor/editing.md`, `safe_zones.md`, `cinematography_basics.md` (kèm nguồn) | bộ kỹ năng dùng cho S3 |
| S0.7 | Số đo thành **chỉ số mục tiêu** có ngưỡng cho linter bảng shot (S3) và QC bản dựng (S1.9) — ví dụ trung vị shot, % shot < 1 s, % có nhạc, nhạc tắt tối đa, cỡ cảnh liền nhau | `data/drama_targets.json` + test |
| S0.8 | **Phiếu so sánh** "bản dựng vs phim tham khảo" (10 mặt, thang 1–5) dùng để chấm #8 cũ, #8 dựng lại và lần chạy thật sau | phiếu trong báo cáo |

Nghiệm thu S0: mỗi mặt A–J có ≥ 3 chỉ số đo hoặc ghi chú kèm mốc giây (1 phim, Q0); ≥ 20 luật cụ thể; người dùng duyệt báo cáo.

**Giao cho agent — đúng việc, tiết kiệm (người dùng yêu cầu):**
- **Một agent** (`general-purpose`, model **sonnet** — rẻ hơn, đủ cho đo + gắn nhãn ảnh); phiên chính chỉ giao việc, kiểm mẫu, viết luật (S0.5–S0.8).
  Không chạy nhiều agent song song cho cùng phim.
- **0 USD Claude API**, không tải video, chỉ đo trong trình duyệt (cách đã chạy được ở phiên này: canvas + `requestVideoFrameCallback`, phát ×2).
- **Phạm vi khóa trước trong đề bài:** đúng danh sách phim + mốc giây của 5 loại đoạn (S0.1 do phiên chính chọn), mỗi đoạn ≤ 3 phút; mỗi tờ
  ảnh 12 khung xem **một lần**; không xem lại cả phim; không tìm thêm phim ngoài danh sách.
- **Đầu ra cố định:** mỗi đoạn một bản ghi `save_record` (JSON, định dạng sẵn có) + phiếu 10 mặt dạng bảng ngắn (≤ 1 trang / phim). Không viết
  văn dài.
- **Điểm dừng kiểm:** làm xong **2 đoạn đầu** (mở đầu + thoại) thì trả về và dừng; phiên chính kiểm định dạng + soi ngẫu nhiên 10 nhãn so với khung thật; đạt mới
  giao 3 đoạn còn lại (tiếp tục cùng agent để giữ ngữ cảnh, không mở agent mới).
- **Trần công sức:** ~150 lượt công cụ / phim; chạm trần thì trả phần đã có + ghi rõ đoạn chưa làm.

## Chi tiết · S1 — Dựng & âm thanh (0 USD, làm lại được trên 33 clip #8 có sẵn)
Sửa góp ý 1.1, 1.8, một phần 1.9.

| Mã | Việc | File chính | Nghiệm thu |
|---|---|---|---|
| S1.1 | **Bỏ hẳn** `name_cards` khỏi luồng (Q4); cue HUD không bao giờ ghi vào `.srt`; ghi luật dùng lại sau này (1 lần khi nhân vật mới xuất hiện, đặt cạnh nhân vật) vào `knowledge/editor/editing.md` | `core/features.py`, `core/subtitles.py:222` (`build_cues`), `to_srt` | `.srt` #8 không còn dòng chỉ có tên |
| S1.2 | Hiệu ứng âm thanh lưu `(shot, lệch trong shot)` thay vì giây tuyệt đối; giây tính lại mỗi lần dựng; timeline đổi → kế hoạch hiệu ứng thành "cũ" | `core/sfx_plan.py` (`timeline`, `apply`), `core/autopilot.py:828` (`_sfx_phase` + dấu `ai_sfx_done`), `audio_assets/assets.json` | súng/va chạm/bíp rơi đúng shot 26 (~63 s), không còn ở 43 s |
| S1.3 | Ý đồ nhạc tự sửa: `cut` lặp khi nhạc đã tắt → bỏ; nhạc tắt > 8 s → cảnh báo chặn ở Bước 5 | `core/sound_intent.py:60-110` (linter + `music_plan`) | #8 không còn khoảng 39–65 s mất nhạc (đo RMS từng giây) |
| S1.4 | Nhạc khớp độ dài thật: soạn lại theo timeline cuối, hoặc lặp/nối đoạn khi phim dài hơn nhạc | `core/music.py`, `core/delivery.py:262` (`sound_plan`) | nhạc phủ tới hết phim |
| S1.5 | Phụ đề chỉ lên đỉnh khi dải trên **trống mặt**; không thì thu nhỏ 1 cỡ / giữ dưới nâng lề | `core/text_placement.py:127` (`placements`), `core/subtitles.py:350` (`to_ass`) | giây 41–44 #8 chữ không đè mặt (dò mặt trên khung thật) |
| S1.6 | Limiter −1 dBTP cuối chuỗi; mã hóa âm một lần (giữ PCM giữa các bước — TON_DONG A18) | `core/ffmpeg_studio.py:399` (`render_final`), `core/final_cut.py` | đỉnh ≤ −1 dBTP; nghe lại giây 43 hết rè |
| S1.7 | Ngữ pháp hồi tưởng ở khâu Dựng: shot `flashback` → flash trắng vào/ra, màu ấm + giảm bão hòa + viền mờ, âm "whoosh" | `core/delivery.py`, `core/ffmpeg_studio.py`, cờ mới `flashback_fx` | shot 28 #8 nhận ra ngay là hồi tưởng |
| S1.8 | Shot kết giữ hình ≥ 2,5 s (kéo khung cuối / làm chậm) | `core/final_cut.py` | 2 shot kết #8 không còn 1 s |
| S1.9 | **QC bản dựng cuối bằng máy** (chặn giao khi lỗi): độ dài so mục tiêu, nhạc lặng > 8 s, hiệu ứng đè câu thoại, đỉnh âm, phụ đề đè mặt, dòng `.srt` không phải thoại, shot < 1 s | module mới `core/final_qc.py`, gọi trong `core/delivery.py`; hiện ở Bước 5 | chạy trên bản giao #8 cũ → bắt đủ 6 lỗi đã biết; bản dựng lại → 0 lỗi chặn |
| S1.10 | Dựng lại #8 từ clip sẵn có → `D:\AI-Video-Output\2026-09-28_du-an-8\v2\` | — | người dùng xem/nghe |

## Chi tiết · S2 — Timeline theo âm thanh + animatic (≈ 0,1 USD TTS)
Sửa gốc góp ý 1.2, 1.7 (phần thứ tự), PH 54.

| Mã | Việc | File chính | Nghiệm thu |
|---|---|---|---|
| S2.1 | Chọn giọng ở Bước 1 (mặc định 4 giọng VN trong `data/voices_vi.json`) | `dashboard/steps/step1.py`, `core/voice.py` | dự án mới có giọng trước Director |
| S2.2 | Sau Director: TTS nháp mọi câu → đo độ dài → chỉnh `duration_s` từng shot (code; lệch > 10 % mục tiêu → hỏi / Director chỉnh) → **khóa timeline** | `core/voice.py` (`fit_durations`, `place_on_timeline:339`), `core/autopilot.py` (thứ tự pha) | #8: độ dài dự kiến trước video = độ dài bản cuối ± 5 % |
| S2.3 | Cổng độ dài: tổng dự kiến lệch mục tiêu kịch bản > 10 % → dừng hỏi trước gen ảnh/video | `core/autopilot.py`, `core/budget.py` | — |
| S2.4 | **Animatic** ở cổng storyboard: ảnh storyboard + pan/zoom theo `camera_move` + giọng + nhạc + phụ đề + hiệu ứng (ffmpeg, 0 USD) | module mới `core/animatic.py`, dùng lại `ffmpeg_studio.render_final`, `subtitles`, `sfx_plan` | animatic #8 xem được trên dashboard trước khi bấm video |
| S2.5 | Clip đơn dài hơn shot → cắt theo chuyển động (`motion_trim`) thay vì giữ nguyên 4 s | `core/final_cut.py`, `core/seedance_refs.py` | — |

## Chi tiết · S3 — Director kể chuyện + Quay phim (💻; Claude chỉ tốn ở lần chạy kiểm)
Sửa góp ý 1.5 (phần dáng), 1.6, 1.9; gộp mục A của `docs/TON_DONG_2026-09-27.md`.

| Mã | Việc | File chính |
|---|---|---|
| S3.1 | Bảng nhịp truyện bắt buộc (thiết lập → xung đột → ngoặt → trả lời → kết); mỗi cú ngoặt có shot thiết lập trước | `prompts/19_*.md`, `prompts/20_*.md`, `knowledge/roles/director.md`, kiểm trong `core/llm_runner.py` (validate) |
| S3.2 | Agent "người xem lần đầu" (1 lượt Claude, chỉ đọc bảng shot + thoại) tóm truyện; tóm sai → Director sửa | module mới `core/story_check.py` |
| S3.3 | Trường `action_peak` → storyboard vẽ tư thế giữa hành động, không vẽ dáng đứng | prompt 20, `core/scene_storyboard.py` |
| S3.4 | **Đoạn diễn liên tục theo góc máy** (theo S0): Director nhóm các shot cùng một đoạn diễn; mỗi góc máy gen một clip diễn trọn đoạn (4–10 s), dựng cắt xen các góc theo hành động — nhịp cắt vẫn ~2 s nhưng chuyển động liền mạch. Shot < 1 s chỉ cho chèn cận có chủ ý | `core/seedance_refs.py`, `camera_setups` (H5), `core/final_cut.py` |
| S3.5 | Cổng Quay phim: ≤ 2 shot liền cùng cỡ; mỗi cảnh ≥ 1 chuyển động máy có lý do; camera move đi vào prompt video | linter bảng shot, `core/motion*.py` |
| S3.6 | Trường `transition_in` từng shot (cut, match, whip, zoom-through, J/L-cut, flash) + khâu Dựng thực hiện | `core/delivery.py`, `core/ffmpeg_studio.py` |
| S3.7 | `hook_mid` / `money_shot` / ý đồ nhạc: vi phạm → Director sửa lại (không chỉ cảnh báo) | linter + vòng hỏi lại hiện có của Director hai lượt |
| S3.8 | Đổi bối cảnh sau Director → bắt chạy lại Director cho cảnh bị ảnh hưởng; dự án mới kế thừa cách làm đã chốt (chia shot, look, phong cách) | `core/assets.py` auto_attach, `dashboard/steps/step1.py` |

Nghiệm thu S3: test dựng từ bảng shot #8 (không gọi lại Director #8); kiểm thật trên kịch bản hài 20–30 s mới (Q6) → agent người xem tóm
đúng truyện; linter 0 lỗi chặn; animatic (S2.4) người dùng duyệt.

## Chi tiết · S4 — Video chất lượng (💵 A/B ~3–5 USD, hỏi trước)
Sửa góp ý 1.3, 1.5, 1.7.

| Mã | Việc | File chính |
|---|---|---|
| S4.1 | Shot cận / cận trung thấy mặt → không gộp nhóm ref-only; đi đường khung đầu = ảnh storyboard | `core/seedance_refs.py` (`eligible`, `route`), `core/model_router.py` |
| S4.2 | Khớp môi mọi shot người nói thấy mặt (đánh dấu bằng code từ `dialogue` + `blocking`) — cách làm chọn theo **A/B (Q2)**: (a) Seedance tạo kèm giọng từng shot vs (b) clip nhóm + sync.so hậu kỳ | `core/seedance_refs.py:45` (`_lip_sync`), `core/autopilot.py:487` |
| S4.3 | Câu khóa phong cách "photoreal 3D game render, not anime" trong mọi prompt video | builder motion prompt |
| S4.4 | Mẫu motion prompt theo loại hành động (trọng tâm, chân chạm đất, tay, tóc/áo) | `core/motion*.py` |
| S4.5 | QC clip: so khung giữa clip với ảnh storyboard (mặt + màu/kết cấu); luồng quang phát hiện giật / trượt chân; đo khớp môi | `core/qc*.py` video |
| S4.6 | 💵 A/B: 2 shot cận (ref-only vs khung đầu) · 3 shot hành động × (Seedance Fast / Pro / Kling) · 2 shot khớp môi | `tools/experiments/` |

## Chi tiết · S5 — Bối cảnh thật theo file 3D Tháp Đồng Hồ (Q3; 💵 ≤ 2 USD vẽ thử)
Sửa góp ý 1.4.

| Mã | Việc | File chính |
|---|---|---|
| S5.1 | Render lại bộ ảnh chuẩn từ GLB Tháp Đồng Hồ (Kho asset 263): tầm mắt, cách tháp 10–30 m, 6–8 hướng, ngày/đêm; thay 3.png/4.png (render sát chân tháp) làm ảnh tham chiếu; sinh câu bố cục từ mặt bằng GLB | `core/location_pack.py`, `tools/location_pack.py`, Kho |
| S5.2 | Chặn gửi prompt ảnh ở địa điểm có mô tả bố cục mà prompt thiếu câu bố cục | `core/scene_establish.py`, đường gửi ảnh |
| S5.3 | Mô tả / ảnh địa điểm đổi → mọi khung ở địa điểm đó thành "cũ" | cơ chế ảnh cũ hiện có (`input_hash`) |
| S5.4 | Lớp 0 đo "tầng tường" (so khung với ảnh toàn cảnh) | `core/qc_scene.py`, sổ tay G1 `knowledge/qc_playbook.md` |
| S5.5 | 💵 Vẽ lại khung #8 bị nhiều tầng | — |
| S5.7 | Hướng máy (`plate_view` + lý do) và đèn cảnh đêm (`practical_lights`) quyết theo kịch bản từng shot, không cố định theo chỗ đứng; chỗ đứng "tùy kịch bản" (dưới mái che) thiếu hướng → dừng + báo; render nền nhận hướng + đèn, khóa cache theo (chỗ đứng, hướng, giờ, thời tiết, đèn) | `core/plate_choice.py`, `core/location_pack.py`, `tools/render_plates.py`, `tools/location_pack.py` (`script-view`, `preview`) |

## Chi tiết · S6 — Ước tính, ngân sách, dashboard (0 USD)
| Mã | Việc | File chính |
|---|---|---|
| S6.1 | Ước tính theo cách làm đã chốt (shot, nhóm Seedance, khớp môi) + vẽ lại / làm lại / nghiệm thu; ngay từ trước Director | `core/cost.py:302` (`estimate_run`) |
| S6.2 | Màn **timeline tổng** (shot + thoại + nhạc + hiệu ứng + phụ đề) | `dashboard/steps/step5.py` hoặc màn mới |
| S6.3 | Hiện danh sách cờ `verified: False` đang ảnh hưởng bản dựng; bản giao chính chỉ dùng cờ đã kiểm | `core/features.py`, Bước 5 |
| S6.4 | E-mail khỏi URL (`?login=`); job ảnh tự gửi khi autopilot chờ cổng; "đã dùng / trần / còn" rõ; cảnh báo "code đổi, cần khởi động lại"; panel 🧪 cho người thường | `dashboard/` |
| S6.5 | Ghi `verified` cho cờ đã được #8 chứng minh (kèm ngày, dự án, số đo) | `core/features.py` |
| S6.6 | Áp tài liệu prompt caching (tóm tắt do agent đọc, 2026-09-28): ước tính 1 lượt = đọc cache × giá đọc + ghi cache × giá ghi + phần không cache × giá thường (khớp cách đang làm trong `llm_runner`); đối chiếu với `usage` thật (`cache_read_input_tokens`, `cache_creation_input_tokens`) trong bảng `llm_calls`. **Kiểm lại tại chỗ trên tài liệu trước khi code** 3 điểm bản tóm tắt còn nghi: số breakpoint tối đa (tóm tắt lẫn với "lookback 20 block"), giá / độ dài tối thiểu của `claude-sonnet-5`, cache với `file_id` ảnh | `core/llm_runner.py`, `core/cost.py`, `data/pricing.json` |

## Chi tiết · S7 — Agent QC (💵 ~1 USD)
| Mã | Việc |
|---|---|
| S7.0 | Theo tài liệu caching: xóa/đổi ảnh ở phần đầu hội thoại → mất cache (đúng nguyên nhân PH 45). Đổi cách: **không cắt ảnh cũ ở giữa hội thoại**; thay vào đó giữ ảnh cũ (thử gửi bằng Files API `file_id` cho payload nhỏ), ảnh mới luôn nằm sau điểm cache cuối; khi hội thoại quá dài thì **kết thúc phiên và mở phiên mới** với bản tóm kết luận (1 lần ghi cache mới) thay vì cắt tỉa. Director hai lượt: giữ luật lượt Đạo diễn ghi cache xong mới chạy song song 6 lượt Quay phim (đang làm — kiểm lại bằng `usage` thật). File: `core/qc_agent.py`, `core/llm_runner.py` |
| S7.1 | Nghiệm thu lại `qc_agent` trên bộ nhãn đã sửa (38 ca) + thêm ca video; đạt (100 % khung chặn, 0 chặn oan) mới bật cờ; đo tỉ lệ token đọc cache ≥ 70 % |

---

## Chi tiết · S9 — Dashboard gọn, dễ nhìn (0 USD) — góp ý mới của người dùng
Bối cảnh: dashboard nay chạy chủ yếu bằng Claude API (Director, QC, dịch…), nhiều khung nhập tay / dán JSON / thông tin kỹ thuật không còn cần
tương tác nhưng vẫn chiếm chỗ. Đã có sẵn: công tắc **🧠 Chế độ chuyên gia** (`dashboard/common.py:52` `expert()`, `dashboard/header.py:173`,
đang dùng ở 17 chỗ), bộ thẻ `ui.card_title`, `step_header`, bản kiểm kê cũ `docs/UI_AUDIT.md`.

**Nguyên tắc 3 tầng hiển thị (áp cho mọi bước):**
1. **Luôn hiện:** tiêu đề bước + tiến độ, **việc kế tiếp + 1 nút chính**, lỗi chặn, tiền (ước tính / đã dùng / trần).
2. **Thu gọn, có nút "▸ Xem chi tiết":** thông tin để hiểu / kiểm tra (kịch bản đã phân tích, kiểm tổ làm phim, Director đánh đổi, ghi chú,
   cảnh báo nhỏ, danh sách job, nhật ký).
3. **Chỉ ở Chế độ chuyên gia:** nhập tay, dán JSON, copy prompt, cài đặt kỹ thuật, thử nghiệm.

| Mã | Việc | File chính |
|---|---|---|
| S9.1 | **Nút thu gọn phần Kịch bản** (1a): khi đã tách cảnh → thu thành 1 dòng tóm tắt ("📜 6 cảnh · 23 câu thoại · phân tích lúc …") + nút "▸ Mở kịch bản"; chưa có kịch bản thì mở sẵn; nhớ trạng thái theo dự án (`session_state`) | `dashboard/steps/step1.py:337-375` |
| S9.2 | Thành phần chung `ui.fold(tiêu đề, tóm tắt 1 dòng, key, mở_mặc_định)` — khung thu gọn thống nhất, tóm tắt luôn nhìn thấy khi đóng | `dashboard/ui.py` |
| S9.3 | Kiểm kê mọi khung ở 5 bước + thanh đầu → xếp tầng 1/2/3 (bảng trong `docs/UI_AUDIT.md` mục mới, người dùng duyệt trước khi sửa) | `docs/UI_AUDIT.md` |
| S9.4 | Áp bảng kiểm kê: Director copy prompt / dán JSON, Kho chủ thể Seedance, World Bible, "✏ Sửa nhân vật", bảng giá, mức sàn QC… → tầng 2/3; mỗi bước có dải "Việc tiếp theo" ở đầu | `dashboard/steps/step1–5.py`, `dashboard/header.py` |
| S9.5 | Tách `step1.py` (1352 dòng, thang devsys trừ điểm > 900 dòng) thành các phần nhỏ (kịch bản, nhân vật, Director, thoại, ngân sách) | `dashboard/steps/` |
| S9.6 | Gộp S6.2 (timeline tổng), S6.4 (e-mail khỏi URL, panel 🧪…) vào cùng đợt để không sửa giao diện hai lần | — |

Nghiệm thu S9: test AppTest hiện có qua hết + test mới cho `ui.fold`; chụp màn từng bước trước/sau bằng trình duyệt trong app (dự án #8),
đo chiều cao trang và số khung hiện sẵn (mục tiêu giảm ≥ 40 % ở Bước 1); người dùng xem ảnh và thử thao tác.

## Chi tiết · S8 — Chấm lại bằng AI Development System (sau khi các đợt được duyệt đã xong)
Dùng đúng quy trình lần chấm 2026-09-26 (`docs/DANH_GIA_DEVSYS_2026-09-26.md`, thang cố định `devsys/rubric.md`):
1. Chạy đủ test (`py -m pytest`) để bộ đo có lần chạy test mới nhất (code tự hạ điểm nếu kết quả test cũ hơn code).
2. `py tools/devsys_score.py --export <khu_vực>` cho 16 khu vực (`devsys/areas.json`).
3. **2 agent Claude Code độc lập** (không agent nào viết code được chấm), mỗi agent 8 khu vực, chấm theo thang → file JSON
   `devsys-score/1` → `py tools/devsys_score.py --import file.json --scorer claude-code-session`. **0 USD** (không dùng Claude API).
4. Viết `docs/DANH_GIA_DEVSYS_<ngày>.md`: bảng so với lần 1 (79,8/100), khu vực tăng/giảm, lỗi người chấm tìm ra → sửa lỗi chặn → báo người dùng.
5. Kỳ vọng: tiêu chí "Bằng chứng chạy thật" tăng nhờ #8 (trước 0/23 cờ đã kiểm); các khu vực Bước 5, Khớp môi, Tài liệu là nơi cần xem kỹ.

**Mở rộng theo góp ý người dùng — đánh giá + feedback chi tiết cho từng điểm trừ:**
| Mã | Việc | File chính |
|---|---|---|
| S8.1 | Mỗi khoản trừ thêm trường **`feedback`**: vì sao trừ (ảnh hưởng tới người dùng / chất lượng phim), **cách sửa cụ thể** (file, hàm, việc), cách nghiệm thu, ước công (💻/💵), mức ưu tiên. Trường tùy chọn → điểm cũ vẫn đọc được; giữ nguyên bảng tiêu chí để điểm so được với lần 1 (nếu `rubric_hash` tính cả phần định dạng thì tách phần định dạng ra file riêng) | `devsys/scorer.py` (kiểm + lưu), `devsys/scores.py`, `devsys/app.py` (hiện feedback dưới từng khoản trừ), `tools/devsys_score.py --import` |
| S8.2 | Báo cáo tổng: mỗi khu vực = điểm + danh sách khoản trừ kèm feedback + 3 việc nên làm trước; cuối báo cáo gom **danh sách việc sửa xếp theo điểm lấy lại được / công** | `docs/DANH_GIA_DEVSYS_<ngày>.md` |
| S8.3 | **So sánh với phần mềm dựng phim AI bên ngoài** (giao 1 agent `general-purpose` model sonnet, chỉ đọc web, 0 USD API, trần ~80 lượt công cụ): 6–8 sản phẩm đang dùng thực tế (ví dụ LTX Studio, Runway, Kling / ClipAI web, Higgsfield, Google Flow, Pika, OpenArt/Hedra, CapCut AI…) — so trên các mặt: kịch bản → shot tự động, giữ nhân vật nhất quán, storyboard / animatic, khớp môi, giọng tiếng Việt, dựng + âm thanh tự động, QC, kiểm soát chi phí, cộng tác. Mỗi ô ghi nguồn (trang tính năng / tài liệu, ngày đọc); không đoán — không có nguồn thì ghi "không rõ" | `docs/SO_SANH_PHAN_MEM_NGOAI_2026-09-29.md` (xong 2026-09-29; làm trong phiên chính, không giao agent) |
| S8.4 | Từ bảng so sánh rút ra: dashboard **hơn** ở đâu (giữ), **kém** ở đâu (đưa vào TODO kèm mức ưu tiên), tính năng nên học | mục cuối của báo cáo S8.2 |

## Chi tiết · Kiểm tra đầu–cuối (sau S1–S4)
- Test: `py -m pytest` qua hết, có test hồi quy cho từng lỗi 1.1–1.9 dựng từ dữ liệu #8 (`tests/fixtures/`).
- #8 dựng lại (S1.10) + animatic (S2.4): `core/final_qc.py` 0 lỗi chặn; đo RMS/đỉnh bằng ffmpeg; Claude Code xem khung + nghe.
- **Chạy thật lần kiểm (theo người dùng):** kịch bản **ngắn gọn, hài hước, 3 nhân vật Kelly · Maxim · Kenta, 20–30 s** (dự án mới, trần duyệt
  **một lần** ở Bước 1, chỉ cờ đã kiểm). Kịch bản: Claude Code soạn 2–3 bản nháp trong chat (0 USD) để người dùng chọn/sửa, hoặc người dùng
  gửi. Đo lại bảng mục 0 của tài liệu tổng kết (độ dài lệch ≤ 10 %, chi phí lệch ước tính ≤ 20 %, 0 lỗi chặn ở QC bản dựng) + chấm phiếu so
  sánh với phim tham khảo (S0.8).

## Chi tiết · Quyết định người dùng đã chốt (2026-09-28)
| Câu | Chốt | Ảnh hưởng tới kế hoạch |
|---|---|---|
| Q0 | Chỉ **1 phim** tham khảo (link đã gửi) để tránh loãng | S0: 5 loại đoạn lấy từ phim này; nghiệm thu "≥ 3 chỉ số / mặt" trên 1 phim; không tìm thêm phim |
| Q1 | Đồng ý thứ tự; **devsys chấm một lần ở cuối** | S8 chỉ chạy sau cùng |
| Q2 | **Chạy test so sánh 2 phương án** khớp môi | S4.2 → A/B: (a) Seedance tạo kèm giọng từng shot vs (b) clip nhóm + sync.so hậu kỳ, cùng 2–3 shot thoại; chấm độ khớp môi (đo máy + mắt), giá / giây, độ giữ nhân vật. Cần kiểm tài khoản / khóa sync.so trước (đợt thử cũ không mở) |
| Q3 | Dùng **file 3D Tháp Đồng Hồ đã cung cấp** làm chuẩn | S5.1 đổi: không xin ảnh in-game; render lại bộ ảnh chuẩn từ GLB ở **tầm mắt, cách tháp 10–30 m, 6–8 hướng, ngày/đêm** (thay render sát chân tháp đã gây lỗi nhiều tầng) + câu bố cục sinh từ mặt bằng GLB; lớp 0 so khung với bộ này |
| Q4 | **Bỏ hẳn** bảng tên | S1.1 xóa khỏi luồng; ghi luật cho sau này vào `knowledge/editor/editing.md`: nếu dùng lại thì hiện **một lần duy nhất** khi nhân vật xuất hiện lần đầu trong cả video, đặt **cạnh chính nhân vật đó** (theo vị trí dò được), không vào `.srt` |
| Q5 | Lần kiểm dùng **chất lượng cao** (kịch bản ngắn) | tắt 🧪 Thử rẻ cho dự án kiểm; model theo S4 A/B |
| Q6 | **Claude tự chọn / soạn 1 kịch bản** hài 20–30 s (Kelly · Maxim · Kenta) | viết ở cuối S3 để kiểm cả bảng nhịp truyện + agent người xem; mục đích: đo xem tổng thể đã tốt hơn chưa |
| Q7 | **Trần cả đợt 50 USD, Claude API 3 USD**; Director phải đưa ra **con số dự tính tổng tiền dự án** khi phân tích kịch bản | xem bảng ngân sách dưới; S6.1 mở rộng |

**S6.1 mở rộng (Q7):** ngay khi Director trả bảng shot, code tính **dự tính tổng dự án chia khâu** (ảnh, video, âm thanh, Claude, dự phòng vẽ
lại/làm lại) bằng `cost.estimate_run` + ngân sách dự án (`project_budget`) và **hiện cùng kết quả Director** ở Bước 1; Director nhận trần dự án
làm mục tiêu (đã có "mục tiêu ngân sách vào prompt") và phải giải thích khi bảng shot vượt. Nghiệm thu: dự tính lúc Director lệch chi phí thật
lần kiểm ≤ 20 %.

**Bảng ngân sách đợt (trần cứng, khóa trước từng việc):**
| Việc | Tổng (USD) | trong đó Claude API |
|---|---|---|
| S0, S8 (agent Claude Code, trình duyệt) | 0 | 0 |
| S1 dựng lại #8, S2 animatic #8 (TTS nháp) | ≤ 0,5 | 0 |
| S4 A/B: cận ref-only vs khung đầu · hành động 3 model · khớp môi (a) vs (b) | ≤ 12 | ≤ 0,3 (QC clip) |
| S5 render GLB (0) + vẽ lại khung thử nền tháp | ≤ 2 | 0 |
| S7 nghiệm thu agent QC | ≤ 1 | ≤ 0,7 |
| Lần chạy kiểm 20–30 s chất lượng cao (Director + agent người xem + ảnh + video + giọng + QC) | ≤ 25 | ≤ 1,5 |
| Dự phòng (chỉ dùng khi người dùng đồng ý) | ~9,5 | ~0,5 |
| **Cộng** | **50** | **3** |
Không chạy lại Director cho #8 (đắt Claude) — kiểm S3 trên kịch bản mới.

