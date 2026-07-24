-- ============================================================================
-- Remove o cadastro separado de Normas: os dados da norma (quando houver)
-- passam a ser informados direto no popup de "Concluir" de uma OS, e ficam
-- gravados na propria linha de alteracoes.
-- ============================================================================

alter table alteracoes drop column if exists norma_id;
alter table alteracoes add column if not exists norma_tipo text;
alter table alteracoes add column if not exists norma_numero text;
alter table alteracoes add column if not exists norma_data_publicacao date;

drop table if exists normas;
