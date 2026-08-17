from fastapi import FastAPI, Request
from groq import Groq

app = FastAPI()
client = Groq(api_key="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")

# 사용자별 상태 관리 메모리 (언어, 난이도, 현재 진행 단계를 철저히 통제)
user_states = {}

@app.post('/api/kakao')
async def kakao_webhook(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()
    
    # 신규 사용자 초기화 (기본값: 영어, 초급, 대기 상태)
    if user_id not in user_states:
        user_states[user_id] = {"lang": "영어", "level": "초급", "step": "IDLE"}

    state = user_states[user_id]["step"]
    current_lang = user_states[user_id]["lang"]
    current_level = user_states[user_id]["level"]

    # 1. 언어 변경 신호 처리
    if utterance.startswith("언어:"):
        selected_lang = utterance.split(":")[1]
        user_states[user_id]["lang"] = selected_lang
        user_states[user_id]["step"] = "IDLE"
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": f"✨ 학습 언어가 **[{selected_lang}]**(으)로 설정되었습니다.\n\n하단 메뉴나 아래 버튼을 눌러 학습을 시작하세요!"}}],
                "quickReplies": [{"label": "🚀 훈련 시작하기", "action": "message", "messageText": "오늘 학습 시작"}]
            }
        }
    
    # 2. 난이도 변경 신호 처리
    if utterance.startswith("난이도:"):
        selected_level = utterance.split(":")[1]
        user_states[user_id]["level"] = selected_level
        user_states[user_id]["step"] = "IDLE"
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": f"🎯 학습 난이도가 **[{selected_level}]**(으)로 설정되었습니다.\n\n준비되셨다면 훈련을 시작해 보세요!"}}],
                "quickReplies": [{"label": "🚀 훈련 시작하기", "action": "message", "messageText": "오늘 학습 시작"}]
            }
        }

    # 3. [Step 2: 미션 출제] 학습 시작 요청 시
    if "학습 시작" in utterance or "시작" in utterance or "처음" in utterance:
        user_states[user_id]["step"] = "WAITING_ANSWER"
        
        # 난이도와 언어에 따른 맞춤형 미션 예시
        missions = {
            "영어": {
                "초급": "🏢 상황: 상사에게 휴가 일정을 하루 연기해 달라고 간단히 요청하세요.\n💡 힌트: 'Could you change my vacation date?'",
                "중급": "🏢 상황: 프로젝트 마감 기한을 이틀만 연장해 달라고 정중히 메일용 문장으로 작성하세요.",
                "고급": "🏢 상황: 공급망 지연 문제로 인해 클라이언트에게 납기일 연장을 격식 있게 통보하고 양해를 구하세요."
            },
            "일본어": {
                "초급": "🏢 상황: 거래처 담당자에게 내일 미팅 시간을 변경해 달라고 요청하세요.\n💡 힌트: '日程を変更していただけますか。'",
                "중급": "🏢 상황: 회의 지연에 대해 정중하게 사과하고 다음 일정을 조율하세요.",
                "고급": "🏢 상황: 비즈니스 파트너에게 계약 조건 재검토를 완곡하게 제안하세요."
            },
            "베트남어": {
                "초급": "🏢 상황: 거래처와의 미팅 일정을 내일로 연기해 달라고 말하세요.\n💡 힌트: 'Xin vui lòng hoãn...'",
                "중급": "🏢 상황: 공장 자재 수급 지연에 대해 바이어에게 양해를 구하세요.",
                "고급": "🏢 상황: 단가 조정 협상 건으로 긴급 미팅을 제안하세요."
            }
        }
        
        # 안전한 기본값 매핑
        lang_data = missions.get(current_lang, missions["영어"])
        mission_text = lang_data.get(current_level, lang_data["초급"])

        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"📌 [ 실전 커리큘럼 훈련 ]\n\n"
                                    f"🌐 언어: {current_lang} | 📊 난이도: {current_level}\n\n"
                                    f"{mission_text}\n\n"
                                    f"🎯 **실제 원어민에게 말하듯 답변을 입력해 주세요!**"
                        }
                    }
                ]
            }
        }

    # 4. [Step 3 & 4: 답변 수렴 및 AI 피드백 제공]
    if state == "WAITING_ANSWER" and utterance:
        
        # AI 프롬프트 (엄격하고 다정한 원어민 채점관)
        prompt = f"""
        당신은 전문 {current_lang} 원어민 채점관이자 비즈니스 멘토입니다.
        현재 학습자의 난이도는 [{current_level}]입니다.
        학습자가 미션에 대해 다음과 같이 답변했습니다: "{utterance}"
        
        다음 구조로 카카오톡 말풍선에 어울리게 피드백을 작성해 주세요:
        1. 👏 원어민식 리액션 (선택된 {current_lang}로 자연스러운 짧은 현지어 반응과 한국어 뜻)
        2. 🌟 추천 비즈니스 표현 (학습자의 문장을 난이도 [{current_level}]에 맞춰 더 정중하고 자연스러운 원어민 비즈니스 표현으로 교정)
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
            feedback_result = "AI 분석 중 오류가 발생했습니다. 다시 시도해 주세요!"

        # 피드백 제공 후 다시 대기 상태로 전환하여 루프 유지
        user_states[user_id]["step"] = "IDLE"

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
                    {"label": "🔄 다음 미션 도전", "action": "message", "messageText": "오늘 학습 시작"}
                ]
            }
        }

    # 기본 안내 화면 (커리큘럼 메인)
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"👋 맞춤형 원어민 비즈니스 튜터입니다.\n\n"
                                f"현재 설정\n"
                                f"• 언어: **[{current_lang}]**\n"
                                f"• 난이도: **[{current_level}]**\n\n"
                                f"하단 메뉴에서 설정을 변경하거나 아래 버튼을 눌러 커리큘럼 훈련을 시작하세요!"
                    }
                }
            ],
            "quickReplies": [
                {"label": "🚀 오늘 학습 시작", "action": "message", "messageText": "오늘 학습 시작"}
            ]
        }
    }
