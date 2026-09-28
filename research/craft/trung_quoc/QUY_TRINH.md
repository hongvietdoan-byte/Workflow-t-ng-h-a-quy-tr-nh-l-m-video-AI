# Quy trình sản xuất AI短剧 ở Trung Quốc (S phiên 2026-09-29)

> Theo `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md`: đây là **kỹ thuật/tư liệu** (tầng 3) — cách các đội TQ hay làm, **không phải
> luật bắt buộc** cho pipeline của mình. Số trong ngoặc vuông dẫn về `NGUON_TQ.md`. [suy luận] = phần người viết báo/blogger
> suy luận hoặc khái quát hoá, không phải số đo trực tiếp.

## 1. Chín giai đoạn (khung 2026, tổng hợp nhiều đội)

Không có một "chuẩn ngành" duy nhất — các nguồn mô tả khác nhau tuỳ quy mô đội. Khung phổ biến nhất (đối chiếu [5][7][8][9]):

1. **Lập dự án / chọn đề tài** — chọn thể loại theo xu hướng nền tảng (phục thù đổi đời, tổng tài ngọt sủng, xuyên không hệ
   thống…) [9][11].
2. **Kịch bản hoá** — dùng LLM (豆包/DeepSeek/ChatGPT) sinh outline + logline + nhân vật + mâu thuẫn + điểm phản转; người viết
   sửa lại cho chặt [5][7][8][10].
3. **Kho tài sản nhân vật/cảnh** (角色/场景资产库) — chốt ngoại hình, trang phục, đạo cụ nhân vật; chốt bố cục không gian cảnh
   *trước khi* sinh video, không sinh video rồi mới lo nhất quán [9][14].
4. **Phân cảnh / storyboard** (分镜脚本) — mỗi shot ghi: số thứ tự, thời lượng, cỡ cảnh, nội dung hình, hành động, thoại, gợi ý
   âm thanh [8][10]. Nhiều đội giới hạn 2–8 giây/shot, tổng 60–90 giây/tập đầu [8][10].
5. **Sinh ảnh tĩnh** (text-to-image) cho từng shot/nhân vật/cảnh — MidJourney, Flux, 即梦, Stable Diffusion [5][7].
6. **Sinh video** (image/text-to-video) — 即梦 Seedance, 可灵 Kling, Vidu, Runway — thường theo từng shot ngắn (5–10 giây)
   [5][7][8].
7. **Lồng tiếng / khớp môi / âm nhạc** — TTS + lip-sync tự động, nhạc nền AI (Suno và tương đương TQ) [5][7][9]. (Xem thêm
   `NHAC_NEN.md`.)
8. **Dựng (hậu kỳ)** — 剪映 CapCut: nối cảnh, chuyển cảnh, phụ đề tự động, chỉnh màu, xuất bản [5][7][8].
9. **QC → Phát hành → Đo dữ liệu → Lặp lại** — theo dõi tỷ lệ xem hết tập, chuyển đổi trả phí, sửa điểm yếu ở tập sau [9][11].

**[suy luận]** Thứ tự 3 (kho tài sản) đặt *trước* bước 4–6 là điểm khác với cách làm "sinh ảnh rồi mới lo nhất quán" của người
mới — nguồn [7][14] đều nhấn mạnh chuẩn bị kho tham chiếu trước là nguyên nhân chính giảm số lần sinh lại.

## 2. Vai trò con người vs AI

Không tìm được nguồn mô tả sơ đồ tổ chức chi tiết cho một đội cụ thể (không có nguồn kiểu "phỏng vấn trưởng phòng sản xuất
liệt kê từng chức danh"). Điểm chung rút ra từ [5][9] [suy luận, mức độ khái quát]:
- Đội có thể co giãn từ **1 người** (làm hết, dùng AI cho toàn bộ khâu kỹ thuật) đến **~10 người** cộng tác từ xa khi lên quy
  mô — nguồn [5] mô tả case cụ thể: bắt đầu 1 đạo diễn, sau đó có "10+ người cộng tác online" trong 2 tuần.
- Nguyên tắc phân công được [9] nêu (qua tóm tắt, chưa đọc trọn bài gốc — độ tin vừa): việc cần **sáng tạo, phán đoán, cảm
  xúc, tuân thủ pháp lý** do người làm; việc **lặp lại, cơ giới, chuẩn hoá, tốn tính toán** giao AI (soạn kịch bản nháp, format
  phân cảnh, dựng nhân vật số, hiệu ứng cảnh, lồng tiếng tự động, dựng thô, chỉnh màu, sản xuất tài sản hàng loạt).
- "Đạo diễn" trong một số công cụ (ví dụ "天工短剧工作台" [9]) được triển khai như **AI agent lập vị trí nhân vật/góc máy dựa
  vào quan hệ cốt truyện, tham chiếu bố cục shot trước để sinh vị trí cho shot sau** — tức là một phần công việc đạo diễn hình
  ảnh được đóng gói thành công cụ, không còn là 1 người ngồi quyết từng khung hình. **[suy luận]** đây là mô tả tính năng sản
  phẩm qua bài PR, cần kiểm chứng thêm nếu dùng làm căn cứ chọn công cụ.

## 3. Công cụ theo khâu (liệt kê thấy trong nguồn, không phải khuyến nghị)

| Khâu | Công cụ được nhắc tới | Nguồn |
|---|---|---|
| Kịch bản / LLM | 豆包 (Doubao), DeepSeek, ChatGPT, 文心一言 | [5][7][8] |
| Ảnh tĩnh | 即梦 (Jimeng), MidJourney V7, Flux/Flux Kontext, Stable Diffusion | [5][7] |
| Video | 即梦 Seedance 2.0/2.5, 可灵 Kling (2.1/3.0), Vidu, 海螺 Hailuo, Runway | [5][7][8] |
| Dựng | 剪映 CapCut, DaVinci Resolve | [5][7][8] |
| Nhạc/âm thanh | Suno, Udio, và các công cụ TQ tương đương (Seed Audio, các nền tảng nhạc bản quyền cho short drama) | [5][16][17] — xem `NHAC_NEN.md` |
| Nhất quán nhân vật (kỹ thuật nền, không phải ClipAI) | LoRA/Dreambooth (huấn luyện ~20 ảnh góc khác nhau), IP-Adapter, ComfyUI workflow | [15] (snippet only) |

**Ghi chú quan trọng cho pipeline của mình**: các công cụ trên là của thị trường TQ nói chung, khác với ClipAI (nền tảng đang
dùng) — ClipAI có cách làm chính thức riêng cho nhất quán nhân vật (**kho chủ thể**, xem `docs/CAP_NHAT_CLIPAI_2026-09-28.md`),
không cần huấn luyện LoRA. Không tự ý chuyển sang LoRA/ComfyUI chỉ vì thấy phổ biến ở TQ.

## 4. Nhất quán nhân vật / cảnh / giọng — 3 phương pháp cụ thể [14]

*(nguồn cá nhân, độ tin vừa — 1 cách làm, không phải chuẩn ngành, nhưng logic hợp lý và có thể đối chiếu với ClipAI)*

1. **Thẻ hồ sơ nhân vật điện ảnh** (角色资料卡): không chỉ đưa 1 ảnh tham chiếu, mà gộp "mô tả văn bản nhân vật" (ngoại hình +
   trang phục + đạo cụ + tính cách + thân phận) + ảnh tham chiếu → sinh ra 1 tấm ảnh tổng hợp gồm ảnh chính diện toàn thân,
   bán thân trái/phải, cận trang phục, cận mặt, nền trắng thuần, không đổ bóng. Dùng tấm này làm ảnh tham chiếu chính cho mọi
   shot sau, thay vì chỉ 1 ảnh mặt.
2. **Lưới 9 ô không gian cảnh** (空间九宫格): trước khi sinh video, sinh 1 ảnh nhìn từ trên xuống (top-down) định vị cửa/cửa
   sổ/vị trí nhân vật trong không gian, rồi từ đó sinh 9 góc khác nhau (toàn cảnh, trung cảnh, cận, góc thấp, góc cao, góc
   phản...) giữ nguyên kết cấu kiến trúc/đồ đạc — để khi đổi góc máy giữa các shot, AI không "tưởng tượng lại" không gian mỗi
   lần.
3. **Khoá giọng bằng đoạn tham chiếu 3–5 giây**: tách giọng từ 1 đoạn video ưng ý trước đó (ví dụ bằng công cụ tách tiếng của
   CapCut), cắt câu ngắn rõ nhất, dùng làm file âm thanh tham chiếu cho các lần sinh sau, kèm câu prompt "giọng nhân vật tham
   chiếu @âm thanh 1, giữ nguyên âm sắc/tốc độ/giọng điệu".

**Đối chiếu với ClipAI/Seedance chính thức**: tài liệu Seedance 2.5 [1] xác nhận cùng logic ở mức nguyên tắc — "参考类（多素材
映射）" khuyên liệt kê rõ ánh xạ ảnh/video/audio ↔ nhân vật khi có nhiều chủ thể, và mục lỗi "角色对应错误" khuyên **tải tham
chiếu theo đúng thứ tự xuất hiện lần đầu của nhân vật** để tránh AI gán nhầm người. Đây là điểm khớp giữa nguồn cộng đồng [14]
và nguồn chính thức [1] — độ tin cao hơn khi 2 nguồn độc lập đồng thuận.

## 5. Chi phí & thời gian (số liệu, không phải ước tính của mình)

| Chỉ số | Số liệu | Nguồn | Ghi chú |
|---|---|---|---|
| Chi phí/phút, AI漫剧 (hoạt hình) 2026 | ≈ 1.000 NDT/phút (giảm từ 15.000 NDT/phút tháng 8/2024) | [6] | Lingju Animation, đơn vị đầu ngành |
| Chi phí/phút, AI真人短剧 (người thật giả lập) | 2.000–6.000 NDT/phút, hàng cao cấp >10.000 NDT/phút | (WebSearch tổng hợp, chưa gắn nguồn cụ thể) | độ tin thấp — số tổng hợp lặp lại nhiều bài |
| Tổng chi phí 1 bộ AI短剧 ~100 phút | ≈ 30 vạn NDT (300.000 NDT) so với truyền thống tương đương | (WebSearch tổng hợp) | thấp |
| Case cụ thể: 50 tập, 7 ngày quay xong | 8 vạn NDT chi phí, thu 320 vạn NDT | [17] | nguồn quảng cáo công cụ nhạc — số liệu case có thể chọn lọc để PR, cần thận trọng |
| Case cụ thể: kịch bản+phân cảnh+dựng 1 bộ 3-5 phút | ≈ 1.800–2.000+ NDT (chưa gồm nhân công hậu kỳ) | [7] | tác giả tự tính từ giá dịch vụ đang dùng (即梦/可灵) |
| Tốc độ sản xuất đầu ngành | tới 20 tập/ngày cao điểm, ~100 tập/tháng bình thường | [6] | Lingju Animation |
| Thời gian từ kịch bản → giao bản AI真人短剧 | 35–40 ngày (kịch bản phức tạp thì dài hơn) | (WebSearch tổng hợp) | thấp |
| Thời gian AI漫剧 | ~20 ngày | (WebSearch tổng hợp) | thấp |
| Tỷ lệ sinh lại (retry rate) | 8/2025: 10–20 lần/cảnh → 12/2025: 1–2 lần/cảnh (do model cải thiện) | [6] | Yicai, phỏng vấn ngành |
| ROI mua traffic (buy volume) | ổn định 1,05–1,2 lần, thấp hơn benchmark thương mại điện tử; chỉ ~20% phim đầu ngành có lãi | [6] | Yicai — cho thấy hạ chi phí sản xuất KHÔNG đồng nghĩa dễ có lãi |

**[suy luận] Bài học chi phí quan trọng nhất**: nhiều nguồn PR (case 1 bộ phim lãi lớn) không đại diện cho toàn ngành — nguồn
độc lập nhất [6] (báo kinh tế, phỏng vấn nhiều bên) cho thấy đa số đội **không** có lãi dù chi phí sản xuất đã giảm mạnh, vì
chi phí mua traffic/quảng cáo mới là biến số quyết định, không phải chi phí sản xuất AI.

## 6. QC — kiểm soát chất lượng

Không có nguồn mô tả một quy trình QC chính thức, có tên tuổi, chi tiết theo bước. Các gợi ý rải rác từ [5][7][8]:
- Xem trước (preview) từng shot trước khi render hàng loạt (batch render) — sửa mô tả rồi sinh lại từng shot lỗi thay vì render
  lại cả mẻ [8].
- Kiểm 3 điểm sau khi có video thô: nối cảnh có mượt không, hành động có khớp thoại/lipsync không, chất lượng hình có đạt
  chuẩn không [8].
- Case [6] cho thấy chất lượng model cải thiện nhanh (10–20 lần retry → 1–2 lần trong 4 tháng) — nghĩa là quy trình QC/ngưỡng
  chấp nhận cũng đang thay đổi nhanh, số liệu cụ thể dễ lỗi thời.

## Khoảng trống / câu hỏi còn mở
- Chưa có nguồn mô tả sơ đồ tổ chức/chức danh cụ thể của 1 studio TQ làm AI短剧 (vd: có "prompt engineer" riêng không, ai
  duyệt kịch bản cuối, ai QC).
- Chưa đọc được tài liệu Kling chính thức (trang không tải nội dung) — quy trình camera/nhất quán nhân vật của Kling riêng
  chưa xác minh được.
- Số liệu chi phí "chuẩn ngành" mâu thuẫn nhau giữa các nguồn snippet-only (2.000–15.000 NDT/phút tuỳ nguồn/thời điểm) — nên
  coi là khoảng dao động rộng, không phải con số cố định.
