# Documentação: Acerto de Motoboys - Guia para Frontend

## 📋 Visão Geral

O sistema de acerto de motoboys permite gerenciar o fechamento financeiro de entregas realizadas por entregadores. O sistema calcula automaticamente os valores devidos considerando:
- **Valor dos pedidos**: Soma do valor total dos pedidos entregues
- **Valor da diária**: Valor fixo configurado por entregador (campo `valor_diaria`)
- **Valor líquido**: Soma do valor dos pedidos + diária

## 🔐 Autenticação

Todos os endpoints de acerto de motoboys requerem autenticação de administrador. O token deve ser enviado no header:
```
Authorization: Bearer {token}
```

## 📍 Base URL

Todos os endpoints estão sob o prefixo:
```
/api/financeiro/admin/acertos-entregadores
```

## 🎯 Endpoints Disponíveis

### 1. Listar Pedidos Pendentes de Acerto

**GET** `/api/financeiro/admin/acertos-entregadores/pendentes`

Lista todos os pedidos entregues que ainda não foram acertados no período informado.

#### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | `int` | ✅ Sim | ID da empresa (deve ser > 0) |
| `inicio` | `string` | ✅ Sim | Data/hora inicial do período. Aceita:<br>- `YYYY-MM-DD` (ex: `2024-01-15`)<br>- ISO datetime (ex: `2024-01-15T00:00:00`) |
| `fim` | `string` | ✅ Sim | Data/hora final do período. Aceita:<br>- `YYYY-MM-DD` (ex: `2024-01-15`)<br>- ISO datetime (ex: `2024-01-15T23:59:59`) |
| `entregador_id` | `int` | ❌ Não | ID do entregador para filtrar (opcional, deve ser > 0 se informado) |

#### Exemplo de Requisição

```http
GET /api/financeiro/admin/acertos-entregadores/pendentes?empresa_id=1&inicio=2024-01-01&fim=2024-01-31&entregador_id=5
```

#### Resposta (200 OK)

```json
[
  {
    "id": 123,
    "entregador_id": 5,
    "valor_total": 45.50,
    "data_criacao": "2024-01-15T14:30:00",
    "cliente_id": 10,
    "status": "E"
  },
  {
    "id": 124,
    "entregador_id": 5,
    "valor_total": 32.00,
    "data_criacao": "2024-01-15T16:45:00",
    "cliente_id": 11,
    "status": "E"
  }
]
```

#### Schema de Resposta

```typescript
interface PedidoPendenteAcertoOut {
  id: number;
  entregador_id: number | null;
  valor_total: number | null;
  data_criacao: string; // ISO datetime
  cliente_id: number | null;
  status: string; // Sempre "E" (Entregue) para pedidos pendentes
}
```

---

### 2. Preview do Acerto

**GET** `/api/financeiro/admin/acertos-entregadores/preview`

Retorna um resumo prévio do acerto antes de fechar, agrupado por entregador e por dia. Útil para mostrar ao usuário o que será acertado.

#### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | `int` | ✅ Sim | ID da empresa (deve ser > 0) |
| `inicio` | `string` | ✅ Sim | Data/hora inicial (formato: `YYYY-MM-DD` ou ISO datetime) |
| `fim` | `string` | ✅ Sim | Data/hora final (formato: `YYYY-MM-DD` ou ISO datetime) |
| `entregador_id` | `int` | ❌ Não | ID do entregador para filtrar (opcional) |

#### Exemplo de Requisição

```http
GET /api/financeiro/admin/acertos-entregadores/preview?empresa_id=1&inicio=2024-01-01&fim=2024-01-31
```

#### Resposta (200 OK)

```json
{
  "empresa_id": 1,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "entregador_id": null,
  "resumos": [
    {
      "data": "2024-01-15",
      "entregador_id": 5,
      "entregador_nome": "João Silva",
      "valor_diaria": 50.00,
      "qtd_pedidos": 8,
      "valor_pedidos": 320.50,
      "valor_liquido": 370.50
    },
    {
      "data": "2024-01-16",
      "entregador_id": 5,
      "entregador_nome": "João Silva",
      "valor_diaria": 50.00,
      "qtd_pedidos": 5,
      "valor_pedidos": 180.00,
      "valor_liquido": 230.00
    },
    {
      "data": "2024-01-15",
      "entregador_id": 7,
      "entregador_nome": "Maria Santos",
      "valor_diaria": 60.00,
      "qtd_pedidos": 10,
      "valor_pedidos": 450.00,
      "valor_liquido": 510.00
    }
  ],
  "total_pedidos": 23,
  "total_bruto": 950.50,
  "total_diarias": 160.00,
  "total_liquido": 1110.50
}
```

#### Schema de Resposta

```typescript
interface ResumoAcertoEntregador {
  data: string; // YYYY-MM-DD
  entregador_id: number;
  entregador_nome: string | null;
  valor_diaria: number | null;
  qtd_pedidos: number;
  valor_pedidos: number;
  valor_liquido: number; // valor_pedidos + valor_diaria
}

interface PreviewAcertoResponse {
  empresa_id: number;
  inicio: string; // ISO datetime
  fim: string; // ISO datetime
  entregador_id: number | null;
  resumos: ResumoAcertoEntregador[];
  total_pedidos: number;
  total_bruto: number; // Soma de todos os valores dos pedidos
  total_diarias: number; // Soma de todas as diárias
  total_liquido: number; // total_bruto + total_diarias
}
```

---

### 3. Fechar Pedidos (Realizar Acerto)

**POST** `/api/financeiro/admin/acertos-entregadores/fechar`

Marca os pedidos como acertados no período informado. Esta operação é **irreversível** e atualiza o campo `acertado_entregador = true` nos pedidos.

#### Request Body

```json
{
  "empresa_id": 1,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "entregador_id": 5, // Opcional: null para acertar todos os entregadores
  "fechado_por": "Nome do Usuário" // Opcional: quem fechou o acerto
}
```

#### Schema de Request

```typescript
interface FecharPedidosDiretoRequest {
  empresa_id: number; // > 0
  inicio: string; // ISO datetime
  fim: string; // ISO datetime
  entregador_id?: number | null; // Opcional, > 0 se informado
  fechado_por?: string | null; // Opcional
}
```

#### Exemplo de Requisição

```http
POST /api/financeiro/admin/acertos-entregadores/fechar
Content-Type: application/json

{
  "empresa_id": 1,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "entregador_id": null,
  "fechado_por": "Admin Sistema"
}
```

#### Resposta (200 OK)

```json
{
  "pedidos_fechados": 23,
  "pedido_ids": [123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145],
  "valor_total": 950.50,
  "valor_diaria_total": 160.00,
  "valor_liquido": 1110.50,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "mensagem": "Pedidos marcados como acertados por Admin Sistema"
}
```

#### Schema de Resposta

```typescript
interface FecharPedidosDiretoResponse {
  pedidos_fechados: number;
  pedido_ids: number[];
  valor_total: number | null; // Soma dos valores dos pedidos
  valor_diaria_total: number | null; // Soma das diárias
  valor_liquido: number | null; // valor_total + valor_diaria_total
  inicio: string; // ISO datetime
  fim: string; // ISO datetime
  mensagem: string | null;
}
```

#### Casos Especiais

- Se não houver pedidos para acertar no período, a resposta será:
```json
{
  "pedidos_fechados": 0,
  "pedido_ids": [],
  "valor_total": 0,
  "valor_diaria_total": 0,
  "valor_liquido": 0,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "mensagem": "Nenhum pedido encontrado para o período."
}
```

---

### 4. Consultar Acertos Passados

**GET** `/api/financeiro/admin/acertos-entregadores/passados`

Lista os acertos já realizados (pedidos já marcados como acertados) no período informado. Útil para histórico e relatórios.

#### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | `int` | ✅ Sim | ID da empresa (deve ser > 0) |
| `inicio` | `string` | ✅ Sim | Data/hora inicial (formato: `YYYY-MM-DD` ou ISO datetime) |
| `fim` | `string` | ✅ Sim | Data/hora final (formato: `YYYY-MM-DD` ou ISO datetime) |
| `entregador_id` | `int` | ❌ Não | ID do entregador para filtrar (opcional) |

#### Exemplo de Requisição

```http
GET /api/financeiro/admin/acertos-entregadores/passados?empresa_id=1&inicio=2024-01-01&fim=2024-01-31
```

#### Resposta (200 OK)

A estrutura da resposta é idêntica ao endpoint `/preview`, mas retorna apenas pedidos já acertados:

```json
{
  "empresa_id": 1,
  "inicio": "2024-01-01T00:00:00",
  "fim": "2024-01-31T23:59:59",
  "entregador_id": null,
  "resumos": [
    {
      "data": "2024-01-10",
      "entregador_id": 5,
      "entregador_nome": "João Silva",
      "valor_diaria": 50.00,
      "qtd_pedidos": 6,
      "valor_pedidos": 240.00,
      "valor_liquido": 290.00
    }
  ],
  "total_pedidos": 6,
  "total_bruto": 240.00,
  "total_diarias": 50.00,
  "total_liquido": 290.00
}
```

#### Schema de Resposta

```typescript
// Mesma estrutura de PreviewAcertoResponse
interface AcertosPassadosResponse {
  empresa_id: number;
  inicio: string;
  fim: string;
  entregador_id: number | null;
  resumos: ResumoAcertoEntregador[];
  total_pedidos: number;
  total_bruto: number;
  total_diarias: number;
  total_liquido: number;
}
```

---

## 📦 Endpoint Auxiliar: Listar Entregadores

Para obter a lista de entregadores disponíveis (necessário para filtros e exibição de nomes):

**GET** `/api/cadastros/admin/entregadores`

#### Resposta

```json
[
  {
    "id": 5,
    "nome": "João Silva",
    "telefone": "11999999999",
    "documento": "12345678900",
    "veiculo_tipo": "moto",
    "placa": "ABC1234",
    "acrescimo_taxa": 0.0,
    "valor_diaria": 50.00,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "empresas": []
  }
]
```

#### Schema

```typescript
interface EntregadorOut {
  id: number;
  nome: string;
  telefone: string | null;
  documento: string | null;
  veiculo_tipo: string | null;
  placa: string | null;
  acrescimo_taxa: number | null;
  valor_diaria: number | null; // Valor da diária do entregador
  created_at: string;
  updated_at: string;
  empresas: Array<{ id: number; nome: string }>;
}
```

---

## 🔍 Regras de Negócio Importantes

### 1. Filtros de Pedidos

Os endpoints de pendentes, preview e fechar consideram apenas pedidos que atendem **TODAS** as condições:
- `empresa_id` = empresa informada
- `tipo_entrega` = "DELIVERY"
- `entregador_id` IS NOT NULL
- `status` = "E" (Entregue)
- `acertado_entregador` = `false` (para pendentes/preview/fechar) ou `true` (para passados)
- `created_at` dentro do período informado

### 2. Normalização de Período

- Se a data `fim` for informada apenas como `YYYY-MM-DD` (sem horário), o sistema considera o dia inteiro (até 23:59:59.999999).
- Se for informada como datetime completo, usa o horário exato.
- O sistema usa limite superior **exclusivo** para evitar problemas de microsegundos.

### 3. Cálculo de Valores

- **Valor dos Pedidos**: Soma do campo `valor_total` de todos os pedidos no período
- **Valor da Diária**: Cada entregador pode ter um `valor_diaria` configurado. Se não tiver, considera 0.
- **Valor Líquido**: `valor_pedidos + valor_diaria`
- **Total Diárias**: Se `entregador_id` for informado, usa a diária desse entregador. Caso contrário, soma as diárias de todos os entregadores distintos que têm pedidos no período.

### 4. Agrupamento no Preview/Passados

Os resumos são agrupados por:
- **Entregador** (`entregador_id`)
- **Dia** (data de criação do pedido)

Cada combinação (entregador + dia) gera um item no array `resumos`.

### 5. Operação de Fechamento

- A operação de fechar é **irreversível** (não há endpoint para desfazer)
- Ao fechar, os pedidos são marcados com:
  - `acertado_entregador = true`
  - `acertado_entregador_em = now()`
  - `data_atualizacao = now()`

---

## 💡 Sugestões de Implementação no Frontend

### 1. Fluxo de Acerto

1. **Tela de Seleção de Período**
   - Campos: Data inicial, Data final, Entregador (opcional)
   - Botão: "Visualizar Acerto"

2. **Tela de Preview**
   - Chamar `/preview` com os parâmetros selecionados
   - Exibir:
     - Tabela com resumos por entregador/dia
     - Totais gerais (pedidos, bruto, diárias, líquido)
   - Botões: "Voltar", "Confirmar Acerto"

3. **Confirmação**
   - Modal de confirmação mostrando resumo
   - Campo opcional: "Fechado por" (nome do usuário)
   - Botões: "Cancelar", "Confirmar"

4. **Fechamento**
   - Chamar `/fechar` com os dados
   - Exibir mensagem de sucesso com os totais
   - Redirecionar ou atualizar a lista

### 2. Tela de Histórico

- Usar endpoint `/passados` para listar acertos já realizados
- Mesma estrutura de exibição do preview, mas apenas leitura

### 3. Tela de Pedidos Pendentes

- Usar endpoint `/pendentes` para listar pedidos individuais
- Útil para ver detalhes antes de acertar
- Pode incluir filtros adicionais (cliente, valor mínimo/máximo, etc.)

### 4. Validações no Frontend

- Validar que `empresa_id` > 0
- Validar que `inicio` <= `fim`
- Validar formato de datas
- Mostrar loading durante requisições
- Tratar erros de rede/API

### 5. Formatação de Valores

- Sempre exibir valores monetários com 2 casas decimais
- Usar separador de milhares (ex: R$ 1.110,50)
- Formatar datas no padrão brasileiro (DD/MM/YYYY)

---

## ⚠️ Tratamento de Erros

### Erros Comuns

1. **401 Unauthorized**: Token inválido ou expirado
2. **422 Unprocessable Entity**: Dados inválidos (validação de schema)
3. **404 Not Found**: Empresa ou entregador não encontrado
4. **500 Internal Server Error**: Erro no servidor

### Exemplo de Resposta de Erro

```json
{
  "detail": "Validation error: empresa_id must be greater than 0"
}
```

---

## 📝 Exemplo Completo de Integração (TypeScript/React)

```typescript
// types.ts
interface PedidoPendenteAcertoOut {
  id: number;
  entregador_id: number | null;
  valor_total: number | null;
  data_criacao: string;
  cliente_id: number | null;
  status: string;
}

interface ResumoAcertoEntregador {
  data: string;
  entregador_id: number;
  entregador_nome: string | null;
  valor_diaria: number | null;
  qtd_pedidos: number;
  valor_pedidos: number;
  valor_liquido: number;
}

interface PreviewAcertoResponse {
  empresa_id: number;
  inicio: string;
  fim: string;
  entregador_id: number | null;
  resumos: ResumoAcertoEntregador[];
  total_pedidos: number;
  total_bruto: number;
  total_diarias: number;
  total_liquido: number;
}

interface FecharPedidosDiretoRequest {
  empresa_id: number;
  inicio: string;
  fim: string;
  entregador_id?: number | null;
  fechado_por?: string | null;
}

interface FecharPedidosDiretoResponse {
  pedidos_fechados: number;
  pedido_ids: number[];
  valor_total: number | null;
  valor_diaria_total: number | null;
  valor_liquido: number | null;
  inicio: string;
  fim: string;
  mensagem: string | null;
}

// api.ts
const API_BASE = '/api/financeiro/admin/acertos-entregadores';

export const acertoMotoboysAPI = {
  async listarPendentes(
    empresaId: number,
    inicio: string,
    fim: string,
    entregadorId?: number | null
  ): Promise<PedidoPendenteAcertoOut[]> {
    const params = new URLSearchParams({
      empresa_id: empresaId.toString(),
      inicio,
      fim,
    });
    if (entregadorId) {
      params.append('entregador_id', entregadorId.toString());
    }
    const response = await fetch(`${API_BASE}/pendentes?${params}`, {
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
    });
    if (!response.ok) throw new Error('Erro ao listar pendentes');
    return response.json();
  },

  async preview(
    empresaId: number,
    inicio: string,
    fim: string,
    entregadorId?: number | null
  ): Promise<PreviewAcertoResponse> {
    const params = new URLSearchParams({
      empresa_id: empresaId.toString(),
      inicio,
      fim,
    });
    if (entregadorId) {
      params.append('entregador_id', entregadorId.toString());
    }
    const response = await fetch(`${API_BASE}/preview?${params}`, {
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
    });
    if (!response.ok) throw new Error('Erro ao obter preview');
    return response.json();
  },

  async fechar(
    data: FecharPedidosDiretoRequest
  ): Promise<FecharPedidosDiretoResponse> {
    const response = await fetch(`${API_BASE}/fechar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`,
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Erro ao fechar acerto');
    return response.json();
  },

  async acertosPassados(
    empresaId: number,
    inicio: string,
    fim: string,
    entregadorId?: number | null
  ): Promise<PreviewAcertoResponse> {
    const params = new URLSearchParams({
      empresa_id: empresaId.toString(),
      inicio,
      fim,
    });
    if (entregadorId) {
      params.append('entregador_id', entregadorId.toString());
    }
    const response = await fetch(`${API_BASE}/passados?${params}`, {
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
    });
    if (!response.ok) throw new Error('Erro ao listar acertos passados');
    return response.json();
  },
};
```

---

## 🎨 Exemplo de Componente React

```tsx
import { useState } from 'react';
import { acertoMotoboysAPI } from './api';

function AcertoMotoboys() {
  const [empresaId] = useState(1);
  const [inicio, setInicio] = useState('');
  const [fim, setFim] = useState('');
  const [entregadorId, setEntregadorId] = useState<number | null>(null);
  const [preview, setPreview] = useState<PreviewAcertoResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePreview = async () => {
    if (!inicio || !fim) {
      alert('Preencha as datas');
      return;
    }
    setLoading(true);
    try {
      const data = await acertoMotoboysAPI.preview(
        empresaId,
        inicio,
        fim,
        entregadorId
      );
      setPreview(data);
    } catch (error) {
      alert('Erro ao obter preview');
    } finally {
      setLoading(false);
    }
  };

  const handleFechar = async () => {
    if (!preview) return;
    if (!confirm('Deseja realmente fechar este acerto?')) return;

    setLoading(true);
    try {
      const response = await acertoMotoboysAPI.fechar({
        empresa_id: empresaId,
        inicio: preview.inicio,
        fim: preview.fim,
        entregador_id: entregadorId,
        fechado_por: 'Usuário Logado',
      });
      alert(`Acerto fechado! ${response.pedidos_fechados} pedidos.`);
      setPreview(null);
    } catch (error) {
      alert('Erro ao fechar acerto');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Acerto de Motoboys</h1>
      
      <div>
        <label>Data Inicial:</label>
        <input
          type="date"
          value={inicio}
          onChange={(e) => setInicio(e.target.value)}
        />
      </div>
      
      <div>
        <label>Data Final:</label>
        <input
          type="date"
          value={fim}
          onChange={(e) => setFim(e.target.value)}
        />
      </div>
      
      <div>
        <label>Entregador (opcional):</label>
        <input
          type="number"
          value={entregadorId || ''}
          onChange={(e) => setEntregadorId(e.target.value ? Number(e.target.value) : null)}
          placeholder="ID do entregador"
        />
      </div>
      
      <button onClick={handlePreview} disabled={loading}>
        Visualizar Acerto
      </button>

      {preview && (
        <div>
          <h2>Preview do Acerto</h2>
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Entregador</th>
                <th>Pedidos</th>
                <th>Valor Pedidos</th>
                <th>Diária</th>
                <th>Valor Líquido</th>
              </tr>
            </thead>
            <tbody>
              {preview.resumos.map((resumo, idx) => (
                <tr key={idx}>
                  <td>{resumo.data}</td>
                  <td>{resumo.entregador_nome || `ID: ${resumo.entregador_id}`}</td>
                  <td>{resumo.qtd_pedidos}</td>
                  <td>R$ {resumo.valor_pedidos.toFixed(2)}</td>
                  <td>R$ {resumo.valor_diaria?.toFixed(2) || '0.00'}</td>
                  <td>R$ {resumo.valor_liquido.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          
          <div>
            <p><strong>Total Pedidos:</strong> {preview.total_pedidos}</p>
            <p><strong>Total Bruto:</strong> R$ {preview.total_bruto.toFixed(2)}</p>
            <p><strong>Total Diárias:</strong> R$ {preview.total_diarias.toFixed(2)}</p>
            <p><strong>Total Líquido:</strong> R$ {preview.total_liquido.toFixed(2)}</p>
          </div>
          
          <button onClick={handleFechar} disabled={loading}>
            Confirmar e Fechar Acerto
          </button>
        </div>
      )}
    </div>
  );
}
```

---

## 📚 Resumo dos Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/pendentes` | Lista pedidos pendentes de acerto |
| GET | `/preview` | Preview do acerto (resumo agrupado) |
| POST | `/fechar` | Fecha/acerta os pedidos |
| GET | `/passados` | Lista acertos já realizados |
| GET | `/api/cadastros/admin/entregadores` | Lista entregadores disponíveis |

---

## ✅ Checklist de Implementação

- [ ] Integrar autenticação (token no header)
- [ ] Criar tela de seleção de período e entregador
- [ ] Implementar chamada ao endpoint `/preview`
- [ ] Exibir resumo do acerto em tabela
- [ ] Implementar confirmação antes de fechar
- [ ] Implementar chamada ao endpoint `/fechar`
- [ ] Tratar erros e exibir mensagens adequadas
- [ ] Implementar tela de histórico usando `/passados`
- [ ] Implementar listagem de pedidos pendentes usando `/pendentes`
- [ ] Formatar valores monetários corretamente
- [ ] Validar dados antes de enviar requisições
- [ ] Adicionar loading states
- [ ] Testar com diferentes cenários (com/sem entregador, períodos vazios, etc.)

---

**Última atualização**: Janeiro 2024

