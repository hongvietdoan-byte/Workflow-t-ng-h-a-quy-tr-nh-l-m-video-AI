"""Bảng ý đồ shot (BYĐ) — schema tối thiểu + kiểm hợp lệ (K0a kế hoạch kiểm soát, docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md mục 3.1, N1).

BYĐ = một nguồn ý đồ có cấu trúc cho mỗi shot; mọi lớp kiểm sau này đọc BYĐ (và gói thật), không đọc lại chữ tự do để KẾT LUẬN. BYĐ MỞ RỘNG
`shot_specs` sân khấu 3D V3 (prompts/29_director_stage_specs.md, core/stage_solver.validate): các enum máy / vai / vùng / thấy / tư thế /
chuyển động máy LẤY từ đó (core/stage_grid, core/stage_solver, core/plate_env), không định nghĩa lại khác đi — test giữ khớp.

K0a CHƯA nối vào pipeline (K1a làm: Đạo diễn điền BYĐ, cờ `shot_intent`). Module chỉ có schema + `validate`.

Nhóm (mục 3.1): truyen · thanh_phan (ai trong khung) · hanh_dong · vat · may · noi_chon · ngoai_le (có chủ đích) · am_chu.
Một lỗi (issue) = {"muc": "do" | "vang", "truong": "may.co", "loi": "…"}: "do" = sai schema (chặn khi nối ở K1a), "vang" = không kiểm được.
"""
from typing import Dict, List, Optional

from core import plate_env
from core import stage_grid as sg
from core import stage_solver

# ---- enum tái dùng (một nguồn) -------------------------------------------------------------------------------------------------
CO = tuple(sg.FRAMING)                          # EWS, WS, GAME_TPS, MLS, MS, MCU, CU, ECU — prompt 29 dòng 66
DO_CAO = ("ngang", "thap", "cao", "tren_dau")   # prompt 29 dòng 66; stage_solver.validate nhận đúng các giá trị này (test giữ khớp)
GOC = sg.GOC                                    # ngang, cui, ngua
VAI = sg.ROLES                                  # chinh, phu, khong_duoc_co
THAY = sg.VIEWS                                 # mat, lung, nghieng (ghép "|")
TU_THE = ("dung", "ngoi", "quy", "bo", "nga_ngua", "nam")   # prompt 29 dòng 11–13 (đứng / ngồi bệt / quỳ / bò / ngã ngửa chống tay / nằm)
#   — beats[nhip][khoa].tu_the. K0b phần 2: thêm nga_ngua (#24 shot 4 job 635 ra NGỒI thẳng thay vì ngã ngửa — enum cũ không phân biệt), nam.
#   'nga_ngua', 'nam' CHỈ dùng chạy khô / BYĐ tới khi solver đo thân nằm (K1a/K3): prompt 29 (đang chạy) chưa liệt kê — stage_solver coi
#   người nộm là trụ đứng cao H, thân nằm dài theo phương ngang sẽ bị khung cắt.
CHUYEN_DONG = ("dung_yen",) + tuple(stage_solver.MOVES)   # dung_yen + lui / tien (prompt 29 dòng 31 "may.kieu"); đẩy/kéo/lia: K3
THOI_GIAN = plate_env.TIMES                     # dawn, day, dusk, night
THOI_TIET = plate_env.WEATHERS
# ---- enum mới của BYĐ (chưa có ở đâu trong code) ------------------------------------------------------------------------------
CHAM_DAT = ("ban_chan", "dau_goi", "mong", "ban_tay", "lung", "hong", "bung")   # bộ phận chạm đất
NGOAI_LE_LY_DO = ("ky_nang", "hieu_ung_game", "phong_cach")                        # mục 3.1 / A8
NHIP_HD = ("bat_dau", "dinh", "ket_thuc")

GROUPS = ("truyen", "thanh_phan", "hanh_dong", "vat", "may", "noi_chon", "ngoai_le", "am_chu")
REQUIRED = ("shot", "thanh_phan", "may", "noi_chon")
# Trường chữ chỉ để HIỂU Ý (như `muc_dich` của shot_specs) — không lớp kiểm nào được kết luận từ chúng (N1).
TEXT_ONLY = ("truyen.muc_dich", "truyen.cam_xuc", "ngoai_le[].dieu_trai", "ngoai_le[].cach_hien")


def empty(shot: int) -> Dict:
    """Khung BYĐ rỗng của một shot (mọi nhóm có mặt)."""
    return {"shot": shot, "truyen": {"nhip": None, "muc_dich": "", "cam_xuc": ""}, "thanh_phan": [], "hanh_dong": [], "vat": [],
            "may": {"co": None, "do_cao": "ngang", "goc": None, "chuyen_dong": "dung_yen"},
            "noi_chon": {"kho_id": None, "spot": None, "thoi_gian": None, "thoi_tiet": None, "anh_sang": None},
            "ngoai_le": [], "am_chu": {"thoai": [], "nhac": None, "sfx": [], "popup": None, "phu_de": None}}


def _issue(muc: str, truong: str, loi: str) -> Dict:
    return {"muc": muc, "truong": truong, "loi": loi}


def _enum(out: List[Dict], truong: str, value, allowed, required: bool = False) -> None:
    if value in (None, ""):
        if required:
            out.append(_issue("do", truong, f"thiếu (một trong {', '.join(allowed)})"))
        return
    if value not in allowed and sg.fold(value).replace(" ", "_") not in allowed:
        out.append(_issue("do", truong, f"'{value}' không hợp lệ (một trong {', '.join(allowed)})"))


def _check_may(may, out: List[Dict]) -> None:
    if not isinstance(may, dict):
        out.append(_issue("do", "may", "phải là bảng {co, do_cao, goc, chuyen_dong}"))
        return
    _enum(out, "may.co", may.get("co"), CO, required=True)
    _enum(out, "may.do_cao", may.get("do_cao"), DO_CAO)
    _enum(out, "may.goc", may.get("goc"), GOC)
    cd = may.get("chuyen_dong")
    if isinstance(cd, dict):                                  # {"kieu": "lui"|"tien", "m": 0.5–2, "rung": …} — y như shot_specs.may
        for e in stage_solver.move_errors(cd):
            out.append(_issue("do", "may.chuyen_dong", e))
    else:
        _enum(out, "may.chuyen_dong", cd, CHUYEN_DONG)


def _check_thanh_phan(items, out: List[Dict]) -> None:
    if not isinstance(items, list) or not items:
        out.append(_issue("do", "thanh_phan", "phải có ít nhất một thứ trong khung"))
        return
    if not any(isinstance(c, dict) and c.get("vai") == "chinh" for c in items):
        out.append(_issue("do", "thanh_phan", "không có thứ 'chinh' nào (stage_solver.validate cũng đòi)"))
    for i, c in enumerate(items):
        t = f"thanh_phan[{i}]"
        if not isinstance(c, dict) or not c.get("vat"):
            out.append(_issue("do", t, "thiếu 'vat' (khóa vật / người trên sân khấu)"))
            continue
        _enum(out, f"{t}.vai", c.get("vai"), VAI, required=True)
        try:
            sg.parse_zone(c.get("vung"))
        except ValueError as e:
            out.append(_issue("do", f"{t}.vung", str(e)))
        for v in str(c.get("thay") or "").split("|"):
            if v.strip():
                _enum(out, f"{t}.thay", v.strip(), THAY)


def _check_hanh_dong(items, names: set, out: List[Dict]) -> None:
    for i, h in enumerate(items or []):
        t = f"hanh_dong[{i}]"
        if not isinstance(h, dict) or not h.get("ai"):
            out.append(_issue("do", t, "thiếu 'ai'"))
            continue
        if names and h["ai"] not in names:
            out.append(_issue("do", f"{t}.ai", f"'{h['ai']}' không có trong thanh_phan"))
        for nhip in NHIP_HD:
            st = h.get(nhip)
            if st is None:
                continue
            if not isinstance(st, dict):
                out.append(_issue("do", f"{t}.{nhip}", "phải là bảng {tu_the, cham_dat, nhin}"))
                continue
            _enum(out, f"{t}.{nhip}.tu_the", st.get("tu_the"), TU_THE, required=True)
            for b in st.get("cham_dat") or []:
                _enum(out, f"{t}.{nhip}.cham_dat", b, CHAM_DAT)
        if h.get("bat_dau") is None:
            out.append(_issue("do", f"{t}.bat_dau", "thiếu trạng thái đầu"))


def _check_ngoai_le(items, out: List[Dict]) -> None:
    for i, n in enumerate(items or []):
        t = f"ngoai_le[{i}]"
        if not isinstance(n, dict):
            out.append(_issue("do", t, "phải là bảng"))
            continue
        for k in ("doi_tuong", "dieu_trai", "cach_hien"):
            if not str(n.get(k) or "").strip():
                out.append(_issue("do", f"{t}.{k}", "thiếu"))
        _enum(out, f"{t}.ly_do", n.get("ly_do"), NGOAI_LE_LY_DO, required=True)
        if not isinstance(n.get("pham_vi"), list) or not n.get("pham_vi"):
            out.append(_issue("do", f"{t}.pham_vi", "phải là danh sách shot (≥ 1)"))


def _kho_ids(byd: Dict) -> List[tuple]:
    out = []
    nc = byd.get("noi_chon") or {}
    if nc.get("kho_id") is not None:
        out.append(("noi_chon.kho_id", nc["kho_id"]))
    for key in ("thanh_phan", "vat"):
        for i, c in enumerate(byd.get(key) or []):
            if isinstance(c, dict) and c.get("kho_id") is not None:
                out.append((f"{key}[{i}].kho_id", c["kho_id"]))
    return out


def validate(byd: Dict, conn=None) -> List[Dict]:
    """Lỗi schema của một BYĐ (rỗng = hợp lệ). Có `conn` → mã Kho (`kho_id`) phải có thật trong bảng assets.
    Không có `conn` mà có mã Kho → một mục VÀNG (không im lặng: chưa kiểm được)."""
    out: List[Dict] = []
    if not isinstance(byd, dict):
        return [_issue("do", "", "BYĐ phải là bảng")]
    for k in REQUIRED:
        if k not in byd:
            out.append(_issue("do", k, "thiếu trường bắt buộc"))
    for k in byd:
        if k not in GROUPS and k not in ("shot", "ca_vang_tay"):
            out.append(_issue("do", k, f"trường lạ (nhóm hợp lệ: {', '.join(GROUPS)})"))
    if "shot" in byd and not isinstance(byd["shot"], int):
        out.append(_issue("do", "shot", "phải là số shot"))
    if "thanh_phan" in byd:
        _check_thanh_phan(byd["thanh_phan"], out)
    if "may" in byd:
        _check_may(byd["may"], out)
    names = {c.get("vat") for c in byd.get("thanh_phan") or [] if isinstance(c, dict)}
    _check_hanh_dong(byd.get("hanh_dong"), names, out)
    nc = byd.get("noi_chon")
    if "noi_chon" in byd:
        if not isinstance(nc, dict):
            out.append(_issue("do", "noi_chon", "phải là bảng"))
        else:
            if nc.get("kho_id") is None:
                out.append(_issue("do", "noi_chon.kho_id", "thiếu mã Kho bối cảnh"))
            _enum(out, "noi_chon.thoi_gian", nc.get("thoi_gian"), THOI_GIAN)
            _enum(out, "noi_chon.thoi_tiet", nc.get("thoi_tiet"), THOI_TIET)
    _check_ngoai_le(byd.get("ngoai_le"), out)
    ids = _kho_ids(byd)
    if ids and conn is None:
        out.append(_issue("vang", "kho_id", "chưa kiểm mã Kho (không có kết nối CSDL)"))
    elif ids:
        for truong, kid in ids:
            try:
                row = conn.execute("SELECT 1 FROM assets WHERE id=?", (int(kid),)).fetchone()
            except (TypeError, ValueError):
                row = None
            if not row:
                out.append(_issue("do", truong, f"mã Kho {kid} không có trong Kho"))
    return out


def from_shot_spec(spec: Dict, blocking: Optional[Dict] = None) -> Dict:
    """Một mục `shot_specs` V3 → BYĐ (phần máy + thành phần); dùng cho ca hồi quy và K1a.
    Có `blocking` (dàn cảnh prompt 29: objects + beats[nhip][khoa]) → tư thế của NHỊP shot chuyển vào `hanh_dong`: mỗi người
    (`kind: nguoi`) có trong thanh_phan (trừ `khong_duoc_co`) → {ai, bat_dau: {tu_the}, nguon}. `nguon` = "blocking.beats.<nhip>" (ghi ở
    nhịp) / "blocking.objects" (ghi ở vật gốc) / "mac_dinh_dung" (không ai ghi → đứng, mặc định người nộm prompt 29 — đánh dấu để duyệt).
    Một nhịp = một tư thế: `dinh` / `ket_thuc` để trống (shot_specs không tả đổi tư thế trong shot). Nhịp không có trong blocking →
    ValueError (stage_solver.beat_raw), không im lặng bỏ. Không có blocking → hanh_dong rỗng (không bịa)."""
    b = empty(int(spec.get("shot") or 0))
    b["truyen"].update(nhip=spec.get("nhip"), muc_dich=spec.get("muc_dich") or "")
    b["thanh_phan"] = [dict(c) for c in spec.get("thanh_phan") or []]
    b["may"].update(co=spec.get("co"), do_cao=spec.get("do_cao") or "ngang", goc=spec.get("goc"),
                    chuyen_dong=spec.get("may") or "dung_yen")
    if blocking:
        nhip = spec.get("nhip")
        raw = stage_solver.beat_raw(blocking, nhip) if nhip else stage_solver.beat_raw(blocking)
        base = {o.get("key"): o for o in blocking.get("objects") or []}
        ov_all = ((blocking.get("beats") or {}).get(nhip) or {}) if nhip else {}
        for c in b["thanh_phan"]:
            k = c.get("vat")
            o = raw.get(k)
            if c.get("vai") == "khong_duoc_co" or not o or o.get("kind") != "nguoi":
                continue
            if (ov_all.get(k) or {}).get("tu_the"):
                tu_the, nguon = ov_all[k]["tu_the"], f"blocking.beats.{nhip}"
            elif (base.get(k) or {}).get("tu_the"):
                tu_the, nguon = base[k]["tu_the"], "blocking.objects"
            elif float(o.get("H") or 0) < 0.9 * float((base.get(k) or {}).get("H") or 0):
                tu_the, nguon = None, "thieu_tu_the"          # thấp hơn đứng mà không ghi tư thế → validate ĐỎ 'thiếu', không đoán
            else:
                tu_the, nguon = "dung", "mac_dinh_dung"
            b["hanh_dong"].append({"ai": k, "bat_dau": {"tu_the": tu_the}, "nguon": nguon})
    return b
