# Kế hoạch V3.1: mục tiêu, tiến độ, thời gian hoàn thiện, so với bản cũ (24/10/2026)

Nguồn: `docs/KE_HOACH_AI_VIDEO_PIPELINE_V3_2026-10-20.md` §1–§2, §8; `docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md` §5 (plan_progress 24/10);
`docs/GIAM_SAT_KE_HOACH_V31_2026-10-24.md` (giám sát đợt 1); hộp thư; sổ lỗi `devsys/errors.json`. Không có số nào tính tay ngoài phần ước lượng thời gian (ghi rõ cách tính).

## 1. Mục tiêu của kế hoạch

**Vì sao có V3/V3.1:** sau #31 (Booyah tập 2) và #33, rà lại thấy kế hoạch V2.1 chỉ che ≈ 1/4 lỗi #31 và không che lỗi nào của #33. Có 3 nhóm lỗi lặp
ở cả hai dự án: (1) vận hành Claude / tiến trình / tạm dừng, (2) ước tính giá sai, (3) vị trí người/vật và hình học 3D lệch giữa các shot. Hai nhóm đầu đã làm trả tiền thừa thật.

**5 mục tiêu đo được (V3 §2):**

| # | Mục tiêu | Mốc trước V3 (#31/#33) |
|---|---|---|
| MT1 | 0 lần trả tiền thừa do lỗi hệ thống (gửi trùng, gửi khi tạm dừng, tự gen lại vì đọc file dở, lùi model vì Kho đầy) | có trả thừa thật ở #31 và #33 |
| MT2 | Ước tính giá trước gen lệch sổ chi ≤ 10 % | video nháp ≈ +37 %, bản cao ≈ +24 % |
| MT3 | Gói gửi model đọc trường có cấu trúc (BYĐ v2), lỗi lọt cổng do chữ tự do giảm 50 % | dò chữ tự do |
| MT4 | Vị trí người/vật trong các shot cùng cảnh lấy từ MỘT sơ đồ mặt bằng | tả lại bằng chữ từng shot (lỗi G41–G48 #31) |
| MT5 | QC bắt clip đơ / sai khung đầu trước khi người dùng thấy | QC chấm 0,96 cho clip đơ ở #31 |

Từ 21/10 thêm 3 hướng, đều do người dùng / EP đặt: M6 tổ làm phim có vai chịu trách nhiệm; M8 Dashboard cho người không chuyên, 10 người dùng cùng lúc; M9 (24/10) giám sát theo mốc, tối ưu ghi thẳng vào kế hoạch.

## 2. Đã làm được (24/10)

Tiến độ theo `plan_progress` (tính theo trọng số việc): **68,5 %**, 58/88 việc ✅ (đã thêm M9 hôm nay nên % giảm so với 72,9 %).

| Đợt | Tiến độ | Ghi chú thật |
|---|---:|---|
| M0 Đóng băng, thiết kế | 100 % | cổng đạt thật |
| M1 Nền tin cậy (khóa gửi job, tạm dừng, giá) | 100 % | code xong; **chưa đo trên dự án thật** (0/4 cổng chạy thật) |
| M2 Hợp đồng sản xuất (BYĐ v2) | 87 % | sau cờ TẮT/shadow |
| M3 Thế giới, liên tục (sơ đồ mặt bằng) | 100 % | sau cờ TẮT; chưa có lần gen chứng minh |
| M4 QC + Dashboard | 84 % | Bàn đạo diễn 3D (M4.8) dùng thật ở #34 → lộ lỗi N5, đã sửa 24/10 |
| M5 Sửa chọn lọc + pilot | 54,5 % | pilot A offline ĐẠT; B/C là Cấp 3 trả phí, chưa chạy |
| M6 Tổ làm phim có chủ | 27 % | mới shadow |
| M7 Cờ và cấu hình | 81 % | **0 cờ được khóa** (M7.7 chưa làm) |
| M8 Dashboard người không chuyên | 33 % | an toàn tiền ✅ (M8.0/0b/0c); chế độ Cơ bản đang làm |
| M9 Giám sát | 31 % | mới thêm 24/10 |

**Quan trọng:** giám sát đợt 1 cho thấy 37/55 việc ✅ (tính tới trước M9) mới là "code đã gộp", chưa đạt cổng nghiệm thu chạy thật; điểm giám sát 4,6/10. Chưa mục tiêu
gốc nào (0/5) được đo trên dữ liệu thật (việc M9.2 bổ sung để đo). Sổ lỗi: 91 mục — 60 OPEN, 13 IN_PROGRESS, 16 FIXED_UNVERIFIED, 2 WONT_FIX.

## 3. So với bản cũ (trước V3.1, lúc làm #31/#33): cải thiện rõ ràng

Có bằng chứng (code + test, một phần dùng thật):
1. **An toàn tiền (MT1):** mọi nút tốn tiền trên Dashboard (6 chỗ M8.0 + ~35 nút M8.0b + ~23 nút M8.0c) có giá + xác nhận; lô gửi có xem trước đúng tập + tổng giá + 30 s hoàn tác;
   "Duyệt hết" giữ (HOLD) mục chưa đủ. Một job chỉ một bên gửi kể cả nhiều tiến trình (send_claim); kiểm tạm dừng ngay trước gửi. Trước đây: #31/#33 có gửi trùng / gửi khi tạm dừng.
2. **Báo giá đúng một chỗ (MT2 — một phần):** `pregen_check` in đúng giá nút Gen; #34 dùng thật: báo ≈ 0,22 USD trước khi gen, có ghi sổ chi. Chưa có số đo lệch ≤ 10 % trên nhiều job.
3. **Sân khấu / bàn đạo diễn 3D (MT4 — một phần):** sơ đồ mặt bằng dùng chung theo cảnh, chọn lượt đo theo shot, tấm ghép xem trước. Đang dùng ở #34; trước đây tả vị trí bằng chữ.
4. **Không im lặng khi lỗi:** Tổ rà soát + cổng trước gen chặn và nói lý do (#34: rà xong, mã 0 mới cho gen).
5. **Kiểm thử:** cả bộ 8274 test qua (24/10); mỗi thay đổi có test đỏ→xanh, quy ước 7 rà khu vực liên quan.
6. **Tổ chức build:** 3 phiên Codex chạy song song qua hộp thư sự kiện; AI Dev System chấm và giám sát kế hoạch (đợt 1 bắt được 4 lỗi trạng thái, đã sửa).

Chưa cải thiện thấy được trên sản phẩm:
- Chưa có phim hoàn chỉnh nào làm bằng V3.1 khi bật cờ; ~25 cờ V3.1 còn TẮT → phần lớn cải thiện M2/M3/M4 **chưa tác động lên video thật**.
- MT3, MT5 chưa đo; QC bắt clip đơ có code nhưng sau cờ TẮT.

## 4. Thời gian hoàn thiện (ước lượng)

Còn 29 việc (tổng trọng số 60). Chia 2 loại:

| Loại | Việc | Phụ thuộc | Ước lượng xong |
|---|---|---|---|
| Code 0 USD (Codex làm, phiên chính gộp) | ~22 việc: M2.10 bước 1–2 phần còn, M4.6b/M4.7, M6.0–M6.11, M8.2–M8.4, M9.x | 3 Codex chạy liên tục; nhịp gộp đo 23–24/10 ≈ 4–6 việc/ngày | **30/10 – 01/11** |
| Cổng chạy thật + Cấp 3 (EP quyết, có thể tốn tiền) | M5.4 pilot B, M5.5 pilot C, M7.7 khóa cờ, M7.8, M2.10 bước 3, M6.12, đo KPI M9.2, đo tải M8.3 | dự án thật (#34 đang chạy), EP duyệt từng lô cờ, ngân sách pilot | **07/11 – 14/11** |

Cách tính: việc code = số việc còn ÷ nhịp gộp thật 2 ngày gần nhất, cộng 1–2 ngày rà kỹ/sửa; cổng thật = 1 vòng dự án thật (≈ 3–5 ngày) cho pilot B + 1 vòng cho pilot C,
cộng thời gian EP quyết. Rủi ro làm chậm: hết hạn mức Codex tháng (300 USD, đã dùng ít), phiên chính chạm 5 giờ, lỗi mới khi bật cờ trên dữ liệu thật (như N5).

## 5. Việc kế để rút ngắn

1. M9.2 đo 5 mục tiêu gốc trên bản sao #31/#33 (0 USD) — biết ngay đang cải thiện bao nhiêu.
2. M9.6 → M7.7: gom bằng chứng, EP bật/khóa cờ theo lô trên #34 — để cải thiện tác động lên video thật.
3. M9.1: tách % code và % cổng, để con số tiến độ không đánh giá quá cao.
