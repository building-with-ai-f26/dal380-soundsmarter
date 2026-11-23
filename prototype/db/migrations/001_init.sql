-- 001_init.sql: accounts, prompts and stored recordings for SoundSmarter (Build 3).
-- Run once in each Supabase project's SQL Editor: dev first, then prod.
-- Never edit this file after it has run; changes go in 002_..., 003_...
--
-- Who can do what (row-level security, RLS):
--   signed-out visitors: nothing
--   signed-in users:     read approved prompts and stimuli; read and add their own
--                        prompt events and recordings; read their own consent
--   nobody, from the app: change or delete anything; see sign-up codes
--   owner (dashboard):   everything (the dashboard bypasses RLS)

create schema if not exists private;  -- not exposed to the app's API


-- ---------------------------------------------------------------- sign-up
-- Personal sign-up codes. Owner adds a row per person in Table Editor
-- (code + note). Each code creates exactly one account.
create table public.signup_codes (
  code       text primary key,
  note       text,                    -- who it's for
  created_at timestamptz not null default now(),
  used_by    uuid,                    -- set at sign-up (no FK: set before the user row exists)
  used_at    timestamptz
);

-- Consent: written by the sign-up check below, never by the app directly.
create table public.consents (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references auth.users (id) on delete cascade
                deferrable initially deferred,  -- written in the same step that creates the user
  version     text not null,                    -- e.g. '2026-11-21'; bump when the wording changes
  accepted_at timestamptz not null default now()
);

-- Runs inside every sign-up. No consent or no valid unused code = no account.
-- The page sends both in the sign-up metadata: {consent_version, signup_code}.
create function private.check_signup() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  v_code    text := new.raw_user_meta_data ->> 'signup_code';
  v_consent text := new.raw_user_meta_data ->> 'consent_version';
begin
  if coalesce(v_consent, '') = '' then
    raise exception 'Consent is required to create an account';
  end if;
  update public.signup_codes
     set used_by = new.id, used_at = now()
   where code = v_code and used_by is null;
  if not found then
    raise exception 'Sign-up code is not valid or already used';
  end if;
  insert into public.consents (user_id, version) values (new.id, v_consent);
  new.raw_user_meta_data := new.raw_user_meta_data - 'signup_code';  -- don't keep the code on the user
  return new;
end $$;

create trigger check_signup before insert on auth.users
  for each row execute function private.check_signup();


-- ---------------------------------------------------------------- prompts
-- Image and audio files. Files live in the public Storage bucket 'stimuli';
-- `files` holds their paths (one for a scene, two for a pair, 4-6 for a sequence).
create table public.stimuli (
  id         text primary key,        -- e.g. 'img-scene-01', 'aud-story-01'
  kind       text not null,           -- scene | pair | sequence | diagram | soundscape | story | claim
  files      text[] not null default '{}',
  title      text,
  creator    text,
  year       text,
  source_url text,
  license    text not null,
  credit     text not null,           -- the credit line shown with the stimulus
  status     text not null default 'draft' check (status in ('draft', 'approved', 'retired'))
);

create table public.prompts (
  id              text primary key,   -- e.g. 'des-t-01', 'des-i-01'
  family          text not null check (family in ('describe', 'narrate', 'argue', 'invent', 'explain')),
  mode            text not null check (mode in ('text', 'image', 'audio')),
  variant         text not null,
  openness        text,
  beats           int,
  words_on_screen int,
  stimulus_id     text references public.stimuli (id),
  text            text not null,
  status          text not null default 'draft' check (status in ('draft', 'approved', 'retired')),
  check (mode = 'text' or stimulus_id is not null)
);

-- What each user has been served, skipped, discarded, sent, or had rejected.
-- Anything here counts as seen: a prompt is never served to the same user twice.
-- 'sent' and 'rejected' rows also count toward the daily cap (each one cost a transcription).
create table public.prompt_events (
  id         bigint generated always as identity primary key,
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  prompt_id  text not null references public.prompts (id),
  event      text not null check (event in ('served', 'skipped', 'discarded', 'sent', 'rejected')),
  created_at timestamptz not null default now()
);
create index prompt_events_user_time on public.prompt_events (user_id, created_at);


-- ---------------------------------------------------------------- recordings
-- One row per usable recording. No audio.
create table public.recordings (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null default auth.uid() references auth.users (id) on delete cascade,
  created_at          timestamptz not null default now(),
  prompt_id           text not null references public.prompts (id),
  family              text not null,
  mode                text not null,
  variant             text not null,
  stimulus_id         text,
  session_no          int  not null,  -- new session after 30 min with no recording
  position_in_session int  not null,  -- 1 = first recording of the session
  skipped_before      text[] not null default '{}',  -- prompt ids skipped or discarded just before this one
  prep_from           text not null check (prep_from in ('reveal', 'clip_end')),
  metrics             jsonb not null,
  metrics_version     int  not null,  -- bump when a metric definition changes
  word_list_version   int  not null,  -- bump when the word list changes
  transcription       jsonb not null, -- full speech-to-text response, so metrics can be recomputed
  stt_model           text not null,  -- e.g. 'crisperwhisper-v2'
  language            text            -- as detected by the speech service
);
create index recordings_user_time on public.recordings (user_id, created_at);


-- ---------------------------------------------------------------- RLS
alter table public.signup_codes  enable row level security;  -- no policies: invisible to the app
alter table public.consents      enable row level security;
alter table public.stimuli       enable row level security;
alter table public.prompts       enable row level security;
alter table public.prompt_events enable row level security;
alter table public.recordings    enable row level security;

create policy "own consent: read" on public.consents
  for select to authenticated using (user_id = (select auth.uid()));

-- A stimulus is visible only when approved and its files are present.
create policy "approved stimuli: read" on public.stimuli
  for select to authenticated using (status = 'approved' and cardinality(files) > 0);

-- A prompt is visible only when approved, and, if it needs a stimulus, that
-- stimulus is visible too (so a prompt with a missing file is never served).
create policy "approved prompts: read" on public.prompts
  for select to authenticated using (
    status = 'approved'
    and (stimulus_id is null or exists (
      select 1 from public.stimuli s
       where s.id = stimulus_id and s.status = 'approved' and cardinality(s.files) > 0))
  );

create policy "own prompt events: read" on public.prompt_events
  for select to authenticated using (user_id = (select auth.uid()));
create policy "own prompt events: add" on public.prompt_events
  for insert to authenticated with check (user_id = (select auth.uid()));

create policy "own recordings: read" on public.recordings
  for select to authenticated using (user_id = (select auth.uid()));
create policy "own recordings: add, after consent" on public.recordings
  for insert to authenticated with check (
    user_id = (select auth.uid())
    and exists (select 1 from public.consents c where c.user_id = (select auth.uid()))
  );
-- No update or delete policies anywhere: rows can't be changed or removed from the app.

revoke all on public.signup_codes, public.consents, public.stimuli, public.prompts,
              public.prompt_events, public.recordings from anon, authenticated;
grant select         on public.consents, public.stimuli, public.prompts to authenticated;
grant select, insert on public.prompt_events, public.recordings     to authenticated;


-- ---------------------------------------------------------------- storage
-- Public bucket for stimulus files: anyone with the link can view; only the
-- owner (dashboard) can upload.
insert into storage.buckets (id, name, public) values ('stimuli', 'stimuli', true)
  on conflict (id) do nothing;
