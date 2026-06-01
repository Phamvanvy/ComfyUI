# Setup FLUX.1 Dev GGUF trên ComfyUI

## Bước 1: Tải Model

### FLUX GGUF (Đã có)
- File: `flux1-dev-Q8_0.gguf`
- Đặt vào: `E:\repos\ComfyUI\models\unet\`
- ⚠️ GIỮ NGUYÊN đuôi `.gguf`, KHÔNG đổi thành `.safetensors`

### T5 Text Encoder (BẮT BUỘC)
- URL: https://huggingface.co/city96/t5-v1_1-xxl-encoder-gguf
- File gợi ý:
  - `t5-v1_1-xxl-encoder-Q8_0.gguf` (~12GB) - chất lượng tốt nhất
  - `t5-v1_1-xxl-encoder-Q5_0.gguf` (~7GB) - tiết kiệm VRAM
- Đặt vào: `E:\repos\ComfyUI\models\clip\`

### CLIP L (Khuyến khích)
- URL: https://huggingface.co/comfyanonymous/flux_text_encoders
- File: `clip_l.safetensors` (~300MB)
- Đặt vào: `E:\repos\ComfyUI\models\clip\`

### VAE (Optional)
- URL: https://huggingface.co/comfyanonymous/flux_text_encoders
- File: `ae.sft` (~1MB)
- Đặt vào: `E:\repos\ComfyUI\models\vae\`

## Bước 2: Cấu trúc thư mục sau khi cài

```
E:\repos\ComfyUI\models\
├── unet\
│   └── flux1-dev-Q8_0.gguf          ← FLUX model
├── clip\
│   ├── t5-v1_1-xxl-encoder-Q8_0.gguf ← T5 encoder
│   └── clip_l.safetensors            ← CLIP L
└── vae\
    └── ae.sft                        ← VAE (optional)
```

## Bước 3: Workflow trong ComfyUI

### Node sử dụng (KHÔNG phải node thông thường):

1. **Unet Loader (GGUF)** - category: `bootleg`
   - Chọn file: `flux1-dev-Q8_0.gguf`

2. **CLIPLoader (gguf)** - category: `bootleg`
   - Clip file 1: `t5-v1_1-xxl-encoder-Q8_0.gguf`
   - Clip file 2: `clip_l.safetensors`

3. **CLIPTextEncode** (Positive prompt)
   - Ví dụ: `beautiful anime girl, blue eyes, long hair, detailed face, masterpiece`

4. **CLIPTextEncode** (Negative prompt)
   - Ví dụ: `bad quality, worst quality, blurry, low resolution, deformed`

5. **EmptyLatentImage**
   - Width: 1024, Height: 1024 (Flux tối ưu ở 1024x1024)

6. **KSampler**
   - steps: 20-30
   - cfg: 3.5 (Flux dùng CFG thấp)
   - sampler_name: `euler`
   - scheduler: `simple`
   - denoise: 1.0

7. **VAEDecode** → **SaveImage**

### Kết nối:
```
Unet Loader (GGUF) ──model──→ KSampler
CLIPLoader (gguf) ──clip──→ CLIPTextEncode(+) ──conditioning──→ KSampler
                                    CLIPTextEncode(-) ──conditioning──→ KSampler
EmptyLatentImage ──latent──→ KSampler ──latent──→ VAEDecode ──image──→ SaveImage
VAELoader ──vae──→ VAEDecode
```

## Bước 4: Restart ComfyUI

```powershell
cd E:\repos\ComfyUI
.\venv\Scripts\activate
python main.py
```

## Lưu ý quan trọng

- Node GGUF nằm trong category **"bootleg"** trong menu Add Node
- KHÔNG dùng "Load Diffusion Model" thông thường cho file .gguf
- Flux dùng CFG thấp (3.5) khác với SDXL (7-8)
- RTX 5060 Ti 16GB VRAM chạy Flux Q8_0 + T5 Q8_0 được