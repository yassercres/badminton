-- Run once in the Supabase SQL Editor.
-- Lets the reminder job mark a match as "already reminded" so the group
-- gets exactly one notification per match (no repeats each hourly run).

alter table badminton_schedule
    add column if not exists reminded_for date;
