# 🤖 Sistema de Vendas via Chatbot WhatsApp

Sistema completo de vendas conversacional integrado com WhatsApp Business API, Ollama IA e endpoints de preview/checkout.

## 📋 O que foi implementado

### ✅ Arquivos Criados

1. **`core/sales_assistant.py`**
   - Classe `SalesAssistant` - lógica principal de vendas
   - Busca de produtos no banco de dados
   - Integração com endpoints de preview/checkout
   - Formatação de mensagens

2. **`core/sales_prompts.py`**
   - System prompts específicos para vendas
   - Mensagens de erro e sucesso
   - Tom de conversa natural e brasileiro

3. **`core/sales_handler.py`**
   - `SalesConversationHandler` - gerencia o estado da conversa
   - Processa mensagens e detecta intenções
   - Fluxo completo: busca → seleção → endereço → pagamento → checkout

## 🔄 Fluxo de Conversa Implementado

```
1. BOAS-VINDAS
   ↓
   Cliente: "Oi" / "Olá" / "Menu"
   Bot: Mensagem de boas-vindas + promoções + link do cardápio

2. BUSCA DE PRODUTO
   ↓
   Cliente: "Quero pizza" / "Tem hambúrguer?"
   Bot: Busca no banco → Mostra lista de produtos encontrados

3. SELEÇÃO
   ↓
   Cliente: "1" (número do produto)
   Bot: "Quantos você quer?"

4. QUANTIDADE
   ↓
   Cliente: "2"
   Bot: "Adicionou! Quer mais alguma coisa?"

5. COLETAR ENDEREÇO
   ↓
   Cliente: "Pode fechar" / "É isso"
   Bot: "Preciso do seu endereço para entrega"

6. COLETAR PAGAMENTO
   ↓
   Cliente: "Rua X, 123, Bairro Y"
   Bot: "Como vai ser o pagamento? 1-PIX 2-Dinheiro 3-Cartão"

7. PREVIEW DO PEDIDO
   ↓
   Cliente: "1" (escolhe PIX)
   Bot: Chama endpoint /preview → Mostra resumo completo
       "Itens: ...
        Subtotal: R$ XX
        Taxa: R$ YY
        TOTAL: R$ ZZ

        Digite OK para confirmar"

8. CONFIRMAÇÃO
   ↓
   Cliente: "OK"
   Bot: Chama endpoint /checkout/finalizar → Cria pedido
        "Pedido #123 confirmado!
         Aqui está seu QR Code PIX: ..."

9. FINALIZADO
   ↓
   Bot: Salva pedido → Envia notificações → Reseta estado
```

## 🔧 Como Integrar no Webhook

### Opção 1: Integração Direta (Recomendado)

Modifique seu webhook do WhatsApp para usar o sales_handler:

```python
# No arquivo router.py do chatbot

from .core.sales_handler import processar_mensagem_venda

@router.post("/webhook")
async def webhook_whatsapp(request: Request, db: Session = Depends(get_db)):
    """Webhook do WhatsApp - recebe mensagens"""

    body = await request.json()

    # Extrair dados da mensagem
    if body.get("entry"):
        for entry in body["entry"]:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for message in messages:
                    phone_number = message.get("from")  # Ex: 5561999999999
                    message_text = message.get("text", {}).get("body", "")

                    # AQUI: Usar o sales handler
                    resposta = await processar_mensagem_venda(
                        db=db,
                        user_id=phone_number,
                        mensagem=message_text,
                        empresa_id=1  # ID da sua empresa
                    )

                    # Enviar resposta via WhatsApp
                    await enviar_mensagem_whatsapp(phone_number, resposta)

    return {"status": "success"}
```

### Opção 2: Híbrido (IA + Vendas)

Use IA para conversas gerais, mas ative modo vendas quando detectar intenção de compra:

```python
from .core.sales_handler import processar_mensagem_venda, SalesConversationHandler

# Verificar se o usuário está em processo de venda
estado_atual, _ = obter_estado_conversa(db, phone_number)

if estado_atual != SalesAssistant.STATE_WELCOME:
    # Cliente está no meio de uma venda, usar sales_handler
    resposta = await processar_mensagem_venda(db, phone_number, message_text)
else:
    # Cliente não está comprando, usar IA normal
    # Mas detectar se ele quer comprar algo
    if any(palavra in message_text.lower() for palavra in ['quero', 'comprar', 'pedido', 'pedir']):
        # Iniciar processo de vendas
        resposta = await processar_mensagem_venda(db, phone_number, message_text)
    else:
        # Conversa normal com IA
        resposta = await processar_com_ollama(message_text)
```

## 🗄️ Armazenamento de Estado

Por enquanto, o estado da conversa está em memória (dicionário Python). Para produção, implemente:

### Redis (Recomendado)

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def salvar_estado_conversa(db: Session, user_id: str, estado: str, dados: Dict):
    """Salva estado no Redis"""
    chave = f"sales_state:{user_id}"
    valor = {
        "estado": estado,
        "dados": dados,
        "timestamp": datetime.now().isoformat()
    }
    redis_client.setex(chave, 86400, json.dumps(valor))  # TTL 24h

def obter_estado_conversa(db: Session, user_id: str):
    """Obtém estado do Redis"""
    chave = f"sales_state:{user_id}"
    valor = redis_client.get(chave)

    if valor:
        dados_salvos = json.loads(valor)
        return (dados_salvos["estado"], dados_salvos["dados"])
    else:
        # Estado inicial
        return (SalesAssistant.STATE_WELCOME, {})
```

### Banco de Dados (Alternativa)

```sql
CREATE TABLE chatbot.sales_sessions (
    user_id VARCHAR(20) PRIMARY KEY,
    estado VARCHAR(50),
    dados JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sales_sessions_updated ON chatbot.sales_sessions(updated_at);
```

```python
from app.api.chatbot.models import SalesSession

def salvar_estado_conversa(db: Session, user_id: str, estado: str, dados: Dict):
    session = db.query(SalesSession).filter_by(user_id=user_id).first()

    if session:
        session.estado = estado
        session.dados = dados
        session.updated_at = datetime.now()
    else:
        session = SalesSession(user_id=user_id, estado=estado, dados=dados)
        db.add(session)

    db.commit()
```

## 📦 Dependências Necessárias

Adicione ao `requirements.txt`:

```
httpx>=0.24.0  # Para chamadas HTTP aos endpoints
sqlalchemy>=2.0.0
redis>=4.5.0  # Se usar Redis
```

## 🎯 Integração com Preview/Checkout

O sistema já está preparado para chamar seus endpoints:

### Preview
```python
# Em sales_assistant.py, linha ~150
POST http://localhost:8000/api/cardapio/client/checkout/preview

Payload:
{
    "tipo_entrega": "DELIVERY",
    "itens": [
        {
            "produto_id": 1,
            "quantidade": 2,
            "observacao": "",
            "adicionais": []
        }
    ],
    "endereco_id": null,
    "cliente_id": null,
    "metodo_pagamento": "PIX"
}
```

### Checkout
```python
# Em sales_assistant.py, linha ~200
POST http://localhost:8000/api/cardapio/client/checkout/finalizar

Usa o mesmo payload do preview
```

## 🔐 Autenticação

Se seus endpoints precisam de autenticação, adicione o token:

```python
# Em sales_assistant.py

async def criar_preview_checkout(self, ...):
    headers = {
        "Authorization": f"Bearer {cliente_data.get('token', '')}",
        "Content-Type": "application/json"
    }

    response = await client.post(url, json=payload, headers=headers)
```

Para obter o token, você pode:
1. Criar cliente automático pelo telefone
2. Usar token de serviço (service account)
3. Implementar autenticação via WhatsApp

## 🧪 Testando

### 1. Teste Local (sem WhatsApp)

```python
# test_sales.py
from app.api.chatbot.core.sales_handler import processar_mensagem_venda
from app.database.db_connection import get_db

db = next(get_db())

# Simular conversa
mensagens = [
    "oi",
    "quero pizza",
    "1",  # seleciona primeira pizza
    "2",  # quantidade 2
    "Rua X, 123, Centro",  # endereço
    "1",  # PIX
    "ok"  # confirma
]

for msg in mensagens:
    resposta = await processar_mensagem_venda(db, "5561999999999", msg)
    print(f"Cliente: {msg}")
    print(f"Bot: {resposta}\n")
```

### 2. Teste via WhatsApp

Envie mensagem para o número configurado:
1. "oi" → Deve receber boas-vindas
2. "quero pizza" → Deve listar pizzas
3. "1" → Deve pedir quantidade
4. etc...

## 🐛 Troubleshooting

### Produtos não são encontrados
- Verifique se a tabela de produtos está populada
- Confirme o `empresa_id` correto
- Check se produtos estão com `ativo=True`

### Preview retorna erro
- Verifique se o endpoint `/checkout/preview` está funcionando
- Teste direto via Postman/Insomnia
- Confira os schemas Pydantic

### Estado da conversa não persiste
- Implemente Redis ou banco de dados para salvar estado
- Por padrão, estado está em memória (resetado ao reiniciar)

## 🚀 Próximos Passos

1. **Implementar Redis** para estado persistente
2. **Adicionar autenticação** de clientes
3. **Melhorar busca** de produtos (fuzzy search, sinônimos)
4. **Adicionar adicionais/combos** ao fluxo
5. **Implementar carrinho** com múltiplos produtos
6. **Tracking de entrega** em tempo real
7. **Histórico de pedidos** do cliente
8. **Cupons de desconto**

## 📚 Referências

- WhatsApp Business API: https://developers.facebook.com/docs/whatsapp
- Ollama: https://ollama.ai/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Redis: https://redis.io/docs/

---

**Desenvolvido por:** Vinícius Aguiar
**Data:** Setembro 2024
**Sistema:** Mensura API - Chatbot de Vendas
