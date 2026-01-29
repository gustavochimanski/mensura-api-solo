# Permissões por rota do Frontend (Supervisor) — Integração Frontend x Backend

Este documento define como o frontend (Supervisor) deve **exibir menus/telas** e como o backend deve **autorizar endpoints admin** usando **permissões por rota do frontend** no formato `route:*`.

> Escopo: **apenas rotas/admin do backend** (painel Supervisor). Rotas **public** e **client (X-Super-Token)** não entram nesse modelo.

---

## 1) Conceitos

- **Empresa (tenant)**: permissões são concedidas por **usuário + empresa**.
- **Permissão por rota**: chave que representa uma **tela/área do Supervisor**.
  - **Formato base**: `route:<pathname>`
  - **Formato por aba**: `route:<pathname>:<tab>`

Exemplos:
- `route:/dashboard`
- `route:/pedidos`
- `route:/cadastros:receitas`
- `route:/configuracoes:usuarios`

### Herança recomendada (container → aba)
Para uma área com abas:
- `route:/cadastros` **libera todas as abas** de Cadastros
- `route:/cadastros:clientes` libera **apenas** a aba Clientes

Regra sugerida no backend (e útil no frontend):
- Se usuário tem `route:/cadastros`, então considera permitido para qualquer `route:/cadastros:<tab>`.

---

## 2) Segurança (regra de ouro)

O backend **não deve confiar** em “qual tela estou” enviada pelo frontend para autorizar acesso (isso pode ser forjado).

Modelo correto:
- O backend associa cada **endpoint admin** a uma ou mais permissões `route:*` (ex.: “tudo de pedidos admin exige `route:/pedidos`”).
- O frontend usa as mesmas permissões para **UX** (menus, bloqueio de navegação), mas a segurança real é no backend.

Se o frontend enviar a rota atual, use apenas para **telemetria/log**, não para autorização.

---

## 3) Autenticação (JWT Bearer) e escopo de empresa

### 3.1) Login (JWT)
- `POST /api/auth/token`

Body:
```json
{ "username": "usuario", "password": "senha" }
```

Resposta:
```json
{ "type_user": "admin|cliente|funcionario", "access_token": "JWT...", "token_type": "Bearer" }
```

### 3.2) Headers para chamadas admin
Em qualquer endpoint admin:
- `Authorization: Bearer <access_token>`

Quando o endpoint for “por empresa”:
- **Recomendado:** `X-Empresa-Id: <empresa_id>`

Observações:
- Usuário `type_user="admin"` é bypass operacional (não bloqueia).
- Usuário não-admin precisa estar vinculado à empresa e possuir permissões nessa empresa.

---

## 4) Catálogo de permissões e gestão (para a tela “Configurações → Permissões”)

> Os endpoints abaixo são **admin** (somente `type_user="admin"`).

### 4.1) Listar catálogo de permissões
- `GET /api/mensura/admin/permissoes`

Exemplo:
```json
[
  { "id": 101, "key": "route:/dashboard", "domain": "routes", "description": "Dashboard" },
  { "id": 102, "key": "route:/cadastros:clientes", "domain": "routes", "description": "Cadastros - Clientes" }
]
```

### 4.2) Listar permissões do usuário em uma empresa
- `GET /api/mensura/admin/permissoes/usuarios/{user_id}/empresas/{empresa_id}`

Exemplo:
```json
{
  "user_id": 10,
  "empresa_id": 3,
  "permission_keys": ["route:/dashboard", "route:/pedidos"]
}
```

### 4.3) Definir (substituir) permissões do usuário em uma empresa
> “Replace total”: o conjunto enviado vira o conjunto final.

- `PUT /api/mensura/admin/permissoes/usuarios/{user_id}/empresas/{empresa_id}`

Body:
```json
{
  "permission_keys": ["route:/dashboard", "route:/cadastros", "route:/pedidos"]
}
```

---

## 5) Regras de erro (para UX do frontend)

- **401 Unauthorized**
  - token ausente / inválido / expirado
- **400 Bad Request**
  - empresa inválida (quando requerida) ou payload de permissões inválido
- **403 Forbidden**
  - autenticado, mas sem acesso (sem vínculo com empresa e/ou sem permissão)
- **409 Conflict**
  - ao definir permissões: usuário não está vinculado à empresa (vincule primeiro)

---

## 6) Normalização de rota no frontend (chave `route:*`)

O frontend pode ter páginas equivalentes por:
- URL com tab (ex.: `/cadastros?tab=receitas`)
- subpath (ex.: `/cadastros/receitas`)

Padronize sempre para **uma única chave**:

### 6.1) Cadastros
- `/cadastros` → `route:/cadastros`
- `/cadastros?tab=clientes` → `route:/cadastros:clientes`
- `/cadastros/clientes` → `route:/cadastros:clientes`
- `/cadastros/meios-pagamento` → `route:/cadastros:meios-pagamento`
- `/cadastros/regioes-entrega` → `route:/cadastros:regioes-entrega`

### 6.2) Configurações
- `/configuracoes` → `route:/configuracoes`
- `/configuracoes?tab=usuarios` → `route:/configuracoes:usuarios`
- `/configuracoes/usuarios` → `route:/configuracoes:usuarios`
- `/configuracoes?tab=permissoes` → `route:/configuracoes:permissoes`

### 6.3) Financeiro
- `/financeiro` → `route:/financeiro`
- `/financeiro/caixas` → `route:/financeiro:caixas`
- `/financeiro/acertos-entregadores` → `route:/financeiro:acertos-entregadores`

### 6.4) BI
- `/bi` → `route:/bi`
- `/bi/entregador-detalhado` → `route:/bi:entregador-detalhado`
- `/bi/cliente-detalhado` → `route:/bi:cliente-detalhado`

---

## 7) Catálogo sugerido (Supervisor) — lista oficial de `route:*`

### Públicos (não usar em authz admin)
- `/`
- `/login`

### Supervisor (auth + permissão)
- `route:/dashboard`
- `route:/pedidos`
- `route:/cardapio`
- `route:/mesas`
- `route:/cadastros`
- `route:/cadastros:clientes`
- `route:/cadastros:produtos`
- `route:/cadastros:complementos`
- `route:/cadastros:receitas`
- `route:/cadastros:combos`
- `route:/cadastros:meios-pagamento`
- `route:/cadastros:regioes-entrega`
- `route:/marketing`
- `route:/relatorios`
- `route:/chatbot`
- `route:/atendimentos`
- `route:/financeiro`
- `route:/financeiro:caixas`
- `route:/financeiro:acertos-entregadores`
- `route:/configuracoes`
- `route:/configuracoes:empresas`
- `route:/configuracoes:regioes-entrega`
- `route:/configuracoes:meios-pagamento`
- `route:/configuracoes:entregadores`
- `route:/configuracoes:usuarios`
- `route:/configuracoes:permissoes`
- `route:/bi`
- `route:/bi:entregador-detalhado`
- `route:/bi:cliente-detalhado`
- `route:/empresas`

---

## 8) Recomendações de UX no frontend

- **Menu**: mostrar item apenas se o usuário tem a permissão da rota (ou do container).
- **Guarda de página**: se não tiver permissão, redirecionar para uma página “Sem permissão”.
- **Troca de empresa**: ao trocar `empresa_id`, recarregar permissões e reconstruir menu/guards.

