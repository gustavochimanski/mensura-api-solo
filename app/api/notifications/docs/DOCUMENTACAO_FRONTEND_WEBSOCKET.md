# Documentação WebSocket (Frontend) — Notificações em Tempo Real

Esta documentação descreve **como o frontend deve se conectar e reagir** ao WebSocket de notificações do backend.

---

## 1) URL do WebSocket (conexão)

### Endpoint (principal)

- **WS**: `/api/notifications/ws/notifications?empresa_id={empresa_id}`
- **Exemplo local**: `ws://localhost:8000/api/notifications/ws/notifications?empresa_id=1`
- **Exemplo produção**: `wss://seu-host/api/notifications/ws/notifications?empresa_id=1`

### Observações importantes

- **Não existe mais `user_id` na URL**.
- **Identidade é sempre derivada do JWT**.
- `empresa_id` é usado para “selecionar o escopo” e é **validado no backend**:
  - Se o usuário tiver **1 empresa**, `empresa_id` pode ser omitido.
  - Se o usuário for **multi-empresa**, `empresa_id` é **obrigatório**.

### Endpoint legado (compatibilidade)

Não existe endpoint legado com `user_id` na URL.

---

## 2) Autenticação do WebSocket (obrigatória)

### Contexto (browser)

No WebSocket nativo do browser (`new WebSocket(url)`), **não dá para setar header `Authorization`**.

Por isso, o backend aceita o token de duas formas:

#### Opção A (recomendada no browser): `Sec-WebSocket-Protocol`

Envie o JWT via `protocols`:

```ts
const ws = new WebSocket(wsUrl, ["mensura-bearer", accessToken]);
```

O backend lê isso do header `Sec-WebSocket-Protocol`.

#### Opção B (Node/ambientes que permitem header): `Authorization: Bearer`

Se estiver em Node (ou lib que permite headers), envie:

```
Authorization: Bearer <token>
```

---

## 3) Mensagens: o que o frontend RECEBE

O backend pode enviar **dois formatos**:

1. **Formato legado** `type="notification"` (mantido por compatibilidade)
2. **Formato novo** `type="event"` (contrato padronizado)

### 3.1) Mensagem de conexão

Ao conectar com sucesso, o servidor envia:

```json
{
  "type": "connection",
  "message": "Conectado com sucesso",
  "user_id": "123",
  "empresa_id": "1",
  "timestamp": "2026-01-04T12:00:00.000000"
}
```

### 3.2) Formato novo (contrato padronizado): `type="event"`

Envelope:

```json
{
  "type": "event",
  "event": "pedido.v1.impresso",
  "scope": "empresa",
  "payload": {
    "pedido_id": "123"
  },
  "timestamp": "2026-01-04T12:00:00.000000"
}
```

Campos:

- `type`: sempre `"event"`
- `event`: string do evento (veja lista abaixo)
- `scope`: `"empresa"` ou `"usuario"`
- `payload`: objeto com dados mínimos (normalmente **id** para o frontend refetch)
- `timestamp`: ISO string UTC

### 3.3) Formato legado (compat): `type="notification"`

Exemplo:

```json
{
  "type": "notification",
  "notification_type": "kanban",
  "title": "Novo Pedido Recebido",
  "message": "Pedido #123 impresso - Valor: R$ 10.00",
  "data": {
    "pedido_id": "123"
  },
  "empresa_id": "1",
  "timestamp": "2026-01-04T12:00:00.000000"
}
```

Campos:

- `type`: `"notification"`
- `notification_type`: string (ex: `"kanban"`, `"pedido_aprovado"`, etc.)
- `title`, `message`
- `data`: objeto (pode variar)
- `empresa_id`
- `timestamp`

### 3.4) Pong (resposta ao ping)

```json
{
  "type": "pong",
  "timestamp": "2026-01-04T12:00:00.000000"
}
```

### 3.5) Confirmação de rota

```json
{
  "type": "route_updated",
  "message": "Rota atualizada para: /pedidos",
  "route": "/pedidos",
  "timestamp": "2026-01-04T12:00:00.000000"
}
```

### 3.6) Erro

```json
{
  "type": "error",
  "message": "Formato de mensagem inválido",
  "timestamp": "2026-01-04T12:00:00.000000"
}
```

---

## 4) Mensagens: o que o frontend ENVIA

### 4.1) Ping (manter conexão ativa)

```json
{ "type": "ping" }
```

Servidor responde com `pong`.

### 4.2) set_route (roteamento no frontend)

Use para informar onde o usuário está (para filtragem por rota, ex: `/pedidos`):

```json
{
  "type": "set_route",
  "route": "/pedidos"
}
```

### 4.3) get_stats (debug)

```json
{ "type": "get_stats" }
```

### 4.4) subscribe (reservado / compat)

Atualmente o backend não aplica filtros reais por `event_types`, mas pode ser usado futuramente:

```json
{
  "type": "subscribe",
  "event_types": ["pedido.v1.impresso"]
}
```

---

## 5) Lista de eventos (WSEvents)

Os eventos padronizados (envelope `type="event"`) seguem:

- `pedido.v1.criado`
- `pedido.v1.atualizado`
- `pedido.v1.aprovado`
- `pedido.v1.cancelado`
- `pedido.v1.entregue`
- `pedido.v1.impresso`
- `meios_pagamento.v1.atualizados`
- `auth.v1.token_expirado` (**somente Admin**)

**Recomendação:** o frontend deve tratar `event` como “sinal” e **refazer fetch** dos dados necessários (cache/revalidate fica no HTTP).

---

## 6) Endpoints HTTP auxiliares (REST)

### 6.1) Obter URL de WS para uma empresa

- **GET** `/api/notifications/ws/config/{empresa_id}`

Resposta (exemplo):

```json
{
  "empresa_id": 1,
  "empresa_nome": "Minha Empresa",
  "websocket_url": "wss://seu-host/api/notifications/ws/notifications?empresa_id=1",
  "protocol": "wss",
  "endpoint": "/api/notifications/ws/notifications?empresa_id=1",
  "note": "Envie Authorization Bearer via Sec-WebSocket-Protocol (browser)."
}
```

### 6.2) Estatísticas de conexões

- **GET (admin)** `/api/notifications/ws/connections/stats`
- Requer `Authorization: Bearer <token>` (HTTP normal)

### 6.3) Verificar conexões de uma empresa

- **GET (admin)** `/api/notifications/ws/connections/check/{empresa_id}`
- Requer `Authorization: Bearer <token>` (HTTP normal)

### 6.4) Enviar notificação para um usuário (admin/debug)

Não implementado no backend atual.

### 6.5) Broadcast para empresa (admin/debug)

Não implementado no backend atual.

---

## 7) Implementação recomendada (TypeScript)

### 7.1) Conectar

```ts
type WSEventMessage =
  | { type: "connection"; message: string; user_id: string; empresa_id: string; timestamp: string }
  | { type: "event"; event: string; scope: "empresa" | "usuario"; payload: Record<string, unknown>; timestamp: string }
  | { type: "notification"; notification_type: string; title: string; message: string; data?: any; empresa_id?: string; timestamp: string }
  | { type: "pong"; timestamp: string }
  | { type: "route_updated"; message: string; route: string; timestamp: string }
  | { type: "stats"; data: any; timestamp: string }
  | { type: "error"; message: string; timestamp: string };

export function connectMensuraWS(params: {
  wsUrl: string;
  accessToken: string;
  onMessage: (msg: WSEventMessage) => void;
  onOpen?: () => void;
  onClose?: (ev: CloseEvent) => void;
  onError?: (ev: Event) => void;
}) {
  const { wsUrl, accessToken, onMessage, onOpen, onClose, onError } = params;

  // Browser: envia token via Sec-WebSocket-Protocol
  const ws = new WebSocket(wsUrl, ["mensura-bearer", accessToken]);

  ws.onopen = () => {
    onOpen?.();
  };

  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data));
    } catch {
      // ignore
    }
  };

  ws.onclose = (ev) => onClose?.(ev);
  ws.onerror = (ev) => onError?.(ev);

  return ws;
}
```

### 7.2) Heartbeat (ping)

```ts
export function startPing(ws: WebSocket, intervalMs = 30000) {
  const id = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "ping" }));
    }
  }, intervalMs);
  return () => clearInterval(id);
}
```

### 7.3) Atualizar rota

```ts
export function setRoute(ws: WebSocket, route: string) {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "set_route", route }));
  }
}
```

### 7.4) Como reagir a eventos (refetch)

Exemplo de estratégia:

- Ao receber `event: "pedido.v1.impresso"` com `scope: "empresa"`, o frontend deve:
  - invalidar cache local (ou `revalidateTag` no Next via chamada HTTP) e
  - refazer `GET` dos pedidos/kanban.

---

## 8) Códigos de fechamento (auth)

Quando a autenticação falha, o backend fecha com:

- `code = 1008` (**policy violation**)
- `reason` com texto curto (ex: “Authorization Bearer ausente ou malformado”)

### 8.1) Token expirado durante a sessão (somente Admin)

Quando o **JWT expira durante uma sessão WebSocket**, o backend deve:

1. **Enviar um último evento padronizado** (`type="event"`)
2. **Fechar a conexão** com `code=1008`

#### Evento: `auth.v1.token_expirado`

- **type**: `"event"`
- **event**: `auth.v1.token_expirado`
- **scope**: `"usuario"`
- **payload.code**: `"TOKEN_EXPIRED"`
- **payload.action**: `"logout"`

Exemplo:

```json
{
  "type": "event",
  "event": "auth.v1.token_expirado",
  "scope": "usuario",
  "payload": {
    "code": "TOKEN_EXPIRED",
    "message": "Sessão expirada. Faça login novamente.",
    "action": "logout"
  },
  "timestamp": "2026-01-04T12:00:00.000000"
}
```

#### O que o frontend Admin deve fazer

- Remover `access_token` do storage
- Encerrar o WS (se necessário)
- Redirecionar para `/login`

#### Fallback

Se o socket fechar com `code=1008` e `reason` contendo “Token inválido ou expirado”, trate como o mesmo fluxo (logout).

---

## 9) Checklist rápido (frontend)

- [ ] Construir `wsUrl` com `empresa_id`
- [ ] Conectar com `new WebSocket(wsUrl, ["mensura-bearer", accessToken])`
- [ ] Enviar `set_route` ao abrir e a cada mudança de rota
- [ ] Rodar `ping` a cada 30s
- [ ] Ao receber `type="event"`, fazer refetch no HTTP (payload mínimo)


