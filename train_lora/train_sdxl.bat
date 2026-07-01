@echo off
chcp 65001 > nul
echo ============================================================
echo   SDXL LoRA Training - miaomiao_mature_edition
echo ============================================================

call e:\repos\ComfyUI\venv\Scripts\activate.bat

if not exist "sdxl_lora_config.yaml" (
    echo [ERROR] Khong tim thay sdxl_lora_config.yaml
    echo Hay chay tu thu muc train_lora/
    pause & exit /b 1
)

if not exist "ai-toolkit/run.py" (
    echo [ERROR] ai-toolkit chua duoc cai. Chay install.bat truoc!
    pause & exit /b 1
)

REM Kiem tra dataset co ton tai khong
if not exist "dataset" (
    echo [WARN] Thu muc dataset/ chua ton tai!
    echo Hay chay prepare_dataset.py truoc:
    echo   python prepare_dataset.py --input_dir ..\output\lora_training_data\luxueqi_1024 --trigger_word "luxueqi" --image_size 1024 --repeats 15
    pause & exit /b 1
)

echo [INFO] Bat dau SDXL LoRA training...
echo [INFO] Config: sdxl_lora_config.yaml
echo [INFO] Nhan Ctrl+C de dung training
echo.

python ai-toolkit/run.py sdxl_lora_config.yaml

echo.
echo ============================================================
echo Training xong!
echo LoRA luu tai: output_lora\luxueqi_lora\
echo Copy file .safetensors vao: E:\repos\ComfyUI\models\loras\
echo ============================================================
pause
