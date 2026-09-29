# S0.14 lượt 2 — Kling chính thức, người làm nghề có tên, "cảnh xịn" làm thế nào (2026-09-29)

> Bổ sung cho lượt 1 (`NGUON_TQ.md` #1–18, `BAI_HOC_CHO_PIPELINE.md`). Lấp 2 khoảng trống lượt 1 đã ghi: **tài liệu Kling chính thức**
> và **phỏng vấn người làm có tên**. Nguồn mới #19–#29 ở `NGUON_TQ.md` mục H. Mọi điều dưới đây là **tư liệu có điều kiện** (theo
> `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md`): ghi "ai nói, trong hoàn cảnh nào, độ tin", không phải luật. Trích nguyên văn ≤ 15 chữ.

## 1. Kling 3.0 — tài liệu chính thức (đọc trọn trang hướng dẫn) [19] + bản 驯服指南 [20]

| Điểm | Kling 3.0 (chính thức [19]) | So với Seedance 2.5 (lượt 1, [1]) |
|---|---|---|
| Thời lượng | 3–15 s liên tục, chọn linh hoạt | tương đương |
| Nhiều shot | 2 chế độ: **Multi-Shot tự động** (model tự chia shot, cỡ cảnh, góc) và **Custom Multi-Shot** (người viết từng shot + thời lượng) — ví dụ trong trang có 4–6 shot / 15 s | Seedance 2.5: mốc giây liên tục; 2.0: `Shot N` |
| Cách viết shot | "Shot 1, profile shot… Shot 2, frontal macro shot…" — mỗi shot: góc/cỡ + chuyển động máy (+ thời lượng nếu cần) | gần giống cách pipeline đang viết cho 2.0 |
| Nhất quán | **Element Binding**: tạo "chủ thể" từ 1 video quay (lấy cả ngoại hình + giọng) hoặc 2–4 ảnh (+ audio tùy chọn) | ClipAI: kho chủ thể (S4.7) |
| Thoại gốc | Trung, Anh, Nhật, Hàn, Tây Ban Nha (+ giọng vùng) — **không có tiếng Việt** trong danh sách | Seedance 2.5 có tiếng Việt (docs ClipAI 2026-09-28) |
| Ai nói câu nào | Gắn **từng câu thoại với tên nhân vật** ngay trong prompt; đã gắn giọng vào Element thì **không tả lại giọng** trong prompt | khớp luật "luôn nêu ai nói" ở `knowledge/seedance_director_workflow.md` |
| Khung đầu–cuối | Có "Start & End Frames-to-Video" | có |

- 驯服指南 (bản cộng đồng của tài liệu chính thức, [20]): công thức `主体(描述) + 运动 + 场景 + (镜头语言 + 光影 + 氛围)`; phần trong ngoặc là
  tùy chọn; nhắc mô tả "rõ nhưng không quá phức tạp" vì clip 5–10 s. Bản 3.0 (bài tổng hợp [21], dẫn lại hướng dẫn prompt) thêm **声音 (âm thanh)**
  làm thành phần thứ 6 và khuyên "viết như lời chỉ đạo của đạo diễn, không chồng từ khóa".
- Thử thật của 量子位 [22] (1 người thử, 2026-02-07): Multi-Shot tự động cho 6–7 shot / 10 s, hiểu ngôn ngữ máy tốt; **điểm yếu: chia thoại
  giữa các nhân vật chưa chuẩn**, chế độ tự viết shot "phức tạp, kết quả không ổn định". Độ tin: vừa (1 người thử, không có số lần thử).
- **Điều kiện dùng cho pipeline:** thoại tiếng Việt → Kling 3.0 không nói được (theo danh sách chính thức) → nếu dùng Kling thì thoại vẫn là
  TTS ghép sau; phần "Element Binding giọng" không áp dụng. Chưa xác minh ClipAI mở Kling bản nào (cần xem `https://clipai.ingarena.net/docs/`).

## 2. Người làm nghề có tên / được phỏng vấn trực tiếp

| Ai | Làm gì | Điều họ nói (tóm lời mình; trích ≤ 15 chữ) | Hoàn cảnh / giới hạn | Nguồn |
|---|---|---|---|---|
| **陈坤 (闲人一坤)**, đạo diễn 《山海奇镜之劈波斩浪》 (5 tập, 快手 + 可灵, 10 người, ~2 tháng) | Bản trailer đầu: ChatGPT → Midjourney → PixVerse, 10 ngày ra 1:49; bản chính làm lại bằng 可灵 | Chọn truyện **đơn giản, ít diễn xuất người** vì giới hạn công nghệ lúc đó; sức hút câu chuyện là trụ chính — "故事吸引力是内容效果的主力支撑" | 2024–2025, kỳ ảo (quái thú, cảnh lớn) — thể loại né được điểm yếu diễn xuất | [23][24] |
| **金云水, 王帅帅** (ĐH Đồng Tế), phê bình 《山海奇镜》 | Đánh giá | Điểm mạnh: cảnh kỳ ảo "堪比大片"; điểm yếu: "口型对不上、微表情缺失", tương tác người–vật–quái thú thiếu | Bài phê bình học thuật ngắn, 2025-02-24 | [25] |
| **陈妍** (tên giả), 抽卡师 ở công ty AI短剧 làm cho thị trường nước ngoài | Quy trình: đọc kịch bản → thiết kế nhân vật/cảnh 3 góc → chia phân cảnh **theo nhóm 15 s** → viết prompt (hành động, biểu cảm, vị trí, cảnh, máy) → gen 4–15 lần/clip → ghép sơ bộ gửi đạo diễn | Đa số cảnh 2–3 lần gen, cảnh phức tạp 10+; người giỏi 4 lần cho 5 s, trung bình 10; điểm AI không làm được: "它理解不了你的人物关系" | 潮新闻 phỏng vấn, 2026-09; số liệu 1 người | [26][27] |
| **张强** (tên giả), 8 năm sản xuất ở Hengdian → AI | Nhận xét | Làm một cảnh mở cửa có thể gen **~500 clip** rồi chọn khung tự nhiên nhất; AI thuộc công thức nhưng không hiểu vì sao một ánh mắt làm người xem khóc | 虎嗅, 2026-04-29; con số 500 là giai thoại 1 cảnh, không phải trung bình | [28] |
| DataEye (qua 潮新闻) | Số liệu ngành | 98,7% dự án AI短剧 không hòa vốn sau 6 tháng | Số liệu ngành, không rõ phương pháp | [26] |

**Điều rút ra (có điều kiện):**
1. **Chọn chuyện theo điểm mạnh của model** (陈坤): kỳ ảo / cảnh lớn / ít diễn tinh tế thì AI hợp; cận mặt diễn vi biểu cảm + khớp môi là điểm yếu
   được nhiều nguồn độc lập nói (đạo diễn [23], phê bình [25], 抽卡师 [27], thử Kling [22]) → **đồng thuận ≥ 3 nguồn độc lập = độ tin khá**. Khớp với
   kinh nghiệm dự án: #8/#10 khó nhất đúng là cận mặt thoại (S4.6).
2. **Đơn vị lập kế hoạch = nhóm ~15 s** (陈妍) — trùng giới hạn 15 s của Seedance 2.5 và Kling 3.0: người làm chia truyện thành các "khối gen" trước
   khi viết prompt. Pipeline hiện chia theo cảnh → shot; chưa có khái niệm "khối gen 15 s gồm nhiều shot liền" (xem gợi ý T3).
3. **"Cảnh xịn" = gen nhiều rồi chọn**, không phải một prompt thần kỳ: 2–3 lần là thường, 10+ cho cảnh khó, cá biệt hàng trăm. Nghĩa là chất lượng
   phụ thuộc **ngân sách lần gen cho cảnh then chốt** + **mắt chọn** (con người hoặc QC). Điều kiện: dự án này có trần chi và luật "gen lại ≤ 2 lần
   phải đổi đầu vào" (CHUAN_XAY_DUNG) → không bắt chước "500 lần"; thay vào đó dồn ngân sách vào vài shot then chốt (xem T4).
4. Người làm nói AI **không hiểu quan hệ nhân vật** → quan hệ (ai nhìn ai, ai sợ ai, ai đứng gần ai) phải được viết ra bằng **hành vi nhìn thấy**
   trong prompt — khớp với luật đang có ở `knowledge/roles/director.md` (chỉ đạo bằng hành vi, không bằng nhãn cảm xúc).

## 3. WaytoAGI — cấu trúc kịch bản phân cảnh (trang "Chat with Wiki", tổng hợp từ kho WaytoAGI) [29]

- Prompt nhờ LLM viết phân cảnh = **tổng thời lượng + số shot + nội dung mỗi shot + yêu cầu định dạng**; bảng phân cảnh có cột cảnh / cỡ cảnh /
  thời lượng / chuyển động máy / nội dung hình / thoại–lời dẫn / **nhạc–âm hiệu**; ví dụ quảng cáo 30 s ≈ 10 shot (~3 s/shot).
- Độ tin: vừa–thấp (câu trả lời máy tổng hợp từ wiki cộng đồng, không có tác giả). Ghi nhận: **cột nhạc/âm hiệu nằm ngay trong bảng phân cảnh** —
  âm thanh được lên kế hoạch cùng hình, giống ý `core/sound_intent.py` (Đ9).

## 4. Luật mới ở Trung Quốc (bối cảnh, không phải kỹ thuật) [30]

- 《微短剧发展管理办法》 (广电总局, hiệu lực **2026-09-01**): tác phẩm làm bằng AI phải "在每集明显位置添加提示标识" (nhãn nhắc ở vị trí rõ trong
  **mỗi tập**); bài tổng hợp khác nói thêm siêu dữ liệu truy vết. Áp dụng khi phát hành ở TQ; dự án FF phát ở VN — **chỉ ghi nhận**, không đổi gì.
  Nhưng là lý do để có tùy chọn "nhãn AI" ở khâu xuất nếu sau này phát hành đa thị trường (gợi ý T6, việc của người dùng quyết).

## 5. Đối chiếu với pipeline + gợi ý kiểm được (KHÔNG sửa code trong việc này)

Đã đọc: `knowledge/seedance_prompting.md` (dòng 50: "Seedance không dùng multi-shot có cấu trúc như Kling"), `knowledge/roles/dp.md` (dòng 101:
"Kling multi-shot: chỉ ảnh đầu nhóm bám nhân vật", 114: từ vựng Kling từ blog), `prompts/03_video_motion.md` (Kling: câu ngắn),
`knowledge/video_motion_vocab.md` (dòng 3: còn chờ "đối chiếu hướng dẫn chính thức của Kling").

| # | Gợi ý | Căn cứ | Cách kiểm (đo được) | Chi phí |
|---|---|---|---|---|
| T1 | Cập nhật `video_motion_vocab.md` / `dp.md`: đánh dấu đã đối chiếu tài liệu chính thức Kling 3.0 (Multi-Shot tự động vs tự viết, Element Binding, giới hạn 15 s, **không tiếng Việt**) — kèm ghi rõ nhận xét dp.md:101 là quan sát ở **bản Kling cũ qua ClipAI** (GĐ6 R4), có thể khác ở 3.0 | [19] chính thức | test đọc file: chuỗi "Kling 3.0" + ngày đối chiếu có trong vocab; dòng 3 hết chữ "cần … đối chiếu" | 0 |
| T2 | Khi cảnh chọn Kling và có ≥ 2 người nói: prompt phải gắn tên nhân vật trước mỗi câu thoại (dù thoại do TTS, để model diễn đúng người đang nói) | [19] + điểm yếu chia thoại [22] | lint prompt (kiểu `motion_prompt_lint`): shot Kling có `dialogue` nhiều người mà câu không có tên → cảnh báo; test đơn vị | 0 |
| T3 | Thử khái niệm **"khối gen ~15 s"**: DP gom các shot liền nhau cùng nơi/cùng người thành 1 lần gọi Multi-Shot (Kling 3.0 / Seedance 2.5) thay vì 1 lần gọi / shot | [26][27] + giới hạn 15 s [19][1] | A/B trên 1 cảnh #10: cùng 3 shot, (a) 3 lần gọi, (b) 1 lần Multi-Shot; đo: nhất quán nhân vật (QC lớp 0), số lần gen lại, USD | **tốn tiền** — cần người dùng duyệt + ước tính trước |
| T4 | "Ngân sách lần gen theo độ quan trọng": shot ⭐ (hero/cao trào) được phép 2 lần gen song song để chọn; shot phụ 1 lần | [26][27][28]; giữ luật ≤ 2 lần đổi đầu vào | số liệu sổ chi: tỉ lệ USD dồn vào shot ⭐; phiếu người xem chấm shot ⭐ trước/sau | tốn tiền khi chạy — chỉ ghi đề xuất |
| T5 | Trong bước Director chọn truyện / thể loại: ghi nhận xét "cận mặt diễn tinh tế + khớp môi là điểm yếu chung" như **một điều kiện cân nhắc** (không cấm) — ví dụ ưu tiên kể bằng hành động/không gian ở đoạn đòi vi biểu cảm, hoặc dồn ngân sách khớp môi vào 1–2 câu then chốt | ≥ 3 nguồn độc lập [22][23][25][27] + #8/#10 | test prompt Director có câu điều kiện; theo dõi #11: số shot cận mặt thoại / tổng shot, tỉ lệ gen lại của nhóm đó | 0 (sửa kiến thức) |
| T6 | Tùy chọn "nhãn nội dung AI" ở khâu xuất (tắt mặc định) | [30] | test: bật cờ → khung đầu mỗi video có nhãn; tắt → không | 0 — **chờ người dùng quyết**, không làm tự ý |

## 6. Còn thiếu sau lượt 2
- Chưa đọc trọn trang WaytoAGI gốc (chỉ câu trả lời tổng hợp); chưa có tài liệu 即梦 chính thức riêng cho video (trang tài nguyên chính thức chỉ có
  hướng dẫn prompt ảnh) — 即梦 video dùng chung Seedance nên lượt 1 [1] vẫn là căn cứ chính.
- Chưa có phỏng vấn **biên kịch** AI短剧 có tên thật (mới có đạo diễn + 抽卡师 tên giả).
- Chưa có số đo "tỉ lệ shot dùng được" từ nhiều đội (mới 1 người: 2–3 lần thường, 10+ cảnh khó).
