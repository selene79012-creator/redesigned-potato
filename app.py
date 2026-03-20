"""
🍌 나노바나나2 이미지 생성기
대본 → 분석 → 초단위 분할 → 프롬프트 생성 → 이미지 생성
Gemini API + Freepik API (Mystic / Seedream / Flux / Nano Banana 등) 지원
"""

import streamlit as st
import io
import zipfile
import base64
import time
import re
import requests

# ─────────────────────────────────────────────
# Freepik 모델 정보
# ─────────────────────────────────────────────
FREEPIK_MODELS = {
    # ── Mystic (Freepik 자체) ──
    "Mystic - Realism": {
        "endpoint": "/v1/ai/mystic",
        "type": "mystic",
        "params": {"model": "realism"},
        "desc": "사실적 이미지, AI 느낌 최소화",
    },
    "Mystic - Fluid (Imagen 3)": {
        "endpoint": "/v1/ai/mystic",
        "type": "mystic",
        "params": {"model": "fluid"},
        "desc": "프롬프트 충실도 최고, Google Imagen 3 기반",
    },
    "Mystic - Flexible": {
        "endpoint": "/v1/ai/mystic",
        "type": "mystic",
        "params": {"model": "flexible"},
        "desc": "일러스트/판타지에 강함, 다용도",
    },
    "Mystic - Zen": {
        "endpoint": "/v1/ai/mystic",
        "type": "mystic",
        "params": {"model": "zen"},
        "desc": "부드럽고 깔끔한 결과물",
    },
    "Mystic - Super Real": {
        "endpoint": "/v1/ai/mystic",
        "type": "mystic",
        "params": {"model": "super_real"},
        "desc": "극사실주의 특화",
    },
    # ── Seedream (ByteDance) ──
    "Seedream 4.5": {
        "endpoint": "/v1/ai/text-to-image/seedream-v4-5",
        "type": "standard",
        "params": {},
        "desc": "포스터/타이포그래피 최강, 4K 지원",
    },
    "Seedream 4.0": {
        "endpoint": "/v1/ai/text-to-image/seedream-v4",
        "type": "standard",
        "params": {},
        "desc": "차세대 텍스트-이미지, 고품질",
    },
    "Seedream 3.0": {
        "endpoint": "/v1/ai/text-to-image/seedream",
        "type": "standard",
        "params": {},
        "desc": "빠른 생성, 다양한 스타일",
    },
    # ── Flux (Black Forest Labs) ──
    "Flux 2 Pro": {
        "endpoint": "/v1/ai/text-to-image/flux-2-pro",
        "type": "standard",
        "params": {},
        "desc": "스타일 표현력 최고, 아트 디렉션",
    },
    "Flux 1.1": {
        "endpoint": "/v1/ai/text-to-image/flux-1.1",
        "type": "standard",
        "params": {},
        "desc": "범용 고품질 모델",
    },
    "HyperFlux": {
        "endpoint": "/v1/ai/text-to-image/hyperflux",
        "type": "standard",
        "params": {},
        "desc": "초고속 생성",
    },
    # ── Google (via Freepik) ──
    "Nano Banana (Gemini Flash)": {
        "endpoint": "/v1/ai/text-to-image/nano-banana",
        "type": "standard",
        "params": {},
        "desc": "Google 나노바나나, 빠르고 직관적",
    },
    "Nano Banana Pro": {
        "endpoint": "/v1/ai/text-to-image/nano-banana-pro",
        "type": "standard",
        "params": {},
        "desc": "Google 나노바나나 Pro, 최고 품질",
    },
    "Imagen 4": {
        "endpoint": "/v1/ai/text-to-image/imagen-4",
        "type": "standard",
        "params": {},
        "desc": "Google Imagen 4, 고해상도",
    },
    # ── Runway ──
    "Runway Gen4": {
        "endpoint": "/v1/ai/text-to-image/runway",
        "type": "standard",
        "params": {},
        "desc": "Runway Gen4 이미지 생성",
    },
    # ── Classic Fast ──
    "Classic Fast": {
        "endpoint": "/v1/ai/text-to-image",
        "type": "standard",
        "params": {},
        "desc": "Freepik 기본 빠른 생성",
    },
}

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

📝 출력 템플릿 (Output Template)

> Upgraded stick-man 2D with thick black outline, pure white faces, single hard cel shading, thicker torso and neck, flat matte colors; SCENE: [행동 및 아이콘 묘사 (영문) + no text/letters 강조]
"""

LANGUAGE_INSTRUCTIONS = {
    "영어 (English)": "Write ALL prompts entirely in English.",
    "한국어 (Korean)": "Write ALL prompts entirely in Korean (한국어).",
    "日本語 (Japanese)": "Write ALL prompts entirely in Japanese (日本語).",
    "언어 없음 (No Language)": "Do NOT include any text or words. Only visual elements, no text/letters.",
}

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(page_title="🍌 이미지 생성기", page_icon="🍌", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
    .stApp { font-family: 'Noto Sans KR', sans-serif; }
    .main-title { font-size: 2.2rem; font-weight: 900; background: linear-gradient(135deg, #FFD700, #FF8C00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.2rem; }
    .sub-title { font-size: 0.95rem; color: #888; margin-bottom: 1.5rem; }
    .step-badge { display: inline-block; background: linear-gradient(135deg, #FFD700, #FFA500); color: #000; font-weight: 700; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.85rem; margin-bottom: 0.5rem; }
    .prompt-block { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 1rem; font-family: monospace; font-size: 0.82rem; color: #c9d1d9; margin-bottom: 0.5rem; white-space: pre-wrap; word-break: break-word; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────
defaults = {
    "gemini_api_key": "", "gemini_key_saved": False,
    "freepik_api_key": "", "freepik_key_saved": False,
    "script_text": "", "analysis": "",
    "segments": [], "segments_text": "", "segments_confirmed": False,
    "prompts": [], "prompts_text": "", "prompts_confirmed": False,
    "images": [], "image_prompts_used": [], "step": 0,
    "style_guide": DEFAULT_STYLE_GUIDE,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 설정")

    # 플랫폼 선택
    st.markdown("### 🎨 이미지 생성 플랫폼")
    platform = st.radio("플랫폼", ["Gemini (직접)", "Freepik (다중 모델)"], index=1, label_visibility="collapsed")

    st.divider()

    # API Keys
    st.markdown("### 🔑 API Keys")
    g_input = st.text_input("Gemini Key", value=st.session_state.gemini_api_key, type="password", placeholder="AIza...", label_visibility="collapsed")
    if st.button("💾 Gemini Key 저장", use_container_width=True):
        if g_input.strip():
            st.session_state.gemini_api_key = g_input.strip()
            st.session_state.gemini_key_saved = True
            st.success("✅ 저장!")
    if st.session_state.gemini_key_saved:
        st.caption(f"🔐 Gemini: `{st.session_state.gemini_api_key[:8]}...`")

    f_input = st.text_input("Freepik Key", value=st.session_state.freepik_api_key, type="password", placeholder="fpk_...", label_visibility="collapsed")
    if st.button("💾 Freepik Key 저장", use_container_width=True):
        if f_input.strip():
            st.session_state.freepik_api_key = f_input.strip()
            st.session_state.freepik_key_saved = True
            st.success("✅ 저장!")
    if st.session_state.freepik_key_saved:
        st.caption(f"🔐 Freepik: `{st.session_state.freepik_api_key[:8]}...`")

    st.divider()

    # 분할 설정
    st.markdown("### ✂️ 분할 설정")
    seconds_per_cut = st.select_slider("컷당 초수", options=[5, 10, 15, 20, 25, 30], value=5)
    chars_per_second = st.slider("1초당 글자 수", 3.0, 6.0, 4.5, 0.5)
    chars_per_cut = int(seconds_per_cut * chars_per_second)
    st.info(f"📐 **{seconds_per_cut}초** × {chars_per_second}자 = **{chars_per_cut}자**/컷")

    st.divider()

    # 언어
    st.markdown("### 🌐 프롬프트 언어")
    prompt_language = st.selectbox("언어", list(LANGUAGE_INSTRUCTIONS.keys()), index=0)

    st.divider()

    # 모델 설정
    st.markdown("### 🤖 이미지 모델")
    if platform == "Gemini (직접)":
        gemini_image_model = st.selectbox("Gemini 모델", ["gemini-3.1-flash-image-preview", "gemini-3-pro-image-preview", "gemini-2.5-flash-image"], index=0)
        selected_freepik_model = None
    else:
        model_names = list(FREEPIK_MODELS.keys())
        selected_freepik_model = st.selectbox(
            "Freepik 모델",
            model_names,
            index=model_names.index("Nano Banana (Gemini Flash)") if "Nano Banana (Gemini Flash)" in model_names else 0,
            help="모델별 특성은 설명을 참고하세요",
        )
        st.caption(f"ℹ️ {FREEPIK_MODELS[selected_freepik_model]['desc']}")
        gemini_image_model = None

        # Freepik 공통 설정
        fp_aspect = st.selectbox("비율", ["square_1_1", "widescreen_16_9", "social_story_9_16", "classic_4_3", "traditional_3_4", "standard_3_2", "portrait_2_3"], index=1)

        model_info = FREEPIK_MODELS[selected_freepik_model]
        if model_info["type"] == "mystic":
            fp_resolution = st.selectbox("해상도", ["1k", "2k", "4k"], index=1)
        else:
            fp_resolution = "2k"

    text_model = st.selectbox("텍스트 분석 (Gemini)", ["gemini-2.5-flash", "gemini-2.0-flash"], index=0)

    st.divider()
    if st.button("🔄 전체 초기화", use_container_width=True):
        for k, v in defaults.items():
            if k not in ("gemini_api_key", "gemini_key_saved", "freepik_api_key", "freepik_key_saved"):
                st.session_state[k] = v
        st.rerun()


# ─────────────────────────────────────────────
# API 헬퍼 함수들
# ─────────────────────────────────────────────
def get_gemini_client():
    try:
        from google import genai
        return genai.Client(api_key=st.session_state.gemini_api_key)
    except Exception as e:
        st.error(f"❌ Gemini 클라이언트 실패: {e}")
        return None

def call_text_model(client, prompt, model_name):
    try:
        return client.models.generate_content(model=model_name, contents=[prompt]).text
    except Exception as e:
        st.error(f"❌ 텍스트 모델 실패: {e}")
        return None

def generate_image_gemini(client, prompt, model_name):
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
        st.error(f"❌ Gemini 이미지 실패: {e}")
        return None


def generate_image_freepik(prompt, model_key, aspect_ratio, resolution):
    """Freepik API 이미지 생성 - Mystic(비동기) / Standard(비동기) 모두 지원"""
    api_key = st.session_state.freepik_api_key
    headers = {"x-freepik-api-key": api_key, "Content-Type": "application/json"}
    model_info = FREEPIK_MODELS[model_key]
    endpoint = model_info["endpoint"]
    url = f"https://api.freepik.com{endpoint}"

    # 페이로드 구성
    payload = {"prompt": prompt}

    if model_info["type"] == "mystic":
        payload.update(model_info["params"])
        payload["aspect_ratio"] = aspect_ratio
        payload["resolution"] = resolution
        payload["filter_nsfw"] = True
    else:
        payload["aspect_ratio"] = aspect_ratio

    # 1) 생성 요청
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code not in (200, 201):
            st.error(f"❌ Freepik 요청 실패 ({resp.status_code}): {resp.text[:300]}")
            return None

        data = resp.json().get("data", {})

        # 즉시 완료된 경우 (generated에 URL이 이미 있을 수 있음)
        generated = data.get("generated", [])
        if generated and isinstance(generated[0], str) and generated[0].startswith("http"):
            img_resp = requests.get(generated[0], timeout=30)
            if img_resp.status_code == 200:
                return img_resp.content

        task_id = data.get("task_id")
        if not task_id:
            st.error("❌ task_id 없음")
            return None

    except Exception as e:
        st.error(f"❌ Freepik 요청 오류: {e}")
        return None

    # 2) 폴링 (최대 90초)
    poll_url = f"{url}/{task_id}" if model_info["type"] == "mystic" else f"https://api.freepik.com{endpoint}/{task_id}"

    for _ in range(45):
        time.sleep(2)
        try:
            poll_resp = requests.get(poll_url, headers={"x-freepik-api-key": api_key}, timeout=15)
            if poll_resp.status_code != 200:
                continue
            poll_data = poll_resp.json().get("data", {})
            status = poll_data.get("status", "")

            if status == "COMPLETED":
                gen = poll_data.get("generated", [])
                if gen:
                    img_url = gen[0] if isinstance(gen[0], str) else gen[0].get("url", "")
                    if img_url:
                        img_resp = requests.get(img_url, timeout=30)
                        if img_resp.status_code == 200:
                            return img_resp.content
                return None
            elif status in ("FAILED", "ERROR"):
                st.error(f"❌ Freepik 생성 실패: {status}")
                return None
        except Exception:
            continue

    st.error("❌ Freepik 시간 초과")
    return None


# ─────────────────────────────────────────────
# 대본 분할
# ─────────────────────────────────────────────
def split_script_locally(script_text, max_chars):
    lines = [l.strip() for l in script_text.strip().split("\n") if l.strip()]
    full_text = " ".join(lines)
    sentences = re.split(r'(?<=[.?!。])\s*', full_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) <= 1 and len(full_text) > max_chars:
        sentences = re.split(r'(?<=[,，、])\s*', full_text)
        sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) <= 1 and len(full_text) > max_chars:
        return [full_text[i:i + max_chars] for i in range(0, len(full_text), max_chars)]
    segments, current, threshold = [], "", max_chars * 1.3
    for sentence in sentences:
        if len(current) + len(sentence) + (1 if current else 0) <= threshold:
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
                        if sub_current: segments.append(sub_current)
                        sub_current = sp
                current = sub_current or ""
            else:
                current = sentence
    if current:
        segments.append(current)
    return segments


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
st.markdown('<div class="main-title">🍌 이미지 생성기</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">대본 → 분석 → 분할 → 프롬프트 → 이미지 (Gemini / Freepik 다중 모델)</div>', unsafe_allow_html=True)

if not st.session_state.gemini_api_key:
    st.warning("⚠️ 텍스트 분석용 Gemini API Key를 사이드바에서 입력해주세요.")
    st.stop()
if platform == "Freepik (다중 모델)" and not st.session_state.freepik_api_key:
    st.warning("⚠️ Freepik API Key를 사이드바에서 입력해주세요.")
    st.stop()

tab_guide, tab_script, tab_result = st.tabs(["📝 스타일 가이드", "🎬 대본 입력 & 처리", "🖼️ 생성된 이미지"])

# ═══ 탭1: 스타일 가이드 ═══
with tab_guide:
    st.markdown("### 이미지 프롬프트 스타일 가이드")
    edited_guide = st.text_area("편집", value=st.session_state.style_guide, height=500, label_visibility="collapsed")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 저장", use_container_width=True):
            st.session_state.style_guide = edited_guide
            st.success("✅ 저장!")
    with c2:
        if st.button("🔄 기본값 복원", use_container_width=True):
            st.session_state.style_guide = DEFAULT_STYLE_GUIDE
            st.rerun()

# ═══ 탭2: 대본 & 처리 ═══
with tab_script:
    st.markdown("### 📄 대본 입력")
    script_input = st.text_area("대본", value=st.session_state.script_text, height=200, placeholder="대본 붙여넣기...", label_visibility="collapsed")

    if st.button("🚀 분석 시작", use_container_width=True, type="primary"):
        if script_input.strip():
            st.session_state.script_text = script_input.strip()
            for k in ("analysis", "segments_text", "prompts_text"):
                st.session_state[k] = ""
            for k in ("segments", "prompts", "images", "image_prompts_used"):
                st.session_state[k] = []
            for k in ("segments_confirmed", "prompts_confirmed"):
                st.session_state[k] = False
            st.session_state.step = 1
            st.rerun()

    # STEP 1
    if st.session_state.step >= 1 and st.session_state.script_text:
        st.divider()
        st.markdown('<span class="step-badge">STEP 1</span> **대본 분석**', unsafe_allow_html=True)
        if not st.session_state.analysis:
            with st.spinner("🔍 분석 중..."):
                client = get_gemini_client()
                if client:
                    r = call_text_model(client, f"다음 대본을 분석해주세요.\n[항목] 1.핵심주제 2.톤 3.등장요소 4.타겟 5.글자수:{len(st.session_state.script_text)}자\n[대본]\n{st.session_state.script_text}\n간결히 한국어로.", text_model)
                    if r:
                        st.session_state.analysis = r
                        st.session_state.step = 2
                        st.rerun()
        if st.session_state.analysis:
            with st.expander("📊 분석 결과", expanded=True):
                st.markdown(st.session_state.analysis)

    # STEP 2
    if st.session_state.step >= 2:
        st.divider()
        st.markdown(f'<span class="step-badge">STEP 2</span> **분할** ({seconds_per_cut}초/{chars_per_cut}자)', unsafe_allow_html=True)
        if not st.session_state.segments:
            segs = split_script_locally(st.session_state.script_text, chars_per_cut)
            st.session_state.segments = segs
            st.session_state.segments_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(segs)])
            st.rerun()
        if st.session_state.segments and not st.session_state.segments_confirmed:
            st.caption(f"**{len(st.session_state.segments)}**개 장면")
            ed = st.text_area("편집", value=st.session_state.segments_text, height=300, label_visibility="collapsed", key="seg_edit")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 다시 분할", use_container_width=True):
                    st.session_state.segments = []
                    st.rerun()
            with c2:
                if st.button("✅ 확정 → 프롬프트", use_container_width=True, type="primary"):
                    parsed = [re.sub(r'^\d+[\.\)]\s*', '', l).strip() for l in ed.strip().split("\n") if l.strip()]
                    st.session_state.segments = [p for p in parsed if p]
                    st.session_state.segments_confirmed = True
                    st.session_state.step = 3
                    st.rerun()
        if st.session_state.segments_confirmed:
            with st.expander(f"✅ 분할 확정 ({len(st.session_state.segments)}개)", expanded=False):
                for i, s in enumerate(st.session_state.segments):
                    st.markdown(f"**{i+1}.** {s}")

    # STEP 3
    if st.session_state.step >= 3 and st.session_state.segments_confirmed:
        st.divider()
        st.markdown(f'<span class="step-badge">STEP 3</span> **프롬프트 생성**', unsafe_allow_html=True)
        if not st.session_state.prompts:
            with st.spinner("🎨 프롬프트 생성 중..."):
                client = get_gemini_client()
                if client:
                    seg_list = "\n".join([f"{i+1}. {s}" for i, s in enumerate(st.session_state.segments)])
                    lang = LANGUAGE_INSTRUCTIONS[prompt_language]
                    r = call_text_model(client, f"""이미지 프롬프트 전문가입니다.
[스타일 가이드]\n{st.session_state.style_guide}\n[언어] {lang}\n[장면]\n{seg_list}\n
[규칙] 1.스타일가이드 템플릿 따름 2.번호 유지 "1) ..." 3.프롬프트만 출력 4.{lang} 5.총 {len(st.session_state.segments)}개""", text_model)
                    if r:
                        pp, cur = [], ""
                        for line in r.strip().split("\n"):
                            line = line.strip()
                            if not line: continue
                            if re.match(r'^\d+[\)\.]', line):
                                if cur: pp.append(cur)
                                cur = re.sub(r'^\d+[\)\.\s]+', '', line).strip().strip('"\'')
                            else:
                                cur += " " + line.strip().strip('"\'')
                        if cur: pp.append(cur)
                        st.session_state.prompts = pp
                        st.session_state.prompts_text = "\n\n".join([f"{i+1}) {p}" for i, p in enumerate(pp)])
                        st.rerun()
        if st.session_state.prompts and not st.session_state.prompts_confirmed:
            st.caption(f"**{len(st.session_state.prompts)}**개 프롬프트")
            ed = st.text_area("편집", value=st.session_state.prompts_text, height=400, label_visibility="collapsed", key="pr_edit")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 재생성", use_container_width=True):
                    st.session_state.prompts = []
                    st.rerun()
            with c2:
                if st.button("✅ 확정 → 이미지 생성", use_container_width=True, type="primary"):
                    blocks = re.split(r'\n\s*(?=\d+[\)\.])', ed.strip())
                    pp = [re.sub(r'^\d+[\)\.\s]+', '', b).strip().strip('"\'') for b in blocks if b.strip()]
                    st.session_state.prompts = [p for p in pp if p]
                    st.session_state.prompts_confirmed = True
                    st.session_state.step = 4
                    st.rerun()
        if st.session_state.prompts_confirmed:
            with st.expander(f"✅ 프롬프트 확정 ({len(st.session_state.prompts)}개)", expanded=False):
                for i, p in enumerate(st.session_state.prompts):
                    st.markdown(f'<div class="prompt-block"><b>{i+1})</b> {p}</div>', unsafe_allow_html=True)

    # STEP 4
    if st.session_state.step >= 4 and st.session_state.prompts_confirmed:
        st.divider()
        plabel = gemini_image_model if platform == "Gemini (직접)" else selected_freepik_model
        st.markdown(f'<span class="step-badge">STEP 4</span> **이미지 생성** ({plabel})', unsafe_allow_html=True)

        if not st.session_state.images:
            total = len(st.session_state.prompts)
            bar = st.progress(0, text=f"준비 중... (0/{total})")
            imgs, used = [], []
            status = st.empty()

            for i, pt in enumerate(st.session_state.prompts):
                status.info(f"🎨 {i+1}/{total} 생성 중...")
                bar.progress(i / total, text=f"{i}/{total}")

                if platform == "Gemini (직접)":
                    client = get_gemini_client()
                    d = generate_image_gemini(client, pt, gemini_image_model) if client else None
                else:
                    d = generate_image_freepik(pt, selected_freepik_model, fp_aspect, fp_resolution if FREEPIK_MODELS[selected_freepik_model]["type"] == "mystic" else "2k")

                if d and isinstance(d, bytes):
                    imgs.append(d)
                elif d:
                    try: imgs.append(base64.b64decode(d))
                    except: imgs.append(d)
                else:
                    imgs.append(None)
                used.append(pt)
                if i < total - 1: time.sleep(2)

            bar.progress(1.0, text=f"✅ 완료! ({total}/{total})")
            v = sum(1 for x in imgs if x)
            status.success(f"✅ {v}개 생성 완료!")
            st.session_state.images = imgs
            st.session_state.image_prompts_used = used
            st.rerun()

        if st.session_state.images:
            v = sum(1 for x in st.session_state.images if x)
            st.success(f"✅ {v}개 이미지! '🖼️ 생성된 이미지' 탭에서 확인")

# ═══ 탭3: 결과 ═══
with tab_result:
    if not st.session_state.images:
        st.info("아직 이미지가 없습니다.")
    else:
        imgs = st.session_state.images
        used = st.session_state.image_prompts_used
        segs = st.session_state.segments
        v = sum(1 for x in imgs if x)
        st.markdown(f"### 🖼️ 생성된 이미지 ({v}개)")

        if v > 0:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for i, img in enumerate(imgs):
                    if img: zf.writestr(f"scene_{i+1:03d}.png", img)
                zf.writestr("prompts.txt", "\n\n".join([f"[{i+1}]\n{segs[i] if i<len(segs) else ''}\n{used[i] if i<len(used) else ''}" for i in range(len(imgs))]))
            buf.seek(0)
            st.download_button("📦 ZIP 다운로드", buf.getvalue(), "images.zip", "application/zip", use_container_width=True)

        st.divider()
        for r in range(0, len(imgs), 2):
            cols = st.columns(2)
            for c in range(2):
                idx = r + c
                if idx >= len(imgs): break
                with cols[c]:
                    st.markdown(f"**장면 {idx+1}**")
                    if imgs[idx]:
                        st.image(imgs[idx], use_container_width=True)
                        st.download_button("💾", imgs[idx], f"scene_{idx+1:03d}.png", "image/png", key=f"d{idx}", use_container_width=True)
                    else:
                        st.error("⚠️ 실패")
                    if idx < len(segs): st.caption(f"📄 {segs[idx]}")
                    if idx < len(used):
                        with st.expander("프롬프트"):
                            st.code(used[idx], language=None)
