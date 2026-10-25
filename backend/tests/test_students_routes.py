import tempfile
import unittest
from pathlib import Path

from app.routes.students import StudentCreateRequest, create_student_route
from app.server.db import connect_db, init_db


class StudentRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "test.sqlite3"
        init_db(path)
        self.db = connect_db(path)

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def test_create_student_route_returns_created_student(self) -> None:
        created = create_student_route(
            StudentCreateRequest(name="Alice Tan", required_seniority="ANY"),
            self.db,
        )

        self.assertEqual(created["name"], "Alice Tan")
        self.assertEqual(created["required_seniority"], "ANY")
        stored = self.db.execute(
            "SELECT name, required_seniority FROM students WHERE id = ?",
            (created["id"],),
        ).fetchone()
        self.assertEqual(dict(stored), {"name": "Alice Tan", "required_seniority": "ANY"})


if __name__ == "__main__":
    unittest.main()
