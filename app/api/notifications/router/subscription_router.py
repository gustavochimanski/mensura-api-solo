# Router de assinaturas removido - não utilizado pelo frontend
# Este arquivo foi mantido vazio para evitar quebras de importação
# TODO: Remover completamente se não houver dependências

from fastapi import APIRouter

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
