"""Bảng GÁN NHÃN báo nhầm cho khóa nhận diện A18 (thẩm định 4 lỗ hổng #1, thẩm định 5 #4/#5, A25) — 0 USD, không gọi model, CHỈ ĐỌC
CSDL bản chính.

Chạy lại khóa nhận diện (core.identity_declare) trên prompt thật của TỪNG dự án như chạy khô K0b (tools/dryrun_k0b_p24.py — cùng hàm
identity_rows, cùng cấu hình project_config) hai lần: KHÔNG lọc và LỌC theo BYĐ (data_out/k0b_p<id>/byd_shot*.json: cỡ cảnh, mặt/lưng,
có trong khung). Mục còn bị báo sau lọc (thieu / thieu_mau / sai_mau) → MỘT bảng gộp các dự án cho người dùng gán "đúng lỗi / báo nhầm"
(mặc định 30 mục, chia đều giữa các dự án — dự án ít mục thì dự án kia bù; trong một dự án lấy xoay vòng theo shot). Ghi
docs/NHAN_BAO_NHAM_A18_2026-10-10.md (đường dẫn neo theo repo, không theo cwd):

    PYTHONUTF8=1 py tools/dryrun_k0b_p24.py --project 22        # (một lần) dữ liệu chạy khô #22
    PYTHONUTF8=1 py tools/nhan_bao_nham_a18.py [--projects 22 24] [--main D:/AI-Video-Pipeline] [--max 30]

Dự án chưa có dữ liệu chạy khô (data_out/k0b_p<id>/summary.json) → SystemExit nói rõ, không bỏ im lặng.
"""
import argparse
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import identity_declare as idd  # noqa: E402

DATA = os.path.join(ROOT, "data_out", "k0b_p24")       # tương thích người gọi cũ (#24)
OUT = os.path.join(ROOT, "docs", "NHAN_BAO_NHAM_A18_2026-10-10.md")
# Nhãn ĐỀ XUẤT của agent (không phải nhãn người dùng): khóa 'dự án|shot|nhân vật|món' → {nhan, do_chac, ly_do}; chạy lại tool giữ nhãn
AGENT = os.path.join(ROOT, "docs", "NHAN_BAO_NHAM_A18_agent.json")
BAO = ("thieu", "thieu_mau", "sai_mau")
PROJECTS = (22, 24)
NGUONG = ("Mục 9 kế hoạch chỉ có ngưỡng cho LỚP CLAUDE: báo nhầm ≤ 10 % trước khi chặn, cỡ mẫu ≥ 50 mục trên ≥ 2 dự án. Lớp CODE A18 "
          "có ngưỡng riêng — **người dùng chốt 10/10 (A25): báo nhầm ≤ 10 % trên n ≥ 30 mục, lấy từ ≥ 2 dự án (#22 + #24)**. Chưa "
          "đạt → `CHAN_DO = False` (thiếu chữ = VÀNG, không chặn).")


def _dryrun():
    spec = importlib.util.spec_from_file_location("dryrun_k0b_p24", os.path.join(ROOT, "tools", "dryrun_k0b_p24.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def data_dir(pid) -> str:
    """data_out/k0b_p<pid> neo theo gốc repo — cùng chỗ tools/dryrun_k0b_p24.py ghi."""
    return os.path.join(ROOT, "data_out", f"k0b_p{int(pid)}")


def load_summary(pid) -> dict:
    path = os.path.join(data_dir(pid), "summary.json")
    if not os.path.exists(path):
        raise SystemExit(f"#{pid}: chưa chạy khô ({path} không có) — chạy `PYTHONUTF8=1 py tools/dryrun_k0b_p24.py --project {pid}` trước")
    return json.load(open(path, encoding="utf-8"))


def load_agent(path: str = AGENT) -> dict:
    """File nhãn đề xuất của agent; không có file → {} (cột để trống, không bịa nhãn)."""
    if not path or not os.path.exists(path):
        return {}
    return json.load(open(path, encoding="utf-8"))


def agent_key(pid, shot, nhan_vat, mon) -> str:
    return f"{int(pid)}|{int(shot)}|{nhan_vat}|{mon}"


def agent_cell(label) -> str:
    if not label:
        return ""
    return f"**{label['nhan']}** — {label['ly_do']} ({label['do_chac']})".replace("|", "/")


def agent_summary(chosen, agent: dict) -> list:
    """Mục '## Agent đề xuất': đếm đúng lỗi / báo nhầm trên các mục đã chọn (theo dự án) + kiểu báo nhầm ghi trong file agent."""
    labels = agent.get("nhan", {})
    rows = [(p, labels.get(agent_key(p, it["shot"], it["n"]["nhan_vat"], it["m"]["mon"]))) for p, it in chosen]
    got = [(p, lb) for p, lb in rows if lb]
    if not got:
        return []

    def tally(sel):
        dung = sum(1 for _, lb in sel if lb["nhan"] == "đúng lỗi")
        nham = sum(1 for _, lb in sel if lb["nhan"] == "báo nhầm")
        thap = sum(1 for _, lb in sel if lb.get("do_chac") == "thấp")
        return dung, nham, thap

    dung, nham, thap = tally(got)
    out = ["## Agent đề xuất (10/10)", "",
           f"Agent gán {len(got)}/{len(rows)} mục (nhãn ĐỀ XUẤT, người dùng duyệt cột cuối): **đúng lỗi {dung} / báo nhầm {nham}** → tỉ lệ "
           f"báo nhầm ước **{round(100 * nham / len(got))} %** (n = {len(got)}; ngưỡng A25 ≤ 10 %). Độ chắc thấp: {thap} mục.", "",
           "| Dự án | đúng lỗi | báo nhầm | tỉ lệ báo nhầm |", "|---|---|---|---|"]
    for p in dict.fromkeys(p for p, _ in got):
        d, n, _ = tally([g for g in got if g[0] == p])
        out.append(f"| #{p} | {d} | {n} | {round(100 * n / (d + n))} % |")
    if agent.get("kieu_bao_nham"):
        out += ["", "Kiểu báo nhầm lặp lại (gợi ý sửa luật A18 — CHƯA sửa code A18):", ""]
        out += [f"- {line}" for line in agent["kieu_bao_nham"]]
    missing = len(rows) - len(got)
    if missing:
        out += ["", f"{missing} mục trong bảng chưa có nhãn agent (bảng đổi sau lần gán) — cần gán lại."]
    return out + [""]


def excerpt(text: str, item: str, n: int = 15) -> str:
    """≤ n từ của đoạn prompt nói về nhân vật: quanh chỗ nhắc món (nếu có), không thì đầu đoạn."""
    words = str(text or "").split()
    if not words:
        return "(đoạn prompt của nhân vật rỗng)"
    keys = [idd.fold(w) for w in idd.ITEMS.get(item, ((item,),))[0]]
    at = next((i for i, w in enumerate(words) if any(re.sub(r"[^\w-]", "", idd.fold(w)).startswith(k.split()[0]) for k in keys)), None)
    start = 0 if at is None else max(0, at - n // 2)
    part = words[start:start + n]
    return ("… " if start else "") + " ".join(part) + (" …" if start + n < len(words) else "")


def _count(rows, states):
    return sum(1 for n in rows for m in n["mon"] if m["trang_thai"] in states)


def build(main: str, pid: int = 24, mod=None):
    """Mỗi shot của dự án `pid`: identity_rows trước / sau lọc BYĐ trên prompt hiện tại trong CSDL (cấu hình project_config)."""
    mod = mod or _dryrun()
    cfg = mod.project_config(pid)
    summary = load_summary(pid)
    conn = mod.ro(main)
    scenes = {r[0]: json.loads(r[1]) for r in conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))}
    shots = []
    for s in summary["shots"]:
        idx = s["shot"]
        data = scenes.get(idx)
        if data is None:
            raise SystemExit(f"shot {idx}: không có trong CSDL {main} (project {pid}) — không tạo bảng thiếu shot")
        path = os.path.join(data_dir(pid), f"byd_shot{idx}.json")
        byd = json.load(open(path, encoding="utf-8")).get("byd")
        if byd is None:
            raise SystemExit(f"{path}: không có BYĐ — không lọc được")
        prompt, chars, people = data.get("image_prompt") or "", data.get("characters") or [], set(s["nguoi_trong_khung"])
        before = mod.identity_rows(conn, chars, prompt, people, cfg=cfg)
        after = mod.identity_rows(conn, chars, prompt, people, byd=byd, cfg=cfg)
        seg = idd.segment(prompt, {c: cfg["markers"].get(c, [c.lower()]) for c in chars if cfg["stage_key"].get(c) in people})
        shots.append({"project": pid, "shot": idx, "co": byd["may"]["co"], "before": before, "after": after, "seg": seg,
                      "summary_thieu": sum(n["tong"].get("thieu", 0) for n in s["nhan_dien"])})
    return shots


def _round_robin(items):
    """Xoay vòng theo shot (thứ tự shot giữ nguyên) — mẫu không dồn vào mấy shot đầu."""
    by_shot = {}
    for it in items:
        by_shot.setdefault(it["shot"], []).append(it)
    queues, out = list(by_shot.values()), []
    while any(queues):
        for q in queues:
            if q:
                out.append(q.pop(0))
    return out


def pick(groups, max_rows: int):
    """{pid: [mục có 'shot']} → [(pid, mục)] ≤ max_rows: chia đều giữa dự án; dự án thiếu → phần dư cho dự án còn mục."""
    queues = {p: _round_robin(v) for p, v in groups.items()}
    quota = {p: 0 for p in queues}
    left = max_rows
    while left > 0:
        open_ = [p for p in queues if quota[p] < len(queues[p])]
        if not open_:
            break
        for p in open_:
            if left <= 0:
                break
            quota[p] += 1
            left -= 1
    return [(p, it) for p in queues for it in queues[p][:quota[p]]]


def _items(shots, states):
    return [{"shot": s["shot"], "s": s, "n": n, "m": m} for s in shots for n in s["after"] for m in n["mon"] if m["trang_thai"] in states]


def _stats(shots):
    return {"b_thieu": sum(_count(s["before"], ("thieu",)) for s in shots), "a_thieu": sum(_count(s["after"], ("thieu",)) for s in shots),
            "b_bao": sum(_count(s["before"], BAO) for s in shots), "a_bao": sum(_count(s["after"], BAO) for s in shots),
            "a_can": sum(_count(s["after"], ("khong_can",)) for s in shots),
            "b_shots": sum(1 for s in shots if _count(s["before"], BAO)), "a_shots": sum(1 for s in shots if _count(s["after"], BAO)),
            "sum_thieu": sum(s["summary_thieu"] for s in shots), "n": len(shots),
            "by_state": {k: sum(_count(s["after"], (k,)) for s in shots) for k in BAO}}


def render(by_project, max_rows: int = 30, agent: dict = None) -> str:
    """by_project = {pid: shots (build)} → bảng markdown gộp; agent = load_agent() (nhãn đề xuất, cột trước cột người dùng)."""
    agent = agent or {}
    labels = agent.get("nhan", {})
    pids = list(by_project)
    groups = {p: _items(by_project[p], BAO) for p in pids}
    chosen = pick(groups, max_rows)
    lines = [
        "# Bảng gán nhãn báo nhầm — khóa nhận diện A18 (10/10)",
        "",
        "Thẩm định 4 lỗ hổng #1 + thẩm định 5 #4/#5: luật A18 \"mọi món must_keep phải có chữ trong prompt\" chưa đo báo nhầm. Bảng này lấy",
        f"từ chạy khô {' + '.join('#' + str(p) for p in pids)} (prompt ảnh thật trong CSDL, BYĐ `data_out/k0b_p<id>/byd_shot*.json`), sinh "
        "bằng `tools/nhan_bao_nham_a18.py` — chạy lại ra đúng bảng.",
        "",
        f"**Ngưỡng nhận:** {NGUONG}",
        "",
        "## Số đo trước / sau lọc theo BYĐ (từng dự án)",
        "",
        "| Dự án (số shot) | món `thieu` trước → sau | món bị báo (thieu + thieu_mau + sai_mau) trước → sau | thieu_mau / sai_mau sau | "
        "shot có món bị báo trước → sau | món `khong_can` sau |",
        "|---|---|---|---|---|---|",
    ]
    for p in pids:
        st = _stats(by_project[p])
        lines.append(f"| #{p} ({st['n']}) | {st['b_thieu']} → {st['a_thieu']} | {st['b_bao']} → {st['a_bao']} | "
                     f"{st['by_state']['thieu_mau']} / {st['by_state']['sai_mau']} | {st['b_shots']} → {st['a_shots']} | {st['a_can']} |")
    lines += ["", "(Đối chiếu: summary.json của chạy khô — đã lọc theo BYĐ — ghi số `thieu`: " + ", ".join(
        f"#{p} = {_stats(by_project[p])['sum_thieu']}" for p in pids) + "; khác cột \"sau\" nghĩa là CSDL đổi sau lần chạy khô.)", "",
        "## Gán nhãn (mỗi mục một chạm)", "",
        "Cột cuối: ghi **đúng lỗi** (prompt thật sự thiếu / sai món đó, ảnh dễ vẽ sai) hoặc **báo nhầm** (món có trong khung đúng hoặc không",
        "cần chữ ở shot này). Kết quả code: `thieu` = không có chữ món; `thieu_mau` = có món, thiếu màu chính; `sai_mau` = màu ngược khóa.",
        "Chọn mục: chia đều giữa các dự án, trong một dự án xoay vòng theo shot. Mục đã chọn mỗi dự án: " + ", ".join(
            f"#{p} = {sum(1 for q, _ in chosen if q == p)}/{len(groups[p])}" for p in pids) + f" (tổng {len(chosen)}).", "",
        "| # | Dự án | Shot (cỡ) | Nhân vật | Món (màu khóa) | Kết quả code | Mức | Trích prompt (≤ 15 từ) | "
        "Agent đề xuất (lý do ≤ 20 từ, độ chắc cao/vừa/thấp) | Người dùng: đúng lỗi / báo nhầm |",
        "|---|---|---|---|---|---|---|---|---|---|"]
    for i, (p, it) in enumerate(chosen, 1):
        s, n, m = it["s"], it["n"], it["m"]
        mau = "/".join(m.get("mau_chinh") or []) or "—"
        ex = excerpt(s["seg"].get(n["nhan_vat"], ""), m["mon"]).replace("|", "/")
        lines.append(f"| {i} | #{p} | {s['shot']} ({s['co']}) | {n['nhan_vat']} | {m['mon']} ({mau}) | {m['trang_thai']} | "
                     f"{'ĐỎ' if m['muc'] == 'do' else 'VÀNG'} | {ex} | "
                     f"{agent_cell(labels.get(agent_key(p, s['shot'], n['nhan_vat'], m['mon'])))} | |")
    total = sum(len(v) for v in groups.values())
    if total > len(chosen):
        lines.append(f"\n{total - len(chosen)} mục bị báo khác chưa đưa vào bảng (giới hạn {max_rows}).")
    if not chosen:
        lines.append("| — | — | — | — | — | không còn mục bị báo | — | — | — | — |")
    if total < 30:
        lines.append(f"\n**Chưa đủ mẫu A25:** tổng {total} mục bị báo < 30 — chưa đo được ngưỡng.")
    lines += ["", "## Món bị lọc (`khong_can`) — để người dùng xem lọc có che lỗi thật không", "",
              "| Dự án | Shot (cỡ) | Nhân vật | Món | Lý do |", "|---|---|---|---|---|"]
    for p in pids:
        for it in _items(by_project[p], ("khong_can",)):
            lines.append(f"| #{p} | {it['s']['shot']} ({it['s']['co']}) | {it['n']['nhan_vat']} | {it['m']['mon']} | {it['m']['ly_do']} |")
    lines += ["", "## Giới hạn / chưa có",
              "- #22 không có shot_specs viết tay: BYĐ dựng từ chữ kịch bản (`spec_from_scene` — size / angle / characters / blocking),",
              "  mọi ô ghi `suy_tu_chu` trong `data_out/k0b_p22/byd_shot*.json`. Nhân vật mặc bộ Khủng Long ('… KL'): khóa = tóc/mặt/mắt",
              "  của nhân vật (Kho 33 / 23) + món của trang phục (Kho 416 / 417, mô tả tiếng Việt — món suy từ chữ, có thể sai).",
              "- Món KHÔNG nhận ra (`khong_nhan_ra` trong summary.json: vd bomber / quần của Maxim, 'Hoodie đỏ…' của Kho 416) không được",
              "  kiểm → không có trong bảng; tỉ lệ báo nhầm chỉ đo trên món code nhận ra.",
              "- Lọc chưa chỉnh theo tư thế (ngồi / quỳ / bò đổi phần thân trong khung) và chưa thấy vật che (bàn, thành giếng) — K1a.",
              "- `segment`: hai nhân vật cùng từ đánh dấu (hai dạng yêu nữ cùng 'creature'; 'MAXIM' với 'MAXIM KL' khi chỉ ghi 'Maxim')",
              "  → mệnh đề thuộc CẢ HAI (sửa 10/10, ca `test_segment_shared_marker_belongs_to_both_forms`). Đoạn tả 'biến hình từ dạng",
              "  A sang dạng B' vẫn tính cho cả hai dạng → màu của dạng kia có thể ra `sai_mau` (người dùng gán để đo).", ""]
    lines += agent_summary(chosen, agent)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default="D:/AI-Video-Pipeline")
    ap.add_argument("--projects", type=int, nargs="+", default=list(PROJECTS))
    ap.add_argument("--max", type=int, default=30)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--agent", default=AGENT, help="file nhãn đề xuất của agent (json)")
    a = ap.parse_args(argv)
    mod = _dryrun()
    by_project = {p: build(a.main, p, mod) for p in a.projects}
    text = render(by_project, a.max, load_agent(a.agent))
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    for p, shots in by_project.items():
        for s in shots:
            print(f"#{p} S{s['shot']} {s['co']}: thieu {_count(s['before'], ('thieu',))} -> {_count(s['after'], ('thieu',))}, "
                  f"bao {_count(s['before'], BAO)} -> {_count(s['after'], BAO)}, khong_can {_count(s['after'], ('khong_can',))}")
    print("ghi", a.out)


if __name__ == "__main__":
    main()
