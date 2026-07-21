"""
🏸 BadBoyz Club — badminton sessions tracker.

A small Streamlit app for a closed group of 6 players.
- Anyone with the link can VIEW the next match and the upcoming schedule.
- Someone who enters the admin password can add / edit / delete sessions.

Single-table model: `badminton_schedule` holds MANY rows, one per future
session (columns: date, time, venue, cost, note). The "next match" is simply the
soonest upcoming row (date >= today). See db/upgrade_schedule.sql.

Secrets (password + Supabase creds) come from .streamlit/secrets.toml.
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

# The group plays at a couple of fixed venues. Name -> Yandex Maps link.
VENUES: dict[str, str] = {
    "Luzhniki NLBC": "https://yandex.com/maps/-/CTV8AIP5",
    "Park Kultury NLBC": "https://yandex.com/maps/-/CTV8MYoM",
}

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
      .hero { text-align: center; margin-bottom: 1.2rem; }
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
      .match-card.empty { background: linear-gradient(150deg,#475569 0%,#334155 100%); box-shadow:none; }
      .match-card::after {
          content: "🏸";
          position: absolute; right: -0.4rem; bottom: -0.8rem;
          font-size: 6rem; opacity: 0.10; transform: rotate(-18deg);
      }
      .countdown-pill {
          display: inline-block;
          background: rgba(255,255,255,0.18); color: #ffffff;
          font-size: 0.8rem; font-weight: 700;
          padding: 0.28rem 0.7rem; border-radius: 999px; margin-bottom: 1rem;
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


def load_sessions() -> list[dict]:
    """All sessions, soonest first."""
    client = get_client()
    resp = client.table(TABLE).select("*").order("date").order("time").execute()
    return resp.data or []


def upcoming_sessions(sessions: list[dict]) -> list[dict]:
    today = dt.date.today().isoformat()
    return [s for s in sessions if (s.get("date") or "") >= today]


def next_session(sessions: list[dict]) -> dict | None:
    up = upcoming_sessions(sessions)
    return up[0] if up else None


def _session_payload(
    date: dt.date, time: dt.time, venue: str, cost: float, paid_by: str, note: str
) -> dict:
    return {
        "date": date.isoformat(),
        "time": time.strftime("%H:%M:%S"),
        "venue": venue,
        "cost": float(cost) if cost else None,
        "paid_by": paid_by or None,
        "note": note or None,
    }


def add_session(
    date: dt.date, time: dt.time, venue: str, cost: float, paid_by: str, note: str
) -> None:
    get_client().table(TABLE).insert(
        _session_payload(date, time, venue, cost, paid_by, note)
    ).execute()


def update_session(
    sid: int, date: dt.date, time: dt.time, venue: str, cost: float, paid_by: str, note: str
) -> None:
    get_client().table(TABLE).update(
        _session_payload(date, time, venue, cost, paid_by, note)
    ).eq("id", sid).execute()


def delete_session(sid: int) -> None:
    get_client().table(TABLE).delete().eq("id", sid).execute()


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def map_url(venue: str | None) -> str | None:
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


def short_date(value: str | None) -> str:
    try:
        return dt.date.fromisoformat(value).strftime("%a, %d %b")
    except (ValueError, TypeError):
        return str(value or "TBD")


def pretty_time(value: str | None) -> str:
    if not value:
        return "TBD"
    try:
        return dt.datetime.strptime(value[:8], "%H:%M:%S").strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return str(value)


def pretty_cost(value) -> str | None:
    try:
        v = float(value)
    except (ValueError, TypeError):
        return None
    return f"₽{v:,.0f}" if v > 0 else None


def countdown_label(value: str | None) -> str:
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


# --------------------------------------------------------------------------- #
# UI: next-match card
# --------------------------------------------------------------------------- #
def render_card(session: dict | None) -> None:
    if not session:
        st.markdown(
            """
            <div class="match-card empty">
                <span class="countdown-pill">No match scheduled</span>
                <div class="row"><span class="ic">🗓️</span>
                    <span><span class="label">Next match</span>
                    <span class="value">No sessions booked yet</span></span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info("🏸 Nothing on the calendar right now. Book a court from the **Book a Court** tab, then add it as a session.")
        return

    venue = session.get("venue") or "TBD"
    url = map_url(venue)
    venue_html = f'<a href="{url}" target="_blank">{venue} ↗</a>' if url else venue

    def info_row(icon: str, label: str, value: str | None) -> str:
        if not value:
            return ""
        return (
            f'<div class="row"><span class="ic">{icon}</span><span>'
            f'<span class="label">{label}</span><span class="value">{value}</span></span></div>'
        )

    cost_row = info_row("💰", "Cost", pretty_cost(session.get("cost")))
    paid_row = info_row("💳", "Paid by", session.get("paid_by"))

    st.markdown(
        f"""
        <div class="match-card">
            <span class="countdown-pill">{countdown_label(session.get("date"))}</span>
            <div class="row"><span class="ic">📍</span>
                <span><span class="label">Venue</span><span class="value">{venue_html}</span></span></div>
            <div class="row"><span class="ic">📅</span>
                <span><span class="label">Date</span><span class="value">{pretty_date(session.get("date"))}</span></span></div>
            <div class="row"><span class="ic">⏰</span>
                <span><span class="label">Time</span><span class="value">{pretty_time(session.get("time"))}</span></span></div>
            {cost_row}
            {paid_row}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if url:
        st.write("")
        st.link_button("📍 Get directions (Yandex Maps)", url, use_container_width=True)


# --------------------------------------------------------------------------- #
# UI: admin session management
# --------------------------------------------------------------------------- #
def _venue_index(venue: str | None) -> int:
    names = list(VENUES.keys())
    return names.index(venue) if venue in names else 0


def render_session_form(key: str, session: dict | None = None) -> None:
    """A form to add (session=None) or edit an existing session."""
    session = session or {}
    names = list(VENUES.keys())
    is_edit = bool(session)

    with st.form(f"form_{key}", clear_on_submit=not is_edit):
        choice = st.selectbox("Venue", names, index=_venue_index(session.get("venue")), key=f"v_{key}")
        custom = st.text_input(
            "…or type another venue (optional)",
            value="" if (not session.get("venue") or session.get("venue") in names) else session["venue"],
            key=f"c_{key}",
        )
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", value=parse_date(session.get("date")), key=f"d_{key}")
        with col2:
            time = st.time_input("Time", value=parse_time(session.get("time")), key=f"t_{key}")
        colc, colp = st.columns(2)
        with colc:
            cost = st.number_input(
                "Cost (₽)", min_value=0.0, step=100.0,
                value=float(session.get("cost") or 0), format="%.0f", key=f"cost_{key}",
            )
        with colp:
            paid_by = st.text_input("Paid by", value=session.get("paid_by") or "", key=f"p_{key}")
        note = st.text_input("Note (court no., etc.) — optional", value=session.get("note") or "", key=f"n_{key}")

        if is_edit:
            bcol1, bcol2 = st.columns(2)
            save = bcol1.form_submit_button("💾 Save")
            delete = bcol2.form_submit_button("🗑️ Delete")
        else:
            save = st.form_submit_button("➕ Add session")
            delete = False

    if save:
        venue = custom.strip() or choice
        try:
            if is_edit:
                update_session(session["id"], date, time, venue, cost, paid_by.strip(), note.strip())
                st.success("Saved ✅")
            else:
                add_session(date, time, venue, cost, paid_by.strip(), note.strip())
                st.success("Session added ✅")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not save: {exc}")
    if delete:
        try:
            delete_session(session["id"])
            st.warning("Session deleted.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not delete: {exc}")


def render_admin_manage(sessions: list[dict]) -> None:
    ups = upcoming_sessions(sessions)
    st.subheader("🗓️ Manage sessions")

    with st.expander("➕ Add a session", expanded=not ups):
        render_session_form("add")

    if ups:
        st.caption("Edit or remove upcoming sessions:")
        for s in ups:
            cost = pretty_cost(s.get("cost"))
            label = f"{short_date(s.get('date'))} · {s.get('venue')}" + (f" · {cost}" if cost else "")
            with st.expander("✏️ " + label):
                render_session_form(f"edit_{s['id']}", s)


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


# --------------------------------------------------------------------------- #
# UI: shared upcoming-sessions list
# --------------------------------------------------------------------------- #
def render_upcoming_list(rows: list[dict], heading: str, empty_text: str) -> None:
    st.markdown(f"**{heading}**")
    if not rows:
        if empty_text:
            st.caption(empty_text)
        return
    for s in rows:
        line = f"**{short_date(s.get('date'))}**, {pretty_time(s.get('time'))} — {s.get('venue')}"
        extras = " · ".join(
            x for x in [
                pretty_cost(s.get("cost")),
                (f"paid by {s['paid_by']}" if s.get("paid_by") else None),
                s.get("note"),
            ] if x
        )
        st.markdown(line + (f"  \n_{extras}_" if extras else ""))


# --------------------------------------------------------------------------- #
# UI: booking tab
# --------------------------------------------------------------------------- #
def render_booking(sessions: list[dict]) -> None:
    st.subheader("📅 Book a court")
    st.caption(
        "Pick a venue and date, open the booking site (with your date pre-filled), "
        "and pay there. Then add it as a session (Admin Mode) so it shows up here."
    )

    names = list(VENUE_BOOKING.keys())
    nxt = next_session(sessions)
    default_date = parse_date(nxt.get("date")) if nxt else dt.date.today()
    default_venue = _venue_index(nxt.get("venue")) if nxt else 0

    col1, col2 = st.columns(2)
    with col1:
        venue = st.selectbox("Venue", names, index=default_venue, key="book_venue")
    with col2:
        date = st.date_input("Date", value=default_date, key="book_date")

    url = booking_url(venue, date)
    if url:
        st.link_button(
            f"🎟️ Open booking page — {date.strftime('%d %b %Y')}", url, use_container_width=True
        )
        st.caption("Opens bc-newliga.ru with your date selected. Complete payment on their site.")

    st.divider()
    render_upcoming_list(
        upcoming_sessions(sessions), "📋 Upcoming sessions", "No upcoming sessions yet."
    )


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
        sessions = load_sessions()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Couldn't reach the database: {exc}")
        st.stop()

    tab_match, tab_book = st.tabs(["🏸 Next Match", "📅 Book a Court"])

    with tab_match:
        ups = upcoming_sessions(sessions)
        render_card(ups[0] if ups else None)
        if len(ups) > 1:
            st.write("")
            render_upcoming_list(ups[1:], "📋 More upcoming sessions", "")
        st.divider()
        if st.session_state.is_admin:
            st.success("Admin Mode 🔓")
            render_admin_manage(sessions)
            if st.button("Log out"):
                st.session_state.is_admin = False
                st.rerun()
        else:
            render_login()

    with tab_book:
        render_booking(sessions)


if __name__ == "__main__":
    main()
