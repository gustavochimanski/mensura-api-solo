# 📖 Explicação Completa - Relacionamento N:N entre Complementos e Itens

## 🎯 O Que Mudou?

### Antes (1:N)
```
Complemento
  └── Item 1 (vinculado apenas a este complemento)
  └── Item 2 (vinculado apenas a este complemento)
```

**Problema**: Cada item só podia estar em um complemento. Se você quisesse "Ketchup" em "Molhos" e "Extras", tinha que criar dois itens diferentes.

### Agora (N:N)
```
Complemento "Molhos"
  ├── Item "Ketchup" ←
  └── Item "Maionese"

Complemento "Extras"
  ├── Item "Ketchup" ← Mesmo item!
  └── Item "Bacon"
```

**Solução**: Um item pode estar em vários complementos. Criar "Ketchup" uma vez e usar onde quiser!

---

## 🔄 Como Funciona

### 1. Itens são Independentes

Os itens são criados **independentemente** dos complementos:

```http
POST /api/catalogo/admin/complementos/itens/
{
  "empresa_id": 1,
  "nome": "Ketchup",
  "preco": 0.0
}
```

**Resultado**: Item criado, mas ainda não vinculado a nenhum complemento.

### 2. Complementos são Criados Separadamente

```http
POST /api/catalogo/admin/complementos/
{
  "empresa_id": 1,
  "nome": "Molhos"
}
```

**Resultado**: Complemento criado, mas ainda sem itens.

### 3. Vínculos são Criados Depois

```http
POST /api/catalogo/admin/complementos/1/itens/vincular
{
  "item_ids": [1, 2],
  "ordens": [0, 1]
}
```

**Resultado**: Itens 1 e 2 agora estão vinculados ao complemento 1.

### 4. Reutilização

```http
POST /api/catalogo/admin/complementos/2/itens/vincular
{
  "item_ids": [1],  // Mesmo item "Ketchup"!
  "ordens": [0]
}
```

**Resultado**: O item 1 (Ketchup) agora está em 2 complementos diferentes!

---

## 📊 Estrutura de Dados

### Tabela: `complemento_itens` (Itens)
```sql
id | empresa_id | nome     | preco
---|------------|----------|-------
1  | 1          | Ketchup  | 0.00
2  | 1          | Maionese | 0.00
3  | 1          | Bacon    | 3.00
```

### Tabela: `complemento_produto` (Complementos)
```sql
id | empresa_id | nome
---|------------|-------
1  | 1          | Molhos
2  | 1          | Extras
```

### Tabela: `complemento_item_link` (Vínculos N:N)
```sql
complemento_id | item_id | ordem
---------------|---------|------
1              | 1       | 0     ← Ketchup no Molhos
1              | 2       | 1     ← Maionese no Molhos
2              | 1       | 0     ← Ketchup no Extras (reutilizado!)
2              | 3       | 1     ← Bacon no Extras
```

---

## 💡 Casos de Uso

### Caso 1: Item em Múltiplos Complementos

**Cenário**: "Ketchup" deve aparecer em "Molhos" e "Extras"

```typescript
// 1. Criar item uma vez
const ketchup = await criarItem({
  empresa_id: 1,
  nome: "Ketchup",
  preco: 0.0
});

// 2. Vincular ao complemento "Molhos"
await vincularItens(molhosId, {
  item_ids: [ketchup.id],
  ordens: [0]
});

// 3. Vincular ao complemento "Extras" (mesmo item!)
await vincularItens(extrasId, {
  item_ids: [ketchup.id],
  ordens: [0]
});
```

**Vantagem**: Se mudar o preço do Ketchup, atualiza em ambos os complementos automaticamente!

### Caso 2: Ordem Diferente por Complemento

**Cenário**: "Ketchup" deve ser primeiro em "Molhos" mas segundo em "Extras"

```typescript
// Em "Molhos": ordem 0 (primeiro)
await vincularItens(molhosId, {
  item_ids: [ketchup.id, maionese.id],
  ordens: [0, 1]  // Ketchup primeiro
});

// Em "Extras": ordem 1 (segundo)
await vincularItens(extrasId, {
  item_ids: [bacon.id, ketchup.id],
  ordens: [0, 1]  // Bacon primeiro, Ketchup segundo
});
```

**Resultado**: Mesmo item, ordens diferentes em cada complemento!

### Caso 3: Atualizar Item Afeta Todos os Complementos

```typescript
// Atualizar preço do Ketchup
await atualizarItem(ketchupId, {
  preco: 1.50  // Novo preço
});
```

**Resultado**: O preço atualiza em "Molhos" e "Extras" automaticamente!

---

## 🔧 Endpoints por Funcionalidade

### Gerenciar Itens (CRUD Independente)

| Ação | Endpoint | Quando Usar |
|------|----------|-------------|
| Criar | `POST /itens/` | Criar novo item |
| Listar | `GET /itens/` | Ver todos os itens da empresa |
| Buscar | `GET /itens/{id}` | Ver detalhes de um item |
| Atualizar | `PUT /itens/{id}` | Mudar preço, nome, etc |
| Deletar | `DELETE /itens/{id}` | Remover item (remove de todos os complementos) |

### Gerenciar Vínculos

| Ação | Endpoint | Quando Usar |
|------|----------|-------------|
| Vincular | `POST /{complemento_id}/itens/vincular` | Adicionar itens a um complemento |
| Desvincular | `DELETE /{complemento_id}/itens/{item_id}` | Remover item de um complemento |
| Listar | `GET /{complemento_id}/itens` | Ver itens de um complemento |
| Ordenar | `PUT /{complemento_id}/itens/ordem` | Mudar ordem dos itens |

---

## ⚠️ Importante Saber

### 1. Deleção

- **Deletar Item**: Remove o item de **todos** os complementos
- **Deletar Complemento**: Remove apenas os vínculos, **não deleta** os itens
- **Desvincular**: Remove apenas o vínculo, item e complemento permanecem

### 2. Validações

- ✅ Itens e complementos devem ser da mesma empresa
- ✅ Um item só pode ser vinculado uma vez ao mesmo complemento
- ✅ A ordem é específica por complemento

### 3. Ordem

- A ordem é armazenada na tabela de associação (`complemento_item_link`)
- Mesmo item pode ter ordens diferentes em complementos diferentes
- Use `PUT /{complemento_id}/itens/ordem` para atualizar

---

## 📝 Exemplo Completo

```typescript
// === PASSO 1: Criar Itens ===
const ketchup = await criarItem({
  empresa_id: 1,
  nome: "Ketchup",
  preco: 0.0
}); // id: 1

const maionese = await criarItem({
  empresa_id: 1,
  nome: "Maionese",
  preco: 0.0
}); // id: 2

const bacon = await criarItem({
  empresa_id: 1,
  nome: "Bacon",
  preco: 3.0
}); // id: 3

// === PASSO 2: Criar Complementos ===
const molhos = await criarComplemento({
  empresa_id: 1,
  nome: "Molhos"
}); // id: 1

const extras = await criarComplemento({
  empresa_id: 1,
  nome: "Extras"
}); // id: 2

// === PASSO 3: Vincular Itens aos Complementos ===
// Molhos: Ketchup e Maionese
await vincularItens(1, {
  item_ids: [1, 2],  // Ketchup e Maionese
  ordens: [0, 1]
});

// Extras: Ketchup (reutilizado!) e Bacon
await vincularItens(2, {
  item_ids: [1, 3],  // Ketchup e Bacon
  ordens: [0, 1]
});

// === RESULTADO ===
// Complemento "Molhos" tem: Ketchup, Maionese
// Complemento "Extras" tem: Ketchup, Bacon
// Item "Ketchup" está em 2 complementos!
```

---

## 🎯 Benefícios

✅ **Reutilização**: Criar item uma vez, usar em vários lugares  
✅ **Manutenção**: Atualizar uma vez, reflete em todos os lugares  
✅ **Flexibilidade**: Adicionar/remover itens facilmente  
✅ **Organização**: Itens são entidades independentes  
✅ **Economia**: Não precisa duplicar dados

---

**Documentação Completa**: `docs/API_COMPLEMENTOS_NN_COMPLETA.md`  
**Resumo Rápido**: `docs/API_COMPLEMENTOS_NN_RESUMO.md`

