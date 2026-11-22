-- 003_server_grants.sql: let the server's secret key add rows.
-- Run once in each Supabase project's SQL Editor: dev first, then prod.
-- Never edit this file after it has run; changes go in 004_...
--
-- Why: 002 stopped users adding rows, but the server's role (service_role)
-- had no permission on these tables either, so nothing could be saved.
-- It gets permission to add rows only: not to read, change or delete them.

grant insert on public.prompt_events, public.recordings to service_role;
