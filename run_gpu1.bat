@echo off
echo Starting ComfyUI on GPU 1 (port 8189)...
call venv\Scripts\activate
set CUDA_VISIBLE_DEVICES=1
python main.py --port 8189

python main.py --cuda-device 1 --port 8188