import sqlite3
import unittest
from pathlib import Path

from app.reallocation_service import reallocate_session, session_reallocate


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "app" / "server" / "schema.sql"


class ReallocationServiceTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self._add_student("student", "JUNIOR")
        self._add_therapist("original", "JUNIOR")

    def tearDown(self):
        self.connection.close()

    def _add_student(self, student_id, required_seniority):
        self.connection.execute(
            "INSERT INTO students (id, name, required_seniority) VALUES (?, ?, ?)",
            (student_id, student_id.title(), required_seniority),
        )

    def _add_therapist(self, therapist_id, seniority="JUNIOR", unavailability="[]"):
        self.connection.execute(
            """
            INSERT INTO therapists
                (id, name, seniority, employment_type, unavailability)
            VALUES (?, ?, ?, 'FULL_TIME', ?)
            """,
            (therapist_id, therapist_id.title(), seniority, unavailability),
        )

    def _add_session(
        self,
        session_id,
        therapist_id="original",
        *,
        student_id="student",
        date="2026-10-19",
        slot="AM",
        status="NEEDS_REPLACEMENT",
        assigned_therapist_id=None,
    ):
        self.connection.execute(
            """
            INSERT INTO sessions
                (id, student_id, original_therapist_id,
                 assigned_therapist_id, date, slot, session_type, status)
            VALUES (?, ?, ?, ?, ?, ?, 'CLINIC', ?)
            """,
            (
                session_id,
                student_id,
                therapist_id,
                assigned_therapist_id,
                date,
                slot,
                status,
            ),
        )

    def test_prefers_available_team_member_and_persists_assignment(self):
        self._add_therapist("team-member", "SENIOR")
        self._add_therapist("same-seniority", "JUNIOR")
        self.connection.execute(
            """
            INSERT INTO student_therapists
                (id, student_id, therapist_id, relationship)
            VALUES ('link', 'student', 'team-member', 'TEAM')
            """
        )
        self._add_session("target")

        result = reallocate_session(self.connection, "target")

        self.assertEqual(result.status, "REALLOCATED")
        self.assertEqual(result.assigned_therapist_id, "team-member")
        stored = self.connection.execute(
            "SELECT assigned_therapist_id, status FROM sessions WHERE id = 'target'"
        ).fetchone()
        self.assertEqual(dict(stored), {
            "assigned_therapist_id": "team-member",
            "status": "REALLOCATED",
        })

    def test_skips_unavailable_and_already_booked_therapists(self):
        self._add_therapist(
            "a-unavailable",
            unavailability='[{"start":"2026-10-18","end":"2026-10-20"}]',
        )
        self._add_therapist("b-booked")
        self._add_therapist("c-free")
        self._add_student("other-student", "ANY")
        self._add_session(
            "conflict",
            "b-booked",
            student_id="other-student",
            status="SCHEDULED",
        )
        self._add_session("target")

        result = reallocate_session(self.connection, "target")

        self.assertEqual(result.assigned_therapist_id, "c-free")

    def test_prefers_therapist_from_completed_session_over_seniority_match(self):
        self._add_therapist("a-history", "SENIOR")
        self._add_therapist("b-same-seniority", "JUNIOR")
        self._add_session(
            "past",
            "a-history",
            date="2026-10-01",
            status="COMPLETED",
        )
        self._add_session("target")

        result = reallocate_session(self.connection, "target")

        self.assertEqual(result.assigned_therapist_id, "a-history")

    def test_cancels_when_no_replacement_is_available(self):
        self._add_session("target")

        result = reallocate_session(self.connection, "target")

        self.assertEqual(result.status, "CANCELLED")
        self.assertIsNone(result.assigned_therapist_id)

    def test_non_replacement_session_is_returned_unchanged(self):
        self._add_therapist("assigned")
        self._add_session(
            "target",
            status="REALLOCATED",
            assigned_therapist_id="assigned",
        )

        result = reallocate_session(self.connection, "target")

        self.assertEqual(result.status, "REALLOCATED")
        self.assertEqual(result.assigned_therapist_id, "assigned")

    def test_missing_session_returns_none(self):
        self.assertIsNone(reallocate_session(self.connection, "missing"))

    def test_session_reallocate_marks_day_unavailable_and_updates_both_slots(self):
        self._add_therapist("replacement")
        self._add_session("morning", status="SCHEDULED", slot="AM")
        self._add_session("afternoon", status="SCHEDULED", slot="PM")
        self._add_session("next-day", status="SCHEDULED", date="2026-10-20")

        result = session_reallocate(self.connection, "morning", "original", "AM")

        self.assertEqual(result.status, "REALLOCATED")
        self.assertEqual(result.assigned_therapist_id, "replacement")
        self.assertEqual(
            self.connection.execute(
                "SELECT unavailability FROM therapists WHERE id = 'original'"
            ).fetchone()[0],
            '[{"start": "2026-10-19", "end": "2026-10-19"}]',
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT status, assigned_therapist_id FROM sessions WHERE id = 'afternoon'"
            ).fetchone()[:],
            ("REALLOCATED", "replacement"),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT status FROM sessions WHERE id = 'next-day'"
            ).fetchone()[0],
            "SCHEDULED",
        )

    def test_session_reallocate_rejects_wrong_slot_or_therapist(self):
        self._add_session("target", status="SCHEDULED")
        with self.assertRaises(ValueError):
            session_reallocate(self.connection, "target", "original", "PM")
        with self.assertRaises(ValueError):
            session_reallocate(self.connection, "target", "someone-else", "AM")
        self.assertEqual(
            self.connection.execute(
                "SELECT unavailability FROM therapists WHERE id = 'original'"
            ).fetchone()[0],
            "[]",
        )
        self.assertIsNone(session_reallocate(self.connection, "missing", "original", "AM"))

    def test_session_reallocate_replaces_current_assignment(self):
        self._add_therapist("current")
        self._add_session(
            "target", status="REALLOCATED", assigned_therapist_id="current"
        )

        result = session_reallocate(self.connection, "target", "current", "AM")

        self.assertEqual(result.status, "REALLOCATED")
        self.assertEqual(result.assigned_therapist_id, "original")
        self.assertEqual(
            self.connection.execute(
                "SELECT unavailability FROM therapists WHERE id = 'current'"
            ).fetchone()[0],
            '[{"start": "2026-10-19", "end": "2026-10-19"}]',
        )

    def test_session_reallocate_records_reason_for_day(self):
        self._add_therapist("replacement")
        self._add_session("target", status="SCHEDULED")

        result = session_reallocate(
            self.connection, "target", "original", "AM", "Medical Leave"
        )

        self.assertEqual(result.status, "REALLOCATED")
        self.assertEqual(
            self.connection.execute(
                "SELECT unavailability FROM therapists WHERE id = 'original'"
            ).fetchone()[0],
            '[{"start": "2026-10-19", "end": "2026-10-19", "reason": "Medical Leave"}]',
        )


if __name__ == "__main__":
    unittest.main()
