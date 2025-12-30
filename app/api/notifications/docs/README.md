# 📚 Documentação do Sistema de Notificações WebSocket

Bem-vindo à documentação completa do sistema de notificações em tempo real via WebSocket da API Mensura.

## 📖 Documentação Disponível

- **[Documentação Completa](./WEBSOCKET_FRONTEND.md)** 📡
  - Informações técnicas sobre o sistema
  - Tipos de mensagens e formatos
  - Endpoints da API
  - FAQ técnico

## 🔑 Conceitos Principais

### ⚠️ IMPORTANTE: Variáveis de Ambiente

**A URL da API muda de cliente para cliente.** Sempre use variáveis de ambiente:

- **Next.js:** `NEXT_PUBLIC_API_URL` (ex: `https://teste2.mensuraapi.com.br`)
- **React (CRA):** `REACT_APP_API_URL`
- **React (Vite):** `VITE_API_URL`

A URL do WebSocket é construída automaticamente a partir da URL da API:
- `https://...` → `wss://...` (WebSocket seguro)
- `http://...` → `ws://...` (WebSocket não seguro)

### Conexão WebSocket

```
ws://{API_URL}/api/notifications/ws/notifications/{user_id}?empresa_id={empresa_id}
```

**Onde `{API_URL}` vem da variável de ambiente configurada.**

### Tipos de Notificações

- `kanban` - Novo pedido para o kanban
- `pedido_aprovado` - Pedido aprovado
- `pedido_cancelado` - Pedido cancelado
- `pedido_entregue` - Pedido entregue
- E mais...

### Funcionalidades

- ✅ Notificações em tempo real
- ✅ Filtro por rota (ex: kanban só em `/pedidos`)
- ✅ Sistema de ping/pong
- ✅ Reconexão automática
- ✅ Múltiplas conexões por usuário

## 📋 Checklist de Implementação

- [ ] Obter URL do WebSocket (use endpoint `/config/{empresa_id}`)
- [ ] Conectar ao WebSocket
- [ ] Tratar mensagens recebidas
- [ ] Enviar `set_route` ao navegar
- [ ] Enviar `ping` periodicamente
- [ ] Mostrar notificações ao usuário
- [ ] Implementar reconexão automática
- [ ] Testar em desenvolvimento e produção

## 🔗 Endpoints Úteis

### Obter Configuração do WebSocket
```
GET /api/notifications/ws/config/{empresa_id}?user_id={user_id}
```

### Verificar Conexões
```
GET /api/notifications/ws/connections/check/{empresa_id}
```

### Estatísticas Gerais
```
GET /api/notifications/ws/connections/stats
```

## 📞 Suporte

Para dúvidas ou problemas:

1. Verifique a [Documentação Completa](./WEBSOCKET_FRONTEND.md)
2. Consulte o [FAQ](./WEBSOCKET_FRONTEND.md#faq)
3. Veja os logs do backend
4. Use os endpoints de verificação de conexão

## 📝 Estrutura dos Documentos

```
docs/
├── README.md                    ← Você está aqui
└── WEBSOCKET_FRONTEND.md        ← Documentação completa
```

## 🎓 Documentação

Leia a [Documentação Completa](./WEBSOCKET_FRONTEND.md) para todas as informações técnicas necessárias.

---

**Última atualização:** 2024-01-15

