import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()

# 제공해주신 Groq API 키 설정
GROQ_API_KEY = "Gsk_GI1m4hspv6VtDgtxRyVTWGdyb3FYkx00NSwnIV7nxd0LvhRaNYtp"

# 간단한 인메모리 세션 저장소 (데모용)
user_sessions = {}

@app.get("/", response_class=HTMLResponse)
async def home(user_id: str = "default_user"):
    if user_id not in user_sessions:
        user_sessions[user_id] = {"step": 1, "score": 0}
    
    session = user_sessions[user_id]
    step = session["step"]
    score = session["score"]
    
    # HTML UI 구성 (1~4단계 및 오디오 링크, 퀴즈 포함)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>맞춤형 언어 학습 대시보드</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; color: #333; }}
            .container {{ max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            h2 {{ color: #0056b3; }}
            .btn {{ display: inline-block; padding: 10px 15px; margin: 10px 5px 10px 0; background: #007bff; color: white; text-decoration: none; border-radius: 4px; border: none; cursor: pointer; }}
            .btn:hover {{ background: #0056b3; }}
            .info-box {{ background: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🗣️ 맞춤형 영어 학습 커리큘럼 (Step {step}/4)</h2>
    """
    
    if step == 1:
        html_content += """
            <div class="info-box">
                <h3>Step 1: 핵심 오프닝 & 시그니처 패턴</h3>
                <p>원어민의 정확한 발음과 억양을 확인하며 핵심 표현을 익혀보세요.</p>
                <p>🎧 <a href="https://example.com/audio-sample" target="_blank">원어민 발음 오디오 클립 듣기</a></p>
                <ul>
                    <li><b>Core Expression:</b> Let's get down to business.</li>
                    <li><b>Signature Pattern:</b> I'm calling to follow up on...</li>
                </ul>
            </div>
            <a href="/next?user_id=""" + user_id + """" class="btn">2단계로 넘어가기</a>
        """
    elif step == 2:
        html_content += """
            <div class="info-box">
                <h3>Step 2: 리스크 방어 & 설득 어휘 심화</h3>
                <p>실전 비즈니스 및 상황별 심화 표현을 학습합니다.</p>
                <p>🎧 <a href="https://example.com/audio-step2" target="_blank">2단계 심화 오디오 클립 듣기</a></p>
                <ul>
                    <li><b>Advanced Vocab:</b> Mitigate the risk, Supply chain disruption</li>
                    <li><b>Combo Phrase:</b> To ensure we're on the same page...</li>
                </ul>
            </div>
            <a href="/prev?user_id=""" + user_id + """" class="btn">이전 단계로</a>
            <a href="/next?user_id=""" + user_id + """" class="btn">3단계(음성 미션)로</a>
        """
    elif step == 3:
        html_content += """
            <div class="info-box">
                <h3>Step 3: 음성 녹음 미션 & 전문가 피드백</h3>
                <p>배운 내용을 바탕으로 실제 상황을 가정해 답변을 준비하세요.</p>
                <textarea rows="3" style="width:100%;" placeholder="답변을 입력하세요..."></textarea>
            </div>
            <a href="/prev?user_id=""" + user_id + """" class="btn">이전 단계로</a>
            <a href="/next?user_id=""" + user_id + """" class="btn">4단계(퀴즈)로</a>
        """
    elif step == 4:
        html_content += f"""
            <div class="info-box">
                <h3>Step 4: 마무리 퀴즈 및 점수 확인</h3>
                <form action="/submit_quiz" method="get">
                    <input type="hidden" name="user_id" value="{user_id}">
                    <p><b>Q1. '위험을 완화하다'를 뜻하는 올바른 표현은?</b></p>
                    <input type="radio" name="q1" value="wrong"> Choose one<br>
                    <input type="radio" name="q1" value="correct" required> Mitigate the risk<br><br>
                    
                    <p><b>Q2. 공급망 차단을 영어로 올바르게 표현한 것은?</b></p>
                    <input type="radio" name="q2" value="correct" required> Supply chain disruption<br>
                    <input type="radio" name="q2" value="wrong"> Market index<br><br>
                    
                    <button type="submit" class="btn">채점하기</button>
                </form>
                <hr>
                <p><b>현재 점수:</b> {score}점 / 100점</p>
            </div>
            <a href="/reset?user_id=""" + user_id + """" class="btn" style="background: #dc3545;">처음부터 다시 하기</a>
        """
        
    html_content += """
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/next")
async def next_step(user_id: str = "default_user"):
    if user_id in user_sessions:
        if user_sessions[user_id]["step"] < 4:
            user_sessions[user_id]["step"] += 1
    return HTMLResponse(content=f"<script>window.location.href='/='/'?user_id={user_id}';</script>")

@app.get("/prev")
async def prev_step(user_id: str = "default_user"):
    if user_id in user_sessions:
        if user_sessions[user_id]["step"] > 1:
            user_sessions[user_id]["step"] -= 1
    return HTMLResponse(content=f"<script>window.location.href='/='/'?user_id={user_id}';</script>")

@app.get("/submit_quiz")
async def submit_quiz(user_id: str = "default_user", q1: str = "", q2: str = ""):
    score = 0
    if q1 == "correct":
        score += 50
    if q2 == "correct":
        score += 50
    if user_id in user_sessions:
        user_sessions[user_id]["score"] = score
        user_sessions[user_id]["step"] = 4
    return HTMLResponse(content=f"<script>window.location.href='/='/'?user_id={user_id}';</script>")

@app.get("/reset")
async def reset_session(user_id: str = "default_user"):
    if user_id in user_sessions:
        user_sessions[user_id] = {"step": 1, "score": 0}
    return HTMLResponse(content=f"<script>window.location.href='/='/'?user_id={user_id}';</script>")

# 크론잡 오류 방지를 위해 응답 크기를 최소화한 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    return "OK"
