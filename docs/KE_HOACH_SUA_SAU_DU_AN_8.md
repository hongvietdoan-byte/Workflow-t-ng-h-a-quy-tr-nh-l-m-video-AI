# Kế hoạch sửa sau dự án #8 (2026-09-28) — NGUỒN DUY NHẤT VỀ TIẾN ĐỘ ĐỢT NÀY

> Người dùng duyệt 2026-09-28. Phân tích gốc: `docs/TONG_KET_DU_AN_8_2026-09-28.md`.
> Trần đợt: 50 USD · Claude 3 USD · từ 2026-09-28T08:00:00+00:00
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
| S1 Dựng & âm thanh | 15 | 13 | 0 | 2 | 0 | 88,9 % |
| S0 Học từ phim drama tham khảo | 15 | 11 | 4 | 0 | 0 | 79,6 % |
| S9 Dashboard gọn, dễ nhìn | 6 | 5 | 0 | 0 | 0 | 81,8 % |
| S2 Timeline theo âm thanh + animatic | 6 | 0 | 0 | 1 | 0 | 0 % |
| S3 Director kể chuyện + Quay phim | 8 | 0 | 0 | 0 | 0 | 0 % |
| S4 Video chất lượng | 12 | 2 | 0 | 4 | 0 | 10 % |
| S5 Bối cảnh theo file 3D Tháp Đồng Hồ | 6 | 0 | 0 | 1 | 0 | 0 % |
| S6 Ước tính, ngân sách, dashboard | 6 | 0 | 0 | 0 | 0 | 0 % |
| S7 Agent QC | 2 | 0 | 0 | 0 | 0 | 0 % |
| K Chạy kiểm kịch bản hài 20–30 s | 3 | 0 | 0 | 0 | 0 | 0 % |
| S8 Chấm lại bằng AI Development System (cuối cùng) | 5 | 0 | 0 | 0 | 0 | 0 % |
| **Tổng** | **86** | **33** | **4** | **8** | **0** | **40,8 %** |

Đợt hiện tại: **S1** · việc kế: **S9.6** Gộp timeline tổng + sửa giao diện S6.4
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
- [ ] S1.14 · Soạn nhạc mới theo nhịp truyện cho #8 (người dùng cho phép, sáng tạo theo diễn biến) · nặng:2 · ⏸ · người dùng: xem sau (bản v4 ở D:/AI-Video-Output/2026-09-28_du-an-8/v4_nhac_moi)
- [ ] S1.15 · Tùy chọn model nhạc Eleven Music v2.5 (cập nhật ClipAI) · nặng:1 · ⏸ · chờ người dùng duyệt đề xuất docs/CAP_NHAT_CLIPAI_2026-09-28.md

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
- [ ] S0.11 · Kho kỹ thuật chuyên môn `knowledge/craft/` (máy quay, góc, chuyển động máy, chuyển cảnh, dựng, âm thanh): mỗi kỹ thuật = cách làm + nhiều ý đồ có thể phục vụ + điều kiện + ví dụ ≥ 2 mẫu + nguồn tài liệu (tóm lời mình) · nặng:3 · 🔄 · lượt 1 xong: research/craft/NGUON.md (30 nguồn) + draft 5 nhóm (25 mục) — kiểm duyệt: nhiều mục mới dẫn trang chủ / tóm tắt tìm kiếm, cần lượt 2 đọc bài gốc + ví dụ mốc giây (S0.12) rồi mới vào knowledge/craft/
- [ ] S0.12 · Xem nhiều mẫu đa thể loại (drama dọc, MV, quảng cáo game, phim ngắn, hoạt hình FF…) gắn nhãn theo kho kỹ thuật S0.11 · nặng:3 · 🔄 · short drama = drama dọc 9:16 kiểu ReelShort làm bằng AI (ưu tiên hàng Trung Quốc); danh sách 25 video (research/craft/MAU_S0_12.md), người dùng duyệt 2026-09-29; agent đang xem 2 video đầu (điểm dừng kiểm); bổ sung sau: quảng cáo phim AI của app DramaBox (người dùng gợi ý)
- [ ] S0.13 · Rà kiến thức đang dùng (director / dp / editing / ff_styles) tìm chỗ gán nghĩa cố định hoặc khái quát từ 1 mẫu → sửa thành tư liệu có điều kiện · nặng:1 · ✅ · agent rà 16 chỗ (cinematography_basics 3, dp.md Q2/Q3/Q5/Q8 4, director.md Đ4/N5 2, film_director_method 3, video_motion_vocab 1, genre_guides 3) → đã sửa hết; 1340 test qua
- [ ] S0.14 · Nghiên cứu nguồn tiếng Trung về phim AI (AI短剧 9:16, workflow, nội dung, prompt ngắn đủ ý, cảnh xịn; Seedance/即梦/可灵 tài liệu chính thức, WaytoAGI, bài ngành) → research/craft/trung_quoc/ · nặng:3 · 🔄 · lượt 1 xong: 18 nguồn (Seedance 2.5 提示词指南 chính thức đọc trọn, 第一财经, 澎湃, Zhihu), quy trình 9 bước, nội dung, prompt, nhạc nền, 15 bài học có mức bằng chứng — chờ người dùng xem; thiếu: tài liệu Kling, phỏng vấn biên kịch / đạo diễn có tên
- [ ] S0.15 · Nghề nhạc phim: spotting, nhạc dẫn cảm xúc / dẫn dắt / tạo nhịp, khác nhau theo thể loại (short drama dọc, phim ngắn, hành động, hài, MV, CGI…), cách brief nhạc → prompt model nhạc; đối chiếu music_timing / sound_intent hiện có · nặng:2 · 🔄 · lượt 1 xong: research/craft/draft/nhac_nen.md (15 kỹ thuật), nhac_theo_the_loai.md (8 thể loại), nhac_bai_hoc_pipeline.md (10 bài học đối chiếu music_timing), 20 nguồn (#31–50) + trung_quoc/NHAC_NEN.md — chờ người dùng xem

### S9 — Dashboard gọn, dễ nhìn
- [x] S9.1 · Nút thu gọn phần Kịch bản · nặng:1 · ✅ · xong: 1a Kịch bản thu thành 1 dòng tóm tắt + nút ▸ Mở / ▾ Thu gọn (test_dashboard)
- [x] S9.2 · Thành phần chung ui.fold · nặng:1 · ✅ · xong: ui.fold (dashboard/ui.py)
- [x] S9.3 · Kiểm kê khung → 3 tầng hiển thị (người dùng duyệt) · nặng:2 · ✅ · người dùng duyệt hết bảng E (2026-09-28)
- [x] S9.4 · Áp kiểm kê cho 5 bước + thanh đầu, dải "Việc tiếp theo" · nặng:3 · ✅ · 1c3ce9d · dải Việc tiếp theo 5 bước + các khung theo bảng; đo #8: Bước 1 mặc định 3.347 px so với 11.924 px mở hết (−72 %, mục tiêu −40 %)
- [x] S9.5 · Tách step1.py thành phần nhỏ · nặng:2 · ✅ · step1.py 1.397 dòng → step1 / _run / _prep / _characters / _director (≤ 378 dòng mỗi file); 1337 test qua
- [ ] S9.6 · Gộp timeline tổng + sửa giao diện S6.4 · nặng:2 · ⬜ · làm cùng đợt S6 (timeline tổng + sửa giao diện S6.4) để không sửa giao diện hai lần

### S2 — Timeline theo âm thanh + animatic
- [ ] S2.1 · Chọn giọng ở Bước 1 · nặng:1 · ⬜
- [ ] S2.2 · TTS nháp sau Director → chỉnh thời lượng → khóa timeline · nặng:3 · ⬜
- [ ] S2.3 · Cổng độ dài ±10 % · nặng:1 · ⬜
- [ ] S2.4 · Animatic ở cổng storyboard · nặng:3 · ⬜
- [ ] S2.5 · Clip đơn cắt theo chuyển động · nặng:1 · ⬜
- [ ] S2.6 · Thử Seed Audio 1.0 làm track thoại cả cảnh (3 giọng mẫu, mốc 100 ms, mốc phụ đề) · nặng:2 · ⏸ · chờ người dùng duyệt (cập nhật ClipAI)

### S3 — Director kể chuyện + Quay phim
- [ ] S3.1 · Bảng nhịp truyện bắt buộc · nặng:2 · ⬜
- [ ] S3.2 · Agent "người xem lần đầu" · nặng:2 · ⬜
- [ ] S3.3 · action_peak → storyboard vẽ tư thế hành động · nặng:1 · ⬜
- [ ] S3.4 · Đoạn diễn liên tục theo góc máy, cắt xen · nặng:3 · ⬜
- [ ] S3.5 · Cổng Quay phim (cỡ cảnh, chuyển động máy) · nặng:2 · ⬜
- [ ] S3.6 · transition_in từng shot + khâu Dựng thực hiện · nặng:2 · ⬜
- [ ] S3.7 · hook_mid / money_shot / ý đồ nhạc: vi phạm → Director sửa · nặng:1 · ⬜
- [ ] S3.8 · Đổi bối cảnh → chạy lại Director; dự án mới kế thừa cách làm · nặng:2 · ⬜

### S4 — Video chất lượng
- [ ] S4.1 · Shot cận có mặt → khung đầu thay vì ref-only · nặng:2 · ⬜
- [ ] S4.2 · Khớp môi mọi shot người nói thấy mặt (theo A/B) · nặng:2 · ⬜
- [ ] S4.3 · Câu khóa phong cách "không anime" · nặng:1 · ⬜
- [ ] S4.4 · Mẫu motion prompt theo loại hành động · nặng:1 · ⬜
- [ ] S4.5 · QC clip so storyboard + luồng quang + khớp môi · nặng:3 · ⬜
- [ ] S4.6 · A/B trả tiền: cận · hành động 3 model · khớp môi (a)/(b) · nặng:2 · ⬜
- [ ] S4.7 · Kho chủ thể cho mọi ảnh nhân vật gửi Seedance, bỏ mẹo dấu đỏ trên mắt · nặng:2 · ⏸ · chờ người dùng duyệt (tài liệu ClipAI chính thức)
- [x] S4.8 · Prompt Seedance 2.0/Fast theo 'Shot 1 / Shot 2' thay vì mốc giây · nặng:1 · ✅ · 2026-09-29: seedance_refs.prompt(model=) — 2.0/Fast chỉ số shot, 2.5 giây nguyên liên tục; test
- [x] S4.9 · Prompt theo tài liệu chính thức (vai trò ảnh theo thứ tự xuất hiện, hành động khái quát, biểu cảm dịu + chặn mắt phát sáng, ảnh tham chiếu ≤ 1280 px) · nặng:1 · ✅ · 2026-09-29: seedance_refs (soften, busy_shots ⚠, REF_MAX_SIDE), knowledge/seedance_prompting.md; 1345 test qua; chưa chạy thật (cần lần sinh video kế)
- [ ] S4.10 · A/B Seedance 2.5 (720P) vs Fast: cận, chạy, thoại có tham chiếu âm thanh tiếng Việt · nặng:2 · ⏸ · chờ người dùng duyệt (~3–4 USD)
- [ ] S4.11 · Chế độ bản mẫu (Sample Mode): xác minh API, bản mẫu → duyệt → bản cuối 1080P · nặng:2 · ⏸ · PDF đã có: mẫu chỉ 480p (Seedance 2.5), bản cuối chỉ 1080p, mẫu hết hạn ~7 ngày; còn thử API
- [ ] S4.12 · Advanced Edit: sửa clip lỗi (cận Kelly #8) thay vì sinh lại — kiểm API, thử 1 clip · nặng:1 · ⏸ · chờ người dùng duyệt (docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md, ~0,5 USD)

### S5 — Bối cảnh theo file 3D Tháp Đồng Hồ
- [ ] S5.1 · Render bộ ảnh chuẩn từ GLB ở tầm mắt + câu bố cục · nặng:2 · ⬜
- [ ] S5.2 · Chặn prompt thiếu câu bố cục · nặng:1 · ⬜
- [ ] S5.3 · Địa điểm đổi → khung thành "cũ" · nặng:1 · ⬜
- [ ] S5.4 · Lớp 0 đo "tầng tường" · nặng:2 · ⬜
- [ ] S5.5 · Vẽ thử lại khung nền tháp · nặng:1 · ⬜
- [ ] S5.6 · Render tháp GLB thành video white-model làm tham chiếu cho Seedance 2.5 · nặng:1 · ⏸ · chờ người dùng duyệt (cập nhật ClipAI)

### S6 — Ước tính, ngân sách, dashboard
- [ ] S6.1 · Dự tính tổng dự án ngay khi Director trả bảng shot · nặng:2 · ⬜
- [ ] S6.2 · Màn timeline tổng · nặng:2 · ⬜
- [ ] S6.3 · Hiện cờ chưa kiểm ảnh hưởng bản dựng · nặng:1 · ⬜
- [ ] S6.4 · E-mail khỏi URL, job ảnh khi chờ cổng, trần rõ, cảnh báo khởi động lại · nặng:2 · ⬜
- [ ] S6.5 · Ghi verified cho cờ đã chứng minh · nặng:1 · ⬜
- [ ] S6.6 · Áp tài liệu prompt caching vào ước tính · nặng:1 · ⬜

### S7 — Agent QC
- [ ] S7.0 · Agent QC giữ cache (không cắt ảnh giữa hội thoại) · nặng:2 · ⬜
- [ ] S7.1 · Nghiệm thu lại agent QC · nặng:1 · ⬜

### K — Chạy kiểm kịch bản hài 20–30 s
- [ ] K.1 · Soạn kịch bản hài Kelly · Maxim · Kenta · nặng:1 · ⬜
- [ ] K.2 · Chạy trọn trên dashboard, chất lượng cao, trần duyệt một lần · nặng:3 · ⬜
- [ ] K.3 · Đo lại bảng mục 0 + phiếu so sánh phim tham khảo · nặng:1 · ⬜

### S8 — Chấm lại bằng AI Development System (cuối cùng)
- [ ] S8.0 · Chấm 16 khu vực (2 agent độc lập, 0 USD) · nặng:2 · ⬜
- [ ] S8.1 · Trường feedback chi tiết cho từng khoản trừ · nặng:1 · ⬜
- [ ] S8.2 · Báo cáo đánh giá + danh sách việc theo điểm lấy lại · nặng:1 · ⬜
- [ ] S8.3 · So sánh với phần mềm dựng phim AI bên ngoài · nặng:2 · ⬜
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
| S8.3 | **So sánh với phần mềm dựng phim AI bên ngoài** (giao 1 agent `general-purpose` model sonnet, chỉ đọc web, 0 USD API, trần ~80 lượt công cụ): 6–8 sản phẩm đang dùng thực tế (ví dụ LTX Studio, Runway, Kling / ClipAI web, Higgsfield, Google Flow, Pika, OpenArt/Hedra, CapCut AI…) — so trên các mặt: kịch bản → shot tự động, giữ nhân vật nhất quán, storyboard / animatic, khớp môi, giọng tiếng Việt, dựng + âm thanh tự động, QC, kiểm soát chi phí, cộng tác. Mỗi ô ghi nguồn (trang tính năng / tài liệu, ngày đọc); không đoán — không có nguồn thì ghi "không rõ" | `docs/SO_SANH_PHAN_MEM_AI_<ngày>.md` |
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

