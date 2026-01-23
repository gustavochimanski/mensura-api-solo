# Documentação Completa - CRUD de Usuários do Sistema (Frontend)

Esta documentação descreve **todos os endpoints CRUD** para manipulação de usuários do sistema.

---

## 📋 Índice

1. [Base URL e Autenticação](#base-url-e-autenticação)
2. [Estrutura de Dados](#estrutura-de-dados)
3. [Endpoints CRUD](#endpoints-crud)
4. [Validações e Regras de Negócio](#validações-e-regras-de-negócio)
5. [Códigos de Status HTTP](#códigos-de-status-http)
6. [Exemplos Práticos](#exemplos-práticos)
7. [Tratamento de Erros](#tratamento-de-erros)

---

## 🔐 Base URL e Autenticação

### Base URL

**Prefixo Admin**: `/api/mensura/admin/usuarios`

**Exemplos:**
- **Local**: `http://localhost:8000/api/mensura/admin/usuarios`
- **Produção**: `https://seu-dominio.com/api/mensura/admin/usuarios`

### Autenticação

**Todos os endpoints**: Requerem autenticação de **administrador** via `require_admin` (token JWT no header `Authorization: Bearer <token>`)

**Headers obrigatórios:**
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**⚠️ Importante**: Apenas usuários com `type_user = "admin"` podem acessar estes endpoints.

---

## 📊 Estrutura de Dados

### UserCreate (Criar Usuário)

```typescript
interface UserCreate {
  username: string;              // Obrigatório - Nome de usuário único
  password: string;               // Obrigatório - Senha do usuário
  type_user: string;             // Obrigatório - Tipo: "admin" | "cliente" | "funcionario"
  empresa_ids?: number[];         // Opcional - Lista de IDs das empresas vinculadas
}
```

### UserUpdate (Atualizar Usuário)

```typescript
interface UserUpdate {
  username?: string;              // Opcional - Novo nome de usuário
  password?: string;               // Opcional - Nova senha (será hasheada)
  type_user?: string;             // Opcional - Novo tipo: "admin" | "cliente" | "funcionario"
  empresa_ids?: number[];         // Opcional - Nova lista de IDs das empresas
}
```

### UserResponse (Resposta)

```typescript
interface UserResponse {
  id: number;                     // ID único do usuário
  username: string;               // Nome de usuário
  type_user: string;              // Tipo: "admin" | "cliente" | "funcionario"
  empresa_ids?: number[];         // IDs das empresas vinculadas (se houver)
}
```

**Observação**: A senha (`hashed_password`) **nunca** é retornada nas respostas por questões de segurança.

---

## 🚀 Endpoints CRUD

### 1. Criar Usuário (CREATE)

Cria um novo usuário no sistema.

**Endpoint:**
```
POST /api/mensura/admin/usuarios
```

**Headers:**
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Body Request:**
```json
{
  "username": "joao.silva",
  "password": "senhaSegura123",
  "type_user": "funcionario",
  "empresa_ids": [1, 2]
}
```

**Campos Obrigatórios:**
- `username` ✅ (string, único)
- `password` ✅ (string)
- `type_user` ✅ (string: "admin" | "cliente" | "funcionario")

**Campos Opcionais:**
- `empresa_ids` (array de números)

**Response (200 OK):**
```json
{
  "id": 10,
  "username": "joao.silva",
  "type_user": "funcionario",
  "empresa_ids": [1, 2]
}
```

**Validações:**
- `username` deve ser único (não pode existir outro usuário com o mesmo username)
- `type_user` deve ser exatamente: `"admin"`, `"cliente"` ou `"funcionario"`
- Todos os `empresa_ids` devem existir no banco de dados
- Se algum `empresa_id` não existir, retorna erro 400

**Erros Possíveis:**
- `400 Bad Request`: "Já existe um usuário com este username"
- `400 Bad Request`: "Tipo de usuário inválido"
- `400 Bad Request`: "Uma ou mais empresas não foram encontradas"
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Usuário não é administrador

---

### 2. Listar Usuários (READ)

Lista todos os usuários do sistema com paginação.

**Endpoint:**
```
GET /api/mensura/admin/usuarios
```

**Query Parameters:**
- `skip` (integer, padrão: 0): Número de registros a pular (para paginação)
- `limit` (integer, padrão: 100): Número máximo de registros a retornar

**Exemplo:**
```
GET /api/mensura/admin/usuarios?skip=0&limit=50
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "username": "admin",
    "type_user": "admin",
    "empresa_ids": null
  },
  {
    "id": 2,
    "username": "joao.silva",
    "type_user": "funcionario",
    "empresa_ids": [1, 2]
  },
  {
    "id": 3,
    "username": "maria.santos",
    "type_user": "cliente",
    "empresa_ids": [1]
  }
]
```

**Erros Possíveis:**
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Usuário não é administrador

---

### 3. Obter Usuário por ID (READ)

Obtém os detalhes de um usuário específico.

**Endpoint:**
```
GET /api/mensura/admin/usuarios/{id}
```

**Path Parameters:**
- `id` (integer, obrigatório): ID do usuário

**Exemplo:**
```
GET /api/mensura/admin/usuarios/10
```

**Response (200 OK):**
```json
{
  "id": 10,
  "username": "joao.silva",
  "type_user": "funcionario",
  "empresa_ids": [1, 2]
}
```

**Erros Possíveis:**
- `404 Not Found`: "Usuário não encontrado"
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Usuário não é administrador

---

### 4. Atualizar Usuário (UPDATE)

Atualiza informações de um usuário existente.

**Endpoint:**
```
PUT /api/mensura/admin/usuarios/{id}
```

**Path Parameters:**
- `id` (integer, obrigatório): ID do usuário

**Body Request:**
```json
{
  "username": "joao.silva.updated",
  "type_user": "admin",
  "password": "novaSenha123",
  "empresa_ids": [1, 3, 5]
}
```

**Observações:**
- Todos os campos são **opcionais** (atualização parcial)
- Se `password` for fornecido, será hasheada automaticamente
- Se `username` for alterado, será validado se já existe outro usuário com o novo username
- Se `empresa_ids` for fornecido, substituirá completamente a lista anterior de empresas
- Para remover todas as empresas, envie `empresa_ids: []` ou `empresa_ids: null`

**Exemplo - Atualizar apenas senha:**
```json
{
  "password": "novaSenha123"
}
```

**Exemplo - Atualizar apenas empresas:**
```json
{
  "empresa_ids": [1, 2, 3]
}
```

**Exemplo - Remover todas as empresas:**
```json
{
  "empresa_ids": []
}
```

**Response (200 OK):**
```json
{
  "id": 10,
  "username": "joao.silva.updated",
  "type_user": "admin",
  "empresa_ids": [1, 3, 5]
}
```

**Validações:**
- Se `username` for alterado, deve ser único
- Se `type_user` for fornecido, deve ser: `"admin"`, `"cliente"` ou `"funcionario"`
- Todos os `empresa_ids` devem existir no banco de dados

**Erros Possíveis:**
- `400 Bad Request`: "Já existe um usuário com este username"
- `400 Bad Request`: "Tipo de usuário inválido"
- `400 Bad Request`: "Uma ou mais empresas não foram encontradas"
- `404 Not Found`: "Usuário não encontrado"
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Usuário não é administrador

---

### 5. Deletar Usuário (DELETE)

Remove um usuário do sistema.

**Endpoint:**
```
DELETE /api/mensura/admin/usuarios/{id}
```

**Path Parameters:**
- `id` (integer, obrigatório): ID do usuário

**Exemplo:**
```
DELETE /api/mensura/admin/usuarios/10
```

**Response (204 No Content):**
```
(sem corpo de resposta)
```

**⚠️ Atenção**: Esta operação é **irreversível**. O usuário será removido permanentemente do banco de dados.

**Validações:**
- O usuário deve existir

**Erros Possíveis:**
- `404 Not Found`: "Usuário não encontrado"
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Usuário não é administrador

---

## 🔒 Validações e Regras de Negócio

### Validações Gerais

1. **Username Único**: O `username` deve ser único em todo o sistema
2. **Tipo de Usuário**: `type_user` aceita apenas: `"admin"`, `"cliente"` ou `"funcionario"`
3. **Empresas**: Todos os `empresa_ids` fornecidos devem existir no banco de dados
4. **Senha**: A senha é sempre hasheada antes de ser armazenada (nunca é retornada)
5. **Autenticação**: Apenas usuários com `type_user = "admin"` podem acessar estes endpoints

### Regras de Negócio

1. **Criação de Usuário:**
   - O sistema verifica se já existe um usuário com o mesmo `username`
   - Valida se o `type_user` é válido
   - Valida se todas as empresas existem
   - A senha é hasheada automaticamente

2. **Atualização de Usuário:**
   - Atualização parcial: apenas os campos fornecidos são atualizados
   - Se `username` for alterado, verifica se o novo username já existe
   - Se `password` for fornecido, é hasheada automaticamente
   - Se `empresa_ids` for fornecido, substitui completamente a lista anterior

3. **Deleção de Usuário:**
   - Remove o usuário permanentemente do banco
   - Remove automaticamente os vínculos com empresas (cascade)

4. **Relacionamento com Empresas:**
   - Um usuário pode estar vinculado a múltiplas empresas
   - Uma empresa pode ter múltiplos usuários
   - O relacionamento é N:N (muitos para muitos)

---

## 📝 Códigos de Status HTTP

- `200 OK`: Operação realizada com sucesso
- `204 No Content`: Recurso deletado com sucesso (DELETE)
- `400 Bad Request`: Dados inválidos ou validação falhou
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Sem permissão para acessar o recurso (não é admin)
- `404 Not Found`: Usuário não encontrado
- `422 Unprocessable Entity`: Erro de validação de dados (Pydantic)
- `500 Internal Server Error`: Erro interno do servidor

---

## 🚀 Exemplos Práticos

### Criar Usuário Administrador

```bash
curl -X POST "https://api.exemplo.com/api/mensura/admin/usuarios" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin.novo",
    "password": "senhaAdmin123",
    "type_user": "admin"
  }'
```

### Criar Usuário Funcionário com Empresas

```bash
curl -X POST "https://api.exemplo.com/api/mensura/admin/usuarios" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "funcionario.empresa1",
    "password": "senhaFunc123",
    "type_user": "funcionario",
    "empresa_ids": [1, 2, 3]
  }'
```

### Listar Usuários com Paginação

```bash
curl -X GET "https://api.exemplo.com/api/mensura/admin/usuarios?skip=0&limit=20" \
  -H "Authorization: Bearer {admin_token}"
```

### Obter Usuário Específico

```bash
curl -X GET "https://api.exemplo.com/api/mensura/admin/usuarios/10" \
  -H "Authorization: Bearer {admin_token}"
```

### Atualizar Senha do Usuário

```bash
curl -X PUT "https://api.exemplo.com/api/mensura/admin/usuarios/10" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "novaSenhaSegura456"
  }'
```

### Atualizar Empresas do Usuário

```bash
curl -X PUT "https://api.exemplo.com/api/mensura/admin/usuarios/10" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "empresa_ids": [1, 2, 3, 4]
  }'
```

### Atualizar Múltiplos Campos

```bash
curl -X PUT "https://api.exemplo.com/api/mensura/admin/usuarios/10" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "joao.silva.updated",
    "type_user": "admin",
    "empresa_ids": [1]
  }'
```

### Deletar Usuário

```bash
curl -X DELETE "https://api.exemplo.com/api/mensura/admin/usuarios/10" \
  -H "Authorization: Bearer {admin_token}"
```

---

## ⚠️ Tratamento de Erros

### Estrutura de Erro Padrão

```typescript
interface ErrorResponse {
  detail: string;  // Mensagem de erro descritiva
}
```

### Exemplos de Respostas de Erro

#### 400 Bad Request - Username já existe
```json
{
  "detail": "Já existe um usuário com este username"
}
```

#### 400 Bad Request - Tipo inválido
```json
{
  "detail": "Tipo de usuário inválido"
}
```

#### 400 Bad Request - Empresas não encontradas
```json
{
  "detail": "Uma ou mais empresas não foram encontradas"
}
```

#### 401 Unauthorized
```json
{
  "detail": "Não autenticado Access"
}
```

#### 403 Forbidden
```json
{
  "detail": "Você não tem permissão para acessar este recurso"
}
```

#### 404 Not Found
```json
{
  "detail": "Usuário não encontrado"
}
```

### Tratamento no Frontend

```typescript
try {
  const response = await fetch('/api/mensura/admin/usuarios', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(userData)
  });

  if (!response.ok) {
    const error = await response.json();
    
    switch (response.status) {
      case 400:
        // Validação falhou
        console.error('Erro de validação:', error.detail);
        break;
      case 401:
        // Token inválido ou ausente
        console.error('Não autenticado');
        // Redirecionar para login
        break;
      case 403:
        // Sem permissão
        console.error('Acesso negado');
        break;
      case 404:
        // Usuário não encontrado
        console.error('Usuário não encontrado');
        break;
      default:
        console.error('Erro desconhecido:', error.detail);
    }
  } else {
    const user = await response.json();
    console.log('Usuário criado:', user);
  }
} catch (error) {
  console.error('Erro na requisição:', error);
}
```

---

## 📚 Tipos de Usuário

### `admin`
- Acesso completo ao sistema
- Pode gerenciar todos os recursos
- Pode criar, editar e deletar outros usuários

### `cliente`
- Acesso limitado
- Geralmente usado para clientes externos
- Permissões específicas conforme configuração

### `funcionario`
- Acesso de funcionário
- Permissões intermediárias
- Geralmente vinculado a empresas específicas

---

## 💡 Dicas e Boas Práticas

1. **Sempre valide o token** antes de fazer requisições
2. **Use paginação** em listagens grandes (`skip`/`limit`)
3. **Valide os dados** no frontend antes de enviar
4. **Trate erros adequadamente** para melhor UX
5. **Não exponha senhas** em logs ou mensagens de erro
6. **Use HTTPS** em produção para proteger tokens e senhas
7. **Implemente refresh token** para melhor segurança
8. **Valide `empresa_ids`** antes de enviar (verificar se existem)
9. **Para atualização parcial**, envie apenas os campos que deseja alterar
10. **Para remover empresas**, envie `empresa_ids: []` ou não inclua o campo se não quiser alterar

---

## 🔗 Endpoints Relacionados

- **Autenticação**: `/api/auth` (login, logout, refresh token)
- **Empresas**: `/api/empresas/admin` (gerenciar empresas)
- **Clientes**: `/api/cadastros/admin/clientes` (gerenciar clientes)

---

**Última atualização:** 2024-01-15  
**Versão da API:** 1.0
