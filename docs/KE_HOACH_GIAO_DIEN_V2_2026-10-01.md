# Kế hoạch: dựng lớp thiết kế "AI product" cho Dashboard (giữ Streamlit, luồng tuyến tính)

## Bối cảnh
Người dùng không muốn tiếp tục "sửa từng ô": giao diện hiện là lưới ô phẳng, nhiều điều khiển (≈ 250, 10 hộp thoại, 7 popover), mỗi nơi một kiểu khung/màu/cỡ chữ. Muốn nhìn **công nghệ, hiện đại, đúng chuẩn AI** (gradient, nền tối/kính mờ, glow) và so với canvas Deepix xem đã tối ưu hơn chưa.
Quyết định của người dùng (hỏi 01/10): **giữ Streamlit + dựng lớp thiết kế riêng**; **không làm canvas node**, giữ wizard tuyến tính (Kịch bản → Storyboard → Video → Bản giao) nhưng đẹp hơn.

## So với Deepix Weave Canvas (kết luận để trả lời người dùng)
Bằng chứng: chỉ từ repo (skill `deepix-1.4.1/references/canvas.md`, slide Storyboard, memory) — Weave Canvas là công cụ nội bộ, không có tài liệu công khai; ô chưa rõ ghi [?].
- **Canvas hơn:** đồ thị node trực quan, phân nhánh/nhân bản, thử song song; preview-rồi-apply + undo theo batch; slide Storyboard của họ có giao diện tối/tím/kính mờ, lưới 6 khung với Remix/Regenerate/Copy-to-ClipAI ngay trên thẻ.
- **Ta hơn (chức năng):** khóa ngân sách cứng theo khâu, QC nhiều tầng, cổng duyệt có người ký, hộp "Việc cần bạn" theo người, Kho Free Fire (3D, hồ sơ kỹ năng), autopilot có cổng.
- **Ta kém:** độ gọn, độ bóng, cảm giác "AI" — đây chính là việc kế hoạch này giải quyết. Chưa thể nói "tối ưu hơn" về thao tác cho tới khi gọn lại và đo số click.
- Cách học từ canvas mà không cần canvas: lưới khung với hành động ngay trên thẻ, lịch sử phiên bản mỗi khung (v1 v2 v3 ngang), preview giá trước khi chạy, trạng thái tiến độ trên từng thẻ, ô lệnh chung.

## Ngôn ngữ thiết kế (token + công thức, một nơi duy nhất)
- Nền: tối mặc định ("aurora": 2–3 `radial-gradient` tím/xanh/hồng mờ trên #0F1115), sáng là bản đảo; lớp nền surface/raised/glass.
- Thẻ kính: nền rgba 4–6 %, `backdrop-filter: blur`, viền 1 px gradient, bo 16 px; nút chính nền gradient tím→xanh + glow; nút phụ viền; nút nguy hiểm đỏ tách riêng.
- Chữ: Inter/hệ thống; tiêu đề lớn gradient (kèm màu dự phòng); thang chữ 12/14/16/20/28; không chữ < 12 px.
- Trạng thái: pill nền mờ + chấm (xanh = ok, cam = đang chạy/chờ, đỏ = lỗi, xanh dương = thông tin); thanh tiến độ gradient đổi màu theo % (đã có `ui.bar_color`).
- Chuyển động: shimmer cho job đang chạy, nhấc thẻ 2 px khi hover, tôn trọng `prefers-reduced-motion`.
- Mọi cặp chữ/nền kiểm ≥ 4.5:1, viền/icon ≥ 3:1 (bảng token đã tính ở `docs/THIET_KE_GIAO_DIEN_2026-10-01.md`); thêm lớp phủ tối sau chữ trên gradient.

## Cách triển khai (tái dùng cái đã có)
Tái dùng: `dashboard/ui.py` (CSS hiện tại, `bar_color`, `progress_bar`, `pbar`, `badge`), `dashboard/common.py` (`go_screen`, `confirm_all`, `show_image/show_video`, `step_header`), `tools/ui_contrast_audit.js`, token ở `docs/THIET_KE_GIAO_DIEN_2026-10-01.md`, mockup `mockup/dashboard_v2_4man.html`, `dashboard/home.py`, `dashboard/header.py`.

### Giai đoạn 0 — Nền móng (0,5 ngày)
- Chụp ảnh mốc các màn (sáng/tối) bằng trình duyệt demo; ghim phiên bản Streamlit trong `requirements.txt`; liệt kê selector CSS đang dùng vào một danh sách (để kiểm khi nâng phiên bản).
- Chỉ dùng điểm bám ổn định: `st.container(key="…")` → `.st-key-…`, `[data-testid=…]`, `st.html`; cấm selector emotion tự sinh.

### Giai đoạn 1 — Lớp thiết kế (3–4 ngày)
- Tạo `dashboard/design/` : `tokens.py` (token sáng/tối → khối CSS biến), `theme.css` (gradient, kính, viền, nút, pill, tab, shimmer, reduced-motion), `components.py` (hàm HTML thuần: `hero()`, `card()`, `stat()`, `pill()`, `frame_card()`, `empty_state()`, `stepper()`), nạp một lần ở `ui.inject_css()`; dọn CSS rải rác trong `ui.py`.
- `.streamlit/config.toml`: `[theme.light]`/`[theme.dark]` (màu chủ đạo, font, `baseRadius`, `borderColor`, `showWidgetBorder`).
- Test: token ≥ ngưỡng tương phản (test Python thuần), hàm component trả HTML đúng/đã escape.

### Giai đoạn 2 — Khung ứng dụng (3–4 ngày)
- `dashboard/header.py` + `dashboard/app.py`: thanh trên kiểu glass (logo gradient, chọn dự án, 📥 💵 ⚙ có nhãn chữ), thanh bước dạng stepper trực quan (số/✓/%), dải "hero" của dự án (tên, trạng thái, tiến độ vòng/thanh gradient, việc tiếp theo), nền aurora; gom nút phụ vào menu "Thêm" có nhãn chữ.
- Giữ nguyên `key` của widget để 1700 test không vỡ.

### Giai đoạn 3 — Bốn màn chính (1,5–2 tuần)
- **Tất cả dự án** (`home.py`): lưới thẻ dự án (tiến độ gradient, pill trạng thái, nút "Mở" glow, 🔒 người đang mở) thay bảng.
- **Kịch bản** (`step1*.py`): ô nhập lớn kiểu hero + thẻ "Lập kế hoạch (≈ X USD)" + khay tham chiếu; gập "Tinh chỉnh"; bỏ lựa chọn autopilot/từng bước trùng lặp bằng 🎚 Mức tự động.
- **Storyboard** (`step2.py`, `step3.py`): lưới khung thẻ kính (nhãn Cần duyệt/Đã duyệt/Từ chối trên thẻ, QC chip, dải phiên bản v1…vN, hành động hiện sẵn, thanh hành động dính ở cuối bằng `position: sticky`); lý do loại nhập ngay trên thẻ.
- **Video** (`step4.py`) và **Bản giao** (`step5.py`): thẻ clip có QC chip + gợi ý sửa; Bản giao = một thẻ "Xuất bản đầy đủ" + chip phụ đề/card/khổ phụ, phần dựng/nhạc/SFX vào "Tinh chỉnh".
- Giảm ma sát đã khảo sát: `confirm_all` hai bước chỉ giữ cho việc tốn tiền/không hoàn tác; nút "Xem" lặp ở thẻ ảnh gộp một; "Sửa motion prompt" mở thẳng tab Motion (đã có `go_screen(tab=1)`).

### Giai đoạn 4 — Hộp thoại, admin, hoàn thiện (1 tuần)
- Hộp thoại/popover dùng chung kiểu kính; ⚙ rút còn 3 nhóm (đã có); màn Theo dõi/Nhóm dùng cùng thẻ + pill; bảng dữ liệu quan trọng thay bằng HTML bảng (canvas của `st.dataframe` không đổi nền tối được).
- Skeleton/shimmer cho job đang chạy; trạng thái trống có nút hành động; thời gian đã chờ + nút thử lại cho job treo.

### Giai đoạn 5 (tùy chọn, chỉ khi cần) — một component JS riêng cho lưới duyệt
Streamlit Components v2 cho lưới duyệt có phím tắt Y/N/E (Streamlit không có phím tắt sẵn). Chỉ làm nếu giai đoạn 3 vẫn thiếu.

## File chính sẽ sửa/tạo
`dashboard/design/{tokens.py,theme.css,components.py}` (mới), `dashboard/ui.py`, `dashboard/app.py`, `dashboard/header.py`, `dashboard/home.py`, `dashboard/steps/step1*.py`, `step2.py`, `step3.py`, `step4.py`, `step5.py`, `dashboard/team_screen.py`, `.streamlit/config.toml`, `requirements.txt`, `docs/THIET_KE_GIAO_DIEN_2026-10-01.md`, `tests/` (token, component, và giữ AppTest).

## Rủi ro và cách giảm
- CSS gắn DOM nội bộ Streamlit vỡ khi nâng phiên bản → ghim phiên bản, chỉ dùng `st-key-*`/`data-testid`, kiểm bằng ảnh chụp + công cụ quét sau mỗi lần nâng.
- `backdrop-filter` nặng trên máy yếu → giới hạn số thẻ lồng nhau, có biến tắt hiệu ứng.
- Chữ trên gradient kém tương phản → lớp phủ tối + test tương phản.
- Quá nhiều thay đổi cùng lúc → làm theo giai đoạn, mỗi giai đoạn commit + khởi động lại + người dùng xem ảnh.
- Mất tính năng khi gom nút → danh sách đối chiếu "mọi điều khiển cũ vẫn truy cập được" trước khi đóng mỗi màn.

## Kiểm chứng
1. Mỗi giai đoạn: chạy demo (`preview_start dashboard-demo`), chụp ảnh sáng + tối từng màn, so với mockup đã duyệt.
2. `tools/ui_contrast_audit.js` trên từng màn và từng popover/hộp thoại: 0 chữ < 4.5:1, 0 chữ < 12 px (trừ biểu tượng).
3. `py -m pytest -q tests` đầy đủ (hiện 1700 qua) sau mỗi giai đoạn.
4. Danh sách đối chiếu tính năng cũ ↔ mới cho từng màn (đã có bảng widget theo màn từ khảo sát).
5. Người dùng xem ảnh + dùng thử trên Dashboard thật (khởi động lại cổng 8501) và duyệt trước khi sang giai đoạn kế.
6. Đo số click từ "Dự án mới" đến video đầu tiên trước/sau để trả lời câu hỏi "tối ưu hơn Canvas chưa".

## Ước lượng
Khoảng 3–4 tuần công, nếu làm liên tục từng giai đoạn có duyệt. Giai đoạn 0–2 (≈ 1 tuần) đủ cho người dùng thấy hướng đi và quyết có tiếp hay không.

## Bổ sung (người dùng yêu cầu): ô "↺ Đặt lại thanh tiền" — chỉ Owner
Mục đích: Owner đặt lại mốc tính của các thanh theo dõi tiền (sau khi nạp tiền, bắt đầu đợt thử mới, sang tháng) mà **không xóa sổ chi** (`usage_events` giữ nguyên để báo cáo/kiểm toán).
- **Vị trí:** trong thẻ 💵 Tiền (`dashboard/header.py: money_card`) và hộp "Đợt thử & Claude"; chỉ hiện và chỉ chạy khi `me()["role"] == "owner"` (kiểm lại ở hàm lõi, không chỉ ở giao diện).
- **Đặt lại được những thanh nào (chọn bằng tick):**
  1. Đợt thử → `budget.restart(conn, usd)` (đã có: `since = bây giờ`, giữ trần).
  2. Claude API → `budget.restart_llm(conn, usd)` (đã có).
  3. Tiền theo người / hạn mức tháng → mốc mới `user_reset:<email>` trong `app_settings` (thêm vào `core/team.py: spend_by_user`/`month_spend`, tính từ mốc).
  4. Ngân sách một dự án đã khóa → mốc tính theo khâu trong dữ liệu `project_budget` (thêm `baseline` trừ khỏi `spent_by_stage`). **Cẩn thận:** việc này nới khóa cứng, nên bắt buộc có lý do, ghi nhật ký, và hiện rõ "tính từ … bởi Owner" ngay trên thanh.
- **An toàn:** hai bước xác nhận (`confirm_all`), lý do bắt buộc, ghi `auth.audit(conn, owner_email, "reset_money", chi tiết)`, hiển thị dòng "Đặt lại lần cuối: lúc … bởi …" dưới mỗi thanh; không động tới `usage_events`, `llm_calls`, báo cáo hiệu quả.
- **Test:** thành viên không thấy ô và hàm lõi từ chối; đặt lại không xóa dòng sổ; thanh về 0 theo mốc mới còn tổng sổ chi vẫn đủ; nhật ký có bản ghi; khóa dự án vẫn chặn khi chi vượt trần tính từ mốc mới.
- **Giai đoạn:** làm cùng Giai đoạn 2 (khung ứng dụng, thẻ 💵), mục 3–4 làm sau khi Owner xác nhận cách nới khóa dự án.

## Bổ sung (người dùng yêu cầu): chạy song song nhiều nhánh để đẩy nhanh
Cách làm: mỗi nhánh một **agent riêng trong git worktree riêng** (`isolation: "worktree"`, nhánh `ui/<tên>`), làm đồng thời; tôi (phiên chính) là người tích hợp: rebase từng nhánh lên `main`, chạy bộ test đầy đủ, rồi mới đẩy. Mỗi nhánh **sở hữu danh sách file riêng, không sửa file nhánh khác** để không xung đột.

**Bước 0 (làm trước, ~1 ngày, một mình):** Nhánh A "Lõi thiết kế" chốt **hợp đồng thành phần**: chữ ký các hàm trong `dashboard/design/components.py` (`hero()`, `card()`, `stat()`, `pill()`, `frame_card()`, `clip_card()`, `empty_state()`, `stepper()`, `action_bar()`), tên token/CSS, quy ước `st.container(key="…")`. Có bản stub chạy được ngay để các nhánh khác viết theo.

**Sau đó 6 nhánh chạy cùng lúc:**
| Nhánh | Sở hữu file | Việc |
|---|---|---|
| A. Lõi thiết kế | `dashboard/design/*`, `dashboard/ui.py`, `.streamlit/config.toml`, `requirements.txt` | token sáng/tối, theme.css (gradient, kính, viền, nút, pill, tab, shimmer), components, test tương phản + component |
| B. Khung ứng dụng | `dashboard/app.py`, `dashboard/header.py` | thanh trên glass, stepper, hero dự án, nền aurora, 📥 💵 ⚙ có nhãn chữ, menu "Thêm", **ô Đặt lại thanh tiền (UI)** |
| C. Tiền (lõi, không UI) | `core/budget.py`, `core/team.py`, `core/project_budget.py`, `core/auth.py` (chỉ thêm audit nếu cần), `tests/test_money_reset.py` | `reset_money(actor, bars, reason)` chỉ Owner, mốc đặt lại không xóa sổ, nhật ký, test an toàn (chạy độc lập với giao diện, B gọi hàm này) |
| D. Tất cả dự án + Nhóm + Theo dõi | `dashboard/home.py`, `dashboard/team_screen.py`, `dashboard/admin.py` | lưới thẻ dự án, bảng thành thẻ/pill, Theo dõi dùng thẻ chung |
| E. Kịch bản | `dashboard/steps/step1*.py` | hero nhập, thẻ Lập kế hoạch có giá, khay tham chiếu, gập "Tinh chỉnh", bỏ lựa chọn trùng |
| F. Storyboard | `dashboard/steps/step2.py`, `step3.py` | lưới khung thẻ kính, nhãn duyệt cố định, dải phiên bản, thanh hành động dính, lý do loại ngay trên thẻ |
| G. Video + Bản giao | `dashboard/steps/step4.py`, `step5.py` | thẻ clip + QC chip + gợi ý sửa, thẻ "Xuất bản đầy đủ", gom nhạc/SFX/phụ đề vào "Tinh chỉnh" |
(Mỗi nhánh tự thêm file test riêng `tests/test_ui_<tên>.py`; chỉ sửa test cũ thuộc màn của mình.)

**Thứ tự tích hợp (tránh vỡ):** A → C (không phụ thuộc UI) → B → D, E, F, G (bất kỳ thứ tự, mỗi cái rebase lên `main` mới nhất, chạy `pytest tests -q` đầy đủ trước khi đẩy). Cổng chất lượng mỗi lần tích hợp: toàn bộ test qua, `tools/ui_contrast_audit.js` 0 lỗi trên màn nhánh đó (sáng + tối), danh sách đối chiếu "điều khiển cũ vẫn truy cập được" của màn đó.
**Điểm người dùng xem:** sau khi A + B tích hợp (khung + thanh trên + nền) gửi ảnh chụp; sau khi D–G xong gửi ảnh cả 4 màn rồi khởi động lại Dashboard thật.
**Giới hạn đồng thời:** tối đa 6 agent cùng lúc; mỗi agent chỉ chạy test mục tiêu (không chạy bộ đầy đủ ~7 phút) — chỉ tôi chạy bộ đầy đủ khi tích hợp. Máy một người dùng: tránh hai agent cùng khởi động server trên cổng 8511 (mỗi nhánh dùng cổng riêng 8521–8526 nếu cần xem giao diện).
**Rút ngắn dự kiến:** từ ≈ 3–4 tuần xuống ≈ 1,5–2 tuần (A ~1 ngày, rồi B–G song song ~1 tuần, tích hợp + sửa ~2–3 ngày).
**Rủi ro riêng của song song:** xung đột ở file dùng chung (`ui.py`, `common.py`, test) → quy tắc "chỉ A sửa CSS/thành phần chung; cần gì thì nhờ A qua hợp đồng"; `common.py` chỉ thêm hàm mới ở cuối, không đổi hàm cũ.

## Bổ sung (người dùng yêu cầu): nghiên cứu kỹ để BẢN THẬT đẹp như demo, không chỉ demo đẹp
**Vì sao demo hay đẹp hơn bản thật (nguyên nhân đã gặp ở chính dự án này):**
1. Mockup là HTML tĩnh tự vẽ; bản thật là Streamlit — widget gốc (ô chọn, nút, ô nhập, tab, bảng) có DOM/kiểu riêng, CSS chỉ phủ lên được một phần (đã thấy: khung bị bỏ sót vì đổi `data-testid`, tab chữ tối trên nền tối, bảng `st.dataframe` luôn sáng).
2. Demo dùng dữ liệu "vừa vặn" (4 thẻ, tên ngắn); thật có 30 khung, tên dài, lỗi, trạng thái rỗng, 50 dự án.
3. Demo ở một cỡ cửa sổ; thật ở nhiều độ rộng/độ phóng, Chrome/Edge, hiển thị font Windows, máy yếu (backdrop-filter nặng).
4. Font: mockup dùng font hệ thống; nếu thiết kế dựa vào Inter mà máy không có thì ra font khác.
5. HTML trong `st.html` không chứa được widget Streamlit — thẻ có nút phải là `st.container(key=…)` + CSS, khác hẳn cách mockup vẽ.

**Cổng chống "demo đẹp, thật xấu" (bắt buộc, đặt TRƯỚC khi mở song song):**
- **G1 — Lát cắt dọc thật (spike, 2–3 ngày, một mình nhánh A):** dựng bằng chính Streamlit, trên cổng thật, MỘT lát đại diện đủ mọi loại thành phần: thanh trên + stepper + hero + lưới 8–12 khung (thẻ có nút, pill, thanh tiến độ, dải phiên bản) + một hộp thoại + một bảng + trạng thái rỗng/lỗi/đang chạy. Người dùng duyệt ảnh chụp của lát này trên **Dashboard thật** (cổng 8501, độ rộng màn hình của người dùng, sáng + tối). **Không duyệt thì không mở 6 nhánh.** Nếu có thành phần Streamlit không làm đẹp được, ghi vào "danh sách không làm được" và đổi thiết kế (vd. thay `st.dataframe` bằng bảng HTML), không giấu.
- **G2 — Bộ ảnh chụp trên dữ liệu thật:** `tools/ui_snapshot.py` chạy app thật với CSDL mẫu gần thật (bản sao ẩn danh của #8 + các trạng thái: trống, đang chạy, lỗi, hoàn tất, 50 dự án, tên dài, 30 khung), chụp ở 4 độ rộng (1280/1440/1630/1920) × sáng/tối × độ phóng 100 % và 80 %, lưu `docs/ui_snapshots/<ngày>/`. Mỗi nhánh nộp ảnh của màn mình; so với ảnh lần trước để bắt hồi quy hình.
- **G3 — Công tắc `UI_V2` (cờ) chạy song song hai giao diện:** bật/tắt ngay trong ⚙ → Hệ thống, mặc định TẮT cho tới khi người dùng duyệt; người dùng so cũ/mới trên dữ liệu thật và quay lại bản cũ tức thì nếu có gì sai. Chỉ bỏ giao diện cũ khi người dùng xác nhận.
- **G4 — Kiểm trên dự án thật của người dùng:** trước mỗi lần đẩy, mở Dashboard thật (không phải bản demo) với dự án đã cất khôi phục (#8) và dự án mới, xem đủ 4 màn + hộp thoại + ⚙/💵/📥.
- **G5 — Ngân sách hiệu năng:** đo thời gian rerun màn Storyboard (30 khung) và Home (50 dự án) trước/sau; không chậm hơn bản cũ quá 20 %; `backdrop-filter` chỉ ở thẻ cấp cao nhất, có biến `UI_FX=off` cho máy yếu.
- **G6 — Font đi kèm:** bỏ file Inter (woff2) vào `assets/fonts` và phục vụ qua static serving của Streamlit để font giống nhau trên mọi máy, không phụ thuộc máy có cài hay không.
- **G7 — Công bố giới hạn ngay từ đầu:** mục tiêu thực tế "≈ 75–80 % cảm giác AI-product" của Streamlit; những thứ **không** hứa: canvas node, animation trên widget gốc, phím tắt thật (cần component riêng), gradient trên bảng canvas. Người dùng đồng ý giới hạn này trước khi làm.
- **G8 — Tiêu chí nghiệm thu bằng số:** 0 chữ < 4.5:1 và 0 chữ < 12 px (`tools/ui_contrast_audit.js`) ở mọi màn + hộp thoại + popover, cả sáng và tối; số click từ "Dự án mới" tới video đầu tiên giảm so với bản cũ (đo bằng AppTest kịch bản mẫu); 0 điều khiển cũ bị mất (danh sách đối chiếu).

**Điều chỉnh lộ trình:** thêm **Giai đoạn 0.5 = G1 (lát cắt dọc thật)** giữa "Lõi thiết kế" và "mở 6 nhánh song song"; G2/G3/G6 do nhánh A làm trong Giai đoạn 0.5; tổng thêm ≈ 3 ngày. Tổng ước lượng ≈ 2–2,5 tuần.
