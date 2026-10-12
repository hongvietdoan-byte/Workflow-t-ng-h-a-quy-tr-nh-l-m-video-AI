# Tự rà Đ16 việc 2 — khóa đạo cụ (chờ rà độc lập CLAUDE.md §7)

| Phương án (b) | Tần suất × lợi ích | Công sức / rủi ro | Kết luận |
|---|---|---|---|
| Nhập tỉ lệ từng món | Mọi shot súng; đúng riêng từng món | Thấp; cần nhập Kho | Đề xuất tối thiểu ban đầu |
| Suy theo SMG/rifle/pistol | Mọi shot súng; đỡ nhập, chữa lỗi SKORP nhỏ như pistol | Vừa; loại súng đa dạng, không được coi ước lượng là đo | Người dùng đã chốt qua root: **Tự suy theo loại súng** |

## Phạm vi và chứng cứ
- Base `d932f1d1`, nhánh `codex/d16-viec2-khoa-dao-cu`; chưa commit/push.
- `core/runner.py:2134–2139` sửa tối thiểu vì builder gửi nguyên cụm mâu thuẫn; làm sạch riêng action/fix, giữ trả realism_removed cũ.
- Không ghi scene/Kho; da skin nguyên; cờ OFF so prompt từng byte; loại chưa rõ/mâu thuẫn báo VÀNG.
- Scale ưu tiên nhãn `Tỉ lệ:`/`Scale:` trong trường hồ sơ sẵn có rồi mô tả; tiếp theo kích thước đo Kho; cuối cùng heuristic SMG/rifle/pistol/shotgun có chữ Estimated/not measured.
- Nhận loại theo cụm nguyên từ có dấu, bỏ nhắc phủ định đơn giản (`not a pistol`, `không phải súng lục`); không suy bare gun.
- Dashboard trong nội dung kịch bản ảnh/video hiện các cụm đã bỏ; không thêm nút/widget hoặc đổi key.
- Đỏ (a): 3 hỏng/13 qua; lượt kế tiếp (a) xanh nhưng (b) mới 3 hỏng/16 qua.
- Xanh cuối: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_prop_lock.py tests/test_director_prompt_formula.py tests/test_looks.py tests/test_prompt_assembly_f1b.py` → **56 qua**, 5,47 s.
- Một lệnh trước xanh gõ nhầm `tests/test_ff_looks.py` → pytest không thu thập/chạy test; đã sửa đúng `test_looks.py`.
- `git diff --check` sạch; `related_areas` chỉ ra assets/autopilot/budget/dashboard/cờ; test chậm UI bắt buộc ở bước gộp.
- Không mã Python mới nên không cần khai areas; giữ version. Không API, data thật, secrets, main/live.

## Tự kiểm 2b.5 / giới hạn
- Không đường dẫn mới; không sandbox/network mới; không gọi tốn tiền; cờ hiện có giữ mặc định.
- Builder chung nhận cả bấm tay/autopilot/bulk/khung cuối; không đổi vòng đời job/sổ chi.
- Vệ sinh cụm tính từ sát món và cấu trúc `is/made of/of/là/bằng` kết thúc mệnh đề; không xóa qua vật bên cạnh hoặc generic khi nhiều món.
- Đã kiểm source không đổi, skin/OFF/ranh mệnh đề/nhiều props/metadata ưu tiên/loại phủ định/cảnh không có món.
- Chưa thử model thật (cấm tiền), chưa QA màn hình 1440/1280 (caption đơn giản), chưa cả bộ Windows; root sẽ rà độc lập trước commit.

## Vòng sửa sau rà độc lập
- Đã gom 6 finding trong RA_D16_VIEC2_CODEX_2026-10-12.md: thuộc tính song ngữ/partial, noun head, decimal, selected form, heuristic size-only.
- Đỏ 6 test_review_* (0,76 s) → xanh focused 6 (0,62 s); nhóm 4 file cuối 62 qua (4,53 s), diff --check sạch.
- Caption preview “sẽ bỏ”; mô tả metadata người nhập có thể giữ pose, AUTO không tự ép pose. Chưa model thật/GUI/cả bộ Windows; root đọc diff trước commit.
