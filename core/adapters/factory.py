"""Choose providers from environment variables.

VIDEO_PROVIDER = clipai | mock      (unset = not configured)
IMAGE_PROVIDER = deepix | mock      (unset = not configured)
Tokens come from CLIPAI_TOKEN / DEEPIX_TOKEN and are never written to disk by this project.
"""
import os
from typing import Optional

from ..providers import MockImageProvider, MockVideoProvider

# One simulator per process: a new one on every page rerun would forget the tasks it was given and report them missing.
_MOCKS = {}


def _mock(kind: str, cls):
    if kind not in _MOCKS:
        _MOCKS[kind] = cls()
    return _MOCKS[kind]


def video_provider():
    kind = os.environ.get("VIDEO_PROVIDER", "").strip().lower()
    if kind == "mock":
        return _mock("video", MockVideoProvider)
    if kind == "clipai":
        from .clipai import ClipAIVideoProvider
        return ClipAIVideoProvider.from_env()
    return None


def image_provider():
    kind = os.environ.get("IMAGE_PROVIDER", "").strip().lower()
    if kind == "mock":
        return _mock("image", MockImageProvider)
    if kind == "deepix":
        from .deepix import DeepixImageProvider
        return DeepixImageProvider.from_env()
    return None


def subject_library():
    """SUBJECT_PROVIDER = clipai | mock. Unset: follows VIDEO_PROVIDER (clipai -> real library, mock -> mock)."""
    kind = os.environ.get("SUBJECT_PROVIDER", "").strip().lower() or os.environ.get("VIDEO_PROVIDER", "").strip().lower()
    if kind == "mock":
        from .clipai_subjects import MockSubjectLibrary
        return MockSubjectLibrary()
    if kind == "clipai":
        from .clipai_subjects import ClipAISubjectLibrary
        return ClipAISubjectLibrary.from_env()
    return None


def describe(provider) -> Optional[str]:
    if provider is None:
        return None
    return getattr(provider, "name", type(provider).__name__)
