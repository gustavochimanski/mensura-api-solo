# Documentação Pública - API de Complementos

## 📋 Visão Geral

Esta documentação é destinada a desenvolvedores que consomem a API pública de complementos. Ela explica como buscar complementos de produtos, receitas e combos, e como interpretar as configurações retornadas.

## 🔑 Conceito Principal

**IMPORTANTE:** As configurações de complementos (`obrigatorio`, `quantitativo`, `minimo_itens`, `maximo_itens`) são definidas **na vinculação** entre o complemento e o produto/receita/combo. Isso significa que o mesmo complemento pode ter comportamentos diferentes dependendo de onde está sendo usado.

## 📡 Endpoint Público

### Listar Complementos

**Endpoint:** `GET /api/catalogo/public/complementos`

**Autenticação:** Não requerida (endpoint público)

**Parâmetros de Query (todos obrigatórios):**

| Parâmetro | Tipo | Descrição | Valores Aceitos |
|-----------|------|-----------|-----------------|
| `tipo` | string | Tipo do item | `produto`, `combo`, `receita` |
| `identificador` | string | Identificador do item | Código de barras (produto) ou ID numérico (combo/receita) |
| `tipo_pedido` | string | Tipo de pedido | `balcao`, `mesa`, `delivery` |

**Parâmetros Opcionais:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `apenas_ativos` | boolean | `true` | Se `true`, retorna apenas complementos ativos |

## 📥 Exemplos de Requisições

### 1. Buscar Complementos de um Produto

```http
GET /api/catalogo/public/complementos?tipo=produto&identificador=7891234567890&tipo_pedido=delivery&apenas_ativos=true
```

**Resposta:**
```json
[
  {
    "id": 1,
    "empresa_id": 1,
    "nome": "Bebidas",
    "descricao": "Escolha sua bebida",
    "obrigatorio": true,
    "quantitativo": false,
    "minimo_itens": 1,
    "maximo_itens": 1,
    "ordem": 0,
    "ativo": true,
    "adicionais": [
      {
        "id": 10,
        "nome": "Coca-Cola 350ml",
        "descricao": null,
        "imagem": "https://...",
        "preco": 5.50,
        "custo": 2.00,
        "ativo": true,
        "ordem": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": 11,
        "nome": "Pepsi 350ml",
        "descricao": null,
        "imagem": "https://...",
        "preco": 5.50,
        "custo": 2.00,
        "ativo": true,
        "ordem": 1,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": 2,
    "empresa_id": 1,
    "nome": "Adicionais",
    "descricao": "Adicione extras ao seu pedido",
    "obrigatorio": false,
    "quantitativo": true,
    "minimo_itens": null,
    "maximo_itens": 3,
    "ordem": 1,
    "ativo": true,
    "adicionais": [
      {
        "id": 20,
        "nome": "Bacon",
        "descricao": "Fatias crocantes de bacon",
        "imagem": "https://...",
        "preco": 3.00,
        "custo": 1.50,
        "ativo": true,
        "ordem": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### 2. Buscar Complementos de um Combo

```http
GET /api/catalogo/public/complementos?tipo=combo&identificador=5&tipo_pedido=mesa&apenas_ativos=true
```

### 3. Buscar Complementos de uma Receita

```http
GET /api/catalogo/public/complementos?tipo=receita&identificador=10&tipo_pedido=balcao&apenas_ativos=true
```

## 📊 Estrutura da Resposta

### ComplementoResponse

```typescript
interface ComplementoResponse {
  id: number;                    // ID do complemento
  empresa_id: number;            // ID da empresa
  nome: string;                   // Nome do complemento
  descricao: string | null;       // Descrição do complemento
  obrigatorio: boolean;           // Se é obrigatório (da vinculação)
  quantitativo: boolean;         // Se permite quantidade (da vinculação)
  minimo_itens: number | null;    // Quantidade mínima (da vinculação)
  maximo_itens: number | null;    // Quantidade máxima (da vinculação)
  ordem: number;                  // Ordem de exibição (da vinculação)
  ativo: boolean;                // Se o complemento está ativo
  adicionais: AdicionalResponse[]; // Lista de adicionais disponíveis
  created_at: string;            // Data de criação (ISO 8601)
  updated_at: string;            // Data de atualização (ISO 8601)
}
```

### AdicionalResponse

```typescript
interface AdicionalResponse {
  id: number;              // ID do adicional
  nome: string;            // Nome do adicional
  descricao: string | null; // Descrição do adicional
  imagem: string | null;    // URL da imagem
  preco: number;           // Preço do adicional
  custo: number;           // Custo interno (pode não ser relevante para frontend)
  ativo: boolean;          // Se o adicional está ativo
  ordem: number;           // Ordem de exibição
  created_at: string;      // Data de criação (ISO 8601)
  updated_at: string;      // Data de atualização (ISO 8601)
}
```

## 🎯 Interpretando as Configurações

### Campo `obrigatorio`

- **`true`**: O cliente **DEVE** escolher pelo menos um item deste complemento
- **`false`**: O complemento é opcional

**Exemplo de uso:**
```javascript
if (complemento.obrigatorio) {
  // Exibir como obrigatório
  // Validar que pelo menos um item foi selecionado
}
```

### Campo `quantitativo`

- **`true`**: Permite que o cliente escolha múltiplos itens e defina quantidades (ex: "2x bacon")
- **`false`**: Apenas uma escolha é permitida (radio button)

**Exemplo de uso:**
```javascript
if (complemento.quantitativo) {
  // Exibir com controles de quantidade
  // Permitir múltipla seleção
} else {
  // Exibir como radio buttons (escolha única)
}
```

### Campo `minimo_itens`

- **`null`**: Sem quantidade mínima
- **Número**: Quantidade mínima de itens que devem ser selecionados

**Exemplo de uso:**
```javascript
if (complemento.minimo_itens !== null && complemento.minimo_itens > 0) {
  // Exibir mensagem: "Escolha pelo menos {minimo_itens} item(ns)"
  // Validar quantidade mínima
}
```

### Campo `maximo_itens`

- **`null`**: Sem limite máximo
- **Número**: Quantidade máxima de itens que podem ser selecionados

**Exemplo de uso:**
```javascript
if (complemento.maximo_itens !== null) {
  // Exibir mensagem: "Escolha no máximo {maximo_itens} item(ns)"
  // Validar quantidade máxima
  // Limitar seleção no frontend
}
```

## 💡 Exemplos Práticos de Uso

### Exemplo 1: Complemento Obrigatório com Escolha Única

```json
{
  "id": 1,
  "nome": "Tamanho",
  "obrigatorio": true,
  "quantitativo": false,
  "minimo_itens": 1,
  "maximo_itens": 1
}
```

**Interface sugerida:**
- Radio buttons (escolha única)
- Marcação visual de obrigatório
- Validação: deve ter exatamente 1 item selecionado

### Exemplo 2: Complemento Opcional com Múltipla Escolha e Limite

```json
{
  "id": 2,
  "nome": "Adicionais",
  "obrigatorio": false,
  "quantitativo": true,
  "minimo_itens": null,
  "maximo_itens": 3
}
```

**Interface sugerida:**
- Checkboxes com controles de quantidade
- Mensagem: "Escolha até 3 itens"
- Validação: máximo de 3 itens selecionados

### Exemplo 3: Complemento Obrigatório com Faixa de Quantidade

```json
{
  "id": 3,
  "nome": "Molhos",
  "obrigatorio": true,
  "quantitativo": true,
  "minimo_itens": 2,
  "maximo_itens": 4
}
```

**Interface sugerida:**
- Checkboxes com controles de quantidade
- Mensagem: "Escolha entre 2 e 4 molhos (obrigatório)"
- Validação: entre 2 e 4 itens selecionados

## 🔧 Implementação no Frontend

### Exemplo de Componente React

```typescript
interface Complemento {
  id: number;
  nome: string;
  obrigatorio: boolean;
  quantitativo: boolean;
  minimo_itens: number | null;
  maximo_itens: number | null;
  adicionais: Adicional[];
}

interface Adicional {
  id: number;
  nome: string;
  preco: number;
  imagem: string | null;
}

function ComplementoSelector({ complemento }: { complemento: Complemento }) {
  const [selecionados, setSelecionados] = useState<Map<number, number>>(new Map());
  
  const totalSelecionado = Array.from(selecionados.values())
    .reduce((sum, qtd) => sum + qtd, 0);
  
  // Validação
  const erros: string[] = [];
  
  if (complemento.obrigatorio && totalSelecionado === 0) {
    erros.push(`${complemento.nome} é obrigatório`);
  }
  
  if (complemento.minimo_itens && totalSelecionado < complemento.minimo_itens) {
    erros.push(`Escolha pelo menos ${complemento.minimo_itens} item(ns)`);
  }
  
  if (complemento.maximo_itens && totalSelecionado > complemento.maximo_itens) {
    erros.push(`Escolha no máximo ${complemento.maximo_itens} item(ns)`);
  }
  
  return (
    <div className="complemento">
      <h3>
        {complemento.nome}
        {complemento.obrigatorio && <span className="obrigatorio">*</span>}
      </h3>
      
      {complemento.minimo_itens && complemento.maximo_itens && (
        <p className="limite">
          Escolha entre {complemento.minimo_itens} e {complemento.maximo_itens} itens
        </p>
      )}
      {complemento.maximo_itens && !complemento.minimo_itens && (
        <p className="limite">
          Escolha até {complemento.maximo_itens} itens
        </p>
      )}
      
      {erros.length > 0 && (
        <div className="erros">
          {erros.map((erro, idx) => (
            <span key={idx} className="erro">{erro}</span>
          ))}
        </div>
      )}
      
      {complemento.quantitativo ? (
        // Múltipla escolha com quantidade
        complemento.adicionais.map(adicional => (
          <div key={adicional.id} className="adicional-quantitativo">
            <input
              type="checkbox"
              checked={selecionados.has(adicional.id)}
              onChange={(e) => {
                const novos = new Map(selecionados);
                if (e.target.checked) {
                  novos.set(adicional.id, 1);
                } else {
                  novos.delete(adicional.id);
                }
                setSelecionados(novos);
              }}
            />
            <label>{adicional.nome} - R$ {adicional.preco.toFixed(2)}</label>
            {selecionados.has(adicional.id) && (
              <input
                type="number"
                min={1}
                max={complemento.maximo_itens || undefined}
                value={selecionados.get(adicional.id) || 1}
                onChange={(e) => {
                  const novos = new Map(selecionados);
                  novos.set(adicional.id, parseInt(e.target.value) || 1);
                  setSelecionados(novos);
                }}
              />
            )}
          </div>
        ))
      ) : (
        // Escolha única (radio buttons)
        complemento.adicionais.map(adicional => (
          <div key={adicional.id} className="adicional-unico">
            <input
              type="radio"
              name={`complemento-${complemento.id}`}
              value={adicional.id}
              checked={selecionados.has(adicional.id)}
              onChange={() => {
                setSelecionados(new Map([[adicional.id, 1]]));
              }}
            />
            <label>{adicional.nome} - R$ {adicional.preco.toFixed(2)}</label>
          </div>
        ))
      )}
    </div>
  );
}
```

### Exemplo de Validação Antes de Enviar Pedido

```typescript
function validarComplementos(
  complementos: Complemento[],
  selecoes: Map<number, Map<number, number>> // complemento_id -> { adicional_id -> quantidade }
): string[] {
  const erros: string[] = [];
  
  for (const complemento of complementos) {
    const selecionados = selecoes.get(complemento.id) || new Map();
    const totalSelecionado = Array.from(selecionados.values())
      .reduce((sum, qtd) => sum + qtd, 0);
    
    // Valida obrigatório
    if (complemento.obrigatorio && totalSelecionado === 0) {
      erros.push(`${complemento.nome} é obrigatório`);
    }
    
    // Valida mínimo
    if (complemento.minimo_itens && totalSelecionado < complemento.minimo_itens) {
      erros.push(
        `${complemento.nome}: escolha pelo menos ${complemento.minimo_itens} item(ns). ` +
        `Você escolheu ${totalSelecionado}.`
      );
    }
    
    // Valida máximo
    if (complemento.maximo_itens && totalSelecionado > complemento.maximo_itens) {
      erros.push(
        `${complemento.nome}: escolha no máximo ${complemento.maximo_itens} item(ns). ` +
        `Você escolheu ${totalSelecionado}.`
      );
    }
  }
  
  return erros;
}
```

## ⚠️ Códigos de Erro

### 400 Bad Request

- `tipo` inválido (não é `produto`, `combo` ou `receita`)
- `identificador` inválido (não é número para combo/receita)
- `tipo_pedido` inválido

**Exemplo:**
```json
{
  "detail": "Para combos, o identificador deve ser um número inteiro. Recebido: abc"
}
```

### 404 Not Found

- Produto/combo/receita não encontrado
- Produto/combo/receita inativo

**Exemplo:**
```json
{
  "detail": "Combo 5 não encontrado ou inativo"
}
```

### 500 Internal Server Error

- Erro interno do servidor

## 📝 Notas Importantes

1. **Configurações da Vinculação**: Todos os campos de configuração (`obrigatorio`, `quantitativo`, `minimo_itens`, `maximo_itens`) vêm da vinculação específica. O mesmo complemento pode ter valores diferentes em produtos diferentes.

2. **Campo `ordem`**: Use este campo para ordenar os complementos na interface. Valores menores aparecem primeiro.

3. **Campo `ativo`**: Sempre verifique se o complemento está ativo antes de exibi-lo. O parâmetro `apenas_ativos=true` já filtra isso, mas é uma boa prática verificar.

4. **Adicionais Inativos**: Mesmo com `apenas_ativos=true`, verifique se cada adicional está ativo antes de exibi-lo.

5. **Preços**: O campo `preco` pode ter valores específicos por complemento (quando o adicional tem preço diferente em cada complemento). Use sempre o valor retornado na resposta.

6. **Imagens**: O campo `imagem` pode ser `null`. Sempre verifique antes de exibir.

## 🔄 Fluxo Recomendado

1. **Buscar complementos** ao carregar o produto/receita/combo
2. **Exibir complementos** ordenados por `ordem`
3. **Aplicar validações** conforme as configurações
4. **Validar antes de enviar** o pedido
5. **Enviar seleções** no formato esperado pela API de pedidos

## 📞 Suporte

Para dúvidas sobre a API, consulte a documentação completa ou entre em contato com a equipe de backend.
