# Guia de Configuração do Sistema de Notificações

## 1. Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```bash
# Configurações do Banco de Dados
DATABASE_URL=postgresql://user:password@localhost:5432/mensura_db
DATABASE=mensura_db
USER=postgres
PASSWORD=your_password
HOST=localhost
PORT=5432

# Configurações do RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/

# Configurações de Email (SendGrid)
SENDGRID_API_KEY=your_sendgrid_api_key
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Configurações do WhatsApp (Twilio)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=+14155238886

# Configurações do Firebase (Push Notifications)
FIREBASE_SERVER_KEY=your_firebase_server_key
FIREBASE_PROJECT_ID=your_firebase_project_id

# Configurações de Webhook
WEBHOOK_SECRET=your_webhook_secret
WEBHOOK_TIMEOUT=30

# Configurações de Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Configurações de Segurança
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Configurações do Sistema
DEBUG=True
ENVIRONMENT=development
```

## 2. Configuração do PostgreSQL

1. Instale o PostgreSQL
2. Crie um banco de dados para o projeto
3. Configure as variáveis de ambiente do banco

## 3. Configuração do RabbitMQ

### Opção 1: Docker Compose (Recomendado)
```bash
# Execute o comando abaixo na raiz do projeto
docker-compose -f docker-compose.rabbitmq.yml up -d
```

### Opção 2: Instalação Local
1. Instale o RabbitMQ
2. Configure as variáveis de ambiente
3. Inicie o serviço

## 4. Executar Migrações

```bash
# Execute as migrações do banco de dados
alembic upgrade head
```

## 5. Testar o Sistema

```bash
# Inicie o servidor
python -m uvicorn app.main:app --reload

# Teste os endpoints
curl http://localhost:8000/api/notifications/health
```

## 6. Configuração dos Canais

### Email
- Configure SMTP ou SendGrid
- Defina as credenciais nas variáveis de ambiente

### WhatsApp
- Crie uma conta no Twilio
- Configure as credenciais nas variáveis de ambiente

### Push Notifications
- Configure o Firebase
- Adicione as chaves nas variáveis de ambiente

### Webhooks
- Configure os endpoints de destino
- Defina os segredos de autenticação

## 7. Monitoramento

- Acesse o RabbitMQ Management: http://localhost:15672
- Verifique os logs em `logs/app.log`
- Use os endpoints de health check para monitorar o sistema
