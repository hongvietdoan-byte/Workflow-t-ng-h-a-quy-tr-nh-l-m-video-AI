# Kế hoạch M8.1 — Chế độ ĐƠN GIẢN cho Dashboard (người ít kiến thức video AI)

> **Đánh số (EP 24/10):** "M8.4" trong tài liệu này = lớp AN TOÀN TIỀN = **M8.0** của kế hoạch chính. "M8.4" của kế hoạch chính = tối ưu tải 10 người (cổng trước luồng tự động trả phí).


- Cấp 1: tài liệu, **không code**.
- Người viết: cloud-C, 21/10. Nhánh `cloud/v31-m81`, đọc code `main` @3b58812b.
- Phiên chính trình Executive Producer (EP).
- Bổ sung **mục 8c — Khi lỗi và khi muốn đổi**: cloud-E, 21/10, việc C-M81B, nhánh `cloud/v31-m81b`.
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

## 8c. Khi lỗi và khi muốn đổi

- Bổ sung theo câu hỏi của EP ngày 21/10: *"khi lỗi gen ảnh / gen video, người dùng đơn giản làm gì, thao tác ra sao? Tối giản nhưng vẫn đổi được đầu vào / đầu ra theo ý"*.
- Người viết: cloud-E, 21/10, việc C-M81B, nhánh `cloud/v31-m81b`. Đọc code `main` @12735052. Cấp 1: tài liệu, **không code**.
- Mục này thay hai chỗ cũ: "Vẽ lại / Làm lại + lý do" (mục 4–5) và thẻ lỗi 3 dòng (mục 8b). Thẻ lỗi 3 dòng của 8b vẫn dùng cho lỗi **ngoài cảnh** (chat, xuất bản, đăng nhập).
- Quy ước nhãn cho từng việc:
  - **CÓ**: code hôm nay đã làm được, chỉ cần nối vào màn Đơn giản;
  - **MỚI**: chưa có trong code, phải làm ở Cấp 2;
  - **CHỐT**: cần EP quyết.

### 8c.1 Thẻ cảnh thống nhất (ảnh và clip dùng chung một thẻ)

Ở bước ② và ③, mỗi cảnh là một thẻ, nằm cùng một chỗ. Thẻ có **4 nút cố định** và không bao giờ đổi vị trí:

| Nút | Làm gì | Tiền | Nối vào code |
|---|---|---|---|
| **✔ Được** | Duyệt ảnh / clip của cảnh này | 0 | `Pipeline.approve` (`core/pipeline.py:776`) — CÓ |
| **✍ Sửa bằng lời** | Gõ 1 câu ("Kelly cười tươi hơn", "ngắn còn 4 giây", "quay từ xa hơn"). Đạo diễn AI sửa ý đồ cảnh, người xem **bản trước / sau** rồi mới đồng ý chi | ảnh / clip: giá trên nút Đồng ý | Xem 8c.4 |
| **🖼 Đổi ảnh tham chiếu** | Gắn 1 ảnh mới (trang phục / skin / phông nền / đạo cụ) kèm 1 câu | ảnh vẽ lại: giá trên nút Đồng ý | Xem 8c.4 |
| **⋯ Khác** | Bản cũ (‹ ›) · Cắt ngắn clip · Bỏ cảnh khỏi phim · Đổi thứ tự · Mở ở chế độ Chuyên gia | 0 | Xem 8c.5 |

Mỗi thẻ có một **dòng trạng thái**, chỉ hiện một trong các dạng sau:

- ⏳ đang làm (≈ x phút);
- ✅ đã duyệt;
- 🔧 máy đang tự sửa (lượt 2/3);
- ⚠ cần bạn (thẻ lỗi, 8c.2);
- 🕘 cũ — đầu vào đã đổi.

Dòng "cũ" lấy lý do từ `lineage.scan` qua `dashboard/quality_ui.py:241 stale_reason`, viết lại bằng chữ thường.

**Bản vẽ — thẻ cảnh bình thường**

```
┌ Cảnh 3 · Kelly trèo tường ─────────────────── ✅ đã duyệt ┐
│ ┌───────────────┐  Ảnh  ‹ bản 2/3 ›                       │
│ │               │  Clip ▶ 5 giây (bản xem thử)            │
│ │   (ảnh/clip)  │  💬 "Kelly mặc áo khoác xám"             │
│ │               │                                         │
│ └───────────────┘                                         │
│ [ ✔ Được ] [ ✍ Sửa bằng lời ] [ 🖼 Đổi ảnh tham chiếu ] [⋯]│
└───────────────────────────────────────────────────────────┘
```

**Bản vẽ — "⋯ Khác" mở ra (mọi mục 0 USD)**

```
┌ ⋯ Cảnh 3 ──────────────────────────────┐
│ ‹ › Xem / dùng bản cũ   (3 bản)        │
│ ✂  Cắt ngắn clip        [0,0 ──●── 5,0]│
│ ⤵  Bỏ cảnh khỏi phim    (giữ lại tệp)  │
│ ⇅  Đổi thứ tự cảnh      [↑] [↓]        │
│ 🧠 Mở cảnh này ở chế độ Chuyên gia      │
└────────────────────────────────────────┘
```

### 8c.2 Khi LỖI — thẻ "Chuyện gì — Máy đã thử gì — Bạn chọn"

**Khi nào hiện thẻ lỗi.** Thẻ lỗi thay chỗ dòng trạng thái của thẻ cảnh (không bật hộp thoại) trong 4 trường hợp:

- gen hỏng;
- nhà cung cấp từ chối;
- máy tự kiểm (QC) trượt và **không tự sửa được** nữa;
- hết lượt tự sửa theo M6: ảnh 3 lượt, video 2 lượt mỗi shot, tính cả lần đầu.
  - Chính sách: sổ `v31-m6-generation-limits-policy-b-2026-10-21` và `v31-ep-m6-self-repair-budget-40-2026-10-21`.
  - Code hôm nay: `AUTO_REGEN_LIMIT = {"image_gen": 3, "video_gen": 2}` (`core/pipeline.py:33`).

Khi máy còn đang tự sửa trong trần, thẻ chỉ hiện 🔧, **không** hỏi người.

**Thẻ lỗi có 3 dòng + 2–3 lựa chọn.** Mỗi lựa chọn ghi sẵn giá:

- **Chuyện gì**: một câu chữ thường, lấy từ bảng 8c.3.
- **Máy đã thử gì**: liệt kê các lượt đã chạy, mỗi lượt kèm tiền.
  - Lấy từ chuỗi job cùng shot (`parent_job_id`, `retry_count`) và sổ chi.
  - Lấy thêm kế hoạch sửa `repair_plan` khi cờ `repair_router` bật (`core/repair_router.py`).
- **Bạn chọn**: chọn trong các lựa chọn dưới đây.

| Mã | Lựa chọn | Tiền | Đi vào code |
|---|---|---|---|
| (a) | **Thử lại với góp ý**: gõ 1 câu, máy đổi đầu vào theo câu đó | giá 1 lượt trên nút Đồng ý | `Pipeline.reject(..., note=…)` / `retry(by_user=True)` (`core/pipeline.py:866`, `:453`). Luật "gen lại phải đổi đầu vào": `_same_input_regen` → `quality_tier.regen_refusal` (`core/quality_tier.py:792`). Ô góp ý trống → nút xám — CÓ |
| (b) | **Đổi cách đơn giản hơn**: máy đề xuất sẵn ảnh tham chiếu khác hoặc cách quay đơn giản hơn (ít người hơn, máy quay đứng yên, cảnh rộng hơn) | giá 1 lượt | Đề xuất lấy từ `REPAIR_ACTIONS` (`core/repair_router.py`): SWAP_REF / REWRITE_PROMPT / REFRAME / REPLATE. Hôm nay router chỉ đề xuất, cờ TẮT — MỚI: hiện đề xuất thành lựa chọn |
| (c) | **Giữ bản tốt nhất hiện có** | 0 | `takes.choose` (`core/takes.py:109`), giống nút "đổi bản" ở `dashboard/steps/step4.py:851`. Ảnh: duyệt bản đó — CÓ |
| (d) | **Báo kỹ thuật** | 0 | Mở phiếu M6 lên Đạo diễn / Kỹ sư: `tickets.open_or_merge` / `tickets.from_fix` (`core/tickets.py:132`, `:375`). Cảnh đứng ở "⚠ cần bạn", không chi thêm — CÓ (module), MỚI (nút) |
| (e) | **Cắt bỏ đoạn lỗi** (chỉ với clip; hiện khi lỗi là đoạn đứng / giật / chuyển cảnh thừa) | 0 | TRIM trong `REPAIR_ACTIONS` (QC-V2-STILL_OVER_1_5S, QC-V2-JERK_FREEZE, QC-V2-REF_TRANSITION) → `editor_apply` `trim_head` / `cut_segment`; `delivery.render` với `edits["head"]` / `edits["cut"]` — CÓ (ở màn dựng) |

Thẻ chỉ hiện **2–3 lựa chọn hợp với loại lỗi** (xem bảng 8c.3), không hiện đủ 5. Lựa chọn **0 USD** luôn đứng đầu khi nó giải quyết được lỗi.

**Hết lượt tự sửa → KHÔNG tự chi thêm.**

- Code hôm nay đã đúng: `_spawn_retry(auto=True)` gặp `_retries_exhausted` thì gọi `_escalate(limit=True)` (`core/pipeline.py:1094`, `:1145`). Việc này:
  - ghi diag `auto_regen_limit` (`AUTO_LIMIT_CODE`, `core/pipeline.py:42`);
  - đặt cảnh sang `needs_attention`;
  - không tạo job.
- Màn Đơn giản chỉ việc đổi `needs_attention` thành thẻ lỗi.
- **CHỐT (Q-G):** lượt **người** bấm (a) / (b) sau khi đã hết trần M6.
  - Code hôm nay: lượt người là `auto=False` nên **đặt lại bộ đếm về 0** (`_spawn_retry`, docstring dòng 1096).
  - Sổ M6: trần "tính chung mọi vai", "không tự đặt lại khi sửa prompt".
  - Đề xuất cho chế độ Đơn giản: quá trần thì nút (a) / (b) đổi chữ thành **"Xin thêm 1 lượt · x USD"**.
    - Người dùng là EP: một lần Đồng ý ghi rõ "vượt giới hạn lượt".
    - Không phải EP: mở phiếu chờ EP duyệt.
  - Không lặng lẽ cho lượt thứ 4.

**Bản vẽ — thẻ lỗi (clip)**

```
┌ Cảnh 5 · Kelly ném keo ──────────────────────── ⚠ cần bạn ┐
│ ┌───────────────┐  CHUYỆN GÌ                              │
│ │  (bản tốt     │  Clip bị đứng hình gần 2 giây ở giữa.   │
│ │   nhất: 2/2)  │  MÁY ĐÃ THỬ                             │
│ └───────────────┘  • Lượt 1: đứng hình 2,4 s   (0,9 USD)  │
│                    • Lượt 2: sửa mô tả chuyển động →      │
│                      còn 1,8 s                 (0,9 USD)  │
│                    Đã hết 2/2 lượt tự sửa — máy DỪNG,     │
│                    không chi thêm.                        │
│ BẠN CHỌN                                                  │
│ [ ✂ Cắt bỏ đoạn đứng · 0 USD ]  ← máy gợi ý               │
│ [ ✔ Giữ bản 2 · 0 USD ]                                   │
│ [ ✍ Xin thêm 1 lượt + góp ý · 0,9 USD … ]                 │
│ ⓘ Báo kỹ thuật                                            │
└───────────────────────────────────────────────────────────┘
```

**Bản vẽ — thẻ lỗi (ảnh, nhà cung cấp từ chối)**

```
┌ Cảnh 2 · Kelly trong kho ───────────────────── ⚠ cần bạn ┐
│ CHUYỆN GÌ   Máy làm video từ chối vì ảnh giống người thật.│
│ MÁY ĐÃ THỬ  Đã chuyển sang máy làm video khác — vẫn bị    │
│             từ chối. Không mất tiền (bị từ chối trước khi │
│             làm).                                         │
│ BẠN CHỌN                                                  │
│ [ 🖼 Dùng ảnh mẫu kiểu hoạt hình (máy đề xuất) · 0,05 USD ]│
│ [ ✍ Thử lại với góp ý · 0,05 USD … ]                      │
│ ⓘ Báo kỹ thuật                                            │
└───────────────────────────────────────────────────────────┘
```

Các số USD trong bản vẽ chỉ là **minh họa**. Giá thật lấy từ:

- `cost.estimate_images` / `cost.send_clip_usd` / `cost.price_tag` (`core/cost.py:168`, `:376`, `:430`);
- `tools/pregen_check.py` cho đợt lớn.

Không có giá thì nút ghi "chưa có giá — hỏi kỹ thuật" và **không** cho bấm chi tiền.

### 8c.3 Bảng ánh xạ: loại lỗi → câu chữ thường → lựa chọn

**Nguồn mã lỗi**

- Mã lỗi nhà cung cấp: `ProviderError(code=…)` trong `core/adapters/*`, `core/providers.py`, `core/subjects.py`, `core/llm_runner.py`.
- Mã QC: `REPAIR_ACTIONS` / `CRITERION_CODE` (`core/repair_router.py`).
- Lỗi gốc: sổ `devsys/errors.json`.
- Câu ở cột 3 là bản nháp cho trường `user_vi`; lựa chọn là bản nháp cho trường `action_vi` (mục 8b, làm ở M8.5).

**Lỗi nhà cung cấp và vận hành**

| Loại lỗi | Mã thật | Chuyện gì (câu cho người) | Máy tự làm trước | Bạn chọn |
|---|---|---|---|---|
| Bị kiểm duyệt: ảnh giống người thật / bản quyền | `real_person` (`core/adapters/clipai.py:290`), `risk_control` (`core/providers.py:13`); P31-G32 | "Máy làm video từ chối vì ảnh giống người thật (hoặc giống nhân vật có bản quyền)." | `VideoRunner._on_refused` (`core/runner.py:2302`): Seedance → Kling theo nhóm. CHỐT: M6 điều (6) cấm tự chuyển sang model ngoài phạm vi giá đã duyệt — chỉ tự chuyển khi giá Kling ≤ giá đã duyệt | (b) ảnh mẫu khác / kiểu vẽ khác · (a) góp ý · (d) |
| Nhà cung cấp hết tiền | `out_of_credit` (`core/adapters/http.py:22` `out_of_credit()`); P31-G33, P33-A3, P33-A13 | "Tài khoản máy vẽ / máy làm video đã hết tiền. Máy đã dừng mọi việc gửi đi, không mất thêm tiền." | Dừng gửi (`llm_provider.quota_halt`, `core/llm_provider.py:260`, cho Claude) | (d) báo người nạp tiền · "Chạy tiếp khi đã nạp" (0 USD). **Không** có nút thử lại tốn tiền |
| Quá thời gian chờ / mạng | `timeout` (`core/subjects.py:186`, `core/adapters/clipai_subjects.py:142`, `core/llm_runner.py:1540`), `network` (`core/llm_runner.py:508`) | "Máy làm video trả lời quá lâu. Máy sẽ hỏi lại kết quả, chưa gửi lại." | Hỏi lại (poll); `transient=True` thì thử lại không tốn tiền | (c) giữ bản cũ · "Chờ thêm" · (d) |
| Gửi chưa rõ kết quả | `submit_unknown` (`core/pipeline.py:48`, `Runner._submit_unknown` `core/runner.py:611`); cổng G5 `core/release_gate.py:111` | "Lần gửi trước chưa rõ đã nhận hay chưa — có thể đã tính tiền. Máy không gửi lại để tránh trả 2 lần." | Ghi sổ chi "có thể đã tính", dừng | (d) báo kỹ thuật đối soát. **Không** có (a) / (b) (M6 điều 5) |
| Kho chủ thể đầy | `library_full` (`core/adapters/clipai_subjects.py:35` `is_library_full`, `:41` `full_error`); P31-G30, P31-G58 | "Kho ảnh trên máy làm video đã đầy (100 ảnh). Cần dọn bớt ảnh cũ rồi máy tự gửi lại." | Không ghi `failed` (luật trong `full_error`); chờ | "Dọn ảnh đã bỏ · 0 USD" (cờ `subject_auto_cleanup`, dry-run chờ duyệt) · (d) |
| Prompt quá dài | `prompt_too_long`; `QC-PKG-PROMPT_TOO_LONG`; P31-G13, P31-G54 | "Mô tả gửi máy quá dài — máy đang rút gọn." | FIX_PACKAGE 0 USD (rút theo trần `video_rules`); nối M2.10 gói tối giản | Chỉ hiện khi vẫn đỏ: (a) góp ý ngắn hơn · (d) |
| Nhà cung cấp quá tải | `rate_limited`, `server_error`, `http_error` (`core/adapters/*`) | "Máy làm video đang quá tải. Máy sẽ thử lại sau ít phút, không tốn thêm." | Chờ rồi thử lại (`http.call_rate_limited`) | "Chờ" · (d) |
| Ảnh nhân vật / form thiếu trong Kho | `missing_image`; `QC-PKG-FORM_PICTURE_MISSING`; P31-G27 | "Thiếu ảnh chuẩn của *Kelly (dạng bóng mờ)* nên máy chưa vẽ được." | Tự gắn ảnh form từ Kho nếu có (`Runner._ref_lint`, `core/runner.py:1214`) | **🖼 Thêm ảnh** (8c.4) · (d) |
| Hết lượt tự sửa | `auto_regen_limit` (`core/pipeline.py:42`); dừng `REPAIR_LIMIT`, `REPAIR_SAME_CODE_TWICE` | "Máy đã thử *n/n* lượt cho cảnh này nhưng chưa đạt — đã dừng, không chi thêm." | Không | (c) giữ bản tốt nhất · (a) / (b) "Xin thêm 1 lượt" (CHỐT Q-G) · (d) |
| Lỗi chưa có câu | mọi mã khác, `REPAIR_UNMAPPED` | "Có trục trặc kỹ thuật ở bước *X* — máy đã dừng bước này, không tốn thêm tiền." | Dừng | (c) nếu có bản cũ · (d) |

**Lỗi chất lượng (QC trượt và không tự sửa được nữa)**

| Loại lỗi | Mã thật | Chuyện gì (câu cho người) | Máy tự làm trước | Bạn chọn |
|---|---|---|---|---|
| Sai nhân vật / lệch mặt | `QC-L1-IDENTITY_DRIFT` (`CRITERION_CODE` `character`, `identity`); P31-G37 | "Nhân vật trong ảnh không giống *Kelly* (khuôn mặt / dạng khác)." | SWAP_REF + REWRITE_PROMPT ≤ 3 ảnh / 2 video | (b) đổi ảnh chuẩn (máy đề xuất) · (a) · (c) |
| Lẫn tóc / áo, sai trang phục | `QC-L2-FORM_OUTFIT`; P33-B1 | "Áo / tóc của *Kelly* bị lẫn với ảnh mẫu trang phục." | Ảnh form khác + câu sửa trang phục | (b) **🖼 Đổi ảnh tham chiếu** (ảnh chỉ có áo, không có đầu) · (a) · (c) |
| Thừa người | `QC-L3-EXTRA_PEOPLE` | "Ảnh có thêm người không có trong kịch bản." | Câu "chỉ N người" | (a) · (b) cách quay đơn giản hơn · (c) |
| Sai động tác | `QC-L4-POSE_ACTION`, `QC-V4-MOTION_VS_BYD`; P31-G11 | "Động tác chưa đúng ý cảnh (cần: *trèo tường*)." | Viết lại theo ý đồ cảnh | (a) · (c) |
| Thiếu đồ vật | `QC-L7-PROP_MISSING`; P31-G7 | "Thiếu *khẩu súng* trong ảnh." | Câu đạo cụ + ảnh vật từ Kho | (b) 🖼 gắn ảnh vật · (a) · (c) |
| Sai phông nền / chân trời | `QC-L9-HORIZON_MISMATCH`, `QC-L11-PLACE_MISMATCH`; P31-G20 (báo nhầm) | "Phông nền khác với các cảnh cùng chỗ." | REPLATE (dựng lại phông) | (b) 🖼 đổi phông · (c) "Vẫn dùng" |
| Tay / mặt lỗi | `QC-L14-ARTIFACT` (`hands_face`, `artifacts`) | "Tay / mặt bị méo." | Seed mới + câu khác lần trước | (a) · (c) |
| Đứng hình / giật | `QC-V2-STILL_OVER_1_5S`, `QC-V2-JERK_FREEZE`; P31-G51 | "Clip bị đứng hình *1,8 s* ở giữa." | TRIM nếu cắt đủ, rồi mới viết lại chuyển động | **(e) cắt bỏ · 0 USD** · (c) · (a) |
| Lộ đoạn chuyển cảnh của video mẫu | `QC-V2-REF_TRANSITION`; P33-B8 | "Đầu clip lộ một đoạn của video mẫu." | Chỉ TRIM, không gen lại (lỗi do ref) | **(e) cắt bỏ · 0 USD** · (d) |
| Không bắt đầu đúng ảnh đã duyệt | `QC-V1-FIRST_FRAME_MISMATCH`; P31-G28, P33-B9 | "Clip không mở đầu bằng ảnh bạn đã duyệt." | Đổi chế độ khung đầu (M2.8) | (a) · (c) |
| Khớp môi lệch | `QC-V3-LIP_SYNC` | "Miệng không khớp lời thoại." | Chỉnh độ lệch tiếng (0 USD) rồi mới làm lại clip | (c) · (a) |
| Không liền mạch với cảnh khác | `QC-L13-CONTINUITY` (REVIEW_ONLY) | "Cảnh này không khớp cảnh trước (*vị trí / trang phục*)." | Không tự sửa (D07) | Người quyết: "Vẫn dùng" (0) · (a) · (d) |

**Luật chung của bảng**

- Lỗi provider có `transient=True` và chưa tạo task: máy tự thử lại, 0 USD, không hỏi.
- Lỗi đã tạo task hoặc chưa rõ: **không bao giờ** tự gửi lại.
- 3 shot liên tiếp cùng mã → dừng tự sửa + mở phiếu (sổ `v31-ep-m6-self-repair-budget-40-2026-10-21`). Màn Đơn giản gộp thành **một** thẻ "⚠ 3 cảnh cùng lỗi *X* — đã báo kỹ thuật", không hiện 3 thẻ rời.

### 8c.4 Đổi ĐẦU VÀO kiểu Weave Canvas (gắn 1 ảnh + 1 câu)

**Mẫu Weave Canvas (Deepix).** Mỗi ảnh tham chiếu là một hình có tên. Prompt gọi "Figure 1 / Figure 2" bằng một câu ngắn. Ở Đơn giản:

```
┌ 🖼 Đổi ảnh tham chiếu · Cảnh 3 ──────────────────────────┐
│ ① Ảnh mới:  [ Kéo ảnh vào / chọn từ Kho ]  → [ áo xám ]   │
│ ② Một câu:  [ dùng áo này cho Kelly từ cảnh 3 ]           │
│ ③ [ Xem thay đổi + giá ]                                  │
│ ─────────────────────────────────────────────────────────│
│ Máy hiểu:  Ảnh mới = TRANG PHỤC của Kelly                 │
│            Áp cho: cảnh 3, 4, 5, 6 (Kelly có mặt)         │
│ Bộ ảnh gửi cảnh 3:  Kelly (mặt) · ÁO XÁM (mới) · Kho      │
│            bỏ: áo cũ                                      │
│ Sẽ thành cũ:  4 ảnh (cảnh 3–6) · 2 clip (cảnh 3, 4)       │
│ Giá vẽ lại:  4 ảnh ≈ 0,20 USD · 2 clip ≈ 1,80 USD         │
│ [ Chỉ cảnh 3 ]  [ ④ Đồng ý · 2,00 USD ]  [ Hủy ]          │
└───────────────────────────────────────────────────────────┘
```

**Máy làm gì sau ③ "Xem thay đổi + giá" — 0 USD, chưa gen**

1. **Hiểu vai của ảnh mới** từ câu.
   - Các vai: trang phục / skin / phông nền / đạo cụ / mặt nhân vật.
   - Áp cho nhân vật nào, từ cảnh nào.
   - Đọc câu cần 1 lần gọi Claude rẻ, giá ghi ngay trên nút ③.
   - Chưa chắc thì hỏi lại bằng 2 nút ("Áo cho Kelly" / "Áo cho Rối"), không đoán.
2. **Lưu ảnh vào Kho dự án.** Ảnh vào Kho như tư liệu chat: `chat_intake.apply` / `chat_refs.add` (`core/chat_refs.py:34`).
3. **Cập nhật bộ ảnh tham chiếu của từng cảnh** qua `core/package_overrides.py` — CÓ module, cờ `package_overrides`, chưa nối Dashboard.
   - `save(conn, scene_id, edits, who, reason, expected_revision)` (`:142`) với edit `{"op": "add" | "exclude" | "pin", "role": "outfit", "source_kind": "kho", "wearer": "Kelly", ...}` (`_resolve` `:65`).
   - Module đã có sẵn: kiểm SHA, chặn đường dẫn nhập tay, ghi CAS, giữ `_user_locked`, và `undo` (`:274`) để hoàn tác.
4. **Thêm dòng vai trò ngắn** cho ảnh mới (vd "Figure 3: Kelly's outfit — use clothing only, not hair or face"). Đây là việc **M2.10 gói gửi tối giản**:
   - mỗi ảnh tham chiếu 1 dòng vai trò + thứ KHÔNG lấy;
   - bỏ ảnh trùng hoặc mâu thuẫn;
   - sổ `v31-ep-m210-lean-package-2026-10-21`; số đo đầu vào ở `docs/data/goi_gui_31_33_2026-10-21.md`.
   - **Thứ tự triển khai:**
     - Khi chưa có builder lean (C-M210-DESIGN, `core/lean_package.py` SHADOW cờ `lean_package` TẮT), gói thật vẫn đi builder cũ. Ảnh mới chỉ được **thêm / thay** qua `package_overrides`.
     - Khi M2.10 qua A/B, "đổi skin / nền = thay 1 ref + 1 dòng" là đường chính.
     - Lúc viết mục này chưa có nhánh `origin/cloud/v31-m210`, nên bảng chi tiết theo loại shot lấy từ tài liệu M2.10 khi có.
5. **Đánh dấu cũ đúng các ảnh / clip phụ thuộc.**
   - Ảnh của cảnh nào đổi đầu vào → `lineage` báo cũ: `image_spec_hash` / `image_changes_since_approval` / `stale_image_reason` (`core/lineage.py:32`, `:158`, `:185`).
   - Clip dựng từ ảnh đó → cũ theo `video_input_hash` (`:50`).
   - Phạm vi lan sang shot kề / cả nhóm / mọi shot dùng vật Kho đó: `change_review.affected_scenes` (`core/change_review.py:69`).
   - Danh sách "Sẽ thành cũ" ở bản vẽ trên là **đúng tập này**, không phải "cả phim".
   - **S-D** (sổ chốt EP 21/10, `docs/CAU_HOI_CHOT_TONG_HOP_2026-10-21.md:54`): đổi vai / trang phục cho cảnh **đã có ảnh** phải **hỏi xác nhận riêng**. Nút ④ "Đồng ý" chính là lần xác nhận đó, ghi rõ số ảnh / clip sẽ thành cũ.
6. **Báo giá vẽ lại.**
   - Số ảnh: `cost.estimate_images` (`core/cost.py:168`).
   - Số giây clip: `cost.send_clip_usd` (`:376`).
   - Ghi bằng `cost.price_tag`.
   - Có nút **"Chỉ cảnh 3"** để thu hẹp phạm vi và giảm tiền.
   - Ảnh / clip cũ **không bị xóa**: vẫn xem được bằng ‹ ›.
7. **④ Đồng ý** → gen trong ngân sách cả phim. Vượt dự toán thì dừng và hỏi (mục 8.2).

**Đổi thoại / giọng / độ dài / góc quay bằng lời** (nút "✍ Sửa bằng lời")

- Đạo diễn AI sửa **trường ý đồ cảnh (BYĐ)** tương ứng. Đường viết lại hiện có: `core/prompt_rewrite.py` và `Pipeline._rewrite_before_retry` (`core/pipeline.py:909`).
- Người thấy **bản trước / sau** bằng chữ thường, ví dụ "Thời lượng: 6 s → 4 s; Góc: cận → trung", **trước khi** chi.
- Giá trên nút Đồng ý = Claude (nếu có) + ảnh / clip phải làm lại.
- Đổi chỉ thoại hoặc giọng mà ảnh không đổi → chỉ làm lại giọng / clip, ảnh **giữ**.

**Dữ liệu người sửa → USER_LOCKED** (sổ `v31-ep-motion-prompt-user-locked-2026-10-21`)

- Mọi trường người đổi qua 8c.4 được thêm vào khóa `_user_locked` của cảnh. Cách này đã có ở:
  - `core/dialogue.py:331` (`duration_s`);
  - `core/shots.py:349–373` (giữ trường khóa khi Đạo diễn chạy lại; `package_overrides`);
  - `core/script_pose.py:110`.
- Nhờ khóa, Đạo diễn / máy tự sửa **không ghi đè** các trường này.
- Motion prompt người sửa tay là USER_LOCKED theo C-M25B. Sổ ghi rõ: SHADOW chỉ quan sát, ENFORCE cần nghiệm thu + quyền bật riêng (C3-6). Vì vậy ở Đơn giản, "Sửa bằng lời" sửa **BYĐ** (Đạo diễn viết lại motion từ BYĐ), không cho gõ thẳng motion prompt tiếng Anh.
- Khi máy tự sửa (8c.2) cần đổi một trường đang khóa → dừng `REPAIR_INTENT_CHANGE` và hỏi người, không tự đổi.

### 8c.5 Đổi ĐẦU RA — 0 USD, không cần chế độ Chuyên gia

| Việc | Ở đâu | Tiền | Code |
|---|---|---|---|
| Chọn bản cũ (‹ ›) | ⋯ Khác / thẻ lỗi (c) | 0 | `takes.choose` (`core/takes.py:109`) cho clip; ảnh: `Pipeline.approve` bản cũ. Bản đã loại còn trong thùng rác (`core/trash.py` `restore` `:105`) — CÓ |
| Cắt ngắn clip / cắt đoạn giữa | ⋯ Khác → thanh kéo 2 đầu | 0 (ffmpeg) | `editor_apply` `shorten_shot` / `trim_head` / `cut_segment` (`core/editor_apply.py`); `delivery.render(edits=…)` (`core/delivery.py:527–576`); `shots.trim_clip` (`core/shots.py:539`) — CÓ. Không cắt shot có khớp môi (luật KLD-19 trong `editor_apply`) |
| Bỏ cảnh khỏi phim | ⋯ Khác | 0 | **MỚI**: cờ "không đưa vào bản dựng" trên cảnh. `Pipeline.delete_scene` (`core/pipeline.py:261`) **từ chối** cảnh đã có ảnh / video, và đúng là không nên xóa. Tệp giữ nguyên, bật lại được |
| Đổi thứ tự cảnh | ⋯ Khác ↑ ↓ | 0 | **MỚI**: chưa có hàm đổi `idx`. Đổi thứ tự sau khi có clip thì các nối cảnh (khung cuối → khung đầu, liên tục) có thể thành cũ → hiện cảnh báo + danh sách cảnh bị ảnh hưởng (`change_review.affected_scenes`), vẫn 0 USD cho tới khi người chọn làm lại |
| Thay nhạc | ④ Tải: 3 lựa chọn có sẵn | 0 | `delivery.selected_music` / `music_tracks` (`core/delivery.py:125`, `:101`); nghe thử `final_cut.preview_with_music` (`core/final_cut.py:158`) — CÓ. Tạo nhạc mới (`core/music.py` `generate_music`) **tốn tiền** → chỉ ở Chuyên gia |
| Có / không phụ đề | ④ Tải | 0 | Như mục 6 |

**Sau mỗi thay đổi đầu ra**

- Bản dựng tự làm lại (0 USD).
- Bản trước vẫn giữ để so sánh A/B, theo cách `editor_apply`: `FINAL_VIDEO.mp4` = bản hiện tại, bản cũ ở `output/_editor/`.
- `editor_apply.revert` (`:265`) dùng làm nút "↩ Trở lại bản trước".

### 8c.6 Đếm thao tác

Quy ước đếm:

- Một **cú bấm** = một lần bấm nút / chọn ảnh.
- Gõ chữ không tính là cú bấm.
- Thẻ lỗi hiện sẵn trên thẻ cảnh, nên không có bước "mở".

**Khi gặp lỗi**

| Tình huống | Các bước | Số cú bấm | Mục tiêu |
|---|---|---|---|
| Lỗi → giữ bản tốt nhất | [✔ Giữ bản 2] | **1** | ≤ 3 ✅ |
| Lỗi → cắt bỏ đoạn đứng | [✂ Cắt bỏ · 0 USD] → xem bản cắt → [✔ Được] | **2** | ≤ 3 ✅ |
| Lỗi → đổi cách máy đề xuất | [🖼 Dùng ảnh mẫu máy đề xuất] → [Đồng ý · x USD] | **2** | ≤ 3 ✅ |
| Lỗi → thử lại với góp ý | [✍ Thử lại với góp ý] → *gõ câu* → [Đồng ý · x USD] | **2** | ≤ 3 ✅ |
| Lỗi → báo kỹ thuật | [ⓘ Báo kỹ thuật] → [Gửi] | **2** | ≤ 3 ✅ |
| Lỗi hết trần M6, người không phải EP | [Xin thêm 1 lượt] → *gõ lý do* → [Gửi EP] | **2** (+ chờ EP) | ≤ 3 ✅ |

**Khi muốn đổi đầu vào / đầu ra**

| Tình huống | Các bước | Số cú bấm | Mục tiêu |
|---|---|---|---|
| Đổi skin / áo / phông một cảnh | [🖼 Đổi ảnh tham chiếu] → chọn ảnh → *gõ 1 câu* → [Xem thay đổi + giá] → [Đồng ý] | **4** | ≤ 4 ✅ |
| Như trên, chỉ cảnh 3 | … → [Chỉ cảnh 3] → [Đồng ý] | 5 | (tùy chọn thu hẹp) |
| Đổi thời lượng / góc bằng lời | [✍ Sửa bằng lời] → *gõ câu* → [Xem trước / sau] → [Đồng ý] | **3** | — |
| Dùng bản cũ | [⋯] → [‹] → [✔ Dùng bản này] | 3 | — |
| Cắt ngắn clip | [⋯] → [✂] → kéo → [✔] | 4 | — |
| Thay nhạc | [Vui] | 1 | — |

**So sánh với hôm nay** (đếm theo code, chế độ Chuyên gia):

- Lỗi video hết lượt: phải biết vào ③ → mở thẻ clip → đọc mã → chọn bản / gen lại + lý do. Không có đề xuất "cắt bỏ 0 USD" trên thẻ: cắt nằm ở màn dựng ⑤ (`editor_apply`).
- Đổi áo một cảnh: phải vào ① Nhân vật / Kho → gắn form → sửa cảnh → gen lại ảnh → gen lại clip. Ước ≥ 8 bấm qua 3 màn, không có báo trước ảnh / clip nào sẽ thành cũ.

**Đo khi làm M8.7.** Thêm 2 chỉ số vào mục 9:

| Chỉ số | Cách đo | Mục tiêu |
|---|---|---|
| Cú bấm "lỗi → giải quyết" | `ui_actions` từ lúc thẻ ⚠ hiện tới lúc cảnh rời ⚠ | ≤ 3 |
| Cú bấm "đổi skin / nền một cảnh" | `ui_actions` | ≤ 4 |

### 8c.7 Lộ trình và câu hỏi thêm

**Lộ trình — gắn vào mục 10, không thêm bước mới**

| Phần | Gắn vào | Ghi chú |
|---|---|---|
| Thẻ cảnh 4 nút + ⋯ | M8.2 | |
| Thẻ lỗi + bảng 8c.3 (`user_vi` / `action_vi`) | M8.5 | |
| (b) đề xuất từ `repair_router` | M8.6 | Cần M6-B |
| 🖼 Đổi ảnh tham chiếu | Sau khi bật cờ `package_overrides`, rồi M2.10 | |
| Bỏ cảnh / đổi thứ tự | MỚI, Cấp 2 | Cờ riêng, TẮT, test |

**Câu hỏi thêm cho EP**

- **Q-G — Lượt của người sau trần M6:** quá 3 ảnh / 2 video thì người (không phải EP) phải xin EP; EP tự bấm thì xác nhận "vượt giới hạn lượt". Đồng ý? Code hôm nay đặt lại bộ đếm khi người bấm.
- **Q-H — Tự chuyển máy làm video khi bị kiểm duyệt:** chỉ tự chuyển Seedance → Kling khi giá không vượt mức đã duyệt; vượt thì hỏi. Đồng ý?
- **Q-I — Đổi ảnh tham chiếu lan sang các cảnh sau:** mặc định "từ cảnh N trở đi, nơi nhân vật có mặt", kèm nút "Chỉ cảnh N". Đồng ý? Hay mặc định chỉ một cảnh?

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
