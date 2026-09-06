"""Preserve pricing availability instead of treating missing prices as zero."""


def agent_cost_usage(agent):
    status = getattr(agent, "session_cost_status", None)
    amount = getattr(agent, "session_estimated_cost_usd", None)
    return {
        "estimated_cost": None if status == "unknown" else amount,
        "cost_status": status,
        "cost_source": getattr(agent, "session_cost_source", None),
    }
