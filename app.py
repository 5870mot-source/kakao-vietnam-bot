from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from groq import Groq
import os

app = FastAPI()

# Groq API 설정 (본인 API 키 입력)
client = Groq(api_key="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")

# 사용자별 학습 상태 관리 메모리
user_states = {}

@app.post('/api/kakao')
async def kakao_webhook(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()
    
    if user_id not in user_states:
        user_states[user_id] = {"step": "IDLE", "lang": "베트남어"}

    state = user_states[user_id]["step"]

    # 1. 학습 시작 요청 (1단계: 미션 및 필수 표현 인풋 제공)
    if "학습 시작" in utterance or "시작" in utterance or "처음" in utterance:
        user_states[user_id]["step"] = "WAITING_ANSWER"
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "📌 [ 오늘의 비즈니스 롤플레잉 미션 ]\n\n"
                                    "🏢 상황: 거래처와의 미팅 일정을 긴급히 내일로 연기해야 합니다.\n\n"
                                    "💡 핵심 필수 패턴:\n"
                                    "• \"Xin vui lòng hoãn...\" (연기해 주세요)\n\n"
                                    "🎯 미션: 실제 거래처 담당자에게 말하듯 "
                                    "해당 내용을 포함하여 답변을 작성해 텍스트(또는 음성 메시지)로 전송해 주세요!"
                        }
                    }
                ],
                "quickReplies": [
                    {"label": "💡 예시 답변 보기", "action": "message", "messageText": "예시 답변 보기"}
                ]
            }
        }

    # 2. 예시 답변 보기 요청 시
    if utterance == "예시 답변 보기":
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "💡 [모범 예시 표현]\n\n"
                                    "\"Chào anh, xin vui lòng hoãn cuộc họp sang ngày mai giúp tôi nhé.\"\n"
                                    "(안녕하세요, 회의를 내일로 연기해 주시기 바랍니다.)\n\n"
                                    "👉 이 표현을 참고하여 본인만의 문장으로 답변을 보내보세요!"
                        }
                    }
                ]
            }
        }

    # 3. 학습자의 답변을 받아 AI 심층 코칭 및 납득형 피드백 제공 (3단계)
    if state == "WAITING_ANSWER" and utterance and utterance != "예시 답변 보기":
        
        # AI 코칭 프롬프트 (OPIc/SJPT 채점관 페르소나)
        prompt = f"""
        당신은 전문 외국어(베트남어) OPIc/SJPT 채점관이자 다정한 비즈니스 멘토입니다.
        학습자가 미션에 대해 다음과 같이 답변했습니다: "{utterance}"
        
        다음 3가지 요소를 포함하여 카카오톡 말풍선에 어울리도록 깔끔하고 친절하게 피드백을 작성해 주세요:
        1. 👏 잘한 점 (칭찬과 격려)
        2. 🌟 추천 비즈니스 표현 (학습자의 문장을 더 정중하고 자연스러운 원어민 비즈니스 표현으로 교정)
        3. 💡 납득 포인트 (왜 이렇게 고쳐야 하는지 문화적/문법적 이유를 명쾌하게 설명)
        """

        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            feedback_result = completion.choices[0].message.content
        except Exception as e:
            feedback_result = "AI 분석 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요!"

        # 학습 완료 상태로 변경
        user_states[user_id]["step"] = "COMPLETED"

        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"📊 [ AI 맞춤형 코칭 리포트 ]\n\n{feedback_result}"
                        }
                    }
                ],
                "quickReplies": [
                    {"label": "🔄 심화 미션 도전하기", "action": "message", "messageText": "오늘 학습 시작"},
                    {"label": "📚 처음으로", "action": "message", "messageText": "시작"}
                ]
            }
        }

    # 기본 안내 화면
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "👋 비즈니스 원어민 튜터 봇에 오신 것을 환영합니다!\n\n"
                                "버튼을 눌러 오늘 하루의 실전 회화 훈련을 시작해 보세요."
                    }
                }
            ],
            "quickReplies": [
                {"label": "🚀 오늘 학습 시작", "action": "message", "messageText": "오늘 학습 시작"}
            ]
        }
    }
