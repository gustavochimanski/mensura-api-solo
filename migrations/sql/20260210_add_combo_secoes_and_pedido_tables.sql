-- SQL migration: cria tabelas combo_secoes (catalogo), combo_secoes_itens (catalogo)
-- e pedido_item_combo_secoes / pedido_item_combo_secoes_itens (pedidos)

CREATE SCHEMA IF NOT EXISTS catalogo;
CREATE SCHEMA IF NOT EXISTS pedidos;

-- tabela: catalogo.combo_secoes
CREATE TABLE IF NOT EXISTS catalogo.combo_secoes (
    id SERIAL PRIMARY KEY,
    combo_id INTEGER NOT NULL REFERENCES catalogo.combos(id) ON DELETE CASCADE,
    titulo VARCHAR(120) NOT NULL,
    descricao VARCHAR(255),
    obrigatorio BOOLEAN NOT NULL DEFAULT FALSE,
    quantitativo BOOLEAN NOT NULL DEFAULT FALSE,
    minimo_itens INTEGER NOT NULL DEFAULT 0,
    maximo_itens INTEGER NOT NULL DEFAULT 1,
    ordem INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_combo_secoes_combo_id ON catalogo.combo_secoes(combo_id);

-- tabela: catalogo.combo_secoes_itens
CREATE TABLE IF NOT EXISTS catalogo.combo_secoes_itens (
    id SERIAL PRIMARY KEY,
    secao_id INTEGER NOT NULL REFERENCES catalogo.combo_secoes(id) ON DELETE CASCADE,
    produto_id INTEGER REFERENCES catalogo.produtos(id) ON DELETE RESTRICT,
    produto_cod_barras TEXT,
    receita_id INTEGER REFERENCES catalogo.receitas(id) ON DELETE RESTRICT,
    ordem INTEGER NOT NULL DEFAULT 0,
    preco_incremental NUMERIC(18,2) NOT NULL DEFAULT 0,
    permite_quantidade BOOLEAN NOT NULL DEFAULT FALSE,
    quantidade_min INTEGER NOT NULL DEFAULT 1,
    quantidade_max INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT ck_combo_secao_item_exatamente_um_tipo CHECK (
        (CASE WHEN (produto_id IS NOT NULL OR produto_cod_barras IS NOT NULL) THEN 1 ELSE 0 END) +
        (CASE WHEN receita_id IS NOT NULL THEN 1 ELSE 0 END) = 1
    )
);
CREATE INDEX IF NOT EXISTS ix_combo_secoes_itens_secao_id ON catalogo.combo_secoes_itens(secao_id);
CREATE INDEX IF NOT EXISTS ix_combo_secoes_itens_produto_cod_barras ON catalogo.combo_secoes_itens(produto_cod_barras);

-- tabela: pedidos.pedido_item_combo_secoes
CREATE TABLE IF NOT EXISTS pedidos.pedido_item_combo_secoes (
    id SERIAL PRIMARY KEY,
    pedido_item_id INTEGER NOT NULL REFERENCES pedidos.pedido_item_unificado(id) ON DELETE CASCADE,
    secao_id INTEGER REFERENCES catalogo.combo_secoes(id) ON DELETE SET NULL,
    secao_titulo_snapshot VARCHAR(120),
    ordem INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pedido_item_combo_secoes_pedido_item_id ON pedidos.pedido_item_combo_secoes(pedido_item_id);

-- tabela: pedidos.pedido_item_combo_secoes_itens
CREATE TABLE IF NOT EXISTS pedidos.pedido_item_combo_secoes_itens (
    id SERIAL PRIMARY KEY,
    pedido_item_secao_id INTEGER NOT NULL REFERENCES pedidos.pedido_item_combo_secoes(id) ON DELETE CASCADE,
    combo_secoes_item_id INTEGER REFERENCES catalogo.combo_secoes_itens(id) ON DELETE SET NULL,
    produto_cod_barras_snapshot TEXT,
    receita_id_snapshot INTEGER,
    preco_incremental_snapshot NUMERIC(18,2) NOT NULL DEFAULT 0,
    quantidade INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pedido_item_combo_secoes_itens_pedido_item_secao_id ON pedidos.pedido_item_combo_secoes_itens(pedido_item_secao_id);

-- Fim do script

