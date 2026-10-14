# Bàn giao Đ12 việc 3 — metadata âm ref (14/10/2026)

## Chốt polish 14/10 21:33 — ưu tiên trạng thái này

- Code polish `1d46d091`; dependency backend ff24a25c+b5207db4. Chỉ push nhánh `codex/d12-ref-audio-polish`, bên tích hợp chạy cả bộ Windows gồm slow trước gộp. Tiếp Đ18.4c inventory dry-run tại worktree `d18-viec4c-dry-run`, đang RÀ KỸ; look domain vẫn chờ câu trả lời.

- Root đã đọc diff sửa lần hai; targeted cuối 22 xanh/3,40s. Need_edit trước IO, warning no_audio giữ theo pid qua rerun, help theo cờ, lỗi giữ màn hiện tại và readonly disable nút; giữ consent/use=False/widget keys.
- Browser CUA fixture actual extras_section: 1440/1280 không cuộn ngang, warning shot 2/5 rõ, 0 console error; readonly nút lấy tiếng disabled. Đã xem ảnh1280, lưu docs/images/d12/ref_audio_polish_1280.jpg và _1440.jpg. QA chỉ component/fakeDB/provider, chưa toàn Step5/bản dựng sản xuất/cả bộ Windows.
- Đã đóng tab/reset viewport và dừng đúng owned launcher PID118464; cổng18636 không còn nghe. Không động 8501/8502/data thật/API. Backend dependency ff24a25c+b5207db4 giữ C5/main mới; areas80.

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

## Đ12v3 polish sau thư 14/10 18:26/19:23 — chưa commit/gộp

- Worktree D:/AI-Video-Pipeline/.codex-wt/d12-ref-audio-polish, nhánh codex/d12-ref-audio-polish, base origin/main 7340e6b1.
- Backend có sẵn 4a52a772 + 2808cfe0 chưa main, cherry-pick chủ ý thành ff24a25c + b5207db4. Conflict FEATURES/OPT_IN_ONLY/areas giữ main, bổ sung riêng ref_audio_sync; version 80. Không đổi delivery/ffmpeg_studio/C5.
- Sửa nhỏ: propose need_edit server trước assets_dir/probe/ffmpeg; no_audio VÀNG theo pid giữ qua rerun, cập nhật/xóa ở lần propose thành công tiếp theo; help ON đoạn nguồn+tốc độ (atrim+atempo), OFF giữ ≤40%; caption sync không KeyError khi fit_file có nhưng thiếu fit_tempo.
- Không đổi use=False/checkbox consent, widget keys, autosend hoặc backend sync.
- Test gom 2 file: ĐỎ 4 failed/16 passed (1.53s) → XANH 20 passed (1.37s). Fixture env patch.object fake trước imports/calls; fake DB/files, no paid/provider.
- related_areas: step5, callers core_infra/step3; test CHẬM editor_apply/editor_review/rough_cut bắt buộc ở bước gộp. Chưa fullsuite/GUI polish/chất lượng sản xuất/data thật.
- Tự rà 2b.5 ghi tại docs/RA_D12_VIEC3_CODEX_2026-10-14.md. Cần root RÀ KỸ quyền + fullsuite Windows trước gộp; không TODO/push/commit phần sửa nhỏ.


## Rà độc lập polish và fixture QA · trạng thái mới nhất
- Reviewer đọc phạm vi nhỏ,1P2 catcherror bị rerun xóa đã sửa return+readonly disable riêng refbutton; core need_edit authoritative trước IO vẫn giữ. Không đổi keys/useFalse/flags/backend.
- Actual AppTest extras: RED errorvisibility → **22GREEN/3.40s**, targeted2files. Reviewer4lượt (2lỗi fixture fakeHOME/globalidentity, root cho confirm4th); khôngnới/broad/fullsuite. Cwdtestsource sửa absolute __file__.
- Fixture tracked tests/fixtures/ref_audio_polish_qa.py areas80; fakeenv+winreg/keyring restoremissingpresent, provider/model/auth loaders mock trước dashboardimports. Không realcredential/media/API.
- QAserver http://127.0.0.1:18636 PID118464 unifiedsession49976, launcher ngoàiWS D:/AI-Video-Pipeline/.codex-wt/_qa_ref_audio_polish_launch.py, outerchildspawn explicitnativewhitelist -I -Xutf8. RootbrowserQA1440/1280 và dừng đúngPID; chưa production/fullStep5.
- RA bổ sung docs/RA_D12_VIEC3_CODEX_2026-10-14.md. Còn root đọc fixdiff lần2, chụpQA, cảbộWindowsintegration; khôngcommit/push/TODO/main/live.
