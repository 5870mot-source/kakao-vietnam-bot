from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from groq import Groq
import os

app = FastAPI()

# Groq 설정 (본인 API 키 입력)
client = Groq(api_key="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")
templates = Jinja2Templates(directory="templates")

# 사용자별 학습 상태 및 설정 저장 (메모리 방식)
user_states = {} 
# 예: { "user_id_123": {"level": "초급", "lang": "베트남어", "step": "QUIZ"} }

# 1. 실시간 음성 통화 웹페이지 (마지막 단계)
@app.get("/", response_class=HTMLResponse)
async def voice_chat_page(request: Request):
    return templates.TemplateResponse(request, "index.html", {})

# 2. 카카오톡 챗봇 메시지 처리 (Step-by-Step 핵심 라우터)
@app.post('/api/kakao')
async def kakao_chat(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()

    # 사용자의 기본 상태 초기화
    if user_id not in user_states:
        user_states[user_id] = {"level": "초급", "lang": "베트남어", "step": "IDLE"}

    state = user_states[user_id]

    # [명령어] 설정 변경
    if utterance.startswith("설정:"):
        parts = utterance.replace("설정:", "").split(",")
        if len(parts) >= 2:
            state["lang"] = parts[0].strip()
            state["level"] = parts[1].strip()
            return kakao_text(f"설정 완료! [{state['lang']} / {state['level']}급]으로 학습이 세팅되었습니다.")

    # [Step 0] 학습 시작 트리거 ("오늘 학습 시작" 또는 알람 버튼 클릭 시)
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

    # [Step 1 ➔ Step 2] 퀴즈 풀기로 진입
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

    # [Step 2 ➔ Step 3] 퀴즈 정답 판정
    if state["step"] == "QUIZ":
        if "2" in utterance or "hoãn" in utterance.lower():
            user_states[user_id]["step"] = "VOICE_READY"
            # 렌더 서버 배포 주소로 변경 필요
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

    # 기본 안내
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

# 3. 크론잡이 아침에 찔러줄 푸시 알림 수신부 (추후 카카오 알림톡 API 연동 포인트)
@app.get('/api/cron/push')
async def trigger_push():
    # TODO: 추후 이곳에 카카오 비즈니스 메시지 API를 넣어 사용자들에게 아침 알림 발송
    return {"status": "아침 6시 푸시 알림 트리거 완료"}
