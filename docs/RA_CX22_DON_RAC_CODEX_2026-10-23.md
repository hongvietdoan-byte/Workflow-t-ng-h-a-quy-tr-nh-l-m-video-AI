# Báo cáo CX22-DON-RAC — 2026-10-23

- Nhánh `codex/v31-don-rac`; đối chiếu `origin/main` tại `00a4ed6c`.
- Chỉ thực hiện dọn nhóm 3, 1; nhóm 2 chỉ rà, không xóa.
- Nhật ký khôi phục từng đường dẫn và SHA-256: `D:\AI-Video-Output\_luu_tru\NHAT_KY_DON_RAC_2026-10-23.log`.
- Lưu trữ ngoài repo tại `D:\AI-Video-Output\_luu_tru\`; không đụng dữ liệu dự án bị loại trừ.

## Dọn nhóm 3

- Chuyển 21 backup manifest, 10 backup feature settings, 4 backup `dashboard.env` cũ; giữ 3 bản mới nhất mỗi loại.
- Chuyển 11 file lock đã xác nhận không bị tiến trình giữ; giữ `manifest.sqlite.bgpoll.lock` vì còn handle.
- Chuyển 102 file `_plates3d/` gốc (195,877,789 byte) sau khi tìm mã nguồn không thấy caller dùng đường dẫn gốc; bản `data/_plates3d` giữ nguyên.
- Mỗi bản sao được kiểm SHA-256 trước khi bỏ nguồn. File gốc `22` là file rỗng 0 byte, không phải thư mục; giữ nguyên.

## Dọn nhóm 1

- Gỡ 19 worktree đủ điều kiện (HEAD đã ở main, chỉ còn `HANDOFF.md` chưa theo dõi, cũ hơn 3 ngày, không thuộc danh sách giữ); lưu và kiểm SHA handoff trước khi gỡ.
- Xóa an toàn 19 nhánh local đã vào main bằng `git branch -d`; giữ các worktree/nhánh còn lại theo điều kiện và danh sách bảo vệ.
- `.codex-wt`: 80 → 61 thư mục. Không đổi nhánh hay dừng Dashboard trong repo live.

## Rà nhóm 2 — 17 worktree/nhánh, không xóa

| Worktree | Kết luận | Căn cứ ngắn |
|---|---|---|
| `agent-a1f9c158e92874dd8` | CÒN GIÁ TRỊ | Director: giới hạn gói/pass settings; main vẫn PARALLEL=3. |
| `agent-a21e8e6c6f350168b` | ĐÃ CÓ TRÊN MAIN | QC draft context/soft criteria đã nối trong caller và pipeline. |
| `agent-a22f9d77aeac76d1c` | ĐÃ CÓ TRÊN MAIN | Popup kết thúc và Step 5 đã tích hợp. |
| `agent-a28f8005b758fb117` | ĐÃ CÓ TRÊN MAIN | Mask vùng alpha/vật thể và plate cache recheck đã có. |
| `agent-a3d6ca9826e340219` | BỎ | Bản đánh giá 10/10 cũ; main có các vòng đánh giá mới hơn. |
| `agent-a6ecbad54a44d5a42` | ĐÃ CÓ TRÊN MAIN | Luật POV/ref-only và kiểm tra ClipAI tương đương đã có. |
| `agent-a81a6618e5d0855d4` | ĐÃ CÓ TRÊN MAIN | Tài liệu dự án thử 30 giây đã có trên main. |
| `agent-a892053a168efb677` | CÒN GIÁ TRỊ | Đo liveliness/stillness và dải ảnh; main chưa có cờ/module tương ứng. |
| `agent-aa563756b861fc046` | ĐÃ CÓ TRÊN MAIN | Group-cut UI và recut đã có. |
| `agent-ab11f1962cf159198` | CÒN GIÁ TRỊ | Cảnh báo chuyển động bị đứng; main chưa có `freeze_only`. |
| `agent-ac058a6946d44e5c1` | ĐÃ CÓ TRÊN MAIN | `use_older_take` và UI đã có. |
| `agent-acbfbd4e7bab59f04` | ĐÃ CÓ TRÊN MAIN | Mẫu chất lượng 1080p/ClipAI đã có. |
| `agent-adaa9190b79af629f` | ĐÃ CÓ TRÊN MAIN | Hàm chèn cảnh kế tiếp/kế thừa đã có. |
| `agent-ae3ea475370d740d3` | ĐÃ CÓ TRÊN MAIN | Hành vi anchor-away shot đã có. |
| `agent-ae94d3ee9f9c854f5` | ĐÃ CÓ TRÊN MAIN | Tài liệu duyệt V2.1 đã có nội dung tương đương. |
| `agent-afa4a52159e17769d` | CÒN GIÁ TRỊ | Tách gói/giới hạn pass; cần đo provider trước khi đổi song song. |
| `gop-cuoi-goc-b` | ĐÃ CÓ TRÊN MAIN | Chỉ khác event ghi gộp A/B; code commit `794e4780` là ancestor của main. |

## Dung lượng và kiểm chứng

- Dung lượng trống ổ D: trước 1,229,432,999,936 byte; ngay sau chuyển 1,230,765,146,112 byte (+1,332,146,176 byte). Đo lại khi lập báo cáo: 1,230,765,092,864 byte.
- `.codex-wt`: hiện 61 thư mục, 123,944 file, 4,558,448,626 byte. Trước dọn ghi nhận 80 thư mục; số byte trước không được chụp nên không suy đoán.
- `.claude/worktrees`: hiện 42 thư mục, 71,633 file, 3,168,600,281 byte; không bị thay đổi. Số byte trước dọn không được chụp.
- Nhóm 2 không bị sửa/xóa; không chạy test vì đây là thao tác lưu trữ và báo cáo, không thay đổi mã nguồn.
