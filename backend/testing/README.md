# Reallocation testing

`mock_data.sql` contains a small, deterministic dataset for exercising the
reallocation service against the real application schema.

From `backend/`, run all tests in this folder with:

```sh
python -m unittest discover -s testing -v
```

To create a database that can be inspected manually, run:

```sh
python -m testing.create_mock_database
```

This writes the ignored file `testing/mock_reallocation.sqlite3`. Running the
command again safely replaces that generated fixture database.
