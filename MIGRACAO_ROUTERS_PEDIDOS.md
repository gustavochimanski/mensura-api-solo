# Migração: Unificação dos Routers de Pedidos

## 📋 Resumo das Mudanças

Todos os routers de pedidos (Delivery, Mesa e Balcão) foram **unificados em um único router** (`router_pedidos_admin.py`). Isso foi possível porque todos os tipos de pedidos agora usam a **mesma tabela unificada** no banco de dados.

### ❌ Arquivos Removidos
- `app/api/pedidos/router/admin/router_pedidos_mesa_admin.py`
- `app/api/pedidos/router/admin/router_pedidos_delivery_admin.py`

### ✅ Arquivo Unificado
- `app/api/pedidos/router/admin/router_pedidos_admin.py` (contém TODOS os endpoints)

---

## 🔄 Mudanças nas URLs

### **ANTES** (URLs antigas - NÃO FUNCIONAM MAIS)
```
/api/pedidos/admin/mesa/...
/api/pedidos/admin/delivery/...
/api/pedidos/admin/... (endpoints gerais)
```

### **DEPOIS** (URLs novas - USE ESTAS)

#### **Endpoints Gerais** (funcionam para todos os tipos)
```
GET    /api/pedidos/admin/kanban
GET    /api/pedidos/admin/{pedido_id}
GET    /api/pedidos/admin/{pedido_id}/historico
PUT    /api/pedidos/admin/{pedido_id}/status
DELETE /api/pedidos/admin/{pedido_id}
PUT    /api/pedidos/admin/{pedido_id}/entregador
DELETE /api/pedidos/admin/{pedido_id}/entregador
```

#### **Endpoints de Delivery**
```
POST   /api/pedidos/admin/delivery
GET    /api/pedidos/admin/delivery
GET    /api/pedidos/admin/delivery/cliente/{cliente_id}
PUT    /api/pedidos/admin/delivery/{pedido_id}
PUT    /api/pedidos/admin/delivery/{pedido_id}/itens
PUT    /api/pedidos/admin/delivery/{pedido_id}/entregador
DELETE /api/pedidos/admin/delivery/{pedido_id}/entregador
```

#### **Endpoints de Mesa**
```
POST   /api/pedidos/admin/mesa
GET    /api/pedidos/admin/mesa
GET    /api/pedidos/admin/mesa/{mesa_id}/finalizados
GET    /api/pedidos/admin/mesa/cliente/{cliente_id}
PUT    /api/pedidos/admin/mesa/{pedido_id}/adicionar-item
PUT    /api/pedidos/admin/mesa/{pedido_id}/adicionar-produto-generico
PUT    /api/pedidos/admin/mesa/{pedido_id}/observacoes
PUT    /api/pedidos/admin/mesa/{pedido_id}/status
PUT    /api/pedidos/admin/mesa/{pedido_id}/fechar-conta
PUT    /api/pedidos/admin/mesa/{pedido_id}/reabrir
DELETE /api/pedidos/admin/mesa/{pedido_id}/item/{item_id}
```

---

## 📝 Mapeamento de Endpoints

### **Delivery**

| Endpoint Antigo | Endpoint Novo | Método | Observação |
|----------------|---------------|--------|------------|
| `POST /api/pedidos/admin/delivery/` | `POST /api/pedidos/admin/delivery` | POST | ✅ Mesma URL |
| `GET /api/pedidos/admin/delivery/` | `GET /api/pedidos/admin/delivery` | GET | ✅ Mesma URL |
| `GET /api/pedidos/admin/delivery/{pedido_id}` | `GET /api/pedidos/admin/{pedido_id}` | GET | ⚠️ **MUDOU** - Agora é endpoint geral |
| `GET /api/pedidos/admin/delivery/cliente/{cliente_id}` | `GET /api/pedidos/admin/delivery/cliente/{cliente_id}` | GET | ✅ Mesma URL |
| `PUT /api/pedidos/admin/delivery/{pedido_id}` | `PUT /api/pedidos/admin/delivery/{pedido_id}` | PUT | ✅ Mesma URL |
| `PUT /api/pedidos/admin/delivery/{pedido_id}/itens` | `PUT /api/pedidos/admin/delivery/{pedido_id}/itens` | PUT | ✅ Mesma URL |
| `PUT /api/pedidos/admin/delivery/{pedido_id}/status` | `PUT /api/pedidos/admin/{pedido_id}/status` | PUT | ⚠️ **MUDOU** - Agora é endpoint geral |
| `PUT /api/pedidos/admin/delivery/{pedido_id}/entregador` | `PUT /api/pedidos/admin/delivery/{pedido_id}/entregador` | PUT | ✅ Mesma URL |
| `DELETE /api/pedidos/admin/delivery/{pedido_id}/entregador` | `DELETE /api/pedidos/admin/delivery/{pedido_id}/entregador` | DELETE | ✅ Mesma URL |
| `DELETE /api/pedidos/admin/delivery/{pedido_id}` | `DELETE /api/pedidos/admin/{pedido_id}` | DELETE | ⚠️ **MUDOU** - Agora é endpoint geral |

### **Mesa**

| Endpoint Antigo | Endpoint Novo | Método | Observação |
|----------------|---------------|--------|------------|
| `POST /api/pedidos/admin/mesa/` | `POST /api/pedidos/admin/mesa` | POST | ✅ Mesma URL |
| `GET /api/pedidos/admin/mesa/` | `GET /api/pedidos/admin/mesa` | GET | ✅ Mesma URL |
| `GET /api/pedidos/admin/mesa/{pedido_id}` | `GET /api/pedidos/admin/{pedido_id}` | GET | ⚠️ **MUDOU** - Agora é endpoint geral |
| `GET /api/pedidos/admin/mesa/mesa/{mesa_id}/finalizados` | `GET /api/pedidos/admin/mesa/{mesa_id}/finalizados` | GET | ⚠️ **MUDOU** - Removido `/mesa/` duplicado |
| `GET /api/pedidos/admin/mesa/cliente/{cliente_id}` | `GET /api/pedidos/admin/mesa/cliente/{cliente_id}` | GET | ✅ Mesma URL |
| `PUT /api/pedidos/admin/mesa/{pedido_id}/adicionar-item` | `PUT /api/pedidos/admin/mesa/{pedido_id}/adicionar-item` | PUT | ✅ Mesma URL |
| `PUT /api/pedidos/admin/mesa/{pedido_id}/adicionar-produto-generico` | `PUT /api/pedidos/admin/mesa/{pedido_id}/adicionar-produto-generico` | PUT | ✅ Mesma URL |
| `PUT /api/pedidos/admin/mesa/{pedido_id}/observacoes` | `PUT /api/pedidos/admin/mesa/{pedido_id}/observacoes` | PUT | ✅ Mesma URL |
| `PUT /api/pedidos/admin/mesa/{pedido_id}/status` | `PUT /api/pedidos/admin/{pedido_id}/status` | PUT | ⚠️ **MUDOU** - Agora é endpoint geral |
| `PUT /api/pedidos/admin/mesa/{pedido_id}/fechar-conta` | `PUT /api/pedidos/admin/mesa/{pedido_id}/fechar-conta` | PUT | ✅ Mesma URL |
| `PUT /api/pedidos/admin/mesa/{pedido_id}/reabrir` | `PUT /api/pedidos/admin/mesa/{pedido_id}/reabrir` | PUT | ✅ Mesma URL |
| `DELETE /api/pedidos/admin/mesa/{pedido_id}/item/{item_id}` | `DELETE /api/pedidos/admin/mesa/{pedido_id}/item/{item_id}` | DELETE | ✅ Mesma URL |
| `DELETE /api/pedidos/admin/mesa/{pedido_id}` | `DELETE /api/pedidos/admin/{pedido_id}` | DELETE | ⚠️ **MUDOU** - Agora é endpoint geral |

---

## ⚠️ **AÇÕES NECESSÁRIAS NO FRONTEND**

### 1. **Endpoints que MUDARAM de URL**

#### **Buscar Pedido por ID**
```javascript
// ❌ ANTES
GET /api/pedidos/admin/delivery/{pedido_id}
GET /api/pedidos/admin/mesa/{pedido_id}

// ✅ DEPOIS (use este para TODOS os tipos)
GET /api/pedidos/admin/{pedido_id}
```

#### **Atualizar Status**
```javascript
// ❌ ANTES
PUT /api/pedidos/admin/delivery/{pedido_id}/status
PUT /api/pedidos/admin/mesa/{pedido_id}/status

// ✅ DEPOIS (use este para TODOS os tipos)
PUT /api/pedidos/admin/{pedido_id}/status
```

#### **Cancelar Pedido**
```javascript
// ❌ ANTES
DELETE /api/pedidos/admin/delivery/{pedido_id}
DELETE /api/pedidos/admin/mesa/{pedido_id}

// ✅ DEPOIS (use este para TODOS os tipos)
DELETE /api/pedidos/admin/{pedido_id}
```

#### **Listar Pedidos Finalizados de Mesa**
```javascript
// ❌ ANTES
GET /api/pedidos/admin/mesa/mesa/{mesa_id}/finalizados

// ✅ DEPOIS
GET /api/pedidos/admin/mesa/{mesa_id}/finalizados
```

### 2. **Endpoints que PERMANECERAM IGUAIS**

A maioria dos endpoints específicos de cada tipo permaneceu igual:
- ✅ Todos os endpoints de criação (`POST /api/pedidos/admin/delivery`, `POST /api/pedidos/admin/mesa`)
- ✅ Todos os endpoints de listagem (`GET /api/pedidos/admin/delivery`, `GET /api/pedidos/admin/mesa`)
- ✅ Todos os endpoints específicos de mesa (adicionar item, fechar conta, etc.)
- ✅ Todos os endpoints específicos de delivery (atualizar itens, vincular entregador, etc.)

---

## 🎯 **Vantagens da Unificação**

1. **Consistência**: Todos os pedidos usam os mesmos endpoints para operações comuns (buscar, status, cancelar)
2. **Manutenibilidade**: Um único arquivo para manter em vez de três
3. **Simplicidade**: Menos rotas para gerenciar
4. **Flexibilidade**: Fácil adicionar novos tipos de pedidos no futuro

---

## 📌 **Checklist de Migração**

- [ ] Atualizar todas as chamadas de `GET /api/pedidos/admin/{tipo}/{pedido_id}` para `GET /api/pedidos/admin/{pedido_id}`
- [ ] Atualizar todas as chamadas de `PUT /api/pedidos/admin/{tipo}/{pedido_id}/status` para `PUT /api/pedidos/admin/{pedido_id}/status`
- [ ] Atualizar todas as chamadas de `DELETE /api/pedidos/admin/{tipo}/{pedido_id}` para `DELETE /api/pedidos/admin/{pedido_id}`
- [ ] Atualizar chamada de `GET /api/pedidos/admin/mesa/mesa/{mesa_id}/finalizados` para `GET /api/pedidos/admin/mesa/{mesa_id}/finalizados`
- [ ] Testar todos os fluxos de pedidos (criação, listagem, atualização, cancelamento)
- [ ] Verificar se não há referências aos routers antigos no código

---

## 🔍 **Como Identificar Endpoints que Precisam de Atualização**

Procure no código do frontend por:
- `/api/pedidos/admin/delivery/{pedido_id}` (sem `/delivery/` no final)
- `/api/pedidos/admin/mesa/{pedido_id}` (sem `/mesa/` no final)
- `/api/pedidos/admin/mesa/mesa/` (duplicado)

Todos esses devem ser atualizados conforme a tabela acima.

---

## 📞 **Suporte**

Se encontrar algum problema durante a migração, verifique:
1. Se a URL está correta conforme este documento
2. Se o método HTTP está correto (GET, POST, PUT, DELETE)
3. Se os parâmetros estão sendo enviados corretamente
4. Se o token de autenticação está sendo enviado

---

**Data da Migração:** 2024
**Versão da API:** Unificada

