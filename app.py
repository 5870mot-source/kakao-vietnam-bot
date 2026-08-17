from fastapi import FastAPI, Request
from groq import Groq
import os

app = FastAPI()
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))

user_states = {}

@app.post('/api/kakao')
async def kakao_webhook(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()
    
    if user_id not in user_states:
        user_states[user_id] = {"lang": "영어", "level": "초급", "step": "IDLE"}

    # 1. 언어/난이도 변경 시 -> 바로 버튼을 보여주어 학습 시작 유도
    if utterance.startswith("언어:"):
        user_states[user_id]["lang"] = utterance.split(":")[1]
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": f"✨ 언어가 [{user_states[user_id]['lang']}]로 설정되었습니다."}}],
                "quickReplies": [{"label": "🚀 학습 시작하기", "action": "message", "messageText": "오늘 학습 시작"}]
            }
        }
    
    if utterance.startswith("난이도:"):
        user_states[user_id]["level"] = utterance.split(":")[1]
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": f"🎯 난이도가 [{user_states[user_id]['level']}]로 설정되었습니다."}}],
                "quickReplies": [{"label": "🚀 학습 시작하기", "action": "message", "messageText": "오늘 학습 시작"}]
            }
        }

    # 2. [학습 시작] 버튼을 눌렀을 때 -> 미션 출제 (WAITING_ANSWER 상태로 변경)
    if "오늘 학습 시작" in utterance:
        user_states[user_id]["step"] = "WAITING_ANSWER"
        lang = user_states[user_id]["lang"]
        level = user_states[user_id]["level"]
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": f"[{lang}/{level}] 오늘의 미션: 비즈니스 상황에 맞는 문장을 작성해주세요!"}}]
            }
        }

    # 3. 답변 입력 시 (미션 대기 중인 경우)
    if user_states[user_id]["step"] == "WAITING_ANSWER":
        # AI 코칭 로직
        prompt = f"{user_states[user_id]['lang']} 원어민 멘토로서, '{utterance}' 문장을 평가해주세요."
        try:
            completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
            feedback = completion.choices[0].message.content
        except:
            feedback = "분석 오류 발생"
        
        user_states[user_id]["step"] = "IDLE"
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": feedback}}],
                "quickReplies": [{"label": "🔄 다음 미션 하기", "action": "message", "messageText": "오늘 학습 시작"}]
            }
        }

    # 기본 상태
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": "반갑습니다! 하단 메뉴에서 언어/난이도를 선택하고 '오늘 학습 시작'을 눌러주세요."}}],
            "quickReplies": [{"label": "🚀 오늘 학습 시작", "action": "message", "messageText": "오늘 학습 시작"}]
        }
    }
