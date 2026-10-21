"""V3.1 M7.2 (C-M72, cloud-C 21/10) — sổ v31-ep-k4-k6-flag-baseline-reset-2026-10-21 + docs/BANG_CHUNG_CHOT_CO_2026-10-21.md mục 3 (thứ tự F).
Baseline cờ trong git (data/flag_baseline.json = trạng thái cờ sản xuất) CHỈ áp khi máy CHƯA có data/feature_settings.json. Thứ tự:
REMOVED → khóa → 🧪 → preset → env → baseline có bảo vệ → mặc định. Bảo vệ: không bật cờ costs / OPT_IN_ONLY; cờ học việc tối đa trainee;
bộ test tắt baseline (FEATURE_BASELINE_FILE rỗng). effective_config() + config_hash() + drift. Nút ↺ Bỏ mọi lựa chọn riêng: preview,
xác nhận, sao lưu, khôi phục. Bất biến: 0 cờ đổi khi có cấu hình riêng; 0 cờ costs bị bật trên máy trống."""
import json
import os
from unittest import mock

import pytest

from core import features as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COSTLY = sorted({n for n, m in F.FEATURES.items() if m.get("costs")} | set(F.OPT_IN_ONLY))


def _plain(name):
    """Một cờ thường: không khóa, không tốn tiền, không học việc, mặc định tắt."""
    m = F.FEATURES[name]
    return not m["verified"] and not m.get("default_on") and not m.get("costs") and name not in F.OPT_IN_ONLY \
        and not m.get("trainee") and name not in F.REMOVED


PLAIN = sorted(n for n in F.FEATURES if _plain(n))
TRAINEE = sorted(n for n in F.trainee_list() if not F.FEATURES[n]["verified"] and not F.FEATURES[n].get("costs")
                 and n not in F.OPT_IN_ONLY and n not in F.REMOVED)


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """Máy trống: tệp 🧪 KHÔNG có, baseline ở tmp, khóa thật (không _TEST_BYPASS), không FEATURE_ env của cờ."""
    settings = tmp_path / "feature_settings.json"
    base = tmp_path / "flag_baseline.json"
    monkeypatch.setenv("FEATURE_SETTINGS_FILE", str(settings))
    monkeypatch.setenv("FEATURE_BASELINE_FILE", str(base))
    monkeypatch.delenv("FEATURE_BASELINE", raising=False)
    for k in [k for k in os.environ if k.startswith("FEATURE_") and k[8:].lower() in F.FEATURES]:
        monkeypatch.delenv(k)
    monkeypatch.setattr(F, "_TEST_BYPASS", False)

    def write_base(flags):
        base.write_text(json.dumps({"flags": flags, "captured": "test"}), encoding="utf-8")
    return settings, base, write_base


def test_tests_run_without_baseline():
    assert os.environ.get("FEATURE_BASELINE_FILE") == ""                    # tests/__init__.py: bộ test tắt baseline
    assert F.baseline_active() is False


def test_baseline_fills_an_empty_machine(machine):
    settings, base, write = machine
    name = PLAIN[0]
    assert F.state(name) == "off"
    write({name: "on"})
    assert F.baseline_active() and F.state(name) == "on" and F.source(name) == "baseline"
    assert "baseline" in F.why_state(name)


def test_baseline_never_applies_once_the_machine_has_its_own_settings(machine):
    settings, base, write = machine
    write({n: "on" for n in PLAIN})
    settings.write_text(json.dumps({"preset": "custom", "flags": {}}), encoding="utf-8")     # cấu hình riêng (kể cả rỗng)
    assert not F.baseline_active()
    assert [n for n in PLAIN if F.state(n) != "off"] == []                 # bất biến: 0 cờ đổi khi có cấu hình riêng


def test_env_and_lock_and_removed_beat_baseline(machine, monkeypatch):
    settings, base, write = machine
    a, b = PLAIN[0], PLAIN[1]
    locked = next(n for n, m in F.FEATURES.items() if m["verified"] and n not in F.REMOVED)
    removed = next(iter(F.REMOVED))
    write({a: "on", b: "on", locked: "off", removed: "on"})
    monkeypatch.setenv("FEATURE_" + a.upper(), "0")
    assert F.state(a) == "off" and F.source(a) == "env"
    assert F.state(b) == "on"
    assert F.state(locked) == "on"
    assert F.state(removed) == "off"


def test_guard_no_costly_flag_turned_on_and_trainee_at_most(machine):
    settings, base, write = machine
    write({n: "on" for n in F.FEATURES})                                   # baseline xấu nhất: mọi cờ bật
    before = {n: F.default_state(n) for n in COSTLY}
    assert {n: F.state(n) for n in COSTLY if F.state(n) != before[n]} == {}  # bất biến: 0 cờ costs / OPT_IN bị bật
    for n in TRAINEE:
        assert F.state(n) == "trainee", n                                  # học việc tối đa trainee
    write({n: "trainee" for n in F.FEATURES})
    assert all(F.state(n) == "trainee" for n in TRAINEE)
    assert all(F.state(n) == "off" for n in PLAIN)                         # "trainee" cho cờ không có học việc → bỏ qua


def test_baseline_can_be_switched_off(machine, monkeypatch):
    settings, base, write = machine
    write({PLAIN[0]: "on"})
    monkeypatch.setenv("FEATURE_BASELINE", "0")
    assert not F.baseline_active() and F.state(PLAIN[0]) == "off"
    monkeypatch.delenv("FEATURE_BASELINE")
    monkeypatch.setenv("FEATURE_BASELINE_FILE", "")
    assert not F.baseline_active()


def test_broken_baseline_is_said_not_silent(machine):
    settings, base, write = machine
    base.write_text("{không phải json", encoding="utf-8")
    assert F.state(PLAIN[0]) == "off"
    assert any("baseline" in n for n in F.baseline_problems())


def test_effective_config_and_hash(machine):
    settings, base, write = machine
    cfg = F.effective_config()
    assert set(cfg["flags"]) == set(F.FEATURES) and cfg["hash"] == F.config_hash()
    assert cfg["sources"][PLAIN[0]] == "default"
    h = F.config_hash()
    write({PLAIN[0]: "on"})
    assert F.config_hash() != h and F.config_hash() == F.config_hash()


def test_drift_said_for_a_flag_on_in_the_previous_project(machine, tmp_path):
    settings, base, write = machine
    data = tmp_path / "projects"
    write({PLAIN[0]: "on", PLAIN[1]: "on"})
    F.remember_config(str(data), 30)
    assert F.drift(str(data), 31) == []                                    # cùng cấu hình: im lặng
    write({PLAIN[1]: "on"})                                                # PLAIN[0] nay tắt
    got = F.drift(str(data), 31)
    assert any(PLAIN[0] in d and "#30" in d for d in got)
    snap = json.loads((data / "30" / "flag_config.json").read_text(encoding="utf-8"))
    snap["machine"] = "may-khac"
    (data / "30" / "flag_config.json").write_text(json.dumps(snap), encoding="utf-8")
    assert any("máy khác" in d for d in F.drift(str(data), 31))


def test_baseline_capture_then_diff_is_zero(machine, capsys):
    settings, base, write = machine
    settings.write_text(json.dumps({"preset": "custom", "flags": {PLAIN[0]: True, COSTLY[0]: True}}), encoding="utf-8")
    assert F.main(["--baseline-capture"]) == 0
    saved = json.loads(base.read_text(encoding="utf-8"))
    assert saved["flags"][PLAIN[0]] == "on" and saved["hash"] == F.config_hash()
    capsys.readouterr()
    assert F.main(["--baseline-diff"]) == 0
    out = capsys.readouterr().out
    assert "máy này: 0 cờ đổi" in out
    d = F.baseline_diff()
    assert d["here"] == [] and COSTLY[0] in {r["name"] for r in d["fresh"]}     # máy mới: cờ tốn tiền KHÔNG theo baseline (có lý do)
    assert all(r["why"] for r in d["fresh"])


def test_reset_preview_backup_and_restore(machine):
    settings, base, write = machine
    F.save_settings(flags={PLAIN[0]: True, PLAIN[1]: True})
    prev = F.reset_preview()
    assert {r["name"] for r in prev} == {PLAIN[0], PLAIN[1]} and all(r["now"] == "on" and r["after"] == "off" for r in prev)
    backup = F.reset_choices()
    assert os.path.isfile(backup) and F.settings()["flags"] == {}
    assert backup in [b["path"] for b in F.list_backups()]
    F.save_settings(flags={PLAIN[2]: True})
    F.restore_settings(backup)
    assert F.settings()["flags"] == {PLAIN[0]: True, PLAIN[1]: True}
    assert len(F.list_backups()) >= 2                                     # khôi phục cũng sao lưu bản đang dùng trước
    with pytest.raises(ValueError):
        F.restore_settings(str(base))                                      # không phải bản sao lưu → từ chối


def test_header_reset_asks_with_a_preview_and_backs_up():
    src = open(os.path.join(ROOT, "dashboard", "header.py"), encoding="utf-8").read()
    i = src.index("Bỏ mọi lựa chọn riêng")
    block = src[i - 400:i + 2500]
    assert "reset_preview(" in block and "reset_choices(" in block and "restore_settings(" in block
    assert "feat_reset_yes" in block                                       # bấm lần 2 mới làm (xác nhận)
    assert "save_settings(flags={k: None" not in block                     # không còn xóa một bấm, không sao lưu


def test_runner_remembers_and_before_run_says_drift(machine, tmp_path):
    from core import before_run
    from core.db import connect
    from core.pipeline import Pipeline
    from core.runner import ImageRunner
    settings, base, write = machine
    data = tmp_path / "projects"
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    a, b = p.create_project("a"), p.create_project("b")
    write({PLAIN[0]: "on"})
    r = ImageRunner(p, None, str(data))
    r._remember_flags(a)
    snap = data / str(a) / "flag_config.json"
    first = json.loads(snap.read_text(encoding="utf-8"))
    r._remember_flags(a)
    again = json.loads(snap.read_text(encoding="utf-8"))
    assert again["hash"] == first["hash"] and again["at"] >= first["at"]   # mỗi lần gửi: `at` mới (drift chọn dự án gửi cuối)
    write({})
    res = before_run.collect(p.conn, str(data), b)
    texts = [i["text"] for g in res["groups"] for i in g["items"]]
    assert any("Drift cấu hình cờ" in t and PLAIN[0] in t for t in texts)


# ---- rà khâu C-M72 --------------------------------------------------------------------------------------------------------------
def test_paid_flags_without_costs_meta_are_never_turned_on(machine):
    from core import before_run
    settings, base, write = machine
    paid = sorted(n for n in before_run.PAID_FLAGS if n in F.FEATURES and not F.FEATURES[n]["verified"])
    write({n: "on" for n in paid})
    assert [n for n in paid if F.state(n) != F.default_state(n)] == []


def test_first_save_on_a_baseline_machine_keeps_the_baseline(machine):
    settings, base, write = machine
    a, b = PLAIN[0], PLAIN[1]
    t = TRAINEE[0]
    write({a: "on", t: "on"})
    assert F.state(a) == "on" and F.state(t) == "trainee"
    F.save_settings(flags={b: True})                                       # lần lưu đầu tạo tệp 🧪 → baseline thôi áp
    assert not F.baseline_active()
    assert (F.state(a), F.state(b), F.state(t)) == ("on", "on", "trainee")   # không "rơi vực" về mặc định
    assert F.source(a) == "settings"


def test_reset_preview_never_touches_the_shared_cache(machine):
    settings, base, write = machine
    F.save_settings(flags={PLAIN[0]: True})
    seen = []
    real = F.state

    def spy(name, *a, **k):
        seen.append(F._SETTINGS["data"]["flags"].get(PLAIN[0]))           # luồng khác đọc giữa lúc xem trước
        return real(name, *a, **k)
    with mock.patch.object(F, "state", spy):
        F.reset_preview()
    assert seen and all(v is True for v in seen)


def test_drift_picks_the_project_that_sent_last(machine, tmp_path):
    settings, base, write = machine
    data = tmp_path / "projects"
    write({PLAIN[0]: "on"})
    F.remember_config(str(data), 29)                                       # #29 gửi trước, PLAIN[0] bật
    write({})
    F.remember_config(str(data), 30)                                       # #30 gửi SAU CÙNG, PLAIN[0] tắt
    os.utime(data / "29" / "flag_config.json", (2e9, 2e9))                 # mtime #29 mới hơn — không được quyết định
    assert F.drift(str(data), 31) == []                                    # so với #30 (gửi cuối): không drift


def test_restore_refuses_a_non_json_and_backups_are_capped(machine):
    settings, base, write = machine
    F.save_settings(flags={PLAIN[0]: True})
    for _ in range(F.MAX_BACKUPS + 3):
        F.backup_settings()
    assert len(F.list_backups()) == F.MAX_BACKUPS
    odd = os.path.join(F._backup_dir(), "feature_settings.x.txt")
    open(odd, "w").write("{}")
    with pytest.raises(ValueError):
        F.restore_settings(odd)


def test_tools_that_make_a_fresh_settings_file_switch_baseline_off():
    for rel in ("tools/ui_v2_acceptance.py", "tools/ui_snapshot.py", "tools/golden_db_replay.py"):
        src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        assert 'FEATURE_BASELINE="0"' in src or '"FEATURE_BASELINE": "0"' in src, rel
    src = open(os.path.join(ROOT, "tools", "pregen_check.py"), encoding="utf-8").read()
    assert "json.dump({}, f)" not in src                                   # máy không có tệp 🧪: không tự tạo tệp rỗng (baseline lệch nút Gen)


def test_backups_are_not_committed():
    ign = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read().split()
    assert "data/backup/" in ign and "data/*.tmp" in ign
