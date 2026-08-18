import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from groq import Groq

app = FastAPI()

# Groq 클라이언트 설정
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
                session["quiz_started"] = False # 4단계 진입 시 퀴즈 초기화
        elif "이전 단계" in user_message:
            if session["step"] > 1:
                session["step"] -= 1
                session["quiz_started"] = False

        step = session["step"]
        lang = session["lang"]
        lvl = session["level"]
        top = session["topic"]

        # ==========================================
        # [Step 3] 텍스트 및 음성(녹음) 파일 분석 처리
        # ==========================================
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
                    feedback_text += f"\n🎙️ **[음성 인식 결과 (STT)]**\n\"{user_input_to_analyze}\"\n"
                    
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
            except Exception:
                feedback_text += "\n(음성 파일 처리 중 오류가 발생했습니다. 텍스트로 다시 시도해 주세요.)"

        if step == 3 and user_input_to_analyze not in ["다음 단계", "이전 단계", top] and len(user_input_to_analyze) > 1:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"당신은 {lang} 전문 원어민 비즈니스 튜터입니다. 사용자가 실무 상황([{top}], 난이도: {lvl})에서 구사한 문장을 분석하여 문법적 오류 교정과 더 자연스러운 표현을 한국어로 피드백해주세요."
                        },
                        {
                            "role": "user",
                            "content": user_input_to_analyze
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                )
                ai_feedback = chat_completion.choices[0].message.content
                feedback_text += f"\n🤖 **[AI 튜터 실시간 교정 피드백]**\n{ai_feedback}\n"
            except Exception:
                feedback_text += "\n\n(AI 피드백 생성 중 일시적인 지연이 발생했습니다.)"

        # ==========================================
        # [Step 4] 실전 미니 게임 (퀴즈 & 채점) 처리
        # ==========================================
        game_text = ""
        if step == 4:
            # 사용자가 퀴즈 답을 입력했거나 게임 진행 중인 경우 채점
            if session.get("quiz_started") and user_message not in ["다음 단계", "이전 단계", "처음으로", "🔄 다시 풀기"]:
                try:
                    grade_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": f"당신은 {lang} 어학 퀴즈 마스터입니다. 방금 출제된 학습 주제([{top}], 난이도: {lvl}) 퀴즈에 대해 사용자가 입력한 답변('{user_message}')이 맞았는지 틀렸는지 친절하게 채점하고 해설을 한국어로 제공해주세요."
                            }
                        ],
                        model="llama-3.3-70b-versatile",
                    )
                    game_text = f"\n🎯 **[채점 결과]**\n{grade_completion.choices[0].message.content}\n"
                except Exception:
                    game_text = "\n(채점 중 오류가 발생했습니다.)"
            else:
                # 새로운 퀴즈 출제
                try:
                    quiz_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": f"당신은 {lang} 어학 퀴즈 마스터입니다. [{top}] 상황(난이도: {lvl})에서 학습한 내용을 바탕으로, 사용자가 가볍게 풀 수 있는 객관식 또는 단답형 실무 퀴즈 1문제를 한국어 설명과 함께 출제해주세요."
                            }
                        ],
                        model="llama-3.3-70b-versatile",
                    )
                    game_text = f"\n🎮 **[Step 4: 실전 퀴즈 미니 게임]**\n{quiz_completion.choices[0].message.content}\n\n✍️ 정답을 채팅창에 입력해 주세요!"
                    session["quiz_started"] = True
                except Exception:
                    game_text = "\n🎮 **[Step 4: 실전 미니 게임]**\n퀴즈를 불러오는 중입니다. 아무 텍스트나 입력해 정답을 맞춰보세요!"
                    session["quiz_started"] = True

        # ==========================================
        # 1단계 & 2단계 콘텐츠 매핑
        # ==========================================
        step1_content_map = {
            ("영어", "고급", "비즈니스 미팅"): {
                "expr": "• *\"Let's pivot our focus to the structural implications and long-term ROI of this proposal.\"*\n  (이 제안의 구조적 영향과 장기적 투자 수익률 쪽으로 논의의 초점을 전환해 봅시다.)",
                "dialogue": "A: We're running out of time on minor budget details.\nB: Agreed. Let's pivot our focus to the structural implications.",
                "tip": "'Pivot'은 회의에서 생산적인 논의 주제로 자연스럽게 유도할 때 쓰는 최고급 비즈니스 패턴입니다."
            },
            ("영어", "고급", "여행 회화"): {
                "expr": "• *\"I'd like to request an upgrade to a higher category room, and I'm fully willing to cover any incidental rate difference.\"*\n  (상위 객실로 업그레이드를 요청하고 싶으며, 발생하는 차액은 전적으로 지불하겠습니다.)",
                "dialogue": "Clerk: Standard rooms are fully booked.\nGuest: I understand. I'd like to request an upgrade...",
                "tip": "단순 요구가 아닌 차액 지불 의사를 먼저 밝힘으로써 호텔 프론트 매니저의 적극적인 재량 협조를 이끌어내는 세련된 화법입니다."
            }
        }
        
        step2_content_map = {
            ("영어", "고급", "비즈니스 미팅"): {
                "vocab": "1. **Mitigate the potential risk** (잠재적 리스크를 완화하다)\n2. **Stakeholder alignment** (이해관계자 간 의견 조율)\n3. **Bottleneck resolution** (병목 현상 해소)",
                "tip": "고급 회의에서는 감정적인 주장보다 위와 같은 리스크 관리 및 구조적 용어를 사용하여 설득력을 극대화해야 합니다."
            },
            ("영어", "고급", "여행 회화"): {
                "vocab": "1. **Complimentary amenity** (무료 편의용품/서비스)\n2. **Incidental charges** (부대 비용)\n3. **Flexibility in policy** (정책적 유연성)",
                "tip": "호텔이나 공항 등 프리미엄 서비스 환경에서 서비스 요건을 명확히 할 때 필수적으로 쓰이는 어휘들입니다."
            }
        }

        default_step1 = {
            "expr": f"• *\"Let's streamline our approach regarding this core objective.\"*\n  (본 핵심 목표와 관련하여 접근 방식을 효율화합시다.)",
            "dialogue": "A: How should we proceed?\nB: Let's streamline our approach.",
            "tip": "실무에서 명확하고 전문적인 리더십 뉘앙스를 전달하는 표준 패턴입니다."
        }
        default_step2 = {
            "vocab": "1. **Optimize operational efficiency** (운영 효율성을 최적화하다)\n2. **Strategic execution** (전략적 실행)\n3. **Seamless integration** (원활한 통합)",
            "tip": "어떤 상황에서도 프로페셔널한 인상을 주는 필수 비즈니스 어휘 세트입니다."
        }

        curr_step1 = step1_content_map.get((lang, lvl, top), default_step1)
        curr_step2 = step2_content_map.get((lang, lvl, top), default_step2)

        # 각 스텝별 텍스트 및 버튼 구성
        if step == 1:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 **Step 1: 핵심 오프닝 & 시그니처 패턴**\n\n"
                f"해당 상황에서 고급 원어민이 가장 즐겨 쓰는 알짜배기 핵심 표현입니다.\n\n"
                f"💬 **Core Expression:**\n"
                f"{curr_step1['expr']}\n\n"
                f"👥 **Mini Dialogue (실무 예문):**\n"
                f"{curr_step1['dialogue']}\n\n"
                f"💡 **Professional Tip:**\n"
                f"{curr_step1['tip']}"
            )
            quick_replies = [{"label": "➡️ 2단계(심화 어휘)로", "action": "message", "messageText": "다음 단계"}]
            
        elif step == 2:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🛡️ **Step 2: 리스크 방어 & 설득 어휘**\n\n"
                f"표현력을 대폭 끌어올려 주는 고품격 전문 어휘입니다.\n\n"
                f"📖 **Advanced Vocabulary:**\n"
                f"{curr_step2['vocab']}\n\n"
                f"💡 **Usage Tip:**\n"
                f"{curr_step2['tip']}"
            )
            quick_replies = [
                {"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"},
                {"label": "➡️ 3단계(실전 미션)로", "action": "message", "messageText": "다음 단계"}
            ]
            
        elif step == 3:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎙️ **Step 3: 실전 응용 미션 (텍스트 & 음성 녹음 지원)**\n\n"
                f"방금 학습한 표현들을 활용하여 본인만의 실무 문장을 **직접 타이핑**하시거나, **카카오톡 음성 녹음(오디오)**으로 보내주세요!\n\n"
                f"✍️ 보내주신 내용(텍스트/음성)을 분석하여 네이티브 교정 피드백을 즉시 제공합니다."
                f"{feedback_text}"
            )
            quick_replies = [
                {"label": "⬅️ 이전", "action": "message", "messageText": "이전 단계"},
                {"label": "➡️ 4단계(미니 게임)로", "action": "message", "messageText": "다음 단계"}
            ]
            
        elif step == 4:
            text = (
                f"📚 [{lang} | {lvl} | {top}]\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{game_text}\n\n"
                f"🎉 퀴즈를 풀고 나면 언제든 처음으로 돌아가 다른 주제를 학습할 수 있습니다!"
            )
            quick_replies = [
                {"label": "⬅️ 이전 단계", "action": "message", "messageText": "이전 단계"},
                {"label": "🔄 처음부터 다시하기", "action": "message", "messageText": "처음으로"}
            ]
            
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
                "outputs": [{"simpleText": {"text": "앗, 처리 중 작은 오류가 발생했어요. 잠시 후 '처음'을 입력해 재시도해 주세요!"}}]
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
