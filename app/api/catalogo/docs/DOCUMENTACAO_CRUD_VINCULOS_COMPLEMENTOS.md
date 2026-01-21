# Documentação Completa - CRUD de Vínculos de Complementos

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Estrutura de Dados](#estrutura-de-dados)
3. [Endpoints - Produtos](#endpoints---produtos)
4. [Endpoints - Receitas](#endpoints---receitas)
5. [Endpoints - Combos](#endpoints---combos)
6. [Endpoints - Itens de Complementos](#endpoints---itens-de-complementos)
7. [Problemas Identificados](#problemas-identificados)
8. [Exemplos de Uso](#exemplos-de-uso)
9. [Troubleshooting](#troubleshooting)

---

## Visão Geral

O sistema permite vincular **complementos** a **produtos**, **receitas** e **combos**. Cada vinculação possui configurações específicas:

- `obrigatorio`: Se o complemento é obrigatório nesta vinculação
- `quantitativo`: Se permite quantidade (ex: 2x bacon) e múltipla escolha
- `minimo_itens`: Quantidade mínima de itens (null = sem mínimo)
- `maximo_itens`: Quantidade máxima de itens (null = sem limite)
- `ordem`: Ordem de exibição do complemento

**Importante:** As configurações são definidas **na vinculação**, não no complemento em si. Isso permite que o mesmo complemento tenha comportamentos diferentes em cada produto/receita/combo.

---

## Estrutura de Dados

### Tabelas de Vinculação

1. **`produto_complemento_link`**: Vincula produtos a complementos
   - `produto_cod_barras` (PK)
   - `complemento_id` (PK)
   - `ordem`, `obrigatorio`, `quantitativo`, `minimo_itens`, `maximo_itens`

2. **`receita_complemento_link`**: Vincula receitas a complementos
   - `receita_id` (PK)
   - `complemento_id` (PK)
   - `ordem`, `obrigatorio`, `quantitativo`, `minimo_itens`, `maximo_itens`

3. **`combo_complemento_link`**: Vincula combos a complementos
   - `combo_id` (PK)
   - `complemento_id` (PK)
   - `ordem`, `obrigatorio`, `quantitativo`, `minimo_itens`, `maximo_itens`

---

## Endpoints - Produtos

### 1. Vincular Complementos a Produto

**Endpoint:** `POST /api/catalogo/admin/complementos/produto/{cod_barras}/vincular`

**Autenticação:** Requerida (Admin)

**Descrição:** Vincula múltiplos complementos a um produto. Remove todas as vinculações existentes e cria novas.

**Parâmetros de URL:**
- `cod_barras` (string, obrigatório): Código de barras do produto

**Body Request - Formato Completo (Recomendado):**
```json
{
  "configuracoes": [
    {
      "complemento_id": 1,
      "ordem": 0,
      "obrigatorio": true,
      "quantitativo": false,
      "minimo_itens": 1,
      "maximo_itens": 1
    },
    {
      "complemento_id": 2,
      "ordem": 1,
      "obrigatorio": false,
      "quantitativo": true,
      "minimo_itens": null,
      "maximo_itens": 3
    }
  ]
}
```

**Body Request - Formato Simples (Compatibilidade):**
```json
{
  "complemento_ids": [1, 2, 3],
  "ordens": [0, 1, 2]
}
```

**Campos do Formato Completo:**
- `complemento_id` (int, obrigatório): ID do complemento
- `ordem` (int, opcional): Ordem de exibição (usa índice se não informado)
- `obrigatorio` (bool, obrigatório): Se é obrigatório
- `quantitativo` (bool, obrigatório): Se permite quantidade e múltipla escolha
- `minimo_itens` (int, opcional): Mínimo de itens (null = sem mínimo)
- `maximo_itens` (int, opcional): Máximo de itens (null = sem limite)

**Response 200:**
```json
{
  "produto_cod_barras": "123456789",
  "complementos_vinculados": [
    {
      "id": 1,
      "nome": "Bebidas",
      "obrigatorio": true,
      "quantitativo": false,
      "minimo_itens": 1,
      "maximo_itens": 1,
      "ordem": 0
    }
  ],
  "message": "Complementos vinculados com sucesso"
}
```

**Erros Possíveis:**
- `404`: Produto não encontrado
- `404`: Complemento(s) não encontrado(s)
- `400`: Validação de dados inválida

---

### 2. Listar Complementos de um Produto

**Endpoint:** `GET /api/catalogo/admin/complementos/produto/{cod_barras}`

**Autenticação:** Requerida (Admin)

**Parâmetros de URL:**
- `cod_barras` (string, obrigatório): Código de barras do produto

**Query Parameters:**
- `apenas_ativos` (bool, opcional, padrão: `true`): Retornar apenas complementos ativos

**Response 200:**
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Bebidas",
    "descricao": "Escolha sua bebida",
    "obrigatorio": true,
    "quantitativo": false,
    "minimo_itens": 1,
    "maximo_itens": 1,
    "ordem": 0,
    "ativo": true,
    "adicionais": [
      {
        "id": 1,
        "nome": "Coca-Cola",
        "descricao": "350ml",
        "preco": 5.0,
        "custo": 2.0,
        "ativo": true,
        "ordem": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

**Nota:** Os campos `obrigatorio`, `quantitativo`, `minimo_itens`, `maximo_itens` e `ordem` vêm da **vinculação**, não do complemento.

---

### 3. Desvincular Complemento de Produto

**⚠️ PROBLEMA IDENTIFICADO:** Não existe endpoint para desvincular um complemento específico de um produto.

**Solução Atual:** Use o endpoint de vincular com lista vazia ou sem o complemento desejado.

**Solução Recomendada:** Criar endpoint `DELETE /api/catalogo/admin/complementos/produto/{cod_barras}/{complemento_id}`

---

## Endpoints - Receitas

### 1. Vincular Complementos a Receita

**Endpoint:** `POST /api/catalogo/admin/complementos/receita/{receita_id}/vincular`  
**Endpoint Alternativo:** `PUT /api/catalogo/admin/receitas/{receita_id}/complementos`

**Autenticação:** Requerida (Admin)

**Descrição:** Vincula múltiplos complementos a uma receita. Remove todas as vinculações existentes e cria novas.

**Parâmetros de URL:**
- `receita_id` (int, obrigatório): ID da receita

**Body Request:** Mesma estrutura do endpoint de produtos

**Response 200:**
```json
{
  "receita_id": 1,
  "complementos_vinculados": [
    {
      "id": 1,
      "nome": "Bebidas",
      "obrigatorio": true,
      "quantitativo": false,
      "minimo_itens": 1,
      "maximo_itens": 1,
      "ordem": 0
    }
  ],
  "message": "Complementos vinculados com sucesso"
}
```

---

### 2. Listar Complementos de uma Receita

**Endpoint:** `GET /api/catalogo/admin/complementos/receita/{receita_id}`

**Autenticação:** Requerida (Admin)

**Parâmetros de URL:**
- `receita_id` (int, obrigatório): ID da receita

**Query Parameters:**
- `apenas_ativos` (bool, opcional, padrão: `true`): Retornar apenas complementos ativos

**Response 200:** Mesma estrutura do endpoint de produtos

---

### 3. Desvincular Complemento de Receita

**⚠️ PROBLEMA IDENTIFICADO:** Não existe endpoint para desvincular um complemento específico de uma receita.

**Solução Atual:** Use o endpoint de vincular com lista vazia ou sem o complemento desejado.

**Solução Recomendada:** Criar endpoint `DELETE /api/catalogo/admin/complementos/receita/{receita_id}/{complemento_id}`

---

## Endpoints - Combos

### 1. Vincular Complementos a Combo

**Endpoint:** `POST /api/catalogo/admin/complementos/combo/{combo_id}/vincular`

**Autenticação:** Requerida (Admin)

**Descrição:** Vincula múltiplos complementos a um combo. Remove todas as vinculações existentes e cria novas. **Permite lista vazia para remover todas as vinculações.**

**Parâmetros de URL:**
- `combo_id` (int, obrigatório): ID do combo

**Body Request - Formato Completo:**
```json
{
  "configuracoes": [
    {
      "complemento_id": 1,
      "ordem": 0,
      "obrigatorio": true,
      "quantitativo": false,
      "minimo_itens": 1,
      "maximo_itens": 1
    }
  ]
}
```

**Body Request - Remover Todas as Vinculações:**
```json
{
  "complemento_ids": []
}
```

**Response 200:** Mesma estrutura do endpoint de produtos

**Validações Especiais:**
- Valida se todos os complementos pertencem à mesma empresa do combo
- Lista vazia é permitida (remove todas as vinculações)

---

### 2. Listar Complementos de um Combo

**Endpoint:** `GET /api/catalogo/admin/complementos/combo/{combo_id}`

**Autenticação:** Requerida (Admin)

**Parâmetros de URL:**
- `combo_id` (int, obrigatório): ID do combo

**Query Parameters:**
- `apenas_ativos` (bool, opcional, padrão: `true`): Retornar apenas complementos ativos

**Response 200:** Mesma estrutura do endpoint de produtos

---

### 3. Desvincular Complemento de Combo

**⚠️ PROBLEMA IDENTIFICADO:** Não existe endpoint para desvincular um complemento específico de um combo.

**Solução Atual:** Use o endpoint de vincular com lista vazia ou sem o complemento desejado.

**Solução Recomendada:** Criar endpoint `DELETE /api/catalogo/admin/complementos/combo/{combo_id}/{complemento_id}`

---

## Endpoints - Itens de Complementos

### 1. Vincular Múltiplos Itens a um Complemento

**Endpoint:** `POST /api/catalogo/admin/complementos/{complemento_id}/itens/vincular`

**Autenticação:** Requerida (Admin)

**Descrição:** Vincula múltiplos itens a um complemento. Remove todas as vinculações existentes e cria novas.

**Parâmetros de URL:**
- `complemento_id` (int, obrigatório): ID do complemento

**Body Request:**
```json
{
  "item_ids": [1, 2, 3],
  "ordens": [0, 1, 2],
  "precos": [5.0, 3.0, 4.0]
}
```

**Campos:**
- `item_ids` (array[int], obrigatório): IDs dos itens a vincular
- `ordens` (array[int], opcional): Ordens de exibição (usa índice se não informado)
- `precos` (array[decimal], opcional): Preços específicos por item neste complemento (alinhados por índice)

**Response 200:**
```json
{
  "complemento_id": 1,
  "itens_vinculados": [
    {
      "id": 1,
      "nome": "Bacon",
      "descricao": "Fatias de bacon",
      "preco": 5.0,
      "custo": 2.0,
      "ativo": true,
      "ordem": 0,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "message": "Itens vinculados com sucesso"
}
```

**Validações:**
- Todos os itens devem pertencer à mesma empresa do complemento
- Todos os itens devem existir

---

### 2. Adicionar Um Item a um Complemento

**Endpoint:** `POST /api/catalogo/admin/complementos/{complemento_id}/itens/adicionar`

**Autenticação:** Requerida (Admin)

**Descrição:** Adiciona um único item a um complemento. Se já estiver vinculado, atualiza ordem e/ou preço.

**Parâmetros de URL:**
- `complemento_id` (int, obrigatório): ID do complemento

**Body Request:**
```json
{
  "item_id": 1,
  "ordem": 0,
  "preco_complemento": 5.0
}
```

**Campos:**
- `item_id` (int, obrigatório): ID do item
- `ordem` (int, opcional): Ordem de exibição (usa maior ordem + 1 se não informado)
- `preco_complemento` (decimal, opcional): Preço específico neste complemento

**Response 201:** Mesma estrutura do endpoint anterior

---

### 3. Desvincular Item de Complemento

**Endpoint:** `DELETE /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}`

**Autenticação:** Requerida (Admin)

**Descrição:** Remove a vinculação de um item com um complemento. **Não deleta o item**, apenas remove o vínculo.

**Parâmetros de URL:**
- `complemento_id` (int, obrigatório): ID do complemento
- `item_id` (int, obrigatório): ID do item

**Response 200:**
```json
{
  "message": "Item desvinculado com sucesso"
}
```

---

### 4. Listar Itens de um Complemento

**Endpoint:** `GET /api/catalogo/admin/complementos/{complemento_id}/itens`

**Autenticação:** Requerida (Admin)

**Parâmetros de URL:**
- `complemento_id` (int, obrigatório): ID do complemento

**Query Parameters:**
- `apenas_ativos` (bool, opcional, padrão: `true`): Retornar apenas itens ativos

**Response 200:**
```json
[
  {
    "id": 1,
    "nome": "Bacon",
    "descricao": "Fatias de bacon",
    "preco": 5.0,
    "custo": 2.0,
    "ativo": true,
    "ordem": 0,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### 5. Atualizar Ordem dos Itens

**Endpoint:** `PUT /api/catalogo/admin/complementos/{complemento_id}/itens/ordem`

**Autenticação:** Requerida (Admin)

**Descrição:** Atualiza a ordem dos itens em um complemento.

**Parâmetros de URL:**
- `complemento_id` (int, obrigatório): ID do complemento

**Body Request - Formato Simples:**
```json
{
  "item_ids": [3, 1, 2]
}
```
A ordem será definida pelo índice (0, 1, 2).

**Body Request - Formato Completo:**
```json
{
  "item_ordens": [
    {"item_id": 3, "ordem": 0},
    {"item_id": 1, "ordem": 1},
    {"item_id": 2, "ordem": 2}
  ]
}
```

**Response 200:**
```json
{
  "message": "Ordem dos itens atualizada com sucesso"
}
```

---

### 6. Atualizar Preço de Item no Complemento

**Endpoint:** `PUT /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}/preco`

**Autenticação:** Requerida (Admin)

**Descrição:** Atualiza o preço de um item **apenas dentro deste complemento**. Não altera o preço padrão do item.

**Parâmetros de URL:**
- `complemento_id` (int, obrigatório): ID do complemento
- `item_id` (int, obrigatório): ID do item

**Body Request:**
```json
{
  "preco": 6.0
}
```

**Response 200:**
```json
{
  "id": 1,
  "nome": "Bacon",
  "descricao": "Fatias de bacon",
  "preco": 6.0,
  "custo": 2.0,
  "ativo": true,
  "ordem": 0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

## Problemas Identificados

### 1. ❌ Falta Endpoint para Desvincular Complemento de Produto/Receita/Combo

**Problema:** Não existe endpoint para desvincular um complemento específico. Apenas é possível substituir todas as vinculações.

**Impacto:** Para remover um complemento, é necessário:
1. Listar todos os complementos vinculados
2. Remover o desejado da lista
3. Chamar o endpoint de vincular novamente

**Solução Recomendada:**
- `DELETE /api/catalogo/admin/complementos/produto/{cod_barras}/{complemento_id}`
- `DELETE /api/catalogo/admin/complementos/receita/{receita_id}/{complemento_id}`
- `DELETE /api/catalogo/admin/complementos/combo/{combo_id}/{complemento_id}`

**Status:** Os métodos existem no repositório (`desvincular_complemento_produto`, `desvincular_complemento_receita`, `desvincular_complemento_combo`), mas não estão expostos como endpoints.

---

### 2. ⚠️ Endpoint Duplicado para Receitas

**Problema:** Existem dois endpoints para vincular complementos a receitas:
- `POST /api/catalogo/admin/complementos/receita/{receita_id}/vincular`
- `PUT /api/catalogo/admin/receitas/{receita_id}/complementos`

**Impacto:** Pode causar confusão sobre qual endpoint usar.

**Recomendação:** Manter apenas um endpoint (preferencialmente o POST em `/complementos/receita/{receita_id}/vincular` para consistência).

---

### 3. ⚠️ Falta Endpoint para Atualizar Configuração de Vinculação

**Problema:** Não existe endpoint para atualizar apenas as configurações de uma vinculação específica (obrigatorio, quantitativo, minimo_itens, maximo_itens, ordem) sem substituir todas as vinculações.

**Impacto:** Para atualizar uma configuração, é necessário:
1. Listar todas as vinculações
2. Modificar a desejada
3. Chamar o endpoint de vincular novamente

**Solução Recomendada:**
- `PUT /api/catalogo/admin/complementos/produto/{cod_barras}/{complemento_id}`
- `PUT /api/catalogo/admin/complementos/receita/{receita_id}/{complemento_id}`
- `PUT /api/catalogo/admin/complementos/combo/{combo_id}/{complemento_id}`

---

### 4. ⚠️ Bug Potencial no Service de Combos

**Problema:** No método `vincular_complementos_combo` do service (linha 326), o parâmetro `quantitativos` não está sendo passado para o repositório.

**Código Atual:**
```python
self.repo.vincular_complementos_combo(
    combo_id, 
    complemento_ids, 
    ordens, 
    obrigatorios, 
    minimos_itens,  # ❌ Faltando quantitativos
    maximos_itens
)
```

**Código Correto:**
```python
self.repo.vincular_complementos_combo(
    combo_id, 
    complemento_ids, 
    ordens, 
    obrigatorios, 
    quantitativos,  # ✅ Adicionar
    minimos_itens, 
    maximos_itens
)
```

**Status:** ⚠️ **BUG IDENTIFICADO - CORREÇÃO NECESSÁRIA**

---

## Exemplos de Uso

### Exemplo 1: Vincular Complementos a um Produto

```bash
curl -X POST "https://api.exemplo.com/api/catalogo/admin/complementos/produto/123456789/vincular" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "configuracoes": [
      {
        "complemento_id": 1,
        "ordem": 0,
        "obrigatorio": true,
        "quantitativo": false,
        "minimo_itens": 1,
        "maximo_itens": 1
      },
      {
        "complemento_id": 2,
        "ordem": 1,
        "obrigatorio": false,
        "quantitativo": true,
        "minimo_itens": null,
        "maximo_itens": 3
      }
    ]
  }'
```

### Exemplo 2: Listar Complementos de um Produto

```bash
curl -X GET "https://api.exemplo.com/api/catalogo/admin/complementos/produto/123456789?apenas_ativos=true" \
  -H "Authorization: Bearer TOKEN"
```

### Exemplo 3: Remover Todos os Complementos de um Combo

```bash
curl -X POST "https://api.exemplo.com/api/catalogo/admin/complementos/combo/5/vincular" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "complemento_ids": []
  }'
```

### Exemplo 4: Vincular Itens a um Complemento

```bash
curl -X POST "https://api.exemplo.com/api/catalogo/admin/complementos/1/itens/vincular" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item_ids": [1, 2, 3],
    "ordens": [0, 1, 2],
    "precos": [5.0, 3.0, 4.0]
  }'
```

### Exemplo 5: Desvincular Item de Complemento

```bash
curl -X DELETE "https://api.exemplo.com/api/catalogo/admin/complementos/1/itens/5" \
  -H "Authorization: Bearer TOKEN"
```

---

## Troubleshooting

### Problema: Complementos não aparecem após vincular

**Possíveis Causas:**
1. O complemento está inativo (`ativo = false`)
2. O parâmetro `apenas_ativos=true` está filtrando o complemento
3. Erro na transação (verificar logs)

**Solução:**
- Verificar se o complemento está ativo
- Usar `apenas_ativos=false` para ver todos os complementos
- Verificar logs do servidor

---

### Problema: Configurações não são aplicadas

**Possíveis Causas:**
1. Usando formato simples em vez de formato completo
2. Valores padrão sendo aplicados incorretamente
3. Bug no service (verificar se `quantitativos` está sendo passado)

**Solução:**
- Usar formato completo (`configuracoes`) em vez de formato simples
- Verificar se todos os campos obrigatórios estão sendo enviados
- Verificar logs do servidor

---

### Problema: Erro ao desvincular

**Possíveis Causas:**
1. Endpoint de desvincular não existe (usar workaround)
2. Complemento/Item não existe
3. Vinculação não existe

**Solução:**
- Usar endpoint de vincular com lista atualizada (workaround)
- Verificar se o complemento/item existe
- Verificar se a vinculação existe antes de tentar desvincular

---

### Problema: Ordem não é respeitada

**Possíveis Causas:**
1. Ordem não está sendo enviada corretamente
2. Ordem duplicada (múltiplos complementos com mesma ordem)
3. Ordem sendo sobrescrita

**Solução:**
- Verificar se a ordem está sendo enviada no body
- Garantir que cada complemento tenha ordem única
- Verificar se não há conflito na atualização

---

## Resumo dos Endpoints

| Método | Endpoint | Descrição | Status |
|--------|----------|-----------|--------|
| POST | `/complementos/produto/{cod_barras}/vincular` | Vincular complementos a produto | ✅ Funcionando |
| GET | `/complementos/produto/{cod_barras}` | Listar complementos de produto | ✅ Funcionando |
| DELETE | `/complementos/produto/{cod_barras}/{complemento_id}` | Desvincular complemento de produto | ❌ **NÃO EXISTE** |
| PUT | `/complementos/produto/{cod_barras}/{complemento_id}` | Atualizar configuração de vinculação | ❌ **NÃO EXISTE** |
| POST | `/complementos/receita/{receita_id}/vincular` | Vincular complementos a receita | ✅ Funcionando |
| PUT | `/receitas/{receita_id}/complementos` | Vincular complementos a receita (alternativo) | ✅ Funcionando (duplicado) |
| GET | `/complementos/receita/{receita_id}` | Listar complementos de receita | ✅ Funcionando |
| DELETE | `/complementos/receita/{receita_id}/{complemento_id}` | Desvincular complemento de receita | ❌ **NÃO EXISTE** |
| PUT | `/complementos/receita/{receita_id}/{complemento_id}` | Atualizar configuração de vinculação | ❌ **NÃO EXISTE** |
| POST | `/complementos/combo/{combo_id}/vincular` | Vincular complementos a combo | ⚠️ **BUG: faltando quantitativos** |
| GET | `/complementos/combo/{combo_id}` | Listar complementos de combo | ✅ Funcionando |
| DELETE | `/complementos/combo/{combo_id}/{complemento_id}` | Desvincular complemento de combo | ❌ **NÃO EXISTE** |
| PUT | `/complementos/combo/{combo_id}/{complemento_id}` | Atualizar configuração de vinculação | ❌ **NÃO EXISTE** |
| POST | `/complementos/{complemento_id}/itens/vincular` | Vincular múltiplos itens | ✅ Funcionando |
| POST | `/complementos/{complemento_id}/itens/adicionar` | Adicionar um item | ✅ Funcionando |
| DELETE | `/complementos/{complemento_id}/itens/{item_id}` | Desvincular item | ✅ Funcionando |
| GET | `/complementos/{complemento_id}/itens` | Listar itens do complemento | ✅ Funcionando |
| PUT | `/complementos/{complemento_id}/itens/ordem` | Atualizar ordem dos itens | ✅ Funcionando |
| PUT | `/complementos/{complemento_id}/itens/{item_id}/preco` | Atualizar preço do item | ✅ Funcionando |

---

## Conclusão

O CRUD de vínculos de complementos está **parcialmente funcional**. Os endpoints principais de vinculação e listagem funcionam, mas há algumas limitações:

1. **Falta endpoints de desvinculação** para produtos, receitas e combos
2. **Falta endpoints de atualização** de configurações individuais
3. **Bug identificado** no service de combos (faltando parâmetro `quantitativos`)
4. **Endpoint duplicado** para receitas

**Recomendação:** Implementar os endpoints faltantes e corrigir o bug antes de considerar o sistema completo.

---

**Última Atualização:** 2024-01-XX  
**Versão da Documentação:** 1.0
