from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from groq import Groq
import os

app = FastAPI()

# Groq API 설정 (무료 활용 가능, 본인 API 키 입력)
client = Groq(api_key="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")

# 1. 버튼 없이 말하면 자동으로 인식하고 대화하는 웹 통화 화면
@app.get("/", response_class=HTMLResponse)
async def voice_chat_page(request: Request):
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI 원어민 실시간 음성 대화</title>
        <style>
            body { background-color: #121212; color: #ffffff; font-family: sans-serif; text-align: center; padding-top: 50px; }
            h1 { color: #4CAF50; }
            .status { font-size: 18px; margin: 20px; color: #ffeb3b; }
            .box { background: #1e1e1e; padding: 20px; border-radius: 10px; max-width: 450px; margin: 0 auto; text-align: left; }
            p { margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>📞 AI 원어민 실시간 대화방</h1>
        <div class="status" id="statusText">마이크 준비 중... 편하게 말씀하세요!</div>
        
        <div class="box">
            <p><b>나:</b> <span id="userText" style="color: #90caf9;">대기 중...</span></p>
            <p><b>AI 선생님:</b> <span id="aiText" style="color: #a5d6a7;">대화가 시작되면 여기에 표시됩니다.</span></p>
        </div>

        <script>
            const statusText = document.getElementById("statusText");
            const userTextSpan = document.getElementById("userText");
            const aiTextSpan = document.getElementById("aiText");

            // 브라우저 내장 음성 인식 API (구글 엔진 기반 - 완전 무료)
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            
            if (!SpeechRecognition) {
                alert("이 브라우저는 실시간 음성 인식을 지원하지 않습니다. 크롬(Chrome) 브라우저를 사용해 주세요.");
            } else {
                const recognition = new SpeechRecognition();
                recognition.lang = 'ko-KR'; // 인식 언어 (필요시 'vi-VN' 베트남어로 변경 가능)
                recognition.continuous = false; // 한 문장씩 끊어서 자연스럽게 처리
                recognition.interimResults = true;

                recognition.onstart = () => {
                    statusText.innerText = "🟢 듣고 있어요... 편하게 말씀하세요!";
                };

                recognition.onresult = async (event) => {
                    let transcript = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript;
                    }
                    userTextSpan.innerText = transcript;

                    // 사용자가 말을 끝마쳤을 때 서버로 전송
                    if (event.results[0].isFinal) {
                        statusText.innerText = "⏳ AI가 생각 중...";
                        
                        try {
                            const response = await fetch("/api/chat", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ message: transcript })
                            });
                            const data = await response.json();
                            const reply = data.reply;
                            
                            aiTextSpan.innerText = reply;
                            statusText.innerText = "🔊 AI 답변 중...";
                            
                            // 브라우저 내장 음성 합성(TTS)으로 AI 답변 말하기 (완전 무료)
                            const utterance = new SpeechSynthesisUtterance(reply);
                            utterance.lang = 'ko-KR'; // 한국어 출력 (베트남어 음성 원하시면 'vi-VN'으로 변경)
                            utterance.rate = 1.0;
                            
                            utterance.onend = () => {
                                // 말이 끝나면 자동으로 다시 듣기 시작 (무한 대화 루프)
                                recognition.start();
                            };
                            
                            window.speechSynthesis.speak(utterance);
                        } catch (err) {
                            statusText.innerText = "⚠️ 오류 발생. 다시 시도합니다.";
                            recognition.start();
                        }
                    }
                };

                recognition.onerror = (event) => {
                    console.error(event.error);
                    recognition.start(); // 에러가 나도 끊기지 않고 다시 듣기 시도
                };

                recognition.onend = () => {
                    // 음성 인식이 꺼지면 자동으로 다시 켜서 상시 대기 상태 유지
                    try { recognition.start(); } catch(e) {}
                };

                // 최초 실행
                recognition.start();
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 2. 사용자의 말을 받아 Groq AI로 답변을 만드는 API
@app.post('/api/chat')
async def chat_with_ai(request: Request):
    data = await request.json()
    user_message = data.get("message", "")

    # Groq AI 호출 (초고속 무료 기반 모델 활용)
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "당신은 친절하고 다정한 외국어(베트남어 및 한국어) 원어민 튜터입니다. 사용자의 말에 짧고 자연스럽게 대화하듯 대답해 주세요."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=150
        )
        ai_reply = completion.choices[0].message.content
    except Exception as e:
        ai_reply = "죄송합니다, 잠시 통신이 원활하지 않았어요. 다시 말씀해 주세요!"

    return JSONResponse({"reply": ai_reply})
