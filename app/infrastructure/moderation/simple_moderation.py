import re

from app.domain.models.policy import ModerationResult, PolicyConfig
from app.domain.ports.moderation import ModerationPort


class SimpleModeration(ModerationPort):
    def __init__(self, default_banned: list[str] | None = None):
        self._banned = default_banned or []

    def check(self, text: str, policy: PolicyConfig) -> ModerationResult:
        max_chars = policy.get("max_input_chars", 2000)
        if not text or not text.strip():
            return {"allowed": False, "reason": "empty_input"}

        if len(text) > max_chars:
            return {"allowed": False, "reason": f"too_long>{max_chars}"}

        patterns = list(self._banned) + policy.get("banned_regexes", [])
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                return {"allowed": False, "reason": f"banned_pattern:{pat}"}

        return {"allowed": True, "reason": "ok"}
