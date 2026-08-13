產品需求文件 (PRD): Python 連結 Render PostgreSQL 教學文件製作指南
1. 專案概述 (Project Overview)
本 PRD 旨在指導 LLM (AI 模型) 撰寫一份專為學生與程式初學者設計的教學文件：python連結postgres.md。 該教學文件將引導學生學習如何使用 Python 連結位於 Render 雲端平台上的 PostgreSQL 資料庫，並著重於利用環境變數 (.env) 保護敏感資訊（如資料庫密碼與連線字串）。

2. 目標與產出規範 (Goals & Deliverables)
最終產出檔名：python連結postgres.md
目標對象：Python 初學者 / 學生（具備基礎 Python 語法概念，但初次接觸雲端資料庫與環境變數管理）。
教學目標：
理解雲端 PostgreSQL (Render) 的連線資訊取得方式。
學會在 Python 專案中使用 .env 與 python-dotenv 模組保護敏感數據。
掌握使用 uv 建立虛擬環境與安裝 Python 相關套件（如 psycopg2-binary 與 python-dotenv）。
寫出安全性高、具備錯誤處理機制（try-except）的 Python 資料庫連線測試程式碼。
3. 目標產出文件結構與詳細規格要求 (python連結postgres.md)
模型在生成 python連結postgres.md 時，必須嚴格遵守以下章節結構與內容細節：

章節 1: 前言與觀念建立
概念說明：
為何不能將密碼硬編碼 (Hardcode) 在程式碼中？（說明程式碼上傳至 GitHub 等公開平台的安全風險）。
何謂環境變數 (Environment Variables) 與 .env 檔案的作用。
章節 2: 步驟一 — 取得 Render PostgreSQL 連線資訊
操作指引：
登入 Render 控制台 (Dashboard)。
進入已建立的 PostgreSQL 資料庫頁面。
找到 Connections 區塊，複製 External Database URL (外部連線 URL) 或獨立連線參數 (Host, Database, User, Password, Port)。
提醒學生：Render 的 External URL 格式通常為： postgresql://<user>:<password>@<host>/<database>
章節 3: 步驟二 — 建立 Python 專案與環境（使用 uv）
環境設定與套件安裝指令：
說明本專案採用 uv 作為 Python 虛擬環境管理工具。
步驟說明與終端機 (Terminal) 指令：
初始化/建立虛擬環境：
uv venv
啟動虛擬環境 (Mac / Linux 與 Windows 指令分開標示)：
Mac/Linux: source .venv/bin/activate
Windows: .venv\Scripts\activate
安裝所需套件 (psycopg2-binary 與 python-dotenv)：
uv pip install psycopg2-binary python-dotenv
章節 4: 步驟三 — 設定 .env 檔案與 .gitignore
安全防護設定：
建立 .env 檔案： 在專案根目錄下建立 .env 檔案，內容格式範例：
POSTGRES_URL=postgresql://your_user:your_password@your_host.render.com/your_db_name
建立 .gitignore 檔案（重要提醒）： 教導學生在專案根目錄建立 .gitignore，將 .env 與 .venv/ 加入忽略清單，確保連線資安：
.env
.venv/
__pycache__/
建立 .env.example 檔案（最佳實踐）： 說明為何要建立範例檔（讓其他人知道需要設定哪些環境變數名稱，但不包含真實密碼）：
POSTGRES_URL=postgresql://username:password@hostname/dbname
章節 5: 步驟四 — 撰寫 Python 連線測試程式碼
提供完整且註解詳細的 Python 程式碼範例 (例如 test_connection.py 或直接嵌入 md)：
使用 dotenv 載入 .env 變數。
使用 os.getenv() 讀取設定值。
使用 psycopg2.connect() 進行資料庫連線。
包含 try...except...finally 結構以確保連線異常時能優雅處理，且連線完畢會自動關閉 (close)。
程式碼樣板規格：
import os
import psycopg2
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# 取得連線字串
POSTGRES_URL = os.getenv("POSTGRES_URL")

if not POSTGRES_URL:
    print("錯誤：找不到 POSTGRES_URL 環境變數，請檢查 .env 檔案。")
    exit(1)

try:
    # 建立資料庫連線
    print("正在連線至 Render PostgreSQL...")
    conn = psycopg2.connect(POSTGRES_URL)
    
    # 建立遊標 (Cursor)
    cursor = conn.cursor()
    
    # 執行簡單查詢測試 (取得 PostgreSQL 版本)
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print("連線成功！PostgreSQL 版本資訊：")
    print(db_version[0])

    # 關閉遊標與連線
    cursor.close()
    conn.close()
    print("連線已安全關閉。")

except Exception as error:
    print(f"連線失敗，錯誤訊息：{error}")
章節 6: 常見問題與除錯指南 (Troubleshooting)
針對學生常見的痛點提供處置建議：

SSL / 連線被拒絕問題：Render 要求 SSL 連線，若出現 SSL 錯誤，可在 URL 後加上 ?sslmode=require 或在 psycopg2 參數中設定。
找不到 .env 檔案：確認 main.py 與 .env 是否在同一個根目錄，或執行目錄是否正確。
ModuleNotFoundError：提醒學生確認是否已啟用 uv 虛擬環境。
4. 撰寫風格與語氣指引 (Tone & Style Requirements)
語氣：親切、耐性、淺顯易懂，適合學生學習。
格式：
使用清晰的 Markdown 標題階層 (H1, H2, H3)。
終端機指令區塊需明確標註語法高亮 (bash)。
Python 程式碼區塊需具備豐富繁體中文註解。
重要安全警告事項需使用醒目的格式（如提示框或粗體高亮）。
語言：全繁體中文 (Traditional Chinese)。
5. 給後續模型執行的 Prompt 指示詞 (System Prompt for Target Model)
未來欲生成 python連結postgres.md 的 AI 模型，請閱讀本 PRD.md 後，嚴格依照「3. 目標產出文件結構與詳細規格要求」與「4. 撰寫風格與語氣指引」，生成完整、無缺漏且教學品質優良的 python連結postgres.md 教學文件。