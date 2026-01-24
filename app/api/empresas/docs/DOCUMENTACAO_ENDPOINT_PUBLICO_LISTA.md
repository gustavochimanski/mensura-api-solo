# Documentação - Endpoint Público de Lista de Empresas

## 📋 Visão Geral

Este documento descreve o endpoint público `/api/empresas/public/emp/lista` que permite listar empresas ou buscar uma empresa específica por ID.

---

## 🔗 Endpoint

### GET `/api/empresas/public/emp/lista`

**Autenticação**: Não requerida (endpoint público)

**Descrição**: Retorna empresas disponíveis para seleção pública. Quando `empresa_id` é fornecido, retorna um objeto único com informações completas (incluindo logo e horário de funcionamento). Caso contrário, retorna uma lista de empresas.

---

## 📥 Parâmetros de Query

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | `number` | Não | ID da empresa. Quando fornecido, retorna um objeto único ao invés de lista |
| `q` | `string` | Não | Termo de busca por nome ou slug |
| `cidade` | `string` | Não | Filtrar por cidade |
| `estado` | `string` | Não | Filtrar por estado (sigla, ex: "PR", "SP") |
| `limit` | `number` | Não | Limite máximo de empresas retornadas (padrão: 100, máximo: 500) |

---

## 📤 Respostas

### Caso 1: Com `empresa_id` (objeto único)

**URL**: `GET /api/empresas/public/emp/lista?empresa_id=1`

**Status**: `200 OK`

**Response Body** (objeto único):

```json
{
  "id": 1,
  "nome": "Xmanski - São braz",
  "logo": "https://minio.example.com/bucket/logo-1.jpg",
  "bairro": "Santo Inácio",
  "cidade": "Curitiba",
  "estado": "PR",
  "distancia_km": null,
  "tema": "oklch(0.55 0.22 25)",
  "redireciona_home": false,
  "redireciona_home_para": null,
  "horarios_funcionamento": [
    {
      "dia_semana": 1,
      "intervalos": [
        {
          "inicio": "08:00",
          "fim": "12:00"
        },
        {
          "inicio": "14:00",
          "fim": "18:00"
        }
      ]
    },
    {
      "dia_semana": 2,
      "intervalos": [
        {
          "inicio": "08:00",
          "fim": "12:00"
        },
        {
          "inicio": "14:00",
          "fim": "18:00"
        }
      ]
    }
  ]
}
```

**Estrutura TypeScript**:

```typescript
interface EmpresaPublicListItem {
  id: number;
  nome: string;
  logo: string | null;
  bairro: string | null;
  cidade: string | null;
  estado: string | null;
  distancia_km: number | null;
  tema: string | null;
  redireciona_home: boolean;
  redireciona_home_para: string | null;
  horarios_funcionamento: HorarioDia[] | null;
}

interface HorarioDia {
  dia_semana: number; // 0=domingo, 1=segunda, ..., 6=sábado
  intervalos: HorarioIntervalo[];
}

interface HorarioIntervalo {
  inicio: string; // Formato: "HH:MM" (ex: "08:00")
  fim: string;    // Formato: "HH:MM" (ex: "18:00")
}
```

**Status**: `404 Not Found` (quando empresa não existe)

```json
{
  "detail": "Empresa não encontrada"
}
```

---

### Caso 2: Sem `empresa_id` (lista de empresas)

**URL**: `GET /api/empresas/public/emp/lista`

**Status**: `200 OK`

**Response Body** (array):

```json
[
  {
    "id": 1,
    "nome": "Xmanski - São braz",
    "logo": "https://minio.example.com/bucket/logo-1.jpg",
    "bairro": "Santo Inácio",
    "cidade": "Curitiba",
    "estado": "PR",
    "distancia_km": null,
    "tema": "oklch(0.55 0.22 25)",
    "redireciona_home": false,
    "redireciona_home_para": null,
    "horarios_funcionamento": null
  },
  {
    "id": 2,
    "nome": "Restaurante Exemplo",
    "logo": null,
    "bairro": "Centro",
    "cidade": "São Paulo",
    "estado": "SP",
    "distancia_km": null,
    "tema": "padrao",
    "redireciona_home": false,
    "redireciona_home_para": null,
    "horarios_funcionamento": null
  }
]
```

**Nota**: Na lista, `horarios_funcionamento` sempre será `null` para otimizar a resposta. Use `empresa_id` quando precisar dos horários.

---

## 🔍 Exemplos de Uso

### Exemplo 1: Buscar empresa específica por ID

```typescript
// Buscar empresa com ID 1 (retorna objeto único)
const response = await fetch('https://api.example.com/api/empresas/public/emp/lista?empresa_id=1');
const empresa = await response.json();

console.log(empresa.nome); // "Xmanski - São braz"
console.log(empresa.logo); // URL da logo ou null
console.log(empresa.horarios_funcionamento); // Array com horários ou null
```

### Exemplo 2: Listar todas as empresas

```typescript
// Listar todas as empresas (retorna array)
const response = await fetch('https://api.example.com/api/empresas/public/emp/lista');
const empresas = await response.json();

empresas.forEach(empresa => {
  console.log(`${empresa.id}: ${empresa.nome} - ${empresa.cidade}/${empresa.estado}`);
});
```

### Exemplo 3: Buscar por cidade

```typescript
// Filtrar empresas por cidade
const response = await fetch('https://api.example.com/api/empresas/public/emp/lista?cidade=Curitiba');
const empresas = await response.json();
```

### Exemplo 4: Buscar por termo

```typescript
// Buscar empresas por nome ou slug
const response = await fetch('https://api.example.com/api/empresas/public/emp/lista?q=xmanski');
const empresas = await response.json();
```

### Exemplo 5: Combinar filtros

```typescript
// Buscar empresas em Curitiba/PR com limite de 10
const response = await fetch(
  'https://api.example.com/api/empresas/public/emp/lista?cidade=Curitiba&estado=PR&limit=10'
);
const empresas = await response.json();
```

---

## 📝 Tratamento de Horários de Funcionamento

### Estrutura dos Horários

- `dia_semana`: Número de 0 a 6
  - `0` = Domingo
  - `1` = Segunda-feira
  - `2` = Terça-feira
  - `3` = Quarta-feira
  - `4` = Quinta-feira
  - `5` = Sexta-feira
  - `6` = Sábado

- `intervalos`: Array de intervalos de horário
  - `inicio`: String no formato "HH:MM" (ex: "08:00")
  - `fim`: String no formato "HH:MM" (ex: "18:00")

### Exemplo de Processamento no Frontend

```typescript
interface HorarioDia {
  dia_semana: number;
  intervalos: Array<{ inicio: string; fim: string }>;
}

function formatarHorarios(horarios: HorarioDia[] | null): string {
  if (!horarios || horarios.length === 0) {
    return "Horários não disponíveis";
  }

  const diasSemana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
  
  return horarios.map(dia => {
    const nomeDia = diasSemana[dia.dia_semana];
    const intervalos = dia.intervalos
      .map(intervalo => `${intervalo.inicio} - ${intervalo.fim}`)
      .join(", ");
    return `${nomeDia}: ${intervalos}`;
  }).join(" | ");
}

// Uso
const empresa = await buscarEmpresa(1);
if (empresa.horarios_funcionamento) {
  console.log(formatarHorarios(empresa.horarios_funcionamento));
  // Exemplo: "Seg: 08:00 - 12:00, 14:00 - 18:00 | Ter: 08:00 - 12:00, 14:00 - 18:00"
}
```

---

## ⚠️ Tratamento de Erros

### 404 - Empresa não encontrada

```typescript
try {
  const response = await fetch('https://api.example.com/api/empresas/public/emp/lista?empresa_id=999');
  
  if (response.status === 404) {
    const error = await response.json();
    console.error(error.detail); // "Empresa não encontrada"
  }
} catch (error) {
  console.error('Erro na requisição:', error);
}
```

### 422 - Erro de validação

Se parâmetros inválidos forem enviados (ex: `limit` maior que 500), o FastAPI retornará erro 422.

---

## 🎯 Casos de Uso Recomendados

1. **Buscar empresa específica com detalhes completos**: Use `?empresa_id=X` para obter logo e horários
2. **Listar empresas para seleção**: Use sem `empresa_id` para obter lista otimizada
3. **Filtrar por localização**: Combine `cidade` e `estado` para buscar empresas em uma região
4. **Busca por nome**: Use `q` para buscar empresas por nome ou slug

---

## 📌 Notas Importantes

- **Logo**: A URL da logo pode ser `null` se a empresa não tiver logo cadastrada
- **Horários**: `horarios_funcionamento` só é retornado quando `empresa_id` é fornecido (objeto único)
- **Timezone**: O timezone da empresa não é retornado neste endpoint. Use o endpoint `/api/empresas/public/emp/?empresa_id=X` se precisar do timezone
- **Performance**: Para listas grandes, sempre use o parâmetro `limit` para evitar respostas muito grandes

---

## 🔗 Endpoints Relacionados

- `GET /api/empresas/public/emp/?empresa_id=X` - Retorna dados completos da empresa (incluindo timezone, endereço completo, etc.)
