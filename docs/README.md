# BadBoyz Club — PWA installer page

This folder is a tiny static site served by **GitHub Pages**. Its only job is to
give the installed app a **custom icon ("BB") and name ("BadBoyz Club")** on the
home screen — something Streamlit Community Cloud doesn't let you customize directly.

It loads your Streamlit app inside itself (or redirects to it).

## Setup (one time)

1. Edit `index.html` and set `APP_URL` to your deployed Streamlit link
   (e.g. `https://badboyz.streamlit.app`).
2. On GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a
   branch**, Branch: `main`, Folder: `/docs`, then **Save**.
3. Wait ~1 minute. Your installer page goes live at
   `https://<your-username>.github.io/badminton/`.
4. Open **that** link on your phone → Add to Home Screen. You'll get the BB icon
   and "BadBoyz Club" name.

## If the embedded app misbehaves

Open `index.html` and change `const MODE = "embed";` to `const MODE = "redirect";`.
Redirect is more robust (the app opens directly) at the cost of a thin browser bar
on Android.
