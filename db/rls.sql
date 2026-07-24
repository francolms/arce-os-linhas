-- ============================================================================
-- Habilita Row Level Security e libera acesso completo para usuários logados.
-- Sem isso, a chave "anon" do Supabase (que fica no app) teria acesso livre
-- às tabelas para qualquer pessoa que a obtivesse, mesmo sem logar no app.
-- ============================================================================

alter table usuarios    enable row level security;
alter table sistemas    enable row level security;
alter table lotes       enable row level security;
alter table operadores  enable row level security;
alter table normas      enable row level security;
alter table linhas      enable row level security;
alter table alteracoes  enable row level security;

create policy "usuarios_autenticados"   on usuarios   for all to authenticated using (true) with check (true);
create policy "sistemas_autenticados"   on sistemas   for all to authenticated using (true) with check (true);
create policy "lotes_autenticados"      on lotes      for all to authenticated using (true) with check (true);
create policy "operadores_autenticados" on operadores for all to authenticated using (true) with check (true);
create policy "normas_autenticados"     on normas     for all to authenticated using (true) with check (true);
create policy "linhas_autenticados"     on linhas     for all to authenticated using (true) with check (true);
create policy "alteracoes_autenticados" on alteracoes for all to authenticated using (true) with check (true);
