"""End-to-end checks using the populated mock SQLite database."""

import unittest

from app.reallocation_service import reallocate_session
from testing.create_mock_database import create_mock_database


class MockDatabaseReallocationTests(unittest.TestCase):
    def setUp(self):
        self.connection = create_mock_database()

    def tearDown(self):
        self.connection.close()

    def test_falls_through_unavailable_and_booked_priority_candidates(self):
        result = reallocate_session(self.connection, "session-target")

        self.assertEqual(result.status, "REALLOCATED")
        self.assertEqual(
            result.assigned_therapist_id,
            "therapist-free-junior",
        )
        stored = self.connection.execute(
            """
            SELECT assigned_therapist_id, status
            FROM sessions
            WHERE id = 'session-target'
            """
        ).fetchone()
        self.assertEqual(
            dict(stored),
            {
                "assigned_therapist_id": "therapist-free-junior",
                "status": "REALLOCATED",
            },
        )

    def test_cancels_session_when_fixture_has_no_available_candidate(self):
        result = reallocate_session(self.connection, "session-no-candidate")

        self.assertEqual(result.status, "CANCELLED")
        self.assertIsNone(result.assigned_therapist_id)
        stored = self.connection.execute(
            """
            SELECT assigned_therapist_id, status
            FROM sessions
            WHERE id = 'session-no-candidate'
            """
        ).fetchone()
        self.assertEqual(
            dict(stored),
            {"assigned_therapist_id": None, "status": "CANCELLED"},
        )


if __name__ == "__main__":
    unittest.main()
