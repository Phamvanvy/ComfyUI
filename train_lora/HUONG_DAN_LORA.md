# Hướng dẫn Train & Dùng LoRA nhân vật (SDXL) — ai-toolkit

Quy trình train LoRA nhân vật cho SDXL/Illustrious bằng `ai-toolkit`, dùng chung venv với ComfyUI.
Ví dụ xuyên suốt: nhân vật **luxueqi** (Tru Tiên, hanfu trắng-xanh, phong cách tiên hiệp).

> Đã train thành công ngày 2026-06-03: 75 ảnh × 15 repeats, 3000 steps, rank 16, base `miaomiao_mature_edition_eps1.1`.
> Output: `models/loras/luxueqi_lora.safetensors`.

---

## 0. Yêu cầu môi trường (làm 1 lần)

ai-toolkit dùng chung venv ComfyUI (`e:\repos\ComfyUI\venv`). Vì venv có `transformers 5.9.0` mới hơn
bản ai-toolkit hỗ trợ, cần các bản vá sau (đã áp dụng — **chỉ cần làm lại nếu cài lại diffusers/ai-toolkit**):

```powershell
# Cài deps thiếu
venv\Scripts\python.exe -m pip install clean-fid clip-anytorch
```

Các bản vá code (xem chi tiết trong git diff):
| File | Vá gì |
|------|-------|
| `venv\...\diffusers\loaders\single_file_utils.py` | Chịu được CLIPTextModel "phẳng" của transformers 5.x (strip prefix `text_model.`) |
| `train_lora\ai-toolkit\toolkit\extension.py` | Bỏ qua extension thiếu deps thay vì crash |
| `train_lora\ai-toolkit\toolkit\stable_diffusion_model.py` | `getattr(te,"text_model",te)` cho CLIP phẳng |

> ⚠️ **KHÔNG hạ cấp `transformers`** — sẽ ảnh hưởng ComfyUI. Các vá trên giữ nguyên transformers 5.9.0.
> ⚠️ Vá trong `site-packages/diffusers` sẽ **mất khi pip nâng cấp/cài lại diffusers** → áp lại.

---

## 1. Caption ảnh

Tạo file `.txt` caption cạnh mỗi ảnh, dựa trên tên file (closeup/halfbody/front/action...).

```powershell
cd E:\repos\ComfyUI
venv\Scripts\python.exe caption_training_images.py `
  --input_dir output\lora_training_data\luxueqi_1024 `
  --trigger_word luxueqi
```

- Caption gồm: `<trigger>, zxttstyle, <base tags>, <pose tag từ tên file>`.
- Base tags hardcode trong `caption_training_images.py` (biến `BASE_TAGS`). **Sửa cho khớp nhân vật**
  (vd đổi `long black hair` nếu nhân vật tóc bạc — xem mục Lưu ý).
- Đặt tên file ảnh có keyword: `closeup`, `halfbody`, `front`, `side`, `back`, `sitting`, `action`/`sword`, `3q`.

## 2. Chuẩn bị dataset

Crop vuông, resize, copy ảnh + caption vào `dataset/<repeats>_<trigger>/`.

```powershell
cd E:\repos\ComfyUI\train_lora
..\venv\Scripts\python.exe prepare_dataset.py `
  --input_dir ..\output\lora_training_data\luxueqi_1024 `
  --trigger_word "luxueqi" `
  --image_size 1024 `
  --repeats 15
```

> Script **giữ lại caption** từ Bước 1 (đã sửa). Nếu console lỗi encoding tiếng Việt, thêm `$env:PYTHONUTF8=1` trước lệnh.
> 75 ảnh × 15 repeats = 1125 steps/epoch.

## 3. Train

```powershell
cd E:\repos\ComfyUI\train_lora
.\train_sdxl.bat
# hoặc trực tiếp (tránh pause của .bat):
$env:PYTHONUTF8=1; ..\venv\Scripts\python.exe ai-toolkit\run.py sdxl_lora_config.yaml
```

- ~3000 steps (~2.7 epoch), trên RTX 5060 Ti mất **~2 giờ** (~1.7–2.8s/it).
- Checkpoint + ảnh preview lưu **mỗi 500 steps** tại `output_lora\luxueqi_lora\` và `.../samples\`.
- Giữ 4 checkpoint gần nhất; file cuối: `luxueqi_lora.safetensors`.

### Config quan trọng (`sdxl_lora_config.yaml`)
| Tham số | Giá trị | Ghi chú |
|---------|---------|---------|
| `model.arch` | `"sdxl"` | **BẮT BUỘC** — thiếu sẽ dùng pipeline SD1.5 → crash khi sample |
| `network.linear` / `linear_alpha` | 16 / 16 | rank: 8=nhẹ, 16=cân bằng, 32=chi tiết |
| `train.steps` | 3000 | |
| `train.learning_rate` | 1e-4 | cosine + warmup 100 |
| `train.train_text_encoder` | true | SDXL nên train cả TE (khác Flux) |
| `sample.guidance_scale` | 7 | SDXL dùng 7 (Flux dùng 4) |
| `sample.sampler` | euler_a | SDXL (không phải flowmatch của Flux) |

> **Vì sao không dùng `flux_lora_config.yaml`:** Flux dùng `is_flux: true`, `quantize: true`, sampler flowmatch,
> guidance 4 — tất cả Flux-specific. SDXL cần `arch: sdxl`, train text_encoder, guidance 7.

## 4. Dùng LoRA

File cuối đã copy sẵn vào `E:\repos\ComfyUI\models\loras\luxueqi_lora.safetensors`.

Trong workflow ComfyUI:
1. **LoRALoader** node (sau CheckpointLoader, trước KSampler) → chọn `luxueqi_lora.safetensors`.
2. `strength_model` / `strength_clip` = **0.7–0.9** (tăng tới 1.0 nếu nhân vật ra nhạt).
3. Prompt bắt đầu bằng trigger **`luxueqi`**, kèm tag mô tả + **ghi rõ màu tóc**:
   ```
   luxueqi, 1girl, solo, white and blue hanfu, xianxia style, silver hair, blue eyes,
   close-up portrait, masterpiece, best quality
   ```
4. Negative: `lowres, bad anatomy, bad hands, worst quality, low quality, jpeg artifacts`
5. KSampler: steps 25–30, cfg 7, sampler `euler_ancestral`, 1024×1024.

### Test nhanh qua API (không cần mở GUI)
```powershell
# Khởi động server: .\run_gpu0.bat  (hoặc python main.py --port 8188)
venv\Scripts\python.exe test_luxueqi_lora.py   # sinh 2 ảnh test vào output\luxueqi_test_*.png
```

---

## Giữ nhân vật nhất quán giữa các cảnh

txt2img sinh mỗi ảnh độc lập nên mặt/phong cách dao động. Cách hiệu quả (đã kiểm chứng):

1. **Khoá seed + sampler tốt (mặc định):** `"lock_seed": true` + `"sampler": "dpmpp_2m"`,
   `"scheduler": "karras"`, `cfg 6`, `steps 30` trong `generation`. LoRA render nhân vật rất nhất quán,
   ảnh sắc nét, tông màu đồng bộ. Đây là cách chính.
2. **scene_suffix** (đã có): tag đồng bộ phong cách/màu cho mọi ảnh.
3. Trong cùng phân đoạn, lặp tag địa điểm/thời gian/ánh sáng để nền liền mạch.

> Giới hạn: vẫn là txt2img độc lập từng ảnh — giữ được *nhận diện nhân vật* + *phong cách*, nhưng
> nếp áo/góc mặt/chi tiết nền vẫn đổi giữa các cảnh (không phải storyboard hoàn hảo).

> Đã thử **IPAdapter-face** rồi **gỡ bỏ**: trên model anime này nó gây viền sắc/bạc màu, chất lượng kém
> hơn LoRA thuần. Muốn dùng lại thì cài `ComfyUI_IPAdapter_plus` + `ip-adapter-plus-face_sdxl_vit-h` +
> `CLIP-ViT-H-14` vào `models/ipadapter` & `models/clip_vision`.

---

## Lưu ý & Khắc phục

- **Màu tóc nhập nhằng:** `BASE_TAGS` trong `caption_training_images.py` ghi `long black hair` nhưng nhiều
  ảnh gốc tóc bạc → model học cả 2. Khắc phục: (a) ghi rõ màu tóc trong prompt khi dùng, hoặc
  (b) sửa `BASE_TAGS` cho đúng rồi caption lại + train lại.
- **Overfit:** nếu bản 3000 cứng/lặp, thử checkpoint sớm hơn (`luxueqi_lora_000002000.safetensors`...).
- **Lỗi `No module named 'cleanfid'/'controlnet_aux'`:** xem mục 0 (cài deps / vá extension loader).
- **Lỗi `'CLIPTextModel' object has no attribute 'text_model'`:** chưa áp bản vá transformers 5.x (mục 0).
- **Lỗi `argument of type 'NoneType' is not iterable` khi sample:** thiếu `arch: "sdxl"` trong config.
- **Console lỗi encoding (cp1258):** đặt `$env:PYTHONUTF8=1`.
