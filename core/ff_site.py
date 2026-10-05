"""Reads the official Free Fire website (https://ff.garena.com/vn/) into the resource library.

What the public pages hold: the six maps with every area (name, description, official picture), every character (title, profile, skill,
awakening), every pet (biography, skill) and the weapons of every category (stats). The site's paged list API only answers its own front end
("whitelist check failed") and is NOT used or bypassed: instead the pages are read the way a visitor moves through them, following the
"previous / next" links of the character and pet pages and opening each weapon category. A short pause is kept between requests.

Safety (S14.5 Gói C2): only `https` addresses on garena.com / *.garena.com are opened (pictures also from the CDN hosts in
FF_SITE_IMAGE_HOSTS, default cdn.wildflamestudio.com); the host is checked before opening, after EVERY redirect, when the items are
collected and again right before a picture is downloaded. A refused address is counted and named in the summary, never dropped silently.

Each page carries its data as a script (`window.__NUXT__`). It is read in two tiers: as plain JSON when it is JSON; otherwise (the
real pages use the form `(function(a,b,…){return {…}}(…))`) by Node.js run with the permission model (`--permission`: no file
access, no child processes, no workers, no native addons), an EMPTY environment, a throw-away working folder and a 30 s limit.
A Node.js without the permission model is refused with a message (never run unrestricted). The old `vm.runInContext` sandbox is
gone: it was escapable (`window.constructor.constructor('return process')()` read files).
Existing library entries are enriched, never overwritten: the site text goes into a marked block at the end of the description, which a
later run replaces, and pictures already present are not added twice. The website text reaches Claude wrapped by
`core.prompts.external_block` (reference material, not instructions).
"""
import html as htmllib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from . import assets

BASE = "https://ff.garena.com/vn"
MARK = "[ff.garena.com]"
UA = "Mozilla/5.0 (AIVideoPipeline resource reader)"
PICS_PER_ITEM = 3                      # official pictures kept per entry (the library holds at most 6)
ARTICLES = 12                          # newest news articles kept
ARTICLE_CHARS = 8000
MAX_WALK = 400                         # safety stop when following next-links
PAUSE = 0.25                           # seconds between page requests: be gentle with the website
PAGE_HOSTS = ("garena.com",)           # pages: garena.com and every *.garena.com, https only
DEFAULT_IMAGE_HOSTS = "cdn.wildflamestudio.com"   # where the official pictures really live (all 484 site pictures in the library, 06/10)
NODE_TIMEOUT = 30                      # seconds for one page's script
NUXT = "window.__NUXT__="
# Reads ONE expression (the right-hand side of `window.__NUXT__=`) from stdin and prints it as JSON. The names below are shadowed
# only as a second fence; the real fence is the permission model of the Node process (no files, no child processes).
_NODE = r"""
const out = process.stdout; let h = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', d => h += d).on('end', () => {
  let v;
  try {
    v = new Function('process', 'require', 'module', 'exports', 'global', 'globalThis', 'window',
                     '"use strict"; return (' + h + '\n);')(undefined, undefined, undefined, undefined, undefined, undefined, {});
    out.write(JSON.stringify({ ok: v === undefined ? null : v }));
  } catch (e) {
    out.write(JSON.stringify({ error: String((e && e.message) || e).slice(0, 300) }));
  }
});
"""


class FfSiteError(Exception):
    """A message that can be shown to the person."""


# ---- which addresses may be opened ------------------------------------------------------------------------------------
def image_hosts() -> Tuple[str, ...]:
    """Picture hosts besides garena.com: FF_SITE_IMAGE_HOSTS (comma separated) or the CDN the website really uses."""
    raw = os.environ.get("FF_SITE_IMAGE_HOSTS", DEFAULT_IMAGE_HOSTS)
    return tuple(h.strip().lower().lstrip(".") for h in raw.split(",") if h.strip())


def _host_ok(host: str, allowed) -> bool:
    return any(host == d or host.endswith("." + d) for d in allowed)


def refusal(url: str, images: bool = False) -> Optional[str]:
    """Why `url` may not be opened (None when it may): https only, host garena.com / *.garena.com (+ picture hosts for pictures)."""
    try:
        parts = urllib.parse.urlsplit(str(url))
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        return f"địa chỉ không đọc được: {str(url)[:120]}"
    allowed = PAGE_HOSTS + (image_hosts() if images else ())
    if parts.scheme != "https":
        return f"chỉ mở địa chỉ https, bị từ chối: {str(url)[:120]}"
    if parts.username or parts.password or not host or not _host_ok(host, allowed):
        return (f"máy chủ '{host or '?'}' không nằm trong danh sách cho phép ({', '.join(allowed)}), bị từ chối: {str(url)[:120]}"
                + ("" if images else " — chỉ trang của garena.com"))
    return None


def check_url(url: str, images: bool = False) -> None:
    why = refusal(url, images)
    if why:
        raise FfSiteError(f"Địa chỉ bị từ chối — {why}. Thêm máy chủ ảnh vào FF_SITE_IMAGE_HOSTS nếu đó là máy chủ ảnh chính thức.")


class _RedirectGuard(urllib.request.HTTPRedirectHandler):
    """Checks the target of EVERY redirect against the same list before following it."""

    def __init__(self, images: bool = False):
        super().__init__()
        self.images = images

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(urllib.parse.urljoin(req.full_url, newurl), self.images)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, binary: bool = False, timeout: int = 40):
    """GET one allowed address (a page, or with binary=True a picture). Refused addresses raise FfSiteError before any request."""
    check_url(url, images=binary)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "vi"})
    opener = urllib.request.build_opener(_RedirectGuard(images=binary))
    try:
        with opener.open(req, timeout=timeout) as resp:
            check_url(resp.geturl(), images=binary)                      # where we actually ended up
            body = resp.read()
    except OSError as e:
        raise FfSiteError(f"Không mở được {url}: {e}") from None
    return body if binary else body.decode("utf-8", "replace")


# ---- reading the page's data --------------------------------------------------------------------------------------------
_PERMISSION_FLAG: Dict[str, Optional[str]] = {}


def _node_env() -> Dict[str, str]:
    """The environment Node.js gets: nothing on Linux/macOS; on Windows only SystemRoot (06/10: Node 24 aborts at start with
    'Assertion failed: ncrypto::CSPRNG' when the environment block is completely empty). No keys, no PATH, no user folders."""
    if os.name == "nt":
        root = os.environ.get("SystemRoot") or os.environ.get("SYSTEMROOT") or r"C:\Windows"
        return {"SystemRoot": root}
    return {}


def _permission_flag(node: str) -> str:
    """'--permission' (Node ≥ 22.13/23.5) or '--experimental-permission' (Node 20–22); FfSiteError when the Node has neither."""
    if node not in _PERMISSION_FLAG:
        found = None
        for flag in ("--permission", "--experimental-permission"):
            try:
                proc = subprocess.run([node, flag, "-e", "process.stdout.write(String(process.permission && "
                                       "!process.permission.has('fs.read') && !process.permission.has('child')))"],
                                      capture_output=True, timeout=NODE_TIMEOUT, env=_node_env(), cwd=tempfile.gettempdir())
            except (OSError, subprocess.TimeoutExpired):
                continue
            if proc.returncode == 0 and proc.stdout.strip() == b"true":
                found = flag
                break
        _PERMISSION_FLAG[node] = found
    flag = _PERMISSION_FLAG[node]
    if not flag:
        try:
            ver = subprocess.run([node, "--version"], capture_output=True, timeout=10).stdout.decode().strip()
        except (OSError, subprocess.TimeoutExpired):
            ver = "?"
        raise FfSiteError(f"Node.js {ver} không có chế độ giới hạn quyền (--permission, cần Node.js ≥ 20) — không chạy dữ liệu website "
                          "khi không giới hạn được. Cập nhật Node.js (https://nodejs.org) rồi bấm lại.")
    return flag


def _payload(page: str) -> Optional[str]:
    i = page.find(NUXT)
    if i < 0:
        return None
    j = page.find("</script>", i)
    return page[i + len(NUXT): j if j >= 0 else len(page)].strip().rstrip(";").strip()


def _node_eval(code: str) -> Optional[Dict]:
    node = shutil.which("node")
    if not node:
        raise FfSiteError("Cần Node.js trên máy để đọc dữ liệu từ website (https://nodejs.org).")
    flag = _permission_flag(node)
    with tempfile.TemporaryDirectory(prefix="ff_site_") as cwd:
        try:
            proc = subprocess.run([node, flag, "-e", _NODE], input=code.encode("utf-8"), capture_output=True,
                                  timeout=NODE_TIMEOUT, env=_node_env(), cwd=cwd)
        except subprocess.TimeoutExpired:
            raise FfSiteError(f"Dữ liệu trang chạy quá {NODE_TIMEOUT} giây — đã dừng Node.js, bỏ trang này.") from None
        except OSError as e:
            raise FfSiteError(f"Không chạy được Node.js: {e}") from None
    out = proc.stdout.decode("utf-8", "replace").strip()
    try:
        res = json.loads(out) if out else None
    except ValueError:
        res = None
    if not isinstance(res, dict) or ("ok" not in res and "error" not in res):
        err = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise FfSiteError(f"Không đọc được dữ liệu trang (Node.js thoát mã {proc.returncode}"
                          + (f": {err[-1][:200]}" if err else "") + ").")
    if "error" in res:
        raise FfSiteError(f"Không đọc được dữ liệu trang: {res['error']}")
    return res["ok"] if isinstance(res["ok"], dict) else None


def nuxt_state(page: str) -> Optional[Dict]:
    """The page's data object; None when the page carries none. Plain JSON is read directly; the function form of the real pages is
    run by Node.js under the permission model (see the module note). FfSiteError when the data cannot be read."""
    code = _payload(page)
    if code is None:
        return None
    try:
        value = json.loads(code)
        return value if isinstance(value, dict) else None
    except ValueError:
        pass
    return _node_eval(code)


def _text(fragment) -> str:
    if not isinstance(fragment, str) or fragment.strip().startswith("http"):
        return ""                                       # some fields hold a picture link instead of text
    return " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def _page_data(url: str, getter) -> List:
    state = nuxt_state(getter(url))
    return (state or {}).get("data") or []


def _detail(url: str, key: str, getter) -> Dict:
    for block in _page_data(url, getter):
        if isinstance(block, dict) and block.get(key):
            return block[key]
    return {}


def _walk(first_id, url_fmt: str, key: str, next_key: str, getter) -> List[Dict]:
    """Follow the page's own "next" link from one detail page to the next, like a visitor using the arrows, until the end."""
    out, seen, current = [], set(), first_id
    while current and current not in seen and len(seen) < MAX_WALK:
        seen.add(current)
        try:
            detail = _detail(url_fmt.format(id=current), key, getter)
        except FfSiteError:
            break
        if not detail:
            break
        out.append(detail)
        current = (detail.get(next_key) or {}).get("id")
        time.sleep(PAUSE)
    return out


def _first_id(list_url: str, list_key: str, getter):
    for block in _page_data(list_url, getter):
        rows = (block or {}).get(list_key) if isinstance(block, dict) else None
        if rows:
            return rows[0].get("id")
    return None


def _born(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%d/%m")
    except (TypeError, ValueError, OSError, OverflowError):
        return ""


def _characters(getter) -> List[Dict]:
    out = []
    for c in _walk(_first_id(f"{BASE}/chars/", "list", getter), f"{BASE}/chars/{{id}}/", "charDetail", "next_char", getter):
        name = (c.get("name") or "").strip()
        if not name:
            continue
        profile = []
        if c.get("abstract"):
            profile.append(f"{c['abstract'].strip()}.")
        facts = ", ".join(x for x in (f"giới tính {'nam' if c.get('sex') == 1 else 'nữ'}" if c.get("sex") in (1, 2) else "",
                                       f"{c['age']} tuổi" if c.get("age") else "", f"sinh nhật {_born(c.get('birthday'))}" if c.get("birthday") else "") if x)
        if facts:
            profile.append(f"({facts}).")
        story = _text(c.get("introduction", ""))
        if story:
            profile.append(story)
        quote = _text(c.get("abstract_detail", ""))
        if quote:
            profile.append(f"Câu nói đặc trưng: “{quote}”")
        if c.get("ability"):
            profile.append(f"Kỹ năng {c['ability']}: {_text(c.get('ability_introduction', ''))}")
        if c.get("awaken") and c.get("awaken_name"):
            profile.append(f"Thức tỉnh {c['awaken_name']}" + (f" ({c['awaken_abstract']})" if c.get("awaken_abstract") else "") + ": "
                           + " ".join(x for x in (_text(c.get("awaken_introduction", "")),
                                                  f"Kỹ năng {c['awaken_ability']}: {_text(c.get('awaken_ability_introduction', ''))}" if c.get("awaken_ability") else "") if x))
        en = (c.get("en_name") or "").strip()
        out.append({"kind": "character", "name": name, "aliases": en if en and en.lower() != name.lower() else "", "url": f"{BASE}/chars/{c.get('id')}/",
                    "text": "Nhân vật: " + " ".join(profile),
                    "images": [u for u in (c.get("character_pc"), c.get("cover_img"), c.get("head_icon")) if isinstance(u, str) and u.startswith("http")]})
    return out


def _pets(getter) -> List[Dict]:
    out = []
    for p in _walk(_first_id(f"{BASE}/pets/", "list", getter), f"{BASE}/pets/{{id}}/", "petDetail", "next_pet", getter):
        name = (p.get("name") or "").strip()
        if not name:
            continue
        bits = [x for x in (_text(p.get("abstract", "")), _text(p.get("biography", "")),
                            f"Kỹ năng {p['skill_name']}: {_text(p.get('skill_desc', ''))}" if p.get("skill_name") else "") if x]
        out.append({"kind": "pet", "name": name, "aliases": "", "url": f"{BASE}/pets/{p.get('id')}/", "text": "Thú cưng: " + " ".join(bits),
                    "images": [u for u in (p.get("pic4detail"), p.get("pic4list")) if isinstance(u, str) and u.startswith("http")]})
    return out


def _weapons(getter) -> List[Dict]:
    out, seen = [], set()
    categories = []
    for block in _page_data(f"{BASE}/weapons/", getter):
        if isinstance(block, dict) and block.get("weapon_category"):
            categories = [c for c in block["weapon_category"] if c.get("id", -1) != -1]
    for cat in categories:
        try:
            rows = next((b["data"] for b in _page_data(f"{BASE}/weapons/{cat['id']}/", getter) if isinstance(b, dict) and b.get("data") and "count" in b), [])
        except FfSiteError:
            continue
        time.sleep(PAUSE)
        for w in rows:
            if not w.get("name") or w.get("id") in seen:
                continue
            seen.add(w.get("id"))
            stats = ", ".join(f"{label} {w[key]}" for key, label in (("damage", "sát thương"), ("range", "tầm bắn"), ("rate_of_fire", "tốc độ bắn"),
                                                                    ("reload_speed", "nạp đạn"), ("magazine", "băng đạn"), ("accuracy", "độ chính xác"),
                                                                    ("movement_speed", "tốc độ di chuyển")) if w.get(key) is not None)
            tags = ", ".join(w.get("tags") or [])
            out.append({"kind": "weapon", "name": w["name"].strip(), "aliases": "", "url": f"{BASE}/weapons/{cat['id']}/",
                        "text": f"Vũ khí ({cat.get('name', '')}): {_text(w.get('abstract', ''))}." + (f" Chỉ số: {stats}." if stats else "") + (f" Đặc điểm: {tags}." if tags else ""),
                        "images": [w["normal_img"]] if w.get("normal_img") else []})
    return out


def collect_articles(getter=fetch, limit: int = ARTICLES) -> List[Dict]:
    """The newest news / version articles (title, category, date, plain text): events, collaborations and new characters of each version."""
    listing = []
    for block in _page_data(f"{BASE}/news/", getter):
        if isinstance(block, dict) and block.get("newsList"):
            listing = block["newsList"]
    out = []
    for n in listing[:limit]:
        try:
            detail = _detail(f"{BASE}/article/{n['id']}/", "detail", getter)
        except (FfSiteError, KeyError):
            continue
        text = _text(detail.get("content", ""))
        if not text:
            continue
        out.append({"id": int(n["id"]), "title": (n.get("title") or detail.get("title") or "").strip(), "category": n.get("category") or "",
                    "published": n.get("time"), "url": f"{BASE}/article/{n['id']}/", "text": text[:ARTICLE_CHARS]})
        time.sleep(PAUSE)
    return out


def sync_articles(conn, getter=fetch) -> int:
    n = 0
    for a in collect_articles(getter):
        conn.execute("INSERT INTO ff_articles (id, title, category, published, url, text) VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                     "title=excluded.title, category=excluded.category, published=excluded.published, url=excluded.url, text=excluded.text",
                     (a["id"], a["title"], a["category"], a["published"], a["url"], a["text"]))
        n += 1
    conn.commit()
    return n


def collect(getter=fetch) -> List[Dict]:
    """Items from the public pages: {kind, name, aliases, text, images, url}. `getter(url)` returns page HTML (replaceable for tests)."""
    items: List[Dict] = []
    for block in _page_data(f"{BASE}/maps/", getter):
        for m in (block or {}).get("mapList", []) or []:
            parts = [p for p in m.get("map_parts", []) or [] if p.get("name")]
            listing = ", ".join(p["name"].strip() for p in parts)
            items.append({"kind": "location", "name": m["name"].strip(), "aliases": "", "url": f"{BASE}/maps/",
                          "text": f"Bản đồ Free Fire. {m.get('abstract', '').strip()}" + (f" Các khu vực: {listing}." if listing else ""),
                          "images": [u for u in (m.get("map"), m.get("thumbnail")) if u]})
            for p in parts:
                items.append({"kind": "location", "name": p["name"].strip(), "aliases": "", "url": f"{BASE}/maps/",
                              "text": f"Khu vực trên bản đồ {m['name'].strip()}." + (f" {p['abstract'].strip()}" if p.get("abstract") else ""),
                              "images": [u for u in (p.get("img"), p.get("img_zoom")) if u]})
    items += _pets(getter)
    items += _weapons(getter)
    items += _characters(getter)
    for item in items:                                   # picture links from the page: only allowed hosts, the rest named in `rejected`
        item["rejected"] = [u for u in item["images"] if refusal(u, images=True)]
        item["images"] = [u for u in item["images"] if u not in item["rejected"]]
    return items


def _existing(conn, game: str, item: Dict) -> Optional[Dict]:
    key = assets.fold(item["name"])
    for a in assets.list_assets(conn, game, None, None, shared_only=True):
        names = [a["name"]] + [x for x in re.split(r"[,;\n]+", a.get("aliases") or "") if x.strip()]
        if key in {assets.fold(n) for n in names} and (a["kind"] == item["kind"] or item["kind"] in ("character", "pet")):
            return a
    return None


def _with_block(description: str, text: str) -> str:
    return assets.replace_block(description, MARK, text)


def sync(conn, game: str = "FF", created_by: Optional[str] = None, getter=fetch, download=None) -> Dict:
    """Read the website and add / enrich entries. Returns counts {created, enriched, pictures, skipped, rejected} (+ rejected_urls:
    picture addresses outside the allowed hosts, never downloaded; they are also written to the error log)."""
    download = download or (lambda url: fetch(url, binary=True))
    report = {"created": 0, "enriched": 0, "pictures": 0, "skipped": 0, "rejected": 0, "rejected_urls": []}

    def refuse(url: str) -> None:
        report["rejected"] += 1
        if len(report["rejected_urls"]) < 20:
            report["rejected_urls"].append(url)

    for item in collect(getter):
        for url in item.get("rejected", []):
            refuse(url)
        found = _existing(conn, game, item)
        try:
            if found is None:
                aid = assets.create(conn, game, item["kind"], item["name"], _with_block("", item["text"]), item["aliases"], None, created_by)
                report["created"] += 1
            else:
                aid = found["id"]
                new_desc = _with_block(found["description"], item["text"])
                if new_desc != (found["description"] or ""):
                    assets.update(conn, aid, found["name"], found["aliases"], new_desc)
                    report["enriched"] += 1
        except assets.AssetError:
            report["skipped"] += 1
            continue
        have = {r["src_path"] for r in conn.execute("SELECT src_path FROM asset_images WHERE asset_id=?", (aid,))}
        for url in item["images"][:PICS_PER_ITEM]:
            if url in have:
                continue
            if refusal(url, images=True):                                # checked again right before the download
                refuse(url)
                continue
            try:
                assets.add_image(conn, aid, os.path.basename(url.split("?")[0]) or "site.png", download(url), src_path=url,
                                 status="pending")                       # G2: downloaded without a person looking
                report["pictures"] += 1
            except (assets.AssetError, FfSiteError):
                report["skipped"] += 1
    try:
        report["articles"] = sync_articles(conn, getter)
    except (FfSiteError, OSError):
        report["articles"] = 0
    if report["rejected"]:
        from . import diag
        diag.record(conn, "system", "warn", f"đọc website Free Fire: {report['rejected']} địa chỉ ảnh ngoài danh sách cho phép bị từ chối "
                    f"(không tải), ví dụ {report['rejected_urls'][0]} — nếu đó là máy chủ ảnh chính thức, thêm vào FF_SITE_IMAGE_HOSTS",
                    "ff_site_url")
    return report


def summary(report: Dict) -> str:
    return (f"{report['created']} mục mới, {report['enriched']} mục được bổ sung mô tả, {report['pictures']} ảnh chính thức, "
            f"{report.get('articles', 0)} bài tin tức" + (f", {report['skipped']} bỏ qua" if report["skipped"] else "")
            + (f", {report['rejected']} địa chỉ bị từ chối (ngoài danh sách máy chủ cho phép, xem Nhật ký lỗi)" if report.get("rejected") else ""))


# ---- running it: a button (or once a month) starts it in the background; the outcome is kept for the panel ----------------
import threading
from datetime import timedelta

_running = threading.Lock()
INTERVAL_DAYS = 30


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def status(conn) -> Dict:
    from . import lessons
    return {"last": lessons.meta(conn, "ff_site_last"), "text": lessons.meta(conn, "ff_site_text", ""), "running": _running.locked()}


def start_background(db_path: str, game: str = "FF", user: Optional[str] = None, getter=fetch, download=None) -> bool:
    """Read the website in a thread (a few minutes: it downloads the official pictures). One at a time; True if started."""
    from . import diag, lessons
    from .db import connect
    if not _running.acquire(blocking=False):
        return False

    def work():
        conn = connect(db_path)
        try:
            lessons.set_meta(conn, "ff_site_text", "Đang đọc website…")
            report = sync(conn, game, user, getter, download)
            lessons.set_meta(conn, "ff_site_text", summary(report))
            lessons.set_meta(conn, "ff_site_last", _now())
        except Exception as e:  # noqa: BLE001 - a failed read must be visible, not lost
            lessons.set_meta(conn, "ff_site_text", f"Lỗi: {e}")
            diag.record(conn, "system", "warn", f"đọc website Free Fire lỗi: {type(e).__name__}: {e}", "ff_site")
        finally:
            _running.release()

    threading.Thread(target=work, daemon=True, name="ff-site").start()
    return True


def maybe_monthly(db_path: str, game: str = "FF") -> bool:
    """Once a month (when the library already has entries for the game): refresh from the website in the background."""
    from . import lessons
    from .db import connect
    if os.environ.get("FF_SITE_AUTO", "1") == "0":
        return False
    conn = connect(db_path)
    last = lessons.meta(conn, "ff_site_last")
    if last and datetime.now(timezone.utc) - datetime.fromisoformat(last) < timedelta(days=INTERVAL_DAYS):
        return False
    if not last and not conn.execute("SELECT 1 FROM assets WHERE game=? LIMIT 1", (game,)).fetchone():
        return False                                   # never used the library: do not start downloading by surprise
    return start_background(db_path, game)
