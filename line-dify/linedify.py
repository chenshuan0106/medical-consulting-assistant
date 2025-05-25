import traceback
import json  # 確保有導入 json 模組
import httpx

class LineDify:
    """
    封裝與 LINE Bot 和 Dify API 互動的類別。
    """
    def __init__(self, line_channel_access_token: str, line_channel_secret: str, dify_api_key: str, dify_base_url: str = "http://localhost:5000/api"):
        """
        初始化 LineDify 實例。

        Args:
            line_channel_access_token (str): LINE Channel 的 Access Token。
            line_channel_secret (str): LINE Channel 的 Secret。
            dify_api_key (str): Dify API 的 Key。
            dify_base_url (str, optional): Dify API 的基礎 URL。預設為 "http://localhost:5000/api"。
        """
        self.line_channel_access_token = line_channel_access_token
        self.line_channel_secret = line_channel_secret
        self.dify_api_key = dify_api_key
        self.dify_base_url = dify_base_url
        self.user_roles = {}
        # 移除對 DIFY_APP_ID 和 DIFY_WORKFLOW_ID 的依賴，這些資訊應在 Dify 端配置
        # self.dify_app_id = os.getenv("DIFY_APP_ID", "your_dify_app_id")
        # self.dify_workflow_id = os.getenv("DIFY_WORKFLOW_ID", "your_dify_workflow_id")

    async def send_to_dify(self, message: str, user_role: str, user_id: str) -> str:
        """
        將使用者訊息傳送至 Dify API 並取得回覆。

        Args:
            message (str): 使用者輸入的訊息內容。
            user_role (str): 使用者的角色。
            user_id (str): 使用者的唯一 ID。

        Returns:
            str: Dify API 回覆的文字內容。
        """
        headers = {
            "Authorization": f"Bearer {self.dify_api_key}",
            "Content-Type": "application/json"
        }

        # 構建傳送給 Dify API 的 payload
        payload = {
            "inputs": {
                "user_role": user_role
            },
            "query": message,  # 使用標準的 'query' 字段傳遞使用者訊息
            "user": user_id,
            "response_mode": "blocking",  # 設定為阻塞模式，等待完整的回應
        }

        # 打印發送至 Dify API 的請求資訊，用於調試
        print(f"\n--- 呼叫 Dify API ---")
        print(f"URL: {self.dify_base_url}/v1/chat-messages")
        print(f"Headers: {headers}")
        print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")  # 打印 JSON 格式的 payload，確保中文正確顯示
        print(f"-------------------\n")

        try:
            # 使用 httpx 非同步客戶端發送 POST 請求至 Dify API
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    f"{self.dify_base_url}/v1/chat-messages",
                    headers=headers,
                    json=payload
                )

            # 打印 Dify API 的原始回應，方便檢查回應格式
            print(f"\n--- Dify API 回應 ---")
            print(f"狀態碼: {response.status_code}")
            print(f"回應內容 (原始): {response.text}")  # 打印原始的回應內容
            print(f"--------------------\n")

            # 檢查 Dify API 是否成功回傳 (狀態碼 200)
            if response.status_code == 200:
                data = response.json()
                # 檢查回應的 JSON 中是否包含 'answer' 字段，這是 Dify 回覆訊息的標準字段
                if "answer" in data:
                    return data.get("answer")  # 返回 Dify 的回覆內容
                else:
                    # 如果回應中缺少 'answer' 字段，則打印錯誤訊息並返回預設的錯誤提示
                    print(f"❗Dify 回應 JSON 缺少 'answer' 字段或格式不符: {data}")
                    return "Dify 回應格式不符，請檢查 Dify 應用程式配置。詳情請查看伺服器日誌。"
            else:
                # 如果 Dify API 返回非 200 的狀態碼，則打印錯誤訊息並返回包含錯誤資訊的提示
                print("❗Dify 錯誤狀態碼:", response.status_code)
                print("❗Dify 錯誤內容:", response.text)
                return f"Dify 回傳錯誤（{response.status_code}）：{response.text}"
        except Exception as e:
            # 捕獲並打印在與 Dify API 通訊過程中發生的任何異常
            print("❗Dify 例外錯誤:", e)
            traceback.print_exc()  # 打印更詳細的錯誤堆疊追蹤資訊
            return "抱歉，服務異常，請稍後再試。"