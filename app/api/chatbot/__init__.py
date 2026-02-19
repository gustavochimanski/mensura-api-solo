"""Compatibility shim for the app.api.chatbot package.
This project no longer includes the legacy implementation — always
use the multiagent router as the default.
"""

from .multiagent import Router as MultiRouter  # type: ignore

router = MultiRouter()

__all__ = ["router"]
