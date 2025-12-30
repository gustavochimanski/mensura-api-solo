# 📡 Documentação WebSocket - Sistema de Notificações em Tempo Real

Documentação completa para integração do front-end com o sistema de notificações via WebSocket da API Mensura.

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Conexão WebSocket](#conexão-websocket)
3. [Tipos de Mensagens](#tipos-de-mensagens)
4. [Sistema de Rotas](#sistema-de-rotas)
5. [Endpoints da API](#endpoints-da-api)
6. [FAQ](#faq)

---

## 🎯 Visão Geral

O sistema de notificações em tempo real utiliza WebSocket para enviar atualizações instantâneas para o front-end. Ele suporta:

- ✅ Notificações em tempo real de pedidos
- ✅ Atualizações de status de pedidos
- ✅ Notificações por empresa
- ✅ Notificações direcionadas por rota
- ✅ Sistema de ping/pong para manter conexão ativa
- ✅ Rastreamento de rota do usuário no front-end

---

## 🔌 Conexão WebSocket

### Configuração via Variáveis de Ambiente

**⚠️ IMPORTANTE:** A URL da API muda de cliente para cliente. Sempre use variáveis de ambiente para configurar a URL do backend.

#### Variáveis de Ambiente por Framework

**Next.js:**
```env
NEXT_PUBLIC_API_URL=https://teste2.mensuraapi.com.br
```

**React (Create React App / Vite):**
```env
REACT_APP_API_URL=https://teste2.mensuraapi.com.br
# ou
VITE_API_URL=https://teste2.mensuraapi.com.br
```

**Exemplo de uso no código:**

```typescript
// Next.js
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// React (Create React App)
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// React (Vite)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

### Endpoint de Conexão

**Padrão:**
```
ws://{API_URL}/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}
```

**⚠️ Atenção:** A URL do WebSocket deve ser construída a partir da URL da API:
- Se `API_URL` começa com `https://`, use `wss://` (WebSocket seguro)
- Se `API_URL` começa com `http://`, use `ws://` (WebSocket não seguro)

**Função auxiliar para construir URL do WebSocket:**

```typescript
function getWebSocketUrl(apiUrl: string, userId: string, empresaId: string): string {
  // Remove http:// ou https:// e adiciona ws:// ou wss://
  const protocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
  const cleanUrl = apiUrl.replace(/^https?:\/\//, '');
  return `${protocol}://${cleanUrl}/api/notifications/ws/notifications/${userId}?empresa_id=${empresaId}`;
}

// Exemplo de uso
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const wsUrl = getWebSocketUrl(API_URL, '1', '1');
// Resultado: wss://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=1
```

**Exemplos:**

**Com variável de ambiente (Produção):**
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL; // https://teste2.mensuraapi.com.br
const wsUrl = getWebSocketUrl(API_URL, userId, empresaId);
// wss://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=1
```

**Desenvolvimento Local (fallback):**
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const wsUrl = getWebSocketUrl(API_URL, userId, empresaId);
// ws://localhost:8000/api/notifications/ws/notifications/1?empresa_id=1
```

### Obtendo a URL de Conexão (Alternativa)

Você também pode obter a URL correta do WebSocket através do endpoint de configuração:

**GET** `/api/notifications/ws/config/{empresa_id}?user_id={user_id}`

**Resposta:**
```json
{
  "empresa_id": 1,
  "empresa_nome": "Minha Empresa",
  "websocket_url": "wss://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=1",
  "backend_url": "wss://teste2.mensuraapi.com.br",
  "protocol": "wss",
  "endpoint": "/api/notifications/ws/notifications/{user_id}?empresa_id=1"
}
```

**⚠️ Importante:**
- **SEMPRE use variáveis de ambiente** para a URL da API (muda de cliente para cliente)
- Use `ws://` para desenvolvimento (HTTP) e `wss://` para produção (HTTPS)
- O protocolo do WebSocket deve corresponder ao protocolo da API (http → ws, https → wss)
- O WebSocket sempre aponta para o **BACKEND**, não para o front-end
- Substitua `{user_id}` pelo ID real do usuário logado

---

## 📨 Tipos de Mensagens

### Mensagens Recebidas do Servidor

#### 1. Mensagem de Conexão (Connection)

Recebida quando a conexão é estabelecida com sucesso:

```json
{
  "type": "connection",
  "message": "Conectado com sucesso",
  "user_id": "1",
  "empresa_id": "1",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### 2. Notificação (Notification)

Notificação de evento (novo pedido, atualização de status, etc.):

```json
{
  "type": "notification",
  "notification_type": "kanban",
  "title": "Novo Pedido Recebido",
  "message": "Pedido #123 criado - Valor: R$ 150.00",
  "data": {
    "pedido_id": "123",
    "cliente": {
      "nome": "João Silva",
      "telefone": "11999999999"
    },
    "valor_total": 150.00,
    "itens_count": 3,
    "timestamp": "2024-01-15T10:30:00.000Z"
  },
  "empresa_id": "1",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Tipos de `notification_type`:**
- `kanban` - Novo pedido para o kanban
- `pedido_aprovado` - Pedido foi aprovado
- `pedido_cancelado` - Pedido foi cancelado
- `pedido_entregue` - Pedido foi entregue
- `pedido_status_changed` - Status do pedido mudou
- `pedido_atualizado` - Pedido foi atualizado
- `info` - Notificação genérica de informação
- `warning` - Aviso
- `error` - Erro
- `success` - Sucesso

#### 3. Pong (Resposta ao Ping)

Resposta ao ping enviado pelo cliente:

```json
{
  "type": "pong",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### 4. Confirmação de Inscrição (Subscription)

Confirmação de inscrição em tipos de eventos:

```json
{
  "type": "subscription",
  "message": "Inscrito em 3 tipos de eventos",
  "event_types": ["pedido_criado", "pedido_aprovado", "pedido_cancelado"],
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### 5. Rota Atualizada (Route Updated)

Confirmação de atualização de rota:

```json
{
  "type": "route_updated",
  "message": "Rota atualizada para: /pedidos",
  "route": "/pedidos",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### 6. Estatísticas (Stats)

Estatísticas da conexão (resposta ao `get_stats`):

```json
{
  "type": "stats",
  "data": {
    "total_users_connected": 5,
    "total_empresas_connected": 2,
    "total_connections": 5,
    "users_with_connections": ["1", "2", "3", "4", "5"],
    "empresas_with_connections": ["1", "2"],
    "empresas_details": {
      "1": {
        "connection_count": 3,
        "routes": ["/pedidos", "/dashboard", "/pedidos"]
      }
    }
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### 7. Erro (Error)

Mensagem de erro:

```json
{
  "type": "error",
  "message": "Formato de mensagem inválido",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Mensagens Enviadas pelo Cliente

#### 1. Ping

Mantém a conexão ativa:

```json
{
  "type": "ping"
}
```

#### 2. Subscribe

Inscreve-se em tipos específicos de eventos:

```json
{
  "type": "subscribe",
  "event_types": ["pedido_criado", "pedido_aprovado", "pedido_cancelado"]
}
```

#### 3. Set Route

Informa ao servidor a rota atual do usuário:

```json
{
  "type": "set_route",
  "route": "/pedidos"
}
```

**⚠️ Importante:** Envie esta mensagem sempre que o usuário navegar para uma nova rota. Isso permite que o servidor saiba qual a rota atual do usuario e envie notificações apenas para usuários em rotas específicas (ex: notificações de kanban só para quem está em `/pedidos`).

#### 4. Get Stats

Solicita estatísticas da conexão:

```json
{
  "type": "get_stats"
}
```

---

## 🗺️ Sistema de Rotas

O sistema permite enviar notificações apenas para usuários em rotas específicas.

**Informações Técnicas:**
- Envie mensagem do tipo `set_route` sempre que o usuário navegar para uma nova rota
- Notificações de kanban são enviadas apenas para usuários na rota `/pedidos`
- A rota é comparada em minúsculas e sem espaços
- O servidor mantém o registro da rota atual de cada conexão

**Formato da mensagem:**
```json
{
  "type": "set_route",
  "route": "/pedidos"
}
```

**Comportamento:**
- Quando uma notificação é enviada para uma empresa com filtro de rota, apenas clientes naquela rota recebem
- Se nenhum cliente estiver na rota especificada, a notificação não é entregue
- Rotas são normalizadas (convertidas para minúsculas e espaços removidos) antes da comparação

---

## ❓ FAQ

### Como obter a URL correta do WebSocket?

**⚠️ IMPORTANTE:** A URL da API muda de cliente para cliente. Sempre use variáveis de ambiente:

**Variáveis de Ambiente:**
- Next.js: `NEXT_PUBLIC_API_URL` (ex: `https://teste2.mensuraapi.com.br`)
- React (CRA): `REACT_APP_API_URL`
- React (Vite): `VITE_API_URL`

**Como construir a URL do WebSocket:**
- Se `API_URL` começa com `https://`, use protocolo `wss://`
- Se `API_URL` começa com `http://`, use protocolo `ws://`
- Remova o protocolo da URL (`http://` ou `https://`) e adicione o protocolo WebSocket correspondente
- Formato final: `{protocolo}://{host}/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}`

**Alternativa:** Use o endpoint `/api/notifications/ws/config/{empresa_id}` que retorna a URL completa.

### Por que não recebo notificações de kanban?

Verifique:
1. Se você está conectado ao WebSocket
2. Se você está na rota `/pedidos` (use `set_route`)
3. Se a empresa_id está correta
4. Se há conexões ativas (use endpoint `/connections/check/{empresa_id}`)

### Como testar a conexão?

1. Conecte ao WebSocket
2. Envie um `ping` e espere um `pong`
3. Use `get_stats` para ver estatísticas
4. Verifique logs do backend

### Posso ter múltiplas conexões do mesmo usuário?

Sim, cada aba/janela pode ter sua própria conexão. O servidor gerencia múltiplas conexões por usuário.

### Como parar de receber notificações?

Desconecte o WebSocket ou navegue para uma rota que não recebe notificações (ex: `/configuracoes`).

---

## 🔗 Endpoints da API

### Obter Configuração do WebSocket

**GET** `/api/notifications/ws/config/{empresa_id}?user_id={user_id}`

**Resposta:**
```json
{
  "empresa_id": 1,
  "empresa_nome": "Minha Empresa",
  "websocket_url": "wss://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=1",
  "backend_url": "wss://teste2.mensuraapi.com.br",
  "protocol": "wss",
  "endpoint": "/api/notifications/ws/notifications/{user_id}?empresa_id=1",
  "cors_origins": ["https://unitec-supervisor.vercel.app"]
}
```

### Verificar Conexões de uma Empresa

**GET** `/api/notifications/ws/connections/check/{empresa_id}`

**Autenticação:** Requer token JWT

**Resposta:**
```json
{
  "empresa_id": "1",
  "is_connected": true,
  "connection_count": 3,
  "all_connected_empresas": ["1", "2"],
  "total_connections": 5,
  "empresas_details": {
    "1": {
      "connection_count": 3,
      "routes": ["/pedidos", "/dashboard", "/pedidos"]
    }
  }
}
```

### Estatísticas Gerais

**GET** `/api/notifications/ws/connections/stats`

**Autenticação:** Requer token JWT

**Resposta:**
```json
{
  "total_users_connected": 5,
  "total_empresas_connected": 2,
  "total_connections": 5,
  "users_with_connections": ["1", "2", "3"],
  "empresas_with_connections": ["1", "2"],
  "empresas_details": {
    "1": {
      "connection_count": 3,
      "routes": ["/pedidos", "/dashboard"]
    }
  }
}
```

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs do backend
2. Use os endpoints de verificação de conexão
3. Confira se a URL do WebSocket está correta
4. Verifique se o backend está rodando

---

**Última atualização:** 2024-01-15

