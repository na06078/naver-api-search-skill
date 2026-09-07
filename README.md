# 네이버 API 검색 스킬

네이버 검색 API 7종과 Data Lab API 2종을 로컬 Python 호출기로 실행하는 Hermes 스킬입니다. MCP 서버 없이 Hermes가 `terminal` 도구로 호출기를 실행하고, 결과를 표준 JSON으로 받습니다.

## 주요 기능

### NAVER 검색 API 7종

- **블로그**: 네이버 블로그 글을 검색하고 제목·요약·글 URL·블로그명·작성일을 반환합니다.
- **이미지**: 이미지 원본 URL·섬네일 URL·가로·세로 크기를 반환하며 `all`, `large`, `medium`, `small` 크기 필터를 지원합니다.
- **지식iN**: 질문 제목·요약·URL을 검색하고 정확도순·날짜순·평점순 정렬을 지원합니다.
- **지역**: 업체·기관명, 분류, 지번 주소, 도로명 주소, 좌표를 반환합니다. 지역 검색은 결과 최대 5개, 시작 위치 1로 제한됩니다.
- **뉴스**: 기사 제목·요약·발행일과 함께 네이버 뉴스 URL과 원문 URL을 구분해 반환합니다.
- **웹문서**: 네이버 웹문서의 제목·요약·URL을 반환합니다. 일반적인 네이버 검색 요청의 기본 검색 종류로 사용할 수 있습니다.
- **카페글**: 카페 게시글 제목·요약·게시글 URL·카페명·카페 URL을 반환합니다.

모든 검색은 검색어, 결과 개수, 시작 위치, 검색 종류별 정렬 옵션을 사용하며 결과는 공통 JSON 구조로 정리됩니다.

### Data Lab API

- **검색어트렌드**: 최대 5개 주제어 그룹을 비교하고, 그룹마다 최대 20개 검색어를 묶을 수 있습니다. 일간·주간·월간 구간과 PC·모바일, 성별, 연령 조건을 지원합니다.
- **쇼핑인사이트 8개 모드**: 카테고리 비교, 기기별, 성별별, 연령별, 카테고리 내 키워드 비교와 각 키워드의 기기·성별·연령별 추이를 조회합니다.
- 쇼핑 카테고리는 네이버 쇼핑 URL의 `cat_id`를 사용합니다.
- Data Lab의 `ratio`는 실제 검색량·클릭 수가 아니라 조회 구간 안에서 최댓값을 100으로 환산한 상대 비율입니다.

### API Hub 인증과 안전한 키 관리

- NAVER API Hub 주소와 `X-NCP-APIGW-API-KEY-ID`, `X-NCP-APIGW-API-KEY` 인증 헤더를 사용합니다.
- Client ID와 Client Secret은 `.env`에서만 읽으며 Python 코드·SKILL.md·명령행·로그에 넣지 않습니다.
- `.env`는 `.gitignore`로 Git 추적에서 제외하고, 오류 메시지에도 인증값을 출력하지 않습니다.

### 요청 검증과 결과 표준화

- API에 요청하기 전에 검색 종류별 `display`, `start`, `sort`, 이미지 필터와 Data Lab 날짜·그룹·카테고리·키워드 제한을 검사합니다.
- 잘못된 입력은 네이버 호출 전에 오류로 반환하고, 인증 오류·권한 오류·네트워크 오류·서버 오류를 구분합니다.
- 네이버 결과의 검색어 강조용 HTML 태그를 제거하고, 검색 항목·Data Lab 시계열·오류를 일관된 JSON 형식으로 변환합니다.

## 빠른 설치

### 1. 저장소 받기

```bash
git clone https://github.com/na06078/naver-api-search-skill.git
cd naver-api-search-skill
```

### 2. 설치 경로 확인

먼저 실제 설치 예정 경로만 확인합니다. 이 단계에서는 파일을 복사하지 않습니다.

```bash
python 설치.py --check
```

`설치.py`는 다음 위치를 순서대로 확인합니다.

1. `HERMES_HOME` 환경변수의 `skills` 폴더
2. Windows: `%LOCALAPPDATA%\hermes\skills`
3. Linux/macOS: `~/.hermes/skills`

### 3. API 키 준비

NAVER API Hub(네이버 클라우드 플랫폼 콘솔)에서 Application을 만들고 다음 값을 발급받습니다.

- Client ID
- Client Secret
- 검색 API 권한
- 검색어트렌드·쇼핑인사이트 권한

`.env.example`을 복사해 저장소 루트에 `.env`를 만들고, 본인의 키를 입력합니다.

```bash
# Windows Git Bash
cp .env.example .env
```

```env
NAVER_CLIENT_ID=<본인의_Client_ID>
NAVER_CLIENT_SECRET=<본인의_Client_Secret>
```

### 4. 실제 설치

```bash
python 설치.py --install
```

기존 `naver-search-api` 설치가 있으면 덮어쓰지 않고 중단합니다. 직접 만든 기존 설치를 업데이트하려면 다음을 사용합니다.

```bash
python 설치.py --install --force
```

`--force`를 사용해도 기존 `.env`는 복사하거나 삭제하지 않습니다. 스킬 파일과 호출기 Python 파일만 갱신합니다.

설치 후 Hermes를 새로 시작해야 스킬 목록이 갱신됩니다.

## 수동 설치

설치 스크립트를 사용하지 않으려면 다음 파일을 직접 배치할 수 있습니다.

- `스킬 원본/SKILL.md`: Hermes의 사용자 스킬 폴더 안 `naver-search-api/SKILL.md`
- `호출기/*.py`: 같은 스킬 폴더 안 `호출기/`

다만 `스킬 원본/SKILL.md`에는 설치 경로 placeholder가 있으므로, 수동 설치보다 `설치.py --install`을 권장합니다. 설치 스크립트가 사용자별 Hermes 경로와 저장소 경로를 자동으로 삽입합니다.

## 사용법

설치 후 Hermes가 자연어 질문에 맞춰 호출기를 실행합니다. 직접 실행하려면 다음과 같이 합니다.

```bash
python "호출기/네이버_API_호출기.py" --env-file ".env" search --type news --query "AMD ComfyUI" --sort date
```

```bash
python "호출기/네이버_API_호출기.py" --env-file ".env" trend \
  --start-date 2026-01-01 --end-date 2026-03-01 --time-unit month \
  --group "LTX=LTX,LTX Video"
```

```bash
python "호출기/네이버_API_호출기.py" --env-file ".env" shopping \
  --mode categories --start-date 2026-01-01 --end-date 2026-03-01 --time-unit month \
  --category "패션의류=50000000" --category "화장품/미용=50000002"
```

## 테스트

API 키 없이 오프라인 테스트를 실행할 수 있습니다.

```bash
python "테스트/테스트_네이버_API_전체.py"
```

38개 테스트가 모두 `OK`여야 합니다.

실제 API 테스트는 본인의 `.env`가 필요하며, 네이버 API 호출량을 사용합니다.

## 보안

- API 키를 소스 코드에 넣지 않습니다.
- API 키를 명령행 인자로 넣지 않습니다.
- `.env`를 Git에 추가하지 않습니다.
- 공개 이슈·Pull Request·스크린샷에 키를 붙여 넣지 않습니다.
- 이미 공개된 키는 즉시 NAVER API Hub에서 폐기하고 새 키를 발급합니다.

## 범위와 한계

- 검색 API가 반환한 제목·요약·URL을 정리합니다. URL의 원문 본문을 자동 검증하는 도구는 아닙니다.
- Data Lab의 `ratio`는 절대 검색량·클릭 수가 아니라 상대 비율입니다.
- 검색 결과와 검색어는 Hermes 대화·터미널 기록에 남을 수 있습니다.
- 쇼핑인사이트는 잘못된 `cat_id`에도 HTTP 200과 빈 `data`를 반환할 수 있으므로, 빈 결과를 데이터 부재로 단정하지 않습니다.
- 검색 API 하루 호출 한도는 25,000회, Data Lab은 각 1,000회입니다. 네이버 정책에 따라 변경될 수 있습니다.
