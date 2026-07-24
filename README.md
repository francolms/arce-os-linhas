# Sistema de Controle de OS de Linhas — ARCE

Controle de alterações (tarifa, itinerário, seccionamento, frequência, horário,
inclusão/exclusão) das linhas reguladas pela ARCE, com histórico, vínculo às
normas que validaram cada mudança, fluxo de aprovação e relatórios em PDF.

## Fase 1 (atual)
Cadastro básico (sistemas, lotes, operadores, linhas, normas, usuários) e o
fluxo de alterações com bloqueio de edição concorrente por linha.

- `db/schema.sql` — schema Postgres (rodar no SQL Editor do Supabase)
- `app/` — aplicativo Streamlit (em construção)

## Configuração local
1. Criar `.env` (não versionado) com:
   ```
   SUPABASE_URL=...
   SUPABASE_KEY=...
   ```
2. `pip install -r requirements.txt`
3. `streamlit run app/main.py`
