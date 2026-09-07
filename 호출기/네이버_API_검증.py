# 네이버_API_검증.py
"""검색·Data Lab 요청 입력을 네이버 요청 전에 검증하는 모듈 (PRD 4.3~4.6).

의존성: 계약 모듈, 오류 모듈.

원칙: 잘못된 입력을 조용히 다른 의미로 바꾸지 않고 CallerError로 거부한다.
"""

from __future__ import annotations

import re

import 네이버_API_계약 as 계약
import 네이버_API_오류 as 오류

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fail_arg(message: str) -> None:
    raise 오류.CallerError("E_ARG_INVALID", message)


def _fail_schema(message: str) -> None:
    raise 오류.CallerError("E_SCHEMA_INVALID", message)


def _validate_date(label: str, value: str) -> None:
    if not _DATE_RE.match(value):
        _fail_schema(f"{label}는 yyyy-mm-dd 형식이어야 합니다: {value!r}")
    # 실제 달력 유효성까지 확인한다.
    import datetime

    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        _fail_schema(f"{label}가 존재하지 않는 날짜입니다: {value!r}")


def _validate_date_order(start: str, end: str, min_date: str) -> None:
    import datetime

    s = datetime.date.fromisoformat(start)
    e = datetime.date.fromisoformat(end)
    m = datetime.date.fromisoformat(min_date)
    if s > e:
        _fail_schema(f"시작일({start})이 종료일({end})보다 늦습니다.")
    if s < m:
        _fail_schema(f"시작일({start})은 최소 조회 가능일({min_date}) 이후여야 합니다.")


# ---- 검색 요청 검증 (PRD 4.3) ----

def validate_search(request: 계약.SearchRequest) -> None:
    """검색 요청을 검증한다. 문제가 있으면 CallerError를 던진다."""
    kind = request.kind

    if not request.query or not request.query.strip():
        _fail_arg("검색어(query)가 비어 있습니다.")

    lo, hi = 계약.SEARCH_DISPLAY_RANGE[kind]
    if not isinstance(request.display, int) or not (lo <= request.display <= hi):
        _fail_arg(
            f"{kind.value} 검색의 display는 {lo}~{hi} 범위여야 합니다: {request.display!r}"
        )

    lo_s, hi_s = 계약.SEARCH_START_RANGE[kind]
    if not isinstance(request.start, int) or not (lo_s <= request.start <= hi_s):
        _fail_arg(
            f"{kind.value} 검색의 start는 {lo_s}~{hi_s} 범위여야 합니다: {request.start!r}"
        )

    allowed_sorts = 계약.SEARCH_SORTS[kind]
    if request.sort is not None:
        if not allowed_sorts:
            _fail_arg(f"{kind.value} 검색은 sort 파라미터를 지원하지 않습니다.")
        if request.sort not in allowed_sorts:
            _fail_arg(
                f"{kind.value} 검색의 sort 허용값은 {allowed_sorts}입니다: {request.sort!r}"
            )

    if request.image_filter is not None:
        if kind is not 계약.SearchKind.IMAGE:
            _fail_arg("filter 파라미터는 이미지 검색에서만 사용할 수 있습니다.")
        if request.image_filter not in 계약.IMAGE_FILTERS:
            _fail_arg(
                f"이미지 filter 허용값은 {계약.IMAGE_FILTERS}입니다: {request.image_filter!r}"
            )


# ---- 검색어트렌드 검증 (PRD 4.5) ----

def validate_trend(request: 계약.TrendRequest) -> None:
    _validate_date("startDate", request.start_date)
    _validate_date("endDate", request.end_date)
    _validate_date_order(request.start_date, request.end_date, 계약.TREND_MIN_DATE)

    if request.time_unit not in 계약.TIME_UNITS:
        _fail_schema(f"timeUnit 허용값은 {계약.TIME_UNITS}입니다: {request.time_unit!r}")

    groups = request.keyword_groups
    if not groups:
        _fail_schema("keywordGroups가 비어 있습니다. 최소 1개가 필요합니다.")
    if len(groups) > 계약.TREND_MAX_GROUPS:
        _fail_schema(
            f"keywordGroups는 최대 {계약.TREND_MAX_GROUPS}개입니다: {len(groups)}개"
        )
    for group in groups:
        if not group.name or not group.name.strip():
            _fail_schema("keywordGroups의 groupName이 비어 있습니다.")
        if not group.keywords:
            _fail_schema(f"그룹 {group.name!r}의 keywords가 비어 있습니다.")
        if len(group.keywords) > 계약.TREND_MAX_KEYWORDS_PER_GROUP:
            _fail_schema(
                f"그룹 {group.name!r}의 keywords는 최대 "
                f"{계약.TREND_MAX_KEYWORDS_PER_GROUP}개입니다: {len(group.keywords)}개"
            )
        for kw in group.keywords:
            if not kw or not kw.strip():
                _fail_schema(f"그룹 {group.name!r}에 빈 검색어가 있습니다.")

    if request.device is not None and request.device not in 계약.TREND_DEVICES:
        _fail_schema(f"device 허용값은 {계약.TREND_DEVICES}입니다: {request.device!r}")
    if request.gender is not None and request.gender not in 계약.TREND_GENDERS:
        _fail_schema(f"gender 허용값은 {계약.TREND_GENDERS}입니다: {request.gender!r}")
    for age in request.ages:
        if age not in 계약.TREND_AGES:
            _fail_schema(f"검색어트렌드 age 허용값은 {계약.TREND_AGES}입니다: {age!r}")


# ---- 쇼핑인사이트 검증 (PRD 4.6) ----

def validate_shopping(request: 계약.ShoppingRequest) -> None:
    mode = request.mode

    _validate_date("startDate", request.start_date)
    _validate_date("endDate", request.end_date)
    _validate_date_order(request.start_date, request.end_date, 계약.SHOPPING_MIN_DATE)

    if request.time_unit not in 계약.TIME_UNITS:
        _fail_schema(f"timeUnit 허용값은 {계약.TIME_UNITS}입니다: {request.time_unit!r}")

    # 카테고리 목록 모드 (categories)
    if mode in 계약.SHOPPING_MODES_NEED_CATEGORY_LIST:
        if not request.categories:
            _fail_schema(f"{mode.value} 모드는 category 목록이 필요합니다.")
        if len(request.categories) > 계약.SHOPPING_MAX_CATEGORIES:
            _fail_schema(
                f"category는 최대 {계약.SHOPPING_MAX_CATEGORIES}개입니다: "
                f"{len(request.categories)}개"
            )
        for name, code in request.categories:
            if not name.strip() or not code.strip():
                _fail_schema("category의 이름 또는 코드가 비어 있습니다.")
        if request.keywords:
            _fail_arg(f"{mode.value} 모드는 keyword를 사용하지 않습니다.")

    # 단일 카테고리 코드가 필요한 모드
    if mode in 계약.SHOPPING_MODES_NEED_SINGLE_CATEGORY_CODE:
        if not request.category_code or not request.category_code.strip():
            _fail_arg(
                f"{mode.value} 모드는 카테고리 코드(category_code)가 필요합니다. "
                "네이버 쇼핑 URL의 cat_id 값을 확인하십시오."
            )
        if request.categories:
            _fail_arg(f"{mode.value} 모드는 category 목록을 사용하지 않습니다.")

    # 키워드 그룹 목록이 필요한 모드 (category-keywords)
    if mode in 계약.SHOPPING_MODES_NEED_KEYWORD_GROUPS:
        if not request.keywords:
            _fail_schema(f"{mode.value} 모드는 keyword 그룹이 필요합니다.")
        if len(request.keywords) > 계약.SHOPPING_MAX_KEYWORD_GROUPS:
            _fail_schema(
                f"keyword 그룹은 최대 {계약.SHOPPING_MAX_KEYWORD_GROUPS}개입니다: "
                f"{len(request.keywords)}개"
            )
        for name, kw in request.keywords:
            if not name.strip() or not kw.strip():
                _fail_schema("keyword 그룹의 이름 또는 검색어가 비어 있습니다.")

    # 단일 키워드가 필요한 모드 (category-keyword-*)
    if mode in 계약.SHOPPING_MODES_NEED_SINGLE_KEYWORD:
        if len(request.keywords) != 1:
            _fail_schema(
                f"{mode.value} 모드는 keyword 하나가 필요합니다: "
                f"{len(request.keywords)}개"
            )
        name, kw = request.keywords[0]
        if not kw.strip():
            _fail_schema("keyword가 비어 있습니다.")

    # 공통 device/gender/age
    if request.device is not None and request.device not in 계약.SHOPPING_DEVICES:
        _fail_schema(f"device 허용값은 {계약.SHOPPING_DEVICES}입니다: {request.device!r}")
    if request.gender is not None and request.gender not in 계약.SHOPPING_GENDERS:
        _fail_schema(f"gender 허용값은 {계약.SHOPPING_GENDERS}입니다: {request.gender!r}")
    for age in request.ages:
        if age not in 계약.SHOPPING_AGES:
            _fail_schema(f"쇼핑인사이트 age 허용값은 {계약.SHOPPING_AGES}입니다: {age!r}")
