// remediation.js — Citeable Remediation Plan Viewer
// Uses auth.js and dom.js for safe rendering.

const API = window.location.origin;
let planMarkdownText = '';

function showToast(msg, type = '') {
 const t = document.getElementById('toast');
 t.textContent = msg;
 t.className = `toast show ${type}`;
 setTimeout(() => { t.className = 'toast'; }, 2800);
}

async function loadRuns() {
 try {
 const res = await AreosAPI.fetch(`${API}/api/v1/audit/runs`);
 const data = await res.json();
 const sel = document.getElementById('run-select');
 if (!data.runs || data.runs.length === 0) {
 sel.innerHTML = '<option value="">No audit runs yet — create one in Manual Review</option>';
 return;
 }
 sel.innerHTML = data.runs.map(r =>
 `<option value="${escapeHtml(r.run_id)}">[${escapeHtml(r.run_date)}] ${escapeHtml(r.target_domain)} — ${escapeHtml(r.run_id)} (${escapeHtml(r.status)})</option>`
 ).join('');

 const urlParams = new URLSearchParams(window.location.search);
 const runIdParam = urlParams.get('run_id') || window.AreosContext?.activeRunId;
 if (runIdParam) {
 sel.value = runIdParam;
 loadPlan();
 } else if (data.runs.length > 0) {
 sel.value = data.runs[0].run_id;
 if (window.AreosContext) window.AreosContext.activeRunId = data.runs[0].run_id;
 loadPlan();
 }
 sel.addEventListener('change', (e) => {
 const v = e.target.value;
 if(v) {
 if (window.AreosContext) window.AreosContext.activeRunId = v;
 const u = new URL(window.location);
 u.searchParams.set('run_id', v);
 window.history.replaceState({}, '', u);
 loadPlan();
 }
 });
 } catch (e) {
 document.getElementById('run-select').innerHTML = '<option value="">API offline</option>';
 }
}

async function loadPlan() {
 const runId = document.getElementById('run-select').value;
 if (!runId) { showToast('Select a run first', 'error'); return; }

 try {
 const res = await AreosAPI.fetch(`${API}/api/v1/audit/runs/${runId}/remediation`);
 if (!res.ok) throw new Error((await res.json()).detail || 'API error');
 const data = await res.json();
 renderPlan(data);
 } catch (e) {
 showToast('Error: ' + e.message, 'error');
 }
}

function renderPlan(data) {
 document.getElementById('stat-grid').style.display = '';
 setText('stat-total', data.total_recommendations);
 setText('stat-critical', data.critical_count);
 setText('stat-manual', data.recommendations.filter(r => r.source === 'manual').length);
 setText('stat-qa', data.qa_rejections);

 // QA rejections
 const qaPanel = document.getElementById('qa-panel');
 const qaList = document.getElementById('qa-list');
 if (data.qa_rejected && data.qa_rejected.length > 0) {
 qaPanel.style.display = '';
 qaList.innerHTML = '';
 data.qa_rejected.forEach(r => {
 const div = document.createElement('div');
 div.className = 'qa-item';
 const code = el('code', `[${r.check_code}]`);
 div.appendChild(code);
 div.appendChild(document.createTextNode(` ${r.reason}`));
 qaList.appendChild(div);
 });
 } else {
 qaPanel.style.display = 'none';
 }

 const container = document.getElementById('recs-container');
 if (!data.recommendations || data.recommendations.length === 0) {
 container.innerHTML = '';
 container.appendChild(el('div', 'No recommendations for this run.', {
 className: 'glass-card',
 style: {textAlign: 'center', color: '#64748b', padding: '40px'}
 }));
 return;
 }

 // Group by page_url
 const grouped = {};
 data.recommendations.forEach(rec => {
 const page = rec.page_url || 'Global / Sitewide';
 if (!grouped[page]) grouped[page] = [];
 grouped[page].push(rec);
 });
 
 // Sort pages (Global first, then alphabetical)
 const sortedPages = Object.keys(grouped).sort((a, b) => {
 if (a === 'Global / Sitewide') return -1;
 if (b === 'Global / Sitewide') return 1;
 return a.localeCompare(b);
 });

 container.innerHTML = '';
 let recNum = 1;
 
 for (const page of sortedPages) {
 container.appendChild(el('div', page, {className: 'tier-header tier-MEDIUM', style: 'margin-top: 32px; font-family: var(--font-mono); font-size: 1.1rem; border-bottom: 1px solid var(--border-default); padding-bottom: 8px; margin-bottom: 16px; color: var(--text-primary);'}));
 
 // Sort within page by priority (1 is highest)
 const pageRecs = grouped[page].sort((a, b) => (a.priority || 99) - (b.priority || 99));
 for (const rec of pageRecs) {
 container.appendChild(renderRecCard(rec, recNum++));
 }
 }

 planMarkdownText = data.plan_markdown || '';
 document.getElementById('plan-markdown').textContent = planMarkdownText;
}

// Helper: Deduplicate description by stripping redundant repetition of the recommendation title
function cleanDescription(desc, title) {
  if (!desc) return '';
  let cleaned = String(desc).trim();
  const rawTitle = (title || '').trim().replace(/[.\s]+$/, '');
  if (!rawTitle) return cleaned;

  const lines = cleaned.split('\n');
  const filtered = lines.map(line => {
    let l = line.trim();
    const cleanL = l.replace(/[.\s]+$/, '');
    if (cleanL.toLowerCase() === rawTitle.toLowerCase()) {
      return '';
    }
    const idx = l.toLowerCase().indexOf(rawTitle.toLowerCase());
    if (idx !== -1) {
      let before = l.slice(0, idx).trim().replace(/[:.\s-]+$/, '');
      let after = l.slice(idx + rawTitle.length).replace(/^[.\d)\s]+/, '').replace(/^[:.\s-]+/, '').trim();
      return [before, after].filter(Boolean).join('. ');
    }
    return l;
  }).filter(Boolean);

  return filtered.join('\n').trim();
}

function renderRecCard(rec, num) {
 const card = document.createElement('div');
 card.className = `rec-card source-${rec.source}`;
 card.style.marginBottom = '16px';

 const header = document.createElement('div');
 header.className = 'rec-header';

 const title = el('div', `${num}. ${rec.title}`, {className: 'rec-title'});

 const meta = document.createElement('div');
 meta.className = 'rec-meta';

 const claimStatus = rec.claim_status ? ` · ${rec.claim_status}` : '';
 const confidence = rec.confidence ? ` · conf: ${rec.confidence}` : '';
 const claimPill = el('a', `${rec.claim_id}${claimStatus}${confidence}`, {
 className: 'claim-pill',
 title: `View claim ${rec.claim_id}`,
 onClick: () => fetchClaim(rec.claim_id),
 style: 'cursor: pointer;'
 });

 const srcClass = rec.source === 'manual' ? 'manual' : 'automated';
 const srcLabel = rec.source === 'manual' ? 'Human Review' : 'Automated';
 const srcBadge = el('span', srcLabel, {className: `src-badge ${srcClass}`});
 
 // Priority Badge (bubbled up)
 const priorityNum = rec.priority || 99;
 let prioLabel = 'LOW';
 let prioColor = 'var(--status-deprecated)';
 if (priorityNum <= 5) { prioLabel = 'CRITICAL'; prioColor = 'var(--status-danger)'; }
 else if (priorityNum <= 9) { prioLabel = 'HIGH'; prioColor = 'var(--status-contested)'; }
 else if (priorityNum <= 11) { prioLabel = 'MEDIUM'; prioColor = 'var(--brand-400)'; }
 
 const prioBadge = el('span', `Remediation Priority: ${prioLabel}`, {style: `background: ${prioColor}20; color: ${prioColor}; border: 1px solid ${prioColor}50; padding: 2px 8px; border-radius: var(--radius-full); font-size: 0.75rem; font-weight: bold; margin-left: 8px;`});

 // Evidence Quality Badge (mock from claim API if not present, but for now we show a placeholder if missing)
 // Actually, we don't have claim.source_tier directly on rec, but we can display "Evidence"
 const evBadge = el('span', 'Evidence', {style: `background: var(--surface-panel); color: var(--text-secondary); border: 1px solid var(--border-default); padding: 2px 8px; border-radius: var(--radius-full); font-size: 0.75rem; font-weight: bold; margin-left: 8px;`});

 meta.appendChild(claimPill);
 meta.appendChild(srcBadge);
 meta.appendChild(prioBadge);
 meta.appendChild(evBadge);

 header.appendChild(title);
 header.appendChild(meta);

 const deduplicatedDesc = cleanDescription(rec.description, rec.title);
 const desc = deduplicatedDesc ? el('div', deduplicatedDesc, {className: 'rec-description', style: 'margin-top: 12px; color: var(--text-secondary);'}) : null;

 card.appendChild(header);
 if (desc) card.appendChild(desc);

 // Inline citation — use data already on the rec object if the API returned it,
 // otherwise fall back to a secondary claim fetch (older server versions).
 if (rec.claim_id) {
  const citationEl = document.createElement('div');
  citationEl.className = 'rec-citation';
  citationEl.style.cssText = 'margin-top:14px; padding:10px 14px; background:var(--surface-panel); border-left:3px solid var(--brand-400); border-radius:0 var(--radius-sm) var(--radius-sm) 0; font-size:0.82rem;';
  card.appendChild(citationEl);

  const renderCitation = (statement, sourceUrl) => {
    if (!statement) { citationEl.innerHTML = `<span style="color:var(--text-secondary);">Citation: <em>${escapeHtml(rec.claim_id)}</em></span>`; return; }
    const isWebUrl = sourceUrl && /^https?:\/\//i.test(sourceUrl);
    const sourceLink = isWebUrl
     ? `<a href="${safeUrl(sourceUrl)}" target="_blank" rel="noopener noreferrer" style="color:var(--brand-400); margin-left:10px; white-space:nowrap;">View Source ↗</a>`
     : (sourceUrl ? `<span style="color:var(--text-secondary); margin-left:10px; font-size:0.78rem;">${escapeHtml(sourceUrl)}</span>` : '');
    citationEl.innerHTML = `
     <div style="display:flex; align-items:baseline; gap:6px; flex-wrap:wrap;">
      <span style="color:var(--brand-500); font-weight:700; white-space:nowrap; display:inline-flex; align-items:center; gap:4px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg> ${escapeHtml(rec.claim_id)}</span>
      <span style="color:var(--text-secondary);">—</span>
      <span style="color:var(--text-primary); line-height:1.45;">${escapeHtml(statement)}</span>
      ${sourceLink}
     </div>`;
   };

  if (rec.claim_statement) {
   // Already in the API response — no second fetch needed
   renderCitation(rec.claim_statement, rec.claim_source_url);
  } else {
   // Fallback for older server versions
   citationEl.innerHTML = `<span style="color:var(--text-secondary);">Loading citation for ${rec.claim_id}…</span>`;
   AreosAPI.fetch(`${API}/api/v1/claims?claim_id=${rec.claim_id}&limit=1`)
    .then(r => r.json())
    .then(data => {
     const claim = (data.claims || []).find(c => c.claim_id === rec.claim_id);
     renderCitation(claim && claim.statement, claim && claim.source_url);
    })
    .catch(() => { citationEl.innerHTML = `<span style="color:var(--text-secondary);">Citation: <em>${rec.claim_id}</em></span>`; });
  }
 }

 return card;
}

function renderModalSource(sourceUrl) {
 const container = document.getElementById('modal-source');
 if (!container) return;
 container.innerHTML = '';

 if (!sourceUrl) {
   container.textContent = '(no source URL)';
   return;
 }

 const isWebUrl = /^https?:\/\//i.test(sourceUrl);
 if (!isWebUrl) {
   container.textContent = `${sourceUrl} (internal reference — not externally viewable)`;
   return;
 }

 const link = el('a', sourceUrl, {
   href: safeUrl(sourceUrl),
   target: '_blank',
   rel: 'noopener noreferrer',
   style: 'color: var(--text-primary); text-decoration: underline; word-break: break-all;'
 });
 container.appendChild(link);
}

async function fetchClaim(claimId) {
 try {
 const res = await AreosAPI.fetch(`${API}/api/v1/claims?claim_id=${claimId}&limit=1`);
 const data = await res.json();
 let claim = (data.claims || []).find(c => c.claim_id === claimId);

 if (!claim) {
 showToast(`Claim ${claimId} not found in DB`, 'error');
 return;
 }

 setText('modal-title', claim.claim_id);
 setText('modal-id', claim.claim_type || '');
 setText('modal-status', claim.status || 'unknown');
 setText('modal-confidence', claim.confidence || 'N/A');
 setText('modal-stage', claim.stage_id || 'N/A');
 setText('modal-statement', claim.statement || '(no statement)');
 renderModalSource(claim.source_url);
 document.getElementById('claim-modal').classList.add('open');
 } catch (e) {
 showToast('Could not load claim: ' + e.message, 'error');
 }
}

function closeModal(e) {
 if (e.target.id === 'claim-modal') {
 document.getElementById('claim-modal').classList.remove('open');
 }
}

function toggleMarkdown() {
 const el = document.getElementById('plan-markdown');
 const card = document.getElementById('markdown-card');
 if (el.classList.contains('visible')) {
 el.classList.remove('visible');
 } else {
 el.classList.add('visible');
 card.style.display = '';
 el.scrollIntoView({ behavior: 'smooth' });
 }
}

async function copyMarkdown() {
 if (!planMarkdownText) { showToast('Generate or select a plan first', 'error'); return; }
 try {
 if (navigator.clipboard && navigator.clipboard.writeText) {
 await navigator.clipboard.writeText(planMarkdownText);
 showToast('[OK] Plan markdown copied to clipboard!', 'success');
 return;
 }
 } catch (err) {}

 try {
 const ta = document.createElement('textarea');
 ta.value = planMarkdownText;
 ta.style.position = 'fixed';
 ta.style.left = '-9999px';
 ta.style.top = '-9999px';
 document.body.appendChild(ta);
 ta.focus();
 ta.select();
 const successful = document.execCommand('copy');
 document.body.removeChild(ta);
 if (successful) {
 showToast('[OK] Plan markdown copied to clipboard!', 'success');
 } else {
 throw new Error('Fallback failed');
 }
 } catch (e) {
 showToast('Could not auto-copy. Please manually select and copy.', 'error');
 }
}

loadRuns();
