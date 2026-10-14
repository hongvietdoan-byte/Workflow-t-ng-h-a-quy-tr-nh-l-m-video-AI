# Thử D6 trên Dashboard — cảnh one-shot Tháp Đồng Hồ (14/10/2026, người dùng giao; PHIÊN MỚI trên MÁY CHÍNH làm)

Mục đích: kiểm chứng D6 "đường như chat" (`docs/DANH_GIA_VAI_DAO_DIEN_2026-10-14.md` mục 3b–3d, cờ `chat_prompts`) bằng một dự án THỬ thao
tác trực tiếp trên Dashboard 8501: cùng kịch bản + cùng kế hoạch shot của Đạo diễn, **bản A gửi prompt CŨ (code ghép)**, **bản B gửi prompt D6**
(Claude nhìn đúng ảnh sẽ gửi viết lại) → người dùng so MÙ. KHÔNG phải tập 2; không đụng #27.

## 0. Điều kiện trước (làm theo thứ tự, dừng nếu thiếu)
1. **Gộp PR #15** (code D6) vào main — người dùng gộp. `git pull` ở `D:\AI-Video-Pipeline`, khởi động lại 8501 + 8502, cả bộ test Windows
   `py -m pytest -q -n 8 -p no:cacheprovider` (M0).
2. **M1 xong**: ảnh tường keo skin thang máy ĐÃ DUYỆT `D:\AI-Video-Output\2026-09-30_tai_san_toi_uu\gloowall_ob55_trien_khai_1.png` ở **Kho #367**
   nhãn "triển khai", sort = 0 (tường keo TĨNH, xuất hiện ngay khi đặt — luật người dùng 14/10, KHÔNG có hiệu ứng mọc).
3. Kho có: Kelly (dáng thường, giày trắng), SKORP (ảnh tỉ lệ #433–#436: ≈ 3 đầu, cầm HAI tay), Tháp Đồng Hồ **#263** có mô hình 3D (tháp mảnh
   chóp nhọn, KHÔNG mặt đồng hồ). Thiếu gì → báo người dùng, không đoán.
4. Sao lưu `data/manifest.sqlite` + `data/feature_settings.json` trước khi tạo dự án / đổi cờ.

## 1. Kịch bản (dán vào Bước 1 — dự án mới, tên "Thử D6 one-shot Tháp Đồng Hồ")
> **Cảnh 1 — Tháp Đồng Hồ, ban ngày (thế giới thực, Free Fire in-game).** Một cú máy liền (one-shot), không cắt.
> Kelly đứng ở **điểm A — chân cầu thang của Tháp Đồng Hồ**. Kelly chạy nhanh lên tới **điểm B — bậc cao nhất của cầu thang**. Tới nơi, Kelly
> **đặt bom keo**: tường keo (skin thang máy) xuất hiện ngay trước mặt. Kelly đứng sát, núp ở **bên trái** bức tường keo, ló ra ngó xem có địch
> không. Rồi Kelly **chạy tiếp 5 bước về bên trái**, **đặt bom keo thứ hai**, **ngồi xuống** sau tường, cầm **SKORP** bằng hai tay, thở ra — tỏ ra
> an tâm một chút.
> **Máy quay:** bắt đầu **phía trước Kelly** (Kelly chạy về phía máy, máy lùi theo); **khi Kelly tới điểm B, máy đi vòng ra phía sau** Kelly và
> giữ phía sau tới hết cảnh. Không thoại, không lời dẫn.

Không sửa câu chữ trên. Để **Đạo diễn tự chia** (có thể là một clip liền / một vị trí máy cắt sau / vài shot nối khung) — ghi lại cách Đạo diễn chia.

## 2. Thiết lập dự án
- Look FF_INGAME; ảnh **GPT Image 2.5**; video **Seedance 2.5**; tỉ lệ 9:16; chế độ **làm từng bước** (không chạy tự động — để bấm tay từng bước).
- Gắn Kho: Kelly, SKORP, Bom keo #367, Tháp Đồng Hồ #263. Chỗ đứng 3D: chọn trong gói bối cảnh #263 chỗ khớp **A = chân cầu thang**, **B = đỉnh
  bậc thang** (tên chỗ đứng xem trong gói; KHÔNG dùng `level_9_4` nếu không phải cầu thang). Không có chỗ đứng khớp → báo người dùng.
- Cờ giữ như máy chính đang bật; **`chat_prompts` TẮT** lúc làm bản A.

## 3. Quy trình so (thao tác trên Dashboard, ghi nhật ký + ảnh chụp màn ở `docs/handoff/THU_D6_NHAT_KY_<ngày>.md`)
1. **Bước 1 Đạo diễn** trên dự án A (báo giá Claude trước, hỏi người dùng). Duyệt Bible/kế hoạch như bình thường.
2. **🧬 Nhân bản dự án** (⚙ → "Nhân bản dự án", GIỮ hàng cảnh/shot = cùng kế hoạch Đạo diễn) → dự án **B** "Thử D6 … (B)".
3. **Bản A (cờ `chat_prompts` TẮT):** Bước 2 gen ảnh mọi shot của A (báo giá trước). KHÔNG vẽ lại / sửa tay — lấy lần gen ĐẦU để so.
4. Bật **`chat_prompts`** ở 🧪 (sao lưu `data/feature_settings.json`). **Bản B:** Bước 2 gen ảnh mọi shot của B (cùng ảnh tham chiếu; giá ảnh
   + D6 ≈ 1 lượt Claude có ảnh / shot — báo giá trước). Đọc ⚙ Chẩn đoán: mỗi shot phải có dòng `chat_prompt` (hoặc lý do VÀNG nếu D6 không
   dùng được). Lấy lần gen ĐẦU.
5. **So mù ảnh:** ghép mỗi shot 2 ảnh cạnh nhau, nhãn "Trái / Phải" xáo ngẫu nhiên; đáp án ghi tệp riêng `…/dap_an.json` (chưa mở). Gửi người
   dùng bảng so (`D:\AI-Video-Output\<ngày>_thu_d6\`), người dùng chọn từng shot + lý do; rồi mới mở đáp án, ghi kết quả.
6. **Video:** mỗi bản duyệt ảnh (người dùng chọn) → Bước 3/4 gen **nháp 480p** ở CẢ hai bản (A: cờ tắt, B: cờ bật — đổi cờ giữa hai lượt, không
   chạy song song hai bản). Báo giá trước. So mù clip như bước 5 (cùng tấm ghép / xem cạnh nhau).
7. Ghi kết quả vào `docs/DANH_GIA_VAI_DAO_DIEN_2026-10-14.md` (mục mới "Kết quả thử D6"): mỗi shot bản nào thắng mù, lỗi gặp (đối chiếu luật
   #27: tường keo TĨNH skin thang máy không thành thang máy thật, Kelly núp đúng bên TRÁI tường, máy đúng phía, SKORP đúng cỡ hai tay, tháp không
   mặt đồng hồ, nền bám render 3D), tiền thật theo sổ chi. Prompt cũ ↔ D6 của từng shot: `tools/d6_pilot.py --project <B> --shots … --kind both`
   (chạy trên bản sao CSDL, chỉ để đọc) hoặc diag.

**Luật quyết định:** D6 thắng mù ≥ 2/3 số shot (ảnh, rồi clip) và không thêm loại lỗi mới → đề xuất bật `chat_prompts` cho tập 2 (người dùng
quyết). Hòa / thua → giữ TẮT, gửi các ca thua về phiên cloud để sửa `knowledge/model_guides/`.

## 4. Tiền (hỏi người dùng TRƯỚC mỗi bước tốn tiền; đề xuất trần cả thử nghiệm 15 USD)
Ảnh 0,052 USD/ảnh (bảng giá) × số shot × 2 bản; Claude Đạo diễn 1 lượt; D6 1 lượt Claude có ảnh / shot (ước tính hiện ở diag / `d6_pilot.py`);
video nháp 480p hai bản — lấy giá từ nút báo giá Bước 4. Không gen bản cao 1080p trong thử nghiệm này.

## 5. Lưu ý D6 (để đọc kết quả cho đúng)
- D6 chỉ đổi CHỮ gửi đi ngay trước lúc gửi; ảnh tham chiếu, model, giá video giữ nguyên → khác biệt kết quả là do prompt.
- D6 lưu kết quả theo nội dung đầu vào: gen lại cùng đầu vào không gọi Claude lại; mỗi job tối đa 2 lượt.
- D6 lỗi / không có Claude → gửi bản cũ + diag VÀNG `chat_prompt_*` — khi đó shot đó KHÔNG tính vào so sánh (ghi rõ).
