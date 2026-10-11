# Bàn giao Codex sau Đợt 10 — 12/10/2026

Đã push từng nhánh, không gộp main/pull live/restart. Cả bộ Windows chưa chạy; chạy khi tích hợp. Cờ mới TẮT, chưa thử API thật.

| Việc | Nhánh | Code | HEAD kết quả trước việc 6 | Test cuối |
|---|---|---|---|---|
| Đ10v1 | codex/d10-viec1-goi-gui-kem | d1b325f | cdd48b4 | 119 |
| Đ10v2 | codex/d10-viec2-ky-thuat | 440936f | 096a24c | 73 + 1 xfail |
| Đ10v3 | codex/d8-viec3-bao-gia-video | 10a8823 | dcdb250 | 129 |
| Đ10v4 | codex/d10-viec4-phieu | 9c17c84 | b573310 | 163 |
| Đ10v5 | codex/d10-viec5-khung | 97d1a40 | d1105a1 | 21 |
| Đ10v6 | codex/d10-viec6-chuyen-dong-nen | 5197a1c | commit chứa tài liệu này | 64 |

RA từng việc trong docs trên nhánh tương ứng. Kết quả Codex trong CODEX_TASKS là các row riêng trên nhánh; tích hợp phải giữ đủ, không ghi đè các row khác. Areas version giữ nguyên, tích hợp tăng một lần.

## Bước kế sau reset tự nhiên
Đ9v3 GUI pet/khay/toast/launcher/Windows PNG trước, rồi Đ12v1, Đ11v1, còn lại Đ9–13 (gồm Đ12v5–6 mới), không làm Đ14 chưa giao.
Pet worktree D:\AI-Video-Pipeline\.codex-wt\d9-viec3-lao-dai, nhánh codex/d9-viec3-lao-dai HEAD1236c1b. Backend42ecaec + dependency df62cc7 đã cherry-pick main: fetch/read origin/main mới, merge main vào nhánh pet nếu cần; đừng viết/cherry-pick lại backend. Đ10v4 code9c17c84 có broker/logic cần cho GUI; kiểm main đã gộp chưa, chỉ lấy dependency thiếu và tránh nhân đôi. Main lúc bàn giao4aa8ed8; không đổi nhánh/pull bản live.

GUI cần credential OS và kênh cấp token từ Owner server, không CLI/env/log/URL token; broker GET loopback readonly TTL/revocation, pet không đọc SQLite. Không sửa devsys/admin_auth.py; dùng current/is_owner. QA dữ liệu giả/DB tạm, Computer Use skill, ảnh docs/images/d9. Không maintenanceworker.

Bỏ qua tất cả chờ #24: Đ10v3 project_budget mục2; Đ11v3; Đ11v5 nối gửi; runner/lock_exceptions/end_frames/place_refs/scene_storyboard. Đ10v3 còn giới hạn provenance original/marked, giây submit nhóm, orphan follower tính riêng dư, follower final1080p chưa cắt. Không API tốn tiền/dữ liệu thật/dashboard.env/secrets/main merge.

Hạn mức trước bàn giao đã dùng83% 5h; reset12/10 06:00:16 Asia/Saigon. Sau reset đọc số thật, không dùng reset credit/mua credit. Theo skill ≥60% chỉ1child, 70–90% chỉ việc nhỏ, ≥90% lưu/push/nghỉ. Không bật nhắc quota định kỳ.