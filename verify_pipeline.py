"""
驗證腳本 verify_pipeline.py
依據 PRD 步驟 4 要求，驗證資料庫連線、模型訓練與預測流程
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
POSTGRES_URL = os.getenv("POSTGRES_URL")
if not POSTGRES_URL:
    raise ValueError("缺少 POSTGRES_URL 環境變數！")

import psycopg2
import pandas as pd
import joblib
from salary_train_save import train_and_save_model

def test_db_connection():
    print("=== 資料庫連線測試 ===")
    conn = psycopg2.connect(POSTGRES_URL)
    query = 'SELECT COUNT(*) AS cnt FROM salary_data2;'
    df = pd.read_sql(query, conn)
    conn.close()
    count = int(df['cnt'][0])
    print(f"salary_data2 資料列筆數: {count}")
    assert count > 0, "資料表筆數必須大於 0"
    print("資料庫連線測試通過\n")
    return count

def test_training():
    print("=== 模型訓練測試 ===")
    result = train_and_save_model(
        test_size=0.2,
        random_state=42,
        model_type="LinearRegression",
        alpha=1.0
    )
    print(f"訓練結果: {result}")
    assert result["status"] == "success", "訓練失敗"
    r2 = result["r2"]
    print(f"R² = {r2:.4f}")
    assert r2 > 0.5, f"R² 必須大於 0.5，實際值: {r2}"
    
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salary_model.joblib")
    assert os.path.exists(model_path), "模型檔案未產生"
    print("模型訓練測試通過\n")
    return r2

def test_prediction():
    print("=== 模型預測測試 ===")
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salary_model.joblib")
    model_data = joblib.load(model_path)
    
    # 載入預處理器
    from sklearn.preprocessing import OrdinalEncoder, OneHotEncoder
    import numpy as np
    
    oe = model_data["oe"]
    ohe = model_data["ohe"]
    scaler = model_data["scaler"]
    model = model_data["model"]
    
    # 測試樣本
    years_experience = 3.5
    education_level = "大學"
    city = "城市A"
    
    edu_encoded = int(oe.transform(pd.DataFrame([[education_level]], columns=["EducationLevel"]))[0][0])
    city_vector = ohe.transform(pd.DataFrame([[city]], columns=["City"]))
    feature_row = [years_experience, edu_encoded] + list(city_vector[0])
    feature_names = model_data["feature_names"]
    X = pd.DataFrame([feature_row], columns=feature_names)
    X_scaled = scaler.transform(X)
    pred = float(model.predict(X_scaled)[0])
    
    print(f"輸入: years_experience={years_experience}, education_level={education_level}, city={city}")
    print(f"預測薪資: {pred:.2f}")
    assert pred > 0, "預測薪資必須大於 0"
    print("模型預測測試通過\n")

if __name__ == "__main__":
    try:
        cnt = test_db_connection()
        r2 = test_training()
        test_prediction()
        print("✅ 所有驗證通過！")
        print(f"資料列數: {cnt}, R²: {r2:.4f}")
    except AssertionError as e:
        print(f"❌ 驗證失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
        sys.exit(1)