import os
from datetime import datetime

import streamlit as st

import db
import reminders
from extraction import extract_action_items

st.set_page_config(page_title="AI Meeting & Follow-Up Agent", page_icon="🤖", layout="wide")

if os.environ.get("GROQ_API_KEY") is None:
    try:
        if "GROQ_API_KEY" in st.secrets:
            os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    except st.errors.StreamlitSecretNotFoundError:
        pass  # no secrets.toml at all - fine locally if GROQ_API_KEY is a real env var instead

db.init_db()

if "sweep_done" not in st.session_state:
    st.session_state.sweep_done = True
    sent = reminders.run_reminder_sweep()
    st.session_state.sweep_messages = sent

st.title("🤖 AI Meeting & Follow-Up Agent")
st.caption(
    "Paste a meeting transcript. The agent extracts decisions and action items, assigns "
    "owners and deadlines, and autonomously follows up until each item is marked done."
)

if st.session_state.get("sweep_messages"):
    with st.expander(f"🔔 {len(st.session_state.sweep_messages)} automatic reminder(s) just sent", expanded=True):
        for msg in st.session_state.sweep_messages:
            st.write("  " + msg)

tab_new, tab_dashboard, tab_log = st.tabs(["📝 New Meeting", "📊 Dashboard", "🔔 Reminder Log"])

with tab_new:
    st.subheader("Process a meeting transcript")
    title = st.text_input("Meeting title", placeholder="e.g. Weekly Product Sync - Jul 25")
    transcript = st.text_area(
        "Transcript",
        height=280,
        placeholder=(
            "Paste the raw meeting transcript here - speaker names and rough dialogue is fine, "
            "the agent will figure out the decisions and action items on its own."
        ),
    )
    process = st.button("Extract decisions & action items", type="primary", disabled=not transcript.strip())

    if process:
        if not os.environ.get("GROQ_API_KEY"):
            st.error("No GROQ_API_KEY configured. Set it as an environment variable or in `.streamlit/secrets.toml`.")
        else:
            with st.spinner("Reading the transcript and extracting action items..."):
                try:
                    items = extract_action_items(transcript)
                except Exception as exc:  # noqa: BLE001 - surface any API error directly to the user
                    st.error(f"Extraction failed: {exc}")
                    items = None

            if items is not None:
                meeting_title = title.strip() or f"Meeting - {datetime.now():%Y-%m-%d %H:%M}"
                meeting_id = db.create_meeting(meeting_title, transcript)
                for it in items:
                    db.create_action_item(
                        meeting_id,
                        decision=it.get("decision", ""),
                        task=it.get("task", ""),
                        owner=it.get("owner") or "Unassigned",
                        deadline=it.get("deadline"),
                    )
                if items:
                    st.success(f"Extracted {len(items)} action item(s) from \"{meeting_title}\".")
                    st.table(
                        [
                            {
                                "Task": it.get("task", ""),
                                "Owner": it.get("owner") or "Unassigned",
                                "Deadline": it.get("deadline") or "-",
                            }
                            for it in items
                        ]
                    )
                else:
                    st.info("No clear decisions or action items were found in this transcript.")

with tab_dashboard:
    col1, col2 = st.columns(2)

    def render_item(item, completed: bool):
        with st.container(border=True):
            top = st.columns([5, 2, 2, 2])
            top[0].markdown(f"**{item['task']}**")
            top[1].markdown(f"👤 {item['owner']}")
            top[2].markdown(f"📅 {item['deadline'] or '-'}")
            top[3].markdown(f"_{item['meeting_title']}_")
            if item["decision"]:
                st.caption(f"Decision: {item['decision']}")

            actions = st.columns([1, 1, 3])
            if completed:
                if actions[0].button("🔄 Reopen", key=f"reopen-{item['id']}"):
                    db.reopen_item(item["id"])
                    st.rerun()
            else:
                if actions[0].button("✅ Mark complete", key=f"complete-{item['id']}"):
                    db.mark_complete(item["id"])
                    st.rerun()
                if actions[1].button("🔔 Send reminder now", key=f"remind-{item['id']}"):
                    msg = reminders.send_manual_reminder(item)
                    st.toast(msg)

            item_reminders = db.reminders_for_item(item["id"])
            if item_reminders:
                with st.expander(f"Follow-up history ({len(item_reminders)})"):
                    for r in item_reminders:
                        st.caption(f"{r['sent_at'][:16].replace('T', ' ')} - {r['message']}")

    with col1:
        st.subheader("⏳ Pending")
        pending = db.list_action_items(status="pending")
        if not pending:
            st.info("No pending action items yet - process a meeting to create some.")
        for item in pending:
            render_item(item, completed=False)

    with col2:
        st.subheader("✅ Completed")
        completed = db.list_action_items(status="completed")
        if not completed:
            st.info("Nothing completed yet.")
        for item in completed:
            render_item(item, completed=True)

with tab_log:
    st.subheader("Automated follow-up activity")
    st.caption(
        "Every reminder below was triggered automatically based on real deadline logic "
        "(or manually via 'Send reminder now') - this is a simulated send (no real email/SMS "
        "wired up), logged exactly like a real notification would be."
    )
    log = db.all_reminders()
    if not log:
        st.info("No reminders sent yet.")
    else:
        st.table(
            [
                {
                    "Sent": r["sent_at"][:16].replace("T", " "),
                    "Task": r["task"],
                    "Owner": r["owner"],
                    "Message": r["message"],
                }
                for r in log
            ]
        )
