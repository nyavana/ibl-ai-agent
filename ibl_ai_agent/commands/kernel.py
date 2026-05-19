from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from ibl_ai_agent.commands.common import fail

T = TypeVar("T")


def run_or_fail(action: Callable[[], T], *, error_type: type[Exception]) -> T:
    try:
        return action()
    except error_type as exc:
        fail(str(exc))
