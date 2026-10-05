# HANDOFF S14.34 (05/10/2026) — nhánh worktree-agent-aaa4d960e49c72809

## Đã làm
- Cờ mới `kelly_knowledge` (TẮT, chưa verified): `core/knowledge.py` `kelly_blocks(role)` + `KELLY_DOCS`; 4 sách ngắn `knowledge/craft/kelly_{bien_kich,dao_dien,quay_phim,dung}.md`.
  Nạp vào: Biên kịch (`idea_to_script.build_prompt`, ngay sau khối dựng-được), Đạo diễn (`build_director_bundle` + `build_intent_bundle`), Quay phim (`dp_common`), Biên tập/Dựng (`editor_review.editor_prompt`). Cờ tắt = prompt y hệt (có test).
- Tinh thần theo người dùng 05/10: phần Kelly để MỞ RỘNG phong cách, là GỢI Ý "có thể / nên cân nhắc / khi nào hợp", KHÔNG cấm/bắt buộc (test chặn các từ cấm/bắt buộc trong 4 sách). Chặn cứng chỉ còn ở S14.31 (thứ không dựng được: ngoài Kho, giao diện/gameplay).
- `tests/test_kelly_knowledge.py` (13 test), `devsys/areas.json` khai cờ + test (không tăng version).
- Bộ đo mới `data/idea_golden/ideas.json`: 3 ý tưởng khuôn A/B/D (bản cũ lưu `ideas.before_S14_34_2026-10-05.json` ở máy chính).
- `tools/experiments/idea_script_eval.py`: `--kelly` (bật cờ; ghi vào result.json, replay tự theo), `--sheet-suffix`, và `assets.REPO` theo thư mục chứa DB (chạy từ worktree vẫn thấy ảnh Kho máy chính).

## Bản ghi / phiếu
- Bản ghi: `D:\AI-Video-Pipeline\data\idea_golden\runs\20261005-185120\` (calls.jsonl 8 lượt, result.json `kelly: true`). Replay 0 USD: 0 miss.
- Phiếu: `docs/DO_S11_2_Y_TUONG_2026-10-05b.md` (ý 1, 2 có kịch bản; ý 3 CHƯA chạy vì chạm trần 0,60).
- Chi thật 0,421 USD cho 2 ý (0,208 + 0,213), ước tính 0,36; ý 3 ước 0,18 sẽ vượt trần đã duyệt nên dừng.

## Cập nhật (người dùng duyệt nâng trần tổng 0,70 USD)
- Sửa nhận nhầm người nói: `script_parser._characters` giờ dùng `dialogue._is_speaker` ("Cận mặt Kelly:" không còn là người nói); thêm "HẬU KỲ", "ĐIỂM XOAY", "HOOK" vào `NOT_SPEAKERS`. Test `MetaLabelTests` đỏ→xanh.
- Prompt 23 KHÔNG đổi (giữ sha pin S14.21); lời khuyên "gộp nhịp liền cùng nơi thành cảnh dài hơn" và "nhãn kỹ thuật ngoài mô tả cảnh" nằm trong `knowledge/craft/kelly_bien_kich.md` (mục "Cách viết thành cảnh", giọng gợi ý, chỉ có tác dụng khi bật `kelly_knowledge`).
- Ý 3 chạy riêng: `runs/20261005-191710` (0,214 USD; tổng 0,635 / 0,70). Replay 0 miss. Sổ chi `usage_events` dự án #18 đã ghi tự động (8 dòng cho lần này). Ý 1–2 vẫn là bản ghi trước bản sửa (ghi rõ trong phiếu).
- Quan sát: dù có lời khuyên gộp cảnh, Biên kịch vẫn viết 5 cảnh cùng nơi cho ý 3 (nó bám 5 nhịp của dàn ý ở lượt 3). Muốn gộp thật cần chỉnh lượt 3/4 của prompt 23 (đổi sha pin có chủ ý) hoặc gộp bằng code sau lượt viết.

## Việc mở (đã làm: 2 lỗi nhỏ đầu tiên và chạy ý 3)
- Chạy ý 3 (khuôn D) cần người dùng duyệt thêm ~0,22 USD: `py tools/experiments/idea_script_eval.py --db D:/AI-Video-Pipeline/data/manifest.sqlite --ideas <file chỉ ý 3> --kelly --yes --max-usd 0.3`.
- Lỗi nhỏ ở kiểm code Biên kịch: dòng mô tả bắt đầu bằng "Cận mặt Kelly:" / "Hậu kỳ:" / "Điểm xoay:" bị nhận nhầm là người nói -> cờ "nhân vật mới — cần ảnh" sai (ý 1: 3 cờ, ý 2: 1 cờ). Nên sửa `_said` / bộ tách người nói.
- Biên kịch chia mỗi nhịp thành 1 CẢNH cùng nơi (5 cảnh x 3 s cho clip 15 s); nhãn meta ("Điểm xoay:") lọt vào mô tả cảnh. Cân nhắc prompt 23.
- Kho thiếu cho định dạng Kelly: nơi đời thường (văn phòng, canteen, bếp, lớp học, hành lang, phòng chờ); chim cánh cụt kính đen (pet) và đồ vật 3D (đĩa gà, cốc…); module HUD hoạt hình hậu kỳ (thanh máu/tên/đầu lâu, bảng kill, icon hạng); ý 3 dùng ALVARO + Khu Dân Cư (cổng 0 USD đã qua nhưng chưa chạy thật).
- Trần ký tự nhóm Director khi bật cả `kelly_knowledge`+`murch_knowledge`+`film_crew`: 145 735 / 150 000 (còn 4,3 nghìn): gần trần.
