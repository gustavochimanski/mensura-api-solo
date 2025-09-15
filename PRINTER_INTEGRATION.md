# Integração com Printer API

Este documento descreve como usar a integração entre a API Mensura e a Printer API para impressão automática de pedidos.

## Visão Geral

A integração permite:
- Listar pedidos pendentes de impressão (status 'I')
- Imprimir pedidos individualmente via Printer API
- Imprimir todos os pedidos pendentes de uma empresa
- Marcar pedidos como impressos automaticamente
- Verificar status da Printer API

## Configuração

### Variáveis de Ambiente

Adicione as seguintes variáveis ao seu arquivo `.env`:

```env
# URL da Printer API
PRINTER_API_URL=http://localhost:8000

# Timeout para requisições (segundos)
PRINTER_TIMEOUT=30

# Número máximo de pedidos para imprimir por vez
MAX_PEDIDOS_IMPRESSAO=10

# Configurações de retry (opcional)
PRINTER_RETRY_ATTEMPTS=3
PRINTER_RETRY_DELAY=2
```

### Iniciando a Printer API

1. Navegue até o diretório `printer_api`:
```bash
cd printer_api
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Execute a Printer API:
```bash
python src/main.py
```

A Printer API estará disponível em `http://localhost:8000`

## Endpoints da Integração

### 1. Listar Pedidos Pendentes de Impressão

**GET** `/api/delivery/pedidos/impressao/pendentes`

**Parâmetros:**
- `empresa_id` (obrigatório): ID da empresa

**Resposta:**
```json
[
  {
    "id": 123,
    "status": "I",
    "cliente_id": 456,
    "valor_total": 35.90,
    "data_criacao": "2024-01-15T14:30:00",
    "telefone_cliente": "11999999999",
    "nome_cliente": "João Silva",
    "endereco_cliente": "Rua A, 123, Centro",
    "meio_pagamento_descricao": "Dinheiro",
    "observacao_geral": "Sem cebola",
    "meio_pagamento_id": 1
  }
]
```

### 2. Imprimir Pedido Específico

**POST** `/api/delivery/pedidos/{pedido_id}/imprimir`

**Resposta:**
```json
{
  "sucesso": true,
  "mensagem": "Pedido 123 impresso com sucesso",
  "numero_pedido": 123
}
```

### 3. Imprimir Todos os Pendentes

**POST** `/api/delivery/pedidos/impressao/imprimir-todos`

**Parâmetros:**
- `empresa_id` (obrigatório): ID da empresa
- `limite` (opcional): Número máximo de pedidos (padrão: 10)

**Resposta:**
```json
{
  "sucesso": true,
  "mensagem": "Processados 5 pedidos: 5 sucessos, 0 falhas",
  "pedidos_impressos": 5,
  "pedidos_falharam": 0,
  "detalhes": [
    {
      "pedido_id": 123,
      "sucesso": true,
      "mensagem": "Pedido 123 impresso com sucesso"
    }
  ]
}
```

### 4. Marcar Pedido como Impresso (Manual)

**PUT** `/api/delivery/pedidos/{pedido_id}/marcar-impresso`

**Resposta:**
```json
{
  "id": 123,
  "status": "R",
  "cliente_id": 456,
  // ... outros campos do pedido
}
```

### 5. Verificar Status da Printer API

**GET** `/api/delivery/pedidos/impressao/status-printer`

**Resposta:**
```json
{
  "conectado": true,
  "mensagem": "Printer API funcionando"
}
```

## Fluxo de Trabalho

### Fluxo Automático

1. **Pedido criado** → Status 'I' (Pendente de Impressão)
2. **Chamar endpoint de impressão** → Envia para Printer API
3. **Printer API processa** → Imprime o cupom
4. **Sucesso** → Status muda para 'R' (Em Preparo)
5. **Falha** → Status permanece 'I' para nova tentativa

### Fluxo Manual

1. **Listar pendentes** → Ver pedidos com status 'I'
2. **Imprimir individual** → Escolher pedido específico
3. **Marcar como impresso** → Se impressão foi feita manualmente

## Exemplos de Uso

### Python (httpx)

```python
import httpx

# Listar pendentes
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8001/api/delivery/pedidos/impressao/pendentes",
        params={"empresa_id": 1}
    )
    pedidos = response.json()

# Imprimir pedido específico
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8001/api/delivery/pedidos/123/imprimir"
    )
    resultado = response.json()

# Imprimir todos os pendentes
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8001/api/delivery/pedidos/impressao/imprimir-todos",
        params={"empresa_id": 1, "limite": 5}
    )
    resultado = response.json()
```

### cURL

```bash
# Listar pendentes
curl -X GET "http://localhost:8001/api/delivery/pedidos/impressao/pendentes?empresa_id=1"

# Imprimir pedido específico
curl -X POST "http://localhost:8001/api/delivery/pedidos/123/imprimir"

# Imprimir todos os pendentes
curl -X POST "http://localhost:8001/api/delivery/pedidos/impressao/imprimir-todos?empresa_id=1&limite=5"

# Verificar status da printer
curl -X GET "http://localhost:8001/api/delivery/pedidos/impressao/status-printer"
```

## Testando a Integração

Execute o script de teste:

```bash
python test_printer_integration.py
```

O script irá:
1. Verificar se a Printer API está funcionando
2. Testar impressão de um pedido de exemplo
3. Testar os endpoints da API Mensura

## Solução de Problemas

### Printer API não acessível

1. Verifique se a Printer API está rodando em `http://localhost:8000`
2. Confirme se a variável `PRINTER_API_URL` está correta
3. Teste a conectividade: `curl http://localhost:8000/health`

### Erro de impressão

1. Verifique se a impressora está conectada e funcionando
2. Confirme as configurações da impressora na Printer API
3. Verifique os logs da Printer API para detalhes do erro

### Pedidos não mudam de status

1. Verifique se o pedido tem status 'I' antes de imprimir
2. Confirme se a transação foi commitada no banco
3. Verifique os logs da API Mensura para erros

## Logs

Os logs da integração podem ser encontrados em:
- API Mensura: `app/logs/app.log`
- Printer API: Console onde foi executada

Procure por mensagens com `[PrinterIntegration]` ou `[PrinterClient]`.
