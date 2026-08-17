// approvals.js — Citeable Approvals Queue
// Uses auth.js for API token and dom.js for safe rendering.

const API_BASE = window.location.origin + '/api/v1';

const pendingList = document.getElementById('pending-list');
const diffView = document.getElementById('diff-view');
const pendingCountSpan = document.getElementById('pending-count');
const passwordModal = document.getElementById('password-modal');
// const passwordInput = document.getElementById('admin-password');
const btnSubmitPassword = document.getElementById('btn-submit-password');
const btnCancelPassword = document.getElementById('btn-cancel-password');

let pendingItems = [];
let selectedItem = null;
let pendingAction = null;

// FIX (Remaining Work — Approvals): these three were referenced throughout
// this file (selectedCandidates.clear()/.has()/.add()/.delete(), isBulkMode,
// updateBulkUI()) but never declared anywhere, so fetchPendingApprovals()
// threw a ReferenceError the moment it succeeded — this is what actually
// produced the "Error loading queue." state, not a network/auth failure.
// The Select All / bulk approve / bulk reject buttons also had no click
// handlers at all. Both are fixed below.
let selectedCandidates = new Set();
let isBulkMode = false;

const selectAllCb = document.getElementById('select-all-cb');
const btnBulkApprove = document.getElementById('btn-bulk-approve');
const btnBulkReject = document.getElementById('btn-bulk-reject');
const bulkCountSpan = document.getElementById('bulk-count');

function updateBulkUI() {
 const count = selectedCandidates.size;
 if (bulkCountSpan) bulkCountSpan.textContent = String(count);
 if (btnBulkApprove) btnBulkApprove.disabled = count === 0;
 if (btnBulkReject) btnBulkReject.disabled = count === 0;
 if (selectAllCb) {
 selectAllCb.checked = pendingItems.length > 0 && count === pendingItems.length;
 selectAllCb.indeterminate = count > 0 && count < pendingItems.length;
 }
}

if (selectAllCb) {
 selectAllCb.addEventListener('change', (e) => {
 if (e.target.checked) {
 pendingItems.forEach(item => selectedCandidates.add(item.candidate_id));
 } else {
 selectedCandidates.clear();
 }
 updateBulkUI();
 renderPendingList();
 });
}

if (btnBulkApprove) {
 btnBulkApprove.addEventListener('click', () => {
 isBulkMode = true;
 promptPassword('approve');
 });
}

if (btnBulkReject) {
 btnBulkReject.addEventListener('click', () => {
 isBulkMode = true;
 promptPassword('reject');
 });
}

async function fetchPendingApprovals() {
 pendingList.innerHTML = `<div class="loader-container"><div class="spinner"></div></div>`;

 try {
 const response = await AreosAPI.fetch(`${API_BASE}/approvals`);
 if (!response.ok) throw new Error("Failed to fetch");

 const data = await response.json();
 pendingItems = data.pending || [];
 selectedCandidates.clear();
 if(typeof updateBulkUI === "function") updateBulkUI();
 renderPendingList();
 } catch (err) {
 pendingList.innerHTML = '';
 pendingList.appendChild(el('div', 'Error loading queue.', {className: 'no-results', style: {color: 'var(--status-deprecated)'}}));
 pendingCountSpan.textContent = "Error";
 }
}

function renderPendingList() {
 pendingCountSpan.textContent = `${pendingItems.length} PENDING`;
 pendingList.innerHTML = '';

 if (pendingItems.length === 0) {
 pendingList.innerHTML = `
 <div style="background:#141414; border:1px solid #555; border-radius:8px; padding:40px; text-align:center; box-shadow:0 6px 25px rgba(0,0,0,0.7);">
 <div style="font-size:2rem; margin-bottom:12px;">[OK]</div>
 <h4 style="font-size:1.2rem; font-weight:800; color:#FFFFFF; text-transform:uppercase; margin-bottom:8px;">All Clear</h4>
 <p style="color:#AAAAAA; font-size:0.95rem; margin:0;">Zero pending candidate claims in queue for this run.</p>
 </div>
 `;
 diffView.innerHTML = `
 <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; height:100%; margin: 140px auto; max-width:500px;">
 <h3 style="font-size:1.5rem; font-weight:900; color:#FFFFFF; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:12px;">[OK] ALL CLAIMS VERIFIED</h3>
 <p style="font-size:1.05rem; color:#AAAAAAAA; line-height:1.6;">Every audited assertion in this test suite has been reviewed and recorded to persistent database truth.</p>
 </div>
 `;
 return;
 }

 pendingItems.forEach(item => {
 const card = document.createElement('div');
 card.className = `approval-card-mad ${selectedItem && selectedItem.candidate_id === item.candidate_id ? 'selected' : ''}`;

 const cls = (item.classification || 'unknown').toLowerCase();
 let badgeStyle = 'background:#222; color:#FFF; border:1px solid #AAA;';
 if (cls === 'novel') badgeStyle = 'background:rgba(255,255,255,0.15); color:#FFFFFF; border:1px solid #FFFFFF; box-shadow:0 0 10px rgba(255,255,255,0.2);';
 if (cls === 'corroborating') badgeStyle = 'background:#1C2E20; color:#86EFAC; border:1px solid #22C55E;';
 if (cls === 'contradicting') badgeStyle = 'background:#321515; color:#FCA5A5; border:1px solid #EF4444;';

 const headerDiv = document.createElement('div');
 headerDiv.style.cssText = 'display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;';

 const leftHeader = document.createElement('div');
 leftHeader.style.cssText = 'display:flex; align-items:center; gap:12px;';

 const cb = el('input', '', {type: 'checkbox', className: 'bulk-cb'});
 cb.dataset.id = item.candidate_id;
 cb.dataset.run = item.run_id;
 cb.checked = selectedCandidates.has(item.candidate_id);
 cb.style.cssText = 'width:20px; height:20px; accent-color:#FFF; cursor:pointer; margin:0;';
 cb.onclick = (e) => e.stopPropagation();
 cb.onchange = (e) => {
 if (e.target.checked) selectedCandidates.add(item.candidate_id);
 else selectedCandidates.delete(item.candidate_id);
 if (typeof updateBulkUI === "function") updateBulkUI();
 };
 leftHeader.appendChild(cb);

 const idStrong = el('strong', item.candidate_id, {style: {fontFamily: 'var(--font-mono)', fontSize: '1.0rem', color: '#FFFFFF', fontWeight: '800', letterSpacing: '0.04em'}});
 leftHeader.appendChild(idStrong);

 const badge = el('span', (item.classification || 'CLAIM').toUpperCase(), {
 style: `font-size:0.72rem; font-weight:900; padding:5px 12px; border-radius:4px; text-transform:uppercase; letter-spacing:0.12em; ${badgeStyle}`
 });

 headerDiv.appendChild(leftHeader);
 headerDiv.appendChild(badge);

 const summaryDiv = document.createElement('div');
 summaryDiv.style.cssText = 'font-size:0.98rem; color:#DDDDDD; line-height:1.55; font-weight:400; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; text-overflow:ellipsis; margin-top:8px;';
 const summaryText = item.claim_data ? item.claim_data.statement : (item.candidate_statement || item.target_claim_id || item.action);
 // FIX (Readiness Audit, Blocker 5): summaryText is LLM-derived content sourced
 // from audited (potentially adversarial) third-party sites. It was previously
 // interpolated straight into innerHTML, so a prompt-injection payload in that
 // content could execute script in the operator's session (which also holds the
 // admin token in sessionStorage and BYOK provider keys in localStorage -- see
 // auth.js). Build the DOM with createElement/textContent instead, exactly like
 // the equivalent claim-statement rendering in app.js.
 const actionTag = document.createElement('span');
 actionTag.style.cssText = 'color:#FFFFFF; font-weight:800; font-family:var(--font-mono); margin-right:6px;';
 actionTag.textContent = `[${item.action || 'MODIFY'}]`;
 summaryDiv.appendChild(actionTag);
 summaryDiv.appendChild(document.createTextNode(' ' + (summaryText || '')));

 card.appendChild(headerDiv);
 card.appendChild(summaryDiv);

 card.addEventListener('click', () => {
 selectedItem = item;
 renderPendingList();
 renderDiffView();
 });

 pendingList.appendChild(card);
 });
}

function renderDiffView() {
 if (!selectedItem) return;

 const item = selectedItem;
 diffView.innerHTML = '';
 diffView.className = 'diff-console-mad';

 const topSection = document.createElement('div');

 // Header
 const headerDiv = document.createElement('div');
 headerDiv.className = 'diff-header-mad';

 const leftDiv = document.createElement('div');
 const candLabel = el('div', 'CLAIM CANDIDATE ID', {style: {color: '#AAAAAA', fontSize: '0.8rem', fontWeight: '800', letterSpacing: '0.15em', textTransform: 'uppercase'}});
 const candId = el('h3', item.candidate_id, {style: {fontSize: '2.0rem', fontWeight: '900', color: '#FFFFFF', marginTop: '6px', marginBottom: '0', fontFamily: 'var(--font-mono)', textShadow: '0 0 20px rgba(255,255,255,0.2)'}});
 leftDiv.appendChild(candLabel);
 leftDiv.appendChild(candId);

 const rightDiv = document.createElement('div');
 rightDiv.style.textAlign = 'right';
 const actLabel = el('div', 'PROPOSED MUTATION ACTION', {style: {color: '#AAAAAA', fontSize: '0.8rem', fontWeight: '800', letterSpacing: '0.15em', textTransform: 'uppercase'}});
 const actVal = el('h3', item.action || 'INSERT', {style: {fontSize: '1.6rem', fontWeight: '900', marginTop: '6px', marginBottom: '0', color: '#FFFFFF', fontFamily: 'var(--font-mono)'}});
 rightDiv.appendChild(actLabel);
 rightDiv.appendChild(actVal);

 headerDiv.appendChild(leftDiv);
 headerDiv.appendChild(rightDiv);
 topSection.appendChild(headerDiv);

 // Content
 const contentDiv = document.createElement('div');
 contentDiv.style.cssText = 'display:flex; flex-direction:column; gap:28px;';

 if (item.classification === 'novel' && item.claim_data) {
 const data = item.claim_data;
 
 const stmtBox = document.createElement('div');
 stmtBox.appendChild(el('div', 'PROPOSED ASSERTION STATEMENT', {style: {fontSize: '0.78rem', color: '#AAAAAA', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
 const stmtVal = el('div', data.statement || 'No statement text provided.', {style: {fontSize: '1.25rem', color: '#FFFFFF', fontWeight: '600', lineHeight: '1.6', background: '#181818', border: '1px solid #555555', padding: '24px', borderRadius: '8px', boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.6)'}});
 stmtBox.appendChild(stmtVal);
 contentDiv.appendChild(stmtBox);

 const grid = document.createElement('div');
 grid.style.cssText = 'display:grid; grid-template-columns:repeat(3, 1fr); gap:18px;';

 const fields = [
 ['Assertion Type', data.claim_type || 'N/A'],
 ['Evaluation Scope', data.claim_scope || 'N/A'],
 ['Source Tier Authority', data.source_tier_value || 'Tier-1 Audit']
 ];
 fields.forEach(([label, value]) => {
 const cell = document.createElement('div');
 cell.style.cssText = 'background:#181818; border:1px solid #444444; padding:18px; border-radius:6px;';
 cell.appendChild(el('div', label, {style: {color: '#AAAAAA', fontSize: '0.75rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '6px'}}));
 cell.appendChild(el('div', value, {style: {color: '#FFFFFF', fontSize: '1.15rem', fontWeight: '800', fontFamily: 'var(--font-mono)'}}));
 grid.appendChild(cell);
 });
 contentDiv.appendChild(grid);

 if (data.source_url) {
 const urlBox = document.createElement('div');
 urlBox.style.cssText = 'background:#161616; border:1px solid #444444; padding:16px 20px; border-radius:6px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px;';
 // Blocker 3 fix: safeUrl() only strips javascript:/data: schemes — it
 // does not flag `internal://` (currently claims C93/C94) as non-web, so
 // without this check it still rendered as a normal clickable link and
 // "Open Source" button pointing at a scheme the browser can't fetch.
 // Same isWebUrl pattern as remediation.js's renderModalSource() and
 // app.js's openDrawer().
 const isWebUrl = /^https?:\/\//i.test(data.source_url);
 if (isWebUrl) {
    urlBox.innerHTML = `
    <div>
    <span style="color:#AAAAAA; font-size:0.75rem; font-weight:800; text-transform:uppercase; letter-spacing:0.1em; display:block; margin-bottom:4px;">External Audit Verification Citation</span>
    <a href="${safeUrl(data.source_url)}" target="_blank" style="color:#FFFFFF; font-weight:700; text-decoration:underline; font-family:var(--font-mono); font-size:0.95rem; word-break:break-all;" class="safe-url-display"></a>
    </div>
    <a href="${safeUrl(data.source_url)}" target="_blank" style="background:#262626; border:1px solid #FFF; color:#FFF; padding:6px 14px; border-radius:4px; font-size:0.8rem; font-weight:800; text-transform:uppercase; letter-spacing:0.1em; text-decoration:none;">↗ Open Source</a>
    `;
    urlBox.querySelector('.safe-url-display').textContent = data.source_url;
  } else {
    urlBox.innerHTML = `
    <div>
    <span style="color:#AAAAAA; font-size:0.75rem; font-weight:800; text-transform:uppercase; letter-spacing:0.1em; display:block; margin-bottom:4px;">External Audit Verification Citation</span>
    <span style="color:#FFFFFF; font-weight:700; font-family:var(--font-mono); font-size:0.95rem; word-break:break-all;" class="safe-url-display"></span>
    </div>
    `;
    urlBox.querySelector('.safe-url-display').textContent = data.source_url + ' (internal reference — not externally viewable)';
  }
 contentDiv.appendChild(urlBox);
 }
 } else if (item.classification === 'corroborating') {
 const targetBox = document.createElement('div');
 targetBox.appendChild(el('div', 'TARGET CLAIM IDENTifier', {style: {fontSize: '0.78rem', color: '#AAAAAA', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
 targetBox.appendChild(el('div', item.target_claim_id || 'UNKNOWN', {style: {fontSize: '1.4rem', fontWeight: '900', fontFamily: 'var(--font-mono)', color: '#FFFFFF', background: '#181818', border: '1px solid #555555', padding: '16px 20px', borderRadius: '6px'}}));
 contentDiv.appendChild(targetBox);

 const diffBox = document.createElement('div');
 diffBox.appendChild(el('div', 'PROPOSED DATABASE MUTATION PAYLOAD', {style: {fontSize: '0.78rem', color: '#AAAAAA', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
 const pre = document.createElement('pre');
 pre.style.cssText = 'background:#0D0D0D; border:1px solid #555555; padding:22px; border-radius:8px; overflow-x:auto; font-family:var(--font-mono); font-size:0.95rem; color:#86EFAC; line-height:1.5; box-shadow:inset 0 2px 12px rgba(0,0,0,0.8);';
 pre.textContent = JSON.stringify(item.changes, null, 2);
 diffBox.appendChild(pre);
 contentDiv.appendChild(diffBox);
 } else {
 // Contradicting or custom
 if (item.target_claim_id) {
 const targetBox = document.createElement('div');
 targetBox.appendChild(el('div', 'CONTESTED CLAIM IDENTIFIER', {style: {fontSize: '0.78rem', color: '#AAAAAA', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
 targetBox.appendChild(el('div', item.target_claim_id, {style: {fontSize: '1.4rem', fontWeight: '900', fontFamily: 'var(--font-mono)', color: '#FCA5A5', background: '#1F1010', border: '1px solid #EF4444', padding: '16px 20px', borderRadius: '6px'}}));
 contentDiv.appendChild(targetBox);
 }

 if (item.candidate_statement) {
 const stmtBox = document.createElement('div');
 stmtBox.appendChild(el('div', 'CONTRADICTING ASSERTION STATEMENT', {style: {fontSize: '0.78rem', color: '#AAAAAA', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
 stmtBox.appendChild(el('div', item.candidate_statement, {style: {fontSize: '1.25rem', color: '#FFFFFF', fontWeight: '700', lineHeight: '1.6', background: '#181818', border: '1px solid #555555', padding: '24px', borderRadius: '8px'}}));
 contentDiv.appendChild(stmtBox);
 }

 if (item.rationale) {
 const ratBox = document.createElement('div');
 ratBox.appendChild(el('div', 'AUDIT RATIONALE & ANALYSIS', {style: {fontSize: '0.78rem', color: '#AAAAAA', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
 ratBox.appendChild(el('div', item.rationale, {style: {fontSize: '1.05rem', color: '#DDDDDD', lineHeight: '1.7', background: '#161616', border: '1px solid #444444', padding: '20px', borderRadius: '6px'}}));
 contentDiv.appendChild(ratBox);
 }

 if (item.adversarial_critique) {
 const critBox = document.createElement('div');
 critBox.style.cssText = 'background:#1A1414; border:1px solid #F87171; padding:22px; border-radius:8px; box-shadow:0 0 20px rgba(248,113,113,0.15);';
 critBox.appendChild(el('div', '[WARN] ADVERSARIAL AI RED-TEAM CRITIQUE', {style: {fontSize: '0.85rem', fontWeight: '900', color: '#F87171', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '10px'}}));
 critBox.appendChild(el('div', item.adversarial_critique, {style: {whiteSpace: 'pre-wrap', fontSize: '1.0rem', color: '#FFFFFF', lineHeight: '1.65'}}));
 contentDiv.appendChild(critBox);
 }
 }

 topSection.appendChild(contentDiv);
 diffView.appendChild(topSection);

 // Bottom Action Footer
 const actionsDiv = document.createElement('div');
 actionsDiv.className = 'diff-actions-mad';
 
 const btnApprove = document.createElement('button');
 btnApprove.className = 'btn-mad-approve';
 btnApprove.innerHTML = ' Approve Mutation & Commit';
 btnApprove.onclick = () => promptPassword('approve');

 const btnReject = document.createElement('button');
 btnReject.className = 'btn-mad-reject';
 btnReject.innerHTML = '[FAIL] Reject & Quarantine';
 btnReject.onclick = () => promptPassword('reject');

 actionsDiv.appendChild(btnApprove);
 actionsDiv.appendChild(btnReject);
 diffView.appendChild(actionsDiv);
}

// Password Modal Flow
const confirmDialog = makeDialogAccessible(passwordModal, {
 titleId: 'modal-title',
 onClose: () => {
 passwordModal.classList.remove('active');
 pendingAction = null;
 confirmDialog.close();
 },
});

window.promptPassword = function(action) {
 pendingAction = action;

 document.getElementById('modal-title').textContent = action === 'approve' ? 'Approve Change' : 'Reject Change';

 // FIX (Remaining Work — Approvals): the confirm dialog used to say the same
 // generic "Are you sure you want to proceed?" for every action — a single
 // approve and a 12-item bulk approve looked identical. Say what's actually
 // about to happen, since this is the one screen where a misclick has real
 // consequences (claims are never hard-deleted per the audit-trail design,
 // so a bad approval has to be manually superseded later, not just undone).
 const modalDesc = document.getElementById('modal-desc');
 if (isBulkMode) {
 const n = selectedCandidates.size;
 modalDesc.textContent = `${action === 'approve' ? 'Approve' : 'Reject'} ${n} selected candidate${n === 1 ? '' : 's'}? This cannot be undone from this screen.`;
 } else if (selectedItem) {
 modalDesc.textContent = `${action === 'approve' ? 'Approve' : 'Reject'} candidate ${selectedItem.candidate_id}? This cannot be undone from this screen.`;
 } else {
 modalDesc.textContent = 'Are you sure you want to proceed?';
 }

 // Add a text area for rejection reason if rejecting
 let reasonEl = document.getElementById('rejection-reason');
 if (!reasonEl) {
 reasonEl = document.createElement('textarea');
 reasonEl.id = 'rejection-reason';
 reasonEl.placeholder = 'Rejection reason (optional)';
 reasonEl.style.cssText = 'width:100%; margin-top:10px; padding:10px; border-radius:6px; border:1px solid var(--border); background:var(--bg); color:var(--text);';
 document.getElementById('modal-desc').parentNode.insertBefore(reasonEl, document.getElementById('modal-desc').nextSibling);
 }
 reasonEl.style.display = action === 'reject' ? 'block' : 'none';
 reasonEl.value = '';

 passwordModal.classList.add('active');
 confirmDialog.open();
 if (action === 'reject') reasonEl.focus();
};

btnCancelPassword.addEventListener('click', () => {
 passwordModal.classList.remove('active');
 pendingAction = null;
 isBulkMode = false;
 confirmDialog.close();
});

btnSubmitPassword.addEventListener('click', async () => {
 const action = pendingAction;
 const reasonEl = document.getElementById('rejection-reason');
 const rejection_reason = (action === 'reject' && reasonEl) ? reasonEl.value : null;

 passwordModal.classList.remove('active');
 confirmDialog.close();
 diffView.innerHTML = `<div class="loader-container"><div class="spinner"></div></div>`;

 const itemsToProcess = isBulkMode 
 ? pendingItems.filter(p => selectedCandidates.has(p.candidate_id)) 
 : (selectedItem ? [selectedItem] : []);

 if (itemsToProcess.length === 0) return;

 try {
 const promises = itemsToProcess.map(item => {
 // Include Idempotency-Key header for bulk safety
 return AreosAPI.fetch(`${API_BASE}/approvals/${item.run_id}/${item.candidate_id}`, {
 method: 'POST',
 headers: {
 ...getAuthHeaders(),
 'Idempotency-Key': `bulk_${item.candidate_id}_${action}_${Date.now()}`
 },
 body: JSON.stringify({ action, rejection_reason })
 }).then(() => item.candidate_id);
 });

 const results = await Promise.allSettled(promises);
 const successes = results.filter(r => r.status === 'fulfilled').map(r => r.value);
 const failures = results.filter(r => r.status === 'rejected');

 if (successes.length > 0) {
 AreosAPI.notify(`${action === 'approve' ? 'Approved' : 'Rejected'} ${successes.length} candidates.`, 'success');
 pendingItems = pendingItems.filter(p => !successes.includes(p.candidate_id));
 successes.forEach(id => selectedCandidates.delete(id));
 }
 
 if (failures.length > 0) {
 AreosAPI.notify(`Failed to process ${failures.length} candidates.`, 'error');
 }

 selectedItem = null;
 if (typeof updateBulkUI === "function") updateBulkUI();
 renderPendingList();
 
 if (pendingItems.length > 0) {
 selectedItem = pendingItems[0];
 renderDiffView();
 renderPendingList();
 } else {
 diffView.innerHTML = '';
 }
 } catch (err) {
 AreosAPI.notify(err.message, 'error');
 renderDiffView();
 }
 isBulkMode = false;
});

// Init
fetchPendingApprovals();
