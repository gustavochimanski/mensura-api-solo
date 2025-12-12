# 📘 Guia de Migração Frontend: Sistema de Complementos

## 📋 Índice

1. [Visão Geral das Mudanças](#visão-geral-das-mudanças)
2. [Novos Tipos TypeScript](#novos-tipos-typescript)
3. [Endpoints de Complementos](#endpoints-de-complementos)
4. [Estrutura do Carrinho](#estrutura-do-carrinho)
5. [Checkout e Finalização de Pedido](#checkout-e-finalização-de-pedido)
6. [Validações e Regras de Negócio](#validações-e-regras-de-negócio)
7. [Guia de Migração Passo a Passo](#guia-de-migração-passo-a-passo)
8. [Exemplos de Implementação](#exemplos-de-implementação)
9. [Checklist de Migração](#checklist-de-migração)

---

## 🎯 Visão Geral das Mudanças

### O que mudou?

O sistema migrou de uma estrutura **flat** (adicionais diretos) para uma estrutura **hierárquica** (complementos → adicionais).

**Antes (DEPRECATED):**
```typescript
// Adicionais diretamente no produto
produto.adicionais = [
  { id: 1, nome: "Bacon", preco: 5.00 },
  { id: 2, nome: "Queijo Extra", preco: 3.00 }
]
```

**Agora (NOVO):**
```typescript
// Complementos agrupam adicionais
complementos = [
  {
    id: 1,
    nome: "Adicionais",
    obrigatorio: false,
    permite_multipla_escolha: true,
    adicionais: [
      { id: 10, nome: "Bacon", preco: 5.00 },
      { id: 11, nome: "Queijo Extra", preco: 3.00 }
    ]
  }
]
```

### Por que mudou?

1. **Hierarquia Clara**: Complementos agrupam adicionais logicamente (ex: "Tamanho", "Bebida", "Adicionais")
2. **Regras Flexíveis**: Cada complemento tem suas próprias regras (obrigatório, quantitativo, múltipla escolha)
3. **Consistência**: Mesma estrutura para produtos, combos e receitas - todos usam complementos diretamente vinculados
4. **Escalabilidade**: Fácil adicionar novos tipos de complementos e regras

### Importante: Receitas e Combos

**ATUALIZAÇÃO**: Receitas e combos agora também têm complementos diretamente vinculados, assim como produtos. Não há mais adicionais diretos em receitas ou combos - todos os adicionais estão dentro de complementos.

---

## 📦 Novos Tipos TypeScript

### 1. ComplementoResponse (Resposta da API)

```typescript
interface ComplementoResponse {
  id: number;                        // ID do complemento
  empresa_id: number;                // ID da empresa
  nome: string;                      // Nome do complemento (ex: "Tamanho", "Bebida")
  descricao?: string | null;         // Descrição do complemento
  obrigatorio: boolean;              // Se é obrigatório selecionar
  quantitativo: boolean;             // Se permite quantidade > 1
  permite_multipla_escolha: boolean; // Se permite selecionar múltiplos adicionais
  minimo_itens?: number | null;      // Quantidade mínima de itens (se aplicável)
  maximo_itens?: number | null;      // Quantidade máxima de itens (se aplicável)
  ordem: number;                     // Ordem de exibição
  ativo: boolean;                   // Se está ativo
  adicionais: AdicionalComplementoResponse[]; // Lista de adicionais
  created_at: string;                // ISO 8601
  updated_at: string;                // ISO 8601
}

interface AdicionalComplementoResponse {
  id: number;                        // ID do adicional (usado como adicional_id nos pedidos)
  nome: string;                      // Nome do adicional (ex: "Pequeno", "Coca-Cola")
  descricao?: string | null;         // Descrição
  preco: number;                     // Preço adicional
  custo: number;                     // Custo (geralmente não usado no frontend)
  ativo: boolean;                   // Se está ativo
  ordem: number;                     // Ordem de exibição
  created_at: string;                // ISO 8601
  updated_at: string;                // ISO 8601
}
```

### 2. Estrutura do Carrinho

```typescript
interface CartItem {
  cod_barras: string;
  nome: string;
  preco: number;
  quantity: number;
  empresaId: number;
  imagem?: string | null;
  categoriaId?: number;
  subcategoriaId?: number;
  observacao?: string;
  
  // ✅ NOVO: Estrutura de Complementos (PREFERENCIAL)
  complementos?: CartItemComplemento[];
  
  // ❌ DEPRECATED: Adicionais antigos (remover gradualmente)
  adicionais?: CartItemAdicional[];
}

interface CartCombo {
  combo_id: number;
  nome?: string;
  quantidade: number;
  preco: number;
  observacao?: string;
  
  // ✅ NOVO: Estrutura de Complementos (PREFERENCIAL)
  complementos?: CartItemComplemento[];
  
  // ❌ DEPRECATED: Adicionais antigos (remover gradualmente)
  adicionais?: CartItemAdicional[];
}

interface CartReceita {
  receita_id: number;
  nome?: string;
  quantidade: number;
  preco: number;
  observacao?: string;
  
  // ✅ NOVO: Estrutura de Complementos (PREFERENCIAL)
  complementos?: CartItemComplemento[];
  
  // ❌ DEPRECATED: Adicionais antigos (remover gradualmente)
  adicionais?: CartItemAdicional[];
}

interface CartItemComplemento {
  complemento_id: number;           // ID do complemento
  adicionais: CartItemAdicionalComplemento[]; // Adicionais selecionados
  
  // Campos opcionais para exibição (NÃO enviados na API)
  complemento_nome?: string;
  complemento_obrigatorio?: boolean;
}

interface CartItemAdicionalComplemento {
  adicional_id: number;             // ID do adicional (OBRIGATÓRIO para API)
  quantidade: number;               // Quantidade selecionada
  
  // Campos opcionais para exibição (NÃO enviados na API)
  adicional_nome?: string;
  adicional_preco?: number;
}

// ❌ DEPRECATED - não usar mais
interface CartItemAdicional {
  id: number;
  nome: string;
  preco: number;
}
```

### 3. Estrutura do Checkout (Request)

```typescript
interface ItemAdicionalComplementoRequest {
  adicional_id: number;             // ID do adicional (OBRIGATÓRIO)
  quantidade: number;               // Quantidade (usado se complemento.quantitativo = true)
}

interface ItemComplementoRequest {
  complemento_id: number;            // ID do complemento
  adicionais: ItemAdicionalComplementoRequest[]; // Adicionais selecionados
}

interface ItemPedidoRequest {
  produto_cod_barras: string;
  quantidade: number;
  observacao?: string;
  
  // ✅ NOVO: Complementos agrupados
  complementos?: ItemComplementoRequest[];
  
  // ❌ DEPRECATED: Adicionais diretos (remover)
  adicionais?: any[];
}

interface ReceitaPedidoRequest {
  receita_id: number;
  quantidade: number;
  observacao?: string;
  
  // ✅ NOVO: Complementos agrupados
  complementos?: ItemComplementoRequest[];
  
  // ❌ DEPRECATED: Adicionais diretos (remover)
  adicionais?: any[];
}

interface ComboPedidoRequest {
  combo_id: number;
  quantidade?: number;              // Default: 1
  
  // ✅ NOVO: Complementos agrupados
  complementos?: ItemComplementoRequest[];
  
  // ❌ DEPRECATED: Adicionais diretos (remover)
  adicionais?: any[];
}

interface ProdutosPedidoRequest {
  itens: ItemPedidoRequest[];
  receitas?: ReceitaPedidoRequest[];
  combos?: ComboPedidoRequest[];
}

interface FinalizarPedidoRequest {
  empresa_id?: number | null;
  tipo_pedido: "DELIVERY" | "MESA" | "BALCAO";
  telefone_cliente?: string;
  cliente_id?: number | null;
  endereco_id?: number | null;
  mesa_codigo?: string | null;
  num_pessoas?: number | null;
  meio_pagamento_id?: number | null;
  meios_pagamento?: MeioPagamentoParcialRequest[] | null;
  tipo_entrega?: "DELIVERY" | "RETIRADA";
  origem?: "WEB" | "APP" | "PDV";
  observacao_geral?: string;
  cupom_id?: number | null;
  troco_para?: number | null;
  
  // ✅ NOVO: Formato agrupado (PREFERENCIAL)
  produtos?: ProdutosPedidoRequest;
  
  // ❌ DEPRECATED: Campos diretos na raiz (suportado mas descontinuar)
  itens?: ItemPedidoRequest[];
  receitas?: ReceitaPedidoRequest[];
  combos?: ComboPedidoRequest[];
}
```

---

## 🔌 Endpoints de Complementos

### 1. Buscar Complementos de Produto

**GET** `/api/catalogo/client/complementos/produto/{cod_barras}`

**Headers:**
```
X-Super-Token: {token_do_cliente}
```

**Query Params:**
- `apenas_ativos`: boolean (default: `true`)

**Resposta:** `ComplementoResponse[]`

**Exemplo:**
```typescript
async function buscarComplementosProduto(
  codBarras: string,
  apenasAtivos: boolean = true
): Promise<ComplementoResponse[]> {
  const token = localStorage.getItem('super_token');
  
  const response = await fetch(
    `/api/catalogo/client/complementos/produto/${codBarras}?apenas_ativos=${apenasAtivos}`,
    {
      method: 'GET',
      headers: {
        'X-Super-Token': token || '',
      },
    }
  );
  
  if (!response.ok) {
    throw new Error('Erro ao buscar complementos');
  }
  
  return response.json();
}
```

### 2. Buscar Complementos de Receita

**GET** `/api/catalogo/client/complementos/receita/{receita_id}`

**Headers:**
```
X-Super-Token: {token_do_cliente}
```

**Query Params:**
- `apenas_ativos`: boolean (default: `true`)

**Resposta:** `ComplementoResponse[]`

**Nota**: Receitas agora têm complementos diretamente vinculados (não mais adicionais diretos). Os complementos retornados são aqueles especificamente vinculados à receita.

**Exemplo:**
```typescript
async function buscarComplementosReceita(
  receitaId: number,
  apenasAtivos: boolean = true
): Promise<ComplementoResponse[]> {
  const token = localStorage.getItem('super_token');
  
  const response = await fetch(
    `/api/catalogo/client/complementos/receita/${receitaId}?apenas_ativos=${apenasAtivos}`,
    {
      method: 'GET',
      headers: {
        'X-Super-Token': token || '',
      },
    }
  );
  
  if (!response.ok) {
    throw new Error('Erro ao buscar complementos');
  }
  
  return response.json();
}
```

### 3. Buscar Complementos de Combo

**GET** `/api/catalogo/client/complementos/combo/{combo_id}`

**Headers:**
```
X-Super-Token: {token_do_cliente}
```

**Query Params:**
- `apenas_ativos`: boolean (default: `true`)

**Resposta:** `ComplementoResponse[]`

**Nota**: Combos agora têm complementos diretamente vinculados (não mais adicionais diretos). Os complementos retornados são aqueles especificamente vinculados ao combo.

**Exemplo:**
```typescript
async function buscarComplementosCombo(
  comboId: number,
  apenasAtivos: boolean = true
): Promise<ComplementoResponse[]> {
  const token = localStorage.getItem('super_token');
  
  const response = await fetch(
    `/api/catalogo/client/complementos/combo/${comboId}?apenas_ativos=${apenasAtivos}`,
    {
      method: 'GET',
      headers: {
        'X-Super-Token': token || '',
      },
    }
  );
  
  if (!response.ok) {
    throw new Error('Erro ao buscar complementos');
  }
  
  return response.json();
}
```

---

## 🛒 Estrutura do Carrinho

### Mudanças Necessárias no Store do Carrinho

#### 1. Adicionar Produto com Complementos

```typescript
// ANTES (DEPRECATED)
function addProduto(produto: Produto, adicionaisSelecionados: Adicional[]) {
  const cartItem: CartItem = {
    cod_barras: produto.cod_barras,
    nome: produto.descricao,
    preco: produto.preco_venda,
    quantity: 1,
    empresaId: produto.empresa_id,
    adicionais: adicionaisSelecionados.map(ad => ({
      id: ad.id,
      nome: ad.nome,
      preco: ad.preco,
    })),
  };
  // ... adicionar ao carrinho
}

// AGORA (NOVO)
function addProduto(
  produto: Produto,
  complementosSelecionados: Map<number, CartItemComplemento> // complemento_id -> complemento
) {
  // Converter Map para array
  const complementos = Array.from(complementosSelecionados.values());
  
  const cartItem: CartItem = {
    cod_barras: produto.cod_barras,
    nome: produto.descricao,
    preco: produto.preco_venda,
    quantity: 1,
    empresaId: produto.empresa_id,
    complementos: complementos,
  };
  // ... adicionar ao carrinho
}
```

#### 2. Calcular Preço Total com Complementos

```typescript
function calcularPrecoItem(item: CartItem): number {
  let precoBase = item.preco * item.quantity;
  let precoComplementos = 0;
  
  if (item.complementos && item.complementos.length > 0) {
    item.complementos.forEach(complemento => {
      complemento.adicionais.forEach(adicional => {
        precoComplementos += (adicional.adicional_preco || 0) * adicional.quantidade;
      });
    });
    precoComplementos *= item.quantity; // Multiplica pela quantidade do item
  }
  
  return precoBase + precoComplementos;
}
```

#### 3. Adicionar Receita com Complementos

```typescript
// ANTES (DEPRECATED) - Receitas com adicionais diretos
function addReceita(receita: Receita, adicionaisSelecionados: Adicional[]) {
  const cartReceita: CartReceita = {
    receita_id: receita.id,
    nome: receita.nome,
    quantidade: 1,
    preco: receita.preco_venda,
    adicionais: adicionaisSelecionados.map(ad => ({
      id: ad.id,
      nome: ad.nome,
      preco: ad.preco,
    })),
  };
  // ... adicionar ao carrinho
}

// AGORA (NOVO) - Receitas com complementos
function addReceita(
  receita: Receita,
  complementosSelecionados: Map<number, CartItemComplemento>
) {
  const complementos = Array.from(complementosSelecionados.values());
  
  const cartReceita: CartReceita = {
    receita_id: receita.id,
    nome: receita.nome,
    quantidade: 1,
    preco: receita.preco_venda,
    complementos: complementos, // ✅ NOVO: Complementos em vez de adicionais diretos
  };
  // ... adicionar ao carrinho
}
```

#### 4. Adicionar Combo com Complementos

```typescript
// ANTES (DEPRECATED) - Combos sem complementos/adicionais
function addCombo(combo: Combo) {
  const cartCombo: CartCombo = {
    combo_id: combo.id,
    nome: combo.titulo,
    quantidade: 1,
    preco: combo.preco_total,
    // Sem complementos ou adicionais
  };
  // ... adicionar ao carrinho
}

// AGORA (NOVO) - Combos com complementos
function addCombo(
  combo: Combo,
  complementosSelecionados: Map<number, CartItemComplemento>
) {
  const complementos = Array.from(complementosSelecionados.values());
  
  const cartCombo: CartCombo = {
    combo_id: combo.id,
    nome: combo.titulo,
    quantidade: 1,
    preco: combo.preco_total,
    complementos: complementos, // ✅ NOVO: Complementos diretamente vinculados
  };
  // ... adicionar ao carrinho
}
```

#### 5. Calcular Preço de Receita/Combo com Complementos

```typescript
function calcularPrecoReceita(receita: CartReceita): number {
  let precoBase = receita.preco * receita.quantidade;
  let precoComplementos = 0;
  
  if (receita.complementos && receita.complementos.length > 0) {
    receita.complementos.forEach(complemento => {
      complemento.adicionais.forEach(adicional => {
        precoComplementos += (adicional.adicional_preco || 0) * adicional.quantidade;
      });
    });
    precoComplementos *= receita.quantidade;
  }
  
  return precoBase + precoComplementos;
}

function calcularPrecoCombo(combo: CartCombo): number {
  let precoBase = combo.preco * combo.quantidade;
  let precoComplementos = 0;
  
  if (combo.complementos && combo.complementos.length > 0) {
    combo.complementos.forEach(complemento => {
      complemento.adicionais.forEach(adicional => {
        precoComplementos += (adicional.adicional_preco || 0) * adicional.quantidade;
      });
    });
    precoComplementos *= combo.quantidade;
  }
  
  return precoBase + precoComplementos;
}
```

#### 6. Agrupamento de Itens Idênticos

```typescript
function encontrarItemIdentico(
  novoItem: CartItem,
  itemsExistentes: CartItem[]
): CartItem | null {
  return itemsExistentes.find(item => {
    // Mesmo código de barras
    if (item.cod_barras !== novoItem.cod_barras) {
      return false;
    }
    
    // Mesmos complementos (comparar IDs e quantidades)
    const complementosNovo = JSON.stringify(
      novoItem.complementos?.map(c => ({
        complemento_id: c.complemento_id,
        adicionais: c.adicionais.map(a => ({
          adicional_id: a.adicional_id,
          quantidade: a.quantidade,
        })),
      })).sort((a, b) => a.complemento_id - b.complemento_id)
    );
    
    const complementosExistente = JSON.stringify(
      item.complementos?.map(c => ({
        complemento_id: c.complemento_id,
        adicionais: c.adicionais.map(a => ({
          adicional_id: a.adicional_id,
          quantidade: a.quantidade,
        })),
      })).sort((a, b) => a.complemento_id - b.complemento_id)
    );
    
    return complementosNovo === complementosExistente;
  }) || null;
}
```

---

## 🛍️ Checkout e Finalização de Pedido

### Função de Conversão: Carrinho → Request

```typescript
function mapCartToPedidoItems(cart: CartState): ProdutosPedidoRequest {
  const itens: ItemPedidoRequest[] = cart.items.map(item => ({
    produto_cod_barras: item.cod_barras,
    quantidade: item.quantity,
    observacao: item.observacao || undefined,
    complementos: item.complementos?.map(comp => ({
      complemento_id: comp.complemento_id,
      adicionais: comp.adicionais.map(adicional => ({
        adicional_id: adicional.adicional_id, // ⚠️ IMPORTANTE: usar adicional_id
        quantidade: adicional.quantidade,
      })),
    })),
  }));
  
  const receitas: ReceitaPedidoRequest[] = cart.receitas.map(receita => ({
    receita_id: receita.receita_id,
    quantidade: receita.quantidade,
    observacao: receita.observacao || undefined,
    complementos: receita.complementos?.map(comp => ({
      complemento_id: comp.complemento_id,
      adicionais: comp.adicionais.map(adicional => ({
        adicional_id: adicional.adicional_id,
        quantidade: adicional.quantidade,
      })),
    })),
  }));
  
  const combos: ComboPedidoRequest[] = cart.combos.map(combo => ({
    combo_id: combo.combo_id,
    quantidade: combo.quantidade,
    complementos: combo.complementos?.map(comp => ({
      complemento_id: comp.complemento_id,
      adicionais: comp.adicionais.map(adicional => ({
        adicional_id: adicional.adicional_id,
        quantidade: adicional.quantidade,
      })),
    })),
  }));
  
  return {
    itens,
    receitas: receitas.length > 0 ? receitas : undefined,
    combos: combos.length > 0 ? combos : undefined,
  };
}

// Função para finalizar pedido
async function finalizarPedido(
  cart: CartState,
  dadosCheckout: DadosCheckout
): Promise<PedidoResponse> {
  const produtos = mapCartToPedidoItems(cart);
  
  const request: FinalizarPedidoRequest = {
    empresa_id: dadosCheckout.empresa_id,
    tipo_pedido: dadosCheckout.tipo_pedido,
    telefone_cliente: dadosCheckout.telefone,
    endereco_id: dadosCheckout.endereco_id,
    tipo_entrega: dadosCheckout.tipo_entrega,
    origem: "WEB",
    observacao_geral: cart.observacao || undefined,
    cupom_id: dadosCheckout.cupom_id || undefined,
    troco_para: dadosCheckout.troco_para || undefined,
    meio_pagamento_id: dadosCheckout.meio_pagamento_id || undefined,
    
    // ✅ NOVO: Formato agrupado
    produtos: produtos,
  };
  
  const response = await fetch('/api/pedidos/checkout/finalizar', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Super-Token': localStorage.getItem('super_token') || '',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error('Erro ao finalizar pedido');
  }
  
  return response.json();
}
```

### ⚠️ Campos Importantes no Request

**ENVIAR APENAS:**
- `complemento_id`: ID do complemento
- `adicional_id`: ID do adicional (não enviar `id`, usar `adicional_id`)
- `quantidade`: Quantidade do adicional

**NÃO ENVIAR:**
- Nomes dos complementos/adicionais
- Preços (backend calcula)
- Descrições
- Campos de exibição (`complemento_nome`, `adicional_nome`, etc.)

---

## ✅ Validações e Regras de Negócio

### 1. Complementos Obrigatórios

```typescript
function validarComplementosObrigatorios(
  complementos: ComplementoResponse[],
  complementosSelecionados: Map<number, CartItemComplemento>
): { valido: boolean; erro?: string } {
  for (const complemento of complementos) {
    if (complemento.obrigatorio) {
      const selecionado = complementosSelecionados.get(complemento.id);
      
      if (!selecionado || selecionado.adicionais.length === 0) {
        return {
          valido: false,
          erro: `É obrigatório selecionar ao menos um item em "${complemento.nome}"`,
        };
      }
      
      // Validar quantidade mínima
      if (complemento.minimo_itens && complemento.minimo_itens > 0) {
        const totalItens = selecionado.adicionais.reduce(
          (sum, ad) => sum + ad.quantidade,
          0
        );
        
        if (totalItens < complemento.minimo_itens) {
          return {
            valido: false,
            erro: `É necessário selecionar pelo menos ${complemento.minimo_itens} item(s) em "${complemento.nome}"`,
          };
        }
      }
      
      // Validar quantidade máxima
      if (complemento.maximo_itens && complemento.maximo_itens > 0) {
        const totalItens = selecionado.adicionais.reduce(
          (sum, ad) => sum + ad.quantidade,
          0
        );
        
        if (totalItens > complemento.maximo_itens) {
          return {
            valido: false,
            erro: `É possível selecionar no máximo ${complemento.maximo_itens} item(s) em "${complemento.nome}"`,
          };
        }
      }
    }
  }
  
  return { valido: true };
}
```

### 2. Múltipla Escolha vs. Escolha Única

```typescript
function podeSelecionarMultiplos(complemento: ComplementoResponse): boolean {
  return complemento.permite_multipla_escolha;
}

// Exemplo de uso na UI
function renderizarComplemento(complemento: ComplementoResponse) {
  if (complemento.permite_multipla_escolha) {
    // Renderizar checkboxes ou botões múltiplos
    return renderCheckboxes(complemento);
  } else {
    // Renderizar radio buttons ou botão único
    return renderRadioButtons(complemento);
  }
}
```

### 3. Complementos Quantitativos

```typescript
function permiteQuantidade(complemento: ComplementoResponse): boolean {
  return complemento.quantitativo;
}

// Exemplo de uso na UI
function renderizarAdicional(
  adicional: AdicionalComplementoResponse,
  complemento: ComplementoResponse
) {
  if (complemento.quantitativo) {
    // Mostrar seletor de quantidade (+/-)
    return (
      <div>
        <span>{adicional.nome}</span>
        <button onClick={() => decrementar(adicional.id)}>-</button>
        <span>{quantidadeSelecionada}</span>
        <button onClick={() => incrementar(adicional.id)}>+</button>
      </div>
    );
  } else {
    // Mostrar apenas checkbox/radio
    return <Checkbox value={adicional.id}>{adicional.nome}</Checkbox>;
  }
}
```

---

## 🔄 Guia de Migração Passo a Passo

### Passo 1: Atualizar Tipos TypeScript

1. Criar arquivo `src/types/complementos.ts` com os novos tipos
2. Atualizar `src/types/cart.ts` para incluir `complementos` nos itens
3. Atualizar `src/types/pedido.ts` para usar a nova estrutura de request

### Passo 2: Criar Serviços de Busca de Complementos

1. Criar `src/services/complementos/buscar-complementos-produto.ts`
2. Criar `src/services/complementos/buscar-complementos-receita.ts` - **IMPORTANTE**: Receitas agora têm complementos diretamente vinculados
3. Criar `src/services/complementos/buscar-complementos-combo.ts` - **IMPORTANTE**: Combos agora têm complementos diretamente vinculados

### Passo 3: Atualizar Componentes de Seleção

1. Atualizar `SheetAddProduto.tsx`:
   - Buscar complementos ao abrir o sheet
   - Renderizar complementos hierarquicamente
   - Validar complementos obrigatórios antes de adicionar ao carrinho

2. Atualizar `SheetAddReceita.tsx`:
   - **IMPORTANTE**: Receitas agora usam complementos diretamente vinculados (não mais adicionais diretos)
   - Buscar complementos usando: `GET /api/catalogo/client/complementos/receita/{receita_id}`
   - Remover código de adicionais diretos
   - Mesmas mudanças que no SheetAddProduto (buscar, renderizar e validar complementos)

3. Atualizar `SheetAddCombo.tsx`:
   - **IMPORTANTE**: Combos agora têm complementos diretamente vinculados
   - Buscar complementos usando: `GET /api/catalogo/client/complementos/combo/{combo_id}`
   - Mesmas mudanças que no SheetAddProduto (buscar, renderizar e validar complementos)

### Passo 4: Atualizar Store do Carrinho

1. Atualizar função `add` para aceitar `complementos`
2. Atualizar função `addCombo` para aceitar `complementos`
3. Atualizar função `addReceita` para aceitar `complementos`
4. Atualizar função de cálculo de preço total
5. Atualizar função de agrupamento de itens idênticos

### Passo 5: Atualizar Conversão para Pedido

1. Atualizar `mapCartToPedidoItems`:
   - Converter `CartItemComplemento[]` para `ItemComplementoRequest[]`
   - Garantir que apenas `complemento_id`, `adicional_id` e `quantidade` sejam enviados

### Passo 6: Atualizar Checkout

1. Atualizar função `finalizarPedido`:
   - Usar formato agrupado `produtos: { itens, receitas, combos }`
   - Remover campos legados se não houver mais uso

### Passo 7: Testes

1. Testar adicionar produto com complementos
2. Testar adicionar combo com complementos
3. Testar adicionar receita com complementos
4. Testar validação de complementos obrigatórios
5. Testar finalização de pedido
6. Testar cálculo de preços

### Passo 8: Limpeza

1. Remover código legado de `adicionais` diretos
2. Atualizar testes unitários
3. Atualizar documentação

---

## 💻 Exemplos de Implementação

### Exemplo 1: Hook para Buscar Complementos de Produto

```typescript
import { useState, useEffect } from 'react';

interface UseComplementosProdutoReturn {
  complementos: ComplementoResponse[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function useComplementosProduto(
  codBarras: string | null,
  apenasAtivos: boolean = true
): UseComplementosProdutoReturn {
  const [complementos, setComplementos] = useState<ComplementoResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const buscar = async () => {
    if (!codBarras) {
      setComplementos([]);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const resultado = await buscarComplementosProduto(codBarras, apenasAtivos);
      setComplementos(resultado);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao buscar complementos');
      setComplementos([]);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    buscar();
  }, [codBarras, apenasAtivos]);
  
  return {
    complementos,
    loading,
    error,
    refetch: buscar,
  };
}
```

### Exemplo 1.1: Hook para Buscar Complementos de Receita

```typescript
import { useState, useEffect } from 'react';

interface UseComplementosReceitaReturn {
  complementos: ComplementoResponse[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function useComplementosReceita(
  receitaId: number | null,
  apenasAtivos: boolean = true
): UseComplementosReceitaReturn {
  const [complementos, setComplementos] = useState<ComplementoResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const buscar = async () => {
    if (!receitaId) {
      setComplementos([]);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('super_token');
      const response = await fetch(
        `/api/catalogo/client/complementos/receita/${receitaId}?apenas_ativos=${apenasAtivos}`,
        {
          method: 'GET',
          headers: {
            'X-Super-Token': token || '',
          },
        }
      );
      
      if (!response.ok) {
        throw new Error('Erro ao buscar complementos da receita');
      }
      
      const resultado = await response.json();
      setComplementos(resultado);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao buscar complementos');
      setComplementos([]);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    buscar();
  }, [receitaId, apenasAtivos]);
  
  return {
    complementos,
    loading,
    error,
    refetch: buscar,
  };
}
```

### Exemplo 1.2: Hook para Buscar Complementos de Combo

```typescript
import { useState, useEffect } from 'react';

interface UseComplementosComboReturn {
  complementos: ComplementoResponse[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function useComplementosCombo(
  comboId: number | null,
  apenasAtivos: boolean = true
): UseComplementosComboReturn {
  const [complementos, setComplementos] = useState<ComplementoResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const buscar = async () => {
    if (!comboId) {
      setComplementos([]);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('super_token');
      const response = await fetch(
        `/api/catalogo/client/complementos/combo/${comboId}?apenas_ativos=${apenasAtivos}`,
        {
          method: 'GET',
          headers: {
            'X-Super-Token': token || '',
          },
        }
      );
      
      if (!response.ok) {
        throw new Error('Erro ao buscar complementos do combo');
      }
      
      const resultado = await response.json();
      setComplementos(resultado);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao buscar complementos');
      setComplementos([]);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    buscar();
  }, [comboId, apenasAtivos]);
  
  return {
    complementos,
    loading,
    error,
    refetch: buscar,
  };
}
```

### Exemplo 2: Componente de Seleção de Complementos

```typescript
interface SelecaoComplementosProps {
  complementos: ComplementoResponse[];
  complementosSelecionados: Map<number, CartItemComplemento>;
  onChange: (complementoId: number, adicionalId: number, quantidade: number) => void;
}

function SelecaoComplementos({
  complementos,
  complementosSelecionados,
  onChange,
}: SelecaoComplementosProps) {
  return (
    <div className="space-y-4">
      {complementos.map(complemento => (
        <div key={complemento.id} className="border rounded p-4">
          <h3 className="font-bold mb-2">
            {complemento.nome}
            {complemento.obrigatorio && (
              <span className="text-red-500 ml-1">*</span>
            )}
          </h3>
          
          {complemento.descricao && (
            <p className="text-sm text-gray-600 mb-2">{complemento.descricao}</p>
          )}
          
          {complemento.permite_multipla_escolha ? (
            // Múltipla escolha: checkboxes
            <div className="space-y-2">
              {complemento.adicionais.map(adicional => {
                const selecionado = complementosSelecionados
                  .get(complemento.id)
                  ?.adicionais.find(a => a.adicional_id === adicional.id);
                
                const quantidade = selecionado?.quantidade || 0;
                
                return (
                  <div key={adicional.id} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={quantidade > 0}
                      onChange={(e) => {
                        onChange(
                          complemento.id,
                          adicional.id,
                          e.target.checked ? 1 : 0
                        );
                      }}
                    />
                    <span>{adicional.nome}</span>
                    {adicional.preco > 0 && (
                      <span className="text-green-600">
                        +R$ {adicional.preco.toFixed(2)}
                      </span>
                    )}
                    
                    {complemento.quantitativo && quantidade > 0 && (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() =>
                            onChange(complemento.id, adicional.id, quantidade - 1)
                          }
                        >
                          -
                        </button>
                        <span>{quantidade}</span>
                        <button
                          onClick={() =>
                            onChange(complemento.id, adicional.id, quantidade + 1)
                          }
                        >
                          +
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            // Escolha única: radio buttons
            <div className="space-y-2">
              {complemento.adicionais.map(adicional => {
                const selecionado = complementosSelecionados
                  .get(complemento.id)
                  ?.adicionais.find(a => a.adicional_id === adicional.id);
                
                const quantidade = selecionado?.quantidade || 0;
                
                return (
                  <div key={adicional.id} className="flex items-center gap-2">
                    <input
                      type="radio"
                      name={`complemento-${complemento.id}`}
                      checked={quantidade > 0}
                      onChange={() => {
                        onChange(complemento.id, adicional.id, 1);
                      }}
                    />
                    <span>{adicional.nome}</span>
                    {adicional.preco > 0 && (
                      <span className="text-green-600">
                        +R$ {adicional.preco.toFixed(2)}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

### Exemplo 3: Gerenciamento de Estado de Complementos

```typescript
function useGerenciamentoComplementos(
  complementos: ComplementoResponse[]
) {
  const [complementosSelecionados, setComplementosSelecionados] = useState<
    Map<number, CartItemComplemento>
  >(new Map());
  
  const selecionarAdicional = (
    complementoId: number,
    adicionalId: number,
    quantidade: number
  ) => {
    setComplementosSelecionados(prev => {
      const novo = new Map(prev);
      
      const complemento = complementos.find(c => c.id === complementoId);
      if (!complemento) return prev;
      
      // Se quantidade <= 0, remover
      if (quantidade <= 0) {
        const compSelecionado = novo.get(complementoId);
        if (compSelecionado) {
          const novosAdicionais = compSelecionado.adicionais.filter(
            a => a.adicional_id !== adicionalId
          );
          
          if (novosAdicionais.length === 0) {
            novo.delete(complementoId);
          } else {
            novo.set(complementoId, {
              ...compSelecionado,
              adicionais: novosAdicionais,
            });
          }
        }
        return novo;
      }
      
      // Verificar se permite múltipla escolha
      if (!complemento.permite_multipla_escolha) {
        // Remover outros adicionais do mesmo complemento
        const novosAdicionais = [
          {
            adicional_id: adicionalId,
            quantidade: complemento.quantitativo ? quantidade : 1,
            adicional_nome: complemento.adicionais.find(a => a.id === adicionalId)?.nome,
            adicional_preco: complemento.adicionais.find(a => a.id === adicionalId)?.preco || 0,
          },
        ];
        
        novo.set(complementoId, {
          complemento_id: complementoId,
          adicionais: novosAdicionais,
          complemento_nome: complemento.nome,
        });
      } else {
        // Adicionar ou atualizar adicional
        const compSelecionado = novo.get(complementoId) || {
          complemento_id: complementoId,
          adicionais: [],
          complemento_nome: complemento.nome,
        };
        
        const indexExistente = compSelecionado.adicionais.findIndex(
          a => a.adicional_id === adicionalId
        );
        
        const novosAdicionais = [...compSelecionado.adicionais];
        
        if (indexExistente >= 0) {
          novosAdicionais[indexExistente] = {
            ...novosAdicionais[indexExistente],
            quantidade: complemento.quantitativo ? quantidade : 1,
          };
        } else {
          novosAdicionais.push({
            adicional_id: adicionalId,
            quantidade: complemento.quantitativo ? quantidade : 1,
            adicional_nome: complemento.adicionais.find(a => a.id === adicionalId)?.nome,
            adicional_preco: complemento.adicionais.find(a => a.id === adicionalId)?.preco || 0,
          });
        }
        
        novo.set(complementoId, {
          ...compSelecionado,
          adicionais: novosAdicionais,
        });
      }
      
      return novo;
    });
  };
  
  const limparSelecao = () => {
    setComplementosSelecionados(new Map());
  };
  
  const converterParaCartItemComplementos = (): CartItemComplemento[] => {
    return Array.from(complementosSelecionados.values());
  };
  
  return {
    complementosSelecionados,
    selecionarAdicional,
    limparSelecao,
    converterParaCartItemComplementos,
  };
}
```

---

## ✅ Checklist de Migração

### Fase 1: Preparação
- [ ] Criar novos tipos TypeScript
- [ ] Criar serviços de busca de complementos
- [ ] Atualizar tipos do carrinho
- [ ] Atualizar tipos de pedido

### Fase 2: Componentes
- [ ] Atualizar `SheetAddProduto` para usar complementos
- [ ] Atualizar `SheetAddReceita` para usar complementos
- [ ] Atualizar `SheetAddCombo` para usar complementos
- [ ] Criar componente `SelecaoComplementos`
- [ ] Criar hook `useGerenciamentoComplementos`

### Fase 3: Store do Carrinho
- [ ] Atualizar função `add` para aceitar complementos
- [ ] Atualizar função `addCombo` para aceitar complementos
- [ ] Atualizar função `addReceita` para aceitar complementos
- [ ] Atualizar cálculo de preço total
- [ ] Atualizar agrupamento de itens idênticos

### Fase 4: Checkout
- [ ] Atualizar `mapCartToPedidoItems`
- [ ] Atualizar `finalizarPedido`
- [ ] Validar formato do request

### Fase 5: Validações
- [ ] Implementar validação de complementos obrigatórios
- [ ] Implementar validação de quantidade mínima/máxima
- [ ] Implementar validação de múltipla escolha vs. escolha única

### Fase 6: Testes
- [ ] Testar adicionar produto com complementos
- [ ] Testar adicionar combo com complementos
- [ ] Testar adicionar receita com complementos
- [ ] Testar validações
- [ ] Testar finalização de pedido
- [ ] Testar cálculo de preços

### Fase 7: Limpeza
- [ ] Remover código legado de adicionais diretos
- [ ] Atualizar testes unitários
- [ ] Atualizar documentação

---

## 📞 Suporte

Em caso de dúvidas ou problemas durante a migração:

1. Consulte a documentação completa em `docs/API_COMBOS_CRUD.md`
2. Consulte o guia específico de migração: `docs/MIGRACAO_FRONTEND_RECEITAS_COMBOS_COMPLEMENTOS.md`
3. Verifique os exemplos de código neste documento
4. Entre em contato com a equipe de backend para esclarecimentos sobre a API

## ⚠️ Mudanças Importantes (v2.0.0)

### Receitas
- **ANTES**: Receitas tinham adicionais diretos via `POST /api/catalogo/admin/receitas/adicionais`
- **AGORA**: Receitas têm complementos diretamente vinculados via `GET /api/catalogo/client/complementos/receita/{receita_id}`
- **AÇÃO**: Remover código de adicionais diretos e usar complementos

### Combos
- **ANTES**: Combos não tinham complementos/adicionais
- **AGORA**: Combos têm complementos diretamente vinculados via `GET /api/catalogo/client/complementos/combo/{combo_id}`
- **AÇÃO**: Implementar busca e seleção de complementos para combos

---

## 📅 Histórico de Versões

- **v1.0.0** (Janeiro 2024): Migração inicial para sistema de complementos hierárquicos
- **v1.1.0** (Janeiro 2024): Adicionado suporte a `minimo_itens` e `maximo_itens`
- **v2.0.0** (Dezembro 2024): Receitas e combos agora usam complementos diretamente vinculados (não mais adicionais diretos)

---

**Base URL**: `/api/catalogo/client/complementos`

**Autenticação**: Requer header `X-Super-Token` do cliente

**Endpoint de Finalização**: `POST /api/pedidos/checkout/finalizar`

