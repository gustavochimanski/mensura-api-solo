# Documentação Completa - CRUD de Empresas (Frontend)

Esta documentação descreve todos os endpoints disponíveis para o CRUD de empresas, incluindo exemplos de requisições, respostas e tratamento de erros.

---

## 📋 Índice

1. [Base URL e Autenticação](#base-url-e-autenticação)
2. [Estrutura de Dados](#estrutura-de-dados)
3. [Endpoints Admin (CRUD Completo)](#endpoints-admin-crud-completo)
4. [Endpoints Públicos](#endpoints-públicos)
5. [Tratamento de Erros](#tratamento-de-erros)
6. [Exemplos Práticos](#exemplos-práticos)

---

## 🔐 Base URL e Autenticação

### Base URL

**Prefixo Admin**: `/api/empresas/admin`  
**Prefixo Público**: `/api/empresas/public/emp`

**Exemplos:**
- **Local**: `http://localhost:8000/api/empresas/admin`
- **Produção**: `https://seu-dominio.com/api/empresas/admin`

### Autenticação

**Endpoints Admin**: Requerem autenticação via `get_current_user` (token JWT no header `Authorization: Bearer <token>`)

**Endpoints Públicos**: Não requerem autenticação

---

## 📊 Estrutura de Dados

### EmpresaResponse (Resposta Completa)

```typescript
interface EmpresaResponse {
  id: number;
  nome: string;
  cnpj?: string | null;
  slug: string;
  logo?: string | null;
  timezone?: string; // Padrão: "America/Sao_Paulo"
  horarios_funcionamento?: HorarioDia[];
  cardapio_link?: string | null;
  cardapio_tema?: string; // Padrão: "padrao"
  aceita_pedido_automatico: boolean; // Padrão: false
  redireciona_home: boolean; // Padrão: false
  redireciona_home_para?: string | null;
  
  // Endereço
  cep?: string | null;
  logradouro?: string | null;
  numero?: string | null;
  complemento?: string | null;
  bairro?: string | null;
  cidade?: string | null;
  estado?: string | null; // Sigla (ex: "SP")
  ponto_referencia?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

interface HorarioDia {
  dia_semana: number; // 0=domingo, 1=segunda, ..., 6=sábado
  intervalos: HorarioIntervalo[];
}

interface HorarioIntervalo {
  inicio: string; // Formato: "HH:MM" (ex: "08:00")
  fim: string; // Formato: "HH:MM" (ex: "18:00")
}
```

### EmpresaCardapioLinkResponse

```typescript
interface EmpresaCardapioLinkResponse {
  id: number;
  nome: string;
  cardapio_link?: string | null;
  cardapio_tema?: string | null;
}
```

### EmpresaPublicListItem

```typescript
interface EmpresaPublicListItem {
  id: number;
  nome: string;
  logo?: string | null;
  bairro?: string | null;
  cidade?: string | null;
  estado?: string | null;
  distancia_km?: number | null;
  tema?: string | null;
}
```

---

## 🔧 Endpoints Admin (CRUD Completo)

### 1. Listar Empresas

**GET** `/api/empresas/admin/`

Lista todas as empresas com paginação.

#### Parâmetros Query

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `skip` | integer | Não | 0 | Número de registros a pular |
| `limit` | integer | Não | 100 | Número máximo de registros retornados |

#### Exemplo de Requisição

```http
GET /api/empresas/admin/?skip=0&limit=10
Authorization: Bearer <token>
```

#### Resposta de Sucesso (200 OK)

```json
[
  {
    "id": 1,
    "nome": "Restaurante Exemplo",
    "cnpj": "12.345.678/0001-90",
    "slug": "restaurante-exemplo",
    "logo": "https://minio.../logo.jpg",
    "timezone": "America/Sao_Paulo",
    "horarios_funcionamento": [
      {
        "dia_semana": 1,
        "intervalos": [
          {"inicio": "08:00", "fim": "12:00"},
          {"inicio": "14:00", "fim": "18:00"}
        ]
      }
    ],
    "cardapio_link": "https://...",
    "cardapio_tema": "padrao",
    "aceita_pedido_automatico": false,
    "redireciona_home": false,
    "redireciona_home_para": null,
    "cep": "01234-567",
    "logradouro": "Rua Exemplo",
    "numero": "123",
    "complemento": null,
    "bairro": "Centro",
    "cidade": "São Paulo",
    "estado": "SP",
    "ponto_referencia": null,
    "latitude": -23.5505,
    "longitude": -46.6333
  }
]
```

---

### 2. Buscar Empresa por ID

**GET** `/api/empresas/admin/{id}`

Retorna os dados completos de uma empresa específica.

#### Parâmetros Path

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `id` | integer | Sim | ID da empresa |

#### Exemplo de Requisição

```http
GET /api/empresas/admin/1
Authorization: Bearer <token>
```

#### Resposta de Sucesso (200 OK)

```json
{
  "id": 1,
  "nome": "Restaurante Exemplo",
  "cnpj": "12.345.678/0001-90",
  "slug": "restaurante-exemplo",
  "logo": "https://minio.../logo.jpg",
  "timezone": "America/Sao_Paulo",
  "horarios_funcionamento": [...],
  "cardapio_link": "https://...",
  "cardapio_tema": "padrao",
  "aceita_pedido_automatico": false,
  "redireciona_home": false,
  "redireciona_home_para": null,
  "cep": "01234-567",
  "logradouro": "Rua Exemplo",
  "numero": "123",
  "complemento": null,
  "bairro": "Centro",
  "cidade": "São Paulo",
  "estado": "SP",
  "ponto_referencia": null,
  "latitude": -23.5505,
  "longitude": -46.6333
}
```

#### Resposta de Erro (404 Not Found)

```json
{
  "detail": "Empresa não encontrada"
}
```

---

### 3. Criar Empresa

**POST** `/api/empresas/admin/`

Cria uma nova empresa. **IMPORTANTE**: Este endpoint usa `multipart/form-data` para permitir upload de logo.

#### Form Data

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `nome` | string | Sim | Nome da empresa |
| `cnpj` | string | Não | CNPJ da empresa (único) |
| `endereco` | string (JSON) | Sim | JSON string com campos de endereço |
| `horarios_funcionamento` | string (JSON) | Não | JSON string com horários de funcionamento |
| `timezone` | string | Não | Timezone (padrão: "America/Sao_Paulo") |
| `logo` | file | Não | Arquivo de imagem da logo |
| `cardapio_link` | string | Não | Link do cardápio ou URL |
| `cardapio_tema` | string | Não | Tema do cardápio (padrão: "padrao") |
| `aceita_pedido_automatico` | string | Não | "true" ou "false" (padrão: "false") |
| `redireciona_home` | string | Não | "true" ou "false" (padrão: "false") |
| `redireciona_home_para` | string | Não | URL para redirecionamento (se redireciona_home=true) |

#### Estrutura do JSON `endereco`

```json
{
  "cep": "01234-567",
  "logradouro": "Rua Exemplo",
  "numero": "123",
  "complemento": "Apto 45",
  "bairro": "Centro",
  "cidade": "São Paulo",
  "estado": "SP",
  "ponto_referencia": "Próximo ao metrô",
  "latitude": -23.5505,
  "longitude": -46.6333
}
```

#### Estrutura do JSON `horarios_funcionamento`

```json
[
  {
    "dia_semana": 1,
    "intervalos": [
      {"inicio": "08:00", "fim": "12:00"},
      {"inicio": "14:00", "fim": "18:00"}
    ]
  },
  {
    "dia_semana": 2,
    "intervalos": [
      {"inicio": "08:00", "fim": "18:00"}
    ]
  }
]
```

#### Exemplo de Requisição (JavaScript/FormData)

```javascript
const formData = new FormData();
formData.append('nome', 'Restaurante Exemplo');
formData.append('cnpj', '12.345.678/0001-90');
formData.append('endereco', JSON.stringify({
  cep: '01234-567',
  logradouro: 'Rua Exemplo',
  numero: '123',
  bairro: 'Centro',
  cidade: 'São Paulo',
  estado: 'SP',
  latitude: -23.5505,
  longitude: -46.6333
}));
formData.append('horarios_funcionamento', JSON.stringify([
  {
    dia_semana: 1,
    intervalos: [
      { inicio: '08:00', fim: '18:00' }
    ]
  }
]));
formData.append('timezone', 'America/Sao_Paulo');
formData.append('cardapio_tema', 'padrao');
formData.append('aceita_pedido_automatico', 'false');
formData.append('redireciona_home', 'false');

// Se houver logo
if (logoFile) {
  formData.append('logo', logoFile);
}

fetch('/api/empresas/admin/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

#### Exemplo de Requisição (cURL)

```bash
curl -X POST "http://localhost:8000/api/empresas/admin/" \
  -H "Authorization: Bearer <token>" \
  -F "nome=Restaurante Exemplo" \
  -F "cnpj=12.345.678/0001-90" \
  -F 'endereco={"cep":"01234-567","logradouro":"Rua Exemplo","numero":"123","bairro":"Centro","cidade":"São Paulo","estado":"SP","latitude":-23.5505,"longitude":-46.6333}' \
  -F 'horarios_funcionamento=[{"dia_semana":1,"intervalos":[{"inicio":"08:00","fim":"18:00"}]}]' \
  -F "timezone=America/Sao_Paulo" \
  -F "cardapio_tema=padrao" \
  -F "aceita_pedido_automatico=false" \
  -F "logo=@/caminho/para/logo.jpg"
```

#### Resposta de Sucesso (200 OK)

Retorna o objeto `EmpresaResponse` completo com o ID gerado.

#### Respostas de Erro

**400 Bad Request** - CNPJ duplicado:
```json
{
  "detail": "Empresa já cadastrada (CNPJ)"
}
```

**400 Bad Request** - JSON inválido:
```json
{
  "detail": "Campo 'endereco' deve ser um JSON válido (string)."
}
```

**400 Bad Request** - Slug duplicado:
```json
{
  "detail": "Slug 'restaurante-exemplo' já existe. Tente novamente."
}
```

**400 Bad Request** - Cardápio link duplicado:
```json
{
  "detail": "Cardápio link 'https://...' já existe."
}
```

---

### 4. Atualizar Empresa

**PUT** `/api/empresas/admin/{id}`

Atualiza os dados de uma empresa existente. **IMPORTANTE**: Este endpoint usa `multipart/form-data` para permitir upload de logo.

#### Parâmetros Path

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `id` | integer | Sim | ID da empresa |

#### Form Data

Todos os campos são **opcionais** (exceto o `id` no path). Apenas os campos enviados serão atualizados.

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `nome` | string | Não | Nome da empresa |
| `cnpj` | string | Não | CNPJ da empresa |
| `endereco` | string (JSON) | Não | JSON string com campos de endereço |
| `horarios_funcionamento` | string (JSON) | Não | JSON string com horários |
| `timezone` | string | Não | Timezone |
| `logo` | file | Não | Arquivo de imagem da logo (substitui a anterior) |
| `cardapio_link` | string | Não | Link do cardápio |
| `cardapio_tema` | string | Não | Tema do cardápio |
| `aceita_pedido_automatico` | string | Não | "true" ou "false" |
| `redireciona_home` | string | Não | "true" ou "false" |
| `redireciona_home_para` | string | Não | URL para redirecionamento |

#### Exemplo de Requisição (JavaScript/FormData)

```javascript
const formData = new FormData();
formData.append('nome', 'Novo Nome');
formData.append('endereco', JSON.stringify({
  cidade: 'Rio de Janeiro',
  estado: 'RJ'
}));

// Se houver nova logo
if (novaLogoFile) {
  formData.append('logo', novaLogoFile);
}

fetch(`/api/empresas/admin/${empresaId}`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

#### Resposta de Sucesso (200 OK)

Retorna o objeto `EmpresaResponse` atualizado.

#### Respostas de Erro

**404 Not Found**:
```json
{
  "detail": "Empresa não encontrada"
}
```

**400 Bad Request** - Erros similares ao POST (CNPJ duplicado, JSON inválido, etc.)

---

### 5. Deletar Empresa

**DELETE** `/api/empresas/admin/{id}`

Remove uma empresa do sistema. **IMPORTANTE**: A empresa só pode ser deletada se não houver vínculos com:
- Produtos
- Pedidos
- Regiões de entrega
- Entregadores
- Usuários

#### Parâmetros Path

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `id` | integer | Sim | ID da empresa |

#### Exemplo de Requisição

```http
DELETE /api/empresas/admin/1
Authorization: Bearer <token>
```

#### Resposta de Sucesso (204 No Content)

Sem corpo de resposta.

#### Resposta de Erro (400 Bad Request)

```json
{
  "detail": "Não é possível remover a empresa porque ainda existem relacionamentos vinculados: 5 produto(s) vinculado(s); 10 pedido(s) vinculado(s); 2 região(ões) de entrega vinculada(s).\n- Desvincule ou delete os itens acima antes de remover a empresa.\nSugestão de ordem: produtos → regiões de entrega → entregadores/usuários → pedidos (ou arquivar) → empresa."
}
```

---

### 6. Buscar Endereços (Google Maps)

**GET** `/api/empresas/admin/buscar-endereco`

Busca endereços usando a API do Google Maps. Útil para autocompletar endereços no formulário.

#### Parâmetros Query

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `text` | string | Sim | - | Texto para buscar endereços |
| `max_results` | integer | Não | 5 | Número máximo de resultados (1-10) |

#### Exemplo de Requisição

```http
GET /api/empresas/admin/buscar-endereco?text=Rua%20Exemplo%20São%20Paulo&max_results=5
Authorization: Bearer <token>
```

#### Resposta de Sucesso (200 OK)

```json
[
  {
    "formatted_address": "Rua Exemplo, 123 - Centro, São Paulo - SP, 01234-567",
    "place_id": "ChIJ...",
    "geometry": {
      "location": {
        "lat": -23.5505,
        "lng": -46.6333
      }
    },
    "address_components": [...]
  }
]
```

#### Respostas de Erro

**503 Service Unavailable** - API não configurada:
```json
{
  "detail": "Serviço de geolocalização não configurado. Verifique a configuração da API key do Google Maps."
}
```

**404 Not Found** - Nenhum endereço encontrado:
```json
{
  "detail": "Nenhum endereço encontrado para: Rua Exemplo. Verifique os logs para mais detalhes sobre possíveis problemas com a API key."
}
```

---

### 7. Listar Links de Cardápios

**GET** `/api/empresas/admin/cardapios`

Lista todas as empresas com seus links de cardápio. Útil para gerenciamento de cardápios.

#### Exemplo de Requisição

```http
GET /api/empresas/admin/cardapios
Authorization: Bearer <token>
```

#### Resposta de Sucesso (200 OK)

```json
[
  {
    "id": 1,
    "nome": "Restaurante Exemplo",
    "cardapio_link": "https://...",
    "cardapio_tema": "padrao"
  },
  {
    "id": 2,
    "nome": "Outra Empresa",
    "cardapio_link": null,
    "cardapio_tema": "padrao"
  }
]
```

---

## 🌐 Endpoints Públicos

### 1. Listar Empresas Públicas

**GET** `/api/empresas/public/emp/lista`

Lista empresas disponíveis para seleção pública, com filtros opcionais. **Não requer autenticação**.

#### Parâmetros Query

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `q` | string | Não | - | Termo de busca por nome ou slug |
| `cidade` | string | Não | - | Filtrar por cidade |
| `estado` | string | Não | - | Filtrar por estado (sigla) |
| `limit` | integer | Não | 100 | Limite máximo (1-500) |

#### Exemplo de Requisição

```http
GET /api/empresas/public/emp/lista?q=restaurante&cidade=São%20Paulo&estado=SP&limit=20
```

#### Resposta de Sucesso (200 OK)

```json
[
  {
    "id": 1,
    "nome": "Restaurante Exemplo",
    "logo": "https://minio.../logo.jpg",
    "bairro": "Centro",
    "cidade": "São Paulo",
    "estado": "SP",
    "distancia_km": null,
    "tema": "padrao"
  }
]
```

---

### 2. Buscar Empresa (Cliente)

**GET** `/api/empresas/public/emp/`

Retorna dados da empresa para uso no frontend do cliente. **Não requer autenticação**.

#### Parâmetros Query

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | integer | Sim | ID da empresa |

#### Exemplo de Requisição

```http
GET /api/empresas/public/emp/?empresa_id=1
```

#### Resposta de Sucesso (200 OK)

```json
{
  "nome": "Restaurante Exemplo",
  "logo": "https://minio.../logo.jpg",
  "timezone": "America/Sao_Paulo",
  "horarios_funcionamento": [...],
  "cardapio_tema": "padrao",
  "aceita_pedido_automatico": false,
  "tempo_entrega_maximo": 60,
  "redireciona_home": false,
  "redireciona_home_para": null,
  "cep": "01234-567",
  "logradouro": "Rua Exemplo",
  "numero": "123",
  "complemento": null,
  "bairro": "Centro",
  "cidade": "São Paulo",
  "estado": "SP",
  "ponto_referencia": null,
  "latitude": -23.5505,
  "longitude": -46.6333
}
```

---

## ⚠️ Tratamento de Erros

### Códigos de Status HTTP

| Código | Significado | Quando Ocorre |
|--------|-------------|---------------|
| 200 | OK | Requisição bem-sucedida |
| 204 | No Content | Delete bem-sucedido |
| 400 | Bad Request | Dados inválidos, duplicidade, etc. |
| 401 | Unauthorized | Token ausente ou inválido (endpoints admin) |
| 404 | Not Found | Empresa não encontrada |
| 503 | Service Unavailable | Serviço externo não configurado |

### Estrutura de Erro

```json
{
  "detail": "Mensagem de erro descritiva"
}
```

### Erros Comuns

1. **CNPJ Duplicado**: `"Empresa já cadastrada (CNPJ)"`
2. **Slug Duplicado**: `"Slug 'xxx' já existe. Tente novamente."`
3. **Cardápio Link Duplicado**: `"Cardápio link 'xxx' já existe."`
4. **JSON Inválido**: `"Campo 'endereco' deve ser um JSON válido (string)."`
5. **Empresa Não Encontrada**: `"Empresa não encontrada"`
6. **Vínculos Existentes**: Mensagem detalhada listando os vínculos que impedem a exclusão

---

## 💡 Exemplos Práticos

### Exemplo 1: Criar Empresa Completa (React/TypeScript)

```typescript
interface EmpresaFormData {
  nome: string;
  cnpj?: string;
  endereco: {
    cep?: string;
    logradouro?: string;
    numero?: string;
    bairro?: string;
    cidade?: string;
    estado?: string;
    latitude?: number;
    longitude?: number;
  };
  horarios_funcionamento?: HorarioDia[];
  logo?: File;
}

async function criarEmpresa(data: EmpresaFormData, token: string) {
  const formData = new FormData();
  
  formData.append('nome', data.nome);
  if (data.cnpj) formData.append('cnpj', data.cnpj);
  formData.append('endereco', JSON.stringify(data.endereco));
  
  if (data.horarios_funcionamento) {
    formData.append('horarios_funcionamento', JSON.stringify(data.horarios_funcionamento));
  }
  
  if (data.logo) {
    formData.append('logo', data.logo);
  }
  
  const response = await fetch('/api/empresas/admin/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}
```

### Exemplo 2: Atualizar Apenas Nome e Logo

```typescript
async function atualizarLogoEmpresa(
  empresaId: number, 
  novaLogo: File, 
  token: string
) {
  const formData = new FormData();
  formData.append('logo', novaLogo);
  
  const response = await fetch(`/api/empresas/admin/${empresaId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}
```

### Exemplo 3: Buscar Endereço com Autocomplete

```typescript
async function buscarEnderecos(texto: string, token: string) {
  const response = await fetch(
    `/api/empresas/admin/buscar-endereco?text=${encodeURIComponent(texto)}&max_results=5`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}
```

### Exemplo 4: Validar Antes de Deletar

```typescript
async function deletarEmpresa(empresaId: number, token: string) {
  const response = await fetch(`/api/empresas/admin/${empresaId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    // A mensagem de erro já indica quais vínculos existem
    throw new Error(error.detail);
  }
  
  // 204 No Content - sucesso
  return true;
}
```

---

## 📝 Notas Importantes

1. **Upload de Logo**: 
   - Formatos aceitos: JPG, PNG, etc. (verificar configuração do MinIO)
   - A logo anterior é substituída automaticamente ao fazer upload de uma nova
   - Ao deletar empresa, a logo também é removida do storage

2. **Slug Automático**: 
   - O slug é gerado automaticamente a partir do nome
   - Se o slug já existir, um sufixo numérico é adicionado (ex: `restaurante-exemplo-2`)

3. **Horários de Funcionamento**:
   - `dia_semana`: 0 = domingo, 1 = segunda, ..., 6 = sábado
   - Horários no formato `HH:MM` (24 horas)
   - Um dia pode ter múltiplos intervalos

4. **Timezone**:
   - Padrão: `"America/Sao_Paulo"`
   - Use timezones válidos do IANA (ex: `"America/New_York"`)

5. **Estado**:
   - Sempre em maiúsculas (ex: "SP", "RJ")
   - O backend converte automaticamente para maiúsculas

6. **Cardápio Link**:
   - Pode ser uma URL externa ou um link interno
   - Deve ser único no sistema

7. **Redirecionamento Home**:
   - `redireciona_home`: Ativa/desativa o redirecionamento
   - `redireciona_home_para`: URL de destino (só usado se `redireciona_home = true`)

---

## 🔗 Endpoints Resumidos

| Método | Endpoint | Autenticação | Descrição |
|--------|----------|--------------|-----------|
| GET | `/api/empresas/admin/` | ✅ | Listar empresas |
| GET | `/api/empresas/admin/{id}` | ✅ | Buscar empresa por ID |
| POST | `/api/empresas/admin/` | ✅ | Criar empresa |
| PUT | `/api/empresas/admin/{id}` | ✅ | Atualizar empresa |
| DELETE | `/api/empresas/admin/{id}` | ✅ | Deletar empresa |
| GET | `/api/empresas/admin/buscar-endereco` | ✅ | Buscar endereços (Google Maps) |
| GET | `/api/empresas/admin/cardapios` | ✅ | Listar links de cardápios |
| GET | `/api/empresas/public/emp/lista` | ❌ | Listar empresas públicas |
| GET | `/api/empresas/public/emp/` | ❌ | Buscar empresa (cliente) |

---

**Última atualização**: 2024
