// knowledge_explorer.js — Citeable V2 Knowledge Explorer
// Uses auth.js for API token and dom.js for safe rendering.

const API_BASE = window.location.origin + '/api/v1';

// DOM Elements
const knowledgeContainer = document.getElementById('knowledge-container');
const totalKnowledgeSpan = document.getElementById('total-knowledge');
const searchInput = document.getElementById('search-input');
const filterScope = document.getElementById('filter-scope');
const filterStatus = document.getElementById('filter-status');
const filterConfidence = document.getElementById('filter-confidence');
const filterType = document.getElementById('filter-type');
const filterPinned = document.getElementById('filter-pinned');
const btnReset = document.getElementById('btn-reset');

const drawerDialog = makeDialogAccessible(document.getElementById('knowledge-drawer'), {
 label: 'Knowledge Detail',
 onClose: () => {
 document.getElementById('knowledge-drawer').style.display = 'none';
 knowledgeContainer.querySelectorAll('.index-row.focused').forEach(r => r.classList.remove('focused'));
 document.querySelector('.claims-layout')?.classList.remove('drawer-open');
 drawerDialog.close();
 },
});

// State
let offset = 0;
const LIMIT = 50;
let currentRecords = [];
let totalCount = 0;
let totalDatabaseRecords = 216;
let currentAbortController = null;
let focusedIndex = -1;

const analystId = window.AreosContext?.analystId || 'unknown';
const storageKeyPins = `areos_kb_pins_${analystId}`;
const storageKeyFilters = `areos_kb_filters_${analystId}`;

let pinnedRecords = new Set(JSON.parse(localStorage.getItem(storageKeyPins) || '[]'));

async function fetchKBStats() {
  try {
    const res = await AreosAPI.fetch('/knowledge/stats');
    if (res.ok) {
      const stats = await res.json();
      if (stats.knowledge_count) {
        totalDatabaseRecords = stats.knowledge_count;
        updateCountsDisplay();
      }
    }
  } catch (e) {
    // fallback to 216
  }
}

function updateCountsDisplay() {
  const subtitleEl = document.getElementById('kb-subtitle');
  if (totalCount === totalDatabaseRecords) {
    if (totalKnowledgeSpan) totalKnowledgeSpan.textContent = `${totalCount} Records Found`;
    if (subtitleEl) subtitleEl.textContent = `Scientific Classification · ${totalDatabaseRecords} Verified Empirical & Technical Claims`;
  } else {
    if (totalKnowledgeSpan) totalKnowledgeSpan.textContent = `${totalCount} of ${totalDatabaseRecords} Records`;
    if (subtitleEl) subtitleEl.textContent = `Scientific Classification · ${totalDatabaseRecords} total · ${totalCount} matching current filters`;
  }
}

// Icons
const iconWarning = `<svg viewBox="0 0 24 24" fill="none" stroke="var(--status-contested)" stroke-width="2" width="16"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
const iconPin = `<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" width="16"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>`;
const iconPinUnfilled = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>`;
const iconSource = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>`;

function loadSavedFilters() {
 try {
 const saved = JSON.parse(localStorage.getItem(storageKeyFilters));
 if (saved) {
 if(saved.search) searchInput.value = saved.search;
 if(saved.scope) filterScope.value = saved.scope;
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
 scope: filterScope.value,
 status: filterStatus.value,
 confidence: filterConfidence.value,
 type: filterType.value,
 pinned: filterPinned.checked
 };
 localStorage.setItem(storageKeyFilters, JSON.stringify(filters));
}

function togglePin(kid, btn) {
 if (pinnedRecords.has(kid)) {
 pinnedRecords.delete(kid);
 btn.innerHTML = iconPinUnfilled;
 btn.classList.remove('pinned');
 } else {
 pinnedRecords.add(kid);
 btn.innerHTML = '';
 btn.classList.add('pinned');
 }
 localStorage.setItem(storageKeyPins, JSON.stringify(Array.from(pinnedRecords)));
}

async function fetchKnowledge(isLoadMore = false) {
 if (!isLoadMore) {
 offset = 0;
 currentRecords = [];
 knowledgeContainer.innerHTML = `<div class="loader-container"><div class="spinner"></div></div>`;
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
 if (filterScope.value) params.append("scope", filterScope.value);
 if (filterStatus.value) params.append("status", filterStatus.value);
 if (filterConfidence.value) params.append("confidence", filterConfidence.value);
 if (filterType.value) params.append("type", filterType.value);
 
 params.append("limit", LIMIT);
 params.append("offset", offset);

 try {
 const response = await AreosAPI.fetch(`/knowledge?${params.toString()}`, {
 signal: currentAbortController.signal
 });

 if (!response.ok) throw new Error("Failed to fetch");

 const data = await response.json();
 totalCount = data.total_count || 0;
 
 let fetched = data.records;
 if (filterPinned.checked) {
 fetched = fetched.filter(c => pinnedRecords.has(c.kid));
 totalCount = pinnedRecords.size;
 }

 if (!isLoadMore) {
 currentRecords = fetched;
 knowledgeContainer.innerHTML = '';
 } else {
 currentRecords = currentRecords.concat(fetched);
 const btn = document.getElementById('btn-load-more');
 if (btn) btn.remove();
 }
 
 renderRecords(fetched, isLoadMore);
 } catch (err) {
 if (err.name === 'AbortError') return;
 if (!isLoadMore) knowledgeContainer.innerHTML = '';
 AreosAPI.notify(`Error loading knowledge: ${err.message}`, 'error');
 if (totalKnowledgeSpan) totalKnowledgeSpan.textContent = "Error";
 }
}

function renderRecords(recordsToAppend, isLoadMore) {
 updateCountsDisplay();

 if (currentRecords.length === 0) {
 knowledgeContainer.innerHTML = `<div class="no-results">No records match the selected filters.</div>`;
 return;
 }

 recordsToAppend.forEach((record, idx) => {
 const row = document.createElement('div');
 row.className = 'index-row';
 row.dataset.id = record.kid;
 const actualIndex = isLoadMore ? (offset + idx) : idx;
 row.dataset.index = actualIndex;

 const isContested = record.status === 'contested';
 const isPinned = pinnedRecords.has(record.kid);
 const typeClass = `type-${record.type.toLowerCase()}`;

 row.innerHTML = `
 <div class="index-row-header">
 ${isContested ? `<div class="priority-indicator" title="Contested">${iconWarning}</div>` : ''}
 <div class="badge ${typeClass}" style="flex-shrink:0; margin-top:1px;">${record.type}</div>
 <div class="row-id" style="flex-shrink:0; font-family: var(--font-mono); font-size: 0.8125rem; color: var(--text-secondary); width: 65px; margin-top:2px;">${record.kid}</div>
 <div class="row-statement-preview"></div>
 <button class="btn-pin ${isPinned ? 'pinned' : ''}" style="flex-shrink:0; margin-left:auto; background:none; border:none; cursor:pointer; color:var(--text-secondary); font-size:1.2rem;" aria-label="Pin claim">
 ${isPinned ? '' : iconPinUnfilled}
 </button>
 </div>
 `;

 row.querySelector('.row-statement-preview').textContent = record.statement;

 const pinBtn = row.querySelector('.btn-pin');
 if (pinBtn) {
  pinBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  togglePin(record.kid, pinBtn);
  });
 }

 row.addEventListener('click', (e) => {
 if(e.target.closest('.btn-pin')) return;
 loadAndOpenDrawer(record);
 updateFocusIndex(actualIndex);
 });

 knowledgeContainer.appendChild(row);
 });

 if (currentRecords.length < totalCount && !filterPinned.checked) {
 const btnLoadMore = document.createElement('button');
 btnLoadMore.id = 'btn-load-more';
 btnLoadMore.className = 'btn-secondary';
 btnLoadMore.style.cssText = 'width:100%; margin-top:20px; padding:12px;';
 btnLoadMore.textContent = 'Load More';
 btnLoadMore.onclick = () => {
 offset += LIMIT;
 fetchKnowledge(true);
 };
 knowledgeContainer.appendChild(btnLoadMore);
 }
}

function updateFocusIndex(idx) {
 focusedIndex = idx;
 knowledgeContainer.querySelectorAll('.index-row.focused').forEach(r => r.classList.remove('focused'));
 const row = knowledgeContainer.querySelector(`[data-index="${focusedIndex}"]`);
 if (row) {
 row.classList.add('focused');
 row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
 }
}

async function loadAndOpenDrawer(record) {
 const drawer = document.getElementById('knowledge-drawer');
 const content = document.getElementById('drawer-content');
 if (!drawer || !content) return;
 
 drawer.style.display = 'block';
 drawer.scrollTop = 0;
 document.querySelector('.claims-layout')?.classList.add('drawer-open');
 drawerDialog.open();
 content.innerHTML = `<div class="loader-container"><div class="spinner"></div></div>`;

 try {
 const res = await AreosAPI.fetch(`/knowledge/${record.kid}`);
 if (!res.ok) throw new Error("Failed to load details");
 const detail = await res.json();
 renderDrawer(detail);
 } catch (err) {
 content.innerHTML = `<div style="color:var(--status-contested); padding:20px;">Error loading detail: ${err.message}</div>`;
 }
}

function renderDrawer(detail) {
 const content = document.getElementById('drawer-content');
 const rec = detail.record;
 
 	const formatText = (text) => {
		if (!text) return '';
		const safe = typeof escapeHtml === 'function' ? escapeHtml(text) : String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
		return safe
			.replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--text-primary); font-weight:600;">$1</strong>')
			.replace(/\*(.*?)\*/g, '<em>$1</em>')
			.replace(/`(.*?)`/g, '<code style="background:var(--surface-sunken); padding:2px 4px; border-radius:3px; font-family:var(--font-mono); font-size:0.9em; border:1px solid var(--border-default);">$1</code>');
	};

 const typeClass = `type-${rec.type.toLowerCase()}`;
 const statusClass = `status-${rec.status.toLowerCase()}`;

 let html = `
 <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
 <div style="display:flex; align-items:center; gap: 12px;">
 <span class="badge ${typeClass}">${rec.type}</span>
 <span class="badge ${statusClass}">${rec.status}</span>
 </div>
 <div style="font-family:var(--font-mono); font-size:0.9rem; color:var(--text-secondary);">${rec.kid}</div>
 </div>
 
 <div style="margin: 16px 0; font-size:1.1rem; line-height:1.5; color: var(--text-primary);">
 ${formatText(rec.statement)}
 </div>
 `;

 if (rec.context) {
 html += `
  <div style="margin-bottom: 24px; padding: 12px; background: var(--surface-sunken); border-radius: 6px; font-size: 0.95rem; line-height: 1.5; color: var(--text-secondary); border: 1px solid var(--border-default);">
 <strong>Context:</strong> ${formatText(rec.context)}
 </div>
 `;
 }

 if (rec.type === 'GUIDANCE' && rec.guidance_json) {
 try {
 const g = JSON.parse(rec.guidance_json);
 html += `
 <div style="margin-bottom: 24px; padding: 16px; border-left: 3px solid var(--accent); background: rgba(99,102,241,0.05);">
 <h4 style="margin-top:0; margin-bottom:8px; color:var(--text-primary); font-size:0.9rem; text-transform:uppercase;">Guidance Detail</h4>
 ${g.problem ? `<div style="margin-bottom:8px; font-size:0.95rem;"><strong>Problem:</strong> ${g.problem}</div>` : ''}
 ${g.action ? `<div style="font-size:0.95rem;"><strong>Action:</strong> ${g.action}</div>` : ''}
 </div>
 `;
 } catch(e) {}
 }

 html += `
 <div class="card-meta" style="display:flex; flex-wrap:wrap; gap:16px; margin-bottom:24px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 16px;">
 <div class="meta-item" style="display:flex; align-items:center; gap:6px;">
 <span>Conf: <strong style="color:var(--text-primary);">${rec.confidence}</strong></span>
 </div>
 <div class="meta-item" style="display:flex; align-items:center; gap:6px;">
 <span>Support: <strong style="color:var(--text-primary);">${rec.support}</strong></span>
 </div>
 ${rec.scope ? `<div class="meta-item">Scope: <strong style="color:var(--text-primary);">${rec.scope}</strong></div>` : ''}
 </div>
 `;

 // Evidence Chain
 if (detail.evidence.length > 0) {
 html += `<h4 style="margin-bottom: 12px; font-size:0.9rem; text-transform:uppercase; color:var(--text-secondary);">Evidence Chain (${detail.evidence.length})</h4>`;
 html += `<div style="display:flex; flex-direction:column; gap:12px; margin-bottom:24px;">`;
 
 detail.evidence.forEach(ev => {
 const src = detail.sources.find(s => s.sid === ev.sid);
 html += `
 <div style="padding: 12px; border: 1px solid var(--border-default); border-radius: 6px; background: var(--surface-panel);">
 <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
 <div style="font-size: 0.85rem; font-family: var(--font-mono); color: var(--text-secondary);">${ev.eid}</div>
 <div style="font-size: 0.85rem;"><strong style="color:var(--brand-text-on-canvas);">${ev.relationship}</strong> (${ev.weight})</div>
 </div>
 `;
 if (ev.note) {
 html += `<div style="font-size: 0.95rem; margin-bottom: 8px;">${formatText(ev.note)}</div>`;
 }
 if (src) {
 html += `
 <div style="display:flex; gap: 8px; align-items: flex-start; margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border-subtle);">
 <div style="color: var(--text-secondary); margin-top:2px;">${iconSource}</div>
 <div style="font-size: 0.9rem; overflow:hidden;">
 ${src.title ? `<div style="color:var(--text-primary); margin-bottom:2px;">${escapeHtml(src.title)}</div>` : ''}
 ${src.url ? `<a href="${safeUrl(src.url)}" target="_blank" style="color:var(--brand-text-on-canvas); text-decoration:none; word-break:break-all;">${escapeHtml(src.url)}</a>` : '<span style="color:var(--text-secondary);">Internal Document</span>'}
 ${src.publisher ? `<div style="color:var(--text-secondary); font-size:0.8rem; margin-top:2px;">${escapeHtml(src.publisher)} (${escapeHtml(src.authority)})</div>` : ''}
 </div>
 </div>
 `;
 }
 html += `</div>`;
 });
 
 html += `</div>`;
 } else {
 html += `<div style="font-size:0.9rem; color:var(--text-secondary); margin-bottom:24px;">No evidence linked to this record.</div>`;
 }

 // Check Codes
 if (detail.related_check_codes.length > 0) {
 html += `<div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-subtle);">
 <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:8px;">Mapped Check Codes:</div>
 <div style="display:flex; flex-wrap:wrap; gap:8px;">
  ${detail.related_check_codes.map(cc => `<span style="font-family:var(--font-mono); font-size:0.8rem; background:var(--surface-sunken); padding:2px 6px; border-radius:4px; border:1px solid var(--border-default);">${cc}</span>`).join('')}
 </div></div>`;
 }

 content.innerHTML = html;
}

// Bindings
document.addEventListener('DOMContentLoaded', () => {
 loadSavedFilters();
 fetchKBStats();
 fetchKnowledge();

 let debounce;
 searchInput.addEventListener('input', () => {
 clearTimeout(debounce);
 debounce = setTimeout(() => fetchKnowledge(), 300);
 });

 [filterScope, filterStatus, filterConfidence, filterType, filterPinned].forEach(el => {
 el.addEventListener('change', () => fetchKnowledge());
 });

 btnReset.addEventListener('click', () => {
 searchInput.value = '';
 filterScope.value = '';
 filterStatus.value = '';
 filterConfidence.value = '';
 filterType.value = '';
 filterPinned.checked = false;
 fetchKnowledge();
 });
 
 // Close drawer button
 document.getElementById('btn-close-drawer').addEventListener('click', () => {
 document.getElementById('knowledge-drawer').style.display = 'none';
 knowledgeContainer.querySelectorAll('.index-row.focused').forEach(r => r.classList.remove('focused'));
 document.querySelector('.claims-layout')?.classList.remove('drawer-open');
 drawerDialog.close();
 });
});
