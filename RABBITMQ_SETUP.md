# Como rodar o RabbitMQ

## Opção 1: Docker Compose (Recomendado)

1. **Inicie o RabbitMQ:**
```bash
docker-compose up -d rabbitmq
```

2. **Verifique se está rodando:**
```bash
docker-compose ps
```

3. **Acesse a interface de gerenciamento:**
   - URL: http://localhost:15672
   - Usuário: `mensura`
   - Senha: `mensura123`

4. **Parar o RabbitMQ:**
```bash
docker-compose down
```

## Opção 2: Docker direto (sem docker-compose)

```bash
docker run -d \
  --name teste2_rabbitmq \
  --hostname teste2_rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=mensura \
  -e RABBITMQ_DEFAULT_PASS=mensura123 \
  -e RABBITMQ_DEFAULT_VHOST=/mensura \
  rabbitmq:3-management-alpine
```

## Opção 3: Instalação local (Linux/Mac)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install rabbitmq-server

# Mac (com Homebrew)
brew install rabbitmq
brew services start rabbitmq

# Configurar usuário e virtual host
sudo rabbitmqctl add_user mensura mensura123
sudo rabbitmqctl add_vhost /mensura
sudo rabbitmqctl set_permissions -p /mensura mensura ".*" ".*" ".*"
sudo rabbitmqctl set_user_tags mensura administrator
```

## Configuração do Virtual Host

O sistema está configurado para usar o virtual host `/mensura`. Se você precisar criar manualmente:

```bash
# Via Management UI
1. Acesse http://localhost:15672
2. Vá em "Admin" > "Virtual Hosts"
3. Adicione `/mensura`

# Via CLI
docker exec -it teste2_rabbitmq rabbitmqctl add_vhost /mensura
docker exec -it teste2_rabbitmq rabbitmqctl set_permissions -p /mensura mensura ".*" ".*" ".*"
```

## Variáveis de Ambiente

Certifique-se de que seu arquivo `.env` contém:

```env
RABBITMQ_HOST=teste2_rabbitmq  # ou localhost se rodar localmente
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=mensura
RABBITMQ_PASSWORD=mensura123
RABBITMQ_VHOST=/mensura
```

## Testando a Conexão

Após iniciar o RabbitMQ, você pode testar a conexão através do endpoint:

```bash
curl http://localhost:8000/api/notifications/rabbitmq/status
```

## Troubleshooting

### Erro de conexão
- Verifique se o container está rodando: `docker ps | grep rabbitmq`
- Verifique os logs: `docker-compose logs rabbitmq`
- Verifique se a porta 5672 não está em uso: `netstat -an | grep 5672`

### Virtual Host não encontrado
- O virtual host `/mensura` será criado automaticamente na primeira conexão
- Ou crie manualmente via Management UI ou CLI

### Permissões
- O usuário `mensura` precisa ter permissões no virtual host `/mensura`
- Isso é configurado automaticamente no docker-compose

