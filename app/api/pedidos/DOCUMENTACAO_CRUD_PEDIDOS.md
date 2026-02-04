# Documentação CRUD Completa - Pedidos (Delivery, Mesa e Balcão)

Esta documentação descreve **todos os endpoints CRUD** para manipulação de pedidos de **Delivery, Balcão e Mesa**.

## Base URLs

### Admin (Administradores)
```
/api/pedidos/admin
```
**Autenticação:** Token de administrador (Bearer Token)

### Cliente
```
/api/pedidos/client
```
**Autenticação:** Super Token do cliente (Bearer Token)

---

## 📋 Índice

1. [Criar Pedido (CREATE)](#1-criar-pedido-create)
2. [Listar Pedidos (READ)](#2-listar-pedidos-read)
3. [Obter Pedido Específico (READ)](#3-obter-pedido-específico-read)
4. [Atualizar Pedido (UPDATE)](#4-atualizar-pedido-update)
5. [Atualizar Status (UPDATE)](#5-atualizar-status-update)
6. [Cancelar Pedido (DELETE)](#6-cancelar-pedido-delete)
7. [Gerenciar Itens do Pedido](#7-gerenciar-itens-do-pedido)
8. [Endpoints Especiais](#8-endpoints-especiais)

---

## 1. Criar Pedido (CREATE)

### 1.1. Criar Pedido - Admin

Cria um novo pedido (Delivery, Mesa ou Balcão) via painel administrativo.

**Endpoint:**
```
POST /api/pedidos/admin
```

**Headers:**
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Body Request:**
```json
{
  "empresa_id": 1,
  "cliente_id": 123,
  "tipo_pedido": "DELIVERY | MESA | BALCAO",
  "tipo_entrega": "DELIVERY | RETIRADA",
  "origem": "WEB | APP | BALCAO",
  "endereco_id": 456,
  "mesa_codigo": "5",
  "num_pessoas": 4,
  "observacao_geral": "Observação geral do pedido",
  "troco_para": 50.00,
  "cupom_id": 10,
  "meios_pagamento": [
    {
      "id": 1,
      "valor": 100.00
    }
  ],
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "observacao": "Sem cebola",
        "complementos": [
          {
            "complemento_id": 3,
            "adicionais": [
              {
                "adicional_id": 5,
                "quantidade": 1
              }
            ]
          }
        ]
      }
    ],
    "receitas": [
      {
        "receita_id": 7,
        "quantidade": 1,
        "observacao": "Bem passado",
        "complementos": []
      }
    ],
    "combos": [
      {
        "combo_id": 12,
        "quantidade": 1,
        "complementos": []
      }
    ]
  }
}
```

**`meios_pagamento`:** Array de meios de pagamento. O sistema aceita **um ou mais** meios por pedido. Cada item: `{ "id": number, "valor": number }`. A soma dos valores deve igualar o total. Ver **`app/api/pedidos/docs/DOCUMENTACAO_MULTIPLOS_MEIOS_PAGAMENTO_FRONTEND.md`** para o guia completo (Admin e Cliente).

**Resposta — pagamentos/transações:** A resposta do pedido expõe `transacoes` (lista) como fonte da verdade para múltiplas formas. O campo `transacao` (singular) existe por compatibilidade e não deve ser usado quando houver múltiplas transações.

**Campos Obrigatórios por Tipo:**

#### Delivery
- `empresa_id` ✅
- `cliente_id` ✅
- `endereco_id` ✅
- `tipo_pedido`: `"DELIVERY"` ✅
- `produtos` (ao menos um item, receita ou combo) ✅

#### Mesa
- `empresa_id` ✅
- `mesa_codigo` ✅
- `tipo_pedido`: `"MESA"` ✅
- `produtos` (ao menos um item, receita ou combo) ✅

#### Balcão
- `empresa_id` ✅
- `tipo_pedido`: `"BALCAO"` ✅
- `produtos` (ao menos um item, receita ou combo) ✅

**Response (201 Created):**
```json
{
  "id": 789,
  "status": "P",
  "cliente": {
    "id": 123,
    "nome": "João Silva",
    "telefone": "11987654321"
  },
  "empresa_id": 1,
  "tipo_entrega": "DELIVERY",
  "origem": "WEB",
  "subtotal": 195.50,
  "desconto": 5.00,
  "taxa_entrega": 8.00,
  "taxa_servico": 2.50,
  "valor_total": 201.00,
  "observacao_geral": "Observação geral do pedido",
  "data_criacao": "2024-01-15T14:30:00Z",
  "data_atualizacao": "2024-01-15T14:30:00Z",
  "produtos": {
    "itens": [
      {
        "item_id": 1001,
        "produto_cod_barras": "7891234567890",
        "descricao": "Hambúrguer Artesanal",
        "quantidade": 2,
        "preco_unitario": 25.00,
        "observacao": "Sem cebola",
        "complementos": [
          {
            "complemento_id": 3,
            "complemento_nome": "Acompanhamentos",
            "obrigatorio": false,
            "quantitativo": true,
            "total": 5.00,
            "adicionais": [
              {
                "adicional_id": 5,
                "nome": "Bacon Extra",
                "quantidade": 1,
                "preco_unitario": 5.00,
                "total": 5.00
              }
            ]
          }
        ]
      }
    ],
    "receitas": [
      {
        "item_id": 1002,
        "receita_id": 7,
        "nome": "Pizza Margherita",
        "quantidade": 1,
        "preco_unitario": 45.00,
        "observacao": "Bem passado",
        "complementos": []
      }
    ],
    "combos": [
      {
        "combo_id": 12,
        "nome": "Combo Executivo",
        "quantidade": 1,
        "preco_unitario": 50.00,
        "observacao": null,
        "complementos": [
          {
            "complemento_id": 4,
            "complemento_nome": "Bebidas",
            "obrigatorio": true,
            "quantitativo": false,
            "total": 0.00,
            "adicionais": [
              {
                "adicional_id": 8,
                "nome": "Refrigerante",
                "quantidade": 1,
                "preco_unitario": 0.00,
                "total": 0.00
              }
            ]
          }
        ]
      }
    ]
  }
}
```

---

### 1.2. Criar Pedido - Cliente (Checkout)

**Endpoint:**
```
POST /api/pedidos/client/checkout
```

**Headers:**
```
Authorization: Bearer {super_token_cliente}
Content-Type: application/json
```

**Body Request:**
```json
{
  "empresa_id": 1,
  "tipo_pedido": "DELIVERY | MESA | BALCAO",
  "endereco_id": 456,
  "mesa_codigo": "5",
  "num_pessoas": 4,
  "observacao_geral": "Observação geral",
  "troco_para": 50.00,
  "cupom_id": 10,
  "meios_pagamento": [
    {
      "id": 1,
      "valor": 100.00
    }
  ],
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "observacao": "Sem cebola",
        "complementos": [
          {
            "complemento_id": 3,
            "adicionais": [
              {
                "adicional_id": 5,
                "quantidade": 1
              }
            ]
          }
        ]
      }
    ],
    "receitas": [
      {
        "receita_id": 7,
        "quantidade": 1,
        "observacao": "Bem passado",
        "complementos": []
      }
    ],
    "combos": [
      {
        "combo_id": 12,
        "quantidade": 1,
        "complementos": [
          {
            "complemento_id": 4,
            "adicionais": [
              {
                "adicional_id": 8,
                "quantidade": 1
              }
            ]
          }
        ]
      }
    ]
  }
}
```

**Observação:** O `cliente_id` é obtido automaticamente do token de autenticação.

---

### 1.3. Preview do Checkout (Sem Criar)

Calcula os valores do pedido sem criar no banco de dados.

**Endpoint:**
```
POST /api/pedidos/client/checkout/preview
```

**Body Request:**
```json
{
  "empresa_id": 1,
  "tipo_pedido": "DELIVERY",
  "endereco_id": 456,
  "cupom_id": 10,
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "observacao": "Sem cebola",
        "complementos": [
          {
            "complemento_id": 3,
            "adicionais": [
              {
                "adicional_id": 5,
                "quantidade": 1
              }
            ]
          }
        ]
      }
    ],
    "receitas": [
      {
        "receita_id": 7,
        "quantidade": 1,
        "observacao": "Bem passado",
        "complementos": []
      }
    ],
    "combos": [
      {
        "combo_id": 12,
        "quantidade": 1,
        "complementos": [
          {
            "complemento_id": 4,
            "adicionais": [
              {
                "adicional_id": 8,
                "quantidade": 1
              }
            ]
          }
        ]
      }
    ]
  }
}
```

**Response:**
```json
{
  "subtotal": 195.50,
  "taxa_entrega": 8.00,
  "taxa_servico": 2.50,
  "valor_total": 201.00,
  "desconto": 5.00,
  "distancia_km": 2.5,
  "empresa_id": 1,
  "tempo_entrega_minutos": 30
}
```

---

## 2. Listar Pedidos (READ)

### 2.1. Listar Pedidos - Admin

Lista pedidos com filtros avançados (empresa, tipo, status, cliente, mesa, data).

**Endpoint:**
```
GET /api/pedidos/admin
```

**Query Parameters:**
- `empresa_id` (integer, opcional): Filtrar por empresa
- `tipo` (array, opcional): Tipos de pedido (`DELIVERY`, `BALCAO`, `MESA`, `RETIRADA`)
- `status_filter` (array, opcional): Status do pedido (`P`, `I`, `R`, `S`, `E`, `C`, `D`, `X`, `A`)
- `cliente_id` (integer, opcional): Filtrar por cliente
- `mesa_id` (integer, opcional): Filtrar por mesa
- `data_inicio` (date, opcional): Data inicial (YYYY-MM-DD)
- `data_fim` (date, opcional): Data final (YYYY-MM-DD)
- `skip` (integer, padrão: 0): Registros a pular
- `limit` (integer, padrão: 50, máximo: 200): Limite de registros

**Exemplo:**
```
GET /api/pedidos/admin?empresa_id=1&tipo=DELIVERY&status_filter=P&data_inicio=2024-01-01&limit=20
```

**Response (200 OK):**
```json
[
  {
    "id": 789,
    "status": "P",
    "cliente_id": 123,
    "telefone_cliente": "11987654321",
    "empresa_id": 1,
    "tipo_entrega": "DELIVERY",
    "subtotal": 195.50,
    "valor_total": 201.00,
    "data_criacao": "2024-01-15T14:30:00Z",
    "itens": [
      {
        "id": 1001,
        "produto_cod_barras": "7891234567890",
        "quantidade": 2,
        "preco_unitario": 25.00,
        "observacao": "Sem cebola"
      }
    ],
    "produtos": {
      "itens": [
        {
          "item_id": 1001,
          "produto_cod_barras": "7891234567890",
          "descricao": "Hambúrguer Artesanal",
          "quantidade": 2,
          "preco_unitario": 25.00,
          "observacao": "Sem cebola",
          "complementos": []
        }
      ],
      "receitas": [
        {
          "item_id": 1002,
          "receita_id": 7,
          "nome": "Pizza Margherita",
          "quantidade": 1,
          "preco_unitario": 45.00,
          "observacao": "Bem passado",
          "complementos": []
        }
      ],
      "combos": [
        {
          "combo_id": 12,
          "nome": "Combo Executivo",
          "quantidade": 1,
          "preco_unitario": 50.00,
          "observacao": null,
          "complementos": []
        }
      ]
    }
  }
]
```

---

### 2.2. Listar Kanban - Admin

Lista pedidos agrupados por tipo para visualização em kanban.

**Endpoint:**
```
GET /api/pedidos/admin/kanban
```

**Query Parameters:**
- `date_filter` (date, obrigatório): Data alvo (YYYY-MM-DD)
- `empresa_id` (integer, obrigatório): Empresa para filtragem
- `tipo` (string, opcional): Filtrar por tipo (`DELIVERY`, `BALCAO`, `MESA`)
- `limit` (integer, padrão: 500, máximo: 1000): Limite por agrupamento

**Exemplo:**
```
GET /api/pedidos/admin/kanban?date_filter=2024-01-15&empresa_id=1
```

**Response (200 OK):**
```json
{
  "delivery": [
    {
      "id": 789,
      "status": "P",
      "cliente": {
        "id": 123,
        "nome": "João Silva",
        "telefone": "11987654321"
      },
      "valor_total": 101.00,
      "data_criacao": "2024-01-15T14:30:00Z",
      "endereco": "Rua das Flores, 123",
      "numero_pedido": "000001",
      ...
    }
  ],
  "balcao": [...],
  "mesas": [...]
}
```

---

### 2.3. Listar Pedidos - Cliente

Lista todos os pedidos do cliente autenticado (unificado).

**Endpoint:**
```
GET /api/pedidos/client/
```

**Query Parameters:**
- `skip` (integer, padrão: 0): Registros a pular
- `limit` (integer, padrão: 50, máximo: 200): Limite de registros

**Response (200 OK):**
```json
[
  {
    "tipo_pedido": "DELIVERY",
    "criado_em": "2024-01-15T14:30:00Z",
    "atualizado_em": "2024-01-15T14:35:00Z",
    "status_codigo": "P",
    "status_descricao": "Pendente",
    "numero_pedido": "000001",
    "valor_total": 101.00,
    "delivery": {
      "id": 789,
      "status": "P",
      "subtotal": 95.50,
      "valor_total": 101.00,
      "produtos": {
        "itens": [
          {
            "item_id": 1001,
            "produto_cod_barras": "7891234567890",
            "descricao": "Hambúrguer Artesanal",
            "quantidade": 2,
            "preco_unitario": 25.00,
            "observacao": "Sem cebola",
            "complementos": []
          }
        ],
        "receitas": [
          {
            "item_id": 1002,
            "receita_id": 7,
            "nome": "Pizza Margherita",
            "quantidade": 1,
            "preco_unitario": 45.00,
            "observacao": "Bem passado",
            "complementos": []
          }
        ],
        "combos": [
          {
            "combo_id": 12,
            "nome": "Combo Executivo",
            "quantidade": 1,
            "preco_unitario": 50.00,
            "observacao": null,
            "complementos": []
          }
        ]
      }
    },
    "mesa": null,
    "balcao": null
  },
  {
    "tipo_pedido": "MESA",
    ...
    "mesa": {...},
    "delivery": null,
    "balcao": null
  }
]
```

---

## 3. Obter Pedido Específico (READ)

### 3.1. Obter Pedido - Admin

Obtém detalhes completos de um pedido específico.

**Endpoint:**
```
GET /api/pedidos/admin/{pedido_id}
```

**Path Parameters:**
- `pedido_id` (integer, obrigatório): ID do pedido

**Query Parameters:**
- `empresa_id` (integer, opcional): ID da empresa para validação

**Response (200 OK):**
```json
{
  "id": 789,
  "status": "P",
  "cliente": {
    "id": 123,
    "nome": "João Silva",
    "telefone": "11987654321",
    "email": "joao@example.com"
  },
  "endereco": {
    "endereco_selecionado": {
      "id": 456,
      "rua": "Rua das Flores",
      "numero": "123",
      "bairro": "Centro",
      "cidade": "São Paulo",
      "cep": "01234-567"
    },
    "outros_enderecos": []
  },
  "empresa": {
    "id": 1,
    "nome": "Restaurante Exemplo"
  },
  "entregador": {
    "id": 50,
    "nome": "Carlos Entregador"
  },
  "meio_pagamento": {
    "id": 1,
    "nome": "Dinheiro",
    "tipo": "DINHEIRO"
  },
  "cupom": null,
  "transacao": null,
  "tipo_entrega": "DELIVERY",
  "origem": "WEB",
  "subtotal": 195.50,
  "desconto": 5.00,
  "taxa_entrega": 8.00,
  "taxa_servico": 2.50,
  "valor_total": 201.00,
  "previsao_entrega": "2024-01-15T15:00:00Z",
  "distancia_km": 2.5,
  "observacao_geral": "Observação geral",
  "troco_para": 50.00,
  "endereco_snapshot": {},
  "data_criacao": "2024-01-15T14:30:00Z",
  "data_atualizacao": "2024-01-15T14:35:00Z",
  "pagamento": {
    "status": "PENDENTE",
    "esta_pago": false,
    "valor": 201.00,
    "meio_pagamento_nome": "Dinheiro"
  },
  "pago": false,
  "produtos": {
    "itens": [
      {
        "item_id": 1001,
        "produto_cod_barras": "7891234567890",
        "descricao": "Hambúrguer Artesanal",
        "quantidade": 2,
        "preco_unitario": 25.00,
        "observacao": "Sem cebola",
        "complementos": []
      }
    ],
    "receitas": [
      {
        "item_id": 1002,
        "receita_id": 7,
        "nome": "Pizza Margherita",
        "quantidade": 1,
        "preco_unitario": 45.00,
        "observacao": "Bem passado",
        "complementos": []
      }
    ],
    "combos": [
      {
        "combo_id": 12,
        "nome": "Combo Executivo",
        "quantidade": 1,
        "preco_unitario": 50.00,
        "observacao": null,
        "complementos": []
      }
    ]
  }
}
```

---

### 3.2. Obter Histórico do Pedido - Admin

Obtém o histórico completo de alterações de um pedido.

**Endpoint:**
```
GET /api/pedidos/admin/{pedido_id}/historico
```

**Response (200 OK):**
```json
{
  "pedido_id": 789,
  "historico": [
    {
      "id": 1,
      "tipo_operacao": "PEDIDO_CRIADO",
      "status_anterior": null,
      "status_novo": "P",
      "descricao": "Pedido 000001 criado",
      "usuario_id": 10,
      "cliente_id": 123,
      "data_operacao": "2024-01-15T14:30:00Z"
    },
    {
      "id": 2,
      "tipo_operacao": "STATUS_ALTERADO",
      "status_anterior": "P",
      "status_novo": "R",
      "descricao": "Status alterado de P para R",
      "usuario_id": 10,
      "data_operacao": "2024-01-15T14:35:00Z"
    }
  ]
}
```

---

## 4. Atualizar Pedido (UPDATE)

### 4.1. Atualizar Pedido Completo - Admin

Atualiza informações gerais de um pedido (endereço, meio de pagamento, cupom, observações).

**Endpoint:**
```
PUT /api/pedidos/admin/{pedido_id}
```

**Body Request:**
```json
{
  "cliente_id": 123,
  "mesa_codigo": "5",
  "num_pessoas": 6,
  "endereco_id": 789,
  "meio_pagamento_id": 2,
  "cupom_id": 15,
  "observacoes": "Nova observação",
  "troco_para": 60.00,
  "pagamentos": [
    {
      "id": 2,
      "valor": 120.00
    }
  ]
}
```

**Campos Opcionais:**
- `cliente_id`: Reatribuir cliente
- `mesa_codigo`: Alterar mesa (para pedidos de mesa/balcão)
- `num_pessoas`: Atualizar número de pessoas (mesa)
- `endereco_id`: Alterar endereço (delivery)
- `meio_pagamento_id`: Alterar meio de pagamento
- `cupom_id`: Aplicar/remover cupom
- `observacoes`: Atualizar observações
- `troco_para`: Atualizar valor de troco
- `pagamentos`: Atualizar meios de pagamento parciais (aceita **múltiplos**; lista `[{ "id", "valor" }]`). Ver `app/api/pedidos/docs/DOCUMENTACAO_MULTIPLOS_MEIOS_PAGAMENTO_FRONTEND.md`.

**Response (200 OK):**
```json
{
  "id": 789,
  "status": "P",
  ...
  "observacoes": "Nova observação",
  "troco_para": 60.00,
  ...
}
```

---

### 4.2. Atualizar Observações - Admin

Atualiza apenas as observações do pedido.

**Endpoint:**
```
PATCH /api/pedidos/admin/{pedido_id}/observacoes
```

**Body Request:**
```json
{
  "observacoes": "Nova observação geral do pedido"
}
```

**Response (200 OK):**
```json
{
  "id": 789,
  ...
  "observacao_geral": "Nova observação geral do pedido",
  ...
}
```

---

### 4.3. Editar Pedido - Cliente (DEPRECATED)

⚠️ **DEPRECATED**: Use `/api/pedidos/{pedido_id}/editar` ao invés deste endpoint.

**Endpoint:**
```
PUT /api/pedidos/client/{pedido_id}/editar
```

**Body Request:**
```json
{
  "meio_pagamento_id": 2,
  "endereco_id": 789,
  "cupom_id": 15,
  "observacao_geral": "Nova observação",
  "troco_para": 60.00
}
```

---

## 5. Atualizar Status (UPDATE)

### 5.1. Atualizar Status do Pedido - Admin

Altera o status de um pedido.

**Endpoint:**
```
PATCH /api/pedidos/admin/{pedido_id}/status
```

**Body Request:**
```json
{
  "status": "P | I | R | S | E | C | D | X | A"
}
```

**Status Disponíveis:**
- `P`: Pendente
- `I`: Pendente Impressão / Em Impressão
- `R`: Em Preparo / Preparando
- `S`: Saiu para entrega (apenas delivery)
- `E`: Entregue/Concluído
- `C`: Cancelado
- `D`: Editado
- `X`: Em edição
- `A`: Aguardando pagamento

**Response (200 OK):**
```json
{
  "id": 789,
  "status": "R",
  ...
}
```

---

### 5.2. Fechar Conta - Admin

Fecha a conta de um pedido (mesa/balcão).

**Endpoint:**
```
PATCH /api/pedidos/admin/{pedido_id}/fechar-conta
```

**Body Request:**
```json
{
  "meio_pagamento_id": 1,
  "troco_para": 50.00
}
```

**Campos Opcionais:**
- `meio_pagamento_id`: Meio de pagamento utilizado
- `troco_para`: Valor para troco

**Response (200 OK):**
```json
{
  "id": 789,
  "status": "E",
  ...
}
```

---

### 5.3. Reabrir Pedido - Admin

Reabre um pedido fechado.

**Endpoint:**
```
PATCH /api/pedidos/admin/{pedido_id}/reabrir
```

**Response (200 OK):**
```json
{
  "id": 789,
  "status": "P",
  ...
}
```

---

### 5.4. Marcar Pedido como Pago - Admin

Marca um pedido como **pago** sem alterar o **status** do pedido.

**Endpoint:**
```
PATCH /api/pedidos/admin/{pedido_id}/marcar-pedido-pago
```

**Body Request (opcional):**
```json
{
  "meio_pagamento_id": 1
}
```

**Regras / Validações:**
- Se `meio_pagamento_id` vier no body, o backend **valida** (ativo) e salva no pedido.
- Se o body vier **vazio/omitido**, o pedido **precisa já ter** um meio de pagamento definido (ex.: `meio_pagamento_id` no pedido).
- Se não houver meio de pagamento no pedido e também não vier no payload → **400 Bad Request**.

**Response (200 OK):**
```json
{
  "id": 789,
  "status": "P",
  "pago": true,
  "meio_pagamento": {
    "id": 1,
    "nome": "Dinheiro",
    "tipo": "DINHEIRO"
  },
  ...
}
```

---

## 6. Cancelar Pedido (DELETE)

### 6.1. Cancelar Pedido - Admin

Cancela um pedido (soft delete - status = "C").

**Endpoint:**
```
DELETE /api/pedidos/admin/{pedido_id}
```

**Response (200 OK):**
```json
{
  "id": 789,
  "status": "C",
  ...
}
```

**Observações:**
- O pedido não é removido fisicamente do banco
- O status é alterado para "C" (Cancelado)
- O histórico é registrado automaticamente

---

## 7. Gerenciar Itens do Pedido

### 7.1. Adicionar Item ao Pedido - Admin

Adiciona um produto, receita ou combo a um pedido existente.

**Endpoint:**
```
POST /api/pedidos/admin/{pedido_id}/itens
```

**Query Parameters:**
- `tipo` (string, opcional): Tipo de pedido (`DELIVERY`, `BALCAO`, `MESA`) - apenas para validação

**Body Request:**
```json
{
  "acao": "ADD",
  "produto_cod_barras": "7891234567890",
  "quantidade": 2,
  "observacao": "Sem cebola",
  "complementos": [
    {
      "complemento_id": 3,
      "adicionais": [
        {
          "adicional_id": 5,
          "quantidade": 1
        }
      ]
    }
  ]
}
```

**Ou adicionar Receita:**
```json
{
  "acao": "ADD",
  "receita_id": 7,
  "quantidade": 1,
  "observacao": "Bem passado",
  "complementos": []
}
```

**Ou adicionar Combo:**
```json
{
  "acao": "ADD",
  "combo_id": 12,
  "quantidade": 1,
  "complementos": []
}
```

**Regras:**
- É necessário informar **exatamente um** dos campos: `produto_cod_barras`, `receita_id` ou `combo_id`
- `quantidade` é obrigatória (mínimo: 1)
- `complementos` são opcionais e suportados para Delivery, Mesa e Balcão

**Response (200 OK):**
```json
{
  "id": 789,
  "status": "P",
  "valor_total": 225.50,
  "itens": [
    {
      "id": 1001,
      "produto_cod_barras": "7891234567890",
      "quantidade": 2,
      "preco_unitario": 25.00,
      "observacao": "Sem cebola"
    },
    {
      "id": 1003,
      "produto_cod_barras": "7891234567890",
      "quantidade": 2,
      "preco_unitario": 25.00,
      "observacao": "Sem cebola"
    }
  ],
  "produtos": {
    "itens": [
      {
        "item_id": 1001,
        "produto_cod_barras": "7891234567890",
        "descricao": "Hambúrguer Artesanal",
        "quantidade": 2,
        "preco_unitario": 25.00,
        "observacao": "Sem cebola",
        "complementos": []
      },
      {
        "item_id": 1003,
        "produto_cod_barras": "7891234567890",
        "descricao": "Hambúrguer Artesanal",
        "quantidade": 2,
        "preco_unitario": 25.00,
        "observacao": "Sem cebola",
        "complementos": [
          {
            "complemento_id": 3,
            "complemento_nome": "Acompanhamentos",
            "obrigatorio": false,
            "quantitativo": true,
            "total": 5.00,
            "adicionais": [
              {
                "adicional_id": 5,
                "nome": "Bacon Extra",
                "quantidade": 1,
                "preco_unitario": 5.00,
                "total": 5.00
              }
            ]
          }
        ]
      }
    ],
    "receitas": [
      {
        "item_id": 1002,
        "receita_id": 7,
        "nome": "Pizza Margherita",
        "quantidade": 1,
        "preco_unitario": 45.00,
        "observacao": "Bem passado",
        "complementos": []
      }
    ],
    "combos": [
      {
        "combo_id": 12,
        "nome": "Combo Executivo",
        "quantidade": 1,
        "preco_unitario": 50.00,
        "observacao": null,
        "complementos": []
      }
    ]
  }
}
```

---

### 7.2. Atualizar Item do Pedido - Admin

Atualiza quantidade, observação, receita ou complementos de um item existente.

**Endpoint:**
```
PATCH /api/pedidos/admin/{pedido_id}/itens/{item_id}
```

**Path Parameters:**
- `pedido_id` (integer, obrigatório): ID do pedido
- `item_id` (integer, obrigatório): ID do item

**Body Request:**

⚠️ **O campo `acao` é OBRIGATÓRIO** e deve ser sempre `"UPDATE"` para este endpoint.

**Schema:**
```json
{
  "acao": "UPDATE",  // ⚠️ OBRIGATÓRIO
  "quantidade": 3,  // Opcional: nova quantidade
  "observacao": "string",  // Opcional: nova observação
  "receita_id": 1,  // Opcional: ID da receita (se for receita)
  "complementos": [  // Opcional: lista de complementos atualizados
    {
      "complemento_id": 1,
      "adicionais": [
        {
          "adicional_id": 2,
          "quantidade": 3
        }
      ]
    }
  ]
}
```

**Exemplos:**

#### Atualizar Quantidade e Observação
```json
{
  "acao": "UPDATE",
  "quantidade": 3,
  "observacao": "Nova observação"
}
```

#### Atualizar Receita com Complementos
```json
{
  "acao": "UPDATE",
  "quantidade": 1,
  "receita_id": 1,
  "complementos": [
    {
      "complemento_id": 1,
      "adicionais": [
        {
          "adicional_id": 2,
          "quantidade": 3
        }
      ]
    }
  ]
}
```

#### Atualizar Apenas Quantidade
```json
{
  "acao": "UPDATE",
  "quantidade": 5
}
```

**⚠️ Limitações por Tipo:**
- **Delivery**: ✅ Suporta atualização completa (quantidade, observação, receita e complementos)
- **Mesa**: ❌ **NÃO suporta** atualização parcial. Use remover e adicionar novamente.
- **Balcão**: ❌ **NÃO suporta** atualização parcial. Use remover e adicionar novamente.

**Response (200 OK):**
```json
{
  "id": 789,
  "valor_total": 205.00,
  "produtos": {
    "itens": [
      {
        "item_id": 1002,
        "produto_cod_barras": "7891234567890",
        "descricao": "Hambúrguer Artesanal",
        "quantidade": 3,
        "preco_unitario": 25.00,
        "observacao": "Nova observação",
        "complementos": []
      }
    ],
    "receitas": [
      {
        "item_id": 1003,
        "receita_id": 7,
        "nome": "Pizza Margherita",
        "quantidade": 1,
        "preco_unitario": 45.00,
        "observacao": "Bem passado",
        "complementos": []
      }
    ],
    "combos": [
      {
        "combo_id": 12,
        "nome": "Combo Executivo",
        "quantidade": 1,
        "preco_unitario": 50.00,
        "observacao": null,
        "complementos": []
      }
    ]
  }
}
```

---

### 7.3. Remover Item do Pedido - Admin

Remove um item de um pedido.

**Endpoint:**
```
DELETE /api/pedidos/admin/{pedido_id}/itens/{item_id}
```

**Path Parameters:**
- `pedido_id` (integer, obrigatório): ID do pedido
- `item_id` (integer, obrigatório): ID do item

**Response (200 OK):**
```json
{
  "id": 789,
  "valor_total": 145.50,
  "produtos": {
    "itens": [
      {
        "item_id": 1001,
        "produto_cod_barras": "7891234567890",
        "descricao": "Hambúrguer Artesanal",
        "quantidade": 2,
        "preco_unitario": 25.00,
        "observacao": "Sem cebola",
        "complementos": []
      }
    ],
    "receitas": [
      {
        "item_id": 1002,
        "receita_id": 7,
        "nome": "Pizza Margherita",
        "quantidade": 1,
        "preco_unitario": 45.00,
        "observacao": "Bem passado",
        "complementos": []
      }
    ],
    "combos": [
      {
        "combo_id": 12,
        "nome": "Combo Executivo",
        "quantidade": 1,
        "preco_unitario": 50.00,
        "observacao": null,
        "complementos": []
      }
    ]
  }
}
```

---

### 7.4. Atualizar Item - Cliente

Atualiza itens de um pedido do cliente.

**Endpoint:**
```
PUT /api/pedidos/client/{pedido_id}/itens
```

**Body Request:**
```json
{
  "id": 1002,
  "produto_cod_barras": "7891234567890",
  "quantidade": 3,
  "observacao": "Nova observação",
  "acao": "novo-item | atualizar | remover"
}
```

**Validações:**
- O pedido deve pertencer ao cliente autenticado
- O pedido não pode estar fechado ou cancelado

---

## 8. Endpoints Especiais

### 8.1. Atualizar Entregador - Admin

Associa ou remove um entregador de um pedido de delivery.

**Endpoint:**
```
PUT /api/pedidos/admin/{pedido_id}/entregador
```

**Body Request:**
```json
{
  "entregador_id": 50
}
```

**Para remover entregador:**
```json
{
  "entregador_id": null
}
```

**Response (200 OK):**
```json
{
  "id": 789,
  "entregador_id": 50,
  ...
}
```

---

### 8.2. Remover Entregador - Admin

Remove o entregador de um pedido.

**Endpoint:**
```
DELETE /api/pedidos/admin/{pedido_id}/entregador
```

**Response (200 OK):**
```json
{
  "id": 789,
  "entregador_id": null,
  ...
}
```

---

## 📊 Resumo de Status e Tipos

### Status do Pedido (`PedidoStatusEnum`)
- `P`: Pendente
- `I`: Pendente Impressão / Em Impressão
- `R`: Em Preparo / Preparando
- `S`: Saiu para entrega (apenas delivery)
- `E`: Entregue/Concluído
- `C`: Cancelado
- `D`: Editado
- `X`: Em edição
- `A`: Aguardando pagamento

### Tipo de Entrega (`TipoEntregaEnum`)
- `DELIVERY`: Entrega em domicílio
- `RETIRADA`: Cliente retira no estabelecimento
- `BALCAO`: Pedido no balcão
- `MESA`: Pedido em mesa

### Tipo de Pedido (`TipoPedidoCheckoutEnum`)
- `DELIVERY`: Pedido de delivery
- `MESA`: Pedido de mesa
- `BALCAO`: Pedido de balcão

### Origem do Pedido (`OrigemPedidoEnum`)
- `WEB`: Pedido via web
- `APP`: Pedido via aplicativo móvel
- `BALCAO`: Pedido feito no balcão

---

## 🔒 Validações e Regras de Negócio

### Validações Gerais

1. **Produtos**: É obrigatório informar ao menos um produto (item, receita ou combo)
2. **Status**: Pedidos fechados (`E`) ou cancelados (`C`) não podem ser editados diretamente
3. **Empresa**: Todos os produtos devem pertencer à empresa do pedido
4. **Recálculo Automático**: O valor total é recalculado automaticamente após alterações
5. **Histórico**: Todas as operações são registradas no histórico para auditoria

### Validações por Tipo

#### Delivery
- `cliente_id` é obrigatório
- `endereco_id` é obrigatório
- Suporta atualização parcial de itens (PATCH)
- Suporta entregador

#### Mesa
- `mesa_codigo` é obrigatório
- `num_pessoas` é opcional (1-50)
- NÃO suporta atualização parcial de itens (remover + adicionar)
- Não suporta entregador

#### Balcão
- `mesa_codigo` é opcional
- NÃO suporta atualização parcial de itens (remover + adicionar)
- Não suporta entregador

---

## 📝 Códigos de Status HTTP

- `200 OK`: Operação realizada com sucesso
- `201 Created`: Recurso criado com sucesso
- `400 Bad Request`: Dados inválidos ou validação falhou
- `401 Unauthorized`: Token ausente ou inválido
- `403 Forbidden`: Sem permissão para acessar o recurso
- `404 Not Found`: Pedido ou recurso não encontrado
- `422 Unprocessable Entity`: Erro de validação de dados
- `500 Internal Server Error`: Erro interno do servidor

---

## 🚀 Exemplos de Uso

### Criar Pedido Delivery Completo

```bash
curl -X POST "https://api.exemplo.com/api/pedidos/admin" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "empresa_id": 1,
    "cliente_id": 123,
    "tipo_pedido": "DELIVERY",
    "endereco_id": 456,
    "produtos": {
      "itens": [
        {
          "produto_cod_barras": "7891234567890",
          "quantidade": 2,
          "observacao": "Sem cebola",
          "complementos": [
            {
              "complemento_id": 3,
              "adicionais": [
                {
                  "adicional_id": 5,
                  "quantidade": 1
                }
              ]
            }
          ]
        }
      ],
      "receitas": [
        {
          "receita_id": 7,
          "quantidade": 1,
          "observacao": "Bem passado",
          "complementos": []
        }
      ],
      "combos": [
        {
          "combo_id": 12,
          "quantidade": 1,
          "complementos": [
            {
              "complemento_id": 4,
              "adicionais": [
                {
                  "adicional_id": 8,
                  "quantidade": 1
                }
              ]
            }
          ]
        }
      ]
    },
    "meios_pagamento": [
      {
        "id": 1,
        "valor": 201.00
      }
    ]
  }'
```

### Adicionar Item a um Pedido

```bash
curl -X POST "https://api.exemplo.com/api/pedidos/admin/789/itens" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "acao": "ADD",
    "produto_cod_barras": "7891234567890",
    "quantidade": 1,
    "complementos": [
      {
        "complemento_id": 3,
        "adicionais": [
          {
            "adicional_id": 5,
            "quantidade": 1
          }
        ]
      }
    ]
  }'
```

### Alterar Status do Pedido

```bash
curl -X PATCH "https://api.exemplo.com/api/pedidos/admin/789/status" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "R"
  }'
```

---

## 📚 Documentação Relacionada

- [Documentação de Endpoints - Gerenciamento de Produtos em Pedidos](./ENDPOINTS_PRODUTOS_PEDIDOS.md)
- Documentação de autenticação (consulte `/api/auth`)
- Documentação de empresas (consulte `/api/empresas`)
- Documentação de clientes (consulte `/api/clientes`)

---

## 💡 Dicas e Boas Práticas

1. **Sempre valide o status** antes de fazer alterações em pedidos
2. **Use o histórico** para rastrear alterações importantes
3. **Para Mesa/Balcão**, use remover + adicionar ao invés de atualizar itens
4. **Preview antes de criar** pedidos complexos usando `/checkout/preview`
5. **Filtre por empresa** em listagens para melhor performance
6. **Use paginação** (`skip`/`limit`) em listagens grandes

---

**Última atualização:** 2024-01-15  
**Versão da API:** 1.0
