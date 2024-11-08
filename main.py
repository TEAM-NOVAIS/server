from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse
import speech_recognition as sr
from gtts import gTTS
from openai import OpenAI
import tempfile
import io
import requests
import os
import dotenv

dotenv.load_dotenv()

app = FastAPI()

# OpenAI API 키 설정
api_key = os.getenv('OPENAI_API_KEY')
elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')

client = OpenAI(api_key=api_key)

import time

@app.post("/voice-chat")
async def voice_chat(audio: UploadFile = File(...)):
    start_time = time.time()
    
    # 오디오 파일을 임시 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
        temp_audio_file.write(await audio.read())
        temp_audio_file_path = temp_audio_file.name
    save_audio_time = time.time()
    print(f"오디오 파일 저장 시간: {save_audio_time - start_time}초")

    recognizer = sr.Recognizer()

    # 임시 파일을 AudioFile로 읽기
    with sr.AudioFile(temp_audio_file_path) as source:
        audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language='ko')
    recognize_audio_time = time.time()
    print(f"오디오 인식 시간: {recognize_audio_time - save_audio_time}초")
    
    print(text)

    # LLM: 텍스트를 처리하여 응답 생성
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
        {"role": "system", "content": "너는 한국의 비서처럼 대답해줘. 마크다운 형식 같은 거 쓰지말고 순수 텍스트로 대답해줘. 너의 대답을 tts 로 목소리로 변환해서 들려줄거야. 토큰 수 100개 제한을 둬서 적당히 100글자 이내로 짧게 대답해줘. 그리고 너는 무조건 한국어로 대답해야돼."},
        {
            "role": "user",
            "content": text
        }
        ],
        max_tokens=100  # 응답의 최대 토큰 수를 50으로 제한
    )
    response_text = completion.choices[0].message.content
    generate_response_time = time.time()
    print(f"응답 생성 시간: {generate_response_time - recognize_audio_time}초")
    
    # TTS: 응답 텍스트를 오디오로 변환
    tts_start_time = time.time()
    
    tts_url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL/stream"  # 'Rachel' 음성 ID
    
    headers = {
        "Accept": "application/json",
        "xi-api-key": elevenlabs_api_key
    }
    
    data = {
        "text": response_text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    
    response = requests.post(tts_url, headers=headers, json=data, stream=True)
    
    if response.ok:
        audio_buffer = io.BytesIO()
        for chunk in response.iter_content(chunk_size=1024):
            audio_buffer.write(chunk)
        audio_buffer.seek(0)
    else:
        print("TTS 에러:", response.text)
        return {"error": "TTS 변환 실패"}
    
    tts_end_time = time.time()
    print(f"오디오 변환 시간: {tts_end_time - tts_start_time}초")
    
    
    print(f"총 처리 시간: {tts_end_time - start_time}초")
    
    # StreamingResponse를 사용하여 오디오 데이터를 반환
    return StreamingResponse(audio_buffer, media_type='audio/wav')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

