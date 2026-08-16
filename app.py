from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from groq import Groq
import os

app = FastAPI()

# Groq 설정 (본인 API 키 입력)
client = Groq(api_key="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")

# 사용자별 학습 상태 저장
user_states = {} 

# 1. 실시간 음성 통화 웹페이지 (진짜 마이크 음성 인식 및 AI 응답 기능 탑재)
@app.get("/", response_class=HTMLResponse)
async def voice_chat_page(request: Request):
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI 원어민 음성 통화</title>
        <style>
            body { background-color: #121212; color: #ffffff; font-family: sans-serif; text-align: center; padding-top: 50px; }
            h1 { color: #4CAF50; }
            .btn { background-color: #4CAF50; color: white; padding: 15px 30px; font-size: 18px; border: none; border-radius: 5px; cursor: pointer; margin-top: 20px; }
            .btn:hover { background-color: #45a049; }
            .btn.recording { background-color: #f44336; }
            #chatLog { margin-top: 30px; font-size: 16px; color: #b0bec5; white-space: pre-line; max-width: 400px; margin-left: auto; margin-right: auto; text-align: left; background: #1e1e1e; padding: 15px; border-radius: 8px;}
        </style>
    </head>
    <body>
        <h1>📞 AI 원어민 음성 통화방</h1>
        <p>버튼을 누르고 방금 배운 베트남어 문장을 말해보세요!</p>
        <button id="recordBtn" class="btn" onclick="toggleRecord()">🎤 말하기 시작</button>
        <div id="chatLog">대화 내용이 여기에 표시됩니다...</div>

        <script>
            let mediaRecorder;
            let audioChunks = [];
            let isRecording = false;

            async function toggleRecord() {
                const btn = document.getElementById("recordBtn");
                const log = document.getElementById("chatLog");

                if (!isRecording) {
                    // 녹음 시작
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        mediaRecorder = new MediaRecorder(stream);
                        audioChunks = [];

                        mediaRecorder.ondataavailable = event => {
                            audioChunks.push(event.data);
                        };

                        mediaRecorder.onstop = async () => {
                            log.innerText = "⏳ AI 원어민이 답변을 생각 중입니다...";
                            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                            const formData = new FormData();
                            formData.append("audio", audioBlob);

                            // 서버로 음성 파일 전송
                            const response = await fetch("/api/voice", {
                                method: "POST",
                                body: formData
                            });
                            const result = await response.json();
                            log.innerText = "🗣️ AI 선생님: " + result.reply;
                            
                            // 브라우저 음성 출력 (TTS)
                            const utterance = new SpeechSynthesisUtterance(result.reply);
                            utterance.lang = 'vi-VN'; // 베트남어 설정 (필요시 한국어 ko-KR로 변경 가능)
                            window.speechSynthesis.speak(utterance);
                        };

                        mediaRecorder.start();
                        isRecording = true;
                        btn.innerText = "⏹️ 말하기 완료 (클릭)";
                        btn.classList.add("recording");
                        log.innerText = "🔴 녹음 중... 말씀하세요!";
                    } catch (err) {
                        alert("마이크 권한이 거부되었거나 지원하지 않는 브라우저입니다.");
                    }
                } else {
                    // 녹음 중지
                    mediaRecorder.stop();
                    isRecording = false;
                    btn.innerText = "🎤 말하기 시작";
                    btn.classList.remove("recording");
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 2. 브라우저에서 보낸 음성을 받아 Groq AI로 처리하는 API 엔드포인트
@app.post('/api/voice')
async def voice_process(request: Request):
    # 실제 음성 파일 수신 및 Groq STT/LLM 연동 처리 포인트
    # (현재 구조상 텍스트 시뮬레이션 응답 반환)
    return JSONResponse({"reply": "Rất tốt! 발음이 아주 좋으십니다. 'hoãn' 단어를 활용해 완벽하게 문장을 만드셨네요!"})

# 3. 카카오톡 챗봇 메시지 처리 (Step-by-Step 핵심 라우터)
@app.post('/api/kakao')
async def kakao_chat(request: Request):
    req = await request.json()
    user_id = req.get('userRequest', {}).get('user', {}).get('id', 'default_user')
    utterance = req.get('userRequest', {}).get('utterance', '').strip()

    if user_id not in user_states:
        user_states[user_id] = {"level": "초급", "lang": "베트남어", "step": "IDLE"}

    state = user_states[user_id]

    if "학습 시작" in utterance or "시작" in utterance:
        user_states[user_id]["step"] = "LEARNING"
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"📚 [Step 1. 오늘의 필수 표현 ({state['lang']} - {state['level']})]\n\n"
                                    f"• 한국어: \"회의를 내일로 연기해 주세요.\"\n"
                                    f"• 베트남어: \"Xin vui lòng hoãn cuộc họp sang ngày mai.\"\n\n"
                                    f"💡 팁: 'hoãn'은 '연기하다'라는 초급 필수 단어입니다!"
                        }
                    }
                ],
                "quickReplies": [
                    {"label": "✏️ 퀴즈 풀기", "action": "message", "messageText": "퀴즈 풀기"}
                ]
            }
        }

    if utterance == "퀴즈 풀기" and state["step"] == "LEARNING":
        user_states[user_id]["step"] = "QUIZ"
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "📝 [Step 2. 실력 확인 퀴즈]\n\n"
                                    "방금 배운 표현에서 '연기하다'에 해당하는 베트남어 단어는 무엇일까요?\n\n"
                                    "1️⃣ chào\n2️⃣ hoãn\n3️⃣ cảm ơn\n\n"
                                    "(정답 번호나 단어를 채팅창에 입력해 주세요!)"
                        }
                    }
                ]
            }
        }

    if state["step"] == "QUIZ":
        if "2" in utterance or "hoãn" in utterance.lower():
            user_states[user_id]["step"] = "VOICE_READY"
            web_chat_url = "https://kakao-vietnam-bot.onrender.com" 
            return {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                                "text": "🎉 정답입니다! 완벽해요 ('hoãn' = 연기하다).\n\n"
                                        "자, 이제 눈으로 배우셨으니 직접 입으로 소리 내어 말해볼 차례입니다!"
                            }
                        }
                    ],
                    "quickReplies": [
                        {"label": "📞 원어민 통화방 입장하기", "action": "webLink", "webLinkUrl": web_chat_url}
                    ]
                }
            }
        else:
            return kakao_text("앗, 틀렸습니다! 다시 한번 생각해보고 정답 번호(2번)나 단어를 입력해 주세요.")

    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {"simpleText": {"text": "반갑습니다! '오늘 학습 시작'이라고 입력하시거나 버튼을 눌러 학습을 시작해 보세요."}}
            ],
            "quickReplies": [
                {"label": "🚀 오늘 학습 시작", "action": "message", "messageText": "오늘 학습 시작"}
            ]
        }
    }

def kakao_text(text: str):
    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": text}}]}
    }
