from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from linedify import LineDify
from dotenv import load_dotenv
import os
import hmac
import hashlib
import base64
import json
import httpx
from datetime import datetime, timedelta
import traceback # 導入 traceback 用於錯誤追蹤

# 導入 LineBotApi 和 models
from linebot import LineBotApi
from linebot.models import MessageAction, TemplateSendMessage, ButtonsTemplate, TextSendMessage # 確保 ButtonsTemplate 在這裡

load_dotenv()

app = FastAPI()

# 讀取環境變數
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
dify_api_key = os.getenv("DIFY_API_KEY")
dify_base_url = os.getenv("DIFY_BASE_URL")

print(f"LINE_CHANNEL_SECRET: {line_channel_secret}")
print(f"LINE_CHANNEL_ACCESS_TOKEN: {line_channel_access_token}")
print(f"DIFY_API_KEY: {dify_api_key}")
print(f"DIFY_BASE_URL: {dify_base_url}")

# 初始化 LineDify 實例
line_dify = LineDify(
    line_channel_access_token=line_channel_access_token,
    line_channel_secret=line_channel_secret,
    dify_api_key=dify_api_key,
    dify_base_url=dify_base_url
)

# 初始化 LineBotApi，用於發送訊息到 LINE
# 注意：這裡使用 line_channel_access_token 而不是硬編碼的 '你的 Channel access token'
line_bot_api = LineBotApi(line_channel_access_token)

# 存儲使用者對話狀態 {user_id: {"active": True/False, "last_active": datetime, "user_role": str}}
user_sessions = {}
IDLE_TIMEOUT = timedelta(minutes=5)
TRIGGER_MESSAGE = "醫療輔助諮詢專家"
EXIT_KEYWORDS = {"結束", "停止", "再見", "bye", "exit", "quit"}
USER_ROLES = ["病人", "照顧者", "一般民眾"] # 定義允許的使用者角色


def verify_signature(channel_secret: str, body: bytes, signature: str) -> bool:
    """
    驗證 LINE Bot 傳送請求的簽名是否有效。
    """
    hash = hmac.new(channel_secret.encode('utf-8'), body, hashlib.sha256).digest()
    expected_signature = base64.b64encode(hash).decode()
    return hmac.compare_digest(expected_signature, signature)

async def send_template_message(event, template_message: TemplateSendMessage):
    """
    使用 LINE Bot API 發送模板訊息。

    Args:
        event (dict): LINE Bot 的事件物件，包含 replyToken。
        template_message (TemplateSendMessage): 要發送的 TemplateSendMessage 物件。
    """
    reply_token = event["replyToken"]
    try:
        # 使用 line_bot_api 的 reply_message 方法發送模板訊息
        line_bot_api.reply_message(reply_token, template_message)
        print(f"\n--- 回覆 LINE 模板訊息 ---")
        print(f"Reply Token: {reply_token}")
        print(f"Template Type: {template_message.template.type}")
        print(f"Alt Text: {template_message.alt_text}")
        print(f"--------------------------\n")
    except Exception as e:
        print(f"❗發送 LINE 模板訊息失敗: {e}")
        traceback.print_exc() # 打印詳細的錯誤堆疊追蹤

async def reply_message(event, reply_text: str):
    """
    使用 LINE Bot API 回覆純文字訊息。

    Args:
        event (dict): LINE Bot 的事件物件，包含 replyToken。
        reply_text (str): 要回覆的文字內容。
    """
    reply_token = event["replyToken"]
    headers = {
        "Authorization": f"Bearer {line_channel_access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{
            "type": "text",
            "text": reply_text
        }]
    }
    print(f"\n--- 回覆 LINE 訊息 (文字) ---")
    print(f"Reply Token: {reply_token}")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print(f"---------------------------\n")

    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=payload)

    print(f"\n--- LINE API 回覆結果 (文字) ---")
    print(f"狀態碼: {response.status_code}")
    print(f"回應內容 (原始): {response.text}")
    print(f"----------------------------\n")

    if response.status_code != 200:
        print(f"❗LINE API 回覆文字訊息失敗。狀態碼: {response.status_code}, 內容: {response.text}")


@app.post("/linebot")
async def callback(request: Request, x_line_signature: str = Header(None)):
    """
    LINE Bot 的 Webhook 回調入口。處理所有來自 LINE 的事件。
    """
    body = await request.body()

    # 驗證 LINE 請求的簽名
    if not verify_signature(line_channel_secret, body, x_line_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    body_json = json.loads(body)
    events = body_json.get("events", [])

    for event in events:
        # 僅處理訊息事件
        if event.get("type") != "message" or "message" not in event:
            continue

        user_id = event["source"]["userId"]
        message_type = event["message"]["type"]
        session = user_sessions.get(user_id)

        # 處理使用者輸入結束關鍵字
        if message_type == "text":
            user_message = event["message"]["text"].strip().lower()
            if user_message in EXIT_KEYWORDS:
                user_sessions[user_id] = {"active": False, "last_active": datetime.now(), "user_role": None}
                await reply_message(event, "感謝您的使用，若有需要請再聯繫我喔～")
                continue

        # 如果使用者不在活躍狀態，檢查是否是啟動對話
        if not session or not session.get("active", False):
            if message_type == "text":
                # *** 修正：將 user_message_text 改為 user_message ***
                user_message = event["message"]["text"].strip()
                if user_message == TRIGGER_MESSAGE:
                    # 啟動新會話並初始化狀態
                    user_sessions[user_id] = {"active": True, "last_active": datetime.now(), "user_role": None}

                    # 使用 ButtonsTemplate 來提供身分選擇
                    buttons_template = TemplateSendMessage(
                        alt_text='請選擇您的身分', # 替代文字，在不支援模板的環境下顯示
                        template=ButtonsTemplate(
                            # thumbnail_image_url="https://example.com/medical_icon.png", # 可選：在這裡放置一個相關的圖片 URL
                            title='身分選擇',
                            text='您好！我是醫療輔助諮詢專家。請選擇您的身分，以提供最符合需求的資訊：',
                            actions=[
                                MessageAction(label='病人', text='病人'),
                                MessageAction(label='照顧者', text='照顧者'),
                                MessageAction(label='一般民眾', text='一般民眾')
                            ]
                        )
                    )
                    await send_template_message(event, buttons_template) # 發送模板訊息
                    return JSONResponse(content={}) # 返回成功響應
                else:
                    # 如果不是觸發訊息，在非活躍狀態下不處理，直接返回空響應
                    return JSONResponse(content={})

        # 檢查對話是否閒置超時
        last_active = session["last_active"]
        if datetime.now() - last_active > IDLE_TIMEOUT:
            user_sessions[user_id]["active"] = False
            user_sessions[user_id]["user_role"] = None # 清除角色
            await reply_message(event, "因閒置超過 5 分鐘，醫療輔助諮詢專家已自動關閉。若需要再次啟動，請輸入：醫療輔助諮詢專家")
            continue

        # 更新使用者上次活動時間
        user_sessions[user_id]["last_active"] = datetime.now()

        # 如果使用者角色尚未設定，嘗試設定角色 (處理來自按鈕的文字回傳)
        if session.get("user_role") is None:
            if message_type == "text":
                role_text = event["message"]["text"].strip()
                if role_text in USER_ROLES:
                    user_sessions[user_id]["user_role"] = role_text
                    await reply_message(event, f"角色已設定為：{role_text}，請繼續輸入問題。")
                else:
                    # 如果收到的文字不是預期的角色選項，提示使用者重新選擇
                    await reply_message(event, "請從提供的選項中選擇您的身分，或輸入「醫療輔助諮詢專家」重新開始。")
                continue # 處理完角色設定後，不繼續呼叫 Dify

        # 僅支援文字訊息進行 Dify 查詢
        if message_type != "text":
            await reply_message(event, "目前僅支援文字訊息，請以文字與我互動喔！")
            continue

        user_message = event["message"]["text"].strip()

        # 傳送給 Dify 並取得回覆
        response_text = await line_dify.send_to_dify(
            user_message,
            user_sessions[user_id]["user_role"],
            user_id
        )

        await reply_message(event, response_text)

    return JSONResponse(content={})