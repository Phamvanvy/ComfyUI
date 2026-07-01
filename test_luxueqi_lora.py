"""Quick end-to-end test of the trained luxueqi LoRA through the ComfyUI API."""
import json
import time
import urllib.request
import uuid

URL = "http://127.0.0.1:8188"
CKPT = "miaomiao_mature_edition_eps1.1.safetensors"
LORA = "luxueqi_lora.safetensors"
NEG = "lowres, bad anatomy, bad hands, worst quality, low quality, jpeg artifacts"

PROMPTS = [
    ("closeup", "luxueqi, 1girl, solo, white and blue hanfu, xianxia style, silver hair, "
                "blue eyes, close-up portrait, masterpiece, best quality"),
    ("fullbody", "luxueqi, 1girl, solo, white and blue hanfu, full body, standing, "
                 "silver hair, white background, masterpiece, best quality"),
]


def build_workflow(prompt_text, seed, strength=0.85):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "lora_name": LORA, "strength_model": strength, "strength_clip": strength,
            "model": ["1", 0], "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_text, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 28, "cfg": 7.0, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": 1.0,
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0]}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "luxueqi_test", "images": ["7", 0]}},
    }


def queue(workflow, client_id):
    data = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
    req = urllib.request.Request(f"{URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]


def wait(prompt_id, timeout=300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2)
        hist = json.loads(urllib.request.urlopen(f"{URL}/history/{prompt_id}", timeout=10).read())
        if prompt_id in hist:
            outs = hist[prompt_id].get("outputs", {})
            for node in outs.values():
                for img in node.get("images", []):
                    return img["filename"], img.get("subfolder", "")
            return None, None
    raise TimeoutError("render timed out")


def main():
    client_id = str(uuid.uuid4())
    for i, (label, text) in enumerate(PROMPTS):
        seed = 42 + i
        print(f"[{label}] queueing (seed={seed})...", flush=True)
        pid = queue(build_workflow(text, seed), client_id)
        fname, sub = wait(pid)
        print(f"[{label}] -> {sub + '/' if sub else ''}{fname}", flush=True)


if __name__ == "__main__":
    main()
