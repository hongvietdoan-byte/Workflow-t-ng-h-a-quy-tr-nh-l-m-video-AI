"""Kho (người dùng 29/09): ảnh của Tháp Đồng Hồ #263 và Cổng Trời #265 = TOÀN BỘ ảnh render từ file 3D chính thức; ảnh cũ vào backup.
#84 "Khu vực - Cổng Trời mới" (cùng nơi, ảnh gốc từ Drive) gộp vào #265: ảnh sao lưu, tên thành tên gọi khác, mục bị gỡ; thư mục Drive của
nó vào danh sách bỏ qua của nguồn đồng bộ (không tạo lại mục trùng)."""
import json
import os
import shutil
import sys

sys.path.insert(0, os.getcwd())
from core import assets  # noqa: E402
from core.db import connect  # noqa: E402

DB = r"D:\AI-Video-Pipeline\data\manifest.sqlite"
T = r"D:\AI-Video-Output\2026-09-29_bo-boi-canh-thap-chinh-thuc"
C = r"D:\AI-Video-Output\2026-09-29_bo-boi-canh-cong-troi"
BACKUP = r"D:\AI-Video-Pipeline\data\backup\kho_anh_cu_2026-09-29"
NOTE = "render 3D Blender 5.0.1 — file 3D chính thức của game (model 3D/Ingame_map_building/…/asset.fbx), 2026-09-29"
NEW = {
    263: (T, [("ngay_eye_plaza_front_thap.png", "low_angle", "quảng trường trước tháp, nhìn lên"),
              ("ngay_eye_level_2_3_thap.png", "eye_level", "đường dưới tường chắn, tháp sau dãy nhà"),
              ("ngay_eye_doi_tay_tram_gac_thap.png", "high_angle", "từ đồi tây nhìn xuống thị trấn và tháp"),
              ("ngay_eye_rang_dua_canh.png", "eye_level", "rặng dừa phía đông"),
              ("ngay_eye_nha_do_nam_canh.png", "eye_level", "dãy nhà mái đỏ phía nam"),
              ("ngay_eye_trong_nha_qt_t2_ra.png", "detail", "trong nhà 3 tầng trên quảng trường, cửa sổ nhìn ra rặng dừa")]),
    265: (C, [("ngay_eye_san_truoc_thap.png", "eye_level", "sân trước biệt thự (cổng tây)"),
              ("ngay_eye_ho_boi_nam_canh.png", "eye_level", "sân hồ bơi phía nam, biệt thự phía sau"),
              ("ngay_eye_me_cung_canh.png", "eye_level", "lối vào mê cung, biệt thự phía sau"),
              ("ngay_eye_duong_doc_tay_canh.png", "low_angle", "đồi thông phía tây, biệt thự trên cao"),
              ("ngay_eye_bien_qc_canh.png", "detail", "biển quảng cáo lớn"),
              ("ngay_eye_trong_bt_t1_trong.png", "detail", "trong biệt thự — sảnh tầng 1")]),
}
c = connect(DB)
for aid, (folder, items) in NEW.items():
    for name, _, _ in items:
        assert os.path.exists(os.path.join(folder, name)), name
log = []


def backup_and_remove(aid):
    dest = os.path.join(BACKUP, str(aid))
    os.makedirs(dest, exist_ok=True)
    for r in c.execute("SELECT * FROM asset_images WHERE asset_id=?", (aid,)).fetchall():
        src = assets.resolve(r["path"])
        if src and os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, f"{r['id']}_{os.path.basename(src)}"))
        log.append({k: r[k] for k in r.keys()})
        assets.remove_image(c, r["id"])


for aid in (263, 265, 84):
    backup_and_remove(aid)
with open(os.path.join(BACKUP, "asset_images_da_go.json"), "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=1)
print("sao lưu + gỡ", len(log), "ảnh cũ ->", BACKUP)

# #84 -> #265: tên thành tên gọi khác, liên kết dự án (nếu có) chuyển, mục bị gỡ (ảnh đã gỡ ở trên)
row84 = c.execute("SELECT * FROM assets WHERE id=84").fetchone()
if row84 is not None:
    with open(os.path.join(BACKUP, "asset_84.json"), "w", encoding="utf-8") as f:
        json.dump({k: row84[k] for k in row84.keys()}, f, ensure_ascii=False, indent=1)
    moved = assets.merge(c, 84, 265)
    print("gộp #84 vào #265, ảnh chuyển:", moved)

for aid, (folder, items) in NEW.items():
    for name, role, label in items:
        with open(os.path.join(folder, name), "rb") as fh:
            assets.add_image(c, aid, f"3d_{name}", fh.read(), status="approved", role=role, look="ingame", variant=f"{NOTE}; {label}")
    print(aid, [(r["id"], r["role"], r["status"]) for r in c.execute("SELECT id, role, status FROM asset_images WHERE asset_id=?", (aid,))])
print("aliases #265:", c.execute("SELECT aliases FROM assets WHERE id=265").fetchone()[0])

src = c.execute("SELECT id, ignore FROM asset_sources WHERE path LIKE '%in-game all map image%'").fetchone()
if src is not None and "cong troi moi" not in (src["ignore"] or ""):
    c.execute("UPDATE asset_sources SET ignore=? WHERE id=?", ((src["ignore"] or "") + ", cong troi moi", src["id"]))
    c.commit()
print("nguồn Drive bỏ qua:", c.execute("SELECT ignore FROM asset_sources WHERE id=?", (src["id"],)).fetchone()[0] if src else None)
