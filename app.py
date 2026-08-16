from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from groq import Groq
import os

app = FastAPI()

# Groq 설정 (본인 API 키 입력)
client = Groq(api_key="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")

# 사용자별 학습 상태 및 설정 저장 (메모리 방식)
user_states = {} 

# 1. 실시간 음성 통화 웹페이지 (HTML을 코드 내에서 직접 반환하여 TemplateNotFound 에러 원천 차단)
@app.get("/", response_class=HTMLResponse)
async def voice_chat_page(request: Request):
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI 원어민 음성 통화</title>
        <style>
            body { background-color: #121212; color: #ffffff; font-family: sans-serif; text-align: center; padding-top: 50px; }
            h1 { color: #4CAF50; }
            .btn { background-color: #4CAF50; color: white; padding: 15px 30px; font-size: 18px; border: none; border-radius: 5px; cursor: pointer; margin-top: 20px; }
            .btn:hover { background-color: #45a049; }
        </style>
    </head>
    <body>
        <h1>📞 AI 원어민 음성 통화방</h1>
        <p>버튼을 누르고 마이크에 대고 말해보세요!</p>
        <button class="btn" onclick="alert('마이크 연결 준비 완료!')">🎤 말하기 시작</button>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 2. 카카오톡 챗봇 메시지 처리 (Step-by-Step 핵심 라우터)
@app.post('/api/kakao')
async def kakao_chat(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()

    if user_id not in user_states:
        user_states[user_id] = {"level": "초급", "lang": "베트남어", "step": "IDLE"}

    state = user_states[user_id]

    if "학습 시작" in utterance or "시작" in utterance:
        user_states[user_id]["step"] = "LEARNING"
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"📚 [Step 1. 오늘의 필수 표현 ({state['lang']} - {state['level']})]\n\n"
                                    f"• 한국어: \"회의를 내일로 연기해 주세요.\"\n"
                                    f"• 베트남어: \"Xin vui lòng hoãn cuộc họp sang ngày mai.\"\n\n"
                                    f"💡 팁: 'hoãn'은 '연기하다'라는 초급 필수 단어입니다!"
                        }
                    }
                ],
                "quickReplies": [
                    {"label": "✏️ 퀴즈 풀기", "action": "message", "messageText": "퀴즈 풀기"}
                ]
            }
        }

    if utterance == "퀴즈 풀기" and state["step"] == "LEARNING":
        user_states[user_id]["step"] = "QUIZ"
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "📝 [Step 2. 실력 확인 퀴즈]\n\n"
                                    "방금 배운 표현에서 '연기하다'에 해당하는 베트남어 단어는 무엇일까요?\n\n"
                                    "1️⃣ chào\n2️⃣ hoãn\n3️⃣ cảm ơn\n\n"
                                    "(정답 번호나 단어를 채팅창에 입력해 주세요!)"
                        }
                    }
                ]
            }
        }

    if state["step"] == "QUIZ":
        if "2" in utterance or "hoãn" in utterance.lower():
            user_states[user_id]["step"] = "VOICE_READY"
            web_chat_url = "https://kakao-vietnam-bot.onrender.com" 
            return {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                                "text": "🎉 정답입니다! 완벽해요 ('hoãn' = 연기하다).\n\n"
                                        "자, 이제 눈으로 배우셨으니 직접 입으로 소리 내어 말해볼 차례입니다!"
                            }
                        }
                    ],
                    "quickReplies": [
                        {"label": "📞 원어민 통화방 입장하기", "action": "webLink", "webLinkUrl": web_chat_url}
                    ]
                }
            }
        else:
            return kakao_text("앗, 틀렸습니다! 다시 한번 생각해보고 정답 번호(2번)나 단어를 입력해 주세요.")

    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {"simpleText": {"text": "반갑습니다! '오늘 학습 시작'이라고 입력하시거나 버튼을 눌러 학습을 시작해 보세요."}}
            ],
            "quickReplies": [
                {"label": "🚀 오늘 학습 시작", "action": "message", "messageText": "오늘 학습 시작"}
            ]
        }
    }

def kakao_text(text: str):
    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": text}}]}
    }
