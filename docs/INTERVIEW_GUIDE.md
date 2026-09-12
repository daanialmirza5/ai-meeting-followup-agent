# AI Meeting Follow-Up Agent — Interview Guide & Technical Defense

## 1. Pitches
- **30-Second Pitch**: "AI Meeting Follow-Up Agent extracts structured action items, assignees, and deadlines from meeting transcripts and automatically generates RFC 5545 iCalendar files and email follow-up drafts."
- **2-Minute Pitch**: "Post-meeting follow-ups are notoriously manual and error-prone. This project automates the post-meeting workflow. Using Python, Pydantic, and structured LLM extraction, it parses conversational transcripts into strongly typed action items. It resolves relative conversational dates into exact ISO timestamps and compiles them into standard RFC 5545 `.ics` calendar invitation files that import seamlessly into Google Calendar, Outlook, and Apple Calendar."

## 2. Key Technical Q&A
- **Q: How do you guarantee the LLM outputs valid calendar dates?**
  - **A**: We pass the exact meeting date as a reference anchor in the system prompt and enforce structured Pydantic schema decoding. If the model outputs an unparseable date, the fallback parser defaults to `meeting_date + 7 days` with an explicit 'Deadline unconfirmed' flag.
