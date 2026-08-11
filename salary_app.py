import os 
import sys 
from train_save import train_and_save_model 
from pydantic import BaseModel, Field 
from pprint import pprint 
import joblib 
from fastapi import FastAPI, HTTPException 
import uvicorn 
import pandas as pd 
import numpy as np 

# 確保當前目錄在 sys.path 中，以便正確匯入自訂模組
current_dir = os.getcwd() 
if current_dir not in sys.path: 
    sys.path.insert(0, current_dir) 

model_path = os.path.join(current_dir, "salary_model.joblib") 
MODEL_STATE = {} 

# 訓練設定的 Pydantic 模型
class TrainConfig(BaseModel): 
    test_size: float = Field(0.2, description="測試集分割比例", ge=0.1, le=0.5) 
    random_state: int = Field(76, description="隨機種子", ge=0) 
    model_type: str = Field("LinearRegression", description="模型演算法類型 (LinearRegression, Lasso, Ridge)") 
    alpha: float = Field(1.0, description="正則化強度 alpha (適用於 Lasso 與 Ridge)", ge=0.001, le=100.0) 

# 訓練結果的 Pydantic 模型
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

# 修正後的薪資預測輸入 Pydantic 模型
class SalaryInput(BaseModel): 
    years_experience: float = Field(..., description="工作年資（年）", ge=0.0)
    education_level: str = Field(..., description="學歷程度（例如：高中以下、大學、碩士等）")
    city: str = Field(..., description="工作城市（例如：城市A、城市B等）")

    # 提供 Swagger UI 預覽用的範例資料
    model_config = {
        "json_schema_extra": {
            "example": {
                "years_experience": 5.3,
                "education_level": "高中以下",
                "city": "城市A"
            }
        }
    }

# 預測輸出的 Pydantic 模型
class SalaryOutput(BaseModel): 
    predicted_salary: float 
    estimated_annual_salary: float 

# 載入並更新全域模型狀態
def load_model_state(): 
    global MODEL_STATE 
    if not os.path.exists(model_path): 
        train_and_save_model() 
    model_data = joblib.load(model_path) 
    
    # 修正：不使用 clear()，改用原子操作（Atomic Assignment）替換指標，確保執行緒安全
    new_state = { 
        "model": model_data["model"], 
        "oe": model_data["oe"], 
        "ohe": model_data["ohe"], 
        "scaler": model_data["scaler"], 
        "r2": model_data.get("r2"), 
        "feature_names": model_data["feature_names"], 
        "feature_coefs": model_data.get("feature_coefs", {}), 
        "model_type": model_data.get("model_type"), 
        "alpha": model_data.get("alpha") 
    } 
    MODEL_STATE = new_state

# 初始化時先載入一次模型
load_model_state() 

app = FastAPI(title="薪資預測與線上訓練 API") 

@app.post("/train", response_model=TrainResult) 
def train_endpoint(config: TrainConfig): 
    """ 
    訓練端點：傳入測試集比例、隨機種子、模型類型與 alpha，線上重新訓練模型，並即時更新服務所使用的模型。 
    """ 
    try: 
        # 1. 執行重新訓練並儲存模型 
        res = train_and_save_model( 
            test_size=config.test_size, 
            random_state=config.random_state, 
            model_type=config.model_type, 
            alpha=config.alpha 
        ) 
        # 2. 線上重新載入最新模型狀態至全域變數 
        load_model_state() 
    except Exception as e: 
        raise HTTPException(status_code=500, detail=f"線上訓練失敗: {str(e)}") 
    return res 

@app.post("/predict", response_model=SalaryOutput) 
def predict_endpoint(payload: SalaryInput): 
    """
    預測端點：接收特徵並使用目前全域的模型狀態進行推論。
    """
    try:
        # 從目前的全域狀態快照中提取物件
        current_state = MODEL_STATE
        oe = current_state["oe"] 
        ohe = current_state["ohe"] 
        scaler = current_state["scaler"] 
        model = current_state["model"] 
        
        # 提醒：請確保這裡的欄位名稱 "EducationLevel" 與 "City" 與您訓練模型時的 DataFrame 欄位完全一致
        edu_encoded = int(oe.transform(pd.DataFrame([[payload.education_level]], columns=["EducationLevel"]))[0][0]) 
        city_vector = ohe.transform(pd.DataFrame([[payload.city]], columns=["City"])) 
        city_cols = ohe.get_feature_names_out(['City']) 
        
        # 拼接特徵向量
        feature_row = [payload.years_experience, edu_encoded] + list(city_vector[0]) 
        features = pd.DataFrame([feature_row], columns=["YearsExperience", "EducationLevel"] + list(city_cols)) 
        
        # 標準化與預測
        X_scaled = scaler.transform(features) 
        predicted_salary = float(model.predict(X_scaled)[0]) 
        
        return SalaryOutput( 
            predicted_salary=predicted_salary, 
            estimated_annual_salary=predicted_salary * 14 
        ) 
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"預測失敗，請檢查輸入特徵是否在訓練集中存在: {str(e)}")

if __name__ == "__main__": 
    port = int(os.environ.get("PORT", 8000))
    # 修正：動態取得目前檔案名稱（去除 .py字尾），避免檔名不對稱導致 Uvicorn 啟動失敗
    module_name = os.path.splitext(os.path.basename(__file__))[0]
    uvicorn.run(f"{module_name}:app", host="0.0.0.0", port=port, reload=True)