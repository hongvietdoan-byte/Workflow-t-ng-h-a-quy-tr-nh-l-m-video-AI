"""One-shot live trial: 1 image (Deepix) -> 1 video clip (Clip AI). THIS SPENDS CREDITS.

    py -m core.adapters.trial --yes
    py -m core.adapters.trial --yes --model seedance
    py -m core.adapters.trial --yes --image path\\to\\existing.png      (skip Deepix, only the video step)

Without --yes nothing is sent. Results and a report are written to data/trial/ (git-ignored).
Tokens come from the environment and are never printed.
"""
import argparse
import json
import os
import sys
import time
from typing import Callable, Optional

from ..providers import ProviderError
from . import factory

DEFAULT_IMAGE_PROMPT = ("Wide cinematic shot of a lone traveler in a red cloak walking along a misty mountain ridge at "
                        "sunrise, golden rim light, volumetric fog, layered mountains, 35mm, shallow depth of field, "
                        "no text, no watermark")
DEFAULT_MOTION_PROMPT = ("Slow push-in behind the traveler as they walk forward along the ridge, the cloak sways in the "
                         "wind, mist drifts slowly across the mountains, calm and quiet")


def _wait(provider, external_id: str, label: str, interval: float, timeout: float,
          sleep: Callable[[float], None], clock: Callable[[], float]):
    start = clock()
    while True:
        status = provider.status(external_id)
        print(f"  [{label}] {status.state} ({int(clock() - start)}s)")
        if status.state != "running":
            return status
        if clock() - start > timeout:
            raise ProviderError(f"{label} did not finish within {int(timeout)}s", code="timeout")
        sleep(interval)


def run_trial(args, image_provider=None, video_provider=None, sleep=time.sleep, clock=time.time) -> dict:
    os.makedirs(args.out, exist_ok=True)
    report = {"steps": []}
    image_path = args.image
    if image_path is None:
        image_provider = image_provider or factory.image_provider()
        if image_provider is None:
            raise ProviderError("IMAGE_PROVIDER is not set (use deepix), or pass --image", code="config")
        print(f"Step 1/2: generating an image with {image_provider.name} ...")
        task = image_provider.submit(args.image_prompt)
        status = _wait(image_provider, task, "image", 5, 300, sleep, clock)
        if status.state != "succeeded":
            raise ProviderError(f"image failed: {status.error_code}: {status.error_message}", code="image_failed")
        image_path = image_provider.download(task, os.path.join(args.out, "trial_image.png"))
        report["steps"].append({"step": "image", "provider": image_provider.name, "task": task, "file": image_path})
        print(f"  saved {image_path}")
    video_provider = video_provider or factory.video_provider()
    if video_provider is None:
        raise ProviderError("VIDEO_PROVIDER is not set (use clipai)", code="config")
    print(f"Step 2/2: generating a {args.duration}s clip with {video_provider.name} (model={args.model}) ...")
    task = video_provider.submit(image_path, args.motion_prompt, None, args.duration, args.model)
    status = _wait(video_provider, task, "video", 10, 900, sleep, clock)
    if status.state != "succeeded":
        raise ProviderError(f"video failed: {status.error_code}: {status.error_message}", code="video_failed")
    video_path = video_provider.download(task, os.path.join(args.out, "trial_video.mp4"))
    report["steps"].append({"step": "video", "provider": video_provider.name, "task": task, "model": args.model,
                            "file": video_path, "bytes": os.path.getsize(video_path)})
    print(f"  saved {video_path} ({os.path.getsize(video_path)} bytes)")
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def parse_args(argv: Optional[list] = None):
    ap = argparse.ArgumentParser(description="Live trial: 1 image + 1 clip (spends credits).")
    ap.add_argument("--yes", action="store_true", help="confirm that you accept spending credits")
    ap.add_argument("--image", help="existing image path (skips the Deepix step)")
    ap.add_argument("--image-prompt", default=DEFAULT_IMAGE_PROMPT)
    ap.add_argument("--motion-prompt", default=DEFAULT_MOTION_PROMPT)
    ap.add_argument("--model", default="kling", help="kling | kling-o1 | seedance | seedance-fast | seedance-2.5")
    ap.add_argument("--duration", type=float, default=5)
    ap.add_argument("--out", default=os.path.join("data", "trial"))
    return ap.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)
    if not args.yes:
        print("This trial creates 1 image and 1 video and SPENDS CREDITS. Re-run with --yes to proceed.")
        return 2
    try:
        run_trial(args)
    except ProviderError as e:
        print(f"FAILED ({e.code}): {e}")
        return 1
    print("Done. Check the files in", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
