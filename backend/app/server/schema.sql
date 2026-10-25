CREATE TABLE IF NOT EXISTS therapists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
    seniority TEXT NOT NULL CHECK (seniority IN ('SENIOR', 'JUNIOR')),
    employment_type TEXT NOT NULL CHECK (employment_type IN ('FULL_TIME', 'PART_TIME')),
    unavailability TEXT NOT NULL DEFAULT '[]'
        CHECK (json_valid(unavailability) AND json_type(unavailability) = 'array')
);

CREATE TABLE IF NOT EXISTS students (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
    required_seniority TEXT NOT NULL
        CHECK (required_seniority IN ('SENIOR', 'JUNIOR', 'ANY'))
);

CREATE TABLE IF NOT EXISTS student_therapists (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES students(id),
    therapist_id TEXT NOT NULL REFERENCES therapists(id),
    relationship TEXT NOT NULL CHECK (relationship IN ('TEAM', 'HISTORY')),
    UNIQUE (student_id, therapist_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES students(id),
    original_therapist_id TEXT NOT NULL REFERENCES therapists(id),
    assigned_therapist_id TEXT REFERENCES therapists(id),
    date TEXT NOT NULL CHECK (
        length(date) = 10 AND
        date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
    ),
    slot TEXT NOT NULL CHECK (slot IN ('AM', 'PM')),
    session_type TEXT NOT NULL CHECK (session_type IN ('CLINIC', 'HOME', 'SCHOOL')),
    status TEXT NOT NULL CHECK (
        status IN ('SCHEDULED', 'NEEDS_REPLACEMENT', 'REALLOCATED', 'CANCELLED', 'COMPLETED')
    )
);

CREATE INDEX IF NOT EXISTS idx_sessions_date_slot ON sessions(date, slot);
CREATE INDEX IF NOT EXISTS idx_sessions_assigned_date_slot
    ON sessions(assigned_therapist_id, date, slot);
CREATE INDEX IF NOT EXISTS idx_student_therapists_therapist
    ON student_therapists(therapist_id);
