# 네이버 API 검색 스킬

네이버 검색 API 7종과 Data Lab API 2종을 로컬 Python 호출기로 실행하는 Hermes 스킬입니다. MCP 서버 없이 Hermes가 `terminal` 도구로 호출기를 실행하고, 결과를 표준 JSON으로 받습니다.

## 주요 기능

- 블로그, 이미지, 지식iN, 지역, 뉴스, 웹문서, 카페글 검색
- 검색어트렌드
- 쇼핑인사이트 8개 모드
- NAVER API Hub 인증 방식 지원
- 잘못된 파라미터 사전 검증
- HTML 강조 태그 제거와 결과 표준화
- API 키를 코드와 명령행에서 분리

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
