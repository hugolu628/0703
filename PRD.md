# 產品需求文件 (PRD): 0807 專案重構 — 模型訓練資料源遷移至 Render PostgreSQL

## 1. 專案概述 (Project Overview)
本 PRD 旨在指導 Sub-Agent (AI 代理/模型) 將 `backend/0807` 專案中的薪資預測模型訓練資料源，從原先的靜態 CSV 檔案 (`Salary_Data2.csv`) 徹底遷移至 Render 雲端 PostgreSQL 資料庫（資料表：`salary_data2`）。
重構後的系統需維持 FastAPI 的線上重訓 (`/train`) 與薪資預測 (`/predict`) 功能，並確保資料安全、連線穩定性與完整驗證。

---

## 2. 相關專案與連線參照 (References & Prerequisites)
- **連線與資安參考**：參考 `backend/08_13` 專案中的連線方式與 `.env` 管理規範。
- **環境變數設定**：`.env` 檔案已複製至 `backend/0807/.env`，內容如下：
  ```env
  POSTGRES_URL=postgresql://roberthsu2003:zHh6cGNiqdalZZ6IkCntCER93HDe4f1J@dpg-d9tuoarm8hqs73e404q0-a.singapore-postgres.render.com/tvdi_hebb?sslmode=require
  ```
- **版本控制防衛**：`backend/0807/.gitignore` 必須包含 `.env` 與 `.venv/`，避免敏感密碼外洩。

---

## 3. 資料庫 schema 與資料架構規範 (Database Schema)
使用 MCP Server `render_postgres` 查詢確認之資料表結構：
- **資料表名稱**：`salary_data2`
- **欄位規格**：
  | 欄位名稱 | 資料型態 | 說明與範例值 |
  | :--- | :--- | :--- |
  | `YearsExperience` | `real` (float) | 工作經驗年資 (例如: 3.5) |
  | `Salary` | `real` (float) | 薪資目標變數 (例如: 45.9) |
  | `EducationLevel` | `character varying` | 學歷 (例如: "高中以下", "大學", "碩士以上") |
  | `City` | `character varying` | 居住城市 (例如: "城市A", "城市B", "城市C") |

---

## 4. Sub-Agent 詳細執行步驟規劃 (Step-by-Step Execution Plan)

Sub-Agent 執行本重構任務時，**必須依序執行以下 5 個步驟**：

### 步驟 1: 環境與虛擬套件檢查 (Environment Setup)
1. 確保專案目錄為 `backend/0807`。
2. 檢查 `uv` 虛擬環境與必要套件。若缺少連線驅動，使用以下指令安裝：
   ```bash
   uv pip install psycopg2-binary python-dotenv sqlalchemy pandas joblib scikit-learn fastapi uvicorn
   ```
3. 確認 `.env` 檔案存在於 `backend/0807/` 目錄下。

---

### 步驟 2: 重構 `train_save.py` (資料源遷移至 Postgres)
修改 `train_save.py` 中的 `train_and_save_model()` 函式：

1. **移除 CSV 檔案依賴**：
   - 移除 `csv_path` 與 `os.path.exists(csv_path)` 檢查。
2. **實作 PostgreSQL 連線與讀取**：
   - 使用 `python-dotenv` 載入 `.env` 中的 `POSTGRES_URL`。
   - 使用 `psycopg2` 或 `sqlalchemy` 連接 Render PostgreSQL 資料庫。
   - 執行 SQL 查詢讀取資料表 `salary_data2` 並轉為 Pandas DataFrame：
     ```python
     import os
     import pandas as pd
     import psycopg2
     from dotenv import load_dotenv

     load_dotenv()
     postgres_url = os.getenv("POSTGRES_URL")
     if not postgres_url:
         raise ValueError("缺少 POSTGRES_URL 環境變數！")

     # 方式 A: psycopg2
     conn = psycopg2.connect(postgres_url)
     query = 'SELECT "YearsExperience", "Salary", "EducationLevel", "City" FROM salary_data2;'
     data = pd.read_sql(query, conn)
     conn.close()
     ```
3. **特徵工程與模型訓練邏輯（維持原樣）**：
   - `EducationLevel` 使用 `OrdinalEncoder` 處理（'高中以下' -> 0, '大學' -> 1, '碩士以上' -> 2）。
   - `City` 使用 `OneHotEncoder` 處理（'城市A', '城市B', '城市C'）。
   - 切分 `X_train`, `X_test`, `y_train`, `y_test` 並使用 `StandardScaler` 標準化。
   - 支援 `LinearRegression`, `Lasso`, `Ridge` 模型的擬合與訓練。
4. **模型序列化**：
   - 將訓練好的模型與預處理器儲存至 `salary_model.joblib`。

---

### 步驟 3: 檢查與調整 `app.py` (FastAPI 線上重訓與預測)
1. 確保 `app.py` 載入 `.env` 環境變數。
2. 檢查 `/train` 端點呼叫 `train_and_save_model()` 時，能正確連接 Postgres 拉取最新資料集重新訓練模型。
3. 檢查 `/predict` 端點，確保特徵編碼與預測介面輸入輸出格式正確無誤。

---

### 步驟 4: 產出獨立驗證腳本 `verify_pipeline.py`
為了提供自動化驗證，必須建立 `backend/0807/verify_pipeline.py`，內容需涵蓋：
1. **資料庫連線測試**：驗證能否順利連線 Render PostgreSQL 並讀取 `salary_data2` 資料列筆數。
2. **模型訓練測試**：呼叫 `train_and_save_model()` 驗證能否產出 `salary_model.joblib` 並取得評估指標 $R^2$。
3. **模型預測測試**：載入生成的 joblib 模型，傳入測試資料範例，驗證預測薪資輸出是否合理。

---

### 步驟 5: 全面測試與驗證 (Validation Checklist)

Sub-Agent **必須執行並通過以下驗證程序**始可宣告完成：

- [x] **驗證 1 (連線與重訓測試)**：
  在終端機執行 `python train_save.py`，輸出應顯示成功連接 Render Postgres 並產出 `salary_model.joblib`。
- [x] **驗證 2 (單元驗證腳本測試)**：
  在終端機執行 `python verify_pipeline.py`，斷言 (assert) 資料列筆數 > 0，且 $R^2 > 0.5$。
- [x] **驗證 3 (FastAPI API 端點測試)**：
  - 測試 POST `/train` 端點，傳入 `{ "test_size": 0.2, "random_state": 42, "model_type": "LinearRegression", "alpha": 1.0 }`，確認回傳 `status: success`。
  - 測試 POST `/predict` 端點，傳入 `{ "years_experience": 3.5, "education_level": "大學", "city": "城市A" }`，確認回傳合理之 `predicted_salary`。

---

## 5. Sub-Agent 產出要求與品質驗收
- **程式碼無硬編碼**：不得將 PostgreSQL 密碼寫死在任何 `.py` 檔案中。
- **錯誤處理**：資料庫連線失敗時應回傳明確之提示訊息。
- **成果回報**：Sub-Agent 完成後需輸出詳細測試日誌與驗證結果報告。

---

## 6. Code Review 審查報告與優化建議 (Code Review Report)

### 審查狀態：✅ 通過 (PASSED)
**審查日期**：2026-08-13
**審查對象**：`train_save.py`, `app.py`, `verify_pipeline.py`, `.env`, `.gitignore`

#### 🔍 審查細項與結果表：
| 審查項目 | 審查指標 | 結果 | 說明 |
| :--- | :--- | :--- | :--- |
| **資安與環境變數** | 無硬編碼密碼，`.env` 不納入 Git 追蹤 | **PASS ✅** | `.env` 成功讀取且已被 `.gitignore` 正確忽略。 |
| **資料庫連線與遷移** | 成功從 Render PostgreSQL `salary_data2` 讀取資料 | **PASS ✅** | 已廢除 CSV 依賴，`train_save.py` 成功拉取 36 筆數據。 |
| **模型訓練與序列化** | 訓練邏輯、特徵編碼與 `joblib` 匯出正常 | **PASS ✅** | 成功產出 `salary_model.joblib`，訓練指標 $R^2 = 0.7278$。 |
| **驗證腳本執行** | `verify_pipeline.py` 能否自動化跑通全流程 | **PASS ✅** | 執行 `uv run python verify_pipeline.py` 指令回傳 Exit Code 0，無任何斷言失敗。 |

#### 📊 自動化驗證實測結果記錄：
- **資料庫記錄筆數**：36 筆 (`salary_data2`)
- **多元線性迴歸模型評估**：$R^2 = 0.7278$ (高於門檻 0.5)
- **測試推論範例**：輸入（年資: 3.5年, 學歷: 大學, 城市: 城市A）➔ 預測月薪: **45.12 萬**

#### 💡 後續優化建議 (Optimization Suggestions)：
1. **消除 Pandas DBAPI 警告 (Recommended)**：
   目前 `pd.read_sql` 傳入 `psycopg2` 連線會觸發 UserWarning。建議未來升級為 SQLAlchemy 引擎：
   ```python
   from sqlalchemy import create_engine
   engine = create_engine(postgres_url)
   data = pd.read_sql('SELECT "YearsExperience", "Salary", "EducationLevel", "City" FROM salary_data2;', engine)
   ```
2. **連線資源控制優化**：
   在 `train_save.py` 中使用 `with psycopg2.connect(...) as conn:` 結構，可確保例外發生時能自動釋放連線資源。

---

## 7. Render 雲端部署配置說明 (Render Deployment Specifications)

為了順利將 `backend/0807` 部署至 Render Web Service 平台，已完成以下佈署準備：

1. **依賴套件檔**：已建立 [`requirements.txt`](file:///Users/roberthsu2003/Documents/GitHub/2026_07_03_python_ai_tvdi/backend/0807/requirements.txt)。
2. **Render Web Service 建議設定**：
   - **Build Command**：`pip install -r requirements.txt`
   - **Start Command**：`uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables (環境變數設定)**：
     在 Render 控制台的 Environment 設定中新增 `POSTGRES_URL`，填入 Render PostgreSQL 的內部 (Internal) 或外部 (External) Database URL。
