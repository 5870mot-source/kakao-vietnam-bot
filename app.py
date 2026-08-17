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
    
    # 카카오톡 요청에 음성 파일(media) 또는 첨부된 링크가 있는지 확인
    action = req.get('action', {})
    detailParams = action.get('detailParams', {})
    
    # 사용자가 음성 메시지를 보낸 경우 (카카오톡 음성 메시지 URL 추출)
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

    # 4. 단계별 미션 답변 처리 (텍스트 또는 음성 파일 처리)
    current_state = user_states[user_id]["step"]
    if current_state in ["STEP_1", "STEP_2", "STEP_3"]:
        user_answer = utterance
        
        # 만약 사용자가 음성 메시지(URL)를 보냈다면 Whisper AI로 텍스트 변환 수행
        if media_url:
            try:
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.get(media_url)
                    if response.status_code == 200:
                        # 임시 파일로 저장 후 Groq Whisper에 전달
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
                user_answer = utterance # 실패 시 원본 유지
                
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
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"🗺️ [{lang} / {level}] 3단계 커리큘럼 1단계 미션!\n\n"
                            f"📌 마이크 버튼을 눌러 **음성으로** 정중한 요청 문장을 녹음해서 보내주세요!"
                }
            }]
        }
    }

async def handle_mission_answer(user_id, utterance):
    current_step = user_states[user_id]["step"]
    lang = user_states[user_id]["lang"]
    level = user_states[user_id]["level"]

    prompt = f"당신은 전문 {lang} 멘토입니다. 학습자({level})가 음성으로 답변한 내용: '{utterance}'을 피드백하고 교정해주세요."
    try:
        completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
        feedback = completion.choices[0].message.content
    except:
        feedback = "AI 분석 완료."

    if current_step == "STEP_1":
        user_states[user_id]["step"] = "STEP_2"
        next_text = f"🎙️ [인식된 답변]: \"{utterance}\"\n\n📊 [1단계 코칭 결과]\n{feedback}\n\n👉 **[2단계 미션]**\n상대방이 사유를 물어왔습니다. **음성 녹음**으로 타당한 사유를 답변해 주세요!"
    elif current_step == "STEP_2":
        user_states[user_id]["step"] = "STEP_3"
        next_text = f"🎙️ [인식된 답변]: \"{utterance}\"\n\n📊 [2단계 코칭 결과]\n{feedback}\n\n👉 **[3단계 최종 미션]**\n일정을 최종 확정하는 내용을 **음성 녹음**으로 마무리해 주세요!"
    else:
        user_states[user_id]["step"] = "IDLE"
        next_text = f"🎙️ [인식된 답변]: \"{utterance}\"\n\n🎉 [3단계 최종 코칭 결과]\n{feedback}\n\n모든 과정을 완료하셨습니다!"

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
