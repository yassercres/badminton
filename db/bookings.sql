-- Run once in the Supabase SQL Editor to enable booking records.
-- Stores who booked which court for which day, so the group can see what's booked.

create table if not exists bookings (
    id          bigint generated always as identity primary key,
    created_at  timestamptz default now(),
    match_date  date,
    venue       text,
    booked_by   text,
    note        text
);

alter table bookings enable row level security;

create policy "read bookings"   on bookings for select using (true);
create policy "insert bookings" on bookings for insert with check (true);
create policy "delete bookings" on bookings for delete using (true);
