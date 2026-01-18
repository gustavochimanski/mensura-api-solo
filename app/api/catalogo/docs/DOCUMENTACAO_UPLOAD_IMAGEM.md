# Documentação Frontend - Upload de Imagens (Receitas e Combos)

Esta documentação descreve como o frontend deve implementar o upload de imagens para receitas e combos.

---

## 📋 Visão Geral

O sistema permite fazer upload de imagens para receitas e combos através de endpoints específicos. As imagens são armazenadas no MinIO e uma URL pública é retornada e salva no campo `imagem` do recurso.

**Formatos aceitos:**
- JPEG (`image/jpeg`)
- PNG (`image/png`)
- WebP (`image/webp`)

---

## 🔌 1. Base URL

**Prefixo do módulo**: `/api/catalogo/admin`

**Exemplos:**
- **Local**: `http://localhost:8000/api/catalogo/admin`
- **Produção**: `https://seu-dominio.com/api/catalogo/admin`

---

## 🔐 2. Autenticação

Todos os endpoints abaixo exigem autenticação de administrador via JWT no header:

```http
Authorization: Bearer {seu_token_jwt}
```

---

## 📤 3. Upload de Imagem - Receitas

### 3.1. Endpoint

```
PUT /api/catalogo/admin/receitas/{receita_id}/imagem
```

**Exemplos:**
- **Local**: `http://localhost:8000/api/catalogo/admin/receitas/123/imagem`
- **Produção**: `https://seu-dominio.com/api/catalogo/admin/receitas/123/imagem`

### 3.2. Parâmetros da URL

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `receita_id` | `integer` | ID da receita que terá a imagem atualizada (path parameter) |

### 3.3. Request

**Content-Type:** `multipart/form-data`

**Body (Form Data):**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `cod_empresa` | `integer` | ✅ Sim | ID da empresa dona da receita |
| `imagem` | `file` | ✅ Sim | Arquivo de imagem (JPEG, PNG ou WebP) |

### 3.4. Exemplo de Requisição (JavaScript/Fetch)

```javascript
const atualizarImagemReceita = async (receitaId, empresaId, arquivoImagem) => {
  const formData = new FormData();
  formData.append('cod_empresa', empresaId);
  formData.append('imagem', arquivoImagem);

  const response = await fetch(
    `http://localhost:8000/api/catalogo/admin/receitas/${receitaId}/imagem`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${seuTokenJWT}`
      },
      body: formData
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao fazer upload da imagem');
  }

  return await response.json();
};

// Uso
const arquivo = document.getElementById('inputImagem').files[0];
await atualizarImagemReceita(123, 1, arquivo);
```

### 3.5. Exemplo de Requisição (Axios)

```javascript
import axios from 'axios';

const atualizarImagemReceita = async (receitaId, empresaId, arquivoImagem) => {
  const formData = new FormData();
  formData.append('cod_empresa', empresaId);
  formData.append('imagem', arquivoImagem);

  try {
    const response = await axios.put(
      `/api/catalogo/admin/receitas/${receitaId}/imagem`,
      formData,
      {
        headers: {
          'Authorization': `Bearer ${seuTokenJWT}`,
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Erro ao fazer upload da imagem');
    }
    throw error;
  }
};
```

### 3.6. Response

**Status Code:** `200 OK`

**Schema de Resposta:**

```typescript
interface ReceitaOut {
  id: number;
  empresa_id: number;
  nome: string;
  descricao: string | null;
  preco_venda: number;
  custo_total: number;
  imagem: string | null;  // URL pública da imagem no MinIO
  ativo: boolean;
  disponivel: boolean;
  created_at: string;  // ISO 8601 datetime
  updated_at: string;  // ISO 8601 datetime
}
```

**Exemplo de Response:**

```json
{
  "id": 123,
  "empresa_id": 1,
  "nome": "Pizza Margherita",
  "descricao": "Pizza tradicional italiana",
  "preco_venda": "29.90",
  "custo_total": "15.50",
  "imagem": "https://minio.exemplo.com/bucket/empresa-123/receitas/uuid-imagem.jpg",
  "ativo": true,
  "disponivel": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:45:00Z"
}
```

### 3.7. Erros Possíveis

#### 400 Bad Request

**Formato de imagem inválido:**
```json
{
  "detail": "Formato de imagem inválido"
}
```

**Empresa não confere:**
```json
{
  "detail": "cod_empresa não confere com a empresa da receita."
}
```

#### 404 Not Found

**Receita não encontrada:**
```json
{
  "detail": "Receita não encontrada."
}
```

#### 500 Internal Server Error

**Erro no upload:**
```json
{
  "detail": "Erro ao fazer upload da imagem"
}
```

---

## 📤 4. Upload de Imagem - Combos

### 4.1. Endpoint

```
PUT /api/catalogo/admin/combos/{combo_id}/imagem
```

**Exemplos:**
- **Local**: `http://localhost:8000/api/catalogo/admin/combos/456/imagem`
- **Produção**: `https://seu-dominio.com/api/catalogo/admin/combos/456/imagem`

### 4.2. Parâmetros da URL

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `combo_id` | `integer` | ID do combo que terá a imagem atualizada (path parameter) |

### 4.3. Request

**Content-Type:** `multipart/form-data`

**Body (Form Data):**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `cod_empresa` | `integer` | ✅ Sim | ID da empresa dona do combo |
| `imagem` | `file` | ✅ Sim | Arquivo de imagem (JPEG, PNG ou WebP) |

### 4.4. Exemplo de Requisição (JavaScript/Fetch)

```javascript
const atualizarImagemCombo = async (comboId, empresaId, arquivoImagem) => {
  const formData = new FormData();
  formData.append('cod_empresa', empresaId);
  formData.append('imagem', arquivoImagem);

  const response = await fetch(
    `http://localhost:8000/api/catalogo/admin/combos/${comboId}/imagem`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${seuTokenJWT}`
      },
      body: formData
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erro ao fazer upload da imagem');
  }

  return await response.json();
};

// Uso
const arquivo = document.getElementById('inputImagem').files[0];
await atualizarImagemCombo(456, 1, arquivo);
```

### 4.5. Exemplo de Requisição (Axios)

```javascript
import axios from 'axios';

const atualizarImagemCombo = async (comboId, empresaId, arquivoImagem) => {
  const formData = new FormData();
  formData.append('cod_empresa', empresaId);
  formData.append('imagem', arquivoImagem);

  try {
    const response = await axios.put(
      `/api/catalogo/admin/combos/${comboId}/imagem`,
      formData,
      {
        headers: {
          'Authorization': `Bearer ${seuTokenJWT}`,
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Erro ao fazer upload da imagem');
    }
    throw error;
  }
};
```

### 4.6. Response

**Status Code:** `200 OK`

**Schema de Resposta:**

```typescript
interface ComboDTO {
  id: number;
  empresa_id: number;
  titulo: string;
  descricao: string;
  preco_total: number;
  custo_total: number | null;
  ativo: boolean;
  imagem: string | null;  // URL pública da imagem no MinIO
  itens: ComboItemDTO[];
  created_at: string;  // ISO 8601 datetime
  updated_at: string;  // ISO 8601 datetime
}

interface ComboItemDTO {
  produto_cod_barras: string | null;
  receita_id: number | null;
  quantidade: number;
}
```

**Exemplo de Response:**

```json
{
  "id": 456,
  "empresa_id": 1,
  "titulo": "Combo Pizza + Refri",
  "descricao": "Pizza Grande + Refrigerante 2L",
  "preco_total": 49.90,
  "custo_total": 25.00,
  "ativo": true,
  "imagem": "https://minio.exemplo.com/bucket/empresa-123/combos/uuid-imagem.jpg",
  "itens": [
    {
      "produto_cod_barras": "7891234567890",
      "receita_id": null,
      "quantidade": 1
    },
    {
      "produto_cod_barras": null,
      "receita_id": 123,
      "quantidade": 1
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:45:00Z"
}
```

### 4.7. Erros Possíveis

#### 400 Bad Request

**Formato de imagem inválido:**
```json
{
  "detail": "Formato de imagem inválido"
}
```

**Empresa não confere:**
```json
{
  "detail": "cod_empresa não confere com a empresa do combo."
}
```

#### 404 Not Found

**Combo não encontrado:**
```json
{
  "detail": "Combo não encontrado."
}
```

#### 500 Internal Server Error

**Erro no upload:**
```json
{
  "detail": "Erro ao fazer upload da imagem"
}
```

---

## 💡 5. Exemplo Completo - Componente React

```jsx
import React, { useState } from 'react';
import axios from 'axios';

const UploadImagemReceita = ({ receitaId, empresaId, token }) => {
  const [imagem, setImagem] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    
    // Validação do tipo de arquivo
    const tiposAceitos = ['image/jpeg', 'image/png', 'image/webp'];
    if (!tiposAceitos.includes(file.type)) {
      setError('Formato de imagem inválido. Use JPEG, PNG ou WebP.');
      return;
    }

    setImagem(file);
    setError(null);
  };

  const handleUpload = async () => {
    if (!imagem) {
      setError('Selecione uma imagem');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const formData = new FormData();
      formData.append('cod_empresa', empresaId);
      formData.append('imagem', imagem);

      const response = await axios.put(
        `/api/catalogo/admin/receitas/${receitaId}/imagem`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      setSuccess(true);
      console.log('Imagem atualizada:', response.data);
      
      // Reset do formulário
      setImagem(null);
      document.getElementById('inputImagem').value = '';
    } catch (err) {
      setError(
        err.response?.data?.detail || 
        'Erro ao fazer upload da imagem'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        id="inputImagem"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleFileChange}
        disabled={loading}
      />
      
      {imagem && (
        <div>
          <p>Arquivo selecionado: {imagem.name}</p>
          <button 
            onClick={handleUpload} 
            disabled={loading}
          >
            {loading ? 'Enviando...' : 'Upload'}
          </button>
        </div>
      )}

      {error && (
        <div style={{ color: 'red' }}>
          {error}
        </div>
      )}

      {success && (
        <div style={{ color: 'green' }}>
          Imagem atualizada com sucesso!
        </div>
      )}
    </div>
  );
};

export default UploadImagemReceita;
```

---

## 📝 6. Observações Importantes

### 6.1. Tamanho do Arquivo

Embora não haja limite explícito no endpoint, é recomendado:
- **Tamanho máximo sugerido**: 5 MB
- **Resolução recomendada**: 800x600px ou superior
- **Compressão**: Comprimir imagens antes do upload para melhor performance

### 6.2. Substituição de Imagem

- Quando uma nova imagem é enviada, a **imagem antiga é automaticamente removida** do MinIO
- A URL antiga é substituída pela nova URL no campo `imagem`
- Se houver erro no upload, a imagem anterior permanece intacta

### 6.3. Validação de Empresa

- O `cod_empresa` fornecido deve corresponder ao `empresa_id` do recurso (receita/combo)
- Isso garante que apenas a empresa dona do recurso possa atualizar sua imagem

### 6.4. URL da Imagem

- A URL retornada é **pública** e pode ser usada diretamente em tags `<img>`
- A URL é persistente e não expira
- O formato da URL depende da configuração do MinIO no ambiente

---

## 🔄 7. Fluxo Completo

1. **Usuário seleciona imagem** no input do tipo `file`
2. **Frontend valida** o tipo de arquivo (JPEG, PNG, WebP)
3. **Frontend cria FormData** com `cod_empresa` e `imagem`
4. **Frontend faz requisição PUT** para o endpoint específico
5. **Backend valida** formato, empresa e receita/combo
6. **Backend faz upload** no MinIO (substitui imagem antiga se existir)
7. **Backend atualiza** campo `imagem` com a nova URL
8. **Backend retorna** o recurso completo atualizado
9. **Frontend exibe** feedback de sucesso/erro e atualiza a interface

---

## 📚 8. Endpoints Relacionados

### Receitas

- **Listar receitas**: `GET /api/catalogo/admin/receitas`
- **Obter receita**: `GET /api/catalogo/admin/receitas/{receita_id}`
- **Criar receita**: `POST /api/catalogo/admin/receitas`
- **Atualizar receita**: `PUT /api/catalogo/admin/receitas/{receita_id}`

### Combos

- **Listar combos**: `GET /api/catalogo/admin/combos?cod_empresa={empresa_id}`
- **Obter combo**: `GET /api/catalogo/admin/combos/{combo_id}`
- **Criar combo**: `POST /api/catalogo/admin/combos`
- **Atualizar combo**: `PUT /api/catalogo/admin/combos/{combo_id}`

---

## ✅ 9. Checklist de Implementação

- [ ] Validação de tipo de arquivo antes do upload (JPEG, PNG, WebP)
- [ ] Feedback visual durante o upload (loading state)
- [ ] Tratamento de erros (formato inválido, empresa não confere, etc.)
- [ ] Mensagem de sucesso após upload concluído
- [ ] Atualização da imagem na interface após sucesso
- [ ] Validação do `cod_empresa` corresponde ao recurso
- [ ] Preview da imagem antes do upload (opcional mas recomendado)

---

**Última atualização**: 2024-01-20
