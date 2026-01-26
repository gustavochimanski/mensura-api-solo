# Documentação WebSocket — Gestor App (`/gestor-app`) — Notificações de Pedidos Novos

Esta documentação descreve **como o Gestor App deve receber aviso de pedidos novos** via WebSocket, usando o mesmo endpoint e contrato já existentes (o mesmo usado pela tela `/pedidos`).

---

## 1) Importante: não existe um “WS separado” por rota

No backend, o WebSocket é **um único endpoint**:

- **WS**: `/api/notifications/ws/notifications?empresa_id={empresa_id}`

A “rota” (`/gestor-app`, `/pedidos`, etc.) é usada apenas para **filtragem no servidor**, e é informada pelo frontend após conectar, via mensagem `set_route`.

---

## 2) Conexão e autenticação

Siga exatamente a doc geral:

- `app/api/notifications/docs/DOCUMENTACAO_FRONTEND_WEBSOCKET.md`

Resumo rápido:

- **URL**: `ws://localhost:8000/api/notifications/ws/notifications?empresa_id=1`
- **Produção**: `wss://seu-host/api/notifications/ws/notifications?empresa_id=1`
- **Browser**: enviar token via `Sec-WebSocket-Protocol`:

```ts
const ws = new WebSocket(wsUrl, ["mensura-bearer", accessToken]);
```

---

## 3) Passo obrigatório: informar a rota do Gestor App (`set_route`)

Assim que abrir o socket (e sempre que a rota mudar), o Gestor App deve enviar:

```json
{
  "type": "set_route",
  "route": "/gestor-app"
}
```

### Regras de match (como o backend filtra)

O backend compara a rota do cliente (lowercase) por:

- `current_route == required_route`, **ou**
- `current_route.endswith(required_route)`

Ou seja: funciona tanto com `"/gestor-app"` quanto com algo como `"/app/gestor-app"` (desde que **termine** com `"/gestor-app"`).

---

## 4) Qual evento indica “pedido novo” no Gestor App (checkout)

### 4.1) Evento recomendado (contrato novo): `type="event"`

Para o Gestor App, “**pedido novo chegou**” deve disparar **assim que o pedido é criado no checkout**:

- **Evento**: `pedido.v1.criado`
- **Scope**: `empresa`
- **Filtragem por rota**: para o Gestor App receber, o backend deve emitir com `required_route="/gestor-app"`.

**Exemplo (envelope padrão):**

```json
{
  "type": "event",
  "event": "pedido.v1.criado",
  "scope": "empresa",
  "payload": {
    "pedido_id": "123",
    "tipo_entrega": "DELIVERY",
    "numero_pedido": "000123",
    "status": "P"
  },
  "timestamp": "2026-01-24T12:00:00.000000"
}
```

**Observação importante:** o `payload` é propositalmente “mínimo”. O frontend deve tratar o evento como **sinal** e fazer **refetch** via HTTP (próximca seção).

### 4.2) Formato legado (compat): `type="notification"` (opcional)

Além do evento padronizado, o backend **pode** enviar uma mensagem compatível (se vocês quiserem manter o padrão de “toast” legado):

```json
{
  "type": "notification",
  "notification_type": "pedido_criado",
  "title": "Novo Pedido",
  "message": "Pedido #000123 recebido",
  "data": {
    "pedido_id": "123",
    "tipo_entrega": "DELIVERY",
    "numero_pedido": "000123",
    "status": "P",
    "timestamp": "2026-01-24T12:00:00.000000"
  },
  "empresa_id": "1",
  "timestamp": "2026-01-24T12:00:00.000000"
}
```

**Recomendação:** tratar os dois formatos.

---

## 5) O que o Gestor App deve fazer ao receber “pedido novo”

### Estratégia recomendada: **Refetch (revalidar cache)**

Ao receber `pedido.v1.criado` (e/ou `notification_type="pedido_criado"`), o Gestor App deve:

- Invalidar cache local (React Query / Redux / Zustand / etc.)
- Refazer as requisições HTTP necessárias para atualizar a UI

### Endpoints HTTP típicos para atualizar a tela

Depende da UI do Gestor App, mas normalmente:

- **Kanban**: `GET /api/pedidos/admin/kanban?date_filter=YYYY-MM-DD&empresa_id={empresa_id}`
- **Lista**: `GET /api/pedidos/admin?empresa_id={empresa_id}&...`

---

## 6) Exemplo (TypeScript) — Conectar e escutar pedido novo no Gestor App

Este exemplo usa as funções da doc geral (`connectMensuraWS`, `setRoute`, `startPing`).

```ts
type WSEventMessage =
  | { type: "connection"; message: string; user_id: string; empresa_id: string; timestamp: string }
  | { type: "event"; event: string; scope: "empresa" | "usuario"; payload: Record<string, unknown>; timestamp: string }
  | { type: "notification"; notification_type: string; title: string; message: string; data?: any; empresa_id?: string; timestamp: string }
  | { type: "pong"; timestamp: string }
  | { type: "route_updated"; message: string; route: string; timestamp: string }
  | { type: "error"; message: string; timestamp: string };

function isPedidoNovo(msg: WSEventMessage) {
  // Contrato novo
  if (msg.type === "event" && msg.event === "pedido.v1.criado") return true;
  // Compat/legado
  if (msg.type === "notification" && msg.notification_type === "pedido_criado") return true;
  return false;
}

export function setupGestorAppPedidosWS(params: {
  empresaId: string;
  accessToken: string;
  wsBaseUrl: string; // ex: "wss://seu-host"
  onPedidoNovo: () => void; // ex: invalidate + refetch
}) {
  const { empresaId, accessToken, wsBaseUrl, onPedidoNovo } = params;

  const wsUrl = `${wsBaseUrl}/api/notifications/ws/notifications?empresa_id=${empresaId}`;
  const ws = new WebSocket(wsUrl, ["mensura-bearer", accessToken]);

  ws.onopen = () => {
    ws.send(JSON.stringify({ type: "set_route", route: "/gestor-app" }));
    // heartbeat
    setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }));
    }, 30000);
  };

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data) as WSEventMessage;
      if (isPedidoNovo(msg)) {
        onPedidoNovo();
      }
    } catch {
      // ignore
    }
  };

  return ws;
}
```

---

## 7) Checklist de implementação (Gestor App)

- [ ] Conectar ao WS `/api/notifications/ws/notifications?empresa_id={empresa_id}`
- [ ] Enviar token via `Sec-WebSocket-Protocol` (browser)
- [ ] Enviar `set_route` com `"/gestor-app"` ao abrir e a cada mudança de rota
- [ ] Rodar `ping` a cada 30s
- [ ] Ao receber `pedido.v1.criado` (e/ou `notification_type="pedido_criado"`), **refetch** do kanban/lista
- [ ] Implementar reconexão automática (backoff) + fallback (polling) se necessário

---

## 8) Status do backend (necessário para o Gestor App)

O contrato central (`WSEvents`) possui `pedido.v1.criado`, porém **hoje o backend não envia esse evento em tempo real no WebSocket na criação** (o “kanban” atual está amarrado ao momento em que o pedido é marcado como impresso).

Para o Gestor App funcionar como descrito aqui, é necessário implementar no backend:

- Emitir `event: "pedido.v1.criado"` (`WSEvents.PEDIDO_CRIADO`)
- `scope: "empresa"`
- `payload`: pelo menos `{ "pedido_id": "<id>" }` (opcionalmente incluir `tipo_entrega`, `numero_pedido`, `status`)
- Filtrar para o Gestor App com `required_route="/gestor-app"`

Opcional (legado):

- Enviar também uma `type="notification"` com `notification_type="pedido_criado"` (apenas se houver consumidores legados que precisam de toast/mensagem pronta)

---

**Última atualização**: 2026-01-24
