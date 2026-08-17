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
        user_states[user_id] = {"lang": None, "level": None, "step": "IDLE"}

    # 1. 언어 선택
    if utterance.startswith("언어:"):
        user_states[user_id]["lang"] = utterance.split(":")[1]
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    
    # 2. 난이도 선택
    if utterance.startswith("난이도:"):
        user_states[user_id]["level"] = utterance.split(":")[1]
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)

    # 3. [커리큘럼 시작] 버튼 클릭 시
    if "오늘 학습 시작" in utterance:
        if not user_states[user_id]["lang"] or not user_states[user_id]["level"]:
            return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 언어와 난이도를 모두 먼저 선택해주세요!"}}]}}
        
        user_states[user_id]["step"] = "STEP_1"
        return await send_mission(user_id, "STEP_1")

    # 4. 단계별 미션 답변 처리
    current_state = user_states[user_id]["step"]
    if current_state in ["STEP_1", "STEP_2", "STEP_3"]:
        return await handle_mission_answer(user_id, utterance)

    return await send_setting_status(user_id)

# 상태 확인 및 시작 버튼 제어 함수
async def send_setting_status(user_id):
    state = user_states[user_id]
    lang = state["lang"] or "미선택"
    level = state["level"] or "미선택"
    
    # 두 조건이 모두 충족될 때만 [시작 버튼] 표시
    quick_replies = []
    if lang != "미선택" and level != "미선택":
        quick_replies.append({"label": "🚀 3단계 커리큘럼 시작", "action": "message", "messageText": "오늘 학습 시작"})

    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": f"📌 현재 설정\n• 언어: [{lang}]\n• 난이도: [{level}]\n\n{'아래 버튼을 눌러 학습을 시작하세요!' if quick_replies else '상단 메뉴에서 나머지를 선택해 주세요.'}"}}],
            "quickReplies": quick_replies
        }
    }

# 미션 발송 함수
async def send_mission(user_id, step):
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]
    missions = {"STEP_1": "1단계: 핵심 패턴 영작", "STEP_2": "2단계: 비즈니스 대화", "STEP_3": "3단계: 심화 대처"}
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": f"🗺️ [{missions[step]}] 미션을 시작합니다.\n\n상황에 맞는 답변을 입력하세요!"}}]
        }
    }

# 답변 처리 및 다음 단계 이동 함수
async def handle_mission_answer(user_id, utterance):
    current_step = user_states[user_id]["step"]
    # AI 피드백 로직 (생략... 이전과 동일하게 구성)
    # 피드백 후:
    if current_step == "STEP_1": user_states[user_id]["step"] = "STEP_2"
    elif current_step == "STEP_2": user_states[user_id]["step"] = "STEP_3"
    else: user_states[user_id]["step"] = "IDLE"
    return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "피드백 완료! 다음 단계로 넘어갑니다."}}]}}
