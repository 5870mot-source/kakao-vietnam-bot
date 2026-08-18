import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import httpx

app = FastAPI()

# Groq API 키 설정
GROQ_API_KEY = "Gsk_GI1m4hspv6VtDgtxRyVTWGdyb3FYkx00NSwnIV7nxd0LvhRaNYtp"

# 사용자별 세션 저장소 (어종, 난이도, 현재 단계 관리)
user_sessions = {}

# --- [1] 카카오톡 챗봇 스킬 엔드포인트 (/api/kakao) ---
@app.post("/api/kakao")
async def kakao_skill(request: Request):
    try:
        body = await request.json()
        user_id = body.get("userRequest", {}).get("user", {}).get("id", "default_user")
        user_message = body.get("userRequest", {}).get("utterance", "").strip()

        # 세션이 없거나 '처음'을 원할 때 초기화
        if user_id not in user_sessions or "처처음" in user_message or "처음으로" in user_message:
            user_sessions[user_id] = {"language": None, "level": None, "step": 0}

        session = user_sessions[user_id]

        # 1단계: 언어(어종) 선택이 안 되어 있다면 언어 선택지로 유도
        if not session["language"]:
            if user_message in ["영어", "베트남어"]:
                session["language"] = user_message
                return {
                    "version": "2.0",
                    "template": {
                        "outputs": [
                            {
                                "simpleText": {
                                    "text": f"🎯 **{session['language']}**를 선택하셨네요!\n\n원하시는 **난이도**를 선택해 주세요."
                                }
                            }
                        ]
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
                        "outputs": [
                            {
                                "simpleText": {
                                    "text": "👋 환영합니다! 지루하지 않고 재밌는 맞춤형 어학 학습을 시작해볼까요?\n\n먼저 학습할 **언어(어종)**를 선택해 주세요!"
                                }
                            }
                        ]
                    },
                    "quickReplies": [
                        {"label": "영어 (English)", "action": "message", "messageText": "영어"},
                        {"label": "베트남어 (Tiếng Việt)", "action": "message", "messageText": "베트남어"}
                    ]
                }

        # 2단계: 난이도가 선택되지 않았다면 난이도 저장 후 1단계 학습 시작
        if not session["level"]:
            if user_message in ["초급", "중급", "고급"]:
                session["level"] = user_message
                session["step"] = 1 # 1단계 진입
            else:
                # 난이도 입력이 잘못되었을 경우 다시 유도
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

        # 3단계: 스텝 바이 스텝 커리큘럼 진행 (1단계 ~ 4단계)
        if "다음 단계" in user_message:
            session["step"] += 1

        step = session["step"]
        lang = session["language"]
        lvl = session["level"]

        # 단계별 시각적 구성 및 콘텐츠
        if step == 1:
            text = f"📚 [{lang} / {lvl}] **Step 1: 핵심 오프닝 & 시그니처 패턴**\n\n원어민이 가장 자주 쓰는 알짜배기 표현을 익혀보세요!\n\n💬 *'Let's get down to business.'* (본론으로 들어갑시다.)"
            quick_replies = [{"label": "다음 단계로 ➡️", "action": "message", "messageText": "다음 단계"}]
        elif step == 2:
            text = f"🛡️ [{lang} / {lvl}] **Step 2: 리스크 방어 & 설득 어휘**\n\n실전 비즈니스와 상황별 대처 능력을 키워주는 심화 표현입니다.\n\n💬 *'Mitigate the risk.'* (위험을 완화하다.)"
            quick_replies = [{"label": "다음 단계로 ➡️", "action": "message", "messageText": "다음 단계"}]
        elif step == 3:
            text = f"🎙️ [{lang} / {lvl}] **Step 3: 음성/텍스트 미션**\n\n배운 표현을 활용해 나만의 문장을 만들어 챗봇에게 보내보세요! (Groq AI가 멋진 피드백을 드립니다.)"
            quick_replies = [{"label": "다음 단계로 ➡️", "action": "message", "messageText": "다음 단계"}]
        elif step == 4:
            text = f"🎉 [{lang} / {lvl}] **Step 4: 마무리 퀴즈 & 랭킹 확인**\n\n오늘의 학습을 완벽하게 클리어하셨습니다! 정말 수고 많으셨어요 수강생님."
            session["step"] = 0  # 완료 후 초기화 대비
            session["language"] = None
            session["level"] = None
            quick_replies = [{"label": "처음부터 다시하기 🔄", "action": "message", "messageText": "처음으로"}]
        else:
            session["step"] = 1
            text = f"🚀 학습을 다시 시작합니다!"
            quick_replies = [{"label": "다음 단계", "action": "message", "messageText": "다음 단계"}]

        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": text
                        }
                    }
                ]
            },
            "quickReplies": quick_replies
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


# --- [3] 크론잡 유지용 헬스체크 엔드포인트 (응답 최소화) ---
@app.get("/health")
async def health_check():
    return "OK"
