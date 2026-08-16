from fastapi import FastAPI, Request
from groq import Groq
import os

app = FastAPI()

# Groq 설정
client = Groq(api_key="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")

# 사용자별 설정 저장 (메모리 방식: 서버 재시작 시 초기화되지만 테스트용으로 최적)
user_settings = {}

def get_ai_response(user_id, text):
    # 사용자의 설정을 가져옴 (없으면 기본값 설정)
    setting = user_settings.get(user_id, {"lang": "영어", "level": "초급"})
    
    # 학습 맞춤형 프롬프트
    prompt = f"""
    당신은 사용자에게 어학을 가르치는 전문 에이전트입니다.
    현재 학습자의 언어는 {setting['lang']}, 난이도는 {setting['level']}입니다.
    이 조건에 맞춰 아주 짧고 핵심적인 학습 콘텐츠 1개를 제시하고, 사용자가 답할 수 있는 퀴즈를 하나 내주세요.
    """
    
    chat_completion = client.chat.completions.create(
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
        model="llama-3.3-70b-versatile",
        temperature=0.3
    )
    return chat_completion.choices[0].message.content

@app.post('/api/kakao')
async def kakao_chat(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id')
    utterance = req.get('userRequest', {}).get('utterance', '')

    # 설정 명령어 인식: "설정: 언어, 난이도" (예: 설정: 베트남어, 중급)
    if utterance.startswith("설정:"):
        parts = utterance.replace("설정:", "").split(",")
        if len(parts) >= 2:
            user_settings[user_id] = {"lang": parts[0].strip(), "level": parts[1].strip()}
            return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"설정 완료! 이제부터 {parts[0].strip()}를 {parts[1].strip()} 난이도로 학습합니다."}}]}}
        return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "올바른 형식이 아닙니다. '설정: 언어, 난이도' 형식으로 입력해주세요."}}]}}
    
    # 일반 학습 진행
    response_text = get_ai_response(user_id, utterance)
    return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": response_text}}]}}

@app.get('/api/cron/push')
async def trigger_push():
    # 추후 여기에 카카오 API 연동 로직 추가
    return {"status": "테스트 완료"}
