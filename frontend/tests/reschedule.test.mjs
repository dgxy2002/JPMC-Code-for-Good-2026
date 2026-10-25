import assert from 'node:assert/strict';
import test from 'node:test';

import { planReallocation, submitReallocationPlan } from '../src/data/reschedule.js';

test('plans one request per day and skips days without reallocatable sessions', () => {
  const sessionsByMonth = {
    '2026-10': [
      { id: 'am', date: '2026-10-19', slot: 'AM', therapistId: 'therapist-01', status: 'SCHEDULED' },
      { id: 'pm', date: '2026-10-19', slot: 'PM', therapistId: 'therapist-01', status: 'SCHEDULED' },
      { id: 'other', date: '2026-10-20', slot: 'AM', therapistId: 'other', status: 'SCHEDULED' },
      { id: 'done', date: '2026-10-21', slot: 'AM', therapistId: 'therapist-01', status: 'COMPLETED' },
      { id: 'next', date: '2026-10-22', slot: 'AM', therapistId: 'therapist-01', status: 'REALLOCATED' },
    ],
  };
  const dates = ['2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22'];

  const plan = planReallocation(dates, sessionsByMonth, 'therapist-01');

  assert.deepEqual(plan.targets.map(({ date, session }) => [date, session.id]), [
    ['2026-10-19', 'am'],
    ['2026-10-22', 'next'],
  ]);
  assert.deepEqual(plan.skippedDates, ['2026-10-20', '2026-10-21']);
});

test('submits dates sequentially and reports partial failures', async () => {
  const calls = [];
  const targets = [
    { date: '2026-10-19', session: { id: 'first' } },
    { date: '2026-10-20', session: { id: 'second' } },
    { date: '2026-10-21', session: { id: 'third' } },
  ];
  const send = async (session, therapistId, reason) => {
    calls.push([session.id, therapistId, reason]);
    if (session.id === 'second') throw new Error('Conflict');
  };

  const result = await submitReallocationPlan(targets, 'therapist-01', 'Medical Leave', send);

  assert.deepEqual(calls, [
    ['first', 'therapist-01', 'Medical Leave'],
    ['second', 'therapist-01', 'Medical Leave'],
    ['third', 'therapist-01', 'Medical Leave'],
  ]);
  assert.deepEqual(result.successfulDates, ['2026-10-19', '2026-10-21']);
  assert.deepEqual(result.failedDates, [{ date: '2026-10-20', message: 'Conflict' }]);
});
