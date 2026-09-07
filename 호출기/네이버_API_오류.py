# 네이버_API_오류.py
"""호출기 전역에서 쓰는 오류 코드와 예외, 오류 envelope 생성 모듈.

의존성: 계약 모듈(SCHEMA_VERSION)만 참조한다.

보안 원칙 (PRD 8.3):
- 오류 메시지·envelope에 Client Secret, 인증 헤더, 요청 URL의 민감 쿼리값을
  넣지 않는다. 상위 호출부가 안전한 메시지만 전달하도록 강제한다.
"""

from __future__ import annotations

from typing import Any

import 네이버_API_계약 as 계약

# PRD 9.1 오류 코드 표
ERROR_CODES: dict[str, bool] = {
    # code: retryable
    "E_ARG_INVALID": False,
    "E_SCHEMA_INVALID": False,
    "E_CONFIG_MISSING": False,
    "E_CONFIG_INVALID": False,
    "E_NETWORK_TIMEOUT": True,
    "E_NETWORK": True,
    "E_API_BAD_REQUEST": False,
    "E_API_AUTH": False,
    "E_API_PERMISSION": False,
    "E_API_RATE_LIMIT": True,
    "E_API_SERVER": True,
    "E_API_RESPONSE": False,
    "E_INTERNAL": False,
}


class CallerError(Exception):
    """호출기 표준 예외. 표준 오류 envelope로 변환할 수 있다.

    message에는 절대로 비밀값을 넣지 않는다. 상위에서 안전한 문구만 전달한다.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int | None = None,
        provider_code: str | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        if code not in ERROR_CODES:
            # 미정의 코드는 내부 오류로 강등하되 원래 코드 문자열은 메시지에만 남긴다.
            message = f"[미정의 오류코드 {code}] {message}"
            code = "E_INTERNAL"
        self.code = code
        self.message = message
        self.http_status = http_status
        self.provider_code = provider_code
        self.retryable = ERROR_CODES[code] if retryable is None else retryable


def error_envelope(
    operation: str,
    kind: str,
    error: CallerError,
) -> dict[str, Any]:
    """표준 오류 JSON(PRD 5.4)을 만든다.

    envelope에는 비밀값이 들어갈 자리가 아예 없다.
    """
    return {
        "schema_version": 계약.SCHEMA_VERSION,
        "ok": False,
        "provider": "naver",
        "operation": operation,
        "kind": kind,
        "error": {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
            "http_status": error.http_status,
            "provider_code": error.provider_code,
        },
    }


def http_status_to_error(status_code: int, provider_code: str | None = None) -> CallerError:
    """네이버 HTTP 상태 코드를 표준 오류로 변환한다 (PRD 9.1).

    응답 본문은 비밀값이 섞일 수 있으므로 메시지에 넣지 않는다.
    """
    if status_code == 400:
        return CallerError(
            "E_API_BAD_REQUEST",
            "네이버가 잘못된 요청으로 응답했습니다. 파라미터를 확인하십시오.",
            http_status=status_code,
            provider_code=provider_code,
        )
    if status_code == 401:
        return CallerError(
            "E_API_AUTH",
            "인증 정보가 유효하지 않습니다. Client ID/Secret을 확인하십시오.",
            http_status=status_code,
            provider_code=provider_code,
        )
    if status_code == 403:
        return CallerError(
            "E_API_PERMISSION",
            "이 애플리케이션에 해당 API 권한이 없습니다. "
            "네이버 API Hub Application에 해당 API 사용 권한이 있는지 확인하십시오.",
            http_status=status_code,
            provider_code=provider_code,
        )
    if status_code == 404:
        return CallerError(
            "E_API_BAD_REQUEST",
            "요청 URL이 올바르지 않습니다.",
            http_status=status_code,
            provider_code=provider_code,
        )
    if status_code == 429:
        return CallerError(
            "E_API_RATE_LIMIT",
            "호출 한도 또는 속도 제한에 도달했습니다. 잠시 후 다시 시도하십시오.",
            http_status=status_code,
            provider_code=provider_code,
        )
    if 500 <= status_code < 600:
        return CallerError(
            "E_API_SERVER",
            "네이버 서버 내부 오류가 발생했습니다.",
            http_status=status_code,
            provider_code=provider_code,
        )
    return CallerError(
        "E_API_RESPONSE",
        f"예상하지 못한 HTTP 상태({status_code})를 받았습니다.",
        http_status=status_code,
        provider_code=provider_code,
    )
