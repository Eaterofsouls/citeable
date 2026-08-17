// auth.js — Shared authentication module for Citeable UI
// Uses sessionStorage for API admin tokens and localStorage for ephemeral BYOK headers.
// All UI pages MUST import this and use getAuthHeaders() for authenticated requests.

const AUTH_KEY = 'areos_api_token';
const BYOK_VAULT_KEY = 'areos_byok_vault';

// On load: if sessionStorage is empty but localStorage has a token
// (e.g. set by automated tooling before a page.reload()), seed it over.
(function seedTokenFromLocalStorage() {
 if (!sessionStorage.getItem(AUTH_KEY)) {
  const lsToken = localStorage.getItem(AUTH_KEY);
  if (lsToken) sessionStorage.setItem(AUTH_KEY, lsToken);
 }
})();

/**
 * Get the current API token — sessionStorage primary, localStorage fallback.
 * Falls back to an empty string to trigger 401 on missing credentials.
 */
function getToken() {
 return sessionStorage.getItem(AUTH_KEY) || localStorage.getItem(AUTH_KEY) || '';
}


/**
 * Set the API token in sessionStorage.
 */
function setToken(token) {
 sessionStorage.setItem(AUTH_KEY, token);
}

/**
 * Clear the stored token.
 */
function clearToken() {
 sessionStorage.removeItem(AUTH_KEY);
}

/**
 * Helper to securely pull active BYOK credentials from browser local vault
 * and format them into standard HTTP request headers (X-API-Key-<provider>).
 */
function getByokHeaders() {
 const headers = {};
 try {
 const vaultData = localStorage.getItem(BYOK_VAULT_KEY);
 if (vaultData) {
 const parsed = JSON.parse(vaultData);
 Object.entries(parsed).forEach(([provider, data]) => {
 if (data && data.key && (data.status === 'live' || data.status === 'verifying' || data.status === 'unverified')) {
 headers[`X-API-Key-${provider}`] = data.key.trim();
 }
 });
 }
 } catch (e) {
 console.warn("Failed to read BYOK credentials from local storage:", e);
 }
 return headers;
}

/**
 * Returns headers object with Authorization, Content-Type, and all active BYOK API keys.
 */
function getAuthHeaders() {
 return Object.assign({
 'Content-Type': 'application/json',
 'Authorization': `Bearer ${getToken()}`,
 }, getByokHeaders());
}

/**
 * Returns just Authorization and BYOK headers for GET requests that need auth without Content-Type.
 */
function getAuthHeader() {
 return Object.assign({
 'Authorization': `Bearer ${getToken()}`,
 }, getByokHeaders());
}
