"""C-FIX-THAP-3 (cloud-D 21/10) — 3 lỗi THẤP từ rà 20/10, cờ giữ TẮT.
(1) release_gate.summary: chỉ THIẾU ĐO (G4 đối soát luôn KHÔNG RÕ) không gọi là "CHƯA ĐẠT" — câu "đạt 7 · chưa đo 1 · chưa đạt 0"; `ok` vẫn
    False (KHÔNG RÕ không bao giờ là đạt).
(2) release_gate.check(cache=…): final_qc.run + delivery.status nhớ theo bản dựng (id bản final + id output mới nhất + mtime) — Streamlit
    rerun không chạy lại; bản dựng / lớp mới → đo lại; quá CACHE_TTL_S → đo lại (thiết lập đổi mà chưa dựng lại vẫn hiện trong ≤ TTL).
(3) devsys/errors_page.py: width="stretch" thay use_container_width (như mọi nơi khác)."""
import os
from unittest import mock

from core import release_gate as G

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _res(dat, chua, khong_ro):
    items = [{"id": f"G{i}", "label": "x", "state": G.DAT, "why": "ok"} for i in range(dat)]
    items += [{"id": "G4", "label": "Đối soát chi phí", "state": G.KHONG_RO, "why": "chưa đối soát"}] * khong_ro
    items += [{"id": "G1", "label": "shot", "state": G.CHUA, "why": "1 shot chưa duyệt"}] * chua
    return {"ok": chua == 0 and khong_ro == 0, "items": items, G.DAT: dat, G.CHUA: chua, G.KHONG_RO: khong_ro}


# ---- (1) câu ---------------------------------------------------------------------------------------------------------------------
def test_only_unmeasured_is_not_called_not_passed():
    text = G.summary(_res(7, 0, 1))
    head = text.splitlines()[0]
    assert "CHƯA ĐẠT" not in head and "đạt 7 · chưa đo 1 · chưa đạt 0" in head and "vẫn xuất được" in head
    assert "G4" in text                                                    # mục chưa đo vẫn liệt kê lý do


def test_a_real_failure_still_says_not_passed_with_counts():
    head = G.summary(_res(6, 1, 1)).splitlines()[0]
    assert "CHƯA ĐẠT" in head and "đạt 6 · chưa đo 1 · chưa đạt 1" in head


def test_all_passed_unchanged():
    assert G.summary(_res(8, 0, 0)) == "✅ Cổng phát hành: ĐẠT 8/8"


# ---- (2) cache -------------------------------------------------------------------------------------------------------------------
class _Conn:
    def __init__(self):
        self.final, self.last = 5, 9

    def execute(self, sql, args=()):
        val = self.final if "kind=" in sql else self.last
        return mock.Mock(fetchone=lambda: (val,))


def _check(cache, conn, calls):
    p = mock.Mock(conn=conn)
    qc = {"ok": True, "blocks": 0, "warns": 0, "issues": []}
    st = {"final": {"state": "fresh"}, "layers": []}

    def run(*a, **k):
        calls.append("qc")
        return qc

    def status(*a, **k):
        calls.append("status")
        return st
    with mock.patch("core.final_qc.run", side_effect=run), mock.patch("core.delivery.status", side_effect=status), \
            mock.patch.object(G, "_render_mtime", return_value=1.0):
        for gid in ("G2", "G3"):
            fn = {"G2": G._g2_final_qc, "G3": G._g3_layers_current}[gid]
            fn(p, 31, "/d", cache)


def test_rerun_on_the_same_render_measures_once():
    cache, conn, calls = {}, _Conn(), []
    _check(cache, conn, calls)
    _check(cache, conn, calls)
    assert calls == ["qc", "status"]


def test_a_new_render_or_layer_measures_again():
    cache, conn, calls = {}, _Conn(), []
    _check(cache, conn, calls)
    conn.last = 10                                                         # lớp phụ đề / card mới
    _check(cache, conn, calls)
    conn.final = 6                                                         # bản dựng mới
    _check(cache, conn, calls)
    assert calls == ["qc", "status"] * 3


def test_cache_expires():
    cache, conn, calls = {}, _Conn(), []
    with mock.patch.object(G.time, "monotonic", return_value=100.0):
        _check(cache, conn, calls)
    with mock.patch.object(G.time, "monotonic", return_value=100.0 + G.CACHE_TTL_S + 1):
        _check(cache, conn, calls)
    assert calls == ["qc", "status"] * 2


def test_no_cache_keeps_the_old_behaviour():
    calls = []
    _check(None, _Conn(), calls)
    _check(None, _Conn(), calls)
    assert calls == ["qc", "status"] * 2


def test_step5_passes_a_session_cache():
    src = open(os.path.join(ROOT, "dashboard", "steps", "step5.py"), encoding="utf-8").read()
    block = src[src.index("def _deliver_button"):src.index("def _deliver_button") + 2000]
    assert "release_gate.check(p, pid, C.DATA, cache=" in block


# ---- (3) width -------------------------------------------------------------------------------------------------------------------
def test_errors_page_uses_width_stretch():
    src = open(os.path.join(ROOT, "devsys", "errors_page.py"), encoding="utf-8").read()
    assert "use_container_width" not in src and 'width="stretch"' in src
