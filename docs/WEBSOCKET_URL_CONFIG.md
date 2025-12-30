# 🌐 Configuração de URL do WebSocket

Este documento explica como o frontend descobre a URL do backend para conectar ao WebSocket.

## 📍 Como Funciona

**O backend NÃO precisa "pegar" o IP/domínio do frontend.** 

Na verdade, é o **contrário**: o **frontend precisa saber a URL do backend** para se conectar.

## 🔄 Fluxo de Conexão

```
Frontend (sabe a URL do backend) 
    ↓
Conecta ao WebSocket do backend
    ↓
Backend aceita a conexão
    ↓
Conexão estabelecida
```

## 🏠 Funciona Localmente E Na Nuvem

### ✅ Local (Desenvolvimento)

```javascript
// Frontend rodando em localhost:3000
// Backend rodando em localhost:8000

const wsUrl = 'ws://localhost:8000/api/notifications/ws/notifications/1?empresa_id=1';
const ws = new WebSocket(wsUrl);
```

### ✅ Nuvem (Produção)

```javascript
// Frontend rodando em https://app.seudominio.com
// Backend rodando em https://api.seudominio.com

const wsUrl = 'wss://api.seudominio.com/api/notifications/ws/notifications/1?empresa_id=1';
const ws = new WebSocket(wsUrl);
```

### ✅ IP Local (Rede Local)

```javascript
// Backend rodando em 192.168.1.100:8000

const wsUrl = 'ws://192.168.1.100:8000/api/notifications/ws/notifications/1?empresa_id=1';
const ws = new WebSocket(wsUrl);
```

## 🔧 Como o Frontend Descobre a URL

### Opção 1: Variável de Ambiente (Recomendado)

```javascript
// .env do frontend
REACT_APP_API_URL=ws://localhost:8000
// ou
REACT_APP_API_URL=wss://api.seudominio.com

// No código
const API_URL = process.env.REACT_APP_API_URL || 'ws://localhost:8000';
const wsUrl = `${API_URL}/api/notifications/ws/notifications/${userId}?empresa_id=${empresaId}`;
```

### Opção 2: Configuração Dinâmica

```javascript
// Detectar automaticamente baseado na URL atual
function getWebSocketUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = window.location.port ? `:${window.location.port}` : '';
    
    // Se estiver em produção, usar domínio da API
    if (host.includes('seudominio.com')) {
        return `${protocol}//api.seudominio.com/api/notifications/ws/notifications`;
    }
    
    // Desenvolvimento local
    return `${protocol}//${host}${port}/api/notifications/ws/notifications`;
}

const wsUrl = `${getWebSocketUrl()}/${userId}?empresa_id=${empresaId}`;
```

### Opção 3: Endpoint de Configuração

```javascript
// Backend retorna a URL do WebSocket
async function getWebSocketConfig() {
    const response = await fetch('/api/config/websocket');
    const config = await response.json();
    return config.ws_url;
}

const config = await getWebSocketConfig();
const wsUrl = `${config}/${userId}?empresa_id=${empresaId}`;
```

## 🔒 Protocolos WebSocket

- **`ws://`** - WebSocket não criptografado (HTTP)
  - Usado em desenvolvimento local
  - Exemplo: `ws://localhost:8000`

- **`wss://`** - WebSocket criptografado (HTTPS)
  - Usado em produção
  - Exemplo: `wss://api.seudominio.com`

## 📝 Exemplo Completo

```javascript
class NotificationWebSocket {
    constructor(userId, empresaId) {
        this.userId = userId;
        this.empresaId = empresaId;
        
        // Descobre a URL do backend
        this.baseUrl = this.getBackendUrl();
    }
    
    getBackendUrl() {
        // Opção 1: Variável de ambiente
        if (process.env.REACT_APP_WS_URL) {
            return process.env.REACT_APP_WS_URL;
        }
        
        // Opção 2: Detectar automaticamente
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        
        // Se estiver em produção
        if (host.includes('seudominio.com')) {
            return `${protocol}//api.seudominio.com`;
        }
        
        // Desenvolvimento local
        return `${protocol}//${host}:8000`;
    }
    
    connect() {
        const wsUrl = `${this.baseUrl}/api/notifications/ws/notifications/${this.userId}?empresa_id=${this.empresaId}`;
        console.log('Conectando ao WebSocket:', wsUrl);
        
        this.ws = new WebSocket(wsUrl);
        // ... resto do código
    }
}
```

## 🌍 CORS e WebSocket

O CORS já está configurado no backend. WebSocket tem menos restrições que HTTP, mas ainda precisa:

1. **Origem permitida** (configurado no CORS)
2. **Protocolo correto** (ws:// ou wss://)
3. **URL correta** do backend

### Configuração Atual do CORS

```python
# app/main.py
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "false")

# Permite todas as origens se CORS_ALLOW_ALL=true
# Ou apenas as origens listadas em CORS_ORIGINS
```

## 🐛 Troubleshooting

### Problema: "Connection refused"

**Causa:** URL do backend está incorreta ou backend não está rodando.

**Solução:**
- Verifique se o backend está rodando
- Verifique se a URL está correta
- Verifique se a porta está correta

### Problema: "Failed to connect"

**Causa:** Protocolo incorreto ou CORS bloqueando.

**Solução:**
- Use `ws://` para HTTP e `wss://` para HTTPS
- Verifique configuração de CORS no backend
- Verifique se a origem do frontend está permitida

### Problema: Funciona local mas não na nuvem

**Causa:** URL hardcoded ou variável de ambiente não configurada.

**Solução:**
- Use variáveis de ambiente
- Configure diferentes URLs para dev/prod
- Verifique se está usando `wss://` em produção

## 📋 Checklist

- [ ] Frontend tem variável de ambiente para URL do backend
- [ ] URL muda automaticamente entre dev/prod
- [ ] Usa `ws://` em desenvolvimento
- [ ] Usa `wss://` em produção
- [ ] CORS está configurado no backend
- [ ] Testou localmente
- [ ] Testou na nuvem

## 🔗 Referências

- [Guia de Implementação Frontend](./WEBSOCKET_NOTIFICACOES_FRONTEND.md)
- [Debug de Conexões](./WEBSOCKET_DEBUG.md)

