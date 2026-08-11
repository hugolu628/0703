import gradio as gr
import requests

# FastAPI 端點 URL (假設與 Gradio 在同一台機器，使用 localhost)
BASE_URL = "http://127.0.0.1:8000"

def predict_salary(years_experience, education_level, city):
    """呼叫 FastAPI 的 /predict 端點來進行預測"""
    payload = {
        "years_experience": float(years_experience),
        "education_level": education_level,
        "city": city
    }
    try:
        response = requests.post(f"{BASE_URL}/predict", json=payload)
        if response.status_code == 200:
            data = response.json()
            return f"${data['predicted_salary']:,.2f}", f"${data['estimated_annual_salary']:,.2f}" # 注意：原 app.py 欄位名是 estimated_annual_salary (少了一個 y?) -> 查看原始碼
        else:
            return f"Error: {response.status_code}", "N/A"
    except Exception as e:
        return str(e), "N/A"

def train_model(test_size, random_state, model_type, alpha):
    """呼叫 FastAPI 的 /train 端點來訓練模型"""
    payload = {
        "test_size": float(test_size),
        "random_state": int(random_state),
        "model_type": model_type,
        "alpha": float(alpha)
    }
    try:
        response = requests.post(f"{BASE_URL}/train", json=payload)
        if response.status_code == 200:
            data = response.json()
            status_text = f"✅ {data['message']}\n\n" \
                          f"📊 R² Score: {data['r2']:.4f}\n" \
                          f"🕒 Training Time: {data['train_time']:.2f}s"
            return status_text
        else:
            return f"❌ 訓練失敗: {response.json().get('detail', '未知錯誤')}"
    except Exception as e:
        return f"❌ 連線錯誤: {str(e)}"

# 定義 Gradio UI
with gr.Blocks(theme=gr.themes.Soft()) as demo:
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

            predict_btn.click(
                fn=predict_salary,
                inputs=[years_exp, edu_level, city_val],
                outputs=[output_monthly, output_annual]
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
                fn=train_model,
                inputs=[t_test_size, t_random_state, t_model_type, t_alpha],
                outputs=t_result
            )

if __name__ == "__main__":
    demo.launch()