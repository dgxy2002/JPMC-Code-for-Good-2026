import sqlite3
import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from app.repositories.therapists import (
    add_unavailability_period,
    create_therapist,
    delete_therapist,
    find_therapists_by_name,
    get_therapist,
    list_therapists,
    update_therapist,
)
from app.server.db import connect_db, init_db


class TherapistRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "test.sqlite3"
        init_db(path)
        self.db = connect_db(path)

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def test_crud_and_unavailability(self) -> None:
        therapist = create_therapist(
            self.db,
            {
                "name": "Alex",
                "seniority": "SENIOR",
                "employment_type": "FULL_TIME",
            },
        )
        UUID(therapist["id"])
        self.assertEqual(therapist["unavailability"], [])
        self.assertEqual(get_therapist(self.db, therapist["id"]), therapist)
        self.assertEqual(list_therapists(self.db), [therapist])

        day = {"start": "2026-10-19", "end": "2026-10-19"}
        updated = add_unavailability_period(self.db, therapist["id"], day)
        self.assertEqual(updated["unavailability"], [day])
        self.assertEqual(
            add_unavailability_period(self.db, therapist["id"], day)["unavailability"],
            [day],
        )
        renamed = update_therapist(self.db, therapist["id"], {"name": "Alex B"})
        self.assertEqual(renamed["name"], "Alex B")
        self.assertTrue(delete_therapist(self.db, therapist["id"]))
        self.assertFalse(delete_therapist(self.db, therapist["id"]))

    def test_rejects_invalid_dates_and_enum_values(self) -> None:
        therapist = create_therapist(
            self.db,
            {
                "name": "Alex",
                "seniority": "SENIOR",
                "employment_type": "FULL_TIME",
                "unavailability": [],
            },
        )
        with self.assertRaises(ValueError):
            add_unavailability_period(
                self.db, therapist["id"], {"start": "2026-10-20", "end": "2026-10-19"}
            )
        with self.assertRaises(sqlite3.IntegrityError):
            update_therapist(self.db, therapist["id"], {"seniority": "OTHER"})

    def test_find_therapist_by_name(self) -> None:
        therapist = create_therapist(
            self.db,
            {"name": "Therapist One", "seniority": "SENIOR", "employment_type": "FULL_TIME"},
        )
        self.assertEqual(
            find_therapists_by_name(self.db, "therapist one"),
            [{"id": therapist["id"], "name": "Therapist One"}],
        )
        self.assertEqual(find_therapists_by_name(self.db, "Jen"), [])

    def test_reason_is_saved_when_date_is_already_unavailable(self) -> None:
        therapist = create_therapist(
            self.db,
            {
                "name": "Therapist One",
                "seniority": "SENIOR",
                "employment_type": "FULL_TIME",
                "unavailability": [{"start": "2026-10-19", "end": "2026-10-21"}],
            },
        )
        updated = add_unavailability_period(
            self.db,
            therapist["id"],
            {"start": "2026-10-20", "end": "2026-10-20", "reason": "Urgent Leave"},
        )
        self.assertEqual(updated["unavailability"][-1]["reason"], "Urgent Leave")


if __name__ == "__main__":
    unittest.main()
