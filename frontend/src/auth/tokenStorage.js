// Access token persistence.
//
// Trade-off (Phase 1): the JWT lives in localStorage so a page refresh keeps the session.
// That is readable by any script on the page, so XSS would expose it; exposure is bounded by
// the short token lifetime (ACCESS_TOKEN_EXPIRE_MINUTES) and server-side deactivation.
// Moving to an httpOnly refresh cookie + in-memory access token is a later hardening step.
const KEY = 'disputeiq.accessToken';

export function getToken() {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    window.localStorage.setItem(KEY, token);
  } catch {
    /* storage unavailable (private mode) — session lasts until reload */
  }
}

export function clearToken() {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
