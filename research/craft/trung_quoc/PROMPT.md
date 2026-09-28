# Craft viết prompt (video AI, nguồn tiếng Trung) (S phiên 2026-09-29)

> Tầng 3 theo `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md`. Nguồn chính: tài liệu chính thức Seedance 2.5 [1] (đọc trọn văn) và
> Seedance 2.0 [2]; bổ sung cộng đồng [13][14]. Mỗi kỹ thuật ghi **nhiều ý đồ có thể phục vụ + điều kiện dùng**, không gán
> nghĩa cố định. Ví dụ tiếng Trung ngắn (≤ 15 từ) giữ nguyên văn kèm dịch; đoạn dài diễn giải lại bằng lời của dự án.

## 1. Khung viết prompt chính thức của Seedance 2.5 [1]

Tài liệu chính thức khuyên "coi Seedance như một nhà sản xuất nội dung hình ảnh, viết prompt có cấu trúc theo tư duy đạo
diễn" (nguyên văn ngắn, dịch). Khung gồm 4 phần, theo thứ tự:

1. **Chỉ định tư liệu (素材指代)** — với input đa phương thức (ảnh/video/audio), phải ghi rõ số thứ tự mỗi tư liệu (theo thứ
   tự tải lên) và **vai trò** của nó: ai là hình ảnh nhân vật, ai là âm sắc giọng, ai là tham chiếu chuyển động, ai là cảnh.
   Ví dụ dịch: "ảnh 1–2 là nhân vật 1, tương ứng âm thanh 1; ảnh 3–4 là nhân vật 2, tương ứng âm thanh 2".
2. **Tóm tắt một câu** — công thức: chủ thể + địa điểm + sự kiện + thể loại/phong cách + máy quay đặc biệt (nếu có).
3. **Mô tả tình tiết cụ thể** — chọn 1 trong 2 cách chia đoạn: **theo mốc giây** hoặc **theo "cảnh/shot số N"**, mỗi đoạn mô
   tả hình ảnh + máy quay + hành động + thoại + âm hiệu; ưu tiên mô tả khẳng định (positive), tránh mô tả phủ định trừ 2
   trường hợp được hỗ trợ: phụ đề và điều khiển âm thanh (vd "không phụ đề", "không nhạc nền").
4. **Kết đoạn** — bổ sung chi tiết xuyên suốt: máy quay/góc máy giữ nguyên, môi trường/không khí, âm thanh nền.

**Có thể phục vụ**: prompt ngắn mà vẫn đủ thông tin cho model đa chủ thể/đa tư liệu (đúng yêu cầu "ngắn nhưng đủ ý" của
người dùng) · giảm lỗi gán nhầm nhân vật khi nhiều tham chiếu.
**Khi hợp**: mọi tác vụ tham chiếu (R2V) có ≥ 2 tư liệu đầu vào. **Khi không cần đầy đủ 4 phần**: tác vụ đơn giản 1 chủ thể,
1 hành động — có thể rút gọn còn phần 2–3.

## 2. Mốc thời gian (timestamp) — khác biệt quan trọng giữa các model

- **Seedance 2.0 / Fast**: *"chỉ phản hồi số thứ tự cảnh (shot number), KHÔNG phản hồi mốc giây"* — đây là điểm dự án đã xác
  nhận qua lỗi thực tế #8 (xem `docs/CAP_NHAT_CLIPAI_2026-09-28.md`). Viết "Shot 1 / Shot 2" thay vì "0–3 giây".
- **Seedance 2.5**: phản hồi mốc giây **nguyên số** (đơn vị 1 giây). Quy tắc viết mốc giây theo tài liệu chính thức [1]:
  - Dùng khoảng thời gian liên tục, không nhảy cóc: "0-3 giây...3-7 giây...7-15 giây" (đúng); tránh kiểu "0-3 giây...5-6
    giây..." (thiếu liên tục — model sẽ khó xử lý).
  - Có thể dùng **mốc điểm** ("giây thứ 5 chuyển cảnh nhanh sang trái") hoặc **mốc tương đối** ("nhân vật đứng lặng, 3 giây
    sau mọi người xung quanh lắc đầu").
  - Không dùng mốc giây để ép tần suất lặp lại động tác (vd "1 giây lắc đầu 3 lần") — tài liệu khuyến cáo tránh, dễ ra lỗi.
  - Đoạn thời gian quá ít nội dung → model tự do phát huy; quá nhiều nội dung → cắt vụn hoặc bỏ sót tình tiết — cần cân đối.

**Có thể phục vụ**: kiểm soát nhịp chính xác hơn (2.5) · giữ đơn giản, tránh trôi mốc (2.0/Fast, dùng số shot).
**Điều kiện**: chọn cách theo đúng model đang gọi — đây là lỗi gốc đã gây 5 clip bị chặn QC ở dự án #8 (viết mốc giây cho
model 2.0 không đọc mốc giây).

## 3. Ngôn ngữ máy quay (镜头语言) [1]

Tài liệu chính thức chia 2 mức:
- **Thuật ngữ phổ thông viết thẳng được**: cỡ cảnh (đại toàn cảnh/toàn cảnh/trung cảnh/cận cảnh/đặc tả), động tác máy
  (đẩy/kéo/lia/đi theo/quay vòng/bổ nhào/lùi xa/quay lên/tay cầm rung), góc máy (góc thấp/nhìn từ trên xuống/góc nhìn thứ
  nhất).
- **Kiểu máy quay thịnh hành viết thẳng được**: "一镜到底" (một cú máy liền mạch/long take), "希区柯克变焦" (Hitchcock zoom —
  dolly zoom), góc quay flycam, FPV, "子弹时间" (bullet time), tay cầm, "回弹变速" (đổi tốc độ giật lùi).
- **Thuật ngữ hiếm/quá chuyên môn**: phải viết dạng "[tên thuật ngữ] + giải thích mô tả", không viết trần thuật ngữ. Ví dụ
  dịch: "chuyển tiêu điểm — tiêu điểm hình ảnh chuyển mượt, cây cối đang nét ở tiền cảnh mờ dần, nhân vật ở hậu cảnh từ mờ rõ
  dần".
- **Chuyển cảnh** (转场): phải ghi rõ **điểm kích hoạt** (mốc giây nào) và **cách làm**. Ví dụ dịch: "giây thứ 5 chuyển cảnh
  nhanh sang trái (xoá dần từ trái + hoà tan tự nhiên)".

**Có thể phục vụ**: rút ngắn prompt bằng thuật ngữ thay vì mô tả dài dòng (khi thuật ngữ phổ thông) · giữ chính xác khi thuật
ngữ lạ (bọc giải thích).
**Khi không dùng**: thuật ngữ quá hiếm mà không giải thích — model có thể không hiểu, prompt "ngắn" nhưng mất thông tin.

## 4. Mô tả hành động / biểu cảm [1]

- **Hành động**: ưu tiên mô tả **khái quát** (vd dịch: "liên tục làm vài tổ hợp đá cao và lộn vòng", "hai bên giao chiến cận
  chiến") thay vì liệt kê từng động tác nhỏ; chỉ viết chi tiết cụ thể cho **những động tác ít, có điểm nhấn đáng nhớ**;
  tránh lặp lại mô tả cùng một hành động nhiều lần trong prompt.
- **Biểu cảm**: ưu tiên câu mô tả, hạn chế thành ngữ/từ trừu tượng. Ví dụ chính thức: thay "ăn ngon lành" (津津有味地吃饭,
  thành ngữ) bằng "trên mặt mang nụ cười mãn nguyện, ăn từng miếng lớn" (脸上带着满足的笑容，大口地吃饭 — mô tả cụ thể).
- **Lỗi thường gặp — mắt phát sáng bất thường**: model phản ứng quá mức với cảm xúc mạnh, làm đồng tử phát sáng xanh/đỏ phi
  tự nhiên. Cách sửa [1]: ràng buộc ưu tiên cao nhất "nhân vật có mắt người bình thường, không phát sáng"; đổi từ cảm xúc quá
  mạnh ("cuồng nhiệt", "cực sốc") sang từ thông thường hơn ("kinh ngạc") để giảm xác suất lỗi.

**Có thể phục vụ**: hành động khái quát → prompt ngắn, model tự nhiên hoá chuyển động · hành động chi tiết cụ thể → chỉ dùng
cho điểm nhấn cần chính xác (ví dụ 1 cú đấm quyết định).
**Khi không hợp**: mô tả chi tiết cho *mọi* động tác trong 1 cảnh dài → dễ "nhồi" quá nhiều yêu cầu vào thời lượng ngắn — lỗi
đã gặp ở dự án #8 ("dồn 3–4 shot + hành động vào ≤15s").

## 5. Kiểm soát âm thanh — dương/âm tính [1]

- **Phủ định hỗ trợ**: phụ đề ("không phụ đề/không thêm phụ đề đối thoại") và âm thanh (chi tiết tới từng lớp: hiệu ứng, nhạc
  nền/BGM, lời thoại — vd "không bgm, chỉ sinh âm thanh môi trường và âm thanh động tác").
- **Lỗi "ràng buộc phụ đề không có tác dụng"**: nếu sau lời thoại còn mô tả lặp lại từ ngữ + thêm ngữ khí/biểu cảm/động tác,
  dễ kích hoạt sinh phụ đề ngoài ý muốn. Cách sửa: tách theo khuôn "thoại nhân vật (cảm xúc): nội dung", ví dụ dịch: "bà Chu
  thoại (khó tin): 'giống như...'". Cũng cần đảm bảo video tham chiếu (nếu có) không có sẵn phụ đề.
- **Lỗi "ràng buộc không nhạc nền không có tác dụng"**: một số âm hiệu vẫn bị sinh thành nhạc nền. Cách sửa: liệt kê hết từ
  đồng nghĩa của "nhạc" (nhạc, nhạc nền, BGM, phối nhạc, nhạc cụ, giai điệu, âm hiệu tổng hợp, âm nền không khí…) và lặp lại
  ràng buộc ở **đầu và cuối** prompt để tăng "chú ý" của model.

**Có thể phục vụ**: kiểm soát chính xác track thoại/nhạc/hiệu ứng riêng biệt khi cần lồng tiếng khớp môi (liên hệ trực tiếp
nhu cầu tiếng Việt của dự án) · tránh model tự chèn phụ đề/nhạc không mong muốn làm hỏng bản dựng.

## 6. Tham chiếu nhiều tư liệu (multi-reference) [1]

- Khi có nhiều chủ thể, phải liệt kê **từng cái một**, không dồn hết vào 1 câu mơ hồ. Ví dụ dịch: "ảnh 1-2 là nhân vật 1,
  tương ứng âm thanh 1; ảnh 3-4 là nhân vật 2, tương ứng âm thanh 2".
- Nếu chỉ tham chiếu *một phần* tư liệu, phải ghi rõ phần nào. Ví dụ dịch: "tham chiếu động tác thi triển phép thuật ở video
  1, tham chiếu máy quay vòng quanh ở video 2".
- Khi tư liệu tham chiếu đã đủ chính xác, nên **chỉ định** thay vì mô tả lại toàn bộ chi tiết trong prompt (giảm dư thừa,
  đúng tinh thần "ngắn nhưng đủ"). Ví dụ dịch: "tham chiếu nghiêm ngặt động tác và máy quay của video 1, giữ đúng thứ tự như
  video" — không cần viết lại "trước tiên giơ tay, sau đó xoay người, máy quay quay chậm..." nếu video tham chiếu đã có sẵn.
- **Lỗi "gán nhầm nhân vật"**: khi nhiều người, thứ tự nhân vật xuất hiện lần đầu phải khớp thứ tự tư liệu tải lên + số hiệu
  trong prompt — nếu lệch, nhân vật xuất hiện trước có thể bị AI thay bằng nhân vật khác.

## 7. Đa khung phân cảnh (multi-grid storyboard) và khung hình chính (keyframe) — riêng của 2.5 [1]

- **Đa khung phân cảnh** (宫格分镜): ảnh gộp nhiều ô phân cảnh trong 1 tấm — video sinh ra **không** khớp nghiêm ngặt từng chi
  tiết của phân cảnh, chỉ tham khảo đại ý cốt truyện. Khuyên dùng phân cảnh **line-art/hình que đơn giản** dưới **15 ô**, hạn
  chế chữ trên ảnh phân cảnh; phải bổ sung bằng prompt những gì phân cảnh chưa thể hiện (hành động, máy quay, phong cách).
- **Khung hình chính** (关键帧参考): dùng khi cần video khớp **nghiêm ngặt** theo phân cảnh — câu đầu tiên của prompt phải ghi
  rõ "lấy thứ tự ảnh X đến ảnh Y làm khung hình chính".
- **Trắc nghiệm nhanh khi chọn cách nào**: cần đúng ý tưởng đại khái, để model tự nhiên hoá chuyển động → đa khung phân
  cảnh; cần đúng khung hình chính xác từng điểm → khung hình chính (keyframe).

## 8. Khác biệt Seedance 2.0 vs 2.5 [1] (chính thức, bổ sung cho bảng đã có trong `docs/CAP_NHAT_CLIPAI_2026-09-28.md`)

| Điểm khác | 2.0 | 2.5 |
|---|---|---|
| Mốc thời gian | chỉ phản hồi số shot | phản hồi mốc giây nguyên số |
| Nhiều góc nhìn làm tham chiếu chủ thể | không khuyến khích | hỗ trợ |
| Tỷ lệ khung hình | 6 mức cố định | tự do 0,4–2,5 qua điều chỉnh tư liệu đầu vào |
| Chất lượng V2V (video-to-video) | — | hỗ trợ xuất .mov, giữ màu/độ sáng/đồng bộ âm-hình tốt hơn khi nối dài/biên tập |
| Phong cách thẩm mỹ | khác 2.5 khá rõ, dùng chung ảnh/prompt cho 2 model sẽ lệch phong cách | nếu cần giữ phong cách 2.0, nên đưa video 2.0 vào làm input nối dài (extend), xuất .mov |

## 9. Ví dụ prompt (diễn giải lại, không chép nguyên bài dài; câu ngắn ≤15 từ giữ nguyên văn TQ)

- Prompt tóm tắt 1 câu (giữ nguyên, 14 từ): *"写实自然纪录片风格，电影级真实光影，温暖的午后"* (phong cách tài liệu tự
  nhiên chân thực, ánh sáng điện ảnh, buổi chiều ấm áp) — minh hoạ công thức "phong cách + tông + thời điểm" đứng đầu prompt.
- Prompt chỉ định tư liệu nhiều chủ thể (diễn giải): "Ảnh 1 là bảng phân cảnh 9 ô dùng cho kết cấu máy quay chung; ảnh 2 là
  ảnh thực bối cảnh sân cỏ hoàng hôn dùng làm chuẩn màu; ảnh 3 là ngoại hình nhân vật robot bảo vệ; ảnh 4 là ngoại hình nhân
  vật bà lão" — rồi mới tới phần mô tả từng nhân vật/cảnh/phong cách/loại trừ ("nghiêm cấm: đen trắng, phác thảo, hoạt hình
  2D…")/phân cảnh theo giây.
- Prompt sửa lỗi phát sáng mắt (diễn giải nguyên tắc, không chép câu mẫu dài của tài liệu): đặt câu ràng buộc "mắt người bình
  thường, không phát sáng" **ở vị trí ưu tiên cao** trong prompt, đổi từ cảm xúc cực đoan thành từ nhẹ hơn.

## 10. Sai lầm thường gặp (tổng hợp [1] + [2] + [13])

1. Viết mốc giây cho model 2.0/Fast (chỉ đọc số shot) → hành động/nội dung trôi khỏi mốc dự kiến.
2. Nhồi nhiều hành động/đổi máy quay vào thời lượng ngắn → chuyển động giả, model không kịp thể hiện hết.
3. Chỉ ghi tên nhân vật *trên ảnh* (không ghi trong prompt) khi có nhiều chủ thể → dễ nhầm lẫn giữa các nhân vật.
4. Mô tả phủ định cho nội dung hình ảnh chung chung (model chỉ hỗ trợ phủ định tốt cho phụ đề/âm thanh) — muốn "không có X"
   trong hình, nên thay tài sản tham chiếu thay vì thêm câu phủ định.
5. Dùng thành ngữ/từ trừu tượng cho biểu cảm thay vì mô tả cụ thể quan sát được.
6. Đưa 1 tác vụ quá phức tạp (nhiều loại tham chiếu + biên tập + hiệu ứng cùng lúc) vào 1 lần sinh — tài liệu [1] khuyên
   **tách thành nhiều tác vụ đơn giản**, sinh nhiều lần rồi ghép ở hậu kỳ, thay vì cố gộp 1 lần.
7. Dùng ảnh tham chiếu độ phân giải cao hơn hẳn độ phân giải output → dễ sinh vân "vân tay" ở vùng texture dày (cỏ, lá) —
   nên giảm kích thước ảnh đầu vào xuống ngang hoặc dưới độ phân giải output.

## Khoảng trống / câu hỏi còn mở
- Chưa đọc được tài liệu Kling chính thức (trang không tải nội dung qua công cụ hiện có) — chưa biết khung prompt/thuật ngữ
  máy quay của Kling có khác Seedance không.
- Cộng đồng [13] chỉ cho 12 mẹo rất chung (không đặc thù model) — không đủ chi tiết để đối chiếu chéo với tài liệu chính thức
  ngoài các điểm đã nêu.
- Chưa có ví dụ thất bại/thành công cụ thể kèm mốc giây từ 1 clip mẫu cụ thể trong đợt này (khác với đợt học phim short film
  tiếng Anh) — vì nguồn ở đây là tài liệu hướng dẫn, không phải phim mẫu có mốc giây để đo.
