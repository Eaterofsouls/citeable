// app.js — Citeable Claims Explorer
// Uses auth.js for API token and dom.js for safe rendering.

const API_BASE = window.location.origin + '/api/v1';

// DOM Elements
const claimsContainer = document.getElementById('claims-container');
const totalClaimsSpan = document.getElementById('total-claims');
const searchInput = document.getElementById('search-input');
const filterStage = document.getElementById('filter-stage');
const filterStatus = document.getElementById('filter-status');
const filterConfidence = document.getElementById('filter-confidence');
const filterType = document.getElementById('filter-type');
const filterScope = document.getElementById('filter-scope');
const filterPinned = document.getElementById('filter-pinned');
const btnReset = document.getElementById('btn-reset');
const btnAddClaim = document.getElementById('btn-add-claim');

// Modal Elements
const editorModal = document.getElementById('editor-modal');
const editorForm = document.getElementById('editor-form');
const editorTitle = document.getElementById('editor-title');
const btnCancelEditor = document.getElementById('btn-cancel-editor');

// UI/UX Audit fix: accessible dialog wiring (role="dialog", focus trap, Escape, focus-return)
const editorDialog = makeDialogAccessible(editorModal, {
 titleId: 'editor-title',
 onClose: () => { editorModal.classList.remove('active'); editorDialog.close(); },
});
const drawerDialog = makeDialogAccessible(document.getElementById('claim-drawer'), {
 label: 'Claim Details',
 onClose: () => {
 document.getElementById('claim-drawer').style.display = 'none';
 claimsContainer.querySelectorAll('.index-row.focused').forEach(r => r.classList.remove('focused'));
 document.querySelector('.claims-layout')?.classList.remove('drawer-open');
 drawerDialog.close();
 },
});

// State
let offset = 0;
const LIMIT = 50;
let currentClaims = [];
let totalCount = 0;
let currentAbortController = null;
const expandedClaims = new Set();
let focusedIndex = -1;

const analystId = window.AreosContext?.analystId || 'unknown';
const storageKeyPins = `areos_pins_${analystId}`;
const storageKeyFilters = `areos_filters_${analystId}`;

let pinnedClaims = new Set(JSON.parse(localStorage.getItem(storageKeyPins) || '[]'));

// Icons
const iconFolder = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>`;
const iconTier = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>`;
const iconWarning = `<svg viewBox="0 0 24 24" fill="none" stroke="var(--status-contested)" stroke-width="2" width="16"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
const iconPin = `<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" width="16"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>`; // actually let's use a simpler pin
const iconPinUnfilled = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>`;

function loadSavedFilters() {
 try {
 const saved = JSON.parse(localStorage.getItem(storageKeyFilters));
 if (saved) {
 if(saved.search) searchInput.value = saved.search;
 if(saved.stage) filterStage.value = saved.stage;
 if(saved.status) filterStatus.value = saved.status;
 if(saved.confidence) filterConfidence.value = saved.confidence;
 if(saved.type) filterType.value = saved.type;
 if(saved.pinned) filterPinned.checked = saved.pinned;
 }
 } catch(e) {}
}

function saveFilters() {
 const filters = {
 search: searchInput.value,
 stage: filterStage.value,
 status: filterStatus.value,
 confidence: filterConfidence.value,
 type: filterType.value,
 scope: filterScope ? filterScope.value : '',
 pinned: filterPinned.checked
 };
 localStorage.setItem(storageKeyFilters, JSON.stringify(filters));
}

function togglePin(claimId, btn) {
 if (pinnedClaims.has(claimId)) {
 pinnedClaims.delete(claimId);
 btn.innerHTML = iconPinUnfilled;
 btn.classList.remove('pinned');
 } else {
 pinnedClaims.add(claimId);
 btn.innerHTML = ''; // simple star for filled pin
 btn.classList.add('pinned');
 }
 localStorage.setItem(storageKeyPins, JSON.stringify(Array.from(pinnedClaims)));
}

async function fetchClaims(isLoadMore = false) {
 if (!isLoadMore) {
 offset = 0;
 currentClaims = [];
 claimsContainer.innerHTML = `<div class="loader-container"><div class="spinner"></div></div>`;
 focusedIndex = -1;
 } else {
 const btn = document.getElementById('btn-load-more');
 if (btn) btn.textContent = 'Loading...';
 }

 if (currentAbortController) currentAbortController.abort();
 currentAbortController = new AbortController();

 saveFilters();

 const params = new URLSearchParams();
 if (searchInput.value) params.append("search_query", searchInput.value);
 if (filterStage.value) params.append("stage_id", filterStage.value);
 if (filterStatus.value && filterStatus.value !== "all") {
 params.append("status", filterStatus.value);
 } else if (!filterStatus.value) {
 params.append("exclude_deprecated", "true");
 }
 if (filterConfidence.value) params.append("confidence", filterConfidence.value);
 if (filterType.value) params.append("claim_type", filterType.value);
 if (filterScope && filterScope.value) params.append("claim_scope", filterScope.value);
 
 params.append("limit", LIMIT);
 params.append("offset", offset);

 try {
 const response = await AreosAPI.fetch(`/claims?${params.toString()}`, {
 signal: currentAbortController.signal
 });

 if (!response.ok) throw new Error("Failed to fetch");

 const data = await response.json();
 totalCount = data.total_count || 0;
 
 let fetchedClaims = data.claims;
 if (filterPinned.checked) {
 fetchedClaims = fetchedClaims.filter(c => pinnedClaims.has(c.claim_id));
 totalCount = pinnedClaims.size; // rough estimate since server doesn't filter pins
 }

 if (!isLoadMore) {
 currentClaims = fetchedClaims;
 claimsContainer.innerHTML = '';
 } else {
 currentClaims = currentClaims.concat(fetchedClaims);
 const btn = document.getElementById('btn-load-more');
 if (btn) btn.remove();
 }
 
 renderClaims(fetchedClaims, isLoadMore);
 } catch (err) {
 if (err.name === 'AbortError') return;
 if (!isLoadMore) claimsContainer.innerHTML = '';
 AreosAPI.notify(`Error loading claims: ${err.message}`, 'error');
 if (totalClaimsSpan) totalClaimsSpan.textContent = "Error";
 }
}

function renderClaims(claimsToAppend, isLoadMore) {
 if (totalClaimsSpan) totalClaimsSpan.textContent = `${totalCount} Claims Found`;

 if (currentClaims.length === 0) {
 claimsContainer.innerHTML = `<div class="no-results">No claims match the selected filters.</div>`;
 return;
 }

 claimsToAppend.forEach((claim, idx) => {
 const row = document.createElement('div');
 row.className = 'index-row';
 row.dataset.id = claim.claim_id;
 const actualIndex = isLoadMore ? (offset + idx) : idx;
 row.dataset.index = actualIndex;

 if (expandedClaims.has(claim.claim_id)) row.classList.add('expanded');

 const typeClass = `type-${(claim.claim_type || 'fact').toLowerCase()}`;
 const isContested = claim.status === 'contested';
 const isPinned = pinnedClaims.has(claim.claim_id);

 row.innerHTML = `
 <div class="index-row-header">
 ${isContested ? `<div class="priority-indicator" title="Contested Claim">${iconWarning}</div>` : ''}
 <div class="badge ${typeClass}" style="flex-shrink:0; margin-top:1px;">${escapeHtml((claim.claim_type || 'FACT').toUpperCase())}</div>
 <div class="row-id" style="flex-shrink:0; font-family: var(--font-mono); font-size: 0.8125rem; color: var(--text-secondary); width: 65px; margin-top:2px;">${escapeHtml(claim.claim_id)}</div>
 <div class="row-statement-preview"></div>
 <button class="btn-pin ${isPinned ? 'pinned' : ''}" style="flex-shrink:0; margin-left:auto; background:none; border:none; cursor:pointer; color:var(--text-secondary); font-size:1.2rem;" aria-label="Pin claim">
 ${isPinned ? '' : iconPinUnfilled}
 </button>
 </div>
 `;

 row.querySelector('.row-statement-preview').textContent = claim.statement;

 const pinBtn = row.querySelector('.btn-pin');
 if (pinBtn) {
  pinBtn.addEventListener('click', (e) => {
   e.stopPropagation();
   togglePin(claim.claim_id, pinBtn);
  });
 }

 // Drawer click
 row.addEventListener('click', (e) => {
 if(e.target.closest('.btn-pin')) return;
 openDrawer(claim);
 updateFocusIndex(actualIndex);
 });

 claimsContainer.appendChild(row);
 });

 if (currentClaims.length < totalCount && !filterPinned.checked) {
 const btnLoadMore = document.createElement('button');
 btnLoadMore.id = 'btn-load-more';
 btnLoadMore.className = 'btn-secondary';
 btnLoadMore.style.cssText = 'width:100%; margin-top:20px; padding:12px;';
 btnLoadMore.textContent = 'Load More';
 btnLoadMore.onclick = () => {
 offset += LIMIT;
 fetchClaims(true);
 };
 claimsContainer.appendChild(btnLoadMore);
 }
}

function updateFocusIndex(idx) {
 focusedIndex = idx;
 claimsContainer.querySelectorAll('.index-row.focused').forEach(r => r.classList.remove('focused'));
 const row = claimsContainer.querySelector(`[data-index="${focusedIndex}"]`);
 if (row) {
 row.classList.add('focused');
 }
}

function openDrawer(claim) {
 const drawer = document.getElementById('claim-drawer');
 const content = document.getElementById('drawer-content');
 if (!drawer || !content) return;
 
 drawer.style.display = 'block';
 drawer.scrollTop = 0;
 document.querySelector('.claims-layout')?.classList.add('drawer-open');
 drawerDialog.open();
 
 const formatStatement = (text) => {
     if (!text) return '';
     const escaped = (typeof escapeHtml === 'function' ? escapeHtml(text) : String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"));
     return escaped
         .replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--text-primary); font-weight:600;">$1</strong>')
         .replace(/\*(.*?)\*/g, '<em>$1</em>')
         .replace(/`(.*?)`/g, '<code style="background:#202020; padding:2px 4px; border-radius:3px; font-family:var(--font-mono); font-size:0.9em;">$1</code>');
 };

 // Blocker 3 fix: safeUrl() only strips javascript:/data: — it does not
 // recognize `internal://` (or any other non-http(s) scheme) as unsafe to
 // present as a normal clickable link, and doesn't tell us that here. An
 // `internal://` source_url (currently claims C93/C94) is a case-study
 // cross-reference, not an externally fetchable URL, so it must never be
 // rendered as a clickable <a> or fed to the iframe preview — both would
 // silently fail or mislead. Same isWebUrl check as remediation.js's
 // renderModalSource().
 const isWebUrl = claim.source_url ? /^https?:\/\//i.test(claim.source_url) : false;

 let html = `
 <div style="display:flex; justify-content:space-between; align-items:center;">
  <div style="display:flex; align-items:center; gap:8px;">
    <div class="badge type-${(claim.claim_type || 'fact').toLowerCase()}">${escapeHtml((claim.claim_type || 'FACT').toUpperCase())}</div>
    <div style="font-family:var(--font-mono); font-size:0.9rem; color:var(--text-secondary);">${escapeHtml(claim.claim_id)}</div>
    <span class="status-pill ${claim.status === 'contested' ? 'warning' : 'success'}" style="font-size:0.75rem;">${escapeHtml(claim.status || 'active')}</span>
  </div>
 <button class="btn-secondary btn-propose" style="padding:4px 8px; font-size:0.8rem;">Propose Edit</button>
 </div>
 
 <div style="margin: 16px 0; font-size:1.1rem; line-height:1.5;">
 ${claim.source_url
 ? (isWebUrl
     ? `<a href="${safeUrl(claim.source_url)}" target="_blank" style="color:var(--text-primary); text-decoration:none;">${formatStatement(claim.statement)}</a>`
     : `${formatStatement(claim.statement)}<div style="margin-top:6px; font-size:0.8rem; color:var(--text-secondary);">${escapeHtml(claim.source_url)} (internal reference — not externally viewable)</div>`)
 : formatStatement(claim.statement)}
 </div>
 
 ${claim.superseded_by ? `<div style="color:var(--status-contested); font-size:0.9rem; margin-bottom:16px;">Superseded by: <strong>${escapeHtml(claim.superseded_by)}</strong></div>` : ''}
 
 <div class="card-meta" style="display:flex; flex-wrap:wrap; gap:16px; margin-bottom:24px;">
 <div class="meta-item" title="Stage" style="display:flex; align-items:center; gap:6px;">
 ${iconFolder}
 <span>${escapeHtml(claim.stage_id || 'Unmapped')}</span>
 </div>
 <div class="meta-item" title="Source Tier" style="display:flex; align-items:center; gap:6px;">
 ${iconTier}
 <span>${escapeHtml(claim.source_tier_value || 'Unknown')}</span>
 </div>
 <div class="meta-item" title="Confidence" style="display:flex; align-items:center; gap:6px; color:var(--text-secondary);">
 <span>Conf: ${escapeHtml(claim.confidence || 'N/A')}</span>
 </div>
 </div>
 
  <div class="evidence-preview-container" style="margin-top: 8px;">
            ${isWebUrl
              ? `<button class="btn-secondary btn-preview-source" style="width:100%; margin-bottom:8px;">View Source ↗</button>
                 <div class="iframe-wrapper" style="display:none; border:1px solid var(--border-strong); border-radius:var(--radius-sm); overflow:hidden; margin-bottom:8px;"></div>
                 <a href="${safeUrl(claim.source_url)}" target="_blank" rel="noopener noreferrer" style="display:block; font-size:0.78rem; color:var(--text-secondary); text-align:center; text-decoration:none; padding:4px 0; word-break:break-all;">${escapeHtml(claim.source_url)}</a>`
              : `<div style="font-size:0.8rem; color:var(--text-secondary); padding:8px 0; border-top:1px solid var(--border);">${claim.source_url ? escapeHtml(claim.source_url) + ' (internal reference)' : 'No external source on file for this knowledge base claim.'}</div>`
            }
  </div>
  `;
 
 content.innerHTML = html;

 const proposeBtn = content.querySelector('.btn-propose');
 if (proposeBtn) {
  proposeBtn.addEventListener('click', () => openEditor(claim.claim_id));
 }

 const previewBtn = content.querySelector('.btn-preview-source');
 if (previewBtn && isWebUrl) {
  previewBtn.addEventListener('click', () => toggleSourcePreview(previewBtn, safeUrl(claim.source_url)));
 }
}

if (document.getElementById('btn-close-drawer')) {
 document.getElementById('btn-close-drawer').addEventListener('click', () => {
 drawerDialog.close();
 document.getElementById('claim-drawer').style.display = 'none';
 claimsContainer.querySelectorAll('.index-row.focused').forEach(r => r.classList.remove('focused'));
 document.querySelector('.claims-layout')?.classList.remove('drawer-open');
 });
}

window.toggleSourcePreview = function(btn, url) {
  const wrapper = btn.nextElementSibling;
  if (wrapper.style.display === 'none') {
    wrapper.style.display = 'block';
    wrapper.innerHTML = `<iframe src="${url}" sandbox="allow-same-origin allow-scripts" style="width:100%; height:320px; border:none; background:#fff; display:block;"></iframe>`;
    btn.textContent = 'Hide Source';
  } else {
    wrapper.style.display = 'none';
    wrapper.innerHTML = '';
    btn.textContent = 'View Source ↗';
  }
};

// Keyboard Navigation (MF-17)
claimsContainer.tabIndex = 0;
claimsContainer.addEventListener('keydown', (e) => {
 if (currentClaims.length === 0) return;
 
 if (e.key === 'j' || e.key === 'ArrowDown') {
 e.preventDefault();
 focusedIndex = Math.min(focusedIndex + 1, currentClaims.length - 1);
 updateFocus();
 } else if (e.key === 'k' || e.key === 'ArrowUp') {
 e.preventDefault();
 focusedIndex = Math.max(focusedIndex - 1, 0);
 updateFocus();
 } else if (e.key === 'Enter' && focusedIndex >= 0) {
 e.preventDefault();
 const row = claimsContainer.querySelector(`[data-index="${focusedIndex}"]`);
 if (row) {
 const claimId = row.dataset.id;
 const claim = currentClaims.find(c => c.claim_id === claimId);
 if (claim) openDrawer(claim);
 }
 } else if (e.key === 'Escape') {
 e.preventDefault();
 const drawer = document.getElementById('claim-drawer');
 if (drawer && drawer.style.display !== 'none') {
 drawerDialog.close();
 drawer.style.display = 'none';
 }
 }
});

function updateFocus() {
 claimsContainer.querySelectorAll('.index-row.focused').forEach(r => r.classList.remove('focused'));
 const row = claimsContainer.querySelector(`[data-index="${focusedIndex}"]`);
 if (row) {
 row.classList.add('focused');
 row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
 }
}

// Ingestion Editor Modal
window.openEditor = function(claimId = null) {
 editorModal.classList.add('active');
 editorDialog.open();
 if (claimId) {
 const claim = currentClaims.find(c => c.claim_id === claimId);
 editorTitle.textContent = `Propose Edit: ${claimId}`;
 editorForm.action.value = 'UPDATE';
 editorForm.claim_id.value = claimId;
 editorForm.statement.value = claim.statement || '';
 editorForm.source_url.value = claim.source_url || '';
 editorForm.confidence.value = claim.confidence || 'low';
 editorForm.source_tier.value = claim.source_tier_value || 'unknown';
 } else {
 editorTitle.textContent = 'Add New Claim';
 editorForm.reset();
 editorForm.action.value = 'INSERT';
 editorForm.claim_id.value = '';
 }
};

btnCancelEditor.addEventListener('click', () => {
 editorModal.classList.remove('active');
 editorDialog.close();
});

editorForm.addEventListener('submit', async (e) => {
 e.preventDefault();
 const payload = {
 action: editorForm.action.value,
 claim_id: editorForm.claim_id.value || null,
 statement: editorForm.statement.value,
 source_url: editorForm.source_url.value,
 confidence: editorForm.confidence.value,
 source_tier: editorForm.source_tier.value,
 notes: editorForm.notes.value
 };

 try {
 		const res = await AreosAPI.fetch(`/claims/ingest`, {
			method: 'POST',
			headers: getAuthHeaders(),
			body: JSON.stringify(payload)
		});
		const data = await res.json();
		AreosAPI.notify(`Success! Proposal logged in Run ${data.run_id || 'OK'}`, 'success');
		editorModal.classList.remove('active');
		editorDialog.close();
		fetchClaims(); // refresh to show update or new claim if relevant
 } catch(err) {
 AreosAPI.notify(err.message, 'error');
 }
});

// Event Listeners
let searchTimeout;
searchInput.addEventListener('input', () => {
 clearTimeout(searchTimeout);
 searchTimeout = setTimeout(() => fetchClaims(), 400);
});

[filterStage, filterStatus, filterConfidence, filterType, filterScope, filterPinned].forEach(el => {
 if(el) el.addEventListener('change', () => fetchClaims());
});

btnReset.addEventListener('click', () => {
 searchInput.value = "";
 filterStage.value = "";
 filterStatus.value = "";
 filterConfidence.value = "";
 filterType.value = "";
 if (filterScope) filterScope.value = "";
 filterPinned.checked = false;
 fetchClaims();
});

if(btnAddClaim) btnAddClaim.addEventListener('click', () => window.openEditor());

// Init
loadSavedFilters();
fetchClaims();
