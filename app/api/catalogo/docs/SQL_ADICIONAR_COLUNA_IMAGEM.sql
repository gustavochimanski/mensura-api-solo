-- ============================================================
-- SQL: Adicionar Coluna IMAGEM nas Tabelas RECEITAS e COMBOS
-- ============================================================
-- Descrição: Adiciona a coluna 'imagem' nas tabelas de receitas
--            e combos do schema 'catalogo', se ela não existir.
-- 
-- Data: 2024-01-20
-- ============================================================

-- ============================================================
-- 1. ADICIONAR COLUNA IMAGEM NA TABELA RECEITAS
-- ============================================================

-- Verifica se a coluna existe antes de adicionar (PostgreSQL)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'catalogo'
        AND table_name = 'receitas'
        AND column_name = 'imagem'
    ) THEN
        ALTER TABLE catalogo.receitas
        ADD COLUMN imagem VARCHAR(500) NULL;
        
        COMMENT ON COLUMN catalogo.receitas.imagem IS 
        'URL pública da imagem da receita armazenada no MinIO';
    END IF;
END $$;

-- ============================================================
-- 2. ADICIONAR COLUNA IMAGEM NA TABELA COMBOS
-- ============================================================

-- Verifica se a coluna existe antes de adicionar (PostgreSQL)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'catalogo'
        AND table_name = 'combos'
        AND column_name = 'imagem'
    ) THEN
        ALTER TABLE catalogo.combos
        ADD COLUMN imagem VARCHAR(255) NULL;
        
        COMMENT ON COLUMN catalogo.combos.imagem IS 
        'URL pública da imagem do combo armazenada no MinIO';
    END IF;
END $$;

-- ============================================================
-- 3. VERIFICAÇÃO (Opcional - para confirmar que foi aplicado)
-- ============================================================

-- Verificar se as colunas foram criadas
SELECT 
    table_schema,
    table_name,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'catalogo'
AND table_name IN ('receitas', 'combos')
AND column_name = 'imagem'
ORDER BY table_name;

-- ============================================================
-- ALTERNATIVA: SQL SIMPLES (sem verificação prévia)
-- Use apenas se preferir uma abordagem mais direta
-- ============================================================

/*
-- Para Receitas
ALTER TABLE catalogo.receitas
ADD COLUMN IF NOT EXISTS imagem VARCHAR(500) NULL;

-- Para Combos
ALTER TABLE catalogo.combos
ADD COLUMN IF NOT EXISTS imagem VARCHAR(255) NULL;
*/

-- ============================================================
-- NOTAS:
-- ============================================================
-- 1. As colunas são NULLABLE (permitem valores nulos)
-- 2. Tamanho da coluna:
--    - receitas.imagem: VARCHAR(500) - URLs podem ser longas
--    - combos.imagem: VARCHAR(255) - URLs padrão
-- 3. Os endpoints de upload já estão implementados e 
--    funcionarão automaticamente após a aplicação deste SQL
-- 4. Para ambientes de produção, execute este script durante
--    uma janela de manutenção ou quando não houver tráfego
-- ============================================================
