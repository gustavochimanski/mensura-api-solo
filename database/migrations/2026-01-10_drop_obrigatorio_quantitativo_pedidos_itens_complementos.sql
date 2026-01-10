-- Remove colunas que não são necessárias para o registro de relacionamento
-- Tabela: pedidos.pedidos_itens_complementos
--
-- Observação:
-- - `obrigatorio` e `quantitativo` pertencem ao catálogo (complemento_produto)
-- - No pedido, persistimos apenas o vínculo (item <-> complemento) e seus adicionais selecionados

ALTER TABLE IF EXISTS pedidos.pedidos_itens_complementos
    DROP COLUMN IF EXISTS obrigatorio;

ALTER TABLE IF EXISTS pedidos.pedidos_itens_complementos
    DROP COLUMN IF EXISTS quantitativo;

