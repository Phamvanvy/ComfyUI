# Huong Dan Tao Training Data Nhan Vat Tru Tien voi ComfyUI + Flux

> Muc tieu: Tao 30-60 anh chat luong cao cua cac nhan vat Tru Tien de train LoRA voi Flux model.

---

## 1. Gioi Thieu Pipeline

Pipeline tao training data cho nhan vat Tru Tien hoat dong theo trinh tu:

```
[Flux Model] → [ComfyUI Workflow] → [Anh generate] → [Upscale 4x] → [Resize 1024px]
     ↓
[Caption tung anh (trigger word + tag mo ta)]
     ↓
[Dataset folder chuan] → [ai-toolkit training] → [LoRA .safetensors]
     ↓
[Load LoRA vao ComfyUI → gen anh nhan vat co dinh]
```

**Diem manh cua pipeline nay:**
- Dung Flux (qua ComfyUI-GGUF) nen chat luong anh cao, to hop prompt linh hoat
- Upscale 4x -> 1024px dam bao do phan giai du de train
- ai-toolkit ho tro Flux LoRA training tren RTX 5060 Ti (16GB VRAM)
- Khong can IPAdapter hay ControlNet de gen training data - chi can prompt ky cang

**Luu y ve Flux GGUF:**
Neu ban dang dung Flux qua ComfyUI-GGUF (file `.gguf`), luu y rang training voi ai-toolkit can file
`flux1-dev.safetensors` day du (khong phai GGUF). Xem Buoc 3 de biet them.

---

## 2. Cac Node Can Cai Them

Workflow `tru_tien_training_data.json` yeu cau cac node sau. Kiem tra va cai neu thieu:

### Nodes co san (da cai)
- **ComfyUI-GGUF** - Load model Flux dang GGUF
- **ComfyUI-Manager** - Quan ly custom nodes

### Nodes can cai bo sung

#### 2.1. Image Upscale (BAN BUOC PHAI CO)

| Node | Chuc nang | Tim trong Manager |
|------|-----------|-------------------|
| `ImageUpscaleWithModel` | Upscale 4x bang AI model | Co san trong ComfyUI core |
| `UpscaleModelLoader` | Load model 4x-UltraSharp | Co san trong ComfyUI core |
| `ImageScale` | Resize ve 1024x1024 | Co san trong ComfyUI core |

> Model upscale can tai: `4x-UltraSharp.pth`
> - Dat vao: `E:\repos\ComfyUI\models\upscale_models\`
> - Tai tai: https://openmodeldb.info/models/4x-UltraSharp

#### 2.2. Node khong bat buoc nhung rat huu ich

**WAS Node Suite** - Cung cap ImageSaveAdvanced, text overlay, v.v.
```
ComfyUI-Manager → Custom Nodes Manager → tim "WAS Node Suite" → Install
```
Link: https://github.com/WASasquatch/was-node-suite-comfyui

**ComfyUI-Impact-Pack** - Face detailer de sua chi tiet khuon mat
```
ComfyUI-Manager → Custom Nodes Manager → tim "ComfyUI Impact Pack" → Install
```
Link: https://github.com/ltdrdata/ComfyUI-Impact-Pack

> **IPAdapter va ControlNet khong can** cho pipeline nay. Viec giu nhat quan nhan vat duoc xu ly hoan toan qua prompt engineering va trigger word trong caption.

### Cach cai nhanh qua Manager:
1. Mo ComfyUI tai `http://127.0.0.1:8188`
2. Click bieu tuong **Manager** goc phai tren cung
3. Chon **Custom Nodes Manager**
4. Nhap ten node vao o tim kiem
5. Click **Install** → doi cai xong → **Restart ComfyUI**

---

## 3. Cach Dung Workflow `tru_tien_training_data.json`

### Buoc 3.1 - Load workflow

1. Mo ComfyUI: `http://127.0.0.1:8188`
2. Menu tren → **Load** → chon file `tru_tien_training_data.json`
   - Hoac: keo tha file `.json` thang vao cua so trinh duyet

> Neu chua co file `tru_tien_training_data.json`, ban co the bat dau tu workflow
> `miaomiao_training_data_gen.json` co san va chinh sua prompt theo nhan vat Tru Tien.

### Buoc 3.2 - Cau hinh Model

**Neu dung Flux GGUF (UFluxModelLoader):**
```
Node: UnetLoaderGGUF
  → unet_name: flux1-dev-Q8_0.gguf  (hoac phien ban GGUF ban co)

Node: DualCLIPLoaderGGUF (hoac DualCLIPLoader)
  → clip_name1: t5xxl_fp16.safetensors
  → clip_name2: clip_l.safetensors

Node: VAELoader
  → vae_name: ae.safetensors
```

**Neu dung Flux safetensors thuong (de train LoRA sau nay):**
```
Node: CheckpointLoaderSimple
  → ckpt_name: flux1-dev.safetensors
```

### Buoc 3.3 - Chinh Positive Prompt

Day la phan quan trong nhat. Cau truc prompt cho nhan vat Tru Tien:

```
[trigger_word], [mo ta nhan vat co dinh], [goc nhin], [tu the], [trang phuc], [boi canh]
```

Vi du cho **Tieu Tuong Da Vu**:
```
tieu tuong da vu, 1girl, long dark hair with blue highlights, pale skin, 
blue eyes, slender figure, xianxia cultivation robes, elegant expression,
[THAY GOC NHIN], [THAY TU THE], [THAY BOI CANH],
masterpiece, best quality, ultra detailed, anime style
```

**Phan KHONG THAY DOI (giu nguyen de dam bao nhat quan nhan vat):**
- Ten trigger word
- Mo ta to chuc vat ly: mau toc, mau mat, dang nguoi
- Style tag: xianxia, cultivation, anime

**Phan THAY DOI de tao da dang:**

| Phan thay doi | Cac lua chon |
|---------------|--------------|
| Goc nhin | `full body portrait`, `upper body`, `close-up face`, `side view`, `back view` |
| Tu the | `standing`, `sitting`, `walking`, `running`, `meditating`, `flying` |
| Trang phuc | `white robes`, `battle armor`, `casual hanfu`, `sect uniform` |
| Boi canh | `white background`, `mountain peaks`, `bamboo forest`, `celestial palace`, `night sky` |
| Anh sang | `soft lighting`, `dramatic shadows`, `moonlight`, `glowing cultivation aura` |

### Buoc 3.4 - Cai dat KSampler cho Flux

```
sampler_name: euler
scheduler: simple  (hoac beta)
steps: 25-35
cfg: 1.0  (Flux KHONG dung cfg cao - chi tu 1.0 den 3.5)
denoise: 1.0
```

> **Luu y Flux:** Khac voi SDXL, Flux dung guidance scale rat thap (1.0-3.5).
> Neu dung CFGGuider: set guidance 3.5 la tot nhat cho chat luong.

### Buoc 3.5 - Cai dat Image Size

```
Node: EmptyLatentImage (hoac EmptySD3LatentImage cho Flux)
  → width: 832
  → height: 1216   (ty le doc cho nhan vat dung)
  → batch_size: 1
```

Cac ty le pho bien cho training data:

| Width | Height | Phu hop |
|-------|--------|---------|
| 832 | 1216 | Portrait (nhan vat dung) |
| 1024 | 1024 | Square (khuon mat, bust) |
| 1216 | 832 | Landscape (canh quan) |

### Buoc 3.6 - Upscale Pipeline

Pipeline upscale da duoc cai san trong workflow:
```
VAEDecode → [Luu anh goc]
          ↓
ImageUpscaleWithModel (4x-UltraSharp)
          ↓
ImageScale → resize ve 1024x1024 (lanczos, crop: center)
          ↓
[Luu anh 1024px] ← DUNG CAI NAY DE TRAIN
```

**Thu muc luu anh:**
- Anh goc: `output/lora_training_data/tru_tien/`
- Anh 1024px cho training: `output/lora_training_data/tru_tien_1024/`

### Buoc 3.7 - Gen anh hang loat

1. **Random seed** moi lan gen: Bam nut dice (bieu tuong xuc xac) canh o Seed trong KSampler
2. **Thay doi 1 yeu to** moi batch (goc nhin / tu the / boi canh)
3. **So luong can dat:** Toi thieu 30 anh, tot nhat 50-60 anh
4. **Phan bo can can:**
   - 30-40% anh toan than (full body)
   - 25-30% nua than tren (upper body)
   - 20-25% khuon mat (face/bust)
   - 10-15% goc chup khac (side, back, 3/4)

---

## 4. Caption Strategy (Trigger Words va Style Tags)

Caption tot la yeu to quyet dinh LoRA hoc dung cach. Moi anh training can 1 file `.txt` cung ten.

### 4.1. Cau truc Caption Chuan

```
[TRIGGER_WORD], [MO TA NHAN VAT], [TU THE/GOC NHIN], [TRANG PHUC], [BOI CANH], [CHAT LUONG]
```

### 4.2. Trigger Words cho Tung Nhan Vat

| Nhan vat | Trigger Word de Xuat | Ghi chu |
|----------|---------------------|---------|
| Tieu Tuong Da Vu | `xiaoxiang nightrain` | Dung tieng Anh phien am |
| Luc Tuyet Ky | `lv xueqi girl` | |
| Bi Yen | `biye demon girl` | |
| Tran Dai | `chen da boy` | |
| Pho Thanh | `pu qing fairy` | Neu co trong truyen |

> **Lua chon trigger word:**
> - Dung cum tu 2-3 tu, KHONG trung voi tu trong tu vung model
> - Tranh dung: "girl", "boy", "beautiful" lam trigger word don le
> - Nen them: ten phien am + loai nhan vat (girl/boy/fairy/demon)

### 4.3. Vi du Caption Hoan Chinh

**Anh Tieu Tuong Da Vu toan than:**
```
xiaoxiang nightrain, 1girl, long dark hair with blue-black highlights, pale skin, 
dark blue eyes, slender elegant figure, white xianxia cultivation robes with dark blue trim,
silver accessories, full body standing, confident expression, looking at viewer,
bamboo forest background, soft moonlight, cultivation aura,
masterpiece, best quality, ultra detailed, anime style, xianxia fantasy
```

**Anh khuon mat Luc Tuyet Ky:**
```
lv xueqi girl, 1girl, short light green hair, bright green eyes, fair skin,
youthful gentle expression, green sect robes, upper body portrait,
close-up face, slight smile, indoor cultivation hall background,
masterpiece, best quality, detailed face, anime style
```

**Anh Bi Yen:**
```
biye demon girl, 1girl, long red hair, crimson eyes, seductive expression,
demon cultivation dark robes with red accents, gold accessories,
standing pose, side view, dark cave background with red glowing formations,
masterpiece, best quality, ultra detailed, dark fantasy anime style
```

### 4.4. Tags Quan Trong Can Co

**Tags bat buoc:**
- `masterpiece, best quality, ultra detailed`
- `anime style` (hoac `xianxia anime`)
- `1girl` / `1boy` (so luong nhan vat ro rang)

**Tags style Tru Tien dac trung:**
- `xianxia fantasy` - the gioi tu tien
- `cultivation robes` - ao tu tien
- `cultivation aura` - linh khi bao quanh
- `ancient chinese architecture` - kien truc co dai
- `sword immortal` - kiem tu (neu dung canh chien dau)
- `spirit beast` - linh thu (neu co trong canh)

**Tags NEN TRANH (co the lam model hoc sai):**
- Tranh dung ten chinh xac tieng Trung cua nhan vat lam tag thuong (vi no se "chay" voi kien thuc model)
- Tranh them qua nhieu tag mau sac ma khong lien quan den nhan vat

### 4.5. Caption Dropout (Quan Trong cho Training)

Trong `flux_lora_config.yaml` da co:
```yaml
caption_dropout_rate: 0.05
```
5% so anh se train khong co caption → giup LoRA hoc dung concept nhan vat, khong phu thuoc hoan toan vao text.

---

## 5. Dataset Structure (Cau Truc Thu Muc)

### 5.1. Cau truc thu muc de xuat

```
E:\repos\ComfyUI\train_lora\
├── dataset\
│   └── tru_tien_chars\
│       ├── 15_xiaoxiang nightrain\     ← "15_" = so lan repeat, ten = trigger word
│       │   ├── img_001.png
│       │   ├── img_001.txt             ← caption cua img_001.png
│       │   ├── img_002.png
│       │   ├── img_002.txt
│       │   └── ...
│       ├── 15_lv xueqi girl\
│       │   ├── img_001.png
│       │   ├── img_001.txt
│       │   └── ...
│       └── 15_biye demon girl\
│           ├── img_001.png
│           └── img_001.txt
├── flux_lora_config.yaml
├── train.bat
├── install.bat
└── output_lora\                        ← LoRA output tu training
```

### 5.2. Ten thu muc con: "repeats_triggerword"

Format: `[so_repeat]_[trigger word]`

```
15_xiaoxiang nightrain   → repeat anh 15 lan moi epoch
20_lv xueqi girl         → repeat 20 lan (it anh hon nen repeat nhieu hon)
```

**Tinh so repeat hop ly:**
- 40-50 anh: dung repeat 10-12
- 25-35 anh: dung repeat 15-20
- 15-25 anh: dung repeat 20-25

> Muc tieu: tong so anh * repeat ~ 500-1000 anh effective moi epoch

### 5.3. Neu train nhieu nhan vat cung luc

```
dataset\
└── tru_tien_multi\
    ├── 12_xiaoxiang nightrain\    (50 anh * 12 = 600)
    ├── 15_lv xueqi girl\          (40 anh * 15 = 600)
    └── 20_biye demon girl\        (30 anh * 20 = 600)
```

Giu so effective tuong duong giua cac nhan vat de tranh mot nhan vat "at" nhan vat khac.

### 5.4. Cach tao caption nhanh (script tu dong)

Tao file `create_captions.py` trong thu muc dataset:

```python
import os

# Thay bang trigger word va mo ta nhan vat cua ban
CHARACTER_CONFIGS = {
    "xiaoxiang nightrain": {
        "base": "xiaoxiang nightrain, 1girl, long dark hair with blue highlights, pale skin, dark blue eyes, slender figure, white xianxia robes",
        "quality": "masterpiece, best quality, ultra detailed, anime style, xianxia fantasy"
    },
    "lv xueqi girl": {
        "base": "lv xueqi girl, 1girl, short light green hair, bright green eyes, fair skin, gentle expression, green sect robes",
        "quality": "masterpiece, best quality, ultra detailed, anime style, xianxia fantasy"
    }
}

# Mo ta tu the / boi canh (tu dong trich tu ten file hoac de trong)
SCENE_TAGS = "standing, looking at viewer, outdoor background"

for char_name, config in CHARACTER_CONFIGS.items():
    folder = f"./tru_tien_chars/15_{char_name}"
    for img_file in os.listdir(folder):
        if img_file.endswith((".png", ".jpg", ".webp")):
            caption = f"{config['base']}, {SCENE_TAGS}, {config['quality']}"
            txt_file = os.path.splitext(img_file)[0] + ".txt"
            with open(os.path.join(folder, txt_file), "w", encoding="utf-8") as f:
                f.write(caption)
            print(f"Created: {txt_file}")
```

> **Luu y:** Moi anh nen co caption rieng biet mo ta chinh xac tu the va boi canh trong anh do.
> Script tren chi la diem bat dau - nen chinh tay caption cho anh quan trong.

---

## 6. Train LoRA

### 6.1. Chuan bi (Lan dau)

```batch
cd E:\repos\ComfyUI\train_lora
install.bat
```

Script se:
1. Clone ai-toolkit tu GitHub
2. Cai cac thu vien can thiet (torch, diffusers, v.v.)
3. Cai bitsandbytes cho 8-bit optimizer

### 6.2. Cau hinh `flux_lora_config.yaml`

Mo file `E:\repos\ComfyUI\train_lora\flux_lora_config.yaml` va sua cac muc sau:

```yaml
config:
  name: "tru_tien_lora"           # Ten LoRA output

  process:
    - type: sd_trainer

      device: cuda:0              # GPU so 0 (hoac cuda:1 cho GPU thu 2)
      
      trigger_word: "xiaoxiang nightrain"  # Trigger word CHINH (nhan vat chu yeu)

      network:
        type: "lora"
        linear: 16                # Rank: 16 la can bang tot
        linear_alpha: 16

      datasets:
        - folder_path: "./dataset/tru_tien_chars"
          caption_ext: "txt"
          caption_dropout_rate: 0.05
          cache_latents_to_disk: true
          resolution: [512, 768, 1024]

      train:
        batch_size: 1
        steps: 3000               # 50 anh → 3000-4000 steps
        learning_rate: 1.0e-4
        optimizer: "adamw8bit"
        dtype: bf16

      model:
        name_or_path: "E:/repos/ComfyUI/models/diffusion_models/FLUX1/flux1-dev.safetensors"
        is_flux: true
        quantize: true            # Bat de tiet kiem VRAM (RTX 5060 Ti 16GB)

      sample:
        sampler: "flowmatch"
        sample_every: 500
        width: 768
        height: 1024
        prompts:
          - "xiaoxiang nightrain standing in bamboo forest, xianxia robes"
          - "xiaoxiang nightrain close-up face portrait, moonlight"
          - "xiaoxiang nightrain full body, cultivation aura"
        guidance_scale: 3.5
        sample_steps: 25
```

**So steps de xuat:**

| So anh | So steps | Ghi chu |
|--------|----------|---------|
| 20-25 anh | 1500-2000 | Nhanh, co the bi underfit |
| 30-40 anh | 2500-3500 | Can bang |
| 50-60 anh | 4000-5000 | Chat luong tot nhat |

### 6.3. Bat dau Training

```batch
cd E:\repos\ComfyUI\train_lora
train.bat
```

Training se bat dau va:
- Hien thi tien do moi step
- Luu checkpoint moi 500 steps vao `output_lora/`
- Gen anh preview moi 500 steps de kiem tra ket qua

### 6.4. Ket qua Training

File LoRA se luu tai:
```
E:\repos\ComfyUI\train_lora\output_lora\tru_tien_lora\
├── tru_tien_lora_000500.safetensors
├── tru_tien_lora_001000.safetensors
├── tru_tien_lora_002000.safetensors
└── tru_tien_lora_003000.safetensors   ← Final
```

**Copy vao ComfyUI:**
```batch
copy output_lora\tru_tien_lora\tru_tien_lora_003000.safetensors ^
     E:\repos\ComfyUI\models\loras\tru_tien_lora.safetensors
```

### 6.5. Su dung LoRA trong ComfyUI

Them node `LoraLoader` vao sau `CheckpointLoader`:
```
CheckpointLoader → LoraLoader → KSampler
                       ↑
                  lora_name: tru_tien_lora.safetensors
                  strength_model: 0.8  (0.6-1.0, thu tung gia tri)
                  strength_clip: 0.8
```

---

## 7. Tips Cho Tung Nhan Vat Tru Tien

### 7.1. Tieu Tuong Da Vu (Xiaoxiang Nightrain)

**Nhan dang nhan vat:**
- Toc dai den/xanh den, da trang nhat
- Mat xanh dam, bieu cam thanh thiet lanh lung
- Ao truyen thong trang/xanh dam, phu kien bac
- Linh khi xanh/den bao quanh khi thi phap

**Prompt template:**
```
xiaoxiang nightrain, 1girl, very long black hair with dark blue highlights,
pale white skin, deep dark blue eyes, cold elegant expression,
white xianxia cultivation robes with dark blue trim, silver hairpin,
[SCENE], dark blue spiritual energy aura,
masterpiece, best quality, anime xianxia style
```

**Canh goi y:** Canh dem voi trang sang, dinh nui, rung truc, bau troi sao

**Tranh:** Bieu cam vui cuoi qua lo (nhan vat nay lanh lung), ao mau hong/do

### 7.2. Luc Tuyet Ky (Lv Xueqi)

**Nhan dang nhan vat:**
- Toc ngan xanh la / toc trung binh
- Mat xanh la, ve mat hien diu, thanh thuan
- Ao mon phai xanh la cua Phu Thanh Son
- That lung xanh, trang phuc don gian sach se

**Prompt template:**
```
lv xueqi girl, 1girl, medium light green hair, bright green eyes,
fair skin, gentle sweet expression, youthful appearance,
green xianxia sect robes, simple jade accessories,
[SCENE], soft green spiritual aura,
masterpiece, best quality, anime style, gentle lighting
```

**Canh goi y:** Buoi sang o Phu Thanh Son, hoc phap thuat, canh thiep thu, rung xanh

**Tranh:** Bieu cam lanh lung/ac doc, ao mau den/do, boi canh dem toi

### 7.3. Bi Yen (Biye Demon)

**Nhan dang nhan vat:**
- Toc dai do/den, mac quyen ru
- Mat do/hong, bieu cam goi cam quyen ru
- Ao ma dao den do, phu kien vang
- Khi hoang mau do xung quanh

**Prompt template:**
```
biye demon girl, 1girl, long crimson-red hair, bright red or pink eyes,
light skin, alluring seductive expression, confident demeanor,
dark demon cultivation robes with red accents, gold accessories,
[SCENE], red demonic spiritual energy swirling,
masterpiece, best quality, ultra detailed, dark fantasy anime style
```

**Canh goi y:** Hang dong toi, the gioi ma dao, anh sang do/vang, kien truc den

**Tranh:** Ve mat thuan thien, ao trang/xanh, khung canh sach se thuan khiet

### 7.4. Tran Dai (Chen Da - Nhan vat chinh nam)

**Nhan dang nhan vat:**
- Toc den, dang nguoi thanh cao
- Ve mat quyet doan, mat den/nau
- Trang phuc don gian khi tre, ao mon phai sau nay
- Khi chat mau xanh/trang khi truong thanh

**Prompt template:**
```
chen da boy, 1boy, short black hair, determined dark eyes, lean figure,
focused serious expression, simple xianxia training robes,
[SCENE], cyan blue spiritual energy,
masterpiece, best quality, anime style, xianxia fantasy
```

**Canh goi y:** Luyen kiem, tu hanh, canh chien dau, vach nui khac lo de

### 7.5. Cac Nhan Vat Phu Khac

**Xiaozhu (Nhan vat phu nu nho):**
```
xiaozhu spirit, small female figure, white spirit form, glowing soft blue,
ethereal translucent appearance, gentle innocent expression,
floating pose, spiritual energy wisps,
masterpiece, best quality, anime style
```

**Su phu / Lanh tu cac mon phai:**
```
xianxia sect elder, [nam/nu], ancient cultivation master,
ceremonial robes of [ten mon phai], long white hair, wise expression,
[phu kien dac trung mon phai], powerful spiritual pressure aura,
masterpiece, best quality, detailed, mature xianxia style
```

---

## 8. Kiem Tra Chat Luong va Xu Ly Loi

### 8.1. Anh khong nhat quan giua cac lan gen

**Nguyen nhan:** Prompt thay doi qua nhieu, hoac phan nhan vat co dinh khong du manh

**Giai phap:**
- Them trong so cho dac diem nhan vat: `long black hair:1.3`
- Giu y bieu cam va cau hinh toc hoan toan giong nhau giua cac canh
- Dung batch size cao hon (gen 4 anh cung luc) de so sanh

### 8.2. Anh loi anatomical (tay chan di dang)

**Giai phap:**
- Them vao negative: `bad hands, extra fingers, deformed limbs, bad anatomy`
- Voi Flux: Tang buoc step len 35-40
- Su dung ADetailer / Face Detailer neu co ComfyUI-Impact-Pack

### 8.3. Training LoRA cho ket qua nhat nhat, khong ro nhan vat

**Nguyen nhan co the:**
- It anh qua (duoi 20 anh)
- Caption qua don gian hoac sai
- Steps qua it
- Trigger word trung voi tu co san cua model

**Giai phap:**
- Tang len toi thieu 30 anh
- Kiem tra lai caption: phai ro rang, day du
- Tang steps them 500-1000
- Doi trigger word thanh cum tu doc dao hon

### 8.4. VRAM het trong luc training

**Giai phap cho RTX 5060 Ti 16GB:**
```yaml
train:
  batch_size: 1          # KHONG tang len
  gradient_accumulation_steps: 2  # Tang len de bu
model:
  quantize: true         # Bat luon
  # quantize_te: true   # Bat them neu van het VRAM
train:
  dtype: bf16
  optimizer: "adamw8bit"  # Dung 8bit
```

---

## 9. Quy Trinh Tom Tat

```
1. CHUAN BI
   └── Cai 4x-UltraSharp.pth vao models/upscale_models/
   └── Kiem tra co flux1-dev.safetensors (cho training)

2. GEN ANH (ComfyUI)
   └── Load tru_tien_training_data.json
   └── Sua prompt theo nhan vat (giu phan mo ta nhan vat, thay doi scene)
   └── Random seed, gen 50-60 anh
   └── Anh luu tai: output/lora_training_data/[nhan_vat]_1024/

3. CAPTION
   └── Moi anh .png can 1 file .txt cung ten
   └── Caption: [trigger_word], [mo ta nhan vat], [scene], [quality tags]
   └── Dat vao: train_lora/dataset/tru_tien_chars/15_[trigger_word]/

4. TRAINING
   └── Sua flux_lora_config.yaml (trigger_word, folder_path, steps)
   └── Chay: train.bat
   └── Doi den step cuoi, copy .safetensors vao models/loras/

5. DUNG LORA
   └── Them LoraLoader node vao workflow
   └── strength: 0.7-0.9
   └── Them trigger word vao dau prompt
```

---

*Huong dan nay ap dung cho: ComfyUI + Flux GGUF + ai-toolkit + RTX 5060 Ti (16GB VRAM)*
*Cap nhat: 2026-06-01*
