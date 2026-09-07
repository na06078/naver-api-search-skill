# 네이버_API_호출기.py
"""네이버 API 호출기 CLI 진입점 (PRD 6장, 11.1).

의존성: 계약·설정·전송·검증·정규화·오류 모듈 전부.

사용:
    python "네이버_API_호출기.py" search --type news --query "AMD" --sort date
    python "네이버_API_호출기.py" trend  --start-date 2026-01-01 --end-date 2026-03-01 \
        --time-unit month --group "LTX=LTX,LTX Video"
    python "네이버_API_호출기.py" shopping --mode categories \
        --start-date 2026-01-01 --end-date 2026-03-01 --time-unit month \
        --category "패션의류=50000000"

출력: 성공/오류 모두 표준 출력에 JSON 하나. 진단은 표준 오류.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import 네이버_API_계약 as 계약
import 네이버_API_검증 as 검증
import 네이버_API_설정 as 설정
import 네이버_API_오류 as 오류
import 네이버_API_전송 as 전송
import 네이버_API_정규화 as 정규화

DEFAULT_TIMEOUT = 20.0
DEFAULT_MAX_RETRIES = 1

# 종료 코드 (PRD 6.1)
EXIT_OK = 0
EXIT_ARG = 2
EXIT_CONFIG = 3
EXIT_API = 4
EXIT_NETWORK = 5
EXIT_INTERNAL = 6

_CODE_TO_EXIT: dict[str, int] = {
    "E_ARG_INVALID": EXIT_ARG,
    "E_SCHEMA_INVALID": EXIT_ARG,
    "E_CONFIG_MISSING": EXIT_CONFIG,
    "E_CONFIG_INVALID": EXIT_CONFIG,
    "E_NETWORK_TIMEOUT": EXIT_NETWORK,
    "E_NETWORK": EXIT_NETWORK,
    "E_API_BAD_REQUEST": EXIT_API,
    "E_API_AUTH": EXIT_API,
    "E_API_PERMISSION": EXIT_API,
    "E_API_RATE_LIMIT": EXIT_API,
    "E_API_SERVER": EXIT_API,
    "E_API_RESPONSE": EXIT_API,
    "E_INTERNAL": EXIT_INTERNAL,
}


# ---- 실행 조립 (PRD 10.3~10.5) ----

def _auth_headers(cred: 설정.NaverCredentials) -> dict[str, str]:
    return {
        계약.HEADER_CLIENT_ID: cred.client_id,
        계약.HEADER_CLIENT_SECRET: cred.client_secret,
    }


def _send_with_retry(
    transport: 전송.HttpTransport,
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
    timeout: float,
    max_retries: int,
) -> 전송.HttpResponse:
    """timeout/5xx만 최대 max_retries회 재시도한다 (PRD 9.2)."""
    attempt = 0
    while True:
        try:
            resp = transport.request(method, url, headers, body, timeout)
        except 오류.CallerError as exc:
            if exc.code in ("E_NETWORK_TIMEOUT",) and attempt < max_retries:
                attempt += 1
                continue
            raise
        if 500 <= resp.status_code < 600 and attempt < max_retries:
            attempt += 1
            continue
        return resp


def execute_search(
    request: 계약.SearchRequest,
    credentials: 설정.NaverCredentials,
    transport: 전송.HttpTransport,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict[str, Any]:
    검증.validate_search(request)
    from urllib.parse import urlencode

    params = 정규화.build_search_params(request)
    url = 계약.SEARCH_ENDPOINTS[request.kind] + "?" + urlencode(params)
    resp = _send_with_retry(
        transport, "GET", url, _auth_headers(credentials), None, timeout, max_retries
    )
    if resp.status_code != 200:
        raise 오류.http_status_to_error(resp.status_code)
    raw = 전송.parse_json_body(resp)
    return 정규화.normalize_search_response(request.kind, request, raw)


def execute_trend(
    request: 계약.TrendRequest,
    credentials: 설정.NaverCredentials,
    transport: 전송.HttpTransport,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict[str, Any]:
    검증.validate_trend(request)
    payload = 정규화.build_trend_payload(request)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = _auth_headers(credentials)
    headers["Content-Type"] = "application/json"
    resp = _send_with_retry(
        transport, "POST", 계약.DATALAB_TREND_URL, headers, body, timeout, max_retries
    )
    if resp.status_code != 200:
        raise 오류.http_status_to_error(resp.status_code)
    raw = 전송.parse_json_body(resp)
    request_view = {
        "start_date": request.start_date,
        "end_date": request.end_date,
        "time_unit": request.time_unit,
    }
    return 정규화.normalize_datalab_response("search_trend", request_view, raw)


def execute_shopping(
    request: 계약.ShoppingRequest,
    credentials: 설정.NaverCredentials,
    transport: 전송.HttpTransport,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict[str, Any]:
    검증.validate_shopping(request)
    payload = 정규화.build_shopping_payload(request)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = _auth_headers(credentials)
    headers["Content-Type"] = "application/json"
    url = 계약.SHOPPING_ENDPOINTS[request.mode]
    resp = _send_with_retry(
        transport, "POST", url, headers, body, timeout, max_retries
    )
    if resp.status_code != 200:
        raise 오류.http_status_to_error(resp.status_code)
    raw = 전송.parse_json_body(resp)
    request_view = {
        "mode": request.mode.value,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "time_unit": request.time_unit,
    }
    return 정규화.normalize_datalab_response("shopping_insight", request_view, raw)


# ---- CLI 파서 ----

def _parse_pair(value: str, sep: str = "=") -> tuple[str, str]:
    if sep not in value:
        raise 오류.CallerError(
            "E_ARG_INVALID", f"'이름{sep}값' 형식이어야 합니다: {value!r}"
        )
    name, _, rest = value.partition(sep)
    if not name.strip() or not rest.strip():
        raise 오류.CallerError(
            "E_ARG_INVALID", f"이름과 값이 모두 필요합니다: {value!r}"
        )
    return name.strip(), rest.strip()


def _parse_group(value: str) -> 계약.KeywordGroup:
    name, rest = _parse_pair(value, "=")
    keywords = tuple(k.strip() for k in rest.split(",") if k.strip())
    if not keywords:
        raise 오류.CallerError("E_ARG_INVALID", f"그룹 검색어가 비어 있습니다: {value!r}")
    return 계약.KeywordGroup(name=name, keywords=keywords)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="네이버_API_호출기",
        description="네이버 검색/Data Lab API 호출기 (개인용).",
    )
    parser.add_argument("--env-file", type=str, default=None, help="로컬 .env 경로")
    sub = parser.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("search", help="네이버 검색 API 호출")
    ps.add_argument("--type", required=True, choices=[k.value for k in 계약.SearchKind])
    ps.add_argument("--query", required=True)
    ps.add_argument("--display", type=int, default=10)
    ps.add_argument("--start", type=int, default=1)
    ps.add_argument("--sort", default=None)
    ps.add_argument("--filter", dest="image_filter", default=None)

    pt = sub.add_parser("trend", help="Data Lab 검색어트렌드 호출")
    pt.add_argument("--start-date", required=True)
    pt.add_argument("--end-date", required=True)
    pt.add_argument("--time-unit", required=True, choices=list(계약.TIME_UNITS))
    pt.add_argument("--group", action="append", default=[], help="이름=검색어1,검색어2")
    pt.add_argument("--device", default=None)
    pt.add_argument("--gender", default=None)
    pt.add_argument("--age", action="append", default=[])

    psh = sub.add_parser("shopping", help="Data Lab 쇼핑인사이트 호출")
    psh.add_argument("--mode", required=True, choices=[m.value for m in 계약.ShoppingMode])
    psh.add_argument("--start-date", required=True)
    psh.add_argument("--end-date", required=True)
    psh.add_argument("--time-unit", required=True, choices=list(계약.TIME_UNITS))
    psh.add_argument("--category", action="append", default=[], help="이름=코드")
    psh.add_argument("--category-code", default=None)
    psh.add_argument("--keyword", action="append", default=[], help="이름=검색어")
    psh.add_argument("--device", default=None)
    psh.add_argument("--gender", default=None)
    psh.add_argument("--age", action="append", default=[])

    sub.add_parser("help", help="사용법 출력(비밀값 미표시)")
    return parser


def _build_search_request(args: argparse.Namespace) -> 계약.SearchRequest:
    return 계약.SearchRequest(
        kind=계약.SearchKind(args.type),
        query=args.query,
        display=args.display,
        start=args.start,
        sort=args.sort,
        image_filter=args.image_filter,
    )


def _build_trend_request(args: argparse.Namespace) -> 계약.TrendRequest:
    groups = tuple(_parse_group(g) for g in args.group)
    return 계약.TrendRequest(
        start_date=args.start_date,
        end_date=args.end_date,
        time_unit=args.time_unit,
        keyword_groups=groups,
        device=args.device,
        gender=args.gender,
        ages=tuple(args.age),
    )


def _build_shopping_request(args: argparse.Namespace) -> 계약.ShoppingRequest:
    categories = tuple(_parse_pair(c) for c in args.category)
    keywords = tuple(_parse_pair(k) for k in args.keyword)
    return 계약.ShoppingRequest(
        mode=계약.ShoppingMode(args.mode),
        start_date=args.start_date,
        end_date=args.end_date,
        time_unit=args.time_unit,
        category_code=args.category_code,
        categories=categories,
        keywords=keywords,
        device=args.device,
        gender=args.gender,
        ages=tuple(args.age),
    )


def _help_text() -> dict[str, Any]:
    return {
        "schema_version": 계약.SCHEMA_VERSION,
        "ok": True,
        "provider": "naver",
        "operation": "help",
        "kind": "help",
        "response": {
            "commands": ["search", "trend", "shopping", "help"],
            "search_types": [k.value for k in 계약.SearchKind],
            "shopping_modes": [m.value for m in 계약.ShoppingMode],
            "env_vars": [설정.ENV_CLIENT_ID, 설정.ENV_CLIENT_SECRET],
            "docs": "https://developers.naver.com/docs/serviceapi/search/blog/blog.md",
            "note": "API 키는 로컬 .env에만 저장하며 명령행 인자로 받지 않습니다.",
        },
    }


def run(
    argv: Sequence[str],
    transport: 전송.HttpTransport | None = None,
) -> tuple[dict[str, Any], int]:
    """CLI 인자를 받아 (출력 dict, 종료 코드)를 반환한다.

    transport를 주입하면 테스트에서 네트워크 없이 실행할 수 있다.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "help":
        return _help_text(), EXIT_OK

    operation = "search" if args.command == "search" else "datalab"
    kind = args.type if args.command == "search" else (
        "search_trend" if args.command == "trend" else "shopping_insight"
    )

    try:
        transport = transport or 전송.UrllibTransport()
        env_file = Path(args.env_file) if args.env_file else None
        credentials = 설정.load_credentials(env_file)

        if args.command == "search":
            result = execute_search(_build_search_request(args), credentials, transport)
        elif args.command == "trend":
            result = execute_trend(_build_trend_request(args), credentials, transport)
        else:
            result = execute_shopping(_build_shopping_request(args), credentials, transport)
        return result, EXIT_OK

    except 설정.ConfigError as exc:
        err = 오류.CallerError(exc.code, exc.message)
        return 오류.error_envelope(operation, kind, err), _CODE_TO_EXIT[err.code]
    except 오류.CallerError as exc:
        return 오류.error_envelope(operation, kind, exc), _CODE_TO_EXIT.get(
            exc.code, EXIT_INTERNAL
        )


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    result, code = run(argv)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
