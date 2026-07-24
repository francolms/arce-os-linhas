-- ============================================================================
-- Fase 1b: perfis de usuário + listas padronizadas (Tipo da Linha / Espécie)
-- ============================================================================

-- Perfil do usuário (controla o que cada um pode fazer no app)
alter table usuarios add column if not exists perfil text not null default 'editor'
    check (perfil in ('administrador', 'editor'));

-- Listas padronizadas: só administrador cadastra/edita/exclui os valores
create table if not exists tipos_linha (
    id   bigint generated always as identity primary key,
    nome text not null unique
);

create table if not exists especies_servico (
    id   bigint generated always as identity primary key,
    nome text not null unique
);

insert into tipos_linha (nome) values ('Radial'), ('Regional')
    on conflict (nome) do nothing;

insert into especies_servico (nome) values ('Convencional'), ('Executivo')
    on conflict (nome) do nothing;

alter table tipos_linha      enable row level security;
alter table especies_servico enable row level security;

create policy "tipos_linha_autenticados"      on tipos_linha      for all to authenticated using (true) with check (true);
create policy "especies_servico_autenticados" on especies_servico for all to authenticated using (true) with check (true);

-- Linhas passam a referenciar as listas padronizadas em vez de texto livre.
-- (os dois campos de teste que você já cadastrou vão precisar ser reinformados)
alter table linhas drop column if exists tipo_linha;
alter table linhas drop column if exists especie_servico;
alter table linhas add column if not exists tipo_linha_id bigint references tipos_linha(id);
alter table linhas add column if not exists especie_servico_id bigint references especies_servico(id);

-- Rode este UPDATE trocando o e-mail para se tornar administrador:
-- update usuarios set perfil = 'administrador' where email = 'francolms@gmail.com';
