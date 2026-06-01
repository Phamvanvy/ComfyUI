## ✅ Đã hoàn thành
- [x] ComfyUI UI đang chạy tại: http://127.0.0.1:8188
- [x] PyTorch cu130 (nightly) đã cài cho RTX 5060 Ti

## ⚠️ Vấn đề hiện tại: CHƯA CÓ MODEL

Các thư mục models của bạn **trống**. Bạn cần tải về ít nhất 1 model để generate ảnh.

---

## CÁCH 1: Dùng ComfyUI-Manager (DỄ NHẤT)

1. Mở trình duyệt → truy cập `http://127.0.0.1:8188`
2. Click **Open Simple Graph** hoặc **Open Dev Graph**
3. Nhìn sang bên phải, tìm tab **ComfyUI-Manager** (biểu tượng bánh răng ⚙️)
4. Click **Model Manager** → mở trình quản lý model
5. Tìm và tải 1 trong các model sau:

### Model แนะนำ cho người mới bắt đầu:

| Model | Kích thước | Chất lượng | Tốc độ |
|-------|-----------|-----------|--------|
| **SDXL Base 1.0** | ~6.5GB | Tốt | Nhanh |
| **Flux.1 Dev** | ~23GB | Rất tốt | Chậm |
| **SD 1.5 (anything-v5)** | ~2GB | OK | Rất nhanh |

**Với RTX 5060 Ti (16GB VRAM):** Dùng SDXL hoặc Flux.1 Dev được thoải mái.

---

## CÁCH 2: Tải thủ công từ HuggingFace

### Option A: Stable Diffusion XL (Khuyên dùng)

1. Truy cập: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
2. Tải file `sd_xl_base_1.0.safetensors` (~6.5GB)
3. Đặt vào: `E:\repos\ComfyUI\models\checkpoints\`

### Option B: Flux.1 Dev (Chất lượng cao nhất)

1. Truy cập: https://huggingface.co/black-forest-labs/FLUX.1-dev
2. Tải file `flux1-dev.safetensors` (~23GB) hoặc `flux1-dev.fp8.safetensors` (~12GB)
3. Đặt vào: `E:\repos\ComfyUI\models\diffusion_models\`

### Option C: SD 1.5 (Nhẹ, nhanh)

1. Truy cập: https://huggingface.co/andite/anything-v5
2. Tải file `anything-v5.pruned.safetensors` (~2GB)
3. Đặt vào: `E:\repos\ComfyUI\models\checkpoints\`

---

## CÁCH GENERATE ẢNH SAU KHI CÓ MODEL

### Workflow cơ bản (Text-to-Image):

```
CheckpointLoaderSimple → CLIPTextEncode(Positive) → empty_latent_image → KSampler → SaveImage
                                    ↓
                              CLIPTextEncode(Negative)
```

### Các node cần thiết:

1. **CheckpointLoaderSimple**: Chọn model đã tải
2. **CLIPTextEncode** (Positive): Nhập prompt mô tả ảnh muốn tạo
   - Ví dụ: `a beautiful girl, anime style, blue eyes, long hair`
3. **CLIPTextEncode** (Negative): Nhập những gì KHÔNG muốn
   - Ví dụ: `bad quality, worst quality, blurry, low resolution`
4. **empty_latent_image**: Thiết lập kích thước (1024x1024 cho SDXL, 512x512 cho SD1.5)
5. **KSampler**: Thiết lập sampling
   - steps: 20-30
   - cfg: 7-8
   - sampler_name: euler hoặc dpmpp_2m
   - scheduler: normal
6. **SaveImage**: Lưu kết quả

### Prompt mẫu:

**Anime:**
```
1girl, blue eyes, long silver hair, anime style, masterpiece, best quality, detailed face
```

**Realistic:**
```
photorealistic portrait of a woman, 8k, highly detailed, cinematic lighting
```

**Landscape:**
```
beautiful mountain landscape, sunset, clouds, 4k, photorealistic
```

---

## CÁCH TẠO TRUYỆN TRẠNH (COMIC)

### Phương pháp 1: Generate từng frame + ghép

1. Tạo nhiều ảnh với cùng character (dùng seed cố định)
2. Dùng node **ImageConcat** để ghép các frame lại
3. Thêm text bubble bằng node **DrawText**

### Phương pháp 2: Dùng Blueprint có sẵn

ComfyUI của bạn đã có sẵn blueprints:
- Nhìn vào thư mục `blueprints/` có sẵn các workflow mẫu
- Trong UI: Menu → Load → Load Blueprint → chọn workflow

### Phương pháp 3: Custom Nodes cho Comic

Cài thêm custom nodes:
1. `ComfyUI-Impact-Pack`: Có node để detect/track character
2. `ComfyUI-Frame-Interpolation`: Tạo chuyển động giữa các frame
3. `WAS Node Suite`: Nhiều công cụ edit ảnh

Cách cài:
```
ComfyUI-Manager → Custom Nodes Manager → Install → tìm tên node → Install
```

---

## KHỞI ĐỘNG LẠI SAU KHI CÀI MODEL

```powershell
cd E:\repos\ComfyUI
.\venv\Scripts\activate
python main.py
```

---

## TÀI NGUYÊN HỮU ÍCH

- **Model download:** https://civitai.com/ hoặc https://huggingface.co/
- **Prompt guides:** https://github.com/daswer123/awesome-stable-diffusion-prompts
- **ComfyUI Workflows:** https://openart.ai/workflows
- **ComfyUI Docs:** https://docs.comfy.org/

---

## XỬ LÝ LỖI THƯỜNG GẶP

### Lỗi OOM (Out of Memory):
- Giảm kích thước latent image
- Giảm số steps
- Dùng `--lowvram` trong lệnh khởi động: `python main.py --lowvram`

### Model không hiện trong dropdown:
- Restart ComfyUI
- Kiểm tra file .safetensors có đúng trong thư mục models không

### Generate rất chậm:
