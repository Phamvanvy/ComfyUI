"""
Dataset Preparation for Flux LoRA Training
==========================================
Script này giúp chuẩn bị dataset để train LoRA nhân vật.

Cách dùng:
  python prepare_dataset.py --input_dir ./my_character_images --trigger_word "ohwx cat"

Cấu trúc output:
  train_lora/dataset/<trigger_word>/
    image_001.jpg
    image_001.txt   ← caption
    ...
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from PIL import Image

# Optional: auto-caption bằng BLIP / WD14
AUTO_CAPTION = False
try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
    import torch
    AUTO_CAPTION = True
except ImportError:
    pass


def crop_to_square(img: Image.Image, size: int = 512) -> Image.Image:
    """Crop center → resize về size x size."""
    w, h = img.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    img = img.crop((left, top, left + min_dim, top + min_dim))
    return img.resize((size, size), Image.LANCZOS)


def load_blip():
    if not AUTO_CAPTION:
        return None, None
    print("  Loading BLIP for auto-captioning...")
    device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    ).to(device)
    return processor, model


def generate_caption(img: Image.Image, processor, model, trigger_word: str) -> str:
    """Generate caption bằng BLIP rồi prepend trigger word."""
    import torch
    device = next(model.parameters()).device
    inputs = processor(img, return_tensors="pt").to(device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=50)
    caption = processor.decode(out[0], skip_special_tokens=True)
    return f"{trigger_word}, {caption}"


def prepare_dataset(
    input_dir: str,
    trigger_word: str,
    output_dir: str,
    image_size: int = 512,
    repeats: int = 10,
    auto_caption: bool = False,
):
    input_path = Path(input_dir)
    # Cấu trúc: dataset/N_trigger_word/images
    safe_trigger = trigger_word.replace(" ", "_")
    dataset_path = Path(output_dir) / f"{repeats}_{safe_trigger}"
    dataset_path.mkdir(parents=True, exist_ok=True)

    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    images = [f for f in input_path.iterdir() if f.suffix.lower() in exts]

    if len(images) == 0:
        print(f"[ERROR] Không tìm thấy ảnh trong: {input_dir}")
        sys.exit(1)

    print(f"\n[Dataset Prep] Tìm thấy {len(images)} ảnh trong {input_dir}")
    print(f"  Trigger word: '{trigger_word}'")
    print(f"  Output: {dataset_path}")
    print(f"  Image size: {image_size}x{image_size}")
    print(f"  Repeats: {repeats}")

    # Load BLIP nếu cần
    processor, blip_model = None, None
    if auto_caption and AUTO_CAPTION:
        processor, blip_model = load_blip()

    for idx, img_path in enumerate(sorted(images), 1):
        img = Image.open(img_path).convert("RGB")
        img_out = crop_to_square(img, image_size)

        # Lưu ảnh
        out_img = dataset_path / f"img_{idx:04d}.jpg"
        img_out.save(out_img, quality=95)

        # Tạo caption
        out_txt = dataset_path / f"img_{idx:04d}.txt"
        if out_txt.exists():
            # Giữ caption đã có
            pass
        elif auto_caption and processor is not None:
            caption = generate_caption(img_out, processor, blip_model, trigger_word)
            out_txt.write_text(caption, encoding="utf-8")
        else:
            # Caption mặc định - CHỈ trigger word (kohya style)
            out_txt.write_text(trigger_word, encoding="utf-8")

        print(f"  [{idx}/{len(images)}] {out_img.name} → caption: {out_txt.read_text()[:60]}")

    print(f"\n[DONE] Dataset sẵn sàng tại: {dataset_path}")
    print(f"  Tổng {len(images)} ảnh × {repeats} repeats = {len(images) * repeats} steps/epoch")
    print(f"\nTiếp theo: chạy  python train.py --config flux_lora_config.yaml")
    return str(dataset_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chuẩn bị dataset LoRA training")
    parser.add_argument("--input_dir", required=True,
                        help="Thư mục chứa ảnh nhân vật (20-50 ảnh)")
    parser.add_argument("--trigger_word", default="ohwx character",
                        help="Từ trigger để gọi nhân vật (vd: 'ohwx cat'). Phải unique!")
    parser.add_argument("--output_dir", default="./dataset",
                        help="Thư mục output dataset")
    parser.add_argument("--image_size", type=int, default=512,
                        help="Kích thước ảnh (512 hoặc 1024)")
    parser.add_argument("--repeats", type=int, default=10,
                        help="Số lần lặp dataset mỗi epoch (10-30)")
    parser.add_argument("--auto_caption", action="store_true",
                        help="Tự động caption bằng BLIP (cần cài transformers)")
    args = parser.parse_args()

    prepare_dataset(
        input_dir=args.input_dir,
        trigger_word=args.trigger_word,
        output_dir=args.output_dir,
        image_size=args.image_size,
        repeats=args.repeats,
        auto_caption=args.auto_caption,
    )
