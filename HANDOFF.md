# Bàn giao DP7

Tranche metrics offline đã có module + 15 test mục tiêu xanh; xem docs/RA_DP7_CODEX_2026-10-20.md.
DP7 vẫn OPEN: chưa schema đầy đủ, chưa runner/CLI/checker, chưa nhãn người xác minh, chưa benchmark thật hay xét BLOCK.
Không push/main/TODO/kế hoạch/dữ liệu thật. Phiên cha rà diff trước tích hợp; cả bộ Windows còn phải chạy khi đủ điều kiện gộp.

P2 OPEN (phiên cha bắt): metrics cộng dev + independent khác SHA theo qc_code; tranche sau thêm test và tách/reject mixed split. Chưa được dùng ra quyết định, chưa rà hoàn tất.

## Điểm nghỉ tổng hợp Codex 20/10 23h

- 5h đã dùng91%, còn9%; tuần đã dùng29%. Đã tạo heartbeat `ti-p-t-c-l-n-codex-sau-reset` chạy một lần03:40 ngày21/10 Asia/Saigon sau reset dự kiến03:34:57; không tạo trùng, không monitorquota định kỳ.
- CX20-2 code đãpush9187a289 (35test), CX20-5 70982526 (70test, allocator/lifecycle chuẩn OPEN), CX20-6 ec9e62e1 (52test, .test-home untracked khôngcommit do policychặn xóa). Không production/cả bộ/merge/live.
- CX20-2b nhánh `codex/d20-viec2b-golden-replay` worktree cùng tên HEADbb885088 đãpush43test: 2VỪA+THẤP/isolatedworker; CAO-M2 VẪN OPEN, chưa DB replay độc lập/phânloại drift thật. Câu hỏi `20261020-230550-codex-30dh.json` chờ phien-chinh; đừng đánh XONG/GỘP mởM2. Nhánh đãcherrypickdependencygolden cóchủý vì origin/main9301056b chưa chứa file dùmailnói gộp; phảifetchđốichiếulại.
- DP7 worktree này, nhánhcodex/v31-dp7: metrics/schema tranche afdc1bcf, ghiP2de7dfc1e. 15testxanh KHÔNG chứngminhbenchmarkready. RootthấyP2 trộndev+independentkhácSHA; bướcnhỏđầutiên ĐỎregression→tách/rejectmixedsplit, ràtrước dùng. Rồi mớifullschema/CLI/checker và đánhgiátheospec. KhôngđánhxongDP7 bằng metrics.
- Saureset: get_usage_limits→đọcAGENTS/CLAUDE/CHUAN/skill/hop_thuREADME→fetch/pull worktreehộpthư `D:/AI-Video-Pipeline/.codex-wt/d20-hop-thu`→bang --lane codex, nhậnreply2b trước, tiếpownĐANGLÀMưu tiên, rồi ke --lane codex --nhan --push. Chỉfileeventđượcpushmain. Khôngcheckout/pull/restartD:/AI-Video-Pipeline/live.
- Mọi prompttest/rà: patch.object thayOBJECTos.environ dictfake trướcimports/calls/spawns (khôngpatch.dictclear); mockregistry/credential/provider/model; nativeexplicitwhitelist, khôngpylaunchertrongenvtrống; no secretread/print/assert/repr, no showlocals/envdump; pytest--tb=no. Khôngvôhiệugit hook; hai commit builder trước cóoverrideNUL đãghiRA, khônglặp. Windowscảbộthuộctíchhợp.