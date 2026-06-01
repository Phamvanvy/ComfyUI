"""
Comic Book Generator - Dùng ComfyUI API để tạo truyện tranh từ câu chuyện
Usage: python comic_generator.py --story "Cau chuyen cua ban..." --output ./comics
       python comic_generator.py --storyfile my_story.txt --output ./comics
"""

import argparse
import json
import os
import re
import shutil
import time
import urllib.parse
import urllib.request
from datetime import datetime


# ============================================================
# Cấu hình mặc định
# ============================================================
DEFAULT_SERVER = "http://127.0.0.1:8188"
DEFAULT_OUTPUT = "./comic_output"
DEFAULT_POSITIVE_TEMPLATE = "{scene}, cinematic lighting, photorealistic, 4k, highly detailed, comic book style, manga illustration"
DEFAULT_NEGATIVE = "bad quality, worst quality, blurry, low resolution, deformed, ugly, distorted, text, watermark, signature"
DEFAULT_SEED = 42
DEFAULT_STEPS = 25
DEFAULT_CFG = 3.5
DEFAULT_SAMPLER = "euler"
DEFAULT_SCHEDULER = "simple"
DEFAULT_WIDTH = 768
DEFAULT_HEIGHT = 768


def split_story_into_scenes(story_text, max_scenes=20):
    """Phân tách câu chuyện thành các cảnh riêng biệt."""
    lines = story_text.strip().split('\n')
    separators = ['---', '===', '###', '***']
    has_separator = any(any(sep in line for sep in separators) for line in lines)

    if has_separator:
        full_text = '\n'.join(lines)
        parts = re.split(r'\n\s*(-{3,}|={3,}|#{3,}|\*{3,})\s*\n', full_text)
        scenes = [p.strip() for p in parts if p.strip()]
    else:
        scenes = [line.strip() for line in lines if line.strip()]

    if len(scenes) > max_scenes:
        print(f"WARNING: Câu chuyện có {len(scenes)} cảnh, cắt giảm xuống {max_scenes}")
        scenes = scenes[:max_scenes]

    return scenes


def create_api_workflow(scene_description, scene_number, output_prefix, settings):
    """Tạo API workflow JSON từ scene description."""
    positive_prompt = settings['positive_template'].format(scene=scene_description)
    filename = f"{output_prefix}_{scene_number:03d}"

    workflow = {
        "3": {
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Positive Prompt"},
            "inputs": {
                "text": positive_prompt,
                "clip": ["2", 0]
            }
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Negative Prompt"},
            "inputs": {
                "text": settings['negative_prompt'],
                "clip": ["2", 0]
            }
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "_meta": {"title": "EmptyLatentImage"},
            "inputs": {
                "width": settings['width'],
                "height": settings['height'],
                "batch_size": 1
            }
        },
        "6": {
            "class_type": "KSampler",
            "_meta": {"title": "KSampler"},
            "inputs": {
                "seed": settings['seed'],
                "steps": settings['steps'],
                "cfg": settings['cfg'],
                "sampler_name": settings['sampler'],
                "scheduler": settings['scheduler'],
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0]
            }
        },
        "7": {
            "class_type": "VAELoader",
            "_meta": {"title": "VAELoader"},
            "inputs": {
                "vae_name": settings['vae_name']
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "_meta": {"title": "VAEDecode"},
            "inputs": {
                "samples": ["6", 0],
                "vae": ["7", 0]
            }
        },
        "9": {
            "class_type": "SaveImage",
            "_meta": {"title": "SaveImage"},
            "inputs": {
                "images": ["8", 0],
                "filename_prefix": filename
            }
        },
        "1": {
            "class_type": "UnetLoaderGGUF",
            "_meta": {"title": "UnetLoaderGGUF"},
            "inputs": {
                "unet_name": settings['unet_name']
            }
        },
        "2": {
            "class_type": "DualCLIPLoaderGGUF",
            "_meta": {"title": "DualCLIPLoaderGGUF"},
            "inputs": {
                "clip_name1": settings['clip_name1'],
                "clip_name2": settings['clip_name2'],
                "type": settings['clip_type']
            }
        }
    }

    return workflow


def queue_prompt(workflow, server_url, client_id="comic_generator"):
    """Gửi prompt đến ComfyUI API"""
    prompt_data = {"prompt": workflow, "client_id": client_id}
    url = f"{server_url}/prompt"
    data = json.dumps(prompt_data).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            return result.get('prompt_id')
    except Exception as e:
        print(f"  [ERROR] Gửi prompt thất bại: {e}")
        return None


def get_history(prompt_id, server_url):
    """Lấy kết quả từ prompt history"""
    url = f"{server_url}/history/{prompt_id}"
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None


def wait_for_completion(prompt_id, server_url, timeout=3600):
    """Chờ đến khi prompt hoàn thành."""
    start_time = time.time()
    print(f"  ⏳ Đang generate... (prompt_id: {prompt_id})")

    while time.time() - start_time < timeout:
        history = get_history(prompt_id, server_url)
        if history and prompt_id in history:
            hist_entry = history[prompt_id]
            print(f"  🔍 History status: {hist_entry.get('status', {})}")

            status = hist_entry.get('status', {})
            if status.get('status_str') == 'success':
                outputs = hist_entry.get('outputs', {})
                print(f"  🔍 Output nodes: {list(outputs.keys())}")

                images = []
                for node_id, node_output in outputs.items():
                    print(f"  🔍 Node {node_id}: {list(node_output.keys()) if isinstance(node_output, dict) else type(node_output)}")
                    if isinstance(node_output, dict) and 'images' in node_output:
                        for img in node_output['images']:
                            img_name = img.get('filename', 'unknown')
                            print(f"  🔍 Image entry: {img}")
                            images.append(img_name)
                if images:
                    return images
                else:
                    print(f"  ⚠️  No images found in outputs")
                    return None
            elif status.get('status_str') == 'error':
                print(f"  [ERROR] Generate thất bại!")
                return None
        time.sleep(2)

    print(f"  [ERROR] Timeout sau {timeout} giây")
    return None


def download_image(filename, output_folder, server_url, comfy_base_dir=None):
    """Tải ảnh từ ComfyUI output folder (ưu tiên copy trực tiếp, fallback HTTP)"""
    output_path = os.path.join(output_folder, filename)
    print(f"  📥 Download: {filename}")

    # Method 1: Copy trực tiếp từ ./output/ folder (độ tin cậy cao nhất)
    if comfy_base_dir:
        src_path = os.path.join(comfy_base_dir, "output", filename)
        if os.path.exists(src_path):
            try:
                shutil.copy2(src_path, output_path)
                print(f"  ✅ Copied (direct): {output_path}")
                return output_path
            except Exception as e:
                print(f"  ⚠️  Direct copy failed: {e}, trying HTTP...")

    # Method 2: Dùng urllib với safe_url
    safe_filename = urllib.parse.quote(filename, safe='-._/')
    url = f"{server_url}/view?filename={safe_filename}&subfolder=&type=output"
    print(f"  🌐 HTTP URL: {url}")

    try:
        req = urllib.request.Request(url, headers={'Accept': 'image/*'})
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(output_path, 'wb') as f:
                shutil.copyfileobj(response, f)
        print(f"  ✅ Copied (HTTP): {output_path}")
        return output_path
    except urllib.error.HTTPError as e:
        print(f"  [ERROR] HTTP {e.code}: {e.reason} - {url}")
        return None
    except Exception as e:
        print(f"  [ERROR] Tải ảnh thất bại: {type(e).__name__}: {e}")
        return None


def generate_comic(story_text, output_folder, output_prefix, settings, server_url):
    """Generate toàn bộ comic từ câu chuyện."""
    os.makedirs(output_folder, exist_ok=True)

    # Xác định ComfyUI base directory để copy trực tiếp
    comfy_base_dir = os.getcwd()

    scenes = split_story_into_scenes(story_text)
    print(f"\n📖 Phát hiện {len(scenes)} cảnh trong câu chuyện:")
    for i, scene in enumerate(scenes, 1):
        preview = scene[:80] + "..." if len(scene) > 80 else scene
        print(f"  Scene {i}: {preview}")

    print(f"\n🎨 Bắt đầu generate vào: {output_folder}")
    print(f"   ComfyUI base dir: {comfy_base_dir}")
    print(f"   Source output: {os.path.join(comfy_base_dir, 'output')}")
    print()

    generated_images = []

    for i, scene in enumerate(scenes, 1):
        print(f"🖼️  [{i}/{len(scenes)}] Generate scene {i}...")
        print(f"    Prompt: {scene[:100]}...")

        workflow = create_api_workflow(scene, i, output_prefix, settings)
        prompt_id = queue_prompt(workflow, server_url)

        if not prompt_id:
            print(f"  [SKIP] Scene {i}")
            continue

        images = wait_for_completion(prompt_id, server_url)
        if images:
            print(f"  📸 ComfyUI returned {len(images)} image(s): {images}")
            for img_filename in images:
                img_path = download_image(img_filename, output_folder, server_url, comfy_base_dir)
                if img_path:
                    generated_images.append((i, img_path, scene))
                else:
                    print(f"  ❌ Failed to save scene {i}!")
        else:
            print(f"  ❌ No images returned for scene {i}")

        time.sleep(3)

    return generated_images


def create_story_template():
    """Tạo template file truyện"""
    return """# Cách viết truyện cho Comic Generator

## Định dạng 1: Mỗi dòng = 1 cảnh
A young warrior stands on a cliff overlooking a vast ocean at sunset
The warrior draws a glowing sword as dark clouds gather
A massive dragon emerges from the storm clouds
The warrior fights the dragon with lightning striking around them
Peace returns as the dragon turns to dust and flowers bloom

## Định dạng 2: Dùng separator
---
A detective walks through a rainy neon-lit city street
---
The detective finds a mysterious clue in an abandoned warehouse
---
A chase scene through crowded market streets
---
"""


def main():
    parser = argparse.ArgumentParser(
        description="Comic Book Generator - Tạo truyện tranh từ câu chuyện",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python comic_generator.py --story "A cat on moon, A dog in space"
  python comic_generator.py --storyfile my_story.txt
  python comic_generator.py --story "..." --dry-run
  python comic_generator.py --create-template
        """
    )

    parser.add_argument("--story", type=str, help="Câu chuyện (mỗi câu = 1 cảnh, phân cách bằng dấu phẩy hoặc dòng mới)")
    parser.add_argument("--storyfile", type=str, help="Đường dẫn file chứa câu chuyện (.txt)")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="Folder lưu ảnh")
    parser.add_argument("--prefix", type=str, default="comic", help="Prefix filename")
    parser.add_argument("--max-scenes", type=int, default=50, help="Số cảnh tối đa")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Chiều rộng ảnh")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Chiều cao ảnh")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="Số steps sampling")
    parser.add_argument("--cfg", type=float, default=DEFAULT_CFG, help="CFG scale")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Seed (-1 = random)")
    parser.add_argument("--server", type=str, default=DEFAULT_SERVER, help="ComfyUI server URL")
    parser.add_argument("--create-template", action="store_true", help="Tạo template file truyện mẫu")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ hiển thị scenes, không generate")

    args = parser.parse_args()

    # Tạo template
    if args.create_template:
        template = create_story_template()
        template_path = os.path.join(args.output, "story_template.txt")
        os.makedirs(args.output, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template)
        print(f"✅ Template đã tạo: {template_path}")
        return

    # Đọc story
    story_text = None
    if args.story:
        story_text = args.story
        if '\n' not in story_text and ',' in story_text:
            story_text = '\n'.join([s.strip() for s in story_text.split(',') if s.strip()])
    elif args.storyfile:
        if not os.path.exists(args.storyfile):
            print(f"[ERROR] Không tìm thấy file: {args.storyfile}")
            return
        with open(args.storyfile, 'r', encoding='utf-8') as f:
            story_text = f.read()
    else:
        parser.print_help()
        return

    # Build settings dict
    settings = {
        'positive_template': DEFAULT_POSITIVE_TEMPLATE,
        'negative_prompt': DEFAULT_NEGATIVE,
        'seed': args.seed,
        'steps': args.steps,
        'cfg': args.cfg,
        'sampler': DEFAULT_SAMPLER,
        'scheduler': DEFAULT_SCHEDULER,
        'width': args.width,
        'height': args.height,
        'vae_name': 'ae.safetensors',
        'unet_name': 'FLUX1\\\\flux1-dev-Q8_0.gguf',
        'clip_name1': 't5\\\\t5-v1_1-xxl-encoder-Q8_0.gguf',
        'clip_name2': 'clip_l.safetensors',
        'clip_type': 'flux'
    }

    # Tạo output folder với timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output = os.path.join(args.output, f"comic_{timestamp}")

    # Dry run mode
    if args.dry_run:
        scenes = split_story_into_scenes(story_text, args.max_scenes)
        print(f"\n📖 DRY RUN - {len(scenes)} cảnh:")
        for i, scene in enumerate(scenes, 1):
            prompt = settings['positive_template'].format(scene=scene)
            print(f"\n--- Scene {i} ---")
            print(f"  {scene}")
            print(f"  → {prompt}")
        return

    # Generate!
    print(f"🚀 Comic Book Generator")
    print(f"   ComfyUI Server: {args.server}")
    print(f"   Output: {final_output}")
    print(f"   Size: {args.width}x{args.height}, Steps: {args.steps}, CFG: {args.cfg}")

    # Kiểm tra kết nối ComfyUI
    try:
        with urllib.request.urlopen(f"{args.server}/system_stats") as r:
            print(f"   ✅ Kết nối ComfyUI thành công")
    except Exception as e:
        print(f"   [ERROR] Không kết nối được ComfyUI: {e}")
        print(f"   Hãy chắc chắn ComfyUI đang chạy tại {args.server}")
        return

    generated = generate_comic(story_text, final_output, args.prefix, settings, args.server)

    # Summary
    print(f"\n{'='*60}")
    print(f"🎉 HOÀN THÀNH!")
    print(f"   Tổng cộng: {len(generated)} ảnh")
    print(f"   Output folder: {final_output}")

    # Tạo file manifest
    manifest_path = os.path.join(final_output, "manifest.json")
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "total_scenes": len(generated),
        "settings": {
            "width": args.width,
            "height": args.height,
            "steps": args.steps,
            "cfg": args.cfg,
            "seed": args.seed
        },
        "scenes": [
            {"scene_number": num, "image": path, "description": desc}
            for num, path, desc in generated
        ]
    }
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"   Manifest: {manifest_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()