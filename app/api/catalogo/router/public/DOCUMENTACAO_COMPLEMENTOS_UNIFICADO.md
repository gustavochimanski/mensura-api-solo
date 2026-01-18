# Documentação: Endpoint Unificado de Complementos

## 🚀 Resumo Rápido

**Endpoint Unificado:** `GET /api/catalogo/public/complementos`

**Parâmetros obrigatórios:**
- `tipo`: `produto`, `combo` ou `receita`
- `identificador`: Código de barras (produto) ou ID (combo/receita)
- `tipo_pedido`: `balcao`, `mesa` ou `delivery`

**Exemplo para Receita (ID 3):**
```http
GET /api/catalogo/public/complementos?tipo=receita&identificador=3&tipo_pedido=delivery&apenas_ativos=true
```

**Exemplo para Combo (ID 5):**
```http
GET /api/catalogo/public/complementos?tipo=combo&identificador=5&tipo_pedido=mesa&apenas_ativos=true
```0

**Exemplo para Produto (código 123456):**
```http
GET /api/catalogo/public/complementos?tipo=produto&identificador=123456&tipo_pedido=delivery&apenas_ativos=true
```

## 📋 Resumo das Mudanças

Os três endpoints separados para listar complementos foram **unificados em um único endpoint** que aceita parâmetros de query string.

### ⚠️ IMPORTANTE: Erro 404 com Formato Antigo

**Se você está recebendo erro 404**, isso acontece porque está usando o formato antigo que foi **removido**. 

**❌ Formato antigo (retorna 404):**
```
GET /api/catalogo/public/complementos/receita/3?apenas_ativos=true
GET /api/catalogo/public/complementos/combo/5?apenas_ativos=true
GET /api/catalogo/public/complementos/produto/123456?apenas_ativos=true
```

**✅ Formato correto (novo endpoint unificado):**
```
GET /api/catalogo/public/complementos?tipo=receita&identificador=3&tipo_pedido=delivery&apenas_ativos=true
GET /api/catalogo/public/complementos?tipo=combo&identificador=5&tipo_pedido=mesa&apenas_ativos=true
GET /api/catalogo/public/complementos?tipo=produto&identificador=123456&tipo_pedido=delivery&apenas_ativos=true
```

### ❌ Endpoints Removidos (DEPRECADOS - não usar mais)

Os seguintes endpoints foram **removidos** e não devem mais ser utilizados:

1. `GET /api/catalogo/public/complementos/produto/{cod_barras}` ❌ **Retorna 404**
2. `GET /api/catalogo/public/complementos/combo/{combo_id}` ❌ **Retorna 404**
3. `GET /api/catalogo/public/complementos/receita/{receita_id}` ❌ **Retorna 404**

### ✅ Novo Endpoint Unificado

**Endpoint:** `GET /api/catalogo/public/complementos`

## 📖 Como Usar o Novo Endpoint

### Parâmetros Obrigatórios

| Parâmetro | Tipo | Descrição | Valores Aceitos |
|-----------|------|-----------|-----------------|
| `tipo` | string | Tipo do produto | `produto`, `combo`, `receita` |
| `identificador` | string | Identificador do produto | Código de barras (produto) ou ID numérico (combo/receita) |
| `tipo_pedido` | string | Tipo de pedido | `balcao`, `mesa`, `delivery` |

### Parâmetros Opcionais

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `apenas_ativos` | boolean | `true` | Se `true`, retorna apenas complementos ativos |

### Exemplos de Requisições

#### 1. Listar complementos de um Produto

```http
GET /api/catalogo/public/complementos?tipo=produto&identificador=123456789&tipo_pedido=delivery&apenas_ativos=true
```

**Resposta:**
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Tamanho",
    "descricao": "Escolha o tamanho",
    "obrigatorio": true,
    "quantitativo": false,
    "minimo_itens": 1,
    "maximo_itens": 1,
    "ordem": 0,
    "ativo": true,
    "adicionais": [
      {
        "id": 1,
        "nome": "Pequeno",
        "descricao": "300ml",
        "preco": 0.0,
        "custo": 0.0,
        "ativo": true,
        "ordem": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": 2,
        "nome": "Grande",
        "descricao": "500ml",
        "preco": 2.0,
        "custo": 1.0,
        "ativo": true,
        "ordem": 1,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### 2. Listar complementos de um Combo

```http
GET /api/catalogo/public/complementos?tipo=combo&identificador=5&tipo_pedido=mesa&apenas_ativos=true
```

#### 3. Listar complementos de uma Receita

```http
GET /api/catalogo/public/complementos?tipo=receita&identificador=3&tipo_pedido=delivery&apenas_ativos=true
```

**Exemplo prático resolvendo o erro 404:**
- ❌ **Errado:** `GET /api/catalogo/public/complementos/receita/3?apenas_ativos=true` (retorna 404)
- ✅ **Correto:** `GET /api/catalogo/public/complementos?tipo=receita&identificador=3&tipo_pedido=delivery&apenas_ativos=true`

#### 4. Incluir complementos inativos

```http
GET /api/catalogo/public/complementos?tipo=produto&identificador=123456789&tipo_pedido=delivery&apenas_ativos=false
```

## 🔄 Migração do Código Frontend

### Antes (Código Antigo - NÃO USAR)

```javascript
// ❌ NÃO USAR MAIS
// Para produto
const response = await fetch(`/api/catalogo/public/complementos/produto/${codBarras}?apenas_ativos=true`);

// Para combo
const response = await fetch(`/api/catalogo/public/complementos/combo/${comboId}?apenas_ativos=true`);

// Para receita (FORMATO ANTIGO - NÃO USAR MAIS - retorna 404)
const response = await fetch(`/api/catalogo/public/complementos/receita/${receitaId}?apenas_ativos=true`);
```

### Depois (Código Novo - USAR)

```javascript
// ✅ USAR ESTE FORMATO
// Função auxiliar para buscar complementos
async function buscarComplementos(tipo, identificador, tipoPedido, apenasAtivos = true) {
  const params = new URLSearchParams({
    tipo: tipo, // 'produto', 'combo' ou 'receita'
    identificador: identificador.toString(),
    tipo_pedido: tipoPedido, // 'balcao', 'mesa' ou 'delivery'
    apenas_ativos: apenasAtivos.toString()
  });
  
  const response = await fetch(`/api/catalogo/public/complementos?${params}`);
  return response.json();
}

// Exemplos de uso:
// Para produto
const complementosProduto = await buscarComplementos('produto', codBarras, 'delivery');

// Para combo
const complementosCombo = await buscarComplementos('combo', comboId, 'mesa');

// Para receita
const complementosReceita = await buscarComplementos('receita', receitaId, 'balcao');
```

### Exemplo com TypeScript

```typescript
type TipoProduto = 'produto' | 'combo' | 'receita';
type TipoPedido = 'balcao' | 'mesa' | 'delivery';

interface ComplementoResponse {
  id: number;
  empresa_id: number;
  nome: string;
  descricao: string | null;
  obrigatorio: boolean;
  quantitativo: boolean;
  minimo_itens: number | null;
  maximo_itens: number | null;
  ordem: number;
  ativo: boolean;
  adicionais: AdicionalResponse[];
  created_at: string;
  updated_at: string;
}

async function buscarComplementos(
  tipo: TipoProduto,
  identificador: string | number,
  tipoPedido: TipoPedido,
  apenasAtivos: boolean = true
): Promise<ComplementoResponse[]> {
  const params = new URLSearchParams({
    tipo,
    identificador: identificador.toString(),
    tipo_pedido: tipoPedido,
    apenas_ativos: apenasAtivos.toString()
  });
  
  const response = await fetch(`/api/catalogo/public/complementos?${params}`);
  
  if (!response.ok) {
    throw new Error(`Erro ao buscar complementos: ${response.statusText}`);
  }
  
  return response.json();
}
```

## ⚠️ Observações Importantes

1. **Parâmetro `tipo_pedido` é obrigatório**: Mesmo que atualmente não seja usado para filtrar os resultados, o parâmetro é obrigatório para garantir compatibilidade com futuras implementações. Valores aceitos: `balcao`, `mesa`, `delivery`.

2. **Formato do `identificador`**:
   - Para **produtos**: Use o código de barras (string), exemplo: `"123456789"`
   - Para **combos**: Use o ID numérico (convertido para string na URL), exemplo: `"5"`
   - Para **receitas**: Use o ID numérico (convertido para string na URL), exemplo: `"3"`

3. **Todos os parâmetros obrigatórios devem estar presentes**:
   - `tipo` (obrigatório): `produto`, `combo` ou `receita`
   - `identificador` (obrigatório): código de barras ou ID
   - `tipo_pedido` (obrigatório): `balcao`, `mesa` ou `delivery`

4. **Resposta vazia**: Se não houver complementos vinculados, o endpoint retorna uma lista vazia `[]` com status `200 OK`.

5. **Validações**: O endpoint valida se o produto/combo/receita existe e está ativo antes de retornar os complementos.

6. **Endpoint unificado**: Um único endpoint serve para produtos, combos e receitas. Use o parâmetro `tipo` para especificar qual tipo está consultando.

## 🐛 Tratamento de Erros

### Erro 404 - Not Found (Formato de URL Antigo)

**Se você está recebendo 404, verifique se está usando o formato correto:**

```http
❌ GET /api/catalogo/public/complementos/receita/3?apenas_ativos=true
   → Retorna: 404 Not Found

✅ GET /api/catalogo/public/complementos?tipo=receita&identificador=3&tipo_pedido=delivery&apenas_ativos=true
   → Retorna: 200 OK com lista de complementos
```

**Os endpoints antigos com path parameters (`/receita/{id}`, `/combo/{id}`, `/produto/{cod}`) foram removidos e retornam 404.**

### Erro 400 - Bad Request

**Identificador inválido:**
```json
{
  "detail": "Para combos, o identificador deve ser um número inteiro. Recebido: abc"
}
```

**Parâmetros obrigatórios faltando:**
```json
{
  "detail": "Field required: tipo"
}
```

### Erro 404 - Not Found (Recurso não encontrado)

**Receita/Combo não encontrado ou inativo:**
```json
{
  "detail": "Receita 3 não encontrada ou inativa"
}
```

```json
{
  "detail": "Combo 5 não encontrado ou inativo"
}
```

### Erro 500 - Internal Server Error
```json
{
  "detail": "Erro ao listar complementos: [mensagem de erro]"
}
```

## 📝 Exemplos Práticos Completos

### Exemplo 1: Buscar complementos de uma Receita (ID 3)

**❌ Formato antigo (retorna 404):**
```bash
curl "http://localhost:8000/api/catalogo/public/complementos/receita/3?apenas_ativos=true"
```

**✅ Formato correto (novo endpoint unificado):**
```bash
curl "http://localhost:8000/api/catalogo/public/complementos?tipo=receita&identificador=3&tipo_pedido=delivery&apenas_ativos=true"
```

### Exemplo 2: Buscar complementos de um Combo (ID 5)

**❌ Formato antigo (retorna 404):**
```bash
curl "http://localhost:8000/api/catalogo/public/complementos/combo/5?apenas_ativos=true"
```

**✅ Formato correto (novo endpoint unificado):**
```bash
curl "http://localhost:8000/api/catalogo/public/complementos?tipo=combo&identificador=5&tipo_pedido=mesa&apenas_ativos=true"
```

### Exemplo 3: Buscar complementos de um Produto (código 123456)

**❌ Formato antigo (retorna 404):**
```bash
curl "http://localhost:8000/api/catalogo/public/complementos/produto/123456?apenas_ativos=true"
```

**✅ Formato correto (novo endpoint unificado):**
```bash
curl "http://localhost:8000/api/catalogo/public/complementos?tipo=produto&identificador=123456&tipo_pedido=delivery&apenas_ativos=true"
```

## 📅 Data da Mudança

**Data:** Janeiro 2025

**Versão da API:** Endpoint unificado substitui os três endpoints anteriores.

## ✅ Checklist de Migração

- [ ] Atualizar todas as chamadas para os endpoints antigos
- [ ] Implementar função auxiliar para buscar complementos
- [ ] Adicionar o parâmetro `tipo_pedido` em todas as requisições
- [ ] Testar com produtos, combos e receitas
- [ ] Validar tratamento de erros
- [ ] Remover código antigo que usa os endpoints deprecados

## 📞 Suporte

Em caso de dúvidas ou problemas, entre em contato com a equipe de backend.
