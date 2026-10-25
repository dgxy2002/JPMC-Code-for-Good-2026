# Synthetic fixtures

Every record in this directory is synthetic and uses a numbered placeholder
name. The records exist only to exercise scheduling and reallocation behavior;
they do not represent real students, therapists, sessions, or accounts.

From `backend/`, load the fixtures into the default ignored SQLite database:

```sh
python ../dummy/populate_db.py
```

The loader rejects malformed records, broken foreign keys, and non-empty
databases. `spread_october_sessions.py` can then redistribute the seeded
sessions across October 2026 for the dated demo scenario.

Never replace these files with production exports or other personal data.
