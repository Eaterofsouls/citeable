// outcome.js — Citeable Outcome Logger
// Uses auth.js and dom.js for safe rendering.

const API = window.location.origin;

function showToast(msg, type = '') {
 const t = document.getElementById('toast');
 t.textContent = msg;
 t.className = `toast show ${type}`;
 setTimeout(() => { t.className = 'toast'; }, 2800);
}

function authHeaders() {
 return getAuthHeaders();
}

/**
 * UI/UX Audit fix: GET /api/v1/outcomes returns raw claims rows, which don't
 * include metric_before/metric_after as separate fields — they're only
 * embedded in the free-text statement, e.g.:
 * "...Extracted word count changed from '0 words' to '450 words'. Remediation ID: ..."
 * (see OutcomeEntry.to_claim_statement() in areos/auditors/outcome_logger.py —
 * the template is consistent, so this is parseable rather than guesswork).
 *
 * This tries to extract the before/after values and, if both contain a
 * number, compares them. Returns null if the statement doesn't match the
 * expected shape or neither value is numeric — callers should fall back to
 * a neutral "changed" label rather than guessing.
 */
function parseOutcomeDelta(statement) {
 if (!statement) return null;
 const match = statement.match(/changed from '(.+?)' to '(.+?)'\./);
 if (!match) return null;

 const [, before, after] = match;
 const numBefore = parseFloat((before.match(/-?\d+(\.\d+)?/) || [])[0]);
 const numAfter = parseFloat((after.match(/-?\d+(\.\d+)?/) || [])[0]);

 if (Number.isNaN(numBefore) || Number.isNaN(numAfter)) {
 return { label: `${before} → ${after}`, direction: 'changed' };
 }
 if (numAfter > numBefore) return { label: `${before} → ${after}`, direction: 'improved' };
 if (numAfter < numBefore) return { label: `${before} → ${after}`, direction: 'regressed' };
 return { label: `${before} → ${after}`, direction: 'changed' };
}

async function loadRuns() {
 try {
 const res = await AreosAPI.fetch(`${API}/api/v1/audit/runs`);
 const data = await res.json();
 const sel = document.getElementById('f-run');
 if (!data.runs || data.runs.length === 0) {
 sel.innerHTML = '<option value="">No audit runs available</option>';
 return;
 }
 sel.innerHTML = data.runs.map(r =>
 `<option value="${escapeHtml(r.run_id)}">[${escapeHtml(r.run_date)}] ${escapeHtml(r.target_domain)} — ${escapeHtml(r.run_id)}</option>`
 ).join('');
 } catch (e) {
 document.getElementById('f-run').innerHTML = '<option value="">API offline</option>';
 }
}

async function loadRecentOutcomes() {
 const list = document.getElementById('outcomes-list');
 try {
 const res = await AreosAPI.fetch(`${API}/api/v1/outcomes`);
 if (!res.ok) throw new Error('API error');
 const data = await res.json();

 if (!data.outcomes || data.outcomes.length === 0) {
 list.innerHTML = '';
 list.appendChild(el('div', 'No outcomes logged yet.', {style: {color: '#64748b', fontSize: '13px'}}));
 return;
 }

 list.innerHTML = '';
 data.outcomes.slice(0, 10).forEach(c => {
 const card = document.createElement('div');
 card.className = 'outcome-card';

 const headerRow = document.createElement('div');
 headerRow.style.cssText = 'display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:8px;';
 headerRow.appendChild(el('div', c.claim_id, {className: 'outcome-id'}));

 const badgeGroup = document.createElement('div');
 badgeGroup.style.cssText = 'display:flex; gap:6px; align-items:center;';
 const delta = parseOutcomeDelta(c.statement);
 if (delta) {
 badgeGroup.appendChild(el('div', delta.label, {className: `outcome-delta outcome-delta-${delta.direction}`}));
 }
 badgeGroup.appendChild(el('div', c.status, {className: 'outcome-badge'}));
 headerRow.appendChild(badgeGroup);

 const stmtDiv = el('div', c.statement, {className: 'outcome-statement'});

 const metaDiv = document.createElement('div');
 metaDiv.className = 'outcome-meta';
 metaDiv.appendChild(el('span', `Tier: ${c.source_tier_value || 'N/A'}`));
 metaDiv.appendChild(el('span', `Stage: ${c.stage_id || 'N/A'}`));

 card.appendChild(headerRow);
 card.appendChild(stmtDiv);
 card.appendChild(metaDiv);
 list.appendChild(card);
 });
 } catch (e) {
 list.innerHTML = '';
 list.appendChild(el('div', `Failed to load outcomes: ${e.message}`, {style: {color: '#f87171', fontSize: '13px'}}));
 }
}

async function submitOutcome(e) {
 e.preventDefault();
 const btn = document.getElementById('submit-btn');
 btn.disabled = true;
 btn.textContent = 'Logging...';

 const runId = document.getElementById('f-run').value;
 const payload = {
 remediation_id: document.getElementById('f-remediation').value,
 fix_description: document.getElementById('f-fix').value,
 metric_name: document.getElementById('f-metric').value,
 metric_before: document.getElementById('f-before').value,
 metric_after: document.getElementById('f-after').value,
 page_url: document.getElementById('f-url').value,
 notes: document.getElementById('f-notes').value,
 };

 try {
 const res = await AreosAPI.fetch(`${API}/api/v1/audit/runs/${runId}/outcomes`, {
 method: 'POST',
 headers: authHeaders(),
 body: JSON.stringify(payload)
 });

 if (!res.ok) {
 const err = await res.json();
 throw new Error(err.detail || 'API error');
 }

 const data = await res.json();
 showToast(`Success! Outcome logged as ${data.claim_id}`, 'success');

 ['f-remediation','f-fix','f-metric','f-before','f-after','f-url','f-notes'].forEach(id => {
 document.getElementById(id).value = '';
 });

 loadRecentOutcomes();
 } catch (err) {
 showToast(`Error: ${err.message}`, 'error');
 } finally {
 btn.disabled = false;
 btn.textContent = 'Log Outcome as New Claim';
 }
}

loadRuns();
loadRecentOutcomes();

// FIX (Remaining Work — Outcome Logger): removed ~30 lines of dead code here
// that referenced document.getElementById('remed-id') (no such element exists
// — the actual field is #f-remediation, a plain text input, not a select)
// and an undeclared `runSelect` variable. It threw an uncaught TypeError on
// every page load (Cannot read properties of null (reading 'parentNode'))
// and never successfully wired anything — the remediation-step-suggestions
// feature it was attempting was never functional. If you want that feature
// (auto-suggesting remediation IDs from the selected run's findings), it
// needs to be rebuilt against the real #f-remediation field and the actual
// #f-run select's change event, not reintroduced as-is.
