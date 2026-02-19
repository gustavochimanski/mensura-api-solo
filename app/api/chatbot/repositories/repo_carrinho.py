# app/api/chatbot/repositories/repo_carrinho.py
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from datetime import datetime, timedelta

from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.chatbot.models.model_carrinho import CarrinhoTemporarioModel
from app.api.chatbot.models.model_carrinho_item import CarrinhoItemModel
from app.api.chatbot.models.model_carrinho_item_complemento import CarrinhoItemComplementoModel
from app.api.chatbot.models.model_carrinho_item_complemento_adicional import CarrinhoItemComplementoAdicionalModel
from app.utils.logger import logger


class CarrinhoRepository:
    """Repository para CRUD de carrinho temporário do chatbot"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(
        self, 
        user_id: str, 
        empresa_id: Optional[int] = None,
        load_items: bool = True
    ) -> Optional[CarrinhoTemporarioModel]:
        """Busca carrinho por user_id (telefone)"""
        query = self.db.query(CarrinhoTemporarioModel)
        
        if load_items:
            query = query.options(
                joinedload(CarrinhoTemporarioModel.itens).joinedload(CarrinhoItemModel.complementos)
                .joinedload(CarrinhoItemComplementoModel.adicionais)
            )
        
        query = query.filter(CarrinhoTemporarioModel.user_id == user_id)
        
        if empresa_id:
            query = query.filter(CarrinhoTemporarioModel.empresa_id == empresa_id)
        
        return query.order_by(desc(CarrinhoTemporarioModel.created_at)).first()

    def get_by_id(
        self, 
        carrinho_id: int,
        load_items: bool = True
    ) -> Optional[CarrinhoTemporarioModel]:
        """Busca carrinho por ID"""
        query = self.db.query(CarrinhoTemporarioModel)
        
        if load_items:
            query = query.options(
                joinedload(CarrinhoTemporarioModel.itens).joinedload(CarrinhoItemModel.complementos)
                .joinedload(CarrinhoItemComplementoModel.adicionais)
            )
        
        return query.filter(CarrinhoTemporarioModel.id == carrinho_id).first()

    def create(self, **data) -> CarrinhoTemporarioModel:
        """Cria um novo carrinho"""
        # Define expires_at como 24 horas a partir de agora
        if 'expires_at' not in data:
            data['expires_at'] = datetime.utcnow() + timedelta(hours=24)
        
        carrinho = CarrinhoTemporarioModel(**data)
        self.db.add(carrinho)
        self.db.commit()
        self.db.refresh(carrinho)
        logger.info(f"[Carrinho] Criado carrinho_id={carrinho.id} user_id={carrinho.user_id} empresa_id={carrinho.empresa_id}")
        return carrinho

    def update(self, carrinho: CarrinhoTemporarioModel, **data) -> CarrinhoTemporarioModel:
        """Atualiza um carrinho existente"""
        for key, value in data.items():
            if hasattr(carrinho, key) and value is not None:
                setattr(carrinho, key, value)
        
        # Atualiza expires_at se necessário
        if 'expires_at' not in data:
            carrinho.expires_at = datetime.utcnow() + timedelta(hours=24)
        
        self.db.commit()
        self.db.refresh(carrinho)
        logger.info(f"[Carrinho] Atualizado carrinho_id={carrinho.id}")
        return carrinho

    def delete(self, carrinho: CarrinhoTemporarioModel) -> None:
        """Remove um carrinho e todos os seus itens (CASCADE)"""
        carrinho_id = carrinho.id
        self.db.delete(carrinho)
        self.db.commit()
        logger.info(f"[Carrinho] Deletado carrinho_id={carrinho_id}")

    def delete_by_user_id(self, user_id: str, empresa_id: Optional[int] = None) -> bool:
        """Remove carrinho por user_id"""
        carrinho = self.get_by_user_id(user_id, empresa_id, load_items=False)
        if carrinho:
            self.delete(carrinho)
            return True
        return False

    def get_item_by_id(self, item_id: int) -> Optional[CarrinhoItemModel]:
        """Busca item do carrinho por ID"""
        return (
            self.db.query(CarrinhoItemModel)
            .options(
                joinedload(CarrinhoItemModel.complementos)
                .joinedload(CarrinhoItemComplementoModel.adicionais)
            )
            .filter(CarrinhoItemModel.id == item_id)
            .first()
        )

    def add_item(self, carrinho_id: int, **item_data) -> CarrinhoItemModel:
        """Adiciona um item ao carrinho"""
        # Backfill de produto_id quando vier apenas cod_barras (compatibilidade)
        if item_data.get("produto_id") is None and item_data.get("produto_cod_barras"):
            cod_barras = str(item_data.get("produto_cod_barras"))
            produto_id = (
                self.db.query(ProdutoModel.id)
                .filter(ProdutoModel.cod_barras == cod_barras)
                .scalar()
            )
            item_data["produto_id"] = produto_id

        item = CarrinhoItemModel(carrinho_id=carrinho_id, **item_data)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        logger.info(f"[Carrinho] Item adicionado item_id={item.id} carrinho_id={carrinho_id}")
        return item

    def update_item(self, item: CarrinhoItemModel, **data) -> CarrinhoItemModel:
        """Atualiza um item do carrinho"""
        for key, value in data.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)
        
        # Recalcula preco_total se quantidade ou preco_unitario mudaram
        if 'quantidade' in data or 'preco_unitario' in data:
            item.preco_total = item.calcular_preco_total()
        
        self.db.commit()
        self.db.refresh(item)
        logger.info(f"[Carrinho] Item atualizado item_id={item.id}")
        return item

    def remove_item(self, item: CarrinhoItemModel) -> None:
        """Remove um item do carrinho"""
        item_id = item.id
        self.db.delete(item)
        self.db.commit()
        logger.info(f"[Carrinho] Item removido item_id={item_id}")

    def add_complemento(self, item_id: int, **complemento_data) -> CarrinhoItemComplementoModel:
        """Adiciona um complemento a um item"""
        complemento = CarrinhoItemComplementoModel(carrinho_item_id=item_id, **complemento_data)
        self.db.add(complemento)
        self.db.commit()
        self.db.refresh(complemento)
        logger.info(f"[Carrinho] Complemento adicionado complemento_id={complemento.id} item_id={item_id}")
        return complemento

    def add_adicional(self, complemento_id: int, **adicional_data) -> CarrinhoItemComplementoAdicionalModel:
        """Adiciona um adicional a um complemento"""
        adicional = CarrinhoItemComplementoAdicionalModel(
            item_complemento_id=complemento_id,
            **adicional_data
        )
        self.db.add(adicional)
        self.db.commit()
        self.db.refresh(adicional)
        logger.info(f"[Carrinho] Adicional adicionado adicional_id={adicional.id} complemento_id={complemento_id}")
        return adicional

    def limpar_carrinhos_expirados(self) -> int:
        """Remove carrinhos expirados (mais de 24 horas sem atualização)"""
        agora = datetime.utcnow()
        carrinhos_expirados = (
            self.db.query(CarrinhoTemporarioModel)
            .filter(CarrinhoTemporarioModel.expires_at < agora)
            .all()
        )
        
        count = len(carrinhos_expirados)
        for carrinho in carrinhos_expirados:
            self.db.delete(carrinho)
        
        self.db.commit()
        if count > 0:
            logger.info(f"[Carrinho] {count} carrinho(s) expirado(s) removido(s)")
        return count

    def list_carrinhos_abandonados(
        self,
        horas_sem_atualizacao: int = 24,
        limit: int = 100
    ) -> List[CarrinhoTemporarioModel]:
        """Lista carrinhos abandonados (sem atualização há X horas)"""
        limite_tempo = datetime.utcnow() - timedelta(hours=horas_sem_atualizacao)
        return (
            self.db.query(CarrinhoTemporarioModel)
            .filter(CarrinhoTemporarioModel.updated_at < limite_tempo)
            .order_by(desc(CarrinhoTemporarioModel.updated_at))
            .limit(limit)
            .all()
        )
