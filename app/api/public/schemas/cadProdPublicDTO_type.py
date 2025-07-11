from pydantic import BaseModel
from typing import Optional
from datetime import date

class CadProdPublicDTO(BaseModel):
    cadp_codigo: Optional[int] = None
    cadp_situacao: Optional[str] = None
    cadp_descricao: Optional[str] = None
    cadp_complemento: Optional[str] = None
    cadp_codcategoria: Optional[int] = None
    cadp_categoria: Optional[str] = None
    cadp_codmarca: Optional[int] = None
    cadp_marca: Optional[str] = None
    cadp_diretivas: Optional[str] = None
    cadp_dtcadastro: Optional[date] = None
    cadp_balanca: Optional[str] = None
    cadp_codigobarra: Optional[str] = None
    cadp_controlaestoque: Optional[str] = None
    cadp_vincpreco: Optional[int] = None
    cadp_pesoun: Optional[float] = None
    cadp_pesoemb: Optional[float] = None
    cadp_codvasilhame: Optional[str] = None

    class Config:
        from_attributes = True
