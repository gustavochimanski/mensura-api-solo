# Documentação: Endpoint Unificado de Complementos

## 📋 Resumo das Mudanças

Os três endpoints separados para listar complementos foram **unificados em um único endpoint** que aceita parâmetros de query string.

### ❌ Endpoints Removidos (DEPRECADOS - não usar mais)

Os seguintes endpoints foram **removidos** e não devem mais ser utilizados:

1. `GET /api/catalogo/public/complementos/produto/{cod_barras}`
2. `GET /api/catalogo/public/complementos/combo/{combo_id}`
3. `GET /api/catalogo/public/complementos/receita/{receita_id}`

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
GET /api/catalogo/public/complementos?tipo=receita&identificador=10&tipo_pedido=balcao&apenas_ativos=true
```

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

// Para receita
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

1. **Parâmetro `tipo_pedido` é obrigatório**: Mesmo que atualmente não seja usado para filtrar os resultados, o parâmetro é obrigatório para garantir compatibilidade com futuras implementações.

2. **Formato do `identificador`**:
   - Para **produtos**: Use o código de barras (string)
   - Para **combos**: Use o ID numérico (convertido para string na URL)
   - Para **receitas**: Use o ID numérico (convertido para string na URL)

3. **Resposta vazia**: Se não houver complementos vinculados, o endpoint retorna uma lista vazia `[]` com status `200 OK`.

4. **Validações**: O endpoint valida se o produto/combo/receita existe e está ativo antes de retornar os complementos.

## 🐛 Tratamento de Erros

### Erro 400 - Bad Request
```json
{
  "detail": "Para combos, o identificador deve ser um número inteiro. Recebido: abc"
}
```

### Erro 404 - Not Found
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
