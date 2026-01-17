# 📊 Diagrama Completo do Fluxo do Chatbot

## 🎯 Visão Geral do Sistema

Este documento apresenta o diagrama completo de como funciona o sistema de chatbot integrado com WhatsApp, IA (Groq/LLaMA), carrinho temporário e finalização de pedidos.

---

## 🔄 Fluxo Principal - Processamento de Mensagens

```mermaid
graph TB
    Start([Cliente envia mensagem no WhatsApp]) --> Webhook[Webhook 360Dialog/Meta]
    Webhook --> CheckStatus{Status Global<br/>do Bot Ativo?}
    CheckStatus -->|Não| End1([Retorna 200 OK<br/>sem processar])
    CheckStatus -->|Sim| ParseBody[Parse JSON do Webhook]
    ParseBody --> BackgroundTask[Adiciona Task em Background]
    BackgroundTask --> Return200[Retorna 200 OK imediatamente]
    Return200 --> ProcessMsg[process_whatsapp_message]
    
    ProcessMsg --> CheckDup{Verifica Duplicação<br/>message_id?}
    CheckDup -->|Duplicado| End2([Ignora mensagem])
    CheckDup -->|Nova| CreateClient[Identifica/Cria Cliente<br/>pelo telefone]
    
    CreateClient --> GetConfig[Busca Configuração<br/>ChatbotConfig]
    GetConfig --> CheckAccept{aceita_pedidos_whatsapp<br/>= true?}
    
    CheckAccept -->|false| Redirect[Envia mensagem<br/>de redirecionamento<br/>com link do cardápio]
    Redirect --> End3([Fim])
    
    CheckAccept -->|true| GetConversation[Busca/Cria Conversa<br/>no banco]
    GetConversation --> GetPrompt[Busca Prompt do Sistema<br/>do banco]
    GetPrompt --> GroqHandler[processar_mensagem_groq<br/>GroqSalesHandler]
    
    GroqHandler --> SendResponse[Envia Resposta<br/>via WhatsApp API]
    SendResponse --> SaveLog[Salva mensagens<br/>no banco]
    SaveLog --> End4([Fim])
    
    style Start fill:#e1f5ff
    style Webhook fill:#fff4e1
    style GroqHandler fill:#ffe1f5
    style SendResponse fill:#e1ffe1
    style End1 fill:#ffcccc
    style End2 fill:#ffcccc
    style End3 fill:#ffcccc
    style End4 fill:#ccffcc
```

---

## 🤖 Fluxo do GroqSalesHandler - Processamento com IA

```mermaid
graph TB
    Start[processar_mensagem_groq] --> LoadState[Carrega Estado da Conversa<br/>do banco]
    LoadState --> GetCart[Busca Carrinho Atual<br/>do usuário]
    GetCart --> GetProducts[Busca Lista de Produtos<br/>disponíveis]
    GetProducts --> BuildContext[Monta Contexto para IA:<br/>- Histórico de mensagens<br/>- Carrinho atual<br/>- Produtos disponíveis<br/>- Estado da conversa]
    
    BuildContext --> CallGroq[Chama API Groq<br/>com Function Calling]
    CallGroq --> ParseResponse[IA retorna:<br/>- Resposta textual<br/>- Função a executar]
    
    ParseResponse --> CheckFunction{Função<br/>chamada?}
    CheckFunction -->|Não| TextResponse[Retorna apenas<br/>resposta textual]
    
    CheckFunction -->|Sim| ExecFunction[Executa Função]
    ExecFunction --> FunctionType{Tipo de<br/>Função?}
    
    FunctionType -->|adicionar_produto| AddProduct[Busca Produto<br/>Adiciona ao Carrinho]
    FunctionType -->|ver_carrinho| ShowCart[Formata Carrinho<br/>para exibição]
    FunctionType -->|finalizar_pedido| StartCheckout[Inicia Fluxo<br/>de Checkout]
    FunctionType -->|ver_cardapio| ShowMenu[Lista Produtos<br/>do Cardápio]
    FunctionType -->|remover_produto| RemoveProduct[Remove Item<br/>do Carrinho]
    FunctionType -->|informar_sobre_produto| InfoProduct[Busca Info<br/>do Produto]
    FunctionType -->|personalizar_produto| CustomizeProduct[Personaliza Item<br/>do Carrinho]
    FunctionType -->|ver_adicionais| ShowAddons[Lista Adicionais<br/>Disponíveis]
    FunctionType -->|ver_combos| ShowCombos[Lista Combos<br/>Disponíveis]
    FunctionType -->|conversar| Conversational[Resposta<br/>Conversacional]
    
    AddProduct --> UpdateCart[Atualiza Carrinho<br/>no banco]
    ShowCart --> FormatMsg[Formata Mensagem]
    RemoveProduct --> UpdateCart
    CustomizeProduct --> UpdateCart
    InfoProduct --> FormatMsg
    ShowMenu --> FormatMsg
    ShowAddons --> FormatMsg
    ShowCombos --> FormatMsg
    Conversational --> FormatMsg
    UpdateCart --> FormatMsg
    TextResponse --> FormatMsg
    
    StartCheckout --> CheckState{Estado<br/>Atual?}
    CheckState -->|welcome| AskDelivery[Pergunta:<br/>Entrega ou Retirada?]
    CheckState -->|confirmando_pedido| FinalizeOrder[Finaliza Pedido<br/>via Checkout API]
    
    AskDelivery --> SaveState[Salva Estado<br/>no banco]
    SaveState --> FormatMsg
    FinalizeOrder --> OrderResult[Resultado do<br/>Pedido]
    OrderResult --> FormatMsg
    
    FormatMsg --> ReturnResponse[Retorna Resposta<br/>para Router]
    ReturnResponse --> End([Fim])
    
    style Start fill:#e1f5ff
    style CallGroq fill:#ffe1f5
    style ExecFunction fill:#fff4e1
    style UpdateCart fill:#e1ffe1
    style FinalizeOrder fill:#ffcccc
    style End fill:#ccffcc
```

---

## 🛒 Fluxo do Carrinho Temporário

```mermaid
graph TB
    Start[Operação no Carrinho] --> GetService[CarrinhoService]
    GetService --> LoadContracts[Carrega Contratos:<br/>- ProdutoContract<br/>- ComplementoContract<br/>- ReceitasContract<br/>- ComboContract]
    
    LoadContracts --> Operation{Tipo de<br/>Operação?}
    
    Operation -->|Criar/Atualizar| CreateCart[obter_ou_criar_carrinho]
    Operation -->|Adicionar Item| AddItem[adicionar_item]
    Operation -->|Atualizar Item| UpdateItem[atualizar_item]
    Operation -->|Remover Item| RemoveItem[remover_item]
    Operation -->|Obter Carrinho| GetCart[obter_carrinho]
    Operation -->|Limpar| ClearCart[limpar_carrinho]
    
    CreateCart --> CheckExists{Carrinho<br/>existe?}
    CheckExists -->|Sim| UpdateCart[Atualiza Carrinho<br/>existente]
    CheckExists -->|Não| NewCart[Cria Novo Carrinho<br/>com expires_at 24h]
    
    AddItem --> ItemType{Tipo de<br/>Item?}
    ItemType -->|Produto| AddProduct[Busca Produto<br/>via ProdutoContract<br/>Calcula Preço<br/>Adiciona Complementos]
    ItemType -->|Receita| AddRecipe[Busca Receita<br/>via ReceitasContract<br/>Calcula Preço]
    ItemType -->|Combo| AddCombo[Busca Combo<br/>via ComboContract<br/>Calcula Preço]
    
    AddProduct --> SaveItem[Salva Item no<br/>CarrinhoItemModel]
    AddRecipe --> SaveItem
    AddCombo --> SaveItem
    
    SaveItem --> AddComplements{Item tem<br/>Complementos?}
    AddComplements -->|Sim| ProcessComplements[Processa Complementos:<br/>- Busca via ComplementoContract<br/>- Calcula Preço dos Adicionais<br/>- Salva em CarrinhoItemComplemento<br/>- Salva Adicionais em CarrinhoItemComplementoAdicional]
    AddComplements -->|Não| RecalcTotals
    
    ProcessComplements --> RecalcTotals[Recalcula Totais:<br/>- Subtotal<br/>- Taxa Entrega<br/>- Desconto<br/>- Valor Total]
    
    UpdateItem --> UpdateFields[Atualiza Campos:<br/>- Quantidade<br/>- Observação<br/>- Complementos]
    UpdateFields --> RecalcTotals
    
    RemoveItem --> DeleteItem[Remove Item<br/>do banco]
    DeleteItem --> RecalcTotals
    
    UpdateCart --> RecalcTotals
    NewCart --> RecalcTotals
    RecalcTotals --> SaveCart[Salva Carrinho<br/>atualizado]
    
    GetCart --> ReturnCart[Retorna CarrinhoResponse<br/>com todos os itens]
    ClearCart --> DeleteCart[Remove Carrinho<br/>do banco]
    
    SaveCart --> ReturnCart
    ReturnCart --> End([Fim])
    DeleteCart --> End
    
    style Start fill:#e1f5ff
    style AddProduct fill:#fff4e1
    style AddRecipe fill:#fff4e1
    style AddCombo fill:#fff4e1
    style ProcessComplements fill:#ffe1f5
    style RecalcTotals fill:#e1ffe1
    style End fill:#ccffcc
```

---

## 💳 Fluxo de Checkout e Finalização de Pedido

```mermaid
graph TB
    Start[Cliente solicita<br/>finalizar pedido] --> CheckCart{Carrinho<br/>tem itens?}
    CheckCart -->|Não| EmptyCart[Resposta:<br/>Carrinho vazio]
    CheckCart -->|Sim| CheckState{Estado<br/>da Conversa?}
    
    CheckState -->|welcome| AskDeliveryType[Pergunta:<br/>DELIVERY, RETIRADA,<br/>BALCAO ou MESA?]
    AskDeliveryType --> SaveState1[Salva estado:<br/>perguntando_entrega_retirada]
    
    CheckState -->|perguntando_entrega_retirada| ProcessDelivery[Processa Resposta:<br/>Salva tipo_entrega]
    ProcessDelivery --> CheckType{Tipo de<br/>Entrega?}
    
    CheckType -->|DELIVERY| AddressFlow[Fluxo de Endereço]
    CheckType -->|RETIRADA| PaymentFlow[Fluxo de Pagamento]
    CheckType -->|BALCAO| PaymentFlow
    CheckType -->|MESA| AskTable[Pergunta Número<br/>da Mesa]
    
    AskTable --> SaveTable[Salva mesa_id]
    SaveTable --> PaymentFlow
    
    AddressFlow --> CheckAddress{Cliente tem<br/>endereços salvos?}
    CheckAddress -->|Sim| ListAddresses[Lista Endereços<br/>Salvos]
    CheckAddress -->|Não| SearchGoogle[Busca no Google Maps<br/>via API]
    
    ListAddresses --> SelectAddress[Cliente seleciona<br/>ou informa novo]
    SearchGoogle --> ShowResults[Mostra Resultados<br/>do Google]
    ShowResults --> SelectGoogle[Cliente seleciona<br/>endereço]
    
    SelectAddress --> AskComplement[Pergunta Complemento<br/>do Endereço]
    SelectGoogle --> AskComplement
    AskComplement --> SaveAddress[Salva endereco_id<br/>ou endereco_snapshot]
    SaveAddress --> PaymentFlow
    
    PaymentFlow --> ListPayments[Lista Meios de<br/>Pagamento Disponíveis]
    ListPayments --> SelectPayment[Cliente seleciona<br/>meio de pagamento]
    SelectPayment --> AskTroco{Tipo de<br/>Pagamento?}
    
    AskTroco -->|Dinheiro| AskTrocoValue[Pergunta Troco Para]
    AskTroco -->|Outros| ConfirmOrder
    
    AskTrocoValue --> SaveTroco[Salva troco_para]
    SaveTroco --> ConfirmOrder[Mostra Resumo<br/>do Pedido]
    
    ConfirmOrder --> WaitConfirm[Aguarda Confirmação<br/>do Cliente]
    WaitConfirm --> CheckConfirm{Cliente<br/>confirmou?}
    
    CheckConfirm -->|Não| CancelOrder[Cancelado]
    CheckConfirm -->|Sim| ConvertCart[Converte Carrinho<br/>para FinalizarPedidoRequest]
    
    ConvertCart --> CallCheckout[Chama API Checkout:<br/>POST /api/cardapio/client/checkout/finalizar]
    CallCheckout --> CheckResult{Resultado<br/>do Checkout?}
    
    CheckResult -->|Sucesso| SaveOrder[Pedido criado<br/>com sucesso]
    CheckResult -->|Erro| ShowError[Mostra Erro<br/>ao Cliente]
    
    SaveOrder --> ClearCart[Limpa Carrinho<br/>Temporário]
    ClearCart --> SendConfirmation[Envia Confirmação<br/>com Número do Pedido]
    SendConfirmation --> End([Fim])
    
    ShowError --> End
    CancelOrder --> End
    EmptyCart --> End
    
    style Start fill:#e1f5ff
    style AddressFlow fill:#fff4e1
    style PaymentFlow fill:#ffe1f5
    style CallCheckout fill:#ffcccc
    style SaveOrder fill:#ccffcc
    style End fill:#ccffcc
```

---

## 🗄️ Estrutura de Dados e Banco de Dados

```mermaid
erDiagram
    CHATBOT_CONFIG ||--o{ CONVERSATIONS : "tem"
    CONVERSATIONS ||--o{ MESSAGES : "tem"
    CARRINHO_TEMPORARIO ||--o{ CARRINHO_ITEM : "tem"
    CARRINHO_ITEM ||--o{ CARRINHO_ITEM_COMPLEMENTO : "tem"
    CARRINHO_ITEM_COMPLEMENTO ||--o{ CARRINHO_ITEM_COMPLEMENTO_ADICIONAL : "tem"
    
    EMPRESAS ||--o{ CHATBOT_CONFIG : "tem"
    EMPRESAS ||--o{ CARRINHO_TEMPORARIO : "tem"
    CLIENTES ||--o{ CARRINHO_TEMPORARIO : "tem"
    ENDERECOS ||--o{ CARRINHO_TEMPORARIO : "tem"
    MEIOS_PAGAMENTO ||--o{ CARRINHO_TEMPORARIO : "tem"
    MESAS ||--o{ CARRINHO_TEMPORARIO : "tem"
    
    CHATBOT_CONFIG {
        int id PK
        int empresa_id FK
        string nome
        string personalidade
        boolean aceita_pedidos_whatsapp
        string mensagem_boas_vindas
        string mensagem_redirecionamento
        boolean ativo
        datetime created_at
        datetime updated_at
    }
    
    CONVERSATIONS {
        int id PK
        string session_id
        string user_id
        string prompt_key
        string model
        string contact_name
        int empresa_id FK
        jsonb metadata
        datetime created_at
        datetime updated_at
    }
    
    MESSAGES {
        int id PK
        int conversation_id FK
        string role
        string content
        string whatsapp_message_id
        datetime created_at
    }
    
    CARRINHO_TEMPORARIO {
        int id PK
        string user_id
        int empresa_id FK
        enum tipo_entrega
        int mesa_id FK
        int cliente_id FK
        int endereco_id FK
        int meio_pagamento_id FK
        int cupom_id FK
        decimal subtotal
        decimal desconto
        decimal taxa_entrega
        decimal taxa_servico
        decimal valor_total
        decimal troco_para
        jsonb endereco_snapshot
        datetime created_at
        datetime updated_at
        datetime expires_at
    }
    
    CARRINHO_ITEM {
        int id PK
        int carrinho_id FK
        string produto_cod_barras
        int receita_id
        int combo_id
        int quantidade
        decimal preco_unitario
        decimal preco_total
        string observacao
        string produto_descricao_snapshot
        string produto_imagem_snapshot
    }
    
    CARRINHO_ITEM_COMPLEMENTO {
        int id PK
        int carrinho_item_id FK
        int complemento_id
        decimal total
    }
    
    CARRINHO_ITEM_COMPLEMENTO_ADICIONAL {
        int id PK
        int item_complemento_id FK
        int adicional_id
        int quantidade
        decimal preco_unitario
        decimal total
    }
```

---

## 🔧 Componentes Principais

### 1. **Router (`router.py`)**
- Recebe webhooks do WhatsApp (360Dialog/Meta)
- Processa mensagens em background
- Gerencia conversas e histórico
- Endpoints administrativos

### 2. **GroqSalesHandler (`groq_sales_handler.py`)**
- Integração com API Groq (LLaMA 3.1)
- Function Calling para ações do chatbot
- Gerenciamento de estados da conversa
- Processamento de intenções do usuário

### 3. **CarrinhoService (`service_carrinho.py`)**
- Gerencia carrinho temporário
- Adiciona/remove/atualiza itens
- Calcula totais e complementos
- Converte para formato de checkout

### 4. **ChatbotConfigService (`service_chatbot_config.py`)**
- CRUD de configurações do chatbot
- Validação de regras de negócio
- Gerenciamento por empresa

### 5. **AddressService (`address_service.py`)**
- Integração com Google Maps API
- Gerenciamento de endereços salvos
- Validação de endereços

### 6. **IngredientesService (`ingredientes_service.py`)**
- Detecção de remoção de ingredientes
- Detecção de adicionais extras
- Personalização de produtos

---

## 📡 APIs e Integrações Externas

```mermaid
graph LR
    WhatsApp[WhatsApp Business API<br/>via 360Dialog] --> Webhook[Webhook Endpoint<br/>/api/chatbot/webhook]
    Webhook --> Backend[Backend FastAPI]
    
    Backend --> GroqAPI[Groq API<br/>LLaMA 3.1]
    Backend --> GoogleMaps[Google Maps API<br/>Geocoding/Places]
    Backend --> WhatsAppAPI[WhatsApp API<br/>Envio de Mensagens]
    
    Backend --> Database[(PostgreSQL<br/>Schema: chatbot)]
    Backend --> CheckoutAPI[Checkout API<br/>/api/cardapio/client/checkout]
    
    style WhatsApp fill:#25D366
    style GroqAPI fill:#FF6B6B
    style GoogleMaps fill:#4285F4
    style Database fill:#336791
    style CheckoutAPI fill:#4ECDC4
```

---

## 🔄 Estados da Conversa

```mermaid
stateDiagram-v2
    [*] --> welcome: Primeira mensagem
    welcome --> conversando: Conversa livre
    welcome --> aguardando_pedido: Cliente quer pedir
    
    conversando --> aguardando_pedido: Detecta intenção de pedido
    conversando --> informando_produto: Pergunta sobre produto
    
    aguardando_pedido --> aguardando_quantidade: Produto identificado
    aguardando_quantidade --> aguardando_mais_itens: Quantidade confirmada
    
    aguardando_mais_itens --> perguntando_entrega_retirada: Cliente finaliza carrinho
    perguntando_entrega_retirada --> verificando_endereco: DELIVERY escolhido
    perguntando_entrega_retirada --> coletando_pagamento: RETIRADA/BALCAO/MESA
    
    verificando_endereco --> listando_enderecos: Tem endereços salvos
    verificando_endereco --> buscando_endereco_google: Sem endereços
    listando_enderecos --> coletando_complemento: Endereço selecionado
    buscando_endereco_google --> selecionando_endereco_google: Resultados encontrados
    selecionando_endereco_google --> coletando_complemento: Endereço escolhido
    coletando_complemento --> coletando_pagamento: Complemento informado
    
    coletando_pagamento --> confirmando_pedido: Pagamento selecionado
    confirmando_pedido --> order_placed: Pedido confirmado
    confirmando_pedido --> aguardando_mais_itens: Cliente cancela
    
    order_placed --> [*]: Pedido finalizado
```

---

## 🎯 Function Calling - Funções Disponíveis para a IA

| Função | Descrição | Quando Usar |
|--------|-----------|-------------|
| `adicionar_produto` | Adiciona produto ao carrinho | Cliente pede produto específico |
| `finalizar_pedido` | Inicia fluxo de checkout | Cliente quer fechar pedido |
| `ver_cardapio` | Lista produtos disponíveis | Cliente pede ver cardápio |
| `ver_carrinho` | Mostra itens do carrinho | Cliente quer ver pedido atual |
| `remover_produto` | Remove item do carrinho | Cliente quer cancelar item |
| `informar_sobre_produto` | Informa sobre produto | Cliente pergunta sobre produto |
| `personalizar_produto` | Personaliza produto no carrinho | Cliente quer modificar item |
| `ver_adicionais` | Lista adicionais disponíveis | Cliente pergunta sobre extras |
| `ver_combos` | Lista combos disponíveis | Cliente pergunta sobre combos |
| `conversar` | Resposta conversacional | Qualquer outra situação |

---

## 📝 Notas Importantes

1. **Webhook deve retornar 200 OK imediatamente** (requisito da 360Dialog)
2. **Processamento em background** para não violar limite de 5 segundos
3. **Carrinho temporário expira em 24 horas** (campo `expires_at`)
4. **Duplicação de mensagens** é evitada usando `whatsapp_message_id`
5. **Configuração por empresa** permite diferentes comportamentos
6. **Function Calling** permite que a IA execute ações no sistema
7. **Estados da conversa** são salvos no campo `metadata` da tabela `conversations`

---

## 🔐 Segurança e Validações

- ✅ Validação de token JWT em endpoints administrativos
- ✅ Verificação de status global do bot antes de processar
- ✅ Validação de empresa_id em todas as operações
- ✅ Verificação de duplicação de mensagens
- ✅ Validação de dados antes de criar/atualizar carrinho
- ✅ Verificação de produtos disponíveis antes de adicionar
- ✅ Cálculo seguro de valores monetários (Decimal)

---

## 📊 Métricas e Monitoramento

- Logs de todas as operações importantes
- Histórico completo de conversas no banco
- Rastreamento de mensagens via `whatsapp_message_id`
- Timestamps em todas as tabelas para auditoria
- Campo `expires_at` para limpeza automática de carrinhos abandonados

---

**Última atualização:** 2024
**Versão do Sistema:** 2.0
