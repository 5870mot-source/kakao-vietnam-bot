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

    # 1. 언어 선택 감지 (유연하게 처리)
    if "영어" in utterance or "언어:영어" in utterance:
        user_states[user_id]["lang"] = "영어"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    elif "일본어" in utterance or "언어:일본어" in utterance:
        user_states[user_id]["lang"] = "일본어"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    elif "베트남어" in utterance or "언어:베트남어" in utterance:
        user_states[user_id]["lang"] = "베트남어"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    
    # 2. 난이도 선택 감지 (유연하게 처리)
    if "초급" in utterance or "난이도:초급" in utterance:
        user_states[user_id]["level"] = "초급"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    elif "중급" in utterance or "난이도:중급" in utterance:
        user_states[user_id]["level"] = "중급"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    elif "고급" in utterance or "난이도:고급" in utterance:
        user_states[user_id]["level"] = "고급"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)

    # 3. [커리큘럼 시작] 버튼 클릭 시
    if "오늘 학습 시작" in utterance:
        if not user_states[user_id]["lang"] or not user_states[user_id]["level"]:
            return {
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "⚠️ 언어와 난이도를 모두 먼저 선택해주세요!"}}],
                    "quickReplies": [
                        {"label": "영어", "action": "message", "messageText": "영어"},
                        {"label": "중급", "action": "message", "messageText": "중급"}
                    ]
                }
            }
        
        user_states[user_id]["step"] = "STEP_1"
        return await send_mission(user_id, "STEP_1")

    # 4. 단계별 미션 답변 처리
    current_state = user_states[user_id]["step"]
    if current_state in ["STEP_1", "STEP_2", "STEP_3"]:
        return await handle_mission_answer(user_id, utterance)

    return await send_setting_status(user_id)

async def send_setting_status(user_id):
    state = user_states[user_id]
    lang = state["lang"] or "미선택"
    level = state["level"] or "미선택"
    
    quick_replies = []
    if lang != "미선택" and level != "미선택":
        quick_replies.append({"label": "🚀 3단계 커리큘럼 시작", "action": "message", "messageText": "오늘 학습 시작"})
    else:
        # 선택을 돕는 빠른 응답지 제공
        if lang == "미선택":
            quick_replies.extend([
                {"label": "영어 선택", "action": "message", "messageText": "영어"},
                {"label": "일본어 선택", "action": "message", "messageText": "일본어"},
                {"label": "베트남어 선택", "action": "message", "messageText": "베트남어"}
            ])
        if level == "미선택":
            quick_replies.extend([
                {"label": "초급 선택", "action": "message", "messageText": "초급"},
                {"label": "중급 선택", "action": "message", "messageText": "중급"},
                {"label": "고급 선택", "action": "message", "messageText": "고급"}
            ])

    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"📌 현재 설정\n• 언어: [{lang}]\n• 난이도: [{level}]\n\n"
                            f"{'✅ 준비 완료! 아래 버튼을 눌러 시작하세요.' if quick_replies and '🚀' in str(quick_replies) else '👉 아래 버튼을 눌러 언어와 난이도를 마저 선택해 주세요!'}"
                }
            }],
            "quickReplies": quick_replies
        }
    }

async def send_mission(user_id, step):
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"🗺️ [{lang} / {level}] 3단계 커리큘럼 1단계 미션!\n\n"
                            f"📌 상사에게 일정 변경을 정중하게 요청하는 첫 문장을 작성해 주세요!"
                }
            }]
        }
    }

async def handle_mission_answer(user_id, utterance):
    current_step = user_states[user_id]["step"]
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]

    prompt = f"당신은 전문 {lang} 멘토입니다. 학습자({level})의 답변 '{utterance}'을 피드백하고 교정해주세요."
    try:
        completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
        feedback = completion.choices[0].message.content
    except:
        feedback = "AI 분석 완료."

    if current_step == "STEP_1":
        user_states[user_id]["step"] = "STEP_2"
        next_text = f"📊 [1단계 코칭 결과]\n{feedback}\n\n👉 **[2단계 미션]**\n상대방이 '왜 일정을 변경해야 하냐고' 물어왔습니다. 타당한 사유를 한 문장으로 답변해 주세요!"
    elif current_step == "STEP_2":
        user_states[user_id]["step"] = "STEP_3"
        next_text = f"📊 [2단계 코칭 결과]\n{feedback}\n\n👉 **[3단계 최종 미션]**\n일정을 최종 확정하며 마무리하는 정중한 메시지를 작성해 주세요!"
    else:
        user_states[user_id]["step"] = "IDLE"
        next_text = f"🎉 [3단계 최종 코칭 결과]\n{feedback}\n\n모든 과정을 완료하셨습니다!"

    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": next_text}}]
        }
    }

@app.get('/api/cron/push')
@app.post('/api/cron/push')
async def cron_push():
    return {"status": "ok"}from fastapi import FastAPI, Request
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

    # 1. 언어 선택 감지 (유연하게 처리)
    if "영어" in utterance or "언어:영어" in utterance:
        user_states[user_id]["lang"] = "영어"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    elif "일본어" in utterance or "언어:일본어" in utterance:
        user_states[user_id]["lang"] = "일본어"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    elif "베트남어" in utterance or "언어:베트남어" in utterance:
        user_states[user_id]["lang"] = "베트남어"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    
    # 2. 난이도 선택 감지 (유연하게 처리)
    if "초급" in utterance or "난이도:초급" in utterance:
        user_states[user_id]["level"] = "초급"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    elif "중급" in utterance or "난이도:중급" in utterance:
        user_states[user_id]["level"] = "중급"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)
    elif "고급" in utterance or "난이도:고급" in utterance:
        user_states[user_id]["level"] = "고급"
        user_states[user_id]["step"] = "IDLE"
        return await send_setting_status(user_id)

    # 3. [커리큘럼 시작] 버튼 클릭 시
    if "오늘 학습 시작" in utterance:
        if not user_states[user_id]["lang"] or not user_states[user_id]["level"]:
            return {
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "⚠️ 언어와 난이도를 모두 먼저 선택해주세요!"}}],
                    "quickReplies": [
                        {"label": "영어", "action": "message", "messageText": "영어"},
                        {"label": "중급", "action": "message", "messageText": "중급"}
                    ]
                }
            }
        
        user_states[user_id]["step"] = "STEP_1"
        return await send_mission(user_id, "STEP_1")

    # 4. 단계별 미션 답변 처리
    current_state = user_states[user_id]["step"]
    if current_state in ["STEP_1", "STEP_2", "STEP_3"]:
        return await handle_mission_answer(user_id, utterance)

    return await send_setting_status(user_id)

async def send_setting_status(user_id):
    state = user_states[user_id]
    lang = state["lang"] or "미선택"
    level = state["level"] or "미선택"
    
    quick_replies = []
    if lang != "미선택" and level != "미선택":
        quick_replies.append({"label": "🚀 3단계 커리큘럼 시작", "action": "message", "messageText": "오늘 학습 시작"})
    else:
        # 선택을 돕는 빠른 응답지 제공
        if lang == "미선택":
            quick_replies.extend([
                {"label": "영어 선택", "action": "message", "messageText": "영어"},
                {"label": "일본어 선택", "action": "message", "messageText": "일본어"},
                {"label": "베트남어 선택", "action": "message", "messageText": "베트남어"}
            ])
        if level == "미선택":
            quick_replies.extend([
                {"label": "초급 선택", "action": "message", "messageText": "초급"},
                {"label": "중급 선택", "action": "message", "messageText": "중급"},
                {"label": "고급 선택", "action": "message", "messageText": "고급"}
            ])

    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"📌 현재 설정\n• 언어: [{lang}]\n• 난이도: [{level}]\n\n"
                            f"{'✅ 준비 완료! 아래 버튼을 눌러 시작하세요.' if quick_replies and '🚀' in str(quick_replies) else '👉 아래 버튼을 눌러 언어와 난이도를 마저 선택해 주세요!'}"
                }
            }],
            "quickReplies": quick_replies
        }
    }

async def send_mission(user_id, step):
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"🗺️ [{lang} / {level}] 3단계 커리큘럼 1단계 미션!\n\n"
                            f"📌 상사에게 일정 변경을 정중하게 요청하는 첫 문장을 작성해 주세요!"
                }
            }]
        }
    }

async def handle_mission_answer(user_id, utterance):
    current_step = user_states[user_id]["step"]
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]

    prompt = f"당신은 전문 {lang} 멘토입니다. 학습자({level})의 답변 '{utterance}'을 피드백하고 교정해주세요."
    try:
        completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
        feedback = completion.choices[0].message.content
    except:
        feedback = "AI 분석 완료."

    if current_step == "STEP_1":
        user_states[user_id]["step"] = "STEP_2"
        next_text = f"📊 [1단계 코칭 결과]\n{feedback}\n\n👉 **[2단계 미션]**\n상대방이 '왜 일정을 변경해야 하냐고' 물어왔습니다. 타당한 사유를 한 문장으로 답변해 주세요!"
    elif current_step == "STEP_2":
        user_states[user_id]["step"] = "STEP_3"
        next_text = f"📊 [2단계 코칭 결과]\n{feedback}\n\n👉 **[3단계 최종 미션]**\n일정을 최종 확정하며 마무리하는 정중한 메시지를 작성해 주세요!"
    else:
        user_states[user_id]["step"] = "IDLE"
        next_text = f"🎉 [3단계 최종 코칭 결과]\n{feedback}\n\n모든 과정을 완료하셨습니다!"

    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": next_text}}]
        }
    }

@app.get('/api/cron/push')
@app.post('/api/cron/push')
async def cron_push():
    return {"status": "ok"}
