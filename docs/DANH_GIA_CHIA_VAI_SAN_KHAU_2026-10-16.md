# Đánh giá tổng: luồng chia vai sân khấu (stage_crew) + previs one-shot — ca thử #31, 16/10/2026

Người dùng yêu cầu: "xong cần review lại để đánh giá tổng về kế hoạch sử dụng này, xem đã được tối ưu chưa". Số liệu dưới đây lấy từ
lần chạy thật NGOẠI TUYẾN (0 USD, phiên Claude Code đóng các vai, Blender cục bộ): cảnh 3 #31 (shot 10–13), thư mục
`data/projects/31/stage/kho265/doan_3/crew/`.

## 1. Kết quả ca thử shot 10 (cảnh 3)

| | Lượt cũ (một vai, đã ĐẠT bộ kiểm) | Chia vai — lần đo m3 | Chia vai — lần đo m4 (cuối) |
|---|---|---|---|
| Góc | chúc −6,5° (ý đồ "nhìn lên") | **ngửa +9,2°** | ngang +1,0° |
| Xe nôi (chính) | 93 % khung — một mảng thành xe | **64 %, thấy 100 %** — đọc được hình dạng | 65 %, thấy 60 % |
| Kelly (phụ, ý đồ: chỉ tay ở mép) | 237 % khung, đứng GIỮA máy và xe nôi | thấy 36 % (mép phải) | 141 %, lại đứng giữa máy và xe nôi |
| Bộ kiểm | ĐẠT (không ai so ý đồ) | HỎNG P2 (mép ô cỏ sát máy 26 %) + C1 | HỎNG P3 (không ngửa) |

- **Cơ chế đạt**: bảng đối chiếu "đã khai ↔ đo được" chạy trên lượt cũ bắt đủ 3 lệch của shot 10 (vật chắn giữa máy và chủ thể, "nhìn
  lên" ↔ chúc, vật chính 93 %); Quay phim tự sửa máy theo ý đồ của chính mình và lần đo m3 đạt đúng ý (ngửa, xe nôi đọc được, Kelly ở
  mép).
- **Chưa đạt trọn**: lượt duyệt thứ hai (hết trần 2 lượt) làm shot 10 XẤU đi (m4) — xem mục 3.1–3.2. Shot 11 hỏng khung cuối (máy đẩy
  vào làm Kelly ra khỏi khung). Shot 12–13 đạt. **Chưa ghi máy vào CSDL** — state đang chờ người dùng duyệt (quyết định
  stage-crew-plan-2026-10-16 (1)).

## 2. Lỗi code ca thử lôi ra (đã sửa, có test)

1. **Bộ giải C1 khi nhịp không có trục** (`core/stage_solver.py`): vật trục bị ẩn (xe nôi biến mất) → `side = None` bị coi là "phía khác
   s0" → MỌI phương án hỏng C1. Ảnh hưởng mọi cảnh có vật trục biến mất / chưa xuất hiện, không riêng chia vai.
2. **`v2_run` sập (KeyError) khi vật trục ẩn ở nhịp** — lệch với bộ giải (bộ giải bỏ trục, Blender thì không).
3. Bảng đối chiếu thiếu lý do C1 và khung cuối khi máy chạy ("HỎNG —" trống).
4. Rà quy ước 7 (agent): 3 CAO (autopilot trả tiền lặp khi lỗi; state lưu nửa vời khi Blender lỗi; phiên Claude tự duyệt được bước
   dành cho người dùng), 6 VỪA, nhiều THẤP — đã sửa, có test.

## 3. Đã tối ưu chưa? — CHƯA. Đề xuất theo thứ tự lợi ích

1. **Không lùi khi sửa** (lợi lớn nhất): lần đo m3 tốt hơn m4 nhưng luồng chỉ giữ lần đo CUỐI. → Lưu phương án tốt nhất từng shot qua
   các lần đo (theo kết luận Quay phim), chốt bằng phương án đó; sửa máy chỉ đo lại shot bị sửa.
2. **`cross_ok` không được mở khóa đổi phía máy**: khai cross_ok để qua C1 khiến bộ giải tự chọn phía đông → máy ra sau lưng Kelly.
   → Khi Quay phim sửa một phần, bộ giải ưu tiên phương án GẦN máy lần đo trước (khởi đầu ấm), chỉ đổi phía khi được nói rõ.
3. **Phía máy `s0` thuộc Quay phim, không thuộc Đạo diễn**: Đạo diễn chọn s0 ngược với ghi chú khung của Quay phim (Kelly bên phải) →
   C1 hỏng cả shot 10–11. → Đạo diễn chỉ ghi cặp trục; Quay phim chọn s0 cùng yêu cầu khung.
4. **Đo lại chỉ shot đổi**: mỗi lần đo chạy cả 4 shot (~60 s thực / lần, 4 lần = ~4 phút). → Đo shot đổi, giữ số đo shot đã khớp.
5. **Đề bài Quay phim nặng** (74–77 KB ≈ 20k token mỗi lượt, chủ yếu sách `dp.md` ~300 dòng): chế độ API dự kiến 4–6 lượt/cảnh. →
   Cache phần sách (đã đặt dấu cache), hoặc chỉ gửi các mục `dp.md` liên quan khâu sân khấu (cỡ, góc, trục, qua vai…). Đo chi phí thật
   trước khi người dùng quyết bật API (quyết định (3)).
6. **Trần 2 lượt tự duyệt hơi chặt cho cảnh có ràng buộc vật lý khó** (CU thấp sát đất bị mép ô cỏ chắn): với (1) + (2), 2 lượt có thể
   đủ; chưa nên nới trần trước khi làm (1) (2).

## 3b. ĐÃ LÀM tối ưu (người dùng 16/10 chiều) + ca thử lần 2 cảnh 3 (0 USD)

Đã làm: (1) giữ phương án tốt nhất — mỗi shot nhớ mọi lần đo, kết luận khop / giu_lech KHÓA lần đo (chọn được lần đo trước bằng
`lan_do`), chốt từng shot bằng lần đã duyệt hoặc lần ít lỗi nhất (bỏ lần bị bác), gom vào `crew/final`; (2) `_near` + xếp hạng "cùng
phía máy lần trước" ở bộ giải + K4 (chỉ đổi phía khi Quay phim ghi `doi_phia`); (3) `s0` thuộc Quay phim; (4) đo lại chỉ shot sửa.
Thêm từ ca thử: Quay phim `giu_lech` được miễn luật khung đã nêu tên (`bo_luat`, KHÔNG miễn P1). Rà quy ước 7 lần 3: 3 CAO + 5 VỪA
(xóa lịch sử đo khi đổi dàn cảnh / s0, s0 trống lấy từ lần đo đầy đủ, shot đo lại không ra phương án → không dùng lặng số cũ, …) — đã
sửa, có test.

| | Lần thử 1 | Lần thử 2 (tối ưu) |
|---|---|---|
| Lần đo / lượt duyệt | 4 lần đo cả 4 shot, 2 lượt | 3 lần đo (m2: 2 shot, m3: 1 shot), 2 lượt |
| C1 (phía máy) shot 10–11 | hỏng (s0 Đạo diễn ngược ghi chú) | không còn (s0 Quay phim) |
| Shot 10 | m3 đúng ý → m4 LÙI (ra sau lưng Kelly) | m1 đúng ý → khóa; giữ lệch miễn P2 (mép ô cỏ tiền cảnh) → **có máy** |
| Shot 11 | hỏng khung cuối | vẫn hỏng khung cuối (xe nôi 33 % < 40 % — Kelly qua vai che khi máy đẩy vào) |
| Shot 12–13 | đạt | đạt (lần đo đầu, không đo lại) |

Còn lại: shot 11 cần Đạo diễn dời Kelly lệch khỏi trục máy→xe nôi hoặc bỏ đẩy máy — luồng đã hỏi được (de_nghi_doi_cho) nhưng ca này
Quay phim chọn sửa máy; ca sau nên ưu tiên đề nghị dời người khi khung cuối bị người che lặp 2 lần.

## 4. Previs one-shot (shot 6–9, cảnh 2) — người dùng đề xuất 16/10

- Kelly một mình, bối cảnh đơn giản → một cú máy liền mạch thay cho 4 máy rời: người nộm chạy theo lối thật A* trong mê cung (48,7 m,
  không xuyên hàng rào), máy bám Kelly bằng độ lệch máy↔Kelly của từng shot đã đo, chuyển mượt (Empty + Track To như tài liệu
  `Tai_Lieu_Quy_Trinh_AI_Video_OneShot_Blender.docx`), tiêu cự kẹp 24–35 mm (người dùng chọn).
- Thời lượng: giữ 17,7 s của kịch bản; Kelly CHẠY đều ≈ 6,2 m/s ở shot 6–7 (người dùng: thế giới song song buff ×1,3–1,5 + Kelly
  nội tại chạy nhanh), shot 8–9 giữ nhịp kịch bản.
- Ra 2 video: hình khối (clay) + depth (gần trắng, xa đen, 0,1–20 m) — MP4 H.264 SAR 1:1, 720×1280 (đúng luật ref ClipAI ≥ 700 px,
  ≥ 3 s; code kiểm trước khi render).
- Ba vòng nháp (0 USD) và điều đã sửa: (1) máy giữ độ lệch Bắc/Đông cố định → Kelly rẽ trong mê cung thì máy đâm vào hàng rào → máy
  xoay theo hướng chạy + vượt ngọn rào 0,4 m khi lọt ô rào; (2) depth: trời ra TRẮNG (Blender 5 vẽ nền bằng node) → node Background
  đen; (3) người dùng: máy được đảo góc quanh Kelly (trước mặt / sau lưng / chéo) miễn vẫn focus Kelly → `--orbit 160` (vòng 160°
  mỗi đoạn chạy, đoạn sau ngược chiều) + điểm nhìn KHÓA vào ngực Kelly khi chạy (nháp 2: Kelly trôi ra khỏi khung ở shot 7 vì điểm
  nhìn đo của shot 7 nhắm khoảng trống). Rà quy ước 7: 3 CAO (độ cao máy theo sàn, máy chạy cộng dồn quãng đi, giật khi đổi nhân vật
  chính) + VỪA/THẤP — đã sửa, có test.
- Còn thấy: đoạn shot 9 (máy đo cũ của sân khấu một vai) — lưng Kelly che xe nôi, không thấy tay chạm: CÙNG gốc với shot 10 (không ai
  so khung với ý đồ) → chạy cảnh 2 qua luồng chia vai trước khi làm previs bản giao.
- **Chưa kiểm**: (a) Seedance 2.5 qua API 01/10 theo động tác mannequin nhưng KHÔNG theo khung máy của ref — one-shot dựa hẳn vào việc
  model theo đường máy, cần thử nhỏ trước; (b) Motion Strength / Structure Fidelity 0,6–0,8 và thông số ControlNet trong tài liệu là
  của công cụ khác (SD/ComfyUI, web V2V) — ClipAI API không có tham số này; (c) model video một lượt tối đa ~10–15 s → ref 17,7 s phải
  cắt 2 đoạn liền nhau (nối ở khung cuối).
- **Đề xuất thử nhỏ (cần người dùng duyệt chi tiền)**: một đoạn 5 s của previs (shot 8–9, Kelly bước tới xe nôi) + ảnh Kho Kelly + ảnh
  nền → Seedance 2.5 720p, so khung máy kết quả với previs (đo bằng code như QC khung). Đạt thì mới làm cả đoạn.
- **Kết quả thử nhỏ (16/10 22:02, người dùng duyệt giá $1,38; sổ chi $1,38)** — `tools/experiments/previs_v2v_test.py`, dự án thử #32,
  task `cgt-20261016225620-vfe36`. Ref = previs clay đã duyệt 10–15 s (cuối shot 7 → shot 8, máy sau lưng chếch trái, vòng sang phải
  lúc chuyển shot) + plate đêm shot 8 + Kelly 23/10 + bóng mờ 427/1 + xe nôi 442/2, prompt yêu cầu "EXACTLY the camera … of @Video 1".
  Bản giao: `D:\AI-Video-Output\2026-10-15_du-an-31\previs\v2v_thu_16-10\` (clip, ref, ảnh ghép previs trên / kết quả dưới).
  - THEO được: góc nhìn sau lưng, Kelly chạy ra rồi khựng lại trước xe nôi đúng nhịp; dạng bóng mờ, mê cung đêm, xe nôi đúng ảnh Kho;
    không HUD.
  - KHÔNG theo đường máy: đo chuyển động máy từng khung (ORB + affine, 120 khung): previs quét ngang tổng ≈ +840 px (máy vòng phải ở
    2,8–4,6 s), kết quả ≈ −69 px (gần như đứng, chỉ trôi nhẹ); tương quan pan x −0,11, pan y −0,48, zoom −0,38. Cỡ khung cũng khác:
    previs bám sát (Kelly chiếm gần hết khung), kết quả lùi xa (toàn thân + xe nôi). Cuối clip lưng Kelly che xe nôi — cùng lỗi khung
    của previs shot 8–9 (mục 4 "Còn thấy").
  - Kết luận: Seedance 2.5 qua API dùng video tham chiếu như ref ĐỘNG TÁC / bố cục chung (giống 01/10), chưa sao chép đường máy one-shot
    → chưa dùng previs one-shot làm "đường ray máy" cho cả đoạn 17,7 s. Hướng tiếp (chưa làm, cần người dùng chọn): (a) thử ref DEPTH
    thay clay (cấu trúc + máy rõ hơn); (b) Kling (refer_type "base" — sửa lại video gốc, giữ máy) với ref previs; (c) bỏ one-shot, giữ
    luồng từng shot + khung đầu/cuối từ previs.
- **Lượt 2 — ref DEPTH (16/10 23:30, người dùng chọn (a) + duyệt giá $1,38; sổ chi $1,38, dự án thử #32 tổng $2,76)** — `--ref depth`,
  task `cgt-20261016232924-c29t2`, cùng đoạn 10–15 s + cùng 4 ảnh; prompt tả depth (sáng = gần, đen = trời), "follow EXACTLY … frame
  by frame". Bản giao cùng thư mục (`v2v_seedance25_720p_ref-depth_10-15s.mp4`, ảnh ghép 4 hàng previs clay / previs depth / V2V clay /
  V2V depth).
  - TỐT HƠN lượt clay: CỠ KHUNG + BỐ CỤC khớp previs — máy sát sau vai Kelly, Kelly chiếm phần lớn khung, xe nôi bên trái Kelly đúng
    chỗ khối trụ ở previs 10–13 s (lượt clay lùi xa thành toàn cảnh). Bóng mờ, mê cung đêm, xe nôi vẫn đúng Kho.
  - VẪN CHƯA theo cú vòng máy: 2,8–4,6 s previs quét +840 px; lượt depth nhích +90 px ở 2,8 s rồi quét NGƯỢC chiều (≈ −140 px).
    Tương quan pan x −0,17 · zoom +0,38 · roll +0,57 (clay: −0,11 · −0,38 · −0,11).
  - Kết luận: ref depth truyền được vị trí máy / cỡ khung / bố cục tĩnh, chưa truyền được chuyển động vòng của máy. Hợp cho shot máy
    bám ổn định (follow sau lưng), chưa hợp cho đoạn previs có cú vòng / pan lớn → nếu làm tiếp: cắt ranh giới đoạn gen tại các cú vòng
    (mỗi đoạn máy gần như đứng / bám đều), hoặc thử (b) Kling refer_type "base".

## 5. Khuyến nghị dùng

- **Shot đơn giản theo một nhân vật, một không gian liền** (như 6–9): previs one-shot + ref V2V — ít lượt Claude nhất (chỉ cần dàn
  cảnh + máy đã có), nhất quán nhân vật / không gian theo tài liệu.
- **Cảnh nhiều người, nhiều ý đồ khung khác nhau** (như cảnh 3–4): luồng chia vai, sau khi làm (1)–(3).
- Cờ `stage_crew` giữ TẮT cho tới khi (1)–(3) xong và đo chi phí API thật.
