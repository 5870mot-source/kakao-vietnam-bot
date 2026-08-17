from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from groq import Groq
import os

app = FastAPI()

client = Groq(api_key="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")

# 사용자별 상태 관리 (언어, 단계 저장)
user_states = {}

@app.post('/api/kakao')
async def kakao_webhook(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()
    
    if user_id not in user_states:
        user_states[user_id] = {"step": "IDLE", "lang": "베트남어"}

    state = user_states[user_id]["step"]
    current_lang = user_states[user_id]["lang"]

    # 1. 언어 변경 메뉴 선택 시
    if "언어 변경" in utterance:
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"🌐 [현재 설정된 언어: {current_lang}]\n\n변경하고 싶은 언어를 선택해 주세요!"
                        }
                    }
                ],
                "quickReplies": [
                    {"label": "🇻🇳 베트남어", "action": "message", "messageText": "언어:베트남어"},
                    {"label": "🇺🇸 영어", "action": "message", "messageText": "언어:영어"},
                    {"label": "🇯🇵 일본어", "action": "message", "messageText": "언어:일본어"}
                ]
            }
        }

    # 2. 특정 언어로 설정 변경 처리
    if utterance.startswith("언어:"):
        selected_lang = utterance.split(":")[1]
        user_states[user_id]["lang"] = selected_lang
        user_states[user_id]["step"] = "IDLE"
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"✨ 학습 언어가 **[{selected_lang}]**로 변경되었습니다!\n\n이제 원어민 튜터와 함께 실전 회화 훈련을 시작해 볼까요?"
                        }
                    }
                ],
                "quickReplies": [
                    {"label": "🚀 훈련 시작하기", "action": "message", "messageText": "오늘 학습 시작"},
                    {"label": "🌐 언어 변경", "action": "message", "messageText": "언어 변경"}
                ]
            }
        }

    # 3. 학습 시작 요청 (선택된 언어에 맞춰 미션 출제)
    if "학습 시작" in utterance or "시작" in utterance:
        user_states[user_id]["step"] = "WAITING_ANSWER"
        
        # 언어별 맞춤형 미션 샘플 설정
        missions = {
            "베트남어": "🏢 상황: 거래처와의 미팅 일정을 긴급히 내일로 연기해야 합니다.\n💡 필수 표현: \"Xin vui lòng hoãn...\" (연기해 주세요)",
            "영어": "🏢 상황: 상사에게 프로젝트 마감 기한을 이틀만 연장해 달라고 정중히 요청하세요.\n💡 필수 표현: \"Could you possibly extend...\"",
            "일본어": "🏢 상황: 거래처 담당자에게 회의 일정을 변경해 달라고 정중하게 전화로 요청하세요.\n💡 필수 표현: \"日程を変更していただけますでしょうか。\""
        }
        mission_text = missions.get(current_lang, missions["베트남어"])

        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"📌 [ 오늘의 실전 롤플레잉 미션 ({current_lang}) ]\n\n{mission_text}\n\n🎯 실제 원어민에게 말하듯 해당 언어로 답변을 작성해 전송해 주세요!"
                        }
                    }
                ],
                "quickReplies": [
                    {"label": "🌐 언어 변경", "action": "message", "messageText": "언어 변경"}
                ]
            }
        }

    # 4. 학습자 답변 분석 및 원어민식 피드백 제공
    if state == "WAITING_ANSWER" and utterance and not utterance.startswith("언어:"):
        
        # AI 프롬프트 (선택된 언어의 원어민 튜터 모드)
        prompt = f"""
        당신은 전문 {current_lang} 원어민 채점관이자 다정한 멘토입니다.
        학습자가 미션에 대해 다음과 같이 답변했습니다: "{utterance}"
        
        다음 구조로 카카오톡 말풍선에 맞게 피드백을 작성해 주세요:
        1. 👏 원어민식 리액션 (선택된 {current_lang}로 짧고 자연스러운 현지어 반응을 먼저 적어주고 한국어 뜻을 적어주세요)
        2. 🌟 추천 비즈니스 표현 (학습자의 문장을 더 정중하고 자연스러운 원어민 표현으로 교정)
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

        user_states[user_id]["step"] = "COMPLETED"

        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"📊 [ {current_lang} AI 맞춤형 코칭 리포트 ]\n\n{feedback_result}"
                        }
                    }
                ],
                "quickReplies": [
                    {"label": "🔄 다른 미션 도전", "action": "message", "messageText": "오늘 학습 시작"},
                    {"label": "🌐 언어 변경", "action": "message", "messageText": "언어 변경"}
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
                        "text": f"👋 다국어 비즈니스 원어민 튜터 봇입니다.\n현재 설정된 언어: **[{current_lang}]**\n\n버튼을 눌러 훈련을 시작하거나 언어를 변경해 보세요."
                    }
                }
            ],
            "quickReplies": [
                {"label": "🚀 오늘 학습 시작", "action": "message", "messageText": "오늘 학습 시작"},
                {"label": "🌐 언어 변경", "action": "message", "messageText": "언어 변경"}
            ]
        }
    }
