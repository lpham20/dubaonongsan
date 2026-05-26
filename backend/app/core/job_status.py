from __future__ import annotations


STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_EMPTY = "empty"
STATUS_DUPLICATE = "duplicate"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

STATUS_TEXT_SUCCESS_VI = "th\u00e0nh c\u00f4ng"
STATUS_TEXT_DUPLICATE_VI = "tr\u00f9ng l\u1eb7p"
STATUS_TEXT_RUNNING_VI = "\u0111ang ch\u1ea1y"
STATUS_TEXT_FAILED_VI = "th\u1ea5t b\u1ea1i"


def _mojibake(value: str) -> str:
    return value.encode("utf-8").decode("latin-1")


SUCCESS_STATUSES = frozenset(
    {
        STATUS_SUCCESS,
        STATUS_DUPLICATE,
        "completed",
        "thanh cong",
        "trung lap",
        STATUS_TEXT_SUCCESS_VI,
        STATUS_TEXT_DUPLICATE_VI,
        _mojibake(STATUS_TEXT_SUCCESS_VI),
        _mojibake(STATUS_TEXT_DUPLICATE_VI),
    }
)

FAILED_STATUSES = frozenset(
    {
        STATUS_FAILED,
        "error",
        "loi",
        STATUS_TEXT_FAILED_VI,
        _mojibake(STATUS_TEXT_FAILED_VI),
    }
)

TERMINAL_STATUSES = SUCCESS_STATUSES | FAILED_STATUSES | {STATUS_EMPTY, STATUS_SKIPPED}


def is_success_status(value: str | None) -> bool:
    return _normalize_status(value) in SUCCESS_STATUSES


def is_terminal_status(value: str | None) -> bool:
    return _normalize_status(value) in TERMINAL_STATUSES


def _normalize_status(value: str | None) -> str:
    return (value or "").strip().lower()
