"""Unit test suite for AI Meeting Follow-Up Agent.
Compatible with standard library unittest and pytest.
Tests database persistence, reminder scheduling/sweeps, extraction logic, and RFC 5545 calendar export.
"""
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import db
import reminders
from calendar_export import generate_ics_calendar, _clean_ics_text


class TestMeetingFollowUpAgent(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = Path(self.temp_dir) / "test_app.db"
        self._orig_db_path = db.DB_PATH
        db.DB_PATH = self.temp_db
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self._orig_db_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_db_creates_tables(self):
        """Verify all tables (meetings, action_items, reminders) are created."""
        with db.get_conn() as conn:
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            self.assertIn("meetings", tables)
            self.assertIn("action_items", tables)
            self.assertIn("reminders", tables)

    def test_meeting_and_action_item_lifecycle(self):
        """Verify meeting creation, action item insertion, status transition, and completion."""
        meeting_id = db.create_meeting("Sprint Planning", "Discussed roadmap and Q3 deliverables.")
        self.assertIsInstance(meeting_id, int)

        item_id = db.create_action_item(
            meeting_id=meeting_id,
            decision="Adopt GraphQL for client APIs",
            task="Write schema draft",
            owner="Alice",
            deadline="2026-10-15",
        )
        self.assertIsInstance(item_id, int)

        # Check pending items
        pending = db.list_action_items(status="pending")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["task"], "Write schema draft")
        self.assertEqual(pending[0]["owner"], "Alice")
        self.assertEqual(pending[0]["meeting_title"], "Sprint Planning")

        # Mark complete
        db.mark_complete(item_id)
        self.assertEqual(len(db.list_action_items(status="pending")), 0)
        completed = db.list_action_items(status="completed")
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["id"], item_id)
        self.assertIsNotNone(completed[0]["completed_at"])

        # Reopen
        db.reopen_item(item_id)
        self.assertEqual(len(db.list_action_items(status="pending")), 1)
        self.assertEqual(len(db.list_action_items(status="completed")), 0)

    def test_parse_deadline_utilities(self):
        """Test date parsing under valid and edge-case inputs."""
        self.assertIsNone(reminders._parse_deadline(None))
        self.assertIsNone(reminders._parse_deadline(""))

        dt = reminders._parse_deadline("2026-12-31")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 12)
        self.assertEqual(dt.day, 31)
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_reminder_sweep_triggers_for_due_items(self):
        """Verify autonomous reminder sweep picks up overdue or soon-due items and adheres to cooldown."""
        meeting_id = db.create_meeting("Operations Review", "Budget discussion")
        
        # Due in 12 hours
        tomorrow = (datetime.now(timezone.utc) + timedelta(hours=12)).strftime("%Y-%m-%d")
        item_id = db.create_action_item(
            meeting_id=meeting_id,
            decision="Renew server licenses",
            task="Submit invoice to finance",
            owner="Bob",
            deadline=tomorrow,
        )

        # First sweep should send a reminder
        sent = reminders.run_reminder_sweep()
        self.assertEqual(len(sent), 1)
        self.assertIn("Bob", sent[0])
        self.assertIn("Submit invoice to finance", sent[0])

        # Verify reminder logged in database
        log = db.all_reminders()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["task"], "Submit invoice to finance")

        # Second sweep immediately after should be throttled by cooldown
        sent_second = reminders.run_reminder_sweep()
        self.assertEqual(len(sent_second), 0)

    def test_manual_reminder_dispatch(self):
        """Verify manual reminder trigger logs an explicit reminder notification."""
        meeting_id = db.create_meeting("Ad-hoc Sync", "Quick sync")
        item_id = db.create_action_item(
            meeting_id=meeting_id,
            decision="Fix bug #402",
            task="Patch regex validator",
            owner="Charlie",
            deadline="2026-11-01",
        )

        item = db.list_action_items(status="pending")[0]
        msg = reminders.send_manual_reminder(item)

        self.assertIn("Charlie", msg)
        self.assertIn("Patch regex validator", msg)
        
        item_history = db.reminders_for_item(item_id)
        self.assertEqual(len(item_history), 1)
        self.assertIn("Patch regex validator", item_history[0]["message"])

    def test_ics_calendar_generation(self):
        """Verify standard RFC 5545 iCalendar payload format and attributes."""
        items = [
            {
                "id": 101,
                "task": "Deploy staging cluster",
                "owner": "Daanial Mirza",
                "decision": "Migrate from manual VMs to Kubernetes",
                "meeting_title": "Infra Sync",
                "deadline": "2026-11-20 14:00:00",
                "status": "pending",
            },
            {
                "id": 102,
                "task": "Review security audit report; approve findings",
                "owner": "Sarah",
                "decision": "Quarterly compliance review",
                "meeting_title": "Security Sync",
                "deadline": None,
                "status": "completed",
            }
        ]

        ics = generate_ics_calendar(items, calendar_name="Q4 Deliverables")
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("VERSION:2.0", ics)
        self.assertIn("PRODID:-//AI Meeting Follow-Up Agent//EN", ics)
        self.assertIn("X-WR-CALNAME:Q4 Deliverables", ics)
        self.assertIn("BEGIN:VEVENT", ics)
        self.assertIn("UID:task-101@aimeetingagent", ics)
        self.assertIn("SUMMARY:[Daanial Mirza] Deploy staging cluster", ics)
        self.assertIn("DESCRIPTION:Owner: Daanial Mirza\\nMeeting: Infra Sync\\nContext: Migrate from manual VMs to Kubernetes", ics)
        self.assertIn("STATUS:CONFIRMED", ics)
        self.assertIn("STATUS:COMPLETED", ics)
        self.assertIn("END:VCALENDAR", ics)

    def test_clean_ics_text_escaping(self):
        """Verify special character escaping (commas, semicolons, backslashes, newlines)."""
        raw = "Item 1, with semicolon; and newline\nnext line"
        cleaned = _clean_ics_text(raw)
        self.assertEqual(cleaned, "Item 1\\, with semicolon\\; and newline\\nnext line")


if __name__ == "__main__":
    unittest.main()
