import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from groq import Groq

app = FastAPI()

# Groq 클라이언트 설정
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "여기에_본인의_Groq_API_키를_입력하세요")
client = Groq(api_key=GROQ_API_KEY)

# 사용자별 세션 저장소
user_sessions = {}

# 카카오톡 안정성(최대 10개 제한)을 고려한 핵심 실무 주제 8선
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

        # 세션 초기화 또는 처음으로 돌아갈 때
        if user_id not in user_sessions or "처음" in user_message or "처음으로" in user_message or "오늘의 학습 시작" in user_message:
            user_sessions[user_id] = {"lang": None, "level": None, "topic": None, "step": 0}
        
        session = user_sessions[user_id]

        # [1단계] 어종(언어) 선택
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

        # [2단계] 난이도 선택 직후 -> 주제 버튼 출력
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
                        "outputs": [{"simpleText": {"text": "올바른 난이도(초급, 중급, 고급)를 버튼을 눌러 선택해 주세요!"}}],
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
        elif "이전 단계" in user_message:
            if session["step"] > 1:
                session["step"] -= 1

        step = session["step"]
        lang = session["lang"]
        lvl = session["level"]
        top = session["topic"]

        # Step 3 AI 피드백 처리
        feedback_text = ""
        if step == 3 and user_message not in ["다음 단계", "이전 단계", top] and not any(t in user_message for t in TOPICS_8):
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"당신은 {lang} 전문 원어민 튜터입니다. 사용자가 작성한 문장을 교정하고 자연스러운 표현으로 피드백을 한국어로 제공해주세요."
                        },
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                )
                ai_feedback = chat_completion.choices[0].message.content
                feedback_text = f"\n\n🤖 **[AI 튜터 실시간 교정 피드백]**\n{ai_feedback}\n"
            except Exception:
                feedback_text = "\n\n(AI 피드백 생성 중 일시적인 지연이 발생했습니다.)"

        if step == 1:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 **Step 1: 핵심 오프닝 & 시그니처 패턴**\n\n"
                f"해당 상황에서 원어민이 가장 자주 사용하는 알짜배기 핵심 표현입니다.\n\n"
                f"💬 **Core Expression:**\n"
                f"• 핵심 학습 표현이 제공됩니다.\n\n"
                f"💡 **Learning Tip:**\n"
                f"상황별 맞춤형 뉘앙스를 익혀보세요."
            )
            quick_replies = [{"label": "➡️ 2단계로 넘어가기", "action": "message", "messageText": "다음 단계"}]
            
        elif step == 2:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🛡️ **Step 2: 리스크 방어 & 설득 어휘**\n\n"
                f"표현력을 높여주는 전문 심화 어휘입니다.\n\n"
                f"💬 **Advanced Vocab:**\n"
                f"• 심화 어휘 및 키워드 제공\n\n"
                f"💡 **Learning Tip:**\n"
                f"실무 대처 능력을 높여줍니다."
            )
            quick_replies = [
                {"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"},
                {"label": "➡️ 3단계(미션)로", "action": "message", "messageText": "다음 단계"}
            ]
            
        elif step == 3:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎙️ **Step 3: 실전 응용 미션**\n\n"
                f"방금 학습한 표현들을 활용하여 본인만의 실무 문장을 직접 작성해서 보내주세요!\n\n"
                f"✍️ 채팅창에 문장을 입력하시면 즉시 분석 피드백을 제공합니다."
                f"{feedback_text}"
            )
            quick_replies = [
                {"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"},
                {"label": "➡️ 4단계(완료)로", "action": "message", "messageText": "다음 단계"}
            ]
            
        elif step == 4:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎉 **Step 4: 학습 완료 & 성취도 점검**\n\n"
                f"오늘 준비한 모든 학습 단계를 완벽하게 클리어하셨습니다! 수고 많으셨습니다. 👏"
            )
            session["step"] = 0
            session["lang"] = None
            session["level"] = None
            session["topic"] = None
            quick_replies = [{"label": "🔄 처음부터 다시하기", "action": "message", "messageText": "처음으로"}]
            
        else:
            session["step"] = 1
            text = "🚀 학습을 다시 시작합니다!"
            quick_replies = [{"label": "다음 단계", "action": "message", "messageText": "다음 단계"}]

        return JSONResponse(content={
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": text}}],
                "quickReplies": quick_replies
            }
        })

    except Exception as e:
        return JSONResponse(content={
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": "앗, 처리 중 작은 오류가 발생했어요. 잠시 후 다시 시도해 주세요!"}}]
            }
        })

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<html><body><h2>챗봇 서버 정상 작동 중</h2></body></html>"

@app.get("/health")
async def health_check():
    return "OK"
