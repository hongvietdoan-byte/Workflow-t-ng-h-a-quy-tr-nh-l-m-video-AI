# Agent QC — thiết kế để chạy tự động và NGÀY CÀNG TỐT HƠN (2026-09-27)

Người dùng: "chạy auto hoàn toàn vẫn cần QC và phải có 1 agent QC đích thực theo sát"; "nhiều dự án sẽ phát sinh lỗi khác nhau, công cụ
máy móc có sẵn sẽ không QC ra"; "tối ưu quy trình, tối ưu agent, nhận diện tốt, làm sao để agent ngày càng tốt hơn?"

## 1. Bằng chứng (dự án #8)
| QC | Cách làm | Kết quả |
|---|---|---|
| QC Claude từng ảnh (cũ) | 1 lượt / ảnh, 8 điểm 0–1 | ảnh lỗi 0,67 ≈ ảnh tốt 0,69; tự duyệt 6/16 lỗi rõ |
| QC Claude theo cảnh (lớp 1) | 1 lượt / cảnh, tấm ghép, có/không + bằng chứng | cho qua 6 khung dán + ô đen; báo nhầm 12/21; nhắc lại cờ code |
| Bộ đo bằng code (lớp 0) | cỡ cảnh, sáng mặt, đếm mặt, khung trống | đo đúng cỡ cảnh; báo nhầm 4 (tay = mặt); không hiểu ý đồ |
| **Agent QC (nhiều bước, có công cụ)** | xem đầy đủ, cắt sát, **ghép cùng một chi tiết qua nhiều khung**, so ảnh chuẩn, dùng bộ đo làm gợi ý | **11 chặn đúng** (mũ đội xuôi khi quay sau ×5, tay trái Kenta lật gương ×4, hướng nhìn ×2, hồi tưởng) — người dùng xác nhận; ~41 lượt xem ảnh |
Kết luận: QC tốt là **một quá trình điều tra**, không phải một lần phán. Loại lỗi đắt nhất (lỗi hệ thống lặp qua nhiều khung) chỉ lộ khi đặt
cùng một chi tiết của nhiều khung cạnh nhau.

## 2. Agent QC trong dashboard (thay lớp 1)
**Vòng làm việc (Claude tool use, mỗi cảnh / mỗi đợt):**
1. **Lập kế hoạch soi** từ dữ liệu dự án — tự động, không phụ thuộc Claude đoán:
   - mỗi nhân vật: các chi tiết đặc trưng + chi tiết BẤT ĐỐI XỨNG (từ hồ sơ chuẩn: `must_keep`, `view_notes`) → "dải so sánh" bắt buộc
     (vd. vai trái Kenta ở mọi khung có Kenta; mũ Maxim ở mọi khung có Maxim, tách khung quay trước / quay sau);
   - mỗi shot: cỡ cảnh, ai trái/phải, hướng nhìn, ánh sáng (ngày/đêm/hồi tưởng) từ bảng shot;
   - các "kiểm tra đã học" (mục 3) áp cho dự án này.
2. **Công cụ agent gọi được:** `view(frame, region?, scale?)` (xem đầy đủ / cắt sát), `strip(detail, frames)` (ghép cùng một vùng qua nhiều
   khung — vùng lấy bằng dò người / dò mặt / toạ độ agent chỉ), `compare(frame_region, reference)` (cạnh ảnh chuẩn / ảnh toàn cảnh /
   khung trước), `measure(frame)` (bộ đo lớp 0 — GỢI Ý), `record(frame, issue, evidence_crop, severity, root_cause, fix_en)`.
3. **Kết luận có bằng chứng:** mỗi lỗi lưu kèm vùng cắt; mức `chặn` / `nhỏ`; nguyên nhân gốc → hành động (prompt / ảnh chuẩn / model /
   bảng shot). `chặn` → vẽ lại có câu sửa (tối đa 1 lần cùng lỗi, rồi người); bảng shot sai → người.
4. **Theo sát mọi khâu:** cùng khung làm việc cho clip (khung giữa mỗi shot + điểm cắt so storyboard, cử động, khớp môi), tiếng, bản dựng.
5. **Model:** thử Sonnet 5 và Opus 5.5 trên bộ đo (mục 4) — chọn theo tỉ lệ bắt đúng / tiền, không theo cảm tính.

## 3. Làm sao agent NGÀY CÀNG TỐT HƠN (vòng học)
1. **Mọi quyết định của người là dữ liệu.** Người xác nhận / bác một kết luận của agent, hoặc tự bắt một lỗi agent bỏ sót → lưu thành
   "ca" (ảnh, vùng, loại lỗi, mức, đúng/sai) vào **bộ nhãn** (`data/qc_memory/cases.jsonl`, ngoài git; ảnh cắt kèm theo).
2. **Sổ tay kiểm tra (playbook) có phiên bản** (`knowledge/qc_playbook.md`): mỗi loại lỗi đã xác nhận ≥ 1 lần thành một mục — tên, dấu
   hiệu, **cách soi** (vd. "chi tiết bất đối xứng: ghép dải qua mọi khung, tách quay trước / quay sau"), ví dụ đúng / sai (đường dẫn ca).
   Agent đọc sổ tay mỗi lần chạy → lỗi mới của dự án A thành kiểm tra có sẵn cho dự án B. Loại lỗi hay gặp (≥ 3 ca) và đo được → chuyển
   thành bộ đo code (lớp 0) cho rẻ và chắc.
3. **Phòng từ gốc:** mỗi loại lỗi xác nhận có trường "sửa gốc" (prompt, hồ sơ nhân vật, luật Director) — như `view_notes` vừa thêm cho
   Kenta / Maxim. Lỗi được phòng thì lần sau ít phải bắt.
4. **Bộ đo hồi quy tự chạy khi agent đổi** (prompt, sổ tay, model): chạy lại trên bộ nhãn, báo tỉ lệ bắt đúng lỗi `chặn` và báo nhầm; tụt
   thì không cho dùng bản mới. Kết quả vẽ biểu đồ theo thời gian trên web AI Dev System.
5. **Cổng tin cậy:** chạy tự động chỉ khi bắt đủ lỗi `chặn` đã biết (100 % trên bộ nhãn) và báo nhầm ≤ 10 %. Khi đã tin vẫn **lấy mẫu 10 %**
   khung đã tự duyệt cho người xem nhanh — phát hiện agent trôi dần; lỗi lọt → thành ca mới.
6. **Học từ ngoài dự án:** bộ nhãn chung mọi dự án (theo game / look) — lỗi phổ biến của model ảnh (tay, mặt, lật gương) dùng chung.

## 4. Bộ nhãn hiện có
- 33 khung storyboard mới #8 + kết luận agent đã được người dùng xác nhận (`docs/qc_agent_2026-09-27/verdicts.json`): 11 chặn, 13 nhỏ, 9 đạt.
- 33 ảnh ghép cũ #8 có nhãn lỗi ghép (`tools/experiments/qc_regression.py`): 12 shot lỗi rõ.

## 5. Thứ tự xây
1. Bộ nhãn + sổ tay từ #8 (miễn phí).
2. Công cụ agent (xem / cắt / dải / so / đo / ghi) + vòng tool use + ghi mọi lượt vào `llm_calls` (miễn phí code, test với Claude giả).
3. Đo trên 2 bộ nhãn (tốn Claude API, ước ~1–2 USD mỗi lần đo cả 66 khung) → chọn model.
4. Nối vào luồng: thay lớp 1; cổng tin cậy; lấy mẫu 10 %; nút "đúng / sai" cho người ở cổng storyboard ghi ca mới.
5. Mở rộng sang clip / tiếng / bản dựng.
