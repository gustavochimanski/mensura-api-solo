"""Compatibility shim for the app.api.chatbot package.
Delegates to the legacy implementation by default. Set the
environment variable CHATBOT_USE_MULTIAGENT to enable the multi-agent router.
"""

import os

use_multi = os.getenv("CHATBOT_USE_MULTIAGENT", "false").lower() in ("1", "true", "yes")

if use_multi:
    # Use the new multi-agent router
    from .multiagent import Router as MultiRouter  # type: ignore

    router = MultiRouter()
    __all__ = ["router"]
else:
    # Keep compatibility with the legacy codebase
    from .legacy import router as legacy_router  # type: ignore

    router = legacy_router
    __all__ = ["router"]
