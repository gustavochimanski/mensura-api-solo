# Documentação - Autenticação Admin nos Endpoints de Impressora

## 📋 Visão Geral

**IMPORTANTE**: A partir desta atualização, **todos os endpoints de impressora** (exceto os de autenticação) agora **requerem autenticação via token admin** (JWT Bearer Token).

Esta mudança foi implementada para aumentar a segurança e garantir que apenas usuários autenticados possam acessar os dados de pedidos e realizar operações de impressão.

---

## 🔄 O Que Mudou?

### Antes (Endpoints Públicos)

Os endpoints de impressora eram **públicos** e não requeriam autenticação:

```typescript
// ❌ ANTES - Sem autenticação
const response = await fetch(
  `${baseUrl}/api/cardapio/printer/pedidos-pendentes?empresa_id=1`
);
```

### Agora (Requerem Token Admin)

Todos os endpoints de impressora agora **requerem** o header `Authorization: Bearer <token>`:

```typescript
// ✅ AGORA - Com autenticação admin
const response = await fetch(
  `${baseUrl}/api/cardapio/printer/pedidos-pendentes?empresa_id=1`,
  {
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json',
    },
  }
);
```

---

## 📝 Endpoints Afetados

| Método | Endpoint | Status Anterior | Status Atual |
|--------|----------|-----------------|--------------|
| **GET** | `/api/cardapio/printer/pedidos-pendentes` | Público | **Requer Admin Token** |
| **PUT** | `/api/cardapio/printer/marcar-impresso/{pedido_id}` | Público | **Requer Admin Token** |
| **GET** | `/api/delivery/printer/pedidos-pendentes` | Público | **Requer Admin Token** |
| **GET** | `/api/mensura/impressoras/empresa/{empresa_id}` | Público | **Requer Admin Token** |

### Endpoints de Autenticação (NÃO mudaram)

| Método | Endpoint | Status |
|--------|----------|--------|
| **POST** | `/api/auth/token` | Público (login) |
| **GET** | `/api/auth/me` | Requer Admin Token |

---

## 🔐 Como Obter o Token Admin

### 1. Login (Obter Token)

**POST** `/api/auth/token`

```typescript
interface LoginRequest {
  username: string;
  password: string;
}

interface LoginResponse {
  token_type: string; // "Bearer"
  type_user: string; // "admin"
  access_token: string; // JWT token
}

async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${baseUrl}/api/auth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Credenciais inválidas');
  }

  const data = await response.json();
  
  // Salvar token no localStorage ou gerenciador de estado
  localStorage.setItem('access_token', data.access_token);
  
  return data;
}
```

### 2. Verificar Token Válido

**GET** `/api/auth/me`

```typescript
async function verificarToken(token: string): Promise<boolean> {
  try {
    const response = await fetch(`${baseUrl}/api/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.ok;
  } catch {
    return false;
  }
}
```

---

## 💻 Implementação no Frontend

### Opção 1: Helper Function (Recomendado)

Crie uma função helper que adiciona automaticamente o token em todas as requisições:

```typescript
/**
 * Helper para fazer requisições autenticadas aos endpoints de impressora
 */
async function fetchImpressora(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    throw new Error('Token de autenticação não encontrado. Faça login primeiro.');
  }

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers,
  };

  const response = await fetch(`${baseUrl}${endpoint}`, {
    ...options,
    headers,
  });

  // Tratamento de erros de autenticação
  if (response.status === 401) {
    // Token expirado ou inválido
    localStorage.removeItem('access_token');
    throw new Error('Sessão expirada. Faça login novamente.');
  }

  if (response.status === 403) {
    throw new Error('Você não tem permissão para acessar este recurso.');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
    throw new Error(error.detail || 'Erro na requisição');
  }

  return response;
}
```

### Opção 2: Classe/Service (Para projetos maiores)

```typescript
class ImpressoraService {
  private baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async getAuthHeaders(): Promise<HeadersInit> {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      throw new Error('Token de autenticação não encontrado. Faça login primeiro.');
    }

    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
  }

  /**
   * Lista pedidos pendentes de impressão
   */
  async listarPedidosPendentes(
    empresaId: number,
    limite: number = 50
  ): Promise<PedidosPendentesPrinterResponse> {
    const headers = await this.getAuthHeaders();
    
    const response = await fetch(
      `${this.baseUrl}/api/cardapio/printer/pedidos-pendentes?empresa_id=${empresaId}&limite=${limite}`,
      {
        method: 'GET',
        headers,
      }
    );

    if (response.status === 401) {
      localStorage.removeItem('access_token');
      throw new Error('Sessão expirada. Faça login novamente.');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erro ao listar pedidos pendentes');
    }

    return response.json();
  }

  /**
   * Marca um pedido como impresso
   */
  async marcarPedidoImpresso(
    pedidoId: number,
    tipoPedido: 'delivery' | 'mesa' | 'balcao'
  ): Promise<RespostaImpressaoPrinter> {
    const headers = await this.getAuthHeaders();
    
    const response = await fetch(
      `${this.baseUrl}/api/cardapio/printer/marcar-impresso/${pedidoId}?tipo_pedido=${tipoPedido}`,
      {
        method: 'PUT',
        headers,
      }
    );

    if (response.status === 401) {
      localStorage.removeItem('access_token');
      throw new Error('Sessão expirada. Faça login novamente.');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erro ao marcar pedido como impresso');
    }

    return response.json();
  }

  /**
   * Fallback: Lista pedidos pendentes via endpoint de delivery
   */
  async listarPedidosPendentesDelivery(
    empresaId: number,
    limite: number = 50
  ): Promise<PedidosPendentesPrinterResponse> {
    const headers = await this.getAuthHeaders();
    
    const response = await fetch(
      `${this.baseUrl}/api/delivery/printer/pedidos-pendentes?empresa_id=${empresaId}&limite=${limite}`,
      {
        method: 'GET',
        headers,
      }
    );

    if (response.status === 401) {
      localStorage.removeItem('access_token');
      throw new Error('Sessão expirada. Faça login novamente.');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erro ao listar pedidos pendentes');
    }

    return response.json();
  }

  /**
   * Obtém configuração de impressora da empresa
   */
  async obterConfiguracaoImpressora(empresaId: number): Promise<any> {
    const headers = await this.getAuthHeaders();
    
    const response = await fetch(
      `${this.baseUrl}/api/mensura/impressoras/empresa/${empresaId}`,
      {
        method: 'GET',
        headers,
      }
    );

    if (response.status === 401) {
      localStorage.removeItem('access_token');
      throw new Error('Sessão expirada. Faça login novamente.');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erro ao obter configuração de impressora');
    }

    return response.json();
  }
}

// Uso:
const impressoraService = new ImpressoraService('http://localhost:8001');

// Exemplo de uso
try {
  const pedidos = await impressoraService.listarPedidosPendentes(1);
  console.log('Pedidos pendentes:', pedidos);
} catch (error) {
  console.error('Erro:', error.message);
  // Redirecionar para login se necessário
  if (error.message.includes('Sessão expirada')) {
    window.location.href = '/login';
  }
}
```

---

## 🔄 Migração do Código Existente

### Exemplo: Atualizar chamada de pedidos pendentes

**ANTES:**
```typescript
// ❌ Código antigo (sem autenticação)
async function buscarPedidosPendentes(empresaId: number) {
  const response = await fetch(
    `${baseUrl}/api/cardapio/printer/pedidos-pendentes?empresa_id=${empresaId}`
  );
  return response.json();
}
```

**DEPOIS:**
```typescript
// ✅ Código atualizado (com autenticação)
async function buscarPedidosPendentes(empresaId: number) {
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    throw new Error('Faça login primeiro');
  }

  const response = await fetch(
    `${baseUrl}/api/cardapio/printer/pedidos-pendentes?empresa_id=${empresaId}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    }
  );

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    throw new Error('Sessão expirada');
  }

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao buscar pedidos');
  }

  return response.json();
}
```

---

## ⚠️ Tratamento de Erros

### Códigos de Status HTTP

| Status | Significado | Ação Recomendada |
|--------|-------------|------------------|
| **200** | Sucesso | Processar resposta normalmente |
| **401** | Não autenticado / Token inválido/expirado | Remover token, redirecionar para login |
| **403** | Sem permissão | Verificar se o usuário tem permissão admin |
| **404** | Endpoint não encontrado | Verificar URL e parâmetros |
| **500** | Erro interno do servidor | Logar erro, exibir mensagem ao usuário |

### Exemplo de Tratamento Completo

```typescript
async function fazerRequisicaoAutenticada(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    // Redirecionar para login
    window.location.href = '/login';
    throw new Error('Token não encontrado');
  }

  try {
    const response = await fetch(`${baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    // Tratamento específico por status
    if (response.status === 401) {
      // Token expirado ou inválido
      localStorage.removeItem('access_token');
      window.location.href = '/login?expired=true';
      throw new Error('Sessão expirada');
    }

    if (response.status === 403) {
      // Sem permissão
      throw new Error('Você não tem permissão para acessar este recurso');
    }

    if (!response.ok) {
      // Outros erros
      const error = await response.json().catch(() => ({ 
        detail: `Erro HTTP ${response.status}` 
      }));
      throw new Error(error.detail || 'Erro na requisição');
    }

    return await response.json();
  } catch (error) {
    // Erro de rede ou parsing
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Erro de conexão. Verifique sua internet.');
    }
    throw error;
  }
}
```

---

## 🔄 Fluxo de Autenticação Completo

### 1. Inicialização da Aplicação

```typescript
// Ao iniciar a aplicação, verificar se há token válido
async function inicializarApp() {
  const token = localStorage.getItem('access_token');
  
  if (token) {
    // Verificar se o token ainda é válido
    const isValid = await verificarToken(token);
    
    if (!isValid) {
      // Token inválido, remover e redirecionar
      localStorage.removeItem('access_token');
      window.location.href = '/login';
      return;
    }
    
    // Token válido, continuar
    console.log('Usuário autenticado');
  } else {
    // Sem token, redirecionar para login
    window.location.href = '/login';
  }
}
```

### 2. Login e Armazenamento do Token

```typescript
async function fazerLogin(username: string, password: string) {
  try {
    const response = await login(username, password);
    
    // Salvar token
    localStorage.setItem('access_token', response.access_token);
    
    // Verificar tipo de usuário (deve ser 'admin' para impressora)
    if (response.type_user !== 'admin') {
      throw new Error('Acesso restrito a administradores');
    }
    
    // Redirecionar para a aplicação
    window.location.href = '/dashboard';
  } catch (error) {
    console.error('Erro no login:', error);
    alert(error.message || 'Erro ao fazer login');
  }
}
```

### 3. Interceptor para Renovação Automática (Opcional)

```typescript
// Interceptar requisições para renovar token automaticamente
let isRefreshing = false;

async function fetchWithAutoRefresh(endpoint: string, options: RequestInit = {}) {
  let token = localStorage.getItem('access_token');
  
  if (!token) {
    window.location.href = '/login';
    throw new Error('Token não encontrado');
  }

  const response = await fetch(`${baseUrl}${endpoint}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  // Se token expirou, tentar renovar (se implementado no backend)
  if (response.status === 401 && !isRefreshing) {
    isRefreshing = true;
    
    // Tentar renovar token (se o backend suportar)
    // Se não suportar, apenas redirecionar para login
    localStorage.removeItem('access_token');
    window.location.href = '/login?expired=true';
    
    isRefreshing = false;
    throw new Error('Sessão expirada');
  }

  return response;
}
```

---

## 📋 Checklist de Migração

Use este checklist para garantir que todas as mudanças foram implementadas:

- [ ] **Autenticação**: Implementar login e armazenamento de token
- [ ] **Helper Function**: Criar função helper para requisições autenticadas
- [ ] **GET pedidos-pendentes**: Atualizar para incluir header Authorization
- [ ] **PUT marcar-impresso**: Atualizar para incluir header Authorization
- [ ] **GET delivery/pedidos-pendentes**: Atualizar fallback para incluir header Authorization
- [ ] **GET impressoras/empresa**: Atualizar para incluir header Authorization
- [ ] **Tratamento de 401**: Implementar redirecionamento para login quando token expirar
- [ ] **Tratamento de 403**: Implementar mensagem de erro para falta de permissão
- [ ] **Validação de Token**: Verificar token válido ao iniciar aplicação
- [ ] **Testes**: Testar todos os endpoints com token válido e inválido

---

## 🧪 Exemplos de Teste

### Teste 1: Requisição com Token Válido

```typescript
// 1. Fazer login
const loginResponse = await login('admin', 'senha123');
console.log('Token obtido:', loginResponse.access_token);

// 2. Fazer requisição autenticada
const pedidos = await fetchImpressora(
  '/api/cardapio/printer/pedidos-pendentes?empresa_id=1'
);
console.log('Pedidos:', pedidos);
```

### Teste 2: Requisição sem Token

```typescript
// Remover token
localStorage.removeItem('access_token');

// Tentar fazer requisição (deve falhar)
try {
  const pedidos = await fetchImpressora(
    '/api/cardapio/printer/pedidos-pendentes?empresa_id=1'
  );
} catch (error) {
  console.log('Erro esperado:', error.message);
  // Deve mostrar: "Token de autenticação não encontrado"
}
```

### Teste 3: Requisição com Token Expirado

```typescript
// Usar token expirado
localStorage.setItem('access_token', 'token_expirado_123');

try {
  const pedidos = await fetchImpressora(
    '/api/cardapio/printer/pedidos-pendentes?empresa_id=1'
  );
} catch (error) {
  console.log('Erro esperado:', error.message);
  // Deve mostrar: "Sessão expirada. Faça login novamente."
  // E redirecionar para /login
}
```

---

## 📚 Referências

- [Documentação de Autenticação Completa](./../auth/docs/DOCUMENTACAO_AUTENTICACAO_FRONTEND.md)
- [Documentação CRUD de Pedidos](./../pedidos/DOCUMENTACAO_CRUD_PEDIDOS.md)

---

## ❓ Dúvidas Frequentes

### 1. O token expira? Quanto tempo?

Sim, o token JWT tem validade de **30 minutos** por padrão. Após expirar, é necessário fazer login novamente.

### 2. Posso usar o mesmo token para múltiplas requisições?

Sim, o mesmo token pode ser usado para todas as requisições enquanto estiver válido.

### 3. O que acontece se eu não enviar o token?

A API retornará **401 Unauthorized** com a mensagem "Não autenticado Access".

### 4. Preciso fazer login toda vez que abrir a aplicação?

Não necessariamente. Se o token estiver salvo no `localStorage` e ainda for válido, você pode continuar usando. Apenas quando o token expirar é necessário fazer login novamente.

### 5. Posso usar tokens de usuários não-admin?

Não. Os endpoints de impressora requerem especificamente `type_user='admin'`. Usuários com outros tipos receberão **403 Forbidden**.

---

## 📞 Suporte

Em caso de dúvidas ou problemas na implementação, consulte:
- Logs do backend para detalhes de erros
- Documentação de autenticação completa
- Equipe de desenvolvimento

---

**Última atualização**: Janeiro 2025
