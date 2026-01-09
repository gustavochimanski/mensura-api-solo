# Documentação (Frontend) — Notifications API + WhatsApp Config + Dispatch

Este documento descreve **como o frontend deve consumir** os endpoints HTTP de notificações e **como configurar o canal WhatsApp**.  
Para WebSocket, consulte também: `DOCUMENTACAO_FRONTEND_WEBSOCKET.md`.

---

## Base URL

- **Prefixo do módulo**: `/api/notifications`
- Exemplos:
  - Local: `http://localhost:8000/api/notifications`
  - Prod: `https://seu-host/api/notifications`

---

## Autenticação (HTTP)

Todos os endpoints abaixo exigem JWT via header:

```
Authorization: Bearer <access_token>
```

---

## 1) WhatsApp Config (CRUD + ativação)

Router: `/api/notifications/whatsapp-configs`

### 1.1) Listar configs

- **GET** `/api/notifications/whatsapp-configs?empresa_id={empresa_id}&include_inactive=true`

### 1.2) Obter config ativa

- **GET** `/api/notifications/whatsapp-configs/active?empresa_id={empresa_id}`

### 1.3) Obter config por id

- **GET** `/api/notifications/whatsapp-configs/{config_id}`

### 1.4) Criar config

- **POST** `/api/notifications/whatsapp-configs`

Payload (exemplo mínimo — 360dialog):

```json
{
  "empresa_id": "1",
  "name": "WhatsApp 360",
  "provider": "360dialog",
  "base_url": "https://waba-v2.360dialog.io",
  "access_token": "D360_API_KEY_AQUI",
  "is_active": true
}
```

Payload (exemplo — Meta Cloud API):

```json
{
  "empresa_id": "1",
  "name": "WhatsApp Meta",
  "provider": "meta",
  "access_token": "META_TOKEN_AQUI",
  "phone_number_id": "SEU_PHONE_NUMBER_ID",
  "api_version": "v22.0",
  "is_active": true
}
```

### 1.4.1) Campos de webhook (opcional)

Esses campos **não** são para enviar mensagens; são para **receber eventos** via webhook.

- **`webhook_verify_token`**: token **compartilhado** usado na verificação inicial do webhook (o provedor chama seu endpoint com `hub.verify_token` e o backend compara com este valor).
- **`webhook_header_key` / `webhook_header_value`**: validação extra **via header** no POST do webhook (ex.: um header fixo enviado pelo provedor).  
  Observação: no backend atual essa validação é por **comparação exata** de string; não é validação de assinatura/HMAC dinâmica.

Exemplo de payload com webhook:

```json
{
  "empresa_id": "1",
  "name": "WhatsApp 360",
  "provider": "360dialog",
  "base_url": "https://waba-v2.360dialog.io",
  "access_token": "D360_API_KEY_AQUI",
  "webhook_url": "https://seu-host/public/webhook",
  "webhook_verify_token": "MEU_VERIFY_TOKEN",
  "webhook_header_key": "X-Webhook-Token",
  "webhook_header_value": "MEU_HEADER_TOKEN",
  "is_active": true
}
```

### 1.5) Atualizar config

- **PUT** `/api/notifications/whatsapp-configs/{config_id}`

### 1.6) Ativar config

- **POST** `/api/notifications/whatsapp-configs/{config_id}/activate`

### 1.7) Deletar config

- **DELETE** `/api/notifications/whatsapp-configs/{config_id}`

---

## 2) Disparo de mensagens (dispatch)

Router: `/api/notifications/messages`

### 2.1) Disparo direto (para telefones/emails/user_ids)

- **POST** `/api/notifications/messages/dispatch`

Payload (exemplo — enviar WhatsApp para lista de telefones):

```json
{
  "empresa_id": "1",
  "message_type": "transactional",
  "title": "Aviso",
  "message": "Olá! Sua compra foi confirmada.",
  "recipient_phones": ["5511999999999"],
  "channels": ["whatsapp"],
  "channel_metadata": {
    "whatsapp": {
      "preview_url": false
    }
  }
}
```

Observações:

- `recipient_phones`: números já no formato E.164 “somente dígitos” (o backend também tenta normalizar).
- `channels`: lista de canais (ex.: `"whatsapp"`, `"email"`, `"webhook"`, `"in_app"`).
- `message_type`: enum do backend (ex.: `"marketing"`, `"utility"`, `"transactional"`).

### 2.2) Disparo em massa (bulk)

- **POST** `/api/notifications/messages/bulk-dispatch`

Payload (exemplo):

```json
{
  "empresa_id": "1",
  "message_type": "marketing",
  "title": "Promoção",
  "message": "Hoje tem desconto!",
  "filter_by_empresa": true,
  "channels": ["in_app", "whatsapp"],
  "max_recipients": 200
}
```

### 2.3) Stats de dispatch

- **GET** `/api/notifications/messages/stats?empresa_id={empresa_id}&message_type={opcional}&start_date={iso}&end_date={iso}`

---

## 3) Histórico e dashboard (admin)

Router: `/api/notifications/historico`

### 3.1) Histórico da empresa (paginado)

- **GET** `/api/notifications/historico/empresa/{empresa_id}?data_inicio={iso}&data_fim={iso}&tipos_evento=a&tipos_evento=b&limit=100&offset=0`

### 3.2) Histórico de um pedido

- **GET** `/api/notifications/historico/pedido/{pedido_id}?empresa_id={empresa_id}`

### 3.3) Histórico de um usuário

- **GET** `/api/notifications/historico/usuario/{user_id}?empresa_id={empresa_id}&data_inicio={iso}&data_fim={iso}`

### 3.4) Estatísticas da empresa

- **GET** `/api/notifications/historico/estatisticas/{empresa_id}?data_inicio={iso}&data_fim={iso}`

### 3.5) Dashboard da empresa

- **GET** `/api/notifications/historico/dashboard/{empresa_id}?periodo_dias=30`

---

## 4) WebSocket (tempo real)

O WebSocket é a forma recomendada do front “ouvir eventos” e então **refazer fetch** via HTTP.

Consulte: `DOCUMENTACAO_FRONTEND_WEBSOCKET.md` (no mesmo diretório).

---

## 5) Observações sobre WhatsApp “Catálogo/Produtos”

O backend atualmente envia **texto** e **mídia**; não há endpoint pronto para enviar `interactive/catalog_message` (catálogo/produtos) conforme o docs da 360dialog.  
Se o front precisar dessa feature, o payload esperado está aqui:

- [360dialog — Products & Catalogs](https://docs.360dialog.com/docs/waba-messaging/products-and-catalogs)

