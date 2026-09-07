# 네이버_API_계약.py
"""네이버 API 호출기의 계약(contract) 정의 모듈.

이 모듈은 다른 모듈에 의존하지 않는다. 검색 종류, Data Lab 모드, 요청
데이터 모델, 허용 endpoint, 입력 제약 상수를 한곳에 모아 둔다.

주의: 클래스·함수·필드 이름은 PRD 10장의 인터페이스 계약이므로 임의로
바꾸지 않는다. 값(문자열)은 네이버 공식 문서를 기준으로 한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# 표준 출력 스키마 버전 (PRD 5장)
SCHEMA_VERSION = "1.0"

# NAVER API Hub(NCloud) 규격.
# 2026년 네이버 검색·Data Lab API가 개발자센터(openapi.naver.com)에서
# NAVER API Hub(naverapihub.apigw.ntruss.com)로 이관되어 도메인·경로·인증
# 헤더가 모두 바뀌었다. 아래는 API Hub 현행 규격이다.
API_BASE = "https://naverapihub.apigw.ntruss.com"

# 모든 요청이 향하는 유일한 허용 호스트 (PRD 8.4)
ALLOWED_HOST = "naverapihub.apigw.ntruss.com"
ALLOWED_SCHEME = "https"

# API Hub 인증 헤더 이름 (Client ID / Client Secret에 매핑)
HEADER_CLIENT_ID = "X-NCP-APIGW-API-KEY-ID"
HEADER_CLIENT_SECRET = "X-NCP-APIGW-API-KEY"


class SearchKind(StrEnum):
    """네이버 검색 API 7종 (PRD 4.2)."""

    BLOG = "blog"
    IMAGE = "image"
    KIN = "kin"
    LOCAL = "local"
    NEWS = "news"
    WEB = "web"
    CAFE = "cafe"


class ShoppingMode(StrEnum):
    """네이버 Data Lab 쇼핑인사이트 8개 모드 (PRD 4.6)."""

    CATEGORIES = "categories"
    CATEGORY_DEVICE = "category-device"
    CATEGORY_GENDER = "category-gender"
    CATEGORY_AGE = "category-age"
    CATEGORY_KEYWORDS = "category-keywords"
    CATEGORY_KEYWORD_DEVICE = "category-keyword-device"
    CATEGORY_KEYWORD_GENDER = "category-keyword-gender"
    CATEGORY_KEYWORD_AGE = "category-keyword-age"


# 검색 종류별 JSON 요청 주소 (NAVER API Hub 경로)
SEARCH_ENDPOINTS: dict[SearchKind, str] = {
    SearchKind.BLOG: f"{API_BASE}/search/v1/blog",
    SearchKind.IMAGE: f"{API_BASE}/search/v1/image",
    SearchKind.KIN: f"{API_BASE}/search/v1/kin",
    SearchKind.LOCAL: f"{API_BASE}/search/v1/local",
    SearchKind.NEWS: f"{API_BASE}/search/v1/news",
    SearchKind.WEB: f"{API_BASE}/search/v1/webkr",
    SearchKind.CAFE: f"{API_BASE}/search/v1/cafearticle",
}

# Data Lab 검색어트렌드 요청 주소 (API Hub 경로)
DATALAB_TREND_URL = f"{API_BASE}/search-trend/v1/search"

# 쇼핑인사이트 모드별 요청 주소 (API Hub 경로)
SHOPPING_ENDPOINTS: dict[ShoppingMode, str] = {
    ShoppingMode.CATEGORIES: f"{API_BASE}/shopping/v1/categories",
    ShoppingMode.CATEGORY_DEVICE: f"{API_BASE}/shopping/v1/category/device",
    ShoppingMode.CATEGORY_GENDER: f"{API_BASE}/shopping/v1/category/gender",
    ShoppingMode.CATEGORY_AGE: f"{API_BASE}/shopping/v1/category/age",
    ShoppingMode.CATEGORY_KEYWORDS: f"{API_BASE}/shopping/v1/category/keywords",
    ShoppingMode.CATEGORY_KEYWORD_DEVICE: f"{API_BASE}/shopping/v1/category/keyword/device",
    ShoppingMode.CATEGORY_KEYWORD_GENDER: f"{API_BASE}/shopping/v1/category/keyword/gender",
    ShoppingMode.CATEGORY_KEYWORD_AGE: f"{API_BASE}/shopping/v1/category/keyword/age",
}

# 검색 종류별 허용 정렬 값 (PRD 4.3)
SEARCH_SORTS: dict[SearchKind, tuple[str, ...]] = {
    SearchKind.BLOG: ("sim", "date"),
    SearchKind.IMAGE: ("sim", "date"),
    SearchKind.KIN: ("sim", "date", "point"),
    SearchKind.LOCAL: ("random", "comment"),
    SearchKind.NEWS: ("sim", "date"),
    SearchKind.WEB: (),  # 웹문서는 sort 미사용
    SearchKind.CAFE: ("sim", "date"),
}

# 검색 종류별 기본 정렬 값 (문서 기본값)
SEARCH_DEFAULT_SORT: dict[SearchKind, str | None] = {
    SearchKind.BLOG: "sim",
    SearchKind.IMAGE: "sim",
    SearchKind.KIN: "sim",
    SearchKind.LOCAL: "random",
    SearchKind.NEWS: "sim",
    SearchKind.WEB: None,
    SearchKind.CAFE: "sim",
}

# display 허용 범위 (PRD 4.3). (최소, 최대)
SEARCH_DISPLAY_RANGE: dict[SearchKind, tuple[int, int]] = {
    SearchKind.BLOG: (1, 100),
    SearchKind.IMAGE: (1, 100),
    SearchKind.KIN: (1, 100),
    SearchKind.LOCAL: (1, 5),
    SearchKind.NEWS: (1, 100),
    SearchKind.WEB: (1, 100),
    SearchKind.CAFE: (1, 100),
}

# start 허용 범위 (PRD 4.3). (최소, 최대)
SEARCH_START_RANGE: dict[SearchKind, tuple[int, int]] = {
    SearchKind.BLOG: (1, 1000),
    SearchKind.IMAGE: (1, 1000),
    SearchKind.KIN: (1, 1000),
    SearchKind.LOCAL: (1, 1),
    SearchKind.NEWS: (1, 1000),
    SearchKind.WEB: (1, 1000),
    SearchKind.CAFE: (1, 1000),
}

# 이미지 검색 전용 filter 허용 값 (PRD 4.3)
IMAGE_FILTERS: tuple[str, ...] = ("all", "large", "medium", "small")

# Data Lab 공통 구간 단위
TIME_UNITS: tuple[str, ...] = ("date", "week", "month")

# 검색어트렌드 device/gender/age (PRD 4.5)
TREND_DEVICES: tuple[str, ...] = ("pc", "mo")
TREND_GENDERS: tuple[str, ...] = ("m", "f")
TREND_AGES: tuple[str, ...] = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11")

# 쇼핑인사이트 device/gender/age (PRD 4.6)
SHOPPING_DEVICES: tuple[str, ...] = ("pc", "mo")
SHOPPING_GENDERS: tuple[str, ...] = ("m", "f")
SHOPPING_AGES: tuple[str, ...] = ("10", "20", "30", "40", "50", "60")

# 검색어트렌드 개수 제한 (PRD 4.5)
TREND_MAX_GROUPS = 5
TREND_MAX_KEYWORDS_PER_GROUP = 20

# 검색어트렌드 조회 가능 최소 시작일 (PRD 4.5)
TREND_MIN_DATE = "2016-01-01"

# 쇼핑인사이트 개수·최소 시작일 (PRD 4.6)
SHOPPING_MAX_CATEGORIES = 3
SHOPPING_MAX_KEYWORD_GROUPS = 5
SHOPPING_MIN_DATE = "2017-08-01"

# 모드별로 category 코드 하나가 필요한지, 카테고리 목록이 필요한지 구분
SHOPPING_MODES_NEED_CATEGORY_LIST: frozenset[ShoppingMode] = frozenset(
    {ShoppingMode.CATEGORIES}
)
SHOPPING_MODES_NEED_KEYWORD_GROUPS: frozenset[ShoppingMode] = frozenset(
    {ShoppingMode.CATEGORY_KEYWORDS}
)
SHOPPING_MODES_NEED_SINGLE_KEYWORD: frozenset[ShoppingMode] = frozenset(
    {
        ShoppingMode.CATEGORY_KEYWORD_DEVICE,
        ShoppingMode.CATEGORY_KEYWORD_GENDER,
        ShoppingMode.CATEGORY_KEYWORD_AGE,
    }
)
SHOPPING_MODES_NEED_SINGLE_CATEGORY_CODE: frozenset[ShoppingMode] = frozenset(
    {
        ShoppingMode.CATEGORY_DEVICE,
        ShoppingMode.CATEGORY_GENDER,
        ShoppingMode.CATEGORY_AGE,
        ShoppingMode.CATEGORY_KEYWORDS,
        ShoppingMode.CATEGORY_KEYWORD_DEVICE,
        ShoppingMode.CATEGORY_KEYWORD_GENDER,
        ShoppingMode.CATEGORY_KEYWORD_AGE,
    }
)


# ---- 요청 데이터 모델 (PRD 10장) ----

@dataclass(frozen=True)
class SearchRequest:
    """네이버 검색 요청 (PRD 10.3)."""

    kind: SearchKind
    query: str
    display: int = 10
    start: int = 1
    sort: str | None = None
    image_filter: str | None = None


@dataclass(frozen=True)
class KeywordGroup:
    """검색어트렌드 주제어 묶음 (PRD 10.4)."""

    name: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class TrendRequest:
    """검색어트렌드 요청 (PRD 10.4)."""

    start_date: str
    end_date: str
    time_unit: str
    keyword_groups: tuple[KeywordGroup, ...]
    device: str | None = None
    gender: str | None = None
    ages: tuple[str, ...] = ()


@dataclass(frozen=True)
class ShoppingRequest:
    """쇼핑인사이트 요청 (PRD 10.5).

    categories, keywords는 (표시이름, 값) 쌍의 튜플이다.
    """

    mode: ShoppingMode
    start_date: str
    end_date: str
    time_unit: str
    category_code: str | None = None
    categories: tuple[tuple[str, str], ...] = ()
    keywords: tuple[tuple[str, str], ...] = ()
    device: str | None = None
    gender: str | None = None
    ages: tuple[str, ...] = ()
