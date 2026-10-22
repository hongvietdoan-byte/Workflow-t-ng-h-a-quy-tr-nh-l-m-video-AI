# Danh sách việc chờ người dùng duyệt — 22/10/2026 (tối)

Trả lời gọn theo mã trong chat phiên chính, ví dụ: `Q3: B, E4: không tính lipsync, Q-A: đồng ý`. Phiên chính ghi từng câu vào sổ quyết định
(`data/decisions.json`) + kế hoạch. Cột **Chặn** = việc đang đứng chờ câu trả lời.

| Mã | Câu hỏi | Đề xuất | Chặn | Tài liệu |
|---|---|---|---|---|
| **P1** | Hai pet: dừng Lão Đại; gộp Tiểu Nhị vào M8.2 (chế độ Đơn giản) + M6.10? | Đồng ý | M8.2 | `docs/NGHIEN_CUU_TU_PHUC_VU_DASHBOARD.md` |
| **P2** | Tiểu Nhị dùng API hay dùng gói? Ngưỡng ghi bài học "3/2" hay "≥ 2"? | Gói; "≥ 2" | M6.10 | như trên |
| **Q3** | Ngân sách vai tự gen lại không cần hỏi: A = số USD cố định · B = 40 % tiền lượt đầu · C = không đặt | B (số thật: làm lại = 37 % ở #27, 29 % ở #31) | Gói M6-A | `docs/pdf/DANH_GIA_M6_DIEU_PHOI_VAI_2026-10-22.pdf` |
| **E1** | Gói ref tối giản: công cụ ĐỀ XUẤT cho vai, hay CODE TỰ QUYẾT bộ ref? Ai là chủ "bộ ảnh tham chiếu gửi kèm"? | Đề xuất cho vai | M2.10, M6.5 | như trên |
| **E2** | Chế độ Đơn giản: bấm "✔ Duyệt hết" = đã khóa Bible + duyệt motion + duyệt sân khấu 3D? Không thì thêm cổng "duyệt sân khấu" | — | M8 | như trên |
| **E3** | Ghi vào sổ: "đạo diễn ngoại tuyến" (`stage_auto --crew/--answer`) là vai hợp lệ, kèm 4 điều kiện? | Đồng ý | — | như trên |
| **E4** | Tính vào trần lượt gen: ảnh khung cuối (trần 3 ảnh)? video mẫu 4 s (trần 2 video)? lipsync? | — | M6 | như trên |
| **E5** | Bảng khâu → vai: đặt máy L6 → Quay phim; giọng L4 → Âm thanh; lỗi ảnh/BYĐ L13 → vai thượng nguồn; tranh chấp trường Đạo diễn → EP trọng tài | Đồng ý | M6 | như trên |
| **E6** | Kho (hồ sơ, ảnh mẫu, gộp mục) giao vai nào, hay người dùng làm tay? | — | M6 | như trên |
| **Q-A** | Máy tự chọn 1/3 hướng kịch bản (vẫn có nút "Phương án khác")? | — | M8.1 | `docs/pdf/M8_1_Che_do_Don_gian.pdf` |
| **Q-B** | Máy tự viết + tự duyệt motion prompt? | — | M8.1 | như trên |
| **Q-C** | Clip đã duyệt tự nâng 1080p trong ngân sách, hay hỏi riêng một lần? | — | M8.1 | như trên |
| **Q-D** | Duyệt ngân sách cả phim một lần đầu dự án, chỉ hỏi lại khi vượt; báo trước ở 80 %? | — | M8.1 | như trên |
| **Q-E** | Tài khoản mới mặc định chế độ Đơn giản, tài khoản cũ giữ Chuyên gia? | — | M8.1 | như trên |
| **Q-F** | Làm M8.4 (an toàn tiền) trước các bước khác? | — | M8 | như trên |
| **G1** | M4.8 bàn đạo diễn 3D: quyền "chỉ EP" = chỉ Owner, hay cả chủ dự án? | — | M4.8 | `docs/handoff/GOP_M2_2026-10-22.md` |
| **G2** | M7.3: bật tách nhóm `ref_end_frames`? (thêm clip + ảnh khung cuối = tốn thêm tiền; chạy `pregen_check` báo giá trước khi duyệt) | — | M7.3 | như trên |
| **G3** | M2.8b (DP10): shot tách khỏi nhóm "chỉ ref" chuyển sang chế độ có khung đầu? (đổi cách gen) | — | M2.8b | như trên |
| **C1** | Email xin Enterprise LLM API (Compass) — người dùng tự gửi; có tài khoản thì thêm Sonnet 5.5 vào `data/pricing.json` + `core/llm_runner.py` | Gửi | — | — |
| **R1** | Báo cáo dự án theo khung 7 mục (tiến độ, khối lượng, chi phí token + USD, chất lượng, rủi ro, việc cần quyết): dựng bản đầu + script báo cáo hằng tuần? | Dựng (giao Codex) | — | chat 22/10 |
| **D2** | 17 nhánh agent cũ chưa vào main: xóa / gộp / giao lại — CHỜ báo cáo Codex CX22-DON-RAC nhóm 2 rồi mới hỏi | — | dọn rác | `docs/RA_CX22_DON_RAC_CODEX_*.md` (sắp có) |

## Đã duyệt hôm nay (22/10, để đối chiếu)
- Tự nén phiên ở ~340k token; việc nhẹ giao agent Sonnet (commit 99f3b965).
- Dọn lưu trữ nhóm 3 → 1 → 2, chuyển không xóa → Codex **CX22-DON-RAC**.
- Gói tối ưu A+B: `tools/don_rac.py`, xoay vòng sao lưu, tự gỡ worktree khi gộp → Codex **CX22-DON-RAC-TOOL**; luật skill/lịch đã sửa (23a77347).

## Không tự làm (Cấp 3 — luôn hỏi trước)
Bật cờ production · gọi API trả phí (ClipAI, Claude API, TTS…) · xóa asset · migration CSDL thật · gen ảnh/video (chạy `pregen_check` báo giá trước).
