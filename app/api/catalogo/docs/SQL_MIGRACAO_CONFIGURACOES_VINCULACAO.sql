-- ============================================================
-- MIGRAÇÃO: Configurações de Complemento na Vinculação
-- ============================================================
-- 
-- Esta migração move TODAS as configurações (obrigatorio, quantitativo, 
-- minimo_itens e maximo_itens) da tabela complemento_produto para as 
-- tabelas de vinculação:
-- - produto_complemento_link
-- - receita_complemento_link  
-- - combo_complemento_link
--
-- Isso permite que o mesmo complemento tenha comportamentos diferentes
-- dependendo do item, receita ou combo ao qual está vinculado.
--
-- IMPORTANTE: Após esta migração, essas configurações NÃO existem mais
-- na tabela complemento_produto e DEVEM ser definidas na vinculação.
--
-- Data: 2024
-- ============================================================

BEGIN;

-- ============================================================
-- 1. ADICIONAR COLUNAS NAS TABELAS DE VINCULAÇÃO
-- ============================================================

-- Adiciona colunas na tabela produto_complemento_link
ALTER TABLE catalogo.produto_complemento_link
ADD COLUMN IF NOT EXISTS obrigatorio BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS quantitativo BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS minimo_itens INTEGER,
ADD COLUMN IF NOT EXISTS maximo_itens INTEGER;

-- Adiciona colunas na tabela receita_complemento_link
ALTER TABLE catalogo.receita_complemento_link
ADD COLUMN IF NOT EXISTS obrigatorio BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS quantitativo BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS minimo_itens INTEGER,
ADD COLUMN IF NOT EXISTS maximo_itens INTEGER;

-- Adiciona colunas na tabela combo_complemento_link
ALTER TABLE catalogo.combo_complemento_link
ADD COLUMN IF NOT EXISTS obrigatorio BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS quantitativo BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS minimo_itens INTEGER,
ADD COLUMN IF NOT EXISTS maximo_itens INTEGER;

-- ============================================================
-- 2. MIGRAR DADOS EXISTENTES
-- ============================================================

-- Migra dados de produto_complemento_link
UPDATE catalogo.produto_complemento_link pcl
SET 
    obrigatorio = COALESCE(cp.obrigatorio, FALSE),
    quantitativo = COALESCE(cp.quantitativo, FALSE),
    minimo_itens = cp.minimo_itens,
    maximo_itens = cp.maximo_itens
FROM catalogo.complemento_produto cp
WHERE pcl.complemento_id = cp.id
  AND (pcl.obrigatorio IS NULL OR pcl.obrigatorio = FALSE);

-- Migra dados de receita_complemento_link
UPDATE catalogo.receita_complemento_link rcl
SET 
    obrigatorio = COALESCE(cp.obrigatorio, FALSE),
    quantitativo = COALESCE(cp.quantitativo, FALSE),
    minimo_itens = cp.minimo_itens,
    maximo_itens = cp.maximo_itens
FROM catalogo.complemento_produto cp
WHERE rcl.complemento_id = cp.id
  AND (rcl.obrigatorio IS NULL OR rcl.obrigatorio = FALSE);

-- Migra dados de combo_complemento_link
UPDATE catalogo.combo_complemento_link ccl
SET 
    obrigatorio = COALESCE(cp.obrigatorio, FALSE),
    quantitativo = COALESCE(cp.quantitativo, FALSE),
    minimo_itens = cp.minimo_itens,
    maximo_itens = cp.maximo_itens
FROM catalogo.complemento_produto cp
WHERE ccl.complemento_id = cp.id
  AND (ccl.obrigatorio IS NULL OR ccl.obrigatorio = FALSE);

-- ============================================================
-- 3. COMENTÁRIOS NAS COLUNAS (OPCIONAL - PostgreSQL)
-- ============================================================

COMMENT ON COLUMN catalogo.produto_complemento_link.obrigatorio IS 
    'Se o complemento é obrigatório para este produto específico';

COMMENT ON COLUMN catalogo.produto_complemento_link.quantitativo IS 
    'Se permite quantidade (ex: 2x bacon) e múltipla escolha para este produto específico';

COMMENT ON COLUMN catalogo.produto_complemento_link.minimo_itens IS 
    'Quantidade mínima de itens para este produto específico';

COMMENT ON COLUMN catalogo.produto_complemento_link.maximo_itens IS 
    'Quantidade máxima de itens para este produto específico';

COMMENT ON COLUMN catalogo.receita_complemento_link.obrigatorio IS 
    'Se o complemento é obrigatório para esta receita específica';

COMMENT ON COLUMN catalogo.receita_complemento_link.quantitativo IS 
    'Se permite quantidade (ex: 2x bacon) e múltipla escolha para esta receita específica';

COMMENT ON COLUMN catalogo.receita_complemento_link.minimo_itens IS 
    'Quantidade mínima de itens para esta receita específica';

COMMENT ON COLUMN catalogo.receita_complemento_link.maximo_itens IS 
    'Quantidade máxima de itens para esta receita específica';

COMMENT ON COLUMN catalogo.combo_complemento_link.obrigatorio IS 
    'Se o complemento é obrigatório para este combo específico';

COMMENT ON COLUMN catalogo.combo_complemento_link.quantitativo IS 
    'Se permite quantidade (ex: 2x bacon) e múltipla escolha para este combo específico';

COMMENT ON COLUMN catalogo.combo_complemento_link.minimo_itens IS 
    'Quantidade mínima de itens para este combo específico';

COMMENT ON COLUMN catalogo.combo_complemento_link.maximo_itens IS 
    'Quantidade máxima de itens para este combo específico';

-- ============================================================
-- 4. REMOVER COLUNAS DA TABELA COMPLEMENTO_PRODUTO
-- ============================================================
-- 
-- Remove as colunas obrigatorio, quantitativo, minimo_itens e maximo_itens
-- da tabela complemento_produto, pois agora essas configurações existem
-- APENAS nas tabelas de vinculação.
--
-- IMPORTANTE: Execute esta parte APÓS migrar os dados e verificar que
-- tudo está funcionando corretamente.
--
-- ============================================================

-- Remove as colunas da tabela complemento_produto
ALTER TABLE catalogo.complemento_produto
DROP COLUMN IF EXISTS obrigatorio,
DROP COLUMN IF EXISTS quantitativo,
DROP COLUMN IF EXISTS minimo_itens,
DROP COLUMN IF EXISTS maximo_itens;

COMMIT;

-- ============================================================
-- VERIFICAÇÃO PÓS-MIGRAÇÃO
-- ============================================================
-- 
-- Execute estas queries para verificar se a migração foi bem-sucedida:
--
-- -- Verifica se as colunas foram criadas nas tabelas de vinculação
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_schema = 'catalogo'
--   AND table_name IN ('produto_complemento_link', 'receita_complemento_link', 'combo_complemento_link')
--   AND column_name IN ('obrigatorio', 'quantitativo', 'minimo_itens', 'maximo_itens')
-- ORDER BY table_name, column_name;
--
-- -- Verifica se as colunas foram removidas da tabela complemento_produto
-- SELECT column_name
-- FROM information_schema.columns
-- WHERE table_schema = 'catalogo'
--   AND table_name = 'complemento_produto'
--   AND column_name IN ('obrigatorio', 'quantitativo', 'minimo_itens', 'maximo_itens');
-- -- Deve retornar 0 linhas
--
-- -- Verifica se os dados foram migrados
-- SELECT 
--     'produto_complemento_link' as tabela,
--     COUNT(*) as total,
--     COUNT(obrigatorio) as com_obrigatorio,
--     COUNT(quantitativo) as com_quantitativo,
--     COUNT(minimo_itens) as com_minimo,
--     COUNT(maximo_itens) as com_maximo
-- FROM catalogo.produto_complemento_link
-- UNION ALL
-- SELECT 
--     'receita_complemento_link' as tabela,
--     COUNT(*) as total,
--     COUNT(obrigatorio) as com_obrigatorio,
--     COUNT(quantitativo) as com_quantitativo,
--     COUNT(minimo_itens) as com_minimo,
--     COUNT(maximo_itens) as com_maximo
-- FROM catalogo.receita_complemento_link
-- UNION ALL
-- SELECT 
--     'combo_complemento_link' as tabela,
--     COUNT(*) as total,
--     COUNT(obrigatorio) as com_obrigatorio,
--     COUNT(quantitativo) as com_quantitativo,
--     COUNT(minimo_itens) as com_minimo,
--     COUNT(maximo_itens) as com_maximo
-- FROM catalogo.combo_complemento_link;
--
-- ============================================================
