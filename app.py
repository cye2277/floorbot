import os
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai

app = Flask(__name__)

# ======== 1. 環境變數設定 ========
# 請將這些值設定成你自己的金鑰
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

# ======== 2. 模擬地板產品資料 ========
floor_data = [
    {"model": "DF-1001", "color": "淺木色", "waterproof": True, "price": 850, "thickness": 12},
    {"model": "DF-1002", "color": "深木色", "waterproof": False, "price": 650, "thickness": 8},
    {"model": "DF-1003", "color": "灰色", "waterproof": True, "price": 990, "thickness": 10}
]

# ======== 3. Webhook 接收區 ========
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'

# ======== 4. 訊息處理區 ========
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text

    # 呼叫 OpenAI ChatGPT 來分析需求並推薦地板
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": (
                "你是地板推薦專家。根據用戶輸入的需求，例如預算、顏色、厚度、防水功能等，從下列地板資料中推薦最適合的 1～3 款。"
                f"\n地板資料：{floor_data}"
            )},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7
    )

    reply = response['choices'][0]['message']['content']
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run(port=5000)
