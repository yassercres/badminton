"""
Automatic 12-hour match reminder for the BadBoyz Club.

Runs on a schedule from GitHub Actions (see .github/workflows/reminder.yml) — NOT
inside the Streamlit app. On each run it:
  1. reads the current match from Supabase,
  2. checks whether it is within REMINDER_HOURS (default 12h) from now,
  3. if so and it hasn't already reminded for this match, sends ONE Telegram
     message to the group and stamps `reminded_for` so nobody gets spammed.

Everything is configured via environment variables (GitHub Actions secrets):
  SUPABASE_URL, SUPABASE_KEY        - same project URL + publishable key as the app
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  REMINDER_HOURS   (optional, default 12)
  TZ_OFFSET_HOURS  (optional, default 3 = Moscow, no DST)
  DRY_RUN          (optional; if set, prints the message but does not send or write)
"""

from __future__ import annotations

import datetime as dt
import os
import sys
import urllib.parse
import urllib.request

from supabase import create_client

TABLE = "badminton_schedule"
REMINDER_HOURS = float(os.environ.get("REMINDER_HOURS", "12"))
TZ = dt.timezone(dt.timedelta(hours=float(os.environ.get("TZ_OFFSET_HOURS", "3"))))
DRY_RUN = bool(os.environ.get("DRY_RUN"))

VENUE_MAPS = {
    "Luzhniki NLBC": "https://yandex.com/maps/-/CTV8AIP5",
    "Park Kultury NLBC": "https://yandex.com/maps/-/CTV8MYoM",
}


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def send_telegram(token: str, chat_id: str, text: str) -> int:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30) as resp:
        return resp.status


def main() -> None:
    supabase = create_client(env("SUPABASE_URL"), env("SUPABASE_KEY"))

    rows = supabase.table(TABLE).select("*").order("id").limit(1).execute().data
    if not rows:
        print("No match set; nothing to do.")
        return

    match = rows[0]
    date, time = match.get("date"), match.get("time")
    if not date or not time:
        print("Match is missing date/time; skipping.")
        return

    match_dt = dt.datetime.combine(
        dt.date.fromisoformat(date),
        dt.datetime.strptime(time[:8], "%H:%M:%S").time(),
        tzinfo=TZ,
    )
    now = dt.datetime.now(TZ)
    hours = (match_dt - now).total_seconds() / 3600
    print(
        f"Match: {match_dt.isoformat()} | now: {now.isoformat()} | "
        f"{hours:.2f}h away | reminded_for={match.get('reminded_for')}"
    )

    if match.get("reminded_for") == date:
        print("Already reminded for this match; skipping.")
        return
    if not (0 < hours <= REMINDER_HOURS):
        print("Match is not within the reminder window; skipping.")
        return

    venue = match.get("venue") or "TBD"
    url = VENUE_MAPS.get(venue, "")
    when = match_dt.strftime("%a, %d %b")
    at_time = match_dt.strftime("%I:%M %p").lstrip("0")

    lines = [
        "🏸 <b>BadBoyz — match reminder!</b>",
        f"Starts in about {round(hours)} hours.",
        "",
        f"📍 {venue}",
        f"📅 {when}",
        f"⏰ {at_time}",
    ]
    if url:
        lines.append(f'🗺️ <a href="{url}">Directions</a>')
    text = "\n".join(lines)

    if DRY_RUN:
        print("[DRY_RUN] Would send:\n" + text)
        return

    status = send_telegram(env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID"), text)
    print(f"Telegram responded with HTTP {status}.")
    supabase.table(TABLE).update({"reminded_for": date}).eq("id", match["id"]).execute()
    print("Reminder sent and match marked as reminded.")


if __name__ == "__main__":
    main()
