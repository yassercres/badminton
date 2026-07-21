-- Run once in the Supabase SQL Editor.
-- Moves to a single-table model: `badminton_schedule` now holds MANY rows
-- (one per future session). The app shows the soonest upcoming one as the
-- "next match" and lists the rest. Adds a cost column and a delete policy.

alter table badminton_schedule add column if not exists cost numeric;
alter table badminton_schedule add column if not exists paid_by text;
alter table badminton_schedule add column if not exists note text;

-- Allow the app (anon/publishable key) to delete sessions.
drop policy if exists "delete schedule" on badminton_schedule;
create policy "delete schedule" on badminton_schedule
    for delete using (true);
