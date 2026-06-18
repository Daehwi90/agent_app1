# Streamlit 사내 문서 RAG 챗봇 개발 계획서

이 프로젝트는 코딩 초보자도 쉽게 사용하고 관리할 수 있도록 설계된 **Streamlit 기반 사내 문서 RAG(Retrieval-Augmented Generation) 챗봇**입니다.
API 키가 없어도 문서 업로드와 유사도 기반 검색 결과를 보여주고, API 키를 입력하면 검색된 문서를 바탕으로 AI 답변을 생성합니다.

---

## 주요 기능 및 특징

1. **문서 업로드 및 텍스트 추출**:
   - `PDF` 및 `TXT` 파일 업로드 지원
   - 업로드된 문서 자동 텍스트 분할 (Chunking)

2. **API 키 없는 로컬 검색 (TF-IDF 기반)**:
   - API 키가 없어도 `scikit-learn`의 `TfidfVectorizer`를 사용하여 사용자 질문과 가장 유사한 문서 본문(Chunk) 검색 및 매칭율 표시
   - 로컬 환경 및 스트림릿 서버에서 별도의 과금이나 다운로드 대기 시간 없이 즉시 검색 결과 확인 가능

3. **API 키가 있는 경우의 RAG 답변 생성**:
   - **Google Gemini API** 및 **OpenAI API** 연동 지원 (사용자가 선택하여 입력 가능)
   - 검색된 문서 내용을 AI에게 프롬프트로 전달하여, 신뢰할 수 있는 사내 문서 기반 답변 생성

4. **프리미엄 UI/UX 디자인**:
   - 깔끔하고 세련된 다크/라이트 모드 대응 CSS 커스텀 디자인
   - 직관적인 사이드바 구성 (API 키 입력, 파일 업로드, 검색 설정)
   - 대화형 챗봇 레이아웃 및 검색 출처(Source) 아코디언 제공

---

## 프로젝트 구성 파일

프로젝트 루트 폴더에 아래의 파일들을 생성할 예정입니다.

### 1. `app.py`
- Streamlit 메인 애플리케이션 파일
- 파일 업로드 및 텍스트 추출 로직
- TF-IDF 기반 유사도 검색 구현
- Gemini/OpenAI API 호출 및 답변 생성 로직
- 대화 내역 저장 및 화면 렌더링

### 2. `requirements.txt`
- 프로젝트에 필요한 라이브러리 목록 정의
- 스트림릿 서버 배포를 위해 필수적인 의존성 파일
```text
streamlit>=1.35.0
scikit-learn>=1.0
pypdf>=4.0.0
google-generativeai>=0.5.0
openai>=1.0.0
```

---

## 검증 계획 (Verification Plan)

### 로컬 검증 (Manual Verification)
1. 로컬 환경에서 Streamlit 앱 실행 (`streamlit run app.py`).
2. 샘플 PDF 및 TXT 문서 업로드 후, 사이드바에서 문서 정보(청크 개수 등)가 정상 표시되는지 확인.
3. **API 키 없이** 질문을 입력했을 때, 문서에서 가장 유사한 문단(검색 결과)이 화면에 표시되는지 확인.
4. **Gemini 또는 OpenAI API 키**를 입력한 후 질문했을 때, 문서 내용을 바탕으로 생성된 AI 답변과 출처가 정상적으로 출력되는지 확인.
