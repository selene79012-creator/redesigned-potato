# 🍌 나노바나나2 이미지 생성기

Gemini API(나노바나나2 / `gemini-3.1-flash-image-preview`)를 활용한 유튜브 대본 기반 이미지 자동 생성 Streamlit 앱입니다.

## 기능

1. **대본 분석** — Gemini 텍스트 모델로 대본의 주제, 톤, 등장 요소 분석
2. **초단위 분할** — 5초~30초(5초 단위) 설정으로 대본을 장면별 분할
3. **이미지 프롬프트 생성** — 스타일 가이드 기반 자동 프롬프트 생성 (한국어/영어/일본어/언어없음 선택)
4. **이미지 생성** — 나노바나나2로 장면별 이미지 자동 생성

## 설치 및 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 설정

- **Gemini API Key**: [Google AI Studio](https://aistudio.google.com/apikey)에서 발급
- **분할 설정**: 5~30초 (5초 단위), 1초당 글자수 조절 가능
- **프롬프트 언어**: 영어 / 한국어 / 일본어 / 언어 없음
- **이미지 모델**: 나노바나나2 (gemini-3.1-flash-image-preview) 기본

## 스타일 가이드

기본 스타일: 2D 스틱맨 애니메이션 (Gems System Ver 7.0)
앱 내에서 자유롭게 수정 가능합니다.
