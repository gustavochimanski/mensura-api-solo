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

### Quando Enviar user_id e empresa_id

**⚠️ IMPORTANTE:** O `user_id` e `empresa_id` são enviados **no momento da conexão**, diretamente na URL do WebSocket. Eles não são enviados como mensagens depois da conexão.

**Formato da URL de Conexão:**
```
{protocolo}://{host}/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}
```

**Onde:**
- `{user_id}` - ID do usuário logado (deve estar no path da URL)
- `{empresa_id}` - ID da empresa (deve estar como query parameter)

**Exemplo:**
```
wss://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=1
                                           ↑                              ↑
                                    user_id=1                    empresa_id=1
```

**Quando conectar:**
- O front-end deve ter o `user_id` do usuário autenticado
- O front-end deve ter o `empresa_id` da empresa selecionada/ativa
- Construa a URL com esses valores antes de criar a conexão WebSocket
- Ao fazer `new WebSocket(url)`, os parâmetros já são enviados automaticamente

**⚠️ Observação sobre tipos:**
- Os valores podem ser números ou strings no código do front-end
- Na URL, serão convertidos para string automaticamente
- O backend recebe e normaliza ambos como string internamente
- Certifique-se de que os IDs estão corretos na URL, pois são usados para identificar a conexão

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

### Endpoint de Conexão

**Padrão:**
```
ws://{API_URL}/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}
```

**⚠️ Atenção:** A URL do WebSocket deve ser construída a partir da URL da API:
- Se `API_URL` começa com `https://`, use protocolo `wss://` (WebSocket seguro)
- Se `API_URL` começa com `http://`, use protocolo `ws://` (WebSocket não seguro)
- Remova o protocolo (`http://` ou `https://`) da URL da API
- Adicione o protocolo WebSocket correspondente (`ws://` ou `wss://`)
- Substitua `{user_id}` pelo ID do usuário logado
- Substitua `{empresa_id}` pelo ID da empresa
- Formato: `{protocolo}://{host}/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}`

**Exemplos de URLs:**

| API URL | user_id | empresa_id | URL Final |
|---------|---------|------------|-----------|
| `https://teste2.mensuraapi.com.br` | 1 | 1 | `wss://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=1` |
| `http://localhost:8000` | 5 | 2 | `ws://localhost:8000/api/notifications/ws/notifications/5?empresa_id=2` |

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
- **O `user_id` e `empresa_id` são enviados na URL de conexão**, não como mensagens depois
- Use `ws://` para desenvolvimento (HTTP) e `wss://` para produção (HTTPS)
- O protocolo do WebSocket deve corresponder ao protocolo da API (http → ws, https → wss)
- O WebSocket sempre aponta para o **BACKEND**, não para o front-end
- Substitua `{user_id}` pelo ID real do usuário logado e `{empresa_id}` pelo ID da empresa na URL
- A conexão só pode ser estabelecida se você tiver ambos os valores (user_id e empresa_id)

### ⏰ Quando Manter a Conexão Ativa

**⚠️ CRÍTICO:** A conexão WebSocket deve estar **ativa e mantida continuamente** enquanto o usuário estiver logado e precisar receber notificações.

**Quando estabelecer a conexão:**
- Logo após o login bem-sucedido do usuário
- Quando o usuário seleciona/troca de empresa
- Após uma desconexão (implementar reconexão automática)
- Quando o usuário volta a focar na aba/janela (se a conexão foi perdida)

**Quando manter a conexão:**
- Durante toda a sessão do usuário
- Mesmo quando o usuário navega entre diferentes páginas/rotas
- Quando o usuário está em background (aba não focada) mas ainda logado

**O que acontece se a conexão não estiver ativa:**

Se o front-end não estiver conectado ao WebSocket quando um evento ocorre no backend (ex: criação de pedido, aprovação, etc.), a notificação **não será entregue**.

**Logs do backend quando não há conexão:**
```
WARNING:app.api.notifications.core.websocket_manager:[CHECK] Empresa 1 não tem conexões ativas. Empresas conectadas: []
WARNING:app.api.notifications.services.pedido_notification_service:[NOTIFY] Notificação kanban não enviada: empresa 1 não tem conexões ativas. Pedido 64 criado mas nenhum cliente conectado.
```

**Isso significa:**
- O backend tentou enviar uma notificação
- Não encontrou nenhuma conexão WebSocket ativa para a empresa
- A notificação foi perdida
- O front-end não receberá essa atualização em tempo real

**Verificando se a conexão está ativa:**

1. **No front-end (DevTools):**
   - Abra DevTools → Network → Filtre por "WS" (WebSocket)
   - Verifique se há uma conexão WebSocket listada
   - O status deve estar "101 Switching Protocols" ou similar
   - Verifique se há mensagens sendo trocadas

2. **Via endpoint da API:**
   ```
   GET /api/notifications/ws/connections/check/{empresa_id}
   ```
   - Se `is_connected: true`, há conexões ativas
   - Se `is_connected: false`, não há conexões para essa empresa

3. **Via WebSocket:**
   - Envie um `ping` e espere um `pong` como resposta
   - Use `get_stats` para verificar estatísticas da conexão

**Recomendações:**
- Implemente reconexão automática quando a conexão cair
- Envie `ping` periodicamente (ex: a cada 30 segundos) para manter a conexão viva
- Verifique o status da conexão ao mudar de empresa
- Monitore eventos de `close` e `error` para detectar desconexões

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

**⚠️ Importante:** Envie esta mensagem sempre que o usuário navegar para uma nova rota. Isso permite que o servidor saiba qual a rota atual do usuário e envie notificações apenas para usuários em rotas específicas (ex: notificações de kanban só para quem está em `/pedidos`).

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

**Possíveis causas:**

1. **Não há conexões WebSocket ativas:**
   - O front-end não está conectado ao WebSocket
   - A conexão foi fechada/desconectada
   - Verifique usando o endpoint `/connections/check/{empresa_id}`

2. **Você não está na rota `/pedidos`:**
   - Notificações kanban só são enviadas para usuários na rota `/pedidos`
   - Envie mensagem `set_route` informando a rota atual

3. **A empresa_id está incorreta:**
   - Verifique se o `empresa_id` usado na conexão WebSocket corresponde ao da empresa do pedido

4. **Problema na URL do WebSocket:**
   - URL pode estar incorreta
   - Protocolo pode estar errado (ws vs wss)
   - Verifique usando o endpoint `/config/{empresa_id}`

**Como diagnosticar:**

1. Verifique conexões ativas: `GET /api/notifications/ws/connections/check/{empresa_id}`
   - Se retornar `is_connected: false` ou `connection_count: 0`, não há conexões ativas
   
2. Verifique logs do backend procurando por:
   - `[CHECK] Empresa X não tem conexões ativas`
   - `[NOTIFY] Notificação kanban não enviada: empresa X não tem conexões ativas`
   - `Empresas conectadas: []` indica que não há nenhuma conexão

3. No front-end, verifique:
   - Se a conexão WebSocket foi estabelecida (evento `onopen`)
   - Se está recebendo mensagem de conexão do tipo `connection`
   - Se há erros no console do navegador

### Como testar a conexão?

1. Conecte ao WebSocket e verifique se recebe mensagem do tipo `connection`
2. Envie um `ping` e espere um `pong` como resposta
3. Use `get_stats` via WebSocket para ver estatísticas
4. Use o endpoint `GET /api/notifications/ws/connections/check/{empresa_id}` para verificar se o servidor detecta sua conexão
5. Verifique logs do backend para mensagens de conexão/desconexão

### Interpretando Logs do Backend

**Logs de Conexão Bem-sucedida:**
```
[CONNECT] WebSocket conectado com sucesso - user_id=1, empresa_id=1
[WS_ROUTER] WebSocket conectado e registrado - user_id=1, empresa_id=1. Total de conexões: 1
```

**Logs de Problema (Nenhuma Conexão):**
```
[CHECK] Empresa 1 não tem conexões ativas. Empresas conectadas: []
[NOTIFY] Notificação kanban não enviada: empresa 1 não tem conexões ativas
```

**Erro 404 - Rota não encontrada:**
```
"GET /api/notifications/ws/notifications/1?empresa_id=2 HTTP/1.1" 404
```

**⚠️ Se você ver um 404 ao tentar conectar:**

Este erro indica que o servidor não encontrou a rota. Isso pode acontecer por várias razões:

**1. Está usando requisição HTTP ao invés de WebSocket:**
- **Problema:** Está usando `fetch()`, `axios.get()`, ou qualquer método HTTP ao invés de `new WebSocket()`
- **Solução:** WebSocket requer uma conexão especial, não uma requisição HTTP. Use `new WebSocket(url)`

**2. Protocolo incorreto na URL:**
- **Problema:** Está usando `http://` ou `https://` ao invés de `ws://` ou `wss://`
- **Solução:** WebSocket usa protocolos diferentes:
  - `http://` → use `ws://`
  - `https://` → use `wss://`

**3. URL mal formada:**
- **Problema:** A URL não está no formato correto
- **Solução:** Verifique se a URL está assim: `{protocolo}://{host}/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}`

**4. Problema com o servidor/proxy:**
- **Problema:** Um proxy ou load balancer pode estar bloqueando conexões WebSocket
- **Solução:** Verifique se o servidor/proxy está configurado para permitir upgrades WebSocket

**Como verificar qual é o problema:**

**Teste 1 - Verificar se está usando WebSocket corretamente:**

Exemplo usando a URL real: `wss://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=2`

```javascript
// ✅ CORRETO - Conecta via WebSocket
// URL: wss://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=2
const ws = new WebSocket('wss://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=2');

ws.onopen = () => {
    console.log('✅ Conexão WebSocket estabelecida!');
    console.log('Esperando mensagem de conexão do servidor...');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Mensagem recebida:', data);
    
    // Primeira mensagem deve ser do tipo "connection"
    if (data.type === 'connection') {
        console.log('✅ Confirmado: Conectado com sucesso!');
        console.log('User ID:', data.user_id);
        console.log('Empresa ID:', data.empresa_id);
    }
};

ws.onerror = (error) => {
    console.error('❌ Erro na conexão WebSocket:', error);
    console.error('Verifique se a URL está correta e se o servidor está acessível');
};

ws.onclose = (event) => {
    console.log('Conexão fechada:', event.code, event.reason);
    if (event.code !== 1000) {
        console.warn('⚠️ Conexão fechada inesperadamente. Código:', event.code);
    }
};

// ❌ ERRADO - Isso vai dar 404
// fetch() é para requisições HTTP, não WebSocket
fetch('https://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=2');
```

**Teste 2 - Verificar a URL no DevTools:**
1. Abra DevTools → Network
2. Filtre por "WS" (WebSocket)
3. Tente conectar
4. Se aparecer como requisição HTTP (não WebSocket) no Network, você está usando o método errado

**Teste 3 - Verificar a URL completa:**
- URL correta: `wss://teste2.mensuraapi.com.br/api/notifications/ws/notifications/1?empresa_id=2`
- Verifique se:
  - Usa `ws://` ou `wss://` (não `http://` ou `https://`)
  - Tem `/api/notifications/ws/notifications/` no path
  - Tem `{user_id}` substituído por um número (ex: `1`)
  - Tem `?empresa_id={empresa_id}` no final (ex: `?empresa_id=2`)

**Teste 4 - Verificar se o endpoint existe:**
- Use o endpoint de configuração para obter a URL correta:
  ```
  GET /api/notifications/ws/config/{empresa_id}?user_id={user_id}
  ```
- Isso retorna a URL exata que deve ser usada

**Solução resumida:**
- **SEMPRE use `new WebSocket(url)`** para estabelecer a conexão
- Certifique-se de usar o protocolo correto: `ws://` ou `wss://`
- Não use `fetch()`, `axios()`, ou qualquer biblioteca HTTP para conectar ao WebSocket
- A URL deve ser construída corretamente com `user_id` no path e `empresa_id` como query parameter

**Se você ver logs indicando que não há conexões:**
- O front-end não está conectado ao WebSocket
- A conexão foi estabelecida mas depois foi fechada
- O `empresa_id` usado na conexão não corresponde ao esperado

**Verificações no Front-end:**
- Abra DevTools → Network → Filtre por WS (WebSocket)
- Verifique se há uma conexão WebSocket ativa
- Verifique o status da conexão (deve estar "Open" ou 1)
- Verifique se há mensagens sendo trocadas
- Certifique-se de que está usando `new WebSocket()` e não métodos HTTP

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

