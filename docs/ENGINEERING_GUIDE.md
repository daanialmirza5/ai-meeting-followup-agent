# AI Meeting Follow-Up Agent — Engineering Guide & Mastery Document

## 1. What Is AI Meeting Follow-Up Agent?
AI Meeting Follow-Up Agent is a **meeting intelligence and automated execution agent**. It ingests raw audio/text meeting transcripts, extracts structured decisions, assignees, and deadlines, and automatically generates standard **RFC 5545 iCalendar (`.ics`) files**, email follow-up drafts, and calendar event payloads.

## 2. Real-World Problem Solved
1. **Lost Action Items**: Key operational decisions and commitments agreed upon verbally in meetings are forgotten without structured capture.
2. **Manual Calendar Scheduling**: Manually converting action items into calendar reminders across team members wastes valuable engineering time.
3. **Ambiguous Deadlines & Ownership**: Transcripts contain conversational phrases (e.g., 'Let's wrap this up by next Tuesday, John') that need deterministic date resolution.

## 3. High-Level Architecture
- **App Interface**: Streamlit / Python 3.12.
- **Core Processing Pipeline**:
  - `extraction.py`: Structured prompt extraction using Pydantic output schemas (extracting task description, assignee, deadline, priority).
  - `calendar_export.py`: RFC 5545 compliant `.ics` calendar file generator.
  - `reminders.py`: Automated markdown email summary and action item dispatch formatter.
  - `db.py`: SQLite historical transcript and meeting decision archive.
- **Testing**: `tests/test_meeting_agent.py` pytest suite validating JSON extraction parsing and `.ics` formatting.

## 4. Algorithmic Formulations
- **Temporal Anchor Resolution**: Resolves relative time expressions ('next Friday', 'in 3 days') relative to meeting timestamp into ISO 8601 UTC dates.
- **RFC 5545 iCalendar Generator**: Compiles action items into standard VEVENT blocks with `UID`, `DTSTART`, `DTEND`, `SUMMARY`, and `DESCRIPTION`.

## 5. Testing Strategy
- Automated pytest tests verifying `.ics` calendar structure validity, missing field fallbacks, and task parsing integrity.
