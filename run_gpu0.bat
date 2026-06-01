@echo off
echo Starting ComfyUI on Port 8188 (Primary: GPU 0)...
call venv\Scripts\activate
python main.py --cuda-device 0 --port 8188
python main.py --port 8188