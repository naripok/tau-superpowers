"""Pricing of one child assistant message through Tau's catalog estimator."""

from __future__ import annotations

from tau_agent.messages import AssistantMessage


def estimated_message_cost(message: AssistantMessage) -> float | None:
    """Return the catalog estimate in USD for one accepted child message.

    Tau's usage estimator is imported lazily inside the call so the extension
    loads without it. A missing seam, an estimator failure, or a model without
    catalog rates all degrade to ``None``; the caller decides what an unpriced
    message means.
    """
    try:
        from tau_coding.session_usage import estimated_request_cost

        return estimated_request_cost(
            message.provider,
            message.model,
            fresh=message.usage.input,
            cached=message.usage.cache_read,
            cache_write=message.usage.cache_write,
            cache_write_1h=message.usage.cache_write_1h or 0,
            output=message.usage.output,
        )
    except Exception:
        return None
