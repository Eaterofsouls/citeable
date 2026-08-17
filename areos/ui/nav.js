/**
 * nav.js
 * Centralized navigation for all 7 Citeable pages (Batch B1).
 * Replaces hardcoded <nav> blocks.
 */


 // MF-24: Cmd+K Palette + Admin Auth Modal
 const paletteHTML = `
 <div id="cmdk-modal" class="modal-overlay" style="display:none; align-items:flex-start; padding-top:10vh; z-index:99999;">
 <div class="modal-content glass-panel" style="max-width:500px; width:100%; padding:0; overflow:hidden;">
 <input type="text" id="cmdk-input" role="searchbox" aria-label="Search claims or navigate to a page" placeholder="Search claims or go to..." style="width:100%; padding:16px; border:none; background:transparent; color:var(--text); font-size:1.1rem; outline:none; border-bottom:1px solid var(--border);">
 <div id="cmdk-results" role="listbox" aria-label="Results" style="max-height:400px; overflow-y:auto; padding:8px 0;"></div>
 </div>
 </div>
 
 <div id="admin-auth-modal" class="modal-overlay" style="display:none; align-items:flex-start; padding-top:15vh; z-index:99999;">
 <div class="modal-content glass-panel" style="max-width:400px; width:100%; padding:24px; text-align:center;">
 <h3 style="margin-bottom:16px;">Admin Authentication</h3>
 <input type="password" id="admin-auth-input" placeholder="Enter Admin Token" style="width:100%; padding:12px; margin-bottom:16px; border-radius:6px; border:1px solid var(--border); background:rgba(0,0,0,0.2); color:#fff; outline:none;">
 <button id="admin-auth-submit" class="btn" style="width:100%;">Authenticate</button>
 </div>
 </div>`;
 
 let cmdkDialog = null;

 document.addEventListener('DOMContentLoaded', () => {
 document.body.insertAdjacentHTML('beforeend', paletteHTML);

 const cmdkModal = document.getElementById('cmdk-modal');
 const cmdkInput = document.getElementById('cmdk-input');
 const cmdkResults = document.getElementById('cmdk-results');

 // UI/UX Audit fix: role="dialog" + focus trap + Escape + focus-return.
 // This palette is loaded on every page (nav.js is shared app-wide), so
 // this one fix covers the command palette everywhere, not just index.
 if (typeof makeDialogAccessible === 'function') {
 cmdkDialog = makeDialogAccessible(cmdkModal, {
 label: 'Command palette',
 onClose: () => { cmdkModal.style.display = 'none'; cmdkDialog.close(); },
 });
 }

 document.addEventListener('keydown', (e) => {
 if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'a') {
 e.preventDefault();
 const authModal = document.getElementById('admin-auth-modal');
 authModal.style.display = 'flex';
 document.getElementById('admin-auth-input').focus();
 }
 if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
 e.preventDefault();
 cmdkModal.style.display = 'flex';
 cmdkInput.focus();
 if (cmdkDialog) cmdkDialog.open();
 renderCmdk(cmdkInput.value);
 }
 if (e.key === 'Escape') {
 if (cmdkModal.style.display === 'flex') {
 if (cmdkDialog) cmdkDialog.close();
 cmdkModal.style.display = 'none';
 }
 const authModal = document.getElementById('admin-auth-modal');
 if (authModal && authModal.style.display === 'flex') {
 authModal.style.display = 'none';
 }
 }
 });
 
 document.getElementById('admin-auth-submit').addEventListener('click', () => {
 const token = document.getElementById('admin-auth-input').value.trim();
 if (token) {
 sessionStorage.setItem('areos_api_token', token);
 window.location.reload();
 }
 });
 
 document.getElementById('admin-auth-input').addEventListener('keydown', (e) => {
 if (e.key === 'Enter') document.getElementById('admin-auth-submit').click();
 });
 
 cmdkModal.addEventListener('click', (e) => {
 if (e.target === cmdkModal) {
 if (cmdkDialog) cmdkDialog.close();
 cmdkModal.style.display = 'none';
 }
 });

 let cmdkTimeout;
 cmdkInput.addEventListener('input', (e) => {
 clearTimeout(cmdkTimeout);
 cmdkTimeout = setTimeout(() => renderCmdk(e.target.value), 300);
 });
 });

 async function renderCmdk(query) {
 let html = '';
 const q = query.toLowerCase();
 
 // Match routes
 const matchedRoutes = ROUTES.filter(r => r.label && r.label.toLowerCase().includes(q));
 if (matchedRoutes.length > 0) {
 html += `<div style="padding:4px 16px; font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase;">Pages</div>`;
 matchedRoutes.forEach(r => {
 html += `<button type="button" role="option" class="cmdk-item" style="padding:10px 16px; cursor:pointer; display:flex; align-items:center; gap:8px;" onclick="window.location.href='${r.path}'">
 <span>${r.icon}</span> <span>${r.label}</span>
 </button>`;
 });
 }

 // Match claims via API if query > 2
 if (q.length > 2) {
 html += `<div style="padding:8px 16px 4px 16px; font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase;">Claims</div>`;
 try {
 const res = await fetch(`/api/v1/claims?search_query=${encodeURIComponent(q)}&limit=5`);
 if (res.ok) {
 const data = await res.json();
 if (data.claims.length === 0) {
 html += `<div style="padding:8px 16px; color:var(--text-secondary);">No claims found</div>`;
 } else {
 data.claims.forEach(c => {
 html += `<button type="button" role="option" class="cmdk-item" style="padding:10px 16px; cursor:pointer;" onclick="window.location.href='claims_browser.html?claim_id=${c.claim_id}'">
 <div style="font-size:0.85rem; color:var(--text-secondary);">${c.claim_id}</div>
 <div style="font-size:0.95rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${c.statement}</div>
 </button>`;
 });
 }
 }
 } catch(e) {}
 }
 
 cmdkResults.innerHTML = html;
 
 // Add hover styles (+ button reset, now that .cmdk-item is a <button>)
 if (!document.getElementById('cmdk-style')) {
 const style = document.createElement('style');
 style.id = 'cmdk-style';
 style.textContent = `
 .cmdk-item { background: none; border: none; width: 100%; text-align: left; color: var(--text-primary); font-family: inherit; }
 .cmdk-item:hover, .cmdk-item:focus-visible { background: rgba(255,255,255,0.05); outline: none; }
 `;
 document.head.appendChild(style);
 }
 }
 

window.AreosNav = {
 workflowItems: [
 {
 id: "studio",
 label: "Audit Studio",
 href: "index.html",
 icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>`,
 strong: true
 },
 {
 id: "claims",
 label: "Claims Browser",
 href: "claims_browser.html",
 icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"></path></svg>`
 },
 {
 id: "approvals",
 label: "Approvals",
 href: "approvals.html",
 icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"></path><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>`
 }
 ],
 configItems: [
 {
 id: "docs",
 label: "Documentation",
 href: "docs.html",
 icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>`
 },
 {
 id: "prompts",
 label: "Prompt Design",
 href: "prompts.html",
 icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`
 },
 {
 id: "synthesis_prompts",
 label: "Synthesis Prompts",
 href: "synthesis_prompts.html",
 icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10"></path><path d="M12 2v10l7 4"></path></svg>`
 },
 {
 id: "case_study",
 label: "Case Study",
 href: "case_study.html",
 icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>`
 },
 {
 id: "byok",
 label: "BYOK AI Vault",
 href: "#byok_vault",
 onclick: "event.preventDefault(); if (window.BYOKVault) { window.BYOKVault.open(); } else { alert('BYOK Vault domain loading...'); } return false;",
 icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path></svg>`
 }
 ],

 /**
 * Renders the navigation into #main-nav
 * @param {string} activeId - the id of the active page (e.g., 'claims', 'studio')
 */
 renderNav(activeId) {
 // Automatically attach isolated byok.js domain script app-wide if not present
 if (!document.querySelector('script[src*="byok.js"]')) {
 const byokScript = document.createElement('script');
 byokScript.src = 'byok.js';
 document.head.appendChild(byokScript);
 }

 const navEl = document.getElementById("main-nav");
 if (!navEl) return;
 
 let html = "";
 const runId = window.AreosContext?.activeRunId;
 const qp = runId ? `?run_id=${encodeURIComponent(runId)}` : "";

 // Workflow section
 const adminIds = ["approvals", "outcome", "prompts", "case_study", "synthesis_prompts"];
 const hasToken = !!sessionStorage.getItem('areos_api_token');
 
 html += `<div style="padding: 16px 16px 8px; font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Workflow</div>`;
 for (const item of this.workflowItems) {
 if (adminIds.includes(item.id) && !hasToken) continue;
 const isActive = item.id === activeId ? "active" : "";
 const content = item.strong ? `<strong>${item.label}</strong>` : item.label;
 html += `
 <a href="${item.href}${qp}" class="nav-item ${isActive}">
 ${item.icon}
 ${content}
 </a>
 `;
 }

 // Config section
 html += `<div style="padding: 24px 16px 8px; font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Configuration</div>`;
 for (const item of this.configItems) {
 if (adminIds.includes(item.id) && !hasToken) continue;
 const isActive = item.id === activeId ? "active" : "";
 const clickAttr = item.onclick ? `onclick="${item.onclick}"` : "";
 const hrefAttr = item.onclick ? 'href="javascript:void(0);"' : `href="${item.href}${qp}"`;
 const customStyle = item.id === "byok" ? 'border: 1px solid #4ADE80; margin: 12px 10px 4px 10px; border-radius: 6px; color: #FFFFFF; font-weight: 700; background: rgba(74, 222, 128, 0.1);' : '';
 html += `
 <a ${hrefAttr} ${clickAttr} class="nav-item ${isActive}" style="${customStyle}">
 ${item.icon}
 ${item.label}
 </a>
 `;
 }
 // Inject Run Context Chip into topbar
 const topbar = document.querySelector(".topbar");
 if (topbar && !document.getElementById("run-context-chip")) {
 const chipHtml = runId 
 ? `<div id="run-context-chip" class="run-context-chip" style="display:flex; align-items:center; gap:8px; background:var(--surface-panel); border:1px solid var(--border-default); padding:6px 12px; border-radius:var(--radius-full); margin-left:auto; font-size:0.85rem; cursor:pointer;" title="Click to clear active run context" onclick="window.AreosContext.activeRunId = null; window.location.reload();">
 <span style="width:8px; height:8px; border-radius:50%; background:var(--status-success);"></span>
 <span style="color:var(--text-primary); font-family:var(--font-mono);">Run ${runId.substring(0,8)}</span>
 <span style="color:var(--text-secondary); font-size:0.75rem;">(Active)</span>
 </div>`
 : `<div id="run-context-chip" class="run-context-chip" style="display:flex; align-items:center; gap:8px; background:var(--surface-panel); border:1px solid var(--border-default); padding:6px 12px; border-radius:var(--radius-full); margin-left:auto; font-size:0.85rem; color:var(--text-secondary);">
 <span style="width:8px; height:8px; border-radius:50%; background:var(--border-strong);"></span>
 <span>Global View (No Active Run)</span>
 </div>`;
 topbar.insertAdjacentHTML('beforeend', chipHtml);
 
 // Add hamburger button for mobile
 const hamburgerHtml = `
 <button id="mobile-menu-btn" style="display:none; background:none; border:none; color:var(--text-primary); cursor:pointer; padding:8px; margin-right:12px;">
 <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
 </button>
 `;
 topbar.insertAdjacentHTML('afterbegin', hamburgerHtml);
 
 // Show hamburger on mobile
 const style = document.createElement('style');
 style.textContent = `@media (max-width: 768px) { #mobile-menu-btn { display: block !important; } }`;
 document.head.appendChild(style);
 }

 // Add overlay to body if not exists
 if (!document.getElementById("sidebar-overlay")) {
 const overlay = document.createElement("div");
 overlay.id = "sidebar-overlay";
 overlay.className = "sidebar-overlay";
 document.body.appendChild(overlay);
 
 overlay.addEventListener('click', () => {
 document.querySelector('.sidebar').classList.remove('open');
 overlay.classList.remove('open');
 });
 }
 
 // Wire hamburger
 if (topbar && document.getElementById("mobile-menu-btn")) {
 document.getElementById("mobile-menu-btn").addEventListener('click', () => {
 const sidebar = document.querySelector('.sidebar');
 const overlay = document.getElementById('sidebar-overlay');
 if (sidebar) sidebar.classList.add('open');
 if (overlay) overlay.classList.add('open');
 });
 }

 // Dynamically inject Breadcrumbs below topbar
 const pageItem = [...this.workflowItems, ...this.configItems].find(i => i.id === activeId);
 if (pageItem && !document.getElementById("breadcrumbs")) {
 const main = document.querySelector(".main-content");
 if (main) {
 // If there's a topbar, insert after it, else insert at top
 const bcHtml = `<div id="breadcrumbs" style="padding: 12px 32px; font-size: 0.85rem; color: var(--text-secondary); border-bottom: 1px solid var(--border-subtle);">
 <a href="index.html" style="color: var(--brand-text-on-canvas); text-decoration: none;">Citeable</a> / <span style="color: var(--text-primary);">${pageItem.label}</span>
 </div>`;
 if (topbar) {
 topbar.insertAdjacentHTML('afterend', bcHtml);
 } else {
 main.insertAdjacentHTML('afterbegin', bcHtml);
 }
 }
 }
 
 navEl.innerHTML = html;
 }
};
