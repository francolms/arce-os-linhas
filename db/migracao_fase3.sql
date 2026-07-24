-- ============================================================================
-- Fase 3: Seções (pontos da linha), Tarifas (matriz entre seções) e Horários.
-- Extensão = km_acumulado do ultimo ponto (calculado, nao digitado).
-- Frequência semanal = (viagens dia util x 5) + viagens sabado + viagens domingo.
-- ============================================================================

create table if not exists secoes (
    id              bigint generated always as identity primary key,
    linha_codigo    text not null references linhas(codigo),
    ordem           integer not null,
    nome            text not null,
    tipo_ponto      text not null default 'parada' check (tipo_ponto in ('parada', 'passagem')),
    km_acumulado    numeric,
    unique (linha_codigo, ordem)
);

create table if not exists tarifas (
    id                  bigint generated always as identity primary key,
    linha_codigo        text not null references linhas(codigo),
    secao_origem_id     bigint not null references secoes(id),
    secao_destino_id    bigint not null references secoes(id),
    valor               numeric not null,
    unique (linha_codigo, secao_origem_id, secao_destino_id)
);

-- "ida" = saida do primeiro ponto da linha (origem); "volta" = saida do
-- ultimo ponto (destino). Cada dia da semana e guardado separadamente,
-- igual ao quadro de horarios impresso na OS (SEG a DOM).
create table if not exists horarios (
    id              bigint generated always as identity primary key,
    linha_codigo    text not null references linhas(codigo),
    sentido         text not null check (sentido in ('ida', 'volta')),
    horario_saida   time not null,
    segunda         boolean not null default false,
    terca           boolean not null default false,
    quarta          boolean not null default false,
    quinta          boolean not null default false,
    sexta           boolean not null default false,
    sabado          boolean not null default false,
    domingo         boolean not null default false
);

create index if not exists idx_secoes_linha   on secoes (linha_codigo);
create index if not exists idx_tarifas_linha  on tarifas (linha_codigo);
create index if not exists idx_horarios_linha on horarios (linha_codigo);

alter table secoes   enable row level security;
alter table tarifas  enable row level security;
alter table horarios enable row level security;

create policy "secoes_autenticados"   on secoes   for all to authenticated using (true) with check (true);
create policy "tarifas_autenticados"  on tarifas  for all to authenticated using (true) with check (true);
create policy "horarios_autenticados" on horarios for all to authenticated using (true) with check (true);
