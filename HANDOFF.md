# Bàn giao — nhánh `a18-sua-bao-nham` (10/10, 0 USD)

Nền: `origin/nhan-a18-agent` + merge `origin/main` 6ff54cd (quyết định A26).

## Đã làm
- **A26 (b)** — `core/identity_declare.py` sửa 5 kiểu báo nhầm (mỗi kiểu một test đỏ→xanh, `tests/test_identity_declare.py::test_a26_*`):
  1. ống tay áo ≠ bàn tay (`SLEEVE_VI`, `_mask_sleeve`) + tách câu '. ' trong mô tả Kho;
  2. câu nhóm (`GROUP_RE`: both / each / two … characters / all … / they; loại 'both hands', 'each other') → mọi nhân vật trong khung (`segment`);
  3. vị ngữ 'face is a … pure-black mask' (`PREDICATE`, ≤ 6 từ, dừng ở giới từ) + '<món>less' chỉ khi hồ sơ tự ghi ('faceless');
  4. `FRONT_TORSO` (choker, crop top) bỏ khi BYĐ có 'lung' mà không 'mat'; không rõ hướng → `khong_loc` "không rõ hướng";
  5. món `skirt` (váy + mô tả có áo riêng), `prompt_cut` ('no legs' / 'chest up' / 'waist up' → `view['cat_prompt']`), `SMALL_ITEMS` ở WS/EWS.
- **A26 (c)** — `check`: bật `CHAN_DO` chỉ `sai_mau` + món dấu hiệu (khai_bao_chu có dau_hieu) ĐỎ; `thieu`/`thieu_mau` món thường luôn VÀNG. `CHAN_DO = False` giữ nguyên.
- Test cũ đổi theo A26 (c) (3 test) + golden `p24_shot4_*` (choker / crop top → khong_can, đúng mục 19 bảng nhãn).
- Chạy lại `tools/dryrun_k0b_p24.py --project 22|24` + `tools/nhan_bao_nham_a18.py`; nhãn agent mới trong `docs/NHAN_BAO_NHAM_A18_agent.json`
  (khóa cũ giữ), mục "So sánh trước / sau" trong `docs/NHAN_BAO_NHAM_A18_2026-10-10.md`.

## Số
#22 26 → 13, #24 35 → 26 món bị báo. 15/15 báo nhầm cũ hết, 15/15 đúng lỗi cũ còn. Bảng 30: 0 báo nhầm; toàn bộ 39: 6/39 ≈ 15 % (> 10 % A25).

## Còn lại
- Báo nhầm còn: shot biến hình hai dạng cùng khóa 'yeunu' (#24 S7, 4), bị che theo tư thế (#24 S9 dạng 2, 2).
- Người dùng duyệt cột cuối bảng nhãn. Không sửa TODO.md, không đổi version areas.json.
- `identity_declare` chưa nối pipeline thật (chỗ gọi duy nhất ngoài tools: `core/assets.set_profile` → `validate_khai_bao_chu`, không đổi).
