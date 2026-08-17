/**
 * context.js
 * App-wide store for current analyst identity, active route, last-used domain, and active run_id.
 * This satisfies the cross-page persistence requirement (MF-29) in Batch B1.
 */

window.AreosContext = {
 _state: {
 analystId: localStorage.getItem("areos_analyst_id") || null,
 activeRoute: window.location.pathname,
 lastDomain: localStorage.getItem("areos_last_domain") || "",
 activeRunId: localStorage.getItem("areos_active_run_id") || null,
 },

 get analystId() { return this._state.analystId; },
 set analystId(val) {
 this._state.analystId = val;
 if (val) localStorage.setItem("areos_analyst_id", val);
 else localStorage.removeItem("areos_analyst_id");
 },

 get lastDomain() { return this._state.lastDomain; },
 set lastDomain(val) {
 this._state.lastDomain = val;
 if (val) localStorage.setItem("areos_last_domain", val);
 else localStorage.removeItem("areos_last_domain");
 },

 get activeRunId() { return this._state.activeRunId; },
 set activeRunId(val) {
 this._state.activeRunId = val;
 if (val) localStorage.setItem("areos_active_run_id", val);
 else localStorage.removeItem("areos_active_run_id");
 }
};
