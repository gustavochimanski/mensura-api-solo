"""Lightweight llm_policy shim with minimal behavior."""
def build_system_prompt(*args, **kwargs) -> str:
    return ""

def clamp_temperature(value: float) -> float:
    try:
        v = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, v))

__all__ = ["build_system_prompt", "clamp_temperature"]

