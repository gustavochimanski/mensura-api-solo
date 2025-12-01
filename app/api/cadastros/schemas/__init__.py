"""
Schemas de Cadastros
Centraliza todos os schemas relacionados a CRUD de entidades de cadastro:
- Clientes
- Meios de Pagamento
- Categorias
- Cupons
- Parceiros
- Endereços
"""

# Importar todos os schemas para facilitar o uso
from app.api.cadastros.schemas.schema_cliente import *
from app.api.cadastros.schemas.schema_meio_pagamento import *
from app.api.cadastros.schemas.schema_categoria import *
from app.api.cadastros.schemas.schema_parceiros import *
from app.api.cadastros.schemas.schema_endereco import *
