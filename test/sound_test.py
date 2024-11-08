import pyaudio
import wave
import numpy as np
import requests
import sounddevice as sd
import soundfile as sf
import io

# 녹음 설정
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
SILENCE_THRESHOLD = 30  # 무음 감지 임계값을 높임
SILENCE_CHUNKS = 30  # 무음으로 간주할 청크 수를 늘림

audio = pyaudio.PyAudio()

def list_audio_devices():
    info = audio.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    for i in range(0, numdevices):
        if audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels') > 0:
            print("Input Device id ", i, " - ", audio.get_device_info_by_host_api_device_index(0, i).get('name'))

# 장치 목록 출력
list_audio_devices()

while True:
    # 녹음 시작
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)

    print("Recording...")

    frames = []
    silent_chunks = 0

    while True:
        data = stream.read(CHUNK)
        frames.append(data)

        # 오디오 데이터를 numpy 배열로 변환
        audio_data = np.frombuffer(data, dtype=np.int16)
        # 오디오 데이터의 절대값 평균 계산
        volume = np.abs(audio_data).mean()
        
        
        print(volume)

        if volume < SILENCE_THRESHOLD:
            silent_chunks += 1
        else:
            silent_chunks = 0
            
        print(silent_chunks)

        # 무음이 일정 시간 지속되면 녹음 종료
        if silent_chunks > SILENCE_CHUNKS:
            print("Silence detected, stopping recording.")
            break

    # 녹음 종료
    stream.stop_stream()
    stream.close()

    # 오디오 파일로 저장
    WAVE_OUTPUT_FILENAME = "output.wav"
    waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    waveFile.setnchannels(CHANNELS)
    waveFile.setsampwidth(audio.get_sample_size(FORMAT))
    waveFile.setframerate(RATE)
    waveFile.writeframes(b''.join(frames))
    waveFile.close()

    # 서버 URL 설정
    url = "http://localhost:8000/voice-chat"

    # 오디오 파일 경로 설정
    audio_file_path = "./output.wav"

    # 오디오 파일을 서버에 업로드
    with open(audio_file_path, 'rb') as audio_file:
        files = {'audio': audio_file}
        response = requests.post(url, files=files)

    # 응답으로 받은 오디오 데이터를 재생
    if response.status_code == 200:
        audio_data = io.BytesIO(response.content)
        data, samplerate = sf.read(audio_data)
        sd.play(data, samplerate)
        sd.wait()
    else:
        print("오류 발생:", response.status_code, response.text)

    # continue_chat = input("계속 대화하시겠습니까? (y/n): ")
    # if continue_chat.lower() != 'y':
    #     break

audio.terminate()
