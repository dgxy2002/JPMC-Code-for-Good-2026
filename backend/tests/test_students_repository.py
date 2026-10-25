import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from app.repositories.students import create_student, get_student
from app.server.db import connect_db, init_db


class StudentRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "test.sqlite3"
        init_db(path)
        self.db = connect_db(path)

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def test_create_student_generates_id_trims_name_and_persists(self) -> None:
        created = create_student(
            self.db,
            {"name": "  Alice Tan  ", "required_seniority": "JUNIOR"},
        )

        UUID(created["id"])
        self.assertEqual(created["name"], "Alice Tan")
        self.assertEqual(created["required_seniority"], "JUNIOR")
        self.assertEqual(get_student(self.db, created["id"]), created)

    def test_rejects_blank_name_and_invalid_seniority(self) -> None:
        with self.assertRaises(ValueError):
            create_student(
                self.db,
                {"name": "   ", "required_seniority": "ANY"},
            )
        with self.assertRaises(ValueError):
            create_student(
                self.db,
                {"name": "Alice", "required_seniority": "LEAD"},
            )


if __name__ == "__main__":
    unittest.main()
