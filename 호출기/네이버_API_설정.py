# 네이버_API_설정.py
"""로컬 .env 또는 환경변수에서 네이버 인증 정보를 읽는 모듈.

의존성: 표준 라이브러리만 사용. 계약 모듈에도 의존하지 않는다.

보안 원칙 (PRD 8장):
- 실제 Client Secret 값을 로그·예외 메시지·repr에 넣지 않는다.
- 명령행 인자로 비밀값을 받지 않는다(이 모듈은 그런 통로를 만들지 않는다).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_CLIENT_ID = "NAVER_CLIENT_ID"
ENV_CLIENT_SECRET = "NAVER_CLIENT_SECRET"


class ConfigError(Exception):
    """설정을 읽을 수 없을 때 발생. 메시지에 비밀값을 넣지 않는다."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class NaverCredentials:
    """네이버 인증 정보. 값이 로그에 새지 않도록 repr을 마스킹한다."""

    client_id: str
    client_secret: str

    def __repr__(self) -> str:  # noqa: D401 - 비밀값 마스킹 목적
        return "NaverCredentials(client_id=<masked>, client_secret=<masked>)"

    def __str__(self) -> str:
        return self.__repr__()


def _parse_env_file(text: str) -> dict[str, str]:
    """단순 KEY=VALUE .env 파서.

    - 빈 줄과 '#'로 시작하는 주석 줄은 건너뛴다.
    - 값 양쪽의 큰따옴표/작은따옴표 한 쌍은 제거한다.
    - export 접두사를 허용한다.
    """
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            result[key] = value
    return result


def _load_env_values(env_file: Path | None) -> dict[str, str]:
    """환경변수와 .env 파일을 합친 값을 반환한다.

    우선순위: 프로세스 환경변수가 .env 파일 값보다 우선한다.
    env_file이 None이면 OS 환경변수만 사용한다.
    """
    values: dict[str, str] = {}
    if env_file is not None:
        if not env_file.exists():
            raise ConfigError(
                "E_CONFIG_MISSING",
                f".env 파일을 찾을 수 없습니다: {env_file}",
            )
        try:
            text = env_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigError(
                "E_CONFIG_INVALID",
                f".env 파일을 읽을 수 없습니다: {env_file} ({exc.__class__.__name__})",
            ) from exc
        values.update(_parse_env_file(text))
    # 프로세스 환경변수를 나중에 덮어써서 우선순위를 높인다.
    for key in (ENV_CLIENT_ID, ENV_CLIENT_SECRET):
        env_val = os.environ.get(key)
        if env_val is not None:
            values[key] = env_val
    return values


def load_credentials(env_file: Path | None = None) -> NaverCredentials:
    """환경변수 또는 지정된 로컬 .env에서 네이버 인증 정보를 읽는다.

    Raises:
        ConfigError: 필수 값이 없거나 비어 있을 때. 메시지에 값을 넣지 않는다.
    """
    values = _load_env_values(env_file)

    client_id = (values.get(ENV_CLIENT_ID) or "").strip()
    client_secret = (values.get(ENV_CLIENT_SECRET) or "").strip()

    missing: list[str] = []
    if not client_id:
        missing.append(ENV_CLIENT_ID)
    if not client_secret:
        missing.append(ENV_CLIENT_SECRET)
    if missing:
        raise ConfigError(
            "E_CONFIG_MISSING",
            "다음 인증 정보가 없습니다: "
            + ", ".join(missing)
            + ". 로컬 .env 또는 환경변수에 값을 설정하십시오.",
        )

    return NaverCredentials(client_id=client_id, client_secret=client_secret)
