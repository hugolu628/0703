import os
import sys

# 將當前檔案所在目錄加入 sys.path，確保無論從何處啟動都能導入兄弟模組
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import gradio as gr

# 直接呼叫 salary_app 中的處理函式 (in-process)，不再透過 HTTP 呼叫本機 FastAPI
from salary_app import predict_gradio_handler, train_gradio_handler

# 定義 Gradio UI (Gradio 6 的 theme 需在 Blocks 建立後再指定)
with gr.Blocks() as demo:
    gr.Markdown("# 💰 薪資預測系統 (Salary Predictor with FastAPI & Gradio)")

    with gr.Tabs():
        # --- 第一個分頁：薪資預測 ---
        with gr.Tab("📊 薪資預測"):
            gr.Markdown("### 輸入您的背景資訊以估算年薪")
            with gr.Row():
                with gr.Column():
                    years_exp = gr.Slider(minimum=0, maximum=50, value=5, step=0.5, label="工作經驗 (Years)")
                    edu_level = gr.Dropdown(choices=["高中以下", "大學", "碩士以上"], value="大學", label="最高學歷")
                    city_val = gr.Dropdown(choices=["城市A", "城市B", "城市C"], value="城市A", label="居住城市")
                    predict_btn = gr.Button("立即預測 🚀", variant="primary")

                with gr.Column():
                    output_monthly = gr.Textbox(label="預估月薪 (Estimated Monthly)", placeholder="...")
                    output_annual = gr.Textbox(label="預估年薪 (Estimated Annual)", placeholder="...")

            # queue=False / show_progress="hidden"：避免 Render 反向代理緩衝 SSE 佇列，
            # 造成結果卡在 queue 而無法回傳
            predict_btn.click(
                fn=predict_gradio_handler,
                inputs=[years_exp, edu_level, city_val],
                outputs=[output_monthly, output_annual],
                queue=False,
                show_progress="hidden",
            )

        # --- 第二個分頁：模型訓練 ---
        with gr.Tab("⚙️ 模型管理"):
            gr.Markdown("### 調整超參數並重新訓練模型")
            with gr.Row():
                with gr.Column():
                    t_test_size = gr.Slider(minimum=0.1, maximum=0.5, value=0.2, step=0.05, label="測試集比例 (Test Size)")
                    t_random_state = gr.Number(value=76, label="隨機種子 (Random State)")
                    t_model_type = gr.Dropdown(choices=["LinearRegression", "Lasso", "Ridge"], value="LinearRegression", label="模型演算法")
                    t_alpha = gr.Slider(minimum=0.001, maximum=100, value=1.0, step=0.01, label="Alpha (正則化強度)")
                    train_btn = gr.Button("開始訓練 🔄", variant="secondary")

                with gr.Column():
                    t_result = gr.Textbox(label="訓練狀態與結果", lines=8)

            train_btn.click(
                fn=train_gradio_handler,
                inputs=[t_test_size, t_random_state, t_model_type, t_alpha],
                outputs=t_result,
                queue=False,
                show_progress="hidden",
            )

# ⚠️ 透過 uvicorn 載入 (不經過 demo.launch()) 時，必須手動指定主題並補算 CSS 與雜湊值，
# 否則瀏覽器端會請求 /theme.css?v=null 並得到 500，UI 會退化成無樣式頁面
import hashlib

demo.theme = gr.themes.Soft(primary_hue="blue", secondary_hue="indigo")
demo.theme_css = demo.theme._get_theme_css()
demo.stylesheets = demo.theme._stylesheets
demo.theme_hash = hashlib.sha256(demo.theme_css.encode("utf-8")).hexdigest()

# 放寬佇列的預設併發數，避免多位使用者或連續操作互相阻塞
demo.queue(default_concurrency_limit=10)

if __name__ == "__main__":
    from run import main
    main()
