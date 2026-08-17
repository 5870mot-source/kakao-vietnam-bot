from fastapi import FastAPI, Request
from groq import Groq
import os

app = FastAPI()

# Groq API 키 설정 (Render 환경 변수에 설정되어 있어야 합니다)
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))

# 사용자별 상태 관리 메모리
user_states = {}

# 1. 챗봇 연동 및 커리큘럼 로직 (기존 카카오톡 통신)
@app.post('/api/kakao')
async def kakao_webhook(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()
    
    if user_id not in user_states:
        user_states[user_id] = {"lang": "영어", "level": "초급", "step": "IDLE"}

    state = user_states[user_id]["step"]
    current_lang = user_states[user_id]["lang"]
    current_level = user_states[user_id]["level"]

    # 언어/난이도 변경 신호 처리
    if utterance.startswith("언어:"):
        user_states[user_id]["lang"] = utterance.split(":")[1]
        user_states[user_id]["step"] = "IDLE"
        return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"✨ 학습 언어가 [{user_states[user_id]['lang']}]로 설정되었습니다."}}]}}
    
    if utterance.startswith("난이도:"):
        user_states[user_id]["level"] = utterance.split(":")[1]
        user_states[user_id]["step"] = "IDLE"
        return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"🎯 난이도가 [{user_states[user_id]['level']}]로 설정되었습니다."}}]}}

    # 미션 출제
    if "학습 시작" in utterance or "시작" in utterance:
        user_states[user_id]["step"] = "WAITING_ANSWER"
        mission = f"[{current_lang} / {current_level}] 학습 미션: 상황에 맞는 비즈니스 문장을 작성하세요."
        return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": mission}}]}}

    # 답변 분석 및 피드백
    if state == "WAITING_ANSWER" and utterance:
        prompt = f"{current_lang} 원어민 멘토로서, 학습자의 답변 '{utterance}'를 '{current_level}' 수준에 맞게 평가하고 교정해주세요."
        try:
            completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
            feedback = completion.choices[0].message.content
        except:
            feedback = "AI 분석 중 오류가 발생했습니다."
        
        user_states[user_id]["step"] = "IDLE"
        return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": feedback}}]}}

    return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "반갑습니다! 하단 메뉴에서 학습을 시작하세요."}}]}}

# 2. cron-job.org 호출 전용 (응답 용량을 최소화하여 Failed 방지)
@app.get('/api/cron/push')
async def cron_push():
    # 실제 푸시 로직이 있다면 여기에 추가하고, 응답은 최소화합니다.
    return {"status": "ok"}
