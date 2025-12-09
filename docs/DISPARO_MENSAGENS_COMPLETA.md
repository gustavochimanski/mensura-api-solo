# 📨 API de Disparo de Mensagens - Documentação Completa

Documentação completa e atualizada para implementação de disparo de mensagens no frontend.

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Tipos de Mensagem](#tipos-de-mensagem)
3. [Canais de Envio](#canais-de-envio)
4. [Endpoints da API](#endpoints-da-api)
5. [Schemas e Tipos](#schemas-e-tipos)
6. [Exemplos Práticos](#exemplos-práticos)
7. [Tratamento de Erros](#tratamento-de-erros)
8. [Boas Práticas](#boas-práticas)

---

## 🎯 Visão Geral

O sistema de disparo de mensagens permite enviar notificações para usuários através de múltiplos canais, com classificação por tipo (marketing, utility, transactional, etc).

### Características

- ✅ **Múltiplos tipos de mensagem** (marketing, utility, transactional, etc)
- ✅ **Suporte a múltiplos canais** (email, WhatsApp, push, webhook, in-app)
- ✅ **Disparo individual ou em massa**
- ✅ **Filtros avançados** para seleção de destinatários
- ✅ **Estatísticas de disparo** em tempo real
- ✅ **Agendamento de mensagens**

### Base URL

```
/api/notifications/messages
```

### Autenticação

Todos os endpoints requerem autenticação via Bearer Token:

```
Authorization: Bearer {seu_token}
```

---

## 📨 Tipos de Mensagem

Cada mensagem deve ter um tipo definido para classificação e controle:

| Tipo | Valor | Descrição | Uso Recomendado |
|------|-------|-----------|-----------------|
| `marketing` | "marketing" | Mensagens promocionais e de marketing | Campanhas, ofertas, promoções |
| `utility` | "utility" | Mensagens utilitárias | Confirmações, atualizações de status |
| `transactional` | "transactional" | Mensagens transacionais | Pedidos, pagamentos, faturas |
| `promotional` | "promotional" | Promoções e ofertas | Descontos, cupons, lançamentos |
| `alert` | "alert" | Alertas e avisos importantes | Avisos críticos, lembretes urgentes |
| `system` | "system" | Mensagens do sistema | Manutenções, atualizações técnicas |
| `news` | "news" | Notícias e atualizações | Novidades, comunicados gerais |

---

## 📡 Canais de Envio

Os canais disponíveis para envio de mensagens:

| Canal | Valor | Descrição | Status |
|-------|-------|-----------|--------|
| `email` | "email" | Envio por email | ✅ Disponível |
| `whatsapp` | "whatsapp" | Envio por WhatsApp (Twilio) | ✅ Disponível |
| `push` | "push" | Notificação push (Firebase) | ✅ Disponível |
| `webhook` | "webhook" | Webhook HTTP POST | ✅ Disponível |
| `in_app` | "in_app" | Notificação in-app (WebSocket) | ✅ Disponível |
| `sms` | "sms" | SMS | 🚧 Futuro |
| `telegram` | "telegram" | Telegram | 🚧 Futuro |

---

## 🔌 Endpoints da API

### 1. Disparo de Mensagem Individual

Dispara uma mensagem para um ou mais destinatários específicos.

**Endpoint:** `POST /api/notifications/messages/dispatch`

**Request Body:**
```json
{
  "empresa_id": "string (obrigatório)",
  "message_type": "marketing | utility | transactional | promotional | alert | system | news",
  "title": "string (obrigatório, 1-255 caracteres)",
  "message": "string (obrigatório, mínimo 1 caractere)",
  "channels": ["email", "whatsapp", "push"],
  "user_ids": ["user_123", "user_456"],
  "recipient_emails": ["cliente@email.com"],
  "recipient_phones": ["+5511999999999"],
  "priority": "low | normal | high | urgent",
  "event_type": "string (opcional)",
  "event_data": {},
  "channel_metadata": {},
  "scheduled_at": "2024-12-10T10:00:00Z"
}
```

**Campos Obrigatórios:**
- `empresa_id`: ID da empresa
- `message_type`: Tipo da mensagem
- `title`: Título da mensagem
- `message`: Conteúdo da mensagem
- `channels`: Array com pelo menos um canal

**Campos de Destinatários (pelo menos um obrigatório):**
- `user_ids`: Array de IDs de usuários
- `recipient_emails`: Array de emails
- `recipient_phones`: Array de telefones

**Response 200:**
```json
{
  "success": true,
  "message_type": "marketing",
  "notification_ids": ["notif_123", "notif_456"],
  "total_recipients": 2,
  "channels_used": ["email", "whatsapp"],
  "scheduled": false,
  "scheduled_at": null
}
```

**Response 400 (Erro de Validação):**
```json
{
  "detail": "Deve fornecer pelo menos um: user_ids, recipient_emails ou recipient_phones"
}
```

---

### 2. Disparo em Massa

Dispara mensagem para múltiplos destinatários baseado em filtros.

**Endpoint:** `POST /api/notifications/messages/bulk-dispatch`

**Request Body:**
```json
{
  "empresa_id": "string (obrigatório)",
  "message_type": "marketing | utility | transactional | promotional | alert | system | news",
  "title": "string (obrigatório)",
  "message": "string (obrigatório)",
  "channels": ["email", "whatsapp"],
  "filter_by_empresa": true,
  "filter_by_user_type": "cliente | admin | entregador",
  "filter_by_tags": ["vip", "premium"],
  "priority": "normal",
  "max_recipients": 1000
}
```

**Campos de Filtro:**
- `filter_by_empresa`: Se `true`, envia para todos os usuários da empresa
- `filter_by_user_type`: Filtra por tipo de usuário (opcional)
- `filter_by_tags`: Filtra por tags (opcional)
- `max_recipients`: Limite máximo de destinatários (opcional)

**Response 200:**
```json
{
  "success": true,
  "message_type": "marketing",
  "notification_ids": ["notif_1", "notif_2", "..."],
  "total_recipients": 150,
  "channels_used": ["email"],
  "scheduled": false,
  "scheduled_at": null
}
```

---

### 3. Estatísticas de Disparo

Obtém estatísticas de disparos de mensagens.

**Endpoint:** `GET /api/notifications/messages/stats`

**Query Parameters:**
- `empresa_id` (obrigatório): ID da empresa
- `message_type` (opcional): Filtrar por tipo de mensagem
- `start_date` (opcional): Data inicial (ISO 8601)
- `end_date` (opcional): Data final (ISO 8601)

**Exemplo:**
```
GET /api/notifications/messages/stats?empresa_id=emp_123&message_type=marketing&start_date=2024-12-01T00:00:00Z&end_date=2024-12-31T23:59:59Z
```

**Response 200:**
```json
{
  "total": 500,
  "by_status": {
    "sent": 450,
    "failed": 30,
    "pending": 20
  },
  "by_channel": {
    "email": 300,
    "whatsapp": 200
  },
  "by_message_type": {
    "marketing": 300,
    "utility": 150,
    "transactional": 50
  }
}
```

---

## 📝 Schemas TypeScript

### DispatchMessageRequest
```typescript
interface DispatchMessageRequest {
  empresa_id: string;
  message_type: 'marketing' | 'utility' | 'transactional' | 'promotional' | 'alert' | 'system' | 'news';
  title: string;
  message: string;
  channels: ('email' | 'whatsapp' | 'push' | 'webhook' | 'in_app' | 'sms' | 'telegram')[];
  user_ids?: string[];
  recipient_emails?: string[];
  recipient_phones?: string[];
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  event_type?: string;
  event_data?: Record<string, any>;
  channel_metadata?: Record<string, any>;
  scheduled_at?: string; // ISO 8601
}
```

### DispatchMessageResponse
```typescript
interface DispatchMessageResponse {
  success: boolean;
  message_type: string;
  notification_ids: string[];
  total_recipients: number;
  channels_used: string[];
  scheduled: boolean;
  scheduled_at: string | null;
}
```

### BulkDispatchRequest
```typescript
interface BulkDispatchRequest {
  empresa_id: string;
  message_type: 'marketing' | 'utility' | 'transactional' | 'promotional' | 'alert' | 'system' | 'news';
  title: string;
  message: string;
  channels: string[];
  filter_by_empresa: boolean;
  filter_by_user_type?: string;
  filter_by_tags?: string[];
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  max_recipients?: number;
}
```

### MessageDispatchStats
```typescript
interface MessageDispatchStats {
  total: number;
  by_status: Record<string, number>;
  by_channel: Record<string, number>;
  by_message_type: Record<string, number>;
}
```

---

## 💡 Exemplos Práticos

### Exemplo 1: Disparo de Email Marketing

```typescript
const dispatchMarketingEmail = async () => {
  const response = await fetch('/api/notifications/messages/dispatch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      empresa_id: 'emp_123',
      message_type: 'marketing',
      title: 'Promoção Especial de Natal!',
      message: 'Aproveite 30% de desconto em todos os produtos até 25/12!',
      channels: ['email'],
      recipient_emails: ['cliente@email.com'],
      priority: 'normal'
    })
  });
  
  const data = await response.json();
  console.log('Mensagem disparada:', data);
};
```

### Exemplo 2: Notificação de Pedido (Transactional)

```typescript
const notifyOrderCreated = async (orderId: string, userId: string) => {
  const response = await fetch('/api/notifications/messages/dispatch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      empresa_id: 'emp_123',
      message_type: 'transactional',
      title: 'Pedido Confirmado',
      message: `Seu pedido #${orderId} foi confirmado e está sendo preparado!`,
      channels: ['email', 'push', 'whatsapp'],
      user_ids: [userId],
      priority: 'high',
      event_type: 'pedido_criado',
      event_data: {
        pedido_id: orderId,
        valor: 45.90
      }
    })
  });
  
  return await response.json();
};
```

### Exemplo 3: Campanha em Massa

```typescript
const sendBulkCampaign = async () => {
  const response = await fetch('/api/notifications/messages/bulk-dispatch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      empresa_id: 'emp_123',
      message_type: 'promotional',
      title: 'Novo Cardápio Disponível!',
      message: 'Confira nossos novos pratos e sabores exclusivos!',
      channels: ['email', 'push'],
      filter_by_empresa: true,
      filter_by_tags: ['vip', 'premium'],
      priority: 'normal',
      max_recipients: 1000
    })
  });
  
  const data = await response.json();
  console.log(`Campanha enviada para ${data.total_recipients} destinatários`);
};
```

### Exemplo 4: Agendamento de Mensagem

```typescript
const scheduleMessage = async () => {
  const scheduledDate = new Date();
  scheduledDate.setHours(10, 0, 0, 0); // 10:00 AM
  
  const response = await fetch('/api/notifications/messages/dispatch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      empresa_id: 'emp_123',
      message_type: 'marketing',
      title: 'Lembrete: Promoção Termina Hoje!',
      message: 'Últimas horas para aproveitar nossa promoção!',
      channels: ['email', 'push'],
      recipient_emails: ['cliente@email.com'],
      scheduled_at: scheduledDate.toISOString()
    })
  });
  
  return await response.json();
};
```

### Exemplo 5: Obter Estatísticas

```typescript
const getStats = async (empresaId: string, messageType?: string) => {
  const params = new URLSearchParams({
    empresa_id: empresaId
  });
  
  if (messageType) {
    params.append('message_type', messageType);
  }
  
  const response = await fetch(
    `/api/notifications/messages/stats?${params.toString()}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  return await response.json();
};

// Uso
const stats = await getStats('emp_123', 'marketing');
console.log(`Total de mensagens: ${stats.total}`);
console.log(`Enviadas: ${stats.by_status.sent}`);
```

---

## ⚠️ Tratamento de Erros

### Códigos de Status HTTP

| Código | Descrição | Ação Recomendada |
|--------|-----------|------------------|
| 200 | Sucesso | Processar resposta normalmente |
| 400 | Erro de validação | Verificar campos do request |
| 401 | Não autenticado | Reautenticar usuário |
| 403 | Sem permissão | Verificar permissões |
| 404 | Recurso não encontrado | Verificar IDs fornecidos |
| 500 | Erro interno | Tentar novamente ou reportar |

### Exemplo de Tratamento de Erros

```typescript
const dispatchMessage = async (data: DispatchMessageRequest) => {
  try {
    const response = await fetch('/api/notifications/messages/dispatch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      const error = await response.json();
      
      switch (response.status) {
        case 400:
          console.error('Erro de validação:', error.detail);
          // Mostrar mensagem de erro ao usuário
          break;
        case 401:
          // Redirecionar para login
          window.location.href = '/login';
          break;
        case 500:
          console.error('Erro interno do servidor');
          // Mostrar mensagem genérica
          break;
        default:
          console.error('Erro desconhecido:', error);
      }
      
      throw new Error(error.detail || 'Erro ao disparar mensagem');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Erro na requisição:', error);
    throw error;
  }
};
```

---

## 🎨 Boas Práticas

### 1. Validação no Frontend

Sempre valide os dados antes de enviar:

```typescript
const validateDispatchRequest = (data: DispatchMessageRequest): string[] => {
  const errors: string[] = [];
  
  if (!data.title || data.title.length < 1) {
    errors.push('Título é obrigatório');
  }
  
  if (!data.message || data.message.length < 1) {
    errors.push('Mensagem é obrigatória');
  }
  
  if (!data.channels || data.channels.length === 0) {
    errors.push('Pelo menos um canal deve ser selecionado');
  }
  
  const hasRecipients = 
    (data.user_ids && data.user_ids.length > 0) ||
    (data.recipient_emails && data.recipient_emails.length > 0) ||
    (data.recipient_phones && data.recipient_phones.length > 0);
  
  if (!hasRecipients) {
    errors.push('Pelo menos um destinatário deve ser fornecido');
  }
  
  return errors;
};
```

### 2. Feedback ao Usuário

Mostre feedback claro durante o disparo:

```typescript
const dispatchWithFeedback = async (data: DispatchMessageRequest) => {
  // Mostrar loading
  setLoading(true);
  setMessage('Enviando mensagens...');
  
  try {
    const result = await dispatchMessage(data);
    
    // Sucesso
    setMessage(`Mensagem enviada para ${result.total_recipients} destinatários!`);
    setSuccess(true);
    
    // Limpar formulário após 2 segundos
    setTimeout(() => {
      resetForm();
      setSuccess(false);
    }, 2000);
    
  } catch (error) {
    // Erro
    setMessage('Erro ao enviar mensagem. Tente novamente.');
    setError(true);
  } finally {
    setLoading(false);
  }
};
```

### 3. Seleção de Canais por Tipo de Mensagem

Sugira canais apropriados baseado no tipo:

```typescript
const getRecommendedChannels = (messageType: string): string[] => {
  const recommendations: Record<string, string[]> = {
    marketing: ['email', 'push'],
    transactional: ['email', 'whatsapp', 'push'],
    utility: ['email', 'push'],
    alert: ['push', 'whatsapp', 'email'],
    system: ['in_app', 'email'],
    news: ['email', 'push'],
    promotional: ['email', 'push', 'whatsapp']
  };
  
  return recommendations[messageType] || ['email'];
};
```

### 4. Limitação de Destinatários

Para disparos em massa, sempre defina um limite:

```typescript
const sendBulkWithLimit = async (data: BulkDispatchRequest) => {
  // Limitar a 1000 destinatários por padrão
  const maxRecipients = data.max_recipients || 1000;
  
  const response = await fetch('/api/notifications/messages/bulk-dispatch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      ...data,
      max_recipients: maxRecipients
    })
  });
  
  return await response.json();
};
```

### 5. Monitoramento de Estatísticas

Monitore estatísticas regularmente:

```typescript
const monitorStats = async (empresaId: string) => {
  const stats = await getStats(empresaId);
  
  // Calcular taxa de sucesso
  const successRate = (stats.by_status.sent / stats.total) * 100;
  
  // Alertar se taxa de falha for alta
  if (stats.by_status.failed / stats.total > 0.1) {
    console.warn('Taxa de falha alta:', stats.by_status.failed);
  }
  
  return {
    ...stats,
    successRate: successRate.toFixed(2)
  };
};
```

---

## 📊 Exemplo Completo: Componente React

```typescript
import React, { useState } from 'react';

interface DispatchFormProps {
  empresaId: string;
  onSuccess?: (result: DispatchMessageResponse) => void;
}

const DispatchMessageForm: React.FC<DispatchFormProps> = ({ empresaId, onSuccess }) => {
  const [formData, setFormData] = useState<DispatchMessageRequest>({
    empresa_id: empresaId,
    message_type: 'marketing',
    title: '',
    message: '',
    channels: ['email'],
    priority: 'normal'
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    
    try {
      const response = await fetch('/api/notifications/messages/dispatch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao enviar mensagem');
      }
      
      const result = await response.json();
      onSuccess?.(result);
      
      // Reset form
      setFormData({
        empresa_id: empresaId,
        message_type: 'marketing',
        title: '',
        message: '',
        channels: ['email'],
        priority: 'normal'
      });
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Tipo de Mensagem</label>
        <select
          value={formData.message_type}
          onChange={(e) => setFormData({ ...formData, message_type: e.target.value })}
        >
          <option value="marketing">Marketing</option>
          <option value="utility">Utility</option>
          <option value="transactional">Transactional</option>
          <option value="promotional">Promotional</option>
          <option value="alert">Alert</option>
          <option value="system">System</option>
          <option value="news">News</option>
        </select>
      </div>
      
      <div>
        <label>Título</label>
        <input
          type="text"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          required
        />
      </div>
      
      <div>
        <label>Mensagem</label>
        <textarea
          value={formData.message}
          onChange={(e) => setFormData({ ...formData, message: e.target.value })}
          required
        />
      </div>
      
      <div>
        <label>Canais</label>
        {['email', 'whatsapp', 'push', 'webhook', 'in_app'].map(channel => (
          <label key={channel}>
            <input
              type="checkbox"
              checked={formData.channels?.includes(channel)}
              onChange={(e) => {
                const channels = formData.channels || [];
                if (e.target.checked) {
                  setFormData({ ...formData, channels: [...channels, channel] });
                } else {
                  setFormData({ ...formData, channels: channels.filter(c => c !== channel) });
                }
              }}
            />
            {channel}
          </label>
        ))}
      </div>
      
      <div>
        <label>Emails (separados por vírgula)</label>
        <input
          type="text"
          onChange={(e) => {
            const emails = e.target.value.split(',').map(e => e.trim()).filter(e => e);
            setFormData({ ...formData, recipient_emails: emails });
          }}
        />
      </div>
      
      {error && <div className="error">{error}</div>}
      
      <button type="submit" disabled={loading}>
        {loading ? 'Enviando...' : 'Enviar Mensagem'}
      </button>
    </form>
  );
};

export default DispatchMessageForm;
```

---

## 🔗 Recursos Adicionais

- **Base URL da API:** `/api/notifications`
- **Documentação Swagger:** `/docs` (se disponível)
- **WebSocket para Notificações em Tempo Real:** `/api/notifications/ws/notifications/{user_id}`

---

## 📞 Suporte

Para dúvidas ou problemas, consulte a equipe de desenvolvimento ou a documentação técnica completa.

---

**Última atualização:** Dezembro 2024  
**Versão da API:** 1.0.0

