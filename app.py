"""
🏸 Badminton Group — Next Match tracker.

A small Streamlit app for a closed group of 6 players.
- Anyone with the link can VIEW the next match venue, date and time.
- Only someone who enters the correct admin password can EDIT those details.

Data lives in the Supabase table `badminton_schedule` (columns: date, time, venue).
The app keeps a single "next match" row: it edits the existing row if there is one,
otherwise it inserts one.

Secrets (password + Supabase creds) come from .streamlit/secrets.toml — see secrets.toml.example.
"""

from __future__ import annotations

import datetime as dt
import urllib.parse

import streamlit as st
from supabase import create_client, Client

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
TABLE = "badminton_schedule"
BOOKINGS_TABLE = "bookings"

# The group plays at a couple of fixed venues. Name -> Yandex Maps link.
VENUES: dict[str, str] = {
    "Luzhniki NLBC": "https://yandex.com/maps/-/CTV8AIP5",
    "Park Kultury NLBC": "https://yandex.com/maps/-/CTV8MYoM",
}
OTHER_OPTION = "Other (type manually)"

# Court-booking (bc-newliga.ru). Each venue uses a different booking widget, so
# it has its own URL-parameter prefix and studio id. We inject the chosen date
# so the booking page opens with the right day pre-selected.
BOOKING_BASE = "https://bc-newliga.ru/"
BOOKING_CITY = "Москва"  # Moscow
VENUE_BOOKING: dict[str, dict[str, str]] = {
    "Luzhniki NLBC": {
        "prefix": "prioritypersonal",
        "studio": "461085c7-4f37-4e1e-9a20-cbc0ab51369d",
    },
    "Park Kultury NLBC": {
        "prefix": "bookingChaika",
        "studio": "839939cc-2d9e-4ac9-b901-383d755a45a4",
    },
}

st.set_page_config(
    page_title="BadBoyz Club — Next Match",
    page_icon="assets/icon.png",  # custom app / tab / home-screen icon
    layout="centered",  # centered plays nicely on phones
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------------------------------- #
# Styling — keep it clean and touch-friendly
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 620px; }
      .stButton > button, .stFormSubmitButton > button, a[data-testid="stBaseButton-secondary"] {
          width: 100%;
          border-radius: 12px;
          padding: 0.6rem 1rem;
          font-weight: 600;
      }

      /* Hero header */
      .hero {
          text-align: center;
          margin-bottom: 1.2rem;
      }
      .hero .emoji { font-size: 2.4rem; line-height: 1; }
      .hero .title { font-size: 1.6rem; font-weight: 800; margin-top: 0.2rem; letter-spacing: -0.01em; }
      .hero .sub { color: #64748b; font-size: 0.95rem; margin-top: 0.1rem; }

      /* Match card */
      .match-card {
          background: linear-gradient(150deg, #0f766e 0%, #0d5c56 55%, #0b4f4a 100%);
          color: #ffffff;
          border-radius: 22px;
          padding: 1.5rem 1.4rem 1.6rem;
          box-shadow: 0 12px 30px rgba(13, 92, 86, 0.32);
          position: relative;
          overflow: hidden;
      }
      .match-card::after {
          content: "🏸";
          position: absolute;
          right: -0.4rem; bottom: -0.8rem;
          font-size: 6rem; opacity: 0.10; transform: rotate(-18deg);
      }
      .countdown-pill {
          display: inline-block;
          background: rgba(255,255,255,0.18);
          color: #ffffff;
          font-size: 0.8rem; font-weight: 700;
          padding: 0.28rem 0.7rem; border-radius: 999px;
          margin-bottom: 1rem;
      }
      .row { display: flex; align-items: baseline; gap: 0.6rem; margin-bottom: 0.9rem; }
      .row:last-child { margin-bottom: 0; }
      .row .ic { font-size: 1.1rem; width: 1.4rem; flex: none; }
      .row .label {
          font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em;
          opacity: 0.72; display: block; margin-bottom: 0.05rem;
      }
      .row .value { font-size: 1.22rem; font-weight: 700; line-height: 1.25; }
      .row .value a { color: #ffffff; text-decoration: underline; text-underline-offset: 3px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Supabase helpers
# --------------------------------------------------------------------------- #
@st.cache_resource
def get_client() -> Client:
    """Create (and cache) the Supabase client from Streamlit secrets."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def load_match() -> dict | None:
    """Read the current 'next match' row, or None if the table is empty."""
    client = get_client()
    resp = client.table(TABLE).select("*").order("id").limit(1).execute()
    return resp.data[0] if resp.data else None


def save_match(venue: str, match_date: dt.date, match_time: dt.time) -> None:
    """Update the existing row if there is one, otherwise insert a new one."""
    client = get_client()
    payload = {
        "venue": venue,
        "date": match_date.isoformat(),
        "time": match_time.strftime("%H:%M:%S"),
    }
    existing = load_match()
    if existing and "id" in existing:
        client.table(TABLE).update(payload).eq("id", existing["id"]).execute()
    else:
        client.table(TABLE).insert(payload).execute()


def load_bookings() -> tuple[list[dict], bool]:
    """Return (rows, table_ready). table_ready is False if `bookings` is missing."""
    try:
        client = get_client()
        resp = client.table(BOOKINGS_TABLE).select("*").order("match_date").execute()
        return resp.data or [], True
    except Exception:  # noqa: BLE001 — table not created yet, or transient error
        return [], False


def add_booking(match_date: dt.date, venue: str, booked_by: str, note: str) -> None:
    client = get_client()
    client.table(BOOKINGS_TABLE).insert(
        {
            "match_date": match_date.isoformat(),
            "venue": venue,
            "booked_by": booked_by,
            "note": note or None,
        }
    ).execute()


def delete_booking(booking_id: int) -> None:
    client = get_client()
    client.table(BOOKINGS_TABLE).delete().eq("id", booking_id).execute()


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def map_url(venue: str | None) -> str | None:
    """Return the Yandex Maps link for a known venue, else None."""
    return VENUES.get((venue or "").strip())


def booking_url(venue: str | None, date: dt.date) -> str | None:
    """Build the bc-newliga.ru booking link for a venue with the date pre-filled."""
    cfg = VENUE_BOOKING.get((venue or "").strip())
    if not cfg:
        return None
    prefix = cfg["prefix"]
    params = [
        ("abonements_studioId", "all"),
        (f"{prefix}_date", date.isoformat()),
        (f"{prefix}_studioId", cfg["studio"]),
        (f"{prefix}_city", BOOKING_CITY),
    ]
    return f"{BOOKING_BASE}?{urllib.parse.urlencode(params)}#{prefix}"


def pretty_date(value: str | None) -> str:
    if not value:
        return "TBD"
    try:
        return dt.date.fromisoformat(value).strftime("%A, %d %B %Y")
    except ValueError:
        return str(value)


def pretty_time(value: str | None) -> str:
    if not value:
        return "TBD"
    try:
        return dt.datetime.strptime(value[:8], "%H:%M:%S").strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return str(value)


def countdown_label(value: str | None) -> str:
    """A friendly 'Today / Tomorrow / In N days' badge for the match date."""
    if not value:
        return "Date to be confirmed"
    try:
        days = (dt.date.fromisoformat(value) - dt.date.today()).days
    except ValueError:
        return "Upcoming match"
    if days < 0:
        return "Past match"
    if days == 0:
        return "🔥 Today!"
    if days == 1:
        return "Tomorrow"
    return f"In {days} days"


def parse_date(value: str | None) -> dt.date:
    try:
        return dt.date.fromisoformat(value) if value else dt.date.today()
    except (ValueError, TypeError):
        return dt.date.today()


def parse_time(value: str | None) -> dt.time:
    try:
        return dt.datetime.strptime(value[:8], "%H:%M:%S").time() if value else dt.time(18, 0)
    except (ValueError, TypeError):
        return dt.time(18, 0)


def build_ics(match: dict | None) -> str | None:
    """Build a calendar invite (.ics) with an alarm 12 hours before the match.

    Once a player adds this to their phone calendar, the phone fires a native
    reminder 12h before — no server or push infrastructure needed. Times are
    "floating" (interpreted in the device's local timezone), which is what we
    want since everyone plays in the same city.
    """
    match = match or {}
    date, time = match.get("date"), match.get("time")
    if not date or not time:
        return None
    try:
        start = dt.datetime.combine(dt.date.fromisoformat(date), parse_time(time))
    except (ValueError, TypeError):
        return None

    end = start + dt.timedelta(hours=2)
    venue = match.get("venue") or "Badminton"
    url = map_url(venue) or ""
    local = lambda d: d.strftime("%Y%m%dT%H%M%S")  # noqa: E731 — floating local time
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//BadBoyz Club//Badminton//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{local(start)}-badboyz@club",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{local(start)}",
        f"DTEND:{local(end)}",
        f"SUMMARY:\U0001F3F8 BadBoyz Badminton — {venue}",
        f"LOCATION:{venue}",
        f"DESCRIPTION:Next BadBoyz match at {venue}. {url}".strip(),
        "BEGIN:VALARM",
        "TRIGGER:-PT12H",
        "ACTION:DISPLAY",
        "DESCRIPTION:\U0001F3F8 Badminton in 12 hours!",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


# --------------------------------------------------------------------------- #
# UI sections
# --------------------------------------------------------------------------- #
def render_card(match: dict | None) -> None:
    match = match or {}
    venue = match.get("venue") or "TBD"
    url = map_url(venue)
    venue_html = f'<a href="{url}" target="_blank">{venue} ↗</a>' if url else venue

    st.markdown(
        f"""
        <div class="match-card">
            <span class="countdown-pill">{countdown_label(match.get("date"))}</span>
            <div class="row">
                <span class="ic">📍</span>
                <span><span class="label">Venue</span><span class="value">{venue_html}</span></span>
            </div>
            <div class="row">
                <span class="ic">📅</span>
                <span><span class="label">Date</span><span class="value">{pretty_date(match.get("date"))}</span></span>
            </div>
            <div class="row">
                <span class="ic">⏰</span>
                <span><span class="label">Time</span><span class="value">{pretty_time(match.get("time"))}</span></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # A clear, thumb-sized "directions" button under the card.
    if url:
        st.write("")
        st.link_button("📍 Get directions (Yandex Maps)", url, use_container_width=True)

    # Calendar reminder — fires a native phone notification 12h before the match.
    ics = build_ics(match)
    if ics:
        st.download_button(
            "🔔 Add to calendar (reminds you 12h before)",
            data=ics,
            file_name="badboyz-match.ics",
            mime="text/calendar",
            use_container_width=True,
        )


def render_admin_editor(match: dict | None) -> None:
    match = match or {}
    st.subheader("✏️ Update next match")

    current_venue = match.get("venue") or ""
    venue_names = list(VENUES.keys())
    options = venue_names + [OTHER_OPTION]
    default_index = venue_names.index(current_venue) if current_venue in venue_names else len(options) - 1

    with st.form("edit_match"):
        choice = st.selectbox("Venue", options, index=default_index)
        # Only ask for free text when "Other" is picked.
        custom_venue = ""
        if choice == OTHER_OPTION:
            custom_venue = st.text_input(
                "Custom venue name",
                value="" if current_venue in venue_names else current_venue,
            )

        col1, col2 = st.columns(2)
        with col1:
            match_date = st.date_input("Date", value=parse_date(match.get("date")))
        with col2:
            match_time = st.time_input("Time", value=parse_time(match.get("time")))
        submitted = st.form_submit_button("💾 Save changes")

    if submitted:
        venue = custom_venue.strip() if choice == OTHER_OPTION else choice
        if not venue:
            st.error("Please choose or enter a venue.")
            return
        try:
            save_match(venue, match_date, match_time)
            st.success("Match details updated! ✅")
            st.rerun()
        except Exception as exc:  # noqa: BLE001 — surface any Supabase error to the admin
            st.error(f"Could not save: {exc}")


def render_login() -> None:
    with st.expander("🔒 Admin login"):
        with st.form("login"):
            password = st.text_input("Admin password", type="password")
            submitted = st.form_submit_button("Unlock Admin Mode")
        if submitted:
            if password == st.secrets["app"]["admin_password"]:
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("Incorrect password.")


def render_booking(match: dict | None) -> None:
    match = match or {}
    st.subheader("📅 Book a court")
    st.caption(
        "Pick a venue and date, open the booking site (with your date pre-filled), "
        "and pay there. Then log it below so everyone can see what's booked."
    )

    venue_names = list(VENUE_BOOKING.keys())
    current_venue = match.get("venue")
    v_index = venue_names.index(current_venue) if current_venue in venue_names else 0

    col1, col2 = st.columns(2)
    with col1:
        venue = st.selectbox("Venue", venue_names, index=v_index, key="book_venue")
    with col2:
        date = st.date_input("Date", value=parse_date(match.get("date")), key="book_date")

    url = booking_url(venue, date)
    if url:
        st.link_button(
            f"🎟️ Open booking page — {date.strftime('%d %b %Y')}",
            url,
            use_container_width=True,
        )
        st.caption("Opens bc-newliga.ru with your date selected. Complete payment on their site.")

    st.divider()
    render_booking_records(match)


def render_booking_records(match: dict | None) -> None:
    match = match or {}
    rows, ready = load_bookings()
    if not ready:
        st.info("Booking records aren't enabled yet — run `db/bookings.sql` in Supabase to turn this on.")
        return

    venue_names = list(VENUE_BOOKING.keys())
    cur = match.get("venue")
    idx = venue_names.index(cur) if cur in venue_names else 0

    with st.expander("✅ Log a booking (after you've paid)"):
        with st.form("log_booking"):
            bvenue = st.selectbox("Venue", venue_names, index=idx, key="log_venue")
            bdate = st.date_input("Date", value=parse_date(match.get("date")), key="log_date")
            who = st.text_input("Booked by")
            note = st.text_input("Note (court no., time, cost…)", value="")
            ok = st.form_submit_button("Save booking")
        if ok:
            if not who.strip():
                st.error("Please add who booked it.")
            else:
                try:
                    add_booking(bdate, bvenue, who.strip(), note.strip())
                    st.success("Booking logged! ✅")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not save: {exc}")

    st.markdown("**📋 Upcoming booked sessions**")
    today = dt.date.today().isoformat()
    upcoming = [r for r in rows if (r.get("match_date") or "") >= today]
    if not upcoming:
        st.caption("No upcoming bookings logged yet.")
        return

    for r in upcoming:
        c1, c2 = st.columns([6, 1])
        with c1:
            sub = " · ".join(x for x in [r.get("booked_by"), r.get("note")] if x)
            st.markdown(
                f"**{pretty_date(r.get('match_date'))}** — {r.get('venue')}"
                + (f"  \n_{sub}_" if sub else "")
            )
        with c2:
            if st.session_state.get("is_admin") and st.button("🗑️", key=f"del_{r['id']}"):
                delete_booking(r["id"])
                st.rerun()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    st.session_state.setdefault("is_admin", False)

    st.markdown(
        """
        <div class="hero">
            <div class="emoji">🏸</div>
            <div class="title">BadBoyz Club</div>
            <div class="sub">Our next match</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        match = load_match()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Couldn't reach the database: {exc}")
        st.stop()

    tab_match, tab_book = st.tabs(["🏸 Next Match", "📅 Book a Court"])

    with tab_match:
        render_card(match)
        st.divider()
        if st.session_state.is_admin:
            st.success("Admin Mode 🔓")
            render_admin_editor(match)
            if st.button("Log out"):
                st.session_state.is_admin = False
                st.rerun()
        else:
            render_login()

    with tab_book:
        render_booking(match)


if __name__ == "__main__":
    main()
