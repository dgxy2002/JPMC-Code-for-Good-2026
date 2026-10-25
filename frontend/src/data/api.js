const API_BASE_URL = (process.env.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

async function requestJson(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error(`Cannot reach the backend at ${API_BASE_URL}. Check that it is running and the API URL is correct.`);
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : `Backend request failed (${response.status}).`;
    throw new Error(detail);
  }
  return payload;
}

export function fetchTherapistsByName(name) {
  return requestJson(`/therapists?name=${encodeURIComponent(name)}`);
}

export function fetchSessions(startDate, endDate, signal) {
  return requestJson(`/sessions?start_date=${startDate}&end_date=${endDate}`, { signal });
}

export function createStudent(student) {
  return requestJson('/students', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(student),
  });
}

export function reallocateSession(session, therapistId, reason) {
  return requestJson(`/sessions/${encodeURIComponent(session.id)}/reallocate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ therapist_id: therapistId, slot: session.slot, reason }),
  });
}
