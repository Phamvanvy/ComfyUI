"""
caption_training_images.py
Auto-caption training images for LoRA/DreamBooth fine-tuning.

For Tru Tien (Jade Dynasty) character training images.
Generates .txt caption files alongside each image.

Priority:
  1. WD14 Tagger via ComfyUI API (if available)
  2. Filename-pattern based fallback captioning

Usage:
  python caption_training_images.py --input_dir ./train_images
  python caption_training_images.py --input_dir ./train_images --trigger_word luxueqi --style_trigger zxttstyle
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Filename keyword -> positional/pose tag
FILENAME_PATTERN_TAGS: list[tuple[list[str], str]] = [
    (["front"],          "front view, standing"),
    (["side"],           "side view"),
    (["back"],           "back view"),
    (["sitting", "sit"], "sitting pose"),
    (["action", "sword", "fight"], "holding sword, action pose"),
    (["3q", "quarter"],  "three-quarter view"),
]

# ---------------------------------------------------------------------------
# ComfyUI WD14 helpers
# ---------------------------------------------------------------------------

COMFYUI_URL = "http://127.0.0.1:8188"


def _comfyui_reachable() -> bool:
    """Return True if the local ComfyUI server is reachable."""
    try:
        req = urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=3)
        return req.status == 200
    except Exception:
        return False


def _wd14_node_available() -> bool:
    """Return True if a WD14-tagger node type is registered in ComfyUI."""
    try:
        req = urllib.request.urlopen(f"{COMFYUI_URL}/object_info", timeout=5)
        data = json.loads(req.read().decode())
        return any("WD14" in key or "wd14" in key.lower() for key in data)
    except Exception:
        return False


def _build_wd14_workflow(image_b64: str) -> dict:
    """Build a minimal ComfyUI workflow that loads an image and runs WD14 tagging."""
    return {
        "1": {
            "class_type": "ETN_LoadImageBase64",
            "inputs": {"image": image_b64},
        },
        "2": {
            "class_type": "WD14Tagger|pysssss",
            "inputs": {
                "image": ["1", 0],
                "model": "wd-v1-4-moat-tagger-v2",
                "threshold": 0.35,
                "character_threshold": 0.85,
                "exclude_tags": "",
                "replace_underscore": True,
                "trailing_comma": False,
                "clipboard_output": False,
            },
        },
    }


def _queue_and_wait(workflow: dict, timeout: int = 120) -> str | None:
    """
    Submit a workflow to ComfyUI, poll until done, return the last text output.
    Returns None on any failure.
    """
    client_id = "caption_script"
    payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode()

    try:
        req = urllib.request.Request(
            f"{COMFYUI_URL}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read().decode())
        prompt_id = result.get("prompt_id")
        if not prompt_id:
            return None
    except Exception as exc:
        print(f"    [WD14] Queue failed: {exc}", file=sys.stderr)
        return None

    # Poll history until the prompt finishes
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1)
        try:
            hist_req = urllib.request.urlopen(
                f"{COMFYUI_URL}/history/{prompt_id}", timeout=10
            )
            hist = json.loads(hist_req.read().decode())
            if prompt_id in hist:
                outputs = hist[prompt_id].get("outputs", {})
                # WD14 node outputs text; find first "text" value
                for node_out in outputs.values():
                    for key, val in node_out.items():
                        if key == "text" and val:
                            texts = val if isinstance(val, list) else [val]
                            return texts[0] if texts else None
                # Prompt finished but no text found
                return None
        except Exception:
            continue

    print("    [WD14] Timed out waiting for result.", file=sys.stderr)
    return None


def caption_via_comfyui(image_path: Path) -> str | None:
    """
    Attempt to caption *image_path* using WD14 tagger through the ComfyUI API.
    Returns a comma-separated tag string, or None if unavailable/failed.
    """
    import base64

    try:
        image_b64 = base64.b64encode(image_path.read_bytes()).decode()
    except Exception as exc:
        print(f"    [WD14] Could not read image: {exc}", file=sys.stderr)
        return None

    workflow = _build_wd14_workflow(image_b64)
    return _queue_and_wait(workflow)


# ---------------------------------------------------------------------------
# Filename-pattern fallback
# ---------------------------------------------------------------------------

def _pose_tags_from_filename(stem: str) -> str:
    """Derive pose/view tags from the image filename stem."""
    lower = stem.lower()
    for keywords, tags in FILENAME_PATTERN_TAGS:
        if any(kw in lower for kw in keywords):
            return tags
    return "standing"


def caption_via_fallback(image_path: Path) -> str:
    """Generate caption tags using filename pattern matching only."""
    return _pose_tags_from_filename(image_path.stem)


# ---------------------------------------------------------------------------
# Caption assembly
# ---------------------------------------------------------------------------

BASE_TAGS = "1girl, long black hair, white hanfu, xianxia, sword"


def build_caption(
    trigger_word: str,
    style_trigger: str,
    auto_tags: str,
) -> str:
    """
    Assemble the final caption string.

    Format: "<trigger>, <style>, <base_tags>, <auto_tags>"
    """
    parts = [
        trigger_word.strip(),
        style_trigger.strip(),
        BASE_TAGS,
    ]
    if auto_tags:
        parts.append(auto_tags.strip().strip(","))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_parts: list[str] = []
    for segment in parts:
        for tag in (t.strip() for t in segment.split(",") if t.strip()):
            if tag not in seen:
                seen.add(tag)
                unique_parts.append(tag)

    return ", ".join(unique_parts)


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_directory(
    input_dir: Path,
    trigger_word: str,
    style_trigger: str,
    overwrite: bool = False,
) -> None:
    images = sorted(
        p for p in input_dir.rglob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not images:
        print(f"No supported images found in: {input_dir}")
        return

    # Determine which captioning method to use
    use_comfyui = False
    if _comfyui_reachable():
        if _wd14_node_available():
            use_comfyui = True
            print("WD14 Tagger detected via ComfyUI API — using API captioning.")
        else:
            print("ComfyUI reachable but WD14 node not found — using fallback.")
    else:
        print("ComfyUI not reachable — using filename-pattern fallback.")

    print(f"Found {len(images)} image(s) in {input_dir}\n")

    processed = skipped = failed = 0

    for image_path in images:
        caption_path = image_path.with_suffix(".txt")

        if caption_path.exists() and not overwrite:
            print(f"  [SKIP]  {image_path.name}  (caption already exists)")
            skipped += 1
            continue

        print(f"  [PROC]  {image_path.name}", end="", flush=True)

        if use_comfyui:
            auto_tags = caption_via_comfyui(image_path)
            if auto_tags is None:
                print(" (WD14 failed, using fallback)", end="")
                auto_tags = caption_via_fallback(image_path)
        else:
            auto_tags = caption_via_fallback(image_path)

        caption = build_caption(trigger_word, style_trigger, auto_tags)

        try:
            caption_path.write_text(caption, encoding="utf-8")
            print(f"\n          -> {caption}")
            processed += 1
        except Exception as exc:
            print(f"\n  [ERROR] Could not write {caption_path}: {exc}", file=sys.stderr)
            failed += 1

    print(f"\nDone. Processed: {processed}  Skipped: {skipped}  Failed: {failed}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-caption training images for Tru Tien / Jade Dynasty LoRA training.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python caption_training_images.py --input_dir ./train_lora/luxueqi
  python caption_training_images.py --input_dir ./train_lora/luxueqi --trigger_word luxueqi --style_trigger zxttstyle
  python caption_training_images.py --input_dir ./images --overwrite
        """,
    )
    parser.add_argument(
        "--input_dir",
        type=Path,
        required=True,
        help="Directory containing training images (searched recursively).",
    )
    parser.add_argument(
        "--trigger_word",
        type=str,
        default="luxueqi",
        help="Character trigger word to prepend to every caption (default: luxueqi).",
    )
    parser.add_argument(
        "--style_trigger",
        type=str,
        default="zxttstyle",
        help="Style trigger word (default: zxttstyle).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing .txt caption files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.input_dir.exists():
        sys.exit(f"Error: input directory does not exist: {args.input_dir}")
    if not args.input_dir.is_dir():
        sys.exit(f"Error: path is not a directory: {args.input_dir}")

    print("=== ComfyUI Training Image Auto-Captioner ===")
    print(f"  Input dir    : {args.input_dir.resolve()}")
    print(f"  Trigger word : {args.trigger_word}")
    print(f"  Style trigger: {args.style_trigger}")
    print(f"  Overwrite    : {args.overwrite}")
    print()

    process_directory(
        input_dir=args.input_dir,
        trigger_word=args.trigger_word,
        style_trigger=args.style_trigger,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
