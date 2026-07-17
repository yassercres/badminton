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
      /* Roomier tap targets and rounded cards on mobile */
      .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 640px; }
      .stButton > button, .stFormSubmitButton > button {
          width: 100%;
          border-radius: 12px;
          padding: 0.6rem 1rem;
          font-weight: 600;
      }
      .match-card {
          background: linear-gradient(135deg, #0f766e 0%, #115e59 100%);
          color: #ffffff;
          border-radius: 20px;
          padding: 1.6rem 1.4rem;
          box-shadow: 0 8px 24px rgba(15, 118, 110, 0.28);
          margin-bottom: 1rem;
      }
      .match-card .label {
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          opacity: 0.75;
          margin-bottom: 0.15rem;
      }
      .match-card .value {
          font-size: 1.35rem;
          font-weight: 700;
          margin-bottom: 1rem;
          line-height: 1.25;
      }
      .match-card .value:last-child { margin-bottom: 0; }
      .app-title { text-align: center; font-size: 1.9rem; font-weight: 800; margin-bottom: 0.1rem; }
      .app-sub { text-align: center; color: #6b7280; margin-bottom: 1.4rem; }
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
    st.markdown(
        f"""
        <div class="match-card">
            <div class="label">📍 Venue</div>
            <div class="value">{match.get("venue") or "TBD"}</div>
            <div class="label">📅 Date</div>
            <div class="value">{pretty_date(match.get("date"))}</div>
            <div class="label">⏰ Time</div>
            <div class="value">{pretty_time(match.get("time"))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_admin_editor(match: dict | None) -> None:
    match = match or {}
    st.subheader("✏️ Update next match")
    with st.form("edit_match"):
        venue = st.text_input("Venue", value=match.get("venue") or "")
        col1, col2 = st.columns(2)
        with col1:
            match_date = st.date_input("Date", value=parse_date(match.get("date")))
        with col2:
            match_time = st.time_input("Time", value=parse_time(match.get("time")))
        submitted = st.form_submit_button("💾 Save changes")

    if submitted:
        if not venue.strip():
            st.error("Please enter a venue.")
            return
        try:
            save_match(venue.strip(), match_date, match_time)
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

    st.markdown('<div class="app-title">🏸 Badminton Club</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-sub">Our next match</div>', unsafe_allow_html=True)

    try:
        match = load_match()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Couldn't reach the database: {exc}")
        st.stop()

    render_card(match)

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
