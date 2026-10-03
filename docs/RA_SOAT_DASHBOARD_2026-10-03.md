# Rà soát toàn bộ dashboard bằng AI Development System (thang v2) — 2026-10-03

> Bản tổng hợp của: (1) chấm lại 16 khu vực theo **thang v2** (`devsys/rubric.md`, tối ưu 03/10), (2) so sánh với công cụ ngoài
> (`docs/SO_SANH_NGOAI_A_NEN_TANG_2026-10-03.md`, `docs/SO_SANH_NGOAI_B_WORKFLOW_VA_CONG_CU_2026-10-03.md`), (3) phương án nâng cấp.
> **0 USD**: chấm bằng 9 phiên Claude Code (không gọi Claude API). Code lúc chấm: `main` 41eea5b, test lưu **1970 qua, 0 lỗi**.
> Chi tiết từng khoản trừ (kèm file:dòng, cách sửa): `devsys/data/report.md` (sinh bằng `py tools/devsys_score.py --report`, không vào git)
> và web AI Development System (cổng 8502). Cách chấm mới + phân tích thang cũ: `docs/DANH_GIA_CACH_CHAM_DEVSYS_2026-10-03.md`.

## 1. Điểm 16 khu vực (thang v2 — không so thẳng với điểm cũ)

Tổng có trọng số: **85,6** (thang v1 lần 01/10: 87,2). Thang v2 thêm mức nghiêm trọng, số đo tự động bằng code và 2 tiêu chí mới (tin cậy, bảo trì);
lần chấm này là **mốc mới**, không phải "tụt điểm". Hai người chấm độc lập cho `dashboard_ui` ra 84,3 và 84,5 (chênh 0,2).

| Hạng | Khu vực | Điểm | Chặn | Trừ tự động | Việc lớn nhất |
|---|---|---|---|---|---|
| 1 | Chẩn đoán, hiệu năng & giới hạn (`diag`) | 94,7 | 0 | 2,6 | bảng khâu bỏ sót tên khâu thật (`videos`, `delivery`, `image_gen`) |
| 2 | Khớp môi | 94,6 | 0 | 0,9 | độ khớp đo thật 0,42–0,53 < ngưỡng 0,65, cờ vẫn verified |
| 3 | Chạy tự động (Autopilot) | 92,5 | 0 | 4,7 | trần job/ngày chỉ kiểm 3/6 đường tạo job tốn tiền |
| 4 | Kiến thức & bộ kỹ năng 3 vai | 91,7 | 0 | 1,5 | danh mục Kho ≠ thứ Director đọc; duyệt bài học sát trần → mất bài học |
| 5 | Gói bối cảnh 3D | 91,3 | 0 | 3,9 | `composite_video` không kiểm mã thoát ffmpeg |
| 6 | Bước 3 · Motion & giọng | 88,1 | 0 | 8,6 | `voice_check.redo` xóa bản cũ + gửi lại cùng đầu vào |
| 7 | Tài liệu | 87,8 | 0 | 0 | `PLAN.md` còn ghi S11 "chưa code"; khối S13 trong TODO tự mâu thuẫn |
| 8 | Lõi pipeline & nhà cung cấp | 85,5 | **1** | 7,2 | **gửi trả tiền xong mới `start()` → bấm Tạm dừng đúng lúc = trả tiền 2 lần** |
| 9 | Bước 4 · Video + QC | 85,0 | 0 | 12,0 | `kling_multishot`, `scene_establish` bỏ qua trần dự án |
| 10 | Dashboard chung / giao diện | 84,3 | 0 | 9,7 | nút "Đã nạp tiền — mở lại" không kiểm quyền; trang chủ dựng video mọi lần rerun |
| 11 | Bước 5 · Âm thanh & xuất bản | 84,0 | 0 | 10,2 | duyệt bản thô P2/P3 chưa chạy Claude thật; thiếu `need_edit` |
| 12 | Hệ thống phát triển (devsys) | 82,6 | 0 | 4,6 | bộ đo cờ lệch với `core.features.on`; cổng bằng chứng nông |
| 13 | Ngân sách & sổ chi | 82,2 | 0 | 10,1 | giá chưa biết tính = 0 USD; nới trần không kiểm quyền |
| 14 | Bước 2 · Ảnh + QC | 80,8 | 0 | 16,1 | `costume.make_character_set` gửi Deepix trả tiền bỏ qua mọi cổng |
| 15 | Bước 1 · Kịch bản & Đạo diễn | 80,1 | 0 | 11,8 | `CTA_TEXT:` / `TITLE:` thành người nói ở đường kịch bản dán |
| 16 | Kho tài nguyên | **74,6** | **1** | 10,0 | `costume` bỏ qua cổng tiền (chặn); `assets.merge` xóa ảnh im lặng |

Điểm nhìn nhanh:
- **Không khu vực nào "đỏ" về chức năng**; điểm thấp đến từ **an toàn khi lỗi** (tin cậy 3,5–11,5/12) và **bảo trì**: `header.py` 1029 dòng, `llm_runner.py` 1238, `runner.py` 1715.
- Điểm cao nhất tập trung vào khu vực nhỏ, đã đo thật (`diag`, khớp môi). Khu vực lớn có nhiều đường vào tốn tiền (Bước 1/2, Kho, Ngân sách) có nhiều lỗ hơn.
- 2 lỗi **chặn**: `costume.make_character_set` (tiền ngoài cổng) và cửa sổ gửi–bắt đầu job (`core_infra`; **đã tái hiện bằng nhà cung cấp giả: `submit` gọi 2 lần cho 1 job**).

## 2. Phân tích: các việc lặp lại ở nhiều khu vực (sửa một lần, gỡ nhiều điểm)

| # | Vấn đề gốc | Khu vực dính | Mức | Sửa |
|---|---|---|---|---|
| P1 | **Hàm ghi / tốn tiền không gọi `access.need_edit` ở lõi** (quyền chỉ khóa ở UI): `llm_io.*`, `script_parser.import_scenes`, `claude_tasks` (8 hàm), `voice.generate`, `voice_check.redo`, `kling_multishot`, `model_router.set_override`, `editor_review/apply`, `music/audio_lib.submit_*`, `previz`, `qc_agent`, `costume`, `raise_cap/set_target/budget.reopen`, `trash.restore` | step1/2/3/4/5, budget, assets, core_infra, diag | lớn (K9) | một test **quét mọi hàm ghi/hàm gọi nhà cung cấp** phải có `need_edit` (hoặc nằm trong danh sách miễn có lý do) + thêm hàm còn thiếu |
| P2 | **Lời gọi tốn tiền đi ngoài cổng chung** (`check_*` + `SPEND_LOCK` + `project_budget.check` + ước tính trước): `costume.make_character_set` (chặn), `kling_multishot`, `scene_establish.step`, autopilot `_daily_cap` (3/6 đường), `adapters/trial.py`; **giá chưa biết tính 0 USD** | step2, step4, assets, budget, autopilot, core_infra | chặn/lớn (K7, K2) | một hàm cổng duy nhất `paid_call(...)` bắt buộc cho mọi `provider.submit`; test quét `provider.submit` ngoài cổng; giá `None` = từ chối khi dự án đã khóa |
| P3 | **Mất dữ liệu / trả tiền lại khi thao tác giữa chừng** (K5): `voice_check.redo`, `assets.merge`, "Gỡ liên kết TẤT CẢ", "Xóa ảnh", `sync_knowledge` + `lessons.decide`, `composite_video` | step3, assets, knowledge, plates3d | lớn | "ghi bản mới rồi mới xóa bản cũ"; xác nhận + thùng rác cho mọi xóa hàng loạt |
| P4 | **Vòng đời job & hủy**: bấm Tạm dừng lúc đang gửi → trả tiền 2 lần; "Hủy việc" không hủy ở ClipAI/Deepix; sync.so `COMPLETED` không `outputUrl` chờ mãi; Meshy lỗi mạng để lại dòng SENDING | core_infra, lipsync, plates3d | chặn/lớn | sau `submit` thành công ghi `external_id` + chuyển `running` trong cùng giao dịch; `cancel_job` gọi nhà cung cấp; hạn chờ cho mọi trạng thái `running` |
| P5 | **Bộ đo của devsys sai/nông** (làm điểm sai âm thầm): bộ dò cờ bỏ `data/feature_settings.json` + hằng `FLAG`/`CLAUDE_FLAG`; `check_evidence` nhận `test:tên_giả`; `import_score` không đối chiếu `input_hash`; chưa có lần chấm Claude API thật | devsys, step2, step4 | lớn | xem mục 6 (thang v2.1) |
| P6 | **Dữ liệu web là "tin cậy"**: `ff_site` chạy trang bằng `vm.runInContext`, URL ảnh không kiểm miền, văn bản web vào prompt "BẮT BUỘC" không bọc là dữ liệu | assets, knowledge | lớn (K9) | parse JSON thuần / tiến trình riêng, allowlist miền, bọc `<du_lieu_ngoai>`, test "ignore previous instructions" |
| P7 | **Tài liệu tự mâu thuẫn**: khối S13 trong `TODO.md`, `PLAN.md` mục 3.10 ghi S11 "chưa code", `RUNBOOK` thiếu phân quyền, `WORKFLOW_REVIEW` nói chưa có phân quyền | docs, diag, core_infra | lớn (tai_lieu) | dọn TODO, sửa PLAN + `bash tools/build_docs.sh` |
| P8 | **Nút tốn tiền không ghi giá**: 4 nút Claude Bước 1, nút vẽ lại Bước 2, nút TTS Bước 3, "Xuất bản đầy đủ" Bước 5 | step1/2/3/5 | lớn/nhỏ (K7) | test quét `st.button` gọi hàm tốn tiền phải có `llm_tag`/giá |
| P9 | **Chữ lỗi tiếng Anh lộ ra người dùng** (SchemaError, lỗi Deepix, lỗi sửa nhân vật) | step1/2 | nhỏ | dịch + kèm cách sửa |

**Riêng dashboard (`dashboard_ui`, 84,3):**
- 🔴 Nút **"Đã nạp tiền — mở lại dịch vụ"** trong thẻ 💵 (`dashboard/header.py:417-418`) không kiểm quyền: ai đăng nhập cũng gỡ được cờ hết tiền toàn cục (nút cùng việc trong hộp thoại Ngân sách đã có `allowed('settings')`).
- 🔴 ⌂ Tất cả dự án mục "Sản phẩm đã hoàn tất" **mở/dựng video của mọi dự án xong ở mỗi lần rerun** (`home.py:239-247`); phép đo hiệu năng chỉ thử 50 dự án *chưa có video* nên không bắt được.
- 🟠 Hai giao diện (v2 và bản cũ) chạy song song trong cùng hàm (`header.py` 1029 dòng, `home.py`, `team_screen.py`); `ui_v2` vẫn `verified=False` (mặc định tắt), chưa thử trên dự án thật.
- 🟠 `shell_parts.next_line` biến lỗi thành "Chưa có việc nào đang chờ ✅"; trùng lặp `short_text/show_estimate/confirm_all`.
- 🟡 Hộp 📥 chỉ có 6 loại việc, thiếu job lỗi và trạng thái "đã xem"; tooltip cắt cứng 420 ký tự, mọi popover chung nhãn "Chi tiết"; ⌂ 50 dự án là một cuộn dọc dài, thẻ Lỗi dùng cùng kiểu nút thẻ đang chạy.
- 🟡 Nghiệm thu S13.10 luôn thoát mã 1 vì phép đo "khóa widget mất" không biết bảng đổi tên có chủ ý (`retry_` → `dretry_`, `inbox_kind` có điều kiện) — cần bảng ánh xạ trong `tools/ui_v2_acceptance.py`. TODO ghi "0 khóa mất" lệch với `ui_metrics.json` (11 khóa động).
- ✅ Điểm tốt: phân quyền theo dự án chặn cứng ở lõi (`core/access.py`) có chế độ chỉ xem; tương phản 0 chữ < 4.5:1 ở 40 vùng; click 14 = 14; hiệu năng ⌂ −8,8 %, Storyboard +16,4 %.

## 3. So sánh với công cụ ngoài (chi tiết, nguồn và giới hạn trong 2 file so sánh)

Mức nguồn: đa số giá/tính năng chỉ ở mức bên thứ ba [B]; **chưa thử tay sản phẩm nào → đây là so sánh tính năng công bố, không phải chất lượng thật.**

| Khâu | Mình | Công cụ ngoài tốt nhất | Kết luận |
|---|---|---|---|
| K1 Kịch bản → shot | Director hai lượt + "người xem lần đầu" + kiểm bằng code | Higgsfield Cinema Studio 4.0 (trợ lý tách shot), Invideo (đội tác tử chọn model theo shot) | **mình hơn** (có kiểm + bằng chứng), họ gọn hơn |
| K2 Nhất quán nhân vật/bối cảnh | Kho + hồ sơ chuẩn FF + bối cảnh 3D thật (Blender/Meshy) | Runway References, Higgsfield Soul ID/Elements, **Seedance 2.5 (50 tham chiếu, phông xanh, mô hình trắng 3D)** | ngang; Seedance 2.5 có thể thu hẹp lợi thế bối cảnh 3D |
| K3 Storyboard/animatic | Deepix từng khung + cổng duyệt | LTX Studio, Katalist | ngang |
| K4 Video đa shot | model theo từng cảnh, khung đầu/cuối | Kling 3.x Multi-Shot, Seedance 2.5 (clip ≤ 30 s, long mode 180 s beta) | **kém** ở nối hành động qua điểm cắt / clip dài |
| K5 Khớp môi | Seedance + take (c) + đo bằng mốc môi | Higgsfield Lipsync Studio, HeyGen; mã nguồn mở MuseTalk, LatentSync | kém ở số lựa chọn; độ khớp đo thật còn thấp |
| K6 Giọng/nhạc/SFX | TTS clone giọng FF tiếng Việt, âm thanh trước −14 LUFS | Kling Native Audio (không tiếng Việt, theo bản 29/09) | **mình hơn** |
| K7 Dựng | ffmpeg theo luật nghề, phụ đề vùng an toàn TikTok | Runway (xuất ProRes/PNG tuần tự), Descript/Premiere | hơn ở tự động; **kém ở sửa và xuất timeline** |
| K8 QC | nhiều lớp + bảng luật code + QC bản dựng | không sản phẩm nào trong 13 công bố QC tự động nhiều lớp | **mình hơn rõ** |
| K9 Chi phí | sổ chi, ước tính trước, khóa cứng 3 tầng | n8n/Langfuse/Helicone (ghi sau, không chặn trước) | **mình hơn** (nhưng lỗ P2 làm yếu lời hứa này) |
| K10 Nhóm / UI | phân quyền theo dự án, hộp thư, mức tự động | Flow (lưới tài sản, Collections), Higgsfield (chia sẻ Element cho nhóm) | **kém** ở UX; ngang ở phân quyền |

**Họ có, mình chưa có** (xếp theo giá trị / công sức): sửa clip cục bộ (S4.12 — kiểm ClipAI có đưa ra API không) · nối hành động qua điểm cắt · xuất timeline/ProRes cho Premiere · giọng gắn hồ sơ nhân vật · "QC prompt trước khi gửi" (Higgsfield Assist) · lưới tài sản kiểu Flow cho Kho.
**Mình có, họ không công bố:** QC nhiều lớp · trần chi phí cứng 3 tầng · Director hai lượt + người xem lần đầu · âm thanh trước −14 LUFS · dựng theo luật nghề + vùng an toàn TikTok · giọng clone FF tiếng Việt.
**Không nên làm:** chạy video cục bộ bằng ComfyUI/Wan/Hunyuan/LTX (máy chỉ có GTX 1070 Ti 8 GB); nhúng n8n/LangGraph/Langfuse/Remotion (mình đã có autopilot, sổ chi chặn trước; Remotion cần giấy phép công ty nếu đội > 3 người). Sora đã ngừng (API tắt 24/09/2026 [B]). Giá 2.5 cao hơn 2.0 ~47 % ([A]) → cần phản ánh vào ước tính trước, đừng dùng số giá [B] để lập ngân sách.

## 4. Phương án nâng cấp dashboard (đề xuất — chờ bạn chọn, chưa làm gì)

Thứ tự theo rủi ro tiền/quyền trước, trải nghiệm sau. 💻 = code miễn phí, 💵 = tốn tiền, 👤 = người dùng làm/quyết.

### Đợt 1 — "Đóng lỗ tiền & quyền" (💻, ưu tiên 1, ~1 phiên làm việc)
1. Cổng tiền duy nhất `paid_call` + test quét `provider.submit` ngoài cổng; vá `costume.make_character_set`, `kling_multishot`, `scene_establish`, autopilot `_daily_cap`, `trial`; giá `None` = từ chối khi dự án đã khóa (P2).
2. Test quét hàm ghi/tốn tiền phải có `need_edit`; thêm cho danh sách P1; nút "mở lại dịch vụ" + `raise_cap/set_target` + hộp thoại restart đi qua `money_reset.reset` (Owner + lý do + audit).
3. Sửa cửa sổ gửi–bắt đầu job (trả tiền 2 lần khi Tạm dừng) + "Hủy việc" gọi hủy ở nhà cung cấp (P4), kèm test hồi quy bằng nhà cung cấp giả.
4. `voice_check.redo`: giữ bản cũ tới khi bản mới xong, đếm lần redo, chặn lần 3 (luật gen lại ≤ 2).

### Đợt 2 — "Không mất dữ liệu / lỗi nói rõ" (💻, ưu tiên 2)
5. `assets.merge` chuyển mọi trạng thái ảnh hoặc từ chối; xác nhận + thùng rác cho "Gỡ TẤT CẢ" và "Xóa ảnh"; `sync_knowledge` ghi bản mới rồi mới xóa bản cũ; `composite_video` kiểm mã thoát; Meshy bắt lỗi mạng (P3).
6. Gỡ lỗi nhỏ có chứng minh: `CTA_TEXT/TITLE` vào `NOT_SPEAKERS` một nơi; bảng `diag.STAGES` đủ tên khâu + test; `look_trust` dùng cùng sàn cứng với `apply_qc`; danh mục Kho kiến thức khớp bộ 3 vai (P8, P9 gộp: nhãn giá cho mọi nút tốn tiền, dịch chữ lỗi tiếng Anh).
7. Hardening `ff_site` (P6).

### Đợt 3 — "Dashboard dễ dùng hơn" (💻; một số 👤)
8. 👤 **Bạn dùng thử `ui_v2` trên dự án thật** rồi duyệt cổng G1 → bật mặc định, **xóa nhánh giao diện cũ**, tách `header.py`/`home.py`/`team_screen.py` (gỡ gốc "hai giao diện trong một hàm").
9. ⌂: không dựng video mọi lần rerun (chỉ khi bấm), phân trang/nhóm theo trạng thái ("Cần bạn" → "Đang chạy" → "Lỗi" → "Xong"), thẻ Lỗi khác kiểu nút; thêm ca dự án-đã-xong vào phép đo hiệu năng.
10. Hộp 📥 thành **hộp thư thật** (ý từ so sánh nhóm B): Duyệt / Từ chối / Hoãn ngay trong hộp; có job lỗi; trạng thái đã xem; xếp theo mức chặn dây chuyền; từ chối hai kiểu (loại bỏ / gửi lại kèm ghi chú).
11. Tooltip không cắt cứng, nhãn popover phân biệt; bảng ánh xạ khóa cũ→mới để nghiệm thu S13.10 thoát mã 0.
12. Hiển thị mới (nhóm B): cây vết từng shot (ảnh→video→QC→dựng), biểu đồ tiêu hao so với trần 3 tầng, bảng điểm QC theo lần gen, gắn nguồn 🧮/🤖/👤 cho mỗi điểm QC, bản đồ nhiệt shot × khâu ở ⌂, nhật ký tự duyệt có đảo ngược.

### Đợt 4 — "Năng lực mới từ so sánh ngoài" (kiểm trước khi làm)
13. 💻 Kiểm ClipAI: sửa clip cục bộ (Seedance 2.5 Intelligent Edit), phông xanh / mô hình trắng 3D qua API → có thể thay bối cảnh 3D tự dựng; cập nhật bảng giá 2.5 vào ước tính (💵 thử 1 clip có trần).
14. 💻 QC danh tính bằng DINO (không dùng InsightFace — giấy phép phi thương mại); thử MuseTalk/LatentSync 1 clip ngắn trên máy 8 GB (có thể không chạy được).
15. 💻 Xuất timeline / ProRes cho Premiere; nối hành động qua điểm cắt (K4).

### Đợt 5 — Cần tiền hoặc quyết định của bạn (👤 / 💵)
- Chạy thật các cờ BẬT mà `verified=False` (Đợt 5 trong TODO; 7 cờ ở Bước 2, 3 ở Bước 1/3, 4 ở Bước 4…); chạy Director thật với `film_crew`; chạy P2→P3 duyệt bản thô trên #8 (~0,17 USD); đo `asset_vision` trên 5–10 nhân vật (vài cent); chạy lại `qc_team` trên bộ độc lập 134 khung.
- Chính sách đăng nhập: hiện chỉ bằng e-mail, không mật khẩu; quyền theo dự án dựa vào đó. Chỉ an toàn trên mạng tin cậy → nếu mở LAN: mã một lần/SSO.
- Số click "Dự án mới → video đầu" 14 = 14: muốn giảm phải đổi UX (gộp bước ngân sách với Director, bỏ bước xác nhận).

## 5. Việc cần bạn quyết ngay
1. Duyệt **Đợt 1 + 2** (an toàn tiền/quyền/dữ liệu) làm trước? Tôi đề xuất chia 4–5 nhánh song song như đợt vừa rồi, mỗi nhánh có test hồi quy.
2. Bạn có thể dùng thử `ui_v2` trên dự án thật khi nào để mở Đợt 3 mục 8?
3. Có cho phép kiểm ClipAI (Đợt 4 mục 13) — cần xem trang/đăng nhập ClipAI của bạn, thử 1 clip trả tiền có trần.

## 6. Tối ưu cách chấm của AI Dev — việc còn lại cho thang v2.1 (từ chính phản hồi của người chấm)

**Đã có ở v2** (nhánh 03/10): mức chặn/lớn/nhỏ do code gán điểm, số đo tự động (`devsys/metrics.py`), checklist K1–K10, độ ổn định, trần khi còn lỗi chặn.
**Lần chấm này đã chứng minh thang bắt được lỗi thật** (ví dụ: tái hiện trả tiền 2 lần, mất ảnh khi gộp, mất bài học) — nhưng người chấm cũng chỉ ra chỗ cần sửa:

| # | Vấn đề | Đề xuất v2.1 |
|---|---|---|
| S1 | **Bộ dò cờ lệch**: `collect.flags_state` bỏ `data/feature_settings.json` + preset; bỏ sót hằng `FLAG`/`CLAUDE_FLAG` (đã chạy thật: `ui_v2` bật nhưng devsys báo tắt) | gọi thẳng logic `core.features.on`; test hồi quy |
| S2 | **Cổng bằng chứng nông**: `test:tên_không_tồn_tại` vẫn là bằng chứng cứng; `giai_thich_chenh` chỉ cần có chữ | kiểm tên test bằng `ast`; kiểm evidence của giải thích |
| S3 | **Nhập điểm không đối chiếu dữ liệu export** (file chấm trên dữ liệu cũ vẫn "khớp") | so `input_hash`; luôn lấy `commit/date` từ hệ thống |
| S4 | **Cap `test` phụ thuộc môi trường**: chấm trong worktree thiếu `data/` → bị cap oan (step1 77,1 so với 80,1) | cảnh báo / bỏ cap khi thiếu `data/test_runs`, in "nguồn" của `code_caps` khi nhập |
| S5 | **Quy tắc ổn định so giữa hai người chấm khác nhau** làm lần nhập bị từ chối (step1: lệch 5,3 so với người chấm B) | chỉ so cùng người chấm, hoặc chấp nhận `giai_thich_chenh` giữa người chấm |
| S6 | **Khu vực chỉ có tài liệu bị trần ~88** (test luôn 2,4/12) | `test` = "không áp dụng", chia lại trọng số |
| S7 | **`chan` quá chủ quan / không tính xác suất** (race hẹp = chặn, trần 89 cả khu vực) | thêm "dễ gặp" (thường/hiếm) làm hệ số; ngưỡng tiền cụ thể |
| S8 | **Một lỗi chạm nhiều tiêu chí, không có quy tắc chọn tiêu chí chính** (thiếu `need_edit` = tin_cay hay tuân_thủ?) | bảng "loại K → tiêu chí mặc định" |
| S9 | **Checklist thiếu loại lỗi**: vòng đời/đồng thời/hủy, "xóa trước rồi gửi lại", "mất dữ liệu khi thay thế" | thêm K11 vòng đời job, K12 phá hủy-trước-khi-có-bản-mới; bỏ `khac` |
| S10 | **Trần khoản trừ tự động che bớt thông tin** (13 chỗ nuốt lỗi = 18 chỗ = −4); `nuot_loi` đếm cả chip trạng thái vô hại có chú thích | trọng số theo mức nguy hiểm; bỏ except có chú thích lý do |
| S11 | **`todo_mo` đếm nhầm** dòng `[x]` đã xong có chữ "chưa chạy thật" và quy ước `[ ]`; không trừ TODO "chờ người dùng quyết" dù là việc thật | phân loại: việc code / việc người dùng / quy ước |
| S12 | **Bộ đo giao diện không áp cho `step1/2`** (khu vực có màn Streamlit) và `man_nhieu_nut` đo theo file; **phép đo không đạt (11 khóa mất) không bị trừ** | gán số đo giao diện cho mọi khu vực có màn; luật trừ cho `keys_lost` sau khi có bảng ánh xạ |
| S13 | **Dữ liệu xuất bị cắt** (`runner.py`, `step4.py`, 66 tài liệu) trong khi tiêu chí cần đọc chính các file đó | tăng ngân sách trích cho khu vực lớn; chia tách file lớn |
| S14 | **`overall()` trộn thang v1 và v2** khi chưa chấm lại hết | chỉ trung bình cùng thang, hiển thị "chưa chấm v2" |
| S15 | **`bang_chung` có thể gian lận**: một dòng `TODO.md:1` là đủ 16 điểm | đòi trích dẫn kèm số đo, code kiểm chuỗi số |
| S16 | Đường chấm **Claude API chưa chạy thật** (35 file điểm đều từ phiên Claude Code) | chạy 1 khu vực nhỏ (`--areas diag --yes`) để có số chi thật so với ước tính (💵 vài cent) |

Cách chấm nên giữ: người chấm chỉ ghi khoản trừ + bằng chứng, code tính điểm; **2 người chấm độc lập cho vài khu vực mỗi đợt** để theo dõi chênh lệch (lần này `dashboard_ui` chênh 0,2, `step1` chênh 5,3 — lý do chủ yếu là khác nhau về lỗi `CTA_TEXT` và quyền ở `llm_io`, không phải nhiễu).
