import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import Response
from groq import Groq

app = FastAPI()

# 사용 중이신 Groq API 키를 넣으세요 (gsk_...)
API_KEY = "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"

client = Groq(api_key=API_KEY)

@app.post('/api/kakao')
async def kakao_chat(request: Request):
    try:
        req = await request.json()
        user_message = req.get('userRequest', {}).get('utterance', '')
        
        # Groq 정식 최신 안정화 모델
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 전문적인 베트남어 어학 튜터야. "
                        "답변은 오직 표준 한국어와 베트남어 성조 알파벳(ABC, a, ă, â...)만 사용해. "
                        "힌디어, 태국어, 기타 외래 문자나 유니코드 깨짐 글자는 절대 포함하지 마."
                    )
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            temperature=0.3,  # 무작위성을 낮춰 환각/깨짐 현상 최소화
            max_tokens=1024,
        )
        
        bot_text = completion.choices[0].message.content

    except Exception as e:
        bot_text = f"서버 오류 발생: {str(e)}"

    # 카카오톡 챗봇 응답 포맷
    payload = {
        'version': '2.0',
        'template': {'outputs': [{'simpleText': {'text': bot_text}}]}
    }

    # UTF-8 한글 직렬화 (인코딩 에러 방지)
    json_str = json.dumps(payload, ensure_ascii=False)
    return Response(content=json_str, media_type="application/json; charset=utf-8")

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)