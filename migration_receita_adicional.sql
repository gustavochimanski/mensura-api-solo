-- Migration: Alterar coluna adicional_cod_barras para adicional_id na tabela receita_adicional
-- Data: 2025-01-18
-- Descrição: Migração da estrutura de adicionais em receitas para usar adicional_id (FK para adicional_produto)
--            ao invés de adicional_cod_barras (FK para produtos)

BEGIN;

-- 1. Verificar se a coluna adicional_cod_barras existe
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'catalogo' 
        AND table_name = 'receita_adicional' 
        AND column_name = 'adicional_cod_barras'
    ) THEN
        -- 2. Verificar se já existe a coluna adicional_id (caso a migration já tenha sido executada parcialmente)
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'catalogo' 
            AND table_name = 'receita_adicional' 
            AND column_name = 'adicional_id'
        ) THEN
            -- 3. Adicionar nova coluna adicional_id
            ALTER TABLE catalogo.receita_adicional 
            ADD COLUMN adicional_id INTEGER;

            -- 4. Migrar dados: converter cod_barras para id do adicional
            -- Estratégia: Tentar diferentes formas de correspondência
            
            -- Opção 1: Se cod_barras for numérico e corresponder a um id em adicional_produto
            UPDATE catalogo.receita_adicional ra
            SET adicional_id = CAST(ra.adicional_cod_barras AS INTEGER)
            WHERE ra.adicional_cod_barras ~ '^[0-9]+$'
            AND EXISTS (
                SELECT 1 
                FROM catalogo.adicional_produto ap 
                WHERE ap.id = CAST(ra.adicional_cod_barras AS INTEGER)
            )
            AND ra.adicional_id IS NULL;

            -- Opção 2: Se cod_barras corresponder a um produto que tem relação com adicional
            -- (caso os cod_barras sejam de produtos vinculados a adicionais)
            -- Esta parte pode ser ajustada conforme sua estrutura de dados
            
            -- Verificar quantos registros não foram migrados
            DO $$
            DECLARE
                nao_migrados INTEGER;
            BEGIN
                SELECT COUNT(*) INTO nao_migrados
                FROM catalogo.receita_adicional
                WHERE adicional_id IS NULL;
                
                IF nao_migrados > 0 THEN
                    RAISE WARNING 'Existem % registros que não puderam ser migrados automaticamente. Verifique manualmente antes de continuar.', nao_migrados;
                    RAISE EXCEPTION 'Migration interrompida: existem registros não migrados. Corrija os dados e execute novamente.';
                END IF;
            END $$;

            -- 5. Tornar a coluna NOT NULL (só se todos foram migrados)
            ALTER TABLE catalogo.receita_adicional 
            ALTER COLUMN adicional_id SET NOT NULL;

            -- 6. Adicionar Foreign Key
            ALTER TABLE catalogo.receita_adicional 
            ADD CONSTRAINT fk_receita_adicional_adicional_id 
            FOREIGN KEY (adicional_id) 
            REFERENCES catalogo.adicional_produto(id) 
            ON DELETE RESTRICT;

            -- 7. Adicionar índice para melhor performance
            CREATE INDEX IF NOT EXISTS idx_receita_adicional_adicional_id 
            ON catalogo.receita_adicional(adicional_id);

            -- 8. Remover a coluna antiga adicional_cod_barras
            -- Primeiro, remover a Foreign Key antiga se existir
            ALTER TABLE catalogo.receita_adicional 
            DROP CONSTRAINT IF EXISTS receita_adicional_adicional_cod_barras_fkey;

            -- Depois, remover a coluna
            ALTER TABLE catalogo.receita_adicional 
            DROP COLUMN adicional_cod_barras;

            RAISE NOTICE 'Migration concluída: coluna adicional_cod_barras alterada para adicional_id';
        ELSE
            RAISE NOTICE 'Migration já executada: coluna adicional_id já existe';
        END IF;
    ELSE
        RAISE NOTICE 'Coluna adicional_cod_barras não encontrada. Verifique se a migration já foi executada ou se a estrutura está diferente.';
    END IF;
END $$;

COMMIT;

-- Verificação pós-migration
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'catalogo' 
AND table_name = 'receita_adicional'
ORDER BY ordinal_position;

