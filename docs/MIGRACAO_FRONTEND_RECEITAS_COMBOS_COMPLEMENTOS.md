# 📘 Guia de Migração Frontend: Receitas e Combos com Complementos

## 🎯 Visão Geral

Este documento explica como adaptar o frontend para usar o novo sistema de **complementos** em receitas e combos, substituindo os adicionais diretos que eram usados anteriormente.

### O que mudou?

**ANTES:**
- Receitas tinham adicionais diretos vinculados
- Combos não tinham complementos/adicionais
- Estrutura: `Receita → Adicionais Diretos`

**AGORA:**
- Receitas têm **complementos** diretamente vinculados (como produtos)
- Combos têm **complementos** diretamente vinculados (como produtos)
- Estrutura: `Receita/Combo → Complementos → Adicionais`
- Mesma estrutura hierárquica que produtos

---

## 📋 Índice

1. [Mudanças na API](#mudanças-na-api)
2. [Migração de Receitas](#migração-de-receitas)
3. [Migração de Combos](#migração-de-combos)
4. [Novos Endpoints](#novos-endpoints)
5. [Estrutura de Dados](#estrutura-de-dados)
6. [Exemplos de Código](#exemplos-de-código)
7. [Checklist de Migração](#checklist-de-migração)

---

## 🔄 Mudanças na API

### Endpoints Deprecated (NÃO USAR MAIS)

❌ **DEPRECATED**: `POST /api/catalogo/admin/receitas/adicionais`
- Este endpoint ainda existe para compatibilidade, mas **não deve ser usado**
- Receitas agora usam complementos, não adicionais diretos

### Novos Endpoints

✅ **NOVO**: `GET /api/catalogo/client/complementos/receita/{receita_id}`
- Lista complementos vinculados diretamente à receita
- Retorna `ComplementoResponse[]` com adicionais dentro

✅ **NOVO**: `GET /api/catalogo/client/complementos/combo/{combo_id}`
- Lista complementos vinculados diretamente ao combo
- Retorna `ComplementoResponse[]` com adicionais dentro

### Endpoints Admin (para vincular complementos)

⚠️ **A IMPLEMENTAR**: Endpoints admin para vincular complementos a receitas/combos
- Similar aos endpoints de produtos: `POST /api/catalogo/admin/complementos/vincular-produto`
- Será necessário criar: `POST /api/catalogo/admin/complementos/vincular-receita`
- Será necessário criar: `POST /api/catalogo/admin/complementos/vincular-combo`

---

## 🔧 Migração de Receitas

### Situação Atual (ANTES)

No modal de criação de receitas, a **Etapa 3** vincula adicionais diretos:

```typescript
// ❌ ANTIGO - Etapa 3: Adicionais Diretos
const criarAdicional = async (data: {
  receita_id: number
  adicional_id: number
}) => {
  // POST /api/catalogo/admin/receitas/adicionais
  // Vincula adicional diretamente à receita
}
```

### Nova Situação (AGORA)

A **Etapa 3** deve vincular **complementos** (que contêm adicionais):

```typescript
// ✅ NOVO - Etapa 3: Complementos
const vincularComplementosReceita = async (
  receitaId: number,
  complementoIds: number[]
) => {
  // POST /api/catalogo/admin/complementos/vincular-receita
  // Vincula complementos diretamente à receita
}
```

### Passo a Passo da Migração

#### 1. Atualizar Etapa 3 do Modal

**Arquivo:** `src/app/(dashboard)/cadastros/receitas/_components/modal/criar-receita-modal.tsx`

**ANTES:**
```typescript
// Etapa 3: Adicionais Diretos
const [adicionaisSelecionados, setAdicionaisSelecionados] = useState<Array<{
  adicional_id: number
}>>([])

// Buscar adicionais da empresa
const buscarAdicionais = async (search: string) => {
  // GET /api/catalogo/admin/adicionais/?empresa_id=X&search=...
}
```

**AGORA:**
```typescript
// Etapa 3: Complementos
const [complementosSelecionados, setComplementosSelecionados] = useState<number[]>([])

// Buscar complementos da empresa
const buscarComplementos = async (search: string) => {
  // GET /api/catalogo/admin/complementos/?empresa_id=X&search=...
  // Retorna complementos com seus adicionais já incluídos
}
```

#### 2. Atualizar Action de Finalização

**ANTES:**
```typescript
const handleFinalizar = async () => {
  // Vincular adicionais diretos
  if (adicionaisSelecionados.length > 0) {
    await Promise.all(
      adicionaisSelecionados.map((adic) =>
        criarAdicional({
          receita_id: receitaId,
          adicional_id: adic.adicional_id,
        })
      )
    )
  }
}
```

**AGORA:**
```typescript
const handleFinalizar = async () => {
  // Vincular complementos
  if (complementosSelecionados.length > 0) {
    await vincularComplementosReceita(receitaId, complementosSelecionados)
  }
}
```

#### 3. Criar Nova Action

**Arquivo:** `src/actions/receitas/complementos/vincular-complementos-receita.ts`

```typescript
import { cookies } from 'next/headers'
import { revalidatePath } from 'next/cache'

export type VincularComplementosReceitaRequest = {
  receita_id: number
  complemento_ids: number[]
}

export type VincularComplementosReceitaResult = {
  success: boolean
  data?: any
  error?: string
}

export async function vincularComplementosReceita(
  data: VincularComplementosReceitaRequest
): Promise<VincularComplementosReceitaResult> {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')?.value

  if (!token) {
    return { success: false, error: 'Não autenticado' }
  }

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/catalogo/admin/complementos/vincular-receita`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          receita_id: data.receita_id,
          complemento_ids: data.complemento_ids,
        }),
      }
    )

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      return {
        success: false,
        error: error.detail || 'Erro ao vincular complementos',
      }
    }

    const resultado = await response.json()
    revalidatePath('/cadastros/receitas')
    return { success: true, data: resultado }
  } catch (error) {
    console.error('Erro ao vincular complementos:', error)
    return { success: false, error: 'Erro ao vincular complementos' }
  }
}
```

#### 4. Atualizar Interface da Etapa 3

A interface deve mostrar:
- Lista de complementos disponíveis (com busca)
- Cada complemento mostra seus adicionais dentro
- Seleção de complementos (checkbox ou similar)
- Visualização hierárquica: Complemento → Adicionais

**Exemplo de Componente:**

```typescript
// Etapa 3: Seleção de Complementos
function EtapaComplementos({
  receitaId,
  complementosSelecionados,
  onComplementosChange,
}: {
  receitaId: number
  complementosSelecionados: number[]
  onComplementosChange: (ids: number[]) => void
}) {
  const [complementos, setComplementos] = useState<ComplementoResponse[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  // Buscar complementos da empresa
  useEffect(() => {
    const buscar = async () => {
      setLoading(true)
      try {
        const resultado = await buscarComplementosEmpresa(empresaId, search)
        if (resultado.success && resultado.data) {
          setComplementos(resultado.data)
        }
      } finally {
        setLoading(false)
      }
    }
    buscar()
  }, [empresaId, search])

  return (
    <div className="space-y-4">
      <Input
        placeholder="Buscar complementos..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {loading ? (
        <div>Carregando...</div>
      ) : (
        <div className="space-y-4">
          {complementos.map((complemento) => (
            <div key={complemento.id} className="border rounded p-4">
              <div className="flex items-center gap-2">
                <Checkbox
                  checked={complementosSelecionados.includes(complemento.id)}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      onComplementosChange([...complementosSelecionados, complemento.id])
                    } else {
                      onComplementosChange(
                        complementosSelecionados.filter((id) => id !== complemento.id)
                      )
                    }
                  }}
                />
                <div>
                  <h4 className="font-semibold">{complemento.nome}</h4>
                  {complemento.descricao && (
                    <p className="text-sm text-gray-600">{complemento.descricao}</p>
                  )}
                </div>
              </div>

              {/* Mostrar adicionais dentro do complemento */}
              {complemento.adicionais && complemento.adicionais.length > 0 && (
                <div className="mt-2 ml-6 space-y-1">
                  {complemento.adicionais.map((adicional) => (
                    <div key={adicional.id} className="text-sm text-gray-500">
                      • {adicional.nome} (+R$ {adicional.preco.toFixed(2)})
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

---

## 🍔 Migração de Combos

### Situação Atual (ANTES)

Combos atualmente **não têm** complementos ou adicionais. Apenas produtos (itens).

### Nova Situação (AGORA)

Combos podem ter **complementos** diretamente vinculados (igual produtos e receitas).

### Passo a Passo da Migração

#### 1. Adicionar Etapa de Complementos no Modal

**Arquivo:** `src/app/(dashboard)/cadastros/combos/_components/combo-modal.tsx`

Adicionar uma nova etapa após a etapa de itens:

```typescript
// Estados
const [currentStep, setCurrentStep] = useState(1) // 1: Info, 2: Itens, 3: Complementos
const [complementosSelecionados, setComplementosSelecionados] = useState<number[]>([])

// Etapa 3: Complementos
function EtapaComplementos() {
  // Similar ao componente de receitas acima
}
```

#### 2. Atualizar Action de Criação

**Arquivo:** `src/actions/combos/criar-combo.ts`

**ANTES:**
```typescript
export type CriarComboRequest = {
  empresa_id: number
  titulo: string
  descricao: string
  preco_total: number
  ativo?: boolean
  itens: ComboItem[]
  imagem?: File | null
}
```

**AGORA:**
```typescript
export type CriarComboRequest = {
  empresa_id: number
  titulo: string
  descricao: string
  preco_total: number
  ativo?: boolean
  itens: ComboItem[]
  complemento_ids?: number[] // NOVO
  imagem?: File | null
}
```

E no envio:

```typescript
if (data.complemento_ids && data.complemento_ids.length > 0) {
  formData.append('complemento_ids', JSON.stringify(data.complemento_ids))
}
```

#### 3. Criar Action para Vincular Complementos

**Arquivo:** `src/actions/combos/complementos/vincular-complementos-combo.ts`

```typescript
import { cookies } from 'next/headers'
import { revalidatePath } from 'next/cache'

export type VincularComplementosComboRequest = {
  combo_id: number
  complemento_ids: number[]
}

export type VincularComplementosComboResult = {
  success: boolean
  data?: any
  error?: string
}

export async function vincularComplementosCombo(
  data: VincularComplementosComboRequest
): Promise<VincularComplementosComboResult> {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')?.value

  if (!token) {
    return { success: false, error: 'Não autenticado' }
  }

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/catalogo/admin/complementos/vincular-combo`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          combo_id: data.combo_id,
          complemento_ids: data.complemento_ids,
        }),
      }
    )

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      return {
        success: false,
        error: error.detail || 'Erro ao vincular complementos',
      }
    }

    const resultado = await response.json()
    revalidatePath('/cadastros')
    revalidatePath('/cadastros?tab=combos')
    return { success: true, data: resultado }
  } catch (error) {
    console.error('Erro ao vincular complementos:', error)
    return { success: false, error: 'Erro ao vincular complementos' }
  }
}
```

#### 4. Fluxo de Criação Atualizado

```
Etapa 1: Informações Básicas
  ↓
Etapa 2: Itens (Produtos)
  ↓
Etapa 3: Complementos (NOVO)
  ↓
Finalizar: Criar combo com itens e complementos
```

---

## 📡 Novos Endpoints

### Client (Frontend)

#### Buscar Complementos de Receita

```
GET /api/catalogo/client/complementos/receita/{receita_id}?apenas_ativos=true

Headers:
  X-Super-Token: {token_do_cliente}

Response: ComplementoResponse[]
```

#### Buscar Complementos de Combo

```
GET /api/catalogo/client/complementos/combo/{combo_id}?apenas_ativos=true

Headers:
  X-Super-Token: {token_do_cliente}

Response: ComplementoResponse[]
```

### Admin (Backend - A Implementar)

#### Vincular Complementos a Receita

```
POST /api/catalogo/admin/complementos/vincular-receita

Headers:
  Authorization: Bearer {token}
  Content-Type: application/json

Body:
{
  "receita_id": 1,
  "complemento_ids": [1, 2, 3]
}
```

#### Vincular Complementos a Combo

```
POST /api/catalogo/admin/complementos/vincular-combo

Headers:
  Authorization: Bearer {token}
  Content-Type: application/json

Body:
{
  "combo_id": 1,
  "complemento_ids": [1, 2, 3]
}
```

---

## 📦 Estrutura de Dados

### ComplementoResponse

```typescript
interface ComplementoResponse {
  id: number
  empresa_id: number
  nome: string
  descricao?: string | null
  obrigatorio: boolean
  quantitativo: boolean
  permite_multipla_escolha: boolean
  minimo_itens?: number | null
  maximo_itens?: number | null
  ordem: number
  ativo: boolean
  adicionais: AdicionalComplementoResponse[]
  created_at: string
  updated_at: string
}

interface AdicionalComplementoResponse {
  id: number // usado como adicional_id nos pedidos
  nome: string
  descricao?: string | null
  preco: number
  custo: number
  ativo: boolean
  ordem: number
  created_at: string
  updated_at: string
}
```

### Tipos Atualizados

#### Receita (para exibição)

```typescript
export type Receita = {
  id: number
  empresa_id: number
  nome: string
  descricao?: string | null
  preco_venda: number | string
  custo_total?: number
  imagem?: string | null
  ativo: boolean
  disponivel: boolean
  // NOVO: Complementos vinculados
  complementos?: ComplementoResponse[]
  created_at: string
  updated_at: string
}
```

#### Combo (para exibição)

```typescript
export type ComboDTO = {
  id: number
  empresa_id: number
  titulo: string
  descricao: string
  preco_total: number
  custo_total?: number | null
  ativo: boolean
  imagem?: string | null
  itens: ComboItem[]
  // NOVO: Complementos vinculados
  complementos?: ComplementoResponse[]
  created_at: string
  updated_at: string
}
```

---

## 💻 Exemplos de Código

### Exemplo 1: Buscar Complementos de Receita

```typescript
// src/actions/receitas/complementos/buscar-complementos-receita.ts
import { cookies } from 'next/headers'
import { ComplementoResponse } from '@/types/complemento'

export async function buscarComplementosReceita(
  receitaId: number,
  apenasAtivos: boolean = true
): Promise<{ success: boolean; data?: ComplementoResponse[]; error?: string }> {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')?.value

  if (!token) {
    return { success: false, error: 'Não autenticado' }
  }

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/catalogo/client/complementos/receita/${receitaId}?apenas_ativos=${apenasAtivos}`,
      {
        method: 'GET',
        headers: {
          'X-Super-Token': token,
        },
      }
    )

    if (!response.ok) {
      return { success: false, error: 'Erro ao buscar complementos' }
    }

    const complementos: ComplementoResponse[] = await response.json()
    return { success: true, data: complementos }
  } catch (error) {
    console.error('Erro ao buscar complementos:', error)
    return { success: false, error: 'Erro ao buscar complementos' }
  }
}
```

### Exemplo 2: Componente de Seleção de Complementos

```typescript
// src/components/complementos/selecao-complementos.tsx
'use client'

import { useState, useEffect } from 'react'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { ComplementoResponse } from '@/types/complemento'
import { buscarComplementosEmpresa } from '@/actions/complementos/buscar-complementos-empresa'

interface SelecaoComplementosProps {
  empresaId: number
  complementosSelecionados: number[]
  onComplementosChange: (ids: number[]) => void
}

export function SelecaoComplementos({
  empresaId,
  complementosSelecionados,
  onComplementosChange,
}: SelecaoComplementosProps) {
  const [complementos, setComplementos] = useState<ComplementoResponse[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const buscar = async () => {
      setLoading(true)
      try {
        const resultado = await buscarComplementosEmpresa(empresaId, search)
        if (resultado.success && resultado.data) {
          setComplementos(resultado.data)
        }
      } finally {
        setLoading(false)
      }
    }

    const timeoutId = setTimeout(buscar, 300) // Debounce
    return () => clearTimeout(timeoutId)
  }, [empresaId, search])

  const toggleComplemento = (complementoId: number) => {
    if (complementosSelecionados.includes(complementoId)) {
      onComplementosChange(
        complementosSelecionados.filter((id) => id !== complementoId)
      )
    } else {
      onComplementosChange([...complementosSelecionados, complementoId])
    }
  }

  return (
    <div className="space-y-4">
      <Input
        placeholder="Buscar complementos..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {loading ? (
        <div className="text-center py-4">Carregando...</div>
      ) : complementos.length === 0 ? (
        <div className="text-center py-4 text-gray-500">
          Nenhum complemento encontrado
        </div>
      ) : (
        <div className="space-y-3">
          {complementos.map((complemento) => (
            <div
              key={complemento.id}
              className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-start gap-3">
                <Checkbox
                  checked={complementosSelecionados.includes(complemento.id)}
                  onCheckedChange={() => toggleComplemento(complemento.id)}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold">{complemento.nome}</h4>
                    {complemento.obrigatorio && (
                      <span className="text-xs text-red-500">*Obrigatório</span>
                    )}
                  </div>
                  {complemento.descricao && (
                    <p className="text-sm text-gray-600 mt-1">
                      {complemento.descricao}
                    </p>
                  )}

                  {/* Adicionais dentro do complemento */}
                  {complemento.adicionais && complemento.adicionais.length > 0 && (
                    <div className="mt-3 ml-6 space-y-1">
                      <p className="text-xs font-medium text-gray-500 mb-1">
                        Adicionais disponíveis:
                      </p>
                      {complemento.adicionais.map((adicional) => (
                        <div
                          key={adicional.id}
                          className="text-sm text-gray-600 flex items-center gap-2"
                        >
                          <span>•</span>
                          <span>{adicional.nome}</span>
                          {adicional.preco > 0 && (
                            <span className="text-green-600 font-medium">
                              +R$ {adicional.preco.toFixed(2)}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

### Exemplo 3: Atualizar Modal de Receitas

```typescript
// src/app/(dashboard)/cadastros/receitas/_components/modal/criar-receita-modal.tsx
// ... código existente ...

// Substituir estado de adicionais por complementos
const [complementosSelecionados, setComplementosSelecionados] = useState<number[]>([])

// Atualizar handleFinalizar
const handleFinalizar = async () => {
  if (!receitaId) {
    toast.error('Erro: Receita não encontrada')
    return
  }

  setLoading(true)
  try {
    // Vincular ingredientes (mantém igual)
    if (ingredientesSelecionados.length > 0) {
      await Promise.all(
        ingredientesSelecionados.map((ing) =>
          vincularIngrediente({
            receita_id: receitaId,
            ingrediente_id: ing.ingrediente_id,
            quantidade: ing.quantidade,
          })
        )
      )
    }

    // NOVO: Vincular complementos (substitui adicionais)
    if (complementosSelecionados.length > 0) {
      const resultado = await vincularComplementosReceita({
        receita_id: receitaId,
        complemento_ids: complementosSelecionados,
      })

      if (!resultado.success) {
        throw new Error(resultado.error || 'Erro ao vincular complementos')
      }
    }

    toast.success('Receita criada com sucesso! 🎉')
    reset()
    setCurrentStep(1)
    setReceitaId(null)
    setIngredientesSelecionados([])
    setComplementosSelecionados([]) // NOVO
    onOpenChange(false)
    onSucesso()
  } catch (error: unknown) {
    toast.error(error instanceof Error ? error.message : 'Erro ao finalizar receita')
  } finally {
    setLoading(false)
  }
}

// Atualizar Etapa 3
{currentStep === 3 && (
  <div className="space-y-4">
    <h3 className="text-lg font-semibold">Etapa 3: Complementos</h3>
    <p className="text-sm text-gray-600">
      Selecione os complementos que estarão disponíveis para esta receita.
      Cada complemento contém adicionais que podem ser selecionados pelos clientes.
    </p>
    
    <SelecaoComplementos
      empresaId={empresaId}
      complementosSelecionados={complementosSelecionados}
      onComplementosChange={setComplementosSelecionados}
    />
  </div>
)}
```

---

## ✅ Checklist de Migração

### Receitas

- [ ] Remover código de adicionais diretos da Etapa 3
- [ ] Criar action `vincularComplementosReceita`
- [ ] Criar action `buscarComplementosReceita` (se necessário)
- [ ] Atualizar estado: `adicionaisSelecionados` → `complementosSelecionados`
- [ ] Atualizar `handleFinalizar` para vincular complementos
- [ ] Criar/atualizar componente de seleção de complementos
- [ ] Atualizar interface da Etapa 3
- [ ] Testar criação de receita com complementos
- [ ] Testar exibição de receitas com complementos
- [ ] Atualizar tipos TypeScript

### Combos

- [ ] Adicionar etapa de complementos no modal
- [ ] Criar action `vincularComplementosCombo`
- [ ] Criar action `buscarComplementosCombo` (se necessário)
- [ ] Atualizar `CriarComboRequest` para incluir `complemento_ids`
- [ ] Atualizar `ComboDTO` para incluir `complementos`
- [ ] Adicionar estado `complementosSelecionados`
- [ ] Integrar componente de seleção de complementos
- [ ] Testar criação de combo com complementos
- [ ] Testar exibição de combos com complementos
- [ ] Atualizar tipos TypeScript

### Geral

- [ ] Criar tipos para `ComplementoResponse` e `AdicionalComplementoResponse`
- [ ] Criar componente reutilizável `SelecaoComplementos`
- [ ] Atualizar documentação de tipos
- [ ] Testar integração completa
- [ ] Remover código legado de adicionais diretos (quando seguro)

---

## 🚨 Pontos de Atenção

### 1. Compatibilidade com Dados Existentes

- Receitas antigas podem ter adicionais diretos (via `receita_adicional`)
- O backend ainda suporta isso, mas **não deve ser usado** para novas receitas
- Considere migrar dados existentes no futuro

### 2. Validações

- Complementos devem pertencer à mesma empresa da receita/combo
- Validar se complementos existem antes de vincular
- Não permitir duplicatas

### 3. Performance

- Usar debounce na busca de complementos (300ms recomendado)
- Carregar complementos apenas quando necessário
- Considerar paginação se houver muitos complementos

### 4. UX

- Mostrar claramente a hierarquia: Complemento → Adicionais
- Indicar complementos obrigatórios
- Mostrar preços dos adicionais dentro dos complementos
- Permitir busca/filtro de complementos

---

## 📚 Referências

- [Guia de Migração Frontend: Sistema de Complementos](./MIGRACAO_FRONTEND_COMPLEMENTOS.md)
- [Documentação: Criação de Receitas](./DOC_CRIACAO_RECEITAS.md) (atualizar)
- [Documentação: Criação de Combos](./DOC_CRIACAO_COMBOS.md) (atualizar)

---

**Última atualização:** Dezembro 2024  
**Versão:** 1.0

