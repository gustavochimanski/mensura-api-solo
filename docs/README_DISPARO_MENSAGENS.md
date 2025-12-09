# 📚 Documentação de Disparo de Mensagens - Guia Rápido

## 🚀 Início Rápido

### 1. Importar Tipos TypeScript

```typescript
import {
  DispatchMessageRequest,
  DispatchMessageResponse,
  MESSAGE_TYPES,
  CHANNELS
} from './types/dispatch-messages.types';
```

### 2. Disparar Mensagem Simples

```typescript
const response = await fetch('/api/notifications/messages/dispatch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    empresa_id: 'emp_123',
    message_type: 'marketing',
    title: 'Promoção Especial',
    message: 'Aproveite 30% de desconto!',
    channels: ['email'],
    recipient_emails: ['cliente@email.com']
  })
});

const result = await response.json();
```

### 3. Usar Serviço Helper

```typescript
import { dispatchService } from './examples/dispatch-service';

// Disparar mensagem
const result = await dispatchService.dispatchMessage({
  empresa_id: 'emp_123',
  message_type: 'marketing',
  title: 'Promoção',
  message: 'Mensagem aqui',
  channels: ['email'],
  recipient_emails: ['cliente@email.com']
});

// Obter estatísticas
const stats = await dispatchService.getStats('emp_123', {
  messageType: 'marketing'
});
```

## 📖 Documentação Completa

- **[Documentação Completa](./API_DISPARO_MENSAGENS.md)** - Guia detalhado com todos os endpoints, exemplos e boas práticas
- **[Tipos TypeScript](./types/dispatch-messages.types.ts)** - Definições de tipos para TypeScript
- **[Serviço de Exemplo](./examples/dispatch-service.ts)** - Implementação de serviço helper

## 🔗 Endpoints Principais

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/notifications/messages/dispatch` | POST | Disparo individual |
| `/api/notifications/messages/bulk-dispatch` | POST | Disparo em massa |
| `/api/notifications/messages/stats` | GET | Estatísticas |

## 📋 Tipos de Mensagem

- `marketing` - Campanhas e promoções
- `utility` - Mensagens utilitárias
- `transactional` - Transações (pedidos, pagamentos)
- `promotional` - Promoções e ofertas
- `alert` - Alertas importantes
- `system` - Mensagens do sistema
- `news` - Notícias e atualizações

## 📡 Canais Disponíveis

- `email` - Email
- `whatsapp` - WhatsApp
- `push` - Notificação push
- `webhook` - Webhook HTTP
- `in_app` - Notificação in-app
- `sms` - SMS (futuro)
- `telegram` - Telegram (futuro)

## ⚡ Exemplos Rápidos

### Email Marketing
```typescript
{
  message_type: 'marketing',
  channels: ['email'],
  recipient_emails: ['cliente@email.com']
}
```

### Notificação de Pedido
```typescript
{
  message_type: 'transactional',
  channels: ['email', 'push', 'whatsapp'],
  user_ids: ['user_123'],
  priority: 'high'
}
```

### Campanha em Massa
```typescript
{
  message_type: 'promotional',
  channels: ['email', 'push'],
  filter_by_empresa: true,
  filter_by_tags: ['vip']
}
```

## 🔐 Autenticação

Todos os endpoints requerem token Bearer:

```
Authorization: Bearer {seu_token}
```

## ❓ Dúvidas?

Consulte a [documentação completa](./API_DISPARO_MENSAGENS.md) para:
- Exemplos detalhados
- Tratamento de erros
- Boas práticas
- Componentes React de exemplo

---

**Última atualização:** Dezembro 2024

