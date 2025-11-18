from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel
from app.api.cadastros.repositories.repo_meio_pagamento import MeioPagamentoRepository
from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoCreate, MeioPagamentoUpdate


class MeioPagamentoService:
    def __init__(self, db: Session):
        self.repo = MeioPagamentoRepository(db)

    def list_all(self):
        return self.repo.list_all()

    def get(self, meio_pagamento_id: int):
        mp = self.repo.get(meio_pagamento_id)
        if not mp:
            raise HTTPException(status_code=404, detail="Meio de pagamento não encontrado")
        return mp

    def create(self, data: MeioPagamentoCreate):
        novo = MeioPagamentoModel(**data.dict())
        return self.repo.create(novo)

    def update(self, meio_pagamento_id: int, data: MeioPagamentoUpdate):
        mp = self.get(meio_pagamento_id)
        for field, value in data.dict(exclude_unset=True).items():
            setattr(mp, field, value)
        return self.repo.update(mp)

    def delete(self, meio_pagamento_id: int):
        mp = self.get(meio_pagamento_id)
        self.repo.delete(mp)
        return {"ok": True}
