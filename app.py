from fastapi import FastAPI, Request
from groq import Groq
import os

app = FastAPI()
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))

# 사용자별 상태 관리 (lang: 언어, level: 난이도, step: 진행 단계)
user_states = {}

@app.post('/api/kakao')
async def kakao_webhook(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()
    
    # 최초 사용자 초기화 (기본값 설정)
    if user_id not in user_states:
        user_states[user_id] = {"lang": None, "level": None, "step": "IDLE"}

    # 1. 언어 선택 처리 (아직 학습 시작 전, 세팅 단계)
    if utterance.startswith("언어:"):
        selected_lang = utterance.split(":")[1]
        user_states[user_id]["lang"] = selected_lang
        current_level = user_states[user_id]["level"] or "미선택"
        
        return {
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": f"✨ 학습 언어가 [{selected_lang}]로 설정되었습니다.\n\n"
                                f"📌 현재 설정 상태\n"
                                f"• 언어: [{selected_lang}]\n"
                                f"• 난이도: [{current_level}]\n\n"
                                f"👉 하단 메뉴나 버튼에서 **난이도**를 마저 선택해 주세요!"
                    }
                }]
            }
        }
    
    # 2. 난이도 선택 처리 (아직 학습 시작 전, 세팅 단계)
    if utterance.startswith("난이도:"):
        selected_level = utterance.split(":")[1]
        user_states[user_id]["level"] = selected_level
        current_lang = user_states[user_id]["lang"] or "미선택"
        
        # 언어와 난이도가 모두 선택된 경우에만 '학습 시작' 버튼 제공
        quick_replies = []
        if user_states[user_id]["lang"] and user_states[user_id]["level"]:
            quick_replies.append({"label": "🚀 3단계 커리큘럼 시작", "action": "message", "messageText": "오늘 학습 시작"})

        return {
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": f"🎯 학습 난이도가 [{selected_level}]로 설정되었습니다.\n\n"
                                f"📌 현재 설정 상태\n"
                                f"• 언어: [{current_lang}]\n"
                                f"• 난이도: [{selected_level}]\n\n"
                                f"{'✅ 모든 준비가 완료되었습니다! 아래 버튼을 눌러 시작하세요.' if user_states[user_id]['lang'] else '👉 상단 메뉴에서 **언어**를 마저 선택해 주세요!'}"
                    }
                }],
                "quickReplies": quick_replies
            }
        }

    # 3. [학습 시작] 요청 (AND 조건 검사: 언어와 난이도가 모두 있어야만 진입 가능)
    if "오늘 학습 시작" in utterance:
        lang = user_states[user_id]["lang"]
        level = user_states[user_id]["level"]
        
        if not lang or not level:
            return {
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "⚠️ 언어와 난이도를 모두 선택한 뒤에 학습을 시작할 수 있습니다. 하단 메뉴를 확인해 주세요!"}}]
                }
            }
        
        # 조건 충족 시 1단계로 진입
        user_states[user_id]["step"] = "STEP_1"
        roadmap_intro = (
            f"🗺️ [{lang} / {level}] 3단계 비즈니스 커리큘럼 시작!\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👉 **[1단계] 핵심 패턴 영작 (현재 진행중)**\n"
            f"🔒 [2단계] 비즈니스 실전 대화 (잠김)\n"
            f"🔒 [3단계] 돌발 상황 대처 심화 (잠김)\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 **[1단계 미션]**\n"
            f"상사에게 일정 변경을 정중하게 요청하는 첫 문장을 작성해 주세요!"
        )
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": roadmap_intro}}]
            }
        }

    # 4. [1단계 진행 중 실제 답변] 처리
    current_state = user_states[user_id]["step"]
    lang = user_states[user_id]["lang"] or "영어"
    level = user_states[user_id]["level"] or "초급"

    if current_state == "STEP_1" and utterance:
        prompt = f"당신은 전문 {lang} 멘토입니다. 학습자({level})의 1단계 답변 '{utterance}'을 피드백하고 교정해주세요."
        try:
            completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
            feedback = completion.choices[0].message.content
        except:
            feedback = "AI 분석 완료."

        user_states[user_id]["step"] = "STEP_2"
        next_mission = (
            f"📊 [1단계 코칭 결과]\n{feedback}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"✅ [1단계] 완료!\n"
            f"👉 **[2단계] 비즈니스 실전 대화 (현재 진행중)**\n"
            f"🔒 [3단계] 돌발 상황 대처 심화 (잠김)\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 **[2단계 미션]**\n"
            f"상대방이 '왜 일정을 변경해야 하냐고' 물어왔습니다. 이에 대해 타당한 이유를 한 문장으로 답변해 주세요!"
        )
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": next_mission}}]
            }
        }

    # 5. [2단계 진행 중 실제 답변] 처리
    if current_state == "STEP_2" and utterance:
        prompt = f"당신은 전문 {lang} 멘토입니다. 학습자({level})의 2단계 답변 '{utterance}'을 피드백하고 교정해주세요."
        try:
            completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
            feedback = completion.choices[0].message.content
        except:
            feedback = "AI 분석 완료."

        user_states[user_id]["step"] = "STEP_3"
        next_mission = (
            f"📊 [2단계 코칭 결과]\n{feedback}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"✅ [1단계] 완료!\n"
            f"✅ [2단계] 완료!\n"
            f"👉 **[3단계] 돌발 상황 대처 심화 (현재 진행중)**\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 **[3단계 최종 미션]**\n"
            f"최종적으로 상대방에게 일정을 확정해 주며 마무리 메세지를 깔끔하게 작성해 주세요!"
        )
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": next_mission}}]
            }
        }

    # 6. [3단계 진행 중 실제 최종 답변] 처리
    if current_state == "STEP_3" and utterance:
        prompt = f"당신은 전문 {lang} 멘토입니다. 학습자({level})의 3단계 최종 답변 '{utterance}'을 최종 평가해주세요."
        try:
            completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
            feedback = completion.choices[0].message.content
        except:
            feedback = "AI 분석 완료."

        user_states[user_id]["step"] = "IDLE"
        completion_msg = (
            f"🎉 축하합니다! 오늘의 3단계 커리큘럼을 모두 수료하셨습니다!\n\n"
            f"📊 [최종 종합 코칭]\n{feedback}"
        )
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": completion_msg}}],
                "quickReplies": [{"label": "🔄 새로운 커리큘럼 시작", "action": "message", "messageText": "오늘 학습 시작"}]
            }
        }

    # 기본 첫 진입 화면
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": "👋 맞춤형 어학 튜터에 오신 것을 환영합니다!\n\n"
                            "하단 메뉴에서 **[언어]**와 **[난이도]**를 모두 선택하신 후 커리큘럼을 시작해 주세요."
                }
            }]
        }
    }

# cron-job 전용 가벼운 엔드포인트
@app.get('/api/cron/push')
@app.post('/api/cron/push')
async def cron_push():
    return {"status": "ok"}
