# 📡 Resumo do Sistema WebSocket - Notificações em Tempo Real

## 🎯 Visão Geral

O sistema WebSocket permite receber notificações em tempo real no frontend, como:
- Novos pedidos no kanban
- Atualizações de status de pedidos
- Notificações gerais da empresa
- Mensagens direcionadas por rota

---

## ⚡ Resumo Rápido

### 🔌 Endpoint WebSocket (Conexão Principal)
**Protocolo:** `ws://` ou `wss://` (WebSocket, não HTTP!)  
**URL:** `wss://api.seudominio.com/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}`  
**Uso:** `new WebSocket(url)` - Conexão persistente para receber notificações

### 🔗 Endpoints HTTP REST (Auxiliares)
**Protocolo:** `http://` ou `https://` (HTTP normal, não WebSocket!)  
**Exemplos:**
- `GET /api/notifications/ws/config/{empresa_id}` - Obter URL do WebSocket
- `GET /api/notifications/ws/connections/stats` - Estatísticas
- `GET /api/notifications/ws/connections/check/{empresa_id}` - Verificar conexões
- `POST /api/notifications/ws/notifications/send` - Enviar notificação
- `POST /api/notifications/ws/notifications/broadcast` - Broadcast

**Uso:** `fetch()` ou `axios` - Requisições HTTP normais

**⚠️ IMPORTANTE:** Apenas o endpoint principal é WebSocket. Os outros são HTTP REST normais!

---

## 🔌 Endpoints Disponíveis

### ⚠️ IMPORTANTE: Diferença entre WebSocket e HTTP

- **WebSocket (ws:// ou wss://):** Conexão persistente para receber notificações em tempo real
- **HTTP REST (http:// ou https://):** Endpoints auxiliares para obter informações ou enviar notificações

---

## 🌐 Endpoint WebSocket (Conexão Principal)

### **WebSocket - Conexão para Notificações em Tempo Real**
**Protocolo:** `WS` ou `WSS` (não HTTP!)  
**Endpoint:** `/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}`

**O que faz:**
- Estabelece conexão WebSocket persistente entre frontend e backend
- Registra o usuário e empresa para receber notificações
- Mantém conexão ativa para receber mensagens em tempo real
- Envia mensagem de boas-vindas ao conectar

**Formato da URL (WebSocket):**
```
ws://localhost:8000/api/notifications/ws/notifications/1?empresa_id=1
wss://api.seudominio.com/api/notifications/ws/notifications/1?empresa_id=1
```

**⚠️ ATENÇÃO:** 
- Use `ws://` para desenvolvimento (http://)
- Use `wss://` para produção (https://)
- **NÃO é HTTP GET/POST**, é uma conexão WebSocket!

**Parâmetros:**
- `{user_id}` - ID do usuário logado (no path)
- `empresa_id` - ID da empresa (query parameter)

**Como conectar no frontend:**
```javascript
const ws = new WebSocket('wss://api.seudominio.com/api/notifications/ws/notifications/1?empresa_id=1');
```

---

## 🔗 Endpoints HTTP REST (Auxiliares)

Estes são endpoints HTTP normais (GET/POST), **NÃO são WebSocket**. Eles retornam informações ou enviam notificações, mas usam HTTP, não WebSocket.

### 1. **GET /api/notifications/ws/config/{empresa_id}** (HTTP)
**Protocolo:** `HTTP` ou `HTTPS` (não WebSocket!)  
**O que faz:**
- Retorna a URL completa do WebSocket para uma empresa
- Útil para obter a URL correta sem construir manualmente
- Retorna também informações sobre protocolo (ws/wss)

**Quando usar:**
- Ao inicializar a aplicação para obter a URL correta
- Para garantir que está usando o protocolo correto (ws/wss)

**Exemplo de uso:**
```javascript
// Fazer requisição HTTP GET
const response = await fetch('https://api.seudominio.com/api/notifications/ws/config/1');
const config = await response.json();
// config.websocket_url contém a URL do WebSocket (wss://...)
```

**Exemplo de resposta:**
```json
{
  "empresa_id": 1,
  "empresa_nome": "Minha Empresa",
  "websocket_url": "wss://api.seudominio.com/api/notifications/ws/notifications/{user_id}?empresa_id=1",
  "protocol": "wss",
  "endpoint": "/api/notifications/ws/notifications/{user_id}?empresa_id=1"
}
```

---

### 2. **GET /api/notifications/ws/connections/stats** (HTTP)
**Protocolo:** `HTTP` ou `HTTPS` (não WebSocket!)  
**O que faz:**
- Retorna estatísticas de todas as conexões WebSocket ativas
- Mostra quantos usuários/empresas estão conectados
- Requer autenticação (admin)

**Quando usar:**
- Para debug e monitoramento
- Verificar se há conexões ativas

**Exemplo de uso:**
```javascript
// Fazer requisição HTTP GET
const response = await fetch('https://api.seudominio.com/api/notifications/ws/connections/stats', {
  headers: { 'Authorization': 'Bearer token' }
});
const stats = await response.json();
```

---

### 3. **GET /api/notifications/ws/connections/check/{empresa_id}** (HTTP)
**Protocolo:** `HTTP` ou `HTTPS` (não WebSocket!)  
**O que faz:**
- Verifica se uma empresa específica tem conexões WebSocket ativas
- Retorna quantidade de conexões da empresa
- Requer autenticação

**Quando usar:**
- Para verificar se a empresa está conectada
- Debug de problemas de notificações

**Exemplo de uso:**
```javascript
// Fazer requisição HTTP GET
const response = await fetch('https://api.seudominio.com/api/notifications/ws/connections/check/1', {
  headers: { 'Authorization': 'Bearer token' }
});
const check = await response.json();
```

---

### 4. **POST /api/notifications/ws/notifications/send** (HTTP)
**Protocolo:** `HTTP` ou `HTTPS` (não WebSocket!)  
**O que faz:**
- Envia notificação para um usuário específico via WebSocket
- Requer autenticação (admin)

**Parâmetros:**
- `user_id` - ID do usuário destinatário
- `title` - Título da notificação
- `message` - Mensagem da notificação
- `notification_type` - Tipo (info, success, warning, error)

**Quando usar:**
- Backend envia notificação direta para um usuário
- Não é usado pelo frontend diretamente

**Exemplo de uso:**
```javascript
// Fazer requisição HTTP POST
const response = await fetch('https://api.seudominio.com/api/notifications/ws/notifications/send?user_id=1', {
  method: 'POST',
  headers: { 
    'Authorization': 'Bearer token',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'Nova Notificação',
    message: 'Você tem uma nova mensagem',
    notification_type: 'info'
  })
});
```

---

### 5. **POST /api/notifications/ws/notifications/broadcast** (HTTP)
**Protocolo:** `HTTP` ou `HTTPS` (não WebSocket!)  
**O que faz:**
- Envia notificação para TODOS os usuários de uma empresa
- Requer autenticação (admin)

**Parâmetros:**
- `empresa_id` - ID da empresa
- `title` - Título da notificação
- `message` - Mensagem da notificação
- `notification_type` - Tipo (info, success, warning, error)

**Quando usar:**
- Backend envia notificação para toda a empresa
- Não é usado pelo frontend diretamente

**Exemplo de uso:**
```javascript
// Fazer requisição HTTP POST
const response = await fetch('https://api.seudominio.com/api/notifications/ws/notifications/broadcast?empresa_id=1', {
  method: 'POST',
  headers: { 
    'Authorization': 'Bearer token',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'Aviso Geral',
    message: 'Mensagem para todos',
    notification_type: 'info'
  })
});
```

---

## 📨 Mensagens que o Frontend Pode Enviar

Após conectar ao WebSocket, o frontend pode enviar estas mensagens:

### 1. **ping**
**Formato:**
```json
{
  "type": "ping"
}
```

**O que faz:**
- Mantém a conexão ativa
- Servidor responde com `pong`

**Quando usar:**
- Enviar periodicamente (ex: a cada 30 segundos)
- Para evitar timeout da conexão

---

### 2. **set_route**
**Formato:**
```json
{
  "type": "set_route",
  "route": "/pedidos"
}
```

**O que faz:**
- Informa ao servidor em qual rota o usuário está
- Permite filtrar notificações por rota (ex: kanban só para quem está em `/pedidos`)

**Quando usar:**
- **IMPORTANTE:** Sempre que o usuário navegar para uma nova rota
- Ao entrar na página `/pedidos` (para receber notificações kanban)
- Ao sair de `/pedidos` (envie rota vazia ou outra rota)

**Exemplo:**
```javascript
// Ao entrar em /pedidos
websocket.send(JSON.stringify({
  type: "set_route",
  route: "/pedidos"
}));

// Ao sair de /pedidos
websocket.send(JSON.stringify({
  type: "set_route",
  route: ""
}));
```

---

### 3. **subscribe**
**Formato:**
```json
{
  "type": "subscribe",
  "event_types": ["kanban", "pedido_aprovado"]
}
```

**O que faz:**
- Informa ao servidor quais tipos de eventos o cliente quer receber
- Atualmente não é usado pelo backend, mas pode ser implementado no futuro

---

### 4. **get_stats**
**Formato:**
```json
{
  "type": "get_stats"
}
```

**O que faz:**
- Solicita estatísticas da conexão atual
- Servidor responde com informações sobre conexões

---

## 📥 Mensagens que o Frontend Recebe

### 1. **connection** (Ao conectar)
```json
{
  "type": "connection",
  "message": "Conectado com sucesso",
  "user_id": "1",
  "empresa_id": "1",
  "timestamp": "2024-01-01T12:00:00"
}
```

**Quando recebe:**
- Imediatamente após conectar ao WebSocket

---

### 2. **notification** (Notificação)
```json
{
  "type": "notification",
  "notification_type": "kanban",
  "title": "Novo Pedido",
  "message": "Pedido #123 foi criado",
  "timestamp": "2024-01-01T12:00:00"
}
```

**Tipos de notificação:**
- `kanban` - Novo pedido para o kanban
- `pedido_aprovado` - Pedido aprovado
- `pedido_cancelado` - Pedido cancelado
- `pedido_entregue` - Pedido entregue
- `info`, `success`, `warning`, `error` - Notificações gerais

**Quando recebe:**
- Quando há um evento relevante (ex: novo pedido)
- Apenas se estiver na rota correta (para notificações filtradas por rota)

---

### 3. **pong** (Resposta ao ping)
```json
{
  "type": "pong",
  "timestamp": "2024-01-01T12:00:00"
}
```

**Quando recebe:**
- Após enviar mensagem `ping`

---

### 4. **route_updated** (Confirmação de rota)
```json
{
  "type": "route_updated",
  "message": "Rota atualizada para: /pedidos",
  "route": "/pedidos",
  "timestamp": "2024-01-01T12:00:00"
}
```

**Quando recebe:**
- Após enviar mensagem `set_route`

---

### 5. **error** (Erro)
```json
{
  "type": "error",
  "message": "Formato de mensagem inválido",
  "timestamp": "2024-01-01T12:00:00"
}
```

**Quando recebe:**
- Quando há erro no processamento de uma mensagem

---

## 🚀 Como o Frontend Deve Usar

### ⚠️ LEMBRE-SE:
- **WebSocket (ws:// ou wss://):** Apenas o endpoint principal `/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}`
- **HTTP REST (http:// ou https://):** Todos os outros endpoints (config, stats, check, send, broadcast)

---

### **1. LOGIN - Conectar ao WebSocket**

**Quando:** Imediatamente após o usuário fazer login

**Passos:**
1. **(OPCIONAL)** Obter URL do WebSocket via endpoint HTTP:
   ```javascript
   // Fazer requisição HTTP GET (não WebSocket!)
   const response = await fetch(`https://api.seudominio.com/api/notifications/ws/config/${empresaId}`);
   const config = await response.json();
   const wsUrl = config.websocket_url.replace('{user_id}', userId);
   ```

2. **OU** Construir URL do WebSocket manualmente:
   ```javascript
   const apiUrl = process.env.NEXT_PUBLIC_API_URL; // ou REACT_APP_API_URL
   const protocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
   const wsUrl = `${protocol}://${apiUrl.replace(/^https?:\/\//, '')}/api/notifications/ws/notifications/${userId}?empresa_id=${empresaId}`;
   ```

3. Criar conexão WebSocket:
   ```javascript
   const ws = new WebSocket(wsUrl); // ⚠️ WebSocket, não fetch()!
   ```
4. Configurar handlers:
   ```javascript
   ws.onopen = () => {
     console.log('WebSocket conectado');
     // Enviar rota atual se necessário
   };
   
   ws.onmessage = (event) => {
     const data = JSON.parse(event.data);
     // Processar notificação
   };
   
   ws.onerror = (error) => {
     console.error('Erro WebSocket:', error);
   };
   
   ws.onclose = () => {
     console.log('WebSocket desconectado');
     // Implementar reconexão
   };
   ```

---

### **2. NAVEGAÇÃO - Atualizar Rota**

**Quando:** Sempre que o usuário navegar para uma nova página/rota

**Ação:**
```javascript
// Ao entrar em /pedidos
if (window.location.pathname.includes('/pedidos')) {
  ws.send(JSON.stringify({
    type: "set_route",
    route: "/pedidos"
  }));
}

// Ao sair de /pedidos
else {
  ws.send(JSON.stringify({
    type: "set_route",
    route: window.location.pathname
  }));
}
```

**Importante:**
- Notificações kanban só são entregues para usuários na rota `/pedidos`
- Sempre informe a rota atual ao navegar

---

### **3. MANTER CONEXÃO ATIVA - Ping/Pong**

**Quando:** Periodicamente (ex: a cada 30 segundos)

**Ação:**
```javascript
// Enviar ping a cada 30 segundos
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping" }));
  }
}, 30000);
```

---

### **4. RECEBER NOTIFICAÇÕES - Processar Mensagens**

**Quando:** Sempre que receber mensagem do WebSocket

**Ação:**
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'connection':
      console.log('Conectado:', data.message);
      break;
      
    case 'notification':
      // Mostrar notificação para o usuário
      showNotification(data.title, data.message, data.notification_type);
      
      // Se for kanban, atualizar lista de pedidos
      if (data.notification_type === 'kanban') {
        refreshKanban();
      }
      break;
      
    case 'pong':
      console.log('Conexão ativa');
      break;
      
    case 'route_updated':
      console.log('Rota atualizada:', data.route);
      break;
      
    case 'error':
      console.error('Erro:', data.message);
      break;
  }
};
```

---

### **5. LOGOUT - Desconectar do WebSocket**

**Quando:** Quando o usuário fizer logout

**Ação:**
```javascript
function logout() {
  // Fechar conexão WebSocket
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
  
  // Limpar dados do usuário
  // Redirecionar para login
}
```

---

### **6. RECONEXÃO AUTOMÁTICA**

**Quando:** Quando a conexão for fechada inesperadamente

**Ação:**
```javascript
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

ws.onclose = (event) => {
  console.log('WebSocket desconectado');
  
  // Tentar reconectar
  if (reconnectAttempts < maxReconnectAttempts) {
    reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
    
    setTimeout(() => {
      console.log(`Tentando reconectar (${reconnectAttempts}/${maxReconnectAttempts})...`);
      connectWebSocket(); // Função que cria nova conexão
    }, delay);
  }
};

ws.onopen = () => {
  reconnectAttempts = 0; // Reset contador ao conectar
};
```

---

## 📋 Checklist de Implementação

### ✅ No Login
- [ ] Obter `user_id` e `empresa_id`
- [ ] Construir URL do WebSocket corretamente
- [ ] Criar conexão WebSocket
- [ ] Configurar handlers (onopen, onmessage, onerror, onclose)
- [ ] Enviar rota atual se necessário

### ✅ Na Navegação
- [ ] Detectar mudança de rota
- [ ] Enviar mensagem `set_route` com a nova rota
- [ ] Enviar rota vazia ao sair de `/pedidos` (se necessário)

### ✅ Durante a Sessão
- [ ] Enviar `ping` periodicamente (a cada 30s)
- [ ] Processar notificações recebidas
- [ ] Mostrar notificações para o usuário
- [ ] Atualizar UI quando receber notificações kanban

### ✅ No Logout
- [ ] Fechar conexão WebSocket
- [ ] Limpar referências

### ✅ Tratamento de Erros
- [ ] Implementar reconexão automática
- [ ] Tratar erros de conexão
- [ ] Validar mensagens recebidas

---

## 🔍 Exemplo Completo de Uso

```javascript
class WebSocketService {
  constructor(userId, empresaId, apiUrl) {
    this.userId = userId;
    this.empresaId = empresaId;
    this.apiUrl = apiUrl;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.pingInterval = null;
  }
  
  connect() {
    // Construir URL
    const protocol = this.apiUrl.startsWith('https') ? 'wss' : 'ws';
    const host = this.apiUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${protocol}://${host}/api/notifications/ws/notifications/${this.userId}?empresa_id=${this.empresaId}`;
    
    // Criar conexão
    this.ws = new WebSocket(wsUrl);
    
    // Handlers
    this.ws.onopen = () => {
      console.log('WebSocket conectado');
      this.reconnectAttempts = 0;
      this.startPing();
      this.setRoute(window.location.pathname);
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket desconectado');
      this.stopPing();
      this.attemptReconnect();
    };
    
    this.ws.onerror = (error) => {
      console.error('Erro WebSocket:', error);
    };
  }
  
  handleMessage(data) {
    switch (data.type) {
      case 'notification':
        this.onNotification(data);
        break;
      case 'connection':
        console.log('Conectado:', data.message);
        break;
      case 'pong':
        console.log('Pong recebido');
        break;
    }
  }
  
  onNotification(data) {
    // Mostrar notificação
    showNotification(data.title, data.message, data.notification_type);
    
    // Atualizar kanban se necessário
    if (data.notification_type === 'kanban') {
      refreshKanban();
    }
  }
  
  setRoute(route) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: "set_route",
        route: route
      }));
    }
  }
  
  startPing() {
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000);
  }
  
  stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
  
  attemptReconnect() {
    if (this.reconnectAttempts < 5) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      setTimeout(() => {
        console.log(`Reconectando... (${this.reconnectAttempts}/5)`);
        this.connect();
      }, delay);
    }
  }
  
  disconnect() {
    this.stopPing();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Uso
const wsService = new WebSocketService(userId, empresaId, process.env.NEXT_PUBLIC_API_URL);
wsService.connect();

// Ao navegar
router.events.on('routeChangeComplete', (url) => {
  wsService.setRoute(url);
});

// Ao fazer logout
function logout() {
  wsService.disconnect();
  // ... resto do logout
}
```

---

## ⚠️ Pontos Importantes

1. **URL do WebSocket:** Sempre use variáveis de ambiente, nunca URLs hardcoded
2. **Protocolo:** `https://` → `wss://`, `http://` → `ws://`
3. **Rota:** Sempre informe a rota atual ao navegar (especialmente `/pedidos`)
4. **Reconexão:** Implemente reconexão automática para melhor UX
5. **Ping/Pong:** Envie ping periodicamente para manter conexão ativa
6. **Logout:** Sempre feche a conexão ao fazer logout

---

## 📚 Documentação Adicional

- [Documentação Completa](./WEBSOCKET_FRONTEND.md)
- [Exemplo de Código Frontend](../examples/frontend_websocket_example.js)
- [README Principal](./README.md)

