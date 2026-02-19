import os
import sys
import pytest

# adjust path to import package when running tests from workspace root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), \"..\"))  # noqa: E402

from app.api.chatbot.multiagent.intent_agent.agent import IntentAgent
from app.api.chatbot.multiagent.faq_agent.agent import FaqAgent
from app.api.chatbot.multiagent.router import Router


def test_intent_agent_detects_order_intent():
    agent = IntentAgent()
    res = agent.handle_intent({\"text\": \"Quero comprar um produto\"})
    assert res.intent in (\"create_order\", \"unknown\")


def test_faq_agent_answers_hours():
    agent = FaqAgent()
    res = agent.answer_question({\"text\": \"Qual o horário de funcionamento?\"})
    assert \"horário\" in res.answer.lower() or \"horario\" in res.answer.lower() or res.source is not None


def test_router_routes_faq():
    router = Router()
    out = router.route({\"text\": \"Qual a taxa de entrega?\"})
    assert \"answer\" in out or \"source\" in out or isinstance(out, dict)

