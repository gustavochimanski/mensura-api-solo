-- Remove colunas de nomes do schema pedidos.
-- Os nomes devem vir do catálogo via FK/relationship:
-- - pedidos.pedidos_itens_complementos.complemento_id -> catalogo.complemento_produto.nome
-- - pedidos.pedidos_itens_complementos_adicionais.adicional_id -> catalogo.adicionais.nome

ALTER TABLE IF EXISTS pedidos.pedidos_itens_complementos
    DROP COLUMN IF EXISTS complemento_nome;

ALTER TABLE IF EXISTS pedidos.pedidos_itens_complementos_adicionais
    DROP COLUMN IF EXISTS nome;

