# AI Meeting & Follow-Up Agent

Paste a meeting transcript. The agent extracts decisions and action items, assigns owners and
deadlines, and autonomously follows up (simulated reminders, driven by real deadline logic) until
each item is marked done.

Built for InnovaHack Chapter 1 — Agentic AI domain, Problem Statement 2.

## Run locally

```bash
pip install -r requirements.txt
# Create .streamlit/secrets.toml with: GROQ_API_KEY = "gsk_..."
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. Go to share.streamlit.io, sign in with GitHub, "New app", pick this repo, main file `app.py`.
3. In the app's settings → Secrets, add: `GROQ_API_KEY = "gsk_..."`
4. Deploy.

## How it works

- **Extraction** (`extraction.py`) — sends the transcript to Groq's `llama-3.3-70b-versatile`
  (OpenAI-compatible API, free tier, no card required) with a JSON-mode prompt that returns
  structured `{task, owner, deadline, decision}` items.
- **Persistence** (`db.py`) — SQLite: `meetings`, `action_items`, `reminders`.
- **Reminders** (`reminders.py`) — on every page load, sweeps all pending items and logs a
  simulated reminder for anything due/overdue that hasn't been reminded recently (real date-logic
  driven, not random) — this is what "autonomous" means in a stateless web app without a
  background worker. A manual "Send reminder now" button exists per item too.
