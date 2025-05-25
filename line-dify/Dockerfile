FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 安裝套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製 FastAPI 原始碼
COPY . .

# 啟動 FastAPI 應用（監聽所有介面）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
