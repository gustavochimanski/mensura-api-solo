# Sistema de Notificações - Mensura

Sistema completo de notificações em tempo real para o projeto Mensura, implementado com arquitetura desacoplada orientada a eventos.

## 🏗️ Arquitetura

O sistema segue os princípios de **Domain-Driven Design (DDD)** e **Clean Architecture**, com separação clara de responsabilidades:

```
notifications/
├── core/                    # Lógica de domínio e infraestrutura
│   ├── event_bus.py        # Message broker para eventos
│   ├── event_publisher.py  # Publicador de eventos
│   ├── websocket_manager.py # Gerenciador de conexões WebSocket
│   └── notification_system.py # Sistema principal
├── models/                  # Modelos de dados
│   ├── notification.py      # Modelo de notificação
│   ├── event.py           # Modelo de evento
│   └── subscription.py    # Modelo de assinatura
├── schemas/                # Schemas Pydantic
├── repositories/          # Camada de persistência
├── services/              # Lógica de negócio
├── channels/              # Canais de notificação (Strategy Pattern)
├── router/                # Endpoints da API
└── examples/              # Exemplos de uso
```

## 🚀 Funcionalidades

### ✅ Implementadas

- **Sistema de Eventos**: Event-driven architecture com message broker
- **Múltiplos Canais**: Email, WhatsApp, Webhook, Push, In-App
- **Notificações em Tempo Real**: WebSocket para frontend
- **Persistência**: Histórico completo de notificações
- **Configuração por Cliente**: Assinaturas personalizáveis
- **Retry Automático**: Reenvio de notificações falhadas
- **Strategy Pattern**: Canais extensíveis

### 📋 Canais Suportados

1. **Email** (SMTP)
2. **WhatsApp** (Twilio)
3. **Webhook** (HTTP POST)
4. **Push Notification** (Firebase)
5. **In-App** (WebSocket)
6. **SMS** (futuro)
7. **Telegram** (futuro)

## 🔧 Configuração

### 1. Dependências

Adicione ao `requirements.txt`:

```txt
# Notificações
aiohttp==3.8.6
websockets==11.0.3
```

### 2. Variáveis de Ambiente

```env
# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=mensura
RABBITMQ_PASSWORD=mensura123
RABBITMQ_VHOST=/mensura

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=noreply@mensura.com.br
SMTP_PASSWORD=your_password

# WhatsApp (Twilio)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=+1234567890

# Firebase Push
FIREBASE_SERVER_KEY=your_firebase_server_key

# WebSocket
WEBSOCKET_ENABLED=true
```

### 3. RabbitMQ

#### Instalação Local
```bash
# Docker Compose
docker-compose -f docker-compose.rabbitmq.yml up -d

# Ou instalação manual
sudo apt-get install rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server
```

#### Configuração
```bash
# Cria usuário e vhost
sudo rabbitmqctl add_user mensura mensura123
sudo rabbitmqctl add_vhost /mensura
sudo rabbitmqctl set_permissions -p /mensura mensura ".*" ".*" ".*"
sudo rabbitmqctl set_user_tags mensura administrator
```

#### Interface de Gerenciamento
- URL: http://localhost:15672
- Usuário: mensura
- Senha: mensura123

### 4. Banco de Dados

O sistema criará automaticamente as tabelas necessárias:

- `notifications` - Notificações
- `notification_logs` - Logs de notificações
- `events` - Eventos do sistema
- `notification_subscriptions` - Assinaturas

## 📡 Como Usar

### 1. Conectar ao WebSocket (Frontend)

```javascript
const notificationWS = new NotificationWebSocket('user_123', 'empresa_456');
notificationWS.connect();

notificationWS.onNotification((data) => {
    if (data.notification_type === 'novo_pedido') {
        console.log('🎉 Novo pedido!', data);
        // Atualizar interface
    }
});
```

### 2. Notificar Novo Pedido

```python
# No seu serviço de pedidos
from app.api.notifications.services.pedido_notification_service import PedidoNotificationService

service = PedidoNotificationService()

await service.notify_novo_pedido(
    empresa_id="empresa_123",
    pedido_id="pedido_456",
    cliente_data={"nome": "João", "email": "joao@email.com"},
    itens=[{"produto": "Pizza", "quantidade": 2}],
    valor_total=45.90
)
```

### 3. Endpoint REST

```bash
POST /api/notifications/pedidos/novo-pedido
{
    "empresa_id": "empresa_123",
    "pedido_id": "pedido_456",
    "cliente_data": {"nome": "João"},
    "itens": [{"produto": "Pizza", "quantidade": 2}],
    "valor_total": 45.90
}
```

## 🔄 Fluxo de Notificação

1. **Evento Gerado**: Sistema gera evento (ex: pedido_criado)
2. **Event Bus**: Evento é publicado no message broker
3. **Event Processor**: Processa evento e busca assinaturas
4. **Canais**: Envia via canais configurados (email, webhook, etc.)
5. **WebSocket**: Notifica frontend em tempo real
6. **Persistência**: Salva histórico no banco

## 📊 Monitoramento

### Estatísticas de Conexões

```bash
GET /api/notifications/ws/connections/stats
```

### Logs de Notificações

```bash
GET /api/notifications/{notification_id}/logs
```

## 🛠️ Desenvolvimento

### Adicionar Novo Canal

1. Crie classe em `channels/`:
```python
class NovoChannel(BaseNotificationChannel):
    async def send(self, recipient, title, message, metadata):
        # Implementar envio
        pass
```

2. Registre no `ChannelFactory`:
```python
_channels = {
    'novo_canal': NovoChannel,
}
```

### Adicionar Novo Evento

1. Adicione ao enum `EventType`:
```python
NOVO_EVENTO = "novo_evento"
```

2. Crie método no `EventPublisher`:
```python
async def publish_novo_evento(self, empresa_id, data):
    return await self.publish_event(empresa_id, EventType.NOVO_EVENTO, data)
```

## 🧪 Testes

### Teste de Conexão WebSocket

```javascript
// Conecta e testa
const ws = new WebSocket('ws://localhost:8000/api/notifications/ws/notifications/user_123?empresa_id=empresa_456');
ws.onmessage = (event) => console.log('Mensagem:', JSON.parse(event.data));
```

### Teste de Notificação

```bash
curl -X POST "http://localhost:8000/api/notifications/pedidos/novo-pedido" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "empresa_id": "test_empresa",
    "pedido_id": "test_pedido",
    "cliente_data": {"nome": "Teste"},
    "itens": [{"produto": "Teste", "quantidade": 1}],
    "valor_total": 10.00
  }'
```

## 🔒 Segurança

- **Autenticação**: Todos os endpoints requerem token JWT
- **Autorização**: Usuários só veem notificações de sua empresa
- **Rate Limiting**: Controle de taxa para evitar spam
- **Validação**: Todos os dados são validados com Pydantic

## 📈 Performance

- **Processamento Assíncrono**: Notificações não bloqueiam API
- **Retry Inteligente**: Backoff exponencial para falhas
- **Batch Processing**: Processa múltiplas notificações
- **Connection Pooling**: Reutiliza conexões WebSocket

## 🐛 Troubleshooting

### WebSocket não conecta
- Verifique se o usuário está autenticado
- Confirme se o endpoint está correto
- Verifique logs do servidor

### Notificações não chegam
- Verifique se as assinaturas estão ativas
- Confirme configuração dos canais
- Verifique logs de notificação

### Performance lenta
- Ajuste limites de processamento
- Verifique conexões de banco
- Monitore uso de memória

## 📝 Logs

O sistema gera logs detalhados:

```
INFO: WebSocket conectado: usuário user_123, empresa empresa_456
INFO: Evento publicado: pedido_criado - event_789
INFO: Notificação enviada para 3 usuários da empresa empresa_456
```

## 🤝 Contribuição

1. Siga os padrões de código existentes
2. Adicione testes para novas funcionalidades
3. Documente mudanças na API
4. Mantenha compatibilidade com versões anteriores

## 📄 Licença

Sistema proprietário - Mensura Tech
