-- Migração: Suportar receitas como ingredientes de outras receitas
-- Data: 2026-01-11
-- Descrição: Permite que receitas sejam vinculadas como ingredientes de outras receitas,
--             além dos ingredientes básicos já suportados.

-- 1. Tornar ingrediente_id nullable (permitir NULL quando receita_ingrediente_id estiver preenchido)
ALTER TABLE catalogo.receita_ingrediente 
    ALTER COLUMN ingrediente_id DROP NOT NULL;

-- 2. Adicionar coluna receita_ingrediente_id para suportar sub-receitas
ALTER TABLE catalogo.receita_ingrediente 
    ADD COLUMN receita_ingrediente_id INTEGER;

-- 3. Adicionar foreign key para receita_ingrediente_id
ALTER TABLE catalogo.receita_ingrediente 
    ADD CONSTRAINT fk_receita_ingrediente_receita 
    FOREIGN KEY (receita_ingrediente_id) 
    REFERENCES catalogo.receitas(id) 
    ON DELETE RESTRICT;

-- 4. Adicionar constraint CHECK para garantir que exatamente um dos campos seja preenchido
--    (ingrediente_id OU receita_ingrediente_id, mas não ambos e não nenhum)
ALTER TABLE catalogo.receita_ingrediente 
    ADD CONSTRAINT chk_receita_ingrediente_exactly_one 
    CHECK (
        (ingrediente_id IS NOT NULL AND receita_ingrediente_id IS NULL) OR
        (ingrediente_id IS NULL AND receita_ingrediente_id IS NOT NULL)
    );

-- 5. Adicionar índice para melhorar performance de consultas por receita_ingrediente_id
CREATE INDEX IF NOT EXISTS idx_receita_ingrediente_receita_ingrediente_id 
    ON catalogo.receita_ingrediente(receita_ingrediente_id);

-- 6. Adicionar constraint para evitar referências circulares diretas
--    (uma receita não pode ser ingrediente de si mesma)
--    Nota: Esta validação também deve ser feita na aplicação, mas a constraint ajuda
--    A constraint CHECK não pode referenciar a mesma linha, então isso será validado na aplicação

COMMENT ON COLUMN catalogo.receita_ingrediente.receita_ingrediente_id IS 
    'ID da receita usada como ingrediente. Deve ser NULL se ingrediente_id estiver preenchido.';
