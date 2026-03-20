"""
🍌 나노바나나2 이미지 생성기
대본 → 분석 → 초단위 분할 → 프롬프트 생성 → 이미지 생성
Gemini API + Freepik API 지원
"""

import streamlit as st
import io
import zipfile
import base64
import time
import re
import requests

# ─────────────────────────────────────────────
# 기본 스타일 가이드 (디폴트값)
# ─────────────────────────────────────────────
DEFAULT_STYLE_GUIDE = r"""💎 Gems 시스템 지침 (System Instructions) - [Simple & Economic Focus Ver 7.0]

당신은 '2D 스틱맨 애니메이션 전문 프롬프트 디렉터'입니다.

🎨 스타일 가이드 (Style Lock)

1. 비주얼 정의 (Visuals)
 캐릭터: Pure-white round faces, single hard cel shading(턱 아래 1단 그림자), thick black outline, thicker torso and neck, stick limbs, flat matte colors.
 배경: 저채도 평면 블록(Low saturation flat blocks), 글자 절대 금지.
 네거티브(내재): 3D, photoreal, gradient, soft light, text, letters, speech bubble.

2. 장면 해석 (Scene Interpretation)
 행동 중심: 감정은 눈썹/입선으로, 동작은 명확한 동사(leans, points, nods, clasps, gestures)로 표현.
 경제 개념 시각화: 추상적 개념은 인물+아이콘/도형으로 변환.
     상승/하락 → 화살표 아이콘(Arrow icons)
     데이터/실적 → 차트 도형, 기어, 지도 핀 (Chart shapes, Gears, Map pins)
     계약/문서 → 빈 종이 아이콘 (Blank paper icons)
     주의: 모든 간판, 화면, 문서에 글자(Text) 대신 기호/도형만 사용.

📝 출력 템플릿 (Output Template)

모든 프롬프트는 반드시 아래 문장으로 시작해야 합니다. 대괄호 [...] 부분만 장면에 맞춰 영문으로 작성하세요.

> Upgraded stick-man 2D with thick black outline, pure white faces, single hard cel shading, thicker torso and neck, flat matte colors; SCENE: [행동 및 아이콘 묘사 (영문) + no text/letters 강조]
"""

# 언어별 프롬프트 지시문
LANGUAGE_INSTRUCTIONS = {
    "영어 (English)": "Write ALL prompts entirely in English.",
    "한국어 (Korean)": "Write ALL prompts entirely in Korean (한국어). Use Korean for all scene descriptions.",
    "日本語 (Japanese)": "Write ALL prompts entirely in Japanese (日本語). Use Japanese for all scene descriptions.",
    "언어 없음 (No Language)": "Do NOT include any text, words, or language in the image. The image must contain zero text, zero letters, zero words in any language. Only visual elements.",
}

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🍌 나노바나나2 이미지 생성기",
    page_icon="🍌",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
    .stApp { font-family: 'Noto Sans KR', sans-serif; }
    .main-title {
        font-size: 2.2rem; font-weight: 900;
        background: linear-gradient(135deg, #FFD700, #FF8C00);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title { font-size: 0.95rem; color: #888; margin-bottom: 1.5rem; }
    .step-badge {
        display: inline-block; background: linear-gradient(135deg, #FFD700, #FFA500);
        color: #000; font-weight: 700; padding: 0.3rem 0.8rem;
        border-radius: 20px; font-size: 0.85rem; margin-bottom: 0.5rem;
    }
    .prompt-block {
        background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
        padding: 1rem; font-family: monospace; font-size: 0.82rem;
        color: #c9d1d9; margin-bottom: 0.5rem; white-space: pre-wrap; word-break: break-word;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session State 초기화
# ─────────────────────────────────────────────
defaults = {
    "gemini_api_key": "",
    "gemini_key_saved": False,
    "freepik_api_key": "",
    "freepik_key_saved": False,
    "script_text": "",
    "analysis": "",
    "segments": [],
    "segments_text": "",
    "segments_confirmed": False,
    "prompts": [],
    "prompts_text": "",
    "prompts_confirmed": False,
    "images": [],
    "image_prompts_used": [],
    "step": 0,
    "style_guide": DEFAULT_STYLE_GUIDE,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# 사이드바: 설정
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 설정")

    # 이미지 생성 플랫폼 선택
    st.markdown("### 🎨 이미지 생성 플랫폼")
    platform = st.radio(
        "플랫폼 선택",
        ["Gemini (나노바나나2)", "Freepik (Mystic)"],
        index=0,
        label_visibility="collapsed",
    )

    st.divider()

    # Gemini API Key
    st.markdown("### 🔑 Gemini API Key")
    gemini_input = st.text_input(
        "Gemini Key", value=st.session_state.gemini_api_key,
        type="password", placeholder="AIza...", label_visibility="collapsed",
    )
    if st.button("💾 Gemini Key 저장", use_container_width=True):
        if gemini_input.strip():
            st.session_state.gemini_api_key = gemini_input.strip()
            st.session_state.gemini_key_saved = True
            st.success("✅ Gemini Key 저장됨!")
        else:
            st.error("Key를 입력해주세요.")
    if st.session_state.gemini_key_saved:
        st.caption(f"🔐 Gemini: `{st.session_state.gemini_api_key[:8]}...`")

    st.divider()

    # Freepik API Key
    st.markdown("### 🔑 Freepik API Key")
    freepik_input = st.text_input(
        "Freepik Key", value=st.session_state.freepik_api_key,
        type="password", placeholder="fpk_...", label_visibility="collapsed",
    )
    if st.button("💾 Freepik Key 저장", use_container_width=True):
        if freepik_input.strip():
            st.session_state.freepik_api_key = freepik_input.strip()
            st.session_state.freepik_key_saved = True
            st.success("✅ Freepik Key 저장됨!")
        else:
            st.error("Key를 입력해주세요.")
    if st.session_state.freepik_key_saved:
        st.caption(f"🔐 Freepik: `{st.session_state.freepik_api_key[:8]}...`")

    st.divider()

    # 분할 설정
    st.markdown("### ✂️ 분할 설정")
    seconds_per_cut = st.select_slider(
        "컷당 초수", options=[5, 10, 15, 20, 25, 30], value=5,
        help="5초 단위로 선택 가능 (5초~30초)",
    )
    chars_per_second = st.slider("1초당 글자 수", 3.0, 6.0, 4.5, 0.5)
    chars_per_cut = int(seconds_per_cut * chars_per_second)
    st.info(f"📐 **{seconds_per_cut}초** × {chars_per_second}자 = 컷당 약 **{chars_per_cut}자**")

    st.divider()

    # 언어 설정
    st.markdown("### 🌐 프롬프트 언어")
    prompt_language = st.selectbox(
        "언어 선택", list(LANGUAGE_INSTRUCTIONS.keys()), index=0,
    )

    st.divider()

    # 모델 설정
    st.markdown("### 🤖 모델 설정")
    if platform == "Gemini (나노바나나2)":
        image_model = st.selectbox(
            "Gemini 이미지 모델",
            ["gemini-3.1-flash-image-preview", "gemini-3-pro-image-preview", "gemini-2.5-flash-image"],
            index=0,
        )
        freepik_model = None
    else:
        image_model = None
        freepik_model = st.selectbox(
            "Freepik 모델",
            ["realism", "fluid", "flexible", "zen", "super_real", "editorial_portraits"],
            index=0,
            help="realism=사실적, fluid=프롬프트 충실, flexible=다용도, zen=부드러운",
        )
        freepik_aspect = st.selectbox(
            "Freepik 비율",
            ["square_1_1", "widescreen_16_9", "social_story_9_16", "classic_4_3", "traditional_3_4"],
            index=0,
        )
        freepik_resolution = st.selectbox("Freepik 해상도", ["1k", "2k", "4k"], index=1)

    text_model = st.selectbox("텍스트 분석 모델 (Gemini)", ["gemini-2.5-flash", "gemini-2.0-flash"], index=0)

    st.divider()
    if st.button("🔄 전체 초기화", use_container_width=True):
        for k, v in defaults.items():
            if k not in ("gemini_api_key", "gemini_key_saved", "freepik_api_key", "freepik_key_saved"):
                st.session_state[k] = v
        st.rerun()


# ─────────────────────────────────────────────
# Gemini API 헬퍼
# ─────────────────────────────────────────────
def get_gemini_client():
    try:
        from google import genai
        return genai.Client(api_key=st.session_state.gemini_api_key)
    except ImportError:
        st.error("❌ `google-genai` 패키지가 필요합니다.")
        return None
    except Exception as e:
        st.error(f"❌ Gemini 클라이언트 실패: {e}")
        return None


def call_text_model(client, prompt, model_name):
    try:
        response = client.models.generate_content(model=model_name, contents=[prompt])
        return response.text
    except Exception as e:
        st.error(f"❌ 텍스트 모델 호출 실패: {e}")
        return None


def generate_image_gemini(client, prompt, model_name):
    """나노바나나 계열 이미지 생성"""
    try:
        from google.genai import types
        response = client.models.generate_content(
            model=model_name, contents=[prompt],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        for part in response.parts:
            if part.inline_data is not None:
                return part.inline_data.data
        return None
    except Exception as e:
        st.error(f"❌ Gemini 이미지 생성 실패: {e}")
        return None


# ─────────────────────────────────────────────
# Freepik API 헬퍼
# ─────────────────────────────────────────────
def generate_image_freepik(prompt, model, aspect_ratio, resolution):
    """Freepik Mystic API로 이미지 생성 (비동기: 생성요청 → 폴링)"""
    api_key = st.session_state.freepik_api_key
    headers = {
        "x-freepik-api-key": api_key,
        "Content-Type": "application/json",
    }

    # 1) 생성 요청
    payload = {
        "prompt": prompt,
        "model": model,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "filter_nsfw": True,
    }

    try:
        resp = requests.post(
            "https://api.freepik.com/v1/ai/mystic",
            headers=headers, json=payload, timeout=30,
        )
        if resp.status_code != 200:
            st.error(f"❌ Freepik 요청 실패 ({resp.status_code}): {resp.text[:200]}")
            return None

        data = resp.json().get("data", {})
        task_id = data.get("task_id")
        if not task_id:
            st.error("❌ Freepik task_id를 받지 못했습니다.")
            return None

    except Exception as e:
        st.error(f"❌ Freepik 요청 오류: {e}")
        return None

    # 2) 폴링 (최대 60초)
    for attempt in range(30):
        time.sleep(2)
        try:
            poll_resp = requests.get(
                f"https://api.freepik.com/v1/ai/mystic/{task_id}",
                headers={"x-freepik-api-key": api_key}, timeout=15,
            )
            if poll_resp.status_code != 200:
                continue

            poll_data = poll_resp.json().get("data", {})
            status = poll_data.get("status", "")

            if status == "COMPLETED":
                generated = poll_data.get("generated", [])
                if generated:
                    # URL에서 이미지 다운로드
                    img_url = generated[0]
                    img_resp = requests.get(img_url, timeout=30)
                    if img_resp.status_code == 200:
                        return img_resp.content
                return None

            elif status in ("FAILED", "ERROR"):
                st.error(f"❌ Freepik 생성 실패: {status}")
                return None

        except Exception:
            continue

    st.error("❌ Freepik 시간 초과 (60초)")
    return None


# ─────────────────────────────────────────────
# 대본 분할 함수
# ─────────────────────────────────────────────
def split_script_locally(script_text, max_chars):
    lines = [line.strip() for line in script_text.strip().split("\n") if line.strip()]
    full_text = " ".join(lines)

    sentences = re.split(r'(?<=[.?!。])\s*', full_text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) <= 1 and len(full_text) > max_chars:
        sentences = re.split(r'(?<=[,，、])\s*', full_text)
        sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) <= 1 and len(full_text) > max_chars:
        return [full_text[i:i + max_chars] for i in range(0, len(full_text), max_chars)]

    segments = []
    current = ""
    threshold = max_chars * 1.3

    for sentence in sentences:
        test_len = len(current) + len(sentence) + (1 if current else 0)
        if test_len <= threshold:
            current = (current + " " + sentence).strip() if current else sentence
        else:
            if current:
                segments.append(current)
            if len(sentence) > threshold:
                sub_parts = re.split(r'(?<=[,，、])\s*', sentence)
                sub_current = ""
                for sp in sub_parts:
                    if len(sub_current) + len(sp) + 1 <= threshold:
                        sub_current = (sub_current + " " + sp).strip() if sub_current else sp
                    else:
                        if sub_current:
                            segments.append(sub_current)
                        sub_current = sp
                current = sub_current if sub_current else ""
            else:
                current = sentence

    if current:
        segments.append(current)
    return segments


# ─────────────────────────────────────────────
# 메인 영역
# ─────────────────────────────────────────────
st.markdown('<div class="main-title">🍌 나노바나나2 이미지 생성기</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">대본 → 분석 → 초단위 분할 → 프롬프트 생성 → 이미지 자동 생성 (Gemini / Freepik)</div>', unsafe_allow_html=True)

# API Key 체크
if platform == "Gemini (나노바나나2)" and not st.session_state.gemini_api_key:
    st.warning("⚠️ 사이드바에서 Gemini API Key를 입력해주세요.")
    st.stop()
elif platform == "Freepik (Mystic)" and not st.session_state.freepik_api_key:
    st.warning("⚠️ 사이드바에서 Freepik API Key를 입력해주세요.")
    if not st.session_state.gemini_api_key:
        st.warning("⚠️ 텍스트 분석용 Gemini API Key도 필요합니다.")
    st.stop()

# Gemini key는 텍스트 분석에 항상 필요
if not st.session_state.gemini_api_key:
    st.warning("⚠️ 텍스트 분석을 위해 Gemini API Key가 필요합니다.")
    st.stop()

# ─── 탭 구성 ───
tab_guide, tab_script, tab_result = st.tabs(["📝 스타일 가이드", "🎬 대본 입력 & 처리", "🖼️ 생성된 이미지"])

# ═══════════════════════════════════════════════
# 탭1: 스타일 가이드
# ═══════════════════════════════════════════════
with tab_guide:
    st.markdown("### 이미지 프롬프트 스타일 가이드")
    st.caption("이미지 프롬프트 생성 시 참조됩니다. 자유롭게 수정하세요.")
    edited_guide = st.text_area(
        "스타일 가이드 편집", value=st.session_state.style_guide,
        height=500, label_visibility="collapsed",
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 스타일 가이드 저장", use_container_width=True):
            st.session_state.style_guide = edited_guide
            st.success("✅ 저장됨!")
    with c2:
        if st.button("🔄 기본값으로 복원", use_container_width=True):
            st.session_state.style_guide = DEFAULT_STYLE_GUIDE
            st.rerun()

# ═══════════════════════════════════════════════
# 탭2: 대본 입력 & 4단계 처리
# ═══════════════════════════════════════════════
with tab_script:

    st.markdown("### 📄 대본 입력")
    script_input = st.text_area(
        "대본 입력", value=st.session_state.script_text, height=200,
        placeholder="대본을 여기에 붙여넣으세요...", label_visibility="collapsed",
    )

    if st.button("🚀 분석 시작", use_container_width=True, type="primary"):
        if not script_input.strip():
            st.error("대본을 입력해주세요.")
        else:
            st.session_state.script_text = script_input.strip()
            st.session_state.analysis = ""
            st.session_state.segments = []
            st.session_state.segments_confirmed = False
            st.session_state.prompts = []
            st.session_state.prompts_confirmed = False
            st.session_state.images = []
            st.session_state.image_prompts_used = []
            st.session_state.step = 1
            st.rerun()

    # ═══ STEP 1: 대본 분석 ═══
    if st.session_state.step >= 1 and st.session_state.script_text:
        st.divider()
        st.markdown('<span class="step-badge">STEP 1</span> **대본 분석**', unsafe_allow_html=True)

        if not st.session_state.analysis:
            with st.spinner("🔍 대본을 분석하는 중..."):
                client = get_gemini_client()
                if client:
                    analysis_prompt = f"""다음 유튜브 대본을 분석해주세요.

[분석 항목]
1. 핵심 주제 (1줄 요약)
2. 전체 톤/분위기
3. 주요 등장 요소 (인물, 개념, 오브젝트)
4. 예상 타겟 시청자
5. 총 글자 수: {len(st.session_state.script_text)}자

[대본]
{st.session_state.script_text}

간결하게 한국어로 답변해주세요."""
                    result = call_text_model(client, analysis_prompt, text_model)
                    if result:
                        st.session_state.analysis = result
                        st.session_state.step = 2
                        st.rerun()

        if st.session_state.analysis:
            with st.expander("📊 분석 결과", expanded=True):
                st.markdown(st.session_state.analysis)

    # ═══ STEP 2: 초단위 분할 ═══
    if st.session_state.step >= 2:
        st.divider()
        st.markdown(
            f'<span class="step-badge">STEP 2</span> **초단위 분할** ({seconds_per_cut}초 / 컷당 {chars_per_cut}자)',
            unsafe_allow_html=True,
        )

        if not st.session_state.segments:
            with st.spinner("✂️ 대본을 분할하는 중..."):
                segs = split_script_locally(st.session_state.script_text, chars_per_cut)
                st.session_state.segments = segs
                st.session_state.segments_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(segs)])
                st.rerun()

        if st.session_state.segments and not st.session_state.segments_confirmed:
            st.caption(f"총 **{len(st.session_state.segments)}**개 장면 ({seconds_per_cut}초 기준). 수정 후 확정하세요.")
            edited_segments = st.text_area(
                "분할 편집", value=st.session_state.segments_text,
                height=300, label_visibility="collapsed",
            )
            col_re, col_confirm = st.columns(2)
            with col_re:
                if st.button("🔄 다시 분할", use_container_width=True):
                    st.session_state.segments = []
                    st.session_state.segments_text = ""
                    st.rerun()
            with col_confirm:
                if st.button("✅ 분할 확정 → 프롬프트 생성", use_container_width=True, type="primary"):
                    lines = [l.strip() for l in edited_segments.strip().split("\n") if l.strip()]
                    parsed = [re.sub(r'^\d+[\.\)]\s*', '', l) for l in lines]
                    parsed = [p for p in parsed if p]
                    st.session_state.segments = parsed
                    st.session_state.segments_text = edited_segments
                    st.session_state.segments_confirmed = True
                    st.session_state.step = 3
                    st.rerun()

        if st.session_state.segments_confirmed:
            with st.expander(f"✅ 확정된 분할 ({len(st.session_state.segments)}개)", expanded=False):
                for i, seg in enumerate(st.session_state.segments):
                    st.markdown(f"**{i+1}.** {seg}")

    # ═══ STEP 3: 이미지 프롬프트 생성 ═══
    if st.session_state.step >= 3 and st.session_state.segments_confirmed:
        st.divider()
        lang_label = prompt_language.split("(")[0].strip()
        st.markdown(
            f'<span class="step-badge">STEP 3</span> **이미지 프롬프트 생성** (언어: {lang_label})',
            unsafe_allow_html=True,
        )

        if not st.session_state.prompts:
            with st.spinner("🎨 프롬프트를 생성하는 중..."):
                client = get_gemini_client()
                if client:
                    seg_list = "\n".join([f"{i+1}. {s}" for i, s in enumerate(st.session_state.segments)])
                    lang_instruction = LANGUAGE_INSTRUCTIONS[prompt_language]

                    prompt_gen = f"""당신은 이미지 생성 프롬프트 전문가입니다.

[스타일 가이드]
{st.session_state.style_guide}

[언어 지시]
{lang_instruction}

[분할된 장면 목록]
{seg_list}

[작업]
위 장면 목록의 각 번호에 대해 이미지 생성용 프롬프트를 작성하세요.

[출력 규칙]
1. 각 프롬프트는 스타일 가이드의 출력 템플릿을 따릅니다.
2. 반드시 번호를 유지하세요: "1) ...", "2) ...", "3) ..." 형식.
3. 각 프롬프트만 출력하세요. 설명이나 부가 텍스트 없이 프롬프트만.
4. {lang_instruction}
5. 총 {len(st.session_state.segments)}개의 프롬프트를 출력하세요."""

                    result = call_text_model(client, prompt_gen, text_model)
                    if result:
                        lines = result.strip().split("\n")
                        prompts_parsed = []
                        current_prompt = ""
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            if re.match(r'^\d+[\)\.]', line):
                                if current_prompt:
                                    prompts_parsed.append(current_prompt)
                                current_prompt = re.sub(r'^\d+[\)\.\s]+', '', line).strip().strip('"\'')
                            else:
                                current_prompt += " " + line.strip().strip('"\'')
                        if current_prompt:
                            prompts_parsed.append(current_prompt)

                        st.session_state.prompts = prompts_parsed
                        st.session_state.prompts_text = "\n\n".join(
                            [f"{i+1}) {p}" for i, p in enumerate(prompts_parsed)]
                        )
                        st.rerun()

        if st.session_state.prompts and not st.session_state.prompts_confirmed:
            st.caption(f"총 **{len(st.session_state.prompts)}**개 프롬프트. 수정 후 확정하세요.")
            edited_prompts = st.text_area(
                "프롬프트 편집", value=st.session_state.prompts_text,
                height=400, label_visibility="collapsed",
            )
            col_re2, col_confirm2 = st.columns(2)
            with col_re2:
                if st.button("🔄 프롬프트 재생성", use_container_width=True):
                    st.session_state.prompts = []
                    st.session_state.prompts_text = ""
                    st.rerun()
            with col_confirm2:
                if st.button("✅ 프롬프트 확정 → 이미지 생성", use_container_width=True, type="primary"):
                    blocks = re.split(r'\n\s*(?=\d+[\)\.])', edited_prompts.strip())
                    parsed_prompts = []
                    for block in blocks:
                        block = block.strip()
                        if not block:
                            continue
                        cleaned = re.sub(r'^\d+[\)\.\s]+', '', block).strip().strip('"\'')
                        if cleaned:
                            parsed_prompts.append(cleaned)
                    st.session_state.prompts = parsed_prompts
                    st.session_state.prompts_text = edited_prompts
                    st.session_state.prompts_confirmed = True
                    st.session_state.step = 4
                    st.rerun()

        if st.session_state.prompts_confirmed:
            with st.expander(f"✅ 확정된 프롬프트 ({len(st.session_state.prompts)}개)", expanded=False):
                for i, p in enumerate(st.session_state.prompts):
                    st.markdown(f'<div class="prompt-block"><b>{i+1})</b> {p}</div>', unsafe_allow_html=True)

    # ═══ STEP 4: 이미지 생성 ═══
    if st.session_state.step >= 4 and st.session_state.prompts_confirmed:
        st.divider()
        platform_label = "Gemini 나노바나나2" if platform == "Gemini (나노바나나2)" else "Freepik Mystic"
        st.markdown(
            f'<span class="step-badge">STEP 4</span> **이미지 생성** ({platform_label})',
            unsafe_allow_html=True,
        )

        if not st.session_state.images:
            total = len(st.session_state.prompts)
            progress_bar = st.progress(0, text=f"이미지 생성 준비 중... (0/{total})")
            images_result = []
            prompts_used = []
            status_container = st.empty()

            if platform == "Gemini (나노바나나2)":
                client = get_gemini_client()
                if client:
                    for i, prompt_text in enumerate(st.session_state.prompts):
                        status_container.info(f"🎨 {i+1}/{total} Gemini로 생성 중...")
                        progress_bar.progress(i / total, text=f"생성 중... ({i}/{total})")

                        img_data = generate_image_gemini(client, prompt_text, image_model)

                        if img_data is not None:
                            if isinstance(img_data, bytes):
                                images_result.append(img_data)
                            else:
                                try:
                                    images_result.append(base64.b64decode(img_data))
                                except Exception:
                                    images_result.append(img_data)
                        else:
                            images_result.append(None)
                        prompts_used.append(prompt_text)

                        if i < total - 1:
                            time.sleep(2)

            else:  # Freepik
                for i, prompt_text in enumerate(st.session_state.prompts):
                    status_container.info(f"🎨 {i+1}/{total} Freepik으로 생성 중... (최대 60초 소요)")
                    progress_bar.progress(i / total, text=f"생성 중... ({i}/{total})")

                    img_data = generate_image_freepik(
                        prompt_text, freepik_model, freepik_aspect, freepik_resolution
                    )

                    images_result.append(img_data)
                    prompts_used.append(prompt_text)

                    if i < total - 1:
                        time.sleep(1)

            progress_bar.progress(1.0, text=f"✅ 완료! ({total}/{total})")
            valid = sum(1 for x in images_result if x is not None)
            status_container.success(f"✅ 총 {valid}개 이미지 생성 완료!")

            st.session_state.images = images_result
            st.session_state.image_prompts_used = prompts_used
            st.rerun()

        if st.session_state.images:
            valid = sum(1 for x in st.session_state.images if x is not None)
            st.success(f"✅ {valid}개 이미지 생성됨! '🖼️ 생성된 이미지' 탭에서 확인하세요!")


# ═══════════════════════════════════════════════
# 탭3: 생성된 이미지
# ═══════════════════════════════════════════════
with tab_result:
    if not st.session_state.images:
        st.info("아직 생성된 이미지가 없습니다. '🎬 대본 입력 & 처리' 탭에서 작업을 진행해주세요.")
    else:
        images = st.session_state.images
        prompts_used = st.session_state.image_prompts_used
        segments = st.session_state.segments

        valid_count = sum(1 for x in images if x is not None)
        st.markdown(f"### 🖼️ 생성된 이미지 ({valid_count}개)")

        # ZIP 다운로드
        if valid_count > 0:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for i, img in enumerate(images):
                    if img is not None:
                        zf.writestr(f"scene_{i+1:03d}.png", img)
                prompt_txt = "\n\n".join([
                    f"[Scene {i+1}]\nScript: {segments[i] if i < len(segments) else ''}\nPrompt: {prompts_used[i] if i < len(prompts_used) else ''}"
                    for i in range(len(images))
                ])
                zf.writestr("prompts.txt", prompt_txt)
            zip_buffer.seek(0)

            st.download_button(
                label="📦 전체 이미지 ZIP 다운로드",
                data=zip_buffer.getvalue(),
                file_name="nanobana_images.zip",
                mime="application/zip",
                use_container_width=True,
            )

        st.divider()

        # 이미지 그리드 (2열)
        for row_start in range(0, len(images), 2):
            cols = st.columns(2)
            for col_idx in range(2):
                img_idx = row_start + col_idx
                if img_idx >= len(images):
                    break
                with cols[col_idx]:
                    img_data = images[img_idx]
                    st.markdown(f"**장면 {img_idx + 1}**")

                    if img_data is not None:
                        st.image(img_data, use_container_width=True)
                        st.download_button(
                            label="💾 다운로드", data=img_data,
                            file_name=f"scene_{img_idx+1:03d}.png",
                            mime="image/png", key=f"dl_{img_idx}",
                            use_container_width=True,
                        )
                    else:
                        st.error("⚠️ 생성 실패")

                    if img_idx < len(segments):
                        st.caption(f"📄 {segments[img_idx]}")
                    if img_idx < len(prompts_used):
                        with st.expander("프롬프트 보기"):
                            st.code(prompts_used[img_idx], language=None)
