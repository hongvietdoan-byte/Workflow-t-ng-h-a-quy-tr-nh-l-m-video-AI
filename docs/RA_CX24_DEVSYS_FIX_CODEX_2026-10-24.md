# CX24-DEVSYS-FIX — Codex 1 (24/10/2026)

## Phạm vi và gốc lỗi

- Nền `a113af44`, nhánh `codex/v31-devsys-fix`.
- Test được giao hỏng sẵn: `tests/test_devsys_pipeline_maps.py::test_devsys_page_renders_four_tabs_and_three_maps`.
- Lượt tái hiện ban đầu: **1 đỏ / 12,41 giây**. Chẩn đoán đã lọc cho thấy `ValueError: list.index(x): x not in list` từ lựa chọn radio theo chỉ số toàn trang.
- Thêm kiểm `at.exception` ngay lần mở đầu giúp lộ lỗi production phía dưới: `devsys.collect._features_rule()` nạp `core/features.py` dưới tên module rời. Khi luật baseline gọi `_paid()`, `from . import before_run` không có package cha và làm trang lỗi `ImportError: attempted relative import with no known parent package`.
- Không chỉ sửa assertion để bỏ qua lỗi: sửa loader nạp module trong namespace package riêng theo root của repo được đo. Relative import tiếp tục đọc đúng `<root>/core`, không mượn `core` của repo chạy Dev System. Sau rà độc lập, namespace có UUID riêng từng snapshot, không purge namespace đang được snapshot khác dùng; dependency được nạp từ source thay vì bytecode cache.
- Test chọn radio `Trang` trong sidebar, kiểm không có exception trước/sau chuyển trang; giữ nguyên yêu cầu đúng **4 tab + 3 SVG + lịch sử được ghi**.

## Bằng chứng đỏ → xanh

1. Test trang gốc: **1 đỏ / 12,41 giây**.
2. Lượt chẩn đoán sau kiểm exception đầu trang: **45 qua, 1 đỏ / 22,80 giây**, lộ relative import hỏng thật.
3. Hai regression repo giả (relative import đúng repo; sửa dependency rồi dựng snapshot lại): **2 đỏ / 0,30 giây** trước sửa loader.
4. Sau sửa, gom ba file `test_devsys_pipeline_maps.py`, `test_devsys_doi_soat.py`, `test_devsys_f1.py`: **78 qua / 48,20 giây**, gồm AppTest thực thi trang trên Windows.

Mọi lượt pytest dùng Python 3.14 trên Windows, `--tb=no -p no:cacheprovider`; thay OBJECT `os.environ` bằng dict giả trước import pytest/target. Test trang cũng tự cách ly môi trường/DB và ghi lịch sử vào thư mục tạm. Không đọc lại khóa hay dump môi trường, không gọi provider/API. Một lượt công cụ chẩn đoán độc lập ngoài pytest đã xác nhận cùng ImportError trong môi trường giả; không có dữ liệu thật trong traceback.

## Rà khâu và giới hạn

- `related_areas.py devsys/collect.py tests/test_devsys_pipeline_maps.py`: khu vực devsys, không có caller khu vực khác; các file hiện hữu đã đăng ký trong areas, giữ nguyên version nền.
- Tự rà: giữ nguyên widget key, không đổi cờ/giá/đường ghi pipeline; không sửa `admin_auth.py` hay dữ liệu thật; loader vẫn dùng đúng repo được đo và fallback AST nếu file không có hàm `on()`.
- Rà độc lập hẹp namespace/cache/cross-root đã phát hiện hai P2 và sửa theo mục dưới; chờ root đọc diff sửa lần hai trước bàn giao.
- Chưa chạy cả bộ; bên gộp chạy bộ kiểm phù hợp, gồm test chậm devsys/hộp thư do related_areas yêu cầu.
- **Trang có lỗi code thật**, nên sau gộp phiên chính cần khởi động lại **8502** và kiểm health cả 8501/8502. Codex 1 không restart/pull/check out thư mục live.
- Chưa nghiệm thu trên tiến trình live 8502; bằng chứng là AppTest chạy code thực trong worktree + repo/DB giả.
- Không có server hay subprocess test còn chạy sau lượt kiểm; không xóa asset.

## Vòng rà độc lập — namespace và cache

- **P2 đồng thời:** namespace chỉ theo root rồi purge `sys.modules` khiến hai lần collect cùng root có thể xóa module đang import của nhau. Đã đổi sang namespace UUID từng snapshot; closure giữ package riêng, cleanup namespace/finder bằng `weakref.finalize` khi rule hết được dùng. Không khóa chờ xuyên module import và không sửa namespace `core` của ứng dụng.
- **P2 bytecode cũ:** purge `sys.modules` vẫn dùng `.pyc` cũ nếu source đổi cùng kích thước/mtime. Loader namespace đo đọc source trực tiếp cho features và relative dependencies; không đọc/ghi/xóa bytecode cache của repo. Finder chỉ nhận prefix namespace riêng, không thay loader module khác.
- Hai regression mới: barrier hai thread giữ import snapshot thứ nhất trong lúc snapshot thứ hai nạp; và đổi dependency `fixture_paid` → `fixture_free` cùng kích thước/mtime, đồng thời giữ rule cũ không bị thay dependency.
- **ĐỎ trước sửa:** 2 fail, 38 deselected / **10,65 giây**. **XANH sau sửa:** 5 pass, 35 deselected / **13,05 giây**, gồm bốn regression loader và AppTest trang thực. Không nới assertion; chỉ chạy nhóm liên quan, không chạy lại cả bộ.
- Native Python được spawn với whitelist môi trường và HOME/TEMP giả; thay OBJECT `os.environ` bằng dict giả trước import pytest/target; `--tb=no`, không dump môi trường hay đọc dữ liệu/provider thật.
