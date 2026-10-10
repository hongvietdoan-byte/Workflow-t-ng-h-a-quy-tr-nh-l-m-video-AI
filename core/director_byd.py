"""K1a — Đạo diễn điền bảng ý đồ shot (BYĐ) (docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md hàng K1a, A14, A19, A29), cờ `shot_intent`.

Cờ BẬT: lời gọi Đạo diễn (một lượt / Tầng B Quay phim / chia lại một cảnh) đọc thêm prompts/31_director_byd.md → mỗi shot có khối `byd`.
Code kiểm (`core.shot_intent.validate`, có CSDL → mã Kho phải có thật). Lỗi ĐỎ / thiếu BYĐ → gửi lại ĐÚNG lỗi cho Đạo diễn sửa riêng các
shot hỏng (lượt Claude nhỏ, khâu `director_byd`, qua sổ chi `llm_runner.tagged`), tối đa MAX_ROUNDS vòng; còn hỏng → VÀNG + lý do
(không im lặng: `byd_kiem` trên shot + một dòng ⚙ Chẩn đoán). Hệ thống không chèn chữ nào vào BYĐ (A14): chỉ Đạo diễn viết, code kiểm.

Chỗ lưu: `scenes.data['byd']` + `scenes.data['byd_kiem']` (core/shots.shot_data — chỉ khi cờ bật). Chỗ đọc: tools/dryrun_k0b_p24.py
(ưu tiên `data['byd']` khi có), core/identity_declare.byd_view.

Cờ TẮT: không thêm chữ nào vào prompt, không lời gọi thêm, không trường mới — prompt và kết quả y như trước (test so từng byte).
"""
import json
import os
from typing import Dict, List, Optional, Tuple

from . import diag, features, shot_intent

FLAG = "shot_intent"
STAGE = "director_byd"
PROMPT_FILE = "31_director_byd.md"
MAX_ROUNDS = 2
HEADER = "# Đạo diễn — sửa bảng ý đồ shot (BYĐ)"
OUT_CHARS = 700            # ký tự JSON của một BYĐ (ước tính, tính dư)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def enabled() -> bool:
    return features.on(FLAG)


def prompt_block() -> str:
    """Phần thêm vào prompt Đạo diễn khi cờ bật; tắt → "" (người gọi bỏ qua chuỗi rỗng, prompt y cũ)."""
    if not enabled():
        return ""
    with open(os.path.join(_ROOT, "prompts", PROMPT_FILE), encoding="utf-8") as f:
        return f.read()


def _shots(obj: Dict, only_scene: Optional[int] = None) -> List[Tuple[int, int, Dict]]:
    out = []
    for sc in obj.get("scenes") or []:
        if not isinstance(sc, dict) or (only_scene is not None and sc.get("idx") != only_scene):
            continue
        for k, s in enumerate(sc.get("shots") or [], 1):
            if isinstance(s, dict):
                out.append((int(sc.get("idx") or 0), k, s))
    return out


def problems(shot: Dict, conn=None) -> Tuple[List[Dict], List[Dict]]:
    """(lỗi ĐỎ phải sửa, mục VÀNG không kiểm được) của BYĐ một shot. Không có BYĐ = một lỗi ĐỎ 'thiếu' (Đạo diễn được hỏi lại)."""
    byd = shot.get("byd")
    if byd is None:
        return [{"muc": "do", "truong": "byd", "loi": "Đạo diễn không trả BYĐ cho shot này"}], []
    found = shot_intent.validate(byd, conn)
    return [i for i in found if i["muc"] == "do"], [i for i in found if i["muc"] != "do"]


def _shot_brief(scene: int, k: int, s: Dict) -> Dict:
    keys = ("size", "angle", "camera_move", "characters", "action", "location_asset", "plate_spot", "weather")
    return dict({"canh": scene, "shot": k}, **{key: s[key] for key in keys if s.get(key) not in (None, "", [])})


def build_repair_prompt(bad: List[Tuple[int, int, Dict, List[Dict]]], round_no: int) -> str:
    """Đề bài sửa: cách viết BYĐ (prompt 31) + với mỗi shot hỏng: tóm tắt shot (để hiểu ý), BYĐ trước (hoặc 'không có'), lỗi code."""
    with open(os.path.join(_ROOT, "prompts", PROMPT_FILE), encoding="utf-8") as f:
        guide = f.read()
    L = [HEADER, "", f"Vòng sửa {round_no}/{MAX_ROUNDS}. Code đã kiểm BYĐ bạn viết; các shot dưới đây CHƯA đạt. Sửa đúng các lỗi, giữ "
         "nguyên phần đúng; không đổi ý đồ shot. Trả về MỘT JSON duy nhất:",
         '`{"byd": [{"canh": <số cảnh>, "shot": <số shot trong cảnh>, "byd": {…}}]}` — đủ mọi shot liệt kê dưới đây.', "", guide,
         "", "## Shot cần sửa"]
    for scene, k, s, errs in bad:
        L += ["", f"### Cảnh {scene} · shot {k}", "Shot (để hiểu ý):", "```json",
              json.dumps(_shot_brief(scene, k, s), ensure_ascii=False), "```"]
        L += (["BYĐ trước:", "```json", json.dumps(s["byd"], ensure_ascii=False), "```"] if s.get("byd") is not None
              else ["BYĐ trước: (không có)"])
        L.append("Lỗi code:")
        L += [f"- `{e['truong']}`: {e['loi']}" for e in errs]
    return "\n".join(L)


def _parse(text: str) -> Dict[Tuple[int, int], Dict]:
    from .llm_runner import extract_json
    obj = extract_json(text)
    rows = obj.get("byd") if isinstance(obj, dict) else None
    if not isinstance(rows, list):
        raise ValueError("cần {\"byd\": [{canh, shot, byd}]}")
    out = {}
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get("canh"), int) and isinstance(r.get("shot"), int):
            out[(r["canh"], r["shot"])] = r.get("byd")
    return out


def settle(conn, project_id: int, obj: Dict, client, only_scene: Optional[int] = None) -> Optional[Dict]:
    """Kiểm BYĐ mọi shot của `obj` (câu trả lời Đạo diễn đã qua validate_for_project, chưa lưu), sửa ≤ MAX_ROUNDS vòng, ghi `byd_kiem`
    lên từng shot + tóm tắt `obj['byd_kiem']`. Cờ tắt → None, không đụng `obj`. `only_scene`: chỉ cảnh vừa chia lại (cảnh khác giữ)."""
    if not enabled():
        return None
    from .llm_runner import tagged
    rows = _shots(obj, only_scene)
    bad = [(sc, k, s, problems(s, conn)[0]) for sc, k, s in rows]
    bad = [b for b in bad if b[3]]
    rounds, tin, tout, call_errors = 0, 0, 0, []
    while bad and rounds < MAX_ROUNDS:
        rounds += 1
        try:                                          # Đạo diễn đã trả tiền: lỗi mạng / trần / khóa ở lượt sửa không được làm mất kết quả đó
            with tagged(STAGE, project_id):           # sổ chi: mỗi vòng sửa là một lượt Claude ghi usage_events stage director_byd
                reply = client.complete(build_repair_prompt(bad, rounds))
        except Exception as e:  # noqa: BLE001 - nói ra (byd_kiem.loi_goi + ⚙ Chẩn đoán), không gọi thêm vòng nào
            call_errors.append(f"vòng {rounds}: lượt sửa lỗi ({type(e).__name__}: {str(e)[:160]}) — dừng sửa")
            break
        tin, tout = tin + reply.input_tokens, tout + reply.output_tokens
        try:
            fixed = _parse(reply.text)
        except ValueError as e:
            call_errors.append(f"vòng {rounds}: câu trả lời không đọc được ({str(e)[:120]})")
            fixed = {}
        for sc, k, s, _ in bad:
            if (sc, k) in fixed and fixed[(sc, k)] is not None:
                s["byd"] = fixed[(sc, k)]
        bad = [(sc, k, s, problems(s, conn)[0]) for sc, k, s, _ in bad]
        bad = [b for b in bad if b[3]]
    vang = []
    for sc, k, s in rows:
        red, yellow = problems(s, conn)
        if red:
            why = ("Đạo diễn không trả BYĐ" if s.get("byd") is None else f"BYĐ còn {len(red)} lỗi") + (
                f" sau {rounds} vòng sửa" if rounds else "")
            s["byd_kiem"] = {"muc": "vang", "ly_do": why, "loi": red + yellow, "vong": rounds}
            vang.append(f"cảnh {sc} shot {k}: {why} — " + "; ".join(f"{e['truong']}: {e['loi']}" for e in red[:3]))
        else:
            s["byd_kiem"] = {"muc": "vang" if yellow else "ok", "ly_do": "; ".join(e["loi"] for e in yellow), "loi": yellow,
                             "vong": rounds}
    summary = {"shots": len(rows), "vang_do": len(vang), "vong": rounds, "input_tokens": tin, "output_tokens": tout,
               "loi_goi": call_errors}
    obj["byd_kiem"] = summary
    if vang or call_errors:
        diag.record(conn, "director", "warn", "BYĐ (cờ shot_intent): " + " | ".join(call_errors + vang[:8])
                    + (f" | … và {len(vang) - 8} shot nữa" if len(vang) > 8 else ""), "director_byd", project_id)
    else:
        diag.record(conn, "director", "info", f"BYĐ (cờ shot_intent): {len(rows)} shot đạt"
                    + (f" sau {rounds} vòng sửa" if rounds else ""), "director_byd", project_id)
    return summary


def mock_answer(prompt: str) -> Dict:
    """Câu trả lời giả của MockLlm cho lượt sửa: trả lại nguyên BYĐ trước (không sửa được gì) — thử đường VÀNG không tốn tiền."""
    import re
    out = []
    for m in re.finditer(r"### Cảnh (\d+) · shot (\d+)\n.*?(?:BYĐ trước:\n```json\n(.*?)\n```|BYĐ trước: \(không có\))", prompt, re.S):
        out.append({"canh": int(m.group(1)), "shot": int(m.group(2)), "byd": json.loads(m.group(3)) if m.group(3) else None})
    return {"byd": out}


def estimate(n_shots: int) -> Dict:
    """Phần thêm khi cờ bật (tính dư): token ra thêm của lượt Đạo diễn (mỗi shot một BYĐ, × suy nghĩ) + tối đa MAX_ROUNDS lượt sửa
    (mỗi lượt: đề bài prompt 31 + mọi shot hỏng, câu trả lời mọi shot hỏng — giả định cả shot đều hỏng)."""
    from . import knowledge
    with open(os.path.join(_ROOT, "prompts", PROMPT_FILE), encoding="utf-8") as f:
        guide = len(f.read())
    per_shot_out = round(knowledge.approx_tokens(OUT_CHARS) * 2.0)
    repair_in = round(knowledge.approx_tokens(guide + n_shots * (OUT_CHARS + 600)) * 1.6)
    repair_out = round(knowledge.approx_tokens(n_shots * OUT_CHARS) * 2.0)
    return {"extra_output": per_shot_out * n_shots, "repair_calls_max": MAX_ROUNDS,
            "repair_input": repair_in * MAX_ROUNDS, "repair_output": repair_out * MAX_ROUNDS}
