"""M82: lối vào Cơ bản độc lập; pha B mới nối vào app/header."""


def enabled():
    from core import features
    return features.on("simple_mode")


def render(p, pid, data_dir):
    if not enabled():
        return False
    from .views import render_workspace
    render_workspace(p, pid, data_dir)
    return True
