# Documentação de Autenticação - Frontend

Guia prático para implementar autenticação no frontend. Código pronto para usar.

---

## 📋 Índice

1. [Autenticação Admin (JWT)](#autenticação-admin-jwt)
2. [Autenticação Cliente (Super Token)](#autenticação-cliente-super-token)
3. [Configuração Base](#configuração-base)
4. [Exemplos Completos](#exemplos-completos)

---

## 🔐 Autenticação Admin (JWT)

### Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/token` | Login - retorna JWT token |
| GET | `/api/auth/me` | Obter dados do usuário autenticado |

### 1. Login (Obter Token)

**POST** `/api/auth/token`

```typescript
interface LoginRequest {
  username: string;
  password: string;
}

interface LoginResponse {
  token_type: string; // "bearer"
  type_user: string; // "admin" | "user"
  access_token: string; // JWT token
}

async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch('/api/auth/token', {
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

  return await response.json();
}
```

### 2. Obter Usuário Atual

**GET** `/api/auth/me`

```typescript
interface User {
  id: number;
  username: string;
  type_user: string;
}

async function getCurrentUser(token: string): Promise<User> {
  const response = await fetch('/api/auth/me', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Token inválido ou expirado');
  }

  return await response.json();
}
```

### 3. Helper para Requisições Autenticadas

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
    // Token expirado ou inválido
    localStorage.removeItem('access_token');
    window.location.href = '/login';
    throw new Error('Não autenticado');
  }
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro na requisição');
  }
  
  return response.json();
}

// Uso:
const pedidos = await fetchWithAuth('/api/pedidos/admin');
```

---

## 👤 Autenticação Cliente (Super Token)

### Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/cadastros/client/clientes/novo-dispositivo` | Obter/regenerar super_token |
| GET | `/api/auth/client/me` | Obter dados do cliente autenticado |

### 1. Obter Super Token (Novo Dispositivo)

**POST** `/api/cadastros/client/clientes/novo-dispositivo`

```typescript
interface NovoDispositivoRequest {
  telefone: string;
}

interface NovoDispositivoResponse {
  super_token: string;
  nome: string;
  telefone: string;
}

async function obterSuperToken(telefone: string): Promise<NovoDispositivoResponse> {
  const response = await fetch('/api/cadastros/client/clientes/novo-dispositivo', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ telefone }),
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Telefone não cadastrado');
    }
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao obter token');
  }

  return await response.json();
}
```

### 2. Obter Cliente Atual

**GET** `/api/auth/client/me`

```typescript
interface Cliente {
  nome: string;
  super_token: string;
  telefone: string;
}

async function getCurrentCliente(superToken: string): Promise<Cliente> {
  const response = await fetch('/api/auth/client/me', {
    headers: {
      'X-Super-Token': superToken,
    },
  });

  if (!response.ok) {
    throw new Error('Token inválido');
  }

  return await response.json();
}
```

### 3. Helper para Requisições de Cliente

```typescript
async function fetchWithSuperToken(url: string, options: RequestInit = {}) {
  const superToken = localStorage.getItem('super_token');
  
  if (!superToken) {
    throw new Error('Super token não encontrado');
  }
  
  const headers = {
    'Content-Type': 'application/json',
    'X-Super-Token': superToken,
    ...options.headers,
  };
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  if (response.status === 401) {
    // Token inválido
    localStorage.removeItem('super_token');
    window.location.href = '/login-cliente';
    throw new Error('Token inválido');
  }
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro na requisição');
  }
  
  return response.json();
}

// Uso:
const enderecos = await fetchWithSuperToken('/api/cadastros/client/enderecos');
```

---

## ⚙️ Configuração Base

### Axios Interceptor (Admin)

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
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
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### Axios Interceptor (Cliente)

```typescript
import axios from 'axios';

const apiCliente = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
});

// Interceptor para adicionar super_token em todas as requisições
apiCliente.interceptors.request.use((config) => {
  const superToken = localStorage.getItem('super_token');
  if (superToken) {
    config.headers['X-Super-Token'] = superToken;
  }
  return config;
});

// Interceptor para tratar erros de autenticação
apiCliente.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token inválido
      localStorage.removeItem('super_token');
      window.location.href = '/login-cliente';
    }
    return Promise.reject(error);
  }
);

export default apiCliente;
```

---

## 💻 Exemplos Completos

### React Context - Autenticação Admin

```typescript
// contexts/AuthContext.tsx
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
    typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      verifyToken();
    } else {
      setLoading(false);
    }
  }, []);

  async function verifyToken() {
    if (!token) return;

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
    } catch (error) {
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
      const error = await response.json();
      throw new Error(error.detail || 'Credenciais inválidas');
    }

    const data = await response.json();
    setToken(data.access_token);
    localStorage.setItem('access_token', data.access_token);
    
    // Busca dados completos do usuário
    await verifyToken();
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

### Protected Route Component (Admin)

```typescript
// components/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

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

### Login Component (Admin)

```typescript
// components/Login.tsx
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Erro ao fazer login');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <button type="submit" disabled={loading}>
        {loading ? 'Entrando...' : 'Entrar'}
      </button>
    </form>
  );
}
```

### React Context - Autenticação Cliente

```typescript
// contexts/ClienteAuthContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';

interface Cliente {
  nome: string;
  super_token: string;
  telefone: string;
}

interface ClienteAuthContextType {
  cliente: Cliente | null;
  superToken: string | null;
  obterToken: (telefone: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  loading: boolean;
}

const ClienteAuthContext = createContext<ClienteAuthContextType | undefined>(undefined);

export function ClienteAuthProvider({ children }: { children: React.ReactNode }) {
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [superToken, setSuperToken] = useState<string | null>(
    typeof window !== 'undefined' ? localStorage.getItem('super_token') : null
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (superToken) {
      verifyCliente();
    } else {
      setLoading(false);
    }
  }, []);

  async function verifyCliente() {
    if (!superToken) return;

    try {
      const response = await fetch('/api/auth/client/me', {
        headers: {
          'X-Super-Token': superToken,
        },
      });

      if (response.ok) {
        const clienteData = await response.json();
        setCliente(clienteData);
      } else {
        logout();
      }
    } catch (error) {
      logout();
    } finally {
      setLoading(false);
    }
  }

  async function obterToken(telefone: string) {
    const response = await fetch('/api/cadastros/client/clientes/novo-dispositivo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ telefone }),
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Telefone não cadastrado');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Erro ao obter token');
    }

    const data = await response.json();
    setSuperToken(data.super_token);
    setCliente({
      nome: data.nome,
      super_token: data.super_token,
      telefone: data.telefone,
    });
    localStorage.setItem('super_token', data.super_token);
    
    // Busca dados completos do cliente
    await verifyCliente();
  }

  function logout() {
    setSuperToken(null);
    setCliente(null);
    localStorage.removeItem('super_token');
  }

  return (
    <ClienteAuthContext.Provider
      value={{
        cliente,
        superToken,
        obterToken,
        logout,
        isAuthenticated: !!cliente && !!superToken,
        loading,
      }}
    >
      {children}
    </ClienteAuthContext.Provider>
  );
}

export function useClienteAuth() {
  const context = useContext(ClienteAuthContext);
  if (!context) {
    throw new Error('useClienteAuth deve ser usado dentro de ClienteAuthProvider');
  }
  return context;
}
```

### Login Cliente Component

```typescript
// components/LoginCliente.tsx
import { useState } from 'react';
import { useClienteAuth } from '../contexts/ClienteAuthContext';
import { useNavigate } from 'react-router-dom';

export function LoginCliente() {
  const [telefone, setTelefone] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { obterToken } = useClienteAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await obterToken(telefone);
      navigate('/cliente/dashboard');
    } catch (err: any) {
      setError(err.message || 'Erro ao fazer login');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="tel"
        placeholder="Telefone (ex: 11999999999)"
        value={telefone}
        onChange={(e) => setTelefone(e.target.value)}
        required
      />
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <button type="submit" disabled={loading}>
        {loading ? 'Entrando...' : 'Entrar'}
      </button>
    </form>
  );
}
```

### App.tsx (Exemplo de Uso)

```typescript
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ClienteAuthProvider } from './contexts/ClienteAuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './components/Login';
import { LoginCliente } from './components/LoginCliente';
import Dashboard from './pages/Dashboard';
import ClienteDashboard from './pages/ClienteDashboard';

function App() {
  return (
    <AuthProvider>
      <ClienteAuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Rotas Admin */}
            <Route path="/login" element={<Login />} />
            <Route
              path="/admin/*"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />

            {/* Rotas Cliente */}
            <Route path="/login-cliente" element={<LoginCliente />} />
            <Route path="/cliente/*" element={<ClienteDashboard />} />
          </Routes>
        </BrowserRouter>
      </ClienteAuthProvider>
    </AuthProvider>
  );
}

export default App;
```

### Hook para Requisições (Admin)

```typescript
// hooks/useApi.ts
import { useAuth } from '../contexts/AuthContext';

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

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erro na requisição');
    }

    return response.json();
  }

  return { fetchWithAuth };
}
```

### Hook para Requisições (Cliente)

```typescript
// hooks/useClienteApi.ts
import { useClienteAuth } from '../contexts/ClienteAuthContext';

export function useClienteApi() {
  const { superToken } = useClienteAuth();

  async function fetchWithSuperToken(url: string, options: RequestInit = {}) {
    if (!superToken) {
      throw new Error('Super token não encontrado');
    }

    const headers = {
      'Content-Type': 'application/json',
      'X-Super-Token': superToken,
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      throw new Error('Token inválido');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erro na requisição');
    }

    return response.json();
  }

  return { fetchWithSuperToken };
}
```

---

## 📝 Resumo Rápido

### Admin (JWT)
- **Login**: `POST /api/auth/token` com `{ username, password }`
- **Header**: `Authorization: Bearer <token>`
- **Token expira**: 90 minutos
- **Verificar usuário**: `GET /api/auth/me`

### Cliente (Super Token)
- **Obter token**: `POST /api/cadastros/client/clientes/novo-dispositivo` com `{ telefone }`
- **Header**: `X-Super-Token: <token>`
- **Token não expira**: Permanente (pode regenerar)
- **Verificar cliente**: `GET /api/auth/client/me`

---

## ⚠️ Tratamento de Erros

### Erro 401 (Não Autenticado)
- **Admin**: Token expirado ou inválido → redirecionar para `/login`
- **Cliente**: Token inválido → redirecionar para `/login-cliente`

### Erro 403 (Acesso Negado)
- **Admin**: Usuário não é admin → mostrar mensagem e redirecionar

### Erro 404 (Telefone não cadastrado)
- **Cliente**: Telefone não encontrado → mostrar mensagem de erro

---

**Última atualização**: 2026-01-25
