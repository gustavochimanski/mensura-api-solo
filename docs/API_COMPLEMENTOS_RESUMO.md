# 📋 Resumo Rápido - API Complementos

## 🎯 Conceitos

```
Complemento = Grupo de Itens
  └── Item (Adicional) = Opção individual dentro do grupo
```

**Exemplo:**
- **Complemento**: "Molhos"
  - Item 1: "Ketchup" (R$ 0,00)
  - Item 2: "Maionese" (R$ 0,00)
  - Item 3: "Mostarda" (R$ 1,50)

---

## 📊 Estrutura de Dados

### Complemento
```json
{
  "id": 1,
  "nome": "Molhos",
  "obrigatorio": false,
  "quantitativo": false,
  "permite_multipla_escolha": true,
  "adicionais": [
    { "id": 1, "nome": "Ketchup", "preco": 0.0 },
    { "id": 2, "nome": "Maionese", "preco": 0.0 }
  ]
}
```

### Item (Adicional)
```json
{
  "id": 1,
  "nome": "Ketchup",
  "preco": 0.0,
  "ativo": true
}
```

---

## 🔗 Endpoints Principais

### Admin

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/catalogo/admin/complementos/` | Listar complementos |
| POST | `/api/catalogo/admin/complementos/` | Criar complemento |
| GET | `/api/catalogo/admin/complementos/{id}` | Buscar complemento |
| PUT | `/api/catalogo/admin/complementos/{id}` | Atualizar complemento |
| DELETE | `/api/catalogo/admin/complementos/{id}` | Deletar complemento |
| POST | `/api/catalogo/admin/complementos/{id}/adicionais` | Criar item |
| GET | `/api/catalogo/admin/complementos/{id}/adicionais` | Listar itens |
| PUT | `/api/catalogo/admin/complementos/{id}/adicionais/{item_id}` | Atualizar item |
| DELETE | `/api/catalogo/admin/complementos/{id}/adicionais/{item_id}` | Deletar item |
| POST | `/api/catalogo/admin/complementos/produto/{cod_barras}/vincular` | Vincular a produto |

### Client

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/catalogo/client/complementos/produto/{cod_barras}` | Complementos do produto |
| GET | `/api/catalogo/client/complementos/combo/{combo_id}` | Complementos do combo |
| GET | `/api/catalogo/client/complementos/receita/{receita_id}` | Complementos da receita |

---

## 🛒 Uso em Pedidos

### Request
```json
{
  "produto_cod_barras": "7891234567890",
  "quantidade": 2,
  "complementos": [
    {
      "complemento_id": 1,
      "adicionais": [
        {
          "adicional_id": 1,
          "quantidade": 1
        }
      ]
    }
  ]
}
```

### Campos Importantes
- `complemento_id`: ID do complemento
- `adicional_id`: ID do item (é o `id` do `AdicionalResponse`)
- `quantidade`: Quantidade do item (usado se `complemento.quantitativo = true`)

---

## ✅ Validações

| Regra | Descrição |
|-------|-----------|
| Obrigatório | Se `obrigatorio = true`, deve selecionar pelo menos 1 item |
| Quantitativo | Se `quantitativo = true`, pode escolher quantidade > 1 |
| Múltipla Escolha | Se `permite_multipla_escolha = true`, pode selecionar vários itens |
| Única Escolha | Se `permite_multipla_escolha = false`, apenas 1 item |

---

## 💻 Exemplo TypeScript

```typescript
// Buscar complementos
const complementos = await fetch(
  `/api/catalogo/client/complementos/produto/${codBarras}`,
  { headers: { 'X-Super-Token': token } }
).then(r => r.json());

// Adicionar ao pedido
const item = {
  produto_cod_barras: codBarras,
  quantidade: 1,
  complementos: [
    {
      complemento_id: 1,
      adicionais: [
        { adicional_id: 1, quantidade: 1 }
      ]
    }
  ]
};
```

---

## 📝 Notas

- ✅ Tabela no banco: `complemento_itens` (itens de complemento)
- ✅ Modelo Python: `AdicionalModel` (mantido para compatibilidade)
- ✅ Nos pedidos: use `adicional_id` (é o `id` do item)
- ⚠️ Deletar complemento deleta todos os itens (CASCADE)
- ⚠️ Sempre filtre por `ativo = true` para clientes

