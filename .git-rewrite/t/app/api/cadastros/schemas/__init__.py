"""
Schemas de Cadastros
Centraliza todos os schemas relacionados a CRUD de entidades de cadastro:
- Produtos
- Adicionais
- Clientes
- Combos
- Meios de Pagamento
- Categorias
- Cupons
- Vitrines
- Parceiros
"""

# Importar todos os schemas para facilitar o uso
from app.api.catalogo.schemas.schema_produtos import *
from app.api.catalogo.schemas.schema_adicional import *
from app.api.cadastros.schemas.schema_cliente import *
from app.api.catalogo.schemas.schema_combo import *
from app.api.cadastros.schemas.schema_meio_pagamento import *
from app.api.cadastros.schemas.schema_categoria import *
from app.api.cadastros.schemas.schema_parceiros import *
