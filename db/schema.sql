-- ============================================================================
-- Fase 1: cadastro básico + fluxo de alterações
-- Sistema de Controle de OS de Linhas - ARCE
-- ============================================================================

create table if not exists usuarios (
    id            bigint generated always as identity primary key,
    nome          text not null,
    email         text not null unique,
    criado_em     timestamptz not null default now()
);

create table if not exists sistemas (
    id            bigint generated always as identity primary key,
    nome          text not null unique
);

create table if not exists lotes (
    id            bigint generated always as identity primary key,
    sistema_id    bigint not null references sistemas(id),
    nome          text not null,
    unique (sistema_id, nome)
);

create table if not exists operadores (
    id            bigint generated always as identity primary key,
    nome          text not null unique,
    cnpj          text
);

create table if not exists normas (
    id                  bigint generated always as identity primary key,
    tipo                text not null,          -- OS, Portaria, Resolução, etc.
    numero              text not null,
    data_publicacao     date,
    arquivo_url         text,                   -- PDF no Supabase Storage
    descricao           text,
    escopo_sistema_id   bigint references sistemas(id),
    escopo_lote_id      bigint references lotes(id),
    criado_em           timestamptz not null default now()
);

create table if not exists linhas (
    codigo              text primary key,
    nome                text not null,
    especie_servico     text,
    tipo_linha          text,
    sistema_id          bigint references sistemas(id),
    lote_id             bigint references lotes(id),
    operador_id         bigint references operadores(id),
    status              text not null default 'ativa'
                        check (status in ('ativa', 'suspensa', 'excluida')),
    atualizado_em       timestamptz not null default now()
);

-- Evento central: toda alteração proposta em uma linha, do rascunho até a
-- vigência confirmada pela norma publicada.
create table if not exists alteracoes (
    id                    bigint generated always as identity primary key,
    linha_codigo          text not null references linhas(codigo),
    tipo_alteracao        text not null check (tipo_alteracao in (
                              'tarifa', 'itinerario', 'seccionamento',
                              'frequencia', 'horario', 'cadastral',
                              'inclusao', 'exclusao')),
    campo                 text,                 -- ex.: 'nome', 'operador_id' (quando cadastral)
    valor_anterior        jsonb,
    valor_novo            jsonb,
    status                text not null default 'rascunho' check (status in (
                              'rascunho', 'enviada_aprovacao',
                              'aprovada_aguardando_norma',
                              'concluida', 'cancelada')),
    norma_id              bigint references normas(id),
    data_vigencia         date,
    usuario_criador_id    bigint not null references usuarios(id),
    usuario_conclusao_id  bigint references usuarios(id),
    observacao            text,
    criado_em             timestamptz not null default now(),
    concluido_em          timestamptz
);

-- Trava: só pode existir 1 alteração "aberta" (não concluída/cancelada) por linha.
create unique index if not exists uma_alteracao_aberta_por_linha
    on alteracoes (linha_codigo)
    where status not in ('concluida', 'cancelada');

create index if not exists idx_alteracoes_linha on alteracoes (linha_codigo);
create index if not exists idx_alteracoes_status on alteracoes (status);
