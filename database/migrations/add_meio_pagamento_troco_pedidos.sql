-- Migration: Adicionar campos meio_pagamento_id e troco_para nas tabelas de pedidos
-- Data: 2025-11-22
-- Descrição: Adiciona suporte para meio de pagamento e troco nos pedidos de mesa e balcão

-- ============================================
-- PEDIDOS DE MESA (mesas.pedidos_mesa)
-- ============================================

-- Adiciona coluna meio_pagamento_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'mesas' 
        AND table_name = 'pedidos_mesa' 
        AND column_name = 'meio_pagamento_id'
    ) THEN
        ALTER TABLE mesas.pedidos_mesa 
        ADD COLUMN meio_pagamento_id INTEGER 
        REFERENCES cadastros.meios_pagamento(id) ON DELETE SET NULL;
        
        RAISE NOTICE 'Coluna meio_pagamento_id adicionada em mesas.pedidos_mesa';
    ELSE
        RAISE NOTICE 'Coluna meio_pagamento_id já existe em mesas.pedidos_mesa';
    END IF;
END $$;

-- Adiciona coluna troco_para
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'mesas' 
        AND table_name = 'pedidos_mesa' 
        AND column_name = 'troco_para'
    ) THEN
        ALTER TABLE mesas.pedidos_mesa 
        ADD COLUMN troco_para NUMERIC(18, 2) NULL;
        
        RAISE NOTICE 'Coluna troco_para adicionada em mesas.pedidos_mesa';
    ELSE
        RAISE NOTICE 'Coluna troco_para já existe em mesas.pedidos_mesa';
    END IF;
END $$;

-- ============================================
-- PEDIDOS DE BALCÃO (balcao.pedidos_balcao)
-- ============================================

-- Adiciona coluna meio_pagamento_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'balcao' 
        AND table_name = 'pedidos_balcao' 
        AND column_name = 'meio_pagamento_id'
    ) THEN
        ALTER TABLE balcao.pedidos_balcao 
        ADD COLUMN meio_pagamento_id INTEGER 
        REFERENCES cadastros.meios_pagamento(id) ON DELETE SET NULL;
        
        RAISE NOTICE 'Coluna meio_pagamento_id adicionada em balcao.pedidos_balcao';
    ELSE
        RAISE NOTICE 'Coluna meio_pagamento_id já existe em balcao.pedidos_balcao';
    END IF;
END $$;

-- Adiciona coluna troco_para
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'balcao' 
        AND table_name = 'pedidos_balcao' 
        AND column_name = 'troco_para'
    ) THEN
        ALTER TABLE balcao.pedidos_balcao 
        ADD COLUMN troco_para NUMERIC(18, 2) NULL;
        
        RAISE NOTICE 'Coluna troco_para adicionada em balcao.pedidos_balcao';
    ELSE
        RAISE NOTICE 'Coluna troco_para já existe em balcao.pedidos_balcao';
    END IF;
END $$;

-- ============================================
-- VERIFICAÇÃO FINAL
-- ============================================

DO $$
DECLARE
    colunas_mesa INTEGER;
    colunas_balcao INTEGER;
BEGIN
    -- Verifica colunas em mesas.pedidos_mesa
    SELECT COUNT(*) INTO colunas_mesa
    FROM information_schema.columns 
    WHERE table_schema = 'mesas' 
    AND table_name = 'pedidos_mesa' 
    AND column_name IN ('meio_pagamento_id', 'troco_para');
    
    -- Verifica colunas em balcao.pedidos_balcao
    SELECT COUNT(*) INTO colunas_balcao
    FROM information_schema.columns 
    WHERE table_schema = 'balcao' 
    AND table_name = 'pedidos_balcao' 
    AND column_name IN ('meio_pagamento_id', 'troco_para');
    
    IF colunas_mesa = 2 AND colunas_balcao = 2 THEN
        RAISE NOTICE '✅ Migration concluída com sucesso! Todas as colunas foram adicionadas.';
    ELSE
        RAISE WARNING '⚠️ Algumas colunas podem não ter sido adicionadas. Verifique manualmente.';
        RAISE WARNING 'Colunas em mesas.pedidos_mesa: %', colunas_mesa;
        RAISE WARNING 'Colunas em balcao.pedidos_balcao: %', colunas_balcao;
    END IF;
END $$;

