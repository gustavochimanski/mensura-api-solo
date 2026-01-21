-- ============================================================
-- MIGRAÇÃO: Configurações de Complemento na Vinculação
-- ============================================================
-- 
-- Esta migração move as configurações obrigatorio, minimo_itens e maximo_itens
-- da tabela complemento_produto para as tabelas de vinculação:
-- - produto_complemento_link
-- - receita_complemento_link  
-- - combo_complemento_link
--
-- Isso permite que o mesmo complemento tenha comportamentos diferentes
-- dependendo do item, receita ou combo ao qual está vinculado.
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
ADD COLUMN IF NOT EXISTS minimo_itens INTEGER,
ADD COLUMN IF NOT EXISTS maximo_itens INTEGER;

-- Adiciona colunas na tabela receita_complemento_link
ALTER TABLE catalogo.receita_complemento_link
ADD COLUMN IF NOT EXISTS obrigatorio BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS minimo_itens INTEGER,
ADD COLUMN IF NOT EXISTS maximo_itens INTEGER;

-- Adiciona colunas na tabela combo_complemento_link
ALTER TABLE catalogo.combo_complemento_link
ADD COLUMN IF NOT EXISTS obrigatorio BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS minimo_itens INTEGER,
ADD COLUMN IF NOT EXISTS maximo_itens INTEGER;

-- ============================================================
-- 2. MIGRAR DADOS EXISTENTES
-- ============================================================

-- Migra dados de produto_complemento_link
UPDATE catalogo.produto_complemento_link pcl
SET 
    obrigatorio = COALESCE(cp.obrigatorio, FALSE),
    minimo_itens = cp.minimo_itens,
    maximo_itens = cp.maximo_itens
FROM catalogo.complemento_produto cp
WHERE pcl.complemento_id = cp.id
  AND (pcl.obrigatorio IS NULL OR pcl.obrigatorio = FALSE);

-- Migra dados de receita_complemento_link
UPDATE catalogo.receita_complemento_link rcl
SET 
    obrigatorio = COALESCE(cp.obrigatorio, FALSE),
    minimo_itens = cp.minimo_itens,
    maximo_itens = cp.maximo_itens
FROM catalogo.complemento_produto cp
WHERE rcl.complemento_id = cp.id
  AND (rcl.obrigatorio IS NULL OR rcl.obrigatorio = FALSE);

-- Migra dados de combo_complemento_link
UPDATE catalogo.combo_complemento_link ccl
SET 
    obrigatorio = COALESCE(cp.obrigatorio, FALSE),
    minimo_itens = cp.minimo_itens,
    maximo_itens = cp.maximo_itens
FROM catalogo.complemento_produto cp
WHERE ccl.complemento_id = cp.id
  AND (ccl.obrigatorio IS NULL OR ccl.obrigatorio = FALSE);

-- ============================================================
-- 3. COMENTÁRIOS NAS COLUNAS (OPCIONAL - PostgreSQL)
-- ============================================================

COMMENT ON COLUMN catalogo.produto_complemento_link.obrigatorio IS 
    'Se o complemento é obrigatório para este produto específico (pode diferir do valor padrão do complemento)';

COMMENT ON COLUMN catalogo.produto_complemento_link.minimo_itens IS 
    'Quantidade mínima de itens para este produto específico (pode diferir do valor padrão do complemento)';

COMMENT ON COLUMN catalogo.produto_complemento_link.maximo_itens IS 
    'Quantidade máxima de itens para este produto específico (pode diferir do valor padrão do complemento)';

COMMENT ON COLUMN catalogo.receita_complemento_link.obrigatorio IS 
    'Se o complemento é obrigatório para esta receita específica (pode diferir do valor padrão do complemento)';

COMMENT ON COLUMN catalogo.receita_complemento_link.minimo_itens IS 
    'Quantidade mínima de itens para esta receita específica (pode diferir do valor padrão do complemento)';

COMMENT ON COLUMN catalogo.receita_complemento_link.maximo_itens IS 
    'Quantidade máxima de itens para esta receita específica (pode diferir do valor padrão do complemento)';

COMMENT ON COLUMN catalogo.combo_complemento_link.obrigatorio IS 
    'Se o complemento é obrigatório para este combo específico (pode diferir do valor padrão do complemento)';

COMMENT ON COLUMN catalogo.combo_complemento_link.minimo_itens IS 
    'Quantidade mínima de itens para este combo específico (pode diferir do valor padrão do complemento)';

COMMENT ON COLUMN catalogo.combo_complemento_link.maximo_itens IS 
    'Quantidade máxima de itens para este combo específico (pode diferir do valor padrão do complemento)';

-- ============================================================
-- 4. NOTA SOBRE COLUNAS NA TABELA COMPLEMENTO_PRODUTO
-- ============================================================
-- 
-- As colunas obrigatorio, minimo_itens e maximo_itens na tabela
-- complemento_produto podem ser mantidas como valores padrão
-- ou removidas no futuro. Por enquanto, são mantidas para
-- compatibilidade e como valores padrão quando não especificados
-- na vinculação.
--
-- Se desejar remover essas colunas no futuro, execute:
--
-- ALTER TABLE catalogo.complemento_produto
-- DROP COLUMN IF EXISTS obrigatorio,
-- DROP COLUMN IF EXISTS minimo_itens,
-- DROP COLUMN IF EXISTS maximo_itens;
--
-- ============================================================

COMMIT;

-- ============================================================
-- VERIFICAÇÃO PÓS-MIGRAÇÃO
-- ============================================================
-- 
-- Execute estas queries para verificar se a migração foi bem-sucedida:
--
-- -- Verifica se as colunas foram criadas
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_schema = 'catalogo'
--   AND table_name IN ('produto_complemento_link', 'receita_complemento_link', 'combo_complemento_link')
--   AND column_name IN ('obrigatorio', 'minimo_itens', 'maximo_itens')
-- ORDER BY table_name, column_name;
--
-- -- Verifica se os dados foram migrados
-- SELECT 
--     'produto_complemento_link' as tabela,
--     COUNT(*) as total,
--     COUNT(obrigatorio) as com_obrigatorio,
--     COUNT(minimo_itens) as com_minimo,
--     COUNT(maximo_itens) as com_maximo
-- FROM catalogo.produto_complemento_link
-- UNION ALL
-- SELECT 
--     'receita_complemento_link' as tabela,
--     COUNT(*) as total,
--     COUNT(obrigatorio) as com_obrigatorio,
--     COUNT(minimo_itens) as com_minimo,
--     COUNT(maximo_itens) as com_maximo
-- FROM catalogo.receita_complemento_link
-- UNION ALL
-- SELECT 
--     'combo_complemento_link' as tabela,
--     COUNT(*) as total,
--     COUNT(obrigatorio) as com_obrigatorio,
--     COUNT(minimo_itens) as com_minimo,
--     COUNT(maximo_itens) as com_maximo
-- FROM catalogo.combo_complemento_link;
--
-- ============================================================
