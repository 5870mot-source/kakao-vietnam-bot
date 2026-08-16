from fastapi import FastAPI, Request
from groq import Groq
import os

app = FastAPI()

# Groq 클라이언트 설정 (본인의 API 키를 여기에 넣으세요)
client = Groq(api_key="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")

# 기존 AI 응답 함수
def get_ai_response(text):
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": text}],
        model="llama-3.3-70b-versatile",
        temperature=0.3
    )
    return chat_completion.choices[0].message.content

# 1. 카카오톡 대화 처리 함수
@app.post('/api/kakao')
async def kakao_chat(request: Request):
    req = await request.json()
    utterance = req.get('userRequest', {}).get('utterance', '')

    # 설정 명령어 처리
    if utterance.startswith("설정:"):
        return {
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": "학습 설정이 저장되었습니다. 이제 정해진 시간에 학습 알림을 보내드릴게요."}}]}
        }
    
    # 일반 대화 처리
    response_text = get_ai_response(utterance)
    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": response_text}}]}
    }

# 2. 알림 트리거 함수 (Render Cron Job용)
@app.get('/api/cron/push')
async def trigger_push():
    # 추후 여기에 시트 연동 및 카카오 메시지 발송 로직이 들어갑니다.
    print("알림 발송 로직이 작동 중입니다.")
    return {"status": "알림 발송 시도 완료"}
