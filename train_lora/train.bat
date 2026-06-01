@echo off
chcp 65001 > nul
echo ============================================================
echo   Flux LoRA Training
echo ============================================================

REM Activate venv
call e:\repos\ComfyUI\venv\Scripts\activate.bat

REM Check config
if not exist "flux_lora_config.yaml" (
    echo [ERROR] Khong tim thay flux_lora_config.yaml
    echo Hay chay tu thu muc train_lora/
    pause
    exit /b 1
)

REM Check ai-toolkit
if not exist "ai-toolkit/run.py" (
    echo [ERROR] ai-toolkit chua duoc cai. Chay install.bat truoc!
    pause
    exit /b 1
)

echo [INFO] Bat dau training...
echo [INFO] Config: flux_lora_config.yaml
echo [INFO] Nhan Ctrl+C de dung training
echo.

python ai-toolkit/run.py flux_lora_config.yaml

echo.
echo Training ket thuc! LoRA luu tai: output_lora/
echo Copy file .safetensors vao: E:\repos\ComfyUI\models\loras\
pause
