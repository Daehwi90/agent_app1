import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & PREMIUM STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI 얼굴 비교 감정기 (Face Comparison AI)",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS (Modern typography, neon gradients, glassmorphism card layouts)
custom_css = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>
    /* Global Font Settings */
    * {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    
    /* Main Background & Text Color Tweaks */
    .stApp {
        background-color: #0F172A; /* Slate 900 for modern dark theme */
        color: #F1F5F9;
    }
    
    /* Header styling with premium gradient */
    .header-container {
        padding: 2.5rem 1.5rem;
        background: linear-gradient(135deg, #6366F1 0%, #3B82F6 50%, #06B6D4 100%);
        border-radius: 16px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.3);
    }
    
    .header-title {
        color: #FFFFFF !important;
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        margin-bottom: 0.5rem !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .header-subtitle {
        color: #E2E8F0 !important;
        font-size: 1.2rem !important;
        font-weight: 400;
        opacity: 0.9;
    }
    
    /* Upload Card Layout */
    .upload-card {
        background-color: rgba(30, 41, 59, 0.7); /* Slate 800 with transparency */
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .upload-card:hover {
        transform: translateY(-2px);
        border-color: #6366F1;
        box-shadow: 0 12px 20px -8px rgba(99, 102, 241, 0.4);
    }
    
    /* Analysis Report Card styling */
    .report-card {
        background: rgba(30, 41, 59, 0.85);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 16px;
        padding: 2rem;
        margin-top: 1.5rem;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
    }
    
    /* Custom Match Badges */
    .badge-match {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%); /* Emerald Gradient */
        color: white;
        font-weight: 700;
        padding: 0.5rem 1.2rem;
        border-radius: 30px;
        font-size: 1.1rem;
        display: inline-block;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3);
    }
    
    .badge-mismatch {
        background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); /* Rose Gradient */
        color: white;
        font-weight: 700;
        padding: 0.5rem 1.2rem;
        border-radius: 30px;
        font-size: 1.1rem;
        display: inline-block;
        box-shadow: 0 4px 10px rgba(239, 68, 68, 0.3);
    }

    .badge-uncertain {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); /* Amber Gradient */
        color: white;
        font-weight: 700;
        padding: 0.5rem 1.2rem;
        border-radius: 30px;
        font-size: 1.1rem;
        display: inline-block;
        box-shadow: 0 4px 10px rgba(245, 158, 11, 0.3);
    }
    
    /* Similarity Score Circle or Large Text */
    .score-container {
        text-align: center;
        padding: 1.5rem;
        background: rgba(15, 23, 42, 0.6);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 1.5rem;
    }
    
    .score-value {
        font-size: 3.5rem;
        font-weight: 900;
        background: linear-gradient(135deg, #60A5FA 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Feature table styling */
    .feature-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
        color: #E2E8F0;
    }
    
    .feature-table th {
        background-color: rgba(99, 102, 241, 0.15);
        color: #E2E8F0;
        font-weight: 700;
        text-align: left;
        padding: 0.75rem 1rem;
        border-bottom: 2px solid rgba(99, 102, 241, 0.3);
    }
    
    .feature-table td {
        padding: 0.75rem 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        vertical-align: top;
    }
    
    .feature-table tr:hover {
        background-color: rgba(255, 255, 255, 0.02);
    }
    
    .feature-name {
        font-weight: 600;
        color: #818CF8;
        white-space: nowrap;
    }
    
    /* Guide styling */
    .guide-box {
        background-color: rgba(99, 102, 241, 0.05);
        border-left: 4px solid #6366F1;
        padding: 1rem;
        border-radius: 4px;
        margin-top: 1rem;
        font-size: 0.9rem;
        color: #94A3B8;
    }

    /* Responsive Design (Media Queries) */
    @media (max-width: 768px) {
        .header-container {
            padding: 1.5rem 1rem;
            margin-bottom: 1.5rem;
        }
        .header-title {
            font-size: 1.8rem !important;
        }
        .header-subtitle {
            font-size: 0.95rem !important;
        }
        .upload-card {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .report-card {
            padding: 1.25rem;
        }
        .score-value {
            font-size: 2.5rem;
        }
        .badge-match, .badge-mismatch, .badge-uncertain {
            font-size: 0.9rem;
            padding: 0.4rem 1rem;
        }
        .feature-table th, .feature-table td {
            padding: 0.6rem 0.8rem;
            font-size: 0.85rem;
        }
        .feature-name {
            font-size: 0.85rem;
            white-space: normal;
        }
    }
</style>

"""
st.markdown(custom_css, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. HEADER SECTION
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="header-container">
        <div class="header-title">👤 AI 얼굴 비교 감정기</div>
        <div class="header-subtitle">두 장의 사진 속 인물이 동일인인지 인공지능이 세밀하게 대조 및 분석합니다.</div>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONFIGURATION (API KEY & MODEL SELECTION)
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ 설정 및 API 키")

# Try to resolve API key from secrets or env first
default_api_key = ""
try:
    default_api_key = st.secrets.get("GEMINI_API_KEY") or ""
except Exception:
    # secrets.toml 파일이 로컬 환경에 없을 경우 예외 처리
    pass

if not default_api_key:
    default_api_key = os.environ.get("GEMINI_API_KEY") or ""


# Input for API Key
api_key = st.sidebar.text_input(
    "Gemini API Key 입력",
    value=default_api_key,
    type="password",
    help="Google AI Studio에서 발급받은 API 키를 입력하세요. 입력한 키는 서버에 저장되지 않습니다."
)

st.sidebar.markdown(
    """
    <div style="font-size: 0.85rem; color: #94A3B8; margin-top: -10px; margin-bottom: 15px;">
        🔑 <a href="https://aistudio.google.com/" target="_blank" style="color: #6366F1; text-decoration: none; font-weight: 600;">Google AI Studio에서 API 키 받기 (무료)</a>
    </div>
    """,
    unsafe_allow_html=True
)

# Model selection
model_option = st.sidebar.selectbox(
    "분석 AI 모델 선택",
    options=["gemini-2.5-flash", "gemini-2.5-pro"],
    index=0,
    help="gemini-2.5-flash는 속도가 빠르며, gemini-2.5-pro는 정교하고 고차원적인 분석이 가능합니다."
)


st.sidebar.markdown("---")
st.sidebar.subheader("💡 사용 방법")
st.sidebar.markdown(
    """
    1. 왼쪽 사이드바에 **Gemini API Key**를 입력합니다.
    2. 분석할 사진 2장을 각각 업로드합니다. (얼굴이 잘 보이는 전면 사진 권장)
    3. **'🔍 동일인 대조 분석 시작'** 버튼을 클릭합니다.
    4. AI의 다각도 안면 분석 및 일치율 보고서를 확인합니다.
    """
)

# -----------------------------------------------------------------------------
# 4. IMAGE UPLOAD SECTION
# -----------------------------------------------------------------------------
st.markdown("### 📸 사진 업로드")

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown("#### **사진 1 (대상 A)**")
    file1 = st.file_uploader("첫 번째 사진을 선택하세요", type=["jpg", "jpeg", "png"], key="file1", label_visibility="collapsed")
    img1 = None
    if file1:
        img1 = Image.open(file1)
        # Resize image slightly for consistent display if it's too large, but keep original for API
        st.image(img1, use_column_width=True, caption="사진 1 업로드 완료")
    else:
        st.info("비교할 첫 번째 사진을 올려주세요.")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown("#### **사진 2 (대상 B)**")
    file2 = st.file_uploader("두 번째 사진을 선택하세요", type=["jpg", "jpeg", "png"], key="file2", label_visibility="collapsed")
    img2 = None
    if file2:
        img2 = Image.open(file2)
        st.image(img2, use_column_width=True, caption="사진 2 업로드 완료")
    else:
        st.info("비교할 두 번째 사진을 올려주세요.")
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. ANALYSIS LOGIC
# -----------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)

# Enable button only if both files are uploaded
btn_disabled = not (file1 and file2)
btn_label = "🔍 동일인 대조 분석 시작" if not btn_disabled else "⚠️ 사진 2장을 모두 업로드해주세요"

# Centered Action Button
c_left, c_mid, c_right = st.columns([1, 2, 1])
with c_mid:
    run_analysis = st.button(
        btn_label, 
        disabled=btn_disabled, 
        use_container_width=True,
        type="primary"
    )

if run_analysis:
    if not api_key.strip():
        st.error("🔑 API 키가 입력되지 않았습니다. 왼쪽 사이드바에서 Gemini API Key를 입력해주세요.")
    else:
        with st.spinner("🧠 AI가 안면 해부학적 구조를 바탕으로 분석 중입니다. 잠시만 기다려주세요..."):
            try:
                # Configure the Gemini API
                genai.configure(api_key=api_key.strip())
                model = genai.GenerativeModel(model_option)
                
                # Setup prompt and strict JSON schema output
                prompt = """
                You are a professional forensic face verification expert.
                Analyze the two provided images and determine if the faces in both images belong to the same person.

                Perform a rigorous anatomical and structural face comparison, analyzing:
                1. Facial Contour / Jawline (얼굴 윤곽 및 턱선 - 전체적인 구조, 광대뼈 위치, 턱 끝의 너비와 형태 대조)
                2. Eyes (눈 - 눈매의 각도, 쌍꺼풀 유무 및 선의 두께, 미간 거리의 비율 대조)
                3. Nose (코 - 콧대의 시작점 높이, 코끝의 둥글기, 콧볼의 넓이 대조)
                4. Mouth & Lips (입 및 입술 - 입꼬리의 처짐/올라감 각도, 윗입술과 아랫입술의 두께 비율 대조)
                5. Distinctive Marks / Others (기타 특징 - 눈썹의 산 각도와 두께, 이마 넓이 비율, 귀의 위치 및 외이도 모양, 점, 주름 등 대조)

                Return your assessment in JSON format using the following keys. All explanation strings must be written in professional, forensic-style Korean (한국어):
                {
                  "is_same_person": boolean,
                  "similarity_score": integer (between 0 and 100 representing confidence/similarity),
                  "overall_reasoning": "종합 비교 결과 요약 분석 설명 (한국어)",
                  "features": {
                    "facial_shape": "얼굴 윤곽 및 턱선에 대한 전문 대조 분석 결과 (한국어)",
                    "eyes": "눈매 및 안구 주변 구조 대조 분석 결과 (한국어)",
                    "nose": "비골 및 코 주변 연골 구조 대조 분석 결과 (한국어)",
                    "mouth": "구강 주변 근육 및 입술 구조 대조 분석 결과 (한국어)",
                    "other_features": "기타 지표(눈썹, 이마 비율, 점, 피부 표면 주름 및 촬영 각도 영향 등) 대조 분석 결과 (한국어)"
                  }
                }
                Provide ONLY the raw JSON output matching this schema. Do not wrap the JSON output in markdown block format.
                """
                
                # Request response with JSON type
                response = model.generate_content(
                    contents=[img1, img2, prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # Parse the output
                result = json.loads(response.text)
                
                # Display Results
                st.markdown('<div class="report-card">', unsafe_allow_html=True)
                st.markdown("### 📊 AI 포렌식 얼굴 감정 보고서")
                
                # Similarity Gauge and Summary Card
                r_col1, r_col2 = st.columns([1, 2])
                
                with r_col1:
                    st.markdown('<div class="score-container">', unsafe_allow_html=True)
                    st.markdown("<span>일치 신뢰도</span>", unsafe_allow_html=True)
                    st.markdown(f'<div class="score-value">{result.get("similarity_score", 0)}%</div>', unsafe_allow_html=True)
                    
                    # Display Status Badge based on score and decision
                    is_same = result.get("is_same_person", False)
                    score = result.get("similarity_score", 0)
                    
                    if is_same and score >= 80:
                        st.markdown('<div class="badge-match">동일인 판단 ✅</div>', unsafe_allow_html=True)
                    elif not is_same and score < 50:
                        st.markdown('<div class="badge-mismatch">타인 판단 ❌</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="badge-uncertain">판단 보류 / 분석 주의 ⚠️</div>', unsafe_allow_html=True)
                        
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                with r_col2:
                    st.markdown("#### **🔍 종합 감정 의견**")
                    st.write(result.get("overall_reasoning", "분석 결과를 생성하지 못했습니다."))
                    
                    # Similarity progress bar
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.progress(score / 100.0)
                
                # Detailed Feature Table
                st.markdown("#### **📋 세부 신체 부위별 분석 결과**")
                
                features = result.get("features", {})
                
                feature_labels = {
                    "facial_shape": "얼굴 윤곽 & 턱선 (Facial Shape)",
                    "eyes": "눈매 & 안구 주변 (Eyes)",
                    "nose": "콧대 & 코끝 (Nose)",
                    "mouth": "입술 & 구강 구조 (Mouth)",
                    "other_features": "기타 특징 & 각도 (Others)"
                }
                
                table_rows = ""
                for key, label in feature_labels.items():
                    desc = features.get(key, "분석 데이터 없음")
                    table_rows += f"""
                    <tr>
                        <td class="feature-name">{label}</td>
                        <td>{desc}</td>
                    </tr>
                    """
                
                table_html = f"""
                <div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                    <table class="feature-table">
                        <thead>
                            <tr>
                                <th style="width: 25%;">분석 영역</th>
                                <th>상세 대조 분석 결과 (Forensic Analysis Details)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
                """
                st.markdown(table_html, unsafe_allow_html=True)

                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Disclaimer
                st.markdown(
                    """
                    <div class="guide-box">
                        <strong>⚠️ 주의사항 및 안내</strong><br>
                        본 프로그램은 Google Gemini AI 모델의 컴퓨터 비전 분석 결과를 기반으로 작동합니다. 
                        조명 상태, 메이크업, 촬영 각도 및 표정에 따라 오차가 발생할 수 있으므로, 본 결과는 참고용 법의학 보조 자료로만 활용하시고 공식적인 신원 보증 목적으로 사용할 수 없습니다.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            except json.JSONDecodeError as jde:
                st.error("🚨 AI의 응답 데이터 형식(JSON) 해석에 실패했습니다. 다시 시도해주세요.")
                with st.expander("원문 오류 상세 정보 보기"):
                    st.write(response.text)
            except Exception as e:
                st.error(f"🚨 분석 중 오류가 발생했습니다: {str(e)}")
                st.info("API 키가 올바른지 확인해 주시고, 일시적인 네트워크 오류일 수 있으니 다시 시도해 주세요.")

# -----------------------------------------------------------------------------
# 6. FOOTER SECTION
# -----------------------------------------------------------------------------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align: center; color: #64748B; font-size: 0.85rem; padding-bottom: 2rem;">
        © 2026 AI Face Comparison Service. Powered by Streamlit & Google Gemini.
    </div>
    """,
    unsafe_allow_html=True
)
