import streamlit as st
import pypdf
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
from openai import OpenAI
import pandas as pd
import io
from crawler_service import crawl_parts_service_sync
import subprocess
import os
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

@st.cache_resource
def ensure_playwright_browsers():
    """Streamlit Community Cloud 서버 환경에서 Playwright 크로미움 브라우저 바이너리를 자동 다운로드합니다."""
    is_streamlit_cloud = os.environ.get("STREAMLIT_SERVER") or os.name != "nt"
    if is_streamlit_cloud:
        try:
            # playwright install chromium 실행
            subprocess.run(["python", "-m", "playwright", "install", "chromium"], check=True)
        except Exception as e:
            st.error(f"⚠️ Playwright 브라우저 자동 설치 중 오류 발생: {e}")

# 서버 시작 시 1회 자동 실행 (캐싱 적용)
ensure_playwright_browsers()

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="사내 문서 RAG 챗봇",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Premium Custom CSS
custom_css = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<style>
    /* Global Font Settings */
    * {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    
    /* Header Gradient Style */
    .header-container {
        padding: 1.5rem 0rem;
        background: linear-gradient(135deg, #4F46E5 0%, #06B6D4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        color: #6B7280;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Document Chunk Cards Design (Glassmorphism inspired) */
    .chunk-card {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }
    
    .chunk-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        border-color: #4F46E5;
    }
    
    .chunk-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.8rem;
        border-bottom: 1px dashed rgba(128, 128, 128, 0.2);
        padding-bottom: 0.5rem;
    }
    
    .chunk-source {
        font-weight: 700;
        color: #4F46E5;
        font-size: 0.9rem;
    }
    
    .dark-mode .chunk-source {
        color: #818CF8;
    }
    
    .chunk-score {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .chunk-text {
        font-size: 0.95rem;
        line-height: 1.6;
        color: inherit;
        white-space: pre-wrap;
    }
    
    /* Warning/Notice box for API Keys */
    .api-warning {
        background-color: rgba(245, 158, 11, 0.1);
        border-left: 4px solid #F59E0B;
        padding: 1rem;
        border-radius: 4px 12px 12px 4px;
        margin-bottom: 1.5rem;
        font-size: 0.95rem;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DOCUMENT PROCESSING FUNCTIONS
# -----------------------------------------------------------------------------
def extract_text_from_pdf(file_obj):
    """PDF 파일 객체에서 텍스트와 페이지 번호를 추출합니다."""
    reader = pypdf.PdfReader(file_obj)
    pages_text = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages_text.append((text, i + 1))
    return pages_text

def extract_text_from_txt(file_obj):
    """TXT 파일 객체에서 텍스트를 추출합니다."""
    text = file_obj.read().decode("utf-8", errors="ignore")
    return [(text, 1)]

def chunk_text(text, chunk_size=600, chunk_overlap=150):
    """텍스트를 문장이나 마침표 기준으로 의미가 끊기지 않도록 나누어 청크를 만듭니다."""
    # 문장 단위로 분할하기 위해 정규식 사용 (. ! ? 뒤에 공백이나 줄바꿈이 오는 경우)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_len = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # 문장 하나가 청크 사이즈보다 큰 경우 예외 처리
        if len(sentence) > chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_len = 0
            
            # 긴 문장은 글자 수 기준 강제 분할
            start = 0
            while start < len(sentence):
                end = start + chunk_size
                chunks.append(sentence[start:end])
                start += (chunk_size - chunk_overlap)
            continue
            
        if current_len + len(sentence) > chunk_size:
            chunks.append(" ".join(current_chunk))
            
            # 오버랩 구현: 이전 문장의 일부를 새 청크의 시작 부분에 보존
            overlap_len = 0
            overlap_chunk = []
            for s in reversed(current_chunk):
                if overlap_len + len(s) < chunk_overlap:
                    overlap_chunk.insert(0, s)
                    overlap_len += len(s)
                else:
                    break
            current_chunk = overlap_chunk
            current_len = sum(len(s) for s in current_chunk) + len(current_chunk)
            
        current_chunk.append(sentence)
        current_len += len(sentence) + 1
        
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def process_files(uploaded_files, chunk_size, chunk_overlap):
    """업로드된 파일들을 읽어 분할된 청크 리스트를 반환합니다."""
    all_chunks = []
    for file in uploaded_files:
        try:
            if file.name.endswith(".pdf"):
                pages = extract_text_from_pdf(file)
                for text, page_num in pages:
                    file_chunks = chunk_text(text, chunk_size, chunk_overlap)
                    for c in file_chunks:
                        all_chunks.append({
                            "text": c,
                            "source": file.name,
                            "page": page_num
                        })
            elif file.name.endswith(".txt"):
                pages = extract_text_from_txt(file)
                for text, page_num in pages:
                    file_chunks = chunk_text(text, chunk_size, chunk_overlap)
                    for c in file_chunks:
                        all_chunks.append({
                            "text": c,
                            "source": file.name,
                            "page": None
                        })
        except Exception as e:
            st.sidebar.error(f"파일 처리 오류 ({file.name}): {str(e)}")
    return all_chunks

# -----------------------------------------------------------------------------
# 3. VECTOR & TF-IDF SEARCH FUNCTIONS WITH EMBEDDING CACHING
# -----------------------------------------------------------------------------
@st.cache_resource
def load_local_embedding_model():
    """로컬 Sentence-Transformers 모델을 캐싱하여 로드합니다."""
    if not HAS_SENTENCE_TRANSFORMERS:
        raise ImportError("sentence-transformers 라이브러리가 설치되어 있지 않습니다.")
    return SentenceTransformer("jhgan/ko-sroberta-multitask")

def get_gemini_embeddings(api_key, texts):
    """Gemini API를 활용하여 여러 텍스트들의 임베딩 벡터를 추출합니다."""
    try:
        genai.configure(api_key=api_key)
        # Gemini 임베딩 API 호출
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=texts,
            task_type="retrieval_document"
        )
        return response['embedding']
    except Exception as e:
        st.error(f"Gemini 임베딩 생성 중 오류 발생: {e}")
        return None

def get_gemini_query_embedding(api_key, query):
    """Gemini API를 활용하여 단일 쿼리의 임베딩 벡터를 추출합니다."""
    try:
        genai.configure(api_key=api_key)
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )
        return response['embedding']
    except Exception as e:
        st.error(f"Gemini 쿼리 임베딩 생성 중 오류 발생: {e}")
        return None

def get_openai_embeddings(api_key, texts):
    """OpenAI API를 활용하여 여러 텍스트들의 임베딩 벡터를 추출합니다."""
    try:
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        st.error(f"OpenAI 임베딩 생성 중 오류 발생: {e}")
        return None

def get_openai_query_embedding(api_key, query):
    """OpenAI API를 활용하여 단일 쿼리의 임베딩 벡터를 추출합니다."""
    try:
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=[query]
        )
        return response.data[0].embedding
    except Exception as e:
        st.error(f"OpenAI 쿼리 임베딩 생성 중 오류 발생: {e}")
        return None

def get_cached_embeddings(chunks, search_method, api_provider, api_key=None):
    """문서 조각(Chunk)들에 대한 임베딩 벡터를 생성하고 캐싱합니다."""
    if not chunks:
        return None
        
    if "cached_embeddings" not in st.session_state:
        st.session_state["cached_embeddings"] = {}
        
    # 캐시 키 정의 (검색 방식과 청크 개수를 조합)
    cache_key = f"{search_method}_{len(chunks)}"
    
    # 이미 캐시된 임베딩이 있으면 반환
    if cache_key in st.session_state["cached_embeddings"]:
        return st.session_state["cached_embeddings"][cache_key]
        
    # 새로운 임베딩 생성 진행
    texts = [c["text"] for c in chunks]
    
    if search_method == "🧠 로컬 벡터 검색 (Sentence-Transformers)":
        if not HAS_SENTENCE_TRANSFORMERS:
            st.error("⚠️ sentence-transformers 패키지가 설치되어 있지 않아 로컬 벡터 검색을 수행할 수 없습니다.")
            return None
        with st.spinner("로컬 임베딩 모델(all-MiniLM-L6-v2)을 로드하고 문서 벡터를 추출하는 중... (최초 1회 실행)"):
            try:
                model = load_local_embedding_model()
                embeddings = model.encode(texts, show_progress_bar=False)
                st.session_state["cached_embeddings"][cache_key] = embeddings
                return embeddings
            except Exception as e:
                st.error(f"로컬 벡터 검색 실행 실패: {e}")
                return None
                
    elif search_method == "⚡ API 임베딩 검색 (Gemini / OpenAI)":
        if api_provider == "Google Gemini" and api_key.strip():
            with st.spinner("Gemini API를 통해 문서 벡터를 생성하는 중... (최초 1회 실행)"):
                embeddings = get_gemini_embeddings(api_key, texts)
                if embeddings is not None:
                    st.session_state["cached_embeddings"][cache_key] = embeddings
                    return embeddings
        elif api_provider == "OpenAI" and api_key.strip():
            with st.spinner("OpenAI API를 통해 문서 벡터를 생성하는 중... (최초 1회 실행)"):
                embeddings = get_openai_embeddings(api_key, texts)
                if embeddings is not None:
                    st.session_state["cached_embeddings"][cache_key] = embeddings
                    return embeddings
        else:
            st.warning("⚠️ API 키가 입력되지 않아 API 임베딩 검색이 불가합니다. TF-IDF 검색으로 대체합니다.")
            return None
            
    return None

def search_documents(query, chunks, search_method, api_provider, api_key=None, top_k=3):
    """지정한 검색 방식에 따라 가장 유사도가 높은 문서 청크들을 검색합니다."""
    if not chunks:
        return []
        
    # 1. 키워드 검색 (TF-IDF)
    if search_method == "🔍 키워드 검색 (TF-IDF)":
        texts = [c["text"] for c in chunks]
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(texts)
        query_vector = vectorizer.transform([query])
        
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.0:
                results.append({
                    "chunk": chunks[idx],
                    "score": float(similarities[idx])
                })
        return results
        
    # 2. 벡터 검색 (로컬 또는 API)
    embeddings = get_cached_embeddings(chunks, search_method, api_provider, api_key)
    
    # 임베딩 생성에 실패한 경우 TF-IDF로 대체 작동 (폴백)
    if embeddings is None:
        st.info("💡 TF-IDF 키워드 검색 모드로 대체하여 결과를 찾았습니다.")
        return search_documents(query, chunks, "🔍 키워드 검색 (TF-IDF)", api_provider, api_key, top_k)
        
    # 질문(Query) 임베딩 벡터 구하기
    query_emb = None
    if search_method == "🧠 로컬 벡터 검색 (Sentence-Transformers)":
        try:
            model = load_local_embedding_model()
            query_emb = model.encode([query])[0]
        except Exception as e:
            st.error(f"로컬 쿼리 임베딩 실패: {e}")
    elif search_method == "⚡ API 임베딩 검색 (Gemini / OpenAI)":
        if api_provider == "Google Gemini":
            query_emb = get_gemini_query_embedding(api_key, query)
        elif api_provider == "OpenAI":
            query_emb = get_openai_query_embedding(api_key, query)
            
    # 쿼리 임베딩 실패 시 TF-IDF 대체
    if query_emb is None:
        st.info("💡 임베딩 생성 오류로 키워드 검색(TF-IDF)으로 대체하여 검색합니다.")
        return search_documents(query, chunks, "🔍 키워드 검색 (TF-IDF)", api_provider, api_key, top_k)
        
    # 유사도 계산 수행
    query_vector = np.array(query_emb).reshape(1, -1)
    embeddings_matrix = np.array(embeddings)
    similarities = cosine_similarity(query_vector, embeddings_matrix).flatten()
    
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        results.append({
            "chunk": chunks[idx],
            "score": float(similarities[idx])
        })
    return results

# -----------------------------------------------------------------------------
# 4. LLM API GENERATION FUNCTIONS
# -----------------------------------------------------------------------------
def generate_gemini(api_key, query, context_chunks):
    """Google Gemini API를 호출하여 답변을 얻습니다."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 컨텍스트 조립
        context_str = ""
        for i, c in enumerate(context_chunks):
            source_info = f"{c['source']}"
            if c.get("page"):
                source_info += f" (Page {c['page']})"
            context_str += f"[문서 {i+1} - 출처: {source_info}]\n{c['text']}\n\n"
            
        prompt = f"""당신은 사내 문서를 바탕으로 직원의 질문에 답변하는 친절하고 전문적인 AI 비서입니다.
아래에 제공된 사내 문서 내용(Context)을 매우 신뢰하여 사용자의 질문(Question)에 정직하고 명확하게 답변해 주세요.
답변할 때 문서에 명시되지 않은 내용은 지어내거나 추측하지 마시고, 문서에 나와 있는 팩트만을 기반으로 답변해 주세요.
해당되는 경우 출처([문서 번호])를 답변 중간에 명시해 주세요.

[Context]
{context_str}

[Question]
{query}

[Answer]"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Gemini API 호출 중 오류가 발생했습니다: {str(e)}"

def generate_openai(api_key, query, context_chunks):
    """OpenAI API를 호출하여 답변을 얻습니다."""
    try:
        client = OpenAI(api_key=api_key)
        
        context_str = ""
        for i, c in enumerate(context_chunks):
            source_info = f"{c['source']}"
            if c.get("page"):
                source_info += f" (Page {c['page']})"
            context_str += f"[문서 {i+1} - 출처: {source_info}]\n{c['text']}\n\n"
            
        prompt = f"""당신은 사내 문서를 바탕으로 직원의 질문에 답변하는 친절하고 전문적인 AI 비서입니다.
아래에 제공된 사내 문서 내용(Context)을 매우 신뢰하여 사용자의 질문(Question)에 정직하고 명확하게 답변해 주세요.
답변할 때 문서에 명시되지 않은 내용은 지어내거나 추측하지 마시고, 문서에 나와 있는 팩트만을 기반으로 답변해 주세요.
해당되는 경우 출처([문서 번호])를 답변 중간에 명시해 주세요.

[Context]
{context_str}

[Question]
{query}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 사내 문서를 기반으로 정확히 답변하는 유용한 인공지능 도우미입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ OpenAI API 호출 중 오류가 발생했습니다: {str(e)}"

# -----------------------------------------------------------------------------
# 5. STREAMLIT UI - SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/clouds/100/chat.png", width=80)
    st.markdown("### ⚙️ 작업 메뉴")
    app_mode = st.selectbox("기능 선택", ["💬 사내 문서 RAG 챗봇", "🛒 미스미 가격 크롤러"])
    st.divider()

if app_mode == "🛒 미스미 가격 크롤러":
    # 1. RENDER CRAWLER PAGE
    st.markdown("<h1 class='header-container'>🛒 미스미 코리아 품목 가격 크롤러</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>미스미 코리아(kr.misumi-ec.com) 품목의 가격과 출하 정보를 일괄 크롤링하여 엑셀로 내려받습니다.</p>", unsafe_allow_html=True)
    
    st.markdown("### 📝 크롤링 대상 품번 입력")
    input_method = st.radio("입력 방식 선택", ["직접 텍스트로 입력", "파일 업로드 (TXT 또는 Excel)"])
    
    part_numbers = []
    
    if input_method == "직접 텍스트로 입력":
        raw_text = st.text_area("품번을 한 줄에 하나씩 입력해 주세요 (예: CB6-15)", height=150, placeholder="CB6-15\nSFJ10-100\nSFN10-100")
        if raw_text:
            part_numbers = [line.strip() for line in raw_text.split("\n") if line.strip()]
    else:
        uploaded_file = st.file_uploader("품번 목록 파일 업로드 (.txt 또는 .xlsx)", type=["txt", "xlsx"])
        if uploaded_file:
            if uploaded_file.name.endswith(".txt"):
                file_content = uploaded_file.read().decode("utf-8", errors="ignore")
                part_numbers = [line.strip() for line in file_content.split("\n") if line.strip()]
            elif uploaded_file.name.endswith(".xlsx"):
                try:
                    df_input = pd.read_excel(uploaded_file)
                    if not df_input.empty:
                        first_col = df_input.columns[0]
                        part_numbers = [str(x).strip() for x in df_input[first_col].dropna() if str(x).strip()]
                except Exception as e:
                    st.error(f"엑셀 파일 읽기 오류: {e}")
                    
    if part_numbers:
        st.success(f"📋 총 **{len(part_numbers)}**개의 품번이 확인되었습니다.")
    
    st.markdown("---")
    
    if st.button("🚀 크롤링 시작", type="primary", disabled=len(part_numbers) == 0):
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        table_placeholder = st.empty()
        
        results = []
        
        def progress_callback(current_idx, total_count, res):
            results.append(res)
            progress_bar.progress(current_idx / total_count)
            status_text.write(f"⏳ 크롤링 진행 중... ({current_idx} / {total_count}) - **{res['검색 품번']}** 완료")
            df_temp = pd.DataFrame(results)
            table_placeholder.dataframe(df_temp, use_container_width=True)
            
        status_text.write("⏳ 크롤러 초기화 중... 크롬 브라우저가 실행됩니다. (잠시만 기다려 주세요)")
        
        try:
            final_results = crawl_parts_service_sync(part_numbers, callback=progress_callback)
            status_text.success("✅ 크롤링이 완료되었습니다!")
            
            df_final = pd.DataFrame(final_results)
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name="미스미 가격 정보")
            excel_data = output_excel.getvalue()
            
            st.download_button(
                label="📥 크롤링 결과 엑셀 파일 다운로드",
                data=excel_data,
                file_name="misumi_prices_crawled.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel"
            )
        except Exception as e:
            st.error(f"❌ 크롤링 중 오류가 발생했습니다: {e}")
            status_text.empty()
            
    st.stop()

# Continue with RAG chatbot sidebar
with st.sidebar:
    st.markdown("### 🛠️ 설정 및 문서 제어")
    
    # (1) API 설정
    st.markdown("#### 1. API 키 설정 (선택)")
    api_provider = st.selectbox("API 제공사 선택", ["API 키 없음 (검색 전용)", "Google Gemini", "OpenAI"])
    
    api_key = ""
    if api_provider == "Google Gemini":
        api_key = st.text_input("Gemini API Key 입력", type="password", help="AI 답변 생성을 위해 필요합니다.")
    elif api_provider == "OpenAI":
        api_key = st.text_input("OpenAI API Key 입력", type="password", help="AI 답변 생성을 위해 필요합니다.")
        
    st.divider()
    
    # (2) 문서 업로드
    st.markdown("#### 2. 사내 문서 업로드")
    uploaded_files = st.file_uploader(
        "PDF 또는 TXT 문서를 업로드해 주세요 (다중 선택 가능)",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )
    
    # (3) 고급 설정 (토글 가능하게 확장)
    with st.expander("⚙️ 검색 상세 설정"):
        search_method = st.radio(
            "검색 방식 선택",
            [
                "🔍 키워드 검색 (TF-IDF)",
                "🧠 로컬 벡터 검색 (Sentence-Transformers)",
                "⚡ API 임베딩 검색 (Gemini / OpenAI)"
            ],
            index=0,
            help="로컬 벡터 검색은 설치 시 다운로드 등으로 시간이 소요될 수 있으며 의미 중심 검색이 가능합니다. API 임베딩은 API 키가 설정되어 있어야 합니다."
        )
        chunk_size = st.slider("청크 크기 (글자 수)", min_value=200, max_value=2000, value=600, step=100)
        chunk_overlap = st.slider("청크 중복 크기 (글자 수)", min_value=50, max_value=500, value=150, step=50)
        top_k = st.slider("가장 유사한 구절 개수 (Top-K)", min_value=1, max_value=10, value=3)

    st.divider()
    
    # 문서가 정상적으로 파싱되었는지 요약 표시
    if uploaded_files:
        st.success(f"📂 파일 {len(uploaded_files)}개 업로드 완료")
        
        # 세션 스테이트를 활용해 불필요한 재파싱 방지
        if "processed_files_hash" not in st.session_state or st.session_state.get("processed_files_hash") != len(uploaded_files) + chunk_size + chunk_overlap:
            with st.spinner("문서를 파싱하고 분석하는 중..."):
                st.session_state["chunks"] = process_files(uploaded_files, chunk_size, chunk_overlap)
                st.session_state["processed_files_hash"] = len(uploaded_files) + chunk_size + chunk_overlap
                # 업로드된 문서나 설정이 변경되면 임베딩 캐시 삭제
                if "cached_embeddings" in st.session_state:
                    del st.session_state["cached_embeddings"]
                
        chunks = st.session_state.get("chunks", [])
        st.info(f"📊 총 분할된 조각(Chunk) 개수: **{len(chunks)}**개")
    else:
        # 파일 업로드 없으면 세션 정리
        st.session_state["chunks"] = []
        if "processed_files_hash" in st.session_state:
            del st.session_state["processed_files_hash"]
        st.warning("⚠️ 문서를 업로드해야 대화를 시작할 수 있습니다.")

# -----------------------------------------------------------------------------
# 6. STREAMLIT UI - MAIN CHAT INTERFACE
# -----------------------------------------------------------------------------
# Title and introduction
st.markdown("<h1 class='header-container'>💼 사내 문서 RAG 어시스턴트</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>업로드한 사내 문서(PDF/TXT)를 기반으로 신뢰할 수 있는 답변을 받으세요.</p>", unsafe_allow_html=True)

# API가 없는 경우 경고창 노출
if api_provider == "API 키 없음 (검색 전용)" or not api_key.strip():
    st.markdown(
        """
        <div class='api-warning'>
            <strong>⚠️ 실시간 답변 생성(LLM)이 비활성화되었습니다.</strong><br>
            현재 API 키가 설정되지 않아 대답 작성이 어렵습니다. 질문을 입력하시면 
            <strong>업로드한 문서에서 매칭도가 높은 내용(검색 결과)을 찾아 보여드립니다.</strong><br>
            AI의 완성도 높은 자연어 답변을 원하시면 왼쪽 메뉴에서 <strong>Gemini 또는 OpenAI API 키</strong>를 설정해 주세요.
        </div>
        """,
        unsafe_allow_html=True
    )

# Session State for Chat History Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# Clear Chat History Button
if st.button("🔄 대화 초기화", help="채팅 기록을 지우고 처음부터 시작합니다."):
    st.session_state.messages = []
    st.rerun()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # 과거 메시지의 소스 정보(참고 문서) 렌더링
        if "sources" in message and message["sources"]:
            with st.expander("📚 참고 문서"):
                for src in message["sources"]:
                    source_label = src['source']
                    if src.get('page'):
                        source_label += f" (Page {src['page']})"
                    
                    st.markdown(
                        f"""
                        <div class='chunk-card'>
                            <div class='chunk-header'>
                                <span class='chunk-source'>📁 {source_label}</span>
                                <span class='chunk-score'>유사도: {src['score']:.2%}</span>
                            </div>
                            <div class='chunk-text'>{src['text']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

# User input query
if query := st.chat_input("문서에 대해 질문을 입력해 주세요..."):
    # (1) Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(query)
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": query})
    
    # (2) Check if documents are uploaded
    chunks = st.session_state.get("chunks", [])
    if not chunks:
        with st.chat_message("assistant"):
            warning_msg = "⚠️ 업로드된 문서가 없습니다. 왼쪽 사이드바에서 문서를 먼저 업로드해 주세요!"
            st.markdown(warning_msg)
            st.session_state.messages.append({"role": "assistant", "content": warning_msg})
    else:
        # Perform Similarity search (TF-IDF or Vector embeddings)
        search_results = search_documents(
            query=query, 
            chunks=chunks, 
            search_method=search_method, 
            api_provider=api_provider, 
            api_key=api_key, 
            top_k=top_k
        )
        
        # Prepare context data
        context_chunks = [res["chunk"] for res in search_results]
        source_data = []
        for res in search_results:
            source_data.append({
                "source": res["chunk"]["source"],
                "page": res["chunk"].get("page"),
                "text": res["chunk"]["text"],
                "score": res["score"]
            })
            
        with st.chat_message("assistant"):
            if api_provider == "API 키 없음 (검색 전용)" or not api_key.strip():
                # API Key가 없는 경우: 검색 결과만 출력
                if not search_results:
                    response_text = "❓ 질문과 일치하거나 유사도가 높은 구절을 사내 문서에서 찾지 못했습니다. 다른 키워드로 검색해 보세요."
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                else:
                    response_text = f"🔍 **'{query}'**에 대해 사내 문서에서 매칭율이 높은 구절을 찾았습니다."
                    st.markdown(response_text)
                    
                    # 검색 카드 출력
                    for i, src in enumerate(source_data):
                        source_label = src['source']
                        if src.get('page'):
                            source_label += f" (Page {src['page']})"
                            
                        st.markdown(
                            f"""
                            <div class='chunk-card'>
                                <div class='chunk-header'>
                                    <span class='chunk-source'>[{i+1}] 📁 {source_label}</span>
                                    <span class='chunk-score'>유사도: {src['score']:.2%}</span>
                                </div>
                                <div class='chunk-text'>{src['text']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_text,
                        "sources": source_data
                    })
            else:
                # API Key가 설정된 경우: RAG 답변 및 참고 문서 출력
                with st.spinner("AI 답변을 생성하는 중..."):
                    if not search_results:
                        # 매칭된 텍스트가 없는 경우 경고 후 일반 답변 생성 또는 차단
                        response_text = "⚠️ 업로드된 사내 문서에서 질문과 관련된 내용을 발견하지 못했습니다. 문서 내용을 벗어난 자유 답변이나 정확하지 않은 답변일 수 있습니다."
                        context_chunks_for_llm = []
                    else:
                        response_text = ""
                        context_chunks_for_llm = context_chunks
                    
                    # API 호출
                    if api_provider == "Google Gemini":
                        llm_reply = generate_gemini(api_key, query, context_chunks_for_llm)
                    else:
                        llm_reply = generate_openai(api_key, query, context_chunks_for_llm)
                    
                    if response_text:
                        response_text = response_text + "\n\n" + llm_reply
                    else:
                        response_text = llm_reply
                        
                    st.markdown(response_text)
                    
                    # 참고 문서 아코디언 형태로 출력
                    if search_results:
                        with st.expander("📚 참고 문서"):
                            for src in source_data:
                                source_label = src['source']
                                if src.get('page'):
                                    source_label += f" (Page {src['page']})"
                                
                                st.markdown(
                                    f"""
                                    <div class='chunk-card'>
                                        <div class='chunk-header'>
                                            <span class='chunk-source'>📁 {source_label}</span>
                                            <span class='chunk-score'>유사도: {src['score']:.2%}</span>
                                        </div>
                                        <div class='chunk-text'>{src['text']}</div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                                
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_text,
                        "sources": source_data
                    })
