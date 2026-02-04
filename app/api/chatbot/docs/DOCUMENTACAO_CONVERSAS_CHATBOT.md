## Conversas do Chatbot (API)

Este documento descreve os endpoints de **conversas** do módulo `chatbot`, incluindo o filtro por data para listar conversas de um cliente (usuário).

### Listar conversas de um cliente (com filtro por data)

`GET /conversations/user/{user_id}`

#### Parâmetros de rota

- **user_id**: identificador do usuário no chatbot (normalmente o telefone). O backend aceita variações com/sem `55` e, para celular BR, com/sem o `9`.

#### Query params

- **empresa_id** (opcional, int): filtra por empresa.
- **data_inicio** (opcional, `YYYY-MM-DD`): filtra por `updated_at` (última atividade) a partir desta data (inclusivo).
- **data_fim** (opcional, `YYYY-MM-DD`): filtra por `updated_at` (última atividade) até esta data (inclusivo).

> Observação: o filtro por data é aplicado sobre `updated_at` na tabela `chatbot.conversations`, que é atualizado quando novas mensagens são inseridas.

#### Exemplo

- **Listar conversas do cliente em Janeiro/2026**:

`GET /conversations/user/5511999999999?empresa_id=1&data_inicio=2026-01-01&data_fim=2026-01-31`

#### Resposta (200)

```json
{
  "conversations": [
    {
      "id": 123,
      "session_id": "whatsapp_5511999999999_20260101123000",
      "user_id": "5511999999999",
      "contact_name": "Fulano",
      "prompt_key": "default",
      "model": "llama-3.1-8b-instant",
      "empresa_id": 1,
      "profile_picture_url": null,
      "created_at": "2026-01-01T12:30:00",
      "updated_at": "2026-01-01T12:45:10"
    }
  ]
}
```

### Buscar uma conversa com mensagens

`GET /conversations/{conversation_id}`

Retorna os dados da conversa e a lista completa de mensagens.

### Listar conversas de uma sessão

`GET /conversations/session/{session_id}`

Query param:

- **empresa_id** (opcional, int)

