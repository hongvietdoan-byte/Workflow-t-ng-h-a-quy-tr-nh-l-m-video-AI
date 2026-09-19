import os

from core.db import connect
from core.pipeline import Pipeline

DEFAULT_DB = os.path.join(os.path.dirname(__file__), "..", "data", "manifest.sqlite")


def get_pipeline() -> Pipeline:
    return Pipeline(connect(os.environ.get("PIPELINE_DB", DEFAULT_DB)))
