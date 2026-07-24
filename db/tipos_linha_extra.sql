-- Tipos de Linha adicionais encontrados no CAPAS_CONSOLIDADO.csv (Diametral, Circular).
-- Nenhuma das 654 linhas vigentes atuais usa esses tipos hoje (so aparecem em codigos
-- antigos, fora do BASE_SISTEMA_LOTE.txt), mas ficam disponiveis para uso futuro.

insert into tipos_linha (nome) values ('Diametral') on conflict (nome) do nothing;
insert into tipos_linha (nome) values ('Circular') on conflict (nome) do nothing;
