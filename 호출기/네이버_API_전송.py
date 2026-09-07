# 네이버_API_전송.py
"""HTTPS 전송 경계 모듈 (PRD 10.2, 8.4).

의존성: 계약 모듈(허용 호스트), 오류 모듈(CallerError).

- HttpTransport 프로토콜을 정의해 테스트에서 가짜 전송을 주입할 수 있게 한다.
- 표준 구현 UrllibTransport는 urllib.request만 사용한다.
- 요청 전 호스트/스킴을 검증해 openapi.naver.com·https 외 요청을 차단한다.
- TLS 검증을 끄지 않는다.
"""

from __future__ import annotations

import json
import socket
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping, Protocol
from urllib.parse import urlsplit

import 네이버_API_계약 as 계약
import 네이버_API_오류 as 오류


@dataclass(frozen=True)
class HttpResponse:
    """전송 계층이 반환하는 최소 응답 (PRD 10.2)."""

    status_code: int
    headers: Mapping[str, str]
    body: bytes


class HttpTransport(Protocol):
    """HTTP 전송 경계. 테스트는 이 프로토콜의 가짜 구현을 주입한다."""

    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> HttpResponse:
        ...


def assert_allowed_url(url: str) -> None:
    """호스트/스킴 화이트리스트를 강제한다 (PRD 8.4).

    Raises:
        CallerError(E_INTERNAL): 허용되지 않은 URL. 코드 상수만 요청하므로
        정상 경로에서는 발생하지 않지만, 방어적으로 검사한다.
    """
    parts = urlsplit(url)
    if parts.scheme != 계약.ALLOWED_SCHEME:
        raise 오류.CallerError(
            "E_INTERNAL",
            f"허용되지 않은 스킴입니다: {parts.scheme}",
        )
    if parts.hostname != 계약.ALLOWED_HOST:
        raise 오류.CallerError(
            "E_INTERNAL",
            f"허용되지 않은 호스트입니다: {parts.hostname}",
        )


class UrllibTransport:
    """urllib 기반 표준 HTTPS 전송. TLS 검증을 유지한다."""

    def __init__(self) -> None:
        # 기본 컨텍스트는 인증서/호스트명 검증을 수행한다. 끄지 않는다.
        self._ssl_context = ssl.create_default_context()

    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> HttpResponse:
        assert_allowed_url(url)
        req = urllib.request.Request(
            url=url,
            data=body,
            method=method,
            headers=dict(headers),
        )
        try:
            with urllib.request.urlopen(
                req, timeout=timeout_seconds, context=self._ssl_context
            ) as resp:
                return HttpResponse(
                    status_code=resp.status,
                    headers={k: v for k, v in resp.headers.items()},
                    body=resp.read(),
                )
        except urllib.error.HTTPError as exc:
            # HTTP 오류 응답도 상태 코드와 본문을 반환한다.
            # 리다이렉트로 호스트가 바뀌는 경우까지 방어한다.
            final_url = getattr(exc, "url", url) or url
            try:
                assert_allowed_url(final_url)
            except 오류.CallerError:
                raise 오류.CallerError(
                    "E_NETWORK",
                    "허용되지 않은 호스트로 리다이렉트되었습니다.",
                )
            body_bytes = exc.read() if hasattr(exc, "read") else b""
            return HttpResponse(
                status_code=exc.code,
                headers={k: v for k, v in (exc.headers or {}).items()},
                body=body_bytes,
            )
        except socket.timeout as exc:
            raise 오류.CallerError(
                "E_NETWORK_TIMEOUT",
                f"요청이 {timeout_seconds}초 안에 응답하지 않았습니다.",
            ) from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, socket.timeout):
                raise 오류.CallerError(
                    "E_NETWORK_TIMEOUT",
                    f"요청이 {timeout_seconds}초 안에 응답하지 않았습니다.",
                ) from exc
            raise 오류.CallerError(
                "E_NETWORK",
                "네트워크 연결에 실패했습니다(DNS/TLS/연결 오류).",
            ) from exc


def parse_json_body(response: HttpResponse) -> dict:
    """응답 본문을 JSON으로 파싱한다.

    Raises:
        CallerError(E_API_RESPONSE): JSON이 아니거나 객체가 아닐 때.
    """
    try:
        text = response.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise 오류.CallerError(
            "E_API_RESPONSE",
            "응답 본문을 UTF-8로 해석할 수 없습니다.",
            http_status=response.status_code,
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise 오류.CallerError(
            "E_API_RESPONSE",
            "응답이 JSON 형식이 아닙니다.",
            http_status=response.status_code,
        ) from exc
    if not isinstance(data, dict):
        raise 오류.CallerError(
            "E_API_RESPONSE",
            "응답 JSON이 객체 형식이 아닙니다.",
            http_status=response.status_code,
        )
    return data
