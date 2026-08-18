import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from groq import Groq

app = FastAPI()

# Groq 클라이언트 설정 (환경 변수 우선, 없을 경우 기본 플레이스홀더)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "여기에_본인의_Groq_API_키를_입력하세요")
client = Groq(api_key=GROQ_API_KEY)

# 사용자별 세션 저장소
user_sessions = {}

# 핵심 실무 주제 8선
TOPICS_8 = [
    "비즈니스 미팅", "이메일 작성", "협상 전략", "발표 스킬", 
    "전화 응대", "여행 회화", "카페 주문", "일상 대화"
]

@app.post("/api/kakao")
async def kakao_skill(request: Request):
    try:
        body = await request.json()
        user_id = body.get("userRequest", {}).get("user", {}).get("id", "default_user")
        user_message = body.get("userRequest", {}).get("utterance", "").strip()
        
        # 카카오톡 음성 파일/오디오 URL 추출 시도
        params = body.get("action", {}).get("params", {})
        speech_url = body.get("userRequest", {}).get("speechUrl") or params.get("speechUrl")

        # 세션 초기화 또는 처음으로 돌아갈 때
        if user_id not in user_sessions or "처음" in user_message or "처음으로" in user_message or "오늘의 학습 시작" in user_message:
            user_sessions[user_id] = {"lang": None, "level": None, "topic": None, "step": 0, "quiz_started": False}
        
        session = user_sessions[user_id]

        # [1단계] 언어 선택
        if not session["lang"]:
            if "영어" in user_message:
                session["lang"] = "영어"
            elif "베트남어" in user_message:
                session["lang"] = "베트남어"

            if session["lang"]:
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": f"🎯 **{session['lang']}**를 선택하셨습니다!\n\n이어 원하시는 **난이도**를 선택해 주세요."}}],
                        "quickReplies": [
                            {"label": "초급", "action": "message", "messageText": "초급"},
                            {"label": "중급", "action": "message", "messageText": "중급"},
                            {"label": "고급", "action": "message", "messageText": "고급"}
                        ]
                    }
                })
            else:
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "👋 환영합니다! 맞춤형 어학 학습을 시작해볼까요?\n\n먼저 학습할 **언어**를 선택해 주세요."}}],
                        "quickReplies": [
                            {"label": "영어", "action": "message", "messageText": "영어"},
                            {"label": "베트남어", "action": "message", "messageText": "베트남어"}
                        ]
                    }
                })

        # [2단계] 난이도 선택
        if not session["level"]:
            if "초급" in user_message:
                session["level"] = "초급"
            elif "중급" in user_message:
                session["level"] = "중급"
            elif "고급" in user_message:
                session["level"] = "고급"

            if session["level"]:
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": f"✨ [{session['lang']} / {session['level']}] 난이도가 설정되었습니다!\n\n학습하실 **주제**를 아래 버튼에서 선택해 주세요."}}],
                        "quickReplies": [{"label": t, "action": "message", "messageText": t} for t in TOPICS_8]
                    }
                })
            else:
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "올바른 난이도(초급,중급,고급)를 버튼을 눌러 선택해 주세요!"}}],
                        "quickReplies": [
                            {"label": "초급", "action": "message", "messageText": "초급"},
                            {"label": "중급", "action": "message", "messageText": "중급"},
                            {"label": "고급", "action": "message", "messageText": "고급"}
                        ]
                    }
                })

        # [3단계] 주제 선정 완료 -> 1단계 진입
        if not session["topic"]:
            matched_topic = next((t for t in TOPICS_8 if t in user_message), None)
            if matched_topic:
                session["topic"] = matched_topic
                session["step"] = 1
            else:
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "아래 버튼에서 학습하실 주제를 선택해 주세요!"}}],
                        "quickReplies": [{"label": t, "action": "message", "messageText": t} for t in TOPICS_8]
                    }
                })

        # [4단계] 커리큘럼 스텝 이동
        if "다음 단계" in user_message:
            if session["step"] < 4:
                session["step"] += 1
                session["quiz_started"] = False
        elif "이전 단계" in user_message:
            if session["step"] > 1:
                session["step"] -= 1
                session["quiz_started"] = False

        step = session["step"]
        lang = session["lang"]
        lvl = session["level"]
        top = session["topic"]

        # [Step 3] 음성/텍스트 분석
        feedback_text = ""
        user_input_to_analyze = user_message

        if speech_url:
            try:
                audio_res = requests.get(speech_url)
                if audio_res.status_code == 200:
                    audio_path = "temp_user_audio.m4a"
                    with open(audio_path, "wb") as f:
                        f.write(audio_res.content)
                    
                    with open(audio_path, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-large-v3",
                            file=audio_file,
                            language="en" if lang == "영어" else "vi"
                        )
                    user_input_to_analyze = transcription.text
                    feedback_text += f"\n🎙️ **[음성 인식 결과]**\n\"{user_input_to_analyze}\"\n"
                    
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
            except Exception:
                feedback_text += "\n(음성 파일 처리 중 오류 발생)"

        if step == 3 and user_input_to_analyze not in ["다음 단계", "이전 단계", top] and len(user_input_to_analyze) > 1:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"당신은 {lang} 전문 원어민 튜터입니다. [{top}], 난이도: {lvl} 상황에서 사용자가 작성한 문장을 분석하여 교정 및 피드백을 한국어로 제공해주세요."
                        },
                        {
                            "role": "user",
                            "content": user_input_to_analyze
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                )
                ai_feedback = chat_completion.choices[0].message.content
                feedback_text += f"\n🤖 **[AI 튜터 교정 피드백]**\n{ai_feedback}\n"
            except Exception:
                feedback_text += "\n(AI 피드백 지연)"

        # [Step 4] 미니 게임 퀴즈
        game_text = ""
        if step == 4:
            if session.get("quiz_started") and user_message not in ["다음 단계", "이전 단계", "처음으로", "🔄 다시 풀기"]:
                try:
                    grade_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": f"당신은 어학 퀴즈 마스터입니다. 주제([{top}], 난이도: {lvl}) 퀴즈에 대해 사용자의 답변('{user_message}')을 채점하고 해설을 한국어로 제공해주세요."
                            }
                        ],
                        model="llama-3.3-70b-versatile",
                    )
                    game_text = f"\n🎯 **[채점 결과]**\n{grade_completion.choices[0].message.content}\n"
                except Exception:
                    game_text = "\n(채점 중 오류 발생)"
            else:
                try:
                    quiz_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": f"당신은 어학 퀴즈 마스터입니다. [{top}] 상황(난이도: {lvl}) 학습 내용을 바탕으로 가볍게 풀 수 있는 실무 퀴즈 1문제를 한국어 설명과 함께 출제해주세요."
                            }
                        ],
                        model="llama-3.3-70b-versatile",
                    )
                    game_text = f"\n🎮 **[Step 4: 실전 퀴즈]**\n{quiz_completion.choices[0].message.content}\n\n✍️ 정답을 입력해 주세요!"
                    session["quiz_started"] = True
                except Exception:
                    game_text = "\n🎮 **[Step 4: 퀴즈]**\n정답을 입력해 주세요!"
                    session["quiz_started"] = True

        # 콘텐츠 매핑
        step1_map = {
            ("영어", "고급", "비즈니스 미팅"): {
                "expr": "• *\"Let's pivot our focus to the structural implications and long-term ROI.\"*",
                "dialogue": "A: We're running out of time.\nB: Let's pivot our focus.",
                "tip": "'Pivot'은 논의의 주도권을 잡는 고급 비즈니스 표현입니다."
            }
        }
        step2_map = {
            ("영어", "고급", "비즈니스 미팅"): {
                "vocab": "1. **Mitigate risk** (리스크 완화)\n2. **Stakeholder alignment** (이해관계자 조율)",
                "tip": "리스크 관리 및 구조적 용어 활용"
            }
        }
        
        default_s1 = {"expr": "• *\"Let's streamline our approach.\"*", "dialogue": "A: How to proceed?\nB: Let's streamline.", "tip": "명확한 리더십 뉘앙스"}
        default_s2 = {"vocab": "1. **Optimize efficiency** (효율성 최적화)\n2. **Strategic execution** (전략적 실행)", "tip": "프로페셔널 어휘"}

        s1 = step1_map.get((lang, lvl, top), default_s1)
        s2 = step2_map.get((lang, lvl, top), default_s2)

        if step == 1:
            text = f"📚 [{lang} | {lvl} | {top}]\n━━━━━━━━━━━━\n🔥 **Step 1: 핵심 표현**\n\n{s1['expr']}\n\n👥 **예문:**\n{s1['dialogue']}\n\n💡 **Tip:**\n{s1['tip']}"
            replies = [{"label": "➡️ 2단계로", "action": "message", "messageText": "다음 단계"}]
        elif step == 2:
            text = f"📚 [{lang} | {lvl} | {top}]\n━━━━━━━━━━━━\n🛡️ **Step 2: 심화 어휘**\n\n{s2['vocab']}\n\n💡 **Tip:**\n{s2['tip']}"
            replies = [{"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"}, {"label": "➡️ 3단계로", "action": "message", "messageText": "다음 단계"}]
        elif step == 3:
            text = f"📚 [{lang} | {lvl} | {top}]\n━━━━━━━━━━━━\n🎙️ **Step 3: 실전 미션**\n\n문장이나 음성을 보내주세요!{feedback_text}"
            replies = [{"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"}, {"label": "➡️ 4단계로", "action": "message", "messageText": "다음 단계"}]
        elif step == 4:
            text = f"📚 [{lang} | {lvl} | {top}]\n━━━━━━━━━━━━\n{game_text}"
            replies = [{"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"}, {"label": "🔄 처음으로", "action": "message", "messageText": "처음으로"}]
        else:
            session["step"] = 1
            text = "🚀 학습 시작!"
            replies = [{"label": "다음 단계", "action": "message", "messageText": "다음 단계"}]

        return JSONResponse(content={"version": "2.0", "template": {"outputs": [{"simpleText": {"text": text}}], "quickReplies": replies}})

    except Exception as e:
        return JSONResponse(content={"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "오류가 발생했습니다. 잠시 후 '처음'을 입력해주세요."}}]}})

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h2>🚀 서버 정상 작동 중</h2>"

@app.get("/health")
async def health_check():
    return "OK"
