-- Mock therapists used to exercise availability and allocation priorities.
INSERT INTO therapists
    (id, name, seniority, employment_type, unavailability)
VALUES
    (
        'therapist-original-main',
        'Olivia Original',
        'JUNIOR',
        'FULL_TIME',
        '[{"start":"2026-10-22","end":"2026-10-22"}]'
    ),
    (
        'therapist-team-unavailable',
        'Tessa Team',
        'SENIOR',
        'FULL_TIME',
        '[{"start":"2026-10-21","end":"2026-10-22"}]'
    ),
    (
        'therapist-history-booked',
        'Harper History',
        'SENIOR',
        'FULL_TIME',
        '[{"start":"2026-10-22","end":"2026-10-22"}]'
    ),
    (
        'therapist-free-junior',
        'Freya Free',
        'JUNIOR',
        'FULL_TIME',
        '[{"start":"2026-10-22","end":"2026-10-22"}]'
    ),
    (
        'therapist-free-senior',
        'Sam Senior',
        'SENIOR',
        'PART_TIME',
        '[{"start":"2026-10-22","end":"2026-10-22"}]'
    ),
    (
        'therapist-original-cancel',
        'Casey Cancel',
        'SENIOR',
        'FULL_TIME',
        '[]'
    );

INSERT INTO students (id, name, required_seniority)
VALUES
    ('student-main', 'Mia Main', 'JUNIOR'),
    ('student-other', 'Owen Other', 'ANY'),
    ('student-cancel', 'Chris Cancel', 'ANY');

INSERT INTO student_therapists
    (id, student_id, therapist_id, relationship)
VALUES
    (
        'relationship-main-team',
        'student-main',
        'therapist-team-unavailable',
        'TEAM'
    );

-- A completed session makes therapist-history-booked the historical choice.
INSERT INTO sessions
    (id, student_id, original_therapist_id, assigned_therapist_id,
     date, slot, session_type, status)
VALUES
    (
        'session-main-history',
        'student-main',
        'therapist-history-booked',
        NULL,
        '2026-09-15',
        'AM',
        'CLINIC',
        'COMPLETED'
    ),
    -- This booking prevents the historical therapist taking the target slot.
    (
        'session-conflict',
        'student-other',
        'therapist-history-booked',
        NULL,
        '2026-10-21',
        'AM',
        'SCHOOL',
        'SCHEDULED'
    ),
    (
        'session-target',
        'student-main',
        'therapist-original-main',
        NULL,
        '2026-10-21',
        'AM',
        'HOME',
        'NEEDS_REPLACEMENT'
    ),
    -- Every therapist except the original is unavailable on this date.
    (
        'session-no-candidate',
        'student-cancel',
        'therapist-original-cancel',
        NULL,
        '2026-10-22',
        'PM',
        'CLINIC',
        'NEEDS_REPLACEMENT'
    );
