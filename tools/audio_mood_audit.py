"""Kiểm nhãn/score mood OFFLINE; không import pipeline, đọc Kho hay tải model.

JSON: {"labels": ["Music", "Sad music"], "windows": [[{"label": "Sad music",
"score": 0.1}]], "complete_scores": false}. Thay labels bằng --ontology CSV
cột display_name khi đã có classmap. complete_scores=true đòi mọi nhãn mỗi cửa sổ.
"""
import argparse
import csv
import json
import math
import sys

MOODS = ("Happy music", "Sad music", "Tender music", "Exciting music",
         "Angry music", "Scary music", "Funny music")
THRESHOLD = 0.05


def analyse(payload, ontology=None):
    """Chỉ trả số đếm và nhãn mood cố định; không phản chiếu payload tự do."""
    if not isinstance(payload, dict):
        raise ValueError("JSON phải là object có labels và windows.")
    labels = ontology if ontology is not None else payload.get("labels")
    if not isinstance(labels, list) or not labels or any(not isinstance(x, str) or not x.strip() for x in labels):
        raise ValueError("Thiếu danh sách labels/ontology hợp lệ.")
    if len(set(labels)) != len(labels):
        raise ValueError("Ontology có nhãn trùng.")
    if ontology is not None and "labels" in payload and payload["labels"] != ontology:
        raise ValueError("labels JSON khác ontology CSV; chọn nguồn đúng.")
    rows = payload.get("windows")
    if not isinstance(rows, list):
        raise ValueError("Thiếu windows; dùng [] nếu chỉ kiểm ontology.")
    complete = payload.get("complete_scores", False)
    if not isinstance(complete, bool):
        raise ValueError("complete_scores phải là boolean.")
    label_set = set(labels)
    covered = label_set.intersection(MOODS)
    mismatches = sum(m not in label_set and any(x.casefold() == m.casefold() for x in labels) for m in MOODS)
    counts = {m: 0 for m in MOODS}
    unobserved = below = truncated = scored = 0
    for row in rows:
        if not isinstance(row, list) or not row:
            raise ValueError("Mỗi windows phải là danh sách score không rỗng.")
        seen = set()
        for item in row:
            if not isinstance(item, dict) or not isinstance(item.get("label"), str):
                raise ValueError("Score thiếu nhãn hợp lệ.")
            label, score = item["label"], item.get("score")
            if label not in label_set or label in seen:
                raise ValueError("Score có nhãn ngoài ontology hoặc nhãn trùng.")
            if isinstance(score, bool) or not isinstance(score, (float, int)) or not 0 <= score <= 1 or not math.isfinite(score):
                raise ValueError("Score thiếu hoặc không hữu hạn trong [0, 1].")
            seen.add(label)
            scored += 1
            if label in covered and score >= THRESHOLD:
                counts[label] += 1
        if complete and seen != label_set:
            raise ValueError("complete_scores=true nhưng score không phủ đủ ontology.")
        if seen != label_set:
            truncated += 1
        unobserved += len(covered - seen)
        if covered and covered <= seen and not any(item["label"] in covered and item["score"] >= THRESHOLD for item in row):
            below += 1
    return {"labels": len(labels), "windows": len(rows), "scored_labels": scored,
            "covered_moods": len(covered), "not_covered": len(MOODS) - len(covered),
            "case_mismatch_moods": mismatches,
            "ontology_has_no_mood": not covered and not mismatches,
            "candidates": sum(counts.values()), "candidate_counts": counts,
            "unobserved_mood_scores": unobserved, "truncated_windows": truncated,
            "below_threshold_windows": below, "threshold": THRESHOLD}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Kiểm mood từ JSON/CSV explicit, offline, chỉ đọc.")
    parser.add_argument("--input", required=True, help="JSON nhãn và score do người dùng cung cấp")
    parser.add_argument("--ontology", help="CSV display_name, không tự tìm/tải")
    args = parser.parse_args(argv)
    for location in (args.input, args.ontology):
        if location is None:
            continue
        candidate = location.strip()
        # UNC/extended UNC và mọi URL scheme; drive letter local vẫn hợp lệ.
        prefix, separator, _ = candidate.partition(":")
        if candidate.startswith(("\\\\", "//")) or (separator and len(prefix) > 1):
            print("Chỉ nhận đường dẫn file local; URL/UNC không được phép.", file=sys.stderr)
            return 2
    try:
        with open(args.input, encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        ontology = None
        if args.ontology:
            with open(args.ontology, newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or "display_name" not in reader.fieldnames:
                    raise ValueError("CSV ontology thiếu cột display_name.")
                ontology = [row["display_name"] for row in reader]
        result = analyse(payload, ontology)
    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error):
        print("Không đọc được đầu vào JSON/CSV; kiểm tra file và định dạng.", file=sys.stderr)
        return 2
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
