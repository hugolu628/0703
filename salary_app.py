import os
import sys
from pprint import pprint

import numpy as np
import pandas as pd
from train_save import train_and_save_model

import gradio as gr
import joblib
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

model_path = os.path.join(current_dir, "salary_model.joblib")
MODEL_STATE = {}


class TrainConfig(BaseModel):
    test_size: float = Field(0.2, description="測試集分割比例", ge=0.1, le=0.5)
    random_state: int = Field(76, description="隨機種子", ge=0)
    model_type: str = Field(
        "LinearRegression",
        description="模型演算法類型 (LinearRegression, Lasso, Ridge)",
    )
    alpha: float = Field(
        1.0,
        description="正則化強度 alpha (適用於 Lasso 與 Ridge)",
        ge=0.001,
        le=100.0,
    )


class TrainResult(BaseModel):
    status: str = Field(..., description="執行結果狀態")
    r2: float = Field(..., description="測試集 R-squared 決定係數")
    coef: list[float] = Field(..., description="特徵權重係數列表")
    intercept: float = Field(..., description="截距")
    feature_coefs: dict[str, float] = Field(..., description="特徵及其權重映射")
    model_type: str = Field(..., description="模型演算法類型")
    alpha: float = Field(..., description="正則化強度 alpha")
    train_time: float = Field(..., description="訓練耗時 (秒)")
    message: str = Field(..., description="提示訊息")


class SalaryInput(BaseModel):
    years_experience: float = Field(..., ge=0.0, le=50.0)
    education_level: str
    city: str


class SalaryOutput(BaseModel):
    predicted_salary: float
    estimated_annual_salary: float


def load_model_state():
    global MODEL_STATE
    if not os.path.exists(model_path):
        train_and_save_model()

    model_data = joblib.load(model_path)
    MODEL_STATE.clear()
    MODEL_STATE.update(
        {
            "model": model_data["model"],
            "oe": model_data["oe"],
            "ohe": model_data["ohe"],
            "scaler": model_data["scaler"],
            "r2": model_data.get("r2"),
            "feature_names": model_data["feature_names"],
            "feature_coefs": model_data.get("feature_coefs", {}),
            "model_type": model_data.get("model_type"),
            "alpha": model_data.get("alpha"),
        }
    )


load_model_state()

app = FastAPI()


# 新增健康檢查/首頁路由，防止 Render 報 404
@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "Salary Prediction API & UI is running.",
        "gui_url": "/gui",
    }


# 核心預測邏輯 (提供給 API 與 Gradio 共用)
def predict_salary_logic(years_experience: float, education_level: str, city: str):
    oe = MODEL_STATE["oe"]
    ohe = MODEL_STATE["ohe"]
    scaler = MODEL_STATE["scaler"]
    model = MODEL_STATE["model"]

    edu_encoded = int(
        oe.transform(
            pd.DataFrame([[education_level]], columns=["EducationLevel"])
        )[0][0]
    )
    city_vector = ohe.transform(pd.DataFrame([[city]], columns=["City"]))
    city_cols = ohe.get_feature_names_out(["City"])
    feature_row = [years_experience, edu_encoded] + list(city_vector[0])
    features = pd.DataFrame(
        [feature_row], columns=["YearsExperience", "EducationLevel"] + list(city_cols)
    )
    X_scaled = scaler.transform(features)
    predicted_salary = float(model.predict(X_scaled)[0])
    return predicted_salary, predicted_salary * 14


# API 端點
@app.post("/train", response_model=TrainResult)
def train_endpoint(config: TrainConfig):
    try:
        res = train_and_save_model(
            test_size=config.test_size,
            random_state=config.random_state,
            model_type=config.model_type,
            alpha=config.alpha,
        )
        load_model_state()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"線上訓練失敗: {str(e)}")

    return res


@app.post("/predict", response_model=SalaryOutput)
def predict_endpoint(payload: SalaryInput):
    monthly, annual = predict_salary_logic(
        payload.years_experience, payload.education_level, payload.city
    )
    return SalaryOutput(
        predicted_salary=monthly, estimated_annual_salary=annual
    )


# --- 建立 Gradio UI ---
def gradio_predict(years_experience, education_level, city):
    try:
        monthly, annual = predict_salary_logic(
            years_experience, education_level, city
        )
        return f"${monthly:,.2f} 元", f"${annual:,.2f} 元"
    except Exception as e:
        return f"預測出錯: {str(e)}", ""


demo = gr.Interface(
    fn=gradio_predict,
    inputs=[
        gr.Number(label="工作經驗年資 (Years Experience)", value=3.0),
        gr.Textbox(
            label="學歷 (Education Level)", placeholder="例如: Bachelor, Master"
        ),
        gr.Textbox(label="城市 (City)", placeholder="例如: Taipei, Hsinchu"),
    ],
    outputs=[
        gr.Textbox(label="預估月薪 (Predicted Monthly Salary)"),
        gr.Textbox(label="預估年薪 14個月 (Estimated Annual Salary)"),
    ],
    title="薪資預測系統",
    description="輸入年資、學歷與城市以進行薪資預估",
)

# 將 Gradio 掛載到 FastAPI 的 /gui 路徑上
app = gr.mount_gradio_app(app, demo, path="/gui")

if __name__ == "__main__":
    # 讀取 Render 自動傳入的 PORT，本機測試預設 10000
    port = int(os.environ.get("PORT", 10000))

    # 部署至 Render 必須綁定 0.0.0.0
    uvicorn.run("salary_app:app", host="0.0.0.0", port=port, reload=False)