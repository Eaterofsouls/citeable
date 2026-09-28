/**
 * approvals.js — Citeable Human Verification & Override Console
 */

const API_BASE = (typeof API_BASE_URL !== 'undefined') ? `${API_BASE_URL}/api/v1` : '/api/v1';

let pendingItems = [];
let selectedItem = null;
let selectedCandidates = new Set();
let isBulkMode = false;
let pendingAction = null;

const pendingList = document.getElementById('pending-list');
const diffView = document.getElementById('diff-view');
const pendingCountSpan = document.getElementById('pending-count');
const selectAllCb = document.getElementById('select-all-cb');
const btnBulkApprove = document.getElementById('btn-bulk-approve');
const btnBulkReject = document.getElementById('btn-bulk-reject');
const bulkCountSpan = document.getElementById('bulk-count');
const passwordModal = document.getElementById('password-modal');
const btnSubmitPassword = document.getElementById('btn-submit-password');
const btnCancelPassword = document.getElementById('btn-cancel-password');

function updateBulkUI() {
  const count = selectedCandidates.size;
  if (bulkCountSpan) bulkCountSpan.textContent = count;
  if (btnBulkApprove) btnBulkApprove.disabled = count === 0;
  if (btnBulkReject) btnBulkReject.disabled = count === 0;

  if (selectAllCb) {
    if (pendingItems.length === 0) {
      selectAllCb.checked = false;
      selectAllCb.indeterminate = false;
    } else if (count === pendingItems.length) {
      selectAllCb.checked = true;
      selectAllCb.indeterminate = false;
    } else if (count > 0) {
      selectAllCb.checked = false;
      selectAllCb.indeterminate = true;
    } else {
      selectAllCb.checked = false;
      selectAllCb.indeterminate = false;
    }
  }
}

if (selectAllCb) {
  selectAllCb.addEventListener('change', (e) => {
    if (e.target.checked) {
      pendingItems.forEach(i => selectedCandidates.add(i.candidate_id));
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
  pendingCountSpan.textContent = `${pendingItems.length} Pending`;
  pendingList.innerHTML = '';

  if (pendingItems.length === 0) {
    pendingList.innerHTML = `
      <div style="background:var(--surface-panel); border:1px solid var(--border-default); border-radius:10px; padding:40px; text-align:center; box-shadow:var(--shadow-sm);">
        <div style="width:48px; height:48px; border-radius:50%; background:var(--status-success-bg); border:1px solid var(--status-success-border); display:flex; align-items:center; justify-content:center; margin:0 auto 14px auto;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--status-success)" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <h4 style="font-size:1.15rem; font-weight:800; color:var(--text-primary); text-transform:uppercase; margin-bottom:6px;">All Clear</h4>
        <p style="color:var(--text-secondary); font-size:0.92rem; margin:0;">Zero pending candidate claims in queue for this run.</p>
      </div>
    `;
    diffView.innerHTML = `
      <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; height:100%; margin: 120px auto; max-width:480px;">
        <div style="width:56px; height:56px; border-radius:50%; background:var(--status-success-bg); border:1px solid var(--status-success-border); display:flex; align-items:center; justify-content:center; margin-bottom:16px;">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--status-success)" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <h3 style="font-size:1.4rem; font-weight:800; color:var(--text-primary); text-transform:uppercase; letter-spacing:0.04em; margin-bottom:10px;">All Claims Verified</h3>
        <p style="font-size:0.95rem; color:var(--text-secondary); line-height:1.6;">Every audited assertion in this test suite has been reviewed and recorded to the audit database.</p>
      </div>
    `;
    return;
  }

  pendingItems.forEach(item => {
    const card = document.createElement('div');
    card.className = `approval-card-mad ${selectedItem && selectedItem.candidate_id === item.candidate_id ? 'selected' : ''}`;

    const cls = (item.classification || 'unknown').toLowerCase();
    let badgeStyle = 'background:var(--surface-sunken); color:var(--text-primary); border:1px solid var(--border-default);';
    if (cls === 'novel') badgeStyle = 'background:var(--brand-50); color:var(--brand-500); border:1px solid var(--brand-100);';
    if (cls === 'corroborating') badgeStyle = 'background:var(--status-success-bg); color:var(--status-success); border:1px solid var(--status-success-border);';
    if (cls === 'contradicting') badgeStyle = 'background:var(--status-danger-bg); color:var(--status-danger); border:1px solid var(--status-danger-border);';

    const headerDiv = document.createElement('div');
    headerDiv.style.cssText = 'display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;';

    const leftHeader = document.createElement('div');
    leftHeader.style.cssText = 'display:flex; align-items:center; gap:12px;';

    const cb = el('input', '', {type: 'checkbox', className: 'bulk-cb'});
    cb.dataset.id = item.candidate_id;
    cb.dataset.run = item.run_id;
    cb.checked = selectedCandidates.has(item.candidate_id);
    cb.style.cssText = 'width:20px; height:20px; accent-color:var(--brand-500); cursor:pointer; margin:0;';
    cb.onclick = (e) => e.stopPropagation();
    cb.onchange = (e) => {
      if (e.target.checked) selectedCandidates.add(item.candidate_id);
      else selectedCandidates.delete(item.candidate_id);
      if (typeof updateBulkUI === "function") updateBulkUI();
    };
    leftHeader.appendChild(cb);

    const idStrong = el('strong', item.candidate_id, {style: {fontFamily: 'var(--font-mono)', fontSize: '1.0rem', color: 'var(--text-primary)', fontWeight: '800', letterSpacing: '0.04em'}});
    leftHeader.appendChild(idStrong);

    const badge = el('span', (item.classification || 'CLAIM').toUpperCase(), {
      style: `font-size:0.72rem; font-weight:900; padding:5px 12px; border-radius:4px; text-transform:uppercase; letter-spacing:0.12em; ${badgeStyle}`
    });

    headerDiv.appendChild(leftHeader);
    headerDiv.appendChild(badge);

    const summaryDiv = document.createElement('div');
    summaryDiv.style.cssText = 'font-size:0.98rem; color:var(--text-secondary); line-height:1.55; font-weight:400; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; text-overflow:ellipsis; margin-top:8px;';
    const summaryText = item.claim_data ? item.claim_data.statement : (item.candidate_statement || item.target_claim_id || item.action);

    const actionTag = document.createElement('span');
    actionTag.style.cssText = 'color:var(--brand-500); font-weight:800; font-family:var(--font-mono); margin-right:6px;';
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
  const candLabel = el('div', 'CLAIM CANDIDATE ID', {style: {color: 'var(--text-tertiary)', fontSize: '0.8rem', fontWeight: '800', letterSpacing: '0.15em', textTransform: 'uppercase'}});
  const candId = el('h3', item.candidate_id, {style: {fontSize: '2.0rem', fontWeight: '900', color: 'var(--text-primary)', marginTop: '6px', marginBottom: '0', fontFamily: 'var(--font-mono)', textShadow: '0 0 20px rgba(197,227,132,0.25)'}});
  leftDiv.appendChild(candLabel);
  leftDiv.appendChild(candId);

  const rightDiv = document.createElement('div');
  rightDiv.style.textAlign = 'right';
  const actLabel = el('div', 'PROPOSED MUTATION ACTION', {style: {color: 'var(--text-tertiary)', fontSize: '0.8rem', fontWeight: '800', letterSpacing: '0.15em', textTransform: 'uppercase'}});
  const actVal = el('h3', item.action || 'INSERT', {style: {fontSize: '1.6rem', fontWeight: '900', marginTop: '6px', marginBottom: '0', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)'}});
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
    stmtBox.appendChild(el('div', 'PROPOSED ASSERTION STATEMENT', {style: {fontSize: '0.78rem', color: 'var(--text-tertiary)', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
    const stmtVal = el('div', data.statement || 'No statement text provided.', {style: {fontSize: '1.25rem', color: 'var(--text-primary)', fontWeight: '600', lineHeight: '1.6', background: 'var(--surface-sunken)', border: '1px solid var(--border-default)', padding: '24px', borderRadius: '8px', boxShadow: 'inset 0 2px 10px rgba(16,7,3,0.6)'}});
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
      cell.style.cssText = 'background:var(--surface-panel); border:1px solid var(--border-subtle); padding:18px; border-radius:6px;';
      cell.appendChild(el('div', label, {style: {color: 'var(--text-tertiary)', fontSize: '0.75rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '6px'}}));
      cell.appendChild(el('div', value, {style: {color: 'var(--text-primary)', fontSize: '1.15rem', fontWeight: '800', fontFamily: 'var(--font-mono)'}}));
      grid.appendChild(cell);
    });
    contentDiv.appendChild(grid);

    if (data.source_url) {
      const urlBox = document.createElement('div');
      urlBox.style.cssText = 'background:var(--surface-panel); border:1px solid var(--border-default); padding:16px 20px; border-radius:6px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px;';
      const isWebUrl = /^https?:\/\//i.test(data.source_url);
      if (isWebUrl) {
        urlBox.innerHTML = `
          <div>
            <span style="color:var(--text-tertiary); font-size:0.75rem; font-weight:800; text-transform:uppercase; letter-spacing:0.1em; display:block; margin-bottom:4px;">External Audit Verification Citation</span>
            <a href="${safeUrl(data.source_url)}" target="_blank" style="color:var(--text-primary); font-weight:700; text-decoration:underline; font-family:var(--font-mono); font-size:0.95rem; word-break:break-all;" class="safe-url-display"></a>
          </div>
          <a href="${safeUrl(data.source_url)}" target="_blank" class="btn-primary" style="padding:6px 14px; border-radius:4px; font-size:0.8rem; font-weight:800; text-transform:uppercase; letter-spacing:0.1em; text-decoration:none;">Open Source</a>
        `;
        urlBox.querySelector('.safe-url-display').textContent = data.source_url;
      } else {
        urlBox.innerHTML = `
          <div>
            <span style="color:var(--text-tertiary); font-size:0.75rem; font-weight:800; text-transform:uppercase; letter-spacing:0.1em; display:block; margin-bottom:4px;">External Audit Verification Citation</span>
            <span style="color:var(--text-primary); font-weight:700; font-family:var(--font-mono); font-size:0.95rem; word-break:break-all;" class="safe-url-display"></span>
          </div>
        `;
        urlBox.querySelector('.safe-url-display').textContent = data.source_url + ' (internal reference — not externally viewable)';
      }
      contentDiv.appendChild(urlBox);
    }
  } else if (item.classification === 'corroborating') {
    const targetBox = document.createElement('div');
    targetBox.appendChild(el('div', 'Target Claim Identifier', {style: {fontSize: '0.78rem', color: 'var(--text-tertiary)', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
    targetBox.appendChild(el('div', item.target_claim_id || 'UNKNOWN', {style: {fontSize: '1.4rem', fontWeight: '900', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', background: 'var(--surface-sunken)', border: '1px solid var(--border-default)', padding: '16px 20px', borderRadius: '6px'}}));
    contentDiv.appendChild(targetBox);

    const diffBox = document.createElement('div');
    diffBox.appendChild(el('div', 'Proposed Knowledge Mutation Payload', {style: {fontSize: '0.78rem', color: 'var(--text-tertiary)', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
    const pre = document.createElement('pre');
    pre.style.cssText = 'background:var(--surface-sunken); border:1px solid var(--border-default); padding:22px; border-radius:8px; overflow-x:auto; font-family:var(--font-mono); font-size:0.95rem; color:var(--brand-500); line-height:1.5; box-shadow:inset 0 2px 12px rgba(16,7,3,0.8);';
    pre.textContent = JSON.stringify(item.changes, null, 2);
    diffBox.appendChild(pre);
    contentDiv.appendChild(diffBox);
  } else {
    if (item.target_claim_id) {
      const targetBox = document.createElement('div');
      targetBox.appendChild(el('div', 'Contested Claim Identifier', {style: {fontSize: '0.78rem', color: 'var(--text-tertiary)', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
      targetBox.appendChild(el('div', item.target_claim_id, {style: {fontSize: '1.4rem', fontWeight: '900', fontFamily: 'var(--font-mono)', color: 'var(--status-danger-text)', background: 'var(--status-danger-bg)', border: '1px solid var(--status-danger-border)', padding: '16px 20px', borderRadius: '6px'}}));
      contentDiv.appendChild(targetBox);
    }

    if (item.candidate_statement) {
      const stmtBox = document.createElement('div');
      stmtBox.appendChild(el('div', 'Contradicting Assertion Statement', {style: {fontSize: '0.78rem', color: 'var(--text-tertiary)', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
      stmtBox.appendChild(el('div', item.candidate_statement, {style: {fontSize: '1.25rem', color: 'var(--text-primary)', fontWeight: '700', lineHeight: '1.6', background: 'var(--surface-sunken)', border: '1px solid var(--border-default)', padding: '24px', borderRadius: '8px'}}));
      contentDiv.appendChild(stmtBox);
    }

    if (item.rationale) {
      const ratBox = document.createElement('div');
      ratBox.appendChild(el('div', 'Audit Rationale & Analysis', {style: {fontSize: '0.78rem', color: 'var(--text-tertiary)', fontWeight: '800', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: '8px'}}));
      ratBox.appendChild(el('div', item.rationale, {style: {fontSize: '1.05rem', color: 'var(--text-secondary)', lineHeight: '1.7', background: 'var(--surface-panel)', border: '1px solid var(--border-default)', padding: '20px', borderRadius: '6px'}}));
      contentDiv.appendChild(ratBox);
    }

    if (item.adversarial_critique) {
      const critBox = document.createElement('div');
      critBox.style.cssText = 'background:var(--status-danger-bg); border:1px solid var(--status-danger-border); padding:16px 20px; border-radius:var(--radius-md);';
      critBox.appendChild(el('div', 'Adversarial AI Red-Team Critique', {style: {fontSize: '0.85rem', fontWeight: '900', color: 'var(--status-danger-text)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '10px'}}));
      critBox.appendChild(el('div', item.adversarial_critique, {style: {whiteSpace: 'pre-wrap', fontSize: '1.0rem', color: 'var(--text-primary)', lineHeight: '1.65'}}));
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
  btnApprove.innerHTML = 'Approve Mutation & Commit';
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
    reasonEl.style.cssText = 'width:100%; margin-top:10px; padding:10px; border-radius:6px; border:1px solid var(--border-default); background:var(--surface-sunken); color:var(--text-primary);';
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
      return AreosAPI.fetch(`${API_BASE}/approvals/${item.run_id}/${item.candidate_id}`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Idempotency-Key': `bulk_${item.candidate_id}_${action}_${Date.now()}`
        },
        body: JSON.stringify({ action, rejection_reason })
      }).then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return item.candidate_id;
      });
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
if (pendingList) {
  fetchPendingApprovals();
}
