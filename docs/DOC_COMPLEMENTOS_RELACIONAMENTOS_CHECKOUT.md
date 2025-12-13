# 📘 Documentação Completa: Sistema de Complementos - Relacionamentos e Checkout

## 🎯 Objetivo

Este documento explica **como funciona** o sistema de complementos, seus relacionamentos com produtos, receitas e combos, e como implementar corretamente o checkout. Esta documentação é focada em **entender o funcionamento**, não em implementação específica.

---

## 📋 Índice

1. [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
2. [Estrutura Hierárquica](#estrutura-hierárquica)
3. [Relacionamentos](#relacionamentos)
4. [Como Funcionam os Complementos](#como-funcionam-os-complementos)
5. [Como Funcionam os Itens (Adicionais)](#como-funcionam-os-itens-adicionais)
6. [Preços e Cálculos](#preços-e-cálculos)
7. [Checkout - Estrutura de Dados](#checkout---estrutura-de-dados)
8. [Checkout - Processamento no Backend](#checkout---processamento-no-backend)
9. [Regras de Negócio](#regras-de-negócio)
10. [Exemplos Práticos](#exemplos-práticos)

---

## 🏗️ Visão Geral da Arquitetura

### Hierarquia do Sistema

O sistema de complementos segue uma estrutura hierárquica de 3 níveis:

```
Nível 1: Produto/Receita/Combo
    ↓ (vinculação N:N)
Nível 2: Complemento (grupo de opções)
    ↓ (vinculação N:N)
Nível 3: Item/Adicional (opção individual)
```

### Conceitos Fundamentais

**Complemento:**
- É um **grupo** que agrupa itens relacionados
- Exemplos: "Tamanho", "Bebida", "Adicionais", "Tipo de Pão"
- Tem configurações próprias (obrigatório, quantitativo, múltipla escolha)
- Pode ser vinculado a múltiplos produtos, receitas ou combos

**Item/Adicional:**
- É uma **opção individual** dentro de um complemento
- Exemplos: "Pequeno", "Coca-Cola", "Bacon", "Pão Francês"
- Tem preço próprio
- Pode pertencer a múltiplos complementos (com preços diferentes em cada um)

**Produto/Receita/Combo:**
- Entidades que podem ter complementos vinculados
- Cada uma tem sua própria lista de complementos disponíveis
- Os complementos são específicos para cada produto/receita/combo

---

## 🌳 Estrutura Hierárquica

### Nível 1: Produto, Receita ou Combo

Cada produto, receita ou combo pode ter **zero ou mais complementos** vinculados diretamente.

**Exemplo:**
- Produto "Hambúrguer" → pode ter complementos: "Tamanho", "Adicionais", "Bebida"
- Receita "Pizza Margherita" → pode ter complementos: "Tamanho", "Borda"
- Combo "Combo Família" → pode ter complementos: "Bebida", "Sobremesa"

### Nível 2: Complemento

Cada complemento:
- Agrupa itens relacionados logicamente
- Define regras de seleção (obrigatório, quantitativo, múltipla escolha)
- Define limites (mínimo e máximo de itens)
- Tem ordem de exibição

**Exemplo de Complemento "Tamanho":**
- Nome: "Tamanho"
- Obrigatório: `true`
- Quantitativo: `false`
- Permite múltipla escolha: `false`
- Mínimo itens: `1`
- Máximo itens: `1`

### Nível 3: Item/Adicional

Cada item:
- É uma opção dentro de um complemento
- Tem nome, descrição e preço
- Pode ter preço diferente em cada complemento que pertence
- Tem ordem de exibição dentro do complemento

**Exemplo de Itens no Complemento "Tamanho":**
- Item 1: "Pequeno" - R$ 0,00
- Item 2: "Médio" - R$ 5,00
- Item 3: "Grande" - R$ 10,00

---

## 🔗 Relacionamentos

### 1. Produto ↔ Complemento (N:N)

**Tabela de Associação:** `produto_complemento_link`

**Como funciona:**
- Um produto pode ter múltiplos complementos
- Um complemento pode estar vinculado a múltiplos produtos
- A vinculação é feita pelo `cod_barras` do produto e `id` do complemento
- Cada vinculação tem uma `ordem` de exibição

**Exemplo:**
```
Produto "Hambúrguer" (cod_barras: "HB001")
  ├─ Complemento "Tamanho" (id: 1) - ordem: 1
  ├─ Complemento "Adicionais" (id: 2) - ordem: 2
  └─ Complemento "Bebida" (id: 3) - ordem: 3
```

**Busca de Complementos:**
- Endpoint: `GET /api/catalogo/public/complementos/produto/{cod_barras}`
- **Endpoint público** - não requer autenticação
- Retorna apenas os complementos **vinculados diretamente** ao produto
- Retorna os complementos com seus itens já incluídos

### 2. Receita ↔ Complemento (N:N)

**Tabela de Associação:** `receita_complemento_link`

**Como funciona:**
- Uma receita pode ter múltiplos complementos
- Um complemento pode estar vinculado a múltiplas receitas
- A vinculação é feita pelo `id` da receita e `id` do complemento
- Cada vinculação tem uma `ordem` de exibição

**Exemplo:**
```
Receita "Pizza Margherita" (id: 5)
  ├─ Complemento "Tamanho" (id: 1) - ordem: 1
  └─ Complemento "Borda" (id: 4) - ordem: 2
```

**Busca de Complementos:**
- Endpoint: `GET /api/catalogo/public/complementos/receita/{receita_id}`
- **Endpoint público** - não requer autenticação
- Retorna apenas os complementos **vinculados diretamente** à receita
- Retorna os complementos com seus itens já incluídos

### 3. Combo ↔ Complemento (N:N)

**Tabela de Associação:** `combo_complemento_link`

**Como funciona:**
- Um combo pode ter múltiplos complementos
- Um complemento pode estar vinculado a múltiplos combos
- A vinculação é feita pelo `id` do combo e `id` do complemento
- Cada vinculação tem uma `ordem` de exibição

**Exemplo:**
```
Combo "Combo Família" (id: 3)
  ├─ Complemento "Bebida" (id: 3) - ordem: 1
  └─ Complemento "Sobremesa" (id: 5) - ordem: 2
```

**Busca de Complementos:**
- Endpoint: `GET /api/catalogo/public/complementos/combo/{combo_id}`
- **Endpoint público** - não requer autenticação
- Retorna apenas os complementos **vinculados diretamente** ao combo
- Retorna os complementos com seus itens já incluídos

### 4. Complemento ↔ Item/Adicional (N:N)

**Tabela de Associação:** `complemento_item_link`

**Como funciona:**
- Um complemento pode ter múltiplos itens
- Um item pode pertencer a múltiplos complementos
- A vinculação é feita pelo `id` do complemento e `id` do item
- Cada vinculação pode ter um **preço específico** para aquele complemento
- Cada vinculação tem uma `ordem` de exibição

**Exemplo:**
```
Complemento "Adicionais" (id: 2)
  ├─ Item "Bacon" (id: 10) - preço: R$ 5,00 - ordem: 1
  ├─ Item "Queijo Extra" (id: 11) - preço: R$ 3,00 - ordem: 2
  └─ Item "Ovo" (id: 12) - preço: R$ 2,00 - ordem: 3
```

**Preço Específico por Complemento:**
- Cada item tem um **preço padrão** (na tabela `adicionais`)
- Quando vinculado a um complemento, pode ter um **preço específico** (na tabela `complemento_item_link`)
- Se houver preço específico, ele **sobrescreve** o preço padrão
- Se não houver preço específico, usa o preço padrão do item

**Exemplo de Preço Específico:**
```
Item "Bacon" (id: 10)
  ├─ Preço padrão: R$ 5,00
  ├─ No Complemento "Adicionais" (id: 2): R$ 5,00 (usa padrão)
  └─ No Complemento "Adicionais Premium" (id: 6): R$ 7,00 (preço específico)
```

---

## ⚙️ Como Funcionam os Complementos

### Propriedades do Complemento

Cada complemento tem as seguintes propriedades que definem seu comportamento:

#### 1. `obrigatorio` (boolean)

**Como funciona:**
- Se `true`: o cliente **deve** selecionar pelo menos um item deste complemento
- Se `false`: o complemento é opcional

**Exemplo:**
- Complemento "Tamanho" → `obrigatorio: true` (cliente deve escolher um tamanho)
- Complemento "Adicionais" → `obrigatorio: false` (cliente pode não escolher nenhum)

#### 2. `quantitativo` (boolean)

**Como funciona:**
- Se `true`: o cliente pode selecionar **quantidade > 1** do mesmo item
- Se `false`: o cliente pode apenas selecionar o item (quantidade sempre = 1)

**Exemplo:**
- Complemento "Adicionais" → `quantitativo: true` (cliente pode escolher "2x Bacon")
- Complemento "Tamanho" → `quantitativo: false` (cliente escolhe apenas "Médio", não "2x Médio")

#### 3. `permite_multipla_escolha` (boolean)

**Como funciona:**
- Se `true`: o cliente pode selecionar **múltiplos itens diferentes** no mesmo complemento
- Se `false`: o cliente pode selecionar apenas **um item** no complemento

**Exemplo:**
- Complemento "Adicionais" → `permite_multipla_escolha: true` (cliente pode escolher "Bacon" + "Queijo Extra")
- Complemento "Tamanho" → `permite_multipla_escolha: false` (cliente escolhe apenas "Médio")

#### 4. `minimo_itens` (integer | null)

**Como funciona:**
- Define a **quantidade mínima** de itens que o cliente deve selecionar neste complemento
- Se `null`: não há mínimo específico (usa a regra de obrigatório)
- Soma a quantidade total de todos os itens selecionados

**Exemplo:**
- Complemento "Adicionais" → `minimo_itens: 2` (cliente deve escolher pelo menos 2 itens no total)
- Complemento "Tamanho" → `minimo_itens: null` (usa apenas a regra de obrigatório)

#### 5. `maximo_itens` (integer | null)

**Como funciona:**
- Define a **quantidade máxima** de itens que o cliente pode selecionar neste complemento
- Se `null`: não há limite máximo
- Soma a quantidade total de todos os itens selecionados

**Exemplo:**
- Complemento "Adicionais" → `maximo_itens: 5` (cliente pode escolher no máximo 5 itens no total)
- Complemento "Tamanho" → `maximo_itens: null` (não há limite)

### Combinações de Propriedades

**Exemplo 1: Complemento "Tamanho"**
```
obrigatorio: true
quantitativo: false
permite_multipla_escolha: false
minimo_itens: 1
maximo_itens: 1
```
**Comportamento:** Cliente **deve** escolher exatamente **um** tamanho (radio button).

**Exemplo 2: Complemento "Adicionais"**
```
obrigatorio: false
quantitativo: true
permite_multipla_escolha: true
minimo_itens: null
maximo_itens: 5
```
**Comportamento:** Cliente **pode** escolher múltiplos adicionais diferentes, cada um com quantidade, até no máximo 5 itens no total (checkboxes com seletor de quantidade).

**Exemplo 3: Complemento "Bebida"**
```
obrigatorio: true
quantitativo: false
permite_multipla_escolha: false
minimo_itens: 1
maximo_itens: 1
```
**Comportamento:** Cliente **deve** escolher exatamente **uma** bebida (radio button).

---

## 🎯 Como Funcionam os Itens (Adicionais)

### Propriedades do Item

Cada item tem as seguintes propriedades:

#### 1. `id` (integer)

**Como funciona:**
- ID único do item
- Usado como `adicional_id` no checkout
- **IMPORTANTE:** No checkout, sempre usar `adicional_id`, nunca `id`

#### 2. `nome` (string)

**Como funciona:**
- Nome do item (ex: "Bacon", "Pequeno", "Coca-Cola")
- Usado apenas para exibição no frontend
- **NÃO** é enviado no checkout

#### 3. `preco` (decimal)

**Como funciona:**
- Preço **efetivo** do item no contexto do complemento
- Se houver preço específico no complemento, retorna esse preço
- Se não houver, retorna o preço padrão do item
- O backend calcula automaticamente qual preço usar

**Exemplo:**
```
Item "Bacon" (id: 10)
  ├─ Preço padrão: R$ 5,00
  ├─ No Complemento "Adicionais" (id: 2): preço retornado = R$ 5,00
  └─ No Complemento "Adicionais Premium" (id: 6): preço retornado = R$ 7,00
```

#### 4. `ordem` (integer)

**Como funciona:**
- Ordem de exibição do item dentro do complemento
- Pode ser diferente em cada complemento que o item pertence

### Preço do Item

**Regra de Preço:**
1. O item tem um **preço padrão** (na tabela `adicionais`)
2. Quando vinculado a um complemento, pode ter um **preço específico** (na tabela `complemento_item_link`)
3. O preço retornado na API é sempre o **preço efetivo** (específico se existir, senão padrão)
4. No checkout, o backend recalcula o preço para garantir consistência

**IMPORTANTE:**
- O frontend **não deve** enviar preços no checkout
- O backend **sempre** recalcula os preços baseado nos IDs enviados
- Isso garante que mudanças de preço não quebrem pedidos em andamento

---

## 💰 Preços e Cálculos

### Como o Preço é Calculado

#### 1. Preço Base do Item/Produto/Receita/Combo

Cada item tem um preço base:
- **Produto:** `preco_venda` do produto
- **Receita:** `preco_venda` da receita
- **Combo:** `preco_total` do combo
- **Item/Adicional:** `preco` do item (efetivo no complemento)

#### 2. Preço dos Complementos

O preço dos complementos é calculado assim:

```
Para cada complemento selecionado:
  Para cada adicional selecionado no complemento:
    preco_adicional = preco_unitario_do_adicional
    quantidade_adicional = quantidade_selecionada (ou 1 se não quantitativo)
    subtotal_adicional = preco_adicional * quantidade_adicional
    
  total_complemento = soma de todos os subtotais_adicionais

total_complementos = soma de todos os totais_complementos
```

#### 3. Preço Total do Item no Pedido

```
preco_total_item = (preco_base * quantidade_item) + (total_complementos * quantidade_item)
```

**Exemplo:**
```
Produto "Hambúrguer" - R$ 20,00
Quantidade: 2

Complemento "Tamanho" (obrigatório):
  - Adicional "Médio" - R$ 5,00 (quantidade: 1)

Complemento "Adicionais" (opcional):
  - Adicional "Bacon" - R$ 5,00 (quantidade: 2)
  - Adicional "Queijo Extra" - R$ 3,00 (quantidade: 1)

Cálculo:
  preco_base = R$ 20,00
  quantidade = 2
  
  complementos_por_item = R$ 5,00 + (R$ 5,00 * 2) + R$ 3,00 = R$ 18,00
  
  preco_total = (R$ 20,00 * 2) + (R$ 18,00 * 2) = R$ 40,00 + R$ 36,00 = R$ 76,00
```

### Multiplicação pela Quantidade

**IMPORTANTE:**
- Os complementos são **multiplicados pela quantidade** do item
- Se o cliente compra 2 hambúrgueres, os complementos são aplicados 2 vezes

**Exemplo:**
```
Cliente compra 2 hambúrgueres, cada um com:
  - Tamanho: Médio (+R$ 5,00)
  - Adicionais: Bacon (+R$ 5,00)

Cálculo:
  preco_base = R$ 20,00 * 2 = R$ 40,00
  complementos = (R$ 5,00 + R$ 5,00) * 2 = R$ 20,00
  total = R$ 60,00
```

---

## 🛒 Checkout - Estrutura de Dados

### Estrutura do Request

O checkout envia os dados no seguinte formato:

```json
{
  "empresa_id": 1,
  "tipo_pedido": "DELIVERY",
  "produtos": {
    "itens": [
      {
        "produto_cod_barras": "HB001",
        "quantidade": 2,
        "observacao": "Sem cebola",
        "complementos": [
          {
            "complemento_id": 1,
            "adicionais": [
              {
                "adicional_id": 10,
                "quantidade": 1
              }
            ]
          },
          {
            "complemento_id": 2,
            "adicionais": [
              {
                "adicional_id": 11,
                "quantidade": 2
              },
              {
                "adicional_id": 12,
                "quantidade": 1
              }
            ]
          }
        ]
      }
    ],
    "receitas": [
      {
        "receita_id": 5,
        "quantidade": 1,
        "observacao": null,
        "complementos": [
          {
            "complemento_id": 1,
            "adicionais": [
              {
                "adicional_id": 10,
                "quantidade": 1
              }
            ]
          }
        ]
      }
    ],
    "combos": [
      {
        "combo_id": 3,
        "quantidade": 1,
        "complementos": [
          {
            "complemento_id": 3,
            "adicionais": [
              {
                "adicional_id": 15,
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

### Campos Obrigatórios

**Para cada item no checkout:**

1. **Produto (`ItemPedidoRequest`):**
   - `produto_cod_barras` (string) - **OBRIGATÓRIO**
   - `quantidade` (integer) - **OBRIGATÓRIO**
   - `observacao` (string | null) - opcional
   - `complementos` (array | null) - opcional

2. **Receita (`ReceitaPedidoRequest`):**
   - `receita_id` (integer) - **OBRIGATÓRIO**
   - `quantidade` (integer) - **OBRIGATÓRIO**
   - `observacao` (string | null) - opcional
   - `complementos` (array | null) - opcional

3. **Combo (`ComboPedidoRequest`):**
   - `combo_id` (integer) - **OBRIGATÓRIO**
   - `quantidade` (integer) - **OBRIGATÓRIO** (default: 1)
   - `complementos` (array | null) - opcional

**Para cada complemento (`ItemComplementoRequest`):**
   - `complemento_id` (integer) - **OBRIGATÓRIO**
   - `adicionais` (array) - **OBRIGATÓRIO** (pode ser vazio se complemento não obrigatório)

**Para cada adicional (`ItemAdicionalComplementoRequest`):**
   - `adicional_id` (integer) - **OBRIGATÓRIO**
   - `quantidade` (integer) - **OBRIGATÓRIO** (mínimo: 1)

### O que NÃO Enviar

**NÃO enviar no checkout:**
- Nomes de complementos ou adicionais
- Preços (backend calcula)
- Descrições
- Campos de exibição (`complemento_nome`, `adicional_nome`, etc.)
- IDs diferentes de `complemento_id` e `adicional_id`

**Motivo:**
- O backend recalcula tudo baseado nos IDs
- Isso garante consistência mesmo se houver mudanças de preço/nome
- Reduz o tamanho do payload

---

## 🔄 Checkout - Processamento no Backend

### Fluxo de Processamento

#### 1. Validação Inicial

O backend valida:
- Se o produto/receita/combo existe e está ativo
- Se pertence à empresa correta
- Se os complementos enviados existem e estão vinculados ao item
- Se os adicionais enviados existem e pertencem aos complementos

#### 2. Busca de Complementos

**Para Produtos:**
- Busca complementos vinculados ao produto pelo `cod_barras`
- Valida se os `complemento_id` enviados estão na lista de complementos do produto

**Para Receitas:**
- Busca complementos vinculados à receita pelo `receita_id`
- Valida se os `complemento_id` enviados estão na lista de complementos da receita

**Para Combos:**
- Busca complementos vinculados ao combo pelo `combo_id`
- Valida se os `complemento_id` enviados estão na lista de complementos do combo

#### 3. Validação de Regras

Para cada complemento enviado, o backend valida:

**Complemento Obrigatório:**
- Se `obrigatorio: true`, verifica se pelo menos um adicional foi selecionado
- Se não, retorna erro

**Quantidade Mínima:**
- Se `minimo_itens` estiver definido, soma a quantidade de todos os adicionais
- Se a soma for menor que `minimo_itens`, retorna erro

**Quantidade Máxima:**
- Se `maximo_itens` estiver definido, soma a quantidade de todos os adicionais
- Se a soma for maior que `maximo_itens`, retorna erro

**Quantitativo:**
- Se `quantitativo: false`, força `quantidade: 1` para cada adicional
- Se `quantitativo: true`, usa a quantidade enviada

**Múltipla Escolha:**
- Se `permite_multipla_escolha: false`, verifica se apenas um adicional foi selecionado
- Se mais de um foi selecionado, retorna erro

#### 4. Cálculo de Preços

Para cada item:

1. **Busca preço base:**
   - Produto: `preco_venda` do produto
   - Receita: `preco_venda` da receita
   - Combo: `preco_total` do combo

2. **Calcula preço dos complementos:**
   - Para cada complemento:
     - Para cada adicional:
       - Busca preço efetivo (específico do complemento ou padrão)
       - Multiplica pela quantidade do adicional
       - Soma ao total do complemento
   - Soma todos os totais dos complementos

3. **Calcula preço total:**
   - `(preco_base * quantidade_item) + (total_complementos * quantidade_item)`

#### 5. Criação do Pedido

O backend cria:
- Um registro de pedido
- Um registro de item de pedido para cada produto/receita/combo
- Um registro de adicional de pedido para cada adicional selecionado
- Calcula o total do pedido (soma de todos os itens)

---

## 📐 Regras de Negócio

### 1. Complementos Obrigatórios

**Regra:**
- Se um complemento tem `obrigatorio: true`, o cliente **deve** selecionar pelo menos um item
- A validação acontece no frontend (antes de adicionar ao carrinho) e no backend (no checkout)

**Exemplo:**
```
Complemento "Tamanho" (obrigatorio: true)
  - Cliente DEVE escolher: "Pequeno", "Médio" ou "Grande"
  - Se não escolher, não pode adicionar ao carrinho
```

### 2. Complementos Quantitativos

**Regra:**
- Se `quantitativo: true`, o cliente pode selecionar quantidade > 1 do mesmo item
- Se `quantitativo: false`, a quantidade é sempre 1 (mesmo que o cliente envie outro valor)

**Exemplo:**
```
Complemento "Adicionais" (quantitativo: true)
  - Cliente pode escolher: "2x Bacon", "3x Queijo Extra"

Complemento "Tamanho" (quantitativo: false)
  - Cliente escolhe apenas: "Médio" (quantidade sempre = 1)
```

### 3. Múltipla Escolha

**Regra:**
- Se `permite_multipla_escolha: true`, o cliente pode selecionar múltiplos itens diferentes
- Se `permite_multipla_escolha: false`, o cliente pode selecionar apenas um item

**Exemplo:**
```
Complemento "Adicionais" (permite_multipla_escolha: true)
  - Cliente pode escolher: "Bacon" + "Queijo Extra" + "Ovo"

Complemento "Tamanho" (permite_multipla_escolha: false)
  - Cliente escolhe apenas: "Médio" (não pode escolher "Médio" + "Grande")
```

### 4. Limites Mínimo e Máximo

**Regra:**
- `minimo_itens`: soma a quantidade de **todos os adicionais** selecionados no complemento
- `maximo_itens`: soma a quantidade de **todos os adicionais** selecionados no complemento
- Se `null`, não há limite

**Exemplo:**
```
Complemento "Adicionais" (minimo_itens: 2, maximo_itens: 5)
  - Cliente seleciona: "Bacon" (quantidade: 2) + "Queijo Extra" (quantidade: 1)
  - Total de itens: 3 (dentro do limite de 2 a 5) ✅
  
  - Se selecionar apenas "Bacon" (quantidade: 1)
  - Total de itens: 1 (abaixo do mínimo de 2) ❌
```

### 5. Preço Específico por Complemento

**Regra:**
- Um item pode ter preço diferente em cada complemento
- O preço específico **sobrescreve** o preço padrão
- O backend sempre retorna o preço efetivo na API

**Exemplo:**
```
Item "Bacon" (id: 10)
  - Preço padrão: R$ 5,00
  - No Complemento "Adicionais" (id: 2): R$ 5,00 (usa padrão)
  - No Complemento "Adicionais Premium" (id: 6): R$ 7,00 (preço específico)
```

### 6. Multiplicação pela Quantidade do Item

**Regra:**
- Os complementos são **multiplicados pela quantidade** do item
- Se o cliente compra 2 hambúrgueres, os complementos são aplicados 2 vezes

**Exemplo:**
```
Cliente compra 2 hambúrgueres, cada um com:
  - Tamanho: Médio (+R$ 5,00)
  - Adicionais: Bacon (+R$ 5,00)

Cálculo:
  preco_base = R$ 20,00 * 2 = R$ 40,00
  complementos = (R$ 5,00 + R$ 5,00) * 2 = R$ 20,00
  total = R$ 60,00
```

---

## 💡 Exemplos Práticos

### Exemplo 1: Produto com Complementos Simples

**Produto:** Hambúrguer (cod_barras: "HB001", preço: R$ 20,00)

**Complementos Vinculados:**
1. Complemento "Tamanho" (id: 1)
   - Obrigatório: `true`
   - Quantitativo: `false`
   - Múltipla escolha: `false`
   - Itens:
     - "Pequeno" (id: 10) - R$ 0,00
     - "Médio" (id: 11) - R$ 5,00
     - "Grande" (id: 12) - R$ 10,00

2. Complemento "Adicionais" (id: 2)
   - Obrigatório: `false`
   - Quantitativo: `true`
   - Múltipla escolha: `true`
   - Itens:
     - "Bacon" (id: 20) - R$ 5,00
     - "Queijo Extra" (id: 21) - R$ 3,00
     - "Ovo" (id: 22) - R$ 2,00

**Seleção do Cliente:**
- Tamanho: "Médio" (id: 11)
- Adicionais: "Bacon" (id: 20, quantidade: 2) + "Queijo Extra" (id: 21, quantidade: 1)

**Cálculo:**
```
Preço base: R$ 20,00
Complementos:
  - Tamanho "Médio": R$ 5,00
  - Adicionais: (R$ 5,00 * 2) + (R$ 3,00 * 1) = R$ 13,00
Total: R$ 20,00 + R$ 5,00 + R$ 13,00 = R$ 38,00
```

**Request no Checkout:**
```json
{
  "produto_cod_barras": "HB001",
  "quantidade": 1,
  "complementos": [
    {
      "complemento_id": 1,
      "adicionais": [
        {
          "adicional_id": 11,
          "quantidade": 1
        }
      ]
    },
    {
      "complemento_id": 2,
      "adicionais": [
        {
          "adicional_id": 20,
          "quantidade": 2
        },
        {
          "adicional_id": 21,
          "quantidade": 1
        }
      ]
    }
  ]
}
```

### Exemplo 2: Receita com Complementos

**Receita:** Pizza Margherita (id: 5, preço: R$ 35,00)

**Complementos Vinculados:**
1. Complemento "Tamanho" (id: 1)
   - Obrigatório: `true`
   - Itens:
     - "Pequena" (id: 10) - R$ 0,00
     - "Média" (id: 11) - R$ 10,00
     - "Grande" (id: 12) - R$ 20,00

2. Complemento "Borda" (id: 4)
   - Obrigatório: `false`
   - Itens:
     - "Borda Recheada" (id: 30) - R$ 8,00
     - "Borda Catupiry" (id: 31) - R$ 10,00

**Seleção do Cliente:**
- Tamanho: "Média" (id: 11)
- Borda: "Borda Recheada" (id: 30)

**Cálculo:**
```
Preço base: R$ 35,00
Complementos:
  - Tamanho "Média": R$ 10,00
  - Borda "Borda Recheada": R$ 8,00
Total: R$ 35,00 + R$ 10,00 + R$ 8,00 = R$ 53,00
```

**Request no Checkout:**
```json
{
  "receita_id": 5,
  "quantidade": 1,
  "complementos": [
    {
      "complemento_id": 1,
      "adicionais": [
        {
          "adicional_id": 11,
          "quantidade": 1
        }
      ]
    },
    {
      "complemento_id": 4,
      "adicionais": [
        {
          "adicional_id": 30,
          "quantidade": 1
        }
      ]
    }
  ]
}
```

### Exemplo 3: Combo com Complementos

**Combo:** Combo Família (id: 3, preço: R$ 50,00)

**Complementos Vinculados:**
1. Complemento "Bebida" (id: 3)
   - Obrigatório: `true`
   - Itens:
     - "Coca-Cola" (id: 40) - R$ 0,00
     - "Pepsi" (id: 41) - R$ 0,00
     - "Guaraná" (id: 42) - R$ 0,00

2. Complemento "Sobremesa" (id: 5)
   - Obrigatório: `false`
   - Itens:
     - "Pudim" (id: 50) - R$ 8,00
     - "Brigadeiro" (id: 51) - R$ 5,00

**Seleção do Cliente:**
- Bebida: "Coca-Cola" (id: 40)
- Sobremesa: "Pudim" (id: 50)

**Cálculo:**
```
Preço base: R$ 50,00
Complementos:
  - Bebida "Coca-Cola": R$ 0,00
  - Sobremesa "Pudim": R$ 8,00
Total: R$ 50,00 + R$ 0,00 + R$ 8,00 = R$ 58,00
```

**Request no Checkout:**
```json
{
  "combo_id": 3,
  "quantidade": 1,
  "complementos": [
    {
      "complemento_id": 3,
      "adicionais": [
        {
          "adicional_id": 40,
          "quantidade": 1
        }
      ]
    },
    {
      "complemento_id": 5,
      "adicionais": [
        {
          "adicional_id": 50,
          "quantidade": 1
        }
      ]
    }
  ]
}
```

### Exemplo 4: Item com Quantidade > 1

**Produto:** Hambúrguer (cod_barras: "HB001", preço: R$ 20,00)
**Quantidade:** 2

**Complementos:**
- Tamanho: "Médio" (id: 11) - R$ 5,00
- Adicionais: "Bacon" (id: 20, quantidade: 1) - R$ 5,00

**Cálculo:**
```
Preço base: R$ 20,00 * 2 = R$ 40,00
Complementos por item: R$ 5,00 + R$ 5,00 = R$ 10,00
Complementos totais: R$ 10,00 * 2 = R$ 20,00
Total: R$ 40,00 + R$ 20,00 = R$ 60,00
```

**Request no Checkout:**
```json
{
  "produto_cod_barras": "HB001",
  "quantidade": 2,
  "complementos": [
    {
      "complemento_id": 1,
      "adicionais": [
        {
          "adicional_id": 11,
          "quantidade": 1
        }
      ]
    },
    {
      "complemento_id": 2,
      "adicionais": [
        {
          "adicional_id": 20,
          "quantidade": 1
        }
      ]
    }
  ]
}
```

---

## 📝 Resumo das Regras Importantes

### Para o Frontend

1. **Buscar Complementos:**
   - Produtos: `GET /api/catalogo/public/complementos/produto/{cod_barras}` (público - sem autenticação)
   - Receitas: `GET /api/catalogo/public/complementos/receita/{receita_id}` (público - sem autenticação)
   - Combos: `GET /api/catalogo/public/complementos/combo/{combo_id}` (público - sem autenticação)

2. **Validar Antes de Adicionar ao Carrinho:**
   - Complementos obrigatórios devem ter pelo menos um item selecionado
   - Quantidade mínima/máxima deve ser respeitada
   - Múltipla escolha deve ser respeitada
   - Quantitativo deve ser respeitado

3. **Calcular Preço no Carrinho:**
   - Preço base * quantidade
   - + (soma dos preços dos complementos * quantidade do item)

4. **Enviar no Checkout:**
   - Apenas IDs (`complemento_id`, `adicional_id`)
   - Quantidades
   - **NÃO** enviar preços, nomes ou descrições

### Para o Backend

1. **Processar Checkout:**
   - Validar se complementos existem e estão vinculados
   - Validar se adicionais existem e pertencem aos complementos
   - Validar regras de negócio (obrigatório, mínimo, máximo, etc.)
   - Recalcular preços baseado nos IDs
   - Multiplicar complementos pela quantidade do item

2. **Cálculo de Preços:**
   - Buscar preço efetivo (específico do complemento ou padrão)
   - Multiplicar pela quantidade do adicional
   - Multiplicar pela quantidade do item

---

## 🔍 Endpoints de Referência

### Buscar Complementos

**Produto:**
```
GET /api/catalogo/public/complementos/produto/{cod_barras}?apenas_ativos=true
Headers: (nenhum - endpoint público)
Response: ComplementoResponse[]
```

**Receita:**
```
GET /api/catalogo/public/complementos/receita/{receita_id}?apenas_ativos=true
Headers: (nenhum - endpoint público)
Response: ComplementoResponse[]
```

**Combo:**
```
GET /api/catalogo/public/complementos/combo/{combo_id}?apenas_ativos=true
Headers: (nenhum - endpoint público)
Response: ComplementoResponse[]
```

### Finalizar Pedido

```
POST /api/pedidos/checkout/finalizar
Headers: 
  X-Super-Token: {token}
  Content-Type: application/json
Body: FinalizarPedidoRequest
```

---

## ⚠️ Pontos de Atenção

1. **IDs no Checkout:**
   - Sempre usar `adicional_id` (não `id`)
   - Sempre usar `complemento_id` (não `id`)

2. **Preços:**
   - **NÃO** enviar preços no checkout
   - Backend sempre recalcula baseado nos IDs
   - Preços podem mudar, mas os IDs são estáveis

3. **Quantidades:**
   - Quantidade do adicional: mínimo 1
   - Quantidade do item: mínimo 1
   - Se complemento não é quantitativo, quantidade do adicional é sempre 1

4. **Validações:**
   - Frontend deve validar antes de adicionar ao carrinho
   - Backend valida novamente no checkout
   - Se validação falhar no backend, pedido é rejeitado

5. **Multiplicação:**
   - Complementos são multiplicados pela quantidade do item
   - Se comprar 2 hambúrgueres, os complementos são aplicados 2 vezes

---

---

## 🔄 Histórico de Mudanças

### Versão 1.1 (Dezembro 2024)
- **Endpoints de complementos tornados públicos**: Todos os endpoints de listagem de complementos (produto, receita e combo) foram movidos para rotas públicas e não requerem mais autenticação (`X-Super-Token`).
- URLs atualizadas de `/api/catalogo/client/complementos/` para `/api/catalogo/public/complementos/`

**Última atualização:** Dezembro 2024  
**Versão:** 1.1

