from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.api.delivery.repositories.repo_endereco import EnderecoRepository
from app.api.delivery.schemas.schema_endereco import EnderecoOut, EnderecoCreate, EnderecoUpdate
from app.api.delivery.services.pedidos.service_pedido import PedidoService

class EnderecosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EnderecoRepository(db)

    def list(self, super_token: str):
        cliente_id = self._token_para_cliente_id(super_token)
        return [EnderecoOut.model_validate(x) for x in self.repo.list_by_cliente(cliente_id)]

    def list_by_cliente_id(self, cliente_id: int):
        """
        Lista endereços de um cliente específico por ID.
        Usado por admins para consultar endereços de qualquer cliente.
        """
        return [EnderecoOut.model_validate(x) for x in self.repo.list_by_cliente(cliente_id)]

    def create_by_cliente_id(self, cliente_id: int, payload: EnderecoCreate):
        """
        Cria endereço para um cliente específico por ID.
        Usado por admins para criar endereços para qualquer cliente.
        Verifica se o endereço já existe antes de criar.
        """
        # Verifica se o endereço já existe
        if self.repo.endereco_existe(cliente_id, payload):
            raise HTTPException(
                status_code=400,
                detail="Este endereço já existe para este cliente"
            )
        
        return EnderecoOut.model_validate(self.repo.create(cliente_id, payload))

    def update_by_cliente_id(self, cliente_id: int, endereco_id: int, payload: EnderecoUpdate):
        """
        Atualiza endereço de um cliente específico por ID.
        Usado por admins para atualizar endereços de qualquer cliente.
        Verifica se o endereço já existe antes de atualizar.
        """
        # Verifica se o endereço está sendo usado em pedidos ativos
        pedido_service = PedidoService(self.db)
        if pedido_service.verificar_endereco_em_uso(endereco_id):
            raise HTTPException(
                status_code=400, 
                detail="Não é possível alterar este endereço pois ele está sendo usado em pedidos ativos"
            )
        
        # Se está atualizando dados que podem causar duplicata, verifica
        if self._dados_podem_causar_duplicata(payload):
            # Cria um payload temporário com os dados atualizados para verificar duplicata
            endereco_atual = self.repo.get_by_cliente(cliente_id, endereco_id)
            dados_atualizados = endereco_atual.__dict__.copy()
            for k, v in payload.model_dump(exclude_unset=True).items():
                dados_atualizados[k] = v
            
            # Cria um objeto temporário para verificar duplicata
            from app.api.delivery.schemas.schema_endereco import EnderecoCreate
            payload_temp = EnderecoCreate(
                logradouro=dados_atualizados.get('logradouro'),
                numero=dados_atualizados.get('numero'),
                bairro=dados_atualizados.get('bairro'),
                cidade=dados_atualizados.get('cidade'),
                uf=dados_atualizados.get('uf'),
                cep=dados_atualizados.get('cep'),
                complemento=dados_atualizados.get('complemento')
            )
            
            if self.repo.endereco_existe(cliente_id, payload_temp, exclude_id=endereco_id):
                raise HTTPException(
                    status_code=400,
                    detail="Este endereço já existe para este cliente"
                )
        
        return EnderecoOut.model_validate(self.repo.update(cliente_id, endereco_id, payload))

    def _dados_podem_causar_duplicata(self, payload: EnderecoUpdate) -> bool:
        """
        Verifica se os dados sendo atualizados podem causar duplicata.
        Só verifica duplicata se campos críticos estão sendo alterados.
        """
        dados = payload.model_dump(exclude_unset=True)
        campos_criticos = ['logradouro', 'numero', 'bairro', 'cidade', 'uf', 'cep']
        return any(campo in dados for campo in campos_criticos)

    def get(self, super_token: str, end_id: int):
        cliente_id = self._token_para_cliente_id(super_token)
        return EnderecoOut.model_validate(self.repo.get_by_cliente(cliente_id, end_id))

    def create(self, super_token: str, payload: EnderecoCreate):
        cliente_id = self._token_para_cliente_id(super_token)
        return EnderecoOut.model_validate(self.repo.create(cliente_id, payload))

    def update(self, super_token: str, end_id: int, payload: EnderecoUpdate):
        cliente_id = self._token_para_cliente_id(super_token)
        
        # Verifica se o endereço está sendo usado em pedidos ativos
        pedido_service = PedidoService(self.db)
        if pedido_service.verificar_endereco_em_uso(end_id):
            raise HTTPException(
                status_code=400, 
                detail="Não é possível alterar este endereço pois ele está sendo usado em pedidos ativos"
            )
        
        return EnderecoOut.model_validate(self.repo.update(cliente_id, end_id, payload))

    def delete(self, super_token: str, end_id: int):
        cliente_id = self._token_para_cliente_id(super_token)
        
        # Verifica se o endereço está sendo usado em pedidos ativos
        pedido_service = PedidoService(self.db)
        if pedido_service.verificar_endereco_em_uso(end_id):
            raise HTTPException(
                status_code=400, 
                detail="Não é possível excluir este endereço pois ele está sendo usado em pedidos ativos"
            )
        
        self.repo.delete(cliente_id, end_id)

    def set_padrao(self, super_token: str, end_id: int):
        cliente_id = self._token_para_cliente_id(super_token)
        return EnderecoOut.model_validate(self.repo.set_padrao(cliente_id, end_id))

    # --- função ajustada para retornar cliente_id ---
    def _token_para_cliente_id(self, super_token: str) -> int:
        cliente = self.db.query(ClienteDeliveryModel).filter_by(super_token=super_token).first()
        if not cliente:
            raise HTTPException(status_code=401, detail="Token inválido")
        return cliente.id
