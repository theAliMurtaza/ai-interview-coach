import test from 'node:test';
import assert from 'node:assert/strict';
import { createVercelConfig } from '../deployment/vercel-config.mjs';

test('Vercel CSP allows the configured API without allowing arbitrary HTTPS hosts', () => {
  const config = createVercelConfig('https://coach-api.onrender.com/api/v1');
  const csp = config.headers[0].headers.find(header => header.key === 'Content-Security-Policy').value;
  assert.match(csp, /connect-src 'self' https:\/\/coach-api\.onrender\.com;/);
  assert.ok(!csp.includes('connect-src https:'));
  assert.equal(config.outputDirectory, 'dist');
});

test('Vercel rejects missing or unsafe API URLs before deploying a broken frontend', () => {
  for (const url of [undefined, '/api/v1', 'http://api.example.com/api/v1', 'https://user:secret@api.example.com/api/v1',
    'https://api.example.com', 'https://api.example.com/api/v1?key=secret', "https://api.example.com';/api/v1"]) {
    assert.throws(() => createVercelConfig(url));
  }
});
