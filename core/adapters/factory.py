"""Choose providers from environment variables.

VIDEO_PROVIDER = clipai | mock      (unset = not configured)
IMAGE_PROVIDER = deepix | mock      (unset = not configured)
Tokens come from CLIPAI_TOKEN / DEEPIX_TOKEN and are never written to disk by this project.
"""
import os
from typing import Optional

from ..providers import MockImageProvider, MockVideoProvider


def video_provider():
    kind = os.environ.get("VIDEO_PROVIDER", "").strip().lower()
    if kind == "mock":
        return MockVideoProvider()
    if kind == "clipai":
        from .clipai import ClipAIVideoProvider
        return ClipAIVideoProvider.from_env()
    return None


def image_provider():
    kind = os.environ.get("IMAGE_PROVIDER", "").strip().lower()
    if kind == "mock":
        return MockImageProvider()
    if kind == "deepix":
        from .deepix import DeepixImageProvider
        return DeepixImageProvider.from_env()
    return None


def describe(provider) -> Optional[str]:
    if provider is None:
        return None
    return getattr(provider, "name", type(provider).__name__)
