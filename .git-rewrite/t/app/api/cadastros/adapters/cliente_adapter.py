from typing import Optional
from sqlalchemy.orm import Session

from app.api.cadastros.contracts.cliente_contract import (
    IClienteContract,
    ClienteDTO,
    EnderecoDTO,
)
from app.api.cadastros.repositories.repo_cliente import ClienteRepository
from app.api.cadastros.models.model_endereco_dv import EnderecoModel
from app.api.cadastros.models.model_cliente_dv import ClienteModel


class ClienteAdapter(IClienteContract):
    """Implementação do contrato de clientes baseada nos repositórios atuais."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ClienteRepository(db)

    def _to_cliente_dto(self, c: ClienteModel) -> ClienteDTO:
        return ClienteDTO(
            id=c.id,
            nome=c.nome,
            telefone=c.telefone,
            cpf=c.cpf,
            email=c.email,
            ativo=bool(c.ativo),
        )

    def _to_endereco_dto(self, e: EnderecoModel) -> EnderecoDTO:
        lat = float(e.latitude) if e.latitude is not None else None
        lon = float(e.longitude) if e.longitude is not None else None
        return EnderecoDTO(
            id=e.id,
            cliente_id=e.cliente_id,
            cep=e.cep,
            logradouro=e.logradouro,
            numero=e.numero,
            complemento=e.complemento,
            bairro=e.bairro,
            cidade=e.cidade,
            estado=e.estado,
            latitude=lat,
            longitude=lon,
            is_principal=bool(getattr(e, "is_principal", False)),
        )

    def obter_cliente(self, cliente_id: int) -> Optional[ClienteDTO]:
        c = self.repo.get_by_id(cliente_id)
        if not c:
            return None
        return self._to_cliente_dto(c)

    def obter_endereco_principal(self, cliente_id: int) -> Optional[EnderecoDTO]:
        enderecos = self.repo.get_enderecos(cliente_id)
        if not enderecos:
            return None
        principal = next((e for e in enderecos if getattr(e, "is_principal", False)), None)
        e = principal or enderecos[0]
        return self._to_endereco_dto(e)


