// prompts.js — Governed Prompt Sets UI Manager
// Uses auth.js and dom.js for secure rendering and API calls.

const API_ROOT = window.location.origin;

function showToast(msg, type = '') {
 const t = document.getElementById('toast');
 if (!t) return;
 t.textContent = msg;
 t.className = `toast show ${type}`;
 setTimeout(() => { t.className = 'toast'; }, 3000);
}

async function loadPrompts() {
 const container = document.getElementById('prompts-list');
 try {
 const res = await AreosAPI.fetch(`${API_ROOT}/api/v1/prompts`);
 if (!res.ok) throw new Error(`HTTP error ${res.status}`);
 const data = await res.json();
 
 container.innerHTML = '';
 const list = data.prompts || [];
 
 if (list.length === 0) {
 container.appendChild(el('div', 'No prompt sets configured yet.', { style: { color: '#64748b', fontSize: '13px' } }));
 return;
 }
 
 list.forEach(item => {
 const card = document.createElement('div');
 card.className = 'prompt-card';
 
 const topRow = document.createElement('div');
 topRow.style.cssText = 'display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;';
 
 const titleCol = document.createElement('div');
 titleCol.appendChild(el('div', item.prompt_id, { className: 'prompt-id' }));
 titleCol.appendChild(el('div', item.label, { className: 'prompt-label' }));
 
 const badgesCol = document.createElement('div');
 badgesCol.style.cssText = 'display:flex; gap:8px; align-items:center;';
 if (item.funnel_stage) {
 badgesCol.appendChild(el('span', item.funnel_stage, { className: 'badge' }));
 }
 
 topRow.appendChild(titleCol);
 topRow.appendChild(badgesCol);
 
 const box = el('div', item.prompt_text, { className: 'prompt-text-box' });
 
 const bottomRow = document.createElement('div');
 bottomRow.className = 'prompt-meta';
 
 const info = document.createElement('span');
 const domainTxt = item.target_domain ? `Target Domain: ${item.target_domain}` : 'Global Query';
 info.textContent = `${domainTxt} • Added ${item.created_at || ''}`;
 
 const delBtn = el('button', 'Delete', {
 className: 'btn-delete',
 onclick: () => deletePrompt(item.prompt_id)
 });
 
 bottomRow.appendChild(info);
 bottomRow.appendChild(delBtn);
 
 card.appendChild(topRow);
 card.appendChild(box);
 card.appendChild(bottomRow);
 
 container.appendChild(card);
 });
 } catch (err) {
 console.error('Error loading prompts:', err);
 container.innerHTML = '';
 container.appendChild(el('div', 'Failed to load prompts from server.', { style: { color: '#f87171', fontSize: '13px' } }));
 }
}

async function submitPrompt(e) {
 e.preventDefault();
 const btn = document.getElementById('btn-submit');
 btn.disabled = true;
 btn.textContent = 'Saving...';
 
 const payload = {
 label: document.getElementById('p-label').value.trim(),
 prompt_text: document.getElementById('p-text').value.trim(),
 target_domain: document.getElementById('p-domain').value.trim(),
 funnel_stage: document.getElementById('p-stage').value,
 active: 1
 };
 
 try {
 const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Content-Type': 'application/json', 'Authorization': 'Bearer admin' };
 const res = await AreosAPI.fetch(`${API_ROOT}/api/v1/prompts`, {
 method: 'POST',
 headers: headers,
 body: JSON.stringify(payload)
 });
 
 const data = await res.json();
 if (!res.ok || data.status !== 'success') {
 throw new Error(data.detail || 'Failed to save prompt set');
 }
 
 showToast('Prompt set successfully recorded!', 'success');
 document.getElementById('prompt-form').reset();
 loadPrompts();
 } catch (err) {
 console.error('Save error:', err);
 showToast(`Error: ${err.message}`, 'error');
 } finally {
 btn.disabled = false;
 btn.textContent = 'Save Governed Prompt Set';
 }
}

async function deletePrompt(promptId) {
 if (!confirm(`Are you sure you want to delete prompt set ${promptId}?`)) return;
 
 try {
 const headers = typeof getAuthHeaders === 'function' ? getAuthHeaders() : { 'Authorization': 'Bearer admin' };
 const res = await AreosAPI.fetch(`${API_ROOT}/api/v1/prompts/${encodeURIComponent(promptId)}`, {
 method: 'DELETE',
 headers: headers
 });
 
 const data = await res.json();
 if (!res.ok || data.status !== 'success') {
 throw new Error(data.detail || 'Failed to delete prompt');
 }
 
 showToast(`Deleted ${promptId}`, 'success');
 loadPrompts();
 } catch (err) {
 console.error('Delete error:', err);
 showToast(`Error: ${err.message}`, 'error');
 }
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
 loadPrompts();
});
