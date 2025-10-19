"""
Exemplos de uso das rotas de categorias do módulo @mensura/

Este arquivo contém exemplos de requisições para todas as rotas de categorias.
"""

# =============================================================================
# EXEMPLOS DE REQUISIÇÕES
# =============================================================================

# 1. CRIAR CATEGORIA
# POST /mensura/categorias/
criar_categoria_exemplo = {
    "descricao": "Eletrônicos",
    "parent_id": None,  # Categoria raiz
    "ativo": True
}

# 2. CRIAR SUBCATEGORIA
# POST /mensura/categorias/
criar_subcategoria_exemplo = {
    "descricao": "Smartphones",
    "parent_id": 1,  # ID da categoria "Eletrônicos"
    "ativo": True
}

# 3. BUSCAR CATEGORIA POR ID
# GET /mensura/categorias/1
# Não precisa de body

# 4. LISTAR CATEGORIAS PAGINADO
# GET /mensura/categorias/?page=1&limit=10&apenas_ativas=true&parent_id=None
# Query parameters opcionais

# 5. ATUALIZAR CATEGORIA
# PUT /mensura/categorias/1
atualizar_categoria_exemplo = {
    "descricao": "Eletrônicos e Acessórios",
    "parent_id": None,
    "ativo": True
}

# 6. DELETAR CATEGORIA
# DELETE /mensura/categorias/1
# Não precisa de body

# 7. BUSCAR CATEGORIAS POR TERMO
# GET /mensura/categorias/buscar/termo?termo=smart&page=1&limit=10&apenas_ativas=true

# 8. BUSCAR ÁRVORE DE CATEGORIAS
# GET /mensura/categorias/arvore/estrutura?apenas_ativas=true

# 9. BUSCAR CATEGORIAS RAIZ
# GET /mensura/categorias/raiz/lista?apenas_ativas=true

# 10. BUSCAR FILHOS DE UMA CATEGORIA
# GET /mensura/categorias/1/filhos?apenas_ativas=true

# =============================================================================
# EXEMPLOS DE RESPOSTAS
# =============================================================================

# Resposta de criação/atualização/busca por ID
resposta_categoria_exemplo = {
    "categoria": {
        "id": 1,
        "descricao": "Eletrônicos",
        "ativo": True,
        "parent_id": None,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
}

# Resposta de listagem paginada
resposta_lista_paginada_exemplo = {
    "data": [
        {
            "id": 1,
            "descricao": "Eletrônicos",
            "ativo": True,
            "parent_id": None,
            "parent_descricao": None,
            "total_filhos": 3
        },
        {
            "id": 2,
            "descricao": "Roupas",
            "ativo": True,
            "parent_id": None,
            "parent_descricao": None,
            "total_filhos": 0
        }
    ],
    "total": 2,
    "page": 1,
    "limit": 10,
    "has_more": False
}

# Resposta de árvore de categorias
resposta_arvore_exemplo = {
    "categorias": [
        {
            "id": 1,
            "descricao": "Eletrônicos",
            "ativo": True,
            "parent_id": None,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z",
            "children": [
                {
                    "id": 2,
                    "descricao": "Smartphones",
                    "ativo": True,
                    "parent_id": 1,
                    "created_at": "2024-01-15T10:35:00Z",
                    "updated_at": "2024-01-15T10:35:00Z",
                    "children": []
                },
                {
                    "id": 3,
                    "descricao": "Notebooks",
                    "ativo": True,
                    "parent_id": 1,
                    "created_at": "2024-01-15T10:40:00Z",
                    "updated_at": "2024-01-15T10:40:00Z",
                    "children": []
                }
            ]
        }
    ]
}

# Resposta de deleção
resposta_delecao_exemplo = {
    "message": "Categoria deletada com sucesso."
}

# =============================================================================
# CÓDIGOS DE ERRO COMUNS
# =============================================================================

# 400 - Bad Request
erro_400_exemplo = {
    "detail": "Já existe uma categoria com esta descrição."
}

# 404 - Not Found
erro_404_exemplo = {
    "detail": "Categoria não encontrada."
}

# 400 - Não pode deletar (tem filhos ativos)
erro_delecao_exemplo = {
    "detail": "Não é possível deletar categoria que possui subcategorias ativas."
}

# =============================================================================
# NOTAS IMPORTANTES
# =============================================================================

"""
1. Todas as rotas requerem autenticação (dependência get_current_user)

2. Soft Delete: A deleção marca a categoria como inativa (ativo=0), não remove do banco

3. Hierarquia: Categorias podem ter subcategorias (parent_id), formando uma árvore

4. Validações:
   - Não é possível deletar categoria que tem filhos ativos
   - Não é possível criar categoria com parent_id inexistente
   - Não é possível criar categoria com descrição duplicada
   - Categoria não pode ser pai de si mesma

5. Filtros disponíveis:
   - apenas_ativas: filtra apenas categorias ativas
   - parent_id: filtra por categoria pai específica

6. Paginação:
   - page: número da página (começa em 1)
   - limit: itens por página (máximo 100)
   - has_more: indica se há mais páginas

7. Busca por termo: busca na descrição das categorias (case-insensitive)
"""
