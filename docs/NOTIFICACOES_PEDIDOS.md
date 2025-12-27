# Sistema de Notificações de Novos Pedidos

## 📋 Visão Geral

Sistema implementado para enviar notificações em tempo real ao frontend sempre que um novo pedido é criado no sistema. Utiliza WebSocket para comunicação bidirecional e notificações instantâneas.

## 🏗️ Arquitetura

O sistema está integrado nos seguintes pontos de criação de pedidos:

1. **`service_pedido_admin.py`** - Criação de pedidos via admin (DELIVERY, MESA, BALCAO)
2. **`service_pedidos_mesa.py`** - Criação de pedidos de mesa
3. **`service_pedidos_balcao.py`** - Criação de pedidos de balcão
4. **`service_pedido.py`** - Finalização de pedidos de delivery/retirada

## 🔧 Componentes

### Helper de Notificação

**Arquivo:** `app/api/pedidos/utils/pedido_notification_helper.py`

Função assíncrona que:
- Extrai dados do pedido (cliente, itens, valor total, empresa)
- Prepara metadados adicionais (tipo de entrega, número do pedido, status)
- Chama o serviço de notificação para enviar via WebSocket

### Integração nos Serviços

As notificações são enviadas em **background** (usando `asyncio.create_task`) para não bloquear o fluxo principal de criação do pedido. Se houver erro na notificação, ele é logado mas não interrompe a criação do pedido.

## 📡 WebSocket

### Endpoint

```
WS /api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}
```

### Formato da Notificação

Quando um novo pedido é criado, o frontend recebe uma mensagem no formato:

```json
{
  "type": "notification",
  "notification_type": "novo_pedido",
  "title": "Novo Pedido Recebido",
  "message": "Pedido #123 criado - Valor: R$ 45.90",
  "data": {
    "pedido_id": "123",
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

## 🎯 Como Usar no Frontend

### 1. Conectar ao WebSocket

```javascript
// Exemplo usando a classe NotificationWebSocket (já existe em examples/)
const notificationWS = new NotificationWebSocket(userId, empresaId, baseUrl);

// Define callback para receber notificações
notificationWS.onNotification((data) => {
    if (data.notification_type === 'novo_pedido') {
        console.log('🎉 Novo pedido!', data);
        
        // Atualizar interface
        atualizarListaPedidos();
        mostrarNotificacao(data.title, data.message);
    }
});

// Conecta
notificationWS.connect();
```

### 2. URL de Conexão

```
ws://localhost:8000/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}
```

### 3. Processar Notificações

```javascript
// Exemplo de processamento
notificationWS.onNotification((data) => {
    switch(data.notification_type) {
        case 'novo_pedido':
            // Atualizar contador de pedidos
            atualizarContadorPedidos();
            
            // Adicionar pedido à lista
            adicionarPedidoNaLista(data.data);
            
            // Mostrar notificação visual
            mostrarToast(data.title, data.message, 'success');
            break;
            
        case 'pedido_aprovado':
            // Atualizar status do pedido
            atualizarStatusPedido(data.data.pedido_id, 'aprovado');
            break;
            
        // ... outros tipos
    }
});
```

## 📊 Dados Enviados na Notificação

A notificação inclui:

- **pedido_id**: ID do pedido criado
- **cliente**: Dados do cliente (nome, telefone, email)
- **valor_total**: Valor total do pedido
- **itens_count**: Quantidade de itens
- **tipo_entrega**: Tipo do pedido (DELIVERY, MESA, BALCAO, RETIRADA)
- **numero_pedido**: Número do pedido
- **status**: Status inicial do pedido
- **mesa_id** e **mesa_codigo**: Se for pedido de mesa/balcão

## 🔄 Fluxo de Notificação

1. **Pedido Criado**: Um novo pedido é criado em qualquer um dos serviços
2. **Helper Chamado**: O helper `notificar_novo_pedido` é chamado em background
3. **Dados Extraídos**: Dados do pedido são extraídos e formatados
4. **WebSocket**: Notificação é enviada via WebSocket para todos os usuários da empresa conectados
5. **Frontend**: Frontend recebe a notificação e atualiza a interface

## ⚠️ Tratamento de Erros

- Erros na notificação **não interrompem** a criação do pedido
- Erros são logados para debug
- Se não houver usuários conectados, a notificação é silenciosamente ignorada

## 🧪 Testando

### 1. Conectar ao WebSocket

Use um cliente WebSocket (como Postman ou uma ferramenta online) para conectar:

```
ws://localhost:8000/api/notifications/ws/notifications/1?empresa_id=1
```

### 2. Criar um Pedido

Crie um pedido via API (qualquer tipo: delivery, mesa, balcão)

### 3. Verificar Notificação

Você deve receber uma mensagem JSON com os dados do novo pedido.

## 📝 Exemplo Completo Frontend

```javascript
// Inicializar conexão quando a página carregar
document.addEventListener('DOMContentLoaded', () => {
    const userId = getCurrentUserId(); // Sua função para obter user ID
    const empresaId = getCurrentEmpresaId(); // Sua função para obter empresa ID
    
    const ws = new NotificationWebSocket(userId, empresaId);
    
    ws.onNotification((data) => {
        if (data.notification_type === 'novo_pedido') {
            // Atualizar UI
            const pedido = data.data;
            adicionarPedidoNaLista(pedido);
            
            // Mostrar notificação
            showNotification({
                title: data.title,
                message: data.message,
                type: 'success',
                duration: 5000
            });
        }
    });
    
    ws.connect();
});
```

## 🔍 Monitoramento

Você pode verificar estatísticas de conexões WebSocket:

```
GET /api/notifications/ws/connections/stats
```

Retorna:
- Total de usuários conectados
- Total de empresas com conexões
- Total de conexões ativas
- Lista de usuários e empresas conectados


