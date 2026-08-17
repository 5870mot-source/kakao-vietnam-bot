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

    # 3. [커리큘럼 시작] 버튼 클릭 시 -> 1단계 (공부 및 핵심 표현 학습)로 진입
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
        
        user_states[user_id]["step"] = "STEP_1_STUDY"
        return await send_study_content(user_id, "STEP_1_STUDY")

    # 4. 단계별 진행 버튼 분기 처리
    if utterance == "1단계 복습하기":
        user_states[user_id]["step"] = "STEP_1_STUDY"
        return await send_study_content(user_id, "STEP_1_STUDY")
    elif utterance == "2단계 표현 학습하기":
        user_states[user_id]["step"] = "STEP_2_STUDY"
        return await send_study_content(user_id, "STEP_2_STUDY")
    elif utterance == "3단계 실전 미션 도전하기":
        user_states[user_id]["step"] = "STEP_3_MISSION"
        return await send_mission_prompt(user_id)

    # 5. 3단계 실전 미션에 대한 사용자 답변(음성/텍스트) 처리
    current_state = user_states[user_id]["step"]
    if current_state == "STEP_3_MISSION":
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
                
        return await handle_mission_feedback(user_id, user_answer)

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
                            f"{'✅ 준비 완료! 아래 버튼을 눌러 학습을 시작하세요.' if lang != '미선택' and level != '미선택' else '👉 아래 버튼을 눌러 언어와 난이도를 마저 선택해 주세요!'}"
                }
            }],
            "quickReplies": quick_replies
        }
    }

async def send_study_content(user_id, step):
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]
    
    # AI를 통해 해당 레벨에 맞는 고품격 학습 컨텐츠 생성
    prompt = (
        f"당신은 최고급 글로벌 어학 코치입니다. 학습자 레벨: '{level}', 목표 언어: '{lang}'\n"
        f"주제: '중요한 비즈니스 일정 변경 요청 및 조율'\n"
    )
    
    if step == "STEP_1_STUDY":
        prompt += (
            f"1단계 학습 내용을 제공해주세요.\n"
            f"- 내용: 상대방의 거부감을 최소화하고 정중하게 일정을 열어가는 **[오프닝 핵심 패턴 및 유용한 표현 3가지]**를 예문과 함께 친절하게 정리해주세요."
        )
        next_button = "2단계 표현 학습하기"
    else:
        prompt += (
            f"2단계 학습 내용을 제공해주세요.\n"
            f"- 내용: 상대방이 왜 일정을 바꾸려 하냐고 물었을 때, 당황하지 않고 논리적으로 사유를 방어하고 신뢰를 주는 **[리스크 방어 및 설득 고급 어휘/콤보 3가지]**를 정리해주세요."
        )
        next_button = "3단계 실전 미션 도전하기"

    try:
        completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
        study_text = completion.choices[0].message.content
    except:
        study_text = "학습 콘텐츠를 불러오는 중입니다."

    header = "📖 [1단계: 핵심 오프닝 표현 학습]" if step == "STEP_1_STUDY" else "📖 [2단계: 리스크 방어 및 설득 표현 학습]"

    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"🗺️ [{lang} / {level}] {header}\n\n{study_text}"
                }
            }],
            "quickReplies": [
                {"label": f"👉 {next_button}", "action": "message", "messageText": next_button}
            ]
        }
    }

async def send_mission_prompt(user_id):
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]
    
    mission_text = (
        f"🎙️ [3단계: 실전 음성 녹음 미션]\n\n"
        f"앞서 학습한 표현들을 활용해, **중요한 프로젝트 일정을 연기해야 하는 상황**을 가정하고 오프닝부터 사유 설명, 클로징까지의 흐름을 **음성으로 자유롭게 녹음**해서 보내주세요!\n\n"
        f"💡 마이크 버튼을 눌러 편하게 녹음해 주시면 수석 코치의 하이엔드 피드백과 대안 표현을 제공해 드립니다."
    )
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"🗺️ [{lang} / {level}]\n\n{mission_text}"
                }
            }]
        }
    }

async def handle_mission_feedback(user_id, utterance):
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]

    prompt = (
        f"당신은 글로벌 어학(오픽/SJBT) 수석 코치입니다. "
        f"학습자 레벨: '{level}', 목표 언어: '{lang}'\n"
        f"학습자가 앞서 학습한 내용을 바탕으로 제출한 실전 답변: '{utterance}'\n\n"
        f"다음 기준으로 입체적인 피드백을 제공해주세요:\n"
        f"1. 🎯 **표현 평가**: 앞서 배운 표현이나 오프닝 뉘앙스가 잘 반영되었는지 분석.\n"
        f"2. ✨ **하이엔드 대안 제시**: 채점관의 귀를 사로잡을 수 있는 더 세련된 원어민 시그니처 표현 제안.\n"
        f"3. 💡 **총평 및 칭찬**: 따뜻하고 격려가 되는 최종 코칭."
    )
    
    try:
        completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
        feedback = completion.choices[0].message.content
    except:
        feedback = "AI 분석 완료."

    user_states[user_id]["step"] = "IDLE"
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"🎙️ [인식된 답변]: \"{utterance}\"\n\n📊 [실전 미션 하이엔드 코칭 결과]\n{feedback}\n\n모든 과정을 훌륭하게 수료하셨습니다!"
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
