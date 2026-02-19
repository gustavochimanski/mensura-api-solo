\"\"\"Shim de compatibilidade para o pacote `app.api.chatbot`.
Por padrão delega para o código `legacy`; quando a variável de ambiente
`CHATBOT_USE_MULTIAGENT` estiver ativa, usa o router multi-agent.
\"\"\"

import os

use_multi = os.getenv(\"CHATBOT_USE_MULTIAGENT\", \"false\").lower() in (\"1\", \"true\", \"yes\")

if use_multi:
    # Router multi-agent por padrão
    from .multiagent import Router as MultiRouter  # type: ignore

    router = MultiRouter()
    __all__ = [\"router\"]
else:
    # Compatibilidade: exporta o router legacy para não quebrar consumidores atuais
    from .legacy import router as legacy_router  # type: ignore

    router = legacy_router
    __all__ = [\"router\"]

\"\"\"Shim de compatibilidade para o pacote `app.api.chatbot`.\n+Por padrão delega para o código `legacy`; quando a variável de ambiente\n+`CHATBOT_USE_MULTIAGENT` estiver ativa, usa o router multi-agent.\n+\"\"\"\n+\n+import os\n+\n+use_multi = os.getenv(\"CHATBOT_USE_MULTIAGENT\", \"false\").lower() in (\"1\", \"true\", \"yes\")\n+\n+if use_multi:\n+    # Router multi-agent por padrão\n+    from .multiagent import Router as MultiRouter  # type: ignore\n+\n+    router = MultiRouter()\n+    __all__ = [\"router\"]\n+else:\n+    # Compatibilidade: exporta o router legacy para não quebrar consumidores atuais\n+    from .legacy import router as legacy_router  # type: ignore\n+\n+    router = legacy_router\n+    __all__ = [\"router\"]\n+\n*** End Patch
\"\"\"\n+Shim de compatibilidade para o pacote `app.api.chatbot`.\n+Por padrão delega para o código `legacy`; quando a variável de ambiente\n+`CHATBOT_USE_MULTIAGENT` estiver ativa, usa o router multi-agent.\n+\"\"\"\n+\n+import os\n+\n+use_multi = os.getenv(\"CHATBOT_USE_MULTIAGENT\", \"false\").lower() in (\"1\", \"true\", \"yes\")\n+\n+if use_multi:\n+    from .multiagent import Router as MultiRouter  # type: ignore\n+\n+    router = MultiRouter()\n+    __all__ = [\"router\"]\n+else:\n+    from .legacy import router as legacy_router  # type: ignore\n+\n+    router = legacy_router\n+    __all__ = [\"router\"]\n+\n*** End Patch
