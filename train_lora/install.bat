@echo off
chcp 65001 > nul
echo ============================================================
echo   Flux LoRA Training Setup - ai-toolkit by ostris
echo ============================================================
echo.

REM Activate venv
call e:\repos\ComfyUI\venv\Scripts\activate.bat

REM Clone ai-toolkit nếu chưa có
if not exist "ai-toolkit" (
    echo [1/3] Cloning ai-toolkit...
    git clone https://github.com/ostris/ai-toolkit.git
    cd ai-toolkit
    git submodule update --init --recursive
    cd ..
) else (
    echo [1/3] ai-toolkit da ton tai, skip clone.
)

REM Cài dependencies
echo [2/3] Cai dat dependencies...
pip install -r ai-toolkit/requirements.txt --quiet

REM Cài thêm quantization support
pip install bitsandbytes --quiet

echo [3/3] Setup hoan tat!
echo.
echo Buoc tiep theo:
echo   1. Chuan bi anh nhan vat (20-50 anh) vao mot folder
echo   2. Chay: python prepare_dataset.py --input_dir ./my_images --trigger_word "ohwx cat"
echo   3. Sua flux_lora_config.yaml (model path, trigger_word, steps)
echo   4. Chay: python ai-toolkit/run.py flux_lora_config.yaml
echo.
pause
