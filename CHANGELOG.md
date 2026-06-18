# 프로젝트 변경 이력 (CHANGELOG)

이 문서는 Streamlit 사내 문서 RAG 챗봇 및 크롤러 애플리케이션의 개발 및 업그레이드 이력을 기록합니다.

---

## [v2.0.1] - 2026-06-18
### 수정 (Fixed)
- **Streamlit Community Cloud 환경에서 Playwright 크로미움 브라우저 에러 핫픽스**:
  - `app.py`에 `@st.cache_resource` 기반으로 서버 시작 시 `playwright install chromium`을 1회 백그라운드 자동 실행해 주는 초기화 함수 추가.
  - `crawler_service.py`에서 로컬(Windows)과 서버(Linux) 환경을 감지하여, 리눅스 서버 환경에서는 화면 출력 없는 헤드리스 모드(`headless=True`) 및 채널 없는 일반 `chromium`으로 자동 런칭 및 폴백하도록 조치.

---

## [v2.0.0] - 2026-06-18
### 추가 (Added)
- **다차원 벡터 검색 기능**:
  - `requirements.txt`에 `sentence-transformers>=2.2.0` 라이브러리 추가.
  - **로컬 벡터 검색(Sentence-Transformers)** 모드 구현: `all-MiniLM-L6-v2` 모델을 다운로드하여 로컬 서버 리소스로 문맥적 의미 검색 수행 (API 키 없이 문맥 검색 가능).
  - **API 임베딩 벡터 검색(Gemini / OpenAI)** 모드 구현: Google Gemini (`text-embedding-004`) 및 OpenAI (`text-embedding-3-small`) 임베딩 API 연동.
- **임베딩 캐싱 메커니즘**:
  - 사용자가 문서를 올리거나 검색 모델을 변경할 때 최초 1회만 임베딩을 계산하여 `st.session_state`에 캐싱함으로써, 질문할 때마다 계산하는 부하를 방지하고 응답 속도를 향상시킴.
- **검색 방식 UI 제어**:
  - 사이드바 내 "검색 상세 설정" 메뉴에 검색 방식을 선택할 수 있는 라디오 버튼 추가.

### 유지 (Maintained)
- 사용자가 추가한 **미스미 코리아 품목 가격 크롤러** 페이지 및 라이브러리 의존성(`playwright`, `pandas`, `openpyxl`) 유지.
- 기존의 **TF-IDF 키워드 검색** 모드 유지.

---

## [v1.1.0] - 2026-06-18
### 추가 (Added)
- **미스미 가격 크롤러 통합** (사용자 작업):
  - `crawler_service` 모듈을 연동하여 `kr.misumi-ec.com` 품목 가격 크롤러 페이지 추가.
  - 직접 입력 및 엑셀/TXT 업로드 지원 및 엑셀 다운로드 기능 추가.
  - 의존성 라이브러리 추가: `playwright`, `pandas`, `openpyxl`.
  - Gemini 모델 버전을 `gemini-1.5-flash`에서 `gemini-2.5-flash`로 변경.

---

## [v1.0.0] - 2026-06-18
### 추가 (Added)
- **최초 프로젝트 생성**:
  - `app.py` 및 `requirements.txt` 기본 구성.
  - PDF 및 TXT 사내 문서 업로드 및 한국어 특화 세그먼트/문장 단위 텍스트 분할(Chunking) 기능.
  - API 키가 없는 경우에도 동작할 수 있도록 로컬 `TF-IDF` 기반 키워드 검색 결과 카드 노출 기능 구현.
  - API 키가 있는 경우 OpenAI(`gpt-4o-mini`) 및 Gemini(`gemini-1.5-flash`) RAG 답변 생성 연동.
  - 가독성 높은 Pretendard 폰트 및 다크/라이트 모드 대응 CSS 프리미엄 커스텀 디자인 적용.
