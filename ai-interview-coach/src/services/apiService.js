import { beginActivity } from "./activityService";

const API_BASE = (import.meta.env.VITE_API_URL || "/api/v1").replace(/\/$/, "");
const KEY = "console_auth_v1";
let tokens = null;
try { tokens = JSON.parse(sessionStorage.getItem(KEY)); } catch { /* tab storage unavailable */ }
let version = 0;
let refreshing = null;

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

export function hasSession() { return Boolean(tokens?.refresh_token); }

function storeTokens(value) {
  tokens = value;
  version++;
  try {
    if (value) sessionStorage.setItem(KEY, JSON.stringify(value));
    else sessionStorage.removeItem(KEY);
  } catch { /* keep this login in memory if tab storage is unavailable */ }
}

export function clearAuth() {
  storeTokens(null);
  window.dispatchEvent(new Event("console-auth-expired"));
}

async function send(path, options = {}, accessToken) {
  const finish = beginActivity();
  try { return await sendRequest(path, options, accessToken); }
  finally { finish(); }
}

async function sendRequest(path, options = {}, accessToken) {
  let response;
  const multipart = options.body instanceof FormData;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: options.method || "GET",
      headers: {
        ...(options.body !== undefined && !multipart ? { "Content-Type": "application/json" } : {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: multipart ? options.body : options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: AbortSignal.timeout(120000),
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Cannot reach the server. It may be starting up; wait a moment and retry.", 0);
  }
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const fields = data?.error?.fields?.map(f => `${f.location.at(-1)}: ${f.message}`).join("; ");
    const unavailable = [502, 503, 504].includes(response.status) ? "The server is starting up or temporarily unavailable. Wait a moment and retry." : null;
    throw new ApiError(fields || data?.error?.message || unavailable || `Request failed (${response.status})`, response.status);
  }
  if (response.status !== 204 && data === null) throw new ApiError("The server returned an invalid response. Check the API URL.", 502);
  return data;
}

async function refresh() {
  if (!refreshing) {
    const currentVersion = version;
    const refreshToken = tokens?.refresh_token;
    refreshing = (async () => {
      if (!refreshToken) throw new ApiError("Please sign in to continue.", 401);
      try {
        const next = await send("/auth/refresh", { method: "POST", body: { refresh_token: refreshToken } });
        if (currentVersion !== version) throw new ApiError("Your session changed. Please sign in again.", 401);
        storeTokens(next);
      } catch (error) {
        if (error.status === 401 && currentVersion === version) clearAuth();
        throw error;
      }
    })().finally(() => { refreshing = null; });
  }
  return refreshing;
}

export async function api(path, options = {}) {
  const usedToken = tokens?.access_token;
  try { return await send(path, options, usedToken); }
  catch (error) {
    if (error.status !== 401) throw error;
    if (!tokens?.refresh_token) { clearAuth(); throw error; }
    if (tokens.access_token === usedToken) await refresh();
    try { return await send(path, options, tokens?.access_token); }
    catch (retryError) { if (retryError.status === 401) clearAuth(); throw retryError; }
  }
}

export async function authenticate(mode, credentials) {
  const next = await send(`/auth/${mode}`, { method: "POST", body: credentials });
  storeTokens(next);
  return api("/users/me");
}

export async function logout() {
  const refreshToken = tokens?.refresh_token;
  if (refreshToken) await send("/auth/logout", { method: "POST", body: { refresh_token: refreshToken } });
  clearAuth();
}
