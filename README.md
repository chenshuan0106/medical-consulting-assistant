# medical-consulting-assistant
# 醫療輔助諮詢專家系統

本專題整合 LINE Bot 與 Dify 語言模型，建構醫療衛教輔助諮詢平台，協助使用者根據身分取得即時醫療知識。

## 🔧 系統功能

- ✅ 支援 LINE 文字與語音輸入
- ✅ 使用者角色辨識與對話觸發控制
- ✅ 整合 Dify + RAG 技術從知識庫檢索資料
- ✅ 支援 Docker 快速部署

## 📁 專案結構

| 檔案 / 資料夾       | 說明                                   |
|---------------------|----------------------------------------|
| `dify-flow.yml`     | Dify 流程設定檔（原名：醫療輔助諮詢專家.yml）|
| `line-dify/app.py`  | FastAPI 主應用，處理 LINE webhook     |
| `line-dify/linedify.py` | 處理使用者訊息與角色識別            |
| `line-dify/Dockerfile`  | 容器化部署設定                        |
| `line-dify/requirements.txt` | Python 相依套件列表           |

## 🚀 快速部署指令（Docker）

```bash
cd line-dify
docker build -t medical-assistant .
docker run -p 8000:8000 medical-assistant

