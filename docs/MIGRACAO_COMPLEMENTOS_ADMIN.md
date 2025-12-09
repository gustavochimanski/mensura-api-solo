# 📚 Documentação de Migração: Adicionais → Complementos (Admin)

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Mudanças na Estrutura de Dados](#mudanças-na-estrutura-de-dados)
3. [Endpoints Obsoletos](#endpoints-obsoletos)
4. [Novos Endpoints Necessários](#novos-endpoints-necessários)
5. [Schemas Atualizados](#schemas-atualizados)
6. [Relacionamentos](#relacionamentos)
7. [Migração de Dados](#migração-de-dados)
8. [Exemplos de Uso](#exemplos-de-uso)

---

## 🎯 Visão Geral

O sistema foi migrado de uma estrutura **plana de adicionais** para uma estrutura **hierárquica de complementos**. 

### Antes (Estrutura Antiga)
```
Produto
  └── Adicionais (diretos)
      - Cada adicional tinha suas próprias configurações
      - obrigatorio, permite_multipla_escolha no próprio adicional
```

### Agora (Nova Estrutura)
```
Produto
  └── Complemento (grupo de adicionais)
      - Configurações no complemento: obrigatorio, quantitativo, permite_multipla_escolha
      └── Adicionais (produtos dentro do complemento)
          - Apenas: nome, preco, custo, ativo, ordem
```

---

## 🔄 Mudanças na Estrutura de Dados

### 1. Novo Modelo: `ComplementoModel`

**Tabela:** `catalogo.complemento_produto`

**Campos:**
- `id` (PK)
- `empresa_id` (FK)
- `nome` (String 100)
- `descricao` (String 255, nullable)
- `ativo` (Boolean, default: true)
- **`obrigatorio`** (Boolean, default: false) - **NOVO: configuração do complemento**
- **`quantitativo`** (Boolean, default: false) - **NOVO: permite quantidade nos adicionais**
- **`permite_multipla_escolha`** (Boolean, default: true) - **NOVO: configuração do complemento**
- `ordem` (Integer, default: 0)
- `created_at`, `updated_at`

### 2. Modelo Atualizado: `AdicionalModel`

**Tabela:** `catalogo.adicional_produto`

**Mudanças:**
- ✅ **Adicionado:** `complemento_id` (FK obrigatória para `complemento_produto.id`)
- ❌ **Removido:** `obrigatorio` (agora está no complemento)
- ❌ **Removido:** `permite_multipla_escolha` (agora está no complemento)
- ❌ **Removido:** Relacionamento N:N direto com produtos (agora é via complementos)

**Campos Mantidos:**
- `id`, `empresa_id`, `nome`, `descricao`, `preco`, `custo`, `ativo`, `ordem`

### 3. Novas Tabelas de Associação

**`catalogo.produto_complemento_link`** (NOVO)
- `produto_cod_barras` (FK → `produtos.cod_barras`)
- `complemento_id` (FK → `complemento_produto.id`)
- `ordem` (Integer)
- `created_at`

**`catalogo.produto_adicional_link`** (DEPRECADA)
- Mantida apenas para compatibilidade
- **NÃO DEVE SER USADA** em novos desenvolvimentos

---

## 🚫 Endpoints Obsoletos

### ⚠️ Endpoints de Adicionais que DEVEM SER DESCONTINUADOS

#### Admin - `/api/catalogo/admin/adicionais`

| Método | Endpoint | Status | Motivo |
|--------|----------|--------|--------|
| `POST` | `/api/catalogo/admin/adicionais` | ❌ **OBSOLETO** | Adicionais agora são criados dentro de complementos |
| `PUT` | `/api/catalogo/admin/adicionais/{adicional_id}` | ❌ **OBSOLETO** | Use endpoints de complementos |
| `DELETE` | `/api/catalogo/admin/adicionais/{adicional_id}` | ❌ **OBSOLETO** | Use endpoints de complementos |
| `POST` | `/api/catalogo/admin/adicionais/produto/{cod_barras}/vincular` | ❌ **OBSOLETO** | Vincule complementos ao produto, não adicionais diretos |

#### Client - `/api/catalogo/client/adicionais`

| Método | Endpoint | Status | Motivo |
|--------|----------|--------|--------|
| `GET` | `/api/catalogo/client/adicionais/produto/{cod_barras}` | ❌ **OBSOLETO** | Use endpoint de complementos do produto |
| `GET` | `/api/catalogo/client/adicionais/combo/{combo_id}` | ❌ **OBSOLETO** | Use endpoint de complementos do combo |
| `GET` | `/api/catalogo/client/adicionais/receita/{receita_id}` | ❌ **OBSOLETO** | Use endpoint de complementos da receita |

### ⚠️ Endpoints que AINDA FUNCIONAM (mas limitados)

| Método | Endpoint | Status | Observação |
|--------|----------|--------|------------|
| `GET` | `/api/catalogo/admin/adicionais/` | ⚠️ **LIMITADO** | Lista adicionais, mas eles devem estar dentro de complementos |
| `GET` | `/api/catalogo/admin/adicionais/{adicional_id}` | ⚠️ **LIMITADO** | Busca adicional, mas ele deve estar dentro de um complemento |
| `GET` | `/api/catalogo/admin/adicionais/produto/{cod_barras}` | ⚠️ **LIMITADO** | Retorna vazio (adicionais não são mais vinculados diretamente a produtos) |

---

## ✅ Novos Endpoints Necessários

### 🔨 Endpoints de Complementos (A CRIAR)

#### Admin - `/api/catalogo/admin/complementos`

```python
# Listar complementos de uma empresa
GET /api/catalogo/admin/complementos?empresa_id={id}&apenas_ativos=true

# Criar complemento
POST /api/catalogo/admin/complementos
Body: {
    "empresa_id": int,
    "nome": str,
    "descricao": str | null,
    "obrigatorio": bool,
    "quantitativo": bool,
    "permite_multipla_escolha": bool,
    "ordem": int
}

# Buscar complemento por ID
GET /api/catalogo/admin/complementos/{complemento_id}

# Atualizar complemento
PUT /api/catalogo/admin/complementos/{complemento_id}
Body: {
    "nome": str | null,
    "descricao": str | null,
    "obrigatorio": bool | null,
    "quantitativo": bool | null,
    "permite_multipla_escolha": bool | null,
    "ativo": bool | null,
    "ordem": int | null
}

# Deletar complemento
DELETE /api/catalogo/admin/complementos/{complemento_id}

# Vincular complementos a um produto
POST /api/catalogo/admin/complementos/produto/{cod_barras}/vincular
Body: {
    "complemento_ids": [int]
}

# Listar complementos de um produto
GET /api/catalogo/admin/complementos/produto/{cod_barras}?apenas_ativos=true
```

#### Admin - Adicionais dentro de Complementos

```python
# Criar adicional dentro de um complemento
POST /api/catalogo/admin/complementos/{complemento_id}/adicionais
Body: {
    "nome": str,
    "descricao": str | null,
    "preco": decimal,
    "custo": decimal,
    "ativo": bool,
    "ordem": int
}

# Atualizar adicional
PUT /api/catalogo/admin/complementos/{complemento_id}/adicionais/{adicional_id}
Body: {
    "nome": str | null,
    "descricao": str | null,
    "preco": decimal | null,
    "custo": decimal | null,
    "ativo": bool | null,
    "ordem": int | null
}

# Deletar adicional
DELETE /api/catalogo/admin/complementos/{complemento_id}/adicionais/{adicional_id}

# Listar adicionais de um complemento
GET /api/catalogo/admin/complementos/{complemento_id}/adicionais?apenas_ativos=true
```

#### Client - `/api/catalogo/client/complementos`

```python
# Listar complementos de um produto (com seus adicionais)
GET /api/catalogo/client/complementos/produto/{cod_barras}?apenas_ativos=true

# Listar complementos de um combo (com seus adicionais)
GET /api/catalogo/client/complementos/combo/{combo_id}?apenas_ativos=true

# Listar complementos de uma receita (com seus adicionais)
GET /api/catalogo/client/complementos/receita/{receita_id}?apenas_ativos=true
```

---

## 📝 Schemas Atualizados

### Schemas de Pedidos

#### ❌ Removido: `ItemAdicionalRequest`
```python
# ANTES (OBSOLETO)
class ItemAdicionalRequest(BaseModel):
    adicional_id: int
    quantidade: int
```

#### ✅ Novo: `ItemAdicionalComplementoRequest`
```python
class ItemAdicionalComplementoRequest(BaseModel):
    """Adicional dentro de um complemento"""
    adicional_id: int
    quantidade: int = Field(ge=1, default=1)  # Usado apenas se complemento.quantitativo = true
```

#### ✅ Novo: `ItemComplementoRequest`
```python
class ItemComplementoRequest(BaseModel):
    """Complemento com seus adicionais selecionados"""
    complemento_id: int
    adicionais: List[ItemAdicionalComplementoRequest] = []
```

#### ✅ Atualizado: `ItemPedidoRequest`
```python
class ItemPedidoRequest(BaseModel):
    produto_cod_barras: str
    quantidade: int
    observacao: Optional[str] = None
    
    # NOVO: apenas complementos
    complementos: Optional[List[ItemComplementoRequest]] = None
    
    # REMOVIDO: adicionais (obsoleto)
    # REMOVIDO: adicionais_ids (obsoleto)
```

#### ✅ Atualizado: `ReceitaPedidoRequest`
```python
class ReceitaPedidoRequest(BaseModel):
    receita_id: int
    quantidade: int
    observacao: Optional[str] = None
    
    # NOVO: apenas complementos
    complementos: Optional[List[ItemComplementoRequest]] = None
    
    # REMOVIDO: adicionais (obsoleto)
    # REMOVIDO: adicionais_ids (obsoleto)
```

#### ✅ Atualizado: `ComboPedidoRequest`
```python
class ComboPedidoRequest(BaseModel):
    combo_id: int
    quantidade: int = 1
    
    # NOVO: apenas complementos
    complementos: Optional[List[ItemComplementoRequest]] = None
    
    # REMOVIDO: adicionais (obsoleto)
```

#### ✅ Atualizado: `PedidoItemMutationRequest` (Admin)
```python
class PedidoItemMutationRequest(BaseModel):
    acao: PedidoItemMutationAction
    item_id: Optional[int] = None
    produto_cod_barras: Optional[str] = None
    receita_id: Optional[int] = None
    combo_id: Optional[int] = None
    quantidade: Optional[int] = None
    observacao: Optional[str] = None
    
    # NOVO: apenas complementos
    complementos: Optional[List[ItemComplementoRequest]] = None
    
    # REMOVIDO: adicionais (obsoleto)
    # REMOVIDO: adicionais_ids (obsoleto)
```

### Schemas de Complementos (A CRIAR)

#### Request Schemas

```python
class CriarComplementoRequest(BaseModel):
    empresa_id: int
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    obrigatorio: bool = False
    quantitativo: bool = False
    permite_multipla_escolha: bool = True
    ordem: int = 0

class AtualizarComplementoRequest(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    obrigatorio: Optional[bool] = None
    quantitativo: Optional[bool] = None
    permite_multipla_escolha: Optional[bool] = None
    ativo: Optional[bool] = None
    ordem: Optional[int] = None

class CriarAdicionalRequest(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    preco: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    custo: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    ativo: bool = True
    ordem: int = 0

class VincularComplementosProdutoRequest(BaseModel):
    complemento_ids: List[int] = Field(..., description="IDs dos complementos a vincular")
```

#### Response Schemas

```python
class AdicionalDTO(BaseModel):
    """Adicional dentro de um complemento"""
    id: int
    nome: str
    preco: Decimal
    ordem: int

class ComplementoResponse(BaseModel):
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str]
    obrigatorio: bool
    quantitativo: bool
    permite_multipla_escolha: bool
    ordem: int
    ativo: bool
    adicionais: List[AdicionalDTO]  # Adicionais dentro do complemento
    created_at: datetime
    updated_at: datetime
```

---

## 🔗 Relacionamentos

### Nova Estrutura de Relacionamentos

```
Produto (cod_barras)
  └── N:N → produto_complemento_link
      └── Complemento (id)
          └── 1:N → Adicional (complemento_id)
```

### Diagrama de Relacionamentos

```
┌─────────────────┐
│   Produto       │
│ (cod_barras)    │
└────────┬────────┘
         │
         │ N:N
         │
┌────────▼──────────────────┐
│ produto_complemento_link  │
│ - produto_cod_barras      │
│ - complemento_id         │
│ - ordem                  │
└────────┬──────────────────┘
         │
         │ 1:N
         │
┌────────▼──────────────┐
│   Complemento        │
│ - id                 │
│ - empresa_id         │
│ - nome               │
│ - obrigatorio        │ ← Configurações aqui
│ - quantitativo       │
│ - permite_multipla_  │
│   escolha            │
└────────┬─────────────┘
         │
         │ 1:N
         │
┌────────▼──────────────┐
│   Adicional           │
│ - id                  │
│ - complemento_id      │ ← FK obrigatória
│ - nome                │
│ - preco               │
│ - custo               │
│ - ativo               │
│ - ordem               │
└───────────────────────┘
```

### Tabelas de Associação

1. **`produto_complemento_link`** (NOVO)
   - Relaciona produtos com complementos
   - Permite múltiplos complementos por produto
   - Ordem de exibição configurável

2. **`produto_adicional_link`** (DEPRECADA)
   - Mantida apenas para compatibilidade
   - Não deve ser usada em novos desenvolvimentos

---

## 🔄 Migração de Dados

### Passos para Migração

1. **Criar complementos a partir de adicionais existentes**
   - Agrupar adicionais por produto
   - Criar um complemento "Padrão" para cada produto que tinha adicionais
   - Mover adicionais para dentro do complemento

2. **Atualizar relacionamentos**
   - Migrar dados de `produto_adicional_link` para `produto_complemento_link`
   - Atualizar `AdicionalModel.complemento_id` para todos os adicionais

3. **Configurações**
   - Migrar `obrigatorio` e `permite_multipla_escolha` dos adicionais para o complemento
   - Definir `quantitativo` conforme regra de negócio

### Script de Migração (Exemplo)

```python
# Pseudocódigo para migração
for produto in produtos_com_adicionais:
    # Criar complemento padrão
    complemento = criar_complemento(
        empresa_id=produto.empresa_id,
        nome="Adicionais",
        obrigatorio=False,
        quantitativo=True,
        permite_multipla_escolha=True
    )
    
    # Vincular complemento ao produto
    vincular_complemento_produto(produto.cod_barras, complemento.id)
    
    # Mover adicionais para dentro do complemento
    for adicional in produto.adicionais:
        adicional.complemento_id = complemento.id
        # Remover campos obsoletos
        del adicional.obrigatorio
        del adicional.permite_multipla_escolha
```

---

## 💡 Exemplos de Uso

### 1. Criar um Complemento com Adicionais

```python
# 1. Criar complemento
POST /api/catalogo/admin/complementos
{
    "empresa_id": 1,
    "nome": "Molhos",
    "descricao": "Escolha seus molhos favoritos",
    "obrigatorio": false,
    "quantitativo": false,
    "permite_multipla_escolha": true,
    "ordem": 1
}
# Response: { "id": 10, ... }

# 2. Criar adicionais dentro do complemento
POST /api/catalogo/admin/complementos/10/adicionais
{
    "nome": "Ketchup",
    "preco": 0.00,
    "custo": 0.00,
    "ativo": true,
    "ordem": 1
}

POST /api/catalogo/admin/complementos/10/adicionais
{
    "nome": "Mostarda",
    "preco": 0.00,
    "custo": 0.00,
    "ativo": true,
    "ordem": 2
}

POST /api/catalogo/admin/complementos/10/adicionais
{
    "nome": "Barbecue",
    "preco": 2.00,
    "custo": 1.00,
    "ativo": true,
    "ordem": 3
}

# 3. Vincular complemento a um produto
POST /api/catalogo/admin/complementos/produto/7891234567890/vincular
{
    "complemento_ids": [10]
}
```

### 2. Criar Pedido com Complementos

```python
POST /api/pedidos/client/checkout
{
    "empresa_id": 1,
    "tipo_pedido": "DELIVERY",
    "produtos": {
        "itens": [
            {
                "produto_cod_barras": "7891234567890",
                "quantidade": 2,
                "complementos": [
                    {
                        "complemento_id": 10,
                        "adicionais": [
                            { "adicional_id": 1, "quantidade": 1 },  # Ketchup
                            { "adicional_id": 3, "quantidade": 1 }   # Barbecue
                        ]
                    }
                ]
            }
        ]
    }
}
```

### 3. Adicionar Item em Pedido de Mesa com Complementos

```python
POST /api/pedidos/admin/mesa/{pedido_id}/item
{
    "produto_cod_barras": "7891234567890",
    "quantidade": 1,
    "complementos": [
        {
            "complemento_id": 10,
            "adicionais": [
                { "adicional_id": 1, "quantidade": 1 }
            ]
        }
    ]
}
```

### 4. Buscar Complementos de um Produto (Client)

```python
GET /api/catalogo/client/complementos/produto/7891234567890?apenas_ativos=true

# Response:
[
    {
        "id": 10,
        "nome": "Molhos",
        "descricao": "Escolha seus molhos favoritos",
        "obrigatorio": false,
        "quantitativo": false,
        "permite_multipla_escolha": true,
        "ordem": 1,
        "adicionais": [
            { "id": 1, "nome": "Ketchup", "preco": 0.00, "ordem": 1 },
            { "id": 2, "nome": "Mostarda", "preco": 0.00, "ordem": 2 },
            { "id": 3, "nome": "Barbecue", "preco": 2.00, "ordem": 3 }
        ]
    }
]
```

---

## ⚠️ Pontos de Atenção

1. **Adicionais não podem mais existir sem complemento**
   - Todo adicional DEVE ter um `complemento_id`
   - Não é possível criar adicionais diretamente vinculados a produtos

2. **Configurações movidas para complemento**
   - `obrigatorio`: se o complemento é obrigatório
   - `quantitativo`: se permite quantidade nos adicionais (ex: 2x bacon)
   - `permite_multipla_escolha`: se pode escolher múltiplos adicionais no complemento

3. **Validações necessárias**
   - Se `complemento.obrigatorio = true`, pelo menos um adicional deve ser selecionado
   - Se `complemento.quantitativo = false`, quantidade sempre será 1 (ignorar quantidade enviada)
   - Se `complemento.permite_multipla_escolha = false`, apenas um adicional pode ser selecionado

4. **Endpoints obsoletos**
   - Todos os endpoints de adicionais diretos devem ser descontinuados
   - Frontend deve migrar para usar endpoints de complementos

---

## 📌 Checklist de Migração

- [ ] Criar endpoints de complementos (admin e client)
- [ ] Criar schemas de complementos
- [ ] Atualizar documentação da API
- [ ] Migrar dados existentes
- [ ] Descontinuar endpoints obsoletos de adicionais
- [ ] Atualizar frontend para usar complementos
- [ ] Testar fluxo completo de pedidos com complementos
- [ ] Validar cálculos de preços com complementos
- [ ] Atualizar testes automatizados

---

**Última atualização:** 2024
**Versão:** 1.0.0

