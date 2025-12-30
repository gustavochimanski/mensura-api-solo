# 🔍 Debug de Conexões WebSocket

Este documento explica como as conexões WebSocket funcionam e como debugar problemas.

## 📍 De Onde Vêm as Conexões?

As conexões WebSocket **NÃO são criadas automaticamente**. Elas são criadas quando:

1. **O frontend se conecta** ao endpoint WebSocket
2. **O endpoint é chamado** via protocolo WebSocket (não HTTP)

### Endpoint de Conexão

```
ws://{base_url}/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}
```

**Exemplo:**
```
ws://localhost:8000/api/notifications/ws/notifications/1?empresa_id=1
```

## 🔄 Fluxo de Conexão

```
1. Frontend inicia conexão WebSocket
   ↓
2. Backend recebe no endpoint /ws/notifications/{user_id}
   ↓
3. websocket_manager.connect() é chamado
   ↓
4. Conexão é adicionada aos dicionários:
   - active_connections[user_id]
   - empresa_connections[empresa_id]
   - websocket_to_user[websocket]
   - websocket_to_empresa[websocket]
   ↓
5. Conexão fica ativa até o cliente desconectar
```

## 🧪 Como Verificar Conexões

### 1. Endpoint de Estatísticas

```bash
GET /api/notifications/ws/connections/stats
```

**Resposta:**
```json
{
  "total_users_connected": 0,
  "total_empresas_connected": 0,
  "total_connections": 0,
  "users_with_connections": [],
  "empresas_with_connections": [],
  "empresas_details": {},
  "message": "Use estas informações para verificar se há conexões WebSocket ativas",
  "how_to_connect": {
    "endpoint": "/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}",
    "example": "/api/notifications/ws/notifications/1?empresa_id=1",
    "protocol": "WebSocket (ws:// ou wss://)",
    "note": "As conexões são criadas quando o frontend se conecta ao endpoint WebSocket acima"
  }
}
```

### 2. Verificar Empresa Específica

```bash
GET /api/notifications/ws/connections/check/1
```

**Resposta:**
```json
{
  "empresa_id": "1",
  "is_connected": false,
  "connection_count": 0,
  "all_connected_empresas": [],
  "total_connections": 0,
  "empresas_details": {},
  "message": "Conecte-se ao WebSocket...",
  "how_to_connect": {
    "endpoint": "/api/notifications/ws/notifications/{user_id}?empresa_id=1",
    "protocol": "WebSocket (ws:// ou wss://)",
    "example_url": "ws://localhost:8000/api/notifications/ws/notifications/1?empresa_id=1",
    "note": "Substitua {user_id} pelo ID real do usuário. A conexão deve ser feita pelo frontend."
  }
}
```

## 🐛 Problemas Comuns

### Problema: "Empresas conectadas: []"

**Causa:** Nenhum cliente se conectou ao WebSocket ainda.

**Solução:**
1. Verifique se o frontend está conectando ao WebSocket
2. Verifique se a URL está correta
3. Verifique se o protocolo é WebSocket (ws:// ou wss://), não HTTP

### Problema: Conexão é criada mas não aparece nas estatísticas

**Possíveis causas:**
1. Conexão foi desconectada imediatamente após conectar
2. Erro durante o registro da conexão
3. Problema de normalização de tipos (int vs string)

**Solução:**
- Verifique os logs com prefixo `[CONNECT]` e `[WS_ROUTER]`
- Verifique se há erros durante a conexão

### Problema: Notificações não chegam mesmo com conexões ativas

**Possíveis causas:**
1. Cliente não está na rota `/pedidos`
2. Rota não foi informada ao servidor
3. Problema de normalização de empresa_id

**Solução:**
- Verifique se o cliente enviou `set_route` com `/pedidos`
- Verifique os logs com prefixo `[CHECK]` e `[NOTIFY]`
- Verifique `empresas_details` nas estatísticas para ver as rotas

## 📊 Logs Importantes

### Quando uma conexão é criada:
```
[WS_ROUTER] Tentando conectar WebSocket - user_id=..., empresa_id=...
[CONNECT] Iniciando conexão - user_id=..., empresa_id=...
[CONNECT] WebSocket conectado com sucesso. Estado atual: ...
```

### Quando verifica conexões:
```
[CHECK] Verificando conexões para empresa_id=...
[CHECK] Empresas no dicionário: [...]
[CHECK] Empresa X tem Y conexões ativas. Rotas: [...]
```

### Quando tenta enviar notificação:
```
[NOTIFY] Verificando conexões antes de enviar notificação kanban...
[NOTIFY] Estado atual das conexões: ...
[NOTIFY] Resultado da verificação is_empresa_connected: ...
```

## 🧪 Testando Manualmente

### 1. Usando wscat (Node.js)

```bash
npm install -g wscat
wscat -c "ws://localhost:8000/api/notifications/ws/notifications/1?empresa_id=1"
```

### 2. Usando Python

```python
import asyncio
import websockets
import json

async def test_connection():
    uri = "ws://localhost:8000/api/notifications/ws/notifications/1?empresa_id=1"
    async with websockets.connect(uri) as websocket:
        # Recebe mensagem de boas-vindas
        welcome = await websocket.recv()
        print("Conectado:", welcome)
        
        # Informa rota
        await websocket.send(json.dumps({
            "type": "set_route",
            "route": "/pedidos"
        }))
        
        # Aguarda confirmação
        response = await websocket.recv()
        print("Rota atualizada:", response)
        
        # Mantém conexão aberta
        await asyncio.sleep(60)

asyncio.run(test_connection())
```

### 3. Usando JavaScript no Browser

```javascript
const ws = new WebSocket('ws://localhost:8000/api/notifications/ws/notifications/1?empresa_id=1');

ws.onopen = () => {
    console.log('Conectado!');
    
    // Informa rota
    ws.send(JSON.stringify({
        type: 'set_route',
        route: '/pedidos'
    }));
};

ws.onmessage = (event) => {
    console.log('Mensagem recebida:', JSON.parse(event.data));
};
```

## 📝 Checklist de Debug

- [ ] Frontend está conectando ao WebSocket?
- [ ] URL do WebSocket está correta?
- [ ] Protocolo é WebSocket (ws://), não HTTP?
- [ ] user_id e empresa_id estão corretos?
- [ ] Cliente enviou `set_route` com `/pedidos`?
- [ ] Verificou `/api/notifications/ws/connections/stats`?
- [ ] Verificou `/api/notifications/ws/connections/check/{empresa_id}`?
- [ ] Verificou os logs com prefixos `[CONNECT]`, `[CHECK]`, `[NOTIFY]`?

## 🔗 Referências

- [Guia de Implementação Frontend](./WEBSOCKET_NOTIFICACOES_FRONTEND.md)
- [Documentação de Notificações](./NOTIFICACOES_PEDIDOS.md)

