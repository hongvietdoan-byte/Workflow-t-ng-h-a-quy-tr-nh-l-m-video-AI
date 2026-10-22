"""pytest plugin (scratch, not in the repo): force feature flags for a test run.

FLAGMATRIX_ON  = "a,b"  flags forced ON
FLAGMATRIX_OFF = "c,d"  flags forced OFF
FLAGMATRIX_MODE = "soft" (default) | "hard"
  soft = what `verified: True` (khóa) does under tests: FEATURES[n]["verified"] = True (default ON; tests/__init__ keeps
         _TEST_BYPASS so a test's own FEATURE_X=0 / flags_off still wins). OFF: verified/default_on = False and FEATURE_X dropped.
  hard = features.state() returns "on"/"off" for those names whatever the test chose (only a test that patches features.on itself
         escapes) — shows which tests depend on the flag's value.
Load: PYTHONPATH=<this folder> py -m pytest -p flagforce ...
"""
import os


def _names(var):
    return [x.strip() for x in os.environ.get(var, "").split(",") if x.strip()]


def pytest_configure(config):
    on, off = _names("FLAGMATRIX_ON"), _names("FLAGMATRIX_OFF")
    if not on and not off:
        return
    mode = os.environ.get("FLAGMATRIX_MODE", "soft")
    import core.features as f
    missing = [n for n in on + off if n not in f.FEATURES]
    if missing:
        raise RuntimeError(f"flagforce: unknown flags {missing}")
    if mode == "soft":
        for n in on:
            f.FEATURES[n]["verified"] = True
        for n in off:
            f.FEATURES[n]["verified"] = False
            f.FEATURES[n].pop("default_on", None)
            os.environ.pop("FEATURE_" + n.upper(), None)
    else:
        orig = f.state
        on_s, off_s = set(on), set(off)

        def state(name):
            if name in on_s:
                return "on"
            if name in off_s:
                return "off"
            return orig(name)
        f.state = state
    config._flagforce = (mode, on, off)


def pytest_runtest_teardown(item):
    if os.environ.get("FLAGMATRIX_DUMP") == "1":
        import sys
        mod = sys.modules.get("core.runner")
        if mod is not None:
            print(f"\n[flagforce] {item.nodeid} WAIT_REASONS={dict(mod.WAIT_REASONS)} PREGEN_HELD={dict(mod.PREGEN_HELD)}")


def pytest_report_header(config):
    ff = getattr(config, "_flagforce", None)
    if ff:
        return f"flagforce mode={ff[0]} ON={','.join(ff[1])} OFF={','.join(ff[2])}"
