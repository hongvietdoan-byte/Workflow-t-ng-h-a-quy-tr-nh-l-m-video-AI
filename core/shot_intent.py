"""Bảng ý đồ shot (BYĐ) — schema tối thiểu + kiểm hợp lệ (K0a kế hoạch kiểm soát, docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md mục 3.1, N1).

BYĐ = một nguồn ý đồ có cấu trúc cho mỗi shot; mọi lớp kiểm sau này đọc BYĐ (và gói thật), không đọc lại chữ tự do để KẾT LUẬN. BYĐ MỞ RỘNG
`shot_specs` sân khấu 3D V3 (prompts/29_director_stage_specs.md, core/stage_solver.validate): các enum máy / vai / vùng / thấy / tư thế /
chuyển động máy LẤY từ đó (core/stage_grid, core/stage_solver, core/plate_env), không định nghĩa lại khác đi — test giữ khớp.

K0a CHƯA nối vào pipeline (K1a làm: Đạo diễn điền BYĐ, cờ `shot_intent`). Module chỉ có schema + `validate`.

Nhóm (mục 3.1): truyen · thanh_phan (ai trong khung) · hanh_dong · vat · may · noi_chon · ngoai_le (có chủ đích) · am_chu.
Một lỗi (issue) = {"muc": "do" | "vang", "truong": "may.co", "loi": "…"}: "do" = sai schema (chặn khi nối ở K1a), "vang" = không kiểm được.
"""
import copy
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
#   Người nộm tools/stage_grid.py đã dựng thân nằm cùng bao hình với solver (Đợt 2).
CHUYEN_DONG = ("dung_yen",) + tuple(stage_solver.MOVES)   # dung_yen + lui / tien (prompt 29 dòng 31 "may.kieu"); đẩy/kéo/lia: K3
THOI_GIAN = plate_env.TIMES                     # dawn, day, dusk, night
THOI_TIET = plate_env.WEATHERS


def sync_noi_chon(data: Dict) -> bool:
    """17/10 (#31 shot 27–30): the shot's `time` / `weather` are the ONE source (data/decisions.json time-weather-single-source-2026-10-17);
    byd.noi_chon.thoi_gian / thoi_tiet are their copy. Copies them in place (time words normalised by plate_env.time_of, e.g. 'đêm' →
    night; a weather outside plate_env.WEATHERS is left alone, like the plate does). The database trigger trg_scene_noi_chon does the
    same for every write of canonical values. True when something changed."""
    byd = data.get("byd") if isinstance(data, dict) else None
    nc = byd.get("noi_chon") if isinstance(byd, dict) else None
    if not isinstance(nc, dict):
        return False
    changed = False
    if str(data.get("time_of_day") or data.get("time") or "").strip():
        t = plate_env.time_of(data)
        if nc.get("thoi_gian") != t:
            nc["thoi_gian"], changed = t, True
    if str(data.get("weather") or "").strip():
        w, problem = plate_env.weather_of(data)
        if problem is None and nc.get("thoi_tiet") != w:
            nc["thoi_tiet"], changed = w, True
    return changed
# ---- enum mới của BYĐ (chưa có ở đâu trong code) ------------------------------------------------------------------------------
CHAM_DAT = ("ban_chan", "dau_goi", "mong", "ban_tay", "lung", "hong", "bung")   # bộ phận chạm đất
NGOAI_LE_LY_DO = ("ky_nang", "hieu_ung_game", "phong_cach")                        # mục 3.1 / A8
NHIP_HD = ("bat_dau", "dinh", "ket_thuc")
# K1a (ii): vùng thân bị che ở một nhịp (hanh_dong[].<nhip>.che, tùy chọn) — identity_declare.CHE_ITEMS map vùng → món (test giữ khớp).
# Có trường riêng vì tư thế một mình không đủ: cùng 'quy', ôm mặt (#24 S9) thì mặt khuất, quỳ nhìn thẳng thì lộ mặt.
CHE = ("mat", "toc", "co", "than", "eo", "tay", "chan", "ban_chan")

GROUPS = ("truyen", "thanh_phan", "hanh_dong", "vat", "may", "noi_chon", "ngoai_le", "am_chu")
REQUIRED = ("shot", "thanh_phan", "may", "noi_chon")
# Trường chữ chỉ để HIỂU Ý (như `muc_dich` của shot_specs) — không lớp kiểm nào được kết luận từ chúng (N1).
TEXT_ONLY = ("truyen.muc_dich", "truyen.cam_xuc", "ngoai_le[].dieu_trai", "ngoai_le[].cach_hien")

# ---- V3.1 M2.1 (C-M21): BYĐ v2 — docs/V3_1_M2_1_M2_2_THIET_KE_2026-10-20.md mục 2 --------------------------------------------------
# `byd_v: 2` (thiếu = v1) + `vat[]` là bảng {vat, kho_id, nguoi, cach, bien_the} + nhóm `khung.moc_nen` + `noi_chon.trong_nha` (code suy) +
# provenance `_p` {by, model, at, revision; M2.4: draft, from}. v1 kiểm y như cũ; nhóm / khóa v2 trong BYĐ v1 vẫn là "trường lạ". Mức BLOCK / REVIEW / WARN (assess) chỉ GHI (cờ
# byd_v2_levels → director_byd.settle ghi `byd_kiem.muc_v2`), không chặn gen — BLOCK thật = Cấp 3 sau.
BYD_V = 2
V2_GROUPS = ("khung",)
V2_KEYS = ("_p",)
CACH = ("cam", "deo", "dat", "nem")
Y_DO = ("trong_khung", "ngoai_khung")
P_BY = ("director", "human", "backfill", "code")
LEVELS = ("BLOCK", "REVIEW", "WARN")
LEVELS_FLAG = "byd_v2_levels"
PROVENANCE = ("byd_v2", "byd_v1", "suy_tu_spot", "doc_chu", "thieu")   # suy_tu_spot / doc_chu: nơi gọi tự suy khi read() trả "thieu"
V2_ONLY = ("khung", "_p", "noi_chon.trong_nha")


def levels_enabled() -> bool:
    from core import features
    return features.on(LEVELS_FLAG)


def version(byd) -> Optional[int]:
    """2 = BYĐ v2 (`byd_v: 2`), 1 = bảng BYĐ không khai / khai 1, None = không phải bảng (chưa có BYĐ)."""
    if not isinstance(byd, dict):
        return None
    return BYD_V if byd.get("byd_v") == BYD_V else 1


def byd_of(data) -> Optional[Dict]:
    """BYĐ của một shot (`scenes.data` / shot kế hoạch): chính bảng đó (sửa tại chỗ được), không có / sai kiểu → None."""
    byd = data.get("byd") if isinstance(data, dict) else None
    return byd if isinstance(byd, dict) else None


class BydTypeError(ValueError):
    """BYĐ có giá trị nhưng không phải bảng (chuỗi / danh sách — vd câu trả lời sửa của Claude gán thẳng). Mức REVIEW, mã byd_sai_kieu."""
    code = "byd_sai_kieu"
    level = "REVIEW"


def byd_or_raw(data):
    """Cho nơi đọc cũ `(data.get("byd") or {})` (rà M21-1): bảng → bảng; thiếu / rỗng → None; CÓ giá trị mà sai kiểu:
    cờ byd_v2_levels TẮT → trả NGUYÊN giá trị (nơi gọi vỡ AttributeError y main — không đổi hành vi), BẬT → BydTypeError (REVIEW, nói ra).
    Không bao giờ nuốt im lặng như byd_of()."""
    raw = data.get("byd") if isinstance(data, dict) else None
    if isinstance(raw, dict) or not raw:
        return raw or None
    if levels_enabled():
        raise BydTypeError(f"BYĐ sai kiểu ({type(raw).__name__}, cần bảng) — REVIEW byd_sai_kieu: sửa / điền lại BYĐ shot này")
    return raw


def read(data, field: str, default=None):
    """MỘT hàm đọc trường BYĐ (M2.1): (giá trị, provenance, câu cảnh báo | None). `field` = đường chấm ("noi_chon.kho_id", "khung.moc_nen").
    provenance: "byd_v2" / "byd_v1" (có trường), "thieu" (không có BYĐ / thiếu trường — nơi gọi dùng đường cũ: suy / đọc chữ, và nói ra).
    `vat` luôn qua vat_items (chuỗi v1 → {"vat", "_v": 1})."""
    byd = byd_of(data)
    if byd is None:
        return ([] if field == "vat" and default is None else default), "thieu", "shot chưa có BYĐ"
    v = version(byd)
    cur = byd
    for part in field.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
            continue
        if field == "vat":
            return vat_items(byd), "thieu", f"BYĐ v{v} thiếu `vat`"
        why = (f"BYĐ v1 không có `{field}` (trường của v2)" if v == 1 and any(field == k or field.startswith(k + ".") for k in V2_ONLY)
               else f"BYĐ v{v} thiếu `{field}`")
        return default, "thieu", why
    if field == "vat":
        cur = vat_items(byd)
    return cur, "byd_v2" if v == BYD_V else "byd_v1", None


def level_of(issue: Dict) -> str:
    """Ánh xạ tương thích: "do" cũ = BLOCK, "vang" cũ = WARN; mục đã có `level` giữ nguyên."""
    return issue.get("level") or ("BLOCK" if issue.get("muc") == "do" else "WARN")


def assess(byd, conn=None, *, project_id=None) -> List[Dict]:
    """validate() + mức BLOCK / REVIEW / WARN. Kho forms BẬT: kiểm dạng theo dự án;
    TẮT: giữ REVIEW chưa kiểm của M2.1. Mức này chỉ để ghi, không tự chặn gen."""
    out = [dict(i, level=level_of(i)) for i in validate(byd, conn, project_id=project_id)]
    from . import kho_profile
    if version(byd) == BYD_V and not kho_profile.enabled():
        for i, c in enumerate(byd.get("thanh_phan") or []):
            if isinstance(c, dict) and c.get("dang") not in (None, "", [], {}):
                out.append({"muc": "vang", "truong": f"thanh_phan[{i}].dang", "level": "REVIEW",
                            "loi": "dạng chưa kiểm theo forms của mục Kho (M2.3) — người xem"})
    return out


def _check_v2(byd: Dict, names: set, out: List[Dict]) -> None:
    vat = byd.get("vat")
    if vat is not None and not isinstance(vat, list):
        out.append(_issue("do", "vat", "v2: phải là danh sách bảng {vat, kho_id, nguoi, cach}"))
        vat = []
    for i, item in enumerate(vat or []):
        t = f"vat[{i}]"
        if not isinstance(item, dict):
            out.append(_issue("do", t, "v2: mỗi vật là bảng {vat, kho_id, nguoi, cach, bien_the} (chuỗi chỉ hợp lệ ở v1)"))
            continue
        if not str(item.get("vat") or "").strip():
            out.append(_issue("do", f"{t}.vat", "thiếu tên vật"))
        if item.get("kho_id") is None:
            out.append(_issue("do", f"{t}.kho_id", "v2: thiếu mã Kho của vật"))
        _enum(out, f"{t}.cach", item.get("cach"), CACH, required=True)
        if item.get("nguoi") not in (None, "") and item["nguoi"] not in names:
            out.append(_issue("do", f"{t}.nguoi", f"'{item['nguoi']}' không có trong thanh_phan"))
        if item.get("bien_the") not in (None, ""):
            out.append(_issue("vang", f"{t}.bien_the", "bien_the_khong_kiem_duoc: chưa có forms của mục Kho (M2.3)"))
    if "khung" in byd:
        k = byd["khung"]
        if not isinstance(k, dict):
            out.append(_issue("do", "khung", "phải là bảng {moc_nen}"))
        elif "moc_nen" in k:
            m = k["moc_nen"]
            if not isinstance(m, dict):
                out.append(_issue("do", "khung.moc_nen", "phải là bảng {kho_id, y_do, ly_do}"))
            else:
                if m.get("kho_id") is None:
                    out.append(_issue("do", "khung.moc_nen.kho_id", "thiếu mã Kho của mốc nền"))
                _enum(out, "khung.moc_nen.y_do", m.get("y_do"), Y_DO, required=True)
    nc = byd.get("noi_chon")
    if isinstance(nc, dict) and nc.get("trong_nha") not in (None, True, False):
        out.append(_issue("do", "noi_chon.trong_nha", "phải là true / false / null (code suy từ chỗ đứng 3D)"))
    if "_p" in byd:
        p = byd["_p"]
        if not isinstance(p, dict):
            out.append(_issue("do", "_p", "phải là bảng {by, model, at, revision}"))
        else:
            _enum(out, "_p.by", p.get("by"), P_BY, required=True)
            if "draft" in p and not isinstance(p["draft"], bool):            # M2.4: BYĐ nháp của shot chèn (một nguồn provenance)
                out.append(_issue("do", "_p.draft", "phải là true / false (BYĐ nháp do code dựng)"))
            if p.get("from") is not None and (not isinstance(p["from"], int) or isinstance(p["from"], bool)):
                out.append(_issue("do", "_p.from", "phải là mã shot (scene id) BYĐ nháp chép từ"))


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
        if "dang" in c:
            _check_dang(c["dang"], f"{t}.dang", out)


def _dang_ok(v) -> bool:
    return (isinstance(v, str) and bool(v.strip())) or (isinstance(v, list) and bool(v)
                                                        and all(isinstance(x, str) and x.strip() for x in v))


def _check_dang(v, t: str, out: List[Dict]) -> None:
    """K1a (i) `thanh_phan[].dang` (tùy chọn): dạng của nhân vật có mặt — chữ / danh sách chữ / {nhip (NHIP_HD): chữ|danh sách}
    (shot biến hình khai dạng theo nhịp: {"bat_dau": "dang1", "ket_thuc": "dang2"})."""
    if isinstance(v, dict):
        if not v:
            out.append(_issue("do", t, "bảng dạng theo nhịp rỗng"))
        for k, x in v.items():
            if k not in NHIP_HD:
                out.append(_issue("do", f"{t}.{k}", f"nhịp lạ (một trong {', '.join(NHIP_HD)})"))
            elif not _dang_ok(x):
                out.append(_issue("do", f"{t}.{k}", "dạng phải là chữ hoặc danh sách chữ không rỗng"))
    elif not _dang_ok(v):
        out.append(_issue("do", t, "dạng phải là chữ, danh sách chữ hoặc bảng {nhip: dạng}"))


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
            if "che" in st:
                if not isinstance(st["che"], list):
                    out.append(_issue("do", f"{t}.{nhip}.che", "phải là danh sách vùng bị che"))
                else:
                    for b in st["che"]:
                        _enum(out, f"{t}.{nhip}.che", b, CHE)
        if h.get("bat_dau") is None:
            out.append(_issue("do", f"{t}.bat_dau", "thiếu trạng thái đầu"))


def missing_beat(h: Dict) -> Optional[str]:
    """Nhịp còn thiếu của một hanh_dong có ĐỔI tư thế ("dinh" / "ket_thuc"), None = đủ hoặc không đổi — dùng ở lớp kiểm trước gen video
    (core/video_pregen.py). Đổi = một nhịp sau có `tu_the` khác nhịp đầu; ghi nhịp sau cùng tư thế (vd đầu 'dung' + cuối 'dung', #28/#29
    14/10) vẫn là MỘT tư thế, không bắt thêm nhịp đỉnh."""
    if not isinstance(h, dict) or not isinstance(h.get("bat_dau"), dict):
        return None
    later = [n for n in ("dinh", "ket_thuc") if isinstance(h.get(n), dict)]
    if len(later) != 1:
        return None
    start = h["bat_dau"].get("tu_the")
    if h[later[0]].get("tu_the") == start:
        return None
    return "ket_thuc" if later[0] == "dinh" else "dinh"


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


def vat_items(byd) -> List:
    """V3.1 M1.1 (20/10): MỘT cách đọc nhóm `vat` cho mọi nơi dùng. Dữ liệu thật đều là bản v1 — danh sách CHUỖI tên vật (#30 shot 3
    `["BOM_KEO"]`, #31 shot 33 `["AWM"]`); bản v2 là bảng `{vat, kho_id, nguoi, cach, bien_the}`. Chuỗi → `{"vat": <chuỗi>, "_v": 1}`;
    bảng giữ nguyên; một chuỗi đơn (không phải danh sách) → một vật; thiếu / None → []. Phần tử khác (số, bảng thiếu `vat`…) trả NGUYÊN
    để nơi gọi báo lỗi như trước — không âm thầm ép kiểu."""
    raw = byd.get("vat") if isinstance(byd, dict) else None
    if not raw or (isinstance(raw, str) and not raw.strip()):     # như trước (`get('vat') or []`): "", {}, 0, None = không có vật
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return [raw]
    return [{"vat": x, "_v": 1} if isinstance(x, str) and x.strip() else x for x in raw]


def _kho_ids(byd: Dict) -> List[tuple]:
    out = []
    nc = byd.get("noi_chon") or {}
    if nc.get("kho_id") is not None:
        out.append(("noi_chon.kho_id", nc["kho_id"]))
    for key in ("thanh_phan", "vat"):
        for i, c in enumerate(vat_items(byd) if key == "vat" else byd.get(key) or []):
            if isinstance(c, dict) and c.get("kho_id") is not None:
                out.append((f"{key}[{i}].kho_id", c["kho_id"]))
    m = (byd.get("khung") or {}).get("moc_nen") if version(byd) == BYD_V and isinstance(byd.get("khung"), dict) else None
    if isinstance(m, dict) and m.get("kho_id") is not None:          # M2.1: mốc nền v2
        out.append(("khung.moc_nen.kho_id", m["kho_id"]))
    return out


def _check_kho_dang(byd, conn, project_id, out):
    """Chỉ kiểm enum có ngữ cảnh dự án; không sửa BYĐ hay suy dạng từ tên."""
    from . import kho_profile
    if not kho_profile.enabled():
        return
    items = byd.get("thanh_phan")
    if not isinstance(items, list):
        return  # Lỗi cấu trúc đã được validate báo.
    def leaves(value, path):
        if isinstance(value, str) and value.strip():
            yield path, value
        elif isinstance(value, list):
            for j, item in enumerate(value):
                if isinstance(item, str) and item.strip():
                    yield f"{path}[{j}]", item
        elif isinstance(value, dict):
            for beat, item in value.items():
                if beat in NHIP_HD and _dang_ok(item):
                    yield from leaves(item, f"{path}.{beat}")
    for i, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("vat"):
            continue
        for path, dang in leaves(item.get("dang"), f"thanh_phan[{i}].dang"):
            if conn is None or type(project_id) is not int or project_id <= 0:
                issues = [{"muc": "vang", "ma": "dang_khong_kiem_duoc",
                           "loi": "chưa kiểm dạng Kho (thiếu kết nối CSDL hoặc mã dự án)"}]
            else:
                issues = kho_profile.validate_dang(conn, project_id, item["vat"], dang)
            out.extend(dict(issue, truong=path) for issue in issues)


def validate(byd: Dict, conn=None, *, project_id=None) -> List[Dict]:
    """Lỗi schema của một BYĐ (rỗng = hợp lệ). Có `conn` → mã Kho (`kho_id`) phải có thật trong bảng assets.
    Không có `conn` mà có mã Kho → một mục VÀNG (không im lặng: chưa kiểm được)."""
    out: List[Dict] = []
    if not isinstance(byd, dict):
        return [_issue("do", "", "BYĐ phải là bảng")]
    for k in REQUIRED:
        if k not in byd:
            out.append(_issue("do", k, "thiếu trường bắt buộc"))
    v2 = version(byd) == BYD_V
    if "byd_v" in byd and byd["byd_v"] not in (1, BYD_V):
        out.append(_issue("do", "byd_v", f"phiên bản BYĐ lạ ({byd['byd_v']!r}) — 2 hoặc thiếu (= v1)"))
    groups = GROUPS + (V2_GROUPS if v2 else ())
    for k in byd:
        if k not in groups and k not in ("shot", "ca_vang_tay", "byd_v") and not (v2 and k in V2_KEYS):
            out.append(_issue("do", k, f"trường lạ (nhóm hợp lệ: {', '.join(groups)})"))
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
    if v2:
        _check_v2(byd, names, out)
    _check_kho_dang(byd, conn, project_id, out)
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
    ValueError (stage_solver.beat_raw), không im lặng bỏ. Không có blocking → hanh_dong rỗng (không bịa).
    K1a: spec có `hanh_dong` viết tay (vd tư thế + `che` #24 S9) → chép vào trước, nguon "shot_specs"; blocking không ghi đè người đó."""
    b = empty(int(spec.get("shot") or 0))
    b["truyen"].update(nhip=spec.get("nhip"), muc_dich=spec.get("muc_dich") or "")
    b["thanh_phan"] = [dict(c) for c in spec.get("thanh_phan") or []]
    b["may"].update(co=spec.get("co"), do_cao=spec.get("do_cao") or "ngang", goc=spec.get("goc"),
                    chuyen_dong=spec.get("may") or "dung_yen")
    for h in spec.get("hanh_dong") or []:
        if isinstance(h, dict):
            b["hanh_dong"].append(dict(copy.deepcopy(h), nguon=h.get("nguon") or "shot_specs"))
    declared = {h.get("ai") for h in b["hanh_dong"]}
    if blocking:
        nhip = spec.get("nhip")
        raw = stage_solver.beat_raw(blocking, nhip) if nhip else stage_solver.beat_raw(blocking)
        base = {o.get("key"): o for o in blocking.get("objects") or []}
        ov_all = ((blocking.get("beats") or {}).get(nhip) or {}) if nhip else {}
        for c in b["thanh_phan"]:
            k = c.get("vat")
            o = raw.get(k)
            if c.get("vai") == "khong_duoc_co" or not o or o.get("kind") != "nguoi" or k in declared:
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


# ---- V3.1 M2.4 (cờ insert_inherit / stage_props_byd): BYĐ nháp của shot chèn + đổi số + tên vật BYĐ nhắc ---------------------------
def is_draft(byd) -> bool:
    """BYĐ do code dựng nháp (shot chèn chép từ shot trước) — chưa ai duyệt."""
    return isinstance(byd, dict) and isinstance(byd.get("_p"), dict) and byd["_p"].get("draft") is True


def draft_source(byd) -> Optional[int]:
    """Mã shot (scene id) mà BYĐ nháp chép từ — None khi không phải nháp / không ghi nguồn."""
    if not is_draft(byd):
        return None
    src = byd["_p"].get("from")
    return src if isinstance(src, int) and not isinstance(src, bool) else None


def draft_of(data: Dict, shot: int, from_scene_id: int, characters=None, place=None, spot=None) -> Optional[Dict]:
    """BYĐ NHÁP cho shot chèn sau shot `data` (M2.4, G21): giữ `noi_chon`, `thanh_phan` (có `characters` → chỉ giữ thứ có tên trong đó),
    BỎ `hanh_dong` / `may` (shot mới làm việc khác — không đoán) và KHÔNG có khóa `vat` (vật phải khai lại: thiếu khóa = chưa rõ, không
    phải "không cầm gì" — continuity_shadow / continuity_state đọc `"vat" in byd`). `place` / `spot` = location_asset / plate_spot của
    shot mới: khác nơi chốn của shot trước → noi_chon theo shot mới. `_p` = {by: code, draft, from}. Shot trước không có BYĐ → None."""
    src = data.get("byd") if isinstance(data, dict) else None
    if not isinstance(src, dict):
        return None
    parts = [copy.deepcopy(c) for c in src.get("thanh_phan") or [] if isinstance(c, dict)]
    if characters:
        from core.assets import fold
        names = {fold(str(n)).lower() for n in characters}
        parts = [c for c in parts if fold(str(c.get("vat") or "")).lower() in names]
    noi = copy.deepcopy(src.get("noi_chon") or {})
    moved = False
    if place is not None and noi.get("kho_id") not in (None, place):
        noi["kho_id"], moved = place, True
    if spot and noi.get("spot") not in (None, spot):
        noi["spot"], moved = spot, True
    if moved:
        noi.pop("trong_nha", None)                     # code suy từ chỗ đứng 3D cũ — chỗ mới thì suy lại
    return {"byd_v": BYD_V, "shot": shot, "thanh_phan": parts, "noi_chon": noi, "hanh_dong": [], "may": {},
            "_p": {"by": "code", "draft": True, "from": from_scene_id}}            # `_p` M2.1 chỉ hợp lệ ở v2


def _shift_no(v, after_no: int):
    n = v if isinstance(v, int) and not isinstance(v, bool) else (int(v.strip()) if isinstance(v, str) and v.strip().isdigit() else None)
    if n is None or n <= after_no:
        return v
    return n + 1 if isinstance(v, int) else str(n + 1)


def shift_shot(data: Dict, old_no: int, after_no: int) -> bool:
    """Đổi số shot trong BYĐ khi shot_no dời (chèn shot sau shot_no `after_no` của cùng cảnh): `byd.shot` (chỉ khi đúng là số cũ — số khác
    = người / Đạo diễn ghi khác, giữ) và mọi số > after_no trong `ngoai_le[].pham_vi` (lock_exceptions so pham_vi với byd.shot)."""
    byd = data.get("byd") if isinstance(data, dict) else None
    if not isinstance(byd, dict):
        return False
    new = dict(byd)                                    # bản mới: bảng cũ (của `data` trước khi dời) giữ nguyên để so
    if byd.get("shot") == old_no and not isinstance(byd.get("shot"), bool):
        new["shot"] = old_no + 1
    if isinstance(byd.get("ngoai_le"), list):
        new["ngoai_le"] = [dict(n, pham_vi=[_shift_no(x, after_no) for x in n["pham_vi"]])
                           if isinstance(n, dict) and isinstance(n.get("pham_vi"), list) else n for n in byd["ngoai_le"]]
    if new == byd:
        return False
    data["byd"] = new
    return True


def named_things(data: Dict) -> List[str]:
    """Tên các thứ BYĐ của shot nhắc (`vat[].vat` + `thanh_phan[].vat`) — M2.4 G1: đạo cụ cảnh trước chỉ mang khi có tên ở đây / chữ shot."""
    byd = data.get("byd") if isinstance(data, dict) else None
    if not isinstance(byd, dict):
        return []
    out = [str(c.get("vat")) for c in vat_items(byd) if isinstance(c, dict) and c.get("vat")]
    out += [str(c.get("vat")) for c in byd.get("thanh_phan") or [] if isinstance(c, dict) and c.get("vat")]
    return out
