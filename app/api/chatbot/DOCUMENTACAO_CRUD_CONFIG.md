# Documentação - CRUD de Configurações do Chatbot

## 📋 Visão Geral

Este documento descreve os endpoints disponíveis para gerenciar as configurações do chatbot por empresa. Cada empresa pode ter uma única configuração que define o comportamento do chatbot, incluindo nome, personalidade, e se aceita fazer pedidos pelo WhatsApp ou apenas redireciona para um link.

## 🔐 Autenticação

Todos os endpoints requerem autenticação via Bearer Token (JWT). O token deve ser enviado no header:

```
Authorization: Bearer {seu_token_jwt}
```

## 📍 Base URL

```
/api/chatbot/admin/config
```

---

## 📝 Modelo de Dados

### ChatbotConfigResponse

```typescript
interface ChatbotConfigResponse {
  id: number;
  empresa_id: number;
  nome: string;
  personalidade: string | null;
  aceita_pedidos_whatsapp: boolean;
  mensagem_boas_vindas: string | null;
  mensagem_redirecionamento: string | null;
  ativo: boolean;
  created_at: string; // ISO 8601 datetime
  updated_at: string; // ISO 8601 datetime
  empresa_nome: string | null; // Nome da empresa (opcional na resposta)
}
```

**Nota:** O link de redirecionamento é obtido automaticamente do campo `cardapio_link` da tabela `empresas`. Não é necessário configurá-lo separadamente.

### ChatbotConfigCreate

```typescript
interface ChatbotConfigCreate {
  empresa_id: number; // Obrigatório, > 0
  nome: string; // Obrigatório, 1-100 caracteres
  personalidade?: string | null; // Opcional
  aceita_pedidos_whatsapp?: boolean; // Padrão: true
  mensagem_boas_vindas?: string | null; // Opcional
  mensagem_redirecionamento?: string | null; // Opcional - mensagem quando redireciona para o cardápio
  ativo?: boolean; // Padrão: true
}
```

### ChatbotConfigUpdate

```typescript
interface ChatbotConfigUpdate {
  nome?: string; // Opcional, 1-100 caracteres
  personalidade?: string | null; // Opcional
  aceita_pedidos_whatsapp?: boolean; // Opcional
  mensagem_boas_vindas?: string | null; // Opcional
  mensagem_redirecionamento?: string | null; // Opcional
  ativo?: boolean; // Opcional
}
```

---

## 🚀 Endpoints

### 1. Criar Configuração

Cria uma nova configuração do chatbot para uma empresa.

**Endpoint:** `POST /api/chatbot/admin/config/`

**Request Body:**
```json
{
  "empresa_id": 1,
  "nome": "Assistente Virtual",
  "personalidade": "Você é um atendente amigável e prestativo que ajuda clientes a fazerem pedidos.",
  "aceita_pedidos_whatsapp": true,
  "mensagem_boas_vindas": "Olá! Bem-vindo ao nosso atendimento. Como posso ajudar?",
  "mensagem_redirecionamento": null,
  "ativo": true
}
```

**Response 201 Created:**
```json
{
  "id": 1,
  "empresa_id": 1,
  "nome": "Assistente Virtual",
  "personalidade": "Você é um atendente amigável e prestativo que ajuda clientes a fazerem pedidos.",
  "aceita_pedidos_whatsapp": true,
  "mensagem_boas_vindas": "Olá! Bem-vindo ao nosso atendimento. Como posso ajudar?",
  "mensagem_redirecionamento": null,
  "ativo": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "empresa_nome": "Restaurante Exemplo"
}
```

**Erros Possíveis:**
- `400 Bad Request`: Empresa não encontrada ou já existe configuração para esta empresa
- `401 Unauthorized`: Token inválido ou ausente
- `422 Unprocessable Entity`: Dados inválidos (validação)

**Exemplo com cURL:**
```bash
curl -X POST "https://api.exemplo.com/api/chatbot/admin/config/" \
  -H "Authorization: Bearer seu_token_jwt" \
  -H "Content-Type: application/json" \
  -d '{
    "empresa_id": 1,
    "nome": "Assistente Virtual",
    "personalidade": "Você é um atendente amigável e prestativo.",
    "aceita_pedidos_whatsapp": true,
    "ativo": true
  }'
```

---

### 2. Listar Configurações

Lista todas as configurações do chatbot com filtros opcionais.

**Endpoint:** `GET /api/chatbot/admin/config/`

**Query Parameters:**
- `empresa_id` (opcional, integer > 0): Filtrar por empresa
- `ativo` (opcional, boolean): Filtrar por status ativo/inativo
- `skip` (opcional, integer >= 0): Número de registros para pular (padrão: 0)
- `limit` (opcional, integer 1-500): Limite de registros (padrão: 100)

**Exemplo de Request:**
```
GET /api/chatbot/admin/config/?empresa_id=1&ativo=true&skip=0&limit=10
```

**Response 200 OK:**
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Assistente Virtual",
    "personalidade": "Você é um atendente amigável...",
    "aceita_pedidos_whatsapp": true,
    "mensagem_boas_vindas": "Olá! Bem-vindo...",
    "mensagem_redirecionamento": null,
    "ativo": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "empresa_nome": "Restaurante Exemplo"
  }
]
```

**Exemplo com cURL:**
```bash
curl -X GET "https://api.exemplo.com/api/chatbot/admin/config/?empresa_id=1&ativo=true" \
  -H "Authorization: Bearer seu_token_jwt"
```

---

### 3. Buscar Configuração por Empresa

Busca a configuração do chatbot de uma empresa específica.

**Endpoint:** `GET /api/chatbot/admin/config/empresa/{empresa_id}`

**Path Parameters:**
- `empresa_id` (obrigatório, integer > 0): ID da empresa

**Response 200 OK:**
```json
{
  "id": 1,
  "empresa_id": 1,
  "nome": "Assistente Virtual",
  "personalidade": "Você é um atendente amigável...",
  "aceita_pedidos_whatsapp": true,
  "link_redirecionamento": null,
  "mensagem_boas_vindas": "Olá! Bem-vindo...",
  "mensagem_redirecionamento": null,
  "ativo": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "empresa_nome": "Restaurante Exemplo"
}
```

**Response 200 OK (sem configuração):**
```json
null
```

**Erros Possíveis:**
- `401 Unauthorized`: Token inválido ou ausente
- `404 Not Found`: Empresa não encontrada

**Exemplo com cURL:**
```bash
curl -X GET "https://api.exemplo.com/api/chatbot/admin/config/empresa/1" \
  -H "Authorization: Bearer seu_token_jwt"
```

---

### 4. Buscar Configuração por ID

Busca uma configuração específica por seu ID.

**Endpoint:** `GET /api/chatbot/admin/config/{config_id}`

**Path Parameters:**
- `config_id` (obrigatório, integer > 0): ID da configuração

**Response 200 OK:**
```json
{
  "id": 1,
  "empresa_id": 1,
  "nome": "Assistente Virtual",
  "personalidade": "Você é um atendente amigável...",
  "aceita_pedidos_whatsapp": true,
  "link_redirecionamento": null,
  "mensagem_boas_vindas": "Olá! Bem-vindo...",
  "mensagem_redirecionamento": null,
  "ativo": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "empresa_nome": "Restaurante Exemplo"
}
```

**Erros Possíveis:**
- `401 Unauthorized`: Token inválido ou ausente
- `404 Not Found`: Configuração não encontrada

**Exemplo com cURL:**
```bash
curl -X GET "https://api.exemplo.com/api/chatbot/admin/config/1" \
  -H "Authorization: Bearer seu_token_jwt"
```

---

### 5. Atualizar Configuração

Atualiza uma configuração existente. Todos os campos são opcionais - apenas os campos fornecidos serão atualizados.

**Endpoint:** `PUT /api/chatbot/admin/config/{config_id}`

**Path Parameters:**
- `config_id` (obrigatório, integer > 0): ID da configuração

**Request Body (exemplo parcial):**
```json
{
  "nome": "Novo Nome do Chatbot",
  "aceita_pedidos_whatsapp": false,
  "mensagem_redirecionamento": "Por favor, acesse nosso cardápio online pelo link acima."
}
```

**Response 200 OK:**
```json
{
  "id": 1,
  "empresa_id": 1,
  "nome": "Novo Nome do Chatbot",
  "personalidade": "Você é um atendente amigável...",
  "aceita_pedidos_whatsapp": false,
  "mensagem_boas_vindas": "Olá! Bem-vindo...",
  "mensagem_redirecionamento": "Por favor, acesse nosso cardápio online pelo link acima.",
  "ativo": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z",
  "empresa_nome": "Restaurante Exemplo"
}
```

**Erros Possíveis:**
- `401 Unauthorized`: Token inválido ou ausente
- `404 Not Found`: Configuração não encontrada
- `422 Unprocessable Entity`: Dados inválidos (validação)

**Exemplo com cURL:**
```bash
curl -X PUT "https://api.exemplo.com/api/chatbot/admin/config/1" \
  -H "Authorization: Bearer seu_token_jwt" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Novo Nome",
    "aceita_pedidos_whatsapp": false,
    "mensagem_redirecionamento": "Acesse nosso cardápio online!"
  }'
```

---

### 6. Deletar Configuração

Remove uma configuração (soft delete - marca como inativo).

**Endpoint:** `DELETE /api/chatbot/admin/config/{config_id}`

**Path Parameters:**
- `config_id` (obrigatório, integer > 0): ID da configuração

**Response 204 No Content:**
```
(sem corpo de resposta)
```

**Erros Possíveis:**
- `401 Unauthorized`: Token inválido ou ausente
- `404 Not Found`: Configuração não encontrada

**Exemplo com cURL:**
```bash
curl -X DELETE "https://api.exemplo.com/api/chatbot/admin/config/1" \
  -H "Authorization: Bearer seu_token_jwt"
```

---

## ⚠️ Regras de Negócio

### Validações Importantes

1. **Unicidade por Empresa**: Cada empresa pode ter apenas UMA configuração. Tentar criar uma segunda configuração para a mesma empresa resultará em erro 400.

2. **Link do Cardápio**: O link de redirecionamento é obtido automaticamente do campo `cardapio_link` da tabela `empresas`. Não é necessário configurá-lo na configuração do chatbot.

3. **Aceita Pedidos pelo WhatsApp**: 
   - Se `aceita_pedidos_whatsapp = true`, o chatbot permite fazer pedidos diretamente pelo WhatsApp
   - Se `aceita_pedidos_whatsapp = false`, o chatbot apenas redireciona para o cardápio online (usando o `cardapio_link` da empresa)

4. **Soft Delete**: A exclusão não remove o registro do banco, apenas marca como `ativo = false`. O registro permanece para histórico.

5. **Empresa Deve Existir**: A empresa informada deve existir no sistema, caso contrário retorna 404.

---

## 📋 Exemplos de Uso no Frontend

### React/TypeScript Example

```typescript
// types.ts
export interface ChatbotConfig {
  id: number;
  empresa_id: number;
  nome: string;
  personalidade: string | null;
  aceita_pedidos_whatsapp: boolean;
  mensagem_boas_vindas: string | null;
  mensagem_redirecionamento: string | null;
  ativo: boolean;
  created_at: string;
  updated_at: string;
  empresa_nome?: string | null;
}

export interface ChatbotConfigCreate {
  empresa_id: number;
  nome: string;
  personalidade?: string | null;
  aceita_pedidos_whatsapp?: boolean;
  mensagem_boas_vindas?: string | null;
  mensagem_redirecionamento?: string | null;
  ativo?: boolean;
}

export interface ChatbotConfigUpdate {
  nome?: string;
  personalidade?: string | null;
  aceita_pedidos_whatsapp?: boolean;
  mensagem_boas_vindas?: string | null;
  mensagem_redirecionamento?: string | null;
  ativo?: boolean;
}

// api.ts
const API_BASE_URL = 'https://api.exemplo.com';
const getAuthHeaders = () => ({
  'Authorization': `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json',
});

export const chatbotConfigApi = {
  // Criar configuração
  create: async (data: ChatbotConfigCreate): Promise<ChatbotConfig> => {
    const response = await fetch(`${API_BASE_URL}/api/chatbot/admin/config/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Erro ao criar configuração');
    return response.json();
  },

  // Listar configurações
  list: async (filters?: {
    empresa_id?: number;
    ativo?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<ChatbotConfig[]> => {
    const params = new URLSearchParams();
    if (filters?.empresa_id) params.append('empresa_id', filters.empresa_id.toString());
    if (filters?.ativo !== undefined) params.append('ativo', filters.ativo.toString());
    if (filters?.skip) params.append('skip', filters.skip.toString());
    if (filters?.limit) params.append('limit', filters.limit.toString());

    const response = await fetch(
      `${API_BASE_URL}/api/chatbot/admin/config/?${params.toString()}`,
      { headers: getAuthHeaders() }
    );
    if (!response.ok) throw new Error('Erro ao listar configurações');
    return response.json();
  },

  // Buscar por empresa
  getByEmpresa: async (empresa_id: number): Promise<ChatbotConfig | null> => {
    const response = await fetch(
      `${API_BASE_URL}/api/chatbot/admin/config/empresa/${empresa_id}`,
      { headers: getAuthHeaders() }
    );
    if (!response.ok) throw new Error('Erro ao buscar configuração');
    return response.json();
  },

  // Buscar por ID
  getById: async (config_id: number): Promise<ChatbotConfig> => {
    const response = await fetch(
      `${API_BASE_URL}/api/chatbot/admin/config/${config_id}`,
      { headers: getAuthHeaders() }
    );
    if (!response.ok) throw new Error('Erro ao buscar configuração');
    return response.json();
  },

  // Atualizar configuração
  update: async (config_id: number, data: ChatbotConfigUpdate): Promise<ChatbotConfig> => {
    const response = await fetch(
      `${API_BASE_URL}/api/chatbot/admin/config/${config_id}`,
      {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      }
    );
    if (!response.ok) throw new Error('Erro ao atualizar configuração');
    return response.json();
  },

  // Deletar configuração
  delete: async (config_id: number): Promise<void> => {
    const response = await fetch(
      `${API_BASE_URL}/api/chatbot/admin/config/${config_id}`,
      {
        method: 'DELETE',
        headers: getAuthHeaders(),
      }
    );
    if (!response.ok) throw new Error('Erro ao deletar configuração');
  },
};
```

### Exemplo de Componente React

```tsx
import React, { useState, useEffect } from 'react';
import { chatbotConfigApi, ChatbotConfig, ChatbotConfigCreate } from './api';

const ChatbotConfigForm: React.FC<{ empresaId: number }> = ({ empresaId }) => {
  const [config, setConfig] = useState<ChatbotConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState<ChatbotConfigCreate>({
    empresa_id: empresaId,
    nome: 'Assistente Virtual',
    aceita_pedidos_whatsapp: true,
    ativo: true,
  });

  useEffect(() => {
    loadConfig();
  }, [empresaId]);

  const loadConfig = async () => {
    try {
      const existing = await chatbotConfigApi.getByEmpresa(empresaId);
      if (existing) {
        setConfig(existing);
        setFormData({
          empresa_id: empresaId,
          nome: existing.nome,
          personalidade: existing.personalidade,
          aceita_pedidos_whatsapp: existing.aceita_pedidos_whatsapp,
          mensagem_boas_vindas: existing.mensagem_boas_vindas,
          mensagem_redirecionamento: existing.mensagem_redirecionamento,
          ativo: existing.ativo,
        });
      }
    } catch (error) {
      console.error('Erro ao carregar configuração:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (config) {
        // Atualizar
        const updated = await chatbotConfigApi.update(config.id, formData);
        setConfig(updated);
        alert('Configuração atualizada com sucesso!');
      } else {
        // Criar
        const created = await chatbotConfigApi.create(formData);
        setConfig(created);
        alert('Configuração criada com sucesso!');
      }
    } catch (error) {
      alert('Erro ao salvar configuração');
      console.error(error);
    }
  };

  if (loading) return <div>Carregando...</div>;

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Nome do Chatbot:</label>
        <input
          type="text"
          value={formData.nome}
          onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
          required
          maxLength={100}
        />
      </div>

      <div>
        <label>Personalidade:</label>
        <textarea
          value={formData.personalidade || ''}
          onChange={(e) => setFormData({ ...formData, personalidade: e.target.value })}
          rows={4}
        />
      </div>

      <div>
        <label>
          <input
            type="checkbox"
            checked={formData.aceita_pedidos_whatsapp}
            onChange={(e) => setFormData({ ...formData, aceita_pedidos_whatsapp: e.target.checked })}
          />
          Aceita pedidos pelo WhatsApp
        </label>
      </div>

      {!formData.aceita_pedidos_whatsapp && (
        <div>
          <label>Mensagem de Redirecionamento:</label>
          <textarea
            value={formData.mensagem_redirecionamento || ''}
            onChange={(e) => setFormData({ ...formData, mensagem_redirecionamento: e.target.value })}
            rows={2}
            placeholder="Mensagem exibida ao redirecionar para o cardápio online"
          />
          <small>O link do cardápio é obtido automaticamente da configuração da empresa.</small>
        </div>
      )}

      <div>
        <label>Mensagem de Boas-vindas:</label>
        <textarea
          value={formData.mensagem_boas_vindas || ''}
          onChange={(e) => setFormData({ ...formData, mensagem_boas_vindas: e.target.value })}
          rows={2}
        />
      </div>

      <div>
        <label>Mensagem de Redirecionamento:</label>
        <textarea
          value={formData.mensagem_redirecionamento || ''}
          onChange={(e) => setFormData({ ...formData, mensagem_redirecionamento: e.target.value })}
          rows={2}
        />
      </div>

      <div>
        <label>
          <input
            type="checkbox"
            checked={formData.ativo}
            onChange={(e) => setFormData({ ...formData, ativo: e.target.checked })}
          />
          Ativo
        </label>
      </div>

      <button type="submit">
        {config ? 'Atualizar' : 'Criar'} Configuração
      </button>
    </form>
  );
};

export default ChatbotConfigForm;
```

---

## 🔍 Códigos de Status HTTP

| Código | Significado | Quando Ocorre |
|--------|-------------|---------------|
| 200 | OK | Requisição bem-sucedida (GET, PUT) |
| 201 | Created | Configuração criada com sucesso (POST) |
| 204 | No Content | Configuração deletada com sucesso (DELETE) |
| 400 | Bad Request | Dados inválidos ou regra de negócio violada |
| 401 | Unauthorized | Token ausente ou inválido |
| 403 | Forbidden | Sem permissão para acessar o recurso |
| 404 | Not Found | Recurso não encontrado |
| 422 | Unprocessable Entity | Erro de validação dos dados |

---

## 📌 Notas Importantes

1. **Timezone**: Todas as datas são retornadas em formato ISO 8601 (UTC).

2. **Limites de Caracteres**:
   - `nome`: 1-100 caracteres
   - `personalidade`, `mensagem_boas_vindas`, `mensagem_redirecionamento`: sem limite (mas use com moderação)

3. **Link do Cardápio**: O link de redirecionamento é obtido automaticamente do campo `cardapio_link` da tabela `empresas`. Certifique-se de que a empresa tenha este campo configurado.

4. **Paginação**: Use os parâmetros `skip` e `limit` para paginar resultados grandes.

5. **Filtros**: Combine filtros na listagem para buscar configurações específicas.

---

## 🐛 Tratamento de Erros

Sempre trate os possíveis erros nas requisições:

```typescript
try {
  const config = await chatbotConfigApi.create(data);
  // Sucesso
} catch (error) {
  if (error.response?.status === 400) {
    // Dados inválidos ou regra de negócio violada
    console.error('Erro de validação:', error.response.data);
  } else if (error.response?.status === 401) {
    // Token inválido - redirecionar para login
    window.location.href = '/login';
  } else if (error.response?.status === 404) {
    // Recurso não encontrado
    console.error('Configuração não encontrada');
  } else {
    // Erro genérico
    console.error('Erro ao processar requisição:', error);
  }
}
```

---

## 📞 Suporte

Em caso de dúvidas ou problemas, consulte a documentação do Swagger em:
```
/swagger
```

Ou entre em contato com a equipe de desenvolvimento.
