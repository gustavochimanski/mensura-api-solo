# Documentação Frontend - Redirecionamento de Home

Esta documentação descreve como o frontend deve implementar o redirecionamento automático da home baseado nas configurações da empresa.

---

## 📋 Visão Geral

O sistema permite configurar um redirecionamento automático da página inicial (home) da empresa para uma URL específica. Isso é útil para casos onde a empresa deseja redirecionar os usuários para uma página externa ou uma rota específica do frontend.

**Campos disponíveis:**
- `redireciona_home`: Boolean que indica se o redirecionamento está ativo
- `redireciona_home_para`: String com a URL/href para onde redirecionar (só é usado se `redireciona_home` for `true`)

---

## 🔌 1. Base URL

**Prefixo do módulo**: `/api/empresas/public/emp`

**Exemplos:**
- **Local**: `http://localhost:8000/api/empresas/public/emp`
- **Produção**: `https://seu-dominio.com/api/empresas/public/emp`

---

## 📥 2. Obter Dados da Empresa

### 2.1. Endpoint

```
GET /api/empresas/public/emp?empresa_id={empresa_id}
```

**Exemplos:**
- **Local**: `http://localhost:8000/api/empresas/public/emp?empresa_id=1`
- **Produção**: `https://seu-dominio.com/api/empresas/public/emp?empresa_id=1`

### 2.2. Parâmetros da Query

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `empresa_id` | Integer | Sim | ID da empresa |

### 2.3. Resposta de Sucesso (200 OK)

```json
{
  "nome": "Nome da Empresa",
  "logo": "https://...",
  "timezone": "America/Sao_Paulo",
  "horarios_funcionamento": [...],
  "cardapio_tema": "padrao",
  "aceita_pedido_automatico": false,
  "tempo_entrega_maximo": 60,
  "redireciona_home": true,
  "redireciona_home_para": "https://exemplo.com/pagina-especial",
  "cep": "12345-678",
  "logradouro": "Rua Exemplo",
  "numero": "123",
  "complemento": null,
  "bairro": "Centro",
  "cidade": "São Paulo",
  "estado": "SP",
  "ponto_referencia": null,
  "latitude": -23.5505,
  "longitude": -46.6333
}
```

### 2.4. Campos de Redirecionamento

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `redireciona_home` | Boolean | Indica se o redirecionamento está ativo. Se `true`, o frontend deve redirecionar. |
| `redireciona_home_para` | String \| null | URL/href para onde redirecionar. Só deve ser usado se `redireciona_home` for `true`. Pode ser uma URL externa ou uma rota interna do frontend. |

---

## 🎯 3. Implementação no Frontend

### 3.1. Fluxo de Verificação

Quando o usuário acessa a home da empresa, o frontend deve:

1. **Buscar os dados da empresa** usando o endpoint acima
2. **Verificar se `redireciona_home` é `true`**
3. **Se for `true` e `redireciona_home_para` estiver preenchido**, redirecionar para a URL especificada
4. **Se for `false` ou `redireciona_home_para` estiver vazio/null**, exibir a home normalmente

### 3.2. Exemplo de Implementação (React/Next.js)

```typescript
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

interface EmpresaData {
  redireciona_home: boolean;
  redireciona_home_para: string | null;
  // ... outros campos
}

export default function HomePage() {
  const router = useRouter();
  const { empresa_id } = router.query;
  const [empresa, setEmpresa] = useState<EmpresaData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchEmpresa() {
      if (!empresa_id) return;

      try {
        const response = await fetch(
          `/api/empresas/public/emp?empresa_id=${empresa_id}`
        );
        const data: EmpresaData = await response.json();
        setEmpresa(data);

        // Verificar redirecionamento
        if (data.redireciona_home && data.redireciona_home_para) {
          // Verificar se é URL externa ou rota interna
          if (data.redireciona_home_para.startsWith('http://') || 
              data.redireciona_home_para.startsWith('https://')) {
            // URL externa - redirecionar diretamente
            window.location.href = data.redireciona_home_para;
          } else {
            // Rota interna - usar router do Next.js
            router.push(data.redireciona_home_para);
          }
          return; // Não renderizar a home
        }
      } catch (error) {
        console.error('Erro ao buscar dados da empresa:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchEmpresa();
  }, [empresa_id, router]);

  if (loading) {
    return <div>Carregando...</div>;
  }

  // Se chegou aqui, não há redirecionamento ou está desativado
  return (
    <div>
      {/* Conteúdo normal da home */}
      <h1>Bem-vindo à {empresa?.nome}</h1>
      {/* ... resto do conteúdo */}
    </div>
  );
}
```

### 3.3. Exemplo de Implementação (Vue.js)

```vue
<template>
  <div v-if="loading">Carregando...</div>
  <div v-else>
    <!-- Conteúdo normal da home -->
    <h1>Bem-vindo à {{ empresa?.nome }}</h1>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

interface EmpresaData {
  redireciona_home: boolean;
  redireciona_home_para: string | null;
  nome: string;
  // ... outros campos
}

const route = useRoute();
const router = useRouter();
const empresa = ref<EmpresaData | null>(null);
const loading = ref(true);

async function verificarRedirecionamento() {
  const empresaId = route.params.empresa_id || route.query.empresa_id;
  if (!empresaId) return;

  try {
    const response = await fetch(
      `/api/empresas/public/emp?empresa_id=${empresaId}`
    );
    const data: EmpresaData = await response.json();
    empresa.value = data;

    // Verificar redirecionamento
    if (data.redireciona_home && data.redireciona_home_para) {
      if (data.redireciona_home_para.startsWith('http://') || 
          data.redireciona_home_para.startsWith('https://')) {
        // URL externa
        window.location.href = data.redireciona_home_para;
      } else {
        // Rota interna
        router.push(data.redireciona_home_para);
      }
      return;
    }
  } catch (error) {
    console.error('Erro ao buscar dados da empresa:', error);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  verificarRedirecionamento();
});
</script>
```

### 3.4. Exemplo de Implementação (Vanilla JavaScript)

```javascript
async function verificarRedirecionamento(empresaId) {
  try {
    const response = await fetch(
      `/api/empresas/public/emp?empresa_id=${empresaId}`
    );
    const empresa = await response.json();

    // Verificar redirecionamento
    if (empresa.redireciona_home && empresa.redireciona_home_para) {
      // Redirecionar (funciona para URLs externas e internas)
      window.location.href = empresa.redireciona_home_para;
      return true; // Indica que houve redirecionamento
    }
    
    return false; // Não houve redirecionamento
  } catch (error) {
    console.error('Erro ao verificar redirecionamento:', error);
    return false;
  }
}

// Uso ao carregar a página
const empresaId = new URLSearchParams(window.location.search).get('empresa_id');
if (empresaId) {
  verificarRedirecionamento(empresaId).then((redirecionou) => {
    if (!redirecionou) {
      // Carregar conteúdo normal da home
      carregarHome();
    }
  });
}
```

---

## ⚙️ 4. Configuração no Admin (Backend)

### 4.1. Endpoint de Atualização

```
PUT /api/empresas/admin/{id}
```

### 4.2. Parâmetros do Form

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `redireciona_home` | String | Não | `"true"` ou `"false"` (como string) |
| `redireciona_home_para` | String | Não | URL/href para redirecionamento |

### 4.3. Exemplo de Requisição

```javascript
const formData = new FormData();
formData.append('redireciona_home', 'true');
formData.append('redireciona_home_para', 'https://exemplo.com/pagina-especial');

fetch('/api/empresas/admin/1', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

---

## 📝 5. Casos de Uso

### 5.1. Redirecionamento para URL Externa

```json
{
  "redireciona_home": true,
  "redireciona_home_para": "https://site-externo.com/promocao"
}
```

**Comportamento**: O frontend redireciona para a URL externa usando `window.location.href`.

### 5.2. Redirecionamento para Rota Interna

```json
{
  "redireciona_home": true,
  "redireciona_home_para": "/cardapio"
}
```

**Comportamento**: O frontend redireciona para a rota interna usando o router do framework (ex: `router.push()` no Next.js/Vue).

### 5.3. Redirecionamento Desativado

```json
{
  "redireciona_home": false,
  "redireciona_home_para": null
}
```

**Comportamento**: O frontend exibe a home normalmente, ignorando o campo `redireciona_home_para`.

### 5.4. Configuração Incompleta

```json
{
  "redireciona_home": true,
  "redireciona_home_para": null
}
```

**Comportamento**: O frontend **não deve redirecionar** se `redireciona_home_para` estiver vazio/null, mesmo que `redireciona_home` seja `true`. Exibir a home normalmente.

---

## ⚠️ 6. Observações Importantes

1. **Validação**: Sempre verifique se `redireciona_home_para` não está vazio/null antes de redirecionar, mesmo que `redireciona_home` seja `true`.

2. **URLs Externas vs Internas**: 
   - URLs que começam com `http://` ou `https://` são tratadas como externas
   - Outras URLs são tratadas como rotas internas do frontend

3. **Performance**: Considere cachear os dados da empresa para evitar múltiplas requisições.

4. **Fallback**: Se houver erro ao buscar os dados da empresa, exiba a home normalmente (não bloqueie a experiência do usuário).

5. **SEO**: Se o redirecionamento for para URL externa, considere usar um redirect 301 no servidor para melhor SEO.

---

## 🔍 7. Exemplos de Valores

### Exemplo 1: Redirecionamento para Landing Page Externa
```json
{
  "redireciona_home": true,
  "redireciona_home_para": "https://promocao.empresa.com/black-friday"
}
```

### Exemplo 2: Redirecionamento para Página de Cardápio
```json
{
  "redireciona_home": true,
  "redireciona_home_para": "/cardapio"
}
```

### Exemplo 3: Redirecionamento para Página Específica com Query Params
```json
{
  "redireciona_home": true,
  "redireciona_home_para": "/pedidos?tipo=delivery"
}
```

### Exemplo 4: Sem Redirecionamento
```json
{
  "redireciona_home": false,
  "redireciona_home_para": null
}
```

---

## 📞 8. Suporte

Em caso de dúvidas ou problemas na implementação, consulte:
- Documentação da API: `/docs` (Swagger/OpenAPI)
- Logs do backend para debug
- Equipe de desenvolvimento

---

**Última atualização**: 2024
