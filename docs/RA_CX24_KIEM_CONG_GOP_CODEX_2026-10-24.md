# CX24-KIEM-CONG-GOP — ma trận và công cụ chỉ đọc (24/10/2026)

Nhánh `codex/v31-kiem-cong-gop`, nền `origin/main` d72f80f6; checkpoint tài liệu de856efc đã push. Codex 1 nhận event `20261024-172409-codex-v52z.json` theo quyền lấy việc CHỜ ưu tiên nhỏ nhất chưa ai nhận; đã kiểm không nhánh/worktree đang giữ trước nhận, báo all bằng event `20261024-172557-codex-csrw.json`. Không gộp main hoặc restart live.

## Kết quả theo đề

- `docs/KIEM_CONG_GOP_2026-10-25.md` và catalog version1: đủ **50 hàng** code✅/cổng hiệu lực⬜ theo parser G1 trên master hiện tại; **6 hàng** có thể thu đủ minh chứng trong một dự án có EP xem/duyệt, 44 hàng cần thêm lịch sử/benchmark/đa dự án/process hoặc đối soát tài liệu. Test kiểm chính xác tập mã, không chỉ đếm.
- Mỗi hàng có tiêu chí master §3/§4a/dòng việc, cờ cần bật có điều kiện, nguồn bằng chứng, bước/bảng/file, cách offline và rủi ro. Cuối ma trận có lô cờ đề xuất, nhóm giữ học việc/shadow/không tự bật và điểm dừng xin EP trước ảnh/video/1080p. Cờ được đối chiếu AST registry và dependency cả REQUIRES lẫn world_map_sentences→world_map. Không tự thay cấu hình hay coi trần20USD là quyền chạy Codex.
- `tools/kiem_cong.py --db snapshot.sqlite --project N [--since timezoneISO] [--md new.md]`: bắt buộc snapshot explicit ngoài data thật; thêm --catalog cho fixture/catalog được chỉ định, phải có dòng và ID không trùng. Reuse `tools.kpi_goc.open_db_readonly`: SQLite URI mode=ro, query_only và một BEGIN giữ snapshot nhất quán.
- Gom bảy nguồn: jobs; jobs.sent_package JSON; diag_events; diag stage ui_step; usage_events; qc_results/qc_runs/qc_findings; scenes.data.package_overrides hoặc bảng overrides. Scope trực tiếp hoặc join đúng project; FK có giá trị phải xác minh parent. Thiếu parent schema→MISSING, orphan/khác dự án→FAIL; giữ nguyên phân loại kể cả JSON hỏng. NULL FK không tự gây lỗi khi directproject đã đủ.
- --since có timezone, dùng timestamp riêng từng evidence; không mượn job time cho QC/override. qc_results cũ không có timestamp: chỉ kiểm cấu trúc khi không since; có since→THIẾU DỮ LIỆU. JSON hỏng/NaN/Infinity, job state/type lạ, timestamp lỗi/tương lai, quantity âm, diagnostic lỗi hoặc QC dưới ngưỡng không PASS.
- QC enums đúng contract core.qc_evidence: BLOCK/REVIEW/INFO; open/overridden/resolved/false_positive; run ok/failed/partial. OPEN BLOCK/REVIEW không PASS; finding đã xử lý nhưng thiếu audit người/thời điểm giữ THIẾU DỮ LIỆU, không bịa đã nghiệm thu.
- Report chỉ counts/status/reason cố định, mỗi hàng có lý do manual/nononeproject/missing/failed. Không raw payload/prompt/diag message/SQL exception hay secret. Không quy đổi ledger thành USD bằng giá bịa; chỉ reuse contract usage_events của core.cost, không import runtime/đọc pricing thật.
- Availability có thể ĐẠT; **không hàng cổng nào tự đạt chỉ nhờ số bản ghi**: 50 hàng còn phần manual/EP/benchmark nên giữ THIẾU DỮ LIỆU khi chưa có lỗi thấy được. Ngoài SQLite (world/crew/qc_shadow/ảnh/clip/ground truth/balance) phải đối chiếu riêng, công cụ không giả đã đọc.
- --md chỉ tạo file .md mới bằng mode x, validate trước đọc DB; từ chối existing/data/symlink/junction và input/catalog. Không đè DB/WAL/SHM/hardlink/source hiện có. Giữ areas.version92, đăng ký module/test/docs/catalog; không cờ mới vì tool chỉ đọc, chưa nối Dashboard.

## Test và bằng chứng (các lượt chồng nhau, không cộng thành tổng mới)

1. Root acceptance trước module: **4 errors/6,30s** vì chưa có tool; builder RED thật **1 error collection/1,29s**. GREEN đầu **26 passed,1 skipped/4,03s**; root6acceptance **6 passed/1,01s**.
2. Rà tài liệu ba P2 đã sửa: M7.3 dùng nhầm backview thay endframe; M7.1 thiếu cờ mẹ director_rewrite có phí; M3.3 thiếu cờ mẹ world_map. Closure test root RED1failed/4,49s→GREEN1passed/0,57s; thêm implicitparent RED1failed/0,53s→GREEN1passed/0,56s. Rà độc lập tài liệu chốt0P1/P2 trong phạm vi này.
3. Root code RED độc lập **3 failed,5 passed/4,22s** (reason/state/scope); builder gộp ghi **3 failed,27 passed,1 skipped/7,70s**. Bốn nhóm code đã sửa: reason từng hàng, job enum, foreignscope, QC enum. GREEN mốc này **39 passed,1 skipped/26,25s**.
4. QC enum được phát hiện bằng rà tĩnh; chứng minh hồi quy **sau phát hiện**: patch.object _finding cũ trong bộ nhớ với fixture OPEN+BLOCK cho **1 failed**, không rollback file. Không ghi giả thành RED trước triển khai; ca GREEN nằm trong nhóm trên.
5. Thiếu schema parent scope: root RED **1 failed,8 deselected/0,96s**; thêm bốn ca missingparent/projectcolumn × NULL/nonNULL; GREEN gộp **44 passed,1 skipped/55,97s**.
6. Nhánh malformed overrides table làm rơi scopeflags: root RED **2 failed,9 deselected/0,79s**, sửa giữ scopeerror/scopemissing; **GREEN cuối 46 passed,1 skipped/5,25s** bằng `py -m pytest tests/test_kiem_cong.py tests/test_kiem_cong_acceptance.py -q -p no:cacheprovider --tb=no`. Một skip do Windows không cho tạo symlink vật lý, không tuyên bố đã kiểm link thật.
7. CLI chạy thật với SQLite giả/temp và catalog mặc định: **exit0,7/7 nguồn hợp lệ,50 hàng,0 cổng tự PASS**, tạo Markdown mới, SHA256 DB giữ nguyên. Đây là bằng chứng tool offline, không phải chất lượng dự án thật.

Rà độc lập tiền/dữ liệu/quyền/caller theo related_areas: chỉ vùng devsys, chưa có caller tool; root đọc bản sửa hai lượt. Tất cả QA thay OBJECT os.environ bằng dict giả trước import/call, chặn socket; không keyring/registry/provider/model thật, không --showlocals/dumpenv/traceback có bí mật. Cả bộ Windows/slow thuộc phiên chính khi tích hợp, không gọi targeted là cả bộ.

## Giới hạn thực tế

Chưa chạy trên snapshot sản xuất, chưa có buổi test25/10, chưa nghiệm thu Dashboard/ảnh/video hay benchmark thật; không API, dữ liệu thật, migration, bật cờ, Computer Use, main merge hoặc live restart. Chi phí API0USD. Khi main thay trạng thái kế hoạch cần đối soát lại catalog/ma trận (acceptance kiểm coverage); không tự đóng cổng/master/VERIFIED. Chờ phiên chính rà/gộp nhánh và EP chốt cờ/thử thật.
