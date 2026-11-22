-- 002_server_writes.sql: only the server adds prompt events and recordings.
-- Run once in each Supabase project's SQL Editor: dev first, then prod.
-- Before running: SUPABASE_SECRET_KEY must be set where the server runs
-- (repo-root .env for dev, Render for prod), or nothing can be saved.
-- Never edit this file after it has run; changes go in 003_...
--
-- Why: 001 let a signed-in user add their own rows. The publishable key is
-- public, so a user could skip the server and write recordings with made-up
-- metrics. Now the server checks who the user is and writes the row itself
-- with the secret key (which bypasses RLS). Users can still read their own rows.

drop policy "own prompt events: add" on public.prompt_events;
drop policy "own recordings: add, after consent" on public.recordings;

revoke insert on public.prompt_events, public.recordings from authenticated;

-- The server always supplies user_id. With no default, a row without one is refused.
alter table public.prompt_events alter column user_id drop default;
alter table public.recordings    alter column user_id drop default;
