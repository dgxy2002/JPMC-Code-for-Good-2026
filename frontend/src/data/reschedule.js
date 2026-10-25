import { reallocateSession } from './api.js';
import { getSessionsForDate } from './schedule.js';

const REALLOCATABLE_STATUSES = new Set(['SCHEDULED', 'NEEDS_REPLACEMENT', 'REALLOCATED']);

export function isReallocatableSession(session) {
  return REALLOCATABLE_STATUSES.has(session.status);
}

export function planReallocation(dates, sessionsByMonth, therapistId) {
  const targets = [];
  const skippedDates = [];
  for (const date of dates) {
    const session = getSessionsForDate(sessionsByMonth, date).find(
      (candidate) => candidate.therapistId === therapistId && isReallocatableSession(candidate),
    );
    if (session) targets.push({ date, session });
    else skippedDates.push(date);
  }
  return { targets, skippedDates };
}

export async function submitReallocationPlan(targets, therapistId, reason, send = reallocateSession) {
  const successfulDates = [];
  const failedDates = [];
  for (const { date, session } of targets) {
    try {
      await send(session, therapistId, reason);
      successfulDates.push(date);
    } catch (error) {
      failedDates.push({ date, message: error.message || 'Request failed.' });
    }
  }
  return { successfulDates, failedDates };
}
