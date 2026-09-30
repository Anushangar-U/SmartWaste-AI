"""Shared provider failover helpers for live AI components.

Failover is intentionally limited to credential, quota, timeout, connection,
permission, and provider-side failures. Application errors such as invalid
payloads or schema/JSON parsing problems are not hidden by switching keys.
"""
from __future__ import annotations

from typing import Any

from openai import OpenAI

from backend.config import settings


_FAILOVER_ERROR_NAMES = {
    "AuthenticationError",
    "PermissionDeniedError",
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
    "InternalServerError",
    "ServerError",
    "ServiceUnavailableError",
    "DeadlineExceeded",
}


def _status_code(exc: Exception) -> int | None:
    candidates = [
        getattr(exc, "status_code", None),
        getattr(exc, "code", None),
        getattr(getattr(exc, "response", None), "status_code", None),
    ]
    for value in candidates:
        if isinstance(value, int):
            return value
        try:
            if value is not None and str(value).isdigit():
                return int(value)
        except (TypeError, ValueError):
            pass
    return None


def should_failover_provider_error(exc: Exception) -> bool:
    """Return True only for failures where another credential/provider may help."""
    status = _status_code(exc)
    if status is not None:
        return status in {401, 403, 408, 429} or status >= 500
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    return type(exc).__name__ in _FAILOVER_ERROR_NAMES


def _unique_keys(*values: str | None) -> list[str]:
    keys = [(value or "").strip() for value in values]
    return list(dict.fromkeys(key for key in keys if key))


def openrouter_api_keys(agent_specific_key: str | None = None) -> list[str]:
    """Return OpenRouter credentials in failover order without duplicates."""
    return _unique_keys(
        agent_specific_key,
        settings.openrouter_api_key,
        settings.openrouter_fallback_api_key,
    )


def has_openrouter_credentials(agent_specific_key: str | None = None) -> bool:
    return bool(openrouter_api_keys(agent_specific_key))


def openrouter_chat_create(
    *,
    request: dict[str, Any],
    agent_specific_key: str | None = None,
):
    """Run one OpenRouter chat request, trying the next key only on provider failures."""
    keys = openrouter_api_keys(agent_specific_key)
    if not keys:
        raise RuntimeError(
            "No OpenRouter API key is configured. Add OPENROUTER_API_KEY "
            "or OPENROUTER_FALLBACK_API_KEY to the local .env file."
        )

    for index, api_key in enumerate(keys):
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
        )
        try:
            return client.chat.completions.create(**request)
        except Exception as exc:
            is_last = index == len(keys) - 1
            if is_last or not should_failover_provider_error(exc):
                raise

    raise RuntimeError("OpenRouter request failed without a provider response.")
