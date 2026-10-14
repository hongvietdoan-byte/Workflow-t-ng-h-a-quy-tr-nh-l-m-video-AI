# Bàn giao Đ12 việc 3 — metadata âm ref (14/10/2026)

## Trạng thái mới nhất (thay các dòng chờ rà/QA phía dưới)
- Root đã commit/push code nhánh `4a52a772`; bổ sung sau commit đang workingdiff: nguồnON ffmpeg probe/extract có protocol/demuxer allowlists chặn playlist giả.mp4 mở URL/file khácproject. RED2→XANH16focused/1,40s, WAV+MP4 thật qua, playlist chỉmock khôngmạng. Chưacommit/push fixbổsung, root đọc diff trước quyết; chưacảbộ/gộp/sảnxuất. Dòng này thay trạng thái chưacommit/push cũ phía dưới.
- Nhánh đã RÀ KỸ, sửa2finding reviewer+3finding root; root đã đọc fixdiff vòng2. Thêm OPT_IN_ONLY ref_audio_sync chặn preset experimental tự bật, RED1→GREEN1/0,16s. Không mở rộng tính năng.
- Nhóm47qua/6bỏqua/6,47s; focused13qua/1,23s + flag1GREEN. QA component thật với fake pipeline1440/1280 height1500 đủfields,0pageerror/overflow,2PNG docs/images/d12; root đã xem1280. Fixture và server QA riêng đã dọn.
- Sẵn sàng root commit/push NHÁNH sau kiểm diff cuối; chưa commit/push, chưa cả bộ Windows/gộp/sản xuất. Nội dung tiến trình phía dưới là lịch sử, trạng thái mới nhất này được ưu tiên.

- Nhánh `codex/d12-viec3-ref-audio`, nền `4883f165`; chưa commit/push, chưa gộp.
- ĐÃ DUYỆT nguồn GỐC + giây đầu/cuối + tỉ lệ tốc độ. Lưu `motion_prompts.ref_audio_metadata` JSON: `source_path`, `start`, `end`, `speed`. Đoạn `[start,end]` theo giây nguồn; speed=0,5 là phát chậm ×2.
- Setter `Pipeline.set_motion_ref_video(..., ref_audio_metadata=...)` kiểm quyền cũ, kiểm metadata trước ghi CSDL; đổi/bỏ ref không truyền metadata xóa metadata cũ. Migration thêm cột nullable, không đoán dữ liệu legacy.
- Bước 3: cờ `ref_audio_sync` TẮT. Bật mới thấy expander tải riêng nguồn GỐC vào thư mục dự án + số giây/tốc độ. Có thể bổ sung metadata cho ref đã gắn không cần tải lại ref. Giữ các key nút/uploader cũ.
- Khi bật: `ref_audio.propose` dùng nguồn GỐC dù motion ref đã mất tiếng, atrim + asetpts + chuỗi atempo. Thiếu/sai metadata → VÀNG qua đường failed hiện có ở Bước 5, không fallback ref mất tiếng.
- Tách đã áp tốc độ; khi dựng fit chỉ trim hoặc pad im lặng tới độ dài shot, không kéo tốc độ lần hai. Hash metadata làm khóa đề xuất, metadata đổi làm tiếng cũ stale theo quy tắc sẵn có (người đã tích vẫn quyết).
- Giới hạn: đường tuyệt đối cục bộ, không UNC, phạm vi thư mục dự án, số hữu hạn, .01≤speed≤100, đoạn và kết quả sau đổi tốc độ ≤600s; đầu/cuối trong duration nguồn. Probe timeout15s; extract/fit60s. Subprocess mới chỉ nhận native env whitelist, không kế thừa token.
- Test ĐỎ 2 thiếu hàm → XANH27; nhóm chốt `tests/test_ref_audio_sync.py tests/test_f5b_backlog.py tests/test_chat_intake.py`: **49 qua /13,57s** (lượt trước49/18,82s). Không API/dữ liệu thật.
- Proof ffmpeg thật: WAV nguồn3s với 440Hz đầu/880Hz sau; motion ref silent; lấy nguồn giây1→2, speed.5 ra ~2s và vẫn880Hz; fit2.5s pad im cuối; đề xuất lần hai idempotent.
- Đã chạy related_areas: step5/core_infra/step3; caller `sfx_plan.fit`, `chat_intake.apply`, upload Bước3, Bước5 propose; cả bộ có test CHẬM bắt buộc ở bước gộp.
- Chưa cả bộ Windows, chưa QA ảnh1440/1280, chưa nghe bản dựng sản xuất; version areas giữ75. Không đổi mix_bus/delivery/ffmpeg_studio/step5, TODO, dữ liệu thật.
- Fixture QA local `_qa_ref_audio_ui.py` gọi CHÍNH `_motion_ref_editor` từ step3, environ OBJECT giả trước imports; chỉ fake pipeline. File fixture tạm cần xóa trước commit.
- Kế: root QA1440/1280 + reviewer độc lập; sửa gom kết quả reviewer rồi root quyết commit.
- Vòng sửa reviewer: 2finding P1/P2 đã sửa gom (xem RA). Pipeline root tin cậy từ constructor/data_dir hoặc dashboard.common.scoped; scene quyết project boundary trước probe. Identity thêm SHA256 bytes nguồn, đọc hữu hạn512MiB; đổi bytes cùng path đánh stale/gỡ đề xuất theo use. Thiếu cấu hình metadata fail closed, không đổi setter legacy.
- Test cuối vòng sửa: `test_ref_audio_sync.py test_f5b_backlog.py test_chat_intake.py` **47 qua,6 bỏ qua /6,47s**, environ OBJECT giả/native whitelist; RED setter + RED2 mô phỏng fingerprint legacy. Test mới actor/pathB+pathA và source overwrite dùng/chưa dùng, biên hash. Chưa commit/push, root còn đọc diff/QA/cả bộ.
- Vòng2 root: RED3 → XANH13 focused ref_audio_sync; pre/post fingerprint quanh extraction chặn source đổi/mất/overflow (VÀNG+clean tmp); sync fit trần600s trước spawn; fit WAV tạm+os.replace atomic giữ bản cũ nếu timeout. Root QA1440/1280 0pageerror/overflow, PNG docs/images/d12; còn root ảnh1450 + đọc diff. Chưa xóa fixture/chưa commit/push/chưa cả bộ.
- QA cuối root1280/1440 height1500 đủ fields component thật, 0pageerror/overflow; root đã view1280, server fake riêng đã stop. Reviewer xóa đúng `_qa_ref_audio_ui.py` sau verify theo root. Focused cuối13qua/1,23s; chưa production/8501/cả bộ/commit/push; còn root đọc diff vòng2.
