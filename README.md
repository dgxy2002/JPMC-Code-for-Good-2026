# Care Allocation Scheduler

A mobile-first scheduling prototype for coordinating therapy sessions and
reallocating sessions when a therapist becomes unavailable. It was created for
JPMorganChase Code for Good 2026.

The repository contains an Expo/React Native client, a FastAPI API, and a local
SQLite seed workflow. The allocation service prefers an available member of a
student's existing care team, then a therapist with prior session history, and
then an appropriate seniority match.

> [!IMPORTANT]
> This is a demonstration application, not a production clinical system. It
> has local-only demo authentication, no authorization on the API, and no
> production privacy or security controls. Do not deploy it or load real
> personal, health, student, or employee data without completing a security
> and privacy review.

## Repository layout

```text
backend/   FastAPI application, SQLite schema, and automated tests
dummy/     Sanitized synthetic fixtures and database seed utilities
frontend/  Expo/React Native application and JavaScript tests
```

All bundled people are numbered placeholders (for example, `Student 01` and
`Therapist 01`). The UUIDs, schedules, relationships, and credentials are test
fixtures only and do not represent real people or accounts.

## Prerequisites

- Python 3.10 or newer
- Node.js 22.13 or newer and npm

## Local setup

### 1. Start the API

From the repository root:

```sh
cd backend
python -m venv .venv
```

Activate the virtual environment for your shell, then install and seed:

```sh
python -m pip install -r requirements.txt
python ../dummy/populate_db.py
python -m uvicorn app.server.main:app --reload
```

The seed command creates the ignored file
`backend/data/reallocation.sqlite3`. It intentionally refuses to overwrite a
database that already contains records.

The API listens at `http://127.0.0.1:8000` by default. Interactive API docs are
available at `http://127.0.0.1:8000/docs` while it is running.

### 2. Start the client

In a second terminal:

```sh
cd frontend
npm ci
npm run web
```

The default API URL is `http://127.0.0.1:8000`. To use another address, copy
`frontend/.env.example` to `frontend/.env.local` and change
`EXPO_PUBLIC_API_URL`. Android emulators normally reach the host at
`http://10.0.2.2:8000`; a physical device needs the computer's LAN address.

If the frontend is served from a non-localhost origin, set the API's
`FRONTEND_ORIGINS` environment variable to a comma-separated allowlist of exact
origins before starting Uvicorn.

Demo logins:

- Admin: `admin@example.test` / `demo123`
- Therapist: `therapist01@example.test` / `demo123`

These credentials are intentionally public and only unlock client-side demo
routes. They do not secure the API.

## Tests

Run the backend suites from `backend/`:

```sh
python -m unittest discover -s tests -v
python -m unittest discover -s testing -v
```

Run the frontend tests from `frontend/`:

```sh
node --test
```

## Configuration and public-repository safety

- Local environment files, databases, private keys, signing files, dependency
  folders, and Expo build state are ignored by Git.
- `EXPO_PUBLIC_*` values are bundled into the client. Never put a secret in
  `EXPO_PUBLIC_API_URL` or any other `EXPO_PUBLIC_*` variable.
- Only synthetic fixtures belong in `dummy/`. Do not commit exports or copies
  of production data.
- Before each public push, review `git status`, inspect the staged diff, and run
  a secret scanner over both the working tree and commit history.

See [SECURITY.md](SECURITY.md) for vulnerability reporting and the prototype's
security boundaries.

## License

No project-wide open-source license has been selected. The notice in
`frontend/LICENSE` belongs to the upstream Expo template and does not grant a
license to the repository as a whole. Add an appropriate root license before
inviting reuse or external contributions.
