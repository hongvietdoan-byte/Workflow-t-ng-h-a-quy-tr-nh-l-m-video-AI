"""Hook SessionStart của Claude Code: đầu MỌI phiên mới in gói bàn giao mới nhất ở mục 📨 BÀN GIAO đầu TODO.md để phiên tự đọc
và làm tiếp (người dùng 16/10: skill vòng làm việc chỉ nạp khi người dùng gõ "tiếp tục", phiên mới không tự biết có gói).

Đọc TODO.md trên origin/main (git fetch nhanh, có hạn giờ) vì worktree mới có thể cắt từ commit cũ; lỗi mạng → dùng bản cục bộ.
Gói bàn giao = dòng `  - [..] ... ĐỌC ĐẦU TIÊN ...` mới nhất trong mục 📨. Phiên nhận gói thì sửa "ĐỌC ĐẦU TIÊN" thành
"ĐÃ NHẬN <giờ>" → hook không thúc phiên sau làm lại. Không bao giờ làm hỏng phiên: mọi lỗi → in một dòng báo, thoát 0.

    py -X utf8 tools/session_handoff.py          (hook gọi) in gói bàn giao + trạng thái worktree so với origin/main

21/10 (người dùng): phiên chính chạm ~70 % context từng gọi `clear_session` → ứng dụng LƯU TRỮ phiên, Remote Control đứt. Nay context
được nén TỰ ĐỘNG trong cùng phiên (`CLAUDE_CODE_AUTO_COMPACT_WINDOW=350000` ở .claude/settings.json, 22/10) và hook chạy cả khi `compact`: đọc
`source` từ JSON hook gửi qua stdin, sau khi nén thì bảo chính phiên này làm tiếp theo gói mới nhất (kể cả gói nó đã ghi ĐÃ NHẬN).
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARK = "ĐỌC ĐẦU TIÊN"
TAKEN = "ĐÃ NHẬN"
SECTION = "📨 BÀN GIAO"
MAX_CHARS = 6000


def _git(*args: str, timeout: float = 10) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip() or f"git {' '.join(args)} lỗi {r.returncode}")
    return r.stdout


def handoff_lines(todo: str) -> list:
    """Các dòng bàn giao (`  - [..]`) trong mục 📨, giữ thứ tự file (mới nhất ở đầu)."""
    out, inside = [], False
    for line in todo.splitlines():
        if SECTION in line and line.lstrip().startswith("- "):
            inside = True
            continue
        if inside:
            if line.startswith("  - ["):
                out.append(line.strip()[2:])
            elif line.strip() and not line.startswith("    "):
                break
    return out


def _bold_head(line: str) -> str:
    """Cụm in đậm đầu tiên của dòng (`**…**`) — nơi gói ghi ĐỌC ĐẦU TIÊN; dòng khác chỉ NHẮC tới cụm này (vd 16:08) không tính."""
    a = line.find("**")
    b = line.find("**", a + 2) if a >= 0 else -1
    return line[a + 2:b] if b > a else ""


def latest_pack(lines: list):
    """Gói bàn giao mới nhất (cụm in đậm đầu dòng có ĐỌC ĐẦU TIÊN hoặc ĐÃ NHẬN thay chỗ nó); None nếu không có."""
    for ln in lines:
        head = _bold_head(ln)
        if MARK in head or TAKEN in head:
            return ln
    return None


COMPACT_NOTE = (
    "PHIÊN NÀY VỪA TỰ NÉN CONTEXT (auto-compact ~340k token, cùng phiên — Remote Control vẫn nối). Không chờ người dùng: nạp skill "
    "`vong-lam-viec-theo-plan`, đọc gói bàn giao mới nhất dưới đây (do chính phiên này ghi trước khi nén) + file nó trỏ tới, "
    "`CronList` (thiếu lịch điều phối thì tạo lại theo gói), rồi LÀM TIẾP đúng việc dở. KHÔNG gọi clear_session / archive / "
    "start_session (lưu trữ phiên, đứt remote — người dùng 21/10).")


def render(todo: str, source: str, behind: int = 0, event: str = "startup") -> str:
    lines = handoff_lines(todo)
    if not lines:
        return f"[bàn giao] Không thấy mục {SECTION} trong TODO.md ({source})."
    head = [f"[bàn giao] Đọc từ {source}."]
    if event == "compact":
        pack = latest_pack(lines) or lines[0]
        head.append(COMPACT_NOTE)
        if behind:
            head.append(f"Worktree chậm {behind} commit so với origin/main → `git fetch origin && git merge --ff-only origin/main`.")
        body = pack if len(pack) <= MAX_CHARS else pack[:MAX_CHARS] + " …(cắt — đọc đủ trong TODO.md)"
        return "\n".join(head + ["GÓI:", body])
    if behind:
        head.append(f"Worktree đang chậm {behind} commit so với origin/main → chạy "
                    "`git fetch origin && git merge --ff-only origin/main` trước khi làm.")
    pack = latest_pack(lines)
    if pack is None:
        head.append("Không có gói 'PHIÊN KẾ … ĐỌC ĐẦU TIÊN'. Dòng bàn giao mới nhất (tham khảo):")
        return "\n".join(head + [lines[0][:1500]])
    if MARK not in pack:
        head.append("Gói bàn giao mới nhất ĐÃ có phiên nhận (ĐÃ NHẬN) — chỉ tham khảo, không làm lại trừ khi người dùng bảo:")
        return "\n".join(head + [pack[:1500]])
    head.append(
        "CÓ GÓI BÀN GIAO CHƯA AI NHẬN. Việc ĐẦU TIÊN của phiên này (người dùng 16/10): nạp skill `vong-lam-viec-theo-plan` "
        "(Skill tool) rồi làm theo mục 1 — đọc gói dưới đây + các file nó trỏ tới, sửa 'ĐỌC ĐẦU TIÊN' thành "
        "'ĐÃ NHẬN <giờ thật> (<tên phiên>)' trong TODO.md, commit + push, rồi LÀM TIẾP các việc 'phiên kế làm' theo thứ tự. "
        "Việc ghi CHỜ người dùng chỉ nhắc lại, không tự làm; việc tốn tiền phải hỏi trước. Nếu tin nhắn đầu của người dùng "
        "là việc khác thì làm việc người dùng trước và nhắc một dòng là có gói đang chờ.")
    body = pack if len(pack) <= MAX_CHARS else pack[:MAX_CHARS] + " …(cắt — đọc đủ trong TODO.md)"
    return "\n".join(head + ["GÓI:", body])


def hook_event(raw: str) -> str:
    """`source` của SessionStart (startup | resume | clear | compact | fork) từ JSON hook gửi qua stdin; lỗi → startup."""
    try:
        return str((json.loads(raw) or {}).get("source") or "startup")
    except (ValueError, AttributeError):
        return "startup"


def main() -> int:
    event = "startup"
    try:
        if not sys.stdin.isatty():
            event = hook_event(sys.stdin.read())
    except Exception:  # noqa: BLE001 - không có stdin: coi như mở phiên
        pass
    try:
        source, behind = "origin/main", 0
        try:
            _git("fetch", "-q", "origin", "main", timeout=15)
        except Exception as e:  # mạng lỗi: vẫn đọc ref origin/main đã có
            print(f"[bàn giao] git fetch lỗi ({str(e)[:120]}) — dùng origin/main đã có trên máy.")
        try:
            todo = _git("show", "origin/main:TODO.md")
            behind = int(_git("rev-list", "--count", "HEAD..origin/main").strip() or 0)
        except Exception:
            source = "TODO.md cục bộ"
            with open(os.path.join(ROOT, "TODO.md"), encoding="utf-8") as f:
                todo = f.read()
        print(render(todo, source, behind, event))
    except Exception as e:
        print(f"[bàn giao] Hook không đọc được TODO.md ({str(e)[:200]}) — tự đọc mục {SECTION} đầu TODO.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
