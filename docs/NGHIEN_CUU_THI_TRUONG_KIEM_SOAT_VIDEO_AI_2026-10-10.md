# Nghiên cứu: quy trình công cụ video AI trên thị trường so với kế hoạch kiểm soát (10/10/2026)

Người dùng hỏi (câu 6, mục 9c kế hoạch): "Các tool/web làm video AI trên thị trường có khâu kiểm như mình không? Họ chỉ viết tay, tại sao
lại chuẩn hơn hệ thống?" Agent nghiên cứu độc lập (chỉ đọc web + repo). Lưu ý độ tin cậy: mô tả công cụ thương mại phần lớn từ trang hãng /
bên thứ ba; chưa lấy được tài liệu chính thức Kling, Seedance, Krea; trang Sora trả 403 (dẫn qua arXiv); số "gen bao nhiêu lần/shot" chỉ
từ một nhà bán (Invideo).

## 1. Quy trình từng công cụ

| Công cụ | Bảng shot cấu trúc | Prompt | Giữ nhất quán | Kiểm tự động / người duyệt |
|---|---|---|---|---|
| LTX Studio | Có: kịch bản → cảnh → shot, sửa/gộp/tách trước render | AI viết, người sửa | "Elements" (nhân vật/vật/nơi) gắn mọi shot; IC-LoRA pre-viz | Người duyệt bảng; không thấy QC tự động — [ltx.studio](https://ltx.studio/blog/ltx-storyboard-generator-update), [ltx.io](https://ltx.io/blog/how-to-build-a-complete-pre-visualization-pipeline) |
| Runway Gen-4 | Không | Tay; "thrives on prompt simplicity", câu khẳng định, tránh phủ định | ≤ 3 ảnh tham chiếu có nhãn | Không thấy — [help.runwayml.com](https://help.runwayml.com/hc/en-us/articles/39789879462419) |
| Google Flow / Veo | Scenebuilder, Extend / Jump To | Veo BẬT bộ viết lại LLM mặc định (`enhancePrompt`) | "Ingredients" @; khung đầu/cuối | Không thấy — [Vertex](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/turn-the-prompt-rewriter-off), [Flow](https://support.google.com/flow/answer/16353334?hl=en) |
| OpenAI Sora | Storyboard Sora 2 (beta, Pro) | GPT mở rộng prompt ngắn; "gen nhiều rồi chọn" | không rõ | Người chọn — [arXiv 2402.17177](https://arxiv.org/pdf/2402.17177), [fal.ai](https://fal.ai/learn/devs/how-to-write-prompts-sora-2) |
| Kling O1 / 3.0 | "AI Multi-Shot" (nguồn phụ) | Tay, @Image1… | Elements, Character ID | Không thấy — [scenario](https://help.scenario.com/articles/3906786894-kling-o1-family-the-essentials) |
| Luma Ray3 | Không | — | — | Nháp rẻ nhanh 5–20× rồi nâng 4K; tự nhận "tự đánh giá nháp" (chưa kiểm độc lập) — [lumalabs.ai](https://lumalabs.ai/news/ray3) |
| Higgsfield Popcorn | ≤ 8 khung, tay/tự động | Tay / sinh | ≤ 4 ảnh tham chiếu; Soul ID | Không thấy — [help](https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-popcorn) |
| Katalist | Kịch bản → nhân vật/cảnh/hành động | Sinh | Kho diễn viên | Không thấy — [katalist.ai](https://katalist.ai/) |
| Invideo AI | Agent viết toàn bộ | Sinh, người xem trước | — | "Always Ask": người duyệt trước khi tốn credit — [invideo](https://invideo.io/faq/what-is-a-prompt-first-review-workflow-for-ai-video/) |
| Flora / Freepik Spaces / Firefly Boards | Bảng nút | Nút Assistant biến đổi prompt | Ảnh tham chiếu người đặt | Không thấy |
| ComfyUI cộng đồng | Không | Tay | Bảng nhân vật + IPAdapter/PuLID/InstantID + LoRA | Không |
| MovieAgent (NUS 2025) | Nhiều agent đạo diễn/biên kịch/storyboard | Sinh | Ngân hàng ảnh nhân vật | Tác giả tự báo — [2503.07314](https://arxiv.org/html/2503.07314v1) |
| FilmAgent (2025) | Sân khấu Unity 3D dựng sẵn | Sinh | Môi trường 3D cố định | Critique-Correct-Verify kịch bản + Debate-Judge máy; người chấm 3,98/5 — [2501.12909](https://arxiv.org/html/2501.12909v1) |
| Studio làm thật | — | — | — | ~3 lần gen / shot dùng được, chọn ~25 % (41/164 clip) — nguồn tiếp thị [invideo](https://invideo.io/faq/how-many-ai-video-generations-do-you-need-per-usable/) |

**Tóm lại:** thị trường giữ nhất quán bằng ẢNH THAM CHIẾU có tên gắn từng shot (Elements, Ingredients, @tag, LoRA), không bằng chữ;
người duyệt ở bảng shot và ở bước chọn bản gen. **Không tìm thấy** công cụ thương mại nào công bố kiểm gói tự động trước gen hay QC theo
từng ý sau gen.

## 2. Prompt viết tay hay sinh / mở rộng tự động
- Mở rộng prompt là chuẩn của nhà làm model: DALL-E 3 ([paper](https://cdn.openai.com/papers/dall-e-3.pdf)), Sora, Veo — vì prompt người
  dùng ngắn, khác kiểu chú thích lúc huấn luyện.
- Sinh tự động THẮNG ở độ đẹp: Promptist ([2212.09611](https://arxiv.org/pdf/2212.09611)); Prompt-A-Video thẩm mỹ VBench 0,522 → 0,639
  ([2412.15156](https://arxiv.org/pdf/2412.15156)).
- THUA ở độ khớp ý: WebVid prompt gốc 3,116 vs GPT-4o viết lại 3,079; RAPO (CVPR 2025): viết lại tự do "thêm chi tiết sai hoặc mơ hồ",
  chỉ làm dài hơn là không đủ ([CVPR](https://openaccess.thecvf.com/content/CVPR2025/html/Gao_The_Devil_is_in_the_Prompts_Retrieval-Augmented_Prompt_Optimization_for_CVPR_2025_paper.html)).
- Không tìm thấy nghiên cứu so "prompt chuyên gia viết tay" với "prompt sinh từ bảng cấu trúc" cho video có nhân vật + ảnh tham chiếu.

## 3. VLM làm giám khảo — hướng "tách ý → hỏi từng ý → code kết luận"
- Đúng hướng, đã chuẩn hóa: TIFA / DSG / VQAScore. DSG (ICLR 2024): câu hỏi nguyên tử, ĐỒ THỊ PHỤ THUỘC (hỏi "có xe máy" trước "xe màu gì")
  ([2310.18235](https://arxiv.org/abs/2310.18235)); VQAScore khớp người hơn CLIPScore 62,3 vs 50,8 ([2406.13743](https://arxiv.org/pdf/2406.13743)).
- Điểm yếu đo được: trái/phải VLM ~56 % vs người 99 % ([What's Up](https://aclanthology.org/2023.emnlp-main.568)); GPT-4V thua bộ phát hiện
  vật ở màu, vị trí, đếm ([T2I-CompBench++](https://arxiv.org/html/2307.06350v3)); GenEval chấm vị trí bằng khung bao bộ phát hiện
  ([2310.11513](https://arxiv.org/pdf/2310.11513)).
- Video: MLLM gần người ở tường thuật + chuyển động, chất lượng hình r 0,345 vs người 0,705 ([Co-Director 2604.24842](https://arxiv.org/pdf/2604.24842));
  VBench-2.0 trộn VLM + công cụ chuyên dụng cho vật lý ([2503.21755](https://arxiv.org/html/2503.21755v2)).
- → N4 khớp DSG; trái/phải, đếm, hình học phải để code / bộ phát hiện quyết.

## 4. Vì sao viết tay trong công cụ đơn giản thường "chuẩn hơn"
1. **Vòng nhìn–sửa ngay + chọn bản tốt nhất** (~25 % clip dùng được; Video-T1 ICCV 2025: nhiều ứng viên + bộ kiểm luôn tăng chất lượng,
   model 2B có tìm kiếm tiệm cận 13B — [Video-T1](https://openaccess.thecvf.com/content/ICCV2025/papers/Liu_Video-T1_Test-time_Scaling_for_Video_Generation_ICCV_2025_paper.pdf)).
   Người viết tay có bộ kiểm là con người nhìn ảnh thật.
2. **Prompt ngắn, đúng "ngôn ngữ" model** (Runway đơn giản + khẳng định; Seedance 50–100 từ, ý chính đầu; Flow một hành động/shot).
3. **Prompt dài nhồi nhiều ý thì hỏng**: DetailMaster — mọi model kém dần khi prompt dài, gắn thuộc tính/không gian ~50 %
   ([2505.16915](https://arxiv.org/html/2505.16915v2)); đúng kiểu lỗi #24 (nối câu dần rồi mâu thuẫn).
4. **Viết lại tự động thêm chi tiết chưa kiểm** (RAPO); câu phủ định có thể gây đúng điều bị cấm.
5. **Ảnh tham chiếu ít mà có vai rõ** (Popcorn ≤ 4, Runway ≤ 3); nhiều ảnh xung đột kéo lệch (suy luận, khớp ca ảnh mẫu Kho #24).

## 5. Kết luận cho kế hoạch
**(a) Thị trường làm, kế hoạch chưa có:** gen nhiều phương án rẻ rồi chọn (ở khâu ảnh); ngân sách độ dài / số ý prompt theo model; nhân
vật/vật giao hẳn cho ảnh tham chiếu có tên, chữ chỉ lo hành động; người duyệt bảng shot có hình xem trước.
**(b) Kế hoạch có, thị trường chưa công bố:** kiểm gói trước khi trả tiền bằng code (hình học 3D, vai ảnh, dấu vân tay); model khai enum,
code kết luận; Sổ Làm ↔ Kiểm + ca vàng. Lợi thế chưa ai chứng minh, đồng thời là chi phí độ phức tạp.
**(c) Đề xuất sửa kế hoạch:**
1. **Sửa N2: Đạo diễn viết tay câu chính theo ngữ pháp model; BYĐ là thước kiểm** — code dùng kiểu DSG kiểm câu có phủ các ý BYĐ không, chỉ
   chèn ngắn ý còn thiếu; giữ so A/B ≤ 1 USD.
2. **Ngân sách prompt theo model** (số từ, ý chính đầu, một hành động/shot, chỉ câu khẳng định — đổi 'không được có' thành mô tả dương);
   vượt ngân sách → đỏ.
3. **Gen N bản rẻ → chọn** cho ảnh khung đầu (2–4 bản thấp → QC theo ý → chọn → nâng) — tốn tiền, người dùng duyệt.
4. **QC ④/⑥ theo DSG**: ý nguyên tử + đồ thị phụ thuộc + gắn loại.
5. **Trái/phải, đếm, vị trí không giao VLM** — YuNet / bộ phát hiện + `stage_facts` quyết; không đo được → vàng.
6. **QC video: VLM chỉ chấm tường thuật + chuyển động**; lỗi hình / vật lý dùng công cụ chuyên dụng hoặc người; không chặn tự động theo
   "chất lượng hình".
7. **Ảnh tham chiếu kiểu Elements**: bộ tham chiếu chuẩn mỗi nhân vật/vật (trước, 3/4, nghiêng), gọi bằng tên; trần số ảnh mỗi gói; chữ
   không tả lại ngoại hình ảnh đã giữ.
8. **Người duyệt ở bảng có hình**: duyệt BYĐ kèm xem trước rẻ (render sân khấu 3D / ảnh nháp), không duyệt chữ.
