from fastapi import FastAPI, Request
from groq import Groq
import os
import httpx
import tempfile

app = FastAPI()
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))

user_states = {}

@app.post('/api/kakao')
async def kakao_webhook(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()
    
    media_url = None
    if utterance.startswith("http") and ("m4a" in utterance or "audio" in utterance or "talka_aac" in utterance):
        media_url = utterance

    if user_id not in user_states:
        user_states[user_id] = {"lang": None, "level": None, "step": "IDLE"}

    # 1. 언어 선택 감지
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
    
    # 2. 난이도 선택 감지
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

    # 4. 단계 수동 분기 처리
    if utterance == "1단계 다시 하기":
        user_states[user_id]["step"] = "STEP_1"
        return await send_mission(user_id, "STEP_1")
    elif utterance == "2단계로 넘어가기":
        user_states[user_id]["step"] = "STEP_2"
        return await send_mission(user_id, "STEP_2")
    elif utterance == "2단계 다시 하기":
        user_states[user_id]["step"] = "STEP_2"
        return await send_mission(user_id, "STEP_2")
    elif utterance == "3단계로 넘어가기":
        user_states[user_id]["step"] = "STEP_3"
        return await send_mission(user_id, "STEP_3")
    elif utterance == "3단계 다시 하기":
        user_states[user_id]["step"] = "STEP_3"
        return await send_mission(user_id, "STEP_3")

    # 5. 미션 답변 처리
    current_state = user_states[user_id]["step"]
    if current_state in ["STEP_1", "STEP_2", "STEP_3"]:
        user_answer = utterance
        
        if media_url:
            try:
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.get(media_url)
                    if response.status_code == 200:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as temp_file:
                            temp_file.write(response.content)
                            temp_file_path = temp_file.name
                        
                        with open(temp_file_path, "rb") as audio_file:
                            transcription = client.audio.transcriptions.create(
                                file=(temp_file_path, audio_file.read()),
                                model="whisper-large-v3",
                                language="en" if user_states[user_id]["lang"] == "영어" else ("ja" if user_states[user_id]["lang"] == "일본어" else "vi"),
                                response_format="text"
                            )
                        os.unlink(temp_file_path)
                        user_answer = transcription.strip()
                    else:
                        user_answer = "음성 파일을 다운로드하지 못했습니다."
            except Exception as e:
                user_answer = utterance
                
        return await handle_mission_answer(user_id, user_answer)

    return await send_setting_status(user_id)

async def send_setting_status(user_id):
    state = user_states[user_id]
    lang = state["lang"] or "미선택"
    level = state["level"] or "미선택"
    
    quick_replies = []
    if lang != "미선택" and level != "미선택":
        quick_replies.append({"label": "🚀 3단계 커리큘럼 시작", "action": "message", "messageText": "오늘 학습 시작"})
    else:
        if lang == "미선택":
            quick_replies.extend([
                {"label": "영어", "action": "message", "messageText": "영어"},
                {"label": "일본어", "action": "message", "messageText": "일본어"},
                {"label": "베트남어", "action": "message", "messageText": "베트남어"}
            ])
        if level == "미선택":
            quick_replies.extend([
                {"label": "초급", "action": "message", "messageText": "초급"},
                {"label": "중급", "action": "message", "messageText": "중급"},
                {"label": "고급", "action": "message", "messageText": "고급"}
            ])

    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"📌 현재 설정\n• 언어: [{lang}]\n• 난이도: [{level}]\n\n"
                            f"{'✅ 준비 완료! 아래 버튼을 눌러 시작하세요.' if lang != '미선택' and level != '미선택' else '👉 아래 버튼을 눌러 언어와 난이도를 마저 선택해 주세요!'}"
                }
            }],
            "quickReplies": quick_replies
        }
    }

async def send_mission(user_id, step):
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]
    
    if level == "고급":
        missions = {
            "STEP_1": "【1단계: 전략적 오프닝 (Strategic Opening)】\n📌 [미션] 중요한 프로젝트 마감일을 앞두고 예상치 못한 변수가 생겨 임원진 보고 일정을 연기해야 합니다. 상대방의 부담을 최소화하고 격식 있게 제안하는 오프닝 발언을 음성으로 녹음해 주세요.",
            "STEP_2": "【2단계: 리스크 방어 및 논리적 설득 (Risk Mitigation)】\n📌 [미션] 상대방이 일정 연기에 난색을 표하며 병목 현상을 우려합니다. 리스크가 철저히 통제되고 있음을 전문 어휘로 안심시키는 설득 발언을 녹음해 주세요.",
            "STEP_3": "【3단계: 하이엔드 클로징 (Executive Closing)】\n📌 [미션] 최종 수정된 타임라인을 확정 짓고 향후 일정에 확신을 주는 임원급 비즈니스 클로징 멘트를 녹음해 주세요."
        }
    elif level == "중급":
        missions = {
            "STEP_1": "【1단계: 정중한 일정 변경 요청】\n📌 [미션] 내부 사정으로 내일 예정된 클라이언트 미팅을 오후로 변경해 달라고 요청하는 문장을 음성으로 녹음해 주세요.",
            "STEP_2": "【2단계: 타당한 사유 설명 및 방어】\n📌 [미션] 상대방이 변경 이유를 물어왔습니다. 데이터 검토에 시간이 더 필요하다는 사유를 자연스럽게 설명해 주세요.",
            "STEP_3": "【3단계: 감사의 인사 및 최종 확정】\n📌 [미션] 양해에 감사드리며 최종 미팅 시간을 확정하는 정중한 메시지를 녹음해 주세요."
        }
    else:
        missions = {
            "STEP_1": "【1단계: 첫 문장 영작 및 요청】\n📌 [미션] 상사에게 일정 변경을 정중하게 요청하는 첫 문장을 음성으로 녹음해 주세요!",
            "STEP_2": "【2단계: 간단한 사유 답변】\n📌 [미션] 상대방이 왜 변경해야 하냐고 물었습니다. 타당한 사유를 한 문장으로 녹음해 주세요!",
            "STEP_3": "【3단계: 일정 최종 확정】\n📌 [미션] 최종 일정을 확인하며 마무리 인사를 녹음해 주세요!"
        }
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"🗺️ [{lang} / {level}]\n\n{missions[step]}"
                }
            }]
        }
    }

async def handle_mission_answer(user_id, utterance):
    current_step = user_states[user_id]["step"]
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]

    # 오픽/SJBT 고득점 트렌드에 맞춘 입체적 분석 프롬프트
    prompt = (
        f"당신은 최고급 글로벌 어학(오픽/SJBT) 및 비즈니스 수석 코치입니다. "
        f"학습자 레벨: '{level}', 목표 언어: '{lang}'\n"
        f"학습자의 답변: '{utterance}'\n\n"
        f"다음 기준으로 깊이 있는 분석과 코칭을 제공해주세요:\n"
        f"1. 🎯 **표현 평가**: 원어민 관점에서 이 답변이 얼마나 자연스러운지, 감점 요인이 있는지 분석.\n"
        f"2. ✨ **하이엔드 대안 제시**: 채점관의 귀를 사로잡을 수 있는 더 세련된 어휘와 콤보 표현(Native Expression) 2가지 이상 제시.\n"
        f"3. 💡 **실전 팁**: 해당 단계에서 고득점을 받기 위한 핵심 팁 전달."
    )
    
    try:
        completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
        feedback = completion.choices[0].message.content
    except:
        feedback = "AI 분석 완료."

    if current_step == "STEP_1":
        user_states[user_id]["step"] = "CHOIR_1"
        return {
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": f"🎙️ [인식된 답변]: \"{utterance}\"\n\n📊 [1단계 하이엔드 코칭 결과]\n{feedback}\n\n어떻게 진행하시겠습니까?"
                    }
                }],
                "quickReplies": [
                    {"label": "🔄 1단계 다시 하기", "action": "message", "messageText": "1단계 다시 하기"},
                    {"label": "👉 2단계로 넘어가기", "action": "message", "messageText": "2단계로 넘어가기"}
                ]
            }
        }
    elif current_step == "STEP_2":
        user_states[user_id]["step"] = "CHOIR_2"
        return {
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": f"🎙️ [인식된 답변]: \"{utterance}\"\n\n📊 [2단계 하이엔드 코칭 결과]\n{feedback}\n\n어떻게 진행하시겠습니까?"
                    }
                }],
                "quickReplies": [
                    {"label": "🔄 2단계 다시 하기", "action": "message", "messageText": "2단계 다시 하기"},
                    {"label": "👉 3단계로 넘어가기", "action": "message", "messageText": "3단계로 넘어가기"}
                ]
            }
        }
    else:
        user_states[user_id]["step"] = "IDLE"
        return {
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": f"🎙️ [인식된 답변]: \"{utterance}\"\n\n🎉 [3단계 최종 하이엔드 코칭 결과]\n{feedback}\n\n모든 마스터 과정을 수료하셨습니다!"
                    }
                }],
                "quickReplies": [
                    {"label": "🔄 새로운 커리큘럼 시작", "action": "message", "messageText": "오늘 학습 시작"}
                ]
            }
        }

@app.get('/api/cron/push')
@app.post('/api/cron/push')
async def cron_push():
    return {"status": "ok"}
