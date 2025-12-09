# 🎨 Diagrama Visual - Sistema de Complementos

## 📐 Estrutura de Dados

```
┌─────────────────────────────────────────────────────────────┐
│                        EMPRESA                                │
│                      (empresa_id: 1)                          │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         │ 1:N
                         │
         ┌───────────────▼───────────────┐
         │      COMPLEMENTO               │
         │  (complemento_produto)         │
         ├───────────────────────────────┤
         │ id: 1                         │
         │ nome: "Molhos"                 │
         │ obrigatorio: false             │
         │ quantitativo: false            │
         │ permite_multipla_escolha: true│
         └───────────────┬───────────────┘
                         │
                         │ 1:N
                         │
         ┌───────────────▼───────────────┐
         │   ITEM (ADICIONAL)            │
         │  (complemento_itens)          │
         ├───────────────────────────────┤
         │ id: 1 (adicional_id)          │
         │ nome: "Ketchup"                │
         │ preco: 0.00                   │
         │ complemento_id: 1             │
         └───────────────────────────────┘
```

## 🔄 Fluxo de Relacionamentos

```
┌──────────┐
│ PRODUTO  │
│(cod_barras)│
└────┬─────┘
     │
     │ N:N (via produto_complemento_link)
     │
     ▼
┌──────────────┐         ┌──────────────┐
│ COMPLEMENTO  │◄──1:N───│    ITEM      │
│              │         │  (adicional)  │
│ - obrigatorio│         │ - preco       │
│ - quantitativo│        │ - nome        │
│ - multipla   │         └──────────────┘
│   escolha    │
└──────────────┘
```

## 🛒 Fluxo de Pedido

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENTE NO FRONTEND                       │
│                                                              │
│  1. Buscar complementos do produto                         │
│     GET /api/catalogo/client/complementos/produto/{cod}     │
│                                                              │
│  2. Exibir opções na UI                                     │
│     - Complemento: "Molhos"                                 │
│       ☐ Ketchup (R$ 0,00)                                  │
│       ☐ Maionese (R$ 0,00)                                  │
│       ☑ Mostarda (R$ 1,50)                                  │
│                                                              │
│  3. Cliente seleciona itens                                 │
│                                                              │
│  4. Adicionar ao carrinho/pedido                           │
│     POST /api/pedidos/client/checkout                       │
│     {                                                       │
│       "produto_cod_barras": "789...",                      │
│       "quantidade": 2,                                      │
│       "complementos": [                                     │
│         {                                                   │
│           "complemento_id": 1,                             │
│           "adicionais": [                                  │
│             { "adicional_id": 3, "quantidade": 1 }        │
│           ]                                                 │
│         }                                                   │
│       ]                                                     │
│     }                                                       │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND PROCESSA                         │
│                                                              │
│  1. Valida complementos obrigatórios                        │
│  2. Calcula preço dos itens selecionados                  │
│  3. Cria snapshot dos complementos no pedido               │
│  4. Salva no banco                                         │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Exemplo Completo: Hambúrguer

### 1. Estrutura no Banco

```
COMPLEMENTO: "Tamanhos"
├── ITEM 1: "Pequeno" (R$ 0,00)
├── ITEM 2: "Médio" (R$ 2,00)
└── ITEM 3: "Grande" (R$ 4,00)

COMPLEMENTO: "Molhos"
├── ITEM 1: "Ketchup" (R$ 0,00)
├── ITEM 2: "Maionese" (R$ 0,00)
└── ITEM 3: "Mostarda" (R$ 1,50)

COMPLEMENTO: "Extras"
├── ITEM 1: "Bacon" (R$ 3,00)
├── ITEM 2: "Queijo Extra" (R$ 2,50)
└── ITEM 3: "Ovo" (R$ 1,00)
```

### 2. Response da API

```json
[
  {
    "id": 1,
    "nome": "Tamanhos",
    "obrigatorio": true,
    "quantitativo": false,
    "permite_multipla_escolha": false,
    "adicionais": [
      { "id": 1, "nome": "Pequeno", "preco": 0.0 },
      { "id": 2, "nome": "Médio", "preco": 2.0 },
      { "id": 3, "nome": "Grande", "preco": 4.0 }
    ]
  },
  {
    "id": 2,
    "nome": "Molhos",
    "obrigatorio": false,
    "quantitativo": false,
    "permite_multipla_escolha": true,
    "adicionais": [
      { "id": 4, "nome": "Ketchup", "preco": 0.0 },
      { "id": 5, "nome": "Maionese", "preco": 0.0 },
      { "id": 6, "nome": "Mostarda", "preco": 1.5 }
    ]
  }
]
```

### 3. Cliente Seleciona

```
Tamanhos (obrigatório, escolha única):
  ○ Pequeno
  ● Médio  ← Selecionado
  ○ Grande

Molhos (opcional, múltipla escolha):
  ☑ Ketchup      ← Selecionado
  ☐ Maionese
  ☑ Mostarda     ← Selecionado
```

### 4. Request do Pedido

```json
{
  "produto_cod_barras": "7891234567890",
  "quantidade": 1,
  "complementos": [
    {
      "complemento_id": 1,
      "adicionais": [
        { "adicional_id": 2, "quantidade": 1 }  // Médio
      ]
    },
    {
      "complemento_id": 2,
      "adicionais": [
        { "adicional_id": 4, "quantidade": 1 }, // Ketchup
        { "adicional_id": 6, "quantidade": 1 }  // Mostarda
      ]
    }
  ]
}
```

### 5. Cálculo do Total

```
Produto: R$ 15,00
+ Tamanho Médio: R$ 2,00
+ Ketchup: R$ 0,00
+ Mostarda: R$ 1,50
─────────────────
Total: R$ 18,50
```

## 🔐 Autenticação

### Admin
```
Headers:
  Authorization: Bearer {admin_token}
```

### Client
```
Headers:
  X-Super-Token: {cliente_token}
```

## 📊 Tabelas no Banco

```
catalogo.complemento_produto
├── id
├── empresa_id
├── nome
├── obrigatorio
├── quantitativo
├── permite_multipla_escolha
└── ...

catalogo.complemento_itens
├── id (adicional_id)
├── complemento_id (FK)
├── nome
├── preco
└── ...

catalogo.produto_complemento_link
├── produto_cod_barras (FK)
├── complemento_id (FK)
└── ordem
```

## 🎯 Regras de Negócio

```
┌─────────────────────────────────────────┐
│  COMPLEMENTO OBRIGATÓRIO                 │
│  └─> Deve selecionar ≥ 1 item           │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  COMPLEMENTO QUANTITATIVO                │
│  └─> Pode escolher quantidade > 1       │
│      Ex: 2x Bacon                        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  MÚLTIPLA ESCOLHA = TRUE                 │
│  └─> Pode selecionar vários itens       │
│      Ex: Ketchup + Maionese + Mostarda │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  MÚLTIPLA ESCOLHA = FALSE               │
│  └─> Apenas 1 item pode ser selecionado│
│      Ex: Pequeno OU Médio OU Grande     │
└─────────────────────────────────────────┘
```

## 🔄 Ciclo de Vida

```
CRIAR COMPLEMENTO
    │
    ├─> Criar itens (adicionais)
    │
    └─> Vincular a produtos
        │
        └─> Cliente vê no cardápio
            │
            └─> Seleciona no pedido
                │
                └─> Backend processa
                    │
                    └─> Salva snapshot no pedido
```

