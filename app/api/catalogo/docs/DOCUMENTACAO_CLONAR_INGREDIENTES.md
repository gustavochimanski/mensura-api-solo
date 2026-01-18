# Documentação Frontend - Clonar Ingredientes de Receitas

Esta documentação descreve como o frontend deve implementar a funcionalidade de clonagem de ingredientes de uma receita para outra.

---

## 📋 Visão Geral

O endpoint permite clonar todos os ingredientes de uma receita para outra. Isso é útil quando você deseja criar uma nova receita baseada em uma existente, copiando todos os seus ingredientes de uma vez.

---

## 🔌 1. Endpoint

### URL

```
POST /api/catalogo/admin/receitas/clonar-ingredientes
```

**Exemplos:**
- **Local**: `http://localhost:8000/api/catalogo/admin/receitas/clonar-ingredientes`
- **Produção**: `https://seu-dominio.com/api/catalogo/admin/receitas/clonar-ingredientes`

### Autenticação

Este endpoint requer autenticação de administrador. Inclua o token JWT no header:

```http
Authorization: Bearer {seu_token_jwt}
```

---

## 📨 2. Request Body

### Schema

```typescript
interface ClonarIngredientesRequest {
  receita_origem_id: number;    // ID da receita de origem (de onde serão copiados os ingredientes)
  receita_destino_id: number;   // ID da receita de destino (para onde serão copiados os ingredientes)
}
```

### Exemplo de Request

```json
{
  "receita_origem_id": 10,
  "receita_destino_id": 25
}
```

---

## ✅ 3. Response

### Status Code

- **200 OK**: Clonagem realizada com sucesso

### Schema de Resposta

```typescript
interface ClonarIngredientesResponse {
  receita_origem_id: number;        // ID da receita de origem
  receita_destino_id: number;       // ID da receita de destino
  ingredientes_clonados: number;    // Quantidade de ingredientes clonados
  mensagem: string;                 // Mensagem descritiva da operação
}
```

### Exemplo de Response

```json
{
  "receita_origem_id": 10,
  "receita_destino_id": 25,
  "ingredientes_clonados": 5,
  "mensagem": "5 ingrediente(s) clonado(s) com sucesso"
}
```

---

## ❌ 4. Erros Possíveis

### 400 Bad Request

**Receitas são iguais:**
```json
{
  "detail": "Não é possível clonar ingredientes para a mesma receita"
}
```

**Receita origem sem ingredientes:**
```json
{
  "detail": "A receita origem (ID: 10) não possui ingredientes para clonar"
}
```

### 404 Not Found

**Receita origem não encontrada:**
```json
{
  "detail": "Receita origem (ID: 10) não encontrada"
}
```

**Receita destino não encontrada:**
```json
{
  "detail": "Receita destino (ID: 25) não encontrada"
}
```

### 401 Unauthorized

Token JWT inválido ou ausente:
```json
{
  "detail": "Not authenticated"
}
```

---

## 💻 5. Exemplos de Implementação

### JavaScript/TypeScript com Fetch

```typescript
async function clonarIngredientes(
  receitaOrigemId: number,
  receitaDestinoId: number,
  token: string
): Promise<ClonarIngredientesResponse> {
  const response = await fetch(
    'https://seu-dominio.com/api/catalogo/admin/receitas/clonar-ingredientes',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        receita_origem_id: receitaOrigemId,
        receita_destino_id: receitaDestinoId
      })
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao clonar ingredientes');
  }

  return await response.json();
}

// Uso
try {
  const resultado = await clonarIngredientes(10, 25, token);
  console.log(`✅ ${resultado.mensagem}`);
  console.log(`   ${resultado.ingredientes_clonados} ingrediente(s) clonado(s)`);
} catch (error) {
  console.error('❌ Erro:', error.message);
}
```

### Axios

```typescript
import axios from 'axios';

async function clonarIngredientes(
  receitaOrigemId: number,
  receitaDestinoId: number,
  token: string
): Promise<ClonarIngredientesResponse> {
  try {
    const response = await axios.post(
      '/api/catalogo/admin/receitas/clonar-ingredientes',
      {
        receita_origem_id: receitaOrigemId,
        receita_destino_id: receitaDestinoId
      },
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || 'Erro ao clonar ingredientes');
    }
    throw error;
  }
}
```

### React Hook Example

```typescript
import { useState } from 'react';

function useClonarIngredientes() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clonar = async (receitaOrigemId: number, receitaDestinoId: number) => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        '/api/catalogo/admin/receitas/clonar-ingredientes',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            receita_origem_id: receitaOrigemId,
            receita_destino_id: receitaDestinoId
          })
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao clonar ingredientes');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { clonar, loading, error };
}

// Uso no componente
function ClonarIngredientesComponent() {
  const { clonar, loading, error } = useClonarIngredientes();
  const [receitaOrigemId, setReceitaOrigemId] = useState<number | null>(null);
  const [receitaDestinoId, setReceitaDestinoId] = useState<number | null>(null);

  const handleClonar = async () => {
    if (!receitaOrigemId || !receitaDestinoId) {
      alert('Selecione as receitas de origem e destino');
      return;
    }

    try {
      const resultado = await clonar(receitaOrigemId, receitaDestinoId);
      alert(`✅ ${resultado.mensagem}`);
      // Atualizar lista de ingredientes da receita destino
      // window.location.reload() ou atualizar estado
    } catch (err) {
      alert(`❌ Erro: ${error}`);
    }
  };

  return (
    <div>
      <input
        type="number"
        placeholder="ID Receita Origem"
        value={receitaOrigemId || ''}
        onChange={(e) => setReceitaOrigemId(Number(e.target.value))}
      />
      <input
        type="number"
        placeholder="ID Receita Destino"
        value={receitaDestinoId || ''}
        onChange={(e) => setReceitaDestinoId(Number(e.target.value))}
      />
      <button onClick={handleClonar} disabled={loading}>
        {loading ? 'Clonando...' : 'Clonar Ingredientes'}
      </button>
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
}
```

---

## 📝 6. Observações Importantes

### Duplicatas

- Se um ingrediente já existe na receita destino, ele **não será duplicado**.
- Apenas ingredientes novos serão adicionados à receita destino.
- O contador `ingredientes_clonados` reflete apenas os ingredientes realmente adicionados.

### Tipos de Ingredientes

O endpoint clona todos os tipos de ingredientes:
- **Produtos** (`produto_cod_barras`)
- **Sub-receitas** (`receita_ingrediente_id`)
- **Combos** (`combo_id`)

### Quantidades

As quantidades dos ingredientes são preservadas na clonagem.

### Validações

O endpoint valida:
- ✅ Existência das receitas de origem e destino
- ✅ Receitas devem ser diferentes
- ✅ Receita origem deve possuir ingredientes
- ✅ Não duplica ingredientes já existentes na receita destino

---

## 🔄 7. Fluxo Recomendado no Frontend

1. **Usuario seleciona receita origem** (de onde copiar ingredientes)
2. **Usuario seleciona receita destino** (para onde copiar ingredientes)
3. **Frontend valida** que as receitas são diferentes
4. **Frontend chama o endpoint** `/clonar-ingredientes`
5. **Frontend exibe mensagem de sucesso** com quantidade de ingredientes clonados
6. **Frontend atualiza a lista de ingredientes** da receita destino (re-carrega ou atualiza estado)

---

## 📚 8. Endpoints Relacionados

- **GET** `/api/catalogo/admin/receitas/{receita_id}` - Buscar receita por ID
- **GET** `/api/catalogo/admin/receitas/itens?receita_id={id}` - Listar ingredientes de uma receita
- **POST** `/api/catalogo/admin/receitas/itens` - Adicionar ingrediente a uma receita
- **DELETE** `/api/catalogo/admin/receitas/itens/{id}` - Remover ingrediente de uma receita

---

## ✅ 9. Checklist de Implementação

- [ ] Implementar função/service para chamar o endpoint
- [ ] Adicionar tratamento de erros (400, 404, 401)
- [ ] Adicionar loading state durante a requisição
- [ ] Exibir mensagem de sucesso com quantidade de ingredientes clonados
- [ ] Atualizar lista de ingredientes da receita destino após clonagem
- [ ] Validar que receitas origem e destino são diferentes
- [ ] Testar com receita origem sem ingredientes
- [ ] Testar com receita destino que já possui alguns ingredientes (verificar não-duplicação)
- [ ] Testar com IDs de receitas inexistentes

---

## 📞 10. Suporte

Em caso de dúvidas ou problemas, verifique:
1. Token JWT válido e não expirado
2. IDs das receitas estão corretos
3. Receitas existem no banco de dados
4. Conexão com a API está funcionando

---

**Última atualização:** $(date)
