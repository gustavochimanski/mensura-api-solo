Multi-agent chatbot architecture
===============================

Como ativar
-----------

Defina a variável de ambiente `CHATBOT_USE_MULTIAGENT=1` para que o pacote
`app.api.chatbot` passe a usar o novo roteador multi-agent. Por padrão o
comportamento continua usando o código existente em `app/api/chatbot/legacy`.

Estrutura de pastas
-------------------

- `app/api/chatbot/legacy/` — código atual movido para referência e compatibilidade.  
- `app/api/chatbot/multiagent/` — nova implementação multi-agent:
  - `base.py` — contratos e tipos básicos dos agentes  
  - `intent_agent/` — agente de intenção (mapeia pedidos, ações)  
  - `faq_agent/` — agente de dúvidas/FAQ (horário, preço, taxa, etc)  
  - `router.py` — lógica de decisão entre agentes  
  - `adapters.py` — adaptadores que reutilizam configs e serviços legacy

Reaproveitamento de configurações
--------------------------------

As configurações existentes (ex.: `app/api/chatbot/legacy/core/config_whatsapp.py`)
são reutilizadas pelos adaptadores do multiagent — não duplique configurações.

Como desenvolver novos agentes
-----------------------------

1. Criar um novo pacote em `multiagent/<nome_agent>/` com `agent.py` implementando
   os métodos necessários e retornando tipos compatíveis com `base.py`.  
2. Registrar/injetar dependências no `router.py` ou no bootstrap do multiagent.  
3. Adicionar testes em `tests/test_multiagent.py` (ou criar arquivos novos) e rodar o test suite.

