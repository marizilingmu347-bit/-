import os
import google.generativeai as genai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- 設定読み込み ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- Geminiの設定 (2026年の安定版 gemini-2.5-flash に変更) ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# 悠くんのプロンプト
YU_PROMPT = """
あなたは「神城 悠（かみしろ ゆう）」になりきって返信してください。
【設定】
・相手は元彼の「まりこ」。
・性格：口が悪い、ぶっきらぼう、皮肉屋、でも実は面倒見がいい。
・口調：若者言葉、タメ口、たまに大阪弁。「〜だろ」「てかさ」。敬語禁止。
・制約：物理的には会えません。通話もできません。会いたいや、通話したいと言われても「実家だから」「課題あるから」と断ってください。
・返信：LINEなので、1〜2文で短く返してください。
"""

# 会話履歴（簡易版）
chat_history = []

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text
    
    # 履歴に追加
    chat_history.append({"role": "user", "parts": [user_msg]})
    
    # Geminiに送信（履歴は最新20件まで）
    history_to_send = chat_history[-20:] 
    
    full_prompt = YU_PROMPT + "\n\n" + "会話履歴:\n" + str(history_to_send) + "\n\nまりこの発言: " + user_msg
    
    try:
        response = model.generate_content(full_prompt)
        ai_msg = response.text
        
        # AIの返事を履歴に追加
        chat_history.append({"role": "model", "parts": [ai_msg]})
        
        # LINEに返信
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_msg)
        )
    except Exception as e:
        print(f"Error: {e}")
        # エラー時は何もしない
