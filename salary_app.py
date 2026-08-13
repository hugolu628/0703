import os
import sys
from dotenv import load_dotenv
load_dotenv()
from salary_train_save import train_and_save_model
from pydantic import BaseModel,Field
from pprint import pprint
import joblib
from fastapi import FastAPI,HTTPException
import uvicorn
import pandas as pd
import numpy as np


current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

model_path = os.path.join(current_dir, "salary_model.joblib")
MODEL_STATE = {}


class TrainConfig(BaseModel):
    test_size: float = Field(0.2, description="測試集分割比例", ge=0.1 , le=0.5)
    random_state: int = Field(76, description="隨機種子", ge=0)
    model_type: str = Field("LinearRegression", description="模型演算法類型 (LinearRegression, Lasso, Ridge)")
    alpha: float = Field(1.0, description="正則化強度 alpha (適用於 Lasso 與 Ridge)", ge= 0.001, le=100.0)

class TrainResult(BaseModel):
    status: str = Field(..., description="執行結果狀態")
    r2: float = Field(..., description="測試集 R-squared 決定係數")
    coef: list[float] = Field(..., description="特徵權重係數列表")
    intercept: float = Field(..., description="截距")
    feature_coefs: dict[str, float] = Field(..., description="特徵及其權重映射")
    model_type: str = Field(..., description="模型演算法類型")
    alpha: float = Field(..., description="正則化強度 alpha")
    train_time: float = Field(..., description="訓練耗時 (秒)")
    message:str = Field(..., description="提示訊息")

class SalaryInput(BaseModel):
    years_experience: float = Field(..., ge=0.0, le=50.0)
    education_level:str
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
            "feature_coefs": model_data.get("feature_coefs",{}),
            "model_type": model_data.get("model_type"),
            "alpha": model_data.get("alpha")
        }
    )

load_model_state()

app = FastAPI()
@app.post("/train", response_model=TrainResult)
def train_endpoint(config:TrainConfig):
    """
    訓練端點：傳入測試集比例、隨機種子、模型類型與 alpha，線上重新訓練模型，並即時更新服務所使用的模型。
    """
    try:
        # 1. 執行重新訓練並儲存模型
        res = train_and_save_model(
            test_size=config.test_size,
            random_state= config.random_state,
            model_type= config.model_type,
            alpha=config.alpha
        )
         # 2. 線上重新載入最新模型狀態至全域變數
        load_model_state()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"線上訓練失敗: {str(e)}")

    return res

@app.post("/predict", response_model=SalaryOutput)
def predict_endpoint(payload:SalaryInput):
    oe = MODEL_STATE["oe"]
    ohe = MODEL_STATE["ohe"]
    scaler = MODEL_STATE["scaler"]
    model = MODEL_STATE["model"]

    edu_encoded = int(oe.transform(pd.DataFrame([[payload.education_level]], columns=["EducationLevel"]))[0][0])
    city_vector = ohe.transform(pd.DataFrame([[payload.city]], columns=["City"]))
    city_cols = ohe.get_feature_names_out(['City'])
    feature_row = [payload.years_experience, edu_encoded] + list(city_vector[0])
    features = pd.DataFrame([feature_row],columns=["YearsExperience", "EducationLevel"] + list(city_cols))
    X_scaled = scaler.transform(features)
    predicted_salary = float(model.predict(X_scaled)[0])
    return SalaryOutput(
        predicted_salary=predicted_salary,
        estimated_annual_salary= predicted_salary * 14
    )
    
if __name__ == "__main__":
    uvicorn.run("salary_app:app", reload=True)
