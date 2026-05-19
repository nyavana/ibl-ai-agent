#!/usr/bin/env python3
"""Print non-failing size diagnostics for repo-local skill guidance."""

from __future__ import annotations

from pathlib import Path


ROOTS = [Path("AGENTS.md"), Path("skills")]
INSTRUCTION_PATTERNS = ("SKILL.md", "README.md")


def iter_instruction_files() -> list[Path]:
    files: list[Path] = []
    if Path("AGENTS.md").exists():
        files.append(Path("AGENTS.md"))
    for path in Path("skills").rglob("*.md"):
        if "__pycache__" in path.parts:
            continue
        if (
            path.name in INSTRUCTION_PATTERNS
            or "/references/" in path.as_posix()
            or path.as_posix().startswith("skills/meta/")
        ):
            files.append(path)
    return sorted(files)


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def byte_count(path: Path) -> int:
    return path.stat().st_size


def main() -> None:
    files = iter_instruction_files()
    total_lines = sum(line_count(path) for path in files)
    total_bytes = sum(byte_count(path) for path in files)

    print("Skill guidance size report (non-failing)")
    print(f"Files: {len(files)}")
    print(f"Lines: {total_lines}")
    print(f"Bytes: {total_bytes}")
    print()
    print("Largest files:")
    for path in sorted(files, key=line_count, reverse=True)[:15]:
        print(f"{line_count(path):5d}  {path}")


if __name__ == "__main__":
    main()
