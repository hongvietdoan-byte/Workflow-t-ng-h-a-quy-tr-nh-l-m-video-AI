# Thiết kế Tổ QC nhiều tầng + Director duyệt cuối — 2026-10-01 (bản chờ người dùng duyệt)

> Người dùng 01/10 yêu cầu: QC lọc nhiều tầng; nhiều agent chấm chéo; thứ tự ưu tiên kiểm (nhân vật → cử chỉ → cảnh quan); khâu QC thành một
> nhóm; linh hoạt với kịch bản mới liên tục; Director tham gia duyệt cuối; "dashboard là nhà máy — các khâu ghi kinh nghiệm thành công / thất
> bại để khâu khác cải tiến". Tài liệu này là **thiết kế, chưa code**. Mọi việc tốn tiền vẫn hỏi trước từng lần. Mục 20 = biên bản rà soát.

## 0. Tóm tắt một trang

| Hiện tại (S7.1, 7 lần chạy, ≈ 1,94 USD) | Thiết kế mới |
|---|---|
| 1 agent tự điều tra cả cảnh, vòng lặp tự do, tiền mỗi lượt tăng dần | **Code điều phối**, mỗi vai 1 lượt có cấu trúc / khung (hoặc / cảnh), không vòng lặp |
| Agent tự nghĩ nên soi gì | **Đặc tả của shot** (bảng Director) được code dịch thành **mệnh đề kiểm tra** — kịch bản mới tự có bộ câu hỏi mới |
| Mắt model phán trái/phải, chiều mũ, hướng nhìn | **Code đo** (mốc mặt / mống mắt, dáng người, màu trời, đường nét kiến trúc), model chỉ phán phần code chưa chắc |
| 1 người chấm, không đối chứng | **3 chuyên viên** (Nhân vật · Diễn xuất & hướng · Cảnh & liền mạch) + **Trọng tài** độc lập chỉ xét chỗ cần |
| Không ai xét "cảnh có kể được chuyện không" | **Director duyệt theo cảnh** (ý đồ, nhịp, cảm xúc) trước người dùng — không được ghi đè lỗi cứng |
| Đo trên chính bộ #8 đã dùng để sửa | **Bộ đo vàng** tách *bộ phát triển* (#8) và *bộ độc lập* (dự án khác) + **chạy lại offline** từ bản ghi thật |
| Học bằng sửa sổ tay tay | **Sổ kinh nghiệm** (`core/experience.py`, đã có) + thống kê từng mẫu câu hỏi → tự điều chỉnh ưu tiên |

**Kết quả mong đợi (cổng nghiệm thu, mục 15):** bắt ≥ 90 % khung "chặn" của bộ độc lập, báo nhầm ≤ 10 %, "chưa chắc" (doubt) ≤ 15 %,
chi phí ≤ 0,06 USD / khung (đồng bộ) — **chưa đo**, các con số giá ở mục 16 là ước tính để chọn hướng.

## 1. Bài học từ S7.1 (căn cứ của thiết kế)

| # | Đã xảy ra | Nguyên nhân gốc | Thiết kế mới xử lý ở |
|---|---|---|---|
| 1 | Agent chặn nhầm Kenta quay lưng (vai huy hiệu sao bên trái thân = đúng) 2 lần dù sổ tay A1 đã ghi | phán trái/phải bằng mắt model; ca đã phán không được cho xem | 7.3 (code tính bên thân), 12 (sổ kinh nghiệm) |
| 2 | Cảnh 2 hết lượt / hết tiền không ghi khung nào (3 lần) | vòng lặp tự điều tra; mỗi lượt gửi lại mọi ảnh → giá tăng tới ≈ 0,10 USD/lượt | 8 (1 lượt có cấu trúc, không vòng lặp) |
| 3 | Luật trái/phải bằng code từ chối cả "doubt" và ghi chú "đã kiểm, đúng bên" → vòng lặp | lớp chặn thêm vào sau, đan nhau, test viết theo giả định | 3 (nguyên tắc 7, 8), 15 (chạy lại offline) |
| 4 | Lượt cuối agent vẫn gọi lệnh xem dù được nhắc "ghi ngay" | lời nhắc bằng chữ không ràng buộc | 8.5 (đầu ra có cấu trúc bắt buộc) |
| 5 | K3: agent nhìn sát đúng mũ Maxim vẫn cho qua | phán đoán thị giác yếu với chi tiết hình học; không có ảnh chuẩn đặt cạnh | 7.4 (cắt cặp bộ phận), 9.1, 10 (trọng tài) |
| 6 | Đo lại trên chính #8 → dễ tưởng đã tốt | bộ đo là bộ phát triển | 15 (bộ độc lập) |
| 7 | Tiền nghiệm thu tính vào #8 (dự án đã giao) | thiếu tách dự án | đã sửa (`--bill-project`, #17); 16 |

## 2. Mục tiêu và chỉ số

| Chỉ số | Định nghĩa | Ngưỡng nghiệm thu |
|---|---|---|
| Bắt lỗi chặn (recall) | khung người chấm "chặn" mà tổ kết luận "chặn" (không tính "doubt") / tổng khung "chặn" | ≥ 90 % bộ độc lập |
| Báo nhầm | khung người chấm "đạt / nhỏ" mà tổ kết luận "chặn" / tổng khung đạt + nhỏ | ≤ 10 % |
| Tỉ lệ doubt | khung tổ không quyết được / tổng | ≤ 15 % (doubt về người — tốn công người) |
| Đủ kết quả | khung có kết luận / khung gửi vào | 100 % (không bao giờ "chưa soi" do vòng lặp) |
| Chi phí | USD Claude / khung, tách theo vai | ≤ 0,06 đồng bộ; ≤ 0,04 qua Batch (ước tính mục 16, đo ở giai đoạn 3) |
| Thời gian | phút / cảnh 6 khung (đồng bộ) | ≤ 3 phút |
| Director | cảnh Director cho qua mà người dùng trả về vì lý do kể chuyện | theo dõi, chưa đặt ngưỡng |

Bộ chấm điểm **không** tính "doubt" là "bắt được" (S7.1: bộ cũ tính, làm đọc nhầm kết quả) — sửa ở giai đoạn 1.

## 3. Nguyên tắc thiết kế

1. **Code điều phối, agent không nói chuyện tự do với nhau.** Thứ tự, trần tiền, gom kết quả do code. Mỗi lời gọi model có đầu vào và đầu ra xác định.
2. **Đo trước, phán sau.** Cái gì code đo được (số người, mặt ở đâu, mắt nhìn đâu, bên thân, màu trời, kiến trúc) thì code đo; model phán phần còn lại và được đưa số đo làm bằng chứng.
3. **Mỗi vai một ngữ cảnh nhỏ, tập trung** — ít ảnh, ít chữ, đúng loại lỗi của vai.
4. **Đầu ra có cấu trúc, kết luận do code.** Model trả lời từng mệnh đề (đúng / sai / không thấy + vùng + độ chắc); code quy ra chặn / nhỏ / đạt theo bảng luật (mục 9).
5. **Không vòng lặp mở.** Mỗi vai 1 lượt / khung (hoặc / cảnh). Được 1 lượt "xin xem thêm" có giới hạn khi chính model báo "không thấy" (mục 8.6).
6. **Chấm chéo phải độc lập thật**: khác model và / hoặc khác đầu vào; chỉ xét chỗ cần (mục 10).
7. **Một luật chặn mới phải đi kèm đường thoát**: không lời chấm nào bị từ chối mãi; mọi từ chối có lối ra "doubt + lý do" (bài học 3).
8. **Mọi thay đổi qua bộ đo vàng + chạy lại offline trước khi tốn tiền** (bài học 3, 6).
9. **Tiền khóa cứng nhiều lớp** (lời gọi / khung / cảnh / khâu dự án / đợt thử / giờ) và ước tính trước (luật dự án).
10. **Nhà máy học**: mọi kết luận được người xác nhận / bác bỏ thành ca trong sổ kinh nghiệm; khâu sau đọc được.

## 4. Kiến trúc dây chuyền

```
Bảng shot (Director)  ──►  [A] Bộ dịch đặc tả ──► danh sách MỆNH ĐỀ cho từng khung (loại, chủ thể, ưu tiên, cách kiểm)
Khung vẽ xong        ──►  [B] Tầng 0 — CODE đo (miễn phí) ──► mệnh đề "chắc đúng" / "chắc sai" / "chưa chắc" + số đo + ảnh cắt sẵn
                                   │ chưa chắc / cần mắt
                                   ▼
                          [C] TỔ QC — 3 chuyên viên (song song, 1 lượt có cấu trúc)
                              C1 Nhân vật (từng khung)   C2 Diễn xuất & hướng (từng khung)   C3 Cảnh & liền mạch (cả cảnh)
                                   │ code quy ra kết luận khung (bảng luật mục 9)
                                   ▼
                          [D] TRỌNG TÀI — chỉ: mọi "chặn", "đạt" rủi ro cao, bất đồng code↔model, độ chắc thấp
                                   │ chặn đã xác nhận → VẼ LẠI (≤ 2 lần, đổi đầu vào bằng fix_en) → quay lại [B]
                                   ▼
                          [E] DIRECTOR duyệt CẢNH (ý đồ, nhịp, cảm xúc, kể được chuyện) — không ghi đè lỗi cứng
                                   ▼
                          [F] NGƯỜI DÙNG — cổng duyệt (Bước 2 ảnh / Bước 4 clip) + lấy mẫu 5–10 % khung "đạt"
                                   ▼
                          [G] SỔ KINH NGHIỆM — mọi xác nhận / bác bỏ → ca + thống kê mẫu câu hỏi → [A][C][D][E] lần sau
```

Chỗ gắn vào code hiện có: thay lớp 1 của `core/qc_scene.py` (`review_scene` / `run_ready_scenes`) và `core/qc_agent.py` sau **cờ mới
`qc_team` (TẮT mặc định)**; tầng 0 mở rộng `qc_scene.check_frame`; kết luận vẫn đi qua `qc_scene.apply` (giữ / duyệt / đánh dấu doubt) để
không đổi cổng duyệt của dashboard. `qc_agent` (agent điều tra) giữ lại làm **công cụ của trọng tài** cho ca khó (mục 10.4), không làm
đường chính.

## 5. Ba lớp kiến thức (vì sao QC linh hoạt với kịch bản mới)

| Lớp | Nội dung | Nguồn (đã có trong repo) | Lặp lại ở kịch bản mới? | Cách dùng |
|---|---|---|---|---|
| **L1 — lỗi của model vẽ** | lật trái/phải khi quay lưng (A1), phụ kiện đổi chiều (A2), trôi mặt / sai người (A3), thừa người (D4), ánh sáng nhảy (C4), trùng hình (C1), bịa kiến trúc nhiều tầng (G1), ghép lộ (D3), khung trống (D1) | `knowledge/qc_playbook.md` mục A–G; nhãn #8; sổ kinh nghiệm | **Có — tính chất công cụ** | mẫu câu hỏi chung + số đo tầng 0 + ca mẫu |
| **L2 — thực thể** (nhân vật, thú cưng, bối cảnh, kỹ năng) | chi tiết bất đối xứng, phụ kiện có chiều, chiều cao; ghi chú theo hướng nhìn; kiến trúc thật; hình kỹ năng + "không được vẽ" | Kho: `assets.get_profile` (`identity, must_keep, may_change, forbidden, height_m, build`) + `view_notes`; `data/skills/*/skill.json` (`phases`, `never_vi`); gói 3D bối cảnh | **Có — mỗi khi thực thể xuất hiện** | mẫu câu hỏi sinh từ hồ sơ; thực thể mới → sinh tự động (mục 6.4) |
| **L3 — đặc tả của shot** | ai trong khung, đứng đâu, nhìn ai, làm gì, diễn xuất, cỡ / góc máy, giờ / ánh sáng / thời tiết, thoại, giai đoạn kỹ năng, mô-típ | bảng shot Director (trường thật: mục 6.2) | **Không — mỗi kịch bản một khác** | **dịch tự động thành mệnh đề** (mục 6) |

Nhãn lỗi cũ dùng cho: (a) **bộ đo vàng** đo chất lượng tổ, (b) **trọng số ưu tiên** loại lỗi (mục 9.3), (c) **ca mẫu theo thực thể** khi đúng
thực thể đó xuất hiện. Nhãn cũ **không** dùng làm khuôn nội dung cho kịch bản mới.

## 6. [A] Bộ dịch đặc tả → mệnh đề kiểm tra

### 6.1 Dạng một mệnh đề
```json
{
  "id": "S3·4#gaze:MAXIM",            // khung · loại · chủ thể
  "frame_job": 341,
  "type": "gaze",                      // identity | asym | headwear | count | layout | gaze | gesture | action | size | angle | light | weather | place | continuity | skill | text
  "role": "C2",                        // C1 Nhân vật | C2 Diễn xuất & hướng | C3 Cảnh & liền mạch | T0 chỉ code
  "subject": "MAXIM",
  "claim_vi": "Maxim nhìn về phía Kelly vừa đi (ngoài khung TRÁI)",
  "question_en": "Is MAXIM looking toward frame-left (off-screen)?",
  "expected": "left",                  // giá trị mong đợi khi đo được
  "how": "code+model",                 // code | model | code+model (code đo, model xác nhận khi code chưa chắc)
  "severity_if_false": "block",        // theo bảng mục 9.1
  "priority": 2,                        // mục 9.3
  "source": "performance.eyes",        // trường Director sinh ra mệnh đề — truy được nguồn
  "evidence_needed": ["face_crop:MAXIM", "iris_direction:MAXIM"]
}
```

### 6.2 Bảng ánh xạ trường Director → mệnh đề (trường đọc từ CSDL thật, 62 shot của #8, #10–#15)

| Trường bảng shot | Mệnh đề sinh ra | Loại | Vai | Cách kiểm |
|---|---|---|---|---|
| `characters` | mỗi người có mặt đúng người; không người thừa / thiếu | identity, count | C1 | code đếm mặt / người (D4) + model so ảnh chuẩn |
| `characters` × hồ sơ Kho (`must_keep`, `forbidden`, `view_notes`) | mỗi chi tiết bất đối xứng đúng bên thân; phụ kiện có chiều đúng chiều theo hướng nhìn | asym, headwear | C1 | code: bên thân (dáng người) + cắt cặp; model xác nhận |
| `blocking` (frame-left / frame-right / trước / sau) | vị trí tương đối từng người | layout | C2 | code: tâm mặt / thân theo bề ngang; model khi không có mặt |
| `performance.eyes` + `blocking` "looking …" | hướng nhìn từng người | gaze | C2 | code: mống mắt (MediaPipe face landmarker, model đã có) |
| `performance.face` / `body` / `listener` | biểu cảm, tư thế, người nghe phản ứng | gesture | C2 | model (code không đo được biểu cảm) |
| `action`, `end_state` | hành động đang diễn ra / trạng thái cuối | action | C2 | model |
| `size`, `angle`, `lens_mm` | cỡ cảnh, góc máy | size, angle | T0 | code (đã có: `shot_size`, chiều cao mặt; góc: đường chân trời từ render 3D khi có) |
| `time`, `lighting`, `weather`, `mood` | giờ / ánh sáng / trời khớp, khớp ảnh toàn cảnh cảnh | light, weather | C3 + T0 | code: màu trời B−R, độ sáng (đã làm tay ở lượt 3 #8) |
| `location`, `location_asset`, `plate_spot` | nơi chốn đúng bản đồ, không bịa kiến trúc | place | C3 + T0 | code: `background_match` (cần sửa chỉ so kiến trúc) + `stacked_tiers` |
| `dialogue` | người nói thấy mặt (nếu shot thoại cận) — phục vụ khớp môi sau | text | C2 | model (nhẹ) |
| `skill_phase` (+ hồ sơ kỹ năng) | hình kỹ năng đúng giai đoạn; không vẽ mục `never_vi` | skill | C1 | model + ảnh khung chính thức của giai đoạn |
| `motif`, `knowledge_gap`, `beat`, `emotional_intent` | **không** thành mệnh đề khung — để **Director duyệt cảnh** (mục 11) | — | E | — |
| `on_screen_text` | chữ hiện đúng, đọc được, trong vùng an toàn | text | T0 | code (vùng an toàn đã có) + model đọc chữ |
| `continuous_with_next`, `camera_setup` | cặp khung liền / cùng vị trí máy nhất quán | continuity | C3 | code (so màu / bố cục) + model |

### 6.3 Ví dụ thật — #8 shot 24 (S3·4)
Bảng shot: `characters` KENTA, MAXIM · `blocking` "Maxim frame-left looking off toward where Kelly walked away, Kenta frame-right standing
still" · `performance.eyes` "liếc nhìn hướng Kelly rồi quay sang Kenta" · `body` "đứng thẳng, tay đút túi" · `listener` "Kenta không đáp, mắt
cụp xuống" · `size` MS · `angle` eye · `time` day · `weather` clear.
Mệnh đề sinh ra (rút gọn):
1. C1 identity — Maxim đúng ảnh chuẩn (tóc bạc, mũ đội ngược, áo bomber bạc). · chặn nếu sai
2. C1 headwear — mũ Maxim: khóa cài ở TRÁN (quay mặt vào máy). · chặn
3. C1 asym — tab đỏ ở tay áo TRÁI thân Maxim; găng giáp ở tay TRÁI thân Kenta. · chặn (theo hồ sơ — danh mục "cấm lệch") / nhỏ (chi tiết nhỏ)
4. C2 layout — Maxim ở nửa trái, Kenta nửa phải. · nhỏ
5. C2 gaze — Maxim nhìn ra ngoài khung trái (code: mống mắt). · chặn (B1: sai trục nhìn đổi nghĩa thoại)
6. C2 gesture — Maxim tay đút túi; Kenta mắt cụp, không đáp. · nhỏ
7. T0 size — MS (đo chiều cao mặt). · nhỏ nếu lệch 1 bậc, chặn nếu ≥ 2 (D2)
8. C3 light — trưa nắng, khớp ảnh toàn cảnh cảnh 3. · chặn nếu sai giờ (C4)

### 6.4 Thực thể mới (nhân vật / kỹ năng / bối cảnh chưa có ca)
- Từ hồ sơ Kho: mỗi từ "LEFT / RIGHT / trái / phải" trong `must_keep` / `view_notes` → 1 mẫu câu hỏi asym; mỗi phụ kiện có chiều ("backwards",
  "ngược") → 1 mẫu headwear cho cả 2 hướng nhìn; `forbidden` → mệnh đề "không có X".
- Từ hồ sơ kỹ năng: mỗi giai đoạn `phases[*].vi` → mệnh đề skill theo `skill_phase` của shot; `never_vi` → mệnh đề "không vẽ".
- Thực thể chưa có hồ sơ duyệt → **không** sinh mệnh đề chi tiết, chỉ identity theo ảnh Kho + báo "thiếu hồ sơ" (luật 1 CHUAN_XAY_DUNG: không im lặng).

### 6.5 Bảng shot tự mâu thuẫn (playbook E)
Bộ dịch phát hiện trước (vd xin MLS mà đòi thấy toàn thân; OTS mà chỉ 1 người; `blocking` nói Kelly ở phải, `characters` không có Kelly) → mệnh
đề đó **không** gửi chuyên viên, ghi `plan_conflict` cho người sửa bảng shot (không vẽ lại khung — vẽ lại không sửa được bảng sai).

## 7. [B] Tầng 0 — code đo (miễn phí, mọi khung)

### 7.1 Đã có (`qc_scene.check_frame`)
`blank` (D1) · `stacked_tiers` (G1) · `no_face` · `shot_size` (D2) · `top_bar` (vùng an toàn) · `dark_face` · `extra_faces` (D4 — dễ đếm nhầm tay).
Video: `clip_measure` (`look_drift`, `jerks`, `lip_sync`, `ref_mark`, `stray_edges`) — ngoài phạm vi giai đoạn đầu (mục 17).

### 7.2 Thêm mới
| Đo | Cách | Model cần | Ra |
|---|---|---|---|
| Hướng nhìn | MediaPipe Face Landmarker — mống mắt so với khóe mắt | `data/models/face_landmarker.task` **đã có**; mediapipe 1.0.1 đã cài | trái / giữa / phải + độ chắc, mỗi mặt |
| Bên thân & tư thế | MediaPipe Pose Landmarker — vai / khuỷu / cổ tay trái-phải theo thân, mũi thấy hay không (quay mặt / quay lưng) | `pose_landmarker` **chưa có** — cần tải 1 file (≈ 5–30 MB, hỏi người dùng) | bên thân của từng vùng tay; hướng quay |
| Cắt cặp bộ phận | từ mốc mặt / dáng người: cắt cùng bộ phận ở khung và ở ảnh chuẩn (mục 7.4) | như trên | ảnh ghép cặp |
| Màu trời / giờ | trung bình dải trời: B−R, độ sáng; so ảnh toàn cảnh cảnh | không | lệch giờ / đúng |
| Kiến trúc | `place_refs.background_match` sửa: chỉ đường nét ngoài vùng người và ngoài vùng cỏ / mặt đất (việc tồn S5.5') | không | độ khớp kiến trúc |
| Trùng hình (C1) | băm ảnh cảm quan giữa các khung khác shot | không | cặp gần trùng |
| Đếm người | Pose (đếm thân) bổ sung đếm mặt | như Pose | số người |

### 7.3 Bên thân — đưa hẳn vào code
Quy tắc đã viết bằng code ở `qc_agent.arm_from_side` (nhìn từ sau: trái-tâm-thân = tay TRÁI; quay mặt: ngược lại). Ở thiết kế mới, **đầu
vào** của quy tắc (tâm thân, vị trí chi tiết, quay mặt / lưng) do **Pose** đo thay vì model khai; model chỉ xác nhận "chi tiết X có ở vùng
này không". Mệnh đề asym: code kết luận "đúng bên / sai bên / không đo được" — sai bên + model xác nhận chi tiết → chặn; không đo được → C1
phán bằng mắt kèm ca mẫu, độ chắc thấp → trọng tài.

### 7.4 Cắt cặp với ảnh chuẩn
Mỗi ảnh chuẩn (`front_standard`, bảng nhiều góc) có **bản đồ bộ phận** đo một lần (Pose + mốc mặt trên ảnh chuẩn; lưu theo sha ảnh). Khi soi
mệnh đề headwear / asym, code ghép: [vùng đầu khung | vùng đầu ảnh chuẩn cùng hướng nhìn nếu có trong bảng nhiều góc]. Lỗi kiểu mũ Maxim K3
là so 2 ảnh nhỏ cạnh nhau, không phải tìm chi tiết trong cả khung.

### 7.5 Kết quả tầng 0 cho mỗi mệnh đề
`certain_ok` (bỏ qua model) · `certain_fail` (vẫn gửi chuyên viên để có câu sửa + trọng tài xác nhận nếu là chặn) · `uncertain` (gửi chuyên
viên kèm số đo) · `not_measurable` (gửi chuyên viên). Ngưỡng "chắc" của từng phép đo đặt từ bộ đo vàng (mục 15), không đoán.

## 8. [C] Tổ QC — ba chuyên viên

### 8.1 Chung cho cả ba
- **1 lượt / khung** (C3: 1 lượt / cảnh), trả lời **từng mệnh đề** được giao: `{"id", "answer": "true|false|unclear", "region": [x0,y0,x1,y1],
  "confidence": "high|medium|low", "note_vi", "fix_en"}` + `"other_issues": [...]` (câu hỏi mở, mục 8.7).
- **Đầu ra bắt buộc có cấu trúc**: `output_config.format` (JSON schema; tài liệu Claude API: hỗ trợ `enum`, không hỗ trợ min/max — kiểm
  bằng code sau) — chạy trên mọi model hiện hành, kể cả dòng 5.5 (không nhận ép gọi công cụ). Không còn "lượt cuối quên ghi".
- **Bố cục prompt để cache** (tài liệu Claude API: tiền tố khớp từng byte; thứ tự tools → system → messages): `system` (luật vai + thứ tự ưu
  tiên, cố định) → khối **thực thể** của cảnh (ảnh chuẩn + hồ sơ + ca mẫu — chung cho mọi khung của cảnh, `cache_control`) → **khung** (ảnh
  khung + ảnh cắt + mệnh đề + số đo tầng 0). Danh sách công cụ / schema **không đổi** giữa các lời gọi (đổi là mất cache — bài học S7.1).
- **Thứ tự ưu tiên** (mục 9.3) nằm trong system và trong thứ tự liệt kê mệnh đề.
- **Suy nghĩ (thinking) của model — đặt rõ, không để mặc định** (tài liệu Claude API: Claude Sonnet 5 bỏ trống `thinking` = suy nghĩ thích ứng,
  token suy nghĩ tính như token ra; Claude Opus 5.5 không tắt được, mặc định effort `medium`): chuyên viên C1–C3 trên Sonnet 5 đặt
  `thinking: {type: "disabled"}` (trả lời ngắn có cấu trúc, câu hỏi đã được code chuẩn bị); nếu sau này chuyển Sonnet 5.5 thì dùng
  `{type: "between_tools"}` (5.5 trả 400 với `disabled`). Đo ở giai đoạn 3: tắt suy nghĩ có làm kém độ đúng không — nếu kém, bật lại với
  effort `low` và tính lại giá.
- **Lời gọi đầu tiên của mỗi cảnh chạy một mình** (ghi cache), các lời gọi sau mới song song — cache chỉ có sau khi lời gọi đầu xong.

### 8.2 C1 — Chuyên viên Nhân vật
Mệnh đề: identity, count, asym, headwear, skill. Đầu vào: khung (768 px), ảnh mặt cắt sẵn (YuNet — đã làm), cặp bộ phận (7.4), ảnh chuẩn từng
người trong khung, ca mẫu thực thể từ sổ kinh nghiệm (`experience.relevant`, theo từng người, cùng hướng nhìn, ưu tiên ca nhắc tên người đó;
không lấy bản khác của shot đang chấm — đã làm). Playbook: A1–A4, D4.

### 8.3 C2 — Chuyên viên Diễn xuất & hướng
Mệnh đề: layout, gaze, gesture, action, text (người nói). Đầu vào: khung, mặt cắt sẵn, số đo hướng mắt + vị trí người, bảng shot dòng của khung
(blocking, performance), khung trước / sau trong cảnh (nhỏ) để xét hướng di chuyển qua cú cắt (B2). Playbook: B1–B3.

### 8.4 C3 — Chuyên viên Cảnh & liền mạch (theo cả cảnh)
Mệnh đề: light, weather, place, continuity (C1–C4, G1, D3). Đầu vào: tấm tổng quan cả cảnh, ảnh toàn cảnh (`scene_establish`), render 3D
đúng góc nếu có, số đo màu trời / kiến trúc / trùng hình. Một lời gọi cho cả cảnh — lỗi liền mạch chỉ thấy khi đặt cạnh nhau.

### 8.5 Vì sao không vòng lặp
Mọi thứ chuyên viên cần đã được code chuẩn bị (ảnh cắt, số đo, ca mẫu) → không cần "xem thêm". Đầu ra có cấu trúc → không có lượt "quên ghi".
Chi phí = số lời gọi × giá một lời gọi — **dự đoán được trước khi chạy** (mục 16).

### 8.6 Một lượt "xin xem thêm" có giới hạn
Nếu chuyên viên trả `unclear` kèm `"need": {"region": [...], "reason"}` cho mệnh đề ưu tiên 1–2, code cắt vùng đó (và vùng tương ứng ở ảnh
chuẩn) và gọi **thêm đúng 1 lần** cho riêng mệnh đề đó. Vẫn `unclear` → trọng tài (nếu chặn-khi-sai) hoặc doubt.

### 8.7 Câu hỏi mở
Mỗi chuyên viên trả thêm `other_issues` (tối đa 3) cho lỗi ngoài danh sách. Mặc định **trọng số thấp**: chỉ thành "nhỏ" trừ khi trọng tài xác
nhận. Lỗi mới người dùng xác nhận → loại lỗi mới (mục 12.3).

## 9. Bảng luật kết luận (code)

### 9.1 Mức khi mệnh đề sai
| Loại | Sai thì | Ghi chú |
|---|---|---|
| identity (sai người / sai trang phục chính), count (thừa / thiếu người), headwear, asym thuộc "cấm lệch" của hồ sơ | **chặn** | A1–A3, D4 |
| asym chi tiết nhỏ không thuộc "cấm lệch" (vd tab đỏ tay áo) | nhỏ | theo nhãn người #8 S3·6 |
| gaze sai trục khi khung có thoại / người nghe | **chặn** | B1 |
| gaze lệch khi không có thoại | nhỏ | |
| action mất nghĩa câu chuyện | **chặn** | B3 |
| gesture / biểu cảm lệch sắc thái | nhỏ | "không bắt bẻ vụn" |
| layout lệch vị trí | nhỏ; **chặn** nếu đảo trái/phải làm vượt trục 180° với shot liền trước | `continuity.axis_warnings` đã có cho bảng shot |
| light / weather nhảy giờ trong cảnh, hồi tưởng không khác hiện tại | **chặn** | C3, C4 |
| place bịa kiến trúc rõ | **chặn** | G1 |
| size lệch 1 bậc / ≥ 2 bậc | nhỏ / **chặn** | D2 |
| continuity trùng hình 2 shot cùng dùng | **chặn** | C1 |
| skill sai giai đoạn / vẽ mục "không được vẽ" | **chặn** | hồ sơ kỹ năng |

### 9.2 Gộp thành kết luận khung
- Có mệnh đề "chặn-khi-sai" bị **sai** với độ chắc high/medium → **chặn (chờ trọng tài)**.
- Mệnh đề chặn-khi-sai **unclear** hoặc độ chắc low → **trọng tài**; trọng tài không quyết → **doubt** (về người).
- Chỉ có sai mức nhỏ → **nhỏ** (đi tiếp, ghi chú cho người).
- Còn lại → **đạt**.
- Code ↔ model mâu thuẫn trên cùng mệnh đề (vd code đo mắt trái, model nói phải) → trọng tài.

### 9.3 Thứ tự ưu tiên (kèm lý do; điều chỉnh bằng dữ liệu)
1. **Nhân vật** (identity, count, asym, headwear) — sai thì cả shot vô dụng, sửa đắt nhất ở khâu video; #8 lượt 1 sau sửa nhãn (`labels_v2`):
   9/9 khung chặn có lỗi khóa nhân vật (7) hoặc hướng nhìn (2).
2. **Diễn xuất & hướng** (gaze, action) — sai thì người xem hiểu sai chuyện (B1: Maxim nói với Kenta mà nhìn Kelly).
3. **Liền mạch** (light, continuity) — lỗi giữa các khung, lộ ra khi dựng.
4. **Bối cảnh** (place) — nặng khi bịa rõ; nhẹ hơn khi chỉ lệch chi tiết.
5. **Kỹ thuật** (size, vùng an toàn) — code đo, ít khi cần model.
Thứ tự này quyết định: (a) mệnh đề nào liệt kê trước trong lời gọi, (b) mệnh đề nào được "xin xem thêm" (chỉ ưu tiên 1–2), (c) khi trần tiền
gần chạm thì bỏ mệnh đề ưu tiên thấp trước. **Điều chỉnh tự động**: điểm ưu tiên = mức nghiêm trọng × (tỉ lệ bỏ sót + 0,05) × tần suất, tính
từ thống kê mẫu câu hỏi (mục 12.2) mỗi tuần; người dùng duyệt thay đổi thứ tự (không tự áp).

## 10. [D] Trọng tài

### 10.1 Khi nào gọi
- Mọi khung tổ kết luận **chặn** (xác nhận trước khi tốn tiền vẽ lại; giảm báo nhầm).
- Khung **đạt** có mệnh đề **rủi ro cao**: asym / headwear khi quay lưng; gaze khi có thoại; skill — (giảm bỏ sót kiểu K3).
- **Bất đồng** code ↔ chuyên viên, hoặc giữa C1 và C2 trên cùng chủ thể.
- Mệnh đề chặn-khi-sai có độ chắc **low** / `unclear`.
Ước tính 20–35 % khung có ít nhất 1 lý do (đo ở giai đoạn 3).

### 10.2 Độc lập thật
- **Khác model**: chuyên viên Sonnet 5 (`DEFAULT_MODEL` hiện tại), trọng tài Opus 5.5 (giá niêm yết $4/$20 / triệu token — `data/pricing.json`).
- **Khác đầu vào**: trọng tài xem **cặp bộ phận phóng to + ảnh chuẩn + số đo**, không xem lại khung đầy đủ trước.
- **Chấm mù trước**: trọng tài trả lời mệnh đề **trước khi** được xem kết luận chuyên viên; code so hai kết quả. Không "đọc đáp án rồi đồng ý".

### 10.3 Ra
`confirm` (giữ kết luận) · `overturn` (đổi, kèm lý do + vùng) · `escalate` (về người, kèm câu hỏi cụ thể). Hai bên mâu thuẫn và trọng tài độ
chắc low → `escalate`. Mọi `overturn` / `escalate` thành ca trong sổ kinh nghiệm khi người dùng xác nhận.

### 10.4 Ca rất khó
Trọng tài được gọi `qc_agent` (agent điều tra hiện có, chế độ chấm từng khung, có trần cứng) cho **một** khung, chỉ khi mệnh đề ưu tiên 1 vẫn
`escalate` và shot là ⭐ / money shot. Mặc định tắt (tốn tiền, đã thấy khó kiểm soát ở S7.1).

## 11. [E] Director duyệt cảnh

- **Khi**: sau trọng tài, khi **không còn khung "chặn" chưa vẽ lại** trong cảnh (mọi khung đạt / nhỏ / doubt; khung doubt được đánh dấu cho
  Director biết) — duyệt kể chuyện trên bộ khung sẽ thật sự đi tiếp, không trên khung sắp bị thay.
- **Đầu vào**: tấm ghép storyboard của cả cảnh **theo thứ tự**, thời lượng từng shot, thoại; **sau đó** mới là ý đồ của chính Director
  (`emotional_intent`, `beat`, `knowledge_gap`, `motif`, `why`) — xem hình trước, đọc ý đồ sau (giảm "tác giả thấy điều mình muốn").
- **Phiên mới**, không mang hội thoại lập kế hoạch cũ.
- **Hỏi theo người xem** (director.md Đ1–Đ3, `story_check` "người xem lần đầu" đã có): tắt tiếng còn hiểu không; người xem biết gì ở cảnh này
  (đúng `knowledge_gap`?); cú xoay giá trị (`beat.value`) có thấy trên hình; gieo–gặt có hình gieo; nhịp (shot thừa / thiếu); cảm xúc chủ đạo.
- **Ra** (có cấu trúc): `approve` + 1 câu "cảnh kể được gì" · `redraw` shot X + lý do theo ý đồ + `fix_en` (tối đa 2 lần / shot, đổi đầu vào —
  CHUAN_XAY_DUNG) · `replan` (đổi cách kể shot / cảnh — vd T5: cận mặt diễn tinh tế hỏng → kể bằng hành động) → **cổng người duyệt** nếu đổi nội
  dung kịch bản.
- **Không** được ghi đè kết luận chặn của tổ QC về lỗi cứng (identity, asym, headwear, count). Bất đồng Director ↔ tổ → người dùng xem kèm lý
  do hai bên.
- Chi phí: 1 lời gọi / cảnh (Sonnet 5 hoặc model Director đang dùng), ước ≈ 0,02–0,04 USD.
- Kết luận Director được người xác nhận → ca "kể chuyện" trong sổ kinh nghiệm (stage `director_review`) → Director lập kế hoạch kịch bản sau
  đọc được (vòng học nhà máy).

## 12. [F][G] Người dùng, sổ kinh nghiệm, học

### 12.1 Cổng duyệt
- Bước 2 (ảnh) giữ nguyên chỗ duyệt; thêm cho mỗi khung: kết luận tổ + trọng tài, mệnh đề sai kèm **ảnh cắt bằng chứng**, sắp theo ưu tiên.
- **Lấy mẫu**: 5–10 % khung "đạt" (ưu tiên khung rủi ro cao) hiện cho người dùng chấm nhanh — đo tỉ lệ bỏ sót thật.
- **Màn gắn nhãn nhanh** (mới): đạt / nhỏ / chặn + 1 dòng lý do + (tùy) chọn mệnh đề sai. Dùng cho bộ đo vàng và lấy mẫu.

### 12.2 Thống kê mẫu câu hỏi
Mỗi mẫu (vd `headwear:MAXIM:behind`) đếm: số lần hỏi, đúng / sai so người, báo nhầm, bỏ sót, độ chắc. Mẫu báo nhầm > 20 % → hạ thành "cần số
đo code mới được chặn"; mẫu bỏ sót > 0 ở ưu tiên 1 → luôn gọi trọng tài khi "đạt". Thay đổi **đề xuất**, người dùng duyệt.

### 12.3 Loại lỗi mới
`other_issues` được người xác nhận ≥ 2 lần (≥ 2 khung) → đề xuất loại lỗi mới + mẫu câu hỏi + mục playbook; duyệt rồi mới dùng.

### 12.4 Sổ kinh nghiệm (`core/experience.py` — đã có)
Thêm `stage` mới: `qc_team` (kết luận từng mệnh đề), `qc_arbiter`, `director_review`. Thêm cột `template` (mẫu câu hỏi) để thống kê 12.2 —
đổi bảng `experience_cases` bằng `ALTER TABLE … ADD COLUMN` trong `experience.ensure` (bảng mới tạo 01/10, chưa ai khác đọc).
Khâu Director lập kế hoạch đọc ca `director_review` + ca QC thất bại lặp lại của thực thể (vd "cận Kelly khóc hay trôi mặt").

## 13. Thứ tự tham gia của vai & song song
- Mỗi khung: T0 → (C1 ‖ C2) → trọng tài nếu cần. Mỗi cảnh: C3 sau khi đủ khung → Director.
- Nhiều cảnh / nhiều dự án: **hàng đợi có ưu tiên** — (1) khung đang chặn bước làm video, (2) khung shot ⭐, (3) còn lại; khung không gấp gom
  **Batch API** (tài liệu Claude API: rẻ 50 %, chạy nền, kết quả không theo thứ tự — khớp bằng `custom_id`; không bảo đảm thời gian xong →
  chỉ cho khung không gấp).
- Giới hạn song song theo tốc độ API; lỗi 429 / tạm → thử lại (đã có trong `llm_runner`); lỗi đầu vào → doubt, không lặp.

## 14. Khóa tiền (nhiều lớp)
| Lớp | Có sẵn | Mới |
|---|---|---|
| mỗi lời gọi | `llm_runner` giữ trước theo max_tokens | đặt max_tokens theo số mệnh đề (≈ 120 token / mệnh đề + 200) |
| mỗi khung / cảnh | `spend_cap` (agent cũ) | trần khung = dự đoán × 1,5; trần cảnh |
| khâu dự án | `project_budget` (`claude_qc`) | tiền nghiệm thu tính vào dự án riêng (đã có `--bill-project`) |
| đợt thử | `budget` (`llm_usd`) | — |
| theo giờ | — | trần USD / giờ cho toàn bộ QC (một dự án lỗi không ăn hết của dự án khác) |
| ước tính trước | `cost` | màn "QC cảnh này ≈ X USD" trước khi chạy (số lời gọi × giá dự đoán) |

## 15. Bộ đo vàng, chạy lại offline, cổng nghiệm thu

### 15.1 Bộ đo
| Bộ | Nguồn | Dùng để |
|---|---|---|
| **Phát triển** | #8: 33 khung lượt 1 + lượt 2–3 (nhãn người + `labels_v2`) | sửa / chỉnh — **không** dùng để kết luận chất lượng |
| **Độc lập** | dự án khác: các khung người dùng đã loại / duyệt có ghi chú (sổ kinh nghiệm: #1, #2, #3, #4, #7, #11, #12 ≈ 56 ca ảnh, đã bỏ 12 quyết định do script thử — mục 20) **sau khi người dùng xác nhận nhãn**; cộng 20–30 khung #13–#15 người dùng gắn nhãn mới | đo chất lượng thật — **không** được nhìn khi sửa |
Ghi chú: ghi chú loại ảnh cũ nhiều câu là "câu sửa gửi model" (vd "Use the attached … background"), không phải mô tả lỗi → cần người xác nhận
lại nhãn trước khi vào bộ độc lập.

### 15.2 Chạy lại offline
- Mỗi lần chạy thật lưu **trọn yêu cầu + câu trả lời** từng lời gọi (`qc_team/<run>/calls.jsonl`, không lưu khóa API).
- Công cụ `replay`: client giả trả lại đúng câu trả lời đã ghi theo thứ tự → chạy code mới trên bản ghi cũ **0 USD**: bắt lỗi điều phối / luật
  kết luận / gộp kết quả (loại lỗi đã tốn tiền ở S7.1).
- Thay đổi prompt / ảnh gửi → câu trả lời cũ không còn hợp lệ → phải đo thật (hỏi trước), nhưng mọi thay đổi **code** đều qua replay trước.

### 15.3 Cổng
| Cổng | Điều kiện | Sau cổng |
|---|---|---|
| G1 code | test + replay qua | được chạy đo trả tiền |
| G2 chuyên viên Nhân vật | bộ phát triển: recall chặn nhân vật ≥ 90 %, báo nhầm ≤ 10 % | làm C2, C3 |
| G3 tổ + trọng tài | **bộ độc lập**: recall ≥ 90 %, báo nhầm ≤ 10 %, doubt ≤ 15 % | bật `qc_team` ở chế độ **chỉ báo** (người vẫn duyệt hết) |
| G4 tin cậy | 2 dự án thật liên tiếp: lấy mẫu người không thấy bỏ sót chặn | cho tổ **tự giữ / tự vẽ lại** (tương đương `scene_qc_trusted`) |
| G5 Director | 2 dự án: người dùng đồng ý ≥ 80 % kết luận Director | bật Director duyệt cuối mặc định |

## 16. Chi phí ước tính (CHƯA ĐO — để chọn hướng; đo ở giai đoạn 3)
Giả định: Sonnet 5 ($2 vào / $10 ra / triệu token; đọc cache ≈ 0,1× giá vào, ghi cache ≈ 1,25× một lần / cảnh), ảnh 768 px dọc 9:16 ≈ 1 400
token (rộng × cao / 750), ảnh cắt 384 px ≈ 200–300 token; chuyên viên tắt suy nghĩ (mục 8.1).
| Vai | Mỗi lần gọi | Gọi bao nhiêu | ≈ USD / khung |
|---|---|---|---|
| C1 Nhân vật | ≈ 4 000 token vào mới + 10 000 đọc cache + 600 ra | 1 / khung | ≈ 0,016 |
| C2 Diễn xuất | ≈ 3 000 + 8 000 cache + 500 ra | 1 / khung | ≈ 0,013 |
| C3 Cảnh | ≈ 6 000 + 4 000 cache + 800 ra / cảnh 6 khung | 1 / cảnh | ≈ 0,004 |
| Trọng tài (Opus 5.5, có suy nghĩ effort low–medium) | ≈ 3 000 vào + 600 ra + 500–2 000 token suy nghĩ ≈ 0,034–0,064 | 20–35 % khung | ≈ 0,007–0,022 |
| Director | ≈ 0,03 / cảnh 6 khung | 1 / cảnh | ≈ 0,005 |
| **Tổng** | | | **≈ 0,045–0,06 đồng bộ · ≈ 0,03–0,04 nếu C1–C3 qua Batch** |
So sánh: agent điều tra S7.1 lần 7 đo thật ≈ 0,069 USD / khung có kết luận (0,276 / 4) và không bảo đảm đủ kết quả. Phương án tối giản (chỉ
C1 + luật code) ≈ 0,02 / khung — là cấu hình được code ở GĐ2 và đo ở GĐ3.

## 17. Phạm vi
- **Giai đoạn đầu: ảnh storyboard / khung đầu** (nơi lỗi rẻ nhất để sửa).
- **Clip video**: cùng kiến trúc sau (tầng 0 `clip_measure` đã có: trôi mặt, giật, khớp môi, dấu tham chiếu lọt, viền lạ; mệnh đề từ `motion` +
  `dialogue`), giai đoạn sau G4.
- Không đổi: cổng duyệt của dashboard, `qc_scene.apply`, nhãn trạng thái job.

## 18. Lộ trình
| GĐ | Việc | Tiền | Cổng |
|---|---|---|---|
| 0 | Người dùng duyệt tài liệu này (+ câu hỏi mục 19) | 0 | — |
| 1 | Bộ đo vàng (phát triển + độc lập — màn gắn nhãn nhanh; người dùng xác nhận nhãn); sửa bộ chấm điểm (doubt ≠ bắt được); ghi trọn lời gọi + `replay` | 0 | G1 |
| 2 | [A] bộ dịch đặc tả + [B] tầng 0 mới (hướng mắt — model có sẵn; Pose — cần tải; cắt cặp; màu trời; kiến trúc) + **C1 Nhân vật** + bảng luật 9 + `llm_runner` nhận `output_config.format` và `thinking` theo vai (hiện `converse` chưa có) — sau cờ `qc_team` TẮT | 0 | G1 |
| 3 | Đo C1 trên bộ phát triển rồi bộ độc lập | ≈ 0,3–0,6 USD (hỏi trước) | G2 |
| 4 | C2, C3, trọng tài; đo cả tổ trên bộ độc lập | ≈ 0,5–1,0 USD (hỏi trước) | G3 |
| 5 | Bật chỉ báo trên dự án thật kế tiếp; lấy mẫu người; Batch API + hàng đợi | theo dự án | G4 |
| 6 | Director duyệt cảnh; đo đồng thuận với người dùng | ≈ 0,05 USD / cảnh | G5 |
| 7 | Clip video cùng kiến trúc | sau | — |

## 18b. Rủi ro và cách giảm
| Rủi ro | Dấu hiệu | Cách giảm |
|---|---|---|
| Mốc mặt / mống mắt MediaPipe sai trên mặt 3D cách điệu FF | hướng mắt code ≠ nhãn người trên bộ phát triển | đo ở GĐ2 (0 USD) trước khi dùng; đã có bằng chứng mốc môi chạy được trên clip #8 khi cắt mặt bằng YuNet; sai nhiều → để model phán, code chỉ gợi ý |
| Pose không bắt được người bị che / cỡ cận | `not_measurable` nhiều | mệnh đề chuyển chuyên viên kèm ca mẫu; trọng tài nếu chặn-khi-sai |
| Bộ dịch đặc tả sinh mệnh đề sai vì chữ bảng shot mơ hồ | báo nhầm tập trung ở 1 mẫu | mỗi mệnh đề giữ `source` để truy; mẫu báo nhầm > 20 % tự hạ mức (12.2); mâu thuẫn bảng shot → `plan_conflict` cho người (6.5) |
| Tắt suy nghĩ làm chuyên viên kém | recall giai đoạn 3 thấp | bật suy nghĩ effort `low` cho C1 trước, đo lại; ghi giá thật |
| Trọng tài cùng sai với chuyên viên (lỗi tương quan) | bỏ sót ca rủi ro cao dù có trọng tài | khác model + khác đầu vào + chấm mù trước (10.2); lấy mẫu người (12.1) đo bỏ sót thật |
| Thêm vai làm hệ thống phức tạp, lỗi đan nhau như S7.1 | lỗi điều phối | code điều phối không vòng lặp; replay offline mọi thay đổi code (15.2); xây từng vai, qua cổng mới thêm vai (18) |
| Chi phí vượt ước tính (ảnh nhiều token hơn, cache trượt) | giá / khung > 0,06 | màn ước tính trước khi chạy; trần khung = dự đoán × 1,5; Batch cho khung không gấp; bỏ C2 cho khung không có thoại / người nghe |
| Nhãn người không nhất quán (đã gặp: nhãn lượt 1 xét trái/phải theo mép khung) | trọng tài / tổ "sai" so nhãn nhưng thật ra nhãn sai | ca bất đồng hiện cho người xem lại kèm bằng chứng; sửa nhãn có lý do (như `labels_v2`) |
| Quyết định do script thử lẫn vào dữ liệu "người" | ca giả trong sổ / bộ đo | dấu `[thử tự động]` + lọc (đã sửa — mục 20) |

## 19a. Quyết định của người dùng (01/10) — thay cho phần liên quan ở các mục trên
1. **Không tải Pose lúc này.** Bên trái/phải không cần đo cả dáng người (dáng / cỡ người mỗi nhân vật khác nhau là đúng). Cách làm thay:
   quay mặt hay quay lưng = code dò mặt (YuNet thấy mặt → quay mặt; không thấy mặt mà thấy đầu → quay lưng); tâm thân ≈ tâm đầu / mặt; câu hỏi
   gửi model hỏi thẳng "chi tiết X nằm ở tay TRÁI hay PHẢI của chính người đó" kèm cặp ảnh cắt + ảnh chuẩn; trọng tài Opus 5.5 kiểm khi chặn.
   Pose chỉ thêm nếu GĐ3 đo thấy lỗi trái/phải vẫn còn (khi đó hỏi lại). Mục 7.2 / 7.3 / 7.4 / 18 GĐ2 hiểu theo quyết định này.
2. **Trọng tài dùng Opus 5.5** — thử như mục 10.
3. **Bộ độc lập gắn nhãn trên Google Sheet** "Gắn nhãn bộ đo QC (01-10)" (134 khung #1, #2, #3, #4, #7, #10, #11, #12, #13; cột chọn Đạt / Nhỏ /
   Chặn + loại lỗi + ghi chú) + trang xem ảnh riêng tư "Bộ khung đo QC" trên claude.ai (mỗi dòng Sheet có link tới đúng ảnh). Claude đọc lại
   Sheet qua Google Drive khi người dùng điền xong.
4. **Ngưỡng nghiệm thu giữ nguyên**: bắt ≥ 90 % khung chặn, báo nhầm ≤ 10 %, doubt ≤ 15 %.
5. **Director duyệt mọi cảnh ở mức nhẹ, cảnh then chốt duyệt kỹ.** Mức nhẹ: 1 lời gọi / cảnh, chỉ tấm ghép storyboard + câu hỏi "kể được gì,
   có chỗ nào người xem lạc", trả `approve` hoặc nêu tối đa 1 shot. Mức kỹ (cảnh có shot ⭐ / money shot / thoại then chốt / `beat.turn`): đầy đủ
   như mục 11. Thứ tự duyệt: cảnh then chốt trước.
6. **`qc_agent` (agent điều tra)**: chọn phương án tối ưu = giữ làm công cụ trọng tài cho ca rất khó, **tắt mặc định** (0 USD khi không dùng,
   không phải viết lại nếu cần), không làm đường chính (mục 10.4).

## 19. Câu hỏi đã hỏi người dùng (trả lời ở 19a)
1. Cho tải **MediaPipe Pose Landmarker** (1 file model công khai của Google, ≈ 5–30 MB tùy bản lite / full / heavy) vào `data/models/` để đo bên thân / tư thế?
2. Trọng tài dùng **Opus 5.5** (đắt gấp 2 Sonnet 5 / token) — hay thử Sonnet 5 với đầu vào khác trước?
3. **Bộ độc lập**: bạn dành ≈ 20–30 phút gắn nhãn 20–30 khung #13–#15 + xác nhận ≈ 56 ca cũ trên màn gắn nhãn nhanh?
4. Ngưỡng nghiệm thu mục 2 / 15.3 (90 % / 10 % / 15 %) có đúng mong muốn?
5. Director duyệt cuối: **mọi cảnh** hay chỉ cảnh có shot ⭐ / thoại then chốt (rẻ hơn)?
6. `qc_agent` (agent điều tra) chuyển thành công cụ trọng tài cho ca rất khó (tắt mặc định) — đồng ý không dùng làm đường chính nữa?

## 20. Biên bản rà soát (01/10, sau khi viết — đối chiếu từng khẳng định với code / dữ liệu thật, rồi đọc lại toàn bộ 2 lượt)

### 20.1 Khẳng định đã kiểm bằng code / dữ liệu
| Khẳng định | Cách kiểm | Kết quả |
|---|---|---|
| Trường bảng shot Director (mục 6.2) | đếm khóa `scenes.data` 62 shot #8, #10–#15 trên CSDL thật | có đủ: characters, blocking, performance{face, eyes, body, listener, …}, action, end_state, size, angle, lens_mm, time, lighting, weather, mood, location, plate_spot, dialogue, skill_phase, motif, knowledge_gap, beat, emotional_intent, on_screen_text, continuous_with_next, camera_setup, why |
| Mã tầng 0 hiện có (7.1) | đọc `qc_scene.check_frame` | blank, stacked_tiers, no_face, shot_size, top_bar, dark_face, extra_faces — đúng |
| Model mốc mặt có sẵn; mediapipe đã cài | liệt kê `data/models/`, `import mediapipe` | `face_landmarker.task`, YuNet có; mediapipe 1.0.1; **Pose chưa có** (câu hỏi 1) |
| Hồ sơ Kho có `identity, must_keep, may_change, forbidden, height_m, build` + `view_notes` | `assets.PROFILE_KEYS`; `view_notes` của KENTA trên CSDL | đúng |
| Quy tắc bên thân đã có bằng code | `qc_agent.arm_from_side` + test | đúng |
| Sổ kinh nghiệm chọn ca theo người / hướng, không lộ bản khác của shot đang chấm | `experience.relevant` + 6 test; chạy khô cảnh 2 #8 | đúng |
| Giá Claude | `data/pricing.json` | Sonnet 5 $2/$10, Opus 5.5 $4/$20 — đúng |
| Structured outputs hỗ trợ `enum`, không min/max; chạy với Sonnet 5, Opus 5.5, Batch | tài liệu Claude API (skill claude-api) | đúng |
| Sonnet 5 bỏ trống `thinking` = suy nghĩ thích ứng; Opus 5.5 không tắt được; Sonnet 5.5 dùng `between_tools` | tài liệu Claude API | đúng → đã thêm cấu hình suy nghĩ theo vai (8.1) |
| Ép gọi công cụ chạy trên Sonnet 5 | 1 lời gọi API thật 01/10 (≈ 0,002 USD) | trả đúng `record` — nhưng thiết kế dùng structured outputs để chạy cả dòng 5.5 |
| Lỗi 429 / 5xx được thử lại | `llm_runner` dòng 526 | đúng |
| Chi phí S7.1 ≈ 1,94 USD, 7 lần | cộng 7 lần: 0,13 + 0,33 + 0,209 + 0,325 + 0,395 + 0,268 (+0,002 thử API) + 0,276 | 1,935 — đúng |
| Phép tính mục 16 | tính lại từng dòng | đúng sau sửa (trọng tài có suy nghĩ; tổng 0,045–0,06; Batch 0,03–0,04) |

### 20.2 Sai / thiếu tìm thấy — đã sửa
| # | Chỗ | Sai | Sửa |
|---|---|---|---|
| 1 | 9.3 | "11/11 khung chặn có lỗi nhân vật / hướng" | đếm lại sau `labels_v2`: **9 khung chặn**, 9/9 khóa nhân vật (7) hoặc hướng nhìn (2) |
| 2 | **Dữ liệu thật** | 12 quyết định do script thử của Claude (7 lần duyệt "Claude xem ảnh trước khi duyệt", 5 lần loại S5.5' #13) được ghi `reviewer_type='user'` → lọt vào sổ kinh nghiệm như ca của người | ghi chú 12 dòng `review_log` thêm dấu `[thử tự động]` (CSDL chỉ cho `user` / `ai_agent`); xóa 12 ca khỏi sổ; `experience.import_review_log` bỏ dòng có dấu; 3 script thử ghi dấu từ nay (lệnh loại tách câu sửa tiếng Anh qua `fix=` để model không nhận dấu); test |
| 3 | 8.1, 16 | ước tính giá bỏ qua token suy nghĩ (Sonnet 5 mặc định bật) | đặt suy nghĩ theo vai (C1–C3 tắt, trọng tài effort low–medium); tính lại giá; ngưỡng giá 0,05 → 0,06 |
| 4 | 15.1, 19 | danh sách dự án nguồn bộ độc lập thiếu #4, #12, lẫn #13 (toàn quyết định script) | sửa danh sách, ≈ 56 ca |
| 5 | 6.1, 9.1 | loại `layout` dùng ở 6.2 / 6.3 nhưng thiếu trong danh sách loại và bảng mức | thêm |
| 6 | 4 | sơ đồ thiếu vòng vẽ lại sau khi trọng tài xác nhận chặn | thêm |
| 7 | 11 | Director chạy khi khung chặn "đang chờ" → duyệt trên khung sắp bị thay | chỉ chạy khi không còn khung chặn chưa vẽ lại |
| 8 | 18 GĐ2 | thiếu việc `llm_runner.converse` nhận `output_config.format` / `thinking` (hiện chưa có) | thêm vào GĐ2 |
| 9 | 13 | Batch không bảo đảm thời gian | ghi rõ: chỉ khung không gấp |
| 10 | 19 | dung lượng Pose "vài chục MB" ≠ mục 7.2 | thống nhất ≈ 5–30 MB |
| 11 | 12.4 | thêm cột `template` mà chưa nói cách đổi bảng | `ALTER TABLE … ADD COLUMN` trong `experience.ensure` |
| 12 | `core/effectiveness.py` | thống kê hiệu quả vẫn đếm 12 quyết định script là "người" | 2 truy vấn bỏ ghi chú có dấu `[thử tự động]` |

### 20.3 Còn mở (không sửa được bằng rà soát — cần đo hoặc người dùng quyết)
- Độ đúng hướng mắt / Pose trên mặt 3D cách điệu FF: **chưa đo** (GĐ2, 0 USD).
- Mọi con số giá mục 16: **ước tính**, đo ở GĐ3.
- Ngưỡng "chắc" của tầng 0 (7.5): đặt từ bộ đo vàng, chưa có.
- 6 câu hỏi mục 19.

## 21. Tiến độ (cập nhật khi làm)
**01/10 — GĐ1 + GĐ2 code xong (0 USD), cờ `qc_team` TẮT:**
- `core/qc_spec.py` bộ dịch đặc tả (bảng shot + hồ sơ Kho → mệnh đề có loại / vai / ưu tiên / mức; mã ổn định để chạy lại; phát hiện bảng shot
  tự mâu thuẫn). `core/qc_measure.py` tầng 0 (mặt YuNet, hướng mắt MediaPipe mống mắt, màu trời). `core/qc_rules.py` bảng luật mục 9.
  `core/qc_team.py` C1 Nhân vật (1 lời gọi có cấu trúc `llm_runner.ask_json`, suy nghĩ tắt) + `RecordingClient` / `ReplayClient`.
  `core/qc_golden.py` bộ đo vàng + chấm điểm (doubt ≠ bắt được). `tools/experiments/qc_team_eval.py` (kế hoạch / chạy thật có ghi / chạy lại).
  Test: `tests/test_qc_team.py` (19); toàn bộ 1616 qua.
- **Bằng chứng chạy khô trên dữ liệu thật (0 USD):** hướng mắt đo bằng code so nhãn người trên 5 khung #8 có nhãn hướng nhìn: 4/5 đúng,
  ca sai ở độ chắc "medium" (không thành kết luận). Chạy khô cả chuỗi trên 33 khung bộ phát triển (Claude giả): không lỗi, TB 9,7 câu hỏi
  C1 / khung, ~1 s / khung; **khung S2·4 (lỗi hướng nhìn thật) được code tự kết luận "chắc chắn sai" — không cần model**; bảng shot mâu thuẫn:
  4 khung (3 "Kelly đặt trong khung mà characters không có", 1 "OTS chỉ 1 người" = đúng ví dụ playbook E). 2 lỗi của chính code mới tìm
  ra nhờ chạy khô (báo mâu thuẫn thừa với tên người ngoài khung; không chọn được mặt khi khung 2 mặt) — đã sửa + test.
- **Chờ:** (a) GĐ3 đo C1 trên bộ phát triển ≈ 0,86 USD (ước tính, hỏi trước); (b) người dùng gắn nhãn Google Sheet → bộ độc lập.
- **Người dùng 01/10 (sau GĐ2):** duyệt GĐ3 (≈ 0,86 USD); yêu cầu dùng các tầng miễn phí lọc trước 134 khung bộ độc lập (nhiều khung cũ lỗi rõ) và thêm phần tích chọn nhãn ngay trên trang xem ảnh thay vì chỉ Google Sheet — giao session sau (TODO.md mục 01/10 BÀN GIAO).

**01/10 — Lọc trước bộ độc lập bằng tầng miễn phí (việc 2 bàn giao, 0 USD):** `tools/experiments/qc_prefilter.py` (CSDL chỉ đọc; test
`tests/test_qc_prefilter.py` 10). 134 khung dựng lại từ CSDL = ảnh `image_gen` của #1 #2 #3 #4 #7 #10 #11 #12 #13 (kể cả thùng rác), bỏ 4 job
hủy — khớp số 134 của Sheet (id `P<dự án>-J<job>`). Mỗi khung: tầng 0 (khung một màu, số mặt so bảng shot, hướng mắt chắc chắn sai, dải trời
so giờ) + bảng shot tự mâu thuẫn + lịch sử có sẵn trong `review_log` phân theo nguồn: **người** (độ tin cao) · **người bấm theo QC đồng bộ**
(ghi chú "Đồng bộ cả bộ:" do QC Claude viết, người bấm gen lại — vừa) · **phiên vận hành** (vừa / thấp) · **[thử tự động]** và **QC tự động
cũ** (thấp). Loại lỗi lấy theo từ khóa xuất hiện SỚM NHẤT trong ghi chú (bỏ mệnh đề "Keep …"). Điểm `qc_results` cũ chỉ in kèm, không dùng
gợi ý. Ra `data/qc_golden/prefilter.json` + `prefilter.csv` (ngoài git — chạy lại ≈ 1 phút).
- **Kết quả:** gợi ý **Chặn 58** (cao 17 · vừa 15 · thấp 26) — Nhân vật 30, Bối cảnh / kiến trúc 17, Kỹ thuật 4, Liền mạch / ánh sáng 4,
  Hướng nhìn 1, Khác 2; **Đạt 52** (vừa 8 · thấp 44); **để trống 24** (8 có cờ tầng 0 nghi: 3 mặt / 1 người, cận mà không thấy mặt, trời tối
  trong cảnh ban ngày; 16 không có bằng chứng miễn phí — chủ yếu #10, #11, #13 S4·1–5 bản sau). Tầng 0 KHÔNG có phát hiện "chắc chắn" nào
  trên 134 khung (không khung trống, không hướng mắt chắc chắn sai) — gợi ý chủ yếu đến từ quyết định cũ; người dùng vẫn phải xác nhận.
- **Việc kế (3):** đưa gợi ý vào trang xem ảnh có tích nhãn.

**01/10 — GĐ3 đo C1 trên bộ phát triển #8 (người dùng chạy; run `data/qc_golden/runs/20261001-104111`, 0,611 USD = 0,019 USD / khung):**
- **Số:** 32/33 khung có kết quả (job 333 bị cắt ở giới hạn 1 730 token). Loại "Nhân vật": bắt 5/6 khung chặn; mọi loại: 5/8. **Báo nhầm
  12/24 (50 %)**, doubt 18,8 % → **không qua cổng** (≤ 10 % / ≤ 15 %). Token TB / khung: vào 2 728 mới + 2 790 đọc cache, ra 1 137.
- **Nguyên nhân 1 — trái/phải của Kenta (11/12 ca báo nhầm):** mọi ca báo nhầm đều có mệnh đề `asym` của KENTA "sai". Kiểm bằng mắt job 337
  (nhãn đạt): Kenta quay mặt, tay băng trắng ở trái khung = tay PHẢI của Kenta, găng giáp + bắp tay trần + sao ở phải khung = bên TRÁI → **đúng
  hồ sơ**; model ghi "găng giáp nằm bên trái khung" và "sao ở vai phải khung … là vai PHẢI" — **sai cả đọc vị trí lẫn đổi chiều**, và tự
  mâu thuẫn giữa các khung. Luật trái/phải trong lời dặn (mục 8.2) không đủ: model vẫn suy luận đổi chiều sai.
- **Nguyên nhân 2 — "bắt được" là nhờ may:** 4 khung chặn thật (324, 330, 332, 356) có lỗi **mũ Maxim đội XUÔI khi quay lưng**. Model trả
  lời mệnh đề mũ "đúng, độ chắc cao" với bằng chứng *"thấy khóa cài mũ ở gáy, không thấy lưỡi trai"* — tức **nhìn đúng dấu hiệu lỗi nhưng kết
  luận ngược**. Các khung này bị "chặn" chỉ vì mệnh đề trái/phải Kenta sai ngẫu nhiên. Ca 350 (sao vai phải) cũng lẫn trong các lời sai trái/phải.
  → recall thật của C1 trên lỗi mũ / trái-phải ≈ 0.
- **Nguyên nhân 3 — lỗi code (miễn phí, chạy lại được bằng replay):** (a) job 325: tầng 0 đo **chắc chắn** Maxim nhìn sai hướng (`certain_fail`)
  nhưng khung vẫn "pass" — `review_frame` chỉ tính mệnh đề vai C1 / T0, mệnh đề hướng nhìn (C2) bị bỏ dù code đã chắc; (b) job 352: blocking
  "looking off-screen frame-left toward…" không khớp `_LOOK` → không sinh mệnh đề hướng nhìn; (c) job 333: `C1_MAX_TOKENS` thiếu cho 13+ mệnh đề.
- **Khác:** 2 ca báo nhầm còn lại là `count` khi người thừa chỉ lộ một phần / mờ phía sau (323, 326 — nhãn "nhỏ"). Doubt (6 khung) đều do
  model trả "unclear" cho `asym` Kenta.
- **Hướng sửa đề xuất (chờ người dùng quyết):** model chỉ **khai điều nhìn thấy** dạng chọn sẵn, **code áp luật**: mũ → "ở gáy thấy: lưỡi trai /
  dây-khóa / không thấy"; trái/phải → "chi tiết X ở nửa TRÁI hay PHẢI của ẢNH so với mặt / đầu người đó" (hoặc "cùng phía ẢNH với ảnh chuẩn
  hay ngược"), code đổi chiều theo hướng máy (YuNet thấy mặt = quay mặt). Sửa (a)(b)(c) + replay 0 USD; rồi chạy lại GĐ3 ≈ 0,6 USD. Nếu
  trái/phải vẫn sai khi model chỉ khai vị trí trong ảnh → theo quyết định 19a hỏi lại Pose.

**01/10 — Sửa sau GĐ3 (người dùng duyệt hướng "model khai quan sát, code áp luật"; 0 USD):**
- **3 lỗi code:** (a) mệnh đề vai khác (vd hướng nhìn C2) mà code đã **chắc** thì vẫn tính vào kết luận khung (`qc_team.review_frame` +
  `qc_rules`: không có câu trả lời model mà code chắc → dùng kết quả code); (b) `_LOOK` nhận "looking off-screen frame-left toward…",
  "looking off-frame right", "looks off toward…"; (c) trần token C1 400 + 170 / mệnh đề. **Chạy lại từ bản ghi GĐ3 (0 USD,
  run `20261001-113214`):** job 325 bị chặn đúng nhờ số đo hướng nhìn → mọi loại bắt 6/8 (trước 5/8); job 352 nay có mệnh đề hướng
  nhìn nhưng mống mắt đo "trái, độ chắc vừa" — ngược nhãn người (đồng tử lệch phải) → chưa bắt; ghi lại để chỉnh ngưỡng / cách đo ở C2.
- **Model khai, code kết luận** (`qc_spec` gắn `observe` cho `asym` / `headwear` / `count`; `qc_team.ANSWER_SCHEMA` thêm 4 ô chọn sẵn;
  `qc_rules.observed` / `own_side`): trái/phải → `facing` (front / back / profile_facing_image_left / _right, theo THÂN) + `seen_at`
  (nửa trái / phải ẢNH của thân; nghiêng hẳn: near_side / far_side) → code đổi ra bên của chính người đó; khung 1 người mà model khai
  "back" khi YuNet thấy mặt (hoặc "front" cận cảnh mà không thấy mặt) → chưa chắc. Mũ → `cap_marks` (ở trán / ở gáy thấy gì) → code:
  khóa ở trán hoặc lưỡi trai ở gáy = đội ngược. Số người → `extra_people`; người thừa chỉ lộ một phần / mờ phía sau = **nhỏ** (#8 323, 326).
  Câu hỏi gửi model **không còn nói bên đúng** (chữ LEFT/RIGHT thay bằng "one", không gửi mệnh đề / hướng máy của bảng shot cho các mục
  khai); `answer` của model giữ lại để đối chiếu, không dùng. Test: `tests/test_qc_team.py` 27. Chạy khô 33 khung #8 (client giả trả "na"):
  33 yêu cầu dựng được, 207 mục khai, 0 câu lộ chữ bên.
- **Chờ người dùng:** GĐ3 lần 2 ≈ 0,7 USD (LENH_TON_TIEN_CHO_DUYET #11; trần Claude đợt thử còn 0,65 → nâng +0,5).

**01/10 — GĐ3 lần 2 (model khai, code kết luận; người dùng chạy; run `20261001-115335`, 0,653 USD = 0,020 USD / khung, 33/33 khung):**
- **Số:** Nhân vật bắt 6/7, mọi loại 7/9; **báo nhầm 13/24 (54 %)**, doubt 18,2 % → vẫn không qua cổng.
- **Mũ — đã đúng:** 5/5 khung mũ Maxim đội xuôi (324, 330, 332, 333, 356) bị chặn **đúng lý do** (khai "dây/khóa ở gáy" → code kết luận
  đội xuôi), lần 1 không bắt được khung nào vì đúng lý do. 1 báo nhầm: 323 (Maxim quay mặt, khóa ở trán — model khai "ở gáy").
- **Người thừa một phần → nhỏ:** đúng ở 323, 325, 356; 326 model vẫn khai "clear" (Kenta lộ nửa người mép trái) → còn chặn.
- **Trái/phải — vẫn sai, cả khi chỉ khai vị trí:** kiểm bằng mắt 322, 337 (quay mặt, đúng hồ sơ: tay băng ở TRÁI ảnh, găng giáp + sao ở
  PHẢI ảnh) — model khai ngược (tay áo đen "image_right_of_body", sao "image_left_of_body") ở 322 / 328 / 331 / 337 / 341 / 350; khung
  quay lưng (319, 323) cũng khai sai nửa ảnh. Nghi một phần do tên ô `image_right_of_body` bị hiểu thành "bên phải của thân", nhưng khung
  quay lưng sai cả hai cách hiểu → **model không định vị được chi tiết trái/phải trong ảnh** đủ tin để tự chặn.
- **Tính lại không tốn tiền (bỏ mệnh đề trái/phải khỏi tự chặn):** báo nhầm **2/24 = 8,3 %** (qua cổng), doubt 0 %, Nhân vật bắt 5/7
  (sót 347, 350 — chính là 2 lỗi trái/phải). → phần còn lại của C1 (đúng người, mũ, số người) dùng được; trái/phải cần cách khác.
- **Theo quyết định 19a: hỏi lại người dùng** (Pose hoặc cách khác) — xem TODO.

**01/10 — Việc 3: trang gắn nhãn bộ độc lập (thay trang ảnh cũ không mở được từ phiên này):** https://claude.ai/artifact/GhovWc4sPSQe3GciCAoKs1
("Bàn soát khung QC", riêng tư). 134 khung (ảnh thu nhỏ nhúng sẵn) + gợi ý của bước lọc trước (`qc_prefilter.py`) + người trong shot /
cỡ / giờ / blocking; nút Đạt / Nhỏ / Chặn, loại lỗi, ghi chú, "✓ Đúng gợi ý"; lưu ngay vào CSDL của trang (bộ sưu tập `labels`, mã khung
`P<dự án>-J<job>` → {label, category, note, shot, at}). Khung có gợi ý độ tin **cao** (= chính người dùng từng loại ảnh kèm lý do, 17 khung)
tính là đã xác nhận nếu không sửa. Đọc về: `ArtifactData list labels` → gộp với 17 khung độ tin cao → `data/qc_golden/independent.json`
(định dạng `qc_golden.independent_set`). Google Sheet cũ giữ làm dự phòng.

**01/10 — Bộ độc lập đã gắn nhãn (người dùng, trên trang Bàn soát khung QC):** `data/qc_golden/independent.json` (ngoài git; bản gốc còn trong
CSDL trang): 117 nhãn chọn trên trang + 17 theo quyết định loại ảnh cũ = 134. **Chặn 118 · Nhỏ 10 · Đạt 6.** Loại lỗi của khung không đạt:
trống 64, Nhân vật 36, Bối cảnh / kiến trúc 16, Liền mạch / ánh sáng 5, Kỹ thuật 4, Khác 2, Hướng nhìn 1.
- **Gợi ý tự động của bước lọc trước đúng ít:** độ tin "thấp" đúng 22 / 70, "vừa" đúng 15 / 23 → nhiều khung từng được duyệt nay người dùng
  chấm Chặn (chuẩn đã nâng lên so với lúc làm các dự án cũ).
- **Hệ quả cho việc đo:** recall đo tốt (118 khung chặn); **báo nhầm chỉ có 16 khung không chặn để đo** → con số báo nhầm sẽ dao động lớn;
  64 khung chặn chưa ghi loại lỗi → chưa đo được recall riêng từng chuyên viên (C1 chỉ chịu "Nhân vật").

**01/10 — Quyết định người dùng: dừng đo Tổ QC trên dự án cũ.** Các dự án cũ sai sót nhiều (118 / 134 khung Chặn) nên khó dùng để đánh giá;
không ghi thêm loại lỗi, không chạy C1 trả tiền trên bộ độc lập. **Hướng tiếp:** áp dụng Tổ QC trên các dự án mới rồi sửa dần theo kết quả
thật (cổng nghiệm thu đo trên dự án mới). Bộ độc lập + bộ phát triển #8 giữ lại để chạy lại offline khi sửa code.
