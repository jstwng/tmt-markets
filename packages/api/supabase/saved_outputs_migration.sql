-- Migration: create saved_outputs table for OpenBB dynamic data layer
-- Run this in the Supabase SQL editor at:
-- https://kfksdcqkqqvabridukua.supabase.co

create table if not exists saved_outputs (
  id uuid default gen_random_uuid() primary key,
  query text not null,
  chart_manifest jsonb not null,
  openbb_call text not null,
  created_at timestamptz default now()
);

alter table saved_outputs enable row level security;

create policy "Public read" on saved_outputs for select using (true);
create policy "Public insert" on saved_outputs for insert with check (true);
