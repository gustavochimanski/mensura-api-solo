# Sistema de Monitoramento e Logs

Sistema de monitoramento implementado com Prometheus e visualização de logs via web.

## Funcionalidades

### 1. Métricas Prometheus

O sistema coleta automaticamente métricas de:
- **Requisições HTTP**: Total de requisições, duração, status codes
- **Erros HTTP**: Contagem de erros por status code
- **Conexões ativas**: Número de conexões simultâneas
- **Logs**: Contagem de mensagens de log por nível (INFO, ERROR, WARNING, DEBUG)

### 2. Visualização de Logs

Interface web para visualizar logs da aplicação com:
- Filtros por nível (INFO, ERROR, WARNING, DEBUG)
- Busca por texto
- Auto-refresh a cada 5 segundos
- Visualização colorida por nível de log

## Endpoints

### Métricas Prometheus (Público - Sem autenticação)

```
GET /api/monitoring/metrics
```

Retorna as métricas no formato Prometheus. Pode ser usado pelo Prometheus Server para coletar métricas.

**Exemplo de uso:**
```bash
curl http://localhost:8000/api/monitoring/metrics
```

### Visualização de Logs (Requer autenticação)

```
GET /api/monitoring/logs
```

Interface web para visualizar logs.

**Parâmetros:**
- `lines` (opcional): Número de linhas para exibir (padrão: 100, máximo: 1000)
- `level` (opcional): Filtrar por nível (INFO, ERROR, WARNING, DEBUG)
- `search` (opcional): Buscar texto nas linhas

**Exemplos:**
- Ver últimas 200 linhas: `/api/monitoring/logs?lines=200`
- Ver apenas erros: `/api/monitoring/logs?level=ERROR`
- Buscar por "database": `/api/monitoring/logs?search=database`
- Combinar filtros: `/api/monitoring/logs?lines=500&level=ERROR&search=timeout`

### Logs em JSON (Requer autenticação)

```
GET /api/monitoring/logs/json
```

Retorna os logs em formato JSON para integração com outras ferramentas.

**Parâmetros:** Mesmos do endpoint `/logs`

## Configuração do Prometheus

Para configurar o Prometheus Server para coletar métricas, adicione no `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'mensura-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/monitoring/metrics'
```

## Métricas Disponíveis

### http_requests_total
Contador total de requisições HTTP por método, endpoint e status code.

**Labels:**
- `method`: Método HTTP (GET, POST, etc.)
- `endpoint`: Endpoint normalizado (ex: `/api/users/{id}`)
- `status_code`: Código de status HTTP

### http_request_duration_seconds
Histograma da duração das requisições HTTP em segundos.

**Labels:**
- `method`: Método HTTP
- `endpoint`: Endpoint normalizado

**Buckets:** 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0

### http_errors_total
Contador de erros HTTP (status codes 4xx e 5xx).

**Labels:**
- `method`: Método HTTP
- `endpoint`: Endpoint normalizado
- `status_code`: Código de status HTTP

### active_connections
Gauge com o número de conexões ativas no momento.

### log_messages_total
Contador de mensagens de log por nível.

**Labels:**
- `level`: Nível do log (INFO, ERROR, WARNING, DEBUG)

## Exemplos de Queries Prometheus

### Taxa de requisições por segundo
```promql
rate(http_requests_total[5m])
```

### Taxa de erros por segundo
```promql
rate(http_errors_total[5m])
```

### Percentil 95 da duração das requisições
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Total de logs de erro
```promql
log_messages_total{level="ERROR"}
```

## Segurança

- **Métricas**: Públicas (sem autenticação) - necessário para o Prometheus coletar
- **Logs**: Requerem autenticação JWT (admin)

## Notas

- Os endpoints são normalizados para evitar alta cardinalidade nas métricas (ex: `/api/users/123` vira `/api/users/{id}`)
- O arquivo de log está localizado em `app/logs/app.log`
- O sistema suporta rotação automática de logs (máximo 5MB por arquivo, 3 backups)

