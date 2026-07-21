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
OTHER_OPTION = "Other (type manually)"

st.set_page_config(
    page_title="🏸 Badminton — Next Match",
    page_icon="🏸",
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


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def map_url(venue: str | None) -> str | None:
    """Return the Yandex Maps link for a known venue, else None."""
    return VENUES.get((venue or "").strip())


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


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    st.session_state.setdefault("is_admin", False)

    st.markdown(
        """
        <div class="hero">
            <div class="emoji">🏸</div>
            <div class="title">Badminton Club</div>
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


if __name__ == "__main__":
    main()
