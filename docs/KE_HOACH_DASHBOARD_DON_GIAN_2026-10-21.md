# Kế hoạch M8.1 — Chế độ ĐƠN GIẢN cho Dashboard (người ít kiến thức video AI)

- Cấp 1: tài liệu, **không code**.
- Người viết: cloud-C, 21/10. Nhánh `cloud/v31-m81`, đọc code `main` @3b58812b.
- Phiên chính trình Executive Producer (EP).
- Yêu cầu người dùng 21/10: Dashboard dành cả cho người ÍT kiến thức video AI → tối giản, tối ưu nút + thao tác.
- Phụ lục: [`KIEM_KE_NUT_DASHBOARD_2026-10-21.md`](KIEM_KE_NUT_DASHBOARD_2026-10-21.md).
  - Bảng ĐỦ 853 điều khiển (file:dòng, nhãn, việc làm, tiền, giá / xác nhận, ai dùng, điều kiện hiện).
  - Luồng hiện nay theo code, thuật ngữ, chỗ hiện mã lỗi.
  - Cột "ai dùng" là ước đoán theo vị trí trên màn, chưa phải số đo.

---

## 1. Hiện trạng (số đo từ code)

| Chỉ số | Hiện nay | Ghi chú |
|---|---|---|
| Điều khiển trên 5 màn sản xuất ①–⑤ | **529** (cả Dashboard: 853 = 439 nút + 414 ô nhập / chọn) | ① Kịch bản một mình 241 |
| Nút TỐN TIỀN | ≈ 89 (78 trên 5 màn sản xuất) | |
| Tốn tiền mà KHÔNG giá, KHÔNG hỏi lại | **6 chỗ đang hiện** | Enter trong khung chat gửi Claude; "🎬 Dựng storyboard"; "🔍 Claude rà storyboard"; "↻ Rà lại" (Tổ rà soát); "↻ Thử kiểm tra lại" ảnh / clip |
| Chi lớn chỉ có giá, không hỏi lại | 4 nút | "🤖 Lập kế hoạch", "✔ Duyệt storyboard → gửi video" (nhả gen TOÀN BỘ video), "▶ Tiếp tục · phần còn lại", "📦 Xuất bản" |
| Ý tưởng → video đầu tiên, đi tay | **≈ 33 thao tác, ≈ 19 quyết định** | 6 lần bấm trả tiền Claude trước khi có ảnh đầu tiên (4 lượt Biên kịch + Director …) |
| Ý tưởng → video, chạy tự động | ≈ 22 thao tác, ≈ 13 quyết định | Nút "🚀 Tự động" nằm trong fold "⚙ Chi tiết" |
| Thuật ngữ chuyên môn trên nhãn / caption | > 20 nhóm | BYĐ, plate, Lock, Bible, motion prompt, multi-shot, D6, QC, tên model, tên cờ thô `asset_checklist` … |
| Lỗi hiện tên exception | mọi nút qua `act()` (≈ 124) + ≈ 15 chỗ khác | "Mã lỗi kỹ thuật: ValueError"; lỗi provider in nguyên văn |

Đã có sẵn để dựa vào (không làm lại):
- Công tắc **🧠 Chế độ chuyên gia** (`dashboard/common.expert()`, 25 chỗ dùng; tắt = mỗi bước chỉ hiện việc của một lần chạy thường).
- **🎚 Mức tự động** (`operating_mode`) và **chạy tự động** (autopilot + cổng).
- Nút sáng (glow) chỉ việc kế.
- Nhật ký thao tác `ui_actions` (`core/ui_log`) + sự kiện bước bấm `ui_step` (C-DEVSYS-MAPS) — dùng để ĐO.

## 2. Nguyên tắc

1. **Một màn = một câu hỏi cho người dùng.** Mỗi bước chỉ còn MỘT nút chính (to, sáng); mọi thứ khác vào "⚙ Thêm" hoặc chế độ Chuyên gia.
2. **Máy làm phần kỹ thuật, người chỉ DUYỆT ý.** Các bước người mới không có thông tin để quyết thì TỰ ĐỘNG: chia shot, viết motion, chọn model, nháp / bản cao, QC, dựng.
3. **Không tốn tiền vì bấm nhầm.**
   - Mọi nút tốn tiền: giá trên nút + một lần "Đồng ý" ghi rõ số USD.
   - Chế độ Đơn giản không có lối tốn tiền ẩn (Enter, "thử lại").
4. **Nói bằng chữ thường.** Không mã lỗi, không tên model, không tên cờ. Thuật ngữ cần giữ thì có ⓘ giải thích 1 dòng.
5. **Không mất quyền của chuyên gia.** Chế độ Chuyên gia = Dashboard như hôm nay. Chuyển qua lại bất kỳ lúc nào, nhớ theo tài khoản.

## 3. Hai chế độ

| | **Đơn giản** (mới, mặc định cho tài khoản mới / vai "người làm phim") | **Chuyên gia** (= Dashboard hiện nay, gồm cả 🧠 hiện có) |
|---|---|---|
| Ai | Người ít kiến thức video AI | EP, Đạo diễn kỹ thuật, quản trị |
| Màn | 4 bước + ⌂ | 5 bước + mọi hộp thoại |
| Tự động | Mức "Duyệt cổng chính" cố định; mọi khâu kỹ thuật tự chạy | Như hiện nay (chọn mức) |
| Tiền | Một ngân sách cho cả phim, đồng ý một lần; mỗi lần làm lại báo giá | Như hiện nay |
| Lỗi | Câu "Chuyện gì — Bạn làm gì" | + mã, chi tiết kỹ thuật |

Cách bật (đề xuất):
- Thanh trên có công tắc **"Đơn giản ⇄ Chuyên gia"**, thay chỗ toggle 🧠.
- Lưu theo người (`users` / settings).
- Quyền ⚙ / 💵 / 🧪 / Phân quyền vẫn theo vai. Chế độ Đơn giản chỉ GIẤU, không cấp hay bớt quyền.

## 4. Luồng 4 bước cho người mới

```
 ⌂  Ý tưởng ─▶ ① Duyệt kịch bản ─▶ ② Duyệt ảnh ─▶ ③ Duyệt video ─▶ ④ Tải bản giao
     (gõ 1 câu)    (đọc, sửa bằng lời)  (lưới ảnh)      (xem clip)      (1 nút)
```

| Bước | Người làm | Máy tự làm (thay các nút hiện nay) | Quyết định |
|---|---|---|---|
| ⌂ Ý tưởng | Gõ ý tưởng + Enter | Tạo dự án, khung 9:16. Các điểm then chốt còn thiếu (6 ô bắt buộc hiện nay) được Biên kịch **hỏi lại trong chat**, mỗi câu có sẵn đáp án mặc định để bấm "Được". | 1 (+ trả lời câu hỏi nếu muốn) |
| 💵 Ngân sách | Bấm **"Đồng ý ≈ X USD cho cả phim"** (một lần) | Dự toán toàn phim (`project_budget.propose` + `cost.estimate_run`): kịch bản + kế hoạch + ảnh + video nháp + bản cao + âm thanh. Kèm mức xấu nhất và ngân sách tự sửa 40 % (M6). | 1 |
| ① Kịch bản | Đọc kịch bản (chữ thường, theo cảnh) → **"✔ Được, làm tiếp"** hoặc gõ góp ý ("đoạn cuối vui hơn") | Biên kịch chạy đủ 4 lượt liền, chọn hướng tốt nhất (3 hướng ẩn trong "Xem phương án khác"). Sau khi người đồng ý: Director chia shot + Bible, tự khóa, gen ảnh luôn. | 1 |
| ② Ảnh | Lưới ảnh theo cảnh: **"✔ Duyệt hết"**, hoặc bấm 1 ảnh → "Vẽ lại" + gõ lý do bằng lời | Máy chấm điểm (QC); ảnh trượt tự vẽ lại trong trần M6 (3 lượt). Viết + duyệt motion tự động, giọng thoại tự tạo. | 1 (+ mỗi ảnh muốn sửa) |
| ③ Video | Xem clip theo cảnh: **"✔ Duyệt hết"** hoặc "Làm lại cảnh này" + lý do | Gen video nháp → QC → nâng bản cao cho clip đã duyệt (theo `video-route-2026-10-13`); nhạc / SFX theo mặc định | 1 |
| ④ Tải | **"⬇ Tải video"** | Dựng, phụ đề, xuất bản tự động khi đủ clip | 0 |

**Mục tiêu đo:**
- ≤ **8 cú bấm** và ≤ **6 quyết định** từ ý tưởng tới video đầu tiên (hiện ≈ 33 / ≈ 19);
- **0** nút tốn tiền không giá / không hỏi;
- **1** lần đồng ý chi trước khi máy chạy, rồi chỉ hỏi lại khi vượt dự toán.

Điểm phải được EP chốt (mục 11): tự duyệt motion, tự chọn hướng kịch bản, tự nâng bản cao trong chế độ Đơn giản.

## 5. Bảng quyết định theo nhóm nút: GIỮ / GỘP / ẨN / TỰ ĐỘNG

Quy ước:
- **GIỮ**: hiện ở Đơn giản, có thể đổi chữ.
- **GỘP**: nhiều nút thành một.
- **ẨN**: chỉ ở Chuyên gia.
- **TỰ ĐỘNG**: máy làm, không còn nút ở Đơn giản. Chuyên gia vẫn có nút.

Bảng gom theo NHÓM chức năng. Từng điều khiển (file:dòng) nằm ở phụ lục; khi làm M8.2 thì gắn nhãn GIỮ / GỘP / ẨN / TỰ ĐỘNG cho từng dòng phụ lục theo nhóm dưới đây.

| Màn hiện nay | Nhóm nút (ví dụ file:dòng) | Tiền | Đơn giản | Lý do / nút thay thế |
|---|---|---|---|---|
| ⌂ | Ô "Bắt đầu dự án mới…" (`chat_start.py:54`) | 0 | **GIỮ** | Cửa vào duy nhất |
| ⌂ | Danh sách dự án, ⬇ Tải FINAL (`home.py:291`) | 0 | **GIỮ** | |
| ① | "💡 Dùng làm ý tưởng" — thẻ hỏi loại câu (`step1_box.py:370`) | 0 | **TỰ ĐỘNG** | Câu đầu ở ⌂ luôn là ý tưởng |
| ① | Form 12 ô ⚙ Thiết lập + "💡 Bắt đầu" (`step1_idea.py:56-96`) | 0 | **GỘP** → câu hỏi chat có mặc định | 6 ô bắt buộc thành câu hỏi; 6 ô tùy chọn ẨN |
| ① | "▶ Lượt 1…4" Biên kịch + radio chọn hướng (`step1_idea.py:117-190`) | $ Claude | **GỘP** → "✍ Viết kịch bản" (đã nằm trong ngân sách) | 4 bấm trả tiền → 0 bấm riêng |
| ① | "✔ Dùng kịch bản này" (`:227`) + "🤖 Lập kế hoạch" (`step1_v2.py:166`) + "✔ Duyệt & khóa" (`:173`) | $ Claude | **GỘP** → "✔ Được, làm tiếp" | Một quyết định "kịch bản này được" |
| ① | Trình sửa cảnh (tên trường tiếng Anh: blocking, end_state…) (`step1.py:158-261`) | 0 | **ẨN** | Đơn giản: góp ý bằng lời → Đạo diễn sửa |
| ① | Nhân vật: ảnh mốc, Lock, giọng, "🤖 Claude viết Lock từ ảnh" (`step1_characters.py`) | $ Claude / ảnh | **TỰ ĐỘNG** (khi Kho có ảnh chuẩn); thiếu ảnh → GIỮ một thẻ "Thêm ảnh nhân vật" | Lock / Bible là việc máy |
| ① | Dán JSON tay, ▶ Phân tích, bảng kê tài nguyên, World Bible, chạy tự động chi tiết (`step1_director.py`, `step1_prep.py`, `step1_run.py`) | $ / 0 | **ẨN** | |
| ① | Khung chat gửi Claude khi Enter (`step1_box.py:418`) | $ Claude **không giá** | **GIỮ nhưng sửa**: chat hỏi đáp chỉ gửi khi bấm "Gửi (≈ 0,0x USD)" | Mặc định an toàn |
| ② | "▶ Gen ảnh" (`step2.py:241`) | $ ảnh | **TỰ ĐỘNG** (sau "✔ Được, làm tiếp"), nằm trong ngân sách đã đồng ý | |
| ② | Cổng trước gen, ô "vẫn gen ảnh" (`step2.py:229`) | — | **ẨN** + **TỰ ĐỘNG** | Đơn giản: cổng chặn → thẻ "Máy đang sửa X" hoặc "Cần bạn: …"; không có lối bỏ qua cổng |
| ② | Thẻ ảnh: ✔ Duyệt, ✖ Loại & gen lại + lý do, ↻ Vẽ lại, ‹ › bản cũ (`storyboard_cards.py`) | $ ảnh | **GIỮ** ✔ / "Vẽ lại" (lý do bằng lời, giá trên nút); **ẨN** bản cũ / phiên bản prompt | |
| ② | "✔ Duyệt tất cả" + Có (`storyboard_cards.py:445`) | 0 | **GIỮ** = nút chính bước ② | |
| ② | "✔ Duyệt storyboard → gửi video" (`storyboard_cards.py:439`) | $ video **không hỏi** | **GỘP** vào "✔ Duyệt hết" của bước ② (đã nằm trong ngân sách); vượt dự toán → hỏi | |
| ② | "↻ Render lại nền 3D", Sân khấu 3D, Tổ rà soát "Duyệt lại", "↻ Rà lại", "↻ Thử kiểm tra lại" (`step2.py:89,120`, `change_review_ui.py:40`) | $ / 0 | **ẨN** + **TỰ ĐỘNG** | Lỗi QC lặp lại → thẻ "Máy kiểm ảnh đang lỗi — đã báo kỹ thuật" |
| ② | Ngưỡng QC, tự gen lại dưới ngưỡng (`step2.py:601-630`) | ảnh hưởng $ | **ẨN** | Đơn giản dùng chính sách M6 |
| ③ Motion | "🤖 Viết motion", "✔ Duyệt tất cả prompt" (`step3.py:64,85`) | $ Claude | **TỰ ĐỘNG** (EP chốt Q-B) | Người mới không đọc được motion prompt tiếng Anh |
| ③ Giọng | "🎙 Tạo giọng", "⟳ Kiểm tra + tải về", "⏱ Đặt thời lượng theo giọng" (`step3.py:269-289`) | $ âm thanh | **TỰ ĐỘNG**; giữ "▶ Nghe thử" ở thẻ cảnh | |
| ④ | "▶ Gen video" (`step4.py:205`) | $ video | **TỰ ĐỘNG** sau bước ② | |
| ④ | Thẻ clip: ✔ Duyệt clip, ↻ Gen lại video + lý do (`step4.py:600-640`) | $ video | **GIỮ** ("Làm lại cảnh này" + lý do bằng lời, giá trên nút) | Trần M6: 2 lượt video / shot |
| ④ | "✔ Duyệt tất cả clip" (`step4.py:262`) | 0 | **GIỮ** = nút chính bước ③ | |
| ④ | Model / Chất lượng từng shot, 🔊 âm thanh model, 🔍 Claude kiểm từng clip, ⬆ Gen bản cao, xem gói, cổng ảnh → video, khung cuối (`step4.py:134-147,425,444`, `quality_ui.py:329`, `video_gate_ui`, `end_frame_ui`) | $ | **ẨN** + **TỰ ĐỘNG** (bản cao tự nâng cho clip đã duyệt — EP chốt Q-C) | |
| ⑤ | "📦 Xuất bản đầy đủ" (`step5.py:1143`) | 0 (Claude khi dịch) | **TỰ ĐỘNG** khi đủ clip đã duyệt | |
| ⑤ | "⬇ Tải" (`step5.py:1198`) | 0 | **GIỮ** = nút chính bước ④ | |
| ⑤ | Nhạc / SFX / TTS / phụ đề / bảng làm tay (117 điều khiển) | $ âm thanh | **ẨN**; Đơn giản chỉ giữ "Đổi nhạc" (3 lựa chọn có sẵn) + "Có phụ đề / Không" | |
| Thanh trên | 🎚 Mức tự động, 🧪 Thử rẻ, 🧪 Tính năng thử, preset, sổ chi, Theo dõi, Kho, Bài học (`header.py`) | ảnh hưởng $ | **ẨN** (vai quản trị vẫn mở được ở Chuyên gia) | Đơn giản giữ: tên dự án, 💵 "Đã dùng X / Y USD", ⏸ Tạm dừng, ⇄ chế độ |
| Mọi màn | Thông báo lỗi `act()` "Mã lỗi kỹ thuật" (`common.py:224`) | — | **SỬA** (mục 8) | |

Ước tính khi làm xong: Đơn giản còn ≈ **25–35 điều khiển** trên 4 bước (hiện 529); trong đó tốn tiền chỉ còn "Vẽ lại ảnh", "Làm lại cảnh", "Đồng ý ngân sách", "Gửi chat".

## 6. Bản vẽ màn (ASCII)

```
┌ ⌂ ─────────────────────────────────────────────────────────────┐
│  🎬 Làm video mới                                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Kể ý tưởng của bạn… (vd: Kelly lẻn vào kho súng ban đêm…)  │ │
│  └───────────────────────────────────────────────────────────┘ │
│  Dự án của bạn:  #31 Kho súng  ✅ xong  [⬇ Tải]   #33 …  ⏳ ②   │
└────────────────────────────────────────────────────────────────┘

┌ #33 · ① Kịch bản ──── ① ② ③ ④ ────── 💵 0,4 / 18 USD · ⏸ · ⇄ ┐
│ 💬 Biên kịch: Mình cần biết thêm 2 điều:                       │
│    • Nhân vật mặc gì? [Đồ thường ✓] [Áo giáp] [Khác…]          │
│    • Kết thúc thế nào? [Bất ngờ ✓] [Vui] [Khác…]               │
│ 📄 Kịch bản (6 cảnh · 45 giây)                                  │
│   Cảnh 1 — Đêm, Kelly trèo tường…                               │
│   …                                                             │
│  [ Góp ý cho kịch bản… ]                    [ ✔ Được, làm tiếp ]│
└────────────────────────────────────────────────────────────────┘

┌ #33 · ② Ảnh ───────── ① ② ③ ④ ────── 💵 3,1 / 18 USD ─────────┐
│ ⏳ Máy đang vẽ 12/18 ảnh · đã tự sửa 2 ảnh                      │
│ ┌─────┐┌─────┐┌─────┐┌─────┐   Cảnh 1: Kelly trèo tường         │
│ │ ✅  ││ ✅  ││ ⚠   ││ ⏳  │   ⚠ Ảnh 3: máy thấy tay hơi lạ —    │
│ └─────┘└─────┘└─────┘└─────┘      [Vẽ lại · 0,05 USD] [Vẫn dùng]│
│                                          [ ✔ Duyệt hết ảnh ]    │
└────────────────────────────────────────────────────────────────┘

┌ #33 · ③ Video ──────── ① ② ③ ④ ────── 💵 11,2 / 18 USD ───────┐
│ ▶ Cảnh 1 (5 giây)  ✅     ▶ Cảnh 2  ⏳ đang làm (≈ 3 phút)       │
│ ▶ Cảnh 3  ✅ [Làm lại cảnh này · 0,9 USD + lý do…]              │
│                                          [ ✔ Duyệt hết video ]  │
└────────────────────────────────────────────────────────────────┘

┌ #33 · ④ Tải ────────── ① ② ③ ④ ──────────────────────────────┐
│ 🎞 Video 45 giây · 1080p · có phụ đề      [ ⬇ Tải video ]       │
│ Nhạc: [Hồi hộp ✓] [Vui] [Không nhạc]   Phụ đề: [Có ✓] [Không]   │
└────────────────────────────────────────────────────────────────┘
```

Bản SVG làm ở M8.2, cùng mockup `mockup/dashboard.html` (thêm `#simple`).

## 7. Đổi thuật ngữ sang chữ thường

| Hiện nay | Chế độ Đơn giản | ⓘ giải thích 1 dòng (khi buộc phải hiện) |
|---|---|---|
| BYĐ (bảng ý đồ) | "Ý đồ cảnh" | Điều cảnh này phải cho người xem thấy / cảm thấy |
| Character Bible / Lock | "Hồ sơ nhân vật" | Mô tả cố định để nhân vật giống nhau ở mọi cảnh |
| World Bible | "Bối cảnh chung" | Quy tắc thế giới phim: thời đại, màu sắc, không khí |
| ảnh mốc | "Ảnh chuẩn nhân vật" | Ảnh mẫu máy nhìn theo để vẽ đúng mặt / đồ |
| ref / ảnh tham chiếu | "Ảnh mẫu" | Ảnh gửi kèm để máy vẽ giống |
| plate / nền 3D | "Phông nền" | Ảnh nền dựng sẵn để các cảnh cùng chỗ khớp nhau |
| motion prompt | "Mô tả chuyển động" | Câu tả nhân vật / máy quay di chuyển trong clip |
| storyboard | "Bảng ảnh các cảnh" | |
| nháp / bản cao, 480p / 1080p | "Bản xem thử" / "Bản đẹp" | Xem thử rẻ trước, duyệt rồi mới làm bản đẹp |
| multi-shot, nhóm cảnh | (ẩn) | |
| Seedance / Kling / Deepix / ClipAI | (ẩn) → "máy làm video / máy vẽ" | |
| QC, chấm điểm, ngưỡng | "Máy tự kiểm" | Máy xem ảnh / clip và báo chỗ lỗi trước khi bạn xem |
| Tổ rà soát, cổng | "Kiểm tra trước khi làm" | |
| D6 | (ẩn) | |
| Director / Biên kịch / Quay phim | "Đạo diễn AI" / "Biên kịch AI" | |
| end_state / khung cuối | "Hình kết thúc cảnh" | |
| tên cờ `asset_checklist`… | (không bao giờ hiện ở Đơn giản) | |
| credit / sổ chi / đợt | "Tiền đã dùng" | |

Cách làm (M8.3):
- Một bảng từ điển `dashboard/glossary.py`: khóa → (chữ Đơn giản, ⓘ). Nhãn trong code gọi `T("plate")`.
- Test quét: ở chế độ Đơn giản, không nhãn nào chứa từ trong danh sách cấm (BYĐ, plate, Lock, D6, tên model, tên cờ).

## 8. Mặc định an toàn

1. **Mọi nút tốn tiền** = giá trên nút + xác nhận một lần. Ngoại lệ: các bước đã nằm trong ngân sách cả phim đã đồng ý.
   - Sửa 6 chỗ đang thiếu (mục 1). Ở Đơn giản: ẩn hoặc tự động; ở Chuyên gia: thêm giá.
   - Test quét: mọi nút gọi đường tốn tiền phải có `price_tag` hoặc `confirm`.
2. **Ngân sách cả phim**: một lần "Đồng ý ≈ X USD".
   - Máy chạy trong ngân sách; chạm 80 % thì báo; vượt thì DỪNG và hỏi.
   - Áp cho việc tự động — ngân sách tự sửa M6 (40 % lượt đầu). Thao tác người bấm vẫn theo D01b: chỉ cảnh báo, kèm giá.
3. **Không có lối bỏ qua cổng ở Đơn giản.**
   - Ô "Tôi đã xem, vẫn gen ảnh" chỉ có ở Chuyên gia.
   - Đơn giản: cổng chặn → máy tự sửa trong trần, hoặc thẻ "Cần bạn" bằng chữ thường.
4. **Bấm nhầm thì lùi được.**
   - "Duyệt hết" có "↩ Hoàn tác (30 giây)" trước khi máy gửi tiền.
   - Gen đã gửi thì không hủy được (tiền đã tính) → nói rõ trước khi bấm.
5. **Chat không tự gửi Claude khi Enter** ở Đơn giản. Câu hỏi đáp: nút "Gửi · ≈ 0,0x USD".
6. **Dừng khẩn**: ⏸ luôn ở thanh trên. M1.3 `pause_before_submit` cho đúng nghĩa "không gửi thêm gì".

## 8b. Cảnh báo dễ hiểu thay mã lỗi

- `act()` (`common.py:224`): ở Đơn giản thay "Mã lỗi kỹ thuật: ValueError" bằng thẻ 3 dòng:
  - **Chuyện gì** (chữ thường);
  - **Bạn làm gì** (một nút nếu có);
  - "Đã báo kỹ thuật" (ghi `diag` / phiếu).
- Mã và exception chỉ còn trong ⓘ ở Chuyên gia.
- Nguồn câu: sổ lỗi `devsys/errors.json`.
  - Thêm trường `user_vi` (Chuyện gì) và `action_vi` (Bạn làm gì) cho các mã hay gặp: hết tiền provider, bị từ chối nội dung, nhà cung cấp quá tải, ảnh nhân vật thiếu, gửi chưa rõ kết quả, cổng chặn.
  - Lỗi chưa có câu → "Có trục trặc kỹ thuật ở bước X — máy đã dừng bước này, không tốn thêm tiền. [Báo kỹ thuật]".
- Lỗi provider nguyên văn ("Clip AI: …", lỗi kiểm duyệt) được dịch theo bảng. Ví dụ "Failure to pass the risk control system (real person)" → "Máy làm video từ chối vì ảnh giống người thật — máy sẽ thử cách khác (không tốn thêm)".
- Băng "Code đã đổi…", sha, cổng 8503 / 8504 → chỉ hiện cho quản trị ở Chuyên gia.

## 9. Chỉ số đo (trước / sau)

| Chỉ số | Cách đo | Hiện nay | Mục tiêu Đơn giản |
|---|---|---|---|
| Cú bấm tới video đầu tiên | `ui_actions` (`core/ui_log`) đếm theo dự án, từ "tạo dự án" tới clip đầu `approved` | ≈ 33 (đếm theo code) | ≤ 8 |
| Số quyết định | Số lần người chọn / duyệt / đồng ý (`ui_step` kết quả ok / skip) | ≈ 19 | ≤ 6 |
| Thời gian tới video đầu tiên | `projects.created_at` → clip đầu `approved` (job_events) | đo trên #33+ | giảm 50 % (thời gian chờ người) |
| Lần bấm tốn tiền không giá / không hỏi | Test quét code (M8.4) | 6 | 0 |
| Thuật ngữ cấm trên màn Đơn giản | Test quét nhãn (M8.3) | > 20 nhóm | 0 |
| Thông báo có tên exception ở Đơn giản | Test `act()` + quét `st.caption("Mã lỗi` | ≈ 140 chỗ | 0 |
| Tỉ lệ bỏ dở giữa chừng | Dự án không tới ④ trong 7 ngày | đo | giảm |
| Tiền vượt dự toán | sổ chi / ngân sách | đo | ≤ 10 % |

- Đo trên người mới thật: 2–3 người chưa dùng, mỗi người làm 1 video 30–45 giây.
- Ghi `ui_actions` + `ui_step` (cờ `ui_step_log` bật riêng cho buổi thử).
- So với sơ đồ "Làm phim qua Dashboard" (C-DEVSYS-MAPS).

## 10. Lộ trình (Cấp 2, sau khi EP duyệt — mỗi bước có cờ riêng, TẮT, test)

| Bước | Việc | Cờ | Phụ thuộc |
|---|---|---|---|
| M8.2 | Khung chế độ Đơn giản: công tắc ⇄, 4 bước, giấu theo bảng mục 5 (chỉ GIẤU, chưa tự động mới); mockup + SVG | `simple_mode` | — |
| M8.3 | Từ điển thuật ngữ + test nhãn cấm | (cùng `simple_mode`) | M8.2 |
| M8.4 | An toàn tiền: giá + xác nhận cho 6 chỗ thiếu; chat không tự gửi; hoàn tác "Duyệt hết"; test quét nút tốn tiền | `safe_paid_buttons` | — (làm được ngay, có lợi cả Chuyên gia) |
| M8.5 | Thông báo lỗi chữ thường từ `errors.json` (`user_vi` / `action_vi`) + thay `act()` | `friendly_errors` | sổ lỗi D09 |
| M8.6 | Gộp + tự động: kịch bản 4 lượt một nút, "Được, làm tiếp" = Director + khóa + gen ảnh, motion / giọng tự động, bản cao tự nâng, xuất bản tự động | `simple_autoflow` | M6 (Generation Authorization chặn thật), ngân sách cả phim |
| M8.7 | Buổi đo với người mới + báo cáo chỉ số mục 9 | — | M8.2–M8.6 |

Thứ tự đề xuất:
1. M8.4 trước (an toàn tiền, nhỏ, có lợi ngay);
2. M8.2 + M8.3;
3. M8.5;
4. M8.6 sau cùng (cần M6-B và EP chốt Q-A…Q-D).

## 11. Câu hỏi cho EP

- **Q-A — Kịch bản:** ở Đơn giản, máy TỰ chọn 1 trong 3 hướng (người xem "Phương án khác" nếu muốn) — đồng ý? Hay vẫn bắt chọn hướng?
- **Q-B — Motion:** tự viết + TỰ DUYỆT motion prompt (máy kiểm + QC thay người) ở Đơn giản — đồng ý?
- **Q-C — Bản đẹp:** clip người đã duyệt được TỰ nâng bản đẹp 1080p (trong ngân sách đã đồng ý) — đồng ý? Hay hỏi riêng một lần?
- **Q-D — Ngân sách cả phim:**
  - đồng ý MỘT lần đầu dự án, rồi chỉ hỏi lại khi vượt — đồng ý?
  - Mức báo trước: 80 %?
- **Q-E — Mặc định:** tài khoản mới vào chế độ Đơn giản; tài khoản hiện có giữ Chuyên gia — đồng ý?
- **Q-F — Thứ tự:** làm M8.4 (an toàn tiền) ngay trước các bước khác — đồng ý?
