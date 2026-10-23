## Kết quả pilot vòng A (offline): **DAT_OFFLINE**

Python 3.14.6 · pytest rc=0 · 801 passed, 29 subtests passed in 87.98s (0:01:27)

| Tiêu chí | Đạt | Chi tiết |
|---|---|---|
| c1 ca sổ ghi đã sửa (chưa xác nhận) xanh | ✅ | [] |
| c2 compatibility golden (cờ TẮT = byte giống) | ✅ | "passed" |
| c3 0 kết nối ra ngoài (0 lời gọi trả tiền) | ✅ | 0 |
| c4 0 ghi vào data/ | ✅ | [] |
| c5 ca chưa sửa (OPEN) còn đỏ, không xanh vì bỏ qua | ✅ | [] |

| Nhóm | Mã | Loại | Trạng thái sổ | Kết quả |
|---|---|---|---|---|
| continuity | P31-G1 | dang_lam | IN_PROGRESS | passed |
| continuity | P31-G3 | dang_lam | IN_PROGRESS | passed |
| continuity | P31-G43 | dang_lam | IN_PROGRESS | passed |
| continuity | P31-G46 | dang_lam | IN_PROGRESS | passed |
| continuity | P33-A10 | dang_lam | IN_PROGRESS | passed |
| continuity | P31-G8 | phai_xanh | FIXED_UNVERIFIED | passed |
| khac | V31-GOC1 | dang_lam | IN_PROGRESS | passed |
| payload | P31-G10 | phai_xanh | FIXED_UNVERIFIED | passed |
| payload | P31-G24 | phai_xanh | FIXED_UNVERIFIED | passed |
| payload | P31-G27 | phai_xanh | FIXED_UNVERIFIED | passed |
| payload | P31-G30 | phai_xanh | FIXED_UNVERIFIED | passed |
| payload | P31-G32 | phai_xanh | FIXED_UNVERIFIED | passed |
| payload | P31-G58 | phai_xanh | FIXED_UNVERIFIED | passed |
| payload | P31-G7 | phai_xanh | FIXED_UNVERIFIED | passed |
| phuc_hoi | P31-G36 | dang_lam | IN_PROGRESS | passed |
| phuc_hoi | P31-G35 | phai_xanh | FIXED_UNVERIFIED | passed |
| phuc_hoi | P33-A1 | phai_xanh | FIXED_UNVERIFIED | passed |
| phuc_hoi | P33-A13 | phai_xanh | FIXED_UNVERIFIED | passed |
| phuc_hoi | P33-A15 | phai_xanh | FIXED_UNVERIFIED | passed |
| phuc_hoi | P33-A3 | phai_xanh | FIXED_UNVERIFIED | passed |
| phuc_hoi | V31-R2 | phai_xanh | FIXED_UNVERIFIED | passed |
| qc | P33-A5 | phai_xanh | FIXED_UNVERIFIED | passed |
| qc | V21-R3 | phai_xanh | FIXED_UNVERIFIED | passed |

Mục sổ lỗi đang mở / đã sửa mà CHƯA có test (không chấm được): P31-G2, P31-G4, P31-G5, P31-G6, P31-G9, P31-G11, P31-G12, P31-G13, P31-G14, P31-G15, P31-G16, P31-G17, P31-G18, P31-G19, P31-G20, P31-G21, P31-G22, P31-G23, P31-G26, P31-G28, P31-G29, P31-G31, P31-G33, P31-G34, P31-G37, P31-G38, P31-G39, P31-G40, P31-G41, P31-G42, P31-G44, P31-G45, P31-G47, P31-G48, P31-G49, P31-G50, P31-G51, P31-G52, P31-G53, P31-G54, P31-G55, P31-G56, P31-G57, P33-A2, P33-A4, P33-A6, P33-A7, P33-A8, P33-A9, P33-A11, P33-A12, P33-A14, P33-B1, P33-B2, P33-B3, P33-B4, P33-B5, P33-B7, P33-B8, P33-B9, P33-B10, P33-B11, V31-GOC2, V31-GOC3, V31-GOC4, V31-GOC5

### Dữ liệu cần máy chính chụp (chỉ đọc, D08)

- [payload] jobs.sent_package + sent_refs #31 shot 27, 28, 29, 30, 33, 35, 36 và #33 (6 clip 1080p + nháp; job 1162, 1163) — mã P31-G27, P31-G37, P31-G38, P31-G7, P31-G10, P31-G24
- [qc] ảnh/clip jobs.result_path #33 S2, #33 shot 6 (+ motion_prompts.ref_video_path), #31 shot 33 — mã P33-A5, P33-A6, V21-R3
- [payload] ảnh Kho #427 (dạng bóng mờ, vai character_form), #367 (tường keo) — mã P31-G37, P31-G38
- [continuity] scenes.data + story_scenes #31 cảnh 4/6/8 (shot 14, 26–29, 35) và #33 — mã P31-G41, P31-G43, P31-G45
- [lineage] change_events 17/10 #31 (13 mục đỏ noi_chon) — mã P31-G22
- [phuc_hoi] job_events / diag_events #33 job 1162→1163, #31 job 1058–1072 — mã P33-A1, P31-G36
- [lineage] SHA HEAD + dòng FEATURE_ của dashboard.env + schema version (D08)

Vòng A offline không đổi trạng thái sổ lỗi — xác nhận thật = vòng B (chạy thật, Cấp 3).
