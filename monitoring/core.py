"""Pure helpers shared by the bot, the agent and the tests."""

import hashlib
import hmac
from datetime import datetime, timezone

TLS_FORMAT = "%b %d %H:%M:%S %Y %Z"


def agent_token(secret: str) -> str:
    """Return the value the bot sends and the agent expects for a given secret."""
    return hmac.new(secret.encode(), b"metrics", hashlib.sha256).hexdigest()


def token_matches(secret: str, provided: str) -> bool:
    return hmac.compare_digest(agent_token(secret), provided)


def http_ok(status: int | None) -> bool:
    return status is not None and status < 500


def ssl_days_left(not_after: str, now: datetime | None = None) -> int:
    expire = datetime.strptime(not_after, TLS_FORMAT).replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return max((expire - current).days, 0)


def ssl_level(days: int | None, warn: int, critical: int) -> str:
    if days is None:
        return "unknown"
    if days <= critical:
        return "critical"
    if days <= warn:
        return "warn"
    return "ok"


def resource_level(percent_free: float, warn_free: int) -> str:
    return "ok" if percent_free > warn_free else "warn"
