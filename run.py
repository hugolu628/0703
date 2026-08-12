import os
import sys
import threading
import time
import uvicorn
from salary_app import app


def run_fastapi():
    """在獨立執行緒中啟動 FastAPI（僅供內部 Gradio 呼叫）"""
    # 內部 API 綁定在 127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)


def run_gradio():
    """啟動 Gradio 介面（對外服務）"""
    from salary_interface import demo

    # 取得 Render 自動指派的對外 Port，若在本地端執行則預設使用 7860
    port = int(os.environ.get("PORT", 7860))

    print(f"🚀 Gradio 介面正在啟動於 0.0.0.0:{port}")

    # 必須綁定 0.0.0.0 才能讓 Render Health Check 與外部流量存取
    demo.launch(server_name="0.0.0.0", server_port=port)


if __name__ == "__main__":
    # 1. 先啟動 FastAPI 端點伺服器
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    # 給 API 一點點啟動時間
    time.sleep(2)

    # 2. 啟動 Gradio（作為主要對外服務）
    print("🚀 FastAPI 已就緒，正在開啟 Gradio UI...")
    run_gradio()