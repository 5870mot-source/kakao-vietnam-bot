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
                feedback_text = f"\n\n🤖 **[AI 피드백]**\n{chat_completion.choices[0].message.content}"
            except Exception:
                pass

        # 단계별 텍스트 출력
        if step == 1:
            text = f"📚 [{lang} | {lvl} | {top}]\n━━━━━━━━━━━━\n🔥 **Step 1: 핵심 표현**\n\n- 실무에서 가장 자주 쓰이는 핵심 패턴입니다."
            replies = [{"label": "➡️ 2단계로", "action": "message", "messageText": "다음 단계"}]
        elif step == 2:
            text = f"📚 [{lang} | {lvl} | {top}]\n━━━━━━━━━━━━\n🛡️ **Step 2: 심화 어휘**\n\n- 전문성을 높여주는 고급 어휘를 학습합니다."
            replies = [{"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"}, {"label": "➡️ 3단계로", "action": "message", "messageText": "다음 단계"}]
        elif step == 3:
            text = f"📚 [{lang} | {lvl} | {top}]\n━━━━━━━━━━━━\n🎙️ **Step 3: 실전 미션**\n\n문장을 입력해 피드백을 받아보세요!{feedback_text}"
            replies = [{"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"}, {"label": "➡️ 4단계로", "action": "message", "messageText": "다음 단계"}]
        elif step == 4:
            text = f"📚 [{lang} | {lvl} | {top}]\n━━━━━━━━━━━━\n🎉 **Step 4: 학습 완료!**\n오늘의 학습을 성공적으로 마쳤습니다."
            session.update({"step": 0, "lang": None, "level": None, "topic": None})
            replies = [{"label": "🔄 처음으로", "action": "message", "messageText": "처음으로"}]
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
