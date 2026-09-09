"""iCalendar (RFC 5545) export module for AI Meeting Follow-Up Agent.

Generates standard .ics calendar payloads so users can export action items
directly into Google Calendar, Apple Calendar, Outlook, or Thunderbird.
"""
from datetime import datetime, timezone
import uuid
import re

try:
    from dateutil import parser as dateparser
except ImportError:
    class _FallbackParser:
        @staticmethod
        def parse(timestr, fuzzy=False):
            clean = str(timestr).strip()
            for fmt in (
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S",
            ):
                try:
                    return datetime.strptime(clean[:19], fmt)
                except (ValueError, TypeError):
                    continue
            return datetime.fromisoformat(clean)

    dateparser = _FallbackParser()


def _clean_ics_text(text: str) -> str:
    """Escapes special characters according to RFC 5545 specifications."""
    if not text:
        return ""
    # Escape backslashes, semicolons, commas, and newlines
    escaped = text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return escaped.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")


def generate_ics_calendar(action_items: list[dict], calendar_name: str = "Meeting Action Items") -> str:
    """Transforms a list of action item records into a valid iCalendar .ics string.
    
    Each item with an identifiable deadline becomes a VEVENT scheduled on that deadline date.
    Items without explicit deadlines are generated as all-day reminder tasks for today.
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Meeting Follow-Up Agent//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_clean_ics_text(calendar_name)}",
    ]

    for item in action_items:
        task = item.get("task", "Untitled Task")
        owner = item.get("owner", "Unassigned")
        decision = item.get("decision", "")
        meeting_title = item.get("meeting_title", "Meeting")
        deadline_raw = item.get("deadline")

        dt_due = None
        if deadline_raw:
            try:
                dt_due = dateparser.parse(str(deadline_raw), fuzzy=True)
                if dt_due.tzinfo is None:
                    dt_due = dt_due.replace(tzinfo=timezone.utc)
            except Exception:
                dt_due = None

        if dt_due is None:
            # Fallback to today's date if no parseable deadline
            dt_due = datetime.now(timezone.utc)

        dt_stamp = now_utc
        dt_start = dt_due.strftime("%Y%m%dT%H%M%SZ")
        # 1-hour default event duration
        dt_end = dt_due.replace(hour=(dt_due.hour + 1) % 24).strftime("%Y%m%dT%H%M%SZ")
        uid = f"task-{item.get('id', uuid.uuid4().hex)}@aimeetingagent"

        summary = f"[{owner}] {task}"
        description = f"Owner: {owner}\nMeeting: {meeting_title}"
        if decision:
            description += f"\nContext: {decision}"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dt_stamp}",
            f"DTSTART:{dt_start}",
            f"DTEND:{dt_end}",
            f"SUMMARY:{_clean_ics_text(summary)}",
            f"DESCRIPTION:{_clean_ics_text(description)}",
            f"STATUS:{'COMPLETED' if item.get('status') == 'completed' else 'CONFIRMED'}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
