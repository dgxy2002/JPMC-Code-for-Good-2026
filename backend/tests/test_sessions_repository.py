import sqlite3
import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from app.server.db import connect_db, init_db
from app.repositories.sessions import (
    create_session,
    delete_session,
    get_session,
    list_schedule_sessions,
    list_sessions,
    update_session,
)


class SessionRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "test.sqlite3"
        init_db(path)
        self.db = connect_db(path)
        self.student_id = str(uuid4())
        self.therapist_id = str(uuid4())
        self.db.execute(
            "INSERT INTO students (id, name, required_seniority) VALUES (?, ?, ?)",
            (self.student_id, "Student", "ANY"),
        )
        self.db.execute(
            "INSERT INTO therapists (id, name, seniority, employment_type) VALUES (?, ?, ?, ?)",
            (self.therapist_id, "Therapist", "SENIOR", "FULL_TIME"),
        )
        self.session_data = {
            "student_id": self.student_id,
            "original_therapist_id": self.therapist_id,
            "assigned_therapist_id": None,
            "date": "2026-10-16",
            "slot": "AM",
            "session_type": "CLINIC",
            "status": "SCHEDULED",
        }

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def test_create_read_list_update_delete(self) -> None:
        created = create_session(self.db, self.session_data)
        UUID(created["id"])
        self.assertEqual(created["date"], "2026-10-16")
        self.assertEqual(get_session(self.db, created["id"]), created)
        self.assertEqual(list_sessions(self.db), [created])

        updated = update_session(
            self.db,
            created["id"],
            {"assigned_therapist_id": self.therapist_id, "status": "REALLOCATED"},
        )
        self.assertEqual(updated["assigned_therapist_id"], self.therapist_id)
        self.assertEqual(updated["status"], "REALLOCATED")
        cleared = update_session(self.db, created["id"], {"assigned_therapist_id": None})
        self.assertIsNone(cleared["assigned_therapist_id"])

        self.assertTrue(delete_session(self.db, created["id"]))
        self.assertFalse(delete_session(self.db, created["id"]))
        self.assertIsNone(get_session(self.db, created["id"]))
        self.assertEqual(list_sessions(self.db), [])

    def test_rejects_invalid_changes_and_foreign_keys(self) -> None:
        created = create_session(self.db, self.session_data)
        with self.assertRaises(ValueError):
            update_session(self.db, created["id"], {"id": "replacement"})
        with self.assertRaises(ValueError):
            update_session(self.db, created["id"], {"date": "2026-02-30"})
        with self.assertRaises(sqlite3.IntegrityError):
            update_session(
                self.db, created["id"], {"assigned_therapist_id": str(uuid4())}
            )

    def test_schedule_listing_filters_dates_and_resolves_current_therapist(self) -> None:
        replacement_id = str(uuid4())
        self.db.execute(
            "INSERT INTO therapists (id, name, seniority, employment_type) VALUES (?, ?, ?, ?)",
            (replacement_id, "Replacement", "JUNIOR", "FULL_TIME"),
        )
        previous = create_session(
            self.db, {**self.session_data, "date": "2026-10-15"}
        )
        scheduled = create_session(self.db, self.session_data)
        reallocated = create_session(
            self.db,
            {
                **self.session_data,
                "date": "2026-10-17",
                "assigned_therapist_id": replacement_id,
                "status": "REALLOCATED",
            },
        )
        cancelled = create_session(
            self.db,
            {**self.session_data, "date": "2026-10-18", "status": "CANCELLED"},
        )
        following = create_session(
            self.db, {**self.session_data, "date": "2026-10-19"}
        )

        sessions = list_schedule_sessions(self.db, "2026-10-16", "2026-10-18")

        self.assertEqual(
            [row["id"] for row in sessions],
            [scheduled["id"], reallocated["id"], cancelled["id"]],
        )
        self.assertEqual(sessions[0]["student_name"], "Student")
        self.assertEqual(sessions[0]["therapist_id"], self.therapist_id)
        self.assertEqual(sessions[0]["therapist_name"], "Therapist")
        self.assertEqual(sessions[0]["therapist_seniority"], "SENIOR")
        self.assertEqual(sessions[1]["therapist_id"], replacement_id)
        self.assertEqual(sessions[1]["therapist_name"], "Replacement")
        self.assertEqual(sessions[1]["therapist_seniority"], "JUNIOR")
        self.assertIsNone(sessions[2]["therapist_id"])
        self.assertIsNone(sessions[2]["therapist_name"])
        self.assertNotIn(previous["id"], [row["id"] for row in sessions])
        self.assertNotIn(following["id"], [row["id"] for row in sessions])


if __name__ == "__main__":
    unittest.main()
