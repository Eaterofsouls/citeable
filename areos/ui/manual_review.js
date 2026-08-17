// manual_review.js — Citeable Manual Review UI
// Uses auth.js and dom.js for safe rendering.

const API = window.location.origin;

let currentRunId = null;
let currentCards = [];
let verdictSelections = {};

function showToast(msg, type = '') {
 const t = document.getElementById('toast');
 t.textContent = msg;
 t.className = `toast show ${type}`;
 setTimeout(() => { t.className = 'toast'; }, 3200);
}

function severityFromVerdict(verdict) {
 return { pass: 'info', warn: 'warning', fail: 'error', na: 'info' }[verdict] || 'info';
}

function authHeaders() {
 return getAuthHeaders();
}

async function loadRuns() {
 try {
 const res = await AreosAPI.fetch(`${API}/api/v1/audit/runs`);
 const data = await res.json();
 const sel = document.getElementById('run-select');
 if (!data.runs || data.runs.length === 0) {
 sel.innerHTML = '<option value="">No audit runs yet</option>';
 return;
 }
 sel.innerHTML = data.runs.map(r =>
 `<option value="${escapeHtml(r.run_id)}">[${escapeHtml(r.run_date)}] ${escapeHtml(r.target_domain)} — ${escapeHtml(r.run_id)} (${escapeHtml(r.status)})</option>`
 ).join('');

 const urlParams = new URLSearchParams(window.location.search);
 const runIdParam = urlParams.get('run_id') || window.AreosContext?.activeRunId;
 if (runIdParam) {
 sel.value = runIdParam;
 loadSelectedRun();
 } else if (data.runs.length > 0) {
 sel.selectedIndex = 0;
 loadSelectedRun();
 }

 sel.addEventListener('change', (e) => {
 const v = e.target.value;
 if (v) {
 if (window.AreosContext) window.AreosContext.activeRunId = v;
 const u = new URL(window.location);
 u.searchParams.set('run_id', v);
 window.history.replaceState({}, '', u);
 loadSelectedRun();
 }
 });
 } catch (e) {
 document.getElementById('run-select').innerHTML = '<option value="">API offline</option>';
 }
}

async function loadSelectedRun() {
 const runId = document.getElementById('run-select').value;
 if (!runId) { showToast('Select a run first', 'error'); return; }
 currentRunId = runId;
 verdictSelections = {};

 try {
 const res = await AreosAPI.fetch(`${API}/api/v1/audit/runs/${runId}`);
 if (!res.ok) throw new Error('Run not found');
 const data = await res.json();
 renderRun(data);
 } catch (e) {
 showToast('Failed to load run: ' + e.message, 'error');
 }
}

function renderRun(data) {
 const { run, automated_findings, triggered_cards } = data;
 currentCards = triggered_cards;

 document.getElementById('run-meta').style.display = 'flex';
 setText('run-domain', `Domain: ${run.target_domain}`);
 const badge = document.getElementById('run-status-badge');
 badge.textContent = run.status;
 badge.className = `run-status badge ${run.status}`;
 document.getElementById('final-report-btn').style.display = '';

 updateProgress();
 renderFindings(automated_findings);
 renderCards(triggered_cards);

 // Automatically generate final report so the user immediately sees the markdown baseline
 generateFinalReport();
}

function renderFindings(findings) {
 const sec = document.getElementById('findings-section');
 const list = document.getElementById('findings-list');
 const count = document.getElementById('findings-count');
 if (!findings || findings.length === 0) { sec.style.display = 'none'; return; }
 sec.style.display = '';
 count.textContent = `${findings.length} findings`;

 list.innerHTML = '';
 const icons = { error: '[FAIL]', warning: '[WARN]', info: '[INFO]' };
 const colors = { error: '#f87171', warning: '#fbbf24', info: '#818cf8' };

 findings.forEach(f => {
 const row = document.createElement('div');
 row.style.cssText = 'display:flex; gap:12px; align-items:flex-start; padding:10px 14px; background:#181818; border-radius:4px; border:1px solid #333; margin-bottom:6px;';

 const icon = el('span', icons[f.severity] || '?', {
 style: {color: colors[f.severity] || '#FFFFFF', fontWeight: '800', minWidth: '16px'}
 });
 const code = el('code', `[${f.code}]`, {
 style: {color: '#FFFFFF', fontWeight: '700', fontSize: '13px', minWidth: '220px', fontFamily: 'var(--font-mono)'}
 });
 const msg = el('span', f.message, {
 style: {fontSize: '14px', color: '#E2E8F0', lineHeight: '1.5'}
 });

 row.appendChild(icon);
 row.appendChild(code);
 row.appendChild(msg);
 list.appendChild(row);
 });
}

function renderCards(cards) {
 const sec = document.getElementById('cards-section');
 const grid = document.getElementById('cards-grid');
 if (!cards || cards.length === 0) { sec.style.display = 'none'; return; }
 sec.style.display = '';

 const notAuto = cards.filter(c => c.automatability === 'Not');
 const partial = cards.filter(c => c.automatability === 'Partial');
 setText('not-auto-count', `${notAuto.length} Not-automatable`);
 setText('partial-count', `${partial.length} Partial`);

 grid.innerHTML = cards.map(card => renderCardHTML(card)).join('');

 cards.forEach(card => {
 const vcardEl = document.getElementById(`vcard-${card.card_id}`);
 if (!vcardEl) return;
 vcardEl.querySelector('.vcard-id').textContent = card.card_id;
 vcardEl.querySelector('.vcard-name').textContent = card.check_name;
 vcardEl.querySelector('.vcard-reason').textContent = card.reason;
 });
}

function getHumanReviewGuidance(cardId, checkName, reason) {
  if (typeof window.GuidedReview !== "undefined" && typeof window.GuidedReview.getHumanReviewGuidance === "function") {
    return window.GuidedReview.getHumanReviewGuidance(cardId, checkName, reason);
  }
  return `<strong>General Verification Protocol:</strong> Review this diagnostic check against empirical RAG visibility and LLM citation behavior.<br>
  • <strong>PASS:</strong> Empirical verification confirms zero degradation to AI reference quality or answer accuracy.<br>
  • <strong>WARN:</strong> Minor architectural formatting ambiguity that may lower citation frequency.<br>
  • <strong>FAIL:</strong> Issue severely disrupts Generative AI trust evaluation or prevents citation.`;
}

function renderCardHTML(card) {
 const existing = card.verdicts && card.verdicts.length > 0;
 const autoLabel = card.automatability === 'Not' ? 'Not Automatable' : 'Partial';

 let verdictLog = '';
 if (existing) {
 verdictLog = '<div class="verdict-log" style="background:#141414; padding:14px 18px; border-radius:4px; border:1px solid #444; margin:16px 0;"><div style="font-size:11px; font-weight:800; color:#FFFFFF; text-transform:uppercase; margin-bottom:8px;">RECORDED HUMAN VERDICTS</div>';
 card.verdicts.forEach(v => {
 verdictLog += `<div class="log-entry" style="color:#FFFFFF; font-size:13px; padding:6px 0; border-top:1px solid #222;"><span style="font-weight:800; color:#FFFFFF;">[${escapeHtml(v.verdict).toUpperCase()}]</span>`;
 if (v.page_url) verdictLog += ` <code style="font-size:11px; background:#262626; padding:3px 8px; border-radius:2px; color:#FFFFFF; border:1px solid #555;">${escapeHtml(v.page_url)}</code>`;
 verdictLog += ` — ${escapeHtml(v.notes) || '(no notes provided)'}</div>`;
 });
 verdictLog += '</div>';
 }

 const guidanceHtml = getHumanReviewGuidance(card.card_id, card.check_name || "", card.reason || "");

 return `
 <div class="card vcard ${existing ? 'complete' : ''}" id="vcard-${escapeHtml(card.card_id)}" style="margin-bottom:24px; padding:28px; border:1px solid #444; background:#141414;">
 <div class="vcard-header" style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #333; padding-bottom:14px; margin-bottom:16px;">
 <span class="vcard-id" style="font-family:var(--font-mono); font-weight:800; font-size:1.15rem; color:#FFFFFF;"></span>
 <span class="badge vcard-auto ${escapeHtml(card.automatability)}">${escapeHtml(autoLabel)}</span>
 </div>
 <h3 class="vcard-name" style="color:#FFFFFF; font-size:1.3rem; font-weight:800; margin:0 0 12px 0;"></h3>
 <div style="font-size:0.95rem; color:#BBBBBB; margin-bottom:18px;">
 <strong style="color:#FFFFFF;">Check code(s) fired:</strong> <span class="vcard-reason" style="color:#FFFFFF; font-family:var(--font-mono); font-weight:700;"></span>
 </div>
 
 <div style="background: rgba(255,255,255,0.04); border: 1px solid #383838; border-left: 4px solid #FFFFFF; padding: 16px 20px; margin: 18px 0 24px 0; border-radius: 4px;">
 <span id="gr-technical" style="font-size:0.85rem; color:#f87171; letter-spacing:0.05em; font-weight:800; border:1px solid rgba(248,113,113,0.3); padding:4px 10px; border-radius:4px; display:inline-block; margin-bottom:12px;">HUMAN REVIEW GUIDANCE & CRITICAL PROTOCOL</span>
 <div style="font-size: 0.95rem; line-height: 1.65; color: #E2E8F0;">
 ${guidanceHtml}
 </div>
 </div>

 ${verdictLog}

 <div class="vcard-form" style="display:flex; flex-direction:column; gap:16px; margin-top: 10px;">
 <div style="width: 100%;">
 <input type="text" id="url-${escapeHtml(card.card_id)}" class="input" placeholder="Target Page URL examined (optional)" style="width: 100%; box-sizing: border-box; padding: 12px 16px; font-size: 0.95rem;" />
 </div>
 <div style="width: 100%;">
 <textarea id="notes-${escapeHtml(card.card_id)}" class="input" rows="3" placeholder="Enter your investigative findings, observational context, or remediation notes..." style="width: 100%; box-sizing: border-box; padding: 12px 16px; font-size: 0.95rem; line-height: 1.5;"></textarea>
 </div>
 <div class="verdict-buttons">
 <button class="vbtn pass" id="vbtn-pass-${escapeHtml(card.card_id)}" onclick="selectVerdict('${escapeHtml(card.card_id)}','pass')">PASS</button>
 <button class="vbtn warn" id="vbtn-warn-${escapeHtml(card.card_id)}" onclick="selectVerdict('${escapeHtml(card.card_id)}','warn')">WARN</button>
 <button class="vbtn fail" id="vbtn-fail-${escapeHtml(card.card_id)}" onclick="selectVerdict('${escapeHtml(card.card_id)}','fail')">FAIL</button>
 <button class="vbtn na" id="vbtn-na-${escapeHtml(card.card_id)}" onclick="selectVerdict('${escapeHtml(card.card_id)}','na')">N/A</button>
 </div>
 <button class="btn-primary" id="submit-${escapeHtml(card.card_id)}" onclick="submitVerdict('${escapeHtml(card.card_id)}')" disabled style="padding: 16px; font-size: 1rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em;">
 Submit & Record Verdict
 </button>
 </div>
 </div>
 `;
}

function selectVerdict(cardId, verdict) {
 ['pass','warn','fail','na'].forEach(v => {
 const btn = document.getElementById(`vbtn-${v}-${cardId}`);
 if (btn) btn.classList.remove('selected');
 });
 const selBtn = document.getElementById(`vbtn-${verdict}-${cardId}`);
 if (selBtn) selBtn.classList.add('selected');
 verdictSelections[cardId] = verdict;
 const subBtn = document.getElementById(`submit-${cardId}`);
 if (subBtn) subBtn.disabled = false;
}

async function submitVerdict(cardId) {
 const verdict = verdictSelections[cardId];
 if (!verdict) { showToast('Select a verdict first', 'error'); return; }
 const notes = document.getElementById(`notes-${cardId}`).value.trim();
 const pageUrl = document.getElementById(`url-${cardId}`).value.trim();
 const btn = document.getElementById(`submit-${cardId}`);

 btn.disabled = true;
 btn.textContent = 'Submitting...';

 try {
 const res = await AreosAPI.fetch(`${API}/api/v1/audit/runs/${currentRunId}/verdicts`, {
 method: 'POST',
 headers: authHeaders(),
 body: JSON.stringify({
 card_id: cardId,
 page_url: pageUrl,
 verdict: verdict,
 severity: severityFromVerdict(verdict),
 notes: notes,
 }),
 });
 if (!res.ok) {
 const err = await res.json();
 throw new Error(err.detail || 'API error');
 }

 const card = document.getElementById(`vcard-${cardId}`);
 if (card) card.classList.add('complete');
 btn.textContent = '[SUCCESS] Verdict Recorded';
 showToast(`[SUCCESS] Verdict recorded for ${cardId}`, 'success');
 updateProgress(cardId);
 // Regenerate report to seamlessly merge the freshly recorded verdict
 generateFinalReport();
 } catch (e) {
 btn.disabled = false;
 btn.textContent = 'Submit & Record Verdict';
 showToast('Error: ' + e.message, 'error');
 }
}

function updateProgress(newlyDone) {
 const submitted = document.querySelectorAll('.vcard.complete').length;
 const total = currentCards.length;
 const pct = total > 0 ? Math.round((submitted / total) * 100) : 0;
 const fill = document.getElementById('progress-fill');
 const label = document.getElementById('progress-label');
 if (fill) fill.style.width = pct + '%';
 if (label) label.textContent = `${submitted} / ${total}`;
}

async function generateFinalReport() {
 if (!currentRunId) { return; }
 const btn = document.getElementById('final-report-btn');
 if (btn) {
 btn.textContent = 'Compiling...';
 btn.disabled = true;
 }

 try {
 const res = await AreosAPI.fetch(`${API}/api/v1/audit/runs/${currentRunId}/report`);
 if (!res.ok) throw new Error('Failed to compile report');
 const data = await res.json();

 const sec = document.getElementById('report-section');
 if (sec) sec.style.display = '';
 const box = document.getElementById('report-box');
 if (box) box.textContent = data.report_markdown;

 const badge = document.getElementById('run-status-badge');
 if (badge) {
 badge.textContent = 'report_generated';
 badge.className = 'run-status badge report_generated';
 }
 showToast(`[SUCCESS] Compiled report with ${data.manual_verdicts_count || 0} human verdicts!`, 'success');
 } catch (e) {
 showToast('Error compiling report: ' + e.message, 'error');
 } finally {
 if (btn) {
 btn.textContent = 'Generate Final Report';
 btn.disabled = false;
 }
 }
}

async function copyReport() {
 let text = document.getElementById('report-box')?.textContent?.trim() || "";
 if (!text || text.includes("[Report has not been compiled yet")) {
 if (!currentRunId) {
 showToast('Please select an audit run first.', 'error');
 return;
 }
 showToast('Compiling report before copying...', 'info');
 await generateFinalReport();
 text = document.getElementById('report-box')?.textContent?.trim() || "";
 if (!text || text.includes("[Report has not been compiled yet")) {
 showToast('Report compilation failed or is empty.', 'error');
 return;
 }
 }

 try {
 if (navigator.clipboard && navigator.clipboard.writeText) {
 await navigator.clipboard.writeText(text);
 showToast('[OK] Copied Executive Report Markdown to clipboard!', 'success');
 return;
 }
 } catch (err) {}

 try {
 const ta = document.createElement('textarea');
 ta.value = text;
 ta.style.position = 'fixed';
 ta.style.left = '-9999px';
 ta.style.top = '-9999px';
 document.body.appendChild(ta);
 ta.focus();
 ta.select();
 const successful = document.execCommand('copy');
 document.body.removeChild(ta);
 if (successful) {
 showToast('[OK] Copied Executive Report Markdown to clipboard!', 'success');
 } else {
 throw new Error('Fallback failed');
 }
 } catch (e) {
 showToast('Could not auto-copy. Please manually select and copy text.', 'error');
 }
}

loadRuns();
