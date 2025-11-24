# Documentação API - Fechar Pedido de Balcão

## Visão Geral

Esta documentação descreve como implementar a funcionalidade de fechar pedidos de balcão no frontend. O fechamento de um pedido altera seu status para `ENTREGUE` e pode incluir informações opcionais de pagamento.

## Endpoints Disponíveis

Existem dois endpoints que realizam a mesma operação (fechar pedido):

### 1. Endpoint Principal: `/fechar-conta`
**Recomendado para uso**

### 2. Endpoint Alternativo: `/fechar`
**Atalho que chama o mesmo método**

---

## Endpoint: Fechar Conta do Pedido

### **POST** `/api/balcao/admin/pedidos/{pedido_id}/fechar-conta`

Fecha a conta de um pedido de balcão, alterando seu status para `ENTREGUE`.

#### Autenticação
- **Requerida**: Sim
- **Tipo**: Bearer Token (JWT)
- O usuário deve estar autenticado como admin

#### Parâmetros de URL

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `pedido_id` | `integer` | Sim | ID do pedido a ser fechado (deve ser > 0) |

#### Body (Request)

O body é **opcional**. Se não enviar nada, o pedido será fechado sem informações de pagamento.

```json
{
  "meio_pagamento_id": 1,      // Opcional: ID do meio de pagamento utilizado
  "troco_para": 50.00          // Opcional: Valor para o qual deseja troco (apenas para pagamento em dinheiro)
}
```

**Schema do Request:**
```typescript
interface FecharContaBalcaoRequest {
  meio_pagamento_id?: number;  // ID do meio de pagamento
  troco_para?: number;         // Valor para troco (ex: 50.00)
}
```

#### Resposta de Sucesso (200 OK)

Retorna o pedido atualizado com status `ENTREGUE`:

```json
{
  "id": 123,
  "empresa_id": 1,
  "numero_pedido": "BAL-000001",
  "mesa_id": 5,
  "cliente_id": 10,
  "status": "E",
  "status_descricao": "Entregue",
  "observacoes": "Pedido para viagem",
  "valor_total": 45.50,
  "meio_pagamento_id": 1,
  "troco_para": 50.00,
  "itens": [
    {
      "id": 1,
      "produto_cod_barras": "7891234567890",
      "quantidade": 2,
      "preco_unitario": 15.00,
      "observacao": "Bem passado",
      "produto_descricao_snapshot": "Hambúrguer Artesanal",
      "produto_imagem_snapshot": "https://..."
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z",
  "produtos": {
    "itens": [],
    "receitas": [],
    "combos": []
  }
}
```

**Schema TypeScript da Resposta:**
```typescript
interface PedidoBalcaoOut {
  id: number;
  empresa_id: number;
  numero_pedido: string;
  mesa_id?: number;
  cliente_id?: number;
  status: "P" | "I" | "R" | "E" | "C" | "D" | "X" | "A";
  status_descricao: string;
  observacoes?: string;
  valor_total: number;
  itens: PedidoBalcaoItemOut[];
  created_at?: string;
  updated_at?: string;
  produtos: ProdutosPedidoOut;
}

interface PedidoBalcaoItemOut {
  id: number;
  produto_cod_barras: string;
  quantidade: number;
  preco_unitario: number;
  observacao?: string;
  produto_descricao_snapshot?: string;
  produto_imagem_snapshot?: string;
}
```

#### Respostas de Erro

| Código | Descrição |
|--------|-----------|
| `404` | Pedido não encontrado |
| `401` | Não autenticado |
| `403` | Sem permissão (não é admin) |

---

## Endpoint Alternativo: Fechar Pedido

### **POST** `/api/balcao/admin/pedidos/{pedido_id}/fechar`

Este endpoint é um atalho que chama o mesmo método do endpoint `/fechar-conta`. Aceita os mesmos parâmetros e retorna a mesma resposta.

**Recomendação**: Use o endpoint `/fechar-conta` para maior clareza no código.

---

## Status do Pedido

Após fechar o pedido, o status será alterado para:

- **Status**: `"E"` (ENTREGUE)
- **Status Descrição**: `"Entregue"`

### Status Possíveis de Pedidos de Balcão

| Código | Descrição | Cor Sugerida |
|--------|-----------|--------------|
| `P` | Pendente | Laranja |
| `I` | Em impressão | Azul |
| `R` | Preparando | Amarelo |
| `E` | Entregue | Verde |
| `C` | Cancelado | Vermelho |
| `D` | Editado | Roxo |
| `X` | Em edição | Teal |
| `A` | Aguardando pagamento | Ciano |

---

## Comportamento do Sistema

### Ao Fechar um Pedido:

1. **Status alterado**: O status do pedido muda para `ENTREGUE` (`E`)
2. **Informações de pagamento**: Se fornecidas, são salvas nos campos:
   - `meio_pagamento_id`: ID do meio de pagamento
   - `troco_para`: Valor para troco
3. **Histórico**: Um registro é adicionado ao histórico do pedido com:
   - Tipo de operação: `PEDIDO_FECHADO`
   - Status anterior e novo status
   - Observações sobre pagamento (se houver)
4. **Liberação de mesa**: Se o pedido estava associado a uma mesa:
   - O sistema verifica se há outros pedidos abertos (de balcão ou mesa) na mesma mesa
   - A mesa só é liberada se não houver mais nenhum pedido aberto
   - O status da mesa muda de `OCUPADA` para `LIVRE` (se aplicável)

---

## Exemplos de Uso

### Exemplo 1: Fechar Pedido Sem Informações de Pagamento

```typescript
// Fechar pedido sem informações de pagamento
const fecharPedido = async (pedidoId: number) => {
  const response = await fetch(
    `/api/balcao/admin/pedidos/${pedidoId}/fechar-conta`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(null) // ou não enviar body
    }
  );
  
  if (!response.ok) {
    throw new Error('Erro ao fechar pedido');
  }
  
  return await response.json();
};
```

### Exemplo 2: Fechar Pedido Com Meio de Pagamento

```typescript
// Fechar pedido informando meio de pagamento
const fecharPedidoComPagamento = async (
  pedidoId: number,
  meioPagamentoId: number
) => {
  const response = await fetch(
    `/api/balcao/admin/pedidos/${pedidoId}/fechar-conta`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        meio_pagamento_id: meioPagamentoId
      })
    }
  );
  
  if (!response.ok) {
    throw new Error('Erro ao fechar pedido');
  }
  
  return await response.json();
};
```

### Exemplo 3: Fechar Pedido Com Troco

```typescript
// Fechar pedido informando troco para
const fecharPedidoComTroco = async (
  pedidoId: number,
  meioPagamentoId: number,
  trocoPara: number
) => {
  const response = await fetch(
    `/api/balcao/admin/pedidos/${pedidoId}/fechar-conta`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        meio_pagamento_id: meioPagamentoId,
        troco_para: trocoPara
      })
    }
  );
  
  if (!response.ok) {
    throw new Error('Erro ao fechar pedido');
  }
  
  return await response.json();
};
```

### Exemplo 4: Usando Axios

```typescript
import axios from 'axios';

const fecharPedidoBalcao = async (
  pedidoId: number,
  dadosPagamento?: {
    meio_pagamento_id?: number;
    troco_para?: number;
  }
) => {
  try {
    const response = await axios.post(
      `/api/balcao/admin/pedidos/${pedidoId}/fechar-conta`,
      dadosPagamento || null,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
    
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 404) {
        throw new Error('Pedido não encontrado');
      }
      if (error.response?.status === 401) {
        throw new Error('Não autenticado');
      }
    }
    throw error;
  }
};
```

---

## Fluxo Recomendado no Frontend

1. **Exibir modal/formulário de fechamento**:
   - Mostrar valor total do pedido
   - Opção de selecionar meio de pagamento (opcional)
   - Campo para informar troco (opcional, apenas para dinheiro)
   - Botão "Fechar Pedido"

2. **Validações**:
   - Verificar se o pedido existe
   - Verificar se o pedido não está já fechado ou cancelado
   - Se informar troco, validar que é um número positivo

3. **Chamada à API**:
   - Fazer POST para `/api/balcao/admin/pedidos/{pedido_id}/fechar-conta`
   - Enviar dados de pagamento (se houver)

4. **Tratamento da Resposta**:
   - Se sucesso: atualizar estado do pedido na interface
   - Remover pedido da lista de pedidos abertos
   - Exibir mensagem de sucesso
   - Se houver mesa associada, verificar se foi liberada

5. **Tratamento de Erros**:
   - Exibir mensagem de erro apropriada
   - Se 404: "Pedido não encontrado"
   - Se 401: "Sessão expirada, faça login novamente"
   - Se 403: "Sem permissão para fechar pedidos"

---

## Observações Importantes

1. **Pedidos já fechados**: Não é possível fechar um pedido que já está com status `ENTREGUE` ou `CANCELADO`. O sistema retornará erro 400.

2. **Mesa associada**: Se o pedido tiver uma mesa associada, após fechar, o sistema verificará automaticamente se a mesa pode ser liberada.

3. **Histórico**: Todas as operações de fechamento são registradas no histórico do pedido, incluindo informações de pagamento.

4. **Valor total**: O valor total do pedido é calculado automaticamente com base nos itens e seus adicionais.

5. **Campos opcionais**: Tanto `meio_pagamento_id` quanto `troco_para` são opcionais. O pedido pode ser fechado sem nenhuma informação de pagamento.

---

## Testes

### Casos de Teste Recomendados

1. ✅ Fechar pedido sem informações de pagamento
2. ✅ Fechar pedido com meio de pagamento
3. ✅ Fechar pedido com troco
4. ✅ Fechar pedido com meio de pagamento e troco
5. ✅ Tentar fechar pedido inexistente (deve retornar 404)
6. ✅ Tentar fechar pedido já fechado (deve retornar erro)
7. ✅ Verificar se mesa é liberada após fechar último pedido
8. ✅ Verificar se histórico é criado corretamente

---

## Suporte

Para dúvidas ou problemas, consulte:
- Código do serviço: `app/api/balcao/services/service_pedidos_balcao.py`
- Schema de request: `app/api/balcao/schemas/schema_pedido_balcao.py` (classe `FecharContaBalcaoRequest`)
- Endpoint: `app/api/balcao/router/admin/fechar_conta_pedido.py`

