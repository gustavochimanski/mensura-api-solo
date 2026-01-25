# Documentação WebSocket — Notificações de Meios de Pagamento

Esta documentação descreve **como o frontend deve receber e processar notificações** quando meios de pagamento são criados, atualizados ou deletados.

---

## 1) Visão Geral

Quando um meio de pagamento é **criado**, **atualizado** ou **deletado** no backend, o sistema envia uma notificação em tempo real via WebSocket para todos os clientes conectados.

### Evento WebSocket

- **Nome do evento**: `meios_pagamento.v1.atualizados`
- **Escopo**: `empresa` (todos os usuários da empresa recebem)
- **Quando é disparado**: Após qualquer operação CRUD (Create, Update, Delete) em meios de pagamento

### ⚠️ Nota de Implementação

**Status atual**: O evento está definido e documentado, mas **ainda não está sendo disparado automaticamente** pelo backend quando meios de pagamento são modificados.

**Para ativar**: É necessário implementar a notificação no serviço `MeioPagamentoService` (métodos `create`, `update`, `delete`).

**Solução temporária**: O frontend pode usar polling periódico como fallback até a implementação estar completa.

---

## 2) Formato da Mensagem

### 2.1) Envelope do Evento

Quando um meio de pagamento é modificado, o frontend recebe uma mensagem no formato padronizado:

```json
{
  "type": "event",
  "event": "meios_pagamento.v1.atualizados",
  "scope": "empresa",
  "payload": {
    "empresa_id": "1",
    "action": "updated",
    "meio_pagamento_id": 5
  },
  "timestamp": "2026-01-24T14:30:00.000000"
}
```

### 2.2) Campos do Payload

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `empresa_id` | `string` | ID da empresa que teve meios de pagamento modificados |
| `action` | `string` | Ação realizada: `"created"`, `"updated"` ou `"deleted"` |
| `meio_pagamento_id` | `number` | ID do meio de pagamento afetado (presente em todas as ações) |

### 2.3) Exemplos de Payload por Ação

#### Criado (created)
```json
{
  "empresa_id": "1",
  "action": "created",
  "meio_pagamento_id": 10
}
```

#### Atualizado (updated)
```json
{
  "empresa_id": "1",
  "action": "updated",
  "meio_pagamento_id": 5
}
```

#### Deletado (deleted)
```json
{
  "empresa_id": "1",
  "action": "deleted",
  "meio_pagamento_id": 3
}
```

---

## 3) Como o Frontend Deve Reagir

### 3.1) Estratégia Recomendada: Refetch

**IMPORTANTE**: O payload contém apenas o **ID** do meio de pagamento afetado. O frontend deve:

1. **Receber o evento** via WebSocket
2. **Invalidar o cache** local de meios de pagamento
3. **Refazer a requisição HTTP** para obter a lista atualizada

**Por quê?**
- Garante que o frontend sempre tenha os dados mais recentes
- Evita inconsistências se múltiplas modificações ocorrerem rapidamente
- Simplifica o backend (não precisa enviar dados completos)

### 3.2) Fluxo de Processamento

```
1. Cliente conectado ao WebSocket
   ↓
2. Backend modifica meio de pagamento (create/update/delete)
   ↓
3. Backend envia evento: "meios_pagamento.v1.atualizados"
   ↓
4. Frontend recebe evento
   ↓
5. Frontend invalida cache de meios de pagamento
   ↓
6. Frontend faz GET /api/cadastros/admin/meios-pagamento
   ↓
7. Frontend atualiza UI com nova lista
```

---

## 4) Implementação no Frontend

### 4.1) TypeScript: Tipos

```typescript
// Tipos para o evento de meios de pagamento
type MeiosPagamentoEventPayload = {
  empresa_id: string;
  action: "created" | "updated" | "deleted";
  meio_pagamento_id: number;
};

type WSEventMessage = {
  type: "event";
  event: "meios_pagamento.v1.atualizados";
  scope: "empresa";
  payload: MeiosPagamentoEventPayload;
  timestamp: string;
};
```

### 4.2) Exemplo: Handler do Evento

```typescript
function handleMeiosPagamentoEvent(message: WSEventMessage) {
  const { payload } = message;
  
  console.log(`Meio de pagamento ${payload.action}:`, payload.meio_pagamento_id);
  
  // Invalida cache (exemplo com React Query)
  queryClient.invalidateQueries(['meios-pagamento', payload.empresa_id]);
  
  // Ou refaz fetch manualmente
  // fetchMeiosPagamento(payload.empresa_id);
}
```

### 4.3) Exemplo: Integração com React Query

```typescript
import { useQueryClient } from '@tanstack/react-query';

function useMeiosPagamentoWebSocket(empresaId: string) {
  const queryClient = useQueryClient();
  
  useEffect(() => {
    // Conecta ao WebSocket (ver DOCUMENTACAO_FRONTEND_WEBSOCKET.md)
    const ws = connectMensuraWS({
      wsUrl: `wss://api.exemplo.com/api/notifications/ws/notifications?empresa_id=${empresaId}`,
      accessToken: getAccessToken(),
      onMessage: (msg) => {
        // Verifica se é o evento de meios de pagamento
        if (
          msg.type === "event" &&
          msg.event === "meios_pagamento.v1.atualizados"
        ) {
          // Invalida e refaz a query automaticamente
          queryClient.invalidateQueries({
            queryKey: ['meios-pagamento', empresaId]
          });
        }
      }
    });
    
    return () => {
      ws.close();
    };
  }, [empresaId, queryClient]);
}
```

### 4.4) Exemplo: Integração com Zustand/Redux

```typescript
// Store
const useMeiosPagamentoStore = create((set, get) => ({
  meiosPagamento: [],
  isLoading: false,
  
  // Ação para atualizar após receber evento WebSocket
  refreshMeiosPagamento: async (empresaId: string) => {
    set({ isLoading: true });
    try {
      const response = await fetch(
        `/api/cadastros/admin/meios-pagamento`,
        { headers: { Authorization: `Bearer ${getToken()}` } }
      );
      const data = await response.json();
      set({ meiosPagamento: data, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      console.error('Erro ao atualizar meios de pagamento:', error);
    }
  }
}));

// Handler WebSocket
function setupMeiosPagamentoWebSocket(empresaId: string) {
  const ws = connectMensuraWS({
    wsUrl: `wss://api.exemplo.com/api/notifications/ws/notifications?empresa_id=${empresaId}`,
    accessToken: getAccessToken(),
    onMessage: (msg) => {
      if (
        msg.type === "event" &&
        msg.event === "meios_pagamento.v1.atualizados"
      ) {
        // Dispara refresh na store
        useMeiosPagamentoStore.getState().refreshMeiosPagamento(empresaId);
      }
    }
  });
  
  return ws;
}
```

---

## 5) Endpoint HTTP para Refetch

Após receber o evento WebSocket, o frontend deve fazer uma requisição HTTP para obter a lista atualizada:

### 5.1) Endpoint

- **GET** `/api/cadastros/admin/meios-pagamento`
- **Autenticação**: `Authorization: Bearer <token>`
- **Resposta**: Array de `MeioPagamentoResponse`

### 5.2) Exemplo de Resposta

```json
[
  {
    "id": 1,
    "nome": "PIX",
    "tipo": "PIX_ONLINE",
    "ativo": true,
    "created_at": "2026-01-01T10:00:00",
    "updated_at": "2026-01-24T14:30:00"
  },
  {
    "id": 2,
    "nome": "Cartão de Crédito",
    "tipo": "CARTAO_ENTREGA",
    "ativo": true,
    "created_at": "2026-01-01T10:00:00",
    "updated_at": "2026-01-24T14:30:00"
  }
]
```

---

## 6) Casos de Uso

### 6.1) Lista de Meios de Pagamento

**Cenário**: Usuário A está visualizando a lista de meios de pagamento. Usuário B (mesma empresa) cria um novo meio de pagamento.

**Comportamento esperado**:
1. Usuário A recebe evento `meios_pagamento.v1.atualizados` com `action: "created"`
2. Lista é atualizada automaticamente (sem refresh manual)
3. Novo meio de pagamento aparece na UI

### 6.2) Formulário de Edição

**Cenário**: Usuário A está editando um meio de pagamento. Usuário B deleta o mesmo meio de pagamento.

**Comportamento esperado**:
1. Usuário A recebe evento `meios_pagamento.v1.atualizados` com `action: "deleted"`
2. Formulário é fechado ou mostra mensagem de erro
3. Lista é atualizada (meio de pagamento removido)

### 6.3) Seleção de Meio(s) de Pagamento no Pedido

**Cenário**: Usuário está criando um pedido e selecionando **um ou mais** meios de pagamento. Um meio de pagamento é desativado (`ativo: false`).

**Comportamento esperado**:
1. Evento `meios_pagamento.v1.atualizados` com `action: "updated"` é recebido
2. Lista de opções é atualizada
3. Se **algum** dos meios de pagamento selecionados foi desativado, mostra aviso ou remove da seleção

**Nota**: O sistema aceita **múltiplas formas de pagamento** por pedido (ex.: parte em PIX, parte em dinheiro). O frontend deve permitir selecionar mais de um meio e informar o `valor` de cada um no payload `meios_pagamento` ao finalizar o checkout.

---

## 7) Tratamento de Erros

### 7.1) WebSocket Desconectado

Se o WebSocket desconectar, o frontend deve:

1. Tentar reconectar automaticamente (com backoff exponencial)
2. Fazer polling periódico como fallback (ex: a cada 30 segundos)
3. Mostrar indicador visual de "sincronização offline"

### 7.2) Refetch Falhou

Se o refetch HTTP falhar após receber o evento:

1. Logar o erro
2. Mostrar notificação ao usuário (opcional)
3. Tentar novamente após alguns segundos
4. Não bloquear a UI (degradação graciosa)

---

## 8) Checklist de Implementação

- [ ] Conectar ao WebSocket (ver `DOCUMENTACAO_FRONTEND_WEBSOCKET.md`)
- [ ] Escutar eventos do tipo `"meios_pagamento.v1.atualizados"`
- [ ] Extrair `action` e `meio_pagamento_id` do payload
- [ ] Invalidar cache/refazer fetch após receber evento
- [ ] Atualizar UI com nova lista de meios de pagamento
- [ ] Tratar casos especiais (ex: meio de pagamento deletado enquanto está sendo editado)
- [ ] Implementar reconexão automática do WebSocket
- [ ] Adicionar fallback de polling (opcional, mas recomendado)

---

## 9) Exemplo Completo (React + TypeScript)

```typescript
import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

interface MeioPagamento {
  id: number;
  nome: string;
  tipo: string;
  ativo: boolean;
}

function MeiosPagamentoList({ empresaId }: { empresaId: string }) {
  const queryClient = useQueryClient();
  const [wsConnected, setWsConnected] = useState(false);
  
  // Query para buscar meios de pagamento
  const { data: meiosPagamento, isLoading } = useQuery<MeioPagamento[]>({
    queryKey: ['meios-pagamento', empresaId],
    queryFn: async () => {
      const response = await fetch(
        `/api/cadastros/admin/meios-pagamento`,
        {
          headers: {
            'Authorization': `Bearer ${getAccessToken()}`
          }
        }
      );
      return response.json();
    }
  });
  
  // WebSocket para receber notificações
  useEffect(() => {
    const ws = connectMensuraWS({
      wsUrl: `wss://api.exemplo.com/api/notifications/ws/notifications?empresa_id=${empresaId}`,
      accessToken: getAccessToken(),
      onOpen: () => {
        console.log('WebSocket conectado');
        setWsConnected(true);
      },
      onClose: () => {
        console.log('WebSocket desconectado');
        setWsConnected(false);
      },
      onMessage: (msg) => {
        // Processa evento de meios de pagamento
        if (
          msg.type === "event" &&
          msg.event === "meios_pagamento.v1.atualizados"
        ) {
          const { action, meio_pagamento_id } = msg.payload;
          console.log(`Meio de pagamento ${action}:`, meio_pagamento_id);
          
          // Invalida cache e refaz fetch
          queryClient.invalidateQueries({
            queryKey: ['meios-pagamento', empresaId]
          });
        }
      }
    });
    
    return () => {
      ws.close();
    };
  }, [empresaId, queryClient]);
  
  if (isLoading) {
    return <div>Carregando...</div>;
  }
  
  return (
    <div>
      <div>
        Status WebSocket: {wsConnected ? '🟢 Conectado' : '🔴 Desconectado'}
      </div>
      
      <h2>Meios de Pagamento</h2>
      <ul>
        {meiosPagamento?.map((mp) => (
          <li key={mp.id}>
            {mp.nome} ({mp.tipo}) - {mp.ativo ? 'Ativo' : 'Inativo'}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

## 10) Referências

- **Documentação WebSocket Geral**: `DOCUMENTACAO_FRONTEND_WEBSOCKET.md`
- **API REST de Meios de Pagamento**: `/api/cadastros/admin/meios-pagamento`
- **Eventos WebSocket Disponíveis**: `app/api/notifications/core/ws_events.py`
- **Múltiplos meios de pagamento (frontend Admin e Cliente)**: `app/api/pedidos/docs/DOCUMENTACAO_MULTIPLOS_MEIOS_PAGAMENTO_FRONTEND.md`

---

## 11) Notas Importantes

1. **O evento é enviado para TODA a empresa**, não apenas para o usuário que fez a modificação
2. **O payload contém apenas o ID** - sempre faça refetch para obter dados completos
3. **Ação "updated"** é disparada para qualquer campo modificado (nome, tipo, ativo, etc.)
4. **Não confie apenas no WebSocket** - implemente fallback de polling para casos de desconexão
5. **Trate race conditions** - se o usuário estiver editando um meio de pagamento que foi deletado, mostre erro apropriado
6. **Pedidos aceitam múltiplos meios de pagamento** - na criação do pedido (checkout), envie `meios_pagamento` como array; cada item deve ter `id` (ou `meio_pagamento_id`) e `valor`. A soma dos valores deve bater com o total do pedido.

---

## 12) Status da Implementação no Backend

### ⚠️ Implementação Pendente

O evento `meios_pagamento.v1.atualizados` está **definido** mas **não está sendo disparado automaticamente** quando meios de pagamento são modificados.

### Arquivos Envolvidos

- **Definição do evento**: `app/api/notifications/core/ws_events.py` (linha 14)
- **Serviço que precisa notificar**: `app/api/cadastros/services/service_meio_pagamento.py`
- **WebSocket Manager**: `app/api/notifications/core/websocket_manager.py`

### Como Implementar (Backend)

Para ativar as notificações, adicione o seguinte código no `MeioPagamentoService`:

```python
# No método create()
async def create(self, data: MeioPagamentoCreate, empresa_id: str):
    novo = MeioPagamentoModel(**data.dict())
    resultado = self.repo.create(novo)
    
    # Notifica via WebSocket
    from app.api.notifications.core.websocket_manager import websocket_manager
    from app.api.notifications.core.ws_events import WSEvents
    
    await websocket_manager.emit_event(
        event=WSEvents.MEIOS_PAGAMENTO_ATUALIZADOS,
        scope="empresa",
        empresa_id=empresa_id,
        payload={
            "empresa_id": empresa_id,
            "action": "created",
            "meio_pagamento_id": resultado.id
        }
    )
    
    return resultado

# Similar para update() e delete()
```

**Nota**: Como `MeioPagamentoModel` não tem `empresa_id`, será necessário obter o `empresa_id` do contexto do usuário atual (via `get_current_user` no router).

### Solução Temporária para o Frontend

Enquanto a implementação não estiver completa, o frontend deve:

1. Usar **polling periódico** (ex: a cada 30-60 segundos)
2. Fazer refetch após operações CRUD locais (otimista)
3. Preparar o código para receber eventos WebSocket (já implementado)

---

**Última atualização**: 2026-01-24
