# Tổng kết dự án #8 "ANH CHỌN AI?" — phân tích, đánh giá, định hướng sửa (2026-09-28)

> **Nguồn:** 9 góp ý của người dùng sau khi xem bản giao (2026-09-28) · nhật ký chạy thử `docs/CHAY_THU_2026-09-27_NHAT_KY.md` (60 phát hiện)
> · `docs/BAI_HOC_GIAI_DOAN_ANH_2026-09-27.md` · `docs/PHAN_TICH_GOP_SHOT_2026-09-27.md` · `docs/RA_SOAT_CLAUDE_KY_NANG_2026-09-27.md` ·
> đo lại bản giao `D:\AI-Video-Output\2026-09-28_du-an-8\` (ffmpeg, miễn phí) · CSDL `data/manifest.sqlite` (chỉ đọc).
> **Người dùng chốt:** chỉ tổng kết, **không sửa thêm** trong đợt này. Tài liệu này là đầu vào cho đợt sửa gộp (thay mục A của
> `docs/TON_DONG_2026-09-27.md`).
> Ký hiệu: ✅ đã đo/xác nhận bằng dữ liệu · 🔎 nguyên nhân khả năng cao, cần kiểm thêm · 💻 sửa code miễn phí · 💵 cần tiền để nghiệm thu.

---

## 0. Tóm tắt một trang

| Chỉ số | Kế hoạch | Thực tế | Đánh giá |
|---|---|---|---|
| Độ dài phim | kịch bản ~58 s · Director 63,7 s | **83,0 s** | ❌ dài hơn 30–43 % |
| Chi phí | trần đợt thử **10 USD** | **42,85 USD** (video 28,0 · ảnh ~6,9 · Claude ~7,9) | ❌ gấp 4,3 lần; trần nâng hơn 8 lần |
| Ảnh | 33 khung | **132 ảnh** đã trả tiền (4 ảnh / khung) | ❌ 3 lần đổi cách làm ảnh giữa chừng |
| Clip | 33 shot | **53 clip** (20 lần làm lại) | ⚠ 19 clip làm lại vì chọn giọng sau video |
| Claude | ~1,4 USD ước tính | ≈ 7,9 USD (suy từ tổng trừ video + ảnh), **phần lớn là QC** chưa dùng được (lúc đo 28/09 sáng: ~63 %) | ❌ |
| Thời gian | — | ~2 ngày (27–28/09), nhiều lần dừng để sửa code + khởi động lại dashboard | ⚠ |
| Chất lượng hình tĩnh (storyboard) | — | nhân vật / trang phục / ánh sáng nhất quán, tháp có chóp | ✅ điểm mạnh nhất đợt này |
| Chất lượng phim (chuyển động, âm thanh, kể chuyện) | — | 9 lỗi người dùng nêu, 4 lỗi nặng | ❌ chưa đạt để đăng |

**Kết luận chính:** hệ thống đã làm được **khung hình tĩnh tốt và khóa chi phí đúng**, nhưng **phần "thành phim" còn yếu**: thời gian
(timeline) chốt trước khi có giọng thật nên mọi thứ phía sau (clip, hiệu ứng âm thanh, nhạc, khớp môi, độ dài) lệch theo; nhiều cờ dựng
**chưa từng kiểm thật** (`verified: False`) được bật cùng lúc và đi thẳng vào bản giao; QC chỉ soi **ảnh tĩnh**, không ai soi **chuyển động,
âm thanh, câu chuyện** trước khi giao.

---

## 1. Chín góp ý của người dùng — bằng chứng, nguyên nhân gốc, hướng sửa

Ảnh bằng chứng: `docs/video_check_2026-09-28/giay_41_64_phu_de_va_hud.jpg` (khung giây 41–46, 63–64, 0,5),
`clip01_can_kelly_so_voi_clip_khac.jpg` (clip 01 cạnh clip 02/04/30/32), `storyboard_shot1_2_19.jpg` (storyboard shot 1, 2, 19).

### 1.1 Phụ đề có dòng tên người nói → bỏ
- **Bằng chứng ✅:** file `FINAL_VIDEO_sub_src.srt` có 3 dòng riêng "KELLY" (0,2 s), "KENTA" (1,28 s), "MAXIM" (10,32 s); trên hình chữ
  "KELLY" nằm đè lên trán Kelly ở giây 0,5.
- **Nguyên nhân gốc ✅:** cờ `name_cards` (bảng tên kiểu thông báo game lần đầu nhân vật xuất hiện, `core/subtitles.py:222`) được bật trong
  23 cờ của đợt thử dù `verified: False`. Cue bảng tên là loại HUD nhưng `to_srt` ghi chung vào file phụ đề như câu thoại.
- **Hướng sửa 💻:** tắt `name_cards` mặc định (người dùng đã quyết: không cần); nếu giữ tính năng thì HUD **không** ghi vào `.srt` và
  không đặt trong vùng mặt. Nghiệm thu: dựng lại #8 → `.srt` không còn dòng chỉ có tên.

### 1.2 Phim 83 s trong khi kịch bản ~58 s
- **Bằng chứng ✅:** Director lập 33 shot = 63,7 s. Bản giao 83,0 s. Ba nguồn làm dài:
  1. **Giọng thật dài hơn ước lượng** — giọng được chọn *sau* khi đã có 33 clip; `fit_durations` kéo 19 shot cho vừa giọng → 19 clip làm lại
     (PH 54). Tốc độ nói ước lượng (2,86 âm tiết/s) không tính khoảng ngừng "…" và thẻ `[short pause]` của `delivery`.
  2. **Thời lượng tối thiểu shot** thêm sau khi QC video chặn clip "không kịp làm hành động": 1,5 s/shot, 2 s cho hành động lớn (PH QC video).
  3. **Clip đơn Seedance giữ nguyên ≥ 4 s** (PH 58) để không mất động tác → shot kế hoạch 1–2 s thành 4 s.
- **Nguyên nhân gốc:** (a) **thứ tự pipeline sai** — timeline chốt ở Director bằng số ước lượng, giọng thật tới sau cùng; (b) không có
  **trần độ dài** làm điều kiện chặn (chỉ có số hiển thị); (c) mỗi bản vá (tối thiểu 1,5/2 s, giữ 4 s) đúng cục bộ nhưng không ai cộng tổng.
- **Hướng sửa 💻:** **timeline theo âm thanh trước** (mục 4.1): TTS nháp ngay sau Director → đo độ dài thật → Director/code chỉnh shot →
  **khóa timeline** → mới vẽ ảnh và gen video. Cổng "độ dài dự kiến lệch mục tiêu > 10 %" phải hỏi người trước khi gen video. Clip đơn dài
  hơn shot thì cắt theo chuyển động (`motion_trim`) thay vì giữ nguyên.

### 1.3 Cảnh cận Kelly đầu tiên giống anime, không đồng nhất với các cảnh khác
- **Bằng chứng ✅:** storyboard shot 1 (job 369) là cận trung, da/tóc kiểu render 3D, có nền tháp đêm. Clip 01 ra **cận rất sát (ECU)**,
  không còn nền, da mịn như búp bê, mắt to hơn — khác hẳn clip 02/04/30/32 (cùng Kelly, giữ đúng kiểu render). Clip 01 dài 1,08 s (kế hoạch 1,8 s).
- **Nguyên nhân gốc 🔎:**
  1. Nhóm Seedance **chỉ ảnh tham chiếu** (P2m, không có khung đầu): model tự vẽ lại khuôn mặt; ở cỡ cận, khuôn mặt chiếm cả khung nên "gu"
     riêng của Seedance Fast 720p lấn át; ảnh tham chiếu mặt lại **bị đánh dấu dấu cộng đỏ trên một mắt + dải chữ** để qua bộ lọc người thật
     → thông tin khuôn mặt yếu đi đúng ở shot cần mặt nhất.
  2. Ảnh shot 1 đã **hết lượt tự sửa** (CU ra MCU 2 lần) và được nhận "lỗi nhỏ" → prompt nói CU, ảnh là MCU → video "sửa" thành ECU.
  3. Chế độ 🧪 Thử rẻ (Seedance Fast 720p).
  4. QC video chấm identity/hành động, **không so phong cách** (render 3D ↔ anime) với storyboard.
- **Hướng sửa:** 💻 shot cận / cận trung có mặt → **không gộp nhóm ref-only**; đi đường **khung đầu = ảnh storyboard** (Kling i2v, hoặc
  Seedance khung đầu nếu qua bộ lọc) · câu khóa phong cách "photoreal 3D game render, not anime, not illustration" trong mọi prompt video ·
  QC video so **khung giữa clip với ảnh storyboard** (độ giống mặt + độ giống màu/kết cấu), lệch → chặn. 💵 nghiệm thu: A/B 2 shot cận
  (ref-only vs khung đầu), ~1 USD.

### 1.4 Nền Tháp Đồng Hồ vẫn nhiều tầng, sai map Đảo Quân Sự (đã góp ý nhiều lần)
- **Bằng chứng ✅:** khung giây 41–46 (Kelly): sau lưng là nhiều lớp tường đá, bậc thang, bờ tường cao — kiểu thành lũy. Ảnh toàn cảnh
  nhìn cao (establishing) đúng map (1 quảng trường thấp, nhà 1–2 tầng), nhưng khung ngang tầm mắt "tự thêm tầng".
- **Nguyên nhân gốc ✅ (A/B 28/09):** prompt ảnh **thiếu câu bố cục thật** + ảnh tham chiếu render 3D chụp sát chân tháp (bệ đá, bậc lớn) →
  model đoán phần sau thành thành lũy. Câu bố cục đã thêm vào mô tả Kho ngày 28/09 và A/B xác nhận hiệu quả, **nhưng 33 khung đang dùng
  vẽ ngày 27/09 (trước khi sửa) và không được vẽ lại** → video (ref-only, lấy nền từ storyboard) mang nguyên lỗi. S5·2 còn bị Seedance đổi
  dáng tháp (chóp → vòm).
- **Vì sao lặp dù đã góp ý nhiều lần:** góp ý nằm ở bộ nhớ / sổ tay (`qc_playbook` G1) / tài liệu, **không phải điều kiện chặn trong code**
  (vi phạm `CHUAN_XAY_DUNG` luật 3); không có **ảnh chuẩn in-game** của khu tháp để so; QC không có phép đo "số tầng tường".
- **Hướng sửa:** 👤 người dùng cung cấp 5–10 ảnh chụp in-game quanh tháp (các hướng, ngày/đêm) làm **chuẩn bối cảnh** trong Kho (thay/bổ
  sung render sát chân tháp) · 💻 chặn gửi prompt ảnh ở địa điểm có mô tả bố cục mà prompt thiếu câu bố cục · 💻 khi mô tả địa điểm đổi →
  đánh dấu "cũ" mọi khung của địa điểm đó (như cơ chế ảnh cũ khi prompt đổi) · 💻 lớp 0 so khung với ảnh toàn cảnh (tỉ lệ vùng tường/đá
  trên đường chân trời) · 💻 video: shot rộng có nền nhiều → ưu tiên khung đầu thay vì ref-only.

### 1.5 Chuyển động khựng, dáng không hợp cảnh, cảnh chạy giả
- **Bằng chứng ✅:** 21/33 shot cỡ MS, 20/33 máy tĩnh; storyboard gần như toàn **dáng đứng chân dung** (tay đan trước bụng, đứng thẳng) kể cả
  shot có hành động; 30/33 shot < 3 s, clip nhóm 3–4 shot bị cắt còn 0,5–2 s/shot; 5 clip bị QC chặn vì "không kịp làm hành động".
- **Nguyên nhân gốc:**
  1. **Ảnh storyboard vẽ trạng thái, không vẽ hành động** — `image_prompt` của Director tả cảm xúc + vị trí, không tả tư thế đỉnh hành động
     (bước chạy, đang quay người) → video phải "khởi động" từ dáng đứng.
  2. **Shot quá ngắn cho hành động**: chạy / quay người / ngã cần ≥ 2,5–3 s; nhóm Seedance ép 3–4 hành động vào ≤ 15 s rồi cắt.
  3. **Motion prompt dựng bằng code** (bỏ Claude cho nhóm Seedance để tiết kiệm) → câu chung chung, không có chi tiết vật lý (trọng tâm,
     chân chạm đất, tay đánh, tóc/áo bay).
  4. Seedance **Fast 720p** (Thử rẻ) + ref-only: chất lượng chuyển động thấp nhất trong các lựa chọn.
  5. QC video chỉ hỏi "hành động có xảy ra không", không đo **độ tự nhiên** (trượt chân, giật, người như trôi).
- **Hướng sửa:** 💻 Director/Quay phim: trường `action_peak` (tư thế giữa hành động) cho shot có động tác, storyboard vẽ tư thế đó · 💻 luật
  thời lượng theo loại hành động (chạy/ngã/ôm ≥ 3 s, phản ứng ≥ 1,2 s, chèn cận có chủ ý mới được < 1 s) — **áp từ lúc Director lập shot**,
  không vá lúc cắt · 💻 mẫu motion prompt theo loại hành động có câu vật lý · 💵 A/B 3 shot hành động: Seedance Fast vs Seedance Pro vs Kling
  (khung đầu), ~2–3 USD → chọn model theo loại hành động · 💻 QC video lớp 0: đo luồng quang (optical flow) phát hiện giật / đứng hình /
  trượt chân.

### 1.6 Chuyển cảnh giật, chưa dùng máy quay linh hoạt
- **Bằng chứng ✅:** toàn phim chỉ có **cắt thẳng** (`transition: cut`); 20/33 máy tĩnh, 3 push-in, 1 pan; nhiều shot 0,5–1 s liên tiếp
  (S3·7 0,46 s, S3·3 0,83 s); 4 shot liền cùng cỡ MS (cảnh 2) — linter đã cảnh báo nhưng không chặn (PH 4).
- **Nguyên nhân gốc:** Director/Quay phim không bắt buộc đa dạng cỡ cảnh + chuyển động máy có động cơ; khâu Dựng không có **bộ lập chuyển
  cảnh** (chỉ cut / crossfade / dip toàn phim, không theo từng điểm nối); shot quá ngắn nên cắt thành "nhảy hình".
- **Hướng sửa:** 💻 luật Quay phim thành **cổng**: ≤ 2 shot liền cùng cỡ, mỗi cảnh ≥ 1 chuyển động máy có lý do (push-in ở đỉnh cảm xúc,
  pull-out khi lộ bí mật, bám theo khi chạy) · 💻 trường `transition_in` từng shot (match cut, whip, zoom-through, J/L-cut, flash trắng cho hồi
  tưởng) + khâu Dựng thực hiện · 💻 tối thiểu 1,2 s/shot trừ chèn cận có chủ ý · 💻 camera move nằm **trong prompt video** (Seedance/Kling
  làm được push/pull/orbit) thay vì chỉ ghi ở bảng shot.

### 1.7 Nhân vật thoại chưa khớp môi
- **Bằng chứng ✅:** 23 câu thoại nhưng chỉ **4 shot** được làm khớp môi (`lipsync/index.json`: 4 shot, Seedance tạo kèm giọng); 19 shot có
  thoại nằm trong nhóm Seedance ref-only **không có âm thanh** → miệng cử động ngẫu nhiên hoặc không cử động, giọng TTS đặt đè lên.
- **Nguyên nhân gốc:** (a) Director chỉ đánh dấu `lip_sync` cho ít shot; nhóm Seedance loại shot khớp môi ra nhưng shot thoại không đánh dấu
  thì vẫn vào nhóm; (b) giọng chọn **sau** video → không thể tạo video kèm giọng; (c) đợt thử không mở sync.so (hậu kỳ khớp môi).
  Mục tiêu V4 "khớp môi toàn video" chưa có đường đi trong luồng chia shot + nhóm Seedance.
- **Hướng sửa:** 💻 luật: **mọi shot có người nói thấy mặt** (không quay lưng / qua vai người nghe) phải khớp môi — đánh dấu bằng code từ
  `dialogue` + `blocking`, không chờ Director · 💻 giọng trước video (mục 4.1) · 👤 quyết: Seedance tạo kèm giọng từng shot (đắt hơn nhóm,
  ~0,48 USD/shot) hay mở lại hậu kỳ khớp môi (sync.so) cho shot nhóm · 💻 QC khớp môi bằng máy (độ mở miệng theo đường bao âm lượng).

### 1.8 Giây ~43: chữ đè mặt, sau đó mất nhạc nền, có tiếng rè
- **Chữ đè mặt ✅:** câu "Không được để em biết…?" (41,4–44,3 s) bị đẩy lên **đỉnh** khung và nằm ngang đầu Kelly. `text_placement.placements`
  chuyển phụ đề lên trên khi mặt nằm ở dải dưới và dải trên "đè ít hơn" — **không đòi dải trên phải trống**; shot trung cảnh dọc mặt nằm cao
  nên đè vẫn xảy ra. Không có lựa chọn thứ ba (thu nhỏ, lệch trái/phải, rút gọn câu).
- **Mất nhạc ✅:** đo độ to từng giây: từ **giây 39 tới ~65** khoảng lặng giữa câu thoại tụt xuống −56 dB (không có nhạc). Nguyên nhân:
  Director đặt `sound.music = cut` ở shot 16 rồi **lặp `cut` ở shot 21, 23, 25, 26, 27**, chỉ `in` lại ở shot 28 (hồi tưởng) → nhạc tắt
  liền ~27 s. Linter `sound_intent` đã báo "cut khi nhạc đã tắt — không có tác dụng" nhưng chỉ cảnh báo; cờ `sound_intent` bật dù
  `verified: False`. Thêm: nhạc được soạn cho 64 s, phim thành 83 s.
- **Tiếng rè 🔎:** 3 hiệu ứng **súng + va chạm + bíp** đặt ở 43,28 / 43,45 / 43,60 s — **đúng lúc Kelly đang nói**, đỉnh −1,9 dBFS. Ba âm
  này Director xin cho **shot 26 (Maxim trúng đạn, ở giây ~63 trên bản giao)**. Khâu chọn hiệu ứng (`autopilot._sfx_phase`) chạy **một
  lần** lúc 09:30 trên timeline cũ, lưu **giây tuyệt đối**; sau đó 19 clip làm lại dài hơn nhưng hiệu ứng không dịch theo. Cần nghe lại để
  xác nhận "rè" là tiếng súng/va chạm lệch chỗ hay còn do mã hóa AAC nhiều lần (TON_DONG A18) / giọng TTS.
- **Hướng sửa 💻:** hiệu ứng neo theo **shot + độ lệch trong shot**, tính lại giây mỗi lần dựng · chạy lại kế hoạch nhạc + hiệu ứng khi timeline
  đổi (đánh dấu "cũ" như ảnh/clip) · linter ý đồ nhạc thành **sửa tự động** (cut lặp → bỏ; nhạc tắt > 8 s → hỏi) · phụ đề chỉ lên trên khi dải
  trên **trống**, không thì thu nhỏ/chuyển cạnh · limiter −1 dBTP cuối chuỗi · mã hóa âm 1 lần (A18).

### 1.9 Kịch bản gây tò mò nhưng cụt, Maxim tự nhiên gục, không rõ kết, hồi tưởng không có dấu hiệu
- **Bằng chứng ✅:** shot 26 "Maxim trúng đạn ngã gục giữa chiến trường" dài 1,0 s, HUD "Maxim đã bị hạ" hiện khi Maxim còn đang giơ tay
  (khung giây 63–64); cả phim đặt quanh tháp (người dùng chốt đổi bối cảnh) nên **không có cảnh trận đấu / kẻ địch** dẫn tới cú bắn; hồi tưởng
  (shot 28) chỉ khác ở **ánh sáng ấm** trong ảnh, không có chuyển cảnh / màu / âm báo hiệu; hai shot kết (32–33: Kelly khóc cười, ôm) mỗi shot
  **1,0 s** → cái kết lướt qua.
- **Nguyên nhân gốc:**
  1. Director không có bước kiểm **"người xem lần đầu có hiểu không"**: nguyên nhân → sự kiện (ai bắn Maxim, vì sao Kenta phải chọn) không
     có shot thiết lập; `hook_mid` / `money_shot` đã có luật nhưng Director không làm theo (PH 4).
  2. Đổi bối cảnh toàn phim sang quảng trường tháp **sau** Director mà không chạy lại phần kể chuyện → cảnh "chiến trường" mất bối cảnh.
  3. Khâu Dựng không có **ngữ pháp hồi tưởng** (flash trắng/rung hình vào, màu ấm/giảm bão hòa + viền mờ, âm "whoosh"/vang, ra bằng flash
     ngược); lỗi nhận nhầm hồi tưởng (PH 43) còn làm cảnh 4 bị ánh sáng hồi tưởng trong một lúc.
  4. Kết thúc không có luật **giữ hình** (hold) — thời lượng chia đều theo shot.
- **Hướng sửa:** 💻 Director thêm **bảng nhịp truyện** bắt buộc (thiết lập → xung đột → ngoặt → trả lời → kết) và mỗi cú ngoặt phải có shot
  thiết lập trước · 💻 agent **"người xem lần đầu"** (chỉ đọc bảng shot + thoại, không đọc kịch bản gốc) tóm lại câu chuyện; tóm sai → Director
  sửa (1 lượt Claude ~0,05 USD) · 💻 trường `flashback: true` cấp shot + bộ hiệu ứng hồi tưởng ở khâu Dựng · 💻 shot kết ≥ 2,5 s và kết bằng
  card/nhạc chốt · 💻 đổi bối cảnh sau Director → bắt buộc chạy lại Director cho cảnh bị ảnh hưởng (hoặc cảnh báo chặn).

---

## 2. Toàn bộ lỗi trong quá trình làm #8 — gom theo nguyên nhân gốc

Số PH = số phát hiện trong nhật ký. **ĐS** = đã sửa trong đợt thử (có test; phần lớn **chưa nghiệm thu thật lần hai**).

### 2.1 Ước tính & ngân sách (trần 10 → 42,85 USD)
| PH | Lỗi | Trạng thái |
|---|---|---|
| 2 | Ước tính trước Director tính theo cảnh (6 × 30 s), không theo shot → thấp ~3 lần; nút "Duyệt & chạy tự động" hiện con số sai | mở |
| 3 | Director hai lượt ước 0,48 → thật 1,27 USD (ra ~94k token vs 30k) | mở |
| 5, 6, 7 | Bộ chọn model lấy Seedance Fast cho "cảnh thường" dù Kling rẻ hơn; ước tính bỏ qua `camera_setups`; dòng H6 "multi-shot 65 s" sai luật Kling ≥ 3 s/shot | 5 đã đổi theo quyết định (ưu tiên Seedance); 6, 7 mở |
| 12, 17 | Giá Kling std thật ~0,06/s vs bảng 0,08; `video-list` trả `cost = 0` cho Seedance → không đối chiếu được | mở |
| 33 | Thử rẻ hạ cỡ ảnh dù giá như nhau | ĐS |
| 44, 45 | Ước tính Claude chỉ tính 1 lượt/khâu; agent QC 2 USD cho 1,5 cảnh (cache bị phá) | ĐS (khóa 3 tầng, cache trượt) |
| 51 | Khóa ngân sách chặn lượt dịch vì đề xuất không tính lượt dịch | ĐS |
| 52 | Pha motion dịch lại 33 shot đã dịch | ĐS (`857d904`) |
| 55 | Làm lại shot thành clip đơn ≥ 4 s, ước tính theo giá nhóm | ĐS (`8feaa07`) |
| mới | 132 ảnh cho 33 khung: 3 cách làm ảnh (Seedream + ghép phông xanh → vẽ lại có `GREEN_FIX` → GPT Sunburst + toàn cảnh) | bài học quy trình |
| mới | 53 clip cho 33 shot: 19 clip làm lại do giọng chọn sau video (~6,6 USD) | xem 4.1 |

**Đánh giá:** khóa cứng hoạt động đúng (không lần nào vượt trần đã duyệt) nhưng **trần bị nâng 8 lần** vì ước tính luôn thấp và vì đổi hướng
giữa chừng. Cần ước tính **theo kịch bản đã chốt cách làm**, gồm cả vẽ lại / làm lại / nghiệm thu, và trần duyệt **một lần** ở Bước 1.

### 2.2 Director / kịch bản / âm thanh theo ý đồ
| PH | Lỗi | Trạng thái |
|---|---|---|
| 1 | Dự án mới không kế thừa cách làm đã chốt (chia shot, look, phong cách) → mặc định v2 | mở |
| 4 | Director không làm theo trường mới (`hook_mid`, `money_shot`, mẫu `lighting`, trái/phải trong `start_frame`); ý đồ nhạc `cut`/`in` sai logic | mở — **gây ra lỗi mất nhạc 1.8** |
| 13 | Gắn bối cảnh chỉ theo tên có trong kịch bản; "tháp đồng hồ" không khớp asset 263 | mở |
| 19 | Đổi bối cảnh sau Director không sửa chữ nơi chốn trong `image_prompt` (sửa tay 16 + 8 shot) | mở |
| 43 | Nhận nhầm hồi tưởng từ ghi chú cấp cảnh → cảnh 4 ánh sáng hồi tưởng, S4·2 vẽ lại 4 lần | ĐS (`66b3a42`) |
| 1.9 | Truyện cụt, cú bắn không có thiết lập, kết 2 × 1 s | mở |
| 1.6 | 21/33 MS, 20/33 máy tĩnh, shot TB 1,9 s | mở |

### 2.3 Ảnh / storyboard / bối cảnh
| PH | Lỗi | Trạng thái |
|---|---|---|
| 21, 37 | Kiểm Bible bằng ảnh **báo sai** mũ Maxim; cờ sai còn khóa nút gen ảnh sau khi người đã xác nhận | mở (37 ghi sổ lỗi) |
| 22–31 | Chuỗi lỗi ghép phông xanh lên nền 3D: máy chúc 56–62°, 12/33 khung chữ nhật dán, thân lơ lửng, mép cắt giữa khung, sàn bị coi là vật che, chỗ đứng sát cột, pha nền chạy code cũ | ĐS nhưng **cách làm đã bỏ** (tắt `location_plates`) |
| 32 | Ghi chú cũ "ảnh tham chiếu chỉ ~70 %" sai sau khi có storyboard Deepix | đã ghi lại |
| 38 | Lớp 0 cho vẽ lại cùng lỗi 2 lần | ĐS (`e802973`) |
| 41, 42 | S4·2 hoàng hôn giữa trưa; giả thuyết "phiên storyboard nhớ" sai — gốc là PH 43 | ĐS |
| 47 | Tháp nhiều tầng: thiếu câu bố cục + render sát chân tháp | nguyên nhân ✅ (A/B), **khung sản xuất chưa vẽ lại** → lỗi 1.4 |
| 48 | 4/11 khung chặn lượt 1 là **chặn oan** (xét trái/phải theo mép khung) → 4 lần vẽ lại thừa | ĐS (sổ tay A1) |
| 57 | Ảnh đánh dấu đặt tên theo tên file: KENTA và MAXIM cùng `7.png` → clip Maxim ra Kenta | ĐS (`9a5a041`); **các clip nhóm có cả hai chưa soi lại** |
| mới | Shot 1 CU không vẽ ra CU sau 2 lần, được nhận "lỗi nhỏ" → video tự đẩy thành ECU kiểu anime (1.3) | mở |

### 2.4 QC
| PH | Lỗi | Trạng thái |
|---|---|---|
| 24, 36 | QC Claude duyệt ảnh lỗi ghép; QC theo cảnh không phân biệt ảnh lỗi (0,67) với ảnh tốt (0,69), không đạt nghiệm thu | lớp 1 tắt mặc định (`scene_qc_claude`) |
| 39 | QC lớp 1 nhắc lại cờ code thay vì nhìn độc lập; phán nhầm ý đồ shot chèn | mở |
| 45–50 | Agent QC trong app: cache vỡ, không ghi dần, câu trả lời bị cắt bỏ cả lượt, nhãn chuẩn sai | ĐS từng lỗi; **agent chưa đạt nghiệm thu** (bỏ lọt S6·5), cờ `qc_agent` tắt |
| QC video | QC clip xếp nhầm khâu ngân sách (chặn hết); sau đó **quá khắt khe** (S1·4, S4·4 chặn oan) nhưng **không bắt** phong cách anime (1.3), nền nhiều tầng (1.4), chuyển động giả (1.5), khớp môi (1.7) | mở |
| mới | **Không có QC cho bản dựng cuối**: độ dài, nhạc mất 27 s, hiệu ứng lệch 20 s, phụ đề đè mặt, dòng tên trong `.srt` đều lọt tới người dùng | mở — **ưu tiên cao** |

**Đánh giá:** QC tốt nhất đợt này là **agent Claude Code soi khung cạnh nhau** (bắt lỗi lật gương, mũ, hướng nhìn) — tốn 0 API nhưng cần
người chạy. QC trong app tốn ~5 USD mà chưa tin được. Lỗ hổng lớn nhất: **không ai soi video + âm thanh + bản dựng** trước khi giao.

### 2.5 Video
| PH | Lỗi | Trạng thái |
|---|---|---|
| 8, 9 | Chưa có chế độ nhiều shot / một lần gen cho Seedance; Seedance từ chối ảnh in-game (người thật) | ĐS: P2m đánh dấu ảnh tham chiếu — đổi lại mặt yếu hơn (1.3) |
| 15 | `find_by_prompt` so 200 ký tự đầu → nối clip ngược thứ tự | ĐS |
| 54 | Giọng chọn sau video → 19 clip xếp hàng làm lại không ai hỏi | ĐS (cổng `voice_fit`) — **gốc là thứ tự pipeline** |
| 56, 57 | Clip đơn sai nhân vật (tên ảnh đánh dấu trùng) | ĐS |
| 58 | Clip đơn bị cắt về 1–2 s mất cú ngã | ĐS (giữ nguyên) — **gây dài phim 1.2** |
| QC | Shot quá ngắn cho hành động (0,46–1 s) | ĐS tạm (1,5/2 s) — cần luật từ Director (1.5) |

### 2.6 Âm thanh / dựng / bản giao
| Nguồn | Lỗi | Trạng thái |
|---|---|---|
| PH 60, 1.1 | Dòng tên người nói trong phụ đề (`name_cards`) | mở |
| 1.8 | Nhạc tắt 27 s liền (ý đồ `cut` lặp), nhạc soạn 64 s cho phim 83 s | mở |
| 1.8 | 3 hiệu ứng lệch ~20 s (giây tuyệt đối, không neo shot), chồng lên thoại | mở |
| 1.8 | Phụ đề nhảy lên đỉnh đè mặt | mở |
| 1.7 | 19/23 câu thoại không khớp môi | mở |
| TON_DONG A16 | 9 cờ Dựng `verified: False` được bật cùng lúc (`name_cards`, `sound_intent`, `impact_shake`, `music_breath`, `j_cut`, `ambience_bed`, `motion_trim`, `loudness_normalize`, `shot_color_match`) — chưa ai xem/nghe A/B | mở — **nguồn của phần lớn lỗi 1.1, 1.8** |

### 2.7 Dashboard / vận hành
| PH | Lỗi | Trạng thái |
|---|---|---|
| 11 | Panel 🧪 thử nghiệm chỉ ở chế độ chuyên gia | mở |
| 14 | Bấm theo tọa độ trong trình duyệt app lệch (nút ⚙, nút duyệt) — suýt bấm nhầm "chạy tự động" | mở |
| 16 | Báo tiến độ bằng tiếng Anh sau khi nén ngữ cảnh | đã ghi bộ nhớ |
| 20 | E-mail đăng nhập nằm trên URL (`?login=`) | mở — riêng tư |
| 25 | Chạy tự động chờ ở cổng thì job ảnh mới không tự gửi | mở |
| 30 | Sửa code mà không khởi động lại → tiến trình cũ chạy code cũ | quy tắc vận hành; nên có cảnh báo "code đã đổi, cần khởi động lại" |
| 34 | Không đọc được số dư Claude (không có khóa quản trị) | ghi nhận |
| mới | Không có màn xem **timeline tổng** (shot + thoại + nhạc + hiệu ứng + phụ đề) → lỗi 1.2, 1.8 chỉ thấy khi xem bản cuối | mở |
| mới | Trần Claude "còn 3 USD" bị hiểu là trần tổng từ đầu đợt | mở — hiển thị "đã dùng / trần / còn" |

### 2.8 Cách làm việc của Claude (tự đánh giá)
- **Tự gây lỗi 3 lần:** chèn "the stone clock tower… behind" vào prompt phông xanh (làm nặng PH 24); `is_flashback` đọc cả ghi chú cấp cảnh
  (PH 43); bỏ cả lượt câu trả lời bị cắt của agent (PH 50).
- **Đoán nguyên nhân khi chưa đọc prompt thật đã gửi** (S4·2: 2 giả thuyết sai, 4 lượt vẽ lại) → luật: soi lỗi lặp phải dựng lại prompt gửi đi đầu tiên.
- **Nhãn chuẩn sai được dùng làm chuẩn** (lật gương theo mép khung) → 4 lần vẽ lại thừa.
- **Sửa code trong lúc dự án đang chạy**, nhiều lần khởi động lại; 3 lần đổi cách làm ảnh sau khi đã trả tiền — mỗi lần đổi là một lần trả lại.
- **Tập trung vào khung tĩnh**, chưa tự xem/nghe trọn bản giao trước khi báo "xong" — 9 lỗi người dùng tìm ra lẽ ra phải tự thấy (ít nhất
  1.1, 1.2, 1.8 đo được bằng máy trong vài giây).

---

## 3. Đánh giá theo khâu (sau #8)

| Khâu | Mức | Làm tốt | Chưa đạt |
|---|---|---|---|
| Kịch bản → Director | 5/10 | 33 shot đủ trường, tự gắn tài nguyên đúng, Đạo diễn duyệt 6/6 | truyện cụt, không làm theo luật mới, ý đồ nhạc sai, không biết bối cảnh thật |
| Quay phim (bảng shot) | 4/10 | có trục, blocking, `view_notes` | cỡ cảnh đơn điệu, máy tĩnh, shot quá ngắn, không có chuyển cảnh |
| Ảnh / storyboard | 7/10 | nhất quán nhân vật/trang phục/ánh sáng, tháp có chóp, toàn cảnh mỗi cảnh | nền nhiều tầng, CU không ra CU, 4 ảnh/khung |
| Video | 4/10 | P2m qua bộ lọc, giữ nhân vật phần lớn clip | chuyển động giả, cận anime, 19 thoại không khớp môi, 53 clip/33 shot |
| Giọng | 6/10 | 4 giọng VN đúng người, 23 câu | tới sau video → làm lại 19 clip |
| Nhạc / hiệu ứng / dựng | 3/10 | độ to −14 LUFS, phụ đề đúng giọng thật | mất nhạc 27 s, hiệu ứng lệch 20 s, tên trong phụ đề, chữ đè mặt, hồi tưởng không có dấu hiệu |
| QC | 4/10 | lớp 0 code bắt lỗi kỹ thuật, agent soi dải khung | QC trong app chưa tin được; không QC video/âm thanh/bản dựng |
| Chi phí | 5/10 | khóa cứng đúng, sổ chi đủ | ước tính thấp 3–4 lần, trần nâng 8 lần |
| Dashboard / vận hành | 6/10 | chạy trọn trên giao diện, cổng xác nhận chặn bấm nhầm | không kế thừa cấu hình, không có timeline tổng, e-mail trên URL |

---

## 4. Nguyên nhân gốc xuyên suốt → định hướng sửa

### 4.1 Timeline theo âm thanh trước ("audio-first") — sửa gốc cho 1.2, 1.7, 1.8, PH 54
Thứ tự mới: **Kịch bản → Director (bảng shot) → giọng TTS nháp mọi câu (rẻ) → đo độ dài thật → chỉnh thời lượng shot (code + Director nếu
lệch > 10 %) → khóa timeline → nhạc soạn đúng độ dài → animatic → ảnh → video (clip thoại tạo kèm giọng / khớp môi) → hiệu ứng neo shot → dựng.**
Giọng chọn ở Bước 1 (mặc định 4 giọng VN đã chốt), không phải sau video.

### 4.2 Animatic trước khi trả tiền video — bắt lỗi 1.2, 1.6, 1.8, 1.9 với giá gần 0
Ghép **ảnh storyboard + giọng thật + nhạc + phụ đề + hiệu ứng** thành bản xem trước (ffmpeg, pan/zoom nhẹ theo `camera_move`). Người dùng xem
animatic ở cổng storyboard: độ dài, nhịp, câu chuyện, nhạc, chữ đè mặt đều thấy trước khi tốn ~28 USD video. Đây là thay đổi **có tác động
lớn nhất / chi phí thấp nhất**.

### 4.3 Cờ chưa kiểm thật không được đi vào bản giao
Cờ `verified: False` chỉ chạy ở **bản A/B phụ** (bản giao chính dùng cấu hình đã kiểm); dashboard hiện danh sách cờ chưa kiểm đang ảnh
hưởng bản dựng. Đúng `CHUAN_XAY_DUNG` luật 5 — đợt thử đã vi phạm khi bật 23 cờ cùng lúc.

### 4.4 Mọi mốc thời gian neo theo shot, không theo giây tuyệt đối
Hiệu ứng, nhạc tắt/bật, bảng chữ HUD, phụ đề: lưu `(shot, offset)`; giây tính lại mỗi lần dựng. Timeline đổi → các kế hoạch phụ thuộc
đánh dấu "cũ" và chạy lại (miễn phí phần code, Claude chỉ khi cần chọn lại).

### 4.5 Luật trong tài liệu → cổng trong code
Những thứ đã có luật/sổ tay nhưng vẫn lọt: câu bố cục địa điểm (1.4), ý đồ nhạc (1.8), cỡ cảnh liền nhau (1.6), `hook_mid`/`money_shot`
(1.9), thời lượng tối thiểu theo hành động (1.5). Mỗi luật: **kiểm bằng code → chặn hoặc tự sửa → báo người**, không chỉ cảnh báo.

### 4.6 QC ba tầng cho phim, không chỉ cho ảnh
1. **Ảnh** (đã có lớp 0 + agent soi dải khung).
2. **Clip:** so với storyboard (mặt, màu/phong cách, nền), độ tự nhiên chuyển động (luồng quang), khớp môi.
3. **Bản dựng cuối — miễn phí, bằng máy:** độ dài so mục tiêu, nhạc lặng > 8 s, hiệu ứng rơi vào câu thoại, đỉnh âm > −1 dBTP, phụ đề đè mặt
   (dò mặt trên khung thật), dòng phụ đề không phải thoại, shot < 1 s. **Không giao khi còn lỗi chặn.** Claude Code tự xem/nghe trước khi báo xong.

### 4.7 Chuẩn thật cho bối cảnh và phong cách
Ảnh chụp in-game khu tháp (người dùng cung cấp) làm chuẩn bối cảnh; một bộ **khung chuẩn phong cách** (render 3D FF) để QC clip so "không
anime". Khi chuẩn đổi → khung liên quan tự thành "cũ".

### 4.8 Ổn định trước khi chạy tốn tiền
Không sửa code giữa lượt chạy trả tiền; nếu phải sửa → dừng, khởi động lại, chạy khô trên bản sao CSDL (đã làm tốt ở lần 33/33 yêu cầu ảnh) rồi
mới chạy tiếp. Đổi cách làm (ảnh/video) chỉ sau khi A/B nhỏ có kết quả.

---

## 5. Lộ trình sửa đề xuất (chờ người dùng duyệt thứ tự)

| Đợt | Nội dung | Loại | Nghiệm thu |
|---|---|---|---|
| **S1 — Dựng & âm thanh (nhanh, rẻ)** | tắt `name_cards` + HUD không vào `.srt`; hiệu ứng neo shot + tính lại khi dựng; ý đồ nhạc tự sửa (`cut` lặp) + cảnh báo nhạc lặng > 8 s; nhạc co giãn / soạn lại theo độ dài thật; phụ đề chỉ lên trên khi dải trên trống; limiter; mã hóa âm 1 lần; bộ hiệu ứng hồi tưởng; shot kết giữ ≥ 2,5 s; **QC bản dựng cuối bằng máy** (4.6-3) | 💻 | dựng lại #8 từ 33 clip sẵn có (0 USD): hết 1.1, 1.8, có dấu hiệu hồi tưởng; người dùng xem/nghe |
| **S2 — Timeline theo âm thanh + animatic** | giọng ở Bước 1, TTS nháp sau Director, chỉnh thời lượng, khóa timeline, cổng độ dài ±10 %, animatic ở cổng storyboard | 💻 (+ TTS vài cent) | #8 animatic khớp độ dài mục tiêu; người dùng duyệt nhịp trước video |
| **S3 — Director kể chuyện + Quay phim** | bảng nhịp truyện, agent "người xem lần đầu", shot thiết lập cho cú ngoặt, `action_peak`, luật thời lượng theo hành động, đa dạng cỡ cảnh/máy thành cổng, `transition_in`, đổi bối cảnh → chạy lại Director; sửa gộp bộ kỹ năng (TON_DONG mục A) | 💻 + 💵 Director ~1,5 USD | chạy lại Director #8 → agent người xem tóm đúng truyện; linter 0 lỗi chặn |
| **S4 — Video chất lượng** | shot cận/có mặt → khung đầu; khớp môi mọi shot người nói thấy mặt; câu khóa phong cách; motion prompt theo loại hành động; QC clip so storyboard + luồng quang | 💻 + 💵 A/B ~3–5 USD | A/B cận (ref-only vs khung đầu), 3 shot hành động × 3 model, 2 shot khớp môi |
| **S5 — Bối cảnh thật** | ảnh in-game khu tháp vào Kho; chặn prompt thiếu câu bố cục; khung cũ khi mô tả đổi; lớp 0 đo "tầng tường"; vẽ lại khung #8 bị nhiều tầng | 👤 + 💻 + 💵 ~1–2 USD | khung tháp ngang tầm mắt khớp ảnh in-game (người dùng xác nhận) |
| **S6 — Ước tính / ngân sách / dashboard** | ước tính theo cách làm đã chốt + vẽ lại/làm lại/nghiệm thu; dự án mới kế thừa cấu hình; màn **timeline tổng**; e-mail khỏi URL; job ảnh gửi khi đang chờ cổng; hiện cờ chưa kiểm; "đã dùng / trần / còn" rõ ràng; cảnh báo code đổi cần khởi động lại | 💻 | ước tính #8 dựng lại lệch thực tế ≤ 20 % |
| **S7 — QC agent** | tiếp tục nghiệm thu `qc_agent` trên bộ nhãn đã sửa (38 ca) + thêm ca video | 💵 ~1 USD | bắt 100 % khung chặn trên bộ nhãn, 0 chặn oan |

Sau S1–S4: **chạy lại #8 (hoặc một kịch bản mới ~60 s) với trần duyệt một lần ở Bước 1**, chỉ dùng cờ đã kiểm, để đo lại toàn bộ bảng mục 0.

## 6. Cần người dùng quyết
1. Thứ tự đợt S1–S7 (đề xuất: S1 → S2 → S3 → S4 → S5 → S6 → S7; S1 làm được ngay, 0 USD).
2. Khớp môi: Seedance tạo kèm giọng từng shot (~0,48 USD/shot, mất lợi thế gộp nhóm) hay mở lại hậu kỳ sync.so cho shot nhóm?
3. Cung cấp ảnh chụp in-game khu Tháp Đồng Hồ (5–10 ảnh, các hướng, ngày/đêm).
4. Bỏ hẳn tính năng bảng tên (`name_cards`) hay giữ dạng HUD tùy chọn (mặc định tắt)?
5. Chất lượng đợt sau: giữ 🧪 Thử rẻ (Seedance Fast 720p) hay nâng model cho shot cận / shot hành động?
6. Kịch bản "ANH CHỌN AI?": cho Director thêm shot thiết lập (trận đấu, kẻ bắn Maxim) — phim dài hơn — hay giữ khung ~60 s và rút bớt thoại?
