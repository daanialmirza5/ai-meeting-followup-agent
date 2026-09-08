"""Simulated autonomous reminder/follow-up loop.

No real email/SMS service is wired up (that would need another API key) - instead this
logs what the agent *would* send, with real due-date logic driving *when* it sends. Every
time the dashboard loads, this runs and any newly-due pending items get a fresh reminder
logged automatically, which is what "autonomous" means in a request/response web app
without a background worker.
"""
from datetime import datetime, timedelta, timezone

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
            try:
                return datetime.fromisoformat(clean)
            except (ValueError, TypeError):
                raise ValueError(f"Unable to parse date: {timestr}")

    dateparser = _FallbackParser()

import db

REMINDER_COOLDOWN = timedelta(hours=20)  # don't re-remind more than ~once/day in a demo session


def _parse_deadline(deadline: str | None):
    if not deadline:
        return None
    try:
        dt = dateparser.parse(deadline, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, OverflowError):
        return None


def run_reminder_sweep() -> list[str]:
    """Checks every pending action item; logs a reminder for any that are due (or overdue)
    and haven't been reminded recently. Returns human-readable messages for what was sent,
    so the UI can show a toast for what just happened."""
    sent = []
    now = datetime.now(timezone.utc)
    for item in db.list_action_items(status="pending"):
        due = _parse_deadline(item["deadline"])
        is_due = due is not None and due <= now + timedelta(days=1)
        if not is_due:
            continue

        last_reminder = db.last_reminder_time(item["id"])
        if last_reminder:
            try:
                reference_dt = dateparser.parse(last_reminder)
                if reference_dt.tzinfo is None:
                    reference_dt = reference_dt.replace(tzinfo=timezone.utc)
                if now - reference_dt < REMINDER_COOLDOWN:
                    continue
            except (ValueError, OverflowError):
                pass

        overdue = due < now
        phrasing = "is overdue" if overdue else "is due soon"
        message = (
            f"Reminder sent to {item['owner']}: \"{item['task']}\" {phrasing} "
            f"(deadline: {item['deadline']})."
        )
        db.log_reminder(item["id"], message)
        sent.append(message)
    return sent


def send_manual_reminder(item) -> str:
    message = f"Reminder sent to {item['owner']}: \"{item['task']}\" (deadline: {item['deadline'] or 'not specified'})."
    db.log_reminder(item["id"], message)
    return message
