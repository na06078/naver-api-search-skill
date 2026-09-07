"""NAVER API 검색 스킬 설치 도우미.

기본 동작은 검사만 한다.
실제 파일을 Hermes 활성 스킬 폴더에 복사하려면 명시적으로 --install을 사용한다.

보안 원칙:
- 저장소의 .env를 읽어 화면에 출력하지 않는다.
- .env를 활성 스킬 폴더로 복사하지 않는다.
- 기존 설치가 있으면 --force 없이는 덮어쓰지 않는다.
- 임의 파일을 삭제하지 않는다.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_NAME = "naver-search-api"
SOURCE_SKILL = Path("스킬 원본") / "SKILL.md"
SOURCE_CALLER = Path("호출기")
CALLER_ENTRY = "네이버_API_호출기.py"
ENV_EXAMPLE = Path(".env.example")

PLACEHOLDERS = {
    "{{PROJECT_ROOT}}",
    "{{SKILL_ROOT}}",
    "{{CALLER_PATH}}",
    "{{ENV_PATH}}",
}


def project_root() -> Path:
    return Path(__file__).resolve().parent


def hermes_skills_candidates() -> list[Path]:
    """현재 환경에서 가능성이 높은 Hermes skills 경로를 반환한다."""
    candidates: list[Path] = []

    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        candidates.append(Path(hermes_home).expanduser() / "skills")

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "hermes" / "skills")

    candidates.append(Path.home() / ".hermes" / "skills")

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(os.path.abspath(candidate))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def resolve_target(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()

    candidates = hermes_skills_candidates()
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def source_files(root: Path) -> list[Path]:
    caller_root = root / SOURCE_CALLER
    if not caller_root.is_dir():
        raise FileNotFoundError(f"호출기 폴더가 없습니다: {caller_root}")
    files = sorted(
        path for path in caller_root.glob("*.py") if path.is_file()
    )
    if not files:
        raise FileNotFoundError(f"호출기 Python 파일이 없습니다: {caller_root}")
    return files


def read_template(root: Path) -> str:
    template_path = root / SOURCE_SKILL
    if not template_path.is_file():
        raise FileNotFoundError(f"스킬 원본이 없습니다: {template_path}")
    text = template_path.read_text(encoding="utf-8")
    missing = [placeholder for placeholder in PLACEHOLDERS if placeholder not in text]
    if missing:
        raise ValueError(
            "스킬 원본에 설치 경로 placeholder가 없습니다: " + ", ".join(missing)
        )
    return text


def render_skill(template: str, root: Path, target_skill: Path) -> str:
    caller_path = target_skill / "호출기" / CALLER_ENTRY
    env_path = root / ".env"
    replacements = {
        "{{PROJECT_ROOT}}": str(root),
        "{{SKILL_ROOT}}": str(target_skill),
        "{{CALLER_PATH}}": str(caller_path),
        "{{ENV_PATH}}": str(env_path),
    }
    rendered = template
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    if any(marker in rendered for marker in PLACEHOLDERS):
        raise ValueError("스킬 경로 placeholder가 모두 치환되지 않았습니다.")
    return rendered


def check(root: Path, target: Path) -> int:
    try:
        files = source_files(root)
        template = read_template(root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"검사 실패: {exc}", file=sys.stderr)
        return 2

    env_path = root / ".env"
    target_skill = target / SKILL_NAME
    print(f"프로젝트 루트: {root}")
    print(f"대상 Hermes skills: {target}")
    print(f"대상 스킬 폴더: {target_skill}")
    print(f"호출기 파일 수: {len(files)}")
    print(f"스킬 템플릿: {len(template)} chars")
    print(f"로컬 .env 존재: {'예' if env_path.is_file() else '아니오 (키 입력 전 상태)'}")
    print(f"기존 설치 존재: {'예' if target_skill.exists() else '아니오'}")
    print("검사 완료: 실제 설치는 수행하지 않았습니다.")
    return 0


def install(root: Path, target: Path, force: bool) -> int:
    try:
        files = source_files(root)
        template = read_template(root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"설치 실패: {exc}", file=sys.stderr)
        return 2

    target_skill = target / SKILL_NAME
    if target_skill.exists() and not force:
        print(
            f"대상 스킬이 이미 있습니다: {target_skill}\n"
            "기존 파일을 덮어쓰려면 --force를 명시하십시오.",
            file=sys.stderr,
        )
        return 2

    target.mkdir(parents=True, exist_ok=True)
    target_skill.mkdir(parents=True, exist_ok=True)
    target_caller = target_skill / "호출기"
    target_caller.mkdir(parents=True, exist_ok=True)

    rendered = render_skill(template, root, target_skill)
    (target_skill / "SKILL.md").write_text(rendered, encoding="utf-8")

    for source in files:
        shutil.copy2(source, target_caller / source.name)

    # .env는 절대로 복사하지 않는다. 사용자가 프로젝트 루트에 직접 만든다.
    help_script = target_caller / CALLER_ENTRY
    result = subprocess.run(
        [sys.executable, str(help_script), "help"],
        cwd=target_skill,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if result.returncode != 0:
        print("설치는 파일을 복사했지만 호출기 help 검증에 실패했습니다.", file=sys.stderr)
        if result.stderr:
            print(result.stderr[:1000], file=sys.stderr)
        return 3

    print(f"설치 완료: {target_skill}")
    print(".env는 복사하지 않았습니다. 프로젝트 루트의 .env를 사용합니다.")
    print("Hermes 새 세션에서 스킬 로더가 갱신됩니다.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NAVER API 검색 스킬을 Hermes 활성 skills 폴더에 설치합니다."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="설치 경로와 파일만 검사합니다(기본 동작).",
    )
    mode.add_argument(
        "--install",
        action="store_true",
        help="스킬과 호출기를 실제로 복사합니다.",
    )
    parser.add_argument(
        "--target",
        help="Hermes skills 경로를 직접 지정합니다.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 naver-search-api 파일을 덮어씁니다. .env는 건드리지 않습니다.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = project_root()
    target = resolve_target(args.target)
    if args.install:
        return install(root, target, args.force)
    return check(root, target)


if __name__ == "__main__":
    raise SystemExit(main())
