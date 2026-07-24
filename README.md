# Sistema de Controle de OS de Linhas — ARCE

Controle de alterações (tarifa, itinerário, seccionamento, frequência, horário,
inclusão/exclusão) das linhas reguladas pela ARCE, com histórico, vínculo às
normas que validaram cada mudança, fluxo de aprovação e relatórios em PDF.

## Fase 1 (atual)
Cadastro básico (sistemas, lotes, operadores, linhas, normas, usuários).
O fluxo de alterações com bloqueio de edição concorrente por linha (tabela
`alteracoes`) já existe no schema, a tela vem na Fase 2.

- `db/schema.sql` — schema Postgres (rodar no SQL Editor do Supabase)
- `db/rls.sql` — políticas de segurança (rodar depois do schema)
- `app/Home.py` — aplicativo Streamlit

## Deploy (Streamlit Community Cloud)
1. Em share.streamlit.io → New app → repositório `francolms/arce-os-linhas`,
   branch `main`, main file path `app/Home.py`.
2. Em Settings > Secrets do app, adicionar:
   ```
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "chave anon do projeto (Settings > API no Supabase)"
   ```
3. Criar os usuários que poderão logar em Supabase > Authentication > Users > Add user.

## Configuração local (opcional)
1. Criar `.env` (não versionado) com:
   ```
   SUPABASE_URL=...
   SUPABASE_KEY=...
   ```
2. `pip install -r requirements.txt`
3. `streamlit run app/Home.py`
