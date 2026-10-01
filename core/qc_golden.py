"""Bộ đo vàng của Tổ QC (docs/THIET_KE_TO_QC_2026-10-01.md mục 15).

  dev_set()          #8 lượt 1 (docs/qc_agent_2026-09-27/verdicts.json) với nhãn sửa labels_v2 — bộ PHÁT TRIỂN: dùng để chỉnh, không để
                     kết luận chất lượng
  independent_set()  data/qc_golden/independent.json — nhãn người dùng gắn trên Google Sheet "Gắn nhãn bộ đo QC (01-10)" cho 134 khung
                     ngoài dòng #8 (Claude đọc Sheet qua Drive rồi ghi file này); khung chưa có nhãn bị bỏ
  score(items, results, category=None)
                     recall chặn (chỉ kết luận 'block' mới tính — doubt KHÔNG phải bắt được: S7.1 bộ cũ tính, làm đọc nhầm), báo nhầm,
                     tỉ lệ doubt; `category` lọc khung chặn theo loại lỗi của nhãn (vd chỉ "Nhân vật" khi đo C1 một mình)
Label values: "đạt" / "nhỏ" / "chặn"; category: the Sheet's list (Nhân vật, Hướng nhìn / diễn xuất, Liền mạch / ánh sáng, Bối cảnh / kiến
trúc, Kỹ thuật, Khác) or, for the dev set, mapped from the label's issue `loai`.
"""
import glob
import json
import os
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV_LABELS = os.path.join(ROOT, "docs", "qc_agent_2026-09-27")
INDEPENDENT = os.path.join(ROOT, "data", "qc_golden", "independent.json")
CATEGORY_OF_LOAI = (("khóa nhân vật", "Nhân vật"), ("lật", "Nhân vật"), ("trang phục", "Nhân vật"), ("hướng nhìn", "Hướng nhìn / diễn xuất"),
                    ("diễn", "Hướng nhìn / diễn xuất"), ("hành động", "Hướng nhìn / diễn xuất"), ("ánh sáng", "Liền mạch / ánh sáng"),
                    ("liền mạch", "Liền mạch / ánh sáng"), ("hồi tưởng", "Liền mạch / ánh sáng"), ("bối cảnh", "Bối cảnh / kiến trúc"),
                    ("kiến trúc", "Bối cảnh / kiến trúc"), ("cỡ cảnh", "Kỹ thuật"), ("ý đồ", "Hướng nhìn / diễn xuất"))


def category_of(loai: str) -> str:
    t = str(loai or "").lower()
    return next((c for k, c in CATEGORY_OF_LOAI if k in t), "Khác")


def dev_set(project_id: int = 8) -> List[Dict]:
    """[{"job", "project", "shot", "label", "categories"}] — the round-1 labels with the labels_v2 corrections."""
    items = json.load(open(os.path.join(DEV_LABELS, "verdicts.json"), encoding="utf-8"))
    try:
        fixes = json.load(open(os.path.join(DEV_LABELS, "labels_v2.json"), encoding="utf-8")).get("overrides") or {}
    except (OSError, ValueError):
        fixes = {}
    out = []
    for it in items:
        fix = fixes.get(str(it["job"]))
        label = (fix or {}).get("verdict") or it["verdict"]
        issues = (fix or {}).get("issues") if fix is not None else it.get("issues")
        cats = sorted({category_of(i.get("loai")) for i in issues or [] if isinstance(i, dict)})
        out.append({"job": int(it["job"]), "project": project_id, "shot": it.get("shot"), "label": label, "categories": cats})
    return out


def independent_set(path: str = INDEPENDENT) -> List[Dict]:
    """Labelled rows only. The file: [{"id": "P13-J481", "label": "Chặn", "category": "...", "note": "..."}] from the Sheet."""
    if not os.path.exists(path):
        return []
    rows = json.load(open(path, encoding="utf-8"))
    out = []
    for r in rows:
        label = str(r.get("label") or "").strip().lower()
        label = {"đạt": "đạt", "dat": "đạt", "nhỏ": "nhỏ", "nho": "nhỏ", "chặn": "chặn", "chan": "chặn"}.get(label)
        if not label:
            continue
        pid, job = str(r["id"]).lstrip("P").split("-J")
        out.append({"job": int(job), "project": int(pid), "shot": r.get("shot"), "label": label,
                    "categories": [r["category"]] if r.get("category") else [], "note": r.get("note", "")})
    return out


def picture(data_dir: str, project_id: int, job: int) -> Optional[str]:
    path = os.path.join(data_dir, str(project_id), "images", f"job_{job}.png")
    if os.path.exists(path):
        return path
    hits = sorted(glob.glob(os.path.join(data_dir, str(project_id), "trash", "images", f"job_{job}__*.png")))
    return hits[-1] if hits else None


def score(items: List[Dict], results: Dict[int, Dict], category: Optional[str] = None) -> Dict:
    """results: job → {"verdict": block/minor/pass/doubt, …}. Frames without a result are listed, not counted."""
    blocks = [i for i in items if i["label"] == "chặn" and (category is None or category in i["categories"])]
    others = [i for i in items if i["label"] in ("đạt", "nhỏ")]
    judged = [i for i in items if i["job"] in results]
    caught = [i for i in blocks if (results.get(i["job"]) or {}).get("verdict") == "block"]
    doubted_blocks = [i for i in blocks if (results.get(i["job"]) or {}).get("verdict") == "doubt"]
    false_block = [i for i in others if (results.get(i["job"]) or {}).get("verdict") == "block"]
    doubts = [i for i in judged if results[i["job"]].get("verdict") == "doubt"]
    nb = len([i for i in blocks if i["job"] in results])
    no = len([i for i in others if i["job"] in results])
    return {"blocks": nb, "caught": len(caught), "recall": round(len(caught) / nb, 3) if nb else None,
            "blocks_as_doubt": len(doubted_blocks), "others": no, "false_block": len(false_block),
            "false_block_rate": round(len(false_block) / no, 3) if no else None,
            "doubt_rate": round(len(doubts) / len(judged), 3) if judged else None, "judged": len(judged),
            "missing": [i["job"] for i in items if i["job"] not in results],
            "missed_jobs": [i["job"] for i in blocks if i not in caught and i["job"] in results],
            "false_block_jobs": [i["job"] for i in false_block]}
