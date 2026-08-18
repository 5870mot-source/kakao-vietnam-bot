import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from groq import Groq

app = FastAPI()

# Groq 클라이언트 설정
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# 사용자별 세션 저장소
user_sessions = {}

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

        if user_id not in user_sessions or "처음" in user_message or "처음으로" in user_message or "오늘의 학습 시작" in user_message:
            user_sessions[user_id] = {"lang": None, "level": None, "topic": None, "step": 0}
        
        session = user_sessions[user_id]

        # 1단계: 언어 선택
        if not session["lang"]:
            if "영어" in user_message: session["lang"] = "영어"
            elif "베트남어" in user_message: session["lang"] = "베트남어"

            if session["lang"]:
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": f"🎯 **{session['lang']}**를 선택하셨습니다!\n\n이어 원하시는 **난이도**를 선택해 주세요."}}],
                        "quickReplies": [{"label": l, "action": "message", "messageText": l} for l in ["초급", "중급", "고급"]]
                    }
                })
            else:
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "👋 환영합니다! 학습할 **언어**를 선택해 주세요."}}],
                        "quickReplies": [{"label": "영어", "action": "message", "messageText": "영어"}, {"label": "베트남어", "action": "message", "messageText": "베트남어"}]
                    }
                })

        # 2단계: 난이도 선택
        if not session["level"]:
            if any(lvl in user_message for lvl in ["초급", "중급", "고급"]):
                session["level"] = next(lvl for lvl in ["초급", "중급", "고급"] if lvl in user_message)
            
            if session["level"]:
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": f"✨ [{session['lang']} / {session['level']}] 난이도가 설정되었습니다!\n\n학습하실 **주제**를 아래 버튼에서 선택해 주세요."}}],
                        "quickReplies": [{"label": t, "action": "message", "messageText": t} for t in TOPICS_8]
                    }
                })

        # 3단계: 주제 선정
        if not session["topic"]:
            matched_topic = next((t for t in TOPICS_8 if t in user_message), None)
            if matched_topic:
                session["topic"] = matched_topic
                session["step"] = 1

        # 스텝 이동
        if "다음 단계" in user_message: session["step"] = min(session["step"] + 1, 4)
        elif "이전 단계" in user_message: session["step"] = max(session["step"] - 1, 1)

        step, lang, lvl, top = session["step"], session["lang"], session["level"], session["topic"]

        # AI 피드백 처리 (Groq)
        feedback_text = ""
        if step == 3 and user_message not in ["다음 단계", "이전 단계", top] and len(user_message) > 1 and client:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": f"당신은 {lang} 전문 원어민 튜터입니다. 사용자가 작성한 문장을 교정하고 피드백을 한국어로 제공해주세요."},
                        {"role": "user", "content": user_message}
                    ],
                    model="llama-3.3-70b-versatile",
                )
                feedback_text = f"\n\n🤖 **[AI 튜터 실시간 교정 피드백]**\n{chat_completion.choices[0].message.content}"
            except Exception:
                feedback_text = "\n\n(AI 피드백 생성 중 일시적인 지연이 발생했습니다.)"

        # 각 단계별 풍부한 학습 콘텐츠 매핑
        step1_contents = {
            ("영어", "고급", "비즈니스 미팅"): "• *\"Let's pivot our focus to the structural implications of this proposal.\"*\n(이 제안의 구조적 영향 쪽으로 논의의 초점을 전환해 봅시다.)\n\n💡 **Tip:** 'Pivot'을 사용하여 회의 주도권을 잡는 고급 표현입니다.",
            ("영어", "고급", "여행 회화"): "• *\"I'd like to request an upgrade, and I'm willing to cover the rate difference.\"*\n(업그레이드를 요청하며 차액은 지불하겠습니다.)\n\n💡 **Tip:** 프론트 매니저를 공손하게 설득하는 프로페셔널 화법입니다."
        }
        default_step1 = "• *\"Let's streamline our approach regarding this core objective.\"*\n(본 핵심 목표와 관련하여 접근 방식을 효율화합시다.)\n\n💡 **Tip:** 실무에서 명확한 뉘앙스를 전달하는 표준 패턴입니다."

        step2_contents = {
            ("영어", "고급", "비즈니스 미팅"): "1. **Mitigate the potential risk** (잠재적 리스크 완화)\n2. **Stakeholder alignment** (이해관계자 간 의견 조율)\n3. **Bottleneck resolution** (병목 현상 해소)",
            ("영어", "고급", "여행 회화"): "1. **Complimentary amenity** (무료 편의용품/서비스)\n2. **Incidental charges** (부대 비용)\n3. **Flexibility in policy** (정책적 유연성)"
        }
        default_step2 = "1. **Optimize operational efficiency** (운영 효율성 최적화)\n2. **Strategic execution** (전략적 실행)\n3. **Seamless integration** (원활한 통합)"

        curr_s1 = step1_contents.get((lang, lvl, top), default_step1)
        curr_s2 = step2_contents.get((lang, lvl, top), default_step2)

        # 단계별 텍스트 및 버튼 구성
        if step == 1:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 **Step 1: 핵심 오프닝 & 시그니처 패턴**\n\n"
                f"{curr_s1}"
            )
            replies = [{"label": "➡️ 2단계(심화 어휘)로", "action": "message", "messageText": "다음 단계"}]
            
        elif step == 2:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🛡️ **Step 2: 리스크 방어 & 설득 어휘**\n\n"
                f"{curr_s2}\n\n"
                f"💡 어휘를 조합하여 나만의 문장을 구상해 보세요!"
            )
            replies = [
                {"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"}, 
                {"label": "➡️ 3단계(실전 미션)로", "action": "message", "messageText": "다음 단계"}
            ]
            
        elif step == 3:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎙️ **Step 3: 실전 응용 미션**\n\n"
                f"방금 학습한 표현들을 활용해 본인만의 실무 문장을 직접 입력해 주세요!\n\n"
                f"✍️ 채팅창에 문장을 보내시면 즉시 피드백을 드립니다."
                f"{feedback_text}"
            )
            replies = [
                {"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"}, 
                {"label": "➡️ 4단계(완료)로", "action": "message", "messageText": "다음 단계"}
            ]
            
        elif step == 4:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎉 **Step 4: 학습 완료 & 성취도 점검**\n\n"
                f"오늘 준비한 모든 학습 단계를 완벽하게 클리어하셨습니다! 👏\n"
                f"꾸준한 실전 연습이 유창성을 만듭니다."
            )
            session.update({"step": 0, "lang": None, "level": None, "topic": None})
            replies = [{"label": "🔄 처음부터 다시하기", "action": "message", "messageText": "처음으로"}]
            
        else:
            text, replies = "학습을 시작합니다.", [{"label": "다음 단계", "action": "message", "messageText": "다음 단계"}]

        return JSONResponse(content={"version": "2.0", "template": {"outputs": [{"simpleText": {"text": text}}], "quickReplies": replies}})
    except Exception as e:
        return JSONResponse(content={"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "오류가 발생했습니다. '처음'을 입력해 재시작해주세요."}}]}})

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h2>🚀 서버 정상 작동 중</h2>"

@app.get("/health")
async def health_check():
    return "OK"
