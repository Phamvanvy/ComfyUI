"""
generate_story.py
=================
Đọc 1 file truyện JSON (vd stories/luxueqi_story.json), sinh ảnh minh hoạ cho
từng cảnh bằng LoRA qua ComfyUI API, rồi xuất 1 file story.md (truyện minh hoạ).

Cách dùng:
  # 1. Khởi động ComfyUI: run_gpu0.bat  (hoặc python main.py --port 8188)
  # 2. Chạy:
  venv\\Scripts\\python.exe generate_story.py stories\\luxueqi_story.json

Mỗi cảnh -> 1 ảnh trong output/<output_subdir>/ + story.md ghép lời kể với ảnh.
Sửa file JSON (thêm/bớt cảnh, đổi prompt) để "viết" truyện của bạn.
"""
import json
import re
import sys
import time
import urllib.request
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

URL = "http://127.0.0.1:8188"

# Font có dấu tiếng Việt (Windows). Đổi nếu muốn font khác.
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
]


def _load_font(size):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    """Bẻ dòng theo chiều rộng tối đa (đơn vị px)."""
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_dialogue(img_path, text):
    """Vẽ 1 ô thoại (bong bóng trắng bo góc, chữ đen) phía dưới ảnh.
    Chữ render bằng Pillow nên tiếng Việt sắc nét (model SDXL không làm được)."""
    try:
        img = Image.open(img_path).convert("RGB")
    except Exception as exc:
        print(f"    [bong bóng] bỏ qua, không mở được ảnh: {exc}")
        return
    W, H = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    font = _load_font(max(20, W // 30))
    pad = max(14, W // 60)
    max_text_w = W - 4 * pad
    lines = _wrap(draw, text, font, max_text_w)
    line_h = (font.getbbox("Ag")[3] - font.getbbox("Ag")[1]) + 6
    box_h = line_h * len(lines) + 2 * pad
    box_w = min(W - 2 * pad, max(draw.textlength(ln, font=font) for ln in lines) + 2 * pad)
    x0 = (W - box_w) // 2
    y0 = H - box_h - pad
    draw.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], radius=pad,
                           fill=(255, 255, 255, 235), outline=(20, 20, 40, 255), width=3)
    ty = y0 + pad
    for ln in lines:
        tw = draw.textlength(ln, font=font)
        draw.text(((W - tw) / 2, ty), ln, font=font, fill=(15, 15, 30, 255))
        ty += line_h
    img.save(img_path)

# Các độ phân giải SDXL chuẩn (~1 megapixel) cho từng tỉ lệ.
# Ưu tiên khung DỌC để luôn lấy đủ NGƯỜI (toàn thân) + thấy nền,
# thay vì crop ngang cắt mất đầu/chân (lỗi cũ luôn rơi về "wide").
ASPECTS = {
    "wide":      (1344, 768),   # toàn cảnh điện ảnh, không có nhân vật trung tâm
    "landscape": (1216, 832),   # cảnh rộng / nhiều người dàn ngang + nền
    "square":    (1024, 1024),  # 2 người đứng cạnh nhau, cân đối, đủ cả 2
    "portrait":  (832, 1216),   # toàn thân 1 người + nền
    "tall":      (768, 1344),   # toàn thân nhấn chiều cao
}

# Từ khoá gợi ý nhiều người trong cảnh -> cần khung đủ rộng để lấy hết
_MULTI_KW = [
    "two-shot", "two shot", "two people", "two men", "two women",
    "two figures", "couple", "group", "crowd", "beside her", "beside him",
    "next to her", "next to him", "both of them", "each other",
    "facing each other", "several people", "male cultivator beside",
    "female cultivator beside", "three ",
]
# Từ khoá cảnh rộng / phong cảnh
_WIDE_KW = [
    "wide shot", "establishing", "scenery", "landscape", "panorama",
    "vista", "aerial", "wide angle", "vast", "distant",
]


def infer_aspect(prompt):
    """Đoán tỉ lệ khung hình từ prompt cảnh.

    Nguyên tắc: LUÔN ưu tiên lấy ĐỦ NGƯỜI (toàn thân) và thấy được nền,
    không crop ngang cắt mất đầu/chân.
    - Phong cảnh rộng, không có nhân vật -> landscape
    - >= 2 người -> square (đứng cạnh nhau vẫn đủ cả 2 + nền);
      nếu lại còn là cảnh rộng -> landscape
    - Còn lại (1 người, cận cảnh, toàn thân...) -> portrait (đủ người + nền)
    """
    p = prompt.lower()
    multi = any(k in p for k in _MULTI_KW)
    wide = any(k in p for k in _WIDE_KW)
    if multi:
        return "landscape" if wide else "square"
    if wide:
        return "landscape"
    return "portrait"


# Cụm khung hình quá sát -> hạ xuống khung lấy đủ người. Sắp dài trước ngắn
# để "extreme close-up" được thay trước "close-up".
_TIGHT_FRAMING = [
    "extreme close-up", "extreme closeup", "extreme close up",
    "macro shot", "close-up", "close up", "closeup",
    "face shot", "headshot", "head shot", "bust shot",
]
# Từ chặn-cắt thêm vào negative để model không zoom/crop mất người
_ANTI_CROP = ("cropped, cropped body, head out of frame, out of frame, "
              "zoomed in, extreme close-up, macro")


def normalize_framing(prompt):
    """Hạ các cụm 'close-up/cận mặt' thành 'full body shot' để không cắt người.

    Vẫn giữ nguyên chi tiết cảm xúc (hand over mouth, misty eyes...), chỉ đổi
    CÁCH ĐÓNG KHUNG. Vd: 'close-up two-shot' -> 'medium full shot two-shot'.
    """
    out = prompt
    for kw in _TIGHT_FRAMING:
        out = re.sub(re.escape(kw), "medium full shot", out, flags=re.IGNORECASE)
    # gộp nếu lỡ sinh ra trùng lặp liên tiếp
    out = re.sub(r"(medium full shot)(,?\s+\1)+", r"\1", out, flags=re.IGNORECASE)
    return out


def resolve_size(cfg, scene):
    """Quyết định (width, height) theo thứ tự ưu tiên:
    1) scene.width/height  2) scene.aspect / generation.aspect (kể cả 'auto')
    3) generation.width/height cố định  4) tự đoán từ prompt."""
    g = cfg.get("generation", {})
    if scene.get("width") and scene.get("height"):
        return int(scene["width"]), int(scene["height"])
    aspect = scene.get("aspect") or g.get("aspect")
    if aspect == "auto":
        aspect = infer_aspect(scene.get("prompt", ""))
    if aspect in ASPECTS:
        return ASPECTS[aspect]
    if g.get("width") and g.get("height"):
        return int(g["width"]), int(g["height"])
    return ASPECTS["portrait"]  # mặc định an toàn: toàn thân + nền


def build_workflow(cfg, scene):
    s = cfg["style"]
    g = cfg["generation"]
    m = cfg["model"]
    scene_prompt = normalize_framing(scene["prompt"])
    positive = ", ".join(filter(None, [
        m["trigger"], s["character_tags"], scene_prompt, s["quality_tags"],
        s.get("scene_suffix", "")
    ]))
    negative = ", ".join(filter(None, [s["negative"], _ANTI_CROP]))
    # lock_seed=true -> dùng chung 1 seed cho mọi cảnh (nhân vật/màu/phong cách nhất quán hơn)
    if g.get("lock_seed"):
        seed = g["base_seed"]
    else:
        seed = scene.get("seed", g["base_seed"] + scene["id"])
    width, height = resolve_size(cfg, scene)
    prefix = f"{cfg['story']['output_subdir']}/scene_{scene['id']:02d}"
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": m["checkpoint"]}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "lora_name": m["lora"], "strength_model": m["lora_strength"],
            "strength_clip": m["lora_strength"], "model": ["1", 0], "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": g["steps"], "cfg": g["cfg"],
            "sampler_name": g["sampler"], "scheduler": g["scheduler"], "denoise": 1.0,
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0]}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["7", 0]}},
    }
    return wf, positive, seed, (width, height)


def queue(workflow, client_id):
    data = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
    req = urllib.request.Request(f"{URL}/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]


def wait(prompt_id, timeout=300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2)
        hist = json.loads(urllib.request.urlopen(f"{URL}/history/{prompt_id}", timeout=10).read())
        if prompt_id in hist:
            for node in hist[prompt_id].get("outputs", {}).values():
                for img in node.get("images", []):
                    return img["filename"], img.get("subfolder", "")
            return None, None
    raise TimeoutError("render timed out")


def main():
    story_file = sys.argv[1] if len(sys.argv) > 1 else "stories/luxueqi_story1.json"
    cfg = json.loads(Path(story_file).read_text(encoding="utf-8"))
    client_id = str(uuid.uuid4())

    out_root = Path("output") / cfg["story"]["output_subdir"]
    out_root.mkdir(parents=True, exist_ok=True)
    md = [f"# {cfg['story']['title']}\n"]
    if cfg["story"].get("author"):
        md.append(f"*Tác giả: {cfg['story']['author']}*\n")

    print(f"Truyện: {cfg['story']['title']}  ({len(cfg['scenes'])} cảnh)\n")
    for scene in cfg["scenes"]:
        wf, positive, seed, (w, h) = build_workflow(cfg, scene)
        print(f"[Cảnh {scene['id']}] đang vẽ (seed={seed}, {w}x{h})...", flush=True)
        pid = queue(wf, client_id)
        fname, sub = wait(pid)
        rel = f"{fname}" if not sub else f"{sub}/{fname}"
        print(f"[Cảnh {scene['id']}] -> output/{rel}", flush=True)
        # Vẽ ô thoại lên ảnh nếu cảnh có "dialogue"
        img_path = Path("output") / sub / fname if sub else out_root / fname
        if scene.get("dialogue"):
            draw_dialogue(img_path, scene["dialogue"])
            print(f"    [bong bóng] {scene['dialogue']}", flush=True)
        # story.md nằm trong out_root, ảnh cũng trong out_root -> ref bằng tên file
        img_ref = Path(fname).name
        md.append(f"## Cảnh {scene['id']}\n")
        md.append(f"![scene {scene['id']}]({img_ref})\n")
        md.append(f"{scene['narrative']}\n")

    md_path = out_root / "story.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"\nXong! Truyện minh hoạ: {md_path}")


if __name__ == "__main__":
    main()
