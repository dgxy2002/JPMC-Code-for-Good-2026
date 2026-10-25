import assert from 'node:assert/strict';
import test from 'node:test';

import { createStudent } from '../src/data/api.js';


test('createStudent posts the backend student contract', async (context) => {
  const originalFetch = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = originalFetch;
  });

  const student = { name: 'Alice Tan', required_seniority: 'JUNIOR' };
  const created = { id: 'student-id', ...student };
  let request;
  globalThis.fetch = async (url, options) => {
    request = { url, options };
    return {
      ok: true,
      status: 201,
      json: async () => created,
    };
  };

  const result = await createStudent(student);

  assert.equal(request.url, 'http://127.0.0.1:8000/students');
  assert.equal(request.options.method, 'POST');
  assert.deepEqual(request.options.headers, { 'Content-Type': 'application/json' });
  assert.deepEqual(JSON.parse(request.options.body), student);
  assert.deepEqual(result, created);
});
