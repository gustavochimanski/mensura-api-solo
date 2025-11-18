# 🔄 Mudança: Adicionais em Receitas - Preço Automático do Cadastro

## 📋 Resumo da Mudança

Ao adicionar ou atualizar um adicional em uma receita, o **preço é SEMPRE buscado automaticamente do cadastro do produto**. Não é mais possível enviar ou sobrescrever o preço manualmente.

---

## 🎯 O Que Mudou

### ❌ ANTES (Lógica Antiga)

O preço podia ser enviado manualmente:

```json
POST /api/catalogo/admin/receitas/adicionais
{
  "receita_id": 1,
  "adicional_cod_barras": "7891234567890",
  "preco": 5.00  // Podia ser informado
}
```

**Problema:** Tinha que gerenciar preços manualmente e manter sincronização.

---

### ✅ AGORA (Nova Lógica)

O preço é **SEMPRE buscado automaticamente** do cadastro do produto (`ProdutoEmpModel`):

```json
POST /api/catalogo/admin/receitas/adicionais
{
  "receita_id": 1,
  "adicional_cod_barras": "7891234567890"
  // preco NÃO existe mais - sempre busca do cadastro
}
```

**Benefício:** 
- ✅ Sincronização automática com preços do cadastro
- ✅ Menos campos para enviar
- ✅ Menos erros (não precisa buscar preço manualmente)
- ✅ Preços sempre atualizados

---

## 📝 Schemas Atualizados

### AdicionalIn (Request)

```typescript
{
  receita_id: number;                    // OBRIGATÓRIO
  adicional_cod_barras: string;          // OBRIGATÓRIO, min 1 caractere
  // preco REMOVIDO - sempre busca automaticamente do ProdutoEmpModel
}
```

### AdicionalOut (Response)

```typescript
{
  id: number;
  receita_id: number;
  adicional_cod_barras: string;
  preco: number;                         // Sempre preenchido automaticamente do cadastro
}
```

---

## 🔌 Como Usar - Endpoints

### 1. Adicionar Adicional

**Endpoint:**
```http
POST /api/catalogo/admin/receitas/adicionais
```

**Request Body:**
```json
{
  "receita_id": 1,
  "adicional_cod_barras": "7891234567890"
}
```

**Comportamento:**
- Busca automaticamente o `preco_venda` do `ProdutoEmpModel` para a empresa da receita
- Se não encontrar preço cadastrado, usa `0.00` como padrão
- O preço é sempre sincronizado com o cadastro

**Response (201 Created):**
```json
{
  "id": 5,
  "receita_id": 1,
  "adicional_cod_barras": "7891234567890",
  "preco": 5.00  // Preço buscado automaticamente do cadastro
}
```

---

### 2. Atualizar Adicional (Sincronizar Preço)

**Endpoint:**
```http
PUT /api/catalogo/admin/receitas/adicionais/{adicional_id}
```

**Request Body:**
```json
{}
```

**OU simplesmente sem body:**

**Comportamento:**
- Busca novamente o preço atual do `ProdutoEmpModel`
- Atualiza o preço do adicional para o preço atual do cadastro
- Útil para sincronizar quando o preço do produto mudar

**Response (200 OK):**
```json
{
  "id": 5,
  "receita_id": 1,
  "adicional_cod_barras": "7891234567890",
  "preco": 5.50  // Novo preço do cadastro (atualizado)
}
```

---

## 💻 Exemplos de Código Frontend

### JavaScript/TypeScript

```typescript
// Tipo
interface AdicionalIn {
  receita_id: number;
  adicional_cod_barras: string;
  // preco não existe mais
}

// Função para adicionar adicional
async function adicionarAdicionalAReceita(
  receitaId: number,
  codBarras: string
): Promise<AdicionalOut> {
  const response = await fetch('/api/catalogo/admin/receitas/adicionais', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      receita_id: receitaId,
      adicional_cod_barras: codBarras
      // preco não precisa ser enviado - busca automaticamente
    })
  });
  
  return response.json();
}

// Uso: Adicionar adicional (muito simples agora!)
const adicional = await adicionarAdicionalAReceita(1, '7891234567890');
console.log(`Preço: R$ ${adicional.preco}`); // Preço já vem preenchido
```

---

### Função para Sincronizar Preços

```typescript
// Função para atualizar/sincronizar adicional
async function sincronizarPrecoAdicional(
  adicionalId: number
): Promise<AdicionalOut> {
  const response = await fetch(`/api/catalogo/admin/receitas/adicionais/${adicionalId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({}) // Body vazio - apenas sincroniza
  });
  
  return response.json();
}

// Uso: Sincronizar preço quando o produto mudou
const adicionalAtualizado = await sincronizarPrecoAdicional(5);
```

---

### React Component - Exemplo Completo

```typescript
import React, { useState } from 'react';

interface Adicional {
  cod_barras: string;
  nome: string;
  preco_venda?: number;  // Preço do cadastro (apenas para exibição)
}

interface AdicionarAdicionalFormProps {
  receitaId: number;
  adicional: Adicional;
  onSuccess: () => void;
}

const AdicionarAdicionalForm: React.FC<AdicionarAdicionalFormProps> = ({
  receitaId,
  adicional,
  onSuccess
}) => {
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('/api/catalogo/admin/receitas/adicionais', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          receita_id: receitaId,
          adicional_cod_barras: adicional.cod_barras
          // Preço será buscado automaticamente do cadastro
        })
      });

      if (!response.ok) {
        throw new Error('Erro ao adicionar adicional');
      }

      const resultado = await response.json();
      console.log(`Adicional adicionado com preço: R$ ${resultado.preco}`);
      
      onSuccess();
    } catch (error) {
      console.error('Erro:', error);
      alert('Erro ao adicionar adicional');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <h3>{adicional.nome}</h3>
        <p>
          <strong>Preço que será usado:</strong> R$ {adicional.preco_venda?.toFixed(2) || '0.00'}
          <br />
          <small>(Preço será buscado automaticamente do cadastro do produto)</small>
        </p>
      </div>

      <button type="submit" disabled={loading}>
        {loading ? 'Adicionando...' : 'Adicionar Adicional'}
      </button>
    </form>
  );
};
```

---

### Listar e Sincronizar Adicionais

```typescript
// Listar adicionais de uma receita
async function listarAdicionais(receitaId: number): Promise<AdicionalOut[]> {
  const response = await fetch(`/api/catalogo/admin/receitas/${receitaId}/adicionais`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}

// Sincronizar todos os preços de uma receita
async function sincronizarPrecosAdicionais(receitaId: number): Promise<void> {
  const adicionais = await listarAdicionais(receitaId);
  
  for (const adicional of adicionais) {
    await sincronizarPrecoAdicional(adicional.id);
  }
  
  console.log('Preços sincronizados!');
}
```

---

## 🎯 Casos de Uso

### Caso 1: Adicionar Adicional (Mais Comum) ✅

```typescript
// Simples e direto - preço é buscado automaticamente
await adicionarAdicionalAReceita(1, "7891234567890");
```

**Vantagem:** Não precisa buscar ou enviar o preço manualmente.

---

### Caso 2: Sincronizar Preços Após Mudança no Cadastro

Quando o preço de um produto mudou no cadastro e você quer atualizar todas as receitas:

```typescript
// Sincroniza um adicional específico
await sincronizarPrecoAdicional(5);

// OU sincroniza todos os adicionais de uma receita
await sincronizarPrecosAdicionais(1);
```

**Vantagem:** Mantém preços sempre atualizados.

---

### Caso 3: Exibir Preço Esperado Antes de Adicionar

```typescript
// Buscar preço do produto antes de adicionar (para mostrar ao usuário)
async function buscarPrecoProduto(empresaId: number, codBarras: string): Promise<number> {
  const response = await fetch(`/api/cadastros/admin/produtos/${codBarras}?empresa_id=${empresaId}`);
  const produto = await response.json();
  return produto.produtos_empresa?.preco_venda || 0;
}

// Usar antes de adicionar
const precoEsperado = await buscarPrecoProduto(1, "7891234567890");
console.log(`O adicional será adicionado com preço: R$ ${precoEsperado}`);
await adicionarAdicionalAReceita(1, "7891234567890");
```

---

## 📊 Fluxo de Decisão

```
Adicionar Adicional a Receita
│
├─ Busca ReceitaModel (para obter empresa_id)
│
├─ Busca ProdutoEmpModel
│  │
│  ├─ empresa_id = receita.empresa_id
│  └─ cod_barras = adicional_cod_barras
│
├─ Encontrou ProdutoEmpModel?
│  │
│  ├─ SIM → Usa preco_venda do ProdutoEmpModel
│  │
│  └─ NÃO → Usa 0.00 como padrão
│
└─ Cria ReceitaAdicionalModel com preço encontrado
```

---

## ⚠️ Validações e Erros

### Erro 400: Adicional já cadastrado
```json
{
  "detail": "Adicional já cadastrado nesta receita"
}
```

### Erro 404: Produto não encontrado
```json
{
  "detail": "Produto adicional não encontrado"
}
```

### Erro 404: Receita não encontrada
```json
{
  "detail": "Receita não encontrada"
}
```

**Nota:** Se o produto não tiver preço cadastrado no `ProdutoEmpModel`, será usado `0.00` como padrão (não gera erro).

---

## 🔄 Migração do Código Antigo

### Código Antigo (não funciona mais)
```typescript
// ❌ ERRO: campo 'preco' não existe mais
await adicionarAdicional({
  receita_id: 1,
  adicional_cod_barras: "7891234567890",
  preco: 5.00  // ❌ Este campo não existe mais!
});
```

### Código Novo (correto)
```typescript
// ✅ CORRETO: apenas receita_id e cod_barras
await adicionarAdicional({
  receita_id: 1,
  adicional_cod_barras: "7891234567890"
  // preco será buscado automaticamente
});
```

### Código Antigo para Atualizar (não funciona mais)
```typescript
// ❌ ERRO: não aceita mais parâmetro 'preco'
await atualizarAdicional(5, 6.00);  // ❌ Não funciona
```

### Código Novo para Sincronizar (correto)
```typescript
// ✅ CORRETO: apenas sincroniza o preço do cadastro
await sincronizarPrecoAdicional(5);  // ✅ Busca do cadastro
```

---

## 📝 Checklist para Migração Frontend

- [ ] **Remover campo `preco`** de todos os formulários de adicionar adicional
- [ ] **Remover validações** do campo `preco`
- [ ] **Atualizar interfaces/typescript** - remover `preco?` de `AdicionalIn`
- [ ] **Atualizar chamadas PUT** - remover parâmetro `preco` de `update_adicional`
- [ ] **Testar** que preços estão sendo buscados corretamente
- [ ] **Adicionar botão "Sincronizar preços"** se necessário
- [ ] **Atualizar documentação** interna do frontend

---

## 🎯 Benefícios da Mudança

1. ✅ **Menos código:** Não precisa buscar/enviar preço manualmente
2. ✅ **Sincronização automática:** Preços sempre atualizados com o cadastro
3. ✅ **Menos erros:** Não há risco de preço desatualizado
4. ✅ **Mais simples:** Menos campos para gerenciar
5. ✅ **Consistência:** Todos os preços vêm do mesmo lugar (cadastro)

---

## 🔍 Como o Preço é Buscado

O sistema busca o preço na seguinte ordem:

1. **ProdutoEmpModel** com `empresa_id` da receita e `cod_barras` do adicional
2. Usa o campo `preco_venda` do `ProdutoEmpModel`
3. Se não encontrar, usa `0.00` como padrão

**Importante:** O preço é buscado **sempre** da empresa da receita, garantindo que cada empresa tenha seus próprios preços.

---

## 📌 Resumo

| Ação | Antes | Agora |
|------|-------|-------|
| **Adicionar Adicional** | Enviar `preco` manualmente | ✅ Preço buscado automaticamente |
| **Atualizar Adicional** | Pode enviar novo `preco` | ✅ Sincroniza com cadastro |
| **Campos no Request** | 3 campos | ✅ 2 campos (mais simples) |
| **Sincronização** | Manual | ✅ Automática |

---

**Última atualização:** 2025-01-18
