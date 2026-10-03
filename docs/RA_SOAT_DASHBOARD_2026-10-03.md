# Rà soát toàn bộ dashboard bằng AI Development System (thang v2) + kế hoạch nâng cấp — 2026-10-03

> Gồm: (1) chấm lại 16 khu vực theo **thang v2** (`devsys/rubric.md`); (2) **kiểm chứng độc lập** từng lỗi lớn bằng tái hiện/đọc code (3 phiên, CSDL tạm + nhà cung cấp giả, 0 USD) để
> chỉnh mức nghiêm trọng đúng thực tế; (3) so sánh công cụ ngoài; (4) kế hoạch nâng cấp **chỉ dựa trên điều đã xác nhận**.
> **0 USD** (chấm bằng các phiên Claude Code, không gọi Claude API). Code lúc chấm: `main` c849908…5fb6b69, test lưu **1972 qua, 0 lỗi, 1 bỏ qua**.
> Chi tiết khoản trừ từng khu vực (file:dòng, cách sửa): web AI Development System (cổng 8502) và `devsys/data/report.md` (`py tools/devsys_score.py --report`, không vào git).
> Bằng chứng kiểm chứng: `devsys/data/incoming/KIEM_CHUNG_{TIEN_VA_VONG_DOI,QUYEN_VA_DU_LIEU,DASHBOARD}.md` (không vào git; tóm tắt đầy đủ ở mục 2).
> So sánh ngoài: `docs/SO_SANH_NGOAI_A_NEN_TANG_2026-10-03.md`, `docs/SO_SANH_NGOAI_B_WORKFLOW_VA_CONG_CU_2026-10-03.md`. Cách chấm v2: `docs/DANH_GIA_CACH_CHAM_DEVSYS_2026-10-03.md`.

## 1. Điểm 16 khu vực (thang v2; lần chấm lại 03/10 sau kiểm chứng)

Tổng có trọng số **85,6** (trung bình thường 86,4; thấp nhất 76,4, cao nhất 94,7). Thang v2 khác thang v1 (mức chặn/lớn/nhỏ, số đo tự động, thêm tiêu chí tin cậy + bảo trì) nên
**đây là mốc mới, không so thẳng với 87,2 của v1**. Hai người chấm độc lập cho `dashboard_ui` ra 84,3 và 84,5 (chênh 0,2); `step1`: 80,1 / 85,4 (chênh 5,3 — có giải thích: lỗi `CTA_TEXT` và quyền `llm_io`).

| Hạng | Khu vực | Điểm | Chặn | Việc lớn nhất (mức đã hiệu chỉnh sau kiểm chứng) |
|---|---|---|---|---|
| 1 | Chẩn đoán, hiệu năng & giới hạn | 94,7 | 0 | bảng khâu bỏ sót tên khâu thật (`videos`, `delivery`, `image_gen`) |
| 2 | Khớp môi | 94,6 | 0 | độ khớp đo thật 0,42–0,53 < ngưỡng 0,65; cờ vẫn verified nhờ người xem |
| 3 | Chạy tự động | 92,5 | 0 | trần job/ngày thiếu 3/6 đường (nhỏ: trần tiền vẫn áp) |
| 4 | Kiến thức & bộ kỹ năng 3 vai | 91,7 | 0 | danh mục Kho ≠ thứ Director đọc khi `film_crew` bật (đã đọc code: đúng) |
| 5 | Gói bối cảnh 3D | 91,3 | 0 | `composite_video` không kiểm mã thoát ffmpeg (lớn nhưng rất hiếm) |
| 6 | Bước 3 · Motion & giọng | 89,7 | 0 | `voice_check.redo` trả TTS lặp (nhỏ — TTS chưa có giá USD) |
| 7 | Tài liệu | 88,2 | 0 | `PLAN.md` còn ghi S11 "chưa code"; khối S13 trong TODO tự mâu thuẫn |
| 8 | Lõi pipeline & nhà cung cấp | 85,5 | 1 | **gửi trả tiền xong mới `start()`: Tạm dừng đúng lúc → trả tiền 2 lần (đã tái hiện; lớn nhưng hiếm)** |
| 9 | Dashboard chung / giao diện | 84,3 | 0 | ⌂ dựng video mọi lần rerun (đã đo); nút "mở lại dịch vụ" không kiểm quyền (đã tái hiện) |
| 10 | Bước 5 · Âm thanh & xuất bản | 84,0 | 0 | duyệt bản thô P2/P3 chưa chạy Claude thật; nút "Xuất bản đầy đủ" không ghi giá |
| 11 | Bước 4 · Video + QC | 83,8 | 0 | cửa sổ gửi–bắt đầu job (như trên); `composite_video`; 4 cờ bật chưa verified |
| 12 | Hệ thống phát triển (devsys) | 83,5 | 0 | bộ dò cờ lệch `core.features.on`; `import_score` không đối chiếu `input_hash` |
| 13 | Ngân sách & sổ chi | 82,3 | 0 | ước tính/bảng giá chưa nghiệm thu thật sau #8; nút "mở lại dịch vụ" |
| 14 | Bước 2 · Ảnh + QC | 79,7 | 0 | `costume.make_character_set` bỏ qua cổng tiền (lớn, thường gặp) |
| 15 | Bước 1 · Kịch bản & Đạo diễn | 79,6 | 0 | `CTA_TEXT:`/`TITLE:` thành người nói ở đường kịch bản dán; 3 nút Claude không ghi giá |
| 16 | Kho tài nguyên | **76,4** | 0 | `assets.merge` mất ảnh/hồ sơ; xóa hàng loạt không xác nhận; `costume` |

Sau kiểm chứng **không còn lỗi mức "chặn" nào** là lỗi thường gặp gây mất tiền lớn (hai lỗi từng bị xếp "chặn" thực tế là "lớn": một thường gặp nhưng ≤ 2 ảnh/lần, một hiếm).
Điểm thấp nhất đến từ **an toàn khi lỗi / mất dữ liệu / nút tốn tiền không ghi giá**, không phải từ thiếu chức năng.

## 2. Lỗi đã kiểm chứng (mức thực tế, độ dễ gặp, điều kiện) — và lỗi bị bác bỏ

### 2.1 Tiền & vòng đời job (tái hiện bằng nhà cung cấp giả / CSDL tạm)
| # | Lỗi | Kết luận | Mức thực tế | Dễ gặp | Điều kiện | Sửa tối thiểu |
|---|---|---|---|---|---|---|
| T1 | `costume.make_character_set` gửi 2 ảnh Deepix, bỏ qua `check_image`/`SPEND_LOCK`/`project_budget.check`/`halted`/tạm dừng (`core/costume.py:50-60`) | ✅ tái hiện (halt, image_cap=0, paused vẫn gửi 2) | **lớn** (tối đa 2 ảnh/lần bấm) | thường | bấm nút ở `step1_characters.py:75-79`, không cần cờ | cổng tiền trước vòng `submit` + kiểm tạm dừng + giá trên nút |
| T2 | Tạm dừng đúng lúc runner đang gửi: `submit` + ghi sổ xong mới `Pipeline.start()` (`core/runner.py:208,233`, `core/pipeline.py:340-343`) → `PipelinePaused`, job `queued` kèm `external_id`, lần sau gửi lại | ✅ tái hiện (`submit` 2 lần, sổ chi ghi 2 lần) | **lớn** | **hiếm** (cửa sổ = 1 lời gọi `submit`) | bấm Tạm dừng đúng lúc | dùng `transition(RUNNING)` thay `start()`; nhận lại job `queued` đã có `external_id` |
| T3 | "Hủy việc" (`cancel_all_active`) chỉ đổi trạng thái DB, không gọi `provider.cancel` | ✅ một phần | nhỏ–lớn (ClipAI vẫn chạy và tính tiền; Deepix **không có API hủy**) | thường | job running có `external_id` | gọi `runner.cancel_job` cho video running; đổi chữ nút cho ảnh Deepix |
| T4 | `kling_multishot`, `scene_establish.step` (+ `end_frames.tick`, phát hiện thêm) chỉ kiểm trần toàn cục, bỏ `project_budget.check` | ✅ | nhỏ (≤ ~1,2 USD/lần) | hiếm | dự án đã khóa ngân sách; establishing cần cờ `scene_establishing` (tắt mặc định) | `project_budget.check` trong `SPEND_LOCK` ở 3 chỗ |
| T5 | Trần job/ngày `AUTOPILOT_DAILY_JOBS` thiếu 3/6 đường; `end_frames` không được đếm | ✅ | nhỏ (trần mềm; trần tiền, cap video, SHOT_SENDS vẫn áp) | hiếm | sát 300 job/ngày | gọi `_daily_cap` ở 573, 795; đếm `end_frames` |
| T6 | Giá chưa biết tính 0 USD (`runner.py:1044,1444`) | ⚠ một phần | nhỏ ở chế độ thường (router không chọn model giá null); lớn nếu tự đặt env/model | hiếm | đợt thử tắt + dự án khóa + model giá null | giá `None` + dự án khóa → từ chối; `ledger_by_stage` ghi "chưa có giá" |
| T7 | `voice_check.redo` xóa dòng cũ, bộ đếm về 0, bấm 🔁 nhiều lần trả TTS lặp | ⚠ một phần | nhỏ (TTS chưa có giá USD) | hiếm–vừa | nút thủ công | giữ `resends` cộng dồn, chặn vượt `MAX_RESENDS` cùng đầu vào |
| T8 | `adapters/trial.py` gửi tốn tiền chỉ cần `--yes` | ✅ nhưng là **công cụ dòng lệnh**, không dashboard nào gọi | nhỏ, chủ ý | hiếm | gõ tay | (tùy chọn) in ước tính + ghi sổ |
| T9 | `composite_video` không kiểm mã thoát ffmpeg → file hỏng 7 byte ghi đè clip đã trả tiền | ✅ tái hiện | lớn về dữ liệu | **rất hiếm** | cờ `location_plates` + chế độ green | kiểm `returncode`, giữ bản gốc đến khi kiểm xong |

### 2.2 Quyền (nhỏ hơn dự đoán ban đầu)
- Người lạ **không chọn được** dự án của người khác (danh sách lọc theo quyền) và khóa "chỉ xem" **có hiệu lực ở phía server** (Streamlit 1.64.0 bỏ giá trị gửi lên của widget `disabled`). Vì vậy việc nhiều hàm lõi thiếu `need_*` là **lớp phòng thủ thứ hai còn thiếu, chưa phải lỗ hổng người thường chạm tới qua UI** (quét tự động: 188 hàm công khai ghi DB/gọi provider không `need_*`, 112 có đường gọi từ `dashboard/`; phần lớn nằm sau khóa UI hoặc là hàm toàn cục đã rào bằng `allowed(...)`).
- ✅ **Lỗ hổng thật qua UI (đã chạy AppTest):** nút "Đã nạp tiền — mở lại dịch vụ" (`dashboard/header.py:417-418` → `budget.reopen`): thành viên không có quyền, người chỉ xem, người lạ có dự án riêng đều bấm được và xóa cờ hết tiền (mức nhỏ–vừa; khóa tự khóa lại khi gặp 402). Và "↩ Khôi phục" trong hộp thoại Lịch sử (`dashboard/admin.py:874`): người chỉ xem bấm được (nhỏ).
- ❌ **Bác bỏ:** `script_parser.import_scenes` (đã chặn gián tiếp qua `create_scene`/`set_script_text`); hộp thoại Đợt thử/Claude restart (chỉ mở sau `allowed("settings")`; chỉ thiếu tự kiểm lại quyền khi Owner thu quyền giữa phiên).
- ⚠ Đăng nhập chỉ bằng e-mail: rủi ro thật **chỉ khi mở LAN**. `dashboard.env` hiện **`DASHBOARD_LAN=1`, không có mã Owner** → ai trong mạng nội bộ gõ e-mail một đồng nghiệp `@garena.vn` đều thành người đó (xem/sửa/duyệt/chi tiền trên dự án của họ), không giới hạn số lần thử; Owner từ máy khác bị từ chối. Reverse proxy/tunnel cùng máy (ngrok, cloudflared, nginx) làm mọi người trông như localhost → Owner vào được bằng e-mail không cần mã. `requirements.txt` ghi `streamlit>=1.40` (cơ chế khóa phía server cần ghim phiên bản tối thiểu).

### 2.3 Mất dữ liệu (tái hiện trên CSDL/thư mục tạm)
| # | Lỗi | Kết luận | Mức | Dễ gặp | Sửa tối thiểu |
|---|---|---|---|---|---|
| D1 | `assets.merge` (`core/assets.py:322-363`): chỉ chuyển ảnh đã duyệt còn file, rồi `delete()` nguồn → mất ảnh chờ duyệt, ảnh mất file, hồ sơ chuẩn; đích đầy 6 ảnh thì xóa ảnh đã duyệt | ✅ (nguồn 1 duyệt + 1 chờ + 1 mất file + hồ sơ → còn 1 dòng, file chờ bị xóa khỏi đĩa) | **lớn** | trung bình | chuyển mọi trạng thái hoặc từ chối; chỉ `delete()` khi nguồn hết ảnh; xác nhận |
| D2 | "Gỡ liên kết TẤT CẢ ảnh mất file" không `confirm_all` (`dashboard/admin.py:309,319-320`) | ✅ (đổi tên thư mục kho → mọi ảnh báo mất → một lần bấm xóa hết dòng; file thành mồ côi) | vừa–lớn | thấp–trung bình | `confirm_all`; chỉ gỡ dòng `can_reload=False` |
| D3 | "Xóa ảnh" xóa dòng + file ngay, không thùng rác (`admin.py:776-778`) | ✅ | vừa | trung bình | thùng rác + `confirm_all` |
| D4 | `lessons.decide` ghi `approved` rồi `sync_knowledge` xóa doc cũ trước `add_doc`, ném `ValueError` khi vượt 150.000 ký tự; `admin.py:1158-1164` không bọc try | ✅ (chạy tái hiện) | vừa | **rất hiếm** (`data/knowledge_user` hiện rỗng) | `add_doc` mới trước, gỡ cũ sau; bọc try |
| D5 | `ff_site`: `vm.runInContext` (docstring "không mạng, không file" **sai**: trang giả ghi file TEMP và chạy `execSync`), URL ảnh `file://`/`127.0.0.1` được tải, văn bản web vào prompt không bọc "dữ liệu" | ✅ | lớn về kỹ thuật | **rất hiếm** (phải chiếm nội dung ff.garena.com/CDN hoặc chặn TLS) | bỏ `vm`/parser thuần, chỉ `https` + host garena, bọc khối dữ liệu |
| D6 | `CTA_TEXT:`/`TITLE:` thành người nói ở đường kịch bản dán (`core/dialogue.py:24-38`, `script_parser.py:61-72`; B4 chỉ sửa đường Ý tưởng) | ✅ (chạy `dialogue.lines`: +3,1 s, 2 nhân vật thừa) | lớn (chức năng) | thường với kịch bản có CTA | đưa vào `NOT_SPEAKERS` một nơi |
| D7 | Danh mục Kho kiến thức (`GROUPS`) ≠ tài liệu Director đọc khi `film_crew` bật (`FEATURE_FILM_CREW=1`) | ✅ (đọc code) | lớn (hiển thị/ước tính token sai) | thường | `GROUPS` theo cờ + test so với `prompts.py` |

### 2.4 Dashboard (đo/chạy thật)
| # | Lỗi | Kết luận | Số đo / ghi chú |
|---|---|---|---|
| U1 | ⌂ "Sản phẩm đã hoàn tất" (`home.py:239-247`) dựng video của **mọi dự án xong ở mỗi rerun** (thân `st.expander` luôn chạy dù đóng) | ✅ **nặng hơn dự đoán** | 20 dự án xong: rerun +58 % (clip 1 s) … +187 % (clip 14,5 MB); server thật: **~290 MB tải về trình duyệt ngay lần vào ⌂ đầu, RAM Streamlit 117 → 408 MB**; ⌂→Nhóm→⌂ tải lại 20 video (580 MB, không cache). Phép đo cũ (50 dự án chưa xong) không bắt được |
| U2 | Nút "mở lại dịch vụ" không kiểm quyền | ✅ AppTest | xem 2.2 |
| U3 | `shell_parts.next_line` biến lỗi thành "Chưa có việc nào đang chờ ✅" | ✅ (ép nguồn ném lỗi) | không log |
| U4 | Hộp 📥 thiếu job lỗi | ✅ | 6 loại việc; 4 job `failed` + 1 `retryable` → hộp rỗng, ⌂ ghi "Chưa chạy". "Trạng thái đã xem" **không cần** (hộp là danh sách suy ra từ trạng thái) |
| U5 | Trùng lặp: `short_text`, `show_estimate` trùng thật; `confirm_all` **bác bỏ** (chỉ 1 bản thật); hai giao diện song song | ⚠ một phần | gỡ giao diện cũ = 61 lời gọi `ui.v2_on()` ở 20 file, ~122 dòng điều kiện, 10 hàm `*_v2` song song; `header.py` 1029 dòng; `ui_v2` vẫn `verified=False` |
| U6 | Nghiệm thu S13.10 thoát mã 1 ("11 khóa mất") | ⚠ thực chất **0 điều khiển mất** | 11 lần xuất hiện của 5 khóa: `retry_`→`dretry_` (đổi tên), `inbox_kind` (chỉ khi > 3 việc), `fold_*_btn` (thay bằng expander). Công cụ không tra bảng `RENAMED` (chỉ nằm trong file test) |
| U7 | "110 chữ nhỏ" | ⚠ không tái hiện | 9 chữ đúng 12 px ở 4 lớp CSS cũ (`ui.py`: `.badge`, `.pbpct`, `.qcrow`, `.cardtitle`) — **12 px đạt luật "không chữ < 12 px"**; số 110 do bộ đếm phần tử DOM lặp |
| U8 | `TODO.md` dòng 24 ghi "0 khóa mất" | ⚠ lệch | thực tế 5 khóa / 11 lần, 0 mất "chưa giải thích" |

**Điểm tốt đã xác nhận:** phân quyền theo dự án chặn cứng ở lõi, có chế độ chỉ xem, thông báo tiếng Việt; tương phản 0 chữ < 4.5:1 ở 40 vùng (sáng/tối × 1440/1100); click 14 = 14; hiệu năng ⌂ 50 dự án −8,8 %, Storyboard 30 khung +16,4 %; B3 (tỉ lệ ảnh tham chiếu) đã sửa đúng + có test.

## 3. So sánh với công cụ ngoài (chi tiết/nguồn trong 2 file so sánh)

Mức nguồn: đa số giá/tính năng chỉ ở mức bên thứ ba [B]; **chưa thử tay sản phẩm nào → so sánh tính năng công bố, không phải chất lượng thật.**

| Khâu | Mình | Công cụ ngoài tốt nhất | Kết luận |
|---|---|---|---|
| K1 Kịch bản → shot | Director hai lượt + "người xem lần đầu" + kiểm bằng code | Higgsfield Cinema Studio 4.0, Invideo (đội tác tử chọn model theo shot) | **mình hơn** (có kiểm + bằng chứng); họ gọn hơn |
| K2 Nhất quán nhân vật/bối cảnh | Kho + hồ sơ chuẩn FF + bối cảnh 3D (Blender/Meshy) | Runway References, Higgsfield Soul ID, **Seedance 2.5 (50 tham chiếu, phông xanh, mô hình trắng 3D)** | ngang; Seedance 2.5 có thể thu hẹp lợi thế bối cảnh 3D |
| K3 Storyboard/animatic | Deepix từng khung + cổng duyệt | LTX Studio, Katalist | ngang |
| K4 Video đa shot | model theo từng cảnh, khung đầu/cuối | Kling 3.x Multi-Shot, Seedance 2.5 (≤ 30 s, long mode 180 s beta) | **kém** ở nối hành động qua điểm cắt / clip dài |
| K5 Khớp môi | Seedance + take (c) + đo mốc môi | Higgsfield Lipsync Studio, HeyGen; mã nguồn mở MuseTalk, LatentSync | kém ở số lựa chọn; độ khớp đo thật còn thấp |
| K6 Giọng/nhạc/SFX | TTS clone giọng FF tiếng Việt, âm thanh trước −14 LUFS | Kling Native Audio (không tiếng Việt, theo bản 29/09) | **mình hơn** |
| K7 Dựng | ffmpeg theo luật nghề, phụ đề vùng an toàn TikTok | Runway (ProRes/PNG tuần tự), Descript/Premiere | hơn ở tự động; **kém ở sửa & xuất timeline** |
| K8 QC | nhiều lớp + bảng luật code + QC bản dựng | không sản phẩm nào trong 13 công bố QC tự động nhiều lớp | **mình hơn rõ** |
| K9 Chi phí | sổ chi, ước tính trước, khóa cứng 3 tầng | n8n/Langfuse/Helicone (ghi sau, không chặn trước) | **mình hơn** — nhưng T1/T4/T5 làm yếu lời hứa này |
| K10 Nhóm / UI | phân quyền theo dự án, hộp thư, mức tự động | Flow (lưới tài sản, Collections), Higgsfield (chia sẻ Element) | **kém** ở UX; ngang ở phân quyền |

**Họ có, mình chưa có:** sửa clip cục bộ (S4.12; cần kiểm ClipAI có đưa ra API không) · nối hành động qua điểm cắt · xuất timeline/ProRes cho Premiere · giọng gắn hồ sơ nhân vật · "QC prompt trước khi gửi" · lưới tài sản cho Kho.
**Mình có, họ không công bố:** QC nhiều lớp · trần chi phí cứng 3 tầng · Director hai lượt + người xem lần đầu · âm thanh trước −14 LUFS · dựng theo luật nghề + vùng an toàn TikTok · giọng clone FF tiếng Việt.
**Không nên làm:** chạy video cục bộ bằng ComfyUI/Wan/Hunyuan/LTX (máy chỉ **GTX 1070 Ti 8 GB**); nhúng n8n/LangGraph/Langfuse/Remotion (mình đã có autopilot và sổ chi chặn trước; Remotion cần giấy phép công ty nếu đội > 3 người). Sora đã ngừng (API tắt 24/09/2026 [B]). Giá Seedance 2.5 cao hơn 2.0 ~47 % ([A]) → cập nhật vào ước tính trước; **không dùng số giá [B] để lập ngân sách**.

## 4. Kế hoạch nâng cấp dashboard (chính xác — chỉ gồm điều đã xác nhận; chờ bạn duyệt, chưa làm gì)

Nguyên tắc: tiền/dữ liệu trước, trải nghiệm sau; mỗi đợt chia **nhánh song song độc lập** (mỗi nhánh một worktree, test hồi quy, commit riêng, tôi gộp + chạy cả bộ test + đo lại bằng devsys). Nghiệm thu mọi đợt: bộ test đầy đủ 0 lỗi + chấm lại khu vực bị đụng, điểm không giảm và khoản trừ liên quan biến mất.
💻 = code miễn phí · 💵 = tốn tiền · 👤 = người dùng làm/quyết.

### Đợt 1 — Tiền & vòng đời job (💻, ưu tiên 1; 2 nhánh)
- **1A (T2, T3, T9):** `runner._submit_pending` dùng `transition(RUNNING)` + nhận lại job `queued` có `external_id`; `cancel_all_active` → `runner.cancel_job` (bọc try/except, ghi diag; ảnh Deepix: đổi chữ nút thành "bỏ khỏi hàng đợi"); `composite_video` kiểm `returncode` + độ dài, runner giữ bản gốc đến khi kiểm xong. *Test:* provider giả đặt `paused` giữa lúc `submit` → job phải `running`, tiếp tục không gọi `submit` lần 2; hủy job running có `external_id` → `provider.cancelled` có id, lỗi hủy không làm hỏng job khác; `Popen` giả writer thoát mã ≠ 0 → `CompositeError`, clip gốc còn nguyên.
- **1B (T1, T4, T5, T6, T7):** cổng tiền dùng chung `paid_call(...)` (hoặc một hàm `guard_paid`) cho mọi `provider.submit`: `SPEND_LOCK` + `check_*` + `project_budget.check` + tạm dừng + ước tính + ghi sổ; áp cho `costume`, `kling_multishot`, `scene_establish`, `end_frames`; `_daily_cap` ở 573/795 + đếm `end_frames`; giá `None` + dự án khóa → từ chối; `voice_check.redo` giữ `resends`; giá/số lượt trên nhãn nút (4 nút Claude Bước 1, nút vẽ lại Bước 2, TTS Bước 3, "Xuất bản đầy đủ"). *Test:* quét `provider.submit` ngoài cổng (đỏ nếu thêm đường mới không qua cổng); halt/cap=0/trần dự án/paused → 0 lần `submit`; quét `st.button` gọi hàm tốn tiền phải có giá/`llm_tag`.

### Đợt 2 — Không mất dữ liệu, lỗi nói rõ (💻, ưu tiên 2; 2 nhánh)
- **2A (D1–D3, D4):** `assets.merge` chuyển mọi trạng thái (hoặc từ chối + báo số ảnh bị bỏ), copy hồ sơ chuẩn, `delete()` chỉ khi nguồn rỗng; "Gỡ TẤT CẢ" có `confirm_all` + chỉ gỡ dòng `can_reload=False` + sao lưu JSON; "Xóa ảnh" qua thùng rác; `sync_knowledge` thêm doc mới rồi mới gỡ cũ, `lessons.decide` bọc try + giữ trạng thái "đề xuất" khi lỗi. *Test:* ca merge 5 ảnh/3 ảnh/pending/mất file; 149.700 ký tự + duyệt bài học không ném lỗi, doc cũ còn.
- **2B (D5–D7, P9 + diag):** `CTA/CTA_TEXT/TITLE/SUPER/CAPTION` vào `NOT_SPEAKERS` một nơi (bỏ `_ON_SCREEN_SPEAKERS`); `GROUPS` theo cờ `film_crew` + test so với `prompts.py`; `ff_site`: không `vm`, chỉ `https` + host garena, bọc khối dữ liệu + test "ignore previous instructions"; `research.run` bỏ finding không phải dict; `diag.STAGES` đủ tên khâu thật + test quét tên khâu; dịch lỗi tiếng Anh (SchemaError, Deepix, sửa nhân vật) kèm cách sửa.

### Đợt 3 — Quyền (💻; một việc 👤)
- **3A:** bọc nút "mở lại dịch vụ" bằng `allowed("settings")` + `budget.reopen(actor)`; `trash.restore` + hộp thoại Lịch sử trong `access_ui.read_only`; hộp thoại Đợt thử tự kiểm lại quyền; ghim `streamlit>=1.64` trong `requirements.txt` (+ test khẳng định widget `disabled` không nhận giá trị gửi lên); `need_edit` ở lõi cho **các hàm nhận `p`** (lớp phòng thủ thứ hai, ưu tiên thấp, làm bằng test quét ma trận vai × hàm). Hàm nhận `conn`/`provider` (voice, `raise_cap`, `set_target`, `submit_*`) cần đổi chữ ký — làm sau, gộp với việc `paid_call` ở 1B.
- 👤 **Chính sách LAN (cần bạn quyết):** `DASHBOARD_LAN=1` hiện cho mạo danh bằng e-mail. Lựa chọn: (a) mã một lần/OTP cho thành viên khi LAN bật; (b) tắt LAN, chỉ localhost; (c) giữ nguyên + giới hạn số lần thử + cảnh báo.

### Đợt 4 — Dashboard dễ dùng hơn (💻; mục 4C cần 👤)
- **4A (U1, U3, U4, U6, U7, U5 nhẹ):** ⌂ không dựng video mọi lần rerun (chọn 1 dự án xong rồi dựng 1 video, nút tải đọc lười) + ca "20 dự án xong" vào phép đo hiệu năng (mục tiêu: không quá +20 % so với 0 dự án xong, ≤ 1 `st.video`); `next_line` lỗi → mức `warn` + ghi diag; hộp 📥 thêm loại "Lỗi gen" (job `failed` mới nhất mỗi cảnh); bảng `RENAMED` vào `tools/ui_v2_acceptance.py` (chỉ báo lỗi khi mất khóa **không ánh xạ**) và `devsys/metrics.py::ui_from_text` → `keys_lost = 0`; 4 lớp CSS 12 → 12,5 px; gộp `short_text`/`show_estimate`; sửa dòng TODO 24.
- **4B (hộp thư thật, ý từ so sánh nhóm B):** Duyệt/Từ chối/Hoãn ngay trong hộp; xếp theo mức chặn dây chuyền; từ chối hai kiểu (loại bỏ / gửi lại kèm ghi chú); chụp trạng thái tại cổng duyệt; bảng điểm QC theo lần gen; gắn nguồn 🧮/🤖/👤 cho mỗi điểm QC; biểu đồ tiêu hao so với trần ba tầng; cây vết từng shot. *Làm sau 4A; mỗi ý một nhánh nhỏ.*
- **4C (👤 → 💻):** bạn dùng thử `ui_v2` trên dự án thật và duyệt → đặt `ui_v2` mặc định, **gỡ nhánh giao diện cũ** (61 lời gọi `v2_on()` / 20 file / ~122 dòng), tách `header.py`/`home.py`/`team_screen.py`; ⌂ phân trang + nhóm theo trạng thái (Cần bạn → Đang chạy → Lỗi → Xong), thẻ Lỗi khác kiểu nút.

### Đợt 5 — Thang chấm v2.1 (💻; xem mục 6)
### Đợt 6 — Năng lực mới từ so sánh ngoài (kiểm trước)
- 💻 kiểm ClipAI: sửa clip cục bộ (Seedance 2.5 Intelligent Edit), phông xanh/mô hình trắng 3D qua API → cập nhật ước tính theo giá 2.5 (💵 thử 1 clip có trần);
- 💻 QC danh tính bằng DINO (không InsightFace — giấy phép phi thương mại); thử MuseTalk/LatentSync 1 clip ngắn trên máy 8 GB (có thể không chạy được); xuất timeline/ProRes; nối hành động qua điểm cắt.

### Đợt 7 — Cần tiền hoặc quyết định của bạn (👤/💵)
- Chạy thật các cờ BẬT mà `verified=False` (Bước 1: `film_crew`, `story_check`, `camera_setups`; Bước 2: 7 cờ; Bước 3: `audio_first`, `j_cut`, `voice_check_redo`; Bước 4: `seedance_subjects`, `continuous_takes`, `camera_setups`, `seedance_ref_groups`); Director thật với `film_crew`; duyệt bản thô P2→P3 trên #8 (~0,17 USD); `asset_vision` trên 5–10 nhân vật (vài cent); `qc_team` trên bộ độc lập 134 khung; **nghiệm thu ước tính** sau một dự án có trần (giá Kling std thật ≈ 0,06 so với 0,08 trong bảng; ước tính từng khâu lệch ≤ 20 %).
- Số click "Dự án mới → video đầu" 14 = 14: muốn giảm phải đổi UX (gộp bước ngân sách với Director, bỏ bước xác nhận).

## 5. Việc cần bạn quyết ngay
1. Duyệt **Đợt 1 + Đợt 2** (4 nhánh song song: 1A, 1B, 2A, 2B) làm trước? Mỗi nhánh có test hồi quy; tôi gộp, chạy cả bộ test, rồi chấm lại các khu vực bị đụng bằng devsys.
2. **Chính sách LAN** (Đợt 3): OTP/mã cho thành viên, tắt LAN, hay giữ nguyên + giới hạn thử?
3. Khi nào bạn dùng thử `ui_v2` trên dự án thật (mở khóa 4C: bật mặc định + gỡ giao diện cũ)?
4. Có cho kiểm ClipAI về sửa clip cục bộ / phông xanh (Đợt 6; thử 1 clip trả tiền có trần)?

## 6. Tối ưu cách chấm của AI Dev — việc còn lại cho thang v2.1

**Đã có ở v2:** mức chặn/lớn/nhỏ do code gán điểm; số đo tự động (`devsys/metrics.py`); checklist K1–K10; độ ổn định (lệch > 5 phải giải thích); trần khu vực khi còn lỗi chặn.
**Lần chấm này chứng minh thang bắt được lỗi thật** (tái hiện trả tiền 2 lần, mất ảnh khi gộp, mất bài học) và việc **kiểm chứng độc lập trước khi chốt mức** đã hạ/bác bỏ nhiều khoản (xem mục 2) — nên làm kiểm chứng thành bước chính thức của quy trình chấm.

| # | Vấn đề | Đề xuất v2.1 |
|---|---|---|
| S1 | **Bộ dò cờ lệch**: `collect.flags_state` bỏ `data/feature_settings.json` + preset (đã chạy thật: `ui_v2` bật mà devsys báo tắt); bỏ sót hằng `FLAG`/`CLAUDE_FLAG` | gọi thẳng logic `core.features.on`; nhận hằng `*_FLAG`; test hồi quy |
| S2 | **Cổng bằng chứng nông**: `test:tên_không_tồn_tại` vẫn là bằng chứng cứng; `giai_thich_chenh` chỉ cần có chữ | kiểm tên test bằng `ast`; kiểm evidence của giải thích |
| S3 | **`import_score` không đối chiếu dữ liệu export** (file chấm trên dữ liệu cũ vẫn "khớp") | so `input_hash`; luôn lấy `commit/date` từ hệ thống |
| S4 | **Cap `test` phụ thuộc môi trường**: chấm trong worktree thiếu `data/` → bị cap oan (step1 77,1 so với 80,1) | cảnh báo / in "nguồn" của `code_caps` khi nhập; từ chối nhập ngoài repo gốc |
| S5 | **Quy tắc ổn định so giữa hai người chấm khác nhau** làm lần nhập bị từ chối | chỉ so cùng người chấm, hoặc chấp nhận `giai_thich_chenh` giữa người chấm |
| S6 | **Khu vực chỉ có tài liệu bị trần ~88** (test luôn 2,4/12) | `test` = "không áp dụng", chia lại trọng số |
| S7 | **`chan`/`lon` không có trục "dễ gặp"** (lỗi hiếm trừ ngang lỗi thường gặp; kiểm chứng ghi độ hiếm nhưng thang không dùng) | thêm "thường/hiếm" làm hệ số; ngưỡng tiền cụ thể |
| S8 | **Một lỗi chạm nhiều tiêu chí, không có tiêu chí chính** (thiếu `need_edit`: tin_cay hay tuân_thủ?; "tiền ngoài sổ" bị chia sang 2 tiêu chí) | bảng "loại K → tiêu chí mặc định" |
| S9 | **Checklist thiếu loại lỗi**: vòng đời job/đồng thời/hủy; "xóa trước rồi mới có bản mới"; mất dữ liệu khi thay thế | thêm K11 vòng đời job, K12 phá hủy-trước-khi-có-bản-mới; bỏ `khac` |
| S10 | **Trần khoản trừ tự động che thông tin** (13 chỗ nuốt lỗi = 18 chỗ = −4; một file lớn bị trừ 3 lần ở `bao_tri`); `nuot_loi` đếm cả `except` chú thích vô hại | trọng số theo mức nguy hiểm; bỏ `except` có chú thích lý do; mỗi file chỉ trừ một lần |
| S11 | **`todo_mo` đếm nhầm**: dòng `[x]` đã xong có chữ "chưa chạy thật", quy ước `[ ]`, dòng "chờ người dùng quyết" | phân loại: việc code / việc người dùng / quy ước. *(Đã làm 03/10: dòng nhật ký "Đã chạy…/Chấm lại…" thành việc chung, không gán khu vực.)* |
| S12 | **Bộ đo giao diện không áp cho `step1/2/3`** (khu vực có màn Streamlit); `man_nhieu_nut` đo theo file; phép đo "khóa mất" báo sai | gán số đo giao diện cho mọi khu vực có màn; luật trừ `keys_lost` sau khi có bảng `RENAMED` |
| S13 | **Dữ liệu xuất bị cắt** (`runner.py` 1715 dòng, `step4.py`, 66 tài liệu) trong khi tiêu chí cần đọc chính các file đó; heredoc JSON dài hay vỡ | tăng ngân sách trích cho khu vực lớn; hướng dẫn ghi file điểm bằng công cụ Write |
| S14 | **`overall()` trộn thang v1 và v2** khi chưa chấm lại hết | chỉ trung bình cùng thang, hiển thị "chưa chấm v2" |
| S15 | **`bang_chung` có thể gian lận**: một dòng `TODO.md:1` là đủ 16 điểm; cờ chưa verified bị trừ ở 2 tiêu chí | đòi trích dẫn kèm số đo, code kiểm chuỗi số; một cờ chỉ trừ một lần |
| S16 | Đường chấm **Claude API chưa chạy thật** (không file điểm `claude-api` nào) | chạy 1 khu vực nhỏ (`--areas diag --yes`, 💵 vài cent) để có số chi thật so với ước tính |
| S17 | **Dấu vân tay nhạy với số test**: thêm test vào file test được ánh xạ vào nhiều khu vực làm các khu vực đó hiện "⚠ đã đổi" dù code không đổi | tách "đổi code/TODO" (cần chấm lại) khỏi "đổi số test" (chỉ cần thu lại test) |
| S18 | **Dòng nhật ký TODO** từng làm 4 khu vực hiện "đổi" giả (đã sửa 03/10: `DONE_LOG` → việc chung `_chung`, test `TodoLogLinesTests`) và trang "Chấm điểm AI" từng văng `TypeError` vì biến `stale` đè hàm (đã sửa, test `AppNameShadowTests`) | giữ test; mở rộng test chống đè tên cho `AugAssign/for/with/import` |

Cách chấm nên giữ: người chấm chỉ ghi khoản trừ + bằng chứng, code tính điểm; **2 người chấm độc lập cho vài khu vực mỗi đợt** (lần này `dashboard_ui` chênh 0,2); **kiểm chứng độc lập các khoản lớn trước khi chốt mức** (lần này đã hạ/bác bỏ ≥ 6 khoản).
