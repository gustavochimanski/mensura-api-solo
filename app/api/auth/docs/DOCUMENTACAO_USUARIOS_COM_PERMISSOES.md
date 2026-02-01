# Usuários + Permissões (por rota) — Documentação completa (Supervisor/Admin)

Este documento descreve, de forma **atualizada pelo código**, como funciona:

- **Autenticação Admin (JWT)** (`/api/auth/*`)
- **CRUD de Usuários** (`/api/mensura/admin/usuarios`)
- **Catálogo e Grants de Permissões por rota** (`/api/mensura/admin/permissoes` e `/api/mensura/permissoes/me`)

> Escopo: endpoints do **Supervisor/Admin** (usuário do tipo `funcionario` ou `super`).

---

## 1) Conceitos e regras do modelo

- **Usuário (cadastros.usuarios)**:
  - `type_user`: normalmente **`cliente`** ou **`funcionario`**
  - existe também o tipo **`super`** (usuário seed) com acesso amplo (ver seção 4)
- **Empresa (tenant)**:
  - permissões são concedidas por **usuário + empresa**
  - o backend exige `empresa_id` em diversas rotas autenticadas (ver seção 2.2)
- **Permissão (cadastros.permissions)**:
  - catálogo “canônico” com keys **no formato** `route:/...` (ex.: `route:/pedidos`, `route:/configuracoes:usuarios`)
- **Grant (cadastros.user_permissions)**:
  - tabela de vínculo **(user_id, empresa_id, permission_id)**
  - o endpoint de “definir permissões” faz **replace total** (substitui todas as permissões do usuário naquela empresa)

---

## 2) Autenticação e headers obrigatórios

### 2.1) Login (JWT)

- **POST** `/api/auth/token`

Body:
```json
{ "username": "usuario", "password": "senha" }
```

Resposta:
```json
{
  "type_user": "cliente|funcionario|super",
  "access_token": "JWT...",
  "token_type": "Bearer"
}
```

Observação: o JWT expira conforme `ACCESS_TOKEN_EXPIRE_MINUTES` (config).

### 2.2) Headers padrão do Supervisor/Admin

Em endpoints Admin protegidos por `require_admin` e/ou permissões:

- `Authorization: Bearer <access_token>`
- `X-Empresa-Id: <empresa_id>`
  - alternativa (compat): `?empresa_id=<empresa_id>` (quando aplicável)

Sem `X-Empresa-Id` (ou `empresa_id`), o backend pode retornar:
- **400**: `empresa_id é obrigatório (use X-Empresa-Id ou query empresa_id)`
- **403**: `Você não tem acesso a esta empresa`

### 2.3) Quem é “admin” para o backend?

Um usuário consegue acessar rotas administrativas quando `type_user` é:
- `funcionario` **ou**
- `super`

Usuário `cliente` recebe **403** em rotas admin.

---

## 3) Usuários (Admin) — CRUD + vínculo com empresas

### 3.1) Modelo exposto na API

Em responses (`UserResponse`), o backend expõe:

```json
{
  "id": 123,
  "username": "joao",
  "type_user": "cliente|funcionario|super",
  "empresa_ids": [1, 3]
}
```

Notas:
- a senha **não** é retornada; o banco guarda `hashed_password`.
- no create/update, o frontend pode enviar `empresa_ids` **ou** `empresa_id` (compat).

### 3.2) Permissão exigida para CRUD de usuários

Para chamar os endpoints abaixo, além de ser `funcionario|super`, o backend exige:
- `route:/configuracoes` **OU**
- `route:/configuracoes:usuarios`

E também exige `X-Empresa-Id` (tenant) no request.

### 3.3) Criar usuário

- **POST** `/api/mensura/admin/usuarios`
- **Status**: 201

Body:
```json
{
  "username": "maria",
  "password": "minha-senha",
  "type_user": "funcionario",
  "empresa_ids": [1, 3]
}
```

Erros comuns:
- **400** `Já existe um usuário com este username`
- **400** `Tipo de usuário inválido` (valores aceitos via API: `cliente|funcionario`)
- **400** `Uma ou mais empresas não foram encontradas`

### 3.4) Listar usuários

- **GET** `/api/mensura/admin/usuarios?skip=0&limit=100`
- **Status**: 200

Resposta:
```json
[
  { "id": 1, "username": "admin", "type_user": "funcionario", "empresa_ids": [1] }
]
```

### 3.5) Obter usuário por ID

- **GET** `/api/mensura/admin/usuarios/{id}`
- **Status**: 200

Erros:
- **404** `Usuário não encontrado`

### 3.6) Atualizar usuário

- **PUT** `/api/mensura/admin/usuarios/{id}`
- **Status**: 200

Body (parcial — envie apenas o que mudar):
```json
{
  "username": "maria.oliveira",
  "password": "nova-senha",
  "empresa_ids": [1]
}
```

Notas:
- `password` (quando enviado) atualiza a senha do usuário.
- `empresa_ids`:
  - se enviado como `[]`, **remove** o vínculo com todas as empresas
  - se omitido, não altera o vínculo atual

### 3.7) Remover usuário

- **DELETE** `/api/mensura/admin/usuarios/{id}`
- **Status**: 204

Regras importantes:
- pode retornar **409** se existirem registros vinculados (ex.: abertura(s) de caixa / retirada(s)).
- ao remover, o backend também faz cleanup de:
  - vínculos `cadastros.usuario_empresa`
  - permissões `cadastros.user_permissions`

---

## 4) Permissões por rota (Admin) — catálogo + grants por usuário/empresa

### 4.1) Permissão exigida para gestão de permissões

Para os endpoints Admin de permissões, além de ser `funcionario|super`, o backend exige:
- `route:/configuracoes` **OU**
- `route:/configuracoes:permissoes`

E também exige `X-Empresa-Id` no request.

### 4.2) Catálogo de permissões (cadastros.permissions)

O catálogo é **seed** (idempotente) a partir de `app/core/permissions_catalog.py` e contém apenas chaves:
- `route:/...`

### 4.3) Listar catálogo (para tela “Configurações → Permissões”)

- **GET** `/api/mensura/admin/permissoes`
- **Status**: 200

Resposta (exemplo):
```json
[
  { "id": 101, "key": "route:/dashboard", "domain": "routes", "description": "Dashboard" },
  { "id": 102, "key": "route:/configuracoes:usuarios", "domain": "routes", "description": "Configurações - Usuários" }
]
```

### 4.4) Listar permissões (keys) de um usuário em uma empresa

- **GET** `/api/mensura/admin/permissoes/usuarios/{user_id}/empresas/{empresa_id}`
- **Status**: 200

Resposta:
```json
{
  "user_id": 10,
  "empresa_id": 3,
  "permission_keys": ["route:/dashboard", "route:/pedidos"]
}
```

Erros:
- **404** `Usuário não encontrado`
- **404** `Empresa não encontrada`

### 4.5) Definir (substituir) permissões de um usuário em uma empresa (replace total)

- **PUT** `/api/mensura/admin/permissoes/usuarios/{user_id}/empresas/{empresa_id}`
- **Status**: 200

Body:
```json
{
  "permission_keys": [
    "route:/dashboard",
    "route:/cadastros",
    "route:/configuracoes:usuarios"
  ]
}
```

Regras:
- **valida** se todas as `permission_keys` existem no catálogo; se houver desconhecidas:
  - **400** `Permissões inválidas/desconhecidas: [...]`
- faz **replace total**: remove todas as permissões atuais do usuário nessa empresa e grava apenas as do payload
- garante vínculo `usuario_empresa` (idempotente) mesmo que não exista endpoint dedicado para isso

### 4.6) Minhas permissões (para o frontend montar menu/guards)

- **GET** `/api/mensura/permissoes/me`
- **Status**: 200
- Obrigatório:
  - `Authorization: Bearer <token>`
  - `X-Empresa-Id: <empresa_id>`

Resposta:
```json
{
  "user_id": 10,
  "empresa_id": 3,
  "permission_keys": ["route:/dashboard", "route:/pedidos"]
}
```

### 4.7) Regra especial: usuário `super`

Quando `type_user == "super"`:
- o backend considera que o usuário possui **todas** as permissões do catálogo para a empresa informada
- mesmo que não exista vínculo usuário↔empresa ou grants diretos

---

## 5) Fluxo recomendado (cadastro → permissão → uso no frontend)

1) **Criar/editar usuário** (`POST/PUT /api/mensura/admin/usuarios`) com `empresa_ids`
2) **Definir permissões** (`PUT /api/mensura/admin/permissoes/usuarios/{user_id}/empresas/{empresa_id}`)
3) No Supervisor, após selecionar empresa, carregar:
   - **GET** `/api/mensura/permissoes/me` com `X-Empresa-Id`
4) Montar menu/guards no frontend a partir de `permission_keys`

---

## 6) Tabela rápida de erros (para UX)

- **401 Unauthorized**
  - JWT ausente / inválido / expirado
- **400 Bad Request**
  - `empresa_id` ausente/inválido em endpoints que exigem tenant
  - payload de permissões com keys desconhecidas
  - `type_user` inválido no create/update de usuário
- **403 Forbidden**
  - usuário autenticado, mas `type_user` não é `funcionario|super`
  - usuário sem acesso à empresa informada
  - usuário sem a permissão exigida pela rota
- **404 Not Found**
  - usuário/empresa não existe (endpoints específicos)
- **409 Conflict**
  - remoção de usuário bloqueada por registros vinculados (ex.: caixa/retirada)

