from typing import Any, Dict, List, Optional

class AgentBase:
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError()


class IntentResult:
    def __init__(self, intent: str, params: Optional[Dict[str, Any]] = None):
        self.intent = intent
        self.params = params or {}


class FAQResult:
    def __init__(self, answer: str, source: Optional[str] = None):
        self.answer = answer
        self.source = source

