import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi import HTTPException

from app.routes.sessions import list_schedule_sessions_route
from app.server.db import connect_db, init_db


class ScheduleRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "test.sqlite3"
        init_db(path)
        self.db = connect_db(path)

    def tearDown(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def test_empty_range_and_reversed_dates(self) -> None:
        self.assertEqual(
            list_schedule_sessions_route(
                date(2026, 10, 1), date(2026, 10, 31), self.db
            ),
            [],
        )
        with self.assertRaises(HTTPException) as error:
            list_schedule_sessions_route(
                date(2026, 10, 31), date(2026, 10, 1), self.db
            )
        self.assertEqual(error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
