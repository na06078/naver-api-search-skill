# 네이버_API_정규화.py
"""요청 payload 생성과 응답 정규화 모듈 (PRD 5장, 4장).

의존성: 계약 모듈, 오류 모듈.

- build_search_url: 검색 요청 → (url, query string 파라미터)
- build_trend_payload / build_shopping_payload: Data Lab POST 본문 dict
- normalize_search_response: 원본 검색 JSON → 표준 items envelope
- normalize_datalab_response: 원본 Data Lab JSON → 표준 series envelope
- strip_highlight: <b> 등 HTML 태그 제거
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone, timedelta
from typing import Any

import 네이버_API_계약 as 계약
import 네이버_API_오류 as 오류

_KST = timezone(timedelta(hours=9))
_TAG_RE = re.compile(r"<[^>]+>")


def now_iso() -> str:
    """호출기가 생성하는 요청 시각(KST, ISO 8601)."""
    return datetime.now(_KST).replace(microsecond=0).isoformat()


def strip_highlight(text: str | None) -> str:
    """네이버 결과의 <b> 강조 태그와 HTML 엔티티를 제거한다 (PRD 5.2)."""
    if not text:
        return ""
    no_tags = _TAG_RE.sub("", text)
    return html.unescape(no_tags).strip()


# ---- 검색 요청 payload ----

def build_search_params(request: 계약.SearchRequest) -> dict[str, str]:
    """검색 GET query string 파라미터를 만든다.

    query는 urllib이 인코딩하도록 원문 그대로 담는다.
    """
    params: dict[str, str] = {
        "query": request.query,
        "display": str(request.display),
        "start": str(request.start),
    }
    # sort: 명시값이 있으면 그대로, 없으면 종류별 기본값(있을 때만)
    sort = request.sort if request.sort is not None else 계약.SEARCH_DEFAULT_SORT[request.kind]
    if sort is not None:
        params["sort"] = sort
    if request.kind is 계약.SearchKind.IMAGE:
        params["filter"] = request.image_filter or "all"
    return params


# ---- Data Lab 요청 payload ----

def build_trend_payload(request: 계약.TrendRequest) -> dict[str, Any]:
    """검색어트렌드 POST 본문 (PRD 4.5)."""
    payload: dict[str, Any] = {
        "startDate": request.start_date,
        "endDate": request.end_date,
        "timeUnit": request.time_unit,
        "keywordGroups": [
            {"groupName": g.name, "keywords": list(g.keywords)}
            for g in request.keyword_groups
        ],
    }
    if request.device is not None:
        payload["device"] = request.device
    if request.gender is not None:
        payload["gender"] = request.gender
    if request.ages:
        payload["ages"] = list(request.ages)
    return payload


def build_shopping_payload(request: 계약.ShoppingRequest) -> dict[str, Any]:
    """쇼핑인사이트 POST 본문 (PRD 4.6). 모드별 필드를 채운다."""
    mode = request.mode
    payload: dict[str, Any] = {
        "startDate": request.start_date,
        "endDate": request.end_date,
        "timeUnit": request.time_unit,
    }

    if mode in 계약.SHOPPING_MODES_NEED_CATEGORY_LIST:
        payload["category"] = [
            {"name": name, "param": [code]} for name, code in request.categories
        ]
    if mode in 계약.SHOPPING_MODES_NEED_SINGLE_CATEGORY_CODE:
        payload["category"] = request.category_code

    if mode in 계약.SHOPPING_MODES_NEED_KEYWORD_GROUPS:
        payload["keyword"] = [
            {"name": name, "param": [kw]} for name, kw in request.keywords
        ]
    if mode in 계약.SHOPPING_MODES_NEED_SINGLE_KEYWORD:
        payload["keyword"] = request.keywords[0][1]

    if request.device is not None:
        payload["device"] = request.device
    if request.gender is not None:
        payload["gender"] = request.gender
    if request.ages:
        payload["ages"] = list(request.ages)
    return payload


# ---- 검색 응답 정규화 (PRD 5.2) ----

def _normalize_search_item(kind: 계약.SearchKind, raw: dict[str, Any]) -> dict[str, Any]:
    title = strip_highlight(raw.get("title"))
    description = strip_highlight(raw.get("description"))
    item: dict[str, Any] = {
        "title": title,
        "url": raw.get("link", ""),
        "description": description,
        "published_at": None,
        "source_name": None,
        "source_url": None,
        "thumbnail_url": None,
        "metadata": {},
    }

    if kind is 계약.SearchKind.BLOG:
        item["source_name"] = raw.get("bloggername")
        item["source_url"] = raw.get("bloggerlink")
        item["published_at"] = raw.get("postdate")
    elif kind is 계약.SearchKind.NEWS:
        item["source_url"] = raw.get("originallink")
        item["published_at"] = raw.get("pubDate")
    elif kind is 계약.SearchKind.CAFE:
        item["source_name"] = raw.get("cafename")
        item["source_url"] = raw.get("cafeurl")
    elif kind is 계약.SearchKind.IMAGE:
        item["thumbnail_url"] = raw.get("thumbnail")
        item["metadata"] = {
            "size_height": raw.get("sizeheight"),
            "size_width": raw.get("sizewidth"),
        }
    elif kind is 계약.SearchKind.LOCAL:
        # 지역은 title/description도 강조 태그가 없지만 동일 처리한다.
        item["metadata"] = {
            "category": raw.get("category"),
            "address": raw.get("address"),
            "road_address": raw.get("roadAddress"),
            "mapx": raw.get("mapx"),
            "mapy": raw.get("mapy"),
        }
        # telephone은 문서상 값을 반환하지 않는 요소이므로 유효 전화로 취급하지 않는다.
    return item


def normalize_search_response(
    kind: 계약.SearchKind, request: 계약.SearchRequest, raw: dict[str, Any]
) -> dict[str, Any]:
    """원본 검색 JSON을 표준 성공 envelope로 변환한다."""
    items_raw = raw.get("items")
    if not isinstance(items_raw, list):
        raise 오류.CallerError(
            "E_API_RESPONSE", "검색 응답에 items 배열이 없습니다."
        )
    items = [_normalize_search_item(kind, it) for it in items_raw if isinstance(it, dict)]

    request_view: dict[str, Any] = {
        "query": request.query,
        "display": request.display,
        "start": request.start,
    }
    sort = request.sort if request.sort is not None else 계약.SEARCH_DEFAULT_SORT[kind]
    if sort is not None:
        request_view["sort"] = sort
    if kind is 계약.SearchKind.IMAGE:
        request_view["filter"] = request.image_filter or "all"

    return {
        "schema_version": 계약.SCHEMA_VERSION,
        "ok": True,
        "provider": "naver",
        "operation": "search",
        "kind": kind.value,
        "requested_at": now_iso(),
        "request": request_view,
        "response": {
            "total": raw.get("total", 0),
            "start": raw.get("start", request.start),
            "display": raw.get("display", len(items)),
            "items": items,
        },
    }


# ---- Data Lab 응답 정규화 (PRD 5.3) ----

def _normalize_series(raw_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for res in raw_results:
        if not isinstance(res, dict):
            continue
        # 검색어트렌드는 keywords(array), 쇼핑인사이트는 keyword(array) 사용
        keywords = res.get("keywords")
        if keywords is None:
            keywords = res.get("keyword", [])
        if isinstance(keywords, str):
            keywords = [keywords]
        data_points: list[dict[str, Any]] = []
        for d in res.get("data", []):
            if not isinstance(d, dict):
                continue
            data_points.append(
                {
                    "period": d.get("period"),
                    "group": d.get("group"),
                    "ratio": d.get("ratio"),
                }
            )
        series.append(
            {
                "label": res.get("title"),
                "keywords": list(keywords) if isinstance(keywords, list) else [],
                "data": data_points,
            }
        )
    return series


def normalize_datalab_response(
    kind: str, request_view: dict[str, Any], raw: dict[str, Any]
) -> dict[str, Any]:
    """원본 Data Lab JSON을 표준 성공 envelope로 변환한다.

    kind: "search_trend" 또는 "shopping_insight".
    """
    results = raw.get("results")
    if not isinstance(results, list):
        raise 오류.CallerError(
            "E_API_RESPONSE", "Data Lab 응답에 results 배열이 없습니다."
        )
    return {
        "schema_version": 계약.SCHEMA_VERSION,
        "ok": True,
        "provider": "naver",
        "operation": "datalab",
        "kind": kind,
        "requested_at": now_iso(),
        "request": request_view,
        "response": {
            "start_date": raw.get("startDate", request_view.get("start_date")),
            "end_date": raw.get("endDate", request_view.get("end_date")),
            "time_unit": raw.get("timeUnit", request_view.get("time_unit")),
            "series": _normalize_series(results),
        },
    }
