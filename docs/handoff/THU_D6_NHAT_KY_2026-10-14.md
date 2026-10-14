# Nhật ký thử D6 — one-shot Tháp Đồng Hồ (14/10/2026, phiên máy chính)

Đề bài: `docs/handoff/THU_D6_ONESHOT_THAP_DONG_HO_2026-10-14.md`. Người dùng 14/10: làm thử phải **thao tác trực tiếp trên Dashboard 8501**;
được phép chạy các bước tốn tiền trong ngân sách dự tính (trần cả thử nghiệm 15 USD theo đề bài).

## 0. Điều kiện trước
- main = `347ab560` (đã gộp PR #15). Sao lưu `data/backup/manifest.backup_20261014_thu_d6.sqlite` + `data/feature_settings.backup_20261014_thu_d6.json`.
- Khởi động lại 8501 + 8502 (tiến trình cũ chạy từ trước khi gộp PR #15).
- M0: `py -m pytest -q -n 8 -p no:cacheprovider` → **5314 qua**, 1 bỏ qua, 1 xfail (10 phút 07 giây).
- M1: Kho #367 chưa có ảnh đã duyệt → người dùng đồng ý thêm: ảnh `gloowall_ob55_trien_khai_1.png` → asset_images #1166, nhãn "triển khai",
  sort 0, đã duyệt (thêm bằng `core.assets.add_image`, trước khi người dùng dặn thao tác trên Dashboard).
- Kho: KELLY #23 (9 ảnh), SKORP #433 (2 ảnh), Tháp Đồng Hồ #263 (6 ảnh + mô hình 3D).
- Chỗ đứng: A = `bac_thang_giua` (có sẵn, chân cầu thang). B không có trong gói → người dùng chọn tạo mới. Đo độ cao 3D (`plates3d.ground_heights`,
  Blender, 0 USD) theo hướng 118° từ A: phẳng z 3,92 tới 4,5 m, bậc thang 4,5 → 15 m, đỉnh z 8,5. Render xem thử
  `D:\AI-Video-Output\2026-10-14_thu_d6\diem_B\` → người dùng duyệt "bậc trên cùng dải dài" → thêm chỗ đứng `dinh_bac_thang_giua`
  (−240,0; 136,82; 8,5), hướng 118°, nhóm `nhay` (sao lưu `manifest.backup_20261014_truoc_diem_B.sqlite` trước). Gói Dashboard không có ô
  thêm chỗ đứng — chỉ có `tools/location_pack.py register` (ghi đè cả mục model3d), nên ghi thẳng một chỗ đứng vào hồ sơ #263.

## 1. Dự án A (#28 "Thử D6 one-shot Tháp Đồng Hồ") — cờ `chat_prompts` TẮT
- ➕ Dự án mới: 9:16, SHORT_FORM, Cân bằng, FF → #28 (kế thừa look FF_INGAME, ảnh `gpt-image-2.5-sunburst`). Mức tự động: **Tôi duyệt hết**.
- Dán kịch bản đúng nguyên văn đề bài (bỏ dấu markdown) vào khung chat → nhận 1 cảnh → ▶ Phân tích (0 USD).
- 🧰 Tài nguyên đi kèm: "Dùng tất cả gợi ý" = KELLY, Tháp Đồng Hồ, Bom keo, SKORP (đúng 4 mục đề bài).
- Tổ rà soát (change_review, 0,02 USD) báo ĐỎ shot 1 ngay sau tách cảnh: "characters rỗng nhưng chữ có Kelly" — trước khi Đạo diễn chạy
  (Đạo diễn mới điền nhân vật) → báo động sớm, ghi lại làm lỗi phụ.
- 🤖 Chạy Director (báo giá ≈ 0,81 USD; thật 2 lượt `director` 43,8k+2,5k in / 4,8k+20,6k out, cộng dồn dự án 0,53 USD).
- **Cách Đạo diễn chia: 5 shot nối nhau (KHÔNG một clip liền), 16 s**:
  1. S01·1 WS track eye 4,5 s — chạy nước rút từ chân cầu thang về phía máy · `bac_thang_giua` · nền `landmark`
  2. S01·2 MS orbit high 2,5 s — tới bậc cao nhất, ném keo, tường dựng, máy vòng ra sau · `dinh_bac_thang_giua` · nền `away`
  3. S01·3 GAME_TPS static high 2,8 s — núp sát bên trái tường 1, ló đầu nhìn · B · nền `scenery`
  4. S01·4 GAME_TPS track high 2,8 s — chạy 5 bước sang trái, keo thứ hai · B · nền `scenery`
  5. S01·5 MCU pan high 3,4 s ⭐ — ngồi sau tường 2, hai tay SKORP, thở ra · B · nền `landmark`
- Lỗi kế hoạch (chung cho cả A và B — giữ nguyên để so đúng prompt): tường keo tả "plain white flat glue wall" (KHÔNG phải skin thang máy,
  trái luật #27); shot 1 máy phía trước Kelly mà nền `landmark` "tháp sau lưng Kelly" — sai hình học (Kelly chạy VỀ phía tháp); code tự báo
  `plate_view_check` VÀNG cùng lỗi này. `prompt_formula` VÀNG shot 2, 4 (Đạo cụ dự án).
- Duyệt ảnh mốc KELLY (ảnh Kho, 0 USD) → ✔ Duyệt & khóa → Storyboard. Mục đỏ Tổ rà soát → "✓ Đã sửa" (Đạo diễn đã điền KELLY).

## 2. Nhân bản → dự án B (#29 "Thử D6 one-shot Tháp Đồng Hồ (B)")
- ⚙ Cài đặt → 🧬 Nhân bản dự án, "Giữ nguyên các cảnh/shot hiện tại" → #29. Kiểm CSDL: 5 shot, `image_prompt` + `plate_spot` trùng khớp A,
  cùng 4 tài nguyên Kho.

## 3. Bản A — ảnh (cờ `chat_prompts` TẮT)
- ▶ Gen ảnh các cảnh chưa có / đã cũ · ≈ 0,26 USD → 5 job `image_gen`; Blender render nền 3D trước (10 góc máy).
- Xong: job 916–920 (lần gen ĐẦU), bản sao `D:\AI-Video-Output\2026-10-14_thu_d6\anh_A_raw\`. Diag: `skill_object_words` (câu cấm cửa mở cho
  Bom keo), `storyboard_anchor_skipped` (shot 2–5 khác chỗ đứng shot 1 → không gửi ảnh neo), khớp nét nền↔render 3D F1 0,45–0,70.

## 4. Bản B — ảnh (cờ `chat_prompts` BẬT)
- Sao lưu `data/feature_settings.backup_20261014_truoc_chat_prompts.json`; bật `chat_prompts` ở ⚙ → 🧪 Tính năng thử (chỉ thêm đúng cờ này).
- #29: ▶ Gen ảnh · ≈ 0,26 USD (nút KHÔNG cộng giá D6) → job 921–925, bản sao `anh_B_raw\`.
- D6 (diag `chat_prompt`): Claude nhìn 6 ảnh / shot, rút prompt ~6,2–6,8k → ~3,1–3,5k ký tự.
  - shot 1 ✅ (≈ 0,044 USD) · shot 3 ✅ (≈ 0,034) · shot 5 ✅ (≈ 0,034)
  - shot 2 ⛔ `chat_prompt_refused` "mất mã ảnh / shot: Images 2/3" → gửi bản cũ
  - shot 4 ⛔ `chat_prompt_refused` "dài 4168 > 4000 ký tự" → gửi bản cũ
  - 6 lượt `chat_prompt` (56,6k in / 8,9k out). **2/5 shot D6 bị code chặn** — kết quả riêng cần sửa (giới hạn 4000 ký tự quá chặt so với bản
    cũ 6–7k; Claude viết "Images 2/3" thay vì "Image 2, Image 3").
- Theo đề bài, shot 2, 4 KHÔNG tính; vẫn đưa vào bảng mù làm cặp đối chứng (cùng prompt cũ → đo độ ngẫu nhiên của model ảnh).

## 5. So mù ảnh
- `D:\AI-Video-Output\2026-10-14_thu_d6\so_mu_shot{1..5}.jpg` + `so_mu_anh_tat_ca.jpg`; Trái/Phải xáo ngẫu nhiên; đáp án `dap_an.json` (chưa mở).
- Gửi người dùng chọn từng shot + lý do.
- **Người dùng chọn (trước khi mở đáp án)**:
  - shot 1 → Phải ("trái lỗi nền dưới chân, cả 2 có vẻ nhầm hướng di chuyển; phải giữ được vết xước nhỏ trên mặt Kelly")
  - shot 3 → Trái ("phải hình như lỗi hình khẩu súng; bom keo cả 2 bên sai so với yêu cầu")
  - shot 5 → Phải ("giữ vết xước trên mặt Kelly khá rõ, súng ít lỗi hơn, tỉ lệ cơ thể hợp lý")
  - đối chứng shot 2 → Trái ("phải lỗi đeo súng; vết xước cả 2 đều mất"); shot 4 không chấm
- **Đáp án**: shot 1 Trái=A/Phải=B(D6) · shot 3 Trái=A/Phải=B(D6) · shot 5 Trái=A/Phải=B(D6) · shot 2 Trái=B(cũ)/Phải=A · shot 4 Trái=B(cũ)/Phải=A.
- **Kết quả ảnh: D6 thắng 2/3** (shot 1, 5; thua shot 3 vì hình súng). Không có loại lỗi mới chỉ riêng D6 (lỗi súng có ở cả hai bản).
  Điểm D6 hơn: giữ chi tiết ảnh tham chiếu (vết xước mặt Kelly) — hợp lý vì D6 NHÌN ảnh sẽ gửi. Lỗi chung cả hai (do kế hoạch Đạo diễn):
  tường keo không phải skin thang máy, hướng chạy shot 1 sai. Hạn chế: lần xáo tình cờ đặt A bên trái ở cả 3 shot tính điểm.

## 6. Video nháp
- Người dùng: duyệt cả 5 ảnh mỗi bản (lần gen đầu) + gen nháp cả hai bản.
- B (#29, cờ BẬT): "✔ Duyệt tất cả (5 ảnh)" → hộp xác nhận "Có, duyệt hết" (giao diện cũ hiện "Chờ gen" tới khi tải lại trang).
  Tab Motion: motion prompt đã có sẵn + đã duyệt (bản sao mang theo). Bước Video:
  - Bộ chọn model đề xuất: S01–S04 Seedance 2.5 · nháp 480p (2 clip nhóm S01–S02, S03–S04); **S05 Seedance 2.0 · 720p** — trái quyết
    định 13/10 "video hết Seedance 2.5" (tuyến E1 còn trong `model_router`). Đổi S05 → Seedance 2.5 (chỉ có lựa chọn 720p, không có nháp 480p
    cho shot lẻ). Sẽ đặt y hệt ở A.
  - Báo giá 5 clip ≈ 2,67 USD (tự gen lại tối đa ≈ 8,01). Video tự gen lại khi QC trượt (không tắt được) → canh, chỉ lấy lần đầu.
  - Nút ▶ Gen video phải bấm 2 lần (lần 1 chỉ xếp hàng 4 job "chờ gửi", lần 2 thêm S05) → job 926–930.
  - Diag: `skill_object_compose` VÀNG (tường keo xuất hiện luôn; gợi ý ghép code).
  - **Cả 5 job bị `video_pregen_hold`** "đổi tư thế nhưng thiếu nhịp đỉnh". BYĐ Đạo diễn: shot 1, 2, 4 `dung→dung`, shot 3 `quy→quy`,
    shot 5 `dung→ngoi`. Shot 1–4 = **báo nhầm** (cùng tư thế mà code chỉ đếm nhịp). Shot 5 = mâu thuẫn hai lớp code: prompt
    `prompts/31_director_byd.md:21,33` + mẫu `_good()` cho đổi tư thế 2 nhịp (`dinh` tùy chọn), còn `video_pregen` đòi 3 nhịp → ĐỎ.
  - Người dùng: "quan trọng là tư thế nào đúng theo kịch bản" → **sửa code**: `shot_intent.missing_beat()` (đổi = `tu_the` nhịp sau khác
    nhịp đầu) dùng ở `video_pregen._check_motion`; đổi tư thế thiếu một nhịp → VÀNG (vẫn gửi). Test đỏ trước (cùng tư thế bị chặn), 113 qua
    ở 6 tệp liên quan. Agent rà (quy ước 7): không test nào dựa hành vi cũ; `_changes()` (khung cuối) so cả `cham_dat` → có thể VÀNG
    "không kèm khung cuối" — giữ (chỉ VÀNG, đổi chỗ chạm đất thấy được ở khung cuối).
  - **Tư thế sai kịch bản (lỗi kế hoạch, chung A/B):** shot 3 Đạo diễn ghi `quy` (quỳ) trong khi kịch bản "Kelly **đứng sát**, núp bên
    trái… ló ra ngó" — ảnh cả hai bản vẽ Kelly ngồi xổm. Code chưa kiểm tư thế BYĐ ↔ chữ kịch bản.
  - D6 video (diag): job 926 (nhóm S01–S02) `chat_prompt_refused` "mất mã ảnh / shot: Shot 1, Shot 2" → bản cũ; job 928 (nhóm S03–S04)
    `chat_prompt_cap` (2 lượt mà đầu vào vẫn đổi) → bản cũ; job 930 (S05) ✅ D6 (bỏ câu 'back to camera, face never seen' trái ảnh khung
    đầu). → Video chỉ S05 thật sự có D6.
