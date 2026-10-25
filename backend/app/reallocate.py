"""Therapist selection rules for sessions that need a replacement."""


def reallocate_therapist(
    session,
    student,
    therapists,
    student_team,
    past_sessions,
    is_available,
):
    """Mutate and return ``session`` after selecting the best replacement.

    Candidates are considered in this order: a therapist on the student's
    team, a therapist who completed a previous session with the student, a
    therapist of the requested seniority, then a therapist one seniority level
    above or below the request. Students with an ``ANY`` requirement skip the
    seniority-specific steps.
    """

    if session.status != "NEEDS_REPLACEMENT":
        return session

    unavailable_therapist_id = (
        session.assigned_therapist_id or session.original_therapist_id
    )

    def get_available(candidate_therapists):
        return [
            therapist
            for therapist in candidate_therapists
            if therapist.id != unavailable_therapist_id
            and is_available(therapist.id, session.date, session.slot)
        ]

    def assign(therapist):
        session.assigned_therapist_id = therapist.id
        session.status = "REALLOCATED"
        return session

    team_candidates = [
        therapist for therapist in therapists if therapist.id in student_team
    ]
    available = get_available(team_candidates)
    if available:
        return assign(available[0])

    previous_therapist_ids = set()
    for past_session in past_sessions:
        if (
            past_session.student_id == student.id
            and past_session.status == "COMPLETED"
        ):
            previous_therapist_ids.add(
                past_session.assigned_therapist_id
                or past_session.original_therapist_id
            )

    history_candidates = [
        therapist
        for therapist in therapists
        if therapist.id in previous_therapist_ids
        and therapist.id not in student_team
    ]
    available = get_available(history_candidates)
    if available:
        return assign(available[0])

    if student.required_seniority == "ANY":
        other_candidates = [
            therapist
            for therapist in therapists
            if therapist.id not in student_team
            and therapist.id not in previous_therapist_ids
        ]
        available = get_available(other_candidates)
        if available:
            return assign(available[0])

        session.status = "CANCELLED"
        session.assigned_therapist_id = None
        return session

    same_seniority_candidates = [
        therapist
        for therapist in therapists
        if therapist.seniority == student.required_seniority
        and therapist.id not in student_team
        and therapist.id not in previous_therapist_ids
    ]
    available = get_available(same_seniority_candidates)
    if available:
        return assign(available[0])

    if student.required_seniority == "JUNIOR":
        higher_seniority_candidates = [
            therapist
            for therapist in therapists
            if therapist.seniority == "SENIOR"
            and therapist.id not in student_team
            and therapist.id not in previous_therapist_ids
        ]
        available = get_available(higher_seniority_candidates)
        if available:
            return assign(available[0])

    if student.required_seniority == "SENIOR":
        lower_seniority_candidates = [
            therapist
            for therapist in therapists
            if therapist.seniority == "JUNIOR"
            and therapist.id not in student_team
            and therapist.id not in previous_therapist_ids
        ]
        available = get_available(lower_seniority_candidates)
        if available:
            return assign(available[0])

    session.assigned_therapist_id = None
    session.status = "CANCELLED"
    return session
