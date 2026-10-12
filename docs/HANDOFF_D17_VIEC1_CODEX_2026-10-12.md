# Bàn giao Đ17v1 c/d
- Nhánh codex/d17-viec1-dao-cu, base a03afe67; chưa commit/push phần c/d.
- c súng khóa thay đúng slot nền rộng hợp lệ, giữ count/protected refs/modelcap.
- d POV VÀNG vẫn chạy; bỏ gun lock/named refs/sharedgun; giữ nongun/cast.
- 90 passed +23 subtests /7,70s; 3 lượt ĐỎ→XANH, diff check xanh.
- Sửa core/prop_lock.py, core/assets.py, core/runner.py, tests/test_prop_lock.py + RA.
- Dùng chung same asset/variant đã có; không build collage.
- Bước kế root rà độc lập + QA Dashboard; xem RA đầy đủ.
- Không API/data/main/TODO/PLAN/admin_auth/version/widgets.
- Rà độc lập c/d bắt 1 P2 (OTS phủ định che POV): đã sửa helper chung, đỏ 4 subtest→xanh; nhóm cuối 91 passed +30 subtests/7,80s, diff check xanh. Root đọc diff sửa; chưa commit/push.
