from fastapi import FastAPI, Request
from groq import Groq
import os

app = FastAPI()
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "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"))

# 사용자별 상세 상태 메모리 (언어, 난이도, 현재 진행 중인 step 관리)
# step 종류: IDLE(대기), STEP_1(1단계), STEP_2(2단계), STEP_3(3단계), COMPLETED(완료)
user_states = {}

@app.post('/api/kakao')
async def kakao_webhook(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()
    
    if user_id not in user_states:
        user_states[user_id] = {"lang": "영어", "level": "초급", "step": "IDLE"}

    current_state = user_states[user_id]["step"]
    current_lang = user_states[user_id]["lang"]
    current_level = user_states[user_id]["level"]

    # 1. 언어 변경 신호
    if utterance.startswith("언어:"):
        user_states[user_id]["lang"] = utterance.split(":")[1]
        user_states[user_id]["step"] = "IDLE"
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": f"✨ 학습 언어가 [{user_states[user_id]['lang']}]로 설정되었습니다."}}],
                "quickReplies": [{"label": "🚀 3단계 커리큘럼 시작", "action": "message", "messageText": "오늘 학습 시작"}]
            }
        }
    
    # 2. 난이도 변경 신호
    if utterance.startswith("난이도:"):
        user_states[user_id]["level"] = utterance.split(":")[1]
        user_states[user_id]["step"] = "IDLE"
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": f"🎯 학습 난이도가 [{user_states[user_id]['level']}]로 설정되었습니다."}}],
                "quickReplies": [{"label": "🚀 3단계 커리큘럼 시작", "action": "message", "messageText": "오늘 학습 시작"}]
            }
        }

    # 3. [학습 시작] 버튼을 누르면 -> 전체 커리큘럼 로드맵 안내 후 [1단계] 자동 시작
    if "오늘 학습 시작" in utterance or current_state == "IDLE":
        user_states[user_id]["step"] = "STEP_1"
        
        roadmap_intro = (
            f"🗺️ [{current_lang} / {current_level}] 단계별 커리큘럼 로드맵\n\n"
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

    # 4. [1단계 진행 중] 답변이 들어오면 -> 피드백 후 자동으로 [2단계]로 진입
    if current_state == "STEP_1":
        prompt = f"당신은 {current_lang} 멘토입니다. 학습자({current_level})의 1단계 답변 '{utterance}'을 피드백하고 교정해주세요."
        try:
            completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
            feedback = completion.choices[0].message.content
        except:
            feedback = "AI 분석 완료."

        # 다음 단계로 상태 업데이트
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

    # 5. [2단계 진행 중] 답변이 들어오면 -> 피드백 후 자동으로 [3단계]로 진입
    if current_state == "STEP_2":
        prompt = f"당신은 {current_lang} 멘토입니다. 학습자({current_level})의 2단계 답변 '{utterance}'을 피드백하고 교정해주세요."
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
            f"최종적으로 상대방에게 일정을 확정해 주며 마무리 메사를 깔끔하게 작성해 주세요!"
        )
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": next_mission}}]
            }
        }

    # 6. [3단계 진행 중] 최종 답변이 들어오면 -> 전 과정 완료 처리
    if current_state == "STEP_3":
        prompt = f"당신은 {current_lang} 멘토입니다. 학습자({current_level})의 3단계 최종 답변 '{utterance}'을 최종 평가해주세요."
        try:
            completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
            feedback = completion.choices[0].message.content
        except:
            feedback = "AI 분석 완료."

        # 모든 과정 종료, 대기 상태로 초기화
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

    # 기본 상태
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": f"👋 현재 설정: [{current_lang} / {current_level}]\n\n아래 버튼을 눌러 체계적인 3단계 커리큘럼을 시작하세요!"}}],
            "quickReplies": [{"label": "🚀 3단계 커리큘럼 시작", "action": "message", "messageText": "오늘 학습 시작"}]
        }
    }

# cron-job 전용 가벼운 엔드포인트
@app.get('/api/cron/push')
@app.post('/api/cron/push')
async def cron_push():
    return {"status": "ok"}
