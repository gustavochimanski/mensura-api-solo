from sqlalchemy.orm import Session

from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self):
        return self.db.query(MeioPagamentoModel).order_by(MeioPagamentoModel.id).all()

    def get(self, meio_pagamento_id: int):
        return self.db.query(MeioPagamentoModel).filter(MeioPagamentoModel.id == meio_pagamento_id).first()

    def create(self, meio_pagamento: MeioPagamentoModel):
        self.db.add(meio_pagamento)
        self.db.commit()
        self.db.refresh(meio_pagamento)
        return meio_pagamento

    def update(self, meio_pagamento: MeioPagamentoModel):
        self.db.commit()
        self.db.refresh(meio_pagamento)
        return meio_pagamento

    def delete(self, meio_pagamento: MeioPagamentoModel):
        self.db.delete(meio_pagamento)
        self.db.commit()
