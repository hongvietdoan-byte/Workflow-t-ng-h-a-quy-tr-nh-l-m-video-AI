"""B1 học việc (08/10): FEATURE_<NAME>=1 on one of the 7 🎓 flags now means học việc (no effect), not ON. Tests that need such a flag
really ON switch it on the 🧪 way (data/feature_settings.json "flags", the file of this test run) — the only real ON."""
import contextlib

from core import features


def _set(names, value):
    prev = {n: features.settings()["flags"].get(n) for n in names}
    prev_modes = {n for n in names if n in (features.settings().get("modes") or {})}
    features.save_settings(flags={n: value for n in names})
    return prev, prev_modes


def _restore(prev, prev_modes):
    features.save_settings(flags=prev)
    if prev_modes:
        features.save_settings(modes={n: "trainee" for n in prev_modes})


def flags_on(tc, *names, value=True):
    """Switch `names` really ON (value=False: really OFF) for the rest of the test `tc`; restored by addCleanup."""
    tc.addCleanup(_restore, *_set(names, value))


def flags_trainee(tc, *names):
    """Put `names` in 🎓 học việc (the 🧪 "modes" choice) for the rest of the test `tc`; restored by addCleanup."""
    s = features.settings()
    prev = {n: ("trainee" if n in (s.get("modes") or {}) else
                (None if s["flags"].get(n) is None else ("on" if s["flags"][n] else "off"))) for n in names}
    features.save_settings(modes={n: "trainee" for n in names})
    tc.addCleanup(features.save_settings, modes=prev)


def flags_off(tc, *names):
    flags_on(tc, *names, value=False)


def flags_clear(*names):
    """Drop the 🧪 choice (back to the default rule) — in place of os.environ.pop("FEATURE_X")."""
    features.save_settings(flags={n: None for n in names})


@contextlib.contextmanager
def flags_on_ctx(*names, value=True):
    saved = _set(names, value)
    try:
        yield
    finally:
        _restore(*saved)


def flags_on_deco(*names):
    """Decorator form (in place of @mock.patch.dict(os.environ, {"FEATURE_X": "1"}))."""
    def wrap(fn):
        import functools

        @functools.wraps(fn)
        def inner(*a, **kw):
            with flags_on_ctx(*names):
                return fn(*a, **kw)
        return inner
    return wrap
