# Codex → Claude: tổng hợp nhánh đã push và việc còn chờ

Gửi theo yêu cầu người dùng 14/10. Các nhánh dưới đây đã push riêng, chưa được Codex gộp main; số test là nhóm liên quan, không phải cả bộ Windows. Phiên rà/gộp kiểm dependency và trạng thái main trước khi cherry-pick, rồi chạy cả bộ gồm slow theo related_areas.

| Việc | Nhánh | HEAD đã push / code | Bằng chứng và giới hạn |
|---|---|---|---|
| Đ11v1b mockup | `codex/d11-viec1b-mockup` | `87ed86f7` / `f962f0f9` + `e74d8233` | 3 test, 4 PNG, 16 tổ hợp kéo; 5 P2 sửa. 18 mục bản gọn; #12/#20 để sau; chưa giảm clicks (5/5). |
| Đ13v4 cost nhóm | `codex/d13-viec4-cost-nhom` | `bd0a2306` / `a4a9dc83` | 133 test + 6 subtests; rà SAVEPOINT 3 đỏ → sửa 28 xanh. Ngoài transaction 1 query/20 parse/99 member; trong transaction đọc mới. |
| Đ12v4 kho âm | `codex/d12-viec4-kho-am-thanh` | `d8d39642` / `f7a6ab10` + `bba75ff5` | 34 test; công cụ JSON/CSV offline, nguồn giấy phép, AST không có mood trực tiếp; chưa đo Kho thật/tải âm. |
| Đ13v3 mockup pet | `codex/d13-viec3-mockup-pet` | `5df9a02d` / `ca5bd2ba` + sửa canonical số | 7 test; browser 1440/1280, tập đầu vào ngăn gen trùng, pet thường ẩn phiếu. |
| Đ12v2 SFX nhịp | `codex/d12-viec2-sfx-nhip` | `1c9d5d6d` / `6e789358` | 100 xanh, 2 PNG Edge 1440/1280; 3 P2 + 2 guard root sửa. Backend/component độc lập, chưa nối production/Claude bổ sung/ca clip thật. |
| Đ13v2 blockout | `codex/d13-viec2-goi-blockout` | `4ade6aff` / `bad2a535` | 97 xanh; 2 P2 sửa: metadata lồng lọt SHA, bitmap lỗi tiếng Việt. Schema2 exact geometry, schema1 raw strict, ngày timezone/legacy VÀNG. Actual Pillow cũ còn mở. |
| Đ13v1 hậu kỳ mục1/3/5 | `codex/d13-viec1-post-fx` | `dec1fb3b` / `728be4be` | 147 xanh/131,81 s, ffmpeg local; 2 P2 caller sửa. Tên file SHA đầu vào/atomic, schema Đạo diễn + lưu v2/v3, context chung Editor/Director; cờ OFF giữ luồng cũ. **Mục2/4 chưa làm.** |

## Claude cần nhận hoặc giải phóng

- Rà/gộp các nhánh trên theo quy ước 7 và cả bộ Windows; không bật mặc định phần chưa thử production. RA/HANDOFF và Kết quả Codex nằm trên từng nhánh. Giữ areas.version nền 74 ở nhánh việc, tăng một lần ở nhánh tích hợp.
- Đ13v1 mục2 (post_fx trước `_hold_end`) và mục4 (`delivery.status` nhận stale khi spec/cờ đổi), Đ12v3 mix_bus đang chờ C5/owner giải phóng `core/delivery.py`, `core/ffmpeg_studio.py`, `dashboard/steps/step5.py`. Codex chưa sửa những file này; đề nghị phối hợp vào cùng vòng khâu dựng hoặc báo rõ khi giải phóng.
- Đ12v3 âm ref: câu hỏi người dùng đang chờ chốt metadata file gốc + giây bắt đầu/kết thúc + tỉ lệ tốc độ; ref cũ thiếu báo VÀNG, không đoán. Code hiện chỉ giữ `ref_video_path`; không được suy rằng im lặng là duyệt.
- Đ18v1–3 đã push từ các lượt trước nhưng plan `d52253e6` chưa ancestor main lần kiểm 05:25. Đ18v4/Đ11v3 và phần nối Đ11v4 (approved blocking/objects theo beat/subject.id/end_actor/GUI) dùng DUY NHẤT registry A; không tạo registry hoặc editor2D cạnh tranh. Đ11v5 còn theo dependency nguồn A; runnergroup và seedance_refs chỉ nhận khi mail giải phóng/ủy quyền rõ.
- Đ9v3 GUI Windows thật (toast/DPI/2 màn hình/sleep-resume) vẫn thuộc máy chính/người dùng; không dùng shell giả thao tác desktop.
- Đã đọc mail 14/10 01:46 + kế hoạch trước tập2: C1/C2/C3/C5 thuộc Cloud, M0/M1/M3–M7 máy chính. Không nhận trùng; bom keo tĩnh/ảnh Remote đã duyệt, C4/M2 bỏ; không tự chạy thật hoặc tạo lại dự án tập2.

## Giới hạn QA và phòng ngừa lộ khóa

- Thử Pillow 10.0.1 thật trong TEMP bị automatic approval review chặn trước bootstrap ProcessStartInfo env whitelist + pip isolated/binary-only: chỉ `blocked by policy`, không lý do chi tiết. Chưa cài/chạy probe/sinh PNG; không đổi runtime hoặc bypass. 97 test không được mô tả là đã thử Pillow cũ thật.
- Mọi test env/token/loader: thay OBJECT os.environ bằng dict giả qua patch.object trước import/call/spawn; không patch.dict(clear=True). Native subprocess explicit whitelist env; mock registry/credential/provider/model trước gọi; teardown thiếu/có. Không đọc/in/assert/repr env/header/token/payload bí mật, không --showlocals/dumpenv; pytest --tb=no. QA DB/ASSET_DIR/DATA/flags/knowledge/credentials tạm; không API/data thật/dashboard.env.
- Bàn giao đầy đủ: `docs/HANDOFF_CODEX_2026-10-14.md` trên d13-viec1-post-fx `dec1fb3b`; bổ sung mail/dependency/QA blocked: `docs/HANDOFF_CODEX_2026-10-14_05H.md` trên d13-viec2-goi-blockout `4ade6aff`.
