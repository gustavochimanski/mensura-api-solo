# 📋 Documentação - API Kanban (Frontend)

## 🎯 O que mudou?

O endpoint do Kanban agora retorna os pedidos **agrupados por categoria** ao invés de uma lista única. Isso resolve o problema de IDs duplicados entre diferentes tipos de pedidos.

---

## 📡 Endpoint

```
GET /api/pedidos/kanban
```

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | number | ✅ Sim | ID da empresa |
| `date_filter` | string (YYYY-MM-DD) | ❌ Não | Filtrar por data específica |
| `limit` | number | ❌ Não | Limite por categoria (padrão: 500, máx: 1000) |

### Autenticação

Requer token Bearer de admin no header:
```
Authorization: Bearer <seu_token>
```

---

## 📦 Formato de Resposta

### Antes (❌ Antigo)
```json
[
  { "id": 1, "tipo_pedido": "DELIVERY", ... },
  { "id": 1, "tipo_pedido": "MESA", ... },      // ❌ ID duplicado!
  { "id": 2, "tipo_pedido": "DELIVERY", ... }
]
```

### Agora (✅ Novo)
```json
{
  "delivery": [
    { "id": 1, "tipo_pedido": "DELIVERY", ... },
    { "id": 2, "tipo_pedido": "DELIVERY", ... }
  ],
  "balcao": [
    { "id": 1, "tipo_pedido": "BALCAO", ... },
    { "id": 3, "tipo_pedido": "BALCAO", ... }
  ],
  "mesas": [
    { "id": 1, "tipo_pedido": "MESA", ... },
    { "id": 5, "tipo_pedido": "MESA", ... }
  ]
}
```

---

## 💻 Exemplos de Uso

### TypeScript / JavaScript

```typescript
interface PedidoKanban {
  id: number;
  status: string;
  cliente: Cliente | null; // contém id / nome / telefone etc.
  valor_total: number;
  data_criacao: string;
  observacao_geral: string | null;
  endereco: string | null;
  meio_pagamento: object | null;
  entregador: { id: number; nome: string } | null;
  pagamento: object | null;
  acertado_entregador: boolean | null;
  tempo_entrega_minutos: number | null;
  troco_para: number | null;
  tipo_pedido: "DELIVERY" | "MESA" | "BALCAO";
}
interface PedidoKanban {
  id: number;
  status: string;
  cliente: Cliente | null;
  valor_total: number;
  data_criacao: string;
  observacao_geral: string | null;
  endereco: string | null;
  meio_pagamento: object | null;
  entregador: { id: number; nome: string } | null;
  pagamento: object | null;
  acertado_entregador: boolean | null;
  tempo_entrega_minutos: number | null;
  troco_para: number | null;
  tipo_pedido: "DELIVERY" | "MESA" | "BALCAO";
}

interface KanbanResponse {
  delivery: PedidoKanban[];
  balcao: PedidoKanban[];
  mesas: PedidoKanban[];
}

// Buscar pedidos
async function buscarKanban(empresaId: number, data?: string) {
  const params = new URLSearchParams({
    empresa_id: empresaId.toString(),
    ...(data && { date_filter: data }),
    limit: "500"
  });

  const response = await fetch(
    `/api/delivery/admin/pedidos/kanban?${params}`,
    {
      headers: {
        "Authorization": `Bearer ${seuToken}`
      }
    }
  );

  const dados: KanbanResponse = await response.json();
  return dados;
}

// Exemplo de uso
const kanban = await buscarKanban(1, "2024-01-15");

// Acessar pedidos por categoria
console.log(kanban.delivery);    // Array de pedidos delivery
console.log(kanban.balcao);      // Array de pedidos balcão
console.log(kanban.mesas);       // Array de pedidos mesas

// Combinar todos os pedidos (se necessário)
const todosPedidos = [
  ...kanban.delivery,
  ...kanban.balcao,
  ...kanban.mesas
];

// Filtrar por status em uma categoria específica
const pedidosPendentes = kanban.delivery.filter(
  p => p.status === "P"
);
```

---

## 🔑 Pontos Importantes

### ✅ IDs são únicos por categoria
- Cada categoria mantém seus IDs originais da respectiva tabela
- **Não há mais conflitos de ID** entre categorias diferentes
- Exemplo: pode existir `delivery[0].id = 1` e `mesas[0].id = 1` sem problema

### ✅ Cada categoria é independente
- `delivery`: IDs da tabela `pedidos_dv`
- `balcao`: IDs da tabela `pedidos_balcao`
- `mesas`: IDs da tabela `pedidos_mesa`

### ✅ Ordenação
- Cada array já vem ordenado por `data_criacao` (mais recentes primeiro)
- O `limit` se aplica **por categoria**, não no total

### ✅ Campos principais
- `cliente` agora contém o objeto completo (id, nome, telefone, etc.). Os campos `cliente_id`, `nome_cliente` e `telefone_cliente` foram removidos.
- `tipo_pedido` continua presente, embora seja redundante se você já souber a coluna.

---

## 🔄 Migração do Código Antigo

### Se você tinha algo assim:

```typescript
// ❌ ANTES
const pedidos = await buscarKanban();
pedidos.forEach(pedido => {
  // Renderizar card...
});
```

### Mude para:

```typescript
// ✅ AGORA
const { delivery, balcao, mesas } = await buscarKanban();

// Opção 1: Renderizar cada categoria separadamente
renderCategoria("Delivery", delivery);
renderCategoria("Balcão", balcao);
renderCategoria("Mesas", mesas);

// Opção 2: Combinar todas se precisar
const todos = [...delivery, ...balcao, ...mesas];
todos.forEach(pedido => {
  // Renderizar card...
});
```

---

## 📊 Estrutura do Pedido

Cada pedido no array possui:

```typescript
{
  id: number,                    // ID original da tabela
  status: string,                // Status do pedido
  cliente: Cliente | null,       // Objeto completo (id, nome, telefone...)
  valor_total: number,
  data_criacao: string,          // ISO 8601
  observacao_geral: string | null,
  endereco: string | null,
  meio_pagamento: object | null,
  entregador: { id: number; nome: string } | null,
  pagamento: object | null,
  acertado_entregador: boolean | null,
  tempo_entrega_minutos: number | null,
  troco_para: number | null,
  tipo_pedido: "DELIVERY" | "MESA" | "BALCAO"
}
```

---

## ❓ FAQ

**P: Por que mudou?**  
R: Para resolver conflitos de IDs duplicados entre tabelas diferentes.

**P: Preciso mudar minha lógica de renderização?**  
R: Se você renderiza todos os pedidos juntos, precisa combinar os arrays. Se já separava por tipo, apenas use a categoria correspondente.

**P: Os IDs ainda são únicos globalmente?**  
R: Não. IDs podem se repetir entre categorias, mas cada categoria mantém unicidade interna. Use `tipo_pedido` + `id` se precisar de identificador único global.

**P: Como criar uma chave única para React?**  
R: Use `tipo_pedido + id`: `key={`${pedido.tipo_pedido}-${pedido.id}`}`

---

## 🆘 Suporte

Em caso de dúvidas, consulte a documentação Swagger em `/docs` ou entre em contato com o time de backend.

