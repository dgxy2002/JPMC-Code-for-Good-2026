import { fetchSessions } from './api.js';

export const SLOT_TIMES = {
  AM: '8:30 - 12:00',
  PM: '2:00 - 5:30',
};

const LOCATIONS = {
  CLINIC: 'Centre',
  HOME: 'Home',
  SCHOOL: 'School',
};

const pad = (n) => String(n).padStart(2, '0');
export const toDateString = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const fromDateString = (s) => {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d);
};
export const monthKey = (year, monthIndex) => `${year}-${pad(monthIndex + 1)}`;

export function getSessionsForDate(sessionsByMonth, dateString) {
  return (sessionsByMonth[dateString.slice(0, 7)] || []).filter((s) => s.date === dateString);
}

export function getSessionsForMonth(sessionsByMonth, year, monthIndex) {
  return sessionsByMonth[monthKey(year, monthIndex)] || [];
}

export async function fetchSessionsForMonth(year, monthIndex, signal) {
  const first = toDateString(new Date(year, monthIndex, 1));
  const last = toDateString(new Date(year, monthIndex + 1, 0));
  const sessions = await fetchSessions(first, last, signal);
  return sessions.map((session) => ({
    ...session,
    student: session.student_name,
    therapist: session.therapist_name,
    therapistId: session.therapist_id,
    level: session.therapist_seniority,
    location: LOCATIONS[session.session_type] || 'Centre',
    time: SLOT_TIMES[session.slot],
  }));
}
