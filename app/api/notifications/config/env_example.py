"""
Exemplo de configuração de variáveis de ambiente para o sistema de notificações
Copie este arquivo para .env na raiz do projeto e configure as variáveis
"""

# Configurações do Banco de Dados
DATABASE_URL = "postgresql://user:password@localhost:5432/mensura_db"
DATABASE = "mensura_db"
USER = "postgres"
PASSWORD = "your_password"
HOST = "localhost"
PORT = 5432

# Configurações do RabbitMQ
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "guest"
RABBITMQ_PASSWORD = "guest"
RABBITMQ_VHOST = "/"

# Configurações de Email (SendGrid)
SENDGRID_API_KEY = "your_sendgrid_api_key"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"

# Configurações do WhatsApp (Twilio)
TWILIO_ACCOUNT_SID = "your_twilio_account_sid"
TWILIO_AUTH_TOKEN = "your_twilio_auth_token"
TWILIO_WHATSAPP_FROM = "+14155238886"

# Configurações do Firebase (Push Notifications)
FIREBASE_SERVER_KEY = "your_firebase_server_key"
FIREBASE_PROJECT_ID = "your_firebase_project_id"

# Configurações de Webhook
WEBHOOK_SECRET = "your_webhook_secret"
WEBHOOK_TIMEOUT = 30

# Configurações de Logging
LOG_LEVEL = "INFO"
LOG_FILE = "logs/app.log"

# Configurações de Segurança
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configurações do Sistema
DEBUG = True
ENVIRONMENT = "development"

# Configurações do Chatbot (IA)
GROQ_API_KEY = "your_groq_api_key_here"

# Configurações do Ngrok (para webhooks do WhatsApp)
NGROK_AUTHTOKEN = "your_ngrok_authtoken_here"
NGROK_DOMAIN = "your-static-domain.ngrok-free.dev"