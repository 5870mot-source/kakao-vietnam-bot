import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import httpx

app = FastAPI()

# Groq API 키 설정
GROQ_API_KEY = "Gsk_GI1m4hspv6VtDgtxRyVTWGdyb3FYkx00NSwnIV7nxd0LvhRaNYtp"

# 사용자별 세션 저장소 (어종, 난이도, 주제, 현재 단계 관리)
user_sessions = {}

# --- [1] 카카오톡 챗봇 스킬 엔드포인트 (/api/kakao) ---
@app.post("/api/kakao")
async def kakao_skill(request: Request):
    try:
        body = await request.json()
        user_id = body.get("userRequest", {}).get("user", {}).get("id", "default_user")
        user_message = body.get("userRequest", {}).get("utterance", "").strip()

        # 세션 초기화 또는 처음으로 돌아갈 때
        if user_id not in user_sessions or "처음" in user_message or "처음으로" in user_message:
            user_sessions[user_id] = {"language": None, "level": None, "topic": None, "step": 0}

        session = user_sessions[user_id]

        # [단계 1] 언어(어종) 선택
        if not session["language"]:
            if user_message in ["영어", "베트남어"]:
                session["language"] = user_message
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [{
                            "simpleText": {
                                "text": f"🎯 **{session['language']}**를 선택하셨네요!\n\n이어 원하시는 **난이도**를 선택해 주세요."
                            }
                        }]
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
                        "outputs": [{
                            "simpleText": {
                                "text": "👋 환영합니다! 지루하지 않고 재밌는 맞춤형 어학 학습을 시작해볼까요?\n\n먼저 학습할 **언어(어종)**를 선택해 주세요!"
                            }
                        }]
                    },
                    "quickReplies": [
                        {"label": "영어 (English)", "action": "message", "messageText": "영어"},
                        {"label": "베트남어 (Tiếng Việt)", "action": "message", "messageText": "베트남어"}
                    ]
                }

        # [단계 2] 난이도 선택
        if not session["level"]:
            if user_message in ["초급", "중급", "고급"]:
                session["level"] = user_message
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [{
                            "simpleText": {
                                "text": f"✨ [{session['language']} / {session['level']}] 난이도가 설정되었습니다!\n\n이제 집중해서 학습할 **세부 주제**를 선택해 주세요."
                            }
                        }]
                    },
                    "quickReplies": [
                        {"label": "💼 비즈니스 & 협상", "action": "message", "messageText": "비즈니스 회화"},
                        {"label": "☕ 일상 & 네트워킹", "action": "message", "messageText": "일상 대화"}
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

        # [단계 3] 주제 선택
        if not session["topic"]:
            if user_message in ["비즈니스 회화", "일상 대화"]:
                session["topic"] = user_message
                session["step"] = 1  # 주제 선정 완료 후 1단계 학습 본격 시작!
            else:
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "버튼을 눌러 학습 주제를 선택해 주세요!"}}],
                        "quickReplies": [
                            {"label": "💼 비즈니스 & 협상", "action": "message", "messageText": "비즈니스 회화"},
                            {"label": "☕ 일상 & 네트워킹", "action": "message", "messageText": "일상 대화"}
                        ]
                    }
                }

        # [단계 4] 스텝 바이 스텝 커리큘럼 진행 (1단계 ~ 4단계)
        if "다음 단계" in user_message:
            session["step"] += 1

        step = session["step"]
        lang = session["language"]
        lvl = session["level"]
        top = session["topic"]

        # 단계별 풍부한 학습 내용 구성
        if step == 1:
            text = (
                f"📚 [{lang} / {lvl} / {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 **Step 1: 핵심 오프닝 & 시그니처 패턴**\n\n"
                f"원어민이 미팅이나 대화 시작할 때 가장 자주 쓰는 알짜배기 표현입니다.\n\n"
                f"💬 **Core Expression:**\n"
                f"• *Let's get down to business.* (본론으로 들어갑시다.)\n\n"
                f"💡 **Tip:** 격식 있는 자리나 회의 시작 직후 분위기를 전환할 때 유용하게 쓰입니다."
            )
            quick_replies = [{"label": "➡️ 2단계로 넘어가기", "action": "message", "messageText": "다음 단계"}]
            
        elif step == 2:
            text = (
                f"📚 [{lang} / {lvl} / {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🛡️ **Step 2: 리스크 방어 & 설득 어휘**\n\n"
                f"실전 비즈니스 및 상황별 대처 능력을 키워주는 심화 표현입니다.\n\n"
                f"💬 **Advanced Vocab:**\n"
                f"• *Mitigate the risk* (위험을 완화하다)\n"
                f"• *Supply chain disruption* (공급망 차단)\n\n"
                f"💡 **Tip:** 문제가 생겼을 때 상대방을 안심시키고 대안을 제시할 때 꼭 필요한 표현입니다."
            )
            quick_replies = [
                {"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"},
                {"label": "➡️ 3단계(미션)로", "action": "message", "messageText": "다음 단계"}
            ]
            
        elif step == 3:
            text = (
                f"📚 [{lang} / {lvl} / {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🎙️ **Step 3: 음성 및 텍스트 실전 미션**\n\n"
                f"방금 배운 표현을 활용해 나만의 문장을 직접 작성해서 보내보세요!\n"
                f"*(Groq AI가 문장을 분석해 자연스러운 피드백을 드립니다.)*"
            )
            quick_replies = [
                {"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"},
                {"label": "➡️ 4단계(퀴즈)로", "action": "message", "messageText": "다음 단계"}
            ]
            
        elif step == 4:
            text = (
                f"📚 [{lang} / {lvl} / {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🎉 **Step 4: 마무리 퀴즈 & 성취도 확인**\n\n"
                f"오늘 준비한 모든 스텝을 완벽하게 클리어하셨습니다! 정말 수고 많으셨습니다 수강생님. 👏"
            )
            session["step"] = 0  # 초기화 준비
            session["language"] = None
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


# --- [2] 웹 대시보드 인터페이스 (브라우저 접속용) ---
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


# --- [3] 크론잡 유지용 헬스체크 엔드포인트 ---
@app.get("/health")
async def health_check():
    return "OK"
