from typing import TypedDict


class ModerationResult(TypedDict):
    allowed: bool
    reason: str


class PolicyConfig(TypedDict, total=False):
    max_input_chars: int
    banned_regexes: list[str]
