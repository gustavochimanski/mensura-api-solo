# Documentação — Autenticação Admin

Esta documentação descreve **como implementar autenticação de administrador** no frontend para acessar rotas protegidas da API.

---

## 1) Visão Geral

O sistema utiliza **JWT (JSON Web Tokens)** para autenticação de usuários admin. O fluxo funciona da seguinte forma:

1. **Login**: Frontend envia credenciais (username + password)
2. **Token**: Backend retorna um JWT access token
3. **Requisições**: Frontend inclui o token no header `Authorization: Bearer <token>`
4. **Validação**: Backend valida o token e verifica se o usuário é admin (`type_user='admin'`)

### Características

- **Tipo de Token**: JWT (HS256)
- **Validade**: 90 minutos (configurável via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Formato**: `Bearer <token>`
- **Validação**: Token é validado em cada requisição protegida
- **Permissões**: Apenas usuários com `type_user='admin'` podem acessar rotas admin

---

## 2) Endpoints de Autenticação

### 2.1) Login (Obter Token)

**POST** `/api/auth/token`

Autentica um usuário e retorna o JWT access token.

#### Request Body

```json
{
  "username": "admin",
  "password": "senha123"
}
```

#### Response (200 OK)

```json
{
  "token_type": "bearer",
  "type_user": "admin",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Campos da Resposta

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `token_type` | `string` | Sempre `"bearer"` |
| `type_user` | `string` | Tipo do usuário: `"admin"` ou `"user"` |
| `access_token` | `string` | JWT token para usar em requisições autenticadas |

#### Erros

**401 Unauthorized** - Credenciais inválidas
```json
{
  "detail": "Credenciais inválidas"
}
```

### 2.2) Obter Usuário Atual

**GET** `/api/auth/me`

Retorna os dados do usuário autenticado baseado no token JWT.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response (200 OK)

```json
{
  "id": 1,
  "username": "admin",
  "type_user": "admin"
}
```

#### Erros

**401 Unauthorized** - Token inválido ou ausente
```json
{
  "detail": "Não autenticado Access"
}
```

---

## 3) Como Proteger Rotas no Frontend

### 3.1) Adicionar Token nas Requisições

Todas as requisições para rotas admin devem incluir o token no header `Authorization`:

```typescript
const response = await fetch('/api/pedidos/admin', {
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
});
```

### 3.2) Interceptor HTTP (Axios)

Se estiver usando Axios, configure um interceptor:

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://api.exemplo.com',
});

// Interceptor para adicionar token em todas as requisições
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para tratar erros de autenticação
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expirado ou inválido
      localStorage.removeItem('access_token');
      // Redirecionar para login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### 3.3) Fetch com Helper

```typescript
async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = localStorage.getItem('access_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  if (response.status === 401) {
    // Token expirado
    localStorage.removeItem('access_token');
    throw new Error('Não autenticado');
  }
  
  return response;
}
```

---

## 4) Fluxo Completo de Autenticação

### 4.1) Login

```typescript
async function login(username: string, password: string) {
  const response = await fetch('/api/auth/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  });
  
  if (!response.ok) {
    throw new Error('Credenciais inválidas');
  }
  
  const data = await response.json();
  
  // Armazena o token
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('type_user', data.type_user);
  
  return data;
}
```

### 4.2) Verificar Autenticação

```typescript
async function checkAuth(): Promise<boolean> {
  const token = localStorage.getItem('access_token');
  if (!token) return false;
  
  try {
    const response = await fetch('/api/auth/me', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (response.ok) {
      const user = await response.json();
      // Verifica se é admin
      return user.type_user === 'admin';
    }
    
    return false;
  } catch (error) {
    return false;
  }
}
```

### 4.3) Logout

```typescript
function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('type_user');
  // Redirecionar para login
  window.location.href = '/login';
}
```

---

## 5) Implementação com React

### 5.1) Context de Autenticação

```typescript
// AuthContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  id: number;
  username: string;
  type_user: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isAdmin: boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('access_token')
  );
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Verifica autenticação ao carregar
    if (token) {
      checkAuth();
    } else {
      setLoading(false);
    }
  }, []);
  
  async function checkAuth() {
    try {
      const response = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // Token inválido
        setToken(null);
        localStorage.removeItem('access_token');
      }
    } catch (error) {
      setToken(null);
      localStorage.removeItem('access_token');
    } finally {
      setLoading(false);
    }
  }
  
  async function login(username: string, password: string) {
    const response = await fetch('/api/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    
    if (!response.ok) {
      throw new Error('Credenciais inválidas');
    }
    
    const data = await response.json();
    setToken(data.access_token);
    setUser({ id: 0, username, type_user: data.type_user });
    localStorage.setItem('access_token', data.access_token);
    
    // Busca dados completos do usuário
    await checkAuth();
  }
  
  function logout() {
    setToken(null);
    setUser(null);
    localStorage.removeItem('access_token');
  }
  
  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        isAuthenticated: !!user && !!token,
        isAdmin: user?.type_user === 'admin',
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider');
  }
  return context;
}
```

### 5.2) Protected Route Component

```typescript
// ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  
  if (loading) {
    return <div>Carregando...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  if (!isAdmin) {
    return <Navigate to="/unauthorized" replace />;
  }
  
  return <>{children}</>;
}
```

### 5.3) Uso no App

```typescript
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import { ProtectedRoute } from './ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

### 5.4) Hook para Requisições Autenticadas

```typescript
// useApi.ts
import { useAuth } from './AuthContext';

export function useApi() {
  const { token } = useAuth();
  
  async function fetchWithAuth(url: string, options: RequestInit = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    if (response.status === 401) {
      throw new Error('Não autenticado');
    }
    
    return response;
  }
  
  return { fetchWithAuth };
}
```

---

## 6) Tratamento de Erros

### 6.1) Token Expirado

Quando o token expira (após 90 minutos), o backend retorna **401 Unauthorized**. O frontend deve:

1. **Detectar o erro 401**
2. **Limpar o token** do storage
3. **Redirecionar para login**

```typescript
// Interceptor ou wrapper de fetch
if (response.status === 401) {
  localStorage.removeItem('access_token');
  // Opção 1: Redirecionar
  window.location.href = '/login';
  // Opção 2: Disparar evento para o contexto
  // authContext.logout();
}
```

### 6.2) Acesso Negado (403)

Quando um usuário não-admin tenta acessar uma rota admin:

```json
{
  "detail": "Você não tem permissão para acessar este recurso"
}
```

O frontend deve mostrar uma mensagem apropriada e redirecionar.

### 6.3) Token Inválido

Se o token estiver malformado ou inválido, o backend retorna **401**. Trate da mesma forma que token expirado.

---

## 7) Rotas Protegidas no Backend

### 7.1) Como o Backend Protege Rotas

O backend utiliza **dependencies** do FastAPI para proteger rotas:

```python
from app.core.admin_dependencies import require_admin

router = APIRouter(
    prefix="/api/pedidos/admin",
    dependencies=[Depends(require_admin)],  # Protege todas as rotas
)

# Ou em rotas específicas:
@router.get("/pedidos")
def list_pedidos(
    current_user: UserModel = Depends(require_admin)
):
    # current_user já está validado como admin
    ...
```

### 7.2) Validação no Backend

1. **Extrai o token** do header `Authorization: Bearer <token>`
2. **Decodifica o JWT** usando `SECRET_KEY`
3. **Busca o usuário** no banco pelo ID do token
4. **Verifica `type_user`** - deve ser `'admin'`
5. **Retorna 401** se token inválido ou ausente
6. **Retorna 403** se usuário não é admin

---

## 8) Exemplos de Uso

### 8.1) Listar Pedidos (Admin)

```typescript
async function listPedidos() {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('/api/pedidos/admin', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    throw new Error('Erro ao listar pedidos');
  }
  
  return response.json();
}
```

### 8.2) Criar Usuário (Admin)

```typescript
async function createUser(userData: any) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('/api/mensura/admin/usuarios', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(userData),
  });
  
  if (!response.ok) {
    throw new Error('Erro ao criar usuário');
  }
  
  return response.json();
}
```

### 8.3) Com React Query

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import { useAuth } from './AuthContext';

function usePedidos() {
  const { token } = useAuth();
  
  return useQuery({
    queryKey: ['pedidos'],
    queryFn: async () => {
      const response = await fetch('/api/pedidos/admin', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) throw new Error('Erro ao buscar pedidos');
      return response.json();
    },
    enabled: !!token, // Só executa se tiver token
  });
}
```

---

## 9) Segurança

### 9.1) Armazenamento do Token

**⚠️ IMPORTANTE**: O token JWT contém informações sensíveis. Recomendações:

- **LocalStorage**: Funciona, mas vulnerável a XSS
- **SessionStorage**: Mais seguro (limpa ao fechar aba)
- **HttpOnly Cookies**: Mais seguro ainda (não acessível via JavaScript)

**Recomendação atual**: LocalStorage é aceitável se:
- O site usa HTTPS
- Implementa proteção contra XSS
- Valida e sanitiza inputs

### 9.2) Renovação de Token

O token expira em **90 minutos**. Para melhor UX:

1. **Monitorar expiração**: Verificar tempo restante antes de fazer requisições
2. **Refresh automático**: Implementar refresh token (se disponível)
3. **Renovar proativamente**: Fazer novo login antes de expirar

```typescript
// Verificar se token está próximo de expirar
function isTokenExpiringSoon(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // Converter para ms
    const now = Date.now();
    const timeUntilExpiry = exp - now;
    
    // Considera "próximo de expirar" se faltam menos de 5 minutos
    return timeUntilExpiry < 5 * 60 * 1000;
  } catch {
    return true; // Se não conseguir decodificar, assume que está expirado
  }
}
```

### 9.3) HTTPS

**SEMPRE** use HTTPS em produção. Tokens JWT transmitidos via HTTP podem ser interceptados.

---

## 10) Checklist de Implementação

- [ ] Criar tela de login
- [ ] Implementar função de login (POST `/api/auth/token`)
- [ ] Armazenar token após login bem-sucedido
- [ ] Adicionar header `Authorization: Bearer <token>` em todas as requisições admin
- [ ] Implementar interceptor/helper para adicionar token automaticamente
- [ ] Tratar erro 401 (token expirado/inválido) - redirecionar para login
- [ ] Tratar erro 403 (acesso negado) - mostrar mensagem apropriada
- [ ] Criar componente/hook para verificar autenticação
- [ ] Proteger rotas admin no frontend (ProtectedRoute)
- [ ] Implementar logout (limpar token e redirecionar)
- [ ] Adicionar verificação de token ao carregar a aplicação
- [ ] Implementar renovação proativa de token (opcional)

---

## 11) Exemplo Completo (React + TypeScript)

```typescript
// hooks/useAuth.ts
import { useState, useEffect } from 'react';

interface User {
  id: number;
  username: string;
  type_user: string;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('access_token')
  );
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    if (token) {
      verifyToken();
    } else {
      setLoading(false);
    }
  }, [token]);
  
  async function verifyToken() {
    try {
      const response = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        logout();
      }
    } catch {
      logout();
    } finally {
      setLoading(false);
    }
  }
  
  async function login(username: string, password: string) {
    const response = await fetch('/api/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    
    if (!response.ok) {
      throw new Error('Credenciais inválidas');
    }
    
    const data = await response.json();
    setToken(data.access_token);
    localStorage.setItem('access_token', data.access_token);
    await verifyToken();
  }
  
  function logout() {
    setToken(null);
    setUser(null);
    localStorage.removeItem('access_token');
  }
  
  return {
    user,
    token,
    login,
    logout,
    isAuthenticated: !!user && !!token,
    isAdmin: user?.type_user === 'admin',
    loading,
  };
}

// components/Login.tsx
import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    
    try {
      await login(username, password);
      // Redirecionar para dashboard
      window.location.href = '/dashboard';
    } catch (err) {
      setError('Credenciais inválidas');
    }
  }
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {error && <div>{error}</div>}
      <button type="submit">Login</button>
    </form>
  );
}

// utils/api.ts
export async function apiRequest(url: string, options: RequestInit = {}) {
  const token = localStorage.getItem('access_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  if (response.status === 401) {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
    throw new Error('Não autenticado');
  }
  
  if (!response.ok) {
    throw new Error(`Erro: ${response.statusText}`);
  }
  
  return response.json();
}
```

---

## 12) Referências

- **Endpoint de Login**: `POST /api/auth/token`
- **Endpoint de Usuário Atual**: `GET /api/auth/me`
- **Dependencies do Backend**: `app/core/admin_dependencies.py`
- **Security Utils**: `app/core/security.py`
- **Auth Controller**: `app/api/auth/auth_controller.py`

---

## 13) Notas Importantes

1. **Token expira em 90 minutos** - implemente renovação proativa ou avise o usuário
2. **Apenas usuários com `type_user='admin'`** podem acessar rotas admin
3. **Token deve ser incluído em TODAS as requisições** para rotas protegidas
4. **Use HTTPS em produção** para proteger o token durante a transmissão
5. **Trate erros 401 e 403** adequadamente no frontend
6. **Não exponha o `SECRET_KEY`** - ele é usado apenas no backend
7. **O token JWT contém o ID do usuário** no campo `sub` (subject)

---

**Última atualização**: 2026-01-24
