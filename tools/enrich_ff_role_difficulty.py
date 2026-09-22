"""One-off enrichment: add gameplay difficulty + role tags to Free Fire character descriptions.

Source: internal Google Sheet "Data for Viet Mabu" (tab char_Skill, cross-checked with
char_Role/char_Hard tabs) shared by the project owner, 2026-09-22. Not an official API --
transcribed by hand from the sheet UI, so re-run only if the sheet data changes.

    py tools/enrich_ff_role_difficulty.py

Safe to re-run: skips any character whose description already has the MARK block.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import assets  # noqa: E402

DB = os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))

HARD = {1: "Dễ", 2: "Trung bình", 3: "Khó"}
ROLE = {1: "Tấn công", 2: "Thông tin", 3: "Sinh tồn", 4: "Đồng đội"}
MARK = "[Độ khó & vai trò gameplay]"

# (tên trong sheet, hardId, [roleIds]) -- chép tay từ Google Sheet char_Skill, 2026-09-22
DATA = [
    ("A-Patroa", 1, []), ("Olivia", 1, [3, 4]), ("Ford", 1, [3]), ("Nikita", 1, [1]),
    ("Misha", 1, [3]), ("Maxim", 1, [1]), ("Kla", 1, [1]), ("Paloma", 1, [1]),
    ("Miguel", 1, [3]), ("Caroline", 1, [3]), ("Wukong", 2, [3]), ("Antonio", 1, [3]),
    ("Laura", 1, [1]), ("Rafael", 1, [3]), ("A124", 3, [1]), ("Joseph", 1, [3]),
    ("Shani", 1, [3, 4]), ("Notora", 1, []), ("Kelly", 1, [1, 3]), ("Steffie", 1, [3, 4]),
    ("Jota", 1, [3]), ("Kapella", 1, [4]), ("Luqueta", 1, [3]), ("Wolfrahh", 1, [1, 3]),
    ("Clu", 1, [2, 4]), ("Hayato", 1, [1, 3]), ("Dasha", 1, [1, 3]), ("K", 2, [3, 4]),
    ("Skyler", 3, [1]), ("Shirou", 1, [2, 4]), ("Andrew", 1, [3]), ("Maro", 1, [1]),
    ("Xayne", 1, [1, 3]), ("D-bee", 1, [1, 3]), ("Thiva", 1, [4]), ("Dimitri", 2, [4]),
    ("Moco", 1, [2, 4]), ("Leon", 1, [3]), ("Otho", 1, [1, 2]), ("Jai", 1, [1]),
    ("Nairi", 1, [3, 4]), ("Luna", 1, [1, 3]), ("Kenta", 1, [3]), ("Homer", 1, [1, 2]),
    ("Iris", 1, [1, 2]), ("Tatsuya", 3, [1, 3]), ("Santino", 3, [3]), ("J.Biebs", 1, [3, 4]),
    ("Orion", 3, [1, 3]), ("Alvaro", 2, [1]), ("Sonia", 1, [3]), ("Suzy", 1, [4]),
    ("Ignis", 3, [1, 2]), ("Ryden", 3, [1]), ("Kairos", 1, [1, 3]), ("Kassie", 3, [4]),
    ("Lila", 1, [1, 3]), ("Koda", 1, []), ("Chrono", 2, [3]), ("Oscar", 3, [1, 3]),
    ("Rin", 1, [1]), ("Nero", 2, [1]), ("Morse", 2, [1, 3]), ("Ray", 2, [1]),
    ("Alok", 2, [3, 4]),
]


def block_text(hard_id: int, role_ids: list) -> str:
    roles = ", ".join(ROLE[r] for r in role_ids) if role_ids else "(không gắn vai trò)"
    return f"{MARK} Độ khó: {HARD[hard_id]} · Vai trò: {roles} (nguồn: Google Sheet nội bộ, 2026-09-22)"


def main() -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    by_fold = {}
    for row in con.execute("SELECT id, name, aliases, description FROM assets WHERE kind='character' AND game='FF'"):
        names = [row["name"]] + [x for x in (row["aliases"] or "").replace(";", ",").split(",") if x.strip()]
        for n in names:
            by_fold[assets.fold(n)] = row

    updated, skipped, missing = 0, 0, []
    for name, hard_id, role_ids in DATA:
        row = by_fold.get(assets.fold(name))
        if row is None:
            missing.append(name)
            continue
        desc = row["description"] or ""
        if MARK in desc:
            skipped += 1
            continue
        new_desc = (desc.rstrip() + "\n\n" if desc.strip() else "") + block_text(hard_id, role_ids)
        con.execute("UPDATE assets SET description=? WHERE id=?", (new_desc, row["id"]))
        updated += 1
    con.commit()
    print(f"updated={updated} skipped(already had block)={skipped} missing={missing}")


if __name__ == "__main__":
    main()
