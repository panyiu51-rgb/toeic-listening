import streamlit as st
import google.generativeai as genai
from gtts import gTTS
from pydub import AudioSegment
import io
import json
import random

# 페이지 설정
st.set_page_config(page_title="토익 리스닝 마스터", page_icon="🎧")

st.title("🎧 토익 리스닝(LC) 자동 암기")
st.caption("TOEIC 빈출 표현 -> 코리안 발음 -> 한국어 뜻 순서로 무한 재생")

# --- 1. 비밀 열쇠(API 키) 가져오기 ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("설정에서 API 키를 등록해주세요! (Secrets)")
    st.stop()

# --- 2. 기능 함수들 ---

def get_toeic_sentences():
    """제미나이에게 토익 빈출 문장을 요청합니다."""
    # 모델 설정 (gemini-2.5-flash 또는 gemini-pro 사용)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """
    TOEIC Listening (Part 1, 2, 3) 시험에 정말 자주 나오는 필수 영어 표현이나 문장 5개를 뽑아줘.
    비즈니스 상황, 회사 생활, 일상 업무와 관련된 표현 위주로 선정해줘.
    
    반드시 다음 JSON 형식으로만 출력해줘 (다른 말 금지):
    [
        {"eng": "Could you review this report?", "kor_pron": "쿠쥬 리뷰 디스 리포트?", "mean": "이 보고서 좀 검토해 주시겠어요?"},
        ...
    ]
    조건: 'kor_pron'은 실제 들리는 연음을 반영해서 한글로 적어줘.
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "")
        return json.loads(text)
    except Exception as e:
        st.error(f"AI 연결 중 오류 발생: {e}")
        return []

def create_audio(text, lang):
    """텍스트를 소리로 바꿉니다."""
    tts = gTTS(text=text, lang=lang)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return AudioSegment.from_file(fp, format="mp3")

def speed_change(sound, speed=1.0):
    """오디오 속도를 조절하는 함수입니다."""
    # 프레임 속도를 조절하여 속도와 피치(음높이)를 같이 올림 -> 여자 목소리 유지에 도움됨
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    })
    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)

# --- 3. 화면 구성 및 실행 ---

if st.button("▶️ 공부 시작 (자동 생성)"):
    with st.spinner("AI가 토익 족보를 뒤지는 중입니다... (약 15초 소요)"):
        
        # 문장 가져오기
        data = get_toeic_sentences()
        
        if data:
            full_audio = AudioSegment.empty()
            silence = AudioSegment.silent(duration=1000) # 1초 쉼
            short_silence = AudioSegment.silent(duration=500) # 0.5초 쉼

            progress_bar = st.progress(0)
            
            for i, item in enumerate(data):
                # 진행률 표시
                progress_bar.progress((i + 1) / 5)
                
                # 1. 영어 원문 (정상 속도)
                eng = create_audio(item['eng'], 'en')
                
                # 2. 한국식 발음 (영어 텍스트를 한국어 성우가 읽음)
                # [핵심] 여기서 속도를 1.2배 빠르게 조절!
                raw_kor = create_audio(item['eng'], 'ko') 
                kor = speed_change(raw_kor, speed=1.25) 
                
                # 3. 한국어 뜻 (정상 속도)
                mean = create_audio(item['mean'], 'ko')

                # 합치기
                full_audio += eng + short_silence + kor + short_silence + mean + silence
                
                # 화면 표시
                st.markdown(f"""
                ---
                **{i+1}. {item['eng']}** 🗣️ *{item['kor_pron']}* 🇰🇷 {item['mean']}
                """)

            # 최종 재생
            st.success("생성 완료! 아래 플레이어를 누르세요.")
            buffer = io.BytesIO()
            full_audio.export(buffer, format="mp3")
            st.audio(buffer, format='audio/mp3')
