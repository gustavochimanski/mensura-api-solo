# Documentação Frontend - Notificações "Chamar Atendente"

Esta documentação descreve como o frontend deve tratar as notificações quando um cliente solicita atendimento humano via chatbot.

---

## 📋 Visão Geral

Quando um cliente pede para "chamar atendente" no chatbot, o sistema envia uma notificação em tempo real via WebSocket para o dashboard da empresa. O frontend precisa estar conectado ao WebSocket e escutar esses eventos para exibir a notificação.

---

## 🔌 1. Conexão WebSocket

### Endpoint

```
WS: /api/notifications/ws/notifications?empresa_id={empresa_id}
```

**Exemplos:**
- **Local**: `ws://localhost:8000/api/notifications/ws/notifications?empresa_id=1`
- **Produção**: `wss://seu-dominio.com/api/notifications/ws/notifications?empresa_id=1`

### Autenticação

O WebSocket requer autenticação via JWT. No browser, use o header `Sec-WebSocket-Protocol`:

```typescript
const token = localStorage.getItem('access_token'); // ou como você armazena o token
const wsUrl = `wss://seu-dominio.com/api/notifications/ws/notifications?empresa_id=${empresaId}`;
const ws = new WebSocket(wsUrl, ["mensura-bearer", token]);
```

---

## 📨 2. Formato da Mensagem

Quando um cliente solicita atendimento, você receberá uma mensagem no seguinte formato:

```json
{
  "type": "notification",
  "notification_type": "chamar_atendente",
  "title": "🔔 Solicitação de Atendimento Humano",
  "message": "Cliente João Silva está solicitando atendimento de um humano.\n\n📱 Telefone: 5511999999999\n👤 Nome: João Silva",
  "data": {
    "cliente_phone": "5511999999999",
    "cliente_nome": "João Silva",
    "tipo": "chamar_atendente",
    "timestamp": "2024-01-17T20:30:45.123456"
  },
  "empresa_id": "1",
  "timestamp": "2024-01-17T20:30:45.123456"
}
```

### Campos Importantes

- **`notification_type`**: Sempre `"chamar_atendente"` para este tipo de notificação
- **`data.cliente_phone`**: Telefone do cliente (formato: 5511999999999)
- **`data.cliente_nome`**: Nome do cliente (pode ser `null` se não cadastrado)
- **`data.timestamp`**: Quando a solicitação foi feita
- **`empresa_id`**: ID da empresa que recebeu a solicitação

---

## 💻 3. Implementação no Frontend

### Exemplo Completo (TypeScript/React)

```typescript
import { useEffect, useState } from 'react';

interface ChamarAtendenteNotification {
  type: 'notification';
  notification_type: 'chamar_atendente';
  title: string;
  message: string;
  data: {
    cliente_phone: string;
    cliente_nome: string | null;
    tipo: string;
    timestamp: string;
  };
  empresa_id: string;
  timestamp: string;
}

export function useChatbotNotifications(empresaId: string) {
  const [notifications, setNotifications] = useState<ChamarAtendenteNotification[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token || !empresaId) return;

    const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/api/notifications/ws/notifications?empresa_id=${empresaId}`;
    const websocket = new WebSocket(wsUrl, ["mensura-bearer", token]);

    websocket.onopen = () => {
      console.log('✅ WebSocket conectado para notificações do chatbot');
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Filtra apenas notificações de "chamar atendente"
        if (data.type === 'notification' && data.notification_type === 'chamar_atendente') {
          const notification = data as ChamarAtendenteNotification;
          
          // Adiciona à lista de notificações
          setNotifications(prev => [notification, ...prev]);
          
          // Exibe notificação visual (toast, modal, etc)
          showNotificationToast(notification);
          
          // Opcional: Emite som de notificação
          playNotificationSound();
        }
      } catch (error) {
        console.error('Erro ao processar mensagem WebSocket:', error);
      }
    };

    websocket.onerror = (error) => {
      console.error('Erro no WebSocket:', error);
    };

    websocket.onclose = () => {
      console.log('WebSocket desconectado. Tentando reconectar...');
      // Implementar reconexão automática se necessário
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [empresaId]);

  return { notifications, ws };
}

// Componente de exibição
export function ChamarAtendenteNotificationToast({ notification }: { notification: ChamarAtendenteNotification }) {
  return (
    <div className="notification-toast">
      <div className="notification-header">
        <span className="notification-icon">🔔</span>
        <h3>{notification.title}</h3>
      </div>
      <div className="notification-body">
        <p>{notification.message}</p>
        <div className="notification-actions">
          <button onClick={() => handleContactClient(notification.data.cliente_phone)}>
            Entrar em Contato
          </button>
          <button onClick={() => handleViewChat(notification.data.cliente_phone)}>
            Ver Conversa
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## 🎨 4. Exemplo de UI/UX

### Opção 1: Toast/Notificação Flutuante

```typescript
function showNotificationToast(notification: ChamarAtendenteNotification) {
  // Usando uma biblioteca de toast (ex: react-toastify, sonner, etc)
  toast.info(
    <div>
      <strong>{notification.title}</strong>
      <p>{notification.data.cliente_nome || notification.data.cliente_phone}</p>
      <button onClick={() => openChatWindow(notification.data.cliente_phone)}>
        Atender
      </button>
    </div>,
    {
      duration: 10000, // 10 segundos
      position: 'top-right',
      icon: '🔔'
    }
  );
}
```

### Opção 2: Badge/Contador no Menu

```typescript
const [pendingRequests, setPendingRequests] = useState(0);

// Ao receber notificação
if (data.notification_type === 'chamar_atendente') {
  setPendingRequests(prev => prev + 1);
}

// No componente de menu
<MenuIcon>
  Atendimentos
  {pendingRequests > 0 && (
    <Badge count={pendingRequests}>
      <BellIcon />
    </Badge>
  )}
</MenuIcon>
```

### Opção 3: Lista de Solicitações Pendentes

```typescript
function AtendimentoRequestsList({ notifications }: { notifications: ChamarAtendenteNotification[] }) {
  return (
    <div className="atendimento-requests">
      <h2>Solicitações de Atendimento ({notifications.length})</h2>
      {notifications.map((notif, index) => (
        <div key={index} className="request-card">
          <div className="request-header">
            <span className="client-name">
              {notif.data.cliente_nome || 'Cliente sem nome'}
            </span>
            <span className="request-time">
              {formatTime(notif.data.timestamp)}
            </span>
          </div>
          <div className="request-phone">
            📱 {formatPhoneNumber(notif.data.cliente_phone)}
          </div>
          <div className="request-actions">
            <button onClick={() => openWhatsApp(notif.data.cliente_phone)}>
              Abrir WhatsApp
            </button>
            <button onClick={() => markAsRead(notif)}>
              Marcar como Lida
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## 🔧 5. Funções Auxiliares

### Formatar Telefone

```typescript
function formatPhoneNumber(phone: string): string {
  // Remove caracteres não numéricos
  const cleaned = phone.replace(/\D/g, '');
  
  // Formata: (11) 99999-9999
  if (cleaned.length === 13) {
    return `(${cleaned.slice(2, 4)}) ${cleaned.slice(4, 9)}-${cleaned.slice(9)}`;
  }
  
  return phone;
}
```

### Abrir WhatsApp

```typescript
function openWhatsApp(phone: string) {
  // Remove código do país se necessário
  const phoneNumber = phone.startsWith('55') ? phone.slice(2) : phone;
  const whatsappUrl = `https://wa.me/${phone}`;
  window.open(whatsappUrl, '_blank');
}
```

### Abrir Chat do Cliente (se tiver tela de chat)

```typescript
function openChatWindow(phone: string) {
  // Navegar para a tela de chat do cliente
  window.location.href = `/chatbot/conversas/${phone}`;
  // Ou usar roteamento do seu framework
  // router.push(`/chatbot/conversas/${phone}`);
}
```

---

## 📊 6. Persistência Local (Opcional)

Se quiser manter as notificações mesmo após recarregar a página:

```typescript
// Salvar no localStorage
function saveNotification(notification: ChamarAtendenteNotification) {
  const saved = localStorage.getItem('atendimento_requests');
  const notifications = saved ? JSON.parse(saved) : [];
  notifications.push(notification);
  localStorage.setItem('atendimento_requests', JSON.stringify(notifications));
}

// Carregar ao iniciar
function loadSavedNotifications(): ChamarAtendenteNotification[] {
  const saved = localStorage.getItem('atendimento_requests');
  return saved ? JSON.parse(saved) : [];
}

// Marcar como lida
function markAsRead(notification: ChamarAtendenteNotification) {
  const saved = localStorage.getItem('atendimento_requests');
  const notifications = saved ? JSON.parse(saved) : [];
  const updated = notifications.filter(n => 
    n.data.cliente_phone !== notification.data.cliente_phone ||
    n.timestamp !== notification.timestamp
  );
  localStorage.setItem('atendimento_requests', JSON.stringify(updated));
}
```

---

## 🚨 7. Tratamento de Erros

```typescript
websocket.onerror = (error) => {
  console.error('Erro no WebSocket:', error);
  // Exibir mensagem de erro ao usuário
  toast.error('Erro na conexão com o servidor. Tentando reconectar...');
};

websocket.onclose = (event) => {
  console.log('WebSocket fechado:', event.code, event.reason);
  
  // Reconexão automática após 3 segundos
  if (event.code !== 1000) { // Não foi fechado intencionalmente
    setTimeout(() => {
      connectWebSocket(); // Sua função de conexão
    }, 3000);
  }
};
```

---

## ✅ 8. Checklist de Implementação

- [ ] Conectar ao WebSocket com autenticação JWT
- [ ] Escutar mensagens do tipo `"chamar_atendente"`
- [ ] Exibir notificação visual (toast, modal, badge)
- [ ] Implementar ação "Entrar em Contato" (abrir WhatsApp)
- [ ] Implementar ação "Ver Conversa" (se tiver tela de chat)
- [ ] Formatar telefone para exibição
- [ ] Tratar reconexão automática em caso de queda
- [ ] (Opcional) Persistir notificações no localStorage
- [ ] (Opcional) Marcar notificações como lidas
- [ ] (Opcional) Emitir som de notificação

---

## 📝 9. Exemplo de Integração com React Router

```typescript
import { useNavigate } from 'react-router-dom';

function useAtendimentoNotifications(empresaId: string) {
  const navigate = useNavigate();
  
  // ... código do WebSocket ...
  
  websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.notification_type === 'chamar_atendente') {
      // Exibe toast
      toast.info('Nova solicitação de atendimento!', {
        onClick: () => navigate(`/atendimentos/${data.data.cliente_phone}`)
      });
      
      // Atualiza contador global
      updateAtendimentoCount();
    }
  };
}
```

---

## 🔗 10. Endpoints Relacionados

Se precisar buscar histórico ou mais informações:

- **GET** `/api/notifications/historico/empresa/{empresa_id}` - Histórico de notificações
- **GET** `/api/chatbot/conversas?empresa_id={empresa_id}&phone={phone}` - Conversa do cliente
- **GET** `/api/cadastros/clientes?telefone={phone}` - Dados do cliente

---

## 💡 Dicas

1. **Performance**: Limite o número de notificações em memória (ex: últimas 50)
2. **UX**: Dê feedback visual claro quando uma notificação é recebida
3. **Acessibilidade**: Use ARIA labels e suporte a leitores de tela
4. **Mobile**: Considere notificações push para mobile (se implementado)
5. **Priorização**: Destaque notificações não lidas

---

## 📞 Suporte

Em caso de dúvidas sobre a implementação, consulte:
- Documentação WebSocket: `DOCUMENTACAO_FRONTEND_WEBSOCKET.md`
- Documentação Notificações: `app/api/notifications/docs/DOCUMENTACAO_FRONTEND_NOTIFICATIONS_API.md`
