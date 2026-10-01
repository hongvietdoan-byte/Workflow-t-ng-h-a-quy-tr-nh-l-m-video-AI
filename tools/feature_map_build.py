"""Sơ đồ cây tính năng dashboard: docs/so_do/feature_map.json (nguồn duy nhất) → .md (gạch đầu dòng) + .html (cây, import Figma bằng html.to.design).

    py tools/feature_map_build.py                         đọc trạng thái cờ từ dashboard.env của thư mục repo chính
    py tools/feature_map_build.py --env path/dashboard.env

Trạng thái cờ không ghi tay trong JSON: lấy mặc định + 'đã thử thật' từ core/features.py và giá trị thật từ dashboard.env, nên sơ đồ
không lệch khi bật/tắt cờ. Miễn phí, không gọi API.
"""
import argparse
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
SRC = os.path.join(ROOT, "docs", "so_do", "feature_map.json")
FIELDS = (("resp", "Trách nhiệm"), ("who", "Ai làm"), ("in", "Đầu vào"), ("out", "Đầu ra"), ("store", "Lưu ở đâu"),
          ("cost", "Tiền"), ("ui", "Trên giao diện"), ("code", "Code"))


def env_flags(path):
    out = {}
    if path and os.path.exists(path):
        for line in open(path, encoding="utf-8-sig"):
            m = re.match(r"\s*FEATURE_([A-Z0-9_]+)\s*=\s*(\S+)", line)
            if m:
                out[m.group(1).lower()] = m.group(2).strip().strip('"') in ("1", "true", "on", "yes")
    return out


def flag_notes(text, env):
    from core import features
    notes = []
    for name in re.findall(r"[a-z][a-z0-9_]+", text or ""):
        meta = features.FEATURES.get(name)
        if meta is None:
            continue
        on = env.get(name, False)
        notes.append({"name": name, "on": on, "verified": bool(meta.get("verified"))})
    return notes


def flag_text(notes):
    return ", ".join(f"`{n['name']}` {'BẬT' if n['on'] else 'TẮT'}{'' if n['verified'] else ' · chưa thử thật'}" for n in notes)


def walk(nodes, depth=0):
    for n in nodes:
        yield n, depth
        yield from walk(n.get("children") or [], depth + 1)


def to_md(data, env):
    L = [f"# {data['title']}", "", f"Ngày {data['date']} · {data['commit_note']}. Nguồn: `docs/so_do/feature_map.json`; "
         "bản hình: `docs/so_do/SO_DO_TINH_NANG.html` (import Figma bằng plugin html.to.design).", ""]
    L += [f"- {v}" for v in data["legend"].values()] + [""]
    for n, d in walk(data["nodes"]):
        if d == 0:
            L += [f"## {n['name']}", f"_Giao diện / code: {n.get('ui', '')}_", ""]
            continue
        ind = "  " * (d - 1)
        L.append(f"{ind}- **{n['name']}**")
        for key, label in FIELDS:
            if n.get(key):
                L.append(f"{ind}  - {label}: {n[key]}")
        notes = flag_notes(n.get("flag"), env)
        if notes:
            L.append(f"{ind}  - Cờ: {flag_text(notes)}")
    return "\n".join(L) + "\n"


CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2330;--mute:#5d6678;--line:#d6dbe4;--acc:#2f6fed;--acc2:#e8f0ff;--pay:#b4530a;--pay2:#fff1e3;
--on:#137a3f;--on2:#e3f6ea;--off:#6b7280;--off2:#eef0f3;--warn:#a1161b;--warn2:#fde8e8}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#12151b;--card:#1b2029;--ink:#e6e9ef;--mute:#9aa3b5;--line:#2c3340;
--acc:#7aa7ff;--acc2:#1d2a44;--pay:#f0a35c;--pay2:#3a2615;--on:#5fd393;--on2:#163222;--off:#a0a7b4;--off2:#262b35;--warn:#ff8b8f;--warn2:#3a1a1c}}
:root[data-theme="dark"]{--bg:#12151b;--card:#1b2029;--ink:#e6e9ef;--mute:#9aa3b5;--line:#2c3340;--acc:#7aa7ff;--acc2:#1d2a44;--pay:#f0a35c;
--pay2:#3a2615;--on:#5fd393;--on2:#163222;--off:#a0a7b4;--off2:#262b35;--warn:#ff8b8f;--warn2:#3a1a1c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 "Be Vietnam Pro",system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:24px 16px 64px}h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:0}
.sub{color:var(--mute);margin:0 0 16px}.legend{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 20px}.legend span{background:var(--card);border:1px solid var(--line);
border-radius:8px;padding:6px 10px;font-size:12.5px;color:var(--mute)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 24px}.stat{background:var(--card);border:1px solid var(--line);
border-radius:10px;padding:12px}.stat b{display:block;font-size:22px}.stat small{color:var(--mute)}
.flow{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:0 0 28px}.flow h2{margin-bottom:12px}
.chain{display:flex;flex-wrap:wrap;align-items:stretch;gap:6px}.chain a{flex:1 1 150px;text-decoration:none;color:inherit;background:var(--acc2);
border:1px solid var(--acc);border-radius:10px;padding:10px}.chain a b{display:block;font-size:13.5px}.chain a small{color:var(--mute);font-size:12px}
.arrow{align-self:center;color:var(--acc);font-weight:700}.support{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.support a{flex:1 1 140px;
text-decoration:none;color:inherit;border:1px dashed var(--line);border-radius:10px;padding:8px 10px;font-size:12.5px}
section.group{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:0 0 20px}
.ghead{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;margin-bottom:12px}.ghead code{color:var(--mute);font-size:12px}
ul.tree{list-style:none;margin:0;padding:0 0 0 18px;border-left:2px solid var(--line)}ul.tree>li{position:relative;margin:0 0 10px}
ul.tree>li:before{content:"";position:absolute;left:-18px;top:18px;width:14px;border-top:2px solid var(--line)}
section.group>ul.tree{padding-left:18px}
.node{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:var(--bg)}.node.parent{background:var(--acc2);border-color:var(--acc)}
.nt{font-weight:600;margin-bottom:6px}.chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px}.chip{font-size:11.5px;border-radius:999px;padding:2px 8px;
border:1px solid var(--line);background:var(--card)}.chip.pay{color:var(--pay);background:var(--pay2);border-color:transparent}.chip.on{color:var(--on);
background:var(--on2);border-color:transparent}.chip.off{color:var(--off);background:var(--off2);border-color:transparent}.chip.unv{color:var(--warn);
background:var(--warn2);border-color:transparent}
dl{display:grid;grid-template-columns:120px 1fr;gap:3px 12px;margin:0;font-size:13px}dt{color:var(--mute)}dd{margin:0;overflow-wrap:anywhere}
dd code{font-size:12px}@media (max-width:640px){dl{grid-template-columns:1fr}dt{margin-top:4px}ul.tree{padding-left:12px}ul.tree>li:before{left:-12px;width:9px}}
"""


def esc(s):
    return html.escape(str(s or ""))


def node_html(n, env, top=False):
    kids = n.get("children") or []
    chips = []
    if "💵" in (n.get("cost") or ""):
        chips.append('<span class="chip pay">💵 tốn tiền</span>')
    for f in flag_notes(n.get("flag"), env):
        chips.append(f'<span class="chip {"on" if f["on"] else "off"}">cờ {esc(f["name"])}: {"BẬT" if f["on"] else "TẮT"}</span>')
        if not f["verified"]:
            chips.append(f'<span class="chip unv">{esc(f["name"])} chưa thử thật</span>')
    rows = "".join(f"<dt>{label}</dt><dd>{esc(n[key])}</dd>" for key, label in FIELDS if n.get(key))
    body = (f'<div class="node{" parent" if kids else ""}" id="{esc(n["id"])}"><div class="nt">{esc(n["name"])}</div>'
            + (f'<div class="chips">{"".join(chips)}</div>' if chips else "") + (f"<dl>{rows}</dl>" if rows else "") + "</div>")
    if kids:
        body += '<ul class="tree">' + "".join(f"<li>{node_html(k, env)}</li>" for k in kids) + "</ul>"
    return body


def to_html(data, env):
    from core import features
    all_nodes = [n for n, d in walk(data["nodes"]) if d > 0]
    leaves = [n for n in all_nodes if not n.get("children")]
    paid = sum(1 for n in leaves if "💵" in (n.get("cost") or ""))
    fl_on = sum(1 for k in features.FEATURES if env.get(k))
    fl_unv_on = sum(1 for k, v in features.FEATURES.items() if env.get(k) and not v.get("verified"))
    stats = [(len(data["nodes"]), "nhóm lớn"), (len(leaves), "tính năng (lá)"), (paid, "tính năng tốn tiền"),
             (f"{fl_on}/{len(features.FEATURES)}", "cờ đang BẬT (máy chính)"), (fl_unv_on, "cờ BẬT mà chưa thử thật")]
    steps = [n for n in data["nodes"] if n["id"].startswith("S")]
    support = [n for n in data["nodes"] if not n["id"].startswith("S")]
    chain = '<span class="arrow">→</span>'.join(
        f'<a href="#{esc(n["id"])}"><b>{esc(n["name"])}</b><small>{len(list(walk(n.get("children") or [])))} khối</small></a>' for n in steps)
    sup = "".join(f'<a href="#{esc(n["id"])}">{esc(n["name"])}</a>' for n in support)
    groups = "".join(
        f'<section class="group" id="{esc(n["id"])}"><div class="ghead"><h2>{esc(n["name"])}</h2><code>{esc(n.get("ui"))}</code></div>'
        f'<ul class="tree">' + "".join(f"<li>{node_html(k, env)}</li>" for k in n.get("children") or []) + "</ul></section>"
        for n in data["nodes"])
    return (f'<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Sơ đồ tính năng</title><link rel="preconnect" href="https://fonts.googleapis.com">'
            f'<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700&display=swap" rel="stylesheet">'
            f'<style>{CSS}</style></head><body><div class="wrap"><h1>{esc(data["title"])}</h1>'
            f'<p class="sub">{esc(data["date"])} · {esc(data["commit_note"])}. Trạng thái cờ đọc từ dashboard.env lúc dựng sơ đồ.</p>'
            f'<div class="legend">' + "".join(f"<span>{esc(v)}</span>" for v in data["legend"].values()) + "</div>"
            f'<div class="stats">' + "".join(f"<div class=stat><b>{esc(a)}</b><small>{esc(b)}</small></div>" for a, b in stats) + "</div>"
            f'<div class="flow"><h2>Luồng chính</h2><div class="chain">{chain}</div><div class="support">{sup}</div></div>'
            f"{groups}</div></body></html>\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default=None, help="dashboard.env để đọc trạng thái cờ (mặc định: repo chính, rồi repo này)")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    env_path = a.env
    if env_path is None:
        for cand in (os.path.join(ROOT, "dashboard.env"), os.path.join(ROOT, "..", "..", "..", "dashboard.env")):
            if os.path.exists(cand):
                env_path = cand
                break
    env = env_flags(env_path)
    data = json.load(open(SRC, encoding="utf-8"))
    out_dir = os.path.dirname(SRC)
    with open(os.path.join(out_dir, "SO_DO_TINH_NANG.md"), "w", encoding="utf-8") as fh:
        fh.write(to_md(data, env))
    with open(os.path.join(out_dir, "SO_DO_TINH_NANG.html"), "w", encoding="utf-8") as fh:
        fh.write(to_html(data, env))
    print(f"cờ đọc từ: {env_path or '(không có — coi mọi cờ TẮT)'} · ghi {out_dir}/SO_DO_TINH_NANG.md + .html")


if __name__ == "__main__":
    main()
