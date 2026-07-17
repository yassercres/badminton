-- Your `badminton_schedule` table already exists (columns: date, time, venue).
-- Run this in the Supabase SQL Editor to allow the app (which uses the anon key)
-- to read and write it. New Supabase tables have Row Level Security ON with no
-- policies, which silently blocks the anon key — this adds the policies it needs.
-- The admin password is enforced in the app, not the database.

alter table badminton_schedule enable row level security;

create policy "read schedule" on badminton_schedule
    for select using (true);

create policy "insert schedule" on badminton_schedule
    for insert with check (true);

create policy "update schedule" on badminton_schedule
    for update using (true) with check (true);
