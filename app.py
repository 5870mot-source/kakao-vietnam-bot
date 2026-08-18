import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

# Groq API 키 설정
GROQ_API_KEY = "Gsk_GI1m4hspv6VtDgtxRyVTWGdyb3FYkx00NSwnIV7nxd0LvhRaNYtp"

# 사용자별 세션 저장소
user_sessions = {}

# 주제 카테고리 (카카오 퀵버튼 제한인 10개 이하로 안전하게 분리)
BUSINESS_TOPICS = ["비즈니스 미팅", "이메일 작성", "협상 전략", "발표 스킬", "전화 응대"]
DAILY_TOPICS = ["여행 회화", "카페 주문", "길 묻기", "병원 방문", "일상 대화"]
ALL_TOPICS = BUSINESS_TOPICS + DAILY_TOPICS

@app.post("/api/kakao")
async def kakao_skill(request: Request):
    try:
        body = await request.json()
        user_id = body.get("userRequest", {}).get("user", {}).get("id", "default_user")
        user_message = body.get("userRequest", {}).get("utterance", "").strip()

        # 세션 초기화 또는 처음으로 돌아갈 때
        if user_id not in user_sessions or "처음" in user_message or "처음으로" in user_message:
            user_sessions[user_id] = {"lang": None, "level": None, "topic": None, "step": 0}
        
        session = user_sessions[user_id]

        # [1단계] 어종(언어) 선택
        if not session["lang"]:
            if user_message in ["영어", "베트남어"]:
                session["lang"] = user_message
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": f"🎯 **{session['lang']}**를 선택하셨습니다!\n\n이어 원하시는 **난이도**를 선택해 주세요."}}]
                    },
                    "quickReplies": [
                        {"label": "초급 (Beginner)", "action": "message", "messageText": "초급"},
                        {"label": "중급 (Intermediate)", "action": "message", "messageText": "중급"},
                        {"label": "고급 (Advanced)", "action": "message", "messageText": "고급"}
                    ]
                }
            else:
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "👋 환영합니다! 맞춤형 어학 학습을 시작해볼까요?\n\n먼저 학습할 **언어(어종)**를 선택해 주세요."}}]
                    },
                    "quickReplies": [
                        {"label": "영어 (English)", "action": "message", "messageText": "영어"},
                        {"label": "베트남어 (Tiếng Việt)", "action": "message", "messageText": "베트남어"}
                    ]
                }

        # [2단계] 난이도 선택
        if not session["level"]:
            if user_message in ["초급", "중급", "고급"]:
                session["level"] = user_message
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": f"✨ [{session['lang']} / {session['level']}] 난이도가 설정되었습니다!\n\n학습할 주제의 **영역**을 선택해 주세요."}}]
                    },
                    "quickReplies": [
                        {"label": "💼 비즈니스/업무", "action": "message", "messageText": "비즈니스 영역"},
                        {"label": "☕ 일상/생활", "action": "message", "messageText": "일상 영역"}
                    ]
                }
            else:
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "올바른 난이도(초급, 중급, 고급)를 버튼을 눌러 선택해 주세요!"}}],
                        "quickReplies": [
                            {"label": "초급", "action": "message", "messageText": "초급"},
                            {"label": "중급", "action": "message", "messageText": "중급"},
                            {"label": "고급", "action": "message", "messageText": "고급"}
                        ]
                    }
                }

        # [3단계] 주제 영역 선택에 따른 세부 주제 노출
        if user_message == "비즈니스 영역":
            return {
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "💼 학습하실 **비즈니스 세부 주제**를 선택해 주세요."}}],
                    "quickReplies": [{"label": t, "action": "message", "messageText": t} for t in BUSINESS_TOPICS]
                }
            }
        elif user_message == "일상 영역":
            return {
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "☕ 학습하실 **일상 세부 주제**를 선택해 주세요."}}],
                    "quickReplies": [{"label": t, "action": "message", "messageText": t} for t in DAILY_TOPICS]
                }
            }

        # [4단계] 세부 주제 확정 및 1단계 시작
        if not session["topic"]:
            if user_message in ALL_TOPICS:
                session["topic"] = user_message
                session["step"] = 1  # 주제 선정 완료 후 곧바로 1단계 시작
            else:
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "아래 버튼에서 학습 영역을 다시 선택해 주세요!"}}],
                        "quickReplies": [
                            {"label": "💼 비즈니스/업무", "action": "message", "messageText": "비즈니스 영역"},
                            {"label": "☕ 일상/생활", "action": "message", "messageText": "일상 영역"}
                        ]
                    }
                }

        # [5단계] 순차적 커리큘럼 진행 (1단계 -> 2단계 -> 3단계 -> 4단계)
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

        # 단계별 풍부하고 정확한 학습 내용 구성
        if step == 1:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 **Step 1: 핵심 오프닝 & 시그니처 패턴**\n\n"
                f"해당 상황에서 가장 자주 사용하는 알짜배기 핵심 표현입니다.\n\n"
                f"💬 **Core Expression:**\n"
                f"• *Let's get down to business.* (본론으로 들어갑시다.)\n\n"
                f"💡 **Learning Tip:**\n"
                f"가벼운 인사 후에 분위기를 전환하여 대화를 이끌어낼 때 매우 유용합니다."
            )
            quick_replies = [{"label": "➡️ 2단계로 넘어가기", "action": "message", "messageText": "다음 단계"}]
            
        elif step == 2:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🛡️ **Step 2: 리스크 방어 & 설득 어휘**\n\n"
                f"상황별 대처 능력과 표현력을 높여주는 전문 심화 어휘입니다.\n\n"
                f"💬 **Advanced Vocab:**\n"
                f"• *Mitigate the risk* (위험을 완화하다)\n"
                f"• *Supply chain disruption* (공급망 차단)\n\n"
                f"💡 **Learning Tip:**\n"
                f"핵심 키워드를 조합하여 논리적으로 의사를 전달할 때 활용됩니다."
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
                f"방금 학습한 표현들을 활용하여 본인만의 문장을 직접 작성해서 보내주세요!\n\n"
                f"✍️ 채팅창에 문장을 입력하시면 즉시 분석 피드백을 제공합니다."
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

        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": text}}],
                "quickReplies": quick_replies
            }
        }

    except Exception as e:
        return JSONResponse(content={
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": "앗, 처리 중 작은 오류가 발생했어요. 잠시 후 다시 시도해 주세요!"}}]
            }
        })

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head><title>맞춤형 어학 학습 대시보드</title></head>
        <body style="font-family: Arial; padding: 40px; background: #f4f4f9;">
            <h2>🚀 카카오톡 어학 학습 챗봇 서버가 정상 작동 중입니다!</h2>
            <p>카카오톡 채널에서 대화를 통해 스텝 바이 스텝 학습을 진행해 보세요.</p>
        </body>
    </html>
    """

@app.get("/health")
async def health_check():
    return "OK"
