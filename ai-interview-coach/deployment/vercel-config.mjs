export function createVercelConfig(apiUrl) {
  let url;
  try { url = new URL(apiUrl); } catch { throw new Error('Set VITE_API_URL to https://YOUR-API-HOST/api/v1 in Vercel before deploying.'); }
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash ||
      url.pathname.replace(/\/$/, '') !== '/api/v1' || !/^[a-z0-9.-]+$/i.test(url.hostname)) {
    throw new Error('VITE_API_URL must be an HTTPS URL ending in /api/v1, without credentials, query, or fragment.');
  }
  return {
    framework: 'vite', installCommand: 'npm ci', buildCommand: 'npm run build', outputDirectory: 'dist',
    rewrites: [{ source: '/((?!assets/).*)', destination: '/index.html' }],
    headers: [
      { source: '/(.*)', headers: [
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'microphone=(self), camera=(), geolocation=()' },
        { key: 'Content-Security-Policy', value: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self' ${url.origin}; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'` },
      ] },
      { source: '/assets/(.*)', headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }] },
    ],
  };
}
