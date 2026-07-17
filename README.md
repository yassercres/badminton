# 🏸 Badminton Group — Next Match

A tiny, mobile-friendly Streamlit app for a closed group of 6 players.

- **Everyone** who opens the link sees the next match **venue, date and time**.
- **Only** someone who enters the correct password can unlock **Admin Mode** and edit those details.
- Data is stored in **Supabase**.

## 1. Set up Supabase

1. Create a free project at [supabase.com](https://supabase.com).
2. Open **SQL Editor** and run the contents of [`schema.sql`](schema.sql).
3. In **Project Settings → API**, copy your **Project URL** and the **anon public** key.

## 2. Configure secrets

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml`:

```toml
[app]
admin_password = "your-strong-password"

[supabase]
url = "https://your-project.supabase.co"
key = "your-anon-public-key"
```

## 3. Install & run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the URL it prints (default http://localhost:8501) on your phone or share it.

## Deploy (optional)

Push to GitHub and deploy for free on [Streamlit Community Cloud](https://share.streamlit.io).
Paste the same `secrets.toml` contents into the app's **Secrets** box in the dashboard —
don't commit the real file (`.gitignore` already excludes it).

## How the admin lock works

The password is checked in the app (`st.secrets["app"]["admin_password"]`). Anyone without it
only ever sees the read-only card. Keep the password out of the repo — it lives only in
`secrets.toml` / the Streamlit Cloud secrets box.
