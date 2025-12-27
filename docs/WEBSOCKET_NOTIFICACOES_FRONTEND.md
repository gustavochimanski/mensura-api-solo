# 📡 WebSocket de Notificações - Guia de Implementação Frontend

Este documento explica como implementar a conexão WebSocket no frontend para receber notificações em tempo real, especialmente notificações kanban de novos pedidos.

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Conectando ao WebSocket](#conectando-ao-websocket)
3. [Rastreamento de Rotas](#rastreamento-de-rotas)
4. [Tipos de Notificações](#tipos-de-notificações)
5. [Exemplo Completo](#exemplo-completo)
6. [Integração com Frameworks](#integração-com-frameworks)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

O sistema de notificações WebSocket permite que o frontend receba atualizações em tempo real sobre eventos do sistema, como novos pedidos. 

**Características principais:**
- ✅ Conexão persistente WebSocket
- ✅ Rastreamento de rotas (notificações kanban só para clientes em `/pedidos`)
- ✅ Reconexão automática
- ✅ Suporte a ping/pong para manter conexão ativa

---

## 🔌 Conectando ao WebSocket

### URL de Conexão

```
ws://{base_url}/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}
```

**Parâmetros:**
- `base_url`: URL base da API (ex: `localhost:8000` ou `api.seudominio.com`)
- `user_id`: ID do usuário logado
- `empresa_id`: ID da empresa do usuário

**Exemplo:**
```javascript
const userId = '123';
const empresaId = '1';
const baseUrl = 'ws://localhost:8000';
const wsUrl = `${baseUrl}/api/notifications/ws/notifications/${userId}?empresa_id=${empresaId}`;

const ws = new WebSocket(wsUrl);
```

### Mensagem de Boas-Vindas

Ao conectar, o servidor envia uma mensagem de confirmação:

```json
{
  "type": "connection",
  "message": "Conectado com sucesso",
  "user_id": "123",
  "empresa_id": "1",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

## 🗺️ Rastreamento de Rotas

### Por que é importante?

As **notificações kanban** (novos pedidos) são enviadas **APENAS** para clientes que estão na rota `/pedidos`. Isso evita notificações desnecessárias quando o usuário está em outras páginas.

### Como informar a rota atual

Quando o usuário navegar para a página de pedidos, você **DEVE** informar o servidor:

```javascript
// Quando entrar na rota /pedidos
ws.send(JSON.stringify({
    type: 'set_route',
    route: '/pedidos'
}));

// Quando sair da rota /pedidos
ws.send(JSON.stringify({
    type: 'set_route',
    route: ''
}));
```

### Resposta do Servidor

O servidor confirma a atualização da rota:

```json
{
  "type": "route_updated",
  "message": "Rota atualizada para: /pedidos",
  "route": "/pedidos",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

## 📨 Tipos de Notificações

### 1. Notificação Kanban (Novo Pedido)

**Quando é enviada:**
- Apenas para clientes conectados
- Apenas para clientes na rota `/pedidos`
- Quando um novo pedido é criado

**Formato da mensagem:**
```json
{
  "type": "notification",
  "notification_type": "kanban",
  "title": "Novo Pedido Recebido",
  "message": "Pedido #37 criado - Valor: R$ 45.90",
  "data": {
    "pedido_id": "37",
    "cliente": {
      "id": 1,
      "nome": "João Silva",
      "telefone": "11999999999",
      "email": "joao@email.com"
    },
    "valor_total": 45.90,
    "itens_count": 2,
    "timestamp": "2024-01-15T10:30:00.000Z"
  },
  "empresa_id": "1",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### 2. Outros Tipos de Notificação

- `pedido_aprovado`: Pedido foi aprovado
- `pedido_cancelado`: Pedido foi cancelado
- `pedido_entregue`: Pedido foi entregue

---

## 💻 Exemplo Completo

### Implementação Básica (Vanilla JavaScript)

```javascript
class NotificationWebSocket {
    constructor(userId, empresaId, baseUrl = 'ws://localhost:8000') {
        this.userId = userId;
        this.empresaId = empresaId;
        this.baseUrl = baseUrl;
        this.ws = null;
        this.isConnected = false;
        this.currentRoute = '';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        const wsUrl = `${this.baseUrl}/api/notifications/ws/notifications/${this.userId}?empresa_id=${this.empresaId}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('✅ WebSocket conectado');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            
            // Se já estiver na rota /pedidos, informe imediatamente
            if (window.location.pathname.includes('/pedidos')) {
                this.setRoute('/pedidos');
            }
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            console.log('❌ WebSocket desconectado');
            this.isConnected = false;
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('❌ Erro no WebSocket:', error);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connection':
                console.log('Conectado:', data.message);
                break;

            case 'notification':
                if (data.notification_type === 'kanban') {
                    this.handleKanbanNotification(data);
                }
                break;

            case 'route_updated':
                console.log('Rota atualizada:', data.route);
                this.currentRoute = data.route;
                break;

            case 'pong':
                // Resposta ao ping - conexão está ativa
                break;

            case 'error':
                console.error('Erro do servidor:', data.message);
                break;
        }
    }

    handleKanbanNotification(data) {
        console.log('🎉 Novo pedido recebido!', data);
        
        // Atualizar UI do kanban
        this.updateKanban(data.data);
        
        // Mostrar notificação visual (opcional)
        this.showNotification(data.title, data.message);
    }

    updateKanban(pedidoData) {
        // Implementar lógica para adicionar o novo pedido ao kanban
        // Exemplo:
        const kanbanContainer = document.getElementById('kanban-pedidos');
        if (kanbanContainer) {
            // Adicionar card do novo pedido na coluna apropriada
            const novoCard = this.createPedidoCard(pedidoData);
            kanbanContainer.appendChild(novoCard);
        }
    }

    setRoute(route) {
        if (this.isConnected && this.ws) {
            this.ws.send(JSON.stringify({
                type: 'set_route',
                route: route
            }));
            this.currentRoute = route;
        }
    }

    send(data) {
        if (this.isConnected && this.ws) {
            this.ws.send(JSON.stringify(data));
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Tentativa de reconexão ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            setTimeout(() => this.connect(), 3000);
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
    }
}

// Uso
const userId = localStorage.getItem('userId'); // ou de onde você obtém o user_id
const empresaId = localStorage.getItem('empresaId'); // ou de onde você obtém o empresa_id

const notificationWS = new NotificationWebSocket(userId, empresaId);
notificationWS.connect();

// Monitorar mudanças de rota
let lastPath = window.location.pathname;
setInterval(() => {
    const currentPath = window.location.pathname;
    if (currentPath !== lastPath) {
        lastPath = currentPath;
        
        if (currentPath.includes('/pedidos')) {
            notificationWS.setRoute('/pedidos');
        } else {
            notificationWS.setRoute('');
        }
    }
}, 500);
```

---

## 🚀 Integração com Frameworks

### React

```jsx
import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

function useNotificationWebSocket(userId, empresaId) {
    const wsRef = useRef(null);
    const location = useLocation();

    useEffect(() => {
        // Conectar
        const wsUrl = `ws://localhost:8000/api/notifications/ws/notifications/${userId}?empresa_id=${empresaId}`;
        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
            console.log('WebSocket conectado');
        };

        wsRef.current.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'notification' && data.notification_type === 'kanban') {
                // Disparar evento ou atualizar estado
                window.dispatchEvent(new CustomEvent('kanban-notification', { detail: data }));
            }
        };

        // Cleanup
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [userId, empresaId]);

    // Atualizar rota quando mudar
    useEffect(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            if (location.pathname.includes('/pedidos')) {
                wsRef.current.send(JSON.stringify({
                    type: 'set_route',
                    route: '/pedidos'
                }));
            } else {
                wsRef.current.send(JSON.stringify({
                    type: 'set_route',
                    route: ''
                }));
            }
        }
    }, [location.pathname]);

    return wsRef.current;
}

// Uso no componente
function PedidosPage() {
    const userId = useAuth().user.id;
    const empresaId = useAuth().user.empresa_id;
    const ws = useNotificationWebSocket(userId, empresaId);

    useEffect(() => {
        const handleNotification = (event) => {
            const data = event.detail;
            // Atualizar estado do kanban
            console.log('Novo pedido:', data.data);
        };

        window.addEventListener('kanban-notification', handleNotification);
        return () => window.removeEventListener('kanban-notification', handleNotification);
    }, []);

    return <div>Kanban de Pedidos</div>;
}
```

### Vue.js

```vue
<template>
  <div>
    <!-- Seu kanban aqui -->
  </div>
</template>

<script>
export default {
  data() {
    return {
      ws: null,
      userId: null,
      empresaId: null
    }
  },
  mounted() {
    this.userId = this.$store.state.user.id;
    this.empresaId = this.$store.state.user.empresa_id;
    this.connectWebSocket();
    this.setupRouteWatcher();
  },
  beforeUnmount() {
    if (this.ws) {
      this.ws.close();
    }
  },
  methods: {
    connectWebSocket() {
      const wsUrl = `ws://localhost:8000/api/notifications/ws/notifications/${this.userId}?empresa_id=${this.empresaId}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket conectado');
        // Se já estiver na rota /pedidos
        if (this.$route.path.includes('/pedidos')) {
          this.setRoute('/pedidos');
        }
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'notification' && data.notification_type === 'kanban') {
          this.handleKanbanNotification(data);
        }
      };
    },
    setRoute(route) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: 'set_route',
          route: route
        }));
      }
    },
    handleKanbanNotification(data) {
      // Atualizar kanban
      this.$store.dispatch('pedidos/addPedido', data.data);
    },
    setupRouteWatcher() {
      this.$watch('$route.path', (newPath) => {
        if (newPath.includes('/pedidos')) {
          this.setRoute('/pedidos');
        } else {
          this.setRoute('');
        }
      });
    }
  }
}
</script>
```

### Angular

```typescript
import { Injectable, OnDestroy } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class NotificationWebSocketService implements OnDestroy {
  private ws: WebSocket | null = null;
  private kanbanNotifications$ = new Subject<any>();

  constructor(private router: Router) {
    this.setupRouteWatcher();
  }

  connect(userId: string, empresaId: string) {
    const wsUrl = `ws://localhost:8000/api/notifications/ws/notifications/${userId}?empresa_id=${empresaId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket conectado');
      this.updateRoute();
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'notification' && data.notification_type === 'kanban') {
        this.kanbanNotifications$.next(data);
      }
    };
  }

  setRoute(route: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'set_route',
        route: route
      }));
    }
  }

  private updateRoute() {
    const currentRoute = this.router.url;
    if (currentRoute.includes('/pedidos')) {
      this.setRoute('/pedidos');
    } else {
      this.setRoute('');
    }
  }

  private setupRouteWatcher() {
    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {
        this.updateRoute();
      });
  }

  getKanbanNotifications() {
    return this.kanbanNotifications$.asObservable();
  }

  ngOnDestroy() {
    if (this.ws) {
      this.ws.close();
    }
  }
}
```

---

## 🔍 Troubleshooting

### Problema: Notificações não estão chegando

**Verificações:**

1. **Conexão estabelecida?**
   ```javascript
   console.log('WebSocket estado:', ws.readyState);
   // 0 = CONNECTING
   // 1 = OPEN
   // 2 = CLOSING
   // 3 = CLOSED
   ```

2. **Rota informada corretamente?**
   - Verifique se você está enviando `set_route` quando entrar em `/pedidos`
   - Verifique os logs do servidor para confirmar que a rota foi atualizada

3. **Empresa e usuário corretos?**
   - Confirme que `user_id` e `empresa_id` estão corretos na URL de conexão

4. **Verificar conexões ativas:**
   ```bash
   GET /api/notifications/ws/connections/stats
   GET /api/notifications/ws/connections/check/{empresa_id}
   ```

### Problema: Conexão cai frequentemente

**Soluções:**

1. **Implementar ping/pong:**
   ```javascript
   setInterval(() => {
       if (ws.readyState === WebSocket.OPEN) {
           ws.send(JSON.stringify({ type: 'ping' }));
       }
   }, 30000); // A cada 30 segundos
   ```

2. **Reconexão automática:**
   ```javascript
   ws.onclose = () => {
       console.log('Reconectando em 3 segundos...');
       setTimeout(() => connect(), 3000);
   };
   ```

### Problema: Notificações chegam mesmo fora de /pedidos

**Causa:** Rota não foi informada ou foi informada incorretamente.

**Solução:** Certifique-se de chamar `setRoute('/pedidos')` quando entrar na rota e `setRoute('')` quando sair.

---

## 📝 Checklist de Implementação

- [ ] Conectar ao WebSocket na inicialização da aplicação
- [ ] Informar rota `/pedidos` quando o usuário entrar nessa página
- [ ] Limpar rota quando o usuário sair de `/pedidos`
- [ ] Implementar handler para notificações tipo `kanban`
- [ ] Atualizar UI do kanban quando receber notificação
- [ ] Implementar reconexão automática
- [ ] Implementar ping/pong para manter conexão ativa
- [ ] Tratar erros e desconexões

---

## 🔗 Referências

- [Exemplo completo de implementação](../app/api/notifications/examples/frontend_websocket_example.js)
- [Documentação de notificações de pedidos](./NOTIFICACOES_PEDIDOS.md)
- [API de estatísticas de conexões](../app/api/notifications/router/websocket_router.py#L134)

---

## 💡 Dicas

1. **Conecte uma única vez:** Crie uma instância global do WebSocket e reutilize
2. **Monitore a rota:** Use os hooks/observers do seu framework para detectar mudanças de rota
3. **Trate erros:** Sempre implemente tratamento de erros e reconexão
4. **Logs úteis:** Adicione logs para debug durante desenvolvimento
5. **Teste desconexões:** Simule perda de conexão para garantir que a reconexão funciona

---

**Última atualização:** Janeiro 2024

