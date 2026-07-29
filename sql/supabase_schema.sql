-- Schema LLMO — persistência no Supabase (Postgres)
-- Execute no SQL Editor do projeto Supabase antes do deploy na Vercel.

create table if not exists public.llmo_jobs (
  job_id uuid primary key,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create index if not exists llmo_jobs_updated_at_idx
  on public.llmo_jobs (updated_at desc);

create table if not exists public.llmo_perguntas (
  id uuid primary key,
  dados jsonb not null,
  updated_at timestamptz not null default now()
);

create index if not exists llmo_perguntas_segmento_idx
  on public.llmo_perguntas ((dados->>'segmento'));

-- Acesso só pelo service role no backend (Vercel).
-- Sem policies = bloqueado para anon/authenticated via PostgREST com chave anon.
alter table public.llmo_jobs enable row level security;
alter table public.llmo_perguntas enable row level security;
